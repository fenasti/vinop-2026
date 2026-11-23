"""
Small template helpers available in every template (registered as a
"builtin" in settings.TEMPLATES, so no {% load %} is needed).

    {{ wine.price|money }}        → €24.90
    {% icon "cart" %}             → decorative SVG icon from the sprite
    {% icon "cart" "Your cart" %} → icon with an accessible label
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django import template
from django.conf import settings
from django.utils.html import format_html

register = template.Library()

CENT = Decimal("0.01")


@register.filter
def money(value):
    """Format a number as euros with two decimals: 1234.5 → €1,234.50."""
    if value is None or value == "":
        return ""
    try:
        amount = Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return ""
    return f"{settings.CURRENCY_SYMBOL}{amount:,.2f}"


@register.simple_tag
def icon(name, label=""):
    """Inline SVG icon from templates/includes/icon_sprite.html."""
    if label:
        return format_html('<svg class="icon" role="img" aria-label="{}"><use href="#i-{}"></use></svg>', label, name)
    return format_html('<svg class="icon" aria-hidden="true" focusable="false"><use href="#i-{}"></use></svg>', name)
