from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    path("<slug:slug>/write/", views.write, name="write"),
    path("<int:pk>/delete/", views.delete, name="delete"),
]
