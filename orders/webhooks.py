"""
Stripe webhook: Stripe's servers tell us what happened to a payment.

This is the reliable path. The customer might close the tab before coming
back from the bank page; the webhook still arrives (Stripe retries for up
to three days until we answer 200), and mark_paid() is safe to call twice.

Set it up in the Stripe dashboard (Developers → Webhooks) pointing at
https://<your-domain>/checkout/webhook/ with these events:
    payment_intent.succeeded
    payment_intent.payment_failed
    charge.refunded
Locally:  stripe listen --forward-to localhost:8000/checkout/webhook/
"""

import logging

from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import payments, services
from .models import Order

log = logging.getLogger(__name__)


def _order_for_intent(intent) -> Order | None:
    order = Order.objects.filter(stripe_payment_intent_id=intent.id).first()
    if order is None:
        number = (intent.get("metadata") or {}).get("order_number")
        order = Order.objects.filter(number=number).first() if number else None
    return order


def payment_succeeded(intent) -> None:
    order = _order_for_intent(intent)
    if order is None:
        log.warning("Payment %s succeeded but no order matches it.", intent.id)
        return
    services.mark_paid(order, intent)


def payment_failed(intent) -> None:
    error = intent.get("last_payment_error") or {}
    log.info("Payment %s failed: %s", intent.id, error.get("message", "no reason given"))


def charge_refunded(charge) -> None:
    order = Order.objects.filter(stripe_payment_intent_id=charge.get("payment_intent")).first()
    if order and charge.get("refunded"):  # True only when the full amount was refunded
        services.mark_refunded(order)


HANDLERS = {
    "payment_intent.succeeded": payment_succeeded,
    "payment_intent.payment_failed": payment_failed,
    "charge.refunded": charge_refunded,
}


@csrf_exempt  # Stripe can't send our CSRF token; the signature check replaces it.
@require_POST
def stripe_webhook(request):
    signature = request.headers.get("Stripe-Signature", "")
    try:
        event = payments.construct_event(request.body, signature)
    except (ValueError, payments.SignatureVerificationError):
        return HttpResponseBadRequest("Invalid payload or signature.")
    except payments.PaymentsNotConfigured:
        return HttpResponse("Stripe is not configured.", status=503)

    handler = HANDLERS.get(event.type)
    if handler:
        handler(event.data.object)
    return HttpResponse(status=200)
