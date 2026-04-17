"""
raf.core.spec
=============
Frozen Spec object and SpecLedger for goal integrity enforcement.

WHY THIS MODULE EXISTS
----------------------
Without goal integrity enforcement, LLM agents tend to drift.  A consortium
proposer might add an unsolicited blockchain layer to a plain web-auth request.
A merger might silently drop a required feature because no child happened to
mention it.  By the time the run finishes, the output can look polished but be
wrong relative to what the user actually asked.

This module solves that with three interlocking pieces:

Spec
    A frozen snapshot of what the user ASKED FOR, extracted once from the root
    goal before any node runs.  It has three fields:
    - required   : items that MUST be present in the final output
    - forbidden  : high-drift primitives that must NOT appear unless the user
                   explicitly requested them
    - success_criteria : measurable pass/fail conditions

    The Spec is injected into every agent prompt as read-only context.  No
    agent can claim ignorance of the requirements; they are literally printed
    at the top of every prompt.

SpecLedger
    Accumulates locked key decisions as the run progresses.  The first winning
    agent that declares "db=PostgreSQL" locks that choice.  Every subsequent
    agent that tries to pick MySQL will be rejected by the ledger gate before
    the jury even sees it.  This prevents branch inconsistency — two siblings
    choosing contradictory technology stacks.

    The ledger is thread-safe so parallel child nodes can read/write safely.

SpecExtractor
    Translates the root goal into a Spec via a single LLM call.  Cached so it
    runs exactly once per run even if called from multiple threads.  Degrades
    gracefully if no adapter is available — returns a minimal Spec with the
    root goal as its only requirement.

SpecValidator
    Two-stage validator: a cheap deterministic keyword check runs first.
    Only calls the LLM when the deterministic check detects failures, so clean
    outputs pay zero extra API cost.  Never hard-blocks a run — on any error
    it returns the deterministic result or passes through.

extract_implicit_decisions
    Heuristic scanner for technology signals in output text.  Used ONLY for
    ledger contradiction detection — not for locking new decisions.  Locking
    only happens through explicit ``decisions`` fields returned by agents.

HOW THE REPAIR LOOP FITS IN
----------------------------
After base execution and merge, ``_spec_repair_loop`` in node.py:
  1. Calls ``SpecValidator.validate()`` on the output.
  2. If it passes → done, no extra cost.
  3. If it fails → spawns a targeted "patch" RafNode with the missing items
     listed explicitly, up to ``config.spec_repair_limit`` attempts.

The validator intentionally only runs at depth <= spec_repair_depth_limit
(default 0 = root only) so repair nodes don't recursively spawn more repair
nodes and exhaust the budget.

TWO-STAGE VALIDATOR DESIGN
---------------------------
The deterministic stage does a simple word-split substring match.  For a
required item like "JWT login", it checks whether any significant word in
that phrase ("JWT", "login") appears in the output (case-insensitive).  This
is fast, free, and catches most problems.

The LLM stage only fires when the deterministic check reports missing items.
It asks the LLM whether the items might be covered under a different phrasing
— for example, "authentication" might satisfy "JWT login" if the rest of the
context makes it clear JWT is being used.  The LLM stage provides nuance that
pure substring matching can't.
"""

import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ── domain detection ───────────────────────────────────────────────────────────
# Keyword-based domain classification — fast, deterministic, no LLM.
# Used as a domain_hint for the SpecExtractor LLM call and to gate which
# default forbidden items are relevant to a run.
#
# The first domain whose keywords appear (as substrings, case-insensitive) in
# the goal wins.  If no domain matches, "general" is returned as a safe fallback.
#
# This is a pre-filter only — the LLM has final authority to confirm or override
# the detected domain in the spec_extract call.  Setting config.domain explicitly
# overrides both.
_DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "culinary":  ["recipe", "cook", "meal", "ingredient", "bake", "cuisine", "dish", "food", "menu", "kitchen"],
    "fitness":   ["workout", "gym", "exercise", "fitness", "training", "reps", "sets", "calorie", "diet", "nutrition"],
    "creative":  ["essay", "story", "poem", "novel", "write", "fiction", "screenplay", "script", "blog", "article"],
    "business":  ["business", "revenue", "market", "startup", "roi", "strategy", "investor", "pitch", "sales", "brand"],
    "academic":  ["research", "thesis", "paper", "study", "academic", "hypothesis", "methodology", "survey", "literature"],
    "technical": ["code", "api", "database", "server", "deploy", "software", "backend", "frontend", "app", "program"],
}

