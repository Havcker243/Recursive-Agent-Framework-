"""
raf.schemas
===========
Pydantic-free validation helpers and the :class:`RafConfig` dataclass.

Every LLM response is validated by one of the ``validate_*`` functions before
it enters the engine.  Validation raises :class:`SchemaError` on bad data so
the JSON-repair utilities can retry the call.

:class:`RafConfig` is the single source of truth for all tunable parameters.
It is constructed by :class:`~server.run_manager.RunManager` from API request
overrides, with sensible defaults for every field.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


class SchemaError(ValueError):
    """Raised when an LLM response fails schema validation."""


def _require_keys(obj: Dict[str, Any], keys: List[str]) -> None:
    for key in keys:
        if key not in obj:
            raise SchemaError(f"Missing key: {key}")


def _require_type(name: str, value: Any, expected: type) -> None:
    if not isinstance(value, expected):
        raise SchemaError(f"{name} must be {expected.__name__}")


def _require_number(name: str, value: Any) -> float:
    """Accept int or float (LLMs often return integers for confidence values)."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise SchemaError(f"{name} must be a number")
    return float(value)


def _require_str_list(name: str, value: Any) -> None:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise SchemaError(f"{name} must be list[str]")


def validate_mode_decision(obj: Dict[str, Any]) -> Dict[str, Any]:
    _require_keys(obj, ["mode", "reason"])
    _require_type("mode", obj["mode"], str)
    _require_type("reason", obj["reason"], str)
    if obj["mode"] not in {"base", "recursive"}:
        raise SchemaError("mode must be 'base' or 'recursive'")
    return obj


def validate_plan(obj: Dict[str, Any]) -> Dict[str, Any]:
    _require_keys(obj, ["children", "rationale"])
    _require_type("children", obj["children"], list)
    _require_type("rationale", obj["rationale"], str)
    for child in obj["children"]:
        _require_keys(child, ["child_id", "goal", "depends_on"])
        _require_type("child_id", child["child_id"], str)
        _require_type("goal", child["goal"], str)
        _require_str_list("depends_on", child["depends_on"])
    return obj


def validate_plan_structure(plan: Dict[str, Any]) -> Tuple[bool, str]:
    """Fast structural check on a selected plan before running its children.

    Returns (ok, reason).  Does NOT raise — callers decide how to recover.

    Checks
    ------
    - At least one child present.
    - Every child has a non-empty goal string.
    - Child ids are unique.
    - No child depends on an id that doesn't exist in the plan (broken dep).
    - No self-dependency.
    """
    children = plan.get("children", [])
    if not children:
        return False, "Plan has no children"
    goals_empty = [c.get("child_id", "?") for c in children if not str(c.get("goal", "")).strip()]
    if goals_empty:
        return False, f"Empty goal on children: {goals_empty}"
    ids = [c["child_id"] for c in children]
    if len(ids) != len(set(ids)):
        return False, "Duplicate child_id values in plan"
    id_set = set(ids)
    for c in children:
        for dep in c.get("depends_on", []):
            if dep not in id_set:
                return False, f"Child '{c['child_id']}' depends on unknown '{dep}'"
            if dep == c["child_id"]:
                return False, f"Child '{c['child_id']}' depends on itself"
    return True, ""


def validate_refined_child(obj: Dict[str, Any]) -> Dict[str, Any]:
    _require_keys(obj, ["child_id", "goal", "depends_on"])
    _require_type("child_id", obj["child_id"], str)
    _require_type("goal", obj["goal"], str)
    _require_str_list("depends_on", obj["depends_on"])
    return obj


def validate_vote_result(obj: Dict[str, Any]) -> Dict[str, Any]:
    _require_keys(obj, ["winner_id", "ranked", "confidence"])
    _require_type("winner_id", obj["winner_id"], str)
    _require_type("ranked", obj["ranked"], list)
    obj["confidence"] = _require_number("confidence", obj["confidence"])
    for item in obj["ranked"]:
        _require_keys(item, ["option_id", "score", "reason"])
        _require_type("option_id", item["option_id"], str)
        item["score"] = int(_require_number("score", item["score"]))
        _require_type("reason", item["reason"], str)
    if not (0.0 <= obj["confidence"] <= 1.0):
        raise SchemaError("confidence must be between 0.0 and 1.0")
    return obj


