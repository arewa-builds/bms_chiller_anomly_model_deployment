"""Load and normalize .env.copilot values for copilot scripts."""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_COPILOT_PATH = REPO_ROOT / ".env.copilot"


def strip_quotes(value: str) -> str:
    """Remove surrounding single or double quotes from an env value."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1].strip()
    return value


def load_env_copilot(path: Path | None = None) -> None:
    """Load .env.copilot into os.environ (does not override existing vars)."""
    env_file = path or ENV_COPILOT_PATH
    if not env_file.exists():
        return

    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = strip_quotes(value.strip())
        os.environ.setdefault(key, value)
