from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class LegalPage(models.Model):
    """
    Imprint, privacy policy, terms, right of withdrawal, shipping info…

    Selling wine to consumers in Germany and the rest of the EU legally
    requires most of these pages. `seed_demo` creates them with placeholder
    text marked "TODO" — have the real wording checked by a lawyer before
    launch. Shop Managers edit them in the team area (/team/pages/).
    """

    slug = models.SlugField(_("address"), unique=True, help_text=_("Used in the link, e.g. 'imprint'."))
    title = models.CharField(_("title"), max_length=120)
    body = models.TextField(_("text"), help_text=_("Plain text. An empty line starts a new paragraph."))
    show_in_footer = models.BooleanField(_("show in footer"), default=True)
    position = models.PositiveSmallIntegerField(_("footer position"), default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "title"]
        verbose_name = _("legal page")
        verbose_name_plural = _("legal pages")

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("core:legal", args=[self.slug])
