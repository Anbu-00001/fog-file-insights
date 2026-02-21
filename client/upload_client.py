import json
import requests
import time
from pathlib import Path

DJANGO_INGEST_URL = "http://localhost:8000/api/ingest/"

def send_file(path: str, client_id: str = "client-local"):
    path = Path(path)
    files = {"file": (path.name, open(path, "rb"))}
    summary = {
        "client_ts": time.time(),
        "note": "sample upload from local client for Day 1 testing"
    }
    data = {"summary": json.dumps(summary), "client_id": client_id}
    r = requests.post(DJANGO_INGEST_URL, files=files, data=data)
    try:
        print("status", r.status_code, r.json())
    except Exception:
        print("status", r.status_code, r.text)

if __name__ == "__main__":
    send_file("client/sample_files/sample_small.csv")
