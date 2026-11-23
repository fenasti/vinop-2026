"""
Who can do what in the team area — the one place to read and change it.

A *role* is a Django Group. Each role grants a set of *areas*. A person can
hold several roles; they get every area those roles grant. Superusers
(created with `python manage.py createsuperuser`) can always do everything.

    Role            Areas
    ──────────────  ────────────────────────────────────────────────
    Shop Manager    everything, including team roles and legal pages
    Cellar Keeper   wines, wineries, regions, grapes, stock; reviews
    Fulfilment      orders and shipping
    Site Editor     the Studio (how the shop looks)

Give someone a role at /team/members/ (Shop Managers only), or from the
terminal:  python manage.py grant_role someone@example.com "Cellar Keeper"

The groups are created automatically after `migrate` (see team/apps.py),
so there is nothing to set up by hand and no Django admin is needed.
"""

from enum import StrEnum


class Area(StrEnum):
    CATALOG = "catalog"
    ORDERS = "orders"
    REVIEWS = "reviews"
    NEWSLETTER = "newsletter"
    STUDIO = "studio"
    PAGES = "pages"
    MEMBERS = "members"


SHOP_MANAGER = "Shop Manager"
CELLAR_KEEPER = "Cellar Keeper"
FULFILMENT = "Fulfilment"
SITE_EDITOR = "Site Editor"

ROLES: dict[str, frozenset[Area]] = {
    SHOP_MANAGER: frozenset(Area),
    CELLAR_KEEPER: frozenset({Area.CATALOG, Area.REVIEWS}),
    FULFILMENT: frozenset({Area.ORDERS}),
    SITE_EDITOR: frozenset({Area.STUDIO}),
}

ROLE_DESCRIPTIONS = {
    SHOP_MANAGER: "Everything, including who is on the team and the legal pages.",
    CELLAR_KEEPER: "Wines, wineries, regions, grapes and stock. Moderates reviews.",
    FULFILMENT: "Sees paid orders, prints the packing list and marks orders as shipped.",
    SITE_EDITOR: "Changes how the shop looks in the Studio. Nothing else.",
}


def areas_for(user) -> frozenset[Area]:
    """All areas a user may open. Cached on the user object for the request."""
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return frozenset()
    if user.is_superuser:
        return frozenset(Area)
    cached = getattr(user, "_team_areas", None)
    if cached is None:
        role_names = user.groups.filter(name__in=ROLES).values_list("name", flat=True)
        cached = frozenset().union(*(ROLES[name] for name in role_names))
        user._team_areas = cached
    return cached


def can(user, area: Area | str) -> bool:
    return Area(area) in areas_for(user)


def is_team_member(user) -> bool:
    return bool(areas_for(user))


def roles_of(user) -> list[str]:
    return list(user.groups.filter(name__in=ROLES).values_list("name", flat=True))
