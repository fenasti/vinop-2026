from django import forms
from django.utils.translation import gettext_lazy as _


class SubscribeForm(forms.Form):
    email = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": _("you@example.com")}),
    )
