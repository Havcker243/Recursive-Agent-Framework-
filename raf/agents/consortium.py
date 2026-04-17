"""
raf.agents.consortium
=====================
The Consortium runs one LLM agent per adapter slot, each producing a
structured candidate answer.  Agents receive the same payload but a different
``_agent_index``, which the adapter can use to vary temperature and inject a
different persona — producing genuinely diverse proposals before the
:class:`~raf.agents.jury.Jury` votes on the best one.

When a list of adapters is supplied each slot uses its own model (true
multi-model ensemble).  When a single adapter is supplied it is used for all
slots (original behaviour — preserved for backward compatibility).

Failures are isolated: if one agent call fails, the others still contribute.
Only a total failure (all agents crash) raises an exception.

All agent calls run in parallel via ThreadPoolExecutor.

Early exit
----------
``call()`` accepts an optional ``early_exit_fn`` callback.  After each agent
result arrives, the callback is invoked with the current result list.  If it
returns True, the consortium stops waiting for remaining agents immediately —
those agents continue running in the background (Python threads cannot be
force-killed) but their results are discarded.  This prevents the slowest
model from bottlenecking the whole consortium when faster agents already
agree.

Use early exit only for binary decisions (e.g. mode_decision) where two
agreeing agents are sufficient.  Do NOT use it for plan/base_execute where
proposal diversity is the entire point.
"""

from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import time
from typing import Any, Callable, Dict, List, Optional, Union

from raf.core.trace import TraceLogger
from raf.llm.adapter import ModelAdapter
from raf.llm.json_utils import ModelCallError, call_json_with_repair


def _adapter_meta(adapter: ModelAdapter) -> Dict[str, str]:
    provider = adapter.__class__.__name__.replace("Adapter", "").lower() or "unknown"
    return {
        "provider": provider,
        "model": str(getattr(adapter, "model_name", provider)),
    }


