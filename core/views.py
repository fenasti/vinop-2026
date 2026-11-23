from django.conf import settings
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from catalog.models import Region, Wine

from .models import LegalPage


def _regions_north_to_south():
    """
    Valleys that have wines, each with `gap`: degrees of latitude from the
    previous valley. The homepage ribbon spaces them by that gap, so the
    list looks like the real length of Chile.
    """
    regions = list(
        Region.objects.annotate(wine_count=Count("wines", filter=Q(wines__is_active=True)))
        .filter(wine_count__gt=0)
        .order_by("latitude")  # needed: Django skips Meta.ordering on annotated queries
    )
    previous = None
    for region in regions:
        region.gap = (region.latitude - previous) if previous is not None else 0
        previous = region.latitude
    return regions


def home(request):
    wines = Wine.objects.visible().in_stock().for_listing()
    featured = list(wines.filter(is_featured=True)[:8]) or list(wines.order_by("-created_at")[:8])
    context = {
        "featured": featured,
        "regions": _regions_north_to_south(),
        "country_count": len(settings.SHIPPING_COUNTRIES),
    }
    return render(request, "core/home.html", context)


def legal_page(request, slug):
    page = get_object_or_404(LegalPage, slug=slug)
    return render(request, "core/legal_page.html", {"page": page})