# All valid domain values — used for validation after the LLM spec_extract call.
_VALID_DOMAINS: frozenset = frozenset(_DOMAIN_KEYWORDS.keys()) | {"general"}


def _detect_domain_from_goal(goal: str) -> str:
    """Return a domain string based on keyword matching against the root goal.

    Returns one of: "technical", "culinary", "fitness", "creative",
    "business", "academic", "general".

    This is intentionally a fast pre-filter — the LLM SpecExtractor can
    override the result in the spec_extract call.  Zero API cost.
    """
    goal_lower = goal.lower()
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        if any(kw in goal_lower for kw in keywords):
            return domain
    return "general"


# ── high-drift primitives ──────────────────────────────────────────────────────
# "High-drift primitives" means technologies that are virtually never required
# by a vanilla web/backend request, yet LLMs will spontaneously suggest them
# because they appear frequently in training data in "impressive" contexts.
#
# These are NOT unconditionally banned.  They are only placed on the forbidden
# list when:
#   1. The domain is "technical" (non-tech goals never need blockchain/NFT).
#   2. The root goal gives no indication the user wants them.
#
# Common implementation tools — Redis, bcrypt, PostgreSQL, SendGrid, JWT,
# Docker — are deliberately ABSENT from this list.  Those are legitimate
# everyday choices.  This list is specifically for the technology layer that
# almost no one needs unless they explicitly asked.
_DEFAULT_FORBIDDEN = [
    "blockchain", "smart contract", "IPFS", "Chainlink", "zero-knowledge", "ZK proof",
    "DID", "verifiable credential", "on-chain", "NFT", "token gating", "Web3 wallet",
]


def _goal_relevant_forbidden(root_goal: str, domain: str = "general") -> List[str]:
    """Return only the default forbidden items relevant for the detected domain.

    DOMAIN GATE
    -----------
    _DEFAULT_FORBIDDEN contains Web3/blockchain terms — only meaningful drift
    risks for technical software tasks.  For culinary, fitness, creative, or
    other non-tech domains, injecting "forbidden: blockchain, NFT, IPFS" into
    every agent prompt is noise: those terms will never appear in a recipe or
    workout plan, and their presence clutters the Frozen Spec block.

    When domain is not "technical", this function returns an empty list.
    The LLM-identified forbidden items (from SpecExtractor) are still applied;
    only the tech-specific defaults are gated by domain.

    GOAL-TEXT FILTERING (technical domain only)
    -------------------------------------------
    For technical goals the original logic applies: each forbidden term is
    split into words; if any word appears in the goal text the term is removed,
    so "build a blockchain voting system" doesn't forbid blockchain.

    Example
    -------
    Goal: "build a blockchain voting system with NFTs"  domain="technical"
    Term: "blockchain"   → "blockchain" in goal → EXCLUDED
    Term: "NFT"          → "nft" in goal.lower  → EXCLUDED
    Term: "IPFS"         → not in goal          → INCLUDED

    Returns
    -------
    List of forbidden terms that are safe to ban for this particular goal.
    """
    if domain != "technical":
        # Non-tech domains: tech drift terms are irrelevant — return nothing.
        return []
    goal_lower = root_goal.lower()
    relevant = []
    for term in _DEFAULT_FORBIDDEN:
        # Split multi-word terms and check if any significant word appears in goal.
        # We skip words <= 2 chars because they are too common to be reliable.
        words = [w for w in re.split(r"[\s/-]+", term) if len(w) > 2]
        if not any(w.lower() in goal_lower for w in words):
            relevant.append(term)
    return relevant

