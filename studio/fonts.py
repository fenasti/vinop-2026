"""
Typefaces offered in the Studio.

Each entry: key → (label shown in the Studio, CSS font stack, Google Fonts
family string or "" for fonts already installed on the visitor's device).

Why the "no external fonts" options are the default: loading fonts from
Google's servers sends the visitor's IP address to Google, which German
courts have treated as a GDPR problem without consent. The default look
uses fonts every device already has. If you pick a Google font, either
mention it in your privacy policy or self-host the font files.
"""

from django.utils.translation import gettext_lazy as _

FONTS = {
    "palatino": (
        _("Palatino – classic book serif (no external fonts)"),
        '"Palatino Linotype", Palatino, "Book Antiqua", "URW Palladio L", Georgia, serif',
        "",
    ),
    "georgia": (
        _("Georgia – sturdy serif (no external fonts)"),
        'Georgia, "Times New Roman", serif',
        "",
    ),
    "system": (
        _("System sans – the device's own font (no external fonts)"),
        'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
        "",
    ),
    "cormorant": (
        _("Cormorant Garamond – refined, high contrast (Google Fonts)"),
        '"Cormorant Garamond", Garamond, Georgia, serif',
        "Cormorant+Garamond:wght@500;600;700",
    ),
    "spectral": (
        _("Spectral – modern book serif (Google Fonts)"),
        '"Spectral", Georgia, serif',
        "Spectral:wght@400;600",
    ),
    "source-sans": (
        _("Source Sans 3 – clear and open (Google Fonts)"),
        '"Source Sans 3", system-ui, sans-serif',
        "Source+Sans+3:wght@400;600",
    ),
    "work-sans": (
        _("Work Sans – friendly grotesque (Google Fonts)"),
        '"Work Sans", system-ui, sans-serif',
        "Work+Sans:wght@400;600",
    ),
}

HEADING_FONT_CHOICES = [(key, FONTS[key][0]) for key in ("palatino", "georgia", "cormorant", "spectral", "system")]
BODY_FONT_CHOICES = [(key, FONTS[key][0]) for key in ("system", "source-sans", "work-sans", "georgia", "palatino")]


def font_stack(key: str) -> str:
    return FONTS.get(key, FONTS["system"])[1]


def google_fonts_url(*keys: str) -> str:
    """Stylesheet URL for the chosen Google fonts, or "" if none is needed."""
    families = sorted({FONTS[key][2] for key in keys if key in FONTS and FONTS[key][2]})
    if not families:
        return ""
    query = "&".join(f"family={family}" for family in families)
    return f"https://fonts.googleapis.com/css2?{query}&display=swap"
