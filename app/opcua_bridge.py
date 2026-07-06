"""
OPC-UA → LOF Inference Bridge
==============================
Reads 16 raw sensor values from the BMS OPC-UA server every 30 minutes,
computes all 197 engineered features using ChillerPreprocessor, and posts
the result to the LOF inference container.

Before running, fill in:
  1. OPC_SERVER_URL  — your BMS OPC-UA endpoint
  2. NODE_MAP        — OPC-UA node ID for each of the 16 raw sensors
  3. SCALER_PATH     — path to scaler.pkl from the training artifacts folder
  4. handle_anomaly()— add your notification channel (email, webhook, etc.)
"""

import asyncio
import logging
import httpx
import numpy as np
from datetime import datetime, timezone
from asyncua import Client, Node
from preprocessor import ChillerPreprocessor

# ── Configuration ─────────────────────────────────────────────────────────────

OPC_SERVER_URL   = "opc.tcp://<BMS_SERVER_IP>:4840"      # ← fill in
INFERENCE_URL    = "http://lof-chiller:8000/predict"
SCALER_PATH      = "/app/model/scaler.pkl"                # ← mount scaler here
POLL_INTERVAL_S  = 1800                                   # 30 minutes

# Map each canonical sensor name to its OPC-UA node ID.
# Fill in the node IDs with your BMS engineer once available.
NODE_MAP: dict[str, str] = {
    "CHW_Return"  : "ns=2;i=XXXX",   # Chiller_1_M_126_CHW_Return (°F)
    "CHW_Supply"  : "ns=2;i=XXXX",   # Chiller_1_M_126_CHW_Supply (°F)
    "RLA_L1"      : "ns=2;i=XXXX",   # Chiller_M126_L1_RLA (%)
    "RLA_L2"      : "ns=2;i=XXXX",   # Chiller_M126_L2_RLA (%)
    "RLA_L3"      : "ns=2;i=XXXX",   # Chiller_M126_L3_RLA (%)
    "RLA_Avg"     : "ns=2;i=XXXX",   # Chiller_M126_Avg_RLA (%)
    "CW_Return"   : "ns=2;i=XXXX",   # Chiller_1_M_126_CW_Return (°F)
    "CW_Supply"   : "ns=2;i=XXXX",   # Chiller_1_M_126_CW_Supply (°F)
    "PH1_FLOW"    : "ns=2;i=XXXX",   # PH_1_Flow (gal/min)
    "PH2_FLOW"    : "ns=2;i=XXXX",   # PH_2_Flow (gal/min)
    "FEEDBACK"    : "ns=2;i=XXXX",   # Chiller_M_126_Twr_C1_FB (%)
    "SIGNAL"      : "ns=2;i=XXXX",   # Chiller_M_126_Twr_C1_Sig (%)
    "CURRENT_L1"  : "ns=2;i=XXXX",   # Chiller_M126_L1_Current (A)
    "CURRENT_L2"  : "ns=2;i=XXXX",   # Chiller_M126_L2_Current (A)
    "CURRENT_L3"  : "ns=2;i=XXXX",   # Chiller_M126_L3_Current (A)
    "WET_BULB"    : "ns=2;i=XXXX",   # OSA_Wet_Bulb_Temperature (°F)
}

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("opcua-bridge")

# ── Alert handler ─────────────────────────────────────────────────────────────

def handle_anomaly(score: float, raw: dict, timestamp: datetime) -> None:
    """
    Called whenever the model flags an anomaly.
    Extend with your notification channel:
      - POST to a Teams / Slack / PagerDuty webhook
      - Send email via smtplib
      - Write an alarm flag back to an OPC-UA node
    """
    log.warning(
        f"⚠️  ANOMALY DETECTED | time={timestamp.isoformat()} | "
        f"score={score:.4f} | "
        f"CHW_Return={raw.get('CHW_Return')} | "
        f"RLA_Avg={raw.get('RLA_Avg')} | "
        f"CW_Supply={raw.get('CW_Supply')}"
    )
    # TODO: add notification here

# ── OPC-UA read ───────────────────────────────────────────────────────────────

async def read_sensors(client: Client) -> dict:
    """Read all 16 raw sensor nodes and return as a dict."""
    nodes: dict[str, Node] = {
        name: client.get_node(node_id)
        for name, node_id in NODE_MAP.items()
    }
    values = await asyncio.gather(*[n.read_value() for n in nodes.values()])
    return {name: float(v) for name, v in zip(nodes.keys(), values)}

# ── Main loop ─────────────────────────────────────────────────────────────────

async def run_bridge() -> None:
    preprocessor = ChillerPreprocessor(scaler_path=SCALER_PATH)
    log.info(f"Connecting to OPC-UA server: {OPC_SERVER_URL}")

    async with Client(url=OPC_SERVER_URL) as client:
        log.info("Connected. Starting 30-minute polling loop.")

        async with httpx.AsyncClient(timeout=15.0) as http:
            while True:
                try:
                    timestamp = datetime.now(timezone.utc)

                    # 1. Read raw sensors from BMS
                    raw = await read_sensors(client)
                    log.info(
                        f"Read sensors | RLA_Avg={raw['RLA_Avg']:.1f}% | "
                        f"CHW_Return={raw['CHW_Return']:.1f}°F | "
                        f"CW_Supply={raw['CW_Supply']:.1f}°F"
                    )

                    # 2. Update rolling buffer
                    preprocessor.update(timestamp, raw)

                    # 3. Skip until buffer is warm (needs 24h of history)
                    if not preprocessor.is_warm():
                        remaining = preprocessor._buf.maxlen - len(preprocessor._buf)
                        log.info(
                            f"Buffer warming up — {len(preprocessor._buf)}/{WIN_LONG} "
                            f"readings collected ({remaining} more needed for 24h window)"
                        )
                        await asyncio.sleep(POLL_INTERVAL_S)
                        continue

                    # 4. Compute 197-feature vector
                    features = preprocessor.get_feature_vector()

                    # 5. Post to inference container
                    resp = await http.post(
                        INFERENCE_URL,
                        json={"features": features[0].tolist()},
                    )
                    resp.raise_for_status()
                    result = resp.json()

                    log.info(
                        f"Scored | decision={result['decision_score']:.4f} | "
                        f"anomaly={result['is_anomaly']} | "
                        f"inference={result['inference_ms']}ms"
                    )

                    # 6. Alert if anomaly detected
                    if result["is_anomaly"]:
                        handle_anomaly(result["decision_score"], raw, timestamp)

                except Exception as exc:
                    log.error(f"Bridge error: {exc}", exc_info=True)

                await asyncio.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    asyncio.run(run_bridge())
