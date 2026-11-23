"""Team area: orders and shipping (the Fulfilment role)."""

import csv

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_POST

from orders import payments, services
from orders.forms import ShipOrderForm, StaffNoteForm
from orders.models import Order

from ..mixins import team_required
from ..permissions import Area

TABS = {
    "to-ship": (gettext_lazy("To ship"), Q(status=Order.Status.PAID)),
    "shipped": (gettext_lazy("Shipped"), Q(status__in=[Order.Status.SHIPPED, Order.Status.DELIVERED])),
    "awaiting": (gettext_lazy("Awaiting payment"), Q(status=Order.Status.PENDING)),
    "closed": (gettext_lazy("Cancelled & refunded"), Q(status__in=[Order.Status.CANCELLED, Order.Status.REFUNDED])),
    "all": (gettext_lazy("All"), Q()),
}


@team_required(Area.ORDERS)
def order_list(request):
    tab = request.GET.get("tab", "to-ship")
    if tab not in TABS:
        tab = "to-ship"
    orders = Order.objects.filter(TABS[tab][1]).prefetch_related("items")

    if query := request.GET.get("q", "").strip():
        orders = orders.filter(Q(number__icontains=query) | Q(full_name__icontains=query) | Q(email__icontains=query))

    # Oldest first when there's work to do; newest first otherwise.
    orders = orders.order_by("paid_at" if tab == "to-ship" else "-created_at")
    counts = {key: Order.objects.filter(condition).count() for key, (_label, condition) in TABS.items() if key != "all"}

    context = {
        "page": Paginator(orders, 30).get_page(request.GET.get("page")),
        "tabs": [(key, label, counts.get(key)) for key, (label, _condition) in TABS.items()],
        "tab": tab,
        "query": query,
    }
    return render(request, "team/order_list.html", context)


@team_required(Area.ORDERS)
def order_detail(request, number):
    order = get_object_or_404(Order.objects.prefetch_related("items__wine"), number=number)
    context = {
        "order": order,
        "ship_form": ShipOrderForm(),
        "note_form": StaffNoteForm(instance=order),
    }
    return render(request, "team/order_detail.html", context)


@team_required(Area.ORDERS)
@require_POST
def order_ship(request, number):
    order = get_object_or_404(Order, number=number)
    form = ShipOrderForm(request.POST)
    if not order.can_ship:
        messages.error(request, _("Only paid orders can be marked as shipped."))
    elif form.is_valid():
        services.mark_shipped(order, form.cleaned_data["carrier"], form.cleaned_data["tracking_number"])
        messages.success(
            request,
            _("Order %(number)s is marked as shipped and the customer has been emailed.") % {"number": order.number},
        )
    else:
        messages.error(request, _("Please check the carrier and tracking number."))
    return redirect("team:order_detail", number=order.number)


@team_required(Area.ORDERS)
@require_POST
def order_delivered(request, number):
    order = get_object_or_404(Order, number=number)
    if order.status == Order.Status.SHIPPED:
        services.mark_delivered(order)
        messages.success(request, _("Order %(number)s is marked as delivered.") % {"number": order.number})
    else:
        messages.error(request, _("Only shipped orders can be marked as delivered."))
    return redirect("team:order_detail", number=order.number)


@team_required(Area.ORDERS)
@require_POST
def order_cancel(request, number):
    order = get_object_or_404(Order, number=number)
    if not order.can_cancel:
        messages.error(request, _("This order can't be cancelled any more."))
        return redirect("team:order_detail", number=order.number)

    was_paid = order.is_paid
    if order.is_pending and order.stripe_payment_intent_id:
        payments.cancel_intent(order.stripe_payment_intent_id)
    services.cancel(order)
    if was_paid:
        messages.warning(
            request,
            _(
                "Order %(number)s is cancelled and its bottles are back in stock. "
                "Now refund the payment in the Stripe dashboard; the order will show as refunded."
            )
            % {"number": order.number},
        )
    else:
        messages.success(request, _("Order %(number)s is cancelled.") % {"number": order.number})
    return redirect("team:order_detail", number=order.number)


@team_required(Area.ORDERS)
@require_POST
def order_note(request, number):
    order = get_object_or_404(Order, number=number)
    form = StaffNoteForm(request.POST, instance=order)
    if form.is_valid():
        form.save()
        messages.success(request, _("Internal note saved."))
    return redirect("team:order_detail", number=order.number)


@team_required(Area.ORDERS)
def packing_list(request):
    """CSV of every paid order not yet shipped: one row per order, for the courier's bulk import or printing."""
    orders = Order.objects.filter(status=Order.Status.PAID).order_by("paid_at").prefetch_related("items")
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    filename = f"vinop-packing-list-{timezone.localdate():%Y-%m-%d}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("﻿")  # lets Excel open the umlauts and accents correctly

    writer = csv.writer(response)
    writer.writerow(
        [
            "order",
            "paid",
            "name",
            "street",
            "address line 2",
            "postcode",
            "city",
            "region",
            "country",
            "phone",
            "email",
            "bottles",
            "contents",
            "note",
        ]
    )
    for order in orders:
        writer.writerow(
            [
                order.number,
                timezone.localtime(order.paid_at).strftime("%Y-%m-%d %H:%M") if order.paid_at else "",
                order.full_name,
                order.street_address1,
                order.street_address2,
                order.postcode,
                order.city,
                order.region,
                order.country.code,
                order.phone,
                order.email,
                order.bottle_count,
                "; ".join(f"{item.quantity}× {item.wine_name}" for item in order.items.all()),
                order.customer_note,
            ]
        )
    return response
