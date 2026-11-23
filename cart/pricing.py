"""
Money rules in one place, shared by the cart and by orders so the price a
customer sees is exactly the price Stripe charges.

All prices include VAT (B2C prices in the EU must be shown VAT-inclusive).
"""

from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def round_money(amount: Decimal) -> Decimal:
    return Decimal(amount).quantize(CENT, rounding=ROUND_HALF_UP)


def shipping_for(subtotal: Decimal) -> Decimal:
    """Flat rate, free from FREE_SHIPPING_THRESHOLD, nothing for an empty cart."""
    if subtotal <= ZERO:
        return ZERO
    if subtotal >= settings.FREE_SHIPPING_THRESHOLD:
        return ZERO
    return round_money(settings.SHIPPING_FLAT_RATE)


def free_shipping_gap(subtotal: Decimal) -> Decimal:
    """How much more the customer needs to add for free shipping (0 if reached)."""
    return max(ZERO, round_money(settings.FREE_SHIPPING_THRESHOLD - subtotal))


def to_cents(amount: Decimal) -> int:
    """Stripe wants integer cents: €24.90 → 2490."""
    return int((round_money(amount) * 100).to_integral_value())
