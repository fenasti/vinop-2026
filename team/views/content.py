"""Team area: reviews, newsletter subscribers, legal pages and the Studio."""

import csv

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.decorators.http import require_POST

from core.models import LegalPage
from core.utils import redirect_back
from newsletter.models import Subscriber
from reviews.models import Review
from studio.forms import SiteSettingsForm
from studio.models import SiteSettings

from ..forms import LegalPageForm
from ..mixins import TeamCreateView, TeamDeleteView, TeamUpdateView, team_required
from ..permissions import Area

# ── Reviews ──────────────────────────────────────────────────────────────


@team_required(Area.REVIEWS)
def review_list(request):
    show = request.GET.get("show", "all")
    reviews = Review.objects.select_related("user", "wine__winery")
    if show == "published":
        reviews = reviews.filter(is_published=True)
    elif show == "hidden":
        reviews = reviews.filter(is_published=False)
    elif show == "low":
        reviews = reviews.filter(rating__lte=2)
    tabs = [("all", _("All")), ("published", _("Published")), ("hidden", _("Hidden")), ("low", _("1–2 stars"))]
    page = Paginator(reviews, 30).get_page(request.GET.get("page"))
    return render(request, "team/review_list.html", {"page": page, "show": show, "tabs": tabs})


@team_required(Area.REVIEWS)
@require_POST
def review_toggle(request, pk):
    review = get_object_or_404(Review, pk=pk)
    review.is_published = not review.is_published
    review.save(update_fields=["is_published", "updated_at"])
    messages.success(request, _("The review is published.") if review.is_published else _("The review is hidden."))
    return redirect_back(request, "team:reviews")


class ReviewDeleteView(TeamDeleteView):
    area = Area.REVIEWS
    model = Review
    list_url_name = "team:reviews"
    consequence = gettext_lazy(
        "The customer can write a new review afterwards. To keep it but not show it, hide it instead."
    )


# ── Newsletter ───────────────────────────────────────────────────────────


@team_required(Area.NEWSLETTER)
def subscriber_list(request):
    show = request.GET.get("show", "confirmed")
    subscribers = Subscriber.objects.all()
    if show == "confirmed":
        subscribers = subscribers.confirmed()
    elif show == "unconfirmed":
        subscribers = subscribers.filter(confirmed_at=None)
    tabs = [("confirmed", _("Confirmed")), ("unconfirmed", _("Not confirmed yet")), ("all", _("All"))]
    page = Paginator(subscribers, 50).get_page(request.GET.get("page"))
    return render(request, "team/subscriber_list.html", {"page": page, "show": show, "tabs": tabs})


@team_required(Area.NEWSLETTER)
def subscriber_export(request):
    """Confirmed addresses only: unconfirmed ones may not be emailed (double opt-in)."""
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="vinop-subscribers-{timezone.localdate():%Y-%m-%d}.csv"'
    writer = csv.writer(response)
    writer.writerow(["email", "confirmed", "unsubscribe link"])
    for subscriber in Subscriber.objects.confirmed():
        writer.writerow(
            [
                subscriber.email,
                timezone.localtime(subscriber.confirmed_at).strftime("%Y-%m-%d"),
                request.build_absolute_uri(subscriber.get_unsubscribe_url()),
            ]
        )
    return response


class SubscriberDeleteView(TeamDeleteView):
    area = Area.NEWSLETTER
    model = Subscriber
    list_url_name = "team:subscribers"
    consequence = gettext_lazy("Use this when someone asks to be removed. The address is deleted for good.")


# ── Legal pages ──────────────────────────────────────────────────────────


@team_required(Area.PAGES)
def page_list(request):
    return render(request, "team/page_list.html", {"pages": LegalPage.objects.all()})


class PageCreateView(TeamCreateView):
    area = Area.PAGES
    model = LegalPage
    form_class = LegalPageForm
    list_url_name = "team:pages"


class PageUpdateView(TeamUpdateView):
    area = Area.PAGES
    model = LegalPage
    form_class = LegalPageForm
    list_url_name = "team:pages"


class PageDeleteView(TeamDeleteView):
    area = Area.PAGES
    model = LegalPage
    list_url_name = "team:pages"
    consequence = gettext_lazy(
        "Links to it stop working. The imprint, privacy, terms and withdrawal pages are legally required: "
        "edit them rather than deleting them."
    )


# ── Studio ───────────────────────────────────────────────────────────────


@team_required(Area.STUDIO)
def studio(request):
    """How the shop looks: homepage, colours, fonts, logo, footer. Changes are live on save."""
    site = SiteSettings.load()
    form = SiteSettingsForm(request.POST or None, request.FILES or None, instance=site)
    if request.method == "POST":
        if form.is_valid():
            site = form.save()
            messages.success(request, _("Saved. Your changes are live in the shop."))
            for warning in site.readability_warnings():
                messages.warning(request, _("%(what)s may be hard to read. Try more contrast.") % {"what": warning})
            return redirect("team:studio")
        messages.error(request, _("Please check the highlighted fields."))
    return render(request, "team/studio.html", {"form": form, "site_preview": site})
