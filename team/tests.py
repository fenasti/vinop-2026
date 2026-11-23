from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from catalog.models import Region, Wine
from core.testing import make_user, make_wine
from reviews.models import Review

from .permissions import CELLAR_KEEPER, FULFILMENT, ROLES, SHOP_MANAGER, SITE_EDITOR, Area, can


class RoleTests(TestCase):
    def test_role_groups_exist_after_migrate(self):
        self.assertEqual(set(Group.objects.values_list("name", flat=True)), set(ROLES))

    def test_what_each_role_can_open(self):
        manager = make_user("m@example.com", SHOP_MANAGER)
        packer = make_user("p@example.com", FULFILMENT)
        designer = make_user("d@example.com", SITE_EDITOR)
        customer = make_user("c@example.com")
        owner = make_user("o@example.com", superuser=True)

        self.assertTrue(all(can(manager, area) for area in Area))
        self.assertTrue(all(can(owner, area) for area in Area))
        self.assertTrue(can(packer, Area.ORDERS))
        self.assertFalse(can(packer, Area.CATALOG))
        self.assertTrue(can(designer, Area.STUDIO))
        self.assertFalse(can(designer, Area.ORDERS))
        self.assertFalse(any(can(customer, area) for area in Area))

    def test_customers_get_a_403_not_a_crash(self):
        self.client.force_login(make_user())
        self.assertEqual(self.client.get(reverse("team:hub")).status_code, 403)

    def test_guests_are_sent_to_login(self):
        response = self.client.get(reverse("team:wines"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("account_login"), response["Location"])


class CatalogCrudTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user("cellar@example.com", CELLAR_KEEPER))

    def test_create_a_wine_without_django_admin(self):
        wine = make_wine()  # gives us a winery and region
        data = {
            "winery": wine.winery.pk,
            "name": "Nuevo",
            "vintage": 2023,
            "style": "white",
            "region": wine.region.pk,
            "price": "18.00",
            "stock": 12,
            "is_active": "on",
            "alcohol": "12.5",
            "volume_ml": 750,
        }
        response = self.client.post(reverse("team:wine_add"), data)
        self.assertRedirects(response, reverse("team:wines"))
        self.assertTrue(Wine.objects.filter(name="Nuevo", price=Decimal("18.00")).exists())

    def test_previous_price_must_be_higher(self):
        wine = make_wine(price="20.00")
        data = {
            "winery": wine.winery.pk,
            "name": "X",
            "style": "red",
            "region": wine.region.pk,
            "price": "20.00",
            "compare_at_price": "15.00",
            "stock": 1,
            "alcohol": "13",
            "volume_ml": 750,
        }
        response = self.client.post(reverse("team:wine_add"), data)
        self.assertContains(response, "previous price must be higher")

    def test_hide_and_restock(self):
        wine = make_wine(stock=1)
        self.client.post(reverse("team:wine_toggle", args=[wine.pk]))
        self.client.post(reverse("team:wine_stock", args=[wine.pk]), {"stock": 48})
        wine.refresh_from_db()
        self.assertFalse(wine.is_active)
        self.assertEqual(wine.stock, 48)

    def test_deleting_a_region_in_use_explains_instead_of_crashing(self):
        wine = make_wine()
        response = self.client.post(reverse("team:region_delete", args=[wine.region.pk]), follow=True)
        self.assertContains(response, "can&#x27;t be deleted")
        self.assertTrue(Region.objects.filter(pk=wine.region.pk).exists())

    def test_cellar_keeper_can_moderate_reviews(self):
        review = Review.objects.create(user=make_user(), wine=make_wine(), rating=1, body="Meh")
        self.client.post(reverse("team:review_toggle", args=[review.pk]))
        review.refresh_from_db()
        self.assertFalse(review.is_published)


class MemberTests(TestCase):
    def setUp(self):
        self.manager = make_user("boss@example.com", SHOP_MANAGER)
        self.client.force_login(self.manager)

    def test_give_someone_a_role(self):
        colleague = make_user("colleague@example.com")
        self.client.post(reverse("team:member_edit", args=[colleague.pk]), {"roles": [FULFILMENT]})
        self.assertTrue(can(type(colleague).objects.get(pk=colleague.pk), Area.ORDERS))

    def test_you_cannot_lock_yourself_out(self):
        self.client.post(reverse("team:member_edit", args=[self.manager.pk]), {"roles": []})
        self.assertTrue(self.manager.groups.filter(name=SHOP_MANAGER).exists())

    def test_find_by_email(self):
        colleague = make_user("colleague@example.com")
        response = self.client.post(reverse("team:members"), {"email": "COLLEAGUE@example.com"})
        self.assertRedirects(response, reverse("team:member_edit", args=[colleague.pk]))