def validate_base_execution_result(obj: Dict[str, Any]) -> Dict[str, Any]:
    _require_keys(obj, ["output", "key_points", "scope_notes"])
    _require_type("output", obj["output"], str)
    _require_str_list("key_points", obj["key_points"])
    _require_str_list("scope_notes", obj["scope_notes"])
    # tool_call is optional — validate structure if present, else remove
    if "tool_call" in obj:
        tc = obj["tool_call"]
        if not isinstance(tc, dict) or not isinstance(tc.get("name"), str):
            del obj["tool_call"]
    # DECISIONS FIELD (optional)
    # decisions is optional — only present when the agent is committing to a
    # technology choice.  An absent decisions key is perfectly valid and means
    # the agent made no explicit technology commitment this call.
    #
    # WHY IT IS OPTIONAL:
    #   Not every base execution involves a technology commitment.  A node
    #   that writes "Generate a password reset email template" doesn't need to
    #   declare db/framework/auth choices — those are owned by other nodes.
    #
    # STR→STR COERCION:
    #   The LLM sometimes returns integer values ({"port": 5432}) or nested
    #   objects.  We coerce all keys and values to str with str(k)/str(v) so
    #   the SpecLedger can compare them consistently.  Empty-string keys or
    #   values are filtered out — they indicate the LLM returned a placeholder.
    if "decisions" in obj:
        d = obj["decisions"]
        if not isinstance(d, dict):
            # Malformed — remove entirely rather than propagating bad data
            del obj["decisions"]
        else:
            # Coerce to flat str→str; drop entries with empty keys or values
            obj["decisions"] = {str(k): str(v) for k, v in d.items() if k and v}
    return obj


