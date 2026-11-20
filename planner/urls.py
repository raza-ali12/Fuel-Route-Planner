from django.urls import path

from planner import views

urlpatterns = [
    path("", views.map_view, name="map"),
    path("map/", views.map_view, name="map-page"),
    path("api/route", views.RouteView.as_view(), name="api-route"),
    path("api/route/", views.RouteView.as_view(), name="api-route-slash"),
    path("api/places", views.PlacesView.as_view(), name="api-places"),
    path("api/places/", views.PlacesView.as_view(), name="api-places-slash"),
]
