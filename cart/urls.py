from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_detail, name="detail"),
    path("add/<int:wine_id>/", views.add, name="add"),
    path("update/<int:wine_id>/", views.update, name="update"),
    path("remove/<int:wine_id>/", views.remove, name="remove"),
]
