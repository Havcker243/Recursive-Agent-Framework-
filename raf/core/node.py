"""
raf.core.node
=============
Core execution units for the Recursive Agent Framework.

RafNode
    A single task node. Decides whether to execute directly (base) or split
    into child nodes (recursive), then runs itself accordingly.

RafEngine
    Orchestrator. Holds global config, adapters, trace logger, node budget,
    and the optional cancellation signal. Creates all nodes and is the single
    source of truth for remaining budget.

Decision flow at every node
    1. _maybe_clarify   – ask user if goal is ambiguous (root only, optional)
    2. _decide_mode     – Consortium proposes base/recursive, Jury votes
    3a. _execute_base   – Consortium proposes outputs, Jury votes, optional tool loop + scope check
    3b. _execute_recursive
                        – _plan_children (Consortium+Jury) →
                          optional human approval →
                          _refine_children (Consortium+Jury per child) →
                          parallel child execution →
                          merge (Consortium+Jury) →
                          _analyze (Consortium+Jury)

Spec / Ledger / Repair machinery (added in session 9)
------------------------------------------------------
Three new systems protect goal integrity across the entire execution tree:

1. Spec (raf.core.spec.Spec)
   Extracted once from the root goal by RafEngine.run() before the root node
   is created.  Contains required items, forbidden items, and success criteria.
   Attached to the engine as ``self.spec`` and injected into every agent prompt
   via RafNode._spec_context() using the ``_spec`` meta-key.

2. SpecLedger (raf.core.spec.SpecLedger)
   Accumulates key technology decisions as each winning agent declares them in
   their ``decisions`` dict.  First-write-wins: once "db=PostgreSQL" is locked,
   no downstream node can switch to MongoDB.  The ledger is thread-safe so
   parallel child nodes read/write safely.  _ledger_gate() filters candidate
   proposals before jury voting using SpecLedger.check_compatible().
   _lock_decisions() writes the winning agent's declarations to the ledger and
   also runs a heuristic scan for implicit technology signals (warnings only —
   implicit signals are never locked).

3. Repair loop (_spec_repair_loop)
   Runs after base execution and after merge (before _analyze).  Calls
   SpecValidator.validate() on the output — first a cheap deterministic
   keyword check, then an LLM call only if the deterministic check fails.
   On failure, spawns a targeted "patch" RafNode with explicit instructions
   to add the missing items without rewriting what is already correct.
   Runs up to config.spec_repair_limit times.  Depth-gated by
   config.spec_repair_depth_limit (default 0 = root only) so repair nodes
   don't recursively trigger more repair nodes.

WHERE THESE FIT IN THE DECISION FLOW
--------------------------------------
  RafEngine.run()
    → SpecExtractor.extract()   (once, synchronous, before root node)
    → root.run()
        → _execute_base()
            → consortium + jury
            → _quality_gate()   (remove placeholder proposals)
            → _ledger_gate()    (remove ledger-contradicting proposals)
            → _lock_decisions() (lock winning agent's decisions + warn on implicit)
            → _spec_repair_loop() (fix missing spec items, before _analyze)
            → _analyze()
        → _execute_recursive()
            → _plan_children()
                → validator child filter (_VALIDATOR_CHILD_RE) removes
                  pure-validator nodes from the plan
            → parallel children
            → merge + _quality_gate() + _ledger_gate() + _lock_decisions()
            → _spec_repair_loop() (fix missing spec items in merged output)
            → _analyze()
"""

import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

from raf.agents.consortium import Consortium, mode_decision_early_exit
from raf.agents.jury import Jury
from raf.core.deps import DependencyError, topo_sort, validate_plan
from raf.core.referee import Referee, RefereeReport
from raf.core.spec import (
    Spec, SpecLedger, SpecExtractor, SpecValidator, extract_implicit_decisions,
)
from raf.llm.json_utils import call_json_with_guard, call_json_with_repair
from raf.schemas import (
    RafConfig,
    validate_clarify_request,
    validate_analysis_result,
    validate_base_execution_result,
    validate_merge_result,
    validate_mode_decision,
    validate_plan as validate_plan_schema,
    validate_plan_structure,
    validate_refined_child,
    validate_scope_check,
)

# Maximum tool-call iterations per base execution (prevents infinite loops)
_MAX_TOOL_CALLS = 5