# ── heuristic signals for implicit decision detection ─────────────────────────
# Each tuple is (compiled_regex, decision_key, detected_value).
#
# These patterns are used ONLY for ledger CONTRADICTION DETECTION — specifically
# to fire a warning when an output's text implies a technology choice that
# contradicts an already-locked decision.
#
# IMPORTANT: These signals NEVER lock new decisions.  Only explicit ``decisions``
# dicts returned by agents (and passed through SpecLedger.lock()) are locked.
# The distinction matters: an output might casually mention "like Redis could work
# here" without actually committing to Redis.  We warn, not lock, on implicit signals.
#
# Pattern notes:
#   - re.I makes all matches case-insensitive.
#   - Express uses (?!ion) to avoid matching "Expression" (common in non-framework
#     contexts such as "regular expression").
#   - Java uses (?!\s*Script) to avoid matching "JavaScript" as Java.
#   - All patterns use \b word boundaries to avoid partial matches (e.g. "FastAPI"
#     must not match inside "FastAPIWrapper").
_IMPLICIT_SIGNALS: List[Tuple[re.Pattern, str, str]] = [
    (re.compile(r"\bFastAPI\b",       re.I), "framework", "FastAPI"),
    (re.compile(r"\bDjango\b",        re.I), "framework", "Django"),
    (re.compile(r"\bExpress\b(?!ion)",re.I), "framework", "Express"),
    (re.compile(r"\bPhoenix\b",       re.I), "framework", "Phoenix"),
    (re.compile(r"\bRails\b",         re.I), "framework", "Rails"),
    (re.compile(r"\bSpring Boot\b",   re.I), "framework", "Spring Boot"),
    (re.compile(r"\bPostgreSQL\b",    re.I), "db", "PostgreSQL"),
    (re.compile(r"\bMySQL\b",         re.I), "db", "MySQL"),
    (re.compile(r"\bMongoDB\b",       re.I), "db", "MongoDB"),
    (re.compile(r"\bSQLite\b",        re.I), "db", "SQLite"),
    (re.compile(r"\bRedis\b",         re.I), "cache", "Redis"),
    (re.compile(r"\bMemcached\b",     re.I), "cache", "Memcached"),
    (re.compile(r"\bCognito\b",       re.I), "auth", "AWS Cognito"),
    (re.compile(r"\bAuth0\b",         re.I), "auth", "Auth0"),
    (re.compile(r"\bSupabase\b",      re.I), "auth", "Supabase"),
    (re.compile(r"\bFirebase\b",      re.I), "auth", "Firebase"),
    (re.compile(r"\bJWT\b",           re.I), "token_model", "JWT"),
    (re.compile(r"\bsession.?based\b",re.I), "token_model", "sessions"),
    (re.compile(r"\bElixir\b",        re.I), "backend_language", "Elixir"),
    (re.compile(r"\bRust\b",          re.I), "backend_language", "Rust"),
    (re.compile(r"\bGo(?:lang)?\b",   re.I), "backend_language", "Go"),
    (re.compile(r"\bNode\.?js\b",     re.I), "backend_language", "Node.js"),
    (re.compile(r"\bPython\b",        re.I), "backend_language", "Python"),
    (re.compile(r"\bJava\b(?!\s*Script)", re.I), "backend_language", "Java"),
]


# ── spec dataclass ─────────────────────────────────────────────────────────────

@dataclass
class Spec:
    """Immutable snapshot of the run's requirements.  Set once at run start.

    The Spec is extracted from the root goal by SpecExtractor before any node
    executes.  It is then attached to the RafEngine and injected into every
    agent prompt via _spec_context() so all agents share the same ground truth
    about what the user asked for.

    Attributes
    ----------
    required:
        Items that MUST be present in the final output.  Extracted from the
        user's goal — e.g. "JWT login", "password reset flow", "rate limiting".
        The SpecValidator checks these after base execution and merge; the
        repair loop patches any that are missing.

    forbidden:
        High-drift primitives that must NOT appear unless the user asked.
        Default: blockchain, ZK proofs, IPFS, Chainlink, NFTs, etc.
        Common implementation details (Redis, bcrypt, SendGrid) are NOT
        forbidden — only technology that almost no normal request needs.

    success_criteria:
        Measurable pass/fail conditions extracted from the goal, e.g.
        "each endpoint documented with HTTP method, path, and schema",
        "all error codes have example responses".  These appear in the
        Frozen Spec block of every agent prompt as explicit acceptance tests.
    """

    required: List[str] = field(default_factory=list)
    forbidden: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)
    domain: str = "general"
    """Domain of the root goal — one of technical/culinary/fitness/creative/business/academic/general."""
    concrete_indicators: List[str] = field(default_factory=list)
    """Domain-specific phrases that signal concrete/actionable content in this goal's domain.
    Extracted by the SpecExtractor LLM call and used by the quality gate in node.py."""
    task_class: str = "general"
    """High-level class of the root task.  One of:
      implement  — build or code something (validator children are meta-noise)
      coordinate — orchestrate or manage sub-tasks (validator children are legitimate)
      analyze    — audit, review, or evaluate (validator children are legitimate)
      create     — creative/generative output (validator children are meta-noise)
      transform  — convert or reformat content (validator children are meta-noise)
      general    — catch-all (validator children filtered conservatively)
    The validator child filter (_VALIDATOR_CHILD_RE) is bypassed entirely for
    'coordinate' and 'analyze' classes so legitimate review/audit children survive."""


