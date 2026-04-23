"""
server.run_manager
==================
Manages the lifecycle of RAF runs spawned by the API server.

Each run executes in a background daemon thread and emits JSON events into a
Queue.  WebSocket clients drain the queue in real time via :func:`stream_events`.

Key classes
-----------
RunState
    All state for a single run: its events list, streaming queue, thread,
    cancellation event, plan-approval gates, and completion metadata.
RunManager
    Factory and registry for RunState objects.  Handles adapter selection,
    config assembly, and the optional jury adapter for multi-model setups.
"""

import asyncio
import os
import secrets
import threading
import time
import uuid
from dataclasses import dataclass, field
from queue import Queue
from typing import Any, Dict, List, Optional

from raf.core.deps import DependencyError, validate_plan
from raf.core.engine import RafEngine
from raf.core.trace import TraceLogger
from raf.llm.mock_adapter import MockAdapter
from raf.schemas import RafConfig

# Maximum number of completed run summaries kept in history
_MAX_HISTORY = 50
# Maximum events kept per run in the replay list (guards against memory growth on deep runs)
_MAX_EVENTS_PER_RUN = 2000


@dataclass
class RunState:
    """All state for a single RAF run.

    Parameters
    ----------
    run_id:
        UUID string identifying this run.
    goal:
        The top-level goal string passed to the engine.
    provider:
        LLM provider name (e.g. ``"openrouter"``, ``"mock"``).
    model:
        Optional specific model name within the provider.
    jury_model:
        Optional model name for the jury adapter (falls back to *model*).
    config_overrides:
        Dict of RafConfig field overrides supplied by the API caller.
    """

    run_id: str
    goal: str
    provider: str
    model: Optional[str] = None
    jury_model: Optional[str] = None
    # Per-slot model specs — if non-empty these override provider/model/jury_model.
    # Each entry: {"provider": str, "model": str | None}
    consortium_agents: List[Dict[str, Optional[str]]] = field(default_factory=list)
    jury_agents: List[Dict[str, Optional[str]]] = field(default_factory=list)
    # Tier-based routing agents — when provided, override flat consortium/jury for
    # their respective depth tier.  See RafEngine for routing logic.
    leaf_agents: List[Dict[str, Optional[str]]] = field(default_factory=list)   # Tier 0: deep workers
    mid_agents: List[Dict[str, Optional[str]]] = field(default_factory=list)    # Tier 1: planners/mergers
    root_agents: List[Dict[str, Optional[str]]] = field(default_factory=list)   # Tier 2: root/referee
    config_overrides: Dict[str, object] = field(default_factory=dict)
    api_key: Optional[str] = None  # user-supplied key; overrides server env vars
    access_token: str = field(default_factory=lambda: secrets.token_urlsafe(24))
    status: str = "running"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)
    queue: Queue = field(default_factory=Queue)
    thread: Optional[threading.Thread] = None

    # Timing
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    # Cooperative cancellation — set this event to ask the engine to stop.
    cancel_event: threading.Event = field(default_factory=threading.Event)

    # Max children per plan — set by _execute() after config is built; used by approve_plan().
    max_children_per_plan: int = 20

    # Plan approval: keyed by node_id
    _plan_events: Dict[str, threading.Event] = field(default_factory=dict)
    _approved_plans: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # ── event helpers ─────────────────────────────────────────────────────────

    def emit(self, event: Dict[str, Any]) -> None:
        """Append *event* to the replay list (capped) and push it to the live queue."""
        if len(self.events) < _MAX_EVENTS_PER_RUN:
            self.events.append(event)
        self.queue.put(event)

    # ── cancellation ──────────────────────────────────────────────────────────

    def cancel(self) -> None:
        """Signal the engine to stop at the next cancellation checkpoint."""
        self.cancel_event.set()

    # ── plan approval ─────────────────────────────────────────────────────────

    def request_plan_approval(self, node_id: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Called from the engine background thread.  Emits ``plan_ready`` and blocks
        until the user approves (or up to 5 minutes, then falls back to the original plan).
        """
        event = threading.Event()
        self._plan_events[node_id] = event
        self.emit(
            {
                "event": "plan_ready",
                "node_id": node_id,
                "children": plan.get("children", []),
                "rationale": plan.get("rationale", ""),
            }
        )
        event.wait(timeout=300)
        # Pop both maps after the gate is released to avoid stale memory growth.
        result = self._approved_plans.pop(node_id, plan)
        self._plan_events.pop(node_id, None)
        return result

    def approve_plan(self, node_id: str, children: List[Dict[str, Any]]) -> None:
        """Called from the API endpoint when the user approves (or edits) a plan.

        Validates dependency structure using the run's configured max_children_per_plan
        before storing, so that a user-edited plan with invalid or circular dependencies
        fails fast here rather than crashing the engine during topo_sort at execution time.
        """
        plan = {"children": children}
        try:
            validate_plan(plan, max_children=self.max_children_per_plan)
        except DependencyError as exc:
            raise ValueError(f"Invalid plan: {exc}") from exc
        existing = self._approved_plans.get(node_id, {})
        self._approved_plans[node_id] = {**existing, "children": children}
        # Pop _plan_events here so the map doesn't grow; the engine thread will
        # also pop it in request_plan_approval after reading _approved_plans.
        ev = self._plan_events.pop(node_id, None)
        if ev:
            ev.set()


class RunManager:
    """Registry and factory for :class:`RunState` objects.

    Creates runs, builds adapters and config, and provides helpers for
    cancellation, history listing, and model discovery.
    """

    def __init__(self) -> None:
        self._runs: Dict[str, RunState] = {}
        self._history: List[str] = []  # run_ids ordered oldest→newest

    # ── public accessors ──────────────────────────────────────────────────────

    def get(self, run_id: str) -> Optional[RunState]:
        """Return the :class:`RunState` for *run_id*, or ``None``."""
        return self._runs.get(run_id)

    def cancel_run(self, run_id: str) -> bool:
        """Signal *run_id* to cancel.  Returns ``True`` if the run exists."""
        run = self._runs.get(run_id)
        if not run:
            return False
        run.cancel()
        return True

    def list_runs(self) -> List[Dict[str, Any]]:
        """Return summary dicts for the most recent runs (newest first)."""
        result = []
        for rid in reversed(self._history):
            run = self._runs.get(rid)
            if not run:
                continue
            result.append(
                {
                    "run_id": rid,
                    "goal": run.goal[:120],
                    "provider": run.provider,
                    "model": run.model,
                    "status": run.status,
                    "started_at": run.started_at,
                    "completed_at": run.completed_at,
                    "event_count": len(run.events),
                }
            )
        return result

    # ── run creation ──────────────────────────────────────────────────────────

    def create_run(
        self,
        goal: str,
        provider: str = "mock",
        model: Optional[str] = None,
        config_overrides: Optional[Dict[str, object]] = None,
        jury_model: Optional[str] = None,
        consortium_agents: Optional[List[Dict[str, Optional[str]]]] = None,
        jury_agents: Optional[List[Dict[str, Optional[str]]]] = None,
        leaf_agents: Optional[List[Dict[str, Optional[str]]]] = None,
        mid_agents: Optional[List[Dict[str, Optional[str]]]] = None,
        root_agents: Optional[List[Dict[str, Optional[str]]]] = None,
        api_key: Optional[str] = None,
    ) -> RunState:
        """Create, register, and immediately start a new run in a daemon thread."""
        run_id = str(uuid.uuid4())
        run = RunState(
            run_id=run_id,
            goal=goal,
            provider=provider,
            model=model,
            jury_model=jury_model,
            consortium_agents=consortium_agents or [],
            jury_agents=jury_agents or [],
            leaf_agents=leaf_agents or [],
            mid_agents=mid_agents or [],
            root_agents=root_agents or [],
            config_overrides=config_overrides or {},
            api_key=api_key,
        )
        self._runs[run_id] = run
        self._history.append(run_id)
        if len(self._history) > _MAX_HISTORY:
            # Prefer evicting the oldest *completed* run; fall back to oldest run
            # if every slot is still active (prevents unbounded history growth).
            evicted = False
            for i, rid in enumerate(self._history):
                candidate = self._runs.get(rid)
                if candidate is None or candidate.status != "running":
                    self._history.pop(i)
                    self._runs.pop(rid, None)
                    evicted = True
                    break
            if not evicted:
                oldest = self._history.pop(0)
                self._runs.pop(oldest, None)

        run.thread = threading.Thread(target=self._execute, args=(run,), daemon=True)
        run.thread.start()
        return run

    # ── model discovery ───────────────────────────────────────────────────────

    def list_models(self) -> Dict[str, Any]:
        """Return all known providers and their models.

        Every provider is always included so users can configure multi-model
        ensembles without needing all API keys upfront.  The ``available``
        list contains only providers whose API key is currently set — the
        frontend uses this to warn about missing keys.
        """
        # Static model catalogue — always returned regardless of API key status.
        # Two providers: "openrouter" for all cloud models, "mock" for local testing.
        all_models: Dict[str, List[str]] = {
            "mock": ["mock-deterministic"],
            "openrouter": [
                "openai/gpt-4.1",
                "openai/gpt-4.1-mini",
                "openai/o3-mini",
                "openai/gpt-5.4-nano",
                "anthropic/claude-3.7-sonnet",
                "anthropic/claude-3.5-sonnet",
                "google/gemini-2.5-pro",
                "google/gemini-2.5-flash",
                "meta-llama/llama-3.3-70b-instruct",
                "mistralai/mistral-large",
                "deepseek/deepseek-chat",
                "deepseek/deepseek-r1",
                "qwen/qwen-2.5-72b-instruct",
                "qwen/qwen3-coder",
                "qwen/qwen3.6-plus",
                "qwen/qwen3.5-35b-a3b",
                "qwen/qwen3.5-9b",
                "z-ai/glm-5.1",
                "stepfun/step-3.5-flash:free",
                "nvidia/nemotron-3-super-120b-a12b:free",
                "nvidia/nemotron-nano-12b-v2-vl:free",
                "qwen/qwen3-next-80b-a3b-instruct:free",
                "qwen/qwen3-coder:free",
                "liquid/lfm-2.5-1.2b-thinking:free",
                "arcee-ai/trinity-large-preview:free",
                "google/gemma-4-26b-a4b-it:free",
                "z-ai/glm-4.5-air:free",
                "moonshotai/kimi-k2-thinking",
                "mistralai/devstral-2512",
                "mistralai/ministral-14b-2512",
                "x-ai/grok-4.1-fast",
            ],
        }
        model_catalog = {
            provider: [
                {
                    "id": model,
                    "label": model.split("/")[-1],
                    "family": self._model_family(provider, model),
                    "tags": self._model_tags(provider, model),
                }
                for model in provider_models
            ]
            for provider, provider_models in all_models.items()
        }

        # All non-mock providers are available — users supply their own API key via the UI.
        available: List[str] = list(all_models.keys())

        priority = ["openrouter", "mock"]
        default_provider = next((p for p in priority if p in available), "mock")
        default_model = all_models[default_provider][0]

        return {
            "providers": list(all_models.keys()),
            "models": all_models,
            "model_catalog": model_catalog,
            "available": available,
            "defaults": {"provider": default_provider, "model": default_model},
        }

    # ── internals ─────────────────────────────────────────────────────────────

    def _model_family(self, provider: str, model: str) -> str:
        """Small display hint for the frontend model browser."""
        if provider == "openrouter" and "/" in model:
            return model.split("/", 1)[0]
        if provider == "mock":
            return "local"
        return provider

    def _model_tags(self, provider: str, model: str) -> List[str]:
        """Classify known model ids for display only; adapter behavior is unchanged."""
        tags: List[str] = []
        name = model.lower()
        if provider == "openrouter":
            tags.append("router")
        if ":free" in name:
            tags.append("free")
        if any(part in name for part in ["r1", "reason", "thinking", "o3"]):
            tags.append("reasoning")
        if any(part in name for part in ["flash", "mini", "nano", "haiku", "instant"]):
            tags.append("fast")
        if any(part in name for part in ["coder", "code"]):
            tags.append("coding")
        if not tags:
            tags.append("general")
        return tags

    def _build_adapter(self, provider: str, model: Optional[str], api_key: Optional[str] = None) -> object:
        """Instantiate the LLM adapter for the given provider.

        Supported providers: ``"openrouter"`` (all cloud models via OpenRouter API),
        ``"mock"`` (local deterministic testing — no API key needed).

        *api_key* overrides the environment variable when supplied (user-provided key flow).
        """
        name = (provider or "mock").lower()

        if name == "openrouter":
            from raf.llm.openrouter_adapter import OpenRouterAdapter
            resolved_key = api_key or os.getenv("OPENROUTER_API_KEY")
            if not resolved_key:
                raise RuntimeError("An OpenRouter API key is required. Paste yours into the key field in the UI.")
            model_name = model or "stepfun/step-3.5-flash:free"
            temperature = float(os.getenv("OPENROUTER_TEMPERATURE", "0.2"))
            return OpenRouterAdapter(api_key=resolved_key, model_name=model_name, temperature=temperature)

        return MockAdapter()

    def _build_config(self, overrides: Dict[str, object]) -> RafConfig:
        """Build a :class:`RafConfig` by applying non-None overrides from the API request."""
        config = RafConfig()
        for attr in (
            "consortium_size", "jury_size", "max_depth",
            "max_parallel_children", "max_nodes_total",
        ):
            
            value = overrides.get(attr)
            if value is not None and value > 0:
                setattr(config, attr, value)

        system_prompt = overrides.get("system_prompt")
        if isinstance(system_prompt, str) and system_prompt.strip():
            config.system_prompt = system_prompt.strip()

        if overrides.get("plan_approval_required"):
            config.plan_approval_required = True

        plan_recovery = overrides.get("plan_recovery")
        if isinstance(plan_recovery, str) and plan_recovery in {"off", "auto", "ask"}:
            config.plan_recovery = plan_recovery

        max_plan_retries = overrides.get("max_plan_retries")
        if isinstance(max_plan_retries, int) and max_plan_retries >= 0:
            config.max_plan_retries = max_plan_retries

        retry_limit = overrides.get("retry_limit")
        if isinstance(retry_limit, int) and retry_limit >= 0:
            config.retry_limit = retry_limit

        timeout_by_task = overrides.get("timeout_by_task")
        if isinstance(timeout_by_task, dict):
            for task, seconds in timeout_by_task.items():
                if isinstance(task, str) and isinstance(seconds, int) and seconds > 0:
                    config.timeout_by_task[task] = seconds

        if overrides.get("tools_enabled"):
            config.tools_enabled = True

        if overrides.get("force_recursive"):
            config.force_recursive = True

        clarify = overrides.get("clarify_before_execute")
        if isinstance(clarify, bool):
            config.clarify_before_execute = clarify

        domain = overrides.get("domain")
        if isinstance(domain, str) and domain:
            config.domain = domain

        return config

    def _execute(self, run: RunState) -> None:
        """Entry point for the background daemon thread that runs the engine."""
        try:
            config = self._build_config(run.config_overrides)
            # Expose the run-specific limit so approve_plan() validates correctly.
            run.max_children_per_plan = config.max_children_per_plan

            # Build per-slot adapter lists.
            # If consortium_agents/jury_agents are specified, each slot gets its own model.
            # Otherwise fall back to a single adapter replicated across all slots
            # (RafEngine handles the replication internally).
            key = run.api_key  # user-supplied key (may be None — falls back to env var)

            if run.consortium_agents:
                consortium_adapters = [
                    self._build_adapter(a["provider"], a.get("model"), key)
                    for a in run.consortium_agents
                ]
            else:
                consortium_adapters = self._build_adapter(run.provider, run.model, key)

            if run.jury_agents:
                jury_adapters = [
                    self._build_adapter(a["provider"], a.get("model"), key)
                    for a in run.jury_agents
                ]
            elif run.jury_model:
                jury_adapters = self._build_adapter(run.provider, run.jury_model, key)
            else:
                jury_adapters = None  # engine defaults to consortium adapters

            trace = TraceLogger(emit=run.emit, store=False, quiet=True)

            on_plan_ready = run.request_plan_approval if config.plan_approval_required else None

            # Build optional fallback adapter — used when all primary consortium/jury
            # agents time out and zero results are available.
            fallback_adapter = None
            fb_provider = getattr(config, "fallback_provider", "")
            fb_model = getattr(config, "fallback_model", "") or None
            if fb_provider:
                try:
                    fallback_adapter = self._build_adapter(fb_provider, fb_model, key)
                except Exception:
                    pass  # missing key — run without fallback

            # ── Tier adapter lists for depth-based model routing ───────────────
            # When tier agents are provided: leaf → workers, mid → planners,
            # root → referee/analysis.  When empty, each tier falls back to the
            # flat consortium/jury adapters inside RafEngine.
            #
            # The mid-tier adapters also serve as jury for the leaf tier
            # (jury floor rule: weak models must not judge weak models).
            # The root-tier adapters serve as jury for root/analysis decisions.
            def _build_tier(agents):
                """Build an adapter list from a list of {provider, model} dicts."""
                if not agents:
                    return None
                return [self._build_adapter(a["provider"], a.get("model"), key) for a in agents]

            leaf_adapters = _build_tier(run.leaf_agents)
            mid_adapters = _build_tier(run.mid_agents)
            root_adapters = _build_tier(run.root_agents)
            # Jury tiers — same objects as mid/root adapters (see RafEngine docstring)
            mid_jury_adapters = mid_adapters   # jury floor for Tier 0 + Tier 1
            root_jury_adapters = root_adapters  # jury for Tier 2 analysis/root

            engine = RafEngine(
                config, consortium_adapters, trace,
                jury_adapters=jury_adapters,
                on_plan_ready=on_plan_ready,
                cancel_event=run.cancel_event,
                fallback_adapter=fallback_adapter,
                leaf_adapters=leaf_adapters,
                mid_adapters=mid_adapters,
                root_adapters=root_adapters,
                mid_jury_adapters=mid_jury_adapters,
                root_jury_adapters=root_jury_adapters,
            )
            result = engine.run(run.goal)
            run.result = result
            run.status = "cancelled" if run.cancel_event.is_set() else "done"
        except Exception as exc:
            run.status = "error"
            run.error = str(exc)
        finally:
            run.completed_at = time.time()
            run.emit(
                {
                    "event": "run_done",
                    "status": run.status,
                    "run_id": run.run_id,
                    "error": run.error,
                    "result": run.result,
                }
            )

    async def stream_events(self, run: RunState):
        """Async generator that yields all events for a run.

        First replays already-completed events from the in-memory list, then
        drains the live queue until ``run_done`` is emitted.
        """
        sent = 0
        for event in run.events:
            yield event
            sent += 1
        # Drain already-replayed events from the queue to avoid duplicates
        from queue import Empty
        for _ in range(sent):
            try:
                run.queue.get_nowait()
            except Empty:
                break
        while True:
            event = await asyncio.to_thread(run.queue.get)
            yield event
            if event.get("event") == "run_done":
                break
