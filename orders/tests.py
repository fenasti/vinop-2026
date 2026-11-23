"""
Checkout and payment tests. Stripe is replaced by fakes (unittest.mock),
so these run offline and never touch a real Stripe account.
"""

from decimal import Decimal
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.models import Wine
from core.testing import StripeLike, fake_intent, make_user, make_wine
from team.permissions import FULFILMENT

from . import services
from .models import Order, OrderItem

CHECKOUT_DATA = {
    "email": "ana@example.com",
    "full_name": "Ana Muñoz",
    "phone": "+49 30 1234567",
    "street_address1": "Torstraße 1",
    "postcode": "10119",
    "city": "Berlin",
    "country": "DE",
    "age_confirmed": "on",
    "accept_terms": "on",
}


@override_settings(
    SHIPPING_FLAT_RATE=Decimal("9.90"),
    FREE_SHIPPING_THRESHOLD=Decimal("120.00"),
    STRIPE_SECRET_KEY="sk_test_fake",
    STRIPE_PUBLIC_KEY="pk_test_fake",
    STORE_OWNER_EMAIL="owner@vinop.example",
)
class CheckoutFlowTests(TestCase):
    def setUp(self):
        self.wine = make_wine(price="24.50", stock=10)
        self.client.post(reverse("cart:add", args=[self.wine.pk]), {"quantity": 2})

    def submit_details(self, **changes):
        return self.client.post(reverse("orders:checkout"), {**CHECKOUT_DATA, **changes})

    def test_checkout_needs_a_cart(self):
        self.client.post(reverse("cart:remove", args=[self.wine.pk]))
        response = self.client.get(reverse("orders:checkout"))
        self.assertRedirects(response, reverse("catalog:list"))

    def test_details_create_a_pending_order_with_server_side_totals(self):
        response = self.submit_details()
        order = Order.objects.get()
        self.assertRedirects(response, reverse("orders:pay", args=[order.number]), fetch_redirect_response=False)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.subtotal, Decimal("49.00"))
        self.assertEqual(order.shipping_cost, Decimal("9.90"))
        self.assertEqual(order.total, Decimal("58.90"))
        self.assertEqual(order.items.get().wine_name, self.wine.full_name)
        self.assertTrue(order.age_confirmed)
        self.assertIsNotNone(order.terms_accepted_at)

    def test_age_and_terms_are_required(self):
        response = self.submit_details(age_confirmed="", accept_terms="")
        self.assertEqual(Order.objects.count(), 0)
        self.assertContains(response, "adults aged 18 and over")
        self.assertContains(response, "accept the terms")

    def test_only_shipping_countries_are_accepted(self):
        self.submit_details(country="US")
        self.assertEqual(Order.objects.count(), 0)

    def test_going_back_reuses_the_same_pending_order(self):
        self.submit_details()
        self.submit_details(city="Hamburg")
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.get().city, "Hamburg")

    @mock.patch("orders.payments.prepare_payment", return_value="pi_123_secret_abc")
    def test_pay_page_gets_a_client_secret_for_the_order(self, prepare):
        self.submit_details()
        order = Order.objects.get()
        response = self.client.get(reverse("orders:pay", args=[order.number]))
        self.assertContains(response, "pi_123_secret_abc")
        self.assertContains(response, "Buy now, pay €58.90")
        prepare.assert_called_once()

    def test_returning_from_stripe_marks_the_order_paid(self):
        self.submit_details()
        order = Order.objects.get()
        order.stripe_payment_intent_id = "pi_123"
        order.save()

        with mock.patch("orders.payments.retrieve_intent", return_value=fake_intent(order)):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.get(reverse("orders:complete", args=[order.number]))

        self.assertRedirects(response, reverse("orders:confirmation", args=[order.number]))
        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.PAID)
        self.assertEqual(order.invoice_number, 1)
        self.assertEqual(Wine.objects.get(pk=self.wine.pk).stock, 8)
        self.assertEqual(self.client.session.get("cart"), None)  # cart emptied
        self.assertEqual(len(mail.outbox), 2)  # customer confirmation + shop alert
        self.assertEqual(mail.outbox[0].to, ["ana@example.com"])
        self.assertIn(order.number, mail.outbox[0].subject)

    def test_failed_payment_goes_back_to_the_payment_page(self):
        self.submit_details()
        order = Order.objects.get()
        order.stripe_payment_intent_id = "pi_123"
        order.save()
        intent = fake_intent(order, status="requires_payment_method")
        with mock.patch("orders.payments.retrieve_intent", return_value=intent):
            response = self.client.get(reverse("orders:complete", args=[order.number]))
        self.assertRedirects(response, reverse("orders:pay", args=[order.number]), fetch_redirect_response=False)
        self.assertEqual(Order.objects.get().status, Order.Status.PENDING)

    def test_someone_else_cannot_see_the_order(self):
        # The first VinOp showed any order to anyone who had its number.
        self.submit_details()
        order = Order.objects.get()
        stranger = self.client_class()
        self.assertEqual(stranger.get(reverse("orders:confirmation", args=[order.number])).status_code, 404)
        self.assertEqual(stranger.get(reverse("orders:pay", args=[order.number])).status_code, 404)