# ── spec ledger ────────────────────────────────────────────────────────────────

class SpecLedger:
    """Thread-safe store of locked key decisions.

    WHAT IT SOLVES
    --------------
    When parallel child nodes execute independently, each might commit to a
    different technology stack.  Node A might say "use PostgreSQL" while Node B
    says "use MongoDB".  The merged output then reads like two different systems
    were designed by two different developers — because they were.

    The SpecLedger prevents this.  The first winning agent to declare a decision
    locks it.  Subsequent nodes that try to declare a different value for the
    same key are filtered out by _ledger_gate() before the jury even votes on
    them.  First-write-wins semantics enforce consistency across the entire tree.

    FIRST-WRITE-WINS
    ----------------
    This is a deliberate design choice, not an arbitrary default.  The first
    node to commit to a technology choice has already been through Consortium
    proposal + Jury voting — it represents the system's best estimate at that
    point.  Overriding it later would mean the downstream node's single opinion
    beats the earlier multi-agent consensus, which is almost never right.

    Typical keys: "framework", "backend_language", "auth", "token_model",
    "db", "cache", "email_provider".  Keys are short, consistent strings
    defined in the DECISIONS field guidance in prompt_adapter.py.
    """

    def __init__(self) -> None:
        self._locked: Dict[str, str] = {}
        # A single lock protects both reads and writes so no thread sees a
        # partially updated dict during a multi-key lock() call.
        self._lock = threading.Lock()

    def lock(self, decisions: Dict[str, str]) -> None:
        """Lock key=value pairs.  First write per key wins; later writes ignored.

        The first-write-wins rule is enforced by checking ``k not in self._locked``
        before inserting.  Keys or values that are falsy (empty string, None) are
        skipped — agents sometimes return partial decision dicts.

        Parameters
        ----------
        decisions:
            Dict of key → value to attempt to lock.  Any key already in the
            ledger is silently skipped; the existing value is kept unchanged.
        """
        with self._lock:
            for k, v in decisions.items():
                # Skip empty keys/values — the agent returned an incomplete dict.
                # Skip already-locked keys — first writer keeps their value.
                if k and v and k not in self._locked:
                    self._locked[k] = str(v)

    def locked(self) -> Dict[str, str]:
        """Return a snapshot of all currently locked decisions.

        Returns a copy so callers cannot accidentally mutate the internal state.
        """
        with self._lock:
            return dict(self._locked)

    def check_compatible(
        self, proposal_decisions: Dict[str, str]
    ) -> Tuple[bool, str]:
        """Check whether a proposal's decisions contradict any locked entry.

        WHAT A CONTRADICTION LOOKS LIKE
        --------------------------------
        If the ledger has {"db": "PostgreSQL"} and a proposal says
        {"db": "MongoDB"}, that is a contradiction.  The proposal would lock in
        a different value for a key that was already committed.

        Keys in the proposal that are NOT yet in the ledger are fine — they
        don't contradict anything.  The check only fails on key collisions
        where the values differ.

        Returns
        -------
        (True, "")
            Proposal is compatible with all locked decisions.
        (False, description)
            Proposal contradicts at least one locked decision.
            ``description`` names the key and both conflicting values so the
            trace log gives the developer a useful diagnostic message.
        """
        with self._lock:
            for k, proposed_v in proposal_decisions.items():
                if k in self._locked and self._locked[k] != str(proposed_v):
                    return (
                        False,
                        f"{k}: locked='{self._locked[k]}', proposed='{proposed_v}'",
                    )
        return True, ""


# ── implicit decision extraction ───────────────────────────────────────────────

def extract_implicit_decisions(output: str) -> Dict[str, str]:
    """Scan output text for implicit technology decisions using heuristics.

    Returns a dict of ``{decision_key: detected_value}`` for any signals found.

    Used ONLY for ledger contradiction detection — not for locking new
    decisions.  When this function returns {"framework": "Django"} but the
    ledger has {"framework": "FastAPI"}, _lock_decisions() emits an
    ``implicit_decision_conflict`` trace event so the developer can see the
    inconsistency.

    If multiple signals fire for the same key (e.g. output mentions both
    Redis and Memcached), the first match wins — consistent with how the
    ledger itself works.

    Parameters
    ----------
    output:
        Raw text output from any node.  Scanned in order of _IMPLICIT_SIGNALS.
    """
    found: Dict[str, str] = {}
    for pattern, key, value in _IMPLICIT_SIGNALS:
        # Skip if we already have a value for this key — first match wins.
        if key not in found and pattern.search(output):
            found[key] = value
    return found


