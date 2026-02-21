import os
import uuid
import json
import time
import logging
from pathlib import Path

log = logging.getLogger(__name__)

def ensure_dirs(base: str, *names):
    basep = Path(base)
    basep.mkdir(parents=True, exist_ok=True)
    for n in names:
        (basep / n).mkdir(parents=True, exist_ok=True)

def save_bytes_to_file(base_dir: str, subdir: str, filename: str, data: bytes) -> str:
    """
    Save bytes to a uniquely named file under base_dir/subdir.
    Returns the absolute path to saved file.
    """
    target_dir = Path(base_dir) / subdir
    target_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{int(time.time())}-{uuid.uuid4().hex}-{filename}"
    path = target_dir / safe_name
    with open(path, "wb") as f:
        f.write(data)
    log.info("Saved file to %s", path)
    return str(path)

def write_json(path: str, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
