"""Team area: wines, wineries, regions and grapes (the Cellar Keeper's work)."""

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_POST

from catalog.forms import GrapeForm, RegionForm, StockForm, WineForm, WineryForm
from catalog.models import Grape, Region, Wine, Winery
from core.utils import redirect_back

from ..mixins import TeamCreateView, TeamDeleteView, TeamUpdateView, team_required
from ..permissions import Area

# ── Wines ────────────────────────────────────────────────────────────────


@team_required(Area.CATALOG)
def wine_list(request):
    wines = Wine.objects.select_related("winery", "region").order_by("winery__name", "name")
    query = request.GET.get("q", "").strip()
    show = request.GET.get("show", "all")

    if query:
        wines = wines.filter(Q(name__icontains=query) | Q(winery__name__icontains=query))
    if show == "visible":
        wines = wines.filter(is_active=True)
    elif show == "hidden":
        wines = wines.filter(is_active=False)
    elif show == "low":
        wines = wines.filter(stock__lte=settings.LOW_STOCK_THRESHOLD).order_by("stock")

    page = Paginator(wines, 25).get_page(request.GET.get("page"))
    tabs = [("all", _("All")), ("visible", _("Visible")), ("hidden", _("Hidden")), ("low", _("Low stock"))]
    return render(request, "team/wine_list.html", {"page": page, "query": query, "show": show, "tabs": tabs})


class WineCreateView(TeamCreateView):
    area = Area.CATALOG
    model = Wine
    form_class = WineForm
    list_url_name = "team:wines"


class WineUpdateView(TeamUpdateView):
    area = Area.CATALOG
    model = Wine
    form_class = WineForm
    list_url_name = "team:wines"


class WineDeleteView(TeamDeleteView):
    area = Area.CATALOG
    model = Wine
    list_url_name = "team:wines"
    consequence = gettext_lazy(
        "Past orders keep their record of this wine (its name and price are stored on each order). "
        "Its reviews and wishlist entries are removed. To take it off the shop for now, hide it instead."
    )


@team_required(Area.CATALOG)
@require_POST
def wine_toggle(request, pk):
    wine = get_object_or_404(Wine.objects.select_related("winery"), pk=pk)
    wine.is_active = not wine.is_active
    wine.save(update_fields=["is_active", "updated_at"])
    if wine.is_active:
        messages.success(request, _("“%(wine)s” is visible in the shop again.") % {"wine": wine})
    else:
        messages.success(request, _("“%(wine)s” is hidden from the shop.") % {"wine": wine})
    return redirect_back(request, "team:wines")


@team_required(Area.CATALOG)
@require_POST
def wine_stock(request, pk):
    wine = get_object_or_404(Wine.objects.select_related("winery"), pk=pk)
    form = StockForm(request.POST)
    if form.is_valid():
        wine.stock = form.cleaned_data["stock"]
        wine.save(update_fields=["stock", "updated_at"])
        messages.success(
            request, _("“%(wine)s” now has %(stock)d bottles in stock.") % {"wine": wine, "stock": wine.stock}
        )
    else:
        messages.error(request, _("Stock must be a whole number of bottles, 0 or more."))
    return redirect_back(request, "team:wines")


# ── Wineries ─────────────────────────────────────────────────────────────


@team_required(Area.CATALOG)
def winery_list(request):
    wineries = Winery.objects.select_related("region").annotate(wine_count=Count("wines")).order_by("name")
    return render(request, "team/winery_list.html", {"wineries": wineries})


class WineryCreateView(TeamCreateView):
    area = Area.CATALOG
    model = Winery
    form_class = WineryForm
    list_url_name = "team:wineries"


class WineryUpdateView(TeamUpdateView):
    area = Area.CATALOG
    model = Winery
    form_class = WineryForm
    list_url_name = "team:wineries"


class WineryDeleteView(TeamDeleteView):
    area = Area.CATALOG
    model = Winery
    list_url_name = "team:wineries"
    consequence = gettext_lazy("A winery that still has wines can't be deleted. Delete or move its wines first.")


# ── Regions ──────────────────────────────────────────────────────────────


@team_required(Area.CATALOG)
def region_list(request):
    regions = Region.objects.annotate(
        wine_count=Count("wines", distinct=True),
        winery_count=Count("wineries", distinct=True),
    ).order_by("latitude")
    return render(request, "team/region_list.html", {"regions": regions})


class RegionCreateView(TeamCreateView):
    area = Area.CATALOG
    model = Region
    form_class = RegionForm
    list_url_name = "team:regions"


class RegionUpdateView(TeamUpdateView):
    area = Area.CATALOG
    model = Region
    form_class = RegionForm
    list_url_name = "team:regions"


class RegionDeleteView(TeamDeleteView):
    area = Area.CATALOG
    model = Region
    list_url_name = "team:regions"
    consequence = gettext_lazy(
        "A region that still has wineries or wines can't be deleted. Move them to another region first."
    )


# ── Grapes ───────────────────────────────────────────────────────────────


@team_required(Area.CATALOG)
def grape_list(request):
    grapes = Grape.objects.annotate(wine_count=Count("wines")).order_by("name")
    return render(request, "team/grape_list.html", {"grapes": grapes})


class GrapeCreateView(TeamCreateView):
    area = Area.CATALOG
    model = Grape
    form_class = GrapeForm
    list_url_name = "team:grapes"


class GrapeUpdateView(TeamUpdateView):
    area = Area.CATALOG
    model = Grape
    form_class = GrapeForm
    list_url_name = "team:grapes"


class GrapeDeleteView(TeamDeleteView):
    area = Area.CATALOG
    model = Grape
    list_url_name = "team:grapes"
    consequence = gettext_lazy("The grape is removed from every wine that lists it. The wines themselves stay.")
