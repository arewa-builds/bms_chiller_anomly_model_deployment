"""
OPC-UA → LOF Inference Bridge
============================
Reads 16 raw sensor values from a local OPC-UA server every 30 minutes,
computes the engineered feature vector with ChillerPreprocessor, and posts
the result to the LOF inference endpoint.

Typical local deployment:
  - OPC server is running on the same machine as this script
  - OPC server requires username/password authentication
  - OPC server uses SignAndEncrypt security

Configuration can be supplied with environment variables or edited below.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from asyncua import Client

from preprocessor import ChillerPreprocessor

# ── Configuration ─────────────────────────────────────────────────────────────

OPC_SERVER_URL = os.getenv("OPC_SERVER_URL", "opc.tcp://127.0.0.1:4840")
OPC_USERNAME = os.getenv("OPC_USERNAME", "")
OPC_PASSWORD = os.getenv("OPC_PASSWORD", "")
OPC_SECURITY_POLICY = os.getenv("OPC_SECURITY_POLICY", "Basic256Sha256")
OPC_SECURITY_MODE = os.getenv("OPC_SECURITY_MODE", "SignAndEncrypt")
INFERENCE_URL = os.getenv("INFERENCE_URL", "http://127.0.0.1:8000/predict")
SCALER_PATH = os.getenv("SCALER_PATH", str(Path(__file__).resolve().parent.parent / "model" / "scaler_model.onnx"))
POLL_INTERVAL_S = int(os.getenv("POLL_INTERVAL_S", "1800"))

# Map each canonical sensor name to its OPC-UA node ID.
# Replace the placeholder node IDs with the values from your OPC server.
NODE_MAP: dict[str, str] = {
    "CHW_Return": "ns=2;i=XXXX",
    "CHW_Supply": "ns=2;i=XXXX",
    "RLA_L1": "ns=2;i=XXXX",
    "RLA_L2": "ns=2;i=XXXX",
    "RLA_L3": "ns=2;i=XXXX",
    "RLA_Avg": "ns=2;i=XXXX",
    "CW_Return": "ns=2;i=XXXX",
    "CW_Supply": "ns=2;i=XXXX",
    "PH1_FLOW": "ns=2;i=XXXX",
    "PH2_FLOW": "ns=2;i=XXXX",
    "FEEDBACK": "ns=2;i=XXXX",
    "SIGNAL": "ns=2;i=XXXX",
    "CURRENT_L1": "ns=2;i=XXXX",
    "CURRENT_L2": "ns=2;i=XXXX",
    "CURRENT_L3": "ns=2;i=XXXX",
    "WET_BULB": "ns=2;i=XXXX",
}

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("opcua-bridge")

# ── Alert handler ─────────────────────────────────────────────────────────────


def handle_anomaly(score: float, raw: dict, timestamp: datetime) -> None:
    """
    Called whenever the model flags an anomaly.
    Extend this with your notification channel (Teams, Slack, email, etc.).
    """
    log.warning(
        f"⚠️  ANOMALY DETECTED | time={timestamp.isoformat()} | "
        f"score={score:.4f} | "
        f"CHW_Return={raw.get('CHW_Return')} | "
        f"RLA_Avg={raw.get('RLA_Avg')} | "
        f"CW_Supply={raw.get('CW_Supply')}"
    )


# ── OPC-UA helpers ───────────────────────────────────────────────────────────

async def connect_opcua() -> Client:
    """Create a client configured for a secured local OPC UA endpoint."""
    client = Client(OPC_SERVER_URL)

    if OPC_USERNAME:
        client.set_user(OPC_USERNAME)
    if OPC_PASSWORD:
        client.set_password(OPC_PASSWORD)

    if OPC_SECURITY_POLICY and OPC_SECURITY_MODE:
        security_string = f"{OPC_SECURITY_POLICY},{OPC_SECURITY_MODE}"
        client.set_security_string(security_string)
        log.info("Using OPC UA security settings: %s", security_string)

    await client.connect()
    return client


async def read_sensors(client: Client) -> dict[str, float]:
    """Read all configured OPC-UA nodes and return them as floats."""
    nodes = {name: client.get_node(node_id) for name, node_id in NODE_MAP.items()}
    values = await asyncio.gather(*[node.read_value() for node in nodes.values()])
    return {name: float(value) for name, value in zip(nodes.keys(), values)}


# ── Main loop ─────────────────────────────────────────────────────────────────

async def run_bridge() -> None:
    if not Path(SCALER_PATH).exists():
        raise FileNotFoundError(f"Scaler file not found at {SCALER_PATH}. Set SCALER_PATH to a valid file.")

    preprocessor = ChillerPreprocessor(scaler_path=SCALER_PATH)
    log.info("Connecting to OPC-UA server: %s", OPC_SERVER_URL)

    client = await connect_opcua()
    log.info("Connected. Starting polling loop.")

    try:
        async with httpx.AsyncClient(timeout=15.0) as http:
            while True:
                try:
                    timestamp = datetime.now(timezone.utc)

                    raw = await read_sensors(client)
                    log.info(
                        "Read sensors | RLA_Avg=%.1f%% | CHW_Return=%.1f°F | CW_Supply=%.1f°F",
                        raw["RLA_Avg"],
                        raw["CHW_Return"],
                        raw["CW_Supply"],
                    )

                    preprocessor.update(timestamp, raw)

                    if not preprocessor.is_warm():
                        remaining = preprocessor._buf.maxlen - len(preprocessor._buf)
                        log.info(
                            "Buffer warming up — %d/%d readings collected (%d more needed for 24h window)",
                            len(preprocessor._buf),
                            48,
                            remaining,
                        )
                        await asyncio.sleep(POLL_INTERVAL_S)
                        continue

                    features = preprocessor.get_feature_vector()
                    if features is None:
                        await asyncio.sleep(POLL_INTERVAL_S)
                        continue

                    resp = await http.post(INFERENCE_URL, json={"features": features[0].tolist()})
                    resp.raise_for_status()
                    result = resp.json()

                    log.info(
                        "Scored | decision=%.4f | anomaly=%s | inference=%sms",
                        result["decision_score"],
                        result["is_anomaly"],
                        result["inference_ms"],
                    )

                    if result["is_anomaly"]:
                        handle_anomaly(result["decision_score"], raw, timestamp)

                except Exception as exc:
                    log.error("Bridge error: %s", exc, exc_info=True)

                await asyncio.sleep(POLL_INTERVAL_S)
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(run_bridge())
