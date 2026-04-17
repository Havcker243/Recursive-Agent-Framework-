"""
raf.agents.jury
===============
The Jury runs one LLM agent per adapter slot, each casting a structured vote
over a set of labeled options produced by a :class:`~raf.agents.consortium.Consortium`.

When a list of adapters is supplied each jury seat uses its own model (true
multi-model voting).  When a single adapter is supplied it is used for all
seats (original behaviour).

Voting uses **confidence-weighted aggregation**: instead of counting raw vote
counts, each vote contributes the voter's reported confidence score to the
running total for its chosen winner.  This means a high-confidence minority
can outweigh a low-confidence majority.

All jury calls run in parallel via ThreadPoolExecutor.
"""

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from raf.core.trace import TraceLogger
from raf.llm.adapter import ModelAdapter
from raf.llm.json_utils import ModelCallError, call_json_with_repair
from raf.schemas import validate_vote_result


def _adapter_meta(adapter: ModelAdapter) -> Dict[str, str]:
    provider = adapter.__class__.__name__.replace("Adapter", "").lower() or "unknown"
    return {
        "provider": provider,
        "model": str(getattr(adapter, "model_name", provider)),
    }


class Jury:
    """Aggregate votes from multiple LLM agents to select the best option.

    Parameters
    ----------
    adapters:
        A single :class:`ModelAdapter` (used for every seat) **or** a list of
        adapters (one per seat).  Pass a list for true multi-model voting.
    retry_limit:
        JSON repair retries per agent call.
    system_prompt:
        Optional system prompt injected into every jury call.
    """

    def __init__(
        self,
        adapters: Union[ModelAdapter, List[ModelAdapter]],
        retry_limit: int,
        system_prompt: str = "",
        trace: Optional[TraceLogger] = None,
        node_id: Optional[str] = None,
        depth: Optional[int] = None,
        timeout_s: Optional[float] = None,
        fallback_adapter: Optional[ModelAdapter] = None,
    ) -> None:
        self.adapters: List[ModelAdapter] = (
            adapters if isinstance(adapters, list) else [adapters]
        )
        self.retry_limit = retry_limit
        self.system_prompt = system_prompt
        self.trace = trace
        self.node_id = node_id
        self.depth = depth
        self.timeout_s = timeout_s
        self.fallback_adapter: Optional[ModelAdapter] = fallback_adapter

    @property
    def size(self) -> int:
        return len(self.adapters)

    @staticmethod
    def unanimous(candidates: List[Dict[str, Any]], key: str) -> Optional[str]:
        """Return the unanimous value for *key* across all candidates, or None if they differ.

        Used to skip the jury call when all consortium agents agree — saving
        jury_size LLM calls per decision.
        """
        if not candidates:
            return None
        values = [str(c.get(key, "")) for c in candidates]
        return values[0] if len(set(values)) == 1 else None

    def vote(
        self,
        options: List[Dict[str, Any]],
        node_context: Optional[Dict[str, Any]] = None,
        task: str = "vote",
    ) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Ask all jury agents to vote in parallel, then return the winner.

        Parameters
        ----------
        options:
            Candidate proposals from the Consortium (raw payload dicts).
        node_context:
            Optional dict of RAF meta-keys merged into every jury agent's
            payload so the frame shows the full run context.

        Returns
        -------
        winner:
            Payload of the winning option.
        aggregate:
            ``{"winner_id", "ranked", "confidence"}`` summary.
        votes:
            Raw vote dicts from each agent (for the trace log).
        labeled:
            Options with ``option_id`` labels attached (for the trace log).
        """
        labeled = [{"option_id": f"option-{i}", "payload": opt} for i, opt in enumerate(options)]

        base_payload = {
            "options": labeled,
            "system_prompt": self.system_prompt,
            **(node_context or {}),
        }

        def _cast_vote(i: int) -> Dict[str, Any]:
            adapter = self.adapters[i]
            meta = _adapter_meta(adapter)
            vote_payload = dict(base_payload)
            vote_payload["_raf_role"]    = "jury"
            vote_payload["_agent_index"] = i
            vote_payload["_agent_total"] = self.size
            started = time.time()
            if self.trace:
                self.trace.log({
                    "event": "model_call_start",
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "task": task,
                    "role": "jury",
                    "provider": meta["provider"],
                    "model": meta["model"],
                    "agent_index": i,
                    "attempt": 1,
                })
            try:
                result = call_json_with_repair(
                    adapter, "vote", vote_payload, validate_vote_result, self.retry_limit
                )
                if self.trace:
                    self.trace.log({
                        "event": "model_call_done",
                        "node_id": self.node_id,
                        "depth": self.depth,
                        "task": task,
                        "role": "jury",
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
                        "task": task,
                        "role": "jury",
                        "provider": meta["provider"],
                        "model": meta["model"],
                        "agent_index": i,
                        "attempt": 1,
                        "duration_ms": int((time.time() - started) * 1000),
                        "cause": cause,
                        "error": str(exc),
                    })
                raise

        votes: List[Dict[str, Any]] = []
        executor = ThreadPoolExecutor(max_workers=self.size)
        try:
            futures = {executor.submit(_cast_vote, i): i for i in range(self.size)}
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
                    agent_id = futures[future]
                    try:
                        votes.append({"agent_id": agent_id, "vote": future.result()})
                    except Exception:
                        pass
            if pending and self.timeout_s and self.timeout_s > 0:
                for future in pending:
                    agent_id = futures[future]
                    future.cancel()
                    meta = _adapter_meta(self.adapters[agent_id])
                    if self.trace:
                        self.trace.log({
                            "event": "model_call_timeout",
                            "node_id": self.node_id,
                            "depth": self.depth,
                            "task": task,
                            "role": "jury",
                            "provider": meta["provider"],
                            "model": meta["model"],
                            "agent_index": agent_id,
                            "attempt": 1,
                            "timeout_ms": int(self.timeout_s * 1000),
                        })
        finally:
            executor.shutdown(wait=False)

        if not votes and self.fallback_adapter is not None:
            votes = self._cast_fallback_vote(base_payload, labeled, task)

        if not votes:
            raise RuntimeError(f"Jury: all {self.size} vote calls failed")

        aggregate = self._aggregate_votes(votes, labeled)

        winner = None
        for item in labeled:
            if item["option_id"] == aggregate["winner_id"]:
                winner = item["payload"]
                break
        if winner is None and labeled:
            winner = labeled[0]["payload"]
        return winner, aggregate, votes, labeled

    def _cast_fallback_vote(
        self,
        base_payload: Dict[str, Any],
        labeled: List[Dict[str, Any]],
        task: str,
    ) -> List[Dict[str, Any]]:
        """Single synchronous fallback vote when all primary jurors timed out."""
        adapter = self.fallback_adapter
        meta = _adapter_meta(adapter)
        started = time.time()
        if self.trace:
            self.trace.log({
                "event": "model_call_fallback",
                "node_id": self.node_id,
                "depth": self.depth,
                "task": task,
                "role": "jury",
                "provider": meta["provider"],
                "model": meta["model"],
                "reason": "all primary jurors timed out",
            })
        try:
            fallback_payload = dict(base_payload)
            fallback_payload["_raf_role"] = "jury_fallback"
            fallback_payload["_agent_index"] = 0
            fallback_payload["_agent_total"] = 1
            result = call_json_with_repair(
                adapter, "vote", fallback_payload, validate_vote_result, self.retry_limit
            )
            if self.trace:
                self.trace.log({
                    "event": "model_call_done",
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "task": task,
                    "role": "jury_fallback",
                    "provider": meta["provider"],
                    "model": meta["model"],
                    "agent_index": 0,
                    "attempt": 1,
                    "duration_ms": int((time.time() - started) * 1000),
                })
            return [{"agent_id": 0, "vote": result}]
        except Exception as exc:
            if self.trace:
                cause = exc.cause if isinstance(exc, ModelCallError) else "api_error"
                self.trace.log({
                    "event": "model_call_failed",
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "task": task,
                    "role": "jury_fallback",
                    "provider": meta["provider"],
                    "model": meta["model"],
                    "agent_index": 0,
                    "attempt": 1,
                    "duration_ms": int((time.time() - started) * 1000),
                    "cause": cause,
                    "error": str(exc),
                })
            return []

    def _aggregate_votes(self, votes: List[Dict[str, Any]], labeled: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Confidence-weighted vote aggregation.

        For each vote, the voter's reported ``confidence`` score is added to a
        running total for the chosen ``winner_id``.  The option with the highest
        total weighted score wins.
        """
        if not votes:
            return {"winner_id": "", "ranked": [], "confidence": 0.0}

        weighted: Dict[str, float] = {}
        confidence_total = 0.0
        score_map: Dict[str, List[int]] = {item["option_id"]: [] for item in labeled}

        for item in votes:
            vote = item["vote"]
            winner_id = vote.get("winner_id", "")
            conf = float(vote.get("confidence", 0.0))
            weighted[winner_id] = weighted.get(winner_id, 0.0) + conf
            confidence_total += conf
            for ranked in vote.get("ranked", []):
                option_id = ranked.get("option_id")
                score = ranked.get("score")
                if option_id in score_map and isinstance(score, int):
                    score_map[option_id].append(score)

        winner_id = max(weighted.items(), key=lambda p: p[1])[0] if weighted else ""

        ranked = []
        for option_id, scores in score_map.items():
            avg_score = sum(scores) / len(scores) if scores else 0.0
            ranked.append({"option_id": option_id, "avg_score": avg_score, "votes": len(scores)})
        ranked.sort(key=lambda item: item["avg_score"], reverse=True)

        confidence = confidence_total / max(1, len(votes))
        return {"winner_id": winner_id, "ranked": ranked, "confidence": float(confidence)}