class Consortium:
    """Generate multiple candidate proposals via independent LLM agent calls.

    Parameters
    ----------
    adapters:
        A single :class:`ModelAdapter` (used for every slot) **or** a list of
        adapters (one per slot).  Pass a list to run a true multi-model
        ensemble where each agent uses a different model.
    task:
        Task name string passed to the adapter's prompt template (e.g. ``"plan"``).
    retry_limit:
        JSON repair retries per agent call.
    """

    def __init__(
        self,
        adapters: Union[ModelAdapter, List[ModelAdapter]],
        task: str,
        retry_limit: int,
        trace: Optional[TraceLogger] = None,
        node_id: Optional[str] = None,
        depth: Optional[int] = None,
        timeout_s: Optional[float] = None,
        fallback_adapter: Optional[ModelAdapter] = None,
    ) -> None:
        self.adapters: List[ModelAdapter] = (
            adapters if isinstance(adapters, list) else [adapters]
        )
        self.task = task
        self.retry_limit = retry_limit
        self.trace = trace
        self.node_id = node_id
        self.depth = depth
        self.timeout_s = timeout_s
        # Fallback: used when ALL primary agents time out and 0 results are available.
        # A single synchronous call to this adapter is attempted before giving up.
        self.fallback_adapter: Optional[ModelAdapter] = fallback_adapter

    @property
    def size(self) -> int:
        return len(self.adapters)

    def call(
        self,
        payload: Dict[str, Any],
        validator: Callable[[Dict[str, Any]], Dict[str, Any]],
        early_exit_fn: Optional[Callable[[List[Dict[str, Any]]], bool]] = None,
    ) -> List[Dict[str, Any]]:
        """Call all agents in parallel and return a list of validated candidate dicts.

        Each agent receives *payload* plus ``_agent_index``, ``_agent_total``,
        and ``_raf_role`` so the adapter can vary temperature, inject a
        different persona, and frame the agent's role in the RAF system.

        Parameters
        ----------
        payload:
            Task payload dict.  Meta-keys (``_``-prefixed) are stripped by the
            adapter before serialisation.
        validator:
            Schema validator called on each raw agent response.
        early_exit_fn:
            Optional callable ``(current_results) -> bool``.  Called after each
            agent result arrives.  When it returns True, the consortium stops
            collecting results immediately — faster agents effectively short-
            circuit the wait for slower ones.  Remaining agents continue in
            background threads but their results are discarded.

        Raises
        ------
        RuntimeError
            If every agent call fails.
        """
        def _run_agent(i: int) -> Dict[str, Any]:
            adapter = self.adapters[i]
            meta = _adapter_meta(adapter)
            agent_payload = dict(payload)
            agent_payload["_raf_role"]    = "consortium"
            agent_payload["_agent_index"] = i
            agent_payload["_agent_total"] = self.size
            started = time.time()
            if self.trace:
                self.trace.log({
                    "event": "model_call_start",
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "task": self.task,
                    "role": "consortium",
                    "provider": meta["provider"],
                    "model": meta["model"],
                    "agent_index": i,
                    "attempt": 1,
                })
            try:
                result = call_json_with_repair(
                    adapter, self.task, agent_payload, validator, self.retry_limit
                )
                if self.trace:
                    self.trace.log({
                        "event": "model_call_done",
                        "node_id": self.node_id,
                        "depth": self.depth,
                        "task": self.task,
                        "role": "consortium",
                        "provider": meta["provider"],
                        "model": meta["model"],
                        "agent_index": i,
                        "attempt": 1,
                        "duration_ms": int((time.time() - started) * 1000),
                    })
                return result
            except Exception as exc:
                if self.trace:
                    cause = exc.cause if isinstance(exc, ModelCallError) else "api_error"
                    self.trace.log({
                        "event": "model_call_failed",
                        "node_id": self.node_id,
                        "depth": self.depth,
                        "task": self.task,
                        "role": "consortium",
                        "provider": meta["provider"],
                        "model": meta["model"],
                        "agent_index": i,
                        "attempt": 1,
                        "duration_ms": int((time.time() - started) * 1000),
                        "cause": cause,
                        "error": str(exc),
                    })
                raise

        def _run_indexed(i: int):
            return i, _run_agent(i)

        results: List[Dict[str, Any]] = []
        # Use manual executor (not context manager) so we can exit early without
        # blocking on remaining futures.  shutdown(wait=False) releases the calling
        # thread immediately; background threads finish their current API call on
        # their own and then terminate naturally.
        executor = ThreadPoolExecutor(max_workers=self.size)
        try:
            futures = {executor.submit(_run_indexed, i): i for i in range(self.size)}
            pending = set(futures)
            deadline = time.time() + self.timeout_s if self.timeout_s and self.timeout_s > 0 else None
            while pending:
                wait_timeout = None if deadline is None else max(0.0, deadline - time.time())
                if deadline is not None and wait_timeout <= 0:
                    break
                done, pending = wait(pending, timeout=wait_timeout, return_when=FIRST_COMPLETED)
                if not done:
                    break
                for future in done:
                    try:
                        idx, result = future.result()
                        # Embed the source adapter index so callers can route follow-up
                        # calls (e.g. tool loops) to the same model that won the vote.
                        result["_adapter_index"] = idx
                        results.append(result)
                    except Exception:
                        pass
                if early_exit_fn is not None and early_exit_fn(results):
                    break  # enough results â€” don't wait for slower agents
            if pending and self.timeout_s and self.timeout_s > 0:
                for future in pending:
                    idx = futures[future]
                    future.cancel()
                    meta = _adapter_meta(self.adapters[idx])
                    if self.trace:
                        self.trace.log({
                            "event": "model_call_timeout",
                            "node_id": self.node_id,
                            "depth": self.depth,
                            "task": self.task,
                            "role": "consortium",
                            "provider": meta["provider"],
                            "model": meta["model"],
                            "agent_index": idx,
                            "attempt": 1,
                            "timeout_ms": int(self.timeout_s * 1000),
                        })
            for future in ():
                continue
                try:
                    idx, result = future.result()
                    # Embed the source adapter index so callers can route follow-up
                    # calls (e.g. tool loops) to the same model that won the vote.
                    result["_adapter_index"] = idx
                    results.append(result)
                except Exception:
                    pass
                if early_exit_fn is not None and early_exit_fn(results):
                    break  # enough results — don't wait for slower agents
        finally:
            executor.shutdown(wait=False)

        if not results and self.fallback_adapter is not None:
            results = self._call_fallback(payload, validator)

        if not results:
            raise RuntimeError(f"Consortium '{self.task}': all {self.size} agent calls failed")
        return results

    def _call_fallback(
        self,
        payload: Dict[str, Any],
        validator: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Single synchronous fallback call when all primary agents timed out.

        Emits ``model_call_fallback`` so the UI can surface which model saved the
        run.  Returns a single-element list on success, or an empty list on failure
        (the caller decides whether that triggers a RuntimeError).
        """
        adapter = self.fallback_adapter
        meta = _adapter_meta(adapter)
        started = time.time()
        if self.trace:
            self.trace.log({
                "event": "model_call_fallback",
                "node_id": self.node_id,
                "depth": self.depth,
                "task": self.task,
                "role": "consortium",
                "provider": meta["provider"],
                "model": meta["model"],
                "reason": "all primary agents timed out",
            })
        try:
            fallback_payload = dict(payload)
            fallback_payload["_raf_role"] = "consortium_fallback"
            fallback_payload["_agent_index"] = 0
            fallback_payload["_agent_total"] = 1
            result = call_json_with_repair(
                adapter, self.task, fallback_payload, validator, self.retry_limit
            )
            result["_adapter_index"] = 0
            result["_fallback"] = True
            if self.trace:
                self.trace.log({
                    "event": "model_call_done",
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "task": self.task,
                    "role": "consortium_fallback",
                    "provider": meta["provider"],
                    "model": meta["model"],
                    "agent_index": 0,
                    "attempt": 1,
                    "duration_ms": int((time.time() - started) * 1000),
                })
            return [result]
        except Exception as exc:
            if self.trace:
                cause = exc.cause if isinstance(exc, ModelCallError) else "api_error"
                self.trace.log({
                    "event": "model_call_failed",
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "task": self.task,
                    "role": "consortium_fallback",
                    "provider": meta["provider"],
                    "model": meta["model"],
                    "agent_index": 0,
                    "attempt": 1,
                    "duration_ms": int((time.time() - started) * 1000),
                    "cause": cause,
                    "error": str(exc),
                })
            return []


def mode_decision_early_exit(results: List[Dict[str, Any]]) -> bool:
    """Early-exit function for mode_decision consortiums.

    Returns True (stop collecting) when a strict majority of received results
    agree on the same mode.  With 3 agents this fires as soon as 2 agree —
    the fastest two models short-circuit the wait for the slowest.

    Only used for mode_decision because it is a binary choice (base/recursive)
    where two agreeing agents are highly reliable.  Plan and base_execute
    benefit from full proposal diversity and should NOT use early exit.
    """
    if len(results) < 2:
        return False  # need at least 2 results before making a majority call
    counts = Counter(r.get("mode") for r in results if r.get("mode"))
    if not counts:
        return False
    top_count = counts.most_common(1)[0][1]
    majority = len(results) // 2 + 1  # strict majority of results so far
    return top_count >= majority
