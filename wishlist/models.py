from django.conf import settings
from django.db import models


class WishlistItem(models.Model):
    """
    One saved wine for one user. A plain row per wine (instead of the first
    VinOp's one-wishlist-per-user object) means there is nothing to create
    when a user signs up, so old accounts can never hit a missing wishlist.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_items")
    wine = models.ForeignKey("catalog.Wine", on_delete=models.CASCADE, related_name="wishlisted")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-added_at"]
        constraints = [models.UniqueConstraint(fields=["user", "wine"], name="wishlist_once_per_wine")]

    def __str__(self):
        return f"{self.user} ♥ {self.wine}"
