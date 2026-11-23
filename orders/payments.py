"""
Everything that talks to Stripe lives here, behind a few small functions,
so views stay readable and tests can replace Stripe with a fake.

We use Stripe's Payment Element: one embedded form that offers cards,
Apple/Google Pay, SEPA Direct Debit, iDEAL, Bancontact, Klarna… whatever
is switched on in your Stripe dashboard for EUR payments.
"""

import logging

import stripe
from django.conf import settings
from stripe import StripeClient

log = logging.getLogger(__name__)

# PaymentIntent states in which we can still change the amount.
EDITABLE_STATES = {"requires_payment_method", "requires_confirmation", "requires_action"}

# Re-exported so callers can `except payments.StripeError` without importing stripe.
StripeError = stripe.StripeError
SignatureVerificationError = stripe.SignatureVerificationError


class PaymentsNotConfigured(Exception):
    """STRIPE_SECRET_KEY is missing."""


class AlreadyPaid(Exception):
    """The order's PaymentIntent has already succeeded."""


class PaymentProcessing(Exception):
    """The bank is still confirming (e.g. SEPA Direct Debit takes days)."""


def get_client() -> StripeClient:
    if not settings.STRIPE_SECRET_KEY:
        raise PaymentsNotConfigured
    return StripeClient(settings.STRIPE_SECRET_KEY, max_network_retries=2)


def _intent_details(order) -> dict:
    return {
        "amount": order.total_cents,
        "currency": settings.STRIPE_CURRENCY,
        "receipt_email": order.email,
        "description": f"VinOp order {order.number}",
        "metadata": {"order_number": order.number},
        "shipping": {
            "name": order.full_name,
            "phone": order.phone,
            "address": {
                "line1": order.street_address1,
                "line2": order.street_address2 or None,
                "postal_code": order.postcode,
                "city": order.city,
                "state": order.region or None,
                "country": order.country.code,
            },
        },
    }


def prepare_payment(order) -> str:
    """
    Make sure the order has a PaymentIntent for exactly its current total,
    and return the client secret the browser needs to show the payment form.
    """
    client = get_client()
    details = _intent_details(order)

    if order.stripe_payment_intent_id:
        intent = client.v1.payment_intents.retrieve(order.stripe_payment_intent_id)
        if intent.status == "succeeded":
            raise AlreadyPaid
        if intent.status == "processing":
            raise PaymentProcessing
        if intent.status in EDITABLE_STATES:
            intent = client.v1.payment_intents.update(intent.id, params=details)
            return intent.client_secret
        # "canceled" (or anything unexpected): start a fresh one below.

    intent = client.v1.payment_intents.create(params={**details, "automatic_payment_methods": {"enabled": True}})
    order.stripe_payment_intent_id = intent.id
    order.save(update_fields=["stripe_payment_intent_id", "updated_at"])
    return intent.client_secret


def retrieve_intent(intent_id: str):
    return get_client().v1.payment_intents.retrieve(intent_id)


def cancel_intent(intent_id: str) -> None:
    """Best effort: cancel an unpaid PaymentIntent when the team cancels the order."""
    try:
        get_client().v1.payment_intents.cancel(intent_id)
    except (StripeError, PaymentsNotConfigured) as error:
        log.warning("Could not cancel PaymentIntent %s: %s", intent_id, error)


def construct_event(payload: bytes, signature: str):
    """Verify that a webhook really comes from Stripe and parse it."""
    return get_client().construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET)