# ── spec extractor ─────────────────────────────────────────────────────────────

class SpecExtractor:
    """Extracts a Spec from the root goal via a single cached LLM call.

    Parameters
    ----------
    root_goal:
        The top-level goal string for this run.
    adapter:
        A ModelAdapter used for the extraction call.  When None the extractor
        degrades to a minimal Spec containing only the root goal as a requirement,
        which is safe — it means the validator can only do a trivial length
        check, but the run can still proceed.
    """

    def __init__(self, root_goal: str, adapter=None) -> None:
        self.root_goal = root_goal
        self.adapter = adapter
        self._spec: Optional[Spec] = None
        self._lock = threading.Lock()
        # _fetched is set to True before the LLM call begins.  This ensures
        # that if two threads race to call extract() simultaneously, only one
        # issues the LLM request — the other returns whatever _spec ends up as.
        self._fetched = False

    def extract(self) -> Spec:
        """Extract and return the Spec.  Thread-safe; LLM called at most once.

        THREADING GUARD
        ---------------
        The _fetched flag is set inside the lock BEFORE the LLM call starts.
        This prevents a second thread from issuing a duplicate LLM call while
        the first thread is still waiting for a response.  The second thread
        exits the lock immediately and re-enters it after the first finishes
        to read the shared _spec.

        This is an optimistic single-call pattern: we accept that _spec may be
        None briefly (if the second thread reads before the first finishes), but
        in practice the calling code at RafEngine.run() extracts synchronously
        before any child threads are spawned, so this race never occurs in the
        current design.

        FALLBACK CHAIN
        --------------
        1. No adapter                    → Spec(required=[root_goal[:120]])
        2. Adapter call fails / bad JSON → Spec(required=[root_goal[:120]])
        3. LLM returns empty required    → Spec(required=[root_goal[:120]])
        4. LLM returns valid required    → full Spec with merged forbidden list

        The fallback ensures the run always proceeds even if the extractor
        hits an API error or parse failure.
        """
        with self._lock:
            if self._fetched:
                # Already fetched (or in progress) — return whatever we have.
                return self._spec  # type: ignore[return-value]
            # Mark as fetched before releasing the lock so no other thread
            # enters the LLM call path.
            self._fetched = True

        # Pre-detect domain from goal keywords (fast, no LLM).
        # Used as domain_hint in the LLM call and as fallback if LLM fails.
        pre_domain = _detect_domain_from_goal(self.root_goal)

        if not self.adapter:
            # No adapter available — degrade to the minimal Spec.
            goal_defaults = _goal_relevant_forbidden(self.root_goal, domain=pre_domain)
            spec = Spec(required=[self.root_goal[:120]], forbidden=goal_defaults, domain=pre_domain)
        else:
            try:
                from raf.llm.json_utils import call_json_with_repair

                def _validator(x: Dict[str, Any]) -> Dict[str, Any]:
                    # Minimal structural check: we need at least a list of required items.
                    if not isinstance(x.get("required"), list):
                        raise ValueError("missing 'required' list")
                    return x

                result = call_json_with_repair(
                    self.adapter,
                    "spec_extract",
                    {
                        "goal": self.root_goal,
                        # domain_hint helps the LLM classify quickly; it can confirm or override.
                        "domain_hint": pre_domain,
                        # _raf_role tells the prompt builder this is a spec extractor call,
                        # not a consortium or jury call — different framing in _build_frame.
                        "_raf_role": "spec_extractor",
                    },
                    _validator,
                    1,  # single retry — extraction is not worth many attempts
                )
                # Extract domain from LLM result; fall back to pre_domain if invalid.
                domain = result.get("domain", pre_domain)
                if domain not in _VALID_DOMAINS:
                    domain = pre_domain
                # Extract concrete_indicators (goal-specific concreteness signals).
                concrete_indicators = [
                    str(c) for c in result.get("concrete_indicators", []) if c
                ][:8]
                # Extract task_class; fall back to "general" if invalid.
                _VALID_TASK_CLASSES = frozenset({"implement", "coordinate", "analyze", "create", "transform", "general"})
                task_class = str(result.get("task_class", "general"))
                if task_class not in _VALID_TASK_CLASSES:
                    task_class = "general"
                # Compute goal_defaults using the FINAL domain so tech-only terms
                # are not injected into non-tech runs.
                goal_defaults = _goal_relevant_forbidden(self.root_goal, domain=domain)
                # Merge goal-filtered defaults with any additional LLM-identified items.
                # LLM items are also filtered: skip any whose words appear in the goal,
                # because the LLM may over-aggressively forbid things the user wants.
                llm_forbidden = [
                    str(f) for f in result.get("forbidden", []) if f
                    and not any(
                        w.lower() in self.root_goal.lower()
                        for w in re.split(r"[\s/-]+", str(f))
                        if len(w) > 2
                    )
                ]
                # dict.fromkeys preserves insertion order and deduplicates.
                # goal_defaults come first so they take priority in display order.
                merged_forbidden = list(dict.fromkeys([*goal_defaults, *llm_forbidden]))
                spec = Spec(
                    # Cap at 15 items — longer lists make prompts unreadable.
                    required=[str(r) for r in result.get("required", []) if r][:15],
                    forbidden=merged_forbidden[:15],
                    success_criteria=[
                        str(s) for s in result.get("success_criteria", []) if s
                    ][:10],
                    domain=domain,
                    concrete_indicators=concrete_indicators,
                    task_class=task_class,
                )
                if not spec.required:
                    # LLM returned an empty required list — fall back to the goal itself.
                    goal_defaults = _goal_relevant_forbidden(self.root_goal, domain=pre_domain)
                    spec = Spec(required=[self.root_goal[:120]], forbidden=goal_defaults, domain=pre_domain)
            except Exception:
                # Any error (network, parse, schema) → minimal safe fallback.
                goal_defaults = _goal_relevant_forbidden(self.root_goal, domain=pre_domain)
                spec = Spec(required=[self.root_goal[:120]], forbidden=goal_defaults, domain=pre_domain)

        # Store under lock so any thread that reads _spec after this point gets
        # a fully constructed Spec object.
        with self._lock:
            self._spec = spec
        return spec


