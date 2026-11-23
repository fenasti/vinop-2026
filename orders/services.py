"""
The business steps of an order, independent of any view:

    save_checkout()   delivery form + cart  → PENDING order
    sync_items()      copy the cart into the order (snapshot prices)
    mark_paid()       Stripe confirmed      → PAID, invoice number, stock, emails
    mark_shipped()    team packed it        → SHIPPED, email with tracking
    mark_delivered(), cancel(), mark_refunded()

mark_paid() is called from two places (the customer's return page and the
Stripe webhook) and may run twice for the same payment. It locks the order
row and only acts while the order is still PENDING, so the second call does
nothing — no double emails, no double stock reduction. The first VinOp
matched orders by comparing a dozen address fields and could create
duplicates; this is the fix.
"""

import logging

from django.db import transaction
from django.db.models import F, Value
from django.db.models.functions import Greatest
from django.utils import timezone

from catalog.models import Wine

from . import emails
from .models import InvoiceSequence, Order, OrderItem

log = logging.getLogger(__name__)


@transaction.atomic
def save_checkout(form, cart, user) -> Order:
    """Save the delivery form as a PENDING order holding the cart's wines."""
    order = form.save(commit=False)
    order.status = Order.Status.PENDING
    order.user = user if user.is_authenticated else None
    order.terms_accepted_at = timezone.now()
    order.save()
    sync_items(order, cart)
    return order


@transaction.atomic
def sync_items(order: Order, cart) -> Order:
    """Replace the order's items with the cart's current lines and prices."""
    order.items.all().delete()
    OrderItem.objects.bulk_create(
        OrderItem(
            order=order,
            wine=line.wine,
            wine_name=line.wine.full_name,
            unit_price=line.wine.price,
            quantity=line.quantity,
            line_total=line.total,  # bulk_create skips save(), so set it here
        )
        for line in cart
    )
    order.recalculate()
    order.save(update_fields=["subtotal", "shipping_cost", "total", "updated_at"])
    return order


def mark_paid(order: Order, intent) -> bool:
    """
    Record a successful Stripe payment. Returns True if this call did the
    work, False if the order had already been handled.
    """
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order.pk)
        if order.status == Order.Status.CANCELLED:
            # The team cancelled it while the customer was paying: flag it loudly.
            order.staff_note = f"{order.staff_note}\nPAID AFTER CANCELLATION: refund it in Stripe.".strip()
            order.save(update_fields=["staff_note", "updated_at"])
            log.error("Order %s was paid after being cancelled.", order.number)
            return False
        if order.status != Order.Status.PENDING:
            return False

        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.stripe_payment_intent_id = intent.id
        order.invoice_number = InvoiceSequence.next_number()

        received = getattr(intent, "amount_received", None) or getattr(intent, "amount", 0)
        if received != order.total_cents:
            order.staff_note = (
                f"{order.staff_note}\nCHECK BEFORE SHIPPING: Stripe received {received / 100:.2f} € "
                f"but the order total is {order.total} €."
            ).strip()
            log.error("Amount mismatch on order %s: %s cents vs %s", order.number, received, order.total_cents)

        order.save()

        for item in order.items.exclude(wine=None):
            Wine.objects.filter(pk=item.wine_id).update(stock=Greatest(F("stock") - item.quantity, Value(0)))

        transaction.on_commit(lambda: emails.send_order_emails(order.pk))
    return True


def mark_shipped(order: Order, carrier: str, tracking_number: str) -> None:
    order.status = Order.Status.SHIPPED
    order.shipped_at = timezone.now()
    order.carrier = carrier
    order.tracking_number = tracking_number
    order.save(update_fields=["status", "shipped_at", "carrier", "tracking_number", "updated_at"])
    emails.send_shipping_update(order)


def mark_delivered(order: Order) -> None:
    order.status = Order.Status.DELIVERED
    order.save(update_fields=["status", "updated_at"])


@transaction.atomic
def cancel(order: Order) -> None:
    """
    Cancel an unpaid or paid order. Bottles of a paid order go back into
    stock. The refund itself is made in the Stripe dashboard; Stripe then
    tells us via the webhook and the order becomes REFUNDED.
    """
    was_paid = order.status == Order.Status.PAID
    order.status = Order.Status.CANCELLED
    order.save(update_fields=["status", "updated_at"])
    if was_paid:
        for item in order.items.exclude(wine=None):
            Wine.objects.filter(pk=item.wine_id).update(stock=F("stock") + item.quantity)


def mark_refunded(order: Order) -> None:
    if order.status == Order.Status.REFUNDED:
        return
    order.status = Order.Status.REFUNDED
    order.save(update_fields=["status", "updated_at"])
