"""
Top-level URL map. Each app owns its own urls.py and a namespace, so
templates always say e.g. {% url 'catalog:detail' wine.slug %}.

There is deliberately no /admin/: the team area at /team/ replaces it.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    path("", include("core.urls")),
    path("wines/", include("catalog.urls")),
    path("cart/", include("cart.urls")),
    path("checkout/", include("orders.urls")),
    path("accounts/", include("allauth.urls")),  # login, signup, password reset…
    path("profile/", include("accounts.urls")),
    path("wishlist/", include("wishlist.urls")),
    path("reviews/", include("reviews.urls")),
    path("newsletter/", include("newsletter.urls")),
    path("team/", include("team.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Error pages: Django's built-in handlers render templates/400.html,
# 403.html, 404.html and 500.html automatically (only with DEBUG=False).
# 500.html is self-contained on purpose: when the server fails we can't
# count on the database or context processors still working.
