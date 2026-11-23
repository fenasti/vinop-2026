from django.urls import path

from . import views

app_name = "wishlist"

urlpatterns = [
    path("", views.wishlist, name="list"),
    path("toggle/<int:wine_id>/", views.toggle, name="toggle"),
]
