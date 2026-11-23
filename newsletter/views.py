from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from core.emails import send_templated_email
from core.utils import redirect_back

from .forms import SubscribeForm
from .models import Subscriber


@require_POST
def subscribe(request):
    form = SubscribeForm(request.POST)
    if not form.is_valid():
        messages.error(request, _("Please enter a valid email address to subscribe."))
    else:
        email = form.cleaned_data["email"].lower()
        subscriber, _created = Subscriber.objects.get_or_create(email=email)
        if subscriber.is_confirmed:
            messages.info(request, _("You're already on the list. Thanks!"))
        else:
            send_templated_email(
                "newsletter_confirm",
                {
                    "confirm_url": request.build_absolute_uri(subscriber.get_confirm_url()),
                    "unsubscribe_url": request.build_absolute_uri(subscriber.get_unsubscribe_url()),
                },
                [subscriber.email],
            )
            messages.success(request, _("Almost done: we've sent you an email. Click the link in it to confirm."))
    return redirect_back(request, "core:home")


def confirm(request, token):
    subscriber = get_object_or_404(Subscriber, token=token)
    subscriber.confirm()
    return render(request, "newsletter/confirmed.html", {"subscriber": subscriber})


def unsubscribe(request, token):
    """GET shows a confirm button (so link scanners can't unsubscribe people); POST removes."""
    subscriber = get_object_or_404(Subscriber, token=token)
    if request.method == "POST":
        subscriber.delete()
        messages.success(request, _("You're unsubscribed and your email address is deleted."))
        return redirect("core:home")
    return render(request, "newsletter/unsubscribe.html", {"subscriber": subscriber})
