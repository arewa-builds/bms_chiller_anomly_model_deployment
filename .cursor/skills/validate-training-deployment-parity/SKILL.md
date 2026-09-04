---
name: validate-training-deployment-parity
description: Verify feature engineering and ONNX inference match the training pipeline. Use when scores look wrong, anomalies are missed, or debugging model vs data issues during deployment.
paths: app/preprocessor.py,app/main.py,app/opcua_bridge.py
---

# Validate Training = Deployment Parity

Before assuming the ONNX model is wrong, prove the deployment pipeline reproduces training numerically.

## Checklist

### 1. Feature count and order

- Confirm `len(FEATURE_ORDER) == 197` in `app/preprocessor.py`
- Confirm ONNX input shape is `(1, 197)` via `/health` or session metadata
- Compare `FEATURE_ORDER` against the training notebook export — byte-for-byte if possible

### 2. Hyperparameter alignment

These constants in `app/preprocessor.py` must match training `CONFIG`:

| Constant | Value | Meaning |
|----------|-------|---------|
| `WIN_SHORT` | 4 | 2 h rolling window |
| `WIN_LONG` | 48 | 24 h rolling window |
| `EWMA_SPAN` | 8 | ~4 h EWMA |
| `W3D` | 144 | 3-day trend |
| `W7D` | 336 | 7-day trend |
| `SMOOTH_WIN` | 5 | Median smoothing |
| `RLA_ON_THR` | 5.0 | Chiller ON threshold |

### 3. Scaler parity

- Use the exact `scaler.pkl` from training artifacts — not a re-fit
- Scaler type: `RobustScaler` applied in `ChillerPreprocessor.get_feature_vector()`
- Compare scaled output for a known training row: max absolute diff should be < 1e-5

### 4. Raw sensor parity

- Same 16 sensors, same units, same poll interval (30 min)
- Timestamp timezone: UTC throughout

### 5. ONNX runtime parity

- Same `onnxruntime` version as export (1.18.0)
- Input dtype `float32`
- Compare `label` and `scores` for a fixed feature vector against training notebook inference

### 6. Operational state handling

- Startup counter (`readings_since_start`) logic must match training OFF/TRANSIENT/STEADY handling
- RLA_ON_THR transition detection must match training

## Parity test procedure

1. Export one historical row (raw sensors + timestamp) from training data.
2. Feed through `ChillerPreprocessor` with sufficient prior history loaded.
3. POST resulting features to `/predict`.
4. Compare `decision_score` to training notebook score for same row.
5. If mismatch: bisect — raw → engineered → scaled → ONNX — to find the diverging step.

## Decision guide

| Symptom | Likely cause |
|---------|--------------|
| All scores near zero | Scaler missing or wrong scaler file |
| Random anomalies | Feature order mismatch |
| Consistent offset | Unit conversion (°C vs °F) |
| Delayed anomalies | Warm-up buffer not filled |
| Works in notebook, fails live | OPC UA tag mapping or timestamp drift |
