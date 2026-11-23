from django import forms
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

from .models import Grape, Region, Wine, Winery


class WineFilterForm(forms.Form):
    """The search & filter bar on /wines/. Every field is optional."""

    SORT_CHOICES = [
        ("", _("Recommended")),
        ("price", _("Price: low to high")),
        ("-price", _("Price: high to low")),
        ("newest", _("Newest arrivals")),
        ("rating", _("Best rated")),
        ("north", _("Region: north to south")),
    ]

    q = forms.CharField(
        label=_("Search"),
        required=False,
        max_length=80,
        widget=forms.SearchInput(attrs={"placeholder": _("Wine, winery or grape")}),
    )
    style = forms.ChoiceField(label=_("Style"), required=False, choices=[("", _("All styles")), *Wine.Style.choices])
    region = forms.ModelChoiceField(
        label=_("Region"),
        required=False,
        queryset=Region.objects.all(),
        to_field_name="slug",
        empty_label=_("All regions"),
    )
    grape = forms.ModelChoiceField(
        label=_("Grape"),
        required=False,
        queryset=Grape.objects.all(),
        to_field_name="slug",
        empty_label=_("All grapes"),
    )
    max_price = forms.DecimalField(
        label=_("Max. price (€)"),
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "1", "inputmode": "decimal"}),
    )
    in_stock = forms.BooleanField(label=_("Only wines in stock"), required=False)
    sort = forms.ChoiceField(label=_("Sort by"), required=False, choices=SORT_CHOICES)

    def apply(self, wines):
        """Filter a Wine queryset with whatever fields were valid."""
        data = self.cleaned_data if self.is_bound else {}
        if query := data.get("q", "").strip():
            # The grape match is a subquery so a wine with two matching
            # grapes isn't counted twice in the rating annotations.
            by_grape = Wine.objects.filter(grapes__name__icontains=query).values("pk")
            wines = wines.filter(
                Q(name__icontains=query)
                | Q(winery__name__icontains=query)
                | Q(region__name__icontains=query)
                | Q(pk__in=by_grape)
            )
        if style := data.get("style"):
            wines = wines.filter(style=style)
        if region := data.get("region"):
            wines = wines.filter(region=region)
        if grape := data.get("grape"):
            wines = wines.filter(grapes=grape)
        if (max_price := data.get("max_price")) is not None:
            wines = wines.filter(price__lte=max_price)
        if data.get("in_stock"):
            wines = wines.filter(stock__gt=0)

        match data.get("sort"):
            case "price":
                wines = wines.order_by("price")
            case "-price":
                wines = wines.order_by("-price")
            case "newest":
                wines = wines.order_by("-created_at")
            case "rating":
                wines = wines.order_by(F("rating_avg").desc(nulls_last=True), "-rating_count")
            case "north":
                wines = wines.order_by("region__latitude", "winery__name")
            case _:
                wines = wines.order_by("-is_featured", "-created_at")
        return wines

    @property
    def active_count(self) -> int:
        """How many filters are switched on (shown on the mobile 'Filters' button)."""
        if not self.is_bound or not hasattr(self, "cleaned_data"):
            return 0
        keys = ("q", "style", "region", "grape", "max_price", "in_stock")
        return sum(1 for key in keys if self.cleaned_data.get(key) not in (None, "", False))


# ── Team area forms ─────────────────────────────────────────────────────


class WineForm(forms.ModelForm):
    class Meta:
        model = Wine
        fields = [
            "winery",
            "name",
            "vintage",
            "style",
            "region",
            "grapes",
            "price",
            "compare_at_price",
            "stock",
            "is_active",
            "is_featured",
            "alcohol",
            "volume_ml",
            "serving_temperature",
            "description",
            "tasting_notes",
            "food_pairing",
            "image",
        ]
        widgets = {
            "grapes": forms.CheckboxSelectMultiple,
            "description": forms.Textarea(attrs={"rows": 4}),
            "tasting_notes": forms.Textarea(attrs={"rows": 3}),
        }


class WineryForm(forms.ModelForm):
    class Meta:
        model = Winery
        fields = ["name", "region", "website", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}


class RegionForm(forms.ModelForm):
    class Meta:
        model = Region
        fields = ["name", "latitude", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class GrapeForm(forms.ModelForm):
    class Meta:
        model = Grape
        fields = ["name"]


class StockForm(forms.Form):
    """Quick 'set bottles in stock' field on the team wine list."""

    stock = forms.IntegerField(min_value=0, max_value=100_000, label=_("Bottles in stock"))
