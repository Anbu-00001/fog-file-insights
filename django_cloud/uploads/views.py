import json
import logging
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import UploadRecord
from .serializers import UploadRecordSerializer

logger = logging.getLogger(__name__)

class IngestAPIView(APIView):
    """
    POST multipart/form-data:
      - file: uploaded file
      - summary: JSON string (optional)
      - client_id: optional
    Requires header X-FOG-TOKEN if settings.FOG_SHARED_TOKEN is set.
    """
    def post(self, request, *args, **kwargs):
        expected_token = settings.FOG_SHARED_TOKEN
        incoming_token = request.headers.get("X-FOG-TOKEN")

        if expected_token:
            if not incoming_token:
                return Response({"detail": "Missing fog token"}, status=401)
            if incoming_token != expected_token:
                return Response({"detail": "Invalid fog token"}, status=401)

        file_obj = request.FILES.get("file")
        if file_obj is None:
            logger.info("Ingest request missing file")
            return Response({"error": "Missing 'file' in form-data."}, status=status.HTTP_400_BAD_REQUEST)

        summary_str = request.data.get("summary", "{}")
        try:
            summary = json.loads(summary_str) if isinstance(summary_str, str) else summary_str
        except Exception:
            summary = {"parse_error": "summary is not valid json"}

        client_id = request.data.get("client_id", None)

        filename = file_obj.name
        save_path = f"uploads/{filename}"
        saved_path = default_storage.save(save_path, ContentFile(file_obj.read()))

        if getattr(settings, "USE_S3", False):
            try:
                s3_url = default_storage.url(saved_path)
            except Exception:
                s3_url = saved_path
            local_path = None
            forwarded = True
        else:
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

        logger.info("Ingest stored file=%s client=%s forwarded=%s record_id=%s", filename, client_id, forwarded, record.id)

        serializer = UploadRecordSerializer(record)
        return Response({"status": "stored", "record": serializer.data}, status=status.HTTP_201_CREATED)

from pathlib import Path
from django.shortcuts import render
from django.utils.timezone import localtime

def _count_files_in_dir(p: Path):
    if not p.exists() or not p.is_dir():
        return 0
    # count only files (ignore meta json if you want both)
    return sum(1 for _ in p.iterdir() if _.is_file())

def dashboard_view(request):
    """
    Renders a small dashboard summarizing cloud-side uploads and fog-side
    attempted uploads (by scanning fog_gateway directories).
    """
    # Cloud (Django) metrics
    total_received = UploadRecord.objects.count()
    last_uploads = UploadRecord.objects.order_by("-created_at")[:10]

    # compute simple averages from stored summary JSONs
    all_records = UploadRecord.objects.all()
    rows_list = []
    nulls_list = []
    for r in all_records:
        s = r.summary or {}
        rows = s.get("rows")
        if rows is not None:
            try:
                rows_list.append(int(rows))
            except Exception:
                pass
        null_pct = s.get("overall_null_pct")
        if null_pct is not None:
            try:
                nulls_list.append(float(null_pct))
            except Exception:
                pass

    avg_rows = round((sum(rows_list) / len(rows_list)) , 2) if rows_list else 0
    avg_null_pct = round((sum(nulls_list) / len(nulls_list)) * 100, 2) if nulls_list else 0

    # Fog folders (relative to repo root; adjust if your layout differs)
    # BASE_DIR in settings points to django_cloud folder; fog_gateway is parent/'fog_gateway'
    repo_root = Path(settings.BASE_DIR).parent
    fog_dir = repo_root / "fog_gateway"
    quarantined = fog_dir / "quarantined_files"
    pending = fog_dir / "pending_files"
    forwarded = fog_dir / "forwarded_files"

    quarantined_count = _count_files_in_dir(quarantined)
    pending_count = _count_files_in_dir(pending)
    forwarded_count = _count_files_in_dir(forwarded)

    total_attempts = forwarded_count + quarantined_count + pending_count
    # cloud_received = total_received
    forward_ratio = round((total_received / total_attempts) * 100, 2) if total_attempts > 0 else 100.0

    # Prepare table rows for template
    table_rows = []
    for rec in last_uploads:
        row = {
            "id": rec.id,
            "filename": rec.original_filename,
            "client_id": rec.client_id or "",
            "rows": (rec.summary.get("rows") if rec.summary else ""),
            "null_pct": (rec.summary.get("overall_null_pct") if rec.summary else ""),
            "stored": rec.s3_url or rec.local_path or "",
            "created_at": localtime(rec.created_at).strftime("%Y-%m-%d %H:%M:%S"),
        }
        table_rows.append(row)

    context = {
        "total_received": total_received,
        "forwarded_count": forwarded_count,
        "quarantined_count": quarantined_count,
        "pending_count": pending_count,
        "total_attempts": total_attempts,
        "forward_ratio": forward_ratio,
        "avg_rows": avg_rows,
        "avg_null_pct": avg_null_pct,
        "table_rows": table_rows,
    }
    return render(request, "uploads/dashboard.html", context)
