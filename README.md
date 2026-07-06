# LOF Chiller Anomaly Detection — Deployment Package

## Folder structure

```
lof_deployment/
├── model/
│   └── lof_chiller_model.onnx    ← Trained model in ONNX format
├── app/
│   ├── main.py                   ← FastAPI inference server
│   └── opcua_bridge.py           ← OPC-UA → API bridge (configure before use)
├── Dockerfile                    ← Container recipe
├── docker-compose.yml            ← Runs inference + bridge together
├── requirements.txt              ← Python packages
└── README.md                     ← This file
```

---

## How to build and run

### Step 1 — Build the container
```bash
docker build -t lof-chiller:2.0 .
```

### Step 2 — Run the inference server
```bash
docker run -p 8000:8000 lof-chiller:2.0
```

### Step 3 — Confirm it is running
```bash
curl http://localhost:8000/health
```

### Step 4 — Send a test sensor reading
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [0.0, 0.0, ...]}'   # 197 values
```

---

## API endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Confirm server is running |
| `/predict` | POST | Score one sensor reading |
| `/predict/batch` | POST | Score multiple readings at once |

### Response from `/predict`
```json
{
  "label": 1,
  "decision_score": 1.587,
  "is_anomaly": false,
  "inference_ms": 6.6
}
```
`label` is `+1` for normal, `-1` for anomaly. `decision_score` above 0 is normal.

---

## Model facts

| Property | Value |
|---|---|
| Algorithm | Local Outlier Factor |
| Format | ONNX (Runtime 1.18) |
| Input features | 197 sensor channels |
| Training samples | 2,754 |
| k-neighbors | 20 |
| Contamination | 0.7% |
| Avg inference latency | ~6.6 ms |

---

## Before connecting to OPC-UA

Open `app/opcua_bridge.py` and fill in:
1. `OPC_SERVER_URL` — IP address and port of your BMS OPC-UA server
2. `NODE_IDS` — the 197 OPC-UA node IDs in the same order the model was trained on
3. `preprocess()` — apply the same scaling used during training

Then run both containers together:
```bash
docker compose up --build
```
