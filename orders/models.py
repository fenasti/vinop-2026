"""
Orders.

Life of an order
----------------
    PENDING ──(Stripe confirms payment)──> PAID ──> SHIPPED ──> DELIVERED
       │                                     └──> REFUNDED (refund made in Stripe)
       └──> CANCELLED

* An order is created as PENDING when the customer submits the delivery
  form, so the amount Stripe charges is always computed on the server from
  the order — never sent by the browser.
* It only becomes PAID when Stripe says so, either via the webhook or when
  the customer returns from the payment page. Both paths call
  orders.services.mark_paid(), which is idempotent: it does the work once.
* Each OrderItem stores a snapshot (name, unit price) of what was sold, so
  editing or deleting a wine later never changes or deletes past orders.
"""

import secrets

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField

from cart.pricing import ZERO, round_money, shipping_for, to_cents

from .countries import ShippingCountries

NUMBER_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"  # no 0/O, 1/I: easy to read out on the phone


def new_order_number() -> str:
    return "VO-" + "".join(secrets.choice(NUMBER_ALPHABET) for _position in range(8))


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", _("Awaiting payment")
        PAID = "paid", _("Paid – being prepared")
        SHIPPED = "shipped", _("Shipped")
        DELIVERED = "delivered", _("Delivered")
        CANCELLED = "cancelled", _("Cancelled")
        REFUNDED = "refunded", _("Refunded")

    PAID_STATUSES = (Status.PAID, Status.SHIPPED, Status.DELIVERED)

    number = models.CharField(_("order number"), max_length=12, unique=True, editable=False)
    invoice_number = models.PositiveIntegerField(
        _("invoice number"), null=True, blank=True, unique=True, editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders"
    )
    status = models.CharField(_("status"), max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True)

    # Customer & delivery
    full_name = models.CharField(_("full name"), max_length=100)
    email = models.EmailField(_("email"))
    phone = models.CharField(_("phone"), max_length=30, help_text=_("The courier may call if they can't find you."))
    street_address1 = models.CharField(_("street and number"), max_length=100)
    street_address2 = models.CharField(_("apartment, floor, c/o"), max_length=100, blank=True)
    postcode = models.CharField(_("postcode"), max_length=20)
    city = models.CharField(_("city"), max_length=60)
    region = models.CharField(_("state or province"), max_length=60, blank=True)
    country = CountryField(_("country"), countries=ShippingCountries, blank_label=_("Choose your country"))
    customer_note = models.TextField(_("note for us"), blank=True, max_length=500)

    # Legal confirmations given at checkout
    age_confirmed = models.BooleanField(_("confirmed 18 or older"), default=False)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)

    # Money (all incl. VAT)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)
    shipping_cost = models.DecimalField(max_digits=8, decimal_places=2, default=ZERO)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=ZERO)

    # Payment & fulfilment
    stripe_payment_intent_id = models.CharField(max_length=255, blank=True, default="", editable=False)
    paid_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    carrier = models.CharField(_("carrier"), max_length=40, blank=True)
    tracking_number = models.CharField(_("tracking number"), max_length=64, blank=True)
    staff_note = models.TextField(_("internal note"), blank=True, help_text=_("Only the team sees this."))
    confirmation_sent_at = models.DateTimeField(null=True, blank=True, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("order")
        verbose_name_plural = _("orders")
        constraints = [
            models.UniqueConstraint(
                fields=["stripe_payment_intent_id"],
                condition=~Q(stripe_payment_intent_id=""),
                name="order_unique_payment_intent",
            )
        ]

    def __str__(self):
        return self.number

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = new_order_number()
            while Order.objects.filter(number=self.number).exists():
                self.number = new_order_number()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("accounts:order_detail", args=[self.number])

    # ── Money ────────────────────────────────────────────────────────

    def recalculate(self) -> None:
        """Totals from the items + the shop's shipping rule. Call after changing items."""
        self.subtotal = round_money(sum((item.line_total for item in self.items.all()), ZERO))
        self.shipping_cost = shipping_for(self.subtotal)
        self.total = self.subtotal + self.shipping_cost

    @property
    def total_cents(self) -> int:
        return to_cents(self.total)

    @property
    def bottle_count(self) -> int:
        return sum(item.quantity for item in self.items.all())

    # ── State ────────────────────────────────────────────────────────

    @property
    def is_paid(self) -> bool:
        return self.status in self.PAID_STATUSES

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING

    @property
    def can_ship(self) -> bool:
        return self.status == self.Status.PAID

    @property
    def can_cancel(self) -> bool:
        return self.status in (self.Status.PENDING, self.Status.PAID)

    @property
    def address_lines(self) -> list[str]:
        lines = [
            self.full_name,
            self.street_address1,
            self.street_address2,
            f"{self.postcode} {self.city}",
            self.region,
            self.country.name,
        ]
        return [line for line in lines if line.strip()]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    # SET_NULL: deleting a wine must never delete sales history.
    wine = models.ForeignKey(
        "catalog.Wine", on_delete=models.SET_NULL, null=True, blank=True, related_name="order_items"
    )
    wine_name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return f"{self.quantity} × {self.wine_name}"

    def save(self, *args, **kwargs):
        self.line_total = round_money(self.unit_price * self.quantity)
        super().save(*args, **kwargs)


class InvoiceSequence(models.Model):
    """
    A single counter row for gap-free, sequential invoice numbers
    (German invoices need unique, consecutive numbers). The row is locked
    while a number is taken, so two payments at once can't get the same one.
    """

    last_number = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Last invoice number: {self.last_number}"

    @classmethod
    def next_number(cls) -> int:
        # Must run inside transaction.atomic().
        cls.objects.get_or_create(pk=1)
        sequence = cls.objects.select_for_update().get(pk=1)
        sequence.last_number += 1
        sequence.save(update_fields=["last_number"])
        return sequence.last_number