# ── spec validator ─────────────────────────────────────────────────────────────

###############################################################################
# Domain-aware concreteness check — replaces the old _CONCRETE_ELEMENT_RE    #
###############################################################################
# The quality gate in node.py rejects short outputs (< 800 chars) that       #
# contain no "concrete element".  The old approach used a single tech-centric #
# regex (_CONCRETE_ELEMENT_RE) that checked for REST paths, SQL, code blocks, #
# etc. — useless for a recipe or fitness plan.                                #
#                                                                             #
# The new approach:                                                           #
#   1. Use LLM-extracted concrete_indicators from the Spec (goal-specific).  #
#   2. Fall back to _DOMAIN_CONCRETE[spec.domain] built-in patterns.         #
#   3. Always include _DOMAIN_CONCRETE["general"] as a universal safety net.  #
###############################################################################

_DOMAIN_CONCRETE: Dict[str, List[str]] = {
    "technical": [
        r"/api/", r"\bPOST\b", r"\bGET\b", r"\bPUT\b", r"\bDELETE\b",
        r"\bendpoint\b", r"\broute\b", r"\btable\b", r"\bschema\b",
        r"```", r"\{[^}]{10,}\}",
        r"\b[A-Z][a-z]+Controller\b", r"\b[A-Z][a-z]+Service\b",
        r"\bSELECT\b", r"\bINSERT\b", r"\bCREATE TABLE\b",
        r"\bfunction\b", r"\bclass\b", r"\basync\b", r"\bawait\b",
        r"\balgorithm\b",
    ],
    "culinary": [
        r"\bingredient", r"\bstep\b", r"\bminute[s]?\b", r"\bcup[s]?\b",
        r"\btbsp\b", r"\btsp\b", r"\boven\b", r"\bserv", r"\bcalorie",
        r"\brecipe\b", r"\bcook\b", r"\bbake\b", r"\bpreheat\b",
    ],
    "fitness": [
        r"\bset[s]?\b", r"\brep[s]?\b", r"\bcalorie",
        r"\bexercise\b", r"\bday\s+\d", r"\bweek\b", r"\brest\b",
        r"\bworkout\b", r"\bminute[s]?\b", r"\bpound[s]?\b", r"\bkg\b",
    ],
    "creative": [
        r"\bchapter\b", r"\bcharacter\b", r"\bscene\b",
        r"\bdialogue\b", r"\bplot\b", r"\bverse\b", r"\bstanza\b",
        r"\bparagraph\b", r"\bsection\b", r"\bact\b",
    ],
    "business": [
        r"\bROI\b", r"\brevenue\b", r"\bmarket\b",
        r"\bstrategy\b", r"\bcost\b", r"\bKPI\b", r"\bQ[1-4]\b",
        r"\bcustomer\b", r"\bproduct\b", r"\bcompetitor\b",
    ],
    "academic": [
        r"\bstudy\b", r"\bresearch\b", r"\bfinding\b",
        r"\bmethodology\b", r"\bhypothesis\b", r"\bcitation\b",
        r"\bdata\b", r"\banalysis\b", r"\bresult\b",
    ],
    "general": [
        r"\bstep\s+\d+\b",
        r"\b\d+\s*[%$€£]\b",
        r"\bfor\s+example\b", r"\bnamely\b", r"\bincluding\b",
        r"\bfirst\b", r"\bsecond\b", r"\bthird\b",
        r"\b\d+\s*(?:hours?|days?|weeks?|months?)\b",
    ],
}


