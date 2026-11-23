"""
Who may look at an order page.

The first VinOp showed any order to anyone who knew its number. Now an
order is visible to:
  * the logged-in customer who placed it,
  * the browser session that placed it (guest checkout),
  * team members who handle orders.
"""

from team.permissions import Area, can

SESSION_KEY = "order_access"
PENDING_KEY = "checkout_order"


def grant(request, order) -> None:
    numbers = request.session.get(SESSION_KEY, [])
    if order.number not in numbers:
        request.session[SESSION_KEY] = [*numbers[-19:], order.number]


def can_view(request, order) -> bool:
    if request.user.is_authenticated and order.user_id == request.user.pk:
        return True
    if order.number in request.session.get(SESSION_KEY, []):
        return True
    return can(request.user, Area.ORDERS)
