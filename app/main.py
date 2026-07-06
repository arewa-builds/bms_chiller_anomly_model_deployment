"""
LOF Chiller Anomaly Detection — FastAPI Inference Server (ONNX)
===============================================================
Exposes three endpoints:
  POST /predict        → label (+1 normal / -1 anomaly) per sample
  POST /predict/batch  → score multiple readings at once
  GET  /health         → liveness check + model metadata
"""

import time
import numpy as np
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
import onnxruntime as rt

# ---------------------------------------------------------------------------
# Load ONNX model once at startup
# ---------------------------------------------------------------------------
MODEL_PATH = Path(__file__).parent.parent / "model" / "lof_chiller_model.onnx"
session    = rt.InferenceSession(str(MODEL_PATH))

INPUT_NAME  = session.get_inputs()[0].name          # "float_input"
N_FEATURES  = session.get_inputs()[0].shape[1]      # 197

app = FastAPI(
    title="LOF Chiller Anomaly Detection API",
    version="2.0.0",
    description="Real-time anomaly scoring for BMS chiller sensor data (ONNX Runtime)",
)

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------
class SensorPayload(BaseModel):
    """A single sensor reading — exactly 197 float values."""
    features: list[float]

    @field_validator("features")
    @classmethod
    def check_length(cls, v):
        if len(v) != N_FEATURES:
            raise ValueError(f"Expected {N_FEATURES} features, got {len(v)}")
        return v


class BatchPayload(BaseModel):
    """Multiple sensor readings submitted together."""
    samples: list[SensorPayload]


class PredictResponse(BaseModel):
    label: int            # +1 = normal, -1 = anomaly
    decision_score: float # positive = normal, negative = anomaly
    is_anomaly: bool
    inference_ms: float


class BatchPredictResponse(BaseModel):
    results: list[PredictResponse]
    total_inference_ms: float


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def run_inference(X: np.ndarray):
    """Run ONNX session and return (labels, scores)."""
    X_f32 = X.astype(np.float32)
    label, scores, _ = session.run(
        ["label", "scores", "score_samples"],
        {INPUT_NAME: X_f32}
    )
    return label.flatten(), scores.flatten()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": "LOF Chiller v2.0 (ONNX)",
        "n_features": N_FEATURES,
        "decision_threshold": 0.0,
        "model_file": "lof_chiller_model.onnx",
    }


@app.post("/predict", response_model=PredictResponse)
def predict(payload: SensorPayload):
    """Score a single sensor reading."""
    t0 = time.perf_counter()
    try:
        X = np.array([payload.features])
        labels, scores = run_inference(X)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    elapsed_ms = (time.perf_counter() - t0) * 1000

    return PredictResponse(
        label=int(labels[0]),
        decision_score=round(float(scores[0]), 6),
        is_anomaly=(int(labels[0]) == -1),
        inference_ms=round(elapsed_ms, 3),
    )


@app.post("/predict/batch", response_model=BatchPredictResponse)
def predict_batch(payload: BatchPayload):
    """Score multiple sensor readings in one call."""
    t0 = time.perf_counter()
    try:
        X = np.array([s.features for s in payload.samples])
        labels, scores = run_inference(X)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    total_ms = (time.perf_counter() - t0) * 1000

    results = [
        PredictResponse(
            label=int(labels[i]),
            decision_score=round(float(scores[i]), 6),
            is_anomaly=(int(labels[i]) == -1),
            inference_ms=round(total_ms / len(payload.samples), 3),
        )
        for i in range(len(payload.samples))
    ]
    return BatchPredictResponse(results=results, total_inference_ms=round(total_ms, 3))