def _is_concrete_output(output: str, spec: "Spec") -> bool:
    """Return True if output contains domain-appropriate concrete elements.

    Used by the quality gate in node.py (_quality_gate, Signal 3) to reject
    vague placeholder outputs shorter than 800 characters.

    PRIORITY ORDER
    --------------
    1. LLM-extracted concrete_indicators from Spec (goal-specific phrases).
    2. Built-in patterns for spec.domain from _DOMAIN_CONCRETE.
    3. Universal fallback patterns from _DOMAIN_CONCRETE["general"].

    A single match is sufficient — the gate checks for the PRESENCE of any
    concrete element, not all of them.

    Returns True (passes gate) when no patterns are defined — defensive only,
    should not happen in practice.

    Parameters
    ----------
    output:
        Candidate output text to check.
    spec:
        The run's Spec object (provides domain and concrete_indicators).
    """
    patterns: List[str] = []
    # 1. Custom indicators from LLM spec extraction (goal-specific)
    for ind in spec.concrete_indicators:
        escaped = re.escape(ind.strip().lower())
        if escaped:
            patterns.append(r"\b" + escaped + r"\b")
    # 2. Domain-specific built-in patterns
    patterns.extend(_DOMAIN_CONCRETE.get(spec.domain, []))
    # 3. Universal fallback (always included)
    patterns.extend(_DOMAIN_CONCRETE["general"])
    if not patterns:
        return True  # Safety net — never gate when no patterns available
    combined = re.compile("|".join(patterns), re.I)
    return bool(combined.search(output))


