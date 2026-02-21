import os
import io
import time
import yaml
import json
import logging
import threading
import requests
import pandas as pd
from flask import Flask, request, jsonify
from utils import ensure_dirs, save_bytes_to_file, write_json

# structured logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
log = logging.getLogger("fog_gateway")

# --- load config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(BASE_DIR, "config.yaml")
with open(CFG_PATH, "r", encoding="utf-8") as f:
    cfg = yaml.safe_load(f)

HOST = cfg["server"].get("host", "0.0.0.0")
PORT = cfg["server"].get("port", 5000)

# policy
NULL_THRESHOLD = float(cfg["policy"].get("null_pct_threshold", 0.3))
MIN_ROWS = int(cfg["policy"].get("min_rows", 1))

# forward
FORWARD_URL = cfg["forward"].get("url", "http://localhost:8000/api/ingest/")
TIMEOUT = int(cfg["forward"].get("timeout_seconds", 10))
MAX_RETRIES = int(cfg["forward"].get("max_retries", 3))
BACKOFF = int(cfg["forward"].get("retry_backoff_seconds", 2))

# auth
AUTH_TOKEN = cfg.get("auth", {}).get("fog_token", "")

# retry worker
RETRY_INTERVAL = int(cfg.get("retry", {}).get("retry_interval_seconds", 20))
MAX_PENDING_ATTEMPTS = int(cfg.get("retry", {}).get("max_pending_attempts", 10))

# storage
FORWARDED_DIR = os.path.join(BASE_DIR, cfg["storage"].get("forwarded_dir", "forwarded_files"))
QUARANTINE_DIR = os.path.join(BASE_DIR, cfg["storage"].get("quarantine_dir", "quarantined_files"))
PENDING_DIR = os.path.join(BASE_DIR, cfg["storage"].get("pending_dir", "pending_files"))
MAX_UPLOAD_BYTES = int(cfg["storage"].get("max_upload_size_bytes", 5 * 1024 * 1024))

ensure_dirs(BASE_DIR, os.path.basename(FORWARDED_DIR), os.path.basename(QUARANTINE_DIR), os.path.basename(PENDING_DIR))

app = Flask(__name__)

def compute_csv_summary(file_bytes: bytes):
    try:
        bio = io.BytesIO(file_bytes)
        df = pd.read_csv(bio)
    except Exception as e:
        log.exception("Failed to parse CSV")
        return None, f"CSV parse error: {str(e)}"

    rows = int(len(df))
    cols = list(df.columns)
    null_pct_per_col = (df.isna().mean() * 100).round(2).to_dict()
    overall_null_pct = float(df.isna().mean().mean())
    numeric_stats = {}
    try:
        numeric_stats = df.select_dtypes(include=["number"]).describe().to_dict()
    except Exception:
        numeric_stats = {}

    sample_row = df.head(1).to_dict(orient="records")
    summary = {
        "rows": rows,
        "columns": cols,
        "null_pct_per_col": null_pct_per_col,
        "overall_null_pct": round(overall_null_pct, 4),
        "numeric_stats": numeric_stats,
        "sample_row": sample_row
    }
    return summary, None

def should_forward(summary: dict):
    if summary is None:
        return False, "no_summary"
    if summary.get("rows", 0) < MIN_ROWS:
        return False, "insufficient_rows"
    if summary.get("overall_null_pct", 1.0) >= NULL_THRESHOLD:
        return False, "high_null_pct"
    return True, None

def forward_to_cloud(file_bytes: bytes, filename: str, summary: dict, client_id: str = None):
    """
    Attempt to POST multipart to Django /api/ingest/.
    Sends X-FOG-TOKEN header when configured.
    """
    files = {"file": (filename, io.BytesIO(file_bytes))}
    data = {"summary": json.dumps(summary)}
    if client_id:
        data["client_id"] = client_id

    headers = {}
    if AUTH_TOKEN:
        headers["X-FOG-TOKEN"] = AUTH_TOKEN

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log.info("Forwarding attempt %d to %s", attempt, FORWARD_URL)
            resp = requests.post(FORWARD_URL, files=files, data=data, headers=headers, timeout=TIMEOUT)
            if resp.status_code in (200, 201):
                try:
                    log.info("Forward success filename=%s status=%s", filename, resp.status_code)
                    return True, resp.json()
                except Exception:
                    return True, {"status": "stored", "raw_response": resp.text}
            else:
                log.warning("Forward failed status=%s body=%s", resp.status_code, resp.text)
                last_error = f"status={resp.status_code} body={resp.text}"
        except Exception as e:
            log.exception("Exception while forwarding")
            last_error = str(e)
        time.sleep(BACKOFF * attempt)
    log.error("Final forward failure for %s: %s", filename, last_error)
    return False, last_error

