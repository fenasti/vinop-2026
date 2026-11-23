from django.urls import path

from . import views, webhooks

app_name = "orders"

urlpatterns = [
    path("", views.checkout, name="checkout"),
    path("webhook/", webhooks.stripe_webhook, name="webhook"),
    path("<str:number>/pay/", views.pay, name="pay"),
    path("<str:number>/complete/", views.complete, name="complete"),
    path("<str:number>/thank-you/", views.confirmation, name="confirmation"),
]
