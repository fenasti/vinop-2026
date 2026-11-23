"""
The shopping cart, stored in the visitor's session.

The session only ever holds {"<wine id>": <quantity>}. Prices are always
read fresh from the database, so a customer can't be charged an old price
and a deleted wine simply disappears from the cart instead of crashing
every page (a bug in the first VinOp).

    cart = Cart(request)
    cart.add(wine, 2)
    for line in cart: line.wine, line.quantity, line.total
    cart.subtotal, cart.shipping, cart.total
"""

from dataclasses import dataclass
from decimal import Decimal
from functools import cached_property

from django.conf import settings

from catalog.models import Wine

from .pricing import ZERO, free_shipping_gap, round_money, shipping_for


@dataclass(frozen=True)
class CartLine:
    wine: Wine
    quantity: int

    @property
    def total(self) -> Decimal:
        return round_money(self.wine.price * self.quantity)

    @property
    def exceeds_stock(self) -> bool:
        return self.quantity > self.wine.stock


class Cart:
    SESSION_KEY = "cart"

    def __init__(self, request):
        self.session = request.session
        raw = self.session.get(self.SESSION_KEY, {})
        # Defensive: ignore anything in the session that isn't id → positive int.
        self._items: dict[str, int] = {
            str(key): int(value)
            for key, value in raw.items()
            if str(key).isdigit() and isinstance(value, int) and value > 0
        }

    # ── Changing the cart ────────────────────────────────────────────

    def add(self, wine: Wine, quantity: int = 1) -> int:
        """Add bottles; never more than stock allows. Returns the new quantity."""
        current = self._items.get(str(wine.pk), 0)
        return self.set(wine, current + quantity)

    def set(self, wine: Wine, quantity: int) -> int:
        """Set the exact quantity (0 removes the wine). Returns what was kept."""
        quantity = max(0, min(int(quantity), wine.max_orderable))
        if quantity:
            self._items[str(wine.pk)] = quantity
        else:
            self._items.pop(str(wine.pk), None)
        self._save()
        return quantity

    def remove(self, wine: Wine) -> None:
        self._items.pop(str(wine.pk), None)
        self._save()

    def clear(self) -> None:
        self._items = {}
        self.session.pop(self.SESSION_KEY, None)
        self.__dict__.pop("lines", None)

    def quantity_of(self, wine: Wine) -> int:
        return self._items.get(str(wine.pk), 0)

    def _save(self) -> None:
        self.session[self.SESSION_KEY] = dict(self._items)
        self.session.modified = True
        self.__dict__.pop("lines", None)  # recompute lines on next access

    # ── Reading the cart ─────────────────────────────────────────────

    @cached_property
    def lines(self) -> list[CartLine]:
        wines = Wine.objects.visible().select_related("winery").in_bulk([int(pk) for pk in self._items])
        lines = [CartLine(wines[int(pk)], qty) for pk, qty in self._items.items() if int(pk) in wines]
        if len(lines) != len(self._items):
            # A wine was hidden or deleted since it was added: drop it quietly.
            self._items = {str(line.wine.pk): line.quantity for line in lines}
            self.session[self.SESSION_KEY] = dict(self._items)
        return lines

    def __iter__(self):
        return iter(self.lines)

    def __len__(self) -> int:
        """Number of bottles (cheap: no database query)."""
        return sum(self._items.values())

    def __bool__(self) -> bool:
        return bool(self._items)

    @property
    def subtotal(self) -> Decimal:
        return round_money(sum((line.total for line in self.lines), ZERO))

    @property
    def shipping(self) -> Decimal:
        return shipping_for(self.subtotal)

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.shipping

    @property
    def free_shipping_gap(self) -> Decimal:
        return free_shipping_gap(self.subtotal)

    @property
    def free_shipping_threshold(self) -> Decimal:
        return settings.FREE_SHIPPING_THRESHOLD

    def stock_problems(self) -> list[CartLine]:
        """Lines asking for more bottles than we have right now."""
        return [line for line in self.lines if line.exceeds_stock]

    def fix_stock_problems(self) -> list[CartLine]:
        """Trim quantities down to what's in stock. Returns the lines changed."""
        problems = self.stock_problems()
        for line in problems:
            self.set(line.wine, line.wine.stock)
        return problems
