#!/bin/bash
# 1️⃣ Activate virtual environment
cd /home/anbu/25_class/Sem_4/hackathons/Fog_project
source .venv/bin/activate

# 2️⃣ Kill any running Django (if exists)
pkill -f "manage.py runserver" || true

# 3️⃣ Ensure Fog is running (start in background if not)
cd fog-file-insights/fog_gateway
pkill -f "app.py" || true
nohup python app.py > fog.log 2>&1 &

sleep 2

# 4️⃣ Stop Django completely to simulate cloud failure
pkill -f "manage.py runserver" || true

# 5️⃣ Trigger upload while Django is DOWN (should go pending)
curl -X POST http://localhost:5000/upload \
  -F "file=@sample_inputs/sample_good.csv" \
  -F "client_id=resilience_test"

echo ""
echo "---- File should now be PENDING ----"

# 6️⃣ Start Django again
cd ../django_cloud
nohup python manage.py runserver > django.log 2>&1 &

sleep 3

echo "---- Waiting for retry worker (20 seconds) ----"
sleep 25

echo "---- Checking fog logs for retry success ----"
tail -n 20 ../fog_gateway/fog.log

echo "---- Checking Django DB count ----"
python manage.py shell -c "from uploads.models import UploadRecord; print('UploadRecord count =', UploadRecord.objects.count())"

echo "---- RESILIENCE TEST COMPLETE ----"
