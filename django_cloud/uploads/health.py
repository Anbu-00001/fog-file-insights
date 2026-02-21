from rest_framework.response import Response
from rest_framework.views import APIView
from django.conf import settings

class HealthCheckAPIView(APIView):
    def get(self, request):
        return Response({
            "status": "ok",
            "debug": settings.DEBUG,
            "use_s3": getattr(settings, "USE_S3", False),
            "storage_backend": settings.DEFAULT_FILE_STORAGE
        })
