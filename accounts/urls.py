from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.overview, name="overview"),
    path("address/", views.address, name="address"),
    path("orders/", views.order_list, name="orders"),
    path("orders/<str:number>/", views.order_detail, name="order_detail"),
    path("delete/", views.delete_account, name="delete"),
]