@override_settings(STRIPE_SECRET_KEY="sk_test_fake", STORE_OWNER_EMAIL="owner@vinop.example")
class MarkPaidTests(TestCase):
    def setUp(self):
        self.wine = make_wine(price="30.00", stock=6)
        self.order = Order.objects.create(
            email="ana@example.com",
            full_name="Ana",
            phone="1",
            street_address1="A 1",
            postcode="1",
            city="Berlin",
            country="DE",
            stripe_payment_intent_id="pi_1",
        )
        OrderItem.objects.create(
            order=self.order, wine=self.wine, wine_name="X", unit_price=Decimal("30.00"), quantity=2
        )
        self.order.recalculate()
        self.order.save()

    def test_paying_twice_does_the_work_once(self):
        with self.captureOnCommitCallbacks(execute=True):
            self.assertTrue(services.mark_paid(self.order, fake_intent(self.order)))
            self.assertFalse(services.mark_paid(self.order, fake_intent(self.order)))
        self.assertEqual(Wine.objects.get(pk=self.wine.pk).stock, 4)
        self.assertEqual(len(mail.outbox), 2)

    def test_amount_mismatch_is_flagged_for_the_team(self):
        services.mark_paid(self.order, fake_intent(self.order, amount=100))
        self.order.refresh_from_db()
        self.assertIn("CHECK BEFORE SHIPPING", self.order.staff_note)

    def test_invoice_numbers_are_sequential(self):
        services.mark_paid(self.order, fake_intent(self.order))
        second = Order.objects.create(
            email="b@example.com",
            full_name="B",
            phone="1",
            street_address1="B 1",
            postcode="1",
            city="Paris",
            country="FR",
            stripe_payment_intent_id="pi_2",
        )
        services.mark_paid(second, StripeLike(id="pi_2", amount_received=0, amount=0))
        self.assertEqual(Order.objects.get(pk=second.pk).invoice_number, 2)

    def test_cancelling_a_paid_order_restocks(self):
        services.mark_paid(self.order, fake_intent(self.order))
        services.cancel(Order.objects.get(pk=self.order.pk))
        self.assertEqual(Wine.objects.get(pk=self.wine.pk).stock, 6)

    def test_deleting_a_wine_keeps_the_order_history(self):
        self.wine.delete()
        item = OrderItem.objects.get()
        self.assertIsNone(item.wine)
        self.assertEqual(item.wine_name, "X")


@override_settings(STRIPE_SECRET_KEY="sk_test_fake", STRIPE_WEBHOOK_SECRET="whsec_fake")
class WebhookTests(TestCase):
    url = reverse("orders:webhook")

    def setUp(self):
        self.order = Order.objects.create(
            email="ana@example.com",
            full_name="Ana",
            phone="1",
            street_address1="A 1",
            postcode="1",
            city="Berlin",
            country="DE",
            stripe_payment_intent_id="pi_hook",
            total=Decimal("10.00"),
        )

    def post_event(self, event):
        with mock.patch("orders.payments.construct_event", return_value=event):
            return self.client.post(
                self.url, data=b"{}", content_type="application/json", HTTP_STRIPE_SIGNATURE="t=1,v1=x"
            )

    def test_rejects_a_bad_signature(self):
        response = self.client.post(self.url, data=b"{}", content_type="application/json", HTTP_STRIPE_SIGNATURE="nope")
        self.assertEqual(response.status_code, 400)

    def test_payment_succeeded_marks_the_order_paid(self):
        event = StripeLike(type="payment_intent.succeeded", data=StripeLike(object=fake_intent(self.order)))
        self.assertEqual(self.post_event(event).status_code, 200)
        self.assertEqual(Order.objects.get().status, Order.Status.PAID)

    def test_full_refund_marks_the_order_refunded(self):
        self.order.status = Order.Status.PAID
        self.order.save()
        charge = StripeLike(payment_intent="pi_hook", refunded=True)
        self.post_event(StripeLike(type="charge.refunded", data=StripeLike(object=charge)))
        self.assertEqual(Order.objects.get().status, Order.Status.REFUNDED)

    def test_unknown_events_are_acknowledged(self):
        self.assertEqual(
            self.post_event(StripeLike(type="customer.created", data=StripeLike(object={}))).status_code, 200
        )


class TeamOrderTests(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            email="ana@example.com",
            full_name="Ana",
            phone="1",
            street_address1="A 1",
            postcode="1",
            city="Berlin",
            country="DE",
            status=Order.Status.PAID,
        )
        self.client.force_login(make_user("pack@example.com", FULFILMENT))

    def test_ship_sends_tracking_email(self):
        url = reverse("team:order_ship", args=[self.order.number])
        self.client.post(url, {"carrier": "DHL", "tracking_number": "00340434"})
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.SHIPPED)
        self.assertIn("00340434", mail.outbox[0].body)

    def test_packing_list_lists_paid_orders(self):
        response = self.client.get(reverse("team:packing_list"))
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn(self.order.number, response.content.decode())
