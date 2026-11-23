from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from catalog.models import Wine
from newsletter.models import Subscriber
from orders.models import Order
from reviews.models import Review

from ..permissions import Area, areas_for, roles_of


@login_required
def hub(request):
    """The team's start page: one card per area the person may open, with what needs attention."""
    areas = areas_for(request.user)
    if not areas:
        raise PermissionDenied(_("This page is for the VinOp team."))

    now = timezone.now()
    cards, attention = [], {}

    if Area.ORDERS in areas:
        to_ship = Order.objects.filter(status=Order.Status.PAID).count()
        paid_30d = Order.objects.filter(status__in=Order.PAID_STATUSES, paid_at__gte=now - timedelta(days=30))
        attention["revenue_30d"] = paid_30d.aggregate(total=Sum("total"))["total"] or 0
        attention["orders_30d"] = paid_30d.count()
        cards.append(
            {
                "title": _("Orders & shipping"),
                "icon": "package",
                "url": reverse("team:orders"),
                "text": _("Paid orders, packing list, mark as shipped."),
                "badge": _("%(count)d to ship") % {"count": to_ship} if to_ship else "",
            }
        )

    if Area.CATALOG in areas:
        low = (
            Wine.objects.visible()
            .filter(stock__lte=settings.LOW_STOCK_THRESHOLD)
            .select_related("winery")
            .order_by("stock")
        )
        attention["low_stock"] = low[:6]
        cards += [
            {
                "title": _("Wines"),
                "icon": "wine",
                "url": reverse("team:wines"),
                "text": _("Add, edit, hide or restock wines."),
                "badge": _("%(count)d running low") % {"count": low.count()} if low.exists() else "",
            },
            {
                "title": _("Wineries"),
                "icon": "home",
                "url": reverse("team:wineries"),
                "text": _("The producers we import from."),
            },
            {
                "title": _("Regions"),
                "icon": "map-pin",
                "url": reverse("team:regions"),
                "text": _("Chile's valleys, north to south."),
            },
            {
                "title": _("Grapes"),
                "icon": "grape",
                "url": reverse("team:grapes"),
                "text": _("Varieties used for filtering."),
            },
        ]

    if Area.REVIEWS in areas:
        new = Review.objects.filter(created_at__gte=now - timedelta(days=7)).count()
        cards.append(
            {
                "title": _("Reviews"),
                "icon": "star",
                "url": reverse("team:reviews"),
                "text": _("Read, hide or remove customer reviews."),
                "badge": _("%(count)d this week") % {"count": new} if new else "",
            }
        )

    if Area.NEWSLETTER in areas:
        cards.append(
            {
                "title": _("Newsletter"),
                "icon": "mail",
                "url": reverse("team:subscribers"),
                "text": _("Confirmed subscribers and CSV export."),
                "badge": _("%(count)d confirmed") % {"count": Subscriber.objects.confirmed().count()},
            }
        )

    if Area.STUDIO in areas:
        cards.append(
            {
                "title": _("Studio"),
                "icon": "palette",
                "url": reverse("team:studio"),
                "text": _("Homepage, colours, fonts, logo and footer."),
            }
        )
    if Area.PAGES in areas:
        cards.append(
            {
                "title": _("Legal pages"),
                "icon": "file-text",
                "url": reverse("team:pages"),
                "text": _("Imprint, privacy, terms, withdrawal, shipping."),
            }
        )
    if Area.MEMBERS in areas:
        cards.append(
            {
                "title": _("Team & roles"),
                "icon": "users",
                "url": reverse("team:members"),
                "text": _("Who can open which part of this area."),
            }
        )

    context = {"cards": cards, "attention": attention, "roles": roles_of(request.user)}
    return render(request, "team/hub.html", context)
