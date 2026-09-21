from django.urls import path

from . import views

app_name = "flights"

urlpatterns = [
    path("", views.search, name="search"),
    path("locations/", views.location_lookup, name="location_lookup"),
]
