#!/usr/bin/env python3
"""Start the Step 5 copilot FastAPI service (works when uvicorn is not on PATH)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from copilot.env_utils import load_env_copilot

load_env_copilot()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "copilot.api.main:app",
        host="0.0.0.0",
        port=8002,
        reload="--reload" in sys.argv,
    )
