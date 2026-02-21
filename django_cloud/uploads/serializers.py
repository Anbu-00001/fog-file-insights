from rest_framework import serializers
from .models import UploadRecord

class UploadRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadRecord
        fields = "__all__"
        read_only_fields = ("id", "created_at",)
