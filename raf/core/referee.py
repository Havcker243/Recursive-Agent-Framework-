"""
raf.core.referee
================
Deterministic state-grounded referee that runs after every node completes.

The referee is NOT an agent — it does not vote, does not join the consortium,
and cannot be persuaded by prose.  It computes objective facts about run
progress and injects them as read-only context into every subsequent agent
payload via the ``_referee`` key.

Two operating modes
-------------------
Structured tasks (Hanoi, N-Queens, Sudoku, …)
    Canonical state derived from output text. Hanoi moves are simulated step
    by step; illegal placements trigger an invariant violation.  Progress is
    1.0 when the goal state is detected in the output.

Open-ended tasks (planning, analysis, writing, …)
    Requirements are extracted from the root goal via a single cheap LLM call
    (no consortium, no jury — one deterministic shot, result cached).
    Subsequent evaluations call the LLM once to check which requirements are
    covered and which are missing.  Accumulated outputs are hashed so agents
    can detect repetition or contradiction.

Thread safety
-------------
``evaluate()`` is safe to call concurrently from parallel child threads.
All shared mutable state is protected by per-attribute locks.
"""

import hashlib
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── patterns that mark a task as structured ────────────────────────────────────

_STRUCTURED_PATTERNS = [
    r"^HANOI\(",
    r"\btowers?\s+of\s+hanoi\b",
    r"\bhanoi\b",
    r"\bn-?queens?\b",
    r"\bsudoku\b",
    r"\bknapsack\b",
]


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ── report ─────────────────────────────────────────────────────────────────────

@dataclass
class RefereeReport:
    """Immutable snapshot of run progress produced after each node completes.

    Injected as ``_referee`` into every subsequent agent payload so all agents
    receive identical, externally computed facts — not agent opinions.

    Attributes
    ----------
    state_hash:
        SHA-256 prefix of the accumulated canonical output state.
        Changes whenever new content is added; stable when outputs repeat.
    progress:
        Estimated completion ratio (0.0–1.0).
    covered:
        Requirements / goals satisfied so far.
    missing:
        Requirements / goals still outstanding.
    invariant_ok:
        False when a structural rule was violated (e.g. illegal disk placement).
    invariant_error:
        Human-readable description of the violation; empty when ok.
    is_structured:
        True for Hanoi / puzzle-style tasks, False for open-ended.
    step:
        How many nodes have been evaluated by this referee so far.
    """

    state_hash: str
    progress: float
    covered: List[str]
    missing: List[str]
    invariant_ok: bool
    invariant_error: str
    is_structured: bool
    step: int


# ── referee ────────────────────────────────────────────────────────────────────

