from django.test import TestCase
from django.urls import reverse

from core.testing import make_user
from orders.models import Order

from .models import Profile


class ProfileTests(TestCase):
    def test_every_new_user_gets_a_profile(self):
        self.assertTrue(Profile.objects.filter(user=make_user()).exists())

    def test_old_accounts_without_a_profile_still_work(self):
        # The first VinOp crashed for users created before the profile/wishlist apps.
        user = make_user()
        Profile.objects.filter(user=user).delete()
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("accounts:overview")).status_code, 200)
        self.assertEqual(self.client.get(reverse("wishlist:list")).status_code, 200)

    def test_saving_an_address(self):
        self.client.force_login(make_user())
        self.client.post(
            reverse("accounts:address"),
            {"full_name": "Ana", "street_address1": "Calle 1", "city": "Madrid", "postcode": "28001", "country": "ES"},
        )
        self.assertEqual(Profile.objects.get().city, "Madrid")


class OrderHistoryTests(TestCase):
    def setUp(self):
        self.ana = make_user("ana@example.com")
        self.order = Order.objects.create(
            user=self.ana,
            email="ana@example.com",
            full_name="Ana",
            phone="1",
            street_address1="A 1",
            postcode="1",
            city="Berlin",
            country="DE",
            status=Order.Status.PAID,
        )

    def test_customers_see_their_own_orders(self):
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(reverse("accounts:orders")), self.order.number)

    def test_customers_cannot_see_other_peoples_orders(self):
        self.client.force_login(make_user("ben@example.com"))
        response = self.client.get(reverse("accounts:order_detail", args=[self.order.number]))
        self.assertEqual(response.status_code, 404)

    def test_deleting_an_account_keeps_the_invoice(self):
        self.client.force_login(self.ana)
        self.client.post(reverse("accounts:delete"), {"password": "a-long-test-password"})
        self.order.refresh_from_db()
        self.assertIsNone(self.order.user)

    def test_deleting_needs_the_right_password(self):
        self.client.force_login(self.ana)
        response = self.client.post(reverse("accounts:delete"), {"password": "wrong"})
        self.assertContains(response, "That password isn")
