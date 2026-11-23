from core.models import LegalPage

from .models import SiteSettings


def site(request):
    """Shop appearance + footer links, available in every template as `site`."""
    return {
        "site": SiteSettings.load(),
        "footer_pages": LegalPage.objects.filter(show_in_footer=True).only("slug", "title"),
    }