def _attempt_forward_pending_file(path: str):
    """
    Attempt to forward a single pending file and move it on success.
    Returns True if forwarded successfully, False otherwise.
    """
    try:
        with open(path, "rb") as f:
            data = f.read()
        filename = os.path.basename(path)
        # read attempt count meta if exists
        meta_path = f"{path}.meta.json"
        attempts = 0
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as mm:
                    meta = json.load(mm)
                    attempts = meta.get("attempts", 0)
            except Exception:
                attempts = 0

        if attempts >= MAX_PENDING_ATTEMPTS:
            log.warning("Pending file %s exceeded max attempts (%d). Moving to quarantine.", path, attempts)
            # move to quarantine
            qpath = save_bytes_to_file(BASE_DIR, os.path.basename(QUARANTINE_DIR), filename, data)
            write_json(f"{qpath}.meta.json", {"reason": "max_attempts_exceeded", "original_pending": path})
            # remove original pending file and meta
            try:
                os.remove(path)
                if os.path.exists(meta_path):
                    os.remove(meta_path)
            except Exception:
                pass
            return False

        ok, resp_or_err = forward_to_cloud(data, filename, {}, client_id=None)
        if ok:
            # move to forwarded dir and write meta
            fpath = save_bytes_to_file(BASE_DIR, os.path.basename(FORWARDED_DIR), filename, data)
            write_json(f"{fpath}.meta.json", {"forwarded_response": resp_or_err})
            # remove pending and its meta
            try:
                os.remove(path)
                if os.path.exists(meta_path):
                    os.remove(meta_path)
            except Exception:
                pass
            log.info("Pending file forwarded and moved: %s -> %s", path, fpath)
            return True
        else:
            # increment attempts in meta
            attempts += 1
            write_json(meta_path, {"attempts": attempts, "last_error": str(resp_or_err)})
            log.info("Pending file %s forward failed (attempts=%d)", path, attempts)
            return False
    except Exception:
        log.exception("Error processing pending file %s", path)
        return False

def retry_pending_loop():
    """
    Background worker that periodically retries pending files.
    """
    log.info("Starting retry_pending_loop every %s seconds", RETRY_INTERVAL)
    while True:
        try:
            files = sorted([
                os.path.join(PENDING_DIR, f) for f in os.listdir(PENDING_DIR)
                if os.path.isfile(os.path.join(PENDING_DIR, f)) and not f.endswith(".meta.json")
            ])
            if files:
                log.info("Retry worker found %d pending files", len(files))
            for p in files:
                _attempt_forward_pending_file(p)
        except Exception:
            log.exception("Retry loop error")
        time.sleep(RETRY_INTERVAL)

@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "missing file"}), 400

    file_obj = request.files["file"]
    filename = file_obj.filename or "upload.csv"
    client_id = request.form.get("client_id", None)

    file_obj.stream.seek(0, os.SEEK_END)
    size = file_obj.stream.tell()
    file_obj.stream.seek(0)
    if size > MAX_UPLOAD_BYTES:
        return jsonify({"status": "rejected", "reason": "file_too_large", "max_bytes": MAX_UPLOAD_BYTES}), 413

    file_bytes = file_obj.read()
    log.info("Received file %s (%d bytes) client=%s", filename, len(file_bytes), client_id)

    summary, err = compute_csv_summary(file_bytes)
    if err:
        path = save_bytes_to_file(BASE_DIR, os.path.basename(QUARANTINE_DIR), filename, file_bytes)
        meta = {"reason": "parse_error", "error": err, "quarantine_path": path}
        write_json(f"{path}.meta.json", meta)
        log.info("File quarantined (parse error): %s", filename)
        return jsonify({"status": "quarantined", "reason": "parse_error", "error": err}), 400

    forward_decision, reason = should_forward(summary)
    if not forward_decision:
        path = save_bytes_to_file(BASE_DIR, os.path.basename(QUARANTINE_DIR), filename, file_bytes)
        meta = {"reason": reason, "summary": summary, "quarantine_path": path}
        write_json(f"{path}.meta.json", meta)
        log.info("File quarantined by policy: %s reason=%s", filename, reason)
        return jsonify({"status": "quarantined", "reason": reason, "summary": summary}), 200

    forwarded_path = save_bytes_to_file(BASE_DIR, os.path.basename(FORWARDED_DIR), filename, file_bytes)
    ok, resp_or_err = forward_to_cloud(file_bytes, filename, summary, client_id=client_id)
    if ok:
        meta = {"forwarded_response": resp_or_err, "summary": summary, "forwarded_path": forwarded_path}
        write_json(f"{forwarded_path}.meta.json", meta)
        log.info("File forwarded: %s", filename)
        return jsonify({"status": "forwarded", "summary": summary, "cloud_response": resp_or_err}), 201
    else:
        pending_path = save_bytes_to_file(BASE_DIR, os.path.basename(PENDING_DIR), filename, file_bytes)
        # write meta with attempts=1
        write_json(f"{pending_path}.meta.json", {"attempts": 1, "last_error": str(resp_or_err)})
        meta = {"error": resp_or_err, "summary": summary, "pending_path": pending_path}
        log.warning("Forward failed; saved to pending: %s error=%s", filename, resp_or_err)
        return jsonify({"status": "pending", "reason": "forward_failed", "error": resp_or_err}), 202

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "null_threshold": NULL_THRESHOLD,
        "min_rows": MIN_ROWS,
        "forward_url": FORWARD_URL,
        "auth_token_set": bool(AUTH_TOKEN)
    })

if __name__ == "__main__":
    # spawn retry worker
    t = threading.Thread(target=retry_pending_loop, daemon=True)
    t.start()

    log.info("Starting Fog Gateway on %s:%s", HOST, PORT)
    app.run(host=HOST, port=PORT)
