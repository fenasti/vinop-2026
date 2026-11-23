from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Review(models.Model):
    """One review per customer per wine; they can edit it any time."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews")
    wine = models.ForeignKey("catalog.Wine", on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(
        _("rating"),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        choices=[(n, str(n)) for n in range(5, 0, -1)],
    )
    title = models.CharField(_("headline"), max_length=100, blank=True)
    body = models.TextField(_("your review"), max_length=2000)
    is_published = models.BooleanField(_("published"), default=True, help_text=_("Untick to hide it from the shop."))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [models.UniqueConstraint(fields=["user", "wine"], name="review_once_per_wine")]
        verbose_name = _("review")
        verbose_name_plural = _("reviews")

    def __str__(self):
        return f"{self.rating}★ for {self.wine} by {self.author_name}"

    @property
    def author_name(self) -> str:
        """First name and initial ("Ana M."), never the full email address."""
        user = self.user
        if user.first_name:
            initial = f" {user.last_name[:1]}." if user.last_name else ""
            return f"{user.first_name}{initial}"
        return user.email.split("@")[0] if user.email else str(_("A customer"))
