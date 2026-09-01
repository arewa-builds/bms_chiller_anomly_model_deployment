"""
Telemetry tool — returns current chiller sensor readings and derived flags.

Step 3 uses demo scenarios (synthetic data) rather than live OPC UA.
"""

from __future__ import annotations

from copilot.data.demo_scenarios import DEMO_SCENARIOS, get_scenario, resolve_scenario
from copilot.schemas import ChillerTelemetry


def get_chiller_telemetry(
    asset_id: str,
    scenario: str | None = None,
) -> ChillerTelemetry:
    """
    Return current telemetry for a chiller asset.

    Args:
        asset_id: Chiller identifier (e.g. ``Chiller-03``).
        scenario: Optional demo scenario key. When omitted, resolves from
            ``asset_id`` aliases or defaults to ``normal``.

    Returns:
        ChillerTelemetry with raw sensors, derived flags, and anomaly status.
    """
    key = resolve_scenario(asset_id=asset_id, scenario=scenario)
    return get_scenario(key, asset_id=asset_id)


def list_scenarios() -> list[str]:
    """Return available demo scenario keys."""
    return sorted(DEMO_SCENARIOS.keys())
