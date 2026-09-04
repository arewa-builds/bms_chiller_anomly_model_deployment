# LOF Chiller Anomaly Detection — Agent Instructions

## Project overview

Production deployment package for BMS chiller anomaly detection. The system reads 16 raw sensor values from an OPC UA server, engineers 197 features via a stateful preprocessor, and scores them with a Local Outlier Factor model exported to ONNX.

**Current project phase:** Week 8 of 12 — deployment and integration.

## Architecture

```
OPC UA Server (BMS)
       ↓
app/opcua_bridge.py   ← asyncua client, 30-min poll
       ↓
app/preprocessor.py   ← ChillerPreprocessor (197 features + scaler)
       ↓
app/main.py           ← FastAPI + ONNX Runtime (/predict)
       ↓
Alerting / Dashboard / Historian (future)
```

## Setup commands

```bash
# Build and run inference API only
docker build -t lof-chiller:2.0 .
docker run -p 8000:8000 lof-chiller:2.0

# Run full stack (inference + OPC-UA bridge)
docker compose up --build
```

## Health check

```bash
curl http://localhost:8000/health
```

## Before connecting to OPC UA

1. Set `OPC_SERVER_URL` in `app/opcua_bridge.py` or `docker-compose.yml`.
2. Fill in all 16 entries in `NODE_MAP` with live BMS node IDs.
3. Mount `model/scaler.pkl` from training artifacts.
4. Extend `handle_anomaly()` for your notification channel.

## Key conventions

- **OPC UA client:** `asyncua` only — no synchronous opcua clients.
- **Sensor names:** Must match `RAW_SENSOR_COLS` / `NODE_MAP` keys exactly.
- **Feature order:** `FEATURE_ORDER` in `app/preprocessor.py` must match training.
- **Poll interval:** 30 minutes (`POLL_INTERVAL_S = 1800`).
- **Warm-up:** 48 readings (24 h) required before first inference.
- **Units:** Temperatures in °F, RLA in %, flow in gal/min — must match training data.

## Model facts

| Property | Value |
|----------|-------|
| Algorithm | Local Outlier Factor |
| Format | ONNX (Runtime 1.18) |
| Input features | 197 |
| Decision threshold | 0.0 (positive score = normal) |
| Label | +1 normal, -1 anomaly |

## Custom agents

| Agent | Invoke | Purpose |
|-------|--------|---------|
| `opcua-expert` | `/opcua-expert` | OPC UA, ONNX deployment, BMS integration specialist |

## Testing inference manually

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [0.0, 0.0, ...]}'   # exactly 197 float values
```

## Security

- Do not commit OPC UA certificates, private keys, or production credentials.
- Use environment variables or mounted secrets for sensitive configuration.
- Prefer SignAndEncrypt security policies in production OPC UA connections.
