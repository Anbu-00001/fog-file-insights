from django.urls import path
from .views import IngestAPIView, dashboard_view
from .health import HealthCheckAPIView

urlpatterns = [
    path("ingest/", IngestAPIView.as_view(), name="ingest"),
    path("health/", HealthCheckAPIView.as_view(), name="health"),
    # NOTE: dashboard route is registered globally in project/urls.py as /dashboard/
]
