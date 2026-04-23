import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from server.run_manager import RunManager

# ⚠ LOCAL DEV ONLY — this server has no authentication.
# Do not expose port 8001 on a shared/public network: any caller can start
# LLM runs (which may cost real API money) or read run history.
# Before deploying, add an API key check (e.g. X-Api-Key header) to all
# POST endpoints and restrict allow_origins to your actual frontend origin.

# Load .env files at server startup using paths relative to this file's location
# so the server finds them regardless of the working directory.
# Both files are loaded (raf/.env first, then .env); first value wins (override=False).
_ROOT = Path(__file__).parent.parent
try:
    from dotenv import load_dotenv
    for _env_path in [_ROOT / "raf" / ".env", _ROOT / ".env"]:
        load_dotenv(_env_path, override=False)
except ImportError:
    # python-dotenv not installed — fall back to simple parser.
    # Handles: KEY=value, KEY="value", KEY='value', blank lines, # comments.
    # Does NOT handle: multiline values, export KEY=value, values containing #.
    for _env_path in [_ROOT / "raf" / ".env", _ROOT / ".env"]:
        if _env_path.exists():
            for _line in _env_path.read_text(encoding="utf-8").splitlines():
                _line = _line.strip()
                if not _line or _line.startswith("#") or "=" not in _line:
                    continue
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip().strip("\"'"))


class AgentSpec(BaseModel):
    """Provider + model for a single agent slot."""
    provider: str
    model: str | None = None


class RunRequest(BaseModel):
    goal: str
    provider: str | None = None
    model: str | None = None
    adapter: str | None = "mock"
    jury_model: str | None = None
    # Per-slot multi-model lists (optional — overrides provider/model when set)
    consortium_agents: List[AgentSpec] | None = None
    jury_agents: List[AgentSpec] | None = None
    # Tier-based routing agents (optional — enables depth-aware model selection)
    # leaf_agents: Tier 0 — fast models for deep leaf base_execute workers
    # mid_agents:  Tier 1 — capable models for mid-level planning and merging
    # root_agents: Tier 2 — strongest models for root node + analysis/referee
    leaf_agents: List[AgentSpec] | None = None
    mid_agents: List[AgentSpec] | None = None
    root_agents: List[AgentSpec] | None = None
    consortium_size: int | None = None
    jury_size: int | None = None
    max_depth: int | None = None
    max_parallel_children: int | None = None
    max_nodes_total: int | None = None
    system_prompt: str | None = None
    plan_approval_required: bool = False
    plan_recovery: str | None = None
    max_plan_retries: int | None = None
    retry_limit: int | None = None
    timeout_by_task: Dict[str, int] | None = None
    tools_enabled: bool = False
    domain: str | None = None  # override auto-detected domain; None = auto
    skip_clarify: bool = False  # set True on clarification continuation runs
    force_recursive: bool = False  # always decompose at root, skip mode vote
    api_key: str | None = None  # user-supplied API key; overrides server env vars


class DemoRequest(BaseModel):
    disks: int = 3
    provider: str | None = None
    model: str | None = None
    consortium_size: int | None = None
    jury_size: int | None = None
    max_depth: int | None = None
    max_parallel_children: int | None = None
    max_nodes_total: int | None = None
    system_prompt: str | None = None


class ApprovePlanRequest(BaseModel):
    node_id: str
    children: List[Dict[str, Any]]


app = FastAPI()
manager = RunManager()


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _allowed_origins() -> List[str]:
    configured = os.getenv("RAF_ALLOWED_ORIGINS", "").strip()
    if configured:
        origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
        return origins or ["*"]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def _require_run_token(run_id: str, access_token: Optional[str]) -> Any:
    run_state = manager.get(run_id)
    if not run_state:
        raise HTTPException(status_code=404, detail="run not found")
    if not access_token or access_token != run_state.access_token:
        raise HTTPException(status_code=403, detail="invalid run token")
    return run_state

_origins = _allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {"ok": True}


@app.get("/api/models")
def models() -> Dict[str, Any]:
    return manager.list_models()


