"""
The wine catalogue.

    Region  ──<  Winery  ──<  Wine  >──<  Grape
       └──────────────────────<┘

Regions are Chile's wine valleys, stored with their latitude so the shop
can always list them in true north-to-south order (Elqui first, Malleco
last) and draw the latitude ribbon on the homepage.

Deleting is protected: a region or winery that still has wines can't be
deleted by accident (the team area explains what to do instead), and a
wine that appears in past orders keeps that history (see orders.OrderItem).
"""

from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Avg, Count, Q
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


def unique_slug(instance, value: str, max_length: int = 80) -> str:
    """slugify(value), adding -2, -3 … until no other row uses it."""
    base = slugify(value)[:max_length] or "item"
    slug, counter = base, 2
    model = type(instance)
    while model.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        suffix = f"-{counter}"
        slug = f"{base[: max_length - len(suffix)]}{suffix}"
        counter += 1
    return slug


class Region(models.Model):
    name = models.CharField(_("name"), max_length=60, unique=True)
    slug = models.SlugField(_("address"), max_length=80, unique=True, blank=True)
    latitude = models.DecimalField(
        _("latitude (° south)"),
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(Decimal("17.0")), MaxValueValidator(Decimal("56.0"))],
        help_text=_("Degrees south of the equator, e.g. 33.7 for Maipo. Sets the north-to-south order."),
    )
    description = models.TextField(_("description"), blank=True)

    class Meta:
        ordering = ["latitude"]
        verbose_name = _("region")
        verbose_name_plural = _("regions")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"{reverse('catalog:list')}?region={self.slug}"

    @property
    def latitude_label(self) -> str:
        return f"{self.latitude}° S"


class Grape(models.Model):
    name = models.CharField(_("name"), max_length=60, unique=True)
    slug = models.SlugField(_("address"), max_length=80, unique=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("grape")
        verbose_name_plural = _("grapes")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name)
        super().save(*args, **kwargs)


class Winery(models.Model):
    name = models.CharField(_("name"), max_length=100, unique=True)
    slug = models.SlugField(_("address"), max_length=120, unique=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="wineries", verbose_name=_("region"))
    description = models.TextField(_("about the winery"), blank=True)
    website = models.URLField(_("website"), blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("winery")
        verbose_name_plural = _("wineries")

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, self.name, max_length=120)
        super().save(*args, **kwargs)


class WineQuerySet(models.QuerySet):
    def visible(self):
        """Wines customers may see: switched on in the team area."""
        return self.filter(is_active=True)

    def in_stock(self):
        return self.filter(stock__gt=0)

    def with_ratings(self):
        published = Q(reviews__is_published=True)
        return self.annotate(
            rating_avg=Avg("reviews__rating", filter=published),
            rating_count=Count("reviews", filter=published),
        )

    def for_listing(self):
        return self.select_related("winery", "region").prefetch_related("grapes")


class Wine(models.Model):
    class Style(models.TextChoices):
        RED = "red", _("Red")
        WHITE = "white", _("White")
        ROSE = "rose", _("Rosé")
        SPARKLING = "sparkling", _("Sparkling")
        SWEET = "sweet", _("Sweet")
        ORANGE = "orange", _("Orange")

    winery = models.ForeignKey(Winery, on_delete=models.PROTECT, related_name="wines", verbose_name=_("winery"))
    name = models.CharField(
        _("name"), max_length=120, help_text=_("Without the winery, e.g. 'Gran Reserva Carménère'.")
    )
    slug = models.SlugField(_("address"), max_length=160, unique=True, blank=True)
    style = models.CharField(_("style"), max_length=12, choices=Style.choices, default=Style.RED)
    vintage = models.PositiveSmallIntegerField(
        _("vintage"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1900), MaxValueValidator(2100)],
        help_text=_("Leave empty for a non-vintage (NV) wine."),
    )
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="wines", verbose_name=_("region"))
    grapes = models.ManyToManyField(Grape, related_name="wines", blank=True, verbose_name=_("grapes"))

    description = models.TextField(_("description"), blank=True)
    tasting_notes = models.TextField(_("tasting notes"), blank=True)
    food_pairing = models.CharField(_("food pairing"), max_length=200, blank=True)
    serving_temperature = models.CharField(
        _("serving temperature"), max_length=20, blank=True, help_text=_("e.g. 16–18 °C")
    )
    alcohol = models.DecimalField(
        _("alcohol % vol"),
        max_digits=3,
        decimal_places=1,
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("25"))],
    )
    volume_ml = models.PositiveSmallIntegerField(_("bottle size (ml)"), default=750)

    price = models.DecimalField(
        _("price (€, incl. VAT)"), max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.50"))]
    )
    compare_at_price = models.DecimalField(
        _("previous price (€)"),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Optional. Fill in to show the wine as reduced."),
    )
    stock = models.PositiveIntegerField(_("bottles in stock"), default=0)
    is_active = models.BooleanField(_("visible in the shop"), default=True)
    is_featured = models.BooleanField(_("feature on the homepage"), default=False)
    image = models.ImageField(_("bottle photo"), upload_to="wines/", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = WineQuerySet.as_manager()

    class Meta:
        ordering = ["winery__name", "name", "-vintage"]
        verbose_name = _("wine")
        verbose_name_plural = _("wines")
        indexes = [models.Index(fields=["is_active", "style"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(compare_at_price__isnull=True) | Q(compare_at_price__gt=models.F("price")),
                name="wine_compare_price_above_price",
                violation_error_message=_("The previous price must be higher than the current price."),
            )
        ]

    def __str__(self):
        return self.full_name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slug(self, f"{self.winery.name} {self.name} {self.vintage or 'nv'}", max_length=160)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("catalog:detail", args=[self.slug])

    # ── Display helpers ──────────────────────────────────────────────

    @property
    def vintage_label(self) -> str:
        return str(self.vintage) if self.vintage else "NV"

    @property
    def full_name(self) -> str:
        return f"{self.winery.name} {self.name} {self.vintage_label}"

    @property
    def price_per_litre(self) -> Decimal:
        """Unit price per litre, which German price law (PAngV) requires us to show."""
        return (self.price * Decimal(1000) / Decimal(self.volume_ml)).quantize(Decimal("0.01"))

    @property
    def is_in_stock(self) -> bool:
        return self.stock > 0

    @property
    def is_low_stock(self) -> bool:
        return 0 < self.stock <= settings.LOW_STOCK_THRESHOLD

    @property
    def is_reduced(self) -> bool:
        return bool(self.compare_at_price and self.compare_at_price > self.price)

    @property
    def can_be_bought(self) -> bool:
        return self.is_active and self.is_in_stock

    @property
    def max_orderable(self) -> int:
        return min(self.stock, settings.MAX_BOTTLES_PER_WINE)
