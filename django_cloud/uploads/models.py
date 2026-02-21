from django.db import models

class UploadRecord(models.Model):
    client_id = models.CharField(max_length=128, blank=True, null=True)
    original_filename = models.CharField(max_length=512)
    summary = models.JSONField(default=dict, blank=True)
    s3_url = models.CharField(max_length=1024, blank=True, null=True)
    local_path = models.CharField(max_length=1024, blank=True, null=True)
    forwarded = models.BooleanField(default=False)  # if forwarded from fog (later)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"UploadRecord(id={self.id}, file={self.original_filename})"
