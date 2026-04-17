"""
raf.llm.prompt_adapter
======================
Shared prompt construction for all LLM adapters.

Every agent call — whether from a Consortium, a Jury, or a direct node call —
goes through ``_build_prompt()``.  The prompt has four layers:

1. **RAF context frame** (``_build_frame``)
   Tells the agent *what system it is part of*, *what role it is playing right
   now*, and *where in the execution tree it sits*.  This is the most important
   layer: an agent that knows it is one of three competing proposers will
   deliberately differentiate its answer; a jury agent that knows its confidence
   score is used as a voting weight will be more calibrated.

2. **Task + schema**
   The task name (e.g. ``"plan"``, ``"vote"``, ``"base_execute"``) and the
   exact JSON schema the agent must return.

3. **Payload**
   The task-specific data (goal, depth, ancestors, candidates to vote on, etc.).
   Internal ``_``-prefixed meta-keys are stripped before serialisation so the
   agent never sees them twice.

4. **Spec / Ledger frame blocks** (within ``_build_frame``)
   Two additional structured blocks injected when the ``_spec`` and ``_ledger``
   meta-keys are present in the payload:

   - **Frozen Spec block** — shows the required items, forbidden items, and
     success criteria extracted from the root goal.  Agents see this as an
     immutable checklist.  Jury agents use it as a hard eligibility gate:
     any proposal missing a required item or containing a forbidden item is
     scored 0 before the lexicographic scoring order even begins.

   - **Locked Decisions block** — shows the technology choices committed by
     earlier winning agents (e.g. framework=FastAPI, db=PostgreSQL).  Agents
     are told that contradicting these will cause their proposal to be rejected.
     The ledger gate in node.py enforces this mechanically on the proposals
     before jury voting; the block in the prompt tells agents up-front so they
     don't waste a proposal on a path that will be filtered anyway.

These blocks are rendered inside ``_build_frame`` from meta-keys, then the
meta-keys are stripped before the payload JSON is serialised — so agents see
the information once, formatted, not buried in raw JSON.
"""

import json
from typing import Any, Dict

from raf.llm.adapter import ModelAdapter

# Prompt version — increment the minor number when prompt wording changes within a
# session; increment the major number when schema or scoring rubric changes.
# Injected into every run_started trace event so traces are self-describing.
# Enables post-hoc attribution: "did this improvement come from routing, prompts, or model?"
_PROMPT_VERSION = "12.2"

# Personas injected per consortium agent index to produce genuinely diverse proposals.
PERSONAS = [
    "You are a thorough, methodical planner. Prioritize completeness and coverage of all relevant aspects.",
    "You are a creative problem-solver. Look for non-obvious approaches, shortcuts, and innovative angles.",
    "You are a critical analyst. Focus on risks, edge cases, potential failures, and what could go wrong.",
    "You are a pragmatic executor. Focus on the simplest, fastest path to a working result.",
    "You are a big-picture strategist. Think about long-term implications and how each step fits the whole.",
]

# Meta-keys injected by the framework — stripped from the payload before serialisation.
# These are read by _build_frame() and rendered as structured, human-readable blocks
# at the top of every prompt.  They are NEVER dumped raw into the payload JSON that
# agents see — agents would get duplicate information in an ugly format.
#
# Key inventory:
#   _agent_index  — which agent in the consortium/jury this is (0-indexed), used to
#                   assign a persona and display "agent N of M" in the frame
#   _agent_total  — total number of agents in this consortium/jury, shown alongside index
#   _raf_role     — the agent's current role ("consortium", "jury", "executor", etc.),
#                   selects the appropriate role-framing block in _build_frame
#   _root_goal    — the top-level run goal, shown as "Run goal:" in the frame so every
#                   agent always sees the big picture even deep in the tree
#   _max_depth    — max recursion depth from config, shown as "depth N/M" in the frame
#   _referee      — current Referee state (coverage progress, hash, invariant status),
#                   rendered as the "Referee — grounded state, read-only" block
#   _spec         — frozen Spec dict (required/forbidden/success_criteria), rendered as
#                   the "Frozen Spec — immutable, read-only" block; jury agents use this
#                   as an eligibility hard gate before lexicographic scoring
#   _ledger       — current locked decisions snapshot from SpecLedger, rendered as the
#                   "Locked Decisions — contradict these and your proposal is rejected" block
_META_KEYS = frozenset({
    "_agent_index", "_agent_total", "_raf_role", "_root_goal", "_max_depth",
    "_referee", "_spec", "_ledger",
})

