from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from core.testing import make_user, make_wine
from team.permissions import CELLAR_KEEPER

from .models import Region


class WineModelTests(TestCase):
    def test_slug_is_unique_and_readable(self):
        first = make_wine(name="Gran Reserva")
        second = make_wine(name="Gran Reserva")
        self.assertEqual(first.slug, "hacienda-test-gran-reserva-2022")
        self.assertEqual(second.slug, "hacienda-test-gran-reserva-2022-2")

    def test_price_per_litre_for_a_half_bottle(self):
        wine = make_wine(price="19.90", volume_ml=375)
        self.assertEqual(wine.price_per_litre, Decimal("53.07"))

    def test_non_vintage_label(self):
        self.assertEqual(make_wine(vintage=None).vintage_label, "NV")


class WineListTests(TestCase):
    def setUp(self):
        self.red = make_wine(name="Red One", style="red")
        self.white = make_wine(name="White One", style="white")
        self.hidden = make_wine(name="Secret", is_active=False)

    def test_lists_only_visible_wines(self):
        response = self.client.get(reverse("catalog:list"))
        self.assertContains(response, "Red One")
        self.assertNotContains(response, "Secret")

    def test_filters_by_style(self):
        response = self.client.get(reverse("catalog:list"), {"style": "white"})
        self.assertContains(response, "White One")
        self.assertNotContains(response, "Red One")

    def test_bad_filter_values_do_not_break_the_page(self):
        response = self.client.get(reverse("catalog:list"), {"region": "atlantis", "max_price": "cheap", "page": "999"})
        self.assertEqual(response.status_code, 200)

    def test_empty_search_shows_everything(self):
        # The first VinOp redirected with an error on an empty search box.
        response = self.client.get(reverse("catalog:list"), {"q": ""})
        self.assertContains(response, "Red One")

    def test_search_finds_by_grape_without_duplicates(self):
        from catalog.models import Grape

        self.red.grapes.add(Grape.objects.create(name="Carménère"), Grape.objects.create(name="Carignan"))
        response = self.client.get(reverse("catalog:list"), {"q": "Car"})
        self.assertEqual(list(response.context["wines"]).count(self.red), 1)

    def test_regions_are_ordered_north_to_south(self):
        Region.objects.create(name="Malleco", latitude=Decimal("38.1"))
        Region.objects.create(name="Elqui", latitude=Decimal("30.0"))
        self.assertEqual(Region.objects.first().name, "Elqui")


class WineDetailTests(TestCase):
    def test_hidden_wine_is_404_for_customers_but_visible_to_the_cellar_team(self):
        hidden = make_wine(is_active=False)
        self.assertEqual(self.client.get(hidden.get_absolute_url()).status_code, 404)
        self.client.force_login(make_user("cellar@example.com", CELLAR_KEEPER))
        self.assertContains(self.client.get(hidden.get_absolute_url()), "hidden from customers")

    def test_shows_unit_price_and_sulphites(self):
        response = self.client.get(make_wine(price="15.00").get_absolute_url())
        self.assertContains(response, "€20.00 per litre")
        self.assertContains(response, "Contains sulphites")
