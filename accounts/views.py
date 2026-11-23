from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from orders.models import Order
from wishlist.models import WishlistItem

from .forms import AddressForm, DeleteAccountForm
from .models import Profile


def _orders_of(user):
    # Orders that never got past the payment page aren't real orders yet.
    return Order.objects.filter(user=user).exclude(status=Order.Status.PENDING).prefetch_related("items")


@login_required
def overview(request):
    context = {
        "profile": Profile.for_user(request.user),
        "recent_orders": _orders_of(request.user)[:3],
        "wishlist_count": WishlistItem.objects.filter(user=request.user).count(),
    }
    return render(request, "accounts/overview.html", context)


@login_required
def address(request):
    profile = Profile.for_user(request.user)
    form = AddressForm(request.POST or None, instance=profile)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, _("Your delivery address is saved. We'll fill it in for you at checkout."))
            return redirect("accounts:overview")
        messages.error(request, _("Please check the highlighted fields."))
    return render(request, "accounts/address.html", {"form": form})


@login_required
def order_list(request):
    return render(request, "accounts/order_list.html", {"orders": _orders_of(request.user)})


@login_required
def order_detail(request, number):
    # Only the customer's own orders: the first VinOp showed any order to anyone.
    order = get_object_or_404(Order.objects.prefetch_related("items__wine"), number=number, user=request.user)
    return render(request, "accounts/order_detail.html", {"order": order})


@login_required
def delete_account(request):
    form = DeleteAccountForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        user = request.user
        logout(request)
        user.delete()  # orders stay (tax law) but are no longer linked to an account
        messages.success(
            request, _("Your account is deleted. We keep past invoices for as long as tax law requires, nothing else.")
        )
        return redirect("core:home")
    return render(request, "accounts/delete_account.html", {"form": form})
