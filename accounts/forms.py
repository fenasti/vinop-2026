from django import forms
from django.utils.translation import gettext_lazy as _

from orders.forms import AUTOCOMPLETE

from .models import ADDRESS_FIELDS, Profile


class AddressForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = list(ADDRESS_FIELDS)
        widgets = {"phone": forms.TextInput(attrs={"type": "tel", "inputmode": "tel"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.fields:
            self.fields[name].widget.attrs["autocomplete"] = AUTOCOMPLETE[name]


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label=_("Your password"), widget=forms.PasswordInput(attrs={"autocomplete": "current-password"})
    )

    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError(_("That password isn't right."))
        return password