class Referee:
    """Deterministic progress referee — runs outside the consortium/jury loop.

    Parameters
    ----------
    root_goal:
        The top-level goal string for this run.
    adapter:
        A ``ModelAdapter`` used for the single-shot requirements-extraction and
        coverage-check LLM calls (open-ended tasks only).  When ``None`` the
        referee degrades gracefully to hash-only mode with no LLM calls.
    """

    def __init__(self, root_goal: str, adapter=None) -> None:
        self.root_goal = root_goal
        self.adapter = adapter
        self._is_structured = self._detect_structured(root_goal)

        # Accumulated node outputs — appended after each evaluation.
        self._outputs: List[str] = []
        self._outputs_lock = threading.Lock()

        # Requirements extracted once from the root goal (open-ended only).
        self._requirements: List[str] = []
        self._req_lock = threading.Lock()
        self._req_fetched = False

        # Monotonically increasing step counter.
        self._step = 0
        self._step_lock = threading.Lock()

    # ── task type detection ────────────────────────────────────────────────────

    @staticmethod
    def _detect_structured(goal: str) -> bool:
        for pattern in _STRUCTURED_PATTERNS:
            if re.search(pattern, goal, re.IGNORECASE):
                return True
        return False

    # ── structured task: Hanoi invariant checker ───────────────────────────────

    def _check_hanoi(self, output: str) -> tuple:
        """Simulate Hanoi moves found in *output*.

        Returns ``(True, "")`` on success or ``(False, error_message)`` on
        the first illegal move detected.
        """
        moves = re.findall(
            r"move disk (\d+) from (?:peg )?(\d+) to (?:peg )?(\d+)",
            output,
            re.IGNORECASE,
        )
        if not moves:
            return True, ""

        # Detect disk count from goal, e.g. HANOI(3,0,2,1)
        m = re.search(r"HANOI\((\d+)", self.root_goal, re.IGNORECASE)
        n_disks = int(m.group(1)) if m else 3
        pegs: List[List[int]] = [list(range(n_disks, 0, -1)), [], []]

        for disk_s, from_s, to_s in moves:
            disk, frm, to = int(disk_s), int(from_s), int(to_s)
            if frm < 0 or frm > 2 or to < 0 or to > 2:
                return False, f"Invalid peg index: from={frm} to={to}"
            if not pegs[frm]:
                return False, f"Move from empty peg {frm}"
            if pegs[frm][-1] != disk:
                return False, (
                    f"Top of peg {frm} is disk {pegs[frm][-1]}, expected disk {disk}"
                )
            if pegs[to] and pegs[to][-1] < disk:
                return False, (
                    f"Cannot place disk {disk} on smaller disk {pegs[to][-1]} at peg {to}"
                )
            pegs[to].append(pegs[frm].pop())

        return True, ""

    def _structured_report(
        self, accumulated: str, output: str, step: int
    ) -> RefereeReport:
        state_hash = _sha(accumulated)
        ok, err = self._check_hanoi(output)
        done = bool(
            re.search(
                r"\b(done|complete|solved|goal.?reached|finished)\b",
                output,
                re.IGNORECASE,
            )
        )
        progress = 1.0 if done else 0.5
        return RefereeReport(
            state_hash=state_hash,
            progress=progress,
            covered=["execution_valid"] if ok else [],
            missing=[] if done else ["goal_not_reached"],
            invariant_ok=ok,
            invariant_error=err,
            is_structured=True,
            step=step,
        )

    # ── open-ended task: requirement extraction + coverage ─────────────────────

    def _ensure_requirements(self) -> List[str]:
        """Extract requirements from the root goal exactly once (cached LLM call)."""
        with self._req_lock:
            if self._req_fetched:
                return list(self._requirements)
            # Mark as fetched before the LLM call to prevent duplicate calls
            # from concurrent threads.
            self._req_fetched = True

        if not self.adapter:
            reqs = [self.root_goal[:120]]
        else:
            try:
                from raf.llm.json_utils import call_json_with_repair

                def _req_validator(x: Dict[str, Any]) -> Dict[str, Any]:
                    if not isinstance(x.get("requirements"), list):
                        raise ValueError("missing 'requirements' list")
                    return x

                result = call_json_with_repair(
                    self.adapter,
                    "coverage_check",
                    {
                        "goal": self.root_goal,
                        "extract_only": True,
                        "_raf_role": "referee",
                    },
                    _req_validator,
                    1,
                )
                reqs = [str(r) for r in result.get("requirements", []) if r][:12]
                if not reqs:
                    reqs = [self.root_goal[:120]]
            except Exception:
                reqs = [self.root_goal[:120]]

        with self._req_lock:
            self._requirements = reqs
        return reqs

    def _open_ended_report(self, accumulated: str, step: int) -> RefereeReport:
        state_hash = _sha(accumulated)
        reqs = self._ensure_requirements()

        if not self.adapter:
            return RefereeReport(
                state_hash=state_hash,
                progress=0.0,
                covered=[],
                missing=reqs,
                invariant_ok=True,
                invariant_error="",
                is_structured=False,
                step=step,
            )

        try:
            from raf.llm.json_utils import call_json_with_repair

            def _cov_validator(x: Dict[str, Any]) -> Dict[str, Any]:
                if not isinstance(x.get("covered"), list):
                    raise ValueError("missing 'covered' list")
                return x

            result = call_json_with_repair(
                self.adapter,
                "coverage_check",
                {
                    "goal": self.root_goal,
                    "requirements": reqs,
                    "output_so_far": accumulated[-3000:],
                    "_raf_role": "referee",
                },
                _cov_validator,
                1,
            )
            covered = [str(c) for c in result.get("covered", [])]
            missing = [str(m) for m in result.get("missing", reqs)]
            progress = float(
                result.get("progress_score", len(covered) / max(1, len(reqs)))
            )
        except Exception:
            covered, missing, progress = [], reqs, 0.0

        return RefereeReport(
            state_hash=state_hash,
            progress=min(1.0, max(0.0, progress)),
            covered=covered,
            missing=missing,
            invariant_ok=True,
            invariant_error="",
            is_structured=False,
            step=step,
        )

    # ── public API ─────────────────────────────────────────────────────────────

    def evaluate(self, output: str) -> RefereeReport:
        """Evaluate a node's output and return a :class:`RefereeReport`.

        Thread-safe — may be called concurrently from parallel child threads.
        """
        with self._outputs_lock:
            self._outputs.append(output)
            accumulated = "\n".join(self._outputs)

        with self._step_lock:
            self._step += 1
            step = self._step

        if self._is_structured:
            return self._structured_report(accumulated, output, step)
        return self._open_ended_report(accumulated, step)

    def to_context(self, report: RefereeReport) -> Dict[str, Any]:
        """Return the dict injected into agent payloads as ``_referee``."""
        return {
            "state_hash": report.state_hash,
            "progress": round(report.progress, 3),
            "covered": report.covered,
            "missing": report.missing,
            "invariant_ok": report.invariant_ok,
            "invariant_error": report.invariant_error,
            "step": report.step,
        }