class SpecValidator:
    """Two-stage validator: deterministic check first, then LLM for nuance.

    WHY TWO STAGES
    ---------------
    A pure LLM validator would cost an extra API call for every node that
    completes.  For a 20-node run with 3 jury members, that is 20 extra calls
    on top of the ~120 already happening.  The deterministic stage eliminates
    this cost for outputs that trivially pass: if every required word is found
    and no forbidden term appears, the LLM never fires.

    The LLM stage exists because the deterministic stage has false negatives.
    "JWT authentication" covers the required item "JWT login" in spirit, but
    the word "login" does not appear literally, so the deterministic check
    marks it missing.  The LLM stage can recognize this coverage and correct
    the deterministic result.

    Stage 1 (deterministic, free):
        For each required item, splits the item into significant words (length
        > 3) and checks whether ANY of those words appear in the output
        (case-insensitive).  This is intentionally lenient: if any word from
        "JWT login" appears in the output, the item is considered covered.
        Checks forbidden items with a simple ``str in str`` test.
        Returns immediately on pass so Stage 2 never runs.

    Stage 2 (LLM, only when deterministic check fails):
        Calls the LLM to do nuanced coverage analysis.  Used when the
        deterministic check flags missing items that might actually be covered
        under a different phrasing.  The LLM is given only the last 4000
        characters of output so token cost stays bounded.

    Never hard-blocks — returns (True, [], []) on any LLM or parse error.
    This is intentional: a validator that can hard-block a run is dangerous.
    The repair loop is the corrective mechanism, not this validator.

    Parameters
    ----------
    adapter:
        A ModelAdapter for the LLM stage.  When None only the deterministic
        stage runs.
    """

    def __init__(self, adapter=None) -> None:
        self.adapter = adapter

    def _deterministic_check(
        self, spec: Spec, output: str
    ) -> Tuple[bool, List[str], List[str]]:
        """Cheap substring-based pre-check.  Case-insensitive.

        HOW THE WORD-SPLIT MATCHING WORKS
        -----------------------------------
        For each required item (e.g. "JWT login flow"):
          1. Split on whitespace and slashes: ["JWT", "login", "flow"]
          2. Keep only words longer than 3 chars: ["login", "flow"]
             (short words like "JWT" are kept only if longer than 3 — "JWT"
             is 3 chars so it's dropped in this example; but "login" at 5
             chars and "flow" at 4 chars are kept)
          3. Check whether ANY of the kept words appear in the lowercased output.

        This is a deliberately lenient test: one matching word from the phrase
        is enough to consider the item covered at Stage 1.  The LLM Stage 2 is
        the precise check; Stage 1 is just a fast pre-filter to skip the LLM
        when everything clearly passes.

        Forbidden items use a simpler test: the entire forbidden term (lowercased)
        must not appear anywhere in the output.  This is stricter because we
        want to catch even partial mentions of forbidden technologies.

        Returns
        -------
        (passed, missing, violations)
            passed     — True when no missing items and no violations.
            missing    — Required items where no significant word was found.
            violations — Forbidden terms that appeared verbatim in the output.
        """
        output_lower = output.lower()
        missing = [
            r for r in spec.required
            if not any(
                word.lower() in output_lower
                for word in re.split(r"[\s/,]+", r)
                if len(word) > 3  # skip short words — too common to be meaningful
            )
        ]
        violations = [
            f for f in spec.forbidden
            if f.lower() in output_lower
        ]
        passed = not missing and not violations
        return passed, missing, violations

    def validate(
        self, spec: Spec, output: str
    ) -> Tuple[bool, List[str], List[str]]:
        """Validate output against Spec.  Runs deterministic check first.

        STAGE SELECTION LOGIC
        ---------------------
        Stage 1 runs unconditionally and returns immediately if it passes.
        Stage 2 only fires when Stage 1 finds problems AND an adapter is available.
        If Stage 2 itself fails (API error, parse error), falls back to the Stage 1
        result rather than passing blindly — we trust the deterministic check more
        than a broken LLM call.

        The output is truncated to the last 4000 characters for the LLM call.
        We use the LAST 4000 chars rather than the first because conclusions and
        summaries tend to appear at the end, and missing items are more likely
        to be detected there.

        Returns
        -------
        (passed, missing, violations)
            passed     — True when all required items are covered and no
                         forbidden item is present.
            missing    — Required items not found (empty if passed).
            violations — Forbidden items that appeared (empty if passed).
        """
        if not spec.required:
            # Nothing required → trivially passes.
            return True, [], []

        # Stage 1: deterministic — free and fast
        passed, det_missing, det_violations = self._deterministic_check(spec, output)
        if passed:
            # All required items found, no forbidden terms → skip LLM entirely.
            return True, [], []

        # Stage 2: LLM — only fires when Stage 1 found issues and adapter is available
        if not self.adapter:
            # No adapter → return Stage 1 result as-is.
            return False, det_missing, det_violations

        try:
            from raf.llm.json_utils import call_json_with_repair

            def _validator(x: Dict[str, Any]) -> Dict[str, Any]:
                if not isinstance(x.get("passed"), bool):
                    raise ValueError("missing 'passed' bool")
                return x

            result = call_json_with_repair(
                self.adapter,
                "spec_validate",
                {
                    "spec_required": spec.required,
                    "spec_forbidden": spec.forbidden,
                    # Pass Stage 1's missing list so the LLM knows which items
                    # to focus its nuanced analysis on — saves tokens.
                    "deterministic_missing": det_missing,
                    # Last 4000 chars — conclusions and summaries are at the end.
                    "output": output[-4000:],
                    "_raf_role": "spec_validator",
                },
                _validator,
                1,  # single retry — validation is not worth many attempts
            )
            passed = bool(result.get("passed", True))
            missing = [str(m) for m in result.get("missing", []) if m]
            violations = [str(v) for v in result.get("violations", []) if v]
            return passed, missing, violations
        except Exception:
            # LLM call failed — fall back to Stage 1 result rather than passing
            # blindly.  The repair loop will handle any remaining gaps.
            return False, det_missing, det_violations