# Validator-only child filter — matches goals that are purely about checking ANOTHER
# child's output, not delivering any artifact.
#
# WHY THIS IS NARROW
# -------------------
# LLMs frequently generate plans that include meta-nodes: "validate the auth
# implementation", "review the API design", "quality check the output".  These
# nodes consume budget and add latency but produce no actual artifact — their
# output is a verdict on another node's output, not a deliverable.  The quality
# gate in _analyze() already handles output evaluation; meta-validation nodes
# duplicate that work without adding value.
#
# The pattern is intentionally narrow to avoid false positives on legitimate goals:
#   BLOCKED:  "validate the above implementation"
#             "audit the previous output"
#             "pre-check", "post-check", "quality gate"
#   ALLOWED:  "verify email ownership" (subject is email, not another node's output)
#             "JWT validation middleware" (an artifact, not a check of another node)
#             "review pull request" (if the root goal explicitly asked for review)
#
# The root_goal guard in _plan_children() bypasses this filter entirely when the
# user's root goal mentions review/audit/validate — e.g. "audit this codebase"
# legitimately needs validator-type children.
_VALIDATOR_CHILD_RE = re.compile(
    r"""
    \b(validate|verify|audit|review)\s+(the\s+)?(above|previous|output|result|child|other|each)\b
    | \bpre.?check\b
    | \bpost.?check\b
    | \bquality\s+(check|gate|review)\b
    | \b(output|result|plan|above|previous)\s+(validation|verification)\b  # meta-checks on another node's output only
    | \baudit\s+(report|trail|log|summary)\b         # "audit report", "audit trail"
    | \bconfirm\s+(that|whether|the|all|each)\b      # "confirm that/whether/the..."
    | \binspect\s+(the|all|each|every)\b              # "inspect the/all/each/every..."
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Minimum nodes we must reserve per planned child before allowing recursion.
# If the remaining budget can't cover this per child, we truncate the plan.
_MIN_NODES_PER_CHILD = 3

# Ledger key allowlist: only lock decisions whose key uses strict dot-notation
# format "category.subtype" (e.g. "storage.backend", "auth.method").
# Free-form keys invented by LLMs (e.g. "holographic_hashing", "fault-tolerant",
# "my_choice") are silently skipped — they pollute the ledger without adding
# any semantic constraint that downstream agents can reliably match.
_LEDGER_KEY_RE = re.compile(r"^[a-z][a-z0-9_]{1,30}\.[a-z][a-z0-9_]{1,30}$")


class RafNode:
    """
    A single recursive execution unit.

    Parameters
    ----------
    engine : RafEngine
        Parent engine — provides config, adapters, trace, budget.
    node_id : str
        Unique identifier assigned by the engine (e.g. "root", "node-1").
    goal : str
        The task this node must accomplish.
    depth : int
        Recursion depth (root = 0).
    parent_id : str | None
        ID of the parent node, or None for root.
    ancestors : list[str]
        Goals of all ancestor nodes, root-first. Used for context injection.
    plan_child_id : str | None
        The child_id from the parent's plan that this node was created to fulfil.
        Emitted in node_created so the frontend can link planned nodes to real ones.
    """

    def __init__(
        self,
        engine: "RafEngine",
        node_id: str,
        goal: str,
        depth: int,
        parent_id: Optional[str],
        ancestors: Optional[List[str]] = None,
        plan_child_id: Optional[str] = None,
    ) -> None:
        self.engine = engine
        self.node_id = node_id
        self.goal = goal
        self.depth = depth
        self.parent_id = parent_id
        self.ancestors: List[str] = ancestors or []
        self.plan_child_id = plan_child_id
        self.mode: Optional[str] = None
        self.status = "CREATED"
        self.children: List["RafNode"] = []
        self.result: Optional[Dict[str, Any]] = None

    # ── public ────────────────────────────────────────────────────────────────

    def run(self) -> Dict[str, Any]:
        """Execute this node and return its result dict."""
        self.engine._check_cancelled()

        self.engine.trace.log(
            {
                "node_id": self.node_id,
                "parent_id": self.parent_id,
                "plan_child_id": self.plan_child_id,
                "depth": self.depth,
                "status": "CREATED",
                "goal": self.goal,
                "ancestors": self.ancestors[-3:],
                "event": "node_created",
            }
        )

        # ── Goal memoization cache check ──────────────────────────────────────
        # Only non-root nodes can hit the cache — the root goal is unique per run.
        # We skip caching when clarification might be needed (root-only) so there
        # is no race between the cache check and the clarify call.
        if self.depth > 0:
            ckey = self._cache_key()
            with self.engine._cache_lock:
                cached = self.engine._goal_cache.get(ckey)
            if cached is not None:
                self.engine.trace.log({
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "goal": self.goal,
                    "event": "cache_hit",
                    "cache_key": ckey,
                })
                self.engine.trace.log({
                    "node_id": self.node_id,
                    "parent_id": self.parent_id,
                    "depth": self.depth,
                    "goal": self.goal,
                    "status": "DONE",
                    "mode": cached.get("metadata", {}).get("mode", "base"),
                    "output": cached.get("output", ""),
                    "confidence": cached.get("metadata", {}).get("confidence", 0.0),
                    "event": "node_done",
                    "cache_hit": True,
                })
                return cached

        clarify = self._maybe_clarify()
        if clarify is not None:
            return clarify

        # Execution-policy fast path: task_class=transform means the goal is a
        # transformation (summarize, rewrite, translate, reformat, extract).
        # These are inherently single-pass — multi-agent mode deliberation adds
        # noise, not quality.  Skip _decide_mode() and go directly to base.
        # force_recursive overrides SINGLE_PASS at depth 0 so the user can always
        # force decomposition regardless of task_class.
        policy = self._execution_policy()
        if policy == "SINGLE_PASS" and not (self.engine.config.force_recursive and self.depth == 0):
            spec = self.engine.spec
            task_class = spec.task_class if spec else "general"
            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "status": "POLICY_SINGLE_PASS",
                    "event": "mode_decided",
                    "winner": "base",
                    "confidence": 0.90,
                    "fast_path": True,
                    "reason": "single_pass_policy",
                    "task_class": task_class,
                }
            )
            self.mode = "base"
            result = self._execute_base()
            self.result = result
            self._cache_write(result)
            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "parent_id": self.parent_id,
                    "depth": self.depth,
                    "goal": self.goal,
                    "status": "DONE",
                    "mode": self.mode,
                    "output": result.get("output", "") if result else "",
                    "confidence": result.get("metadata", {}).get("confidence", 0.0) if result else 0.0,
                    "event": "node_done",
                }
            )
            return result

        self.mode = self._decide_mode()
        if self.mode == "base":
            result = self._execute_base()
        else:
            result = self._execute_recursive()
        self.result = result
        self._cache_write(result)
        self.engine.trace.log(
            {
                "node_id": self.node_id,
                "parent_id": self.parent_id,
                "depth": self.depth,
                "goal": self.goal,
                "status": "DONE",
                "mode": self.mode,
                "output": result.get("output", "") if result else "",
                "confidence": result.get("metadata", {}).get("confidence", 0.0) if result else 0.0,
                "event": "node_done",
            }
        )
        return result

    # ── clarification ─────────────────────────────────────────────────────────

    def _maybe_clarify(self) -> Optional[Dict[str, Any]]:
        """Ask one clarifying question if the goal is ambiguous (root only)."""
        if not self.engine.config.clarify_before_execute:
            return None
        if self.engine.config.clarify_root_only and self.depth != 0:
            return None

        self.engine.trace.log(
            {"node_id": self.node_id, "depth": self.depth, "status": "CLARIFY_CHECK"}
        )
        clarify = call_json_with_repair(
            self.engine.adapter,
            "clarify",
            {
                **self._base_context(),
                "_raf_role": "clarifier",
                "goal": self.goal,
                "ancestors": self.ancestors,
                "system_prompt": self.engine.config.system_prompt,
            },
            validate_clarify_request,
            self.engine.config.retry_limit,
        )
        questions = clarify.get("questions", [])
        question = questions[0] if questions else ""
        if question:
            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "status": "CLARIFY_REQUESTED",
                    "question": question,
                }
            )
            return {
                "output": "",
                "metadata": {"mode": "clarify", "questions": [question]},
            }
        return None

    # ── atomicity check ───────────────────────────────────────────────────────

    # ── depth-based consortium sizing ─────────────────────────────────────────

    def _adapters_for_tier(self, task: str) -> tuple:
        """Return (consortium_adapters, jury_adapters, tier) for *task*.

        Three tiers match model capability to task complexity:

          Tier 2 — Root/Referee (engine.root_adapters + engine.root_jury_adapters)
              Always used for:  analysis, spec_repair
              Also used for:    depth == 0 (root node), depth == 1 planning/merging
              Adaptive sizing:  never scaled down — these decisions need full deliberation.

          Tier 1 — Planner/Synthesizer (engine.mid_adapters + engine.mid_jury_adapters)
              Used for:  depth >= 2 recursive planning/merging, refine_context,
                         mode_decision at depth >= 2
              Adaptive sizing:  mild scale-down when close to max_depth.
              Also serves as jury floor for Tier 0 (weak models never grade weak models).

          Tier 0 — Leaf/Worker (engine.leaf_adapters + engine.mid_jury_adapters)
              Used for:  depth >= 2 base_execute (simple subtask execution)
              Adaptive sizing:  aggressive scale-down — single agent at deepest nodes.
              Jury is always at least Tier 1 (mid_jury_adapters).

        Within-tier adaptive sizing reduces API call count at deep nodes where the
        added deliberation cost outweighs the quality benefit.  Tier 2 is exempt:
        the referee must always give its best answer regardless of depth.

        Returns (consortium_adapters, jury_adapters, tier_number)
        so callers can include the tier in trace events for UI display.
        """
        engine = self.engine
        max_depth = engine.config.max_depth

        def _scale(adapters: list, tier: int) -> list:
            """Scale consortium count within a tier by remaining depth budget.

            Tier 2 — never scaled (referee always uses full adapter list).
            Tier 1 — mild: drop one adapter when one step from max_depth.
            Tier 0 — aggressive: single agent at deepest level, minus-one below.
            """
            if tier == 2 or not adapters:
                return adapters
            n = len(adapters)
            remaining = max(0, max_depth - self.depth)
            if tier == 0:
                if remaining <= 0:
                    return adapters[:1]
                if remaining == 1:
                    return adapters[:max(1, n - 1)]
                return adapters
            else:  # tier == 1
                if remaining <= 1:
                    return adapters[:max(1, n - 1)]
                return adapters

        # ── Tier 2: analysis / spec_repair — always the strongest models ──────
        if task in ("analysis", "spec_repair"):
            return _scale(engine.root_adapters, 2), engine.root_jury_adapters, 2

        # ── Tier 2: root node (depth 0) — all tasks ───────────────────────────
        if self.depth == 0:
            return _scale(engine.root_adapters, 2), engine.root_jury_adapters, 2

        # ── Tier 2: depth 1 planning & merging — critical decomposition ────────
        if self.depth == 1 and task in ("plan", "merge", "mode_decision"):
            return _scale(engine.root_adapters, 2), engine.root_jury_adapters, 2

        # ── Tier 0: deep leaf workers — fast models for single subtasks ────────
        # Jury floored at Tier 1 (mid_jury_adapters) — no weak model grading weak.
        if self.depth >= 2 and task == "base_execute":
            return _scale(engine.leaf_adapters, 0), engine.mid_jury_adapters, 0

        # ── Tier 1: everything else (mid-level plan/merge/refine/mode_decision) ─
        return _scale(engine.mid_adapters, 1), engine.mid_jury_adapters, 1

    def _adapters_for_depth(self) -> list:
        """Deprecated: use _adapters_for_tier(task) instead.

        Kept for reference — no longer called by any decision point.
        Previously returned a depth-scaled slice of consortium_adapters to
        reduce agent count at deeper nodes.  Tier routing supersedes this.
        """
        adapters = self.engine.consortium_adapters
        n = len(adapters)
        if self.depth == 0:
            return adapters
        if self.depth == 1:
            return adapters[:max(2, n - 1)]
        return adapters[:1]

    # ── execution policy ──────────────────────────────────────────────────────

    # Maps task_class → execution policy name.
    # Policies control how much orchestration machinery fires for a given node:
    #
    #   FULL_RAF     — full Consortium+Jury at every decision point (default)
    #   SINGLE_PASS  — skip _decide_mode(); go straight to _execute_base().
    #                  Best for transformation tasks where there is one correct
    #                  output and multi-agent deliberation adds noise not quality
    #                  (summarize, translate, reformat, extract).
    _TASK_CLASS_POLICY: Dict[str, str] = {
        "transform":  "SINGLE_PASS",
        "implement":  "FULL_RAF",
        "coordinate": "FULL_RAF",
        "analyze":    "FULL_RAF",
        "create":     "FULL_RAF",
        "general":    "FULL_RAF",
    }

    def _execution_policy(self) -> str:
        """Return the execution policy for this node based on the Spec's task_class.

        Policy is run-level — all nodes share the same policy because task_class
        describes the nature of the root goal, not individual sub-tasks.

        Returns "FULL_RAF" (default) or "SINGLE_PASS" (transform tasks).
        Falls back to "FULL_RAF" when spec is unavailable.
        """
        spec = self.engine.spec
        if spec is None:
            return "FULL_RAF"
        return self._TASK_CLASS_POLICY.get(spec.task_class, "FULL_RAF")

    # ── mode decision ─────────────────────────────────────────────────────────

    def _decide_mode(self) -> str:
        """
        Use Consortium + Jury to decide whether this node should execute directly
        (base) or recursively decompose into children.

        Returns "base" or "recursive".
        Hard-codes "base" when depth or budget limits are reached.
        """
        self.engine._check_cancelled()
        self.engine.trace.log(
            {
                "node_id": self.node_id,
                "depth": self.depth,
                "status": "DECIDE_MODE",
                "event": "mode_decide_start",
            }
        )

        if self.depth >= self.engine.config.max_depth:
            return "base"

        # force_recursive: skip the LLM vote at root and always decompose.
        # Children still decide their own mode freely.
        if self.engine.config.force_recursive and self.depth == 0:
            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "status": "FORCE_RECURSIVE_CONFIG",
                    "event": "mode_decided",
                    "winner": "recursive",
                    "confidence": 1.0,
                    "fast_path": True,
                    "reason": "force_recursive",
                }
            )
            return "recursive"

        if self.engine.remaining_nodes() <= self.engine.config.min_remaining_for_recursive:
            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "status": "FORCE_BASE_NODE_LIMIT",
                    "remaining_nodes": self.engine.remaining_nodes(),
                }
            )
            return "base"

        _c_adapters, _j_adapters, _tier = self._adapters_for_tier("mode_decision")
        consortium = Consortium(
            _c_adapters,
            "mode_decision",
            self.engine.config.retry_limit,
            trace=self.engine.trace,
            node_id=self.node_id,
            depth=self.depth,
            timeout_s=self.engine.config.timeout_by_task.get("mode_decision"),
            fallback_adapter=self.engine.fallback_adapter,
        )
        jury = Jury(
            _j_adapters,
            self.engine.config.retry_limit,
            self.engine.config.system_prompt,
            trace=self.engine.trace,
            node_id=self.node_id,
            depth=self.depth,
            timeout_s=self.engine.config.timeout_by_task.get("mode_decision"),
            fallback_adapter=self.engine.fallback_adapter,
        )

        retries = 0
        while True:
            candidates = consortium.call(
                {
                    **self._base_context(),
                    **self._referee_context(),
                    **self._spec_context(),
                    "goal": self.goal,
                    "depth": self.depth,
                    "ancestors": self.ancestors[-5:],
                    "constraints": self._constraints(),
                    "system_prompt": self.engine.config.system_prompt,
                },
                validate_mode_decision,
                early_exit_fn=mode_decision_early_exit,
            )
            if not candidates:
                raise RuntimeError("No valid mode candidates")

            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "status": "CONSORTIUM_CANDIDATES",
                    "event": "consortium_candidates",
                    "task": "mode_decision",
                    "tier": _tier,
                    "candidates": candidates,
                }
            )

            # Skip jury when all consortium agents agree — saves jury_size LLM calls.
            # Confidence scales with how many agents agreed: more agreement = higher certainty.
            unanimous_mode = Jury.unanimous(candidates, "mode")
            if unanimous_mode is not None:
                n = len(candidates)
                confidence = 0.75 + 0.20 * min(n, 3) / 3  # 0.82 for 1, 0.88 for 2, 0.95 for 3+
                self.engine.trace.log(
                    {
                        "node_id": self.node_id,
                        "depth": self.depth,
                        "status": "MODE_DECIDED",
                        "winner": unanimous_mode,
                        "confidence": confidence,
                        "retries": retries,
                        "event": "mode_decided",
                        "unanimous": True,
                    }
                )
                winner = candidates[0]
                vote = {"winner_id": "option-0", "confidence": confidence}
                labeled = [{"option_id": f"option-{i}", "payload": c} for i, c in enumerate(candidates)]
                # Populate synthetic jury_votes so the UI shows agent count correctly.
                votes: list = [
                    {"agent_id": i, "vote": {"winner_id": "option-0", "confidence": confidence, "ranked": []}}
                    for i in range(len(candidates))
                ]
            else:
                winner, vote, votes, labeled = jury.vote(candidates, node_context={
                    **self._base_context(), "goal": self.goal, "depth": self.depth,
                }, task="mode_decision")
                confidence = vote["confidence"]
                self.engine.trace.log(
                    {
                        "node_id": self.node_id,
                        "depth": self.depth,
                        "status": "MODE_DECIDED",
                        "winner": winner["mode"],
                        "confidence": confidence,
                        "retries": retries,
                        "event": "mode_decided",
                    }
                )

            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "status": "JURY_VOTES",
                    "event": "jury_votes",
                    "task": "mode_decision",
                    "winner_id": vote.get("winner_id", ""),
                    "confidence": confidence,
                    "options": labeled,
                    "votes": votes,
                }
            )
            winner.pop("_adapter_index", None)  # internal tracking key — not part of the schema
            if (
                winner["mode"] == "base"
                and confidence < self.engine.config.confidence_threshold + self.engine.config.recursive_confidence_margin
                and self.depth < self.engine.config.max_depth - 1
            ):
                self.engine.trace.log(
                    {
                        "node_id": self.node_id,
                        "depth": self.depth,
                        "status": "FORCE_RECURSIVE_LOW_CONF",
                        "confidence": confidence,
                        "event": "mode_forced_recursive",
                    }
                )
                return "recursive"
            if confidence >= self.engine.config.confidence_threshold or retries >= self.engine.config.retry_limit:
                return winner["mode"]
            retries += 1

    # ── base execution ────────────────────────────────────────────────────────

    def _execute_base(self) -> Dict[str, Any]:
        """
        Execute this node directly (no child decomposition).

        Decision point 4 — Base execution:
          1. Consortium proposes N independent execution outputs in parallel.
          2. If all agents agree, skip jury (unanimous shortcut, confidence 0.95).
          3. Otherwise Jury votes on the best proposal.
          4. If the winner requests a tool call (tools_enabled), the tool loop
             runs on the primary adapter; the result is emitted as-is.
          5. Scope check + analysis to produce the final result dict.
        """
        self.engine._check_cancelled()
        self.engine.trace.log(
            {
                "node_id": self.node_id,
                "depth": self.depth,
                "status": "EXECUTE_BASE",
                "event": "base_execute_start",
            }
        )
        base_payload = {
            **self._base_context(),
            **self._referee_context(),
            **self._spec_context(),
            "_raf_role": "executor",
            "goal": self.goal,
            "depth": self.depth,
            "ancestors": self.ancestors[-5:],
            "constraints": self._constraints(),
            "system_prompt": self.engine.config.system_prompt,
        }

        # ── Consortium: N agents each propose an execution output ──
        _c_adapters, _j_adapters, _tier = self._adapters_for_tier("base_execute")
        consortium = Consortium(
            _c_adapters,
            "base_execute",
            self.engine.config.retry_limit,
            trace=self.engine.trace,
            node_id=self.node_id,
            depth=self.depth,
            timeout_s=self.engine.config.timeout_by_task.get("base_execute"),
            fallback_adapter=self.engine.fallback_adapter,
        )
        jury = Jury(
            _j_adapters,
            self.engine.config.retry_limit,
            self.engine.config.system_prompt,
            trace=self.engine.trace,
            node_id=self.node_id,
            depth=self.depth,
            timeout_s=self.engine.config.timeout_by_task.get("base_execute"),
            fallback_adapter=self.engine.fallback_adapter,
        )

        candidates = consortium.call(base_payload, validate_base_execution_result)
        if not candidates:
            raise RuntimeError("No valid base execution candidates")

        # ── Quality gate: remove placeholder/empty candidates ──
        candidates = self._quality_gate(candidates, "output")

        # ── Ledger gate: remove candidates contradicting locked decisions ──
        candidates = self._ledger_gate(candidates)

        self.engine.trace.log(
            {
                "node_id": self.node_id,
                "depth": self.depth,
                "status": "CONSORTIUM_CANDIDATES",
                "event": "consortium_candidates",
                "task": "base_execute",
                "tier": _tier,
                "candidates": candidates,
            }
        )

        # ── Jury: vote on the best proposal (skip if unanimous) ──
        unanimous_output = Jury.unanimous(candidates, "output")
        if unanimous_output is not None:
            n = len(candidates)
            base_conf = 0.75 + 0.20 * min(n, 3) / 3  # scales with agent count
            result: Dict[str, Any] = candidates[0]
            vote: Dict[str, Any] = {"winner_id": "option-0", "confidence": base_conf}
            labeled = [{"option_id": f"option-{i}", "payload": c} for i, c in enumerate(candidates)]
            votes: list = [
                {"agent_id": i, "vote": {"winner_id": "option-0", "confidence": base_conf, "ranked": []}}
                for i in range(len(candidates))
            ]
            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "status": "BASE_EXECUTE_DECIDED",
                    "event": "base_execute_decided",
                    "unanimous": True,
                    "confidence": base_conf,
                }
            )
        else:
            result, vote, votes, labeled = jury.vote(
                candidates,
                node_context={**self._base_context(), "goal": self.goal, "depth": self.depth},
                task="base_execute",
            )
            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "status": "BASE_EXECUTE_DECIDED",
                    "event": "base_execute_decided",
                    "confidence": vote["confidence"],
                }
            )

        self.engine.trace.log(
            {
                "node_id": self.node_id,
                "depth": self.depth,
                "status": "JURY_VOTES",
                "event": "jury_votes",
                "task": "base_execute",
                "winner_id": vote.get("winner_id", ""),
                "confidence": vote.get("confidence", 0.95),
                "options": labeled,
                "votes": votes,
            }
        )

        # ── Lock decisions declared by the winning agent ──
        self._lock_decisions(result)

        # ── Tool call loop: follow the winning agent's tool requests ──
        # Use the same adapter that produced the winning proposal so the follow-up
        # call goes to the same model (important for multi-model ensembles).
        _winning_idx = result.pop("_adapter_index", 0)
        _n_adapters = len(self.engine.consortium_adapters)
        _winning_adapter = self.engine.consortium_adapters[
            max(0, min(_winning_idx, _n_adapters - 1))
        ]

        tool_results: List[Dict[str, Any]] = []
        for _tool_iter in range(_MAX_TOOL_CALLS):
            tool_call = result.get("tool_call") if self.engine.config.tools_enabled else None
            if not tool_call or not isinstance(tool_call, dict) or "name" not in tool_call:
                break

            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})
            if tool_name not in self.engine.config.available_tools:
                self.engine.trace.log(
                    {
                        "node_id": self.node_id,
                        "depth": self.depth,
                        "event": "tool_blocked",
                        "tool": tool_name,
                        "reason": "not in available_tools",
                    }
                )
                break

            tool_result = self.engine.execute_tool(tool_name, tool_args)
            tool_results.append({"name": tool_name, "args": tool_args, "result": tool_result})
            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "event": "tool_called",
                    "tool": tool_name,
                    "result_preview": str(tool_result)[:300],
                }
            )
            payload_with_tools = dict(base_payload)
            payload_with_tools["tool_results"] = tool_results
            result = call_json_with_repair(
                _winning_adapter,
                "base_execute",
                payload_with_tools,
                validate_base_execution_result,
                self.engine.config.retry_limit,
            )

        result = self._scope_check_and_retry(result, base_payload, "base_execute")

        # ── Referee: evaluate output, update grounded state ──
        referee_report = self.engine.referee.evaluate(result["output"])
        self.engine.last_referee_report = referee_report
        self.engine.trace.log(
            {
                "node_id": self.node_id,
                "depth": self.depth,
                "event": "referee_report",
                "state_hash": referee_report.state_hash,
                "progress": referee_report.progress,
                "covered": referee_report.covered,
                "missing": referee_report.missing,
                "invariant_ok": referee_report.invariant_ok,
                "invariant_error": referee_report.invariant_error,
                "step": referee_report.step,
            }
        )

        # ── Spec repair loop: fix missing required items before analysis ──
        result = self._spec_repair_loop(result)

        analysis = self._analyze(result["output"], "base")
        node_result = {
            "output": result["output"],
            "metadata": {
                "mode": "base",
                "confidence": analysis["confidence"],
                "approved": analysis.get("approved", True),
                "locally_valid": analysis.get("locally_valid", analysis.get("approved", True)),
                "goal_completed": analysis.get("goal_completed", analysis.get("approved", True)),
            },
        }
        self.engine.trace.log(
            {
                "node_id": self.node_id,
                "depth": self.depth,
                "status": "EXECUTE_BASE_DONE",
                "event": "base_execute_done",
            }
        )
        return node_result

    # ── recursive execution ───────────────────────────────────────────────────

    def _execute_recursive(self) -> Dict[str, Any]:
        """
        Decompose this node into children and execute them.

        Steps:
          1. _plan_children  – Consortium proposes plans, Jury selects one
          2. Proportional budget check  – truncate plan if budget too tight
          3. Optional human plan approval gate
          4. _refine_children – per-child goal refinement
          5. Parallel child execution with dependency ordering
          6. merge  – combine child outputs
          7. _analyze  – evaluate merged result
        """
        self.engine._check_cancelled()
        self.engine.trace.log(
            {"node_id": self.node_id, "depth": self.depth, "status": "PLAN", "event": "plan_start"}
        )

        if self.engine.remaining_nodes() <= 0:
            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "status": "FORCE_BASE_NODE_LIMIT",
                    "remaining_nodes": self.engine.remaining_nodes(),
                }
            )
            return self._execute_base()

        attempts = 0
        while True:
            plan = self._plan_children()
            try:
                validate_plan(plan, self.engine.config.max_children_per_plan)
                break
            except DependencyError as exc:
                self.engine.trace.log(
                    {
                        "node_id": self.node_id,
                        "depth": self.depth,
                        "status": "PLAN_INVALID",
                        "error": str(exc),
                        "retries": attempts,
                    }
                )
                if attempts >= self.engine.config.retry_limit:
                    raise
                attempts += 1

        self.engine._check_cancelled()

        # ── Proportional budget: ensure each child has enough nodes to run ──
        children = plan.get("children", [])
        n_children = len(children)
        remaining = self.engine.remaining_nodes()
        if n_children > 0 and remaining < n_children * _MIN_NODES_PER_CHILD:
            max_affordable = max(1, remaining // _MIN_NODES_PER_CHILD)
            if max_affordable < n_children:
                self.engine.trace.log(
                    {
                        "node_id": self.node_id,
                        "depth": self.depth,
                        "event": "plan_truncated",
                        "original_children": n_children,
                        "kept_children": max_affordable,
                        "reason": f"budget {remaining} nodes insufficient for {n_children} children (need {n_children * _MIN_NODES_PER_CHILD})",
                    }
                )
                plan = dict(plan)
                kept = children[:max_affordable]
                kept_ids = {c["child_id"] for c in kept}
                for c in kept:
                    c["depends_on"] = [d for d in c.get("depends_on", []) if d in kept_ids]
                plan["children"] = kept

        # ── Human-in-the-loop plan approval ──
        if self.engine.on_plan_ready is not None:
            plan = self.engine.on_plan_ready(self.node_id, plan)

        order = topo_sort(plan["children"])
        self.engine.trace.log(
            {
                "node_id": self.node_id,
                "depth": self.depth,
                "status": "EXECUTE_CHILDREN",
                "order": order,
                "event": "children_start",
            }
        )

        refined_children = self._refine_children(plan["children"])
        child_map = {child["child_id"]: child for child in refined_children}
        completed: Dict[str, Dict[str, Any]] = {}
        deps_map: Dict[str, List[str]] = {
            child["child_id"]: list(child.get("depends_on", [])) for child in refined_children
        }

        ready = [cid for cid in order if not deps_map.get(cid)]
        in_flight: Dict[str, Any] = {}

        child_ancestors = self.ancestors + [self.goal]

        # Truncation limit for each dependency's output injected into a child's goal.
        # Prevents token-limit blowouts when a child depends on many large outputs.
        _DEP_OUTPUT_MAX = 500

        def run_child(child_id: str) -> Dict[str, Any]:
            child_spec = child_map[child_id]
            dep_ids = deps_map.get(child_id, [])
            dep_context = []
            for dep_id in dep_ids:
                dep_result = completed.get(dep_id)
                if dep_result:
                    # Use key_points summary when output exceeds _DEP_OUTPUT_MAX —
                    # same compression as _compress_output but with the dep-specific cap.
                    out = self._compress_output(dep_result, max_chars=_DEP_OUTPUT_MAX)
                    dep_context.append(f"{dep_id}: {out}")
            if dep_context:
                goal = "Dependency outputs:\n" + "\n".join(dep_context) + f"\nGoal: {child_spec['goal']}"
            else:
                goal = child_spec["goal"]
            child_node = self.engine.create_node(
                goal, self.depth + 1, self.node_id, child_ancestors, plan_child_id=child_id
            )
            self.children.append(child_node)
            return child_node.run()

        with ThreadPoolExecutor(max_workers=self.engine.config.max_parallel_children) as executor:
            while ready or in_flight:
                while ready and len(in_flight) < self.engine.config.max_parallel_children:
                    cid = ready.pop(0)
                    fut = executor.submit(run_child, cid)
                    in_flight[cid] = fut

                # Build a reverse map once per batch so we can look up cid in O(1).
                future_to_cid = {v: k for k, v in in_flight.items()}
                done_ids = []
                for future in as_completed(list(in_flight.values())):
                    cid = future_to_cid[future]
                    try:
                        completed[cid] = future.result()
                    except Exception as exc:
                        # Re-raise cancellations; treat other failures as empty output
                        if "cancelled" in str(exc).lower():
                            raise
                        self.engine.trace.log(
                            {
                                "node_id": self.node_id,
                                "depth": self.depth,
                                "event": "child_failed",
                                "child_id": cid,
                                "error": str(exc),
                            }
                        )
                        completed[cid] = {"output": f"[child {cid} failed: {exc}]", "metadata": {"mode": "base", "confidence": 0.0}}
                    done_ids.append(cid)
                    break

                for cid in done_ids:
                    in_flight.pop(cid, None)
                    for child_id, deps in deps_map.items():
                        if cid in deps:
                            deps.remove(cid)
                            if (
                                not deps
                                and child_id not in completed
                                and child_id not in in_flight
                                and child_id not in ready
                            ):
                                ready.append(child_id)

        # Include child_id in each output entry so the merger can attribute
        # sections back to specific children in the structured merge contract.
        # _compress_output() substitutes key_points summaries for long outputs
        # to prevent token-limit blowouts in runs with many or large children.
        child_outputs = [
            {"child_id": cid, "output": self._compress_output(completed[cid])}
            for cid in order if cid in completed
        ]
        merge_payload = {
            **self._base_context(),
            **self._referee_context(),
            **self._spec_context(),
            "_raf_role": "merger",
            "goal": self.goal,
            "depth": self.depth,
            "child_outputs": child_outputs,
            "ancestors": self.ancestors[-5:],
            "constraints": self._constraints(),
            "system_prompt": self.engine.config.system_prompt,
        }

        # ── Merge: Consortium + Jury (decision point 5 — combine child outputs) ──
        _mc_adapters, _mj_adapters, _mtier = self._adapters_for_tier("merge")
        merge_consortium = Consortium(
            _mc_adapters,
            "merge",
            self.engine.config.retry_limit,
            trace=self.engine.trace,
            node_id=self.node_id,
            depth=self.depth,
            timeout_s=self.engine.config.timeout_by_task.get("merge"),
            fallback_adapter=self.engine.fallback_adapter,
        )
        merge_jury = Jury(
            _mj_adapters,
            self.engine.config.retry_limit,
            self.engine.config.system_prompt,
            trace=self.engine.trace,
            node_id=self.node_id,
            depth=self.depth,
            timeout_s=self.engine.config.timeout_by_task.get("merge"),
            fallback_adapter=self.engine.fallback_adapter,
        )

        merge_candidates = merge_consortium.call(merge_payload, validate_merge_result)
        if not merge_candidates:
            raise RuntimeError("No valid merge candidates")

        # ── Quality gate + Ledger gate on merge candidates ──
        merge_candidates = self._quality_gate(merge_candidates, "output")
        merge_candidates = self._ledger_gate(merge_candidates)

        self.engine.trace.log(
            {
                "node_id": self.node_id,
                "depth": self.depth,
                "event": "consortium_candidates",
                "task": "merge",
                "tier": _mtier,
                "candidates": merge_candidates,
            }
        )

        unanimous_merge = Jury.unanimous(merge_candidates, "output")
        if unanimous_merge is not None:
            n = len(merge_candidates)
            m_conf = 0.75 + 0.20 * min(n, 3) / 3
            merge = merge_candidates[0]
            m_vote: Dict[str, Any] = {"winner_id": "option-0", "confidence": m_conf}
            m_labeled = [{"option_id": f"option-{i}", "payload": c} for i, c in enumerate(merge_candidates)]
            m_votes: list = [
                {"agent_id": i, "vote": {"winner_id": "option-0", "confidence": m_conf, "ranked": []}}
                for i in range(n)
            ]
        else:
            merge, m_vote, m_votes, m_labeled = merge_jury.vote(
                merge_candidates,
                node_context={**self._base_context(), "goal": self.goal, "depth": self.depth},
                task="merge",
            )

        merge.pop("_adapter_index", None)
        self.engine.trace.log(
            {
                "node_id": self.node_id,
                "depth": self.depth,
                "event": "jury_votes",
                "task": "merge",
                "winner_id": m_vote.get("winner_id", ""),
                "confidence": m_vote.get("confidence", 0.0),
                "options": m_labeled,
                "votes": m_votes,
            }
        )

        # ── Emit merge attribution event (structured contract fields) ──
        sections = merge.get("sections", [])
        conflicts = merge.get("unresolved_conflicts", [])
        if sections or conflicts:
            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "event": "merge_attribution",
                    "sections": sections,
                    "unresolved_conflicts": conflicts,
                    "conflict_count": len(conflicts),
                    "section_count": len(sections),
                }
            )
        if conflicts:
            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "event": "merge_conflicts_detected",
                    "conflicts": conflicts,
                }
            )

        # ── Lock decisions declared by the winning merge agent ──
        self._lock_decisions(merge)

        merge = self._scope_check_and_retry(merge, merge_payload, "merge")

        # ── Referee: evaluate merged output, update grounded state ──
        referee_report = self.engine.referee.evaluate(merge["output"])
        self.engine.last_referee_report = referee_report
        self.engine.trace.log(
            {
                "node_id": self.node_id,
                "depth": self.depth,
                "event": "referee_report",
                "state_hash": referee_report.state_hash,
                "progress": referee_report.progress,
                "covered": referee_report.covered,
                "missing": referee_report.missing,
                "invariant_ok": referee_report.invariant_ok,
                "invariant_error": referee_report.invariant_error,
                "step": referee_report.step,
            }
        )

        # ── Spec repair loop: fix missing required items before analysis ──
        merge = self._spec_repair_loop(merge)

        analysis = self._analyze(merge["output"], "recursive")
        node_result = {
            "output": merge["output"],
            "metadata": {
                "mode": "recursive",
                "confidence": analysis["confidence"],
                "approved": analysis.get("approved", True),
                "locally_valid": analysis.get("locally_valid", analysis.get("approved", True)),
                "goal_completed": analysis.get("goal_completed", analysis.get("approved", True)),
            },
        }
        self.engine.trace.log(
            {"node_id": self.node_id, "depth": self.depth, "status": "MERGE_DONE", "event": "merge_done"}
        )
        return node_result

    # ── planning ──────────────────────────────────────────────────────────────

    def _plan_children(self) -> Dict[str, Any]:
        """
        Use Consortium + Jury to produce a decomposition plan.

        Returns a validated plan dict: {"children": [...], "rationale": "..."}.
        """
        _pc_adapters, _pj_adapters, _ptier = self._adapters_for_tier("plan")
        consortium = Consortium(
            _pc_adapters,
            "plan",
            self.engine.config.retry_limit,
            trace=self.engine.trace,
            node_id=self.node_id,
            depth=self.depth,
            timeout_s=self.engine.config.timeout_by_task.get("plan"),
            fallback_adapter=self.engine.fallback_adapter,
        )
        jury = Jury(
            _pj_adapters,
            self.engine.config.retry_limit,
            self.engine.config.system_prompt,
            trace=self.engine.trace,
            node_id=self.node_id,
            depth=self.depth,
            timeout_s=self.engine.config.timeout_by_task.get("plan"),
            fallback_adapter=self.engine.fallback_adapter,
        )

        retries = 0
        while True:
            candidates = consortium.call(
                {
                    **self._base_context(),
                    **self._referee_context(),
                    **self._spec_context(),
                    "goal": self.goal,
                    "depth": self.depth,
                    "ancestors": self.ancestors[-5:],
                    "constraints": self._constraints(),
                    "system_prompt": self.engine.config.system_prompt,
                },
                validate_plan_schema,
            )
            if not candidates:
                raise RuntimeError("No valid plan candidates")

            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "status": "CONSORTIUM_CANDIDATES",
                    "event": "consortium_candidates",
                    "task": "plan",
                    "tier": _ptier,
                    "candidates": candidates,
                }
            )

            winner, vote, votes, labeled = jury.vote(candidates, node_context={
                **self._base_context(), "goal": self.goal, "depth": self.depth,
            }, task="plan")
            confidence = vote["confidence"]
            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "status": "PLAN_DECIDED",
                    "confidence": confidence,
                    "retries": retries,
                    "event": "plan_decided",
                }
            )
            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "status": "JURY_VOTES",
                    "event": "jury_votes",
                    "task": "plan",
                    "winner_id": vote.get("winner_id", ""),
                    "confidence": confidence,
                    "options": labeled,
                    "votes": votes,
                }
            )
            if confidence >= self.engine.config.confidence_threshold or retries >= self.engine.config.retry_limit:
                winner.pop("_adapter_index", None)
                # Filter validator-only children from the winning plan.
                #
                # WHAT IT REMOVES: child nodes whose goals match _VALIDATOR_CHILD_RE —
                # i.e. nodes whose sole purpose is to check/validate/audit another
                # child's output rather than produce an artifact.  Examples:
                #   REMOVED: "validate the above implementation"
                #   REMOVED: "quality check the auth output"
                #   REMOVED: "pre-check before deployment"
                #   KEPT:    "implement JWT authentication"
                #   KEPT:    "write unit tests for the login endpoint"
                #
                # ROOT_GOAL GUARD: the filter is bypassed entirely when:
                #   (a) The user's root goal itself matches _VALIDATOR_CHILD_RE — e.g.
                #       "audit this codebase" → audit children are intentional.
                #   (b) The Spec's task_class is 'coordinate' or 'analyze' — these tasks
                #       legitimately decompose into review/validation sub-tasks.
                spec = self.engine.spec
                task_class = spec.task_class if spec is not None else "general"
                bypass_filter = (
                    _VALIDATOR_CHILD_RE.search(self.engine.root_goal)
                    or task_class in {"coordinate", "analyze"}
                )
                if not bypass_filter:
                    original_count = len(winner.get("children", []))
                    winner["children"] = [
                        c for c in winner.get("children", [])
                        if not _VALIDATOR_CHILD_RE.search(c.get("goal", ""))
                    ]
                    removed = original_count - len(winner["children"])
                    if removed:
                        self.engine.trace.log({
                            "node_id": self.node_id,
                            "depth": self.depth,
                            "event": "validator_children_filtered",
                            "removed": removed,
                        })

                # ── Plan recovery: structural validation + retry loop ──────
                # Runs only when plan_recovery != "off" and max_plan_retries > 0.
                # Each failed attempt emits plan_validation_failed so the UI graph
                # can show the history.  After max_plan_retries exhausted, emits
                # plan_abandoned and raises so the node falls back to base execution.
                plan_ok, fail_reason = validate_plan_structure(winner)
                cfg = self.engine.config
                plan_attempt = 0

                while not plan_ok and cfg.plan_recovery != "off" and plan_attempt < cfg.max_plan_retries:
                    self.engine.trace.log({
                        "node_id": self.node_id,
                        "depth": self.depth,
                        "event": "plan_validation_failed",
                        "reason": fail_reason,
                        "plan_attempt": plan_attempt,
                        "retry": plan_attempt,
                        "max_retries": cfg.max_plan_retries,
                    })
                    plan_attempt += 1
                    self.engine.trace.log({
                        "node_id": self.node_id,
                        "depth": self.depth,
                        "event": "plan_retry_start",
                        "retry": plan_attempt,
                        "max_retries": cfg.max_plan_retries,
                    })
                    # Re-run consortium + jury for a fresh plan
                    retry_candidates = consortium.call(
                        {
                            **self._base_context(),
                            **self._referee_context(),
                            **self._spec_context(),
                            "goal": self.goal,
                            "depth": self.depth,
                            "ancestors": self.ancestors[-5:],
                            "constraints": self._constraints(),
                            "system_prompt": cfg.system_prompt,
                            "_plan_failure_reason": fail_reason,  # tell agents why last plan failed
                        },
                        validate_plan_schema,
                    )
                    if retry_candidates:
                        winner, vote, _, _ = jury.vote(retry_candidates, node_context={
                            **self._base_context(), "goal": self.goal, "depth": self.depth,
                        }, task="plan")
                        winner.pop("_adapter_index", None)
                        if not bypass_filter:
                            winner["children"] = [
                                c for c in winner.get("children", [])
                                if not _VALIDATOR_CHILD_RE.search(c.get("goal", ""))
                            ]
                        plan_ok, fail_reason = validate_plan_structure(winner)
                    self.engine.trace.log({
                        "node_id": self.node_id,
                        "depth": self.depth,
                        "event": "plan_retry_done",
                        "retry": plan_attempt,
                        "success": plan_ok,
                        "reason": fail_reason if not plan_ok else "",
                    })

                if not plan_ok:
                    if cfg.plan_recovery != "off":
                        self.engine.trace.log({
                            "node_id": self.node_id,
                            "depth": self.depth,
                            "event": "plan_abandoned",
                            "reason": fail_reason,
                            "plan_attempts": plan_attempt + 1,
                        })
                        raise RuntimeError(f"Plan abandoned after {plan_attempt + 1} attempt(s): {fail_reason}")
                    # plan_recovery == "off": silently continue with whatever plan we have

                if plan_attempt > 0 and plan_ok:
                    self.engine.trace.log({
                        "node_id": self.node_id,
                        "depth": self.depth,
                        "event": "plan_replaced",
                        "plan_attempts": plan_attempt + 1,
                    })

                self.engine.trace.log(
                    {
                        "node_id": self.node_id,
                        "depth": self.depth,
                        "status": "PLAN_SELECTED",
                        "children": winner.get("children", []),
                        "event": "plan_selected",
                        "plan_attempt": plan_attempt,
                    }
                )
                return winner
            retries += 1

    def _analyze(self, output: str, mode: str) -> Dict[str, Any]:
        """Use Consortium + Jury to evaluate output quality (decision point 5/6).

        Multiple agents independently judge the output; jury votes on confidence
        and approved/rejected.  Unanimous agreement skips the jury call.
        """
        analysis_payload = {
            **self._base_context(),
            "_raf_role": "analyzer",
            "goal": self.goal,
            "depth": self.depth,
            "output": output,
            "mode": mode,
            "system_prompt": self.engine.config.system_prompt,
        }

        _ac_adapters, _aj_adapters, _atier = self._adapters_for_tier("analysis")
        consortium = Consortium(
            _ac_adapters,
            "analysis",
            self.engine.config.retry_limit,
            trace=self.engine.trace,
            node_id=self.node_id,
            depth=self.depth,
            timeout_s=self.engine.config.timeout_by_task.get("analysis"),
            fallback_adapter=self.engine.fallback_adapter,
        )
        jury = Jury(
            _aj_adapters,
            self.engine.config.retry_limit,
            self.engine.config.system_prompt,
            trace=self.engine.trace,
            node_id=self.node_id,
            depth=self.depth,
            timeout_s=self.engine.config.timeout_by_task.get("analysis"),
            fallback_adapter=self.engine.fallback_adapter,
        )

        candidates = consortium.call(analysis_payload, validate_analysis_result)
        if not candidates:
            raise RuntimeError("No valid analysis candidates")

        self.engine.trace.log(
            {
                "node_id": self.node_id,
                "depth": self.depth,
                "event": "consortium_candidates",
                "task": "analysis",
                "tier": _atier,
                "candidates": candidates,
            }
        )

        # Unanimous on "approved" — all agents agree on pass/fail
        unanimous_approved = Jury.unanimous(candidates, "approved")
        if unanimous_approved is not None:
            n = len(candidates)
            conf = 0.75 + 0.20 * min(n, 3) / 3
            winner = candidates[0]
            vote: Dict[str, Any] = {"winner_id": "option-0", "confidence": conf}
            labeled = [{"option_id": f"option-{i}", "payload": c} for i, c in enumerate(candidates)]
            votes: list = [
                {"agent_id": i, "vote": {"winner_id": "option-0", "confidence": conf, "ranked": []}}
                for i in range(n)
            ]
        else:
            winner, vote, votes, labeled = jury.vote(
                candidates,
                node_context={**self._base_context(), "goal": self.goal, "depth": self.depth},
                task="analysis",
            )

        winner.pop("_adapter_index", None)
        self.engine.trace.log(
            {
                "node_id": self.node_id,
                "depth": self.depth,
                "event": "jury_votes",
                "task": "analysis",
                "winner_id": vote.get("winner_id", ""),
                "confidence": vote.get("confidence", 0.0),
                "options": labeled,
                "votes": votes,
            }
        )
        return winner

    def _refine_children(self, children: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        For each planned child, use Consortium + Jury to clarify its goal,
        success criteria, and dependencies before execution begins.
        """
        _rc_adapters, _rj_adapters, _rtier = self._adapters_for_tier("refine_context")
        consortium = Consortium(
            _rc_adapters,
            "refine_context",
            self.engine.config.retry_limit,
            trace=self.engine.trace,
            node_id=self.node_id,
            depth=self.depth,
            timeout_s=self.engine.config.timeout_by_task.get("refine_context"),
            fallback_adapter=self.engine.fallback_adapter,
        )
        jury = Jury(
            _rj_adapters,
            self.engine.config.retry_limit,
            self.engine.config.system_prompt,
            trace=self.engine.trace,
            node_id=self.node_id,
            depth=self.depth,
            timeout_s=self.engine.config.timeout_by_task.get("refine_context"),
            fallback_adapter=self.engine.fallback_adapter,
        )

        refined_children: List[Dict[str, Any]] = []
        for child in children:
            payload = {
                **self._base_context(),
                "_raf_role": "refiner",
                "child_id": child["child_id"],
                "goal": child["goal"],
                "depends_on": child.get("depends_on", []),
                "depth": self.depth,
                "ancestors": self.ancestors[-5:] + [self.goal],
                "constraints": self._constraints(),
                "system_prompt": self.engine.config.system_prompt,
            }
            candidates = consortium.call(payload, validate_refined_child)
            if not candidates:
                refined_children.append(child)
                continue
            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "status": "CONSORTIUM_CANDIDATES",
                    "event": "consortium_candidates",
                    "task": "refine_context",
                    "tier": _rtier,
                    "child_id": child["child_id"],
                    "candidates": candidates,
                }
            )

            winner, vote, votes, labeled = jury.vote(candidates, node_context={
                **self._base_context(), "goal": child["goal"], "depth": self.depth + 1,
            }, task="refine_context")
            refined = dict(winner)
            refined["child_id"] = child["child_id"]
            refined["depends_on"] = list(child.get("depends_on", []))
            refined_children.append(refined)

            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "status": "REFINE_CHILD",
                    "child_id": refined["child_id"],
                    "event": "child_refined",
                }
            )
            self.engine.trace.log(
                {
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "status": "JURY_VOTES",
                    "event": "jury_votes",
                    "task": "refine_context",
                    "child_id": refined["child_id"],
                    "winner_id": vote.get("winner_id", ""),
                    "confidence": vote.get("confidence", 0.0),
                    "options": labeled,
                    "votes": votes,
                }
            )
        return refined_children

    # ── scope check ───────────────────────────────────────────────────────────

    def _scope_check_and_retry(
        self,
        result: Dict[str, Any],
        base_payload: Dict[str, Any],
        task: str,
    ) -> Dict[str, Any]:
        """
        Ask the LLM whether the result stays on-topic. If not, retry once with
        explicit scope feedback injected into the prompt.
        """
        try:
            scope = call_json_with_repair(
                self.engine.adapter,
                "scope_check",
                {
                    **self._base_context(),
                    "_raf_role": "scope_guard",
                    "goal": self.goal,
                    "depth": self.depth,
                    "output": result.get("output", ""),
                    "ancestors": self.ancestors[-3:],
                },
                validate_scope_check,
                1,
            )
        except Exception:
            return result

        if scope.get("on_topic", False):  # default False: missing field triggers retry
            return result

        self.engine.trace.log(
            {
                "node_id": self.node_id,
                "depth": self.depth,
                "event": "scope_drift_detected",
                "reason": scope.get("reason", ""),
            }
        )
        retry_payload = dict(base_payload)
        retry_payload["scope_feedback"] = (
            f"Previous output was off-topic: {scope.get('reason', '')}. "
            f"Stay tightly focused on the goal: {self.goal}"
        )
        try:
            result = call_json_with_repair(
                self.engine.adapter,
                task,
                retry_payload,
                validate_base_execution_result,
                self.engine.config.retry_limit,
            )
        except Exception:
            pass
        return result

    # ── helpers ───────────────────────────────────────────────────────────────

    def _cache_key(self) -> str:
        """Compute a short cache key for this node's goal under the current spec+ledger.

        The key is a 16-hex-char SHA-256 prefix of the JSON-serialised tuple:
          (goal, sorted required items, sorted locked decisions)

        Including ``required`` and ``locked`` ensures that the same goal text
        gets different cache slots when the spec requirements or ledger state differ —
        a child that runs after "db=PostgreSQL" is committed must produce a
        PostgreSQL-compatible output, not a cached result from a clean-ledger run.

        This is called in both the cache-read path (before execution) and the
        cache-write path (after execution), so the key is always consistent.
        """
        import hashlib, json as _json
        spec = self.engine.spec
        required = tuple(sorted(spec.required)) if spec else ()
        locked = tuple(sorted(self.engine.ledger.locked().items()))
        key_data = _json.dumps(
            {"goal": self.goal, "required": required, "locked": locked},
            sort_keys=True,
        )
        return hashlib.sha256(key_data.encode()).hexdigest()[:16]

    def _cache_write(self, result: Optional[Dict[str, Any]]) -> None:
        """Write result to the goal cache if it qualifies.

        Only writes when:
        - depth > 0 (root is never repeated in the same run)
        - result has non-empty output (empty = failed execution, not worth caching)
        - result is not a clarification request (mode=clarify means the output is
          a question, not a cacheable answer)

        Uses setdefault() so the first writer wins — if two parallel children both
        compute the same goal concurrently, whichever finishes first populates the
        cache and the second write is a no-op.
        """
        if self.depth == 0 or not result or not result.get("output"):
            return
        meta = result.get("metadata", {})
        if meta.get("mode") == "clarify":
            return
        ckey = self._cache_key()
        with self.engine._cache_lock:
            self.engine._goal_cache.setdefault(ckey, result)

    @staticmethod
    def _compress_output(result: Dict[str, Any], max_chars: int = 800) -> str:
        """Return a compact representation of a node result for injection into prompts.

        When the output text is short (≤ max_chars) it is returned verbatim.
        When it is long, the pre-generated ``key_points`` list is used as a
        structured summary — no extra API call needed.  This prevents token-limit
        blowouts in two places:

        1. ``child_outputs`` in the merge payload — each child's output is sent to
           N merge agents; a 10-child plan with 2000-char outputs would otherwise
           inject ~20k chars before the merge prompt even begins.
        2. ``dep_context`` injected into child goals — a deeply-chained dependency
           whose output is large would inflate every downstream child's prompt.

        Falls back to a truncated excerpt if ``key_points`` is absent or empty.
        """
        output = result.get("output", "")
        if len(output) <= max_chars:
            return output
        points = result.get("key_points", [])
        if points:
            return "[Summary] " + " | ".join(str(p) for p in points)
        return output[:max_chars] + "…"

    def _constraints(self) -> Dict[str, Any]:
        """Return the scope constraints dict from engine config."""
        return {
            "focus": self.engine.config.scope_focus,
            "forbidden_topics": self.engine.config.forbidden_topics,
        }

    def _referee_context(self) -> Dict[str, Any]:
        """Return the current referee state for injection into agent payloads.

        Returns an empty dict when no referee report exists yet (first node).
        Agents treat this as read-only grounded truth — they cannot debate it.
        """
        report = self.engine.last_referee_report
        if report is None:
            return {}
        return {"_referee": self.engine.referee.to_context(report)}

    def _spec_context(self) -> Dict[str, Any]:
        """Return the frozen Spec and current locked Ledger for agent payloads.

        HOW _spec AND _ledger FLOW THROUGH THE SYSTEM
        -----------------------------------------------
        Both keys are prefixed with ``_`` which makes them "meta-keys" in
        PromptBasedAdapter._META_KEYS.  Meta-keys are:
          1. READ by _build_frame() to render the "Frozen Spec" and
             "Locked Decisions" blocks at the top of every agent prompt.
          2. STRIPPED from the clean_payload dict before JSON serialisation,
             so agents never see them duplicated in the raw Payload section.

        This separation matters: agents see the Spec and Ledger as clearly
        labelled, formatted, human-readable blocks — not as buried JSON keys
        that might get confused with task data.

        Returns an empty dict when spec is None (before run() initialises it,
        or if spec extraction failed completely).

        The ledger snapshot is taken at call time, so agents always see the
        decisions that were locked as of when their particular prompt was built.
        Decisions locked by a concurrent sibling that hasn't finished yet will
        not appear — that is acceptable because the ledger gate runs AFTER
        proposals are collected, and will reject any proposal that contradicts
        a decision locked between prompt-build and proposal-collection.
        """
        spec = self.engine.spec
        if spec is None:
            return {}
        ctx: Dict[str, Any] = {
            "_spec": {
                "required": spec.required,
                "forbidden": spec.forbidden,
                "success_criteria": spec.success_criteria,
                "domain": spec.domain,
                "task_class": spec.task_class,
            }
        }
        # Only inject _ledger when there are locked decisions — avoids adding
        # an empty "Locked Decisions" block to every prompt before any node
        # has committed to any technology choices.
        locked = self.engine.ledger.locked()
        if locked:
            ctx["_ledger"] = locked
        return ctx

    def _quality_gate(
        self, candidates: List[Dict[str, Any]], output_key: str = "output"
    ) -> List[Dict[str, Any]]:
        """Filter placeholder or empty candidates before jury voting.

        WHY A QUALITY GATE EXISTS
        --------------------------
        Without this filter, a consortium agent that returns a one-sentence
        placeholder ("I will implement the authentication system") can win the
        jury vote if the other agents gave longer but noisier answers.  The jury
        uses confidence-weighted scoring, not length — a short confident answer
        can beat a long uncertain one.  The gate removes candidates that are
        structurally empty before the jury even sees them.

        THREE SIGNALS (any one failing → candidate rejected)
        -----------------------------------------------------
        1. Length threshold (MIN_LEN = 100 chars after stripping)
           The absolute floor.  Anything under 100 chars is definitionally
           incomplete for a design or code task.  This catches pure
           "I cannot help with that" responses and single-sentence non-answers.

        2. Goal-similarity ceiling (overlap > 0.85)
           A proposal whose word set is more than 85% identical to the goal
           word set is likely just a paraphrase of the goal, not an actual
           execution.  Example: goal is "implement JWT login" and output is
           "We will implement JWT login for the system" — near-identical words,
           no actual implementation.  The 0.85 threshold avoids false positives
           on legitimate short answers that naturally use many goal words.

        3. Concreteness check (only for outputs < 800 chars)
           Uses _CONCRETE_ELEMENT_RE (see spec.py) to verify the output
           contains at least one structural element: an endpoint path, an HTTP
           method, a code keyword, a SQL statement, a class name, etc.
           Applied ONLY to short outputs because long outputs are unlikely to
           be purely fluffy — a 1000-char output almost certainly has some
           concrete content.  The 800-char threshold is the inflection point
           where the false-positive rate of the concreteness regex becomes
           acceptable.

        FALLBACK BEHAVIOUR
        ------------------
        If ALL candidates are rejected by the gate, the full original list is
        returned unchanged.  The gate never hard-blocks a run.  The jury then
        votes on whatever was available.  This matches the general RAF design
        principle: degrade gracefully rather than crash.

        Parameters
        ----------
        candidates:
            List of proposal dicts from the Consortium call.
        output_key:
            The dict key holding the content to evaluate (usually "output").
        """
        from raf.core.spec import _is_concrete_output

        MIN_LEN = 100
        goal_words = set(re.findall(r"\w+", self.goal.lower()))
        spec = self.engine.spec

        def _is_placeholder(content: str) -> bool:
            content = content.strip()
            # Signal 1: too short to be a real answer
            if len(content) < MIN_LEN:
                return True
            # Signal 2: nearly identical words to the goal — it's a restatement
            if goal_words:
                content_words = set(re.findall(r"\w+", content.lower()))
                overlap = len(goal_words & content_words) / len(goal_words)
                if overlap > 0.85:
                    return True
            # Signal 3: short output with no concrete domain-appropriate element.
            # Uses domain-aware _is_concrete_output() so culinary/fitness/creative
            # outputs are not rejected for lacking code blocks or SQL statements.
            # Only apply to short outputs; long outputs are unlikely to be purely fluffy.
            if len(content) < 800 and not _is_concrete_output(content, spec):
                return True
            return False

        filtered = [
            c for c in candidates
            if not _is_placeholder(str(c.get(output_key, "")))
        ]
        return filtered if filtered else candidates

    def _ledger_gate(
        self, candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove candidates that contradict locked ledger decisions.

        HOW THE GATE WORKS
        ------------------
        Each candidate may include a ``decisions`` dict (e.g. {"db": "MongoDB"}).
        The gate calls SpecLedger.check_compatible() which compares each key in
        the proposal against the ledger.  If the ledger already has a different
        value for the same key, the candidate is rejected and a trace event is
        emitted explaining the conflict.

        Candidates that have no ``decisions`` field at all (or an empty dict)
        are passed through unconditionally — they are not committing to any
        choice, so there is nothing to conflict with.

        FALLBACK LOGIC: WHY PASSING THROUGH IS SAFER THAN BLOCKING
        ------------------------------------------------------------
        If every single candidate contradicts a locked decision, rejecting all
        of them would leave the jury with nothing to vote on and crash the run.
        In this pathological case (which can happen if a user changes the
        locked tech mid-run, or if the LLM systematically proposes the same
        technology), it is better to let the contradicting proposals through
        and let the jury decide than to hard-block.

        The ``ledger_conflict_fallback`` trace event makes this fallback visible
        so a developer can spot systematic ledger conflicts in the logs.

        Parameters
        ----------
        candidates:
            List of proposal dicts from the Consortium call.  Evaluated in
            order; all are checked against the current ledger snapshot.
        """
        filtered = []
        for c in candidates:
            decisions = c.get("decisions")
            # Candidates without a decisions dict make no technology commitments
            # and cannot contradict the ledger — pass them through directly.
            if not isinstance(decisions, dict) or not decisions:
                filtered.append(c)
                continue
            compatible, conflict = self.engine.ledger.check_compatible(decisions)
            if compatible:
                filtered.append(c)
            else:
                # Log the specific conflict so developers can trace which node
                # tried to override which locked decision.
                self.engine.trace.log({
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "event": "ledger_candidate_rejected",
                    "conflict": conflict,
                })

        if not filtered:
            # All candidates were rejected — passing through is safer than crashing.
            # The run can still succeed; the ledger conflict is logged for inspection.
            self.engine.trace.log({
                "node_id": self.node_id,
                "depth": self.depth,
                "event": "ledger_conflict_fallback",
                "reason": "all candidates contradicted locked decisions; passing through",
            })
            return candidates
        return filtered

    def _lock_decisions(self, result: Dict[str, Any]) -> None:
        """Lock key decisions declared by the winning agent into the SpecLedger.

        TWO-PART LOGIC: EXPLICIT LOCKING + HEURISTIC CONTRADICTION WARNING
        -------------------------------------------------------------------
        Part 1 — Explicit locking:
            The winning agent's ``decisions`` dict (e.g. {"db": "PostgreSQL",
            "framework": "FastAPI"}) is passed to SpecLedger.lock().  The ledger
            applies first-write-wins per key.  Only the winning agent's decisions
            are locked — not the consortium candidates that lost the jury vote.

        Part 2 — Heuristic contradiction warning:
            extract_implicit_decisions() scans the winning agent's output TEXT
            for technology signals (framework names, DB names, auth patterns)
            using the _IMPLICIT_SIGNALS regex list.  If any detected signal
            contradicts a PREVIOUSLY locked decision, an ``implicit_decision_conflict``
            trace event is emitted.

            This is a WARNING ONLY — the implicit signals are NOT locked into the
            ledger.  Locking implicit signals would be too aggressive: an output
            might mention "you could use Redis as a cache layer" without committing
            to Redis, and locking it would block legitimate MongoDB choices later.

            The distinction: explicit ``decisions`` dict = commitment → lock.
            Detected text signal = possible hint → warn only.
        """
        # Part 1: Lock explicit decisions declared by the winning agent.
        # Only lock keys that pass the _LEDGER_KEY_RE allowlist (dot-notation format).
        # This prevents LLM-invented free-form keys like "holographic_hashing" or
        # "fault-tolerant" from polluting the ledger with noise that downstream
        # agents cannot reliably detect or match.
        decisions = result.get("decisions")
        if isinstance(decisions, dict) and decisions:
            valid_decisions = {k: v for k, v in decisions.items() if _LEDGER_KEY_RE.match(k)}
            skipped = [k for k in decisions if not _LEDGER_KEY_RE.match(k)]
            if skipped:
                self.engine.trace.log({
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "event": "decisions_key_skipped",
                    "skipped_keys": skipped,
                    "reason": "key not in dot-notation format (category.subtype)",
                })
            if valid_decisions:
                self.engine.ledger.lock(valid_decisions)
                self.engine.trace.log({
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "event": "decisions_locked",
                    "decisions": valid_decisions,
                })

        # Part 2: Heuristic scan for implicit technology signals in output text.
        # We only warn — never lock — on implicit signals.
        output = result.get("output", "")
        if output:
            implicit = extract_implicit_decisions(output)
            if implicit:
                compatible, conflict = self.engine.ledger.check_compatible(implicit)
                if not compatible:
                    # The output text implies a technology that contradicts a
                    # locked decision.  This is a diagnostic warning — the run
                    # continues but the developer can see the inconsistency.
                    self.engine.trace.log({
                        "node_id": self.node_id,
                        "depth": self.depth,
                        "event": "implicit_decision_conflict",
                        "conflict": conflict,
                        "implicit_signals": implicit,
                    })

    def _spec_repair_loop(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Validate output against the Spec and spawn repair nodes for failures.

        WHY DEPTH-GATED
        ---------------
        Repair nodes are full RafNodes — they consume budget, can themselves
        go recursive, and could in theory spawn their own repair nodes creating
        an unbounded cascade.  To prevent this, the loop only runs at nodes
        whose depth is at or below ``config.spec_repair_depth_limit`` (default
        0 = root node only).

        Example:
          depth_limit=0 → only the root's output is repaired
          depth_limit=1 → root and its direct children are repaired
          depth_limit=2 → root, children, and grandchildren are repaired

        Raising the limit gives better spec coverage at the cost of more nodes.
        Keep it low for budget-sensitive runs.

        WHY BUDGET-CHECKED
        ------------------
        Each repair attempt costs at least 2 nodes (the repair node + the
        repair node's own execution node).  Before spawning, we check that at
        least 2 nodes remain in the budget.  If not, we break out of the loop
        and do the final validation on whatever output we have.

        WHAT "PATCH" MEANS (VS REWRITE)
        --------------------------------
        The repair_goal is carefully worded to say "PATCH (do not rewrite)".
        A rewrite would throw away correct sections and regenerate everything,
        potentially re-introducing different problems or losing locked decisions.
        A patch adds only what is missing and removes only what is forbidden —
        the existing correct content is passed as context and the agent is
        explicitly instructed to preserve it.

        WHY REPAIR RUNS BEFORE _ANALYZE
        ---------------------------------
        _analyze() evaluates whether the output is approved and reports
        confidence.  It makes no sense to evaluate an output that is already
        known to be missing required items — the analyzer would correctly
        reject it, and then there would be nothing to do.  Running repair
        before analyze means the analyzer sees the best possible output.

        Process
        -------
        1. Early exit if spec is None, spec.required is empty, or depth exceeds limit.
        2. Loop up to config.spec_repair_limit times:
           a. Validate output against spec.required / spec.forbidden.
           b. If passed → emit spec_validation_final and return immediately.
           c. If failed and budget < 2 → break (can't afford a repair node).
           d. Build a "patch" goal with the missing items and locked decisions listed.
           e. Spawn a repair RafNode and run it.
           f. If repair produced output → replace result with repair_result.
        3. After the loop: final validation emit and return (always).
           Never hard-blocks — worst case returns the unrepaired original output.
        """
        spec = self.engine.spec
        # No spec or empty required list → nothing to validate against
        if spec is None or not spec.required:
            return result
        # Depth gate: only repair at shallow nodes to protect budget
        if self.depth > self.engine.config.spec_repair_depth_limit:
            return result

        validator = self.engine._spec_validator
        for attempt in range(self.engine.config.spec_repair_limit):
            passed, missing, violations = validator.validate(spec, result.get("output", ""))
            if passed:
                # All required items found, no forbidden terms — repair not needed.
                self.engine.trace.log({
                    "node_id": self.node_id,
                    "depth": self.depth,
                    "event": "spec_validation_final",
                    "passed": True,
                    "missing": [],
                    "violations": [],
                })
                return result

            self.engine.trace.log({
                "node_id": self.node_id,
                "depth": self.depth,
                "event": "spec_repair_start",
                "attempt": attempt + 1,
                "missing": missing,
                "violations": violations,
            })

            # Budget check: each repair node costs at least 2 nodes
            if self.engine.remaining_nodes() < 2:
                break  # not enough budget to spawn a repair node — skip to final emit

            # Inject locked decisions into the repair goal so the repair agent
            # knows not to change what was already committed.  This prevents a
            # repair from switching "FastAPI" to "Django" while adding a missing
            # password-reset endpoint.
            locked_str = ""
            locked = self.engine.ledger.locked()
            if locked:
                locked_str = (
                    "Locked decisions (DO NOT change these):\n"
                    + "\n".join(f"  {k}: {v}" for k, v in locked.items())
                    + "\n"
                )
            # "PATCH" framing: add missing items, remove violations, preserve the rest.
            # The current output is appended (truncated to 3000 chars) as the base
            # to patch — the repair agent sees what already exists.
            #
            # F12 — Repair prompt feedback anchoring:
            # Cap feedback to the top 3 most concrete missing items and 200 chars total.
            # Abstract items like "ensure correctness" cause the repair agent to produce
            # validator-shaped text (meta-commentary) instead of goal-shaped additions.
            # Prepend PRIMARY OBJECTIVE prominently so the agent always returns to the
            # goal rather than focusing entirely on the validator's feedback.
            _REPAIR_MAX_ITEMS = 3
            _REPAIR_MAX_CHARS = 200
            feedback_items = missing[:_REPAIR_MAX_ITEMS]
            feedback_str = "; ".join(feedback_items)
            if len(feedback_str) > _REPAIR_MAX_CHARS:
                feedback_str = feedback_str[:_REPAIR_MAX_CHARS] + "…"

            repair_goal = (
                f"PRIMARY OBJECTIVE (never deviate from this): {self.goal}\n"
                f"\nPATCH (do not rewrite) the output below to address the missing items.\n"
                f"Missing (up to {_REPAIR_MAX_ITEMS} items shown): {feedback_str}\n"
                + (f"Forbidden violations to remove: {violations[:3]}\n" if violations else "")
                + locked_str
                + "RULES:\n"
                "  • The PRIMARY OBJECTIVE above is the source of truth — not the missing list.\n"
                "  • Do NOT change any locked decisions listed above.\n"
                "  • Preserve existing correct sections verbatim.\n"
                "  • Only ADD missing sections and REMOVE forbidden violations.\n"
                "  • Do not rewrite what is already correct.\n"
                f"Current output:\n{result.get('output', '')[:3000]}"
            )
            try:
                repair_node = self.engine.create_node(
                    repair_goal,
                    self.depth + 1,
                    self.node_id,
                    self.ancestors + [self.goal],
                )
            except RuntimeError:
                # Budget exhausted between the remaining_nodes() check and
                # create_node() — two parallel nodes raced past the guard.
                # Treat as budget < 2 and stop attempting repairs.
                break
            repair_result = repair_node.run()
            # Only replace result if the repair node actually produced output.
            # An empty repair output would be worse than the original.
            if repair_result.get("output"):
                result = repair_result

        # Final validation after all attempts — emit regardless of pass/fail
        # so the trace log always shows the final spec compliance state.
        passed, missing, violations = validator.validate(spec, result.get("output", ""))
        self.engine.trace.log({
            "node_id": self.node_id,
            "depth": self.depth,
            "event": "spec_validation_final",
            "passed": passed,
            "missing": missing,
            "violations": violations,
        })
        return result

    def _base_context(self) -> Dict[str, Any]:
        """Common RAF meta-keys injected into every LLM payload.

        These are prefixed with ``_`` so ``PromptBasedAdapter`` strips them
        from the serialised payload while still using them to build the frame.
        """
        return {
            "_root_goal": self.engine.root_goal,
            "_max_depth": self.engine.config.max_depth,
        }


