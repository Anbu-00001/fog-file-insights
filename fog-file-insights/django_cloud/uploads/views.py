import json
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import UploadRecord
from .serializers import UploadRecordSerializer

class IngestAPIView(APIView):
    """
    POST multipart/form-data:
      - file: uploaded file
      - summary: JSON string (optional)
      - client_id: optional
    """
    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get("file")
        if file_obj is None:
            return Response({"error": "Missing 'file' in form-data."}, status=status.HTTP_400_BAD_REQUEST)

        summary_str = request.data.get("summary", "{}")
        try:
            summary = json.loads(summary_str) if isinstance(summary_str, str) else summary_str
        except Exception:
            summary = {"parse_error": "summary is not valid json"}

        client_id = request.data.get("client_id", None)

        # Save file using default_storage (local or S3 depending on config)
        filename = file_obj.name
        # prefix with uploads/
        save_path = f"uploads/{filename}"
        saved_path = default_storage.save(save_path, ContentFile(file_obj.read()))

        # build s3_url or local path info
        if getattr(settings, "USE_S3", False):
            # when using S3Boto3Storage, the default_storage.url returns the S3 public URL (if configured)
            try:
                s3_url = default_storage.url(saved_path)
            except Exception:
                s3_url = saved_path
            local_path = None
            forwarded = True
        else:
            # local file saved to MEDIA_ROOT/uploads/...
            local_path = os.path.join(settings.MEDIA_ROOT, saved_path)
            s3_url = None
            forwarded = False

        record = UploadRecord.objects.create(
            client_id=client_id,
            original_filename=filename,
            summary=summary,
            s3_url=s3_url,
            local_path=local_path,
            forwarded=forwarded,
        )

        serializer = UploadRecordSerializer(record)
        return Response({"status": "stored", "record": serializer.data}, status=status.HTTP_201_CREATED)
