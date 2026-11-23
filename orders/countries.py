from django.conf import settings
from django_countries import Countries


class ShippingCountries(Countries):
    """Only the countries we deliver to (settings.SHIPPING_COUNTRIES)."""

    only = settings.SHIPPING_COUNTRIES
