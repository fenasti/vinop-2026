import uuid

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class SubscriberQuerySet(models.QuerySet):
    def confirmed(self):
        return self.exclude(confirmed_at=None)


class Subscriber(models.Model):
    """
    Newsletter sign-up with double opt-in, as German/EU law expects:
    the address only counts once its owner clicks the link we email.
    Every email carries an unsubscribe link (the same token).
    """

    email = models.EmailField(_("email"), unique=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(_("confirmed"), null=True, blank=True)

    objects = SubscriberQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("subscriber")
        verbose_name_plural = _("subscribers")

    def __str__(self):
        return self.email

    @property
    def is_confirmed(self) -> bool:
        return self.confirmed_at is not None

    def confirm(self) -> None:
        if not self.confirmed_at:
            self.confirmed_at = timezone.now()
            self.save(update_fields=["confirmed_at"])

    def get_confirm_url(self):
        return reverse("newsletter:confirm", args=[self.token])

    def get_unsubscribe_url(self):
        return reverse("newsletter:unsubscribe", args=[self.token])
