from .permissions import Area, areas_for

# URL name prefix → team navigation item, e.g. "wine_edit" → "wines".
SECTIONS = {
    "wine": "wines",
    "winery": "wineries",
    "region": "regions",
    "grape": "grapes",
    "order": "orders",
    "packing": "orders",
    "review": "reviews",
    "subscriber": "subscribers",
    "page": "pages",
    "member": "members",
}


def team(request):
    """
    `team_areas` in every template, e.g. {% if "orders" in team_areas %}.
    Empty for customers, so the header only shows "Team area" to the team.
    `team_section` tells the team navigation which item is open.
    """
    user = getattr(request, "user", None)
    areas = areas_for(user) if user else frozenset()

    section = ""
    match = getattr(request, "resolver_match", None)
    if match and match.namespace == "team":
        prefix = match.url_name.split("_")[0]
        section = SECTIONS.get(prefix, prefix)

    return {"team_areas": {str(area) for area in areas}, "team_section": section, "Area": Area}
