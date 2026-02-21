#!/bin/bash
# Simple run script for a local environment
set -e
BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE_DIR"

# optional: activate venv if you created one at repository root
if [ -f "../.venv/bin/activate" ]; then
  source ../.venv/bin/activate
fi

# install deps if missing (safe for dev)
pip install -r requirements.txt

# Create directories
python - <<'PY'
from utils import ensure_dirs
import os
base = os.path.abspath('.')
ensure_dirs(base, 'forwarded_files', 'quarantined_files', 'pending_files')
print("Directories ensured.")
PY

# run
python app.py
