# ── LOF Chiller Anomaly Detection — Docker Image (ONNX) ─────────────────────
# Build:  docker build -t lof-chiller:2.0 .
# Run:    docker run -p 8000:8000 lof-chiller:2.0

FROM python:3.11-slim

# Security: run as non-root user
RUN adduser --disabled-password --gecos "" appuser

WORKDIR /app

# Install dependencies first (layer-caches well on rebuilds)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ONNX model and application code
COPY model/lof_chiller_model.onnx ./model/
COPY app/main.py                  ./app/

# Hand ownership to non-root user
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
