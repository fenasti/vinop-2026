from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.wine_list, name="list"),
    path("<slug:slug>/", views.wine_detail, name="detail"),
]
