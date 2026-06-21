from django.urls import path

from . import views

app_name = "licensing"

urlpatterns = [
    path("expired/", views.license_expired, name="license_expired"),
    path("activate/", views.license_activate, name="license_activate"),
]
