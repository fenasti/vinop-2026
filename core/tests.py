from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from catalog.models import Region
from core.testing import make_wine

from .models import LegalPage


class HomeTests(TestCase):
    def test_latitude_ribbon_runs_north_to_south_with_gaps(self):
        south = Region.objects.create(name="Malleco", latitude=Decimal("38.1"))
        north = Region.objects.create(name="Elqui", latitude=Decimal("30.0"))
        make_wine(name="Sur", region=south)
        make_wine(name="Norte", region=north)

        regions = self.client.get(reverse("core:home")).context["regions"]
        self.assertEqual([r.name for r in regions], ["Elqui", "Malleco"])
        self.assertEqual(regions[1].gap, Decimal("8.1"))

    def test_home_works_on_an_empty_shop(self):
        self.assertEqual(self.client.get(reverse("core:home")).status_code, 200)


class LegalPageTests(TestCase):
    def test_pages_show_and_appear_in_the_footer(self):
        LegalPage.objects.create(slug="imprint", title="Imprint", body="VinOp GmbH\n\nBerlin")
        response = self.client.get(reverse("core:legal", args=["imprint"]))
        self.assertContains(response, "<p>VinOp GmbH</p>", html=True)
        self.assertContains(self.client.get(reverse("core:home")), 'href="/legal/imprint/"')
