"""Small helpers shared by the test suites (python manage.py test)."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from catalog.models import Region, Wine, Winery


class StripeLike(dict):
    """A dict you can also read with dots, like Stripe's own objects."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(name) from error


def fake_intent(order, status="succeeded", amount=None):
    cents = order.total_cents if amount is None else amount
    return StripeLike(
        id=order.stripe_payment_intent_id or "pi_test_123",
        status=status,
        amount=cents,
        amount_received=cents if status == "succeeded" else 0,
        metadata={"order_number": order.number},
    )


def make_user(email="ana@example.com", *roles, password="a-long-test-password", superuser=False):
    user = get_user_model().objects.create_user(
        username=email.split("@")[0], email=email, password=password, is_superuser=superuser
    )
    for role in roles:
        user.groups.add(Group.objects.get_or_create(name=role)[0])
    return user


def make_wine(name="Carménère Reserva", price="20.00", stock=10, **extra):
    region, _created = Region.objects.get_or_create(name="Colchagua", defaults={"latitude": Decimal("34.6")})
    winery, _created = Winery.objects.get_or_create(name="Hacienda Test", defaults={"region": region})
    defaults = {"winery": winery, "region": region, "alcohol": Decimal("13.5"), "vintage": 2022}
    return Wine.objects.create(name=name, price=Decimal(price), stock=stock, **{**defaults, **extra})
