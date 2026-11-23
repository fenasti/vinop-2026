from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import ngettext
from django.views.decorators.http import require_POST

from catalog.models import Wine
from core.utils import redirect_back

from .cart import Cart


def _quantity_from(request, default: int = 1) -> int | None:
    try:
        return int(request.POST.get("quantity", default))
    except (TypeError, ValueError):
        return None


def cart_detail(request):
    cart = Cart(request)
    for line in cart.fix_stock_problems():
        if line.wine.stock:
            messages.warning(
                request,
                ngettext(
                    "Only %(count)d bottle of %(wine)s is left, so we updated your cart.",
                    "Only %(count)d bottles of %(wine)s are left, so we updated your cart.",
                    line.wine.stock,
                )
                % {"count": line.wine.stock, "wine": line.wine},
            )
        else:
            messages.warning(request, _("%(wine)s just sold out and was removed from your cart.") % {"wine": line.wine})
    return render(request, "cart/cart_detail.html", {"cart": cart})


@require_POST
def add(request, wine_id):
    wine = get_object_or_404(Wine.objects.visible().select_related("winery"), pk=wine_id)
    cart = Cart(request)
    quantity = _quantity_from(request)

    if quantity is None or quantity < 1:
        messages.error(request, _("Please choose at least one bottle."))
        return redirect_back(request, wine.get_absolute_url())
    if not wine.is_in_stock:
        messages.error(request, _("Sorry, %(wine)s is sold out.") % {"wine": wine})
        return redirect_back(request, wine.get_absolute_url())

    wanted = cart.quantity_of(wine) + quantity
    kept = cart.add(wine, quantity)
    if kept < wanted:
        messages.warning(
            request,
            _("You can order up to %(max)d bottles of %(wine)s, so your cart now has %(max)d.")
            % {"max": kept, "wine": wine},
        )
    else:
        messages.success(
            request,
            ngettext(
                "Added %(count)d bottle of %(wine)s to your cart.",
                "Added %(count)d bottles of %(wine)s to your cart.",
                quantity,
            )
            % {"count": quantity, "wine": wine},
        )
    return redirect_back(request, "cart:detail")


@require_POST
def update(request, wine_id):
    wine = get_object_or_404(Wine.objects.select_related("winery"), pk=wine_id)
    cart = Cart(request)
    quantity = _quantity_from(request, default=cart.quantity_of(wine))

    if quantity is None or quantity < 0:
        messages.error(request, _("Please enter a whole number of bottles."))
        return redirect("cart:detail")

    kept = cart.set(wine, quantity)
    if kept == 0:
        messages.success(request, _("Removed %(wine)s from your cart.") % {"wine": wine})
    elif kept < quantity:
        messages.warning(
            request,
            _("You can order up to %(max)d bottles of %(wine)s, so we set it to %(max)d.")
            % {"max": kept, "wine": wine},
        )
    else:
        messages.success(
            request,
            ngettext(
                "%(wine)s: %(count)d bottle in your cart.",
                "%(wine)s: %(count)d bottles in your cart.",
                kept,
            )
            % {"count": kept, "wine": wine},
        )
    return redirect("cart:detail")


@require_POST
def remove(request, wine_id):
    wine = get_object_or_404(Wine.objects.select_related("winery"), pk=wine_id)
    Cart(request).remove(wine)
    messages.success(request, _("Removed %(wine)s from your cart.") % {"wine": wine})
    return redirect("cart:detail")
