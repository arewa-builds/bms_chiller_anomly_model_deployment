"""Demo telemetry scenarios for Chiller-03 (curated for interviews)."""

from __future__ import annotations

from copy import deepcopy

from copilot.schemas import ChillerTelemetry

DEMO_SCENARIOS = {
    "cw_degradation": {
        "asset_id": "Chiller-03",
        "scenario": "cw_degradation",
        "description": "Condenser water performance deviation with elevated approach and tower tracking error",
        "timestamp": "2026-09-01T14:00:00Z",
        "anomaly": {
            "is_anomaly": True,
            "decision_score": -0.42,
            "label": -1,
        },
        "raw_sensors": {
            "CHW_Return": 54.2,
            "CHW_Supply": 44.1,
            "RLA_L1": 71.0,
            "RLA_L2": 73.5,
            "RLA_L3": 72.0,
            "RLA_Avg": 72.2,
            "CW_Return": 95.3,
            "CW_Supply": 87.6,
            "PH1_FLOW": 890.0,
            "PH2_FLOW": 120.0,
            "FEEDBACK": 45.0,
            "SIGNAL": 68.0,
            "CURRENT_L1": 312.0,
            "CURRENT_L2": 318.0,
            "CURRENT_L3": 315.0,
            "WET_BULB": 78.1,
        },
        "derived_flags": {
            "cw_approach_to_wb_elevated": {"elevated": True, "value": 8.0},
            "flow_imbalance_pct_high": {"elevated": True, "value": 10.0},
            "tower_tracking_error_abs_high": {"elevated": True, "value": 12.0},
        },
    },
    "flow_restriction": {
        "asset_id": "Chiller-03",
        "scenario": "flow_restriction",
        "description": "Low condenser flow with high header imbalance",
        "timestamp": "2026-09-01T10:30:00Z",
        "anomaly": {
            "is_anomaly": True,
            "decision_score": -0.38,
            "label": -1,
        },
        "raw_sensors": {
            "CHW_Return": 53.8,
            "CHW_Supply": 44.5,
            "RLA_L1": 68.0,
            "RLA_L2": 70.0,
            "RLA_L3": 69.0,
            "RLA_Avg": 69.0,
            "CW_Return": 94.0,
            "CW_Supply": 86.5,
            "PH1_FLOW": 420.0,
            "PH2_FLOW": 380.0,
            "FEEDBACK": 52.0,
            "SIGNAL": 55.0,
            "CURRENT_L1": 298.0,
            "CURRENT_L2": 305.0,
            "CURRENT_L3": 301.0,
            "WET_BULB": 76.5,
        },
        "derived_flags": {
            "cw_approach_to_wb_elevated": {"elevated": False, "value": 10.0},
            "flow_imbalance_pct_high": {"elevated": True, "value": 18.5},
            "tower_tracking_error_abs_high": {"elevated": False, "value": 3.0},
        },
    },
    "normal": {
        "asset_id": "Chiller-03",
        "scenario": "normal",
        "description": "Steady-state normal operation",
        "timestamp": "2026-09-01T08:00:00Z",
        "anomaly": {
            "is_anomaly": False,
            "decision_score": 1.24,
            "label": 1,
        },
        "raw_sensors": {
            "CHW_Return": 54.0,
            "CHW_Supply": 44.0,
            "RLA_L1": 62.0,
            "RLA_L2": 64.0,
            "RLA_L3": 63.0,
            "RLA_Avg": 63.0,
            "CW_Return": 92.0,
            "CW_Supply": 84.5,
            "PH1_FLOW": 1050.0,
            "PH2_FLOW": 1040.0,
            "FEEDBACK": 58.0,
            "SIGNAL": 60.0,
            "CURRENT_L1": 285.0,
            "CURRENT_L2": 290.0,
            "CURRENT_L3": 288.0,
            "WET_BULB": 75.0,
        },
        "derived_flags": {
            "cw_approach_to_wb_elevated": {"elevated": False, "value": 9.5},
            "flow_imbalance_pct_high": {"elevated": False, "value": 0.5},
            "tower_tracking_error_abs_high": {"elevated": False, "value": 2.0},
        },
    },
}

ASSET_ALIASES = {
    "chiller-03": "cw_degradation",
    "chiller_03": "cw_degradation",
    "m126": "cw_degradation",
    "chiller-03-normal": "normal",
}


def resolve_scenario(
    asset_id: str | None = None,
    scenario: str | None = None,
) -> str:
    """Pick a demo scenario from an explicit key or asset alias."""
    if scenario:
        return scenario
    if asset_id:
        alias = asset_id.strip().lower().replace(" ", "-")
        if alias in ASSET_ALIASES:
            return ASSET_ALIASES[alias]
    return "normal"


def get_scenario(
    scenario: str,
    *,
    asset_id: str | None = None,
) -> ChillerTelemetry:
    """Load a demo scenario as a validated ChillerTelemetry model."""
    if scenario not in DEMO_SCENARIOS:
        available = ", ".join(sorted(DEMO_SCENARIOS))
        raise ValueError(f"Unknown scenario '{scenario}'. Available: {available}")

    payload = deepcopy(DEMO_SCENARIOS[scenario])
    if asset_id:
        payload["asset_id"] = asset_id

    reading_ts = payload["timestamp"]
    for flag in payload.get("derived_flags", {}).values():
        flag.setdefault("timestamp", reading_ts)

    return ChillerTelemetry.model_validate(payload)
