from django.core import mail
from django.test import TestCase
from django.urls import reverse

from core.testing import make_user
from team.permissions import SHOP_MANAGER

from .models import Subscriber


class DoubleOptInTests(TestCase):
    def test_subscribing_sends_a_confirmation_link(self):
        self.client.post(reverse("newsletter:subscribe"), {"email": "Ana@Example.com"})
        subscriber = Subscriber.objects.get()
        self.assertEqual(subscriber.email, "ana@example.com")
        self.assertFalse(subscriber.is_confirmed)
        self.assertIn(str(subscriber.token), mail.outbox[0].body)

    def test_confirm_link(self):
        subscriber = Subscriber.objects.create(email="ana@example.com")
        self.client.get(reverse("newsletter:confirm", args=[subscriber.token]))
        subscriber.refresh_from_db()
        self.assertTrue(subscriber.is_confirmed)

    def test_unsubscribe_needs_a_click_not_just_opening_the_link(self):
        subscriber = Subscriber.objects.create(email="ana@example.com")
        url = reverse("newsletter:unsubscribe", args=[subscriber.token])
        self.client.get(url)
        self.assertTrue(Subscriber.objects.exists())
        self.client.post(url)
        self.assertFalse(Subscriber.objects.exists())

    def test_export_only_contains_confirmed_addresses(self):
        confirmed = Subscriber.objects.create(email="yes@example.com")
        confirmed.confirm()
        Subscriber.objects.create(email="maybe@example.com")
        self.client.force_login(make_user("boss@example.com", SHOP_MANAGER))
        csv = self.client.get(reverse("team:subscriber_export")).content.decode()
        self.assertIn("yes@example.com", csv)
        self.assertNotIn("maybe@example.com", csv)
