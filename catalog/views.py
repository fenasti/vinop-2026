from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from orders.models import Order, OrderItem
from reviews.models import Review
from team.permissions import Area, can
from wishlist.models import WishlistItem

from .forms import WineFilterForm
from .models import Region, Wine


def wine_list(request):
    """All visible wines with search, filters, sorting and pagination."""
    form = WineFilterForm(request.GET or None)
    if form.is_bound:
        form.is_valid()  # keeps the valid fields; an unknown region just gets ignored
    wines = form.apply(Wine.objects.visible().for_listing().with_ratings())

    page = Paginator(wines, settings.WINES_PER_PAGE).get_page(request.GET.get("page"))

    context = {
        "form": form,
        "page": page,
        "wines": page.object_list,
        "regions": Region.objects.all(),
        "selected_region": form.cleaned_data.get("region") if form.is_bound else None,
    }
    return render(request, "catalog/wine_list.html", context)


def wine_detail(request, slug):
    # The team can preview wines that are hidden from customers.
    wines = Wine.objects.all() if can(request.user, Area.CATALOG) else Wine.objects.visible()
    wine = get_object_or_404(wines.for_listing().with_ratings(), slug=slug)

    reviews = wine.reviews.filter(is_published=True).select_related("user")
    buyer_ids = set(
        OrderItem.objects.filter(wine=wine, order__status__in=Order.PAID_STATUSES).values_list(
            "order__user_id", flat=True
        )
    )

    user_review = None
    in_wishlist = False
    if request.user.is_authenticated:
        user_review = Review.objects.filter(wine=wine, user=request.user).first()
        in_wishlist = WishlistItem.objects.filter(wine=wine, user=request.user).exists()

    related = Wine.objects.visible().in_stock().for_listing().filter(region=wine.region).exclude(pk=wine.pk)[:4]

    context = {
        "wine": wine,
        "reviews": reviews,
        "buyer_ids": buyer_ids,
        "user_review": user_review,
        "in_wishlist": in_wishlist,
        "related": related,
    }
    return render(request, "catalog/wine_detail.html", context)
