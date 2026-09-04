---
name: configure-opcua-nodes
description: Walk through NODE_MAP configuration for BMS OPC-UA chiller tags. Use when mapping sensor node IDs, onboarding a new OPC-UA server, or filling in placeholder ns=2;i=XXXX entries in opcua_bridge.py.
paths: app/opcua_bridge.py
---

# Configure OPC-UA NODE_MAP

## Prerequisites

- OPC UA server endpoint URL from BMS engineer
- Network access to the OPC UA server from the bridge container
- Security policy decision (None for lab, SignAndEncrypt for production)
- Training artifact `model/scaler.pkl` available for mounting

## Steps

### 1. Confirm server endpoint

Update `OPC_SERVER_URL` in `app/opcua_bridge.py`:

```python
OPC_SERVER_URL = "opc.tcp://<BMS_SERVER_IP>:4840"
```

For Docker Compose, also set the `OPC_SERVER_URL` environment variable in `docker-compose.yml`.

### 2. Browse the OPC UA server

Use UaExpert, Prosys, or an asyncua browse script to discover node IDs for each chiller tag. Record both namespace index and identifier (numeric `i=` or string `s=`).

### 3. Map all 16 canonical sensors

Update `NODE_MAP` with live node IDs. Every key below is required:

| Key | Typical BMS tag | Unit |
|-----|-----------------|------|
| `CHW_Return` | Chilled water return temp | °F |
| `CHW_Supply` | Chilled water supply temp | °F |
| `RLA_L1` | Load phase 1 | % |
| `RLA_L2` | Load phase 2 | % |
| `RLA_L3` | Load phase 3 | % |
| `RLA_Avg` | Average load | % |
| `CW_Return` | Condenser water return | °F |
| `CW_Supply` | Condenser water supply | °F |
| `PH1_FLOW` | Primary header flow 1 | gal/min |
| `PH2_FLOW` | Primary header flow 2 | gal/min |
| `FEEDBACK` | Tower control feedback | % |
| `SIGNAL` | Tower control signal | % |
| `CURRENT_L1` | Phase 1 current | A |
| `CURRENT_L2` | Phase 2 current | A |
| `CURRENT_L3` | Phase 3 current | A |
| `WET_BULB` | Outdoor wet bulb | °F |

### 4. Validate a single read

Before enabling the full poll loop, read each node once and confirm:

- Values are numeric and in expected ranges
- Engineering units match training data
- No stale or null timestamps from the server

### 5. Configure security (production)

For production BMS servers:

- Generate or obtain client application certificate
- Trust server certificate on client; trust client on server
- Set `SecurityPolicy` and `MessageSecurityMode` to match server endpoint
- Use dedicated service account — not operator credentials

### 6. Mount scaler and test warm-up

Ensure `SCALER_PATH` points to the training `scaler.pkl`. The bridge will log warm-up progress until 48 readings (24 h) are collected.

### 7. Verify end-to-end

After warm-up, confirm logs show successful `/predict` responses with `decision_score` and `inference_ms`.

## Common mistakes

- Wrong namespace index (`ns=3` vs `ns=2`)
- String node IDs quoted incorrectly (`ns=2;s=Tag.Name` not `ns=2;s="Tag.Name"` unless required)
- Mixing °C and °F without conversion
- Missing sensors causing NaN features that get zero-filled silently
