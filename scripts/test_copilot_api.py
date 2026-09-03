#!/usr/bin/env python3
"""
Step 5 — Smoke-test the copilot FastAPI service.

Usage:
    python3 scripts/test_copilot_api.py
    python3 scripts/test_copilot_api.py --base-url http://localhost:8002
    python3 scripts/test_copilot_api.py --diagnose   # includes POST /diagnose (may call LLM)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DEFAULT_BASE = "http://localhost:8002"


def _get(url: str) -> dict:
    with urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode())


def _post(url: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke-test copilot API endpoints")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help="API base URL")
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help="Run POST /diagnose (normal scenario; no LLM on normal route)",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    try:
        health = _get(f"{base}/health")
        print("GET /health")
        print(json.dumps(health, indent=2))
        assert health.get("status") == "ok", "health status not ok"

        scenarios = _get(f"{base}/scenarios")
        print("\nGET /scenarios")
        print(json.dumps(scenarios, indent=2))
        assert "scenarios" in scenarios and scenarios["scenarios"], "no scenarios"

        telemetry = _get(f"{base}/telemetry/Chiller-03?scenario=normal")
        print("\nGET /telemetry/Chiller-03?scenario=normal")
        print(f"  asset_id: {telemetry.get('asset_id')}")
        print(f"  scenario: {telemetry.get('scenario')}")

        if args.diagnose:
            result = _post(
                f"{base}/diagnose",
                {
                    "question": "health check",
                    "asset_id": "Chiller-03",
                    "scenario": "normal",
                },
            )
            print("\nPOST /diagnose (normal scenario)")
            print(f"  route: {result.get('route')}")
            print(f"  escalated: {result.get('escalated')}")
            assert result.get("route") == "normal", "expected normal route"

        print("\n✓ Copilot API smoke test passed")

    except HTTPError as exc:
        print(f"HTTP error {exc.code}: {exc.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except URLError as exc:
        print(
            f"Cannot reach {base} — start the API first:\n"
            "  python3 scripts/run_copilot_api.py",
            file=sys.stderr,
        )
        print(f"  ({exc.reason})", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
