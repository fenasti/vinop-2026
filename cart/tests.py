from decimal import Decimal

from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse

from core.testing import make_wine

from .pricing import shipping_for, to_cents


@override_settings(SHIPPING_FLAT_RATE=Decimal("9.90"), FREE_SHIPPING_THRESHOLD=Decimal("120.00"))
class PricingTests(TestCase):
    def test_shipping_rules(self):
        self.assertEqual(shipping_for(Decimal("0")), Decimal("0.00"))
        self.assertEqual(shipping_for(Decimal("50")), Decimal("9.90"))
        self.assertEqual(shipping_for(Decimal("120")), Decimal("0.00"))

    def test_cents_never_lose_precision(self):
        self.assertEqual(to_cents(Decimal("24.90")), 2490)
        self.assertEqual(to_cents(Decimal("0.1") + Decimal("0.2")), 30)


class CartViewTests(TestCase):
    def setUp(self):
        self.wine = make_wine(stock=5)

    def add(self, quantity, **extra):
        return self.client.post(reverse("cart:add", args=[self.wine.pk]), {"quantity": quantity, **extra})

    def cart(self):
        return self.client.session.get("cart", {})

    def test_add_and_update(self):
        self.add(2)
        self.assertEqual(self.cart(), {str(self.wine.pk): 2})
        self.client.post(reverse("cart:update", args=[self.wine.pk]), {"quantity": 4})
        self.assertEqual(self.cart(), {str(self.wine.pk): 4})

    def test_never_more_than_in_stock(self):
        response = self.add(9)
        self.assertEqual(self.cart(), {str(self.wine.pk): 5})
        self.assertIn("up to 5 bottles", str(list(get_messages(response.wsgi_request))[0]))

    def test_sold_out_wine_cannot_be_added(self):
        self.wine.stock = 0
        self.wine.save()
        self.add(1)
        self.assertEqual(self.cart(), {})

    def test_get_requests_change_nothing(self):
        response = self.client.get(reverse("cart:add", args=[self.wine.pk]))
        self.assertEqual(response.status_code, 405)

    def test_invalid_quantity_is_rejected_politely(self):
        response = self.add("lots")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.cart(), {})

    def test_next_cannot_redirect_to_another_site(self):
        response = self.add(1, next="https://evil.example/")
        self.assertEqual(response["Location"], reverse("cart:detail"))

    def test_a_deleted_wine_disappears_instead_of_crashing_every_page(self):
        # In the first VinOp, a deleted product in the bag made every page 404.
        self.add(1)
        self.wine.delete()
        self.assertEqual(self.client.get(reverse("core:home")).status_code, 200)
        response = self.client.get(reverse("cart:detail"))
        self.assertContains(response, "Your cart is empty")

    def test_stock_drop_trims_the_cart(self):
        self.add(5)
        self.wine.stock = 2
        self.wine.save()
        self.client.get(reverse("cart:detail"))
        self.assertEqual(self.cart(), {str(self.wine.pk): 2})
