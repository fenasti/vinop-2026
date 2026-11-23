from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField

from orders.countries import ShippingCountries

ADDRESS_FIELDS = ("full_name", "phone", "street_address1", "street_address2", "postcode", "city", "region", "country")


class Profile(models.Model):
    """
    A customer's saved delivery address, prefilled at checkout.

    Created automatically for every new user (see accounts/signals.py).
    Always fetch it with Profile.for_user(user): that also creates it for
    accounts that existed before — the first VinOp crashed on those.
    """

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(_("full name"), max_length=100, blank=True)
    phone = models.CharField(_("phone"), max_length=30, blank=True)
    street_address1 = models.CharField(_("street and number"), max_length=100, blank=True)
    street_address2 = models.CharField(_("apartment, floor, c/o"), max_length=100, blank=True)
    postcode = models.CharField(_("postcode"), max_length=20, blank=True)
    city = models.CharField(_("city"), max_length=60, blank=True)
    region = models.CharField(_("state or province"), max_length=60, blank=True)
    country = CountryField(_("country"), countries=ShippingCountries, blank_label=_("Choose your country"), blank=True)

    class Meta:
        verbose_name = _("profile")
        verbose_name_plural = _("profiles")

    def __str__(self):
        return f"Profile of {self.user}"

    @classmethod
    def for_user(cls, user) -> "Profile":
        profile, _created = cls.objects.get_or_create(user=user)
        return profile

    @property
    def has_address(self) -> bool:
        return bool(self.street_address1 and self.city and self.country)

    def address_as_initial(self) -> dict:
        return {field: getattr(self, field) for field in ADDRESS_FIELDS if getattr(self, field)}

    def copy_address_from(self, order) -> None:
        for field in ADDRESS_FIELDS:
            setattr(self, field, getattr(order, field))
        self.save()