@app.post("/api/run")
def run(request: RunRequest) -> Dict[str, Any]:
    provider = request.provider or request.adapter or "mock"
    require_user_key = _env_flag("RAF_REQUIRE_USER_API_KEY", default=False)
    if require_user_key and provider != "mock" and not (request.api_key or "").strip():
        raise HTTPException(status_code=400, detail="A user API key is required for non-mock providers.")
    consortium_agents = (
        [{"provider": a.provider, "model": a.model} for a in request.consortium_agents]
        if request.consortium_agents else []
    )
    jury_agents = (
        [{"provider": a.provider, "model": a.model} for a in request.jury_agents]
        if request.jury_agents else []
    )
    leaf_agents = (
        [{"provider": a.provider, "model": a.model} for a in request.leaf_agents]
        if request.leaf_agents else []
    )
    mid_agents = (
        [{"provider": a.provider, "model": a.model} for a in request.mid_agents]
        if request.mid_agents else []
    )
    root_agents = (
        [{"provider": a.provider, "model": a.model} for a in request.root_agents]
        if request.root_agents else []
    )
    # If per-slot agents are given, derive consortium_size/jury_size from list lengths
    config_overrides: Dict[str, Any] = {
        "consortium_size": len(consortium_agents) if consortium_agents else request.consortium_size,
        "jury_size": len(jury_agents) if jury_agents else request.jury_size,
        "max_depth": request.max_depth,
        "max_parallel_children": request.max_parallel_children,
        "max_nodes_total": request.max_nodes_total,
        "system_prompt": request.system_prompt,
        "plan_approval_required": request.plan_approval_required,
        "plan_recovery": request.plan_recovery,
        "max_plan_retries": request.max_plan_retries,
        "retry_limit": request.retry_limit,
        "timeout_by_task": request.timeout_by_task,
        "tools_enabled": request.tools_enabled,
    }
    if request.domain is not None:
        config_overrides["domain"] = request.domain
    if request.skip_clarify:
        config_overrides["clarify_before_execute"] = False
    if request.force_recursive:
        config_overrides["force_recursive"] = True
    run_state = manager.create_run(
        request.goal,
        provider,
        request.model,
        config_overrides,
        jury_model=request.jury_model,
        consortium_agents=consortium_agents,
        jury_agents=jury_agents,
        leaf_agents=leaf_agents,
        mid_agents=mid_agents,
        root_agents=root_agents,
        api_key=request.api_key or None,
    )
    return {"run_id": run_state.run_id, "access_token": run_state.access_token}


@app.post("/api/demo/hanoi")
def demo_hanoi(request: DemoRequest) -> Dict[str, Any]:
    disks = max(1, min(10, int(request.disks)))
    goal = f"HANOI({disks},0,2,1)"
    provider = request.provider or "mock"
    run_state = manager.create_run(
        goal,
        provider,
        request.model,
        {
            "consortium_size": request.consortium_size,
            "jury_size": request.jury_size,
            "max_depth": request.max_depth,
            "max_parallel_children": request.max_parallel_children,
            "max_nodes_total": request.max_nodes_total,
            "system_prompt": request.system_prompt,
        },
    )
    return {"run_id": run_state.run_id, "goal": goal, "access_token": run_state.access_token}


@app.get("/api/run/{run_id}")
def run_status(run_id: str, x_run_token: str | None = Header(default=None)) -> Dict[str, Any]:
    run_state = _require_run_token(run_id, x_run_token)
    return {"status": run_state.status, "result": run_state.result, "error": run_state.error}


@app.get("/api/run/{run_id}/events")
def run_events(run_id: str, x_run_token: str | None = Header(default=None)) -> Dict[str, Any]:
    """Return all stored events for a run (up to _MAX_EVENTS_PER_RUN).

    Used by the frontend to replay a run's trace after a WebSocket disconnect.
    """
    run_state = _require_run_token(run_id, x_run_token)
    return {
        "run_id": run_id,
        "status": run_state.status,
        "events": run_state.events,
    }


@app.post("/api/run/{run_id}/approve_plan")
def approve_plan(run_id: str, body: ApprovePlanRequest, x_run_token: str | None = Header(default=None)) -> Dict[str, Any]:
    """Unblock a run waiting for plan approval (with optionally edited children)."""
    run_state = _require_run_token(run_id, x_run_token)
    try:
        run_state.approve_plan(body.node_id, body.children)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True}


@app.post("/api/run/{run_id}/cancel")
def cancel_run(run_id: str, x_run_token: str | None = Header(default=None)) -> Dict[str, Any]:
    """Signal a running run to stop cooperatively."""
    _require_run_token(run_id, x_run_token)
    ok = manager.cancel_run(run_id)
    return {"ok": ok}


@app.get("/api/runs")
def list_runs() -> Dict[str, Any]:
    """Return metadata for recent runs (most recent first)."""
    if not _env_flag("RAF_ENABLE_RUN_LIST", default=False):
        raise HTTPException(status_code=404, detail="run list disabled")
    return {"runs": manager.list_runs()}


@app.websocket("/api/stream/{run_id}")
async def stream(run_id: str, websocket: WebSocket) -> None:
    token = websocket.query_params.get("token")
    run_state = manager.get(run_id)
    if not run_state or not token or token != run_state.access_token:
        await websocket.accept()
        await websocket.send_json({"event": "error", "message": "invalid run token"})
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        async for event in manager.stream_events(run_state):
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return
