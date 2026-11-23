from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .colors import READABLE, contrast_ratio
from .fonts import BODY_FONT_CHOICES, HEADING_FONT_CHOICES, font_stack, google_fonts_url

hex_color = RegexValidator(r"^#[0-9A-Fa-f]{6}$", _("Use a colour in #RRGGBB format."))


def color_field(label, default, help_text=""):
    return models.CharField(label, max_length=7, default=default, validators=[hex_color], help_text=help_text)


class SiteSettings(models.Model):
    """
    Everything about how the shop LOOKS, editable at /team/studio/ by the
    "Site Editor" role — no code, no Django admin.

    Deliberately excluded: anything that changes what customers pay
    (prices, shipping). That stays in settings.py / environment variables.

    It's a singleton: always use SiteSettings.load(), never create rows.
    """

    # Identity
    shop_name = models.CharField(_("shop name"), max_length=40, default="VinOp")
    tagline = models.CharField(
        _("tagline"),
        max_length=140,
        default="Wines from small Chilean producers, delivered across Europe.",
        help_text=_("Shown under the logo in search results and the footer."),
    )
    logo = models.ImageField(
        _("logo"), upload_to="studio/", blank=True, help_text=_("Optional. Without it, the shop name is shown.")
    )
    favicon = models.ImageField(_("browser tab icon"), upload_to="studio/", blank=True)

    # Homepage
    hero_title = models.CharField(_("homepage title"), max_length=90, default="The length of Chile, by the bottle.")
    hero_text = models.CharField(
        _("homepage introduction"),
        max_length=240,
        default=(
            "Small producers from the Elqui desert to the rain of Malleco. "
            "Imported, duty paid and shipped to every EU country."
        ),
    )
    hero_cta = models.CharField(_("homepage button"), max_length=30, default="Browse the wines")
    hero_image = models.ImageField(_("homepage photo"), upload_to="studio/", blank=True)

    # Announcement bar
    announcement_enabled = models.BooleanField(_("show the announcement bar"), default=False)
    announcement_text = models.CharField(_("announcement"), max_length=140, blank=True)

    # Colours
    color_background = color_field(_("page background"), "#EDF0EE")
    color_surface = color_field(_("cards and panels"), "#FFFFFF")
    color_text = color_field(_("text"), "#17222B")
    color_primary = color_field(_("main colour"), "#6E1E3A", _("Buttons, prices and links. White text sits on it."))
    color_secondary = color_field(_("second colour"), "#2D6A6E", _("Regions, stock notes and small highlights."))

    # Typography
    heading_font = models.CharField(_("headings"), max_length=20, choices=HEADING_FONT_CHOICES, default="palatino")
    body_font = models.CharField(_("body text"), max_length=20, choices=BODY_FONT_CHOICES, default="system")

    # Footer & contact
    footer_text = models.CharField(
        _("footer text"),
        max_length=200,
        blank=True,
        default="Please enjoy responsibly. We only sell to adults aged 18 and over.",
    )
    contact_email = models.EmailField(_("contact email"), blank=True)
    contact_phone = models.CharField(_("contact phone"), max_length=30, blank=True)
    instagram_url = models.URLField(_("Instagram link"), blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("site settings")
        verbose_name_plural = _("site settings")

    def __str__(self):
        return str(_("Site appearance"))

    def save(self, *args, **kwargs):
        self.pk = 1  # only ever one row
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SiteSettings":
        settings, _created = cls.objects.get_or_create(pk=1)
        return settings

    # Helpers used by templates/base.html
    @property
    def heading_font_stack(self) -> str:
        return font_stack(self.heading_font)

    @property
    def body_font_stack(self) -> str:
        return font_stack(self.body_font)

    @property
    def google_fonts_url(self) -> str:
        return google_fonts_url(self.heading_font, self.body_font)

    def readability_warnings(self) -> list[str]:
        """Plain-language warnings when colours make text hard to read."""
        checks = [
            (self.color_text, self.color_background, _("Text on the page background")),
            (self.color_text, self.color_surface, _("Text on cards and panels")),
            ("#FFFFFF", self.color_primary, _("White button text on the main colour")),
            (self.color_secondary, self.color_surface, _("The second colour on cards")),
        ]
        return [
            str(label) for foreground, background, label in checks if contrast_ratio(foreground, background) < READABLE
        ]