# Domain-specific DECISIONS field key suggestions (dot-notation: category.subtype).
# Injected into the DECISIONS block when agents are asked to commit to key choices.
# Keys MUST match _LEDGER_KEY_RE in node.py: "^[a-z][a-z0-9_]{1,30}\.[a-z][a-z0-9_]{1,30}$"
# Free-form keys without a dot are silently skipped by the ledger allowlist.
_DOMAIN_DECISION_KEYS: Dict[str, str] = {
    "technical":  "lang.backend, framework.web, db.primary, cache.layer, auth.method, storage.files, email.provider",
    "culinary":   "cuisine.style, diet.restriction, method.cooking, output.difficulty, output.serving_size",
    "fitness":    "training.style, equipment.required, schedule.frequency, intensity.level, diet.approach",
    "creative":   "output.genre, narrative.pov, narrative.tense, audience.target, output.tone",
    "business":   "market.target, revenue.model, channel.distribution, pricing.strategy, product.differentiator",
    "academic":   "research.methodology, citation.style, scope.breadth, sources.primary, argument.type",
    "general":    "approach.style, output.format, scope.level, constraint.primary",
}


class PromptBasedAdapter(ModelAdapter):
    """Base class for LLM adapters that build a structured text prompt from task + payload.

    Subclasses implement ``call_raw`` using their SDK; all prompt construction
    lives here so every provider gets identical framing.
    """

    # ── schema registry ───────────────────────────────────────────────────────

    def _schema_for_task(self, task: str) -> str:
        """Return the JSON schema string for the given task name.

        These schemas are injected into every prompt as the exact output format
        the agent must return.  Keeping them here (rather than inline in the
        prompt string) means the repair prompt can reference the same schema by
        calling ``_schema_for_task(original_task)`` without duplicating strings.
        """
        if task == "mode_decision":
            return '{"mode":"base|recursive","reason":"string"}'
        if task == "plan":
            return '{"children":[{"child_id":"string","goal":"string","depends_on":["string"]}],"rationale":"string"}'
        if task == "vote":
            return '{"winner_id":"string","ranked":[{"option_id":"string","score":0,"reason":"string"}],"confidence":0.0}'
        if task == "base_execute":
            # The "decisions" field is the key addition for the SpecLedger system.
            # It is optional — agents only include it when they are committing to a
            # technology choice.  validate_base_execution_result() in schemas.py
            # coerces all keys and values to strings and removes empty entries.
            # The "tool_call" field is optional; it triggers the tool loop in _execute_base.
            return '{"output":"string","key_points":["string"],"scope_notes":["string"],"decisions":{"key":"value"},"tool_call":{"name":"string","args":{}}}'
        if task == "merge":
            # Merge agents return a structured contract, not just a text blob.
            # sections: each section attributes content back to source child(ren).
            # unresolved_conflicts: explicit contradictions the merger could not resolve.
            # decisions: technology choices committed at merge time (SpecLedger).
            return (
                '{"output":"string",'
                '"sections":[{"title":"string","content":"string","source_child_ids":["child_id"]}],'
                '"unresolved_conflicts":["description of conflict"],'
                '"key_points":["string"],"scope_notes":["string"],"decisions":{"key":"value"}}'
            )
        if task == "analysis":
            return '{"approved":true,"locally_valid":true,"goal_completed":true,"confidence":0.0,"reason":"string"}'
        if task == "clarify":
            return '{"questions":["string"]}'
        if task == "refine_context":
            return '{"child_id":"string","goal":"string","depends_on":["string"]}'
        if task == "scope_check":
            return '{"on_topic":true,"reason":"string"}'
        if task == "spec_extract":
            # Six fields: domain, task_class, concrete_indicators, required, forbidden, success_criteria.
            # domain is used to gate which default forbidden items apply and to drive
            # domain-adaptive quality checks and jury scoring.
            # task_class tells the engine whether validator children are appropriate.
            return '{"domain":"string","task_class":"implement|coordinate|analyze|create|transform|general","concrete_indicators":["string"],"required":["string"],"forbidden":["string"],"success_criteria":["string"]}'
        if task == "spec_validate":
            # Two-outcome schema: passed bool + lists of what was missing/violated.
            # The LLM is asked to be lenient: "passed" should be true if items are
            # covered semantically even if not verbatim.
            return '{"passed":true,"missing":["string"],"violations":["string"]}'
        if task == "coverage_check":
            # Two shapes: extract_only=True returns requirements list;
            # coverage call returns covered/missing/progress_score.
            return '{"requirements":["string"],"covered":["string"],"missing":["string"],"progress_score":0.0}'
        return "{}"

    # ── RAF context frame ─────────────────────────────────────────────────────

    def _build_frame(self, task: str, payload: Dict[str, Any]) -> str:
        """Return the RAF context block that heads every agent prompt.

        Reads ``_``-prefixed meta-keys from the payload to describe:
        - which system the agent is part of
        - the root goal of the current run
        - where in the execution tree this call sits
        - the agent's specific role (proposer, voter, executor, …)
        """
        raf_role    = payload.get("_raf_role", "")
        agent_index = payload.get("_agent_index")
        agent_total = payload.get("_agent_total")
        root_goal   = payload.get("_root_goal", "")
        depth       = payload.get("depth")
        max_depth   = payload.get("_max_depth")
        goal        = payload.get("goal", "")

        lines = ["[RAF - Recursive Agent Framework]"]

        # Root goal (the big-picture task for this run)
        if root_goal:
            lines.append(f"Run goal   : {root_goal[:140]}")

        # Current node context
        if goal and goal != root_goal:
            depth_str = ""
            if depth is not None and max_depth:
                depth_str = f"depth {depth}/{max_depth} - "
            elif depth is not None:
                depth_str = f"depth {depth} - "
            lines.append(f"This task  : {depth_str}{goal[:140]}")

        # Role-specific framing
        if raf_role == "consortium":
            n = (agent_index or 0) + 1
            m = agent_total or "?"
            others = (m - 1) if isinstance(m, int) else "other"
            lines.append(f"Your role  : CONSORTIUM PROPOSER — agent {n} of {m}")
            lines.append(f"             {others} other agent(s) will independently propose a different answer.")
            lines.append(f"             A separate jury votes on all proposals using confidence-weighted scoring.")
            lines.append(f"             Be specific and deliberately different — avoid the generic default answer.")

        elif raf_role == "jury":
            n = (agent_index or 0) + 1
            m = agent_total or "?"
            lines.append(f"Your role  : JURY VOTER — agent {n} of {m}")
            lines.append(f"             Your reported confidence score is your voting weight.")
            lines.append(f"             A high-confidence minority can outweigh a low-confidence majority.")
            # ELIGIBILITY HARD GATE
            # The jury is told to check eligibility BEFORE scoring.  A proposal that
            # fails the eligibility gate is scored 0 regardless of how good it is on
            # other dimensions.  This prevents the "novelty bias" failure mode where a
            # creative but spec-violating proposal wins because it seemed impressive.
            # Two conditions disqualify a proposal:
            #   1. Missing a Required item → the output doesn't satisfy what the user asked for
            #   2. Contains a Forbidden item → the output introduced unsolicited technology
            lines.append(f"             ELIGIBILITY (hard gate — check BEFORE scoring):")
            lines.append(f"               • Missing any Required item from Frozen Spec → INELIGIBLE (score 0)")
            lines.append(f"               • Contains any Forbidden item from Frozen Spec → INELIGIBLE (score 0)")
            lines.append(f"               • Invents infrastructure not justified by the goal (e.g. distributed lock")
            lines.append(f"                 manager for a sorting task, blockchain for a recipe, holographic hashing")
            lines.append(f"                 for a puzzle) → INELIGIBLE (score 0)")
            # LEXICOGRAPHIC SCORING ORDER
            # The scoring criteria are ordered by priority: criterion 1 is more important
            # than criterion 2, which is more important than criterion 3, etc.  Ties at
            # criterion N are broken by criterion N+1.  This is "lexicographic" in the
            # sense that earlier criteria dominate later ones.
            #
            # SIMPLICITY is criterion 3, not an afterthought.  This directly counters the
            # LLM tendency to produce enterprise-sounding output with invented protocols
            # and unnecessary infrastructure.  The simplest valid answer always beats a
            # more complex answer that satisfies the same spec items.
            #
            # Novelty is last and penalised.  Adding unsolicited features loses points
            # even when those features are technically correct.
            spec_meta = payload.get("_spec", {})
            domain = spec_meta.get("domain", "general") if isinstance(spec_meta, dict) else "general"
            lines.append(f"             SCORING ORDER for eligible proposals (lexicographic):")
            lines.append(f"               1. Spec coverage    — satisfies ALL required items from the Frozen Spec")
            lines.append(f"               2. Ledger consistency — does not contradict any Locked Decision")
            lines.append(f"               3. Simplicity       — SIMPLER valid answer BEATS complex one; no invented")
            lines.append(f"                                      protocols, no unsolicited infrastructure, no assumed")
            lines.append(f"                                      enterprise requirements. Prefer direct execution.")
            lines.append(f"               4. Domain quality   — appropriate for domain '{domain}'; no off-domain elements")
            lines.append(f"               5. Clarity          — output directly usable by the intended audience")
            lines.append(f"               6. Novelty          — TIE-BREAKER ONLY; penalise unsolicited extra features")

        elif raf_role == "executor":
            lines.append(f"Your role  : BASE EXECUTOR (leaf node)")
            lines.append(f"             This task will NOT be decomposed further. Execute it directly and completely.")
            lines.append(f"             Your output is the final answer for this subtask.")
            lines.append(f"             SIMPLICITY PRINCIPLE: use the simplest approach that fully satisfies the goal.")
            lines.append(f"             Do NOT invent protocols, infrastructure, or enterprise machinery unless the")
            lines.append(f"             goal explicitly requires it. A direct answer beats a robust-sounding one.")

        elif raf_role == "merger":
            n_outputs = len(payload.get("child_outputs", []))
            child_ids = [str(o.get("child_id", i)) for i, o in enumerate(payload.get("child_outputs", []))]
            lines.append(f"Your role  : OUTPUT MERGER")
            lines.append(f"             {n_outputs} parallel child task(s) have completed.")
            lines.append(f"             Child IDs available for attribution: {child_ids}")
            lines.append(f"             Synthesise their outputs into a single coherent answer for the parent goal.")
            lines.append(f"             Do not just concatenate — integrate, deduplicate, and resolve contradictions.")
            lines.append(f"             STRUCTURED CONTRACT — your response MUST include:")
            lines.append(f"               • output         : the full synthesised text")
            lines.append(f"               • sections       : list of {{title, content, source_child_ids}} — attribute")
            lines.append(f"                                  each section to the child(ren) that produced it")
            lines.append(f"               • unresolved_conflicts : list any contradictions you could NOT resolve,")
            lines.append(f"                                  e.g. 'Child A said PostgreSQL; Child B said DynamoDB'")
            lines.append(f"             SIMPLICITY PRINCIPLE: the merged result should be as simple as the goal")
            lines.append(f"             requires — not as complex as any individual child made it sound. Drop")
            lines.append(f"             invented infrastructure, unsolicited protocols, and enterprise machinery")
            lines.append(f"             that was not present in the original goal.")

        elif raf_role == "analyzer":
            lines.append(f"Your role  : QUALITY ANALYZER")
            lines.append(f"             Independently evaluate whether the output successfully accomplished the goal.")
            lines.append(f"             You are separate from the agent that produced the output — be critical.")

        elif raf_role == "clarifier":
            lines.append(f"Your role  : GOAL CLARIFIER")
            lines.append(f"             Determine if the root goal is specific enough to proceed.")
            lines.append(f"             Ask at most ONE clarifying question. If the goal is clear, return an empty list.")

        elif raf_role == "scope_guard":
            lines.append(f"Your role  : SCOPE VALIDATOR")
            lines.append(f"             Determine whether the output directly addresses the stated goal.")
            lines.append(f"             Only flag off-topic if the output clearly drifts — good-faith attempts pass.")

        elif raf_role == "refiner":
            lines.append(f"Your role  : CHILD GOAL REFINER")
            lines.append(f"             Sharpen a planned child's goal before it executes.")
            lines.append(f"             Make the success criterion explicit and incorporate dependency context.")

        # FROZEN SPEC BLOCK
        # The Spec is extracted from the root goal once by SpecExtractor before
        # any node runs, then injected into every agent prompt via the _spec meta-key.
        # Agents see it as a clearly labelled read-only checklist, not raw JSON.
        #
        # WHAT AGENTS MUST DO WITH IT:
        #   - Proposals must satisfy every Required item (used for eligibility gate).
        #   - Forbidden items must not appear (violations → ineligible in jury scoring).
        #   - Criteria are acceptance tests — agents should structure output to pass them.
        #
        # Items are capped at 8 required and 6 forbidden for prompt legibility.
        # The full lists live in the Spec object on the engine.
        spec = payload.get("_spec") if isinstance(payload, dict) else None
        if spec and isinstance(spec, dict):
            lines.append("-" * 56)
            lines.append("[Frozen Spec — immutable, read-only, set at run start]")
            req = spec.get("required", [])
            forb = spec.get("forbidden", [])
            crit = spec.get("success_criteria", [])
            task_class = spec.get("task_class", "general")
            if task_class and task_class != "general":
                lines.append(f"  Task class: {task_class}  (shapes what kinds of children are appropriate)")
            if req:
                lines.append(f"  Required : {' | '.join(str(r) for r in req[:8])}")
            if forb:
                lines.append(f"  Forbidden: {' | '.join(str(f) for f in forb[:6])}")
            if crit:
                lines.append(f"  Criteria : {' | '.join(str(c) for c in crit[:6])}")
            lines.append("  Your output MUST satisfy every Required item.")
            lines.append("  Forbidden items must not appear unless the user explicitly asked.")

        # LOCKED DECISIONS BLOCK
        # The Ledger accumulates technology choices committed by earlier winning agents.
        # These are shown as an explicit rejection rule: agents whose proposals
        # contradict a locked decision will be filtered by the ledger gate in _ledger_gate()
        # BEFORE the jury votes.  Telling agents up-front in the prompt prevents them
        # from wasting a proposal slot on a path that will be mechanically rejected.
        #
        # The block only appears when there ARE locked decisions (ledger is non-empty).
        # Before any node commits a decision, this block does not show — no false
        # constraints before the first commitment.
        ledger = payload.get("_ledger") if isinstance(payload, dict) else None
        if ledger and isinstance(ledger, dict):
            lines.append("-" * 56)
            lines.append("[Locked Decisions — contradict these and your proposal is rejected]")
            for k, v in list(ledger.items())[:8]:
                lines.append(f"  {k:<12}: {v}")

        # Referee state — grounded facts injected after every node completes.
        # Agents must treat these as read-only truth, not as something to debate.
        referee = payload.get("_referee") if isinstance(payload, dict) else None
        if referee and isinstance(referee, dict):
            lines.append("-" * 56)
            lines.append("[Referee — grounded state, read-only]")
            lines.append(f"  Progress : {referee.get('progress', 0):.0%}")
            covered = referee.get("covered", [])
            missing  = referee.get("missing",  [])
            if covered:
                lines.append(f"  Covered  : {', '.join(str(c) for c in covered[:6])}")
            if missing:
                lines.append(f"  Missing  : {', '.join(str(m) for m in missing[:6])}")
            lines.append(f"  Hash     : {referee.get('state_hash', '')}")
            lines.append(f"  Step     : {referee.get('step', 0)}")
            if not referee.get("invariant_ok", True):
                lines.append(f"  INVARIANT VIOLATION: {referee.get('invariant_error', '')}")
                lines.append("  Your proposal MUST correct this before proceeding.")
            else:
                lines.append("  Do not debate these facts — plan around them.")

        lines.append("-" * 56)
        return "\n".join(lines) + "\n"

    # ── prompt assembly ───────────────────────────────────────────────────────

    def _build_prompt(self, task: str, payload: Dict[str, Any]) -> str:  # noqa: C901
        schema       = self._schema_for_task(task)
        # Strip internal meta-keys before serialising so agents don't see them
        clean_payload = {k: v for k, v in payload.items() if k not in _META_KEYS}
        payload_text  = json.dumps(clean_payload, ensure_ascii=True)

        # ── RAF context frame (always first) ──
        frame = self._build_frame(task, payload)

        # ── System / custom prompt ──
        system_prompt = ""
        if isinstance(payload, dict):
            custom = payload.get("system_prompt")
            if isinstance(custom, str) and custom.strip():
                system_prompt = f"System instruction: {custom.strip()}\n"

        # ── Agent persona (consortium diversity via different roles) ──
        persona_prompt = ""
        agent_index = payload.get("_agent_index") if isinstance(payload, dict) else None
        if isinstance(agent_index, int) and agent_index < len(PERSONAS):
            persona_prompt = f"Perspective: {PERSONAS[agent_index]}\n"

        # ── Ancestor goal chain ──
        ancestor_prompt = ""
        if isinstance(payload, dict):
            ancestors = payload.get("ancestors", [])
            if ancestors:
                chain = " → ".join(str(a)[:80] for a in ancestors[-5:])
                ancestor_prompt = f"Goal ancestry (root → parent): {chain}\n"

        # ── Special-case: repair prompt ──
        if task == "repair":
            original_task    = payload.get("task", "")
            original_schema  = self._schema_for_task(original_task)
            original_payload = json.dumps(payload.get("task_payload", {}), ensure_ascii=True)
            return (
                f"{frame}"
                "Your previous response was invalid JSON or did not match the schema. Fix it.\n"
                f"Original task: {original_task}\n"
                f"Schema: {original_schema}\n"
                f"Original payload: {original_payload}\n"
                f"Error: {payload.get('error', '')}\n"
                f"Last response: {payload.get('last_raw', '')}\n"
                "Return ONLY valid JSON."
            )

        # SPEC_EXTRACT SPECIAL CASE
        # This prompt is used by SpecExtractor to derive the Spec from the root goal.
        # It gets a fully custom prompt instead of the generic task/schema/payload format
        # because the instructions need to be extremely precise about what belongs in
        # "required" vs "forbidden".
        #
        # THE FORBIDDEN / REQUIRED DISTINCTION
        # Required: what the user EXPLICITLY asked for — extracted from the goal text.
        #   e.g. "JWT login" if the goal mentions JWT; "password reset" if mentioned.
        #   Do NOT invent requirements that aren't in the goal.
        #
        # Forbidden: HIGH-DRIFT PRIMITIVES ONLY — technologies that are almost never
        #   needed by a vanilla web/backend request and were not asked for.
        #   e.g. blockchain, smart contracts, IPFS, ZK proofs, NFTs, on-chain.
        #   Do NOT forbid common tools: Redis, PostgreSQL, bcrypt, JWT, Docker, SendGrid
        #   are all legitimate everyday choices and must not be banned.
        #
        # This distinction prevents the forbidden list from becoming so broad that
        # legitimate technology choices are blocked.  SpecExtractor also post-filters
        # the LLM's forbidden list against the goal text to catch cases where the LLM
        # tries to forbid something the user explicitly requested.
        if task == "spec_extract":
            goal = payload.get("goal", "")
            domain_hint = payload.get("domain_hint", "general")
            return (
                f"{frame}"
                "You are a requirements analyst. Extract the following from the goal:\n"
                "\n"
                f"  domain           — classify as ONE of: technical, culinary, fitness, creative,\n"
                f"                     business, academic, general.\n"
                f"                     Pre-detected hint: '{domain_hint}'. Confirm or correct based on goal text.\n"
                "  task_class       — classify as ONE of:\n"
                "                       implement  — build, code, or create an artifact\n"
                "                       coordinate — orchestrate, manage, or plan sub-tasks\n"
                "                       analyze    — audit, review, evaluate, or inspect\n"
                "                       create     — write, design, or generate creative content\n"
                "                       transform  — convert, reformat, or translate existing content\n"
                "                       general    — anything else\n"
                "                     This tells the engine whether meta/validation sub-tasks are appropriate.\n"
                "  concrete_indicators — 3-5 short phrases (lowercase) that signal concrete/actionable\n"
                "                     content in THIS domain. Examples:\n"
                "                       culinary  → [\"ingredient list\", \"cooking temperature\", \"step by step\"]\n"
                "                       fitness   → [\"sets and reps\", \"exercise name\", \"rest period\"]\n"
                "                       technical → [\"function definition\", \"api endpoint\", \"database schema\"]\n"
                "                       creative  → [\"character name\", \"scene description\", \"dialogue\"]\n"
                "                       business  → [\"revenue model\", \"target market\", \"kpi\"]\n"
                "  required         — items that MUST appear in the final output (max 12 short phrases).\n"
                "                     Extract from what the user EXPLICITLY asked for.\n"
                "  forbidden        — items clearly out-of-scope that would be drift from the user's intent\n"
                "                     for THIS domain. Keep short (max 6). Do NOT list universal norms.\n"
                "                     Examples: recipe goal → [\"source code\", \"blockchain\"];\n"
                "                               fitness goal → [\"investment advice\", \"legal counsel\"]\n"
                "  success_criteria — measurable pass/fail checks (max 8).\n"
                "\n"
                f"Goal: {goal}\n"
                "Return ONLY JSON. No markdown.\n"
                f"Schema: {self._schema_for_task('spec_extract')}"
            )

        # SPEC_VALIDATE SPECIAL CASE
        # This prompt is used by SpecValidator as Stage 2 (LLM stage).
        # It is only called when the deterministic Stage 1 found missing items —
        # so the LLM is not wasted on outputs that trivially pass.
        #
        # TWO-FIELD RESPONSE EXPLAINED
        # The response has exactly two actionable fields (plus "passed" as the summary):
        #   passed     — boolean summary: true only if BOTH conditions are met:
        #                  (1) every required item is covered, AND
        #                  (2) no forbidden item appears
        #   missing    — list of required items the LLM judges as NOT covered.
        #                The LLM should be lenient: "authentication" covers "JWT login"
        #                if JWT is clearly implied by context.  Deterministic checks
        #                are strict; the LLM check provides semantic flexibility.
        #   violations — list of forbidden items that appeared in the output.
        #                These are verbatim matches (the deterministic check already
        #                caught them, so this is mostly confirmation).
        #
        # The "deterministic_missing" field passed in the payload tells the LLM which
        # items Stage 1 flagged, so it can focus its analysis rather than re-scanning
        # everything from scratch.
        if task == "spec_validate":
            req  = payload.get("spec_required", [])
            forb = payload.get("spec_forbidden", [])
            out  = payload.get("output", "")
            return (
                f"{frame}"
                "You are a checklist validator. Check the output below against the spec.\n"
                f"Required items (ALL must be present): {req}\n"
                f"Forbidden items (NONE must appear): {forb}\n"
                f"Output to check:\n{out}\n\n"
                "Return {\"passed\": true/false, \"missing\": [...], \"violations\": [...]}.\n"
                "  passed    — true only if every required item is covered AND no forbidden item appears\n"
                "  missing   — list of required items NOT covered\n"
                "  violations — list of forbidden items that DID appear\n"
                "Return ONLY JSON."
            )

        # ── Special-case: coverage_check (referee LLM call) ──
        if task == "coverage_check":
            goal = payload.get("goal", "")
            extract_only = payload.get("extract_only", False)
            if extract_only:
                return (
                    f"{frame}"
                    "You are a requirements analyst for the RAF referee system.\n"
                    f"Goal: {goal}\n"
                    "List the top-level requirements this goal must satisfy (max 12, short phrases).\n"
                    'Return ONLY JSON: {"requirements": ["req1", "req2", ...]}'
                )
            reqs   = payload.get("requirements", [])
            output = payload.get("output_so_far", "")
            return (
                f"{frame}"
                "You are a progress checker for the RAF referee system.\n"
                f"Goal: {goal}\n"
                f"Requirements: {reqs}\n"
                f"Output so far (last 3000 chars):\n{output}\n\n"
                "For each requirement, determine if it is covered by the output.\n"
                'Return ONLY JSON: {"covered": [...], "missing": [...], "progress_score": 0.0-1.0}'
            )

        # ── Special-case: scope_check ──
        if task == "scope_check":
            goal      = payload.get("goal", "")
            output    = payload.get("output", "")
            ancestors = payload.get("ancestors", [])
            anc_str   = " → ".join(str(a)[:80] for a in ancestors[-3:]) if ancestors else "none"
            return (
                f"{frame}"
                f"Root goal chain: {anc_str}\n"
                f"Current goal: {goal}\n"
                f"Output to check:\n{output}\n\n"
                'Return {"on_topic": true/false, "reason": "brief explanation"}.\n'
                "Mark on_topic=false only if the output clearly drifts away from the goal. "
                "If it is a good-faith attempt, return on_topic=true.\n"
                "Return ONLY JSON."
            )

        # ── Task-specific notes ──
        limit_note = ""
        if task == "mode_decision":
            limit_note = (
                "RAF DECOMPOSITION RULES — read before answering:\n"
                "• The RIGHT question is NOT 'can I answer this in one response?' — a language\n"
                "  model can always produce something. Ask instead: 'would separate focused agents\n"
                "  produce meaningfully better output than one agent doing everything at once?'\n"
                "• Choose 'recursive' when the goal has 2+ DISTINCT sections that each need\n"
                "  dedicated depth — e.g. a plan with a budget section, a savings section, and a\n"
                "  tracking section. Each section deserves its own focused agent, not a few lines\n"
                "  inside a one-shot dump.\n"
                "• Choose 'base' only for genuinely atomic tasks: a single lookup, a single\n"
                "  calculation, a single move, a single short creative piece with no sub-parts.\n"
                "• CRITICAL: A one-shot answer to a multi-part goal is almost always shallow.\n"
                "  If the goal lists multiple required deliverables (e.g. 'include X, Y, and Z'),\n"
                "  decompose — each deliverable gets a dedicated child that produces it fully.\n"
                "• Default to 'recursive' for goals with 2+ explicit sections, components,\n"
                "  or required items. Default to 'base' only for single-step atomic tasks.\n"
            )
        if task == "plan":
            limit_note = (
                "PLAN RULES — read before answering:\n"
                "• Max 20 children. Prefer fewer children over more — each extra child costs budget.\n"
                "• Every child must directly produce a required artifact. No 'setup', 'bootstrap',\n"
                "  'validate', 'review', or 'audit' children unless explicitly requested.\n"
                "• Do NOT over-decompose. A task with 3 natural steps should have 3 children, not 6.\n"
                "• SIMPLICITY: reject any child whose goal could be absorbed into a sibling without\n"
                "  quality loss. Prefer 2 focused children over 4 overlapping ones.\n"
                "• Do NOT invent supporting infrastructure children (logging layer, audit pipeline,\n"
                "  lock manager, event sourcing) unless the goal explicitly requires them.\n"
            )
        if task == "analysis":
            limit_note = (
                "ANALYSIS FIELDS:\n"
                "  locally_valid   — true if the output correctly addresses ITS OWN specific sub-goal.\n"
                "  goal_completed  — true if completing this sub-goal means the OVERALL root task is fully done.\n"
                "  approved        — set to (locally_valid AND goal_completed).\n"
                "Example: a child node that correctly moves one disk (locally_valid=true) does NOT\n"
                "complete the full Hanoi puzzle (goal_completed=false) → approved=false.\n"
            )
        if task == "clarify":
            limit_note = "Return ONE most clarifying question. If everything is clear, return an empty list.\n"
        if task in ("base_execute", "merge"):
            # DECISIONS FIELD NOTE
            # The decisions field feeds the SpecLedger.lock() call in _lock_decisions().
            # Only the WINNING agent's decisions are locked — losers' declarations are ignored.
            #
            # WHY CONSISTENT KEYS MATTER FOR THE LEDGER
            # The ledger stores decisions by key.  If one agent writes {"framework": "FastAPI"}
            # and another writes {"web_framework": "FastAPI"}, the ledger sees them as TWO
            # DIFFERENT keys and does not detect the duplication.  Worse, a third agent that
            # writes {"framework": "Django"} would be blocked by the first but not the second,
            # creating an invisible inconsistency.  Using a standardised key set (defined in
            # this note) prevents key variation from breaking ledger consistency checks.
            #
            # The instruction "Only declare what you are actually committing to" is important
            # because every declared decision gets locked permanently for this run.  An agent
            # that writes {"db": "PostgreSQL"} when it's discussing options (not implementing)
            # would incorrectly lock PostgreSQL for all downstream nodes.
            spec_meta = payload.get("_spec", {})
            domain = spec_meta.get("domain", "general") if isinstance(spec_meta, dict) else "general"
            decision_keys = _DOMAIN_DECISION_KEYS.get(domain, _DOMAIN_DECISION_KEYS["general"])
            limit_note += (
                f"DECISIONS field: If you are committing to key design choices, declare them "
                f"in the 'decisions' dict using dot-notation keys (category.subtype format):\n"
                f"  Suggested keys for domain '{domain}': {decision_keys}\n"
                "  Keys MUST use dot-notation: e.g. \"storage.backend\", \"auth.method\", \"output.format\".\n"
                "  Free-form keys (e.g. \"holographic_hashing\", \"my_style\") are IGNORED by the ledger.\n"
                "Use short values (e.g. {\"output.format\":\"markdown\",\"approach.style\":\"incremental\"}).\n"
                "Once locked by the winning agent, these cannot be changed by downstream nodes.\n"
                "Only declare what you are actually committing to — not hypotheticals.\n"
            )

        # ── Scope constraints ──
        scope_note = ""
        if isinstance(payload, dict) and "constraints" in payload:
            constraints = payload.get("constraints", {})
            focus       = constraints.get("focus", "")
            forbidden   = constraints.get("forbidden_topics", [])
            if focus or forbidden:
                scope_note = f"Scope: {focus}"
                if forbidden:
                    scope_note += f" Forbidden: {forbidden}"
                scope_note += "\n"

        # ── Scope retry feedback ──
        scope_feedback = ""
        if isinstance(payload, dict) and payload.get("scope_feedback"):
            scope_feedback = (
                f"IMPORTANT — previous attempt was off-topic: {payload['scope_feedback']}. "
                "Stay tightly focused on the goal.\n"
            )

        # ── Tool results ──
        tool_context = ""
        if isinstance(payload, dict) and payload.get("tool_results"):
            lines = []
            for tr in payload["tool_results"]:
                lines.append(f"Tool: {tr.get('name')} | Result: {str(tr.get('result', ''))[:400]}")
            tool_context = "Tool results available:\n" + "\n".join(lines) + "\n"

        return (
            f"{frame}"
            "You are a JSON-only agent. Return ONLY valid JSON with no markdown.\n"
            f"{system_prompt}"
            f"{persona_prompt}"
            f"{ancestor_prompt}"
            f"Task: {task}\n"
            f"Schema: {schema}\n"
            f"{limit_note}"
            f"{scope_note}"
            f"{scope_feedback}"
            f"{tool_context}"
            f"Payload: {payload_text}\n"
            "Return ONLY JSON."
        )

    def call_raw(self, task: str, payload: Dict[str, Any]) -> str:
        raise NotImplementedError
