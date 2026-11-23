"""
Order emails (templates in templates/emails/).

If the mail server is down, `confirmation_sent_at` stays empty, so the next
Stripe webhook retry sends the confirmation again.
"""

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from core.emails import send_templated_email

from .models import Order


def send_order_emails(order_id: int) -> None:
    """Confirmation to the customer (once) + a 'new order' alert to the shop."""
    order = Order.objects.prefetch_related("items").get(pk=order_id)
    if order.confirmation_sent_at:
        return

    # Guests have no account page to link to; the email itself has every detail.
    order_url = (settings.SITE_URL + reverse("accounts:order_detail", args=[order.number])) if order.user_id else ""
    if send_templated_email("order_confirmation", {"order": order, "order_url": order_url}, [order.email]):
        order.confirmation_sent_at = timezone.now()
        order.save(update_fields=["confirmation_sent_at"])

    team_url = settings.SITE_URL + reverse("team:order_detail", args=[order.number])
    send_templated_email("order_new_alert", {"order": order, "team_url": team_url}, [settings.STORE_OWNER_EMAIL])


def send_shipping_update(order: Order) -> None:
    send_templated_email("order_shipped", {"order": order}, [order.email])
