from django import forms
from django.utils.translation import gettext_lazy as _

from .models import SiteSettings

COLOR_FIELDS = ("color_background", "color_surface", "color_text", "color_primary", "color_secondary")


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = [
            "shop_name",
            "tagline",
            "logo",
            "favicon",
            "hero_title",
            "hero_text",
            "hero_cta",
            "hero_image",
            "announcement_enabled",
            "announcement_text",
            *COLOR_FIELDS,
            "heading_font",
            "body_font",
            "footer_text",
            "contact_email",
            "contact_phone",
            "instagram_url",
        ]
        widgets = {name: forms.TextInput(attrs={"type": "color"}) for name in COLOR_FIELDS}

    # The Studio template shows the fields in these panels.
    def _fields(self, *names):
        return [self[name] for name in names]

    def identity_fields(self):
        return self._fields("shop_name", "tagline", "logo", "favicon")

    def homepage_fields(self):
        return self._fields("hero_title", "hero_text", "hero_cta", "hero_image")

    def announcement_fields(self):
        return self._fields("announcement_enabled", "announcement_text")

    def colour_fields(self):
        return self._fields(*COLOR_FIELDS)

    def type_fields(self):
        return self._fields("heading_font", "body_font")

    def footer_fields(self):
        return self._fields("footer_text", "contact_email", "contact_phone", "instagram_url")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("announcement_enabled") and not cleaned.get("announcement_text"):
            self.add_error("announcement_text", _("Write the announcement, or switch the bar off."))
        return cleaned
