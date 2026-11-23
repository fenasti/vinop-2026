from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Review

RATING_CHOICES = [
    (5, _("5 – Outstanding")),
    (4, _("4 – Very good")),
    (3, _("3 – Good")),
    (2, _("2 – Not for me")),
    (1, _("1 – Disappointing")),
]


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(
        label=_("Your rating"), choices=RATING_CHOICES, coerce=int, widget=forms.RadioSelect
    )

    class Meta:
        model = Review
        fields = ["rating", "title", "body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 5})}
