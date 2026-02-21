from django.urls import path, include
from uploads.views import dashboard_view

urlpatterns = [
    path("api/", include("uploads.urls")),
    # Dashboard (simple HTML page)
    path("dashboard/", dashboard_view, name="dashboard"),
]
