from django.core.management.base import BaseCommand
from uploads.models import UploadRecord
from django.conf import settings
import os

class Command(BaseCommand):
    help = "Run basic self verification tests"

    def handle(self, *args, **kwargs):
        self.stdout.write("Running self test...\n")

        # Check DB connectivity
        count = UploadRecord.objects.count()
        self.stdout.write(f"✔ Database connected. Records count: {count}")

        # Check media folder exists
        media_root = settings.MEDIA_ROOT
        if os.path.exists(media_root):
            self.stdout.write(f"✔ Media folder exists at: {media_root}")
        else:
            self.stdout.write("✘ Media folder missing")

        # Check storage backend
        self.stdout.write(f"✔ Storage backend: {settings.DEFAULT_FILE_STORAGE}")

        self.stdout.write("\nSelf test complete.")