# ── engine ────────────────────────────────────────────────────────────────────

class RafEngine:
    """
    Orchestrates a full RAF run.

    Responsibilities
    ----------------
    - Holds the single shared RafConfig, adapters, and TraceLogger.
    - Tracks the global node counter (budget enforcement).
    - Creates all RafNode instances via create_node().
    - Checks for cooperative cancellation via cancel_event.
    - Routes tool calls.
    - Provides the on_plan_ready callback hook for human-in-the-loop approval.

    Multi-model support
    -------------------
    Pass a list of adapters to give each consortium/jury seat its own model.
    Passing a single adapter replicates it across all seats (original behaviour).
    config.consortium_size and config.jury_size are updated to match the
    supplied adapter lists so the rest of the system stays consistent.

    Parameters
    ----------
    config : RafConfig
        All tunable parameters (depth, size, thresholds, etc.).
    adapters : ModelAdapter | list[ModelAdapter]
        Adapter(s) for the Consortium proposal agents.
    trace : TraceLogger
        Event emitter — writes JSON to stdout and spinner to stderr.
    jury_adapters : ModelAdapter | list[ModelAdapter] | None
        Adapter(s) for the Jury voting agents.  Defaults to the same as
        *adapters* when omitted.
    on_plan_ready : callable | None
        Called with (node_id, plan) after planning. Should return the
        (possibly edited) plan. Used for human approval gates.
    cancel_event : threading.Event | None
        When set, the engine raises RuntimeError("Run cancelled") at the
        next cancellation checkpoint.
    """

    def __init__(
        self,
        config: RafConfig,
        adapters,
        trace,
        jury_adapters=None,
        on_plan_ready: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
        cancel_event: Optional[threading.Event] = None,
        fallback_adapter=None,
        leaf_adapters=None,
        mid_adapters=None,
        root_adapters=None,
        mid_jury_adapters=None,
        root_jury_adapters=None,
    ) -> None:
        self.config = config
        # Normalise to lists — single adapter becomes [adapter] * consortium_size
        self.consortium_adapters: List = (
            adapters if isinstance(adapters, list)
            else [adapters] * config.consortium_size
        )
        # Jury adapter resolution — explicit list wins; otherwise replicate the
        # primary consortium adapter to config.jury_size so the user-configured
        # jury size is always respected (avoids silently matching consortium_size).
        if isinstance(jury_adapters, list):
            self.jury_adapters: List = jury_adapters
        elif jury_adapters is not None:
            self.jury_adapters = [jury_adapters] * config.jury_size
        else:
            self.jury_adapters = [self.consortium_adapters[0]] * config.jury_size
        # Keep config sizes in sync with actual adapter counts
        config.consortium_size = len(self.consortium_adapters)
        config.jury_size = len(self.jury_adapters)

        # ── Tier adapters for depth-based model routing ────────────────────────
        # Three tiers: Tier 0 (leaf workers), Tier 1 (planners/mergers),
        # Tier 2 (root/referee/analysis).  Each falls back to consortium_adapters
        # when not configured so existing runs without tier config work unchanged.
        #
        # Tier 0 — leaf_adapters: fast/cheap models for deep base_execute nodes.
        # Tier 1 — mid_adapters: capable models for mid-level planning/merging.
        # Tier 2 — root_adapters: strongest models for root+analysis decisions.
        #
        # Jury tiers:
        #   mid_jury_adapters — jury for Tier 0 and Tier 1 (floor: never weak grades weak)
        #   root_jury_adapters — jury for Tier 2 analysis/root decisions
        #
        # When a tier is None, it falls back through the chain:
        #   leaf → consortium_adapters
        #   mid  → consortium_adapters
        #   root → consortium_adapters
        #   mid_jury  → jury_adapters
        #   root_jury → jury_adapters
        self.leaf_adapters: List = leaf_adapters if leaf_adapters is not None else self.consortium_adapters
        self.mid_adapters: List = mid_adapters if mid_adapters is not None else self.consortium_adapters
        self.root_adapters: List = root_adapters if root_adapters is not None else self.consortium_adapters
        self.mid_jury_adapters: List = mid_jury_adapters if mid_jury_adapters is not None else self.jury_adapters
        self.root_jury_adapters: List = root_jury_adapters if root_jury_adapters is not None else self.jury_adapters

        self.trace = trace
        self._node_counter = 0
        self.on_plan_ready = on_plan_ready
        self.cancel_event = cancel_event
        # Fallback adapter: used when all primary consortium/jury agents time out.
        # None = no fallback (fail hard on total timeout).
        self.fallback_adapter = fallback_adapter
        # Token budget tracking — thread-safe counter accumulated via usage callbacks
        # wired onto every adapter.  record_tokens() is the sole write path.
        self._tokens_used: int = 0
        self._tokens_lock = threading.Lock()
        # Wire _usage_callback on every unique adapter object so all API calls
        # (Consortium, Jury, SpecExtractor, SpecValidator) feed into this counter.
        self._wire_usage_callbacks()
        # Goal memoization cache — keyed by _cache_key(); reset at each run() call.
        # Avoids re-running identical sub-goals in recursive tasks (e.g. Hanoi).
        # Thread-safe: parallel child nodes read/write concurrently.
        self._goal_cache: Dict[str, Dict] = {}
        self._cache_lock = threading.Lock()
        # Set by run() so all nodes can include the top-level goal in their prompts
        self.root_goal: str = ""
        # Referee — instantiated in run(); updated after each node completes
        self.referee: Optional[Referee] = None
        self.last_referee_report: Optional[RefereeReport] = None
        # Spec + Ledger — instantiated in run(); shared across ALL nodes in the tree.
        # They are declared here (not in run()) so type checkers see them as attributes.
        # run() always reinitialises them before execution starts.
        #
        # self.spec          — frozen Spec object for this run; None until run() calls extract()
        # self.ledger        — SpecLedger accumulating locked decisions as the run progresses
        # self._spec_extractor — holds the cached LLM extraction; ensures extract() runs once
        # self._spec_validator — shared SpecValidator (holds adapter ref; stateless otherwise)
        self.spec: Optional[Spec] = None
        self.ledger: SpecLedger = SpecLedger()
        self._spec_extractor: Optional[SpecExtractor] = None
        self._spec_validator: Optional[SpecValidator] = None

    @property
    def adapter(self):
        """First consortium adapter — backward-compatible alias."""
        return self.consortium_adapters[0]

    @property
    def consortium_adapter(self):
        """First consortium adapter — backward-compatible alias."""
        return self.consortium_adapters[0]

    @property
    def jury_adapter(self):
        """First jury adapter — backward-compatible alias."""
        return self.jury_adapters[0]

    def _wire_usage_callbacks(self) -> None:
        """Attach record_tokens as the usage callback on every unique adapter.

        Called once in __init__ after all adapter lists are finalised.  Uses
        object identity (id()) to avoid wiring the same adapter object twice
        when an adapter is reused across consortium, jury, and tier seats.
        """
        seen: set = set()
        all_adapters = (
            self.consortium_adapters
            + self.jury_adapters
            + self.leaf_adapters
            + self.mid_adapters
            + self.root_adapters
            + self.mid_jury_adapters
            + self.root_jury_adapters
        )
        for adapter in all_adapters:
            if id(adapter) not in seen:
                adapter._usage_callback = self.record_tokens
                seen.add(id(adapter))

    def record_tokens(self, tokens_in: int, tokens_out: int) -> None:
        """Thread-safe accumulator called by every adapter after each API call."""
        with self._tokens_lock:
            self._tokens_used += tokens_in + tokens_out

    @property
    def tokens_used(self) -> int:
        """Total input+output tokens used so far across all adapters in this run."""
        with self._tokens_lock:
            return self._tokens_used

    def _check_cancelled(self) -> None:
        """Raise if cancelled or if the token budget is exceeded."""
        if self.cancel_event and self.cancel_event.is_set():
            raise RuntimeError("Run cancelled by user")
        if self.config.token_budget is not None and self._tokens_used >= self.config.token_budget:
            self.trace.log({
                "event": "token_budget_exceeded",
                "tokens_used": self._tokens_used,
                "token_budget": self.config.token_budget,
            })
            raise RuntimeError(
                f"Token budget exceeded: {self._tokens_used} >= {self.config.token_budget}"
            )

    def _next_node_id(self) -> str:
        self._node_counter += 1
        return f"node-{self._node_counter}"

    def remaining_nodes(self) -> int:
        """Nodes remaining in the global budget."""
        return self.config.max_nodes_total - self._node_counter

    def create_node(
        self,
        goal: str,
        depth: int,
        parent_id: Optional[str],
        ancestors: Optional[List[str]] = None,
        plan_child_id: Optional[str] = None,
    ) -> RafNode:
        """
        Allocate a new RafNode. Raises if the budget is exhausted.

        Parameters
        ----------
        goal : str
            The task for the new node.
        depth : int
            Recursion depth of the new node.
        parent_id : str | None
            ID of the parent node.
        ancestors : list[str] | None
            Goal chain from root to parent (inclusive).
        plan_child_id : str | None
            The plan child_id this node fulfils (for frontend linking).
        """
        if self._node_counter >= self.config.max_nodes_total:
            raise RuntimeError("Max nodes limit reached")
        return RafNode(self, self._next_node_id(), goal, depth, parent_id, ancestors, plan_child_id=plan_child_id)

    def execute_tool(self, name: str, args: Dict[str, Any]) -> str:
        """Execute a named tool and return its string result."""
        try:
            from raf.core.tools import execute_tool
            return execute_tool(name, args)
        except Exception as exc:
            return f"Tool error: {exc}"

    def run(self, goal: str) -> Dict[str, Any]:
        """
        Start a RAF run from a root node with the given goal.

        Returns the result dict: {"output": str, "metadata": {...}}.

        SPEC EXTRACTION STEP (why it runs before the root node)
        -------------------------------------------------------
        The Spec must be extracted BEFORE any node executes, because:
          1. Every agent prompt includes the Frozen Spec block.  If we extracted
             lazily (inside the first node that needs it), the root node's
             _maybe_clarify and _decide_mode calls would run without spec context.
          2. The SpecLedger needs to be clean for this run.  Calling run() again
             on the same engine instance (e.g. after a clarification round) would
             otherwise accumulate decisions from the previous attempt.

        The sequence is:
          1. Reset ledger → clean slate for this run
          2. Instantiate SpecExtractor with the goal and the primary adapter
          3. Call extract() — this makes ONE LLM call (or returns the minimal
             fallback Spec if it fails) and caches the result
          4. Emit spec_extracted event — frontend and logs see what was extracted
          5. Increment node counter for root (root is not created via create_node
             because it has a fixed ID "root"; create_node would generate "node-1")
          6. Create root RafNode and run it

        NOTE ON NODE COUNTER
        --------------------
        The root node ID is hardcoded as "root" and created directly (bypassing
        create_node).  We manually increment _node_counter here so the budget
        correctly reflects that the root is consuming one slot.  All subsequent
        nodes are created via create_node() which auto-increments.
        """
        self.root_goal = goal
        self._goal_cache = {}  # reset per-run so re-runs on the same engine start clean
        # ── run_started event — emitted before any node runs ──────────────────
        # This event is the self-describing header for the trace.  It captures
        # the prompt version, schema version, and key config values so any
        # exported trace can be fully attributed without external context.
        from raf.llm.prompt_adapter import _PROMPT_VERSION
        self.trace.log({
            "event": "run_started",
            "goal": goal,
            "prompt_version": _PROMPT_VERSION,
            "schema_version": "12",
            "config": {
                "max_depth": self.config.max_depth,
                "max_nodes_total": self.config.max_nodes_total,
                "consortium_size": self.config.consortium_size,
                "jury_size": self.config.jury_size,
                "confidence_threshold": self.config.confidence_threshold,
                "token_budget": self.config.token_budget,
            },
            "adapters": {
                "consortium_count": len(self.consortium_adapters),
                "jury_count": len(self.jury_adapters),
            },
        })
        self.referee = Referee(goal, adapter=self.consortium_adapters[0])
        self.last_referee_report = None
        # Reset spec/ledger at run() start to support engine re-use
        # (e.g. if run() is called again after a clarification response).
        self.ledger = SpecLedger()
        self._spec_extractor = SpecExtractor(goal, adapter=self.consortium_adapters[0])
        self._spec_validator = SpecValidator(self.consortium_adapters[0])
        # Extract the Spec once, synchronously, before any node starts.
        # This blocks until the LLM responds (or until the fallback kicks in).
        self.spec = self._spec_extractor.extract()
        # Apply manual domain override from config (user-set config.domain wins).
        from raf.core.spec import _VALID_DOMAINS
        if self.config.domain and self.config.domain in _VALID_DOMAINS:
            # Replace the auto-detected domain; preserve all other Spec fields.
            from dataclasses import replace as _dc_replace
            self.spec = _dc_replace(self.spec, domain=self.config.domain)
        self.trace.log({
            "event": "spec_extracted",
            "required": self.spec.required,
            "forbidden": self.spec.forbidden,
            "success_criteria": self.spec.success_criteria,
            "domain": self.spec.domain,
            "task_class": self.spec.task_class,
            "concrete_indicators": self.spec.concrete_indicators,
            "prompt_version": _PROMPT_VERSION,
        })
        # Count the root node against the budget manually since it bypasses create_node.
        self._node_counter += 1  # count root so budget is accurate
        root = RafNode(self, "root", goal, 0, None, ancestors=[])
        result = root.run()
        # Inject total token usage into result metadata so callers can log it.
        if isinstance(result, dict) and isinstance(result.get("metadata"), dict):
            result["metadata"]["tokens_used"] = self.tokens_used
            result["metadata"]["nodes_used"] = self._node_counter
        return result
