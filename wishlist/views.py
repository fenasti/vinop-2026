from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from catalog.models import Wine
from core.utils import redirect_back

from .models import WishlistItem


@login_required
def wishlist(request):
    items = WishlistItem.objects.filter(user=request.user).select_related("wine__winery", "wine__region")
    return render(request, "wishlist/wishlist.html", {"items": items})


@login_required
@require_POST
def toggle(request, wine_id):
    """Save or un-save a wine (one button, used on the wine page and the wishlist)."""
    wine = get_object_or_404(Wine, pk=wine_id)
    item, created = WishlistItem.objects.get_or_create(user=request.user, wine=wine)
    if created:
        messages.success(request, _("Saved %(wine)s to your wishlist.") % {"wine": wine})
    else:
        item.delete()
        messages.success(request, _("Removed %(wine)s from your wishlist.") % {"wine": wine})
    return redirect_back(request, "wishlist:list")