def validate_merge_result(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a structured merge response.

    Extends base execution validation with three new fields that make the
    merged output inspectable — not just a text blob:

    sections (optional list):
        Each section has:
          - title       : short label (e.g. "Authentication", "Data Model")
          - content     : the synthesised text for that section
          - source_child_ids : which child node IDs contributed this section

        Allows post-hoc attribution: which child was over-weighted, which was
        dropped, where the merger invented a transition.

        The field is optional so older merge agents that return only "output"
        still pass validation.  When absent, downstream code treats the output
        as a single un-attributed section.

    unresolved_conflicts (optional list[str]):
        Explicit contradictions between child outputs that the merger could
        not resolve.  E.g. "Child A said PostgreSQL; Child B said DynamoDB —
        could not determine which is correct for the goal."

        Surfaced in the trace so the user or a repair node can address them.
        An empty list means the merger believes all conflicts are resolved.

    decisions (optional dict):
        Same as base_execute — technology choices committed at merge time.
        Coerced to str→str and passed to the SpecLedger.
    """
    # Require and validate the core output field
    _require_keys(obj, ["output"])
    _require_type("output", obj["output"], str)

    # Carry over standard optional fields from base_execute validation
    for field_name in ("key_points", "scope_notes"):
        obj.setdefault(field_name, [])
        if not isinstance(obj[field_name], list):
            obj[field_name] = []

    # sections — optional structured breakdown
    raw_sections = obj.get("sections")
    if raw_sections is not None and isinstance(raw_sections, list):
        validated_sections = []
        for s in raw_sections:
            if not isinstance(s, dict):
                continue
            title = str(s.get("title", ""))
            content = str(s.get("content", ""))
            source_ids = s.get("source_child_ids", [])
            if not isinstance(source_ids, list):
                source_ids = []
            if title or content:
                validated_sections.append({
                    "title": title,
                    "content": content,
                    "source_child_ids": [str(i) for i in source_ids if i],
                })
        obj["sections"] = validated_sections
    else:
        obj["sections"] = []

    # unresolved_conflicts — optional list of conflict descriptions
    raw_conflicts = obj.get("unresolved_conflicts")
    if isinstance(raw_conflicts, list):
        obj["unresolved_conflicts"] = [str(c) for c in raw_conflicts if c]
    else:
        obj["unresolved_conflicts"] = []

    # decisions — same coercion as base_execute
    if "decisions" in obj:
        d = obj["decisions"]
        if not isinstance(d, dict):
            del obj["decisions"]
        else:
            obj["decisions"] = {str(k): str(v) for k, v in d.items() if k and v}

    return obj


_VALID_SPEC_DOMAINS = frozenset({
    "technical", "culinary", "fitness", "creative", "business", "academic", "general"
})


def validate_spec_extract(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the response from a spec_extract LLM call.

    WHAT IT VALIDATES
    -----------------
    The spec_extract call returns five fields: domain, concrete_indicators,
    required items, forbidden items, and success criteria.

    Only ``required`` is mandatory.  All other fields default gracefully so
    older or simplified LLM responses still work without crashing.

    NEW FIELDS (domain-agnostic spec system)
    ----------------------------------------
    domain:
        One of the _VALID_SPEC_DOMAINS strings.  Defaults to "general" if
        absent or if the LLM returns an unrecognised value.
    concrete_indicators:
        List of domain-specific phrases that signal concrete output.  Defaults
        to an empty list so the quality gate falls back to built-in patterns.
    """
    if not isinstance(obj.get("required"), list):
        raise SchemaError("missing 'required' list")
    # Apply defaults for optional fields before type-checking them
    obj.setdefault("forbidden", [])
    obj.setdefault("success_criteria", [])
    obj.setdefault("domain", "general")
    obj.setdefault("concrete_indicators", [])
    _require_str_list("required", obj["required"])
    _require_str_list("forbidden", obj["forbidden"])
    _require_str_list("success_criteria", obj["success_criteria"])
    # Normalise domain — unknown values fall back to "general"
    if not isinstance(obj["domain"], str) or obj["domain"] not in _VALID_SPEC_DOMAINS:
        obj["domain"] = "general"
    if not isinstance(obj["concrete_indicators"], list):
        obj["concrete_indicators"] = []
    # Coerce to str and drop empty entries
    obj["concrete_indicators"] = [str(c) for c in obj["concrete_indicators"] if c]
    # task_class: optional, defaults to "general", must be one of the valid classes
    _VALID_TASK_CLASSES = frozenset({"implement", "coordinate", "analyze", "create", "transform", "general"})
    obj.setdefault("task_class", "general")
    if not isinstance(obj["task_class"], str) or obj["task_class"] not in _VALID_TASK_CLASSES:
        obj["task_class"] = "general"
    return obj


def validate_spec_validate(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the response from a spec_validate LLM call (Stage 2 of SpecValidator).

    WHAT IT VALIDATES
    -----------------
    The spec_validate call asks the LLM to judge whether an output satisfies
    the spec requirements and avoids the forbidden items.  This validator
    enforces the structure of that judgment before it flows back to the caller.

    THE TWO OUTPUT FIELDS EXPLAINED
    --------------------------------
    ``passed`` (bool, REQUIRED)
        The summary verdict.  True only when:
          - Every required item is covered (possibly under different phrasing), AND
          - No forbidden item appears in the output.
        This is the single bit that _spec_repair_loop() checks to decide
        whether to spawn a repair node.

    ``missing`` (list[str], defaults to [])
        Required items the LLM judges as NOT covered.  The LLM may assess
        semantic coverage more leniently than the deterministic Stage 1 check —
        for example, "authentication" can cover "login flow" if the context
        makes it clear they are the same thing.

    ``violations`` (list[str], defaults to [])
        Forbidden items that appeared in the output.  These are typically
        already caught by the deterministic Stage 1 check, but the LLM stage
        may catch context-dependent mentions (e.g. "we could use blockchain
        theoretically" vs actually recommending it).

    ``passed`` is mandatory — without it, the repair loop cannot decide what
    to do and the call should be retried.  ``missing`` and ``violations``
    default to empty lists since the LLM may omit them when everything passes.
    """
    if not isinstance(obj.get("passed"), bool):
        raise SchemaError("missing 'passed' bool")
    # Defaults for the detail fields — absent is valid (means nothing missing/violated)
    obj.setdefault("missing", [])
    obj.setdefault("violations", [])
    _require_str_list("missing", obj["missing"])
    _require_str_list("violations", obj["violations"])
    return obj


def validate_analysis_result(obj: Dict[str, Any]) -> Dict[str, Any]:
    _require_keys(obj, ["approved", "confidence", "reason"])
    _require_type("approved", obj["approved"], bool)
    obj["confidence"] = _require_number("confidence", obj["confidence"])
    _require_type("reason", obj["reason"], str)
    if not (0.0 <= obj["confidence"] <= 1.0):
        raise SchemaError("confidence must be between 0.0 and 1.0")
    # locally_valid and goal_completed are optional for backwards compatibility.
    # When present they must be booleans; when absent they default to `approved`.
    for field_name in ("locally_valid", "goal_completed"):
        if field_name in obj:
            _require_type(field_name, obj[field_name], bool)
        else:
            obj[field_name] = obj["approved"]
    return obj


def validate_clarify_request(obj: Dict[str, Any]) -> Dict[str, Any]:
    # Coerce common model variants before strict validation:
    #   "question" (singular) → "questions" list
    #   "questions": "string"  → "questions": ["string"]
    if "question" in obj and "questions" not in obj:
        val = obj.pop("question")
        obj["questions"] = [val] if isinstance(val, str) else (val if isinstance(val, list) else [])
    if "questions" in obj and isinstance(obj["questions"], str):
        obj["questions"] = [obj["questions"]]
    _require_keys(obj, ["questions"])
    _require_str_list("questions", obj["questions"])
    return obj


def validate_node_result(obj: Dict[str, Any]) -> Dict[str, Any]:
    _require_keys(obj, ["output", "metadata"])
    _require_type("output", obj["output"], str)
    _require_type("metadata", obj["metadata"], dict)
    return obj


def validate_scope_check(obj: Dict[str, Any]) -> Dict[str, Any]:
    _require_keys(obj, ["on_topic", "reason"])
    _require_type("on_topic", obj["on_topic"], bool)
    _require_type("reason", obj["reason"], str)
    return obj


@dataclass
class RafConfig:
    max_depth: int = 4
    max_nodes_total: int = 500
    max_children_per_plan: int = 20
    min_remaining_for_recursive: int = 5
    recursive_confidence_margin: float = 0.15
    clarify_before_execute: bool = True
    clarify_root_only: bool = True
    max_parallel_children: int = 4
    # Scope enforcement — LLM-based (no more keyword lists)
    scope_focus: str = "Only address the goal. Avoid tangents and unrelated topics."
    forbidden_topics: List[str] = field(default_factory=list)
    consortium_size: int = 3
    jury_size: int = 3
    confidence_threshold: float = 0.6
    retry_limit: int = 3
    # Model call timeout limits in seconds.  The first implementation does not
    # kill provider threads; it stops waiting, emits model_call_timeout, and
    # continues with completed valid results when possible.
    timeout_by_task: Dict[str, int] = field(default_factory=lambda: {
        "mode_decision": 300,   # was 60  (+4 min)
        "plan": 360,            # was 120 (+4 min)
        "refine_context": 300,  # was 60  (+4 min)
        "base_execute": 360,    # was 120 (+4 min)
        "vote": 300,            # was 60  (+4 min)
        "merge": 420,           # was 180 (+4 min)
        "analysis": 330,        # was 90  (+4 min)
    })
    red_flag_terms: List[str] = field(default_factory=list)
    system_prompt: str = ""
    # Plan approval: pause after planning and wait for user to approve/edit children
    plan_approval_required: bool = False
    # Tool use: allow base_execute to call external tools
    tools_enabled: bool = False
    # run_python is excluded from defaults — it executes arbitrary code and must be explicitly opted in
    available_tools: List[str] = field(default_factory=lambda: ["web_search", "http_get"])
    # Spec repair: how many times to retry missing-requirement repair, and at what depth.
    #
    # spec_repair_limit — maximum repair attempts per node before giving up.
    #   Each attempt spawns one repair RafNode (which may itself go recursive).
    #   TRADE-OFF: more attempts = better spec coverage, more node budget consumed.
    #   Default 2 gives two chances to fix missing items without spending too many nodes.
    #   Set to 0 to disable repair entirely (validation still runs, just no repair spawned).
    #
    # spec_repair_depth_limit — only nodes at or above this depth run the repair loop.
    #   0 = root node only (the most conservative, budget-safe default)
    #   1 = root + its direct children
    #   2 = root + children + grandchildren
    #
    #   WHY DEPTH-LIMIT THE REPAIR LOOP:
    #   A repair node is a full RafNode — it can itself go recursive and spawn children.
    #   If repair ran at every depth, a 4-deep tree with 3 agents and 2 repair attempts
    #   could add ~30 extra nodes on top of the planned budget.  Depth-limiting keeps
    #   repair at the level where it matters most (the final merged output) without
    #   cascading through the entire tree.
    #
    #   EXAMPLE: with spec_repair_depth_limit=0 (default):
    #     root node → spec_repair_loop runs (validates final merged output)
    #     child nodes → spec_repair_loop skips (just returns result as-is)
    spec_repair_limit: int = 2
    spec_repair_depth_limit: int = 0  # 0 = root node only; raise for per-branch repair
    # Domain override — if set, overrides the auto-detected domain from the goal text.
    # Valid values: "technical", "culinary", "fitness", "creative", "business", "academic", "general"
    # When None (default), the domain is detected automatically by keyword matching + LLM.
    domain: Optional[str] = None
    # Token budget — maximum total input+output tokens across all LLM calls in a run.
    # None = unlimited.  When exceeded, _check_cancelled() raises and emits
    # a token_budget_exceeded trace event so the run stops cleanly.
    # Rule of thumb: a typical 3-node base run uses ~3k–8k tokens; a 15-node recursive
    # run uses ~30k–80k tokens.  Set this to catch runaway recursion early.
    token_budget: Optional[int] = None
    # Force recursive — skip _decide_mode() at root and always decompose into children.
    # Children still decide their own mode freely (they can go base naturally).
    # Use this when the goal sounds "simple" to the LLM but you know it has sub-parts.
    force_recursive: bool = False
    # Plan recovery — retry plan generation when the selected plan fails validation.
    #
    # max_plan_retries: how many extra plan attempts before giving up and raising.
    #   0 = no retry (fail fast)
    #   2 = two extra attempts (default; balanced between quality and token cost)
    #
    # plan_recovery: controls whether recovery is active and how it behaves.
    #   "off"  — no retry on bad plan; raises immediately on validation failure
    #   "auto" — silently retry up to max_plan_retries; emits plan_validation_failed +
    #            plan_retry_start/done events so the UI graph shows each attempt
    #   "ask"  — reserved for future human-in-the-loop (treated as "auto" by backend
    #            until the UI approval flow is wired)
    max_plan_retries: int = 2
    plan_recovery: str = "off"   # "off" | "auto" | "ask"
    # Fallback model — used when ALL consortium/jury agents time out and 0 results
    # are available.  A single call to the fallback adapter is attempted; if it
    # succeeds the run continues normally.  If the fallback also fails, the node
    # fails as it would without a fallback configured.
    #
    # Intended use: pair a fast/cheap model (fallback) with slower primary models
    # so the system degrades gracefully under heavy load rather than failing hard.
    #
    # fallback_provider: LLM provider key ("openrouter", "gemini", etc.)
    #   Empty string = no fallback (default: fail on total timeout)
    # fallback_model: specific model id within fallback_provider
    #   Empty string = use provider default
    fallback_provider: str = ""
    fallback_model: str = ""
