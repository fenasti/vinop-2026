from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from catalog.models import Wine

from .forms import ReviewForm
from .models import Review


@login_required
def write(request, slug):
    """Write a review, or edit yours if you already wrote one for this wine."""
    wine = get_object_or_404(Wine.objects.visible().select_related("winery"), slug=slug)
    review = Review.objects.filter(wine=wine, user=request.user).first()
    form = ReviewForm(request.POST or None, instance=review)

    if request.method == "POST":
        if form.is_valid():
            saved = form.save(commit=False)
            saved.wine, saved.user = wine, request.user
            saved.save()
            messages.success(
                request, _("Thanks! Your review is updated.") if review else _("Thanks! Your review is live.")
            )
            return redirect(f"{wine.get_absolute_url()}#reviews")
        messages.error(request, _("Please check the highlighted fields."))

    return render(request, "reviews/review_form.html", {"form": form, "wine": wine, "review": review})


@login_required
def delete(request, pk):
    review = get_object_or_404(Review.objects.select_related("wine__winery"), pk=pk, user=request.user)
    if request.method == "POST":
        wine = review.wine
        review.delete()
        messages.success(request, _("Your review of %(wine)s is deleted.") % {"wine": wine})
        return redirect(f"{wine.get_absolute_url()}#reviews")
    return render(request, "reviews/review_confirm_delete.html", {"review": review})
