from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from core.models import LegalPage

from .permissions import ROLE_DESCRIPTIONS, ROLES


class LegalPageForm(forms.ModelForm):
    class Meta:
        model = LegalPage
        fields = ["title", "slug", "body", "show_in_footer", "position"]
        widgets = {"body": forms.Textarea(attrs={"rows": 18})}


class FindMemberForm(forms.Form):
    email = forms.EmailField(
        label=_("Customer's email address"),
        help_text=_("They need a VinOp account first: ask them to sign up, then add them here."),
    )

    def clean_email(self):
        email = self.cleaned_data["email"]
        user = get_user_model().objects.filter(email__iexact=email).first()
        if user is None:
            raise forms.ValidationError(_("Nobody has signed up with that address yet."))
        self.user = user
        return email


class MemberRolesForm(forms.Form):
    roles = forms.MultipleChoiceField(
        label=_("Roles"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=[(name, f"{name} – {ROLE_DESCRIPTIONS[name]}") for name in ROLES],
        help_text=_("Untick every role to remove someone from the team."),
    )
