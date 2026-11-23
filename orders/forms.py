from django import forms
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Order

# Lets browsers and password managers fill the address in one tap.
AUTOCOMPLETE = {
    "full_name": "name",
    "email": "email",
    "phone": "tel",
    "street_address1": "address-line1",
    "street_address2": "address-line2",
    "postcode": "postal-code",
    "city": "address-level2",
    "region": "address-level1",
    "country": "country",
}

ADDRESS_FIELDS = ["full_name", "phone", "street_address1", "street_address2", "postcode", "city", "region", "country"]


class CheckoutForm(forms.ModelForm):
    age_confirmed = forms.BooleanField(
        label=_("I am 18 or older"),
        error_messages={"required": _("We can only sell wine to adults aged 18 and over.")},
    )
    accept_terms = forms.BooleanField(
        label=_("I accept the terms and conditions and have read the right of withdrawal"),
        error_messages={"required": _("Please accept the terms to place your order.")},
    )
    save_address = forms.BooleanField(label=_("Save this address to my profile"), required=False, initial=True)

    class Meta:
        model = Order
        fields = ["email", *ADDRESS_FIELDS, "customer_note", "age_confirmed"]
        widgets = {
            "phone": forms.TextInput(attrs={"type": "tel", "inputmode": "tel"}),
            "customer_note": forms.Textarea(
                attrs={"rows": 2, "placeholder": _("Delivery instructions, a gift message…")}
            ),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        for name, token in AUTOCOMPLETE.items():
            self.fields[name].widget.attrs["autocomplete"] = token
        self.fields["accept_terms"].help_text = format_html(
            '<a href="{}" target="_blank">{}</a> and <a href="{}" target="_blank">{}</a>',
            reverse("core:legal", args=["terms"]),
            _("Terms and conditions"),
            reverse("core:legal", args=["withdrawal"]),
            _("Right of withdrawal"),
        )
        if not (user and user.is_authenticated):
            del self.fields["save_address"]

    def contact_fields(self):
        return [self["email"]]

    def address_fields(self):
        return [self[name] for name in ADDRESS_FIELDS]

    def confirmation_fields(self):
        names = ["customer_note", "save_address", "age_confirmed", "accept_terms"]
        return [self[name] for name in names if name in self.fields]


class ShipOrderForm(forms.Form):
    carrier = forms.CharField(label=_("Carrier"), max_length=40, initial="DHL")
    tracking_number = forms.CharField(label=_("Tracking number"), max_length=64, required=False)


class StaffNoteForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["staff_note"]
        widgets = {"staff_note": forms.Textarea(attrs={"rows": 3})}
