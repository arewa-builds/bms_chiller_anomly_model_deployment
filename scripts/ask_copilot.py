#!/usr/bin/env python3
"""
Ask the troubleshooting copilot (RAG + telemetry + LangGraph workflow).

Usage:
    python3 scripts/ask_copilot.py "Chiller-03 has an elevated anomaly score. What should I investigate?"
    python3 scripts/ask_copilot.py --asset Chiller-03 --scenario cw_degradation "what should I check?"
    python3 scripts/ask_copilot.py --telemetry-only --scenario cw_degradation
    python3 scripts/ask_copilot.py --linear --asset Chiller-03 "elevated CW approach"
    python3 scripts/ask_copilot.py --retrieve-only "tower tracking error"
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from copilot.env_utils import load_env_copilot

load_env_copilot()

from copilot.rag.chain import fetch_telemetry, retrieve_context, troubleshoot
from copilot.tools.telemetry import list_scenarios
from copilot.workflow.graph import run_workflow


def _print_diagnosis(diagnosis) -> None:
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


def _print_workflow(result) -> None:
    print("=" * 60)
    print(f"Route       : {result.route}")
    print(f"Triage      : {result.triage_reason}")
    print(f"Escalated   : {result.escalated}")
    print("=" * 60)
    print(f"Asset       : {result.diagnosis.asset}")
    print(f"Condition   : {result.diagnosis.condition}")
    print(f"Confidence  : {result.diagnosis.confidence}")
    print(f"Escalation  : {result.diagnosis.escalation_required}")
    print("=" * 60)

    print("\nPotential causes:")
    for i, cause in enumerate(result.diagnosis.potential_causes, 1):
        print(f"  {i}. {cause}")

    print("\nEvidence:")
    for item in result.diagnosis.evidence:
        print(f"  • {item}")

    print("\nRecommended investigation:")
    for i, step in enumerate(result.diagnosis.recommended_investigation, 1):
        print(f"  {i}. {step}")

    print("\nSources:")
    for src in result.diagnosis.sources:
        section = f" — {src.section}" if src.section else ""
        print(f"  • {src.title}{section}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manufacturing AI Troubleshooting Copilot (Step 4: LangGraph workflow)"
    )
    parser.add_argument("question", nargs="?", help="Engineer troubleshooting question")
    parser.add_argument("--asset", default=None, help="Asset ID, e.g. Chiller-03")
    parser.add_argument(
        "--scenario",
        default=None,
        choices=list_scenarios(),
        help="Demo telemetry scenario (default: normal, or resolved from asset alias)",
    )
    parser.add_argument(
        "--telemetry-only",
        action="store_true",
        help="Print telemetry JSON only (no retrieval or LLM call)",
    )
    parser.add_argument(
        "--retrieve-only",
        action="store_true",
        help="Show retrieved docs only (no LLM call)",
    )
    parser.add_argument(
        "--linear",
        action="store_true",
        help="Use Step 3 linear RAG chain instead of LangGraph workflow",
    )
    parser.add_argument("--json", action="store_true", help="Output diagnosis as JSON")
    args = parser.parse_args()

    if not args.question and not args.telemetry_only:
        parser.error("question is required unless --telemetry-only is set")

    try:
        if args.telemetry_only:
            telemetry = fetch_telemetry(asset_id=args.asset, scenario=args.scenario)
            print(json.dumps(telemetry.model_dump(), indent=2))
            return

        if args.retrieve_only:
            if not args.question:
                parser.error("question is required for --retrieve-only")
            context, docs = retrieve_context(args.question)
            print("=== Retrieved context ===\n")
            print(context)
            print(f"\n({len(docs)} chunks retrieved)")
            return

        if args.linear:
            diagnosis = troubleshoot(
                args.question,
                asset_id=args.asset,
                scenario=args.scenario,
            )
            if args.json:
                print(json.dumps(diagnosis.model_dump(), indent=2))
                return
            _print_diagnosis(diagnosis)
            return

        result = run_workflow(
            args.question,
            asset_id=args.asset,
            scenario=args.scenario,
        )

        if args.json:
            print(json.dumps(result.model_dump(), indent=2))
            return

        _print_workflow(result)

    except ValueError as exc:
        print(f"Configuration error:\n{exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
