#!/usr/bin/env python3
"""
Step 2 — Ask the troubleshooting copilot (RAG + structured LLM output).

Usage:
    python3 scripts/ask_copilot.py "Chiller-03 has an elevated anomaly score. What should I investigate?"
    python3 scripts/ask_copilot.py --asset Chiller-03 "elevated CW approach temperature"
    python3 scripts/ask_copilot.py --retrieve-only "tower tracking error"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from copilot.env_utils import load_env_copilot

load_env_copilot()

from copilot.rag.chain import retrieve_context, troubleshoot


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manufacturing AI Troubleshooting Copilot (Step 2 RAG)"
    )
    parser.add_argument("question", help="Engineer troubleshooting question")
    parser.add_argument("--asset", default=None, help="Asset ID, e.g. Chiller-03")
    parser.add_argument(
        "--retrieve-only",
        action="store_true",
        help="Show retrieved docs only (no LLM call)",
    )
    parser.add_argument("--json", action="store_true", help="Output diagnosis as JSON")
    args = parser.parse_args()

    try:
        if args.retrieve_only:
            context, docs = retrieve_context(args.question)
            print("=== Retrieved context ===\n")
            print(context)
            print(f"\n({len(docs)} chunks retrieved)")
            return

        diagnosis = troubleshoot(args.question, asset_id=args.asset)

        if args.json:
            print(json.dumps(diagnosis.model_dump(), indent=2))
            return

        print("=" * 60)
        print(f"Asset       : {diagnosis.asset}")
        print(f"Condition   : {diagnosis.condition}")
        print(f"Confidence  : {diagnosis.confidence}")
        print(f"Escalation  : {diagnosis.escalation_required}")
        print("=" * 60)

        print("\nPotential causes:")
        for i, cause in enumerate(diagnosis.potential_causes, 1):
            print(f"  {i}. {cause}")

        print("\nEvidence:")
        for item in diagnosis.evidence:
            print(f"  • {item}")

        print("\nRecommended investigation:")
        for i, step in enumerate(diagnosis.recommended_investigation, 1):
            print(f"  {i}. {step}")

        print("\nSources:")
        for src in diagnosis.sources:
            section = f" — {src.section}" if src.section else ""
            print(f"  • {src.title}{section}")

    except ValueError as exc:
        print(f"Configuration error:\n{exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
