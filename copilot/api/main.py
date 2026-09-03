"""
Manufacturing AI Troubleshooting Copilot — FastAPI service (Step 5).

Endpoints:
  GET  /health
  GET  /scenarios
  GET  /telemetry/{asset_id}
  POST /diagnose
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from copilot.api.schemas import (
    ChillerTelemetry,
    DiagnoseRequest,
    HealthResponse,
    ScenariosResponse,
    WorkflowResult,
)
from copilot.config import CHROMA_MODE, OPENAI_API_KEY
from copilot.env_utils import load_env_copilot
from copilot.tools.telemetry import get_chiller_telemetry, list_scenarios
from copilot.workflow.graph import run_workflow

load_env_copilot()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(
    title="Chiller Troubleshooting Copilot API",
    version="1.0.0",
    description="HTTP API for telemetry, LangGraph routing, and RAG diagnosis",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _openai_configured() -> bool:
    return bool(OPENAI_API_KEY) and not OPENAI_API_KEY.startswith("sk-your")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="chiller-troubleshooting-copilot",
        version="1.0.0",
        chroma_mode=CHROMA_MODE,
        openai_configured=_openai_configured(),
    )


@app.get("/scenarios", response_model=ScenariosResponse)
def scenarios() -> ScenariosResponse:
    return ScenariosResponse(scenarios=list_scenarios())


@app.get("/telemetry/{asset_id}", response_model=ChillerTelemetry)
def telemetry(
    asset_id: str,
    scenario: str | None = Query(default=None, description="Demo scenario key"),
) -> ChillerTelemetry:
    try:
        return get_chiller_telemetry(asset_id, scenario=scenario)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/diagnose", response_model=WorkflowResult)
def diagnose(body: DiagnoseRequest) -> WorkflowResult:
    try:
        return run_workflow(
            body.question,
            asset_id=body.asset_id,
            scenario=body.scenario,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
