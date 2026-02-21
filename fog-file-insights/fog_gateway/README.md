# Fog Gateway

Edge-layer Flask service that receives CSV uploads, computes a quality summary, and decides whether to **forward** the file to the Django cloud backend or **quarantine** it locally.

## Quick Start

```bash
cd fog_gateway
pip install -r requirements.txt
python app.py
```

Or use the run script:

```bash
chmod +x scripts/run_fog.sh
bash scripts/run_fog.sh
```

## Endpoints

| Method | Path      | Description                          |
|--------|-----------|--------------------------------------|
| POST   | /upload   | Upload a CSV file for processing     |
| GET    | /health   | Health check with config summary     |

## Configuration

Edit `config.yaml` to change thresholds, forward URL, storage paths, etc.

## Testing

See `tests/test_fog_policy.md` for manual test cases.
