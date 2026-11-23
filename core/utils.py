from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme


def redirect_back(request, fallback, field: str = "next"):
    """
    Redirect to the URL in POST[field] if it points to our own site,
    otherwise to `fallback` (a URL name or path). Stops forms being abused
    to bounce visitors to other websites ("open redirect").
    """
    target = request.POST.get(field, "")
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(target)
    return redirect(fallback)
