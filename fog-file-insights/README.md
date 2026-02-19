# Fog-File-Insights — Day 1 (Django ingest baseline)

This Day 1 scaffold runs a Django backend locally and exposes `POST /api/ingest/` to accept `file` + `summary` and store the file locally (MEDIA_ROOT/uploads/...). S3 is toggle-able via env `USE_S3`.

## Quick steps (Linux / mac / WSL)
1. Create & activate venv:

```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r django_cloud/requirements.txt
```

3. Copy `.env.example` to `.env` and edit if desired (optional).
4. Run migrations & server:

```bash
cd django_cloud
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

5. Test with client:

```bash
pip install -r client/requirements.txt
python client/upload_client.py
```

6. Inspect saved file under `django_cloud/media/uploads/` and check the API response printed by client.

## Notes
- To enable S3 later, set `USE_S3=1` and fill AWS_* env vars (Day 2).
- This step intentionally stores files locally to let you test quickly before cloud deployment.


The fog layer performs structural parsing, schema validation, and statistical sanity checks. Files that fail parsing, violate expected schema, or exceed configurable anomaly thresholds are quarantined locally and not forwarded to the cloud.