"""
Checkout in three steps, each its own URL:

  1. /checkout/                      delivery details  → creates a PENDING order
  2. /checkout/<number>/pay/         Stripe Payment Element (amount from the order)
  3. /checkout/<number>/complete/    Stripe sends the customer back here
     → /checkout/<number>/thank-you/ the confirmation page

Plus /checkout/webhook/ (see webhooks.py), Stripe's server-to-server call.
"""

import logging

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _

from accounts.models import Profile
from cart.cart import Cart

from . import access, payments, services
from .forms import CheckoutForm
from .models import Order

log = logging.getLogger(__name__)


def _order_for(request, number) -> Order:
    order = get_object_or_404(Order.objects.prefetch_related("items"), number=number)
    if not access.can_view(request, order):
        raise Http404  # don't reveal that the order number exists
    return order


def _pending_order(request) -> Order | None:
    """The order this browser started earlier, if it's still waiting for payment."""
    number = request.session.get(access.PENDING_KEY)
    if not number:
        return None
    order = Order.objects.filter(number=number, status=Order.Status.PENDING).first()
    if order and order.user_id and order.user_id != request.user.pk:
        return None
    return order


def _cart_is_ready(request, cart) -> bool:
    """Empty cart or not enough stock → send the customer back with a reason."""
    if not cart:
        messages.info(request, _("Your cart is empty. Add a few bottles first."))
        return False
    if cart.fix_stock_problems():
        messages.warning(
            request, _("Some wines just ran low, so we adjusted your cart. Please check it before paying.")
        )
        return False
    return True


def _finish_checkout(request) -> None:
    Cart(request).clear()
    request.session.pop(access.PENDING_KEY, None)


def checkout(request):
    cart = Cart(request)
    if not _cart_is_ready(request, cart):
        return redirect("cart:detail" if cart else "catalog:list")

    pending = _pending_order(request)
    if request.method == "POST":
        form = CheckoutForm(request.POST, instance=pending, user=request.user)
        if form.is_valid():
            order = services.save_checkout(form, cart, request.user)
            request.session[access.PENDING_KEY] = order.number
            access.grant(request, order)
            if form.cleaned_data.get("save_address"):
                Profile.for_user(request.user).copy_address_from(order)
            return redirect("orders:pay", number=order.number)
        messages.error(request, _("Please check the highlighted fields."))
    else:
        initial = {} if pending else _initial_details(request)
        form = CheckoutForm(instance=pending, initial=initial, user=request.user)

    return render(request, "orders/checkout.html", {"form": form, "cart": cart})


def _initial_details(request) -> dict:
    if not request.user.is_authenticated:
        return {}
    profile = Profile.for_user(request.user)
    return {"email": request.user.email, **profile.address_as_initial()}


def pay(request, number):
    order = _order_for(request, number)
    if not order.is_pending:
        return redirect("orders:confirmation", number=order.number)

    cart = Cart(request)
    if not _cart_is_ready(request, cart):
        return redirect("cart:detail" if cart else "catalog:list")
    services.sync_items(order, cart)  # the customer may have changed the cart in another tab

    try:
        client_secret = payments.prepare_payment(order)
    except (payments.AlreadyPaid, payments.PaymentProcessing):
        return redirect("orders:complete", number=order.number)
    except payments.PaymentsNotConfigured:
        messages.error(request, _("Payments aren't set up yet. Add your Stripe keys to the .env file."))
        return redirect("orders:checkout")
    except payments.StripeError:
        log.exception("Stripe failed while preparing order %s", order.number)
        messages.error(request, _("We couldn't reach our payment provider. Please try again in a minute."))
        return redirect("orders:checkout")

    stripe_config = {
        "publishableKey": settings.STRIPE_PUBLIC_KEY,
        "clientSecret": client_secret,
        "returnUrl": request.build_absolute_uri(reverse("orders:complete", args=[order.number])),
        "billingName": order.full_name,
        "billingEmail": order.email,
    }
    return render(request, "orders/pay.html", {"order": order, "stripe_config": stripe_config})


def complete(request, number):
    """Stripe redirects here after the payment form (also after 3-D Secure, iDEAL, Klarna…)."""
    order = _order_for(request, number)

    if order.is_pending and order.stripe_payment_intent_id:
        try:
            intent = payments.retrieve_intent(order.stripe_payment_intent_id)
        except (payments.StripeError, payments.PaymentsNotConfigured):
            log.exception("Could not check the payment for order %s", order.number)
            intent = None

        status = getattr(intent, "status", None)
        if status == "succeeded":
            services.mark_paid(order, intent)
        elif status == "processing":
            _finish_checkout(request)
            return redirect("orders:confirmation", number=order.number)
        elif status in ("requires_payment_method", "requires_confirmation", "requires_action", "canceled"):
            messages.error(
                request, _("Your payment didn't go through. Please try again or choose another payment method.")
            )
            return redirect("orders:pay", number=order.number)
        elif status is None:
            messages.warning(
                request, _("We couldn't confirm your payment just yet. You'll get an email as soon as it's through.")
            )
            return redirect("orders:confirmation", number=order.number)
        order.refresh_from_db()

    if order.is_paid:
        _finish_checkout(request)
    return redirect("orders:confirmation", number=order.number)


def confirmation(request, number):
    order = _order_for(request, number)
    if order.is_pending and not order.stripe_payment_intent_id:
        return redirect("orders:pay", number=order.number)
    return render(request, "orders/confirmation.html", {"order": order})
