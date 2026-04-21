# RAF Architecture: How Everything Works

> A complete explanation of the Recursive Agent Framework — voting, proposal selection, information flow, prompt construction, model routing, and every component in detail.

---

## The Core Idea in One Paragraph

RAF treats complex tasks the same way a well-run organization treats a hard problem: break it into pieces, have multiple independent experts each propose a solution to their piece, have another group of experts vote on which proposal is best, and then repeat that process for every sub-piece all the way down. The result is a tree of decisions where no single model made all the calls — every significant choice was proposed by multiple agents and validated by a separate voting group. This makes the final output much harder to fool and much easier to audit.

---

## The Two Core Operations

### 1. Consortium — "Propose"

A **Consortium** is a group of LLM agents that each receive the same task independently and produce their own candidate solution. They run in parallel in separate threads. They do not see each other's output.

Each agent in the consortium receives:
- The goal for this node
- The Spec (extracted requirements — explained below)
- The SpecLedger (locked decisions from earlier in the run)
- Its own index (`_agent_index`) so the adapter can vary its temperature

The index matters: agent-0 runs at the base temperature (e.g. 0.2), agent-1 at +0.1, agent-2 at +0.2. This temperature ladder pushes consortium agents toward genuinely different proposals rather than converging on the same answer.

The output is a list of **candidate proposals**, one per agent. If any agent fails or times out, the others still contribute. Only a total failure (every agent fails) raises an error.

**Unanimity shortcut:** Before sending proposals to the jury, the system checks whether all consortium agents agreed on a key field (e.g. all said `mode: "base"`). If unanimous, the jury is skipped entirely and that answer is accepted with a scaled confidence score. This saves `jury_size` LLM calls when the answer is obvious.

### 2. Jury — "Vote"

A **Jury** is a separate group of LLM agents that receive all the consortium proposals and vote on which is best. Each juror:
- Sees all labeled proposals (Option 1, Option 2, Option 3...)
- Assigns a `winner_id` (which option they think won)
- Reports a `confidence` score (0.0–1.0)
- Ranks all options by score with a brief reason

**Confidence-weighted aggregation:** Votes are not simply counted. Each juror's reported confidence is added to a running total for their chosen winner. The option with the highest total weighted confidence wins. This means a highly-confident minority can outweigh a low-confidence majority — which is usually the right call.

The jury runs in parallel in separate threads, just like the consortium.

---

## The Six Decision Points

RAF applies the Consortium → Jury pattern at every major decision in the run. The six decision points are:

| # | Decision | Task name | What's being decided |
|---|---|---|---|
| 1 | **Mode** | `mode_decision` | Should this goal be solved directly (base) or broken into sub-goals (recursive)? |
| 2 | **Plan** | `plan` | If recursive: what are the child sub-goals, and what are their dependencies? |
| 3 | **Child refinement** | `refine_context` | For each planned child: clarify its exact goal, success criteria, and what it must return |
| 4 | **Base execution** | `base_execute` | If base: what is the actual output/answer for this goal? |
| 5 | **Merge** | `merge` | After children finish: synthesize all child outputs into one coherent result |
| 6 | **Analysis** | `analysis` | Is this node's output good enough? Are required items present? Is the goal completed? |

Two additional operations use a **single adapter** (not Consortium → Jury), because they are procedure-following rather than judgment calls:
- **Clarify** — if the root goal is ambiguous, ask one clarifying question
- **Scope check** — verify the proposed plan doesn't drift outside the original goal

---

## The Recursive Tree

When mode is `recursive`, the node creates child nodes and waits for them. Here is the exact sequence:

```
RafNode.run()
  ├── Spec extraction (root only, once per run)
  ├── Maybe clarify (single-agent, root only)
  ├── Scope check (single-agent, optional)
  ├── _decide_mode()  ← Consortium + Jury (decision point 1)
  │     ↓ mode = "base"
  ├── _execute_base() ← Consortium + Jury (decision point 4)
  │     → _spec_repair_loop() (if output is missing required items)
  │     → _analyze()  ← Consortium + Jury (decision point 6)
  │
  │     ↓ mode = "recursive"
  ├── _plan_children()      ← Consortium + Jury (decision point 2)
  ├── _refine_children()    ← Consortium + Jury per child (decision point 3)
  ├── Run all children in parallel (each child is a full RafNode.run())
  ├── _execute_recursive()  ← Consortium + Jury (decision point 5, the merge)
  │     → _spec_repair_loop() (if merged output is missing required items)
  └── _analyze()            ← Consortium + Jury (decision point 6)
```

Children with no dependencies start immediately. Children that depend on sibling outputs wait until those siblings complete. This is enforced by a topological sort at planning time.

---

## Information Flow: What Each Agent Sees

Every agent prompt is assembled from multiple information sources that are injected as structured blocks. Here is what each agent sees and where it comes from:

### The Goal

The node's specific goal string. For root nodes this is the user's original input. For child nodes this is the refined sub-goal produced in step 3 (child refinement).

### The Spec

Extracted **once** at the root node before any execution begins. Contains:
- `required` — items that must appear in the final output
- `forbidden` — things explicitly out of scope for this run
- `success_criteria` — measurable pass/fail conditions
- `domain` — auto-detected or user-set: `technical` / `culinary` / `fitness` / `creative` / `business` / `academic` / `general`
- `concrete_indicators` — goal-specific phrases that signal real output vs. vague restatements
- `task_class` — `implement` / `coordinate` / `analyze` / `create` / `transform` / `general`

The Spec is injected into **every agent prompt for the entire run**, from root to deepest leaf. No agent can claim ignorance of the requirements.

### The SpecLedger

A thread-safe store of **locked key decisions** — values that have been committed by an earlier agent and cannot be contradicted. Examples: `lang.backend = Python`, `cuisine.style = French`, `training.style = HIIT`.

First-write-wins: the first agent to commit a value for a key locks it for all subsequent agents. Agents are told about locked decisions explicitly in their prompt and told not to contradict them. If a proposal contradicts a locked decision, it is filtered out before the jury votes.

### Ancestor Context

A sliding window of the last 5 ancestor node goals, provided so the agent understands where it sits in the decomposition tree without seeing the entire tree.

### Dependency Context

For child nodes that depend on sibling outputs, the outputs of those completed siblings are included (capped at 800 characters per dependency to avoid token blowout). This is how a child that writes "chapter 2" knows what "chapter 1" already said.

### System Prompt

An optional user-supplied instruction injected into every agent prompt, for domain or persona framing.

---

## Prompt Construction

RAF uses a shared `PromptBasedAdapter` base class that all adapters inherit from. The prompt is built in `_build_prompt(task, payload)`.

The payload dict carries all information fields plus "meta-keys" prefixed with `_` (like `_raf_role`, `_agent_index`, `_spec`) which are stripped before serialization into the prompt text.

The prompt has three sections:

### 1. Role block
```
You are a [ROLE] agent in the RAF (Recursive Agent Framework).
Your _raf_role is [consortium|jury|...].
You are agent [N] of [TOTAL] in this group.
```

The role tells the agent what it's supposed to do: generate a diverse proposal (consortium) or judge between proposals (jury).

### 2. Frozen Spec block
```
═══ FROZEN SPEC (do not contradict) ═══
Domain: technical
Task class: implement
Required: [item1, item2, item3]
Forbidden: [...]
Success criteria: [...]
Concrete indicators: [...]
```

### 3. Locked Decisions block (if any decisions are locked)
```
═══ LOCKED DECISIONS (do not contradict) ═══
lang.backend = Python   [locked at node-abc]
db.engine = PostgreSQL  [locked at node-def]
```

### 4. Task payload
The serialized task-specific fields (goal, depth, constraints, etc.) plus the JSON schema the agent must return.

### 5. JSON schema
Every task has an explicit output schema in the prompt. Agents are told exactly what fields to return and in what shape. If they return malformed JSON, a repair loop calls them again with their bad output shown and asks them to fix it.

---

## Jury Scoring Rubric

Jury agents are not just asked "which is best" — they are given a structured scoring rubric:

1. **Eligibility gate (hard):** If a proposal is missing a Required item or contains a Forbidden item → score 0, ineligible regardless of other qualities
2. **Spec coverage:** Does the proposal address all required items substantively?
3. **Ledger consistency:** Does it respect all locked decisions?
4. **Simplicity:** Is it the simplest valid answer? Unsolicited features or invented infrastructure are penalized.
5. **Domain quality:** Is it appropriate and correct for the detected domain?
6. **Clarity:** Is the output understandable and well-formed?
7. **Novelty (tie-breaker only):** Among tied proposals, prefer the one with the most useful additional insight.

This scoring order means the jury will never pick a proposal that violates requirements, even if it's otherwise impressive.

---

## The Spec Repair Loop

After base execution and after merge, before the analysis phase, RAF runs a validation check:

1. **Stage 1 — Deterministic word-split match:** Does the output contain substrings matching each required item? Fast, free, always runs.
2. **Stage 2 — LLM coverage check:** Only fires if Stage 1 fails. Asks a model to check nuanced semantic coverage of requirements.

If requirements are missing, a targeted **repair node** is spawned — a new child RafNode with a `PATCH` goal that lists exactly what's missing and what decisions are locked. The repair node runs the full Consortium → Jury pipeline. Up to `spec_repair_limit` repair attempts (default 2). The system never hard-blocks on repair failure — if repair fails, the original output is still returned.

---

## The Trace System

Every significant event in a run emits a structured JSON event via `TraceLogger`. Events are:
- Stored in an in-memory list (capped at 2000 per run)
- Pushed to a live queue drained by the WebSocket
- Streamed to the frontend in real time

Key event types:

| Event | What it means |
|---|---|
| `run_started` | Engine started, config snapshot included |
| `spec_extracted` | Spec extracted from root goal |
| `node_created` | A new RafNode was created |
| `mode_decided` | base vs recursive decision made |
| `consortium_candidates` | All proposals from a Consortium call |
| `jury_votes` | All votes from a Jury call, with winner |
| `model_call_start/done/failed/timeout` | Individual LLM call lifecycle |
| `model_call_fallback` | Fallback adapter used when all primaries timed out |
| `node_done` | Node completed with output, confidence, mode |
| `run_done` | Full run complete, final result included |

Every `model_call_*` event carries `provider`, `model`, `role`, `agent_index`, and `duration_ms` — so you always know exactly which model made which call and how long it took.

---

## Model Routing: Choosing the Right Model for the Right Role

This is the most impactful configuration decision in RAF. The key insight: **consortium agents and jury agents have fundamentally different jobs**, so the ideal model for each is different.

### Consortium agents — Propose

**What they need:** Speed, diversity, independence.

Consortium agents each produce a complete proposal independently. You want them to disagree with each other — that's the whole point of having multiple. A fast model that generates a solid answer in 2 seconds is better here than a slow model that generates a perfect answer in 15 seconds, because:
- The jury only runs on the outputs that arrive, not ideal outputs
- Fast models allow more parallel diversity in the same wall-clock time
- A slightly weaker model's proposal that captures a different angle often beats a perfect model's 3rd answer

**Good consortium choices:** Fast free-tier models, small reasoning models, domain-specific models.

Examples from the catalog:
- `google/gemma-4-26b-a4b-it:free` — free, fast, good general reasoning
- `stepfun/step-3.5-flash:free` — free, reasoning enabled, fast
- `qwen/qwen3.5-9b` — small and fast, good diversity
- `mistralai/devstral-2512` — coding-focused, good for technical tasks
- `liquid/lfm-2.5-1.2b-thinking:free` — tiny, extremely fast

### Jury agents — Vote

**What they need:** Strong judgment, ability to compare, attention to requirements.

The jury only runs **once per decision** regardless of consortium size — so a powerful jury model costs only marginally more than a weak one. The jury sees all proposals and must pick the best. A model that is good at comparison, logical evaluation, and requirement checking is ideal.

**Good jury choices:** Powerful reasoning models, models known for instruction-following.

Examples:
- `moonshotai/kimi-k2-thinking` — strong reasoning, good at structured judgment
- `x-ai/grok-4.1-fast` — fast reasoning, good comparison
- `z-ai/glm-5.1` — strong general reasoning
- `qwen/qwen3.6-plus` — capable reasoning, good structured output

### Task-class routing (advanced)

Once you know what kind of task you're running, you can tune even further:

| Task class | Consortium recommendation | Jury recommendation |
|---|---|---|
| `implement` (write code) | `devstral-2512` + `qwen3-coder:free` + fast general | Strong reasoning model |
| `analyze` (evaluate, audit) | Diverse general models | Strong reasoning model |
| `create` (essay, recipe, creative) | Multiple diverse models, high temperature | Strong general model |
| `coordinate` (plan, orchestrate) | Models good at structured output | Reasoning model |
| `transform` (reformat, translate) | Fast general models | Skipped — single-pass policy |

### The three presets

The UI's Config tab offers three named presets that embody different cost/quality tradeoffs:

**Uniform** — Same model everywhere. Best for getting started and debugging. No multi-model complexity.

**Fast + Smart** ⭐ — Fast free models propose, one powerful reasoning model judges. This is the recommended default because:
- 3 fast proposals cost less than 1 powerful proposal each
- The jury's one call costs the same as any other single call
- You get near-top-model judgment quality at a fraction of the cost
- Example: 3× `gemma-4-26b:free` (consortium) + 1× `kimi-k2-thinking` (jury)

**Full Ensemble** — Different model families both propose and judge. Best for adversarial tasks or when you genuinely want maximum independence. More expensive but the hardest setup to fool, because cross-family consensus is difficult to game.

### The fallback adapter

If all primary agents time out for a decision, one synchronous call to a designated fallback model is made before failing the node. Set `fallback_provider: "openrouter"` and `fallback_model: "stepfun/step-3.5-flash:free"` in the API request to always have a safety net.

---

## How a Full Run Flows: Step by Step

Here is exactly what happens when you start a run with goal `"Build a fitness app"`:

1. **`run_started`** — Engine records config, adapter counts, prompt version.

2. **Spec extraction** — One LLM call extracts `required`, `forbidden`, `success_criteria`, `domain="technical"`, `task_class="implement"`, `concrete_indicators=["code", "function", "class", "endpoint"]`.

3. **Mode decision** — 3 consortium agents each see the goal + spec and propose `mode: "recursive"` or `mode: "base"`. Early exit fires if 2 agree. Jury votes if they disagree. At depth 0 with a complex goal, `recursive` wins.

4. **Planning** — 3 consortium agents each propose a decomposition plan: a list of child sub-goals with dependency declarations. Jury picks the best plan. Example winner: `[auth_module, workout_module (depends: auth_module), ui_layer (depends: auth_module, workout_module)]`.

5. **Child refinement** — For each child, a Consortium + Jury round clarifies: exactly what must this child return? What's its success condition? What format?

6. **Child execution** — `auth_module` and `workout_module` start in parallel (only `auth_module` has no deps). Each child runs its own full `RafNode.run()` — mode decision, possibly recursive again, base execution, analysis.

7. **`ui_layer` waits** — When `auth_module` completes, `workout_module` gets its output as dependency context. When both complete, `ui_layer` starts with both outputs.

8. **Merge** — After all children finish, a Consortium + Jury round synthesizes their outputs into one coherent result.

9. **Spec repair** — If the merged output is missing required items (e.g. no authentication code), a repair child is spawned targeting exactly those items.

10. **Analysis** — A Consortium + Jury round evaluates: is the output locally valid? Is the overall goal completed? Returns `approved: true/false`, `locally_valid`, `goal_completed`.

11. **`run_done`** — Final result delivered. All events are in the trace.

---

## Budget and Resource Management

### Node budget
`max_nodes_total` (default 50) is a hard cap. Before planning, RAF checks how many nodes remain. If the proposed plan would exceed the budget, it truncates the plan proportionally and strips dependency references to dropped children.

### Token budget
`token_budget` sets a soft cap on total tokens across the run. Every adapter reports actual token usage from the API response. When the budget is exceeded, the next `_check_cancelled()` checkpoint stops the run with a `token_budget_exceeded` event.

### Depth-based consortium shrink
To control cost automatically as the tree deepens:
- Depth 0 (root): full consortium size (e.g. 3)
- Depth 1: `max(2, size - 1)` agents
- Depth 2+: 1 agent (jury auto-skipped via unanimity)

This front-loads diversity at the top of the tree where it matters most and cuts cost at the leaves where goals are small and atomic.

### Per-task timeouts
Each task type has a timeout in seconds. When a timeout fires, the agent's future is cancelled and a `model_call_timeout` event is emitted. If enough agents finish before the timeout, the jury proceeds with what arrived. If none arrive, the fallback adapter is tried.

---

## The Quality Gate

Before proposals go to the jury, they are filtered through a quality gate that removes obviously bad candidates:

1. **Length check:** Output under 100 characters is likely not a real answer — filtered.
2. **Restatement check:** If the output's word overlap with the goal exceeds 0.85, the agent just copied the goal instead of solving it — filtered.
3. **Concreteness check:** For short outputs (under 800 characters), checks for domain-specific concrete elements (code, numbers, measurements, etc.). If none found — filtered.

If ALL candidates are filtered, the gate falls back to passing all of them (so the jury always has something to vote on).

---

## The Goal Cache

Repeated sub-goals are cached within a run. The cache key is a SHA-256 hash of `(goal, sorted required items, sorted ledger state)`. On a cache hit, the node completes immediately with the cached result and emits a `cache_hit` event. This prevents redundant work when multiple child nodes have identical refined goals.

---

## File Map

```
raf/
├── core/
│   ├── node.py       — RafNode (all execution logic) + RafEngine (run orchestration)
│   ├── spec.py       — Spec, SpecLedger, SpecExtractor, SpecValidator
│   ├── deps.py       — Topological sort + circular dependency detection
│   └── trace.py      — TraceLogger (JSON events + stderr spinner)
├── agents/
│   ├── consortium.py — Consortium: parallel proposals + fallback + early exit
│   └── jury.py       — Jury: parallel votes + confidence-weighted aggregation + fallback
├── llm/
│   ├── adapter.py         — ModelAdapter base class + usage reporting hook
│   ├── prompt_adapter.py  — Shared prompt builder: Spec/Ledger injection, jury scoring rubric
│   ├── openrouter_adapter.py — OpenRouter: reasoning models, JSON mode models, repair
│   └── mock_adapter.py    — Deterministic mock: Hanoi solver, domain-aware responses
└── schemas.py    — All validators + RafConfig dataclass

server/
├── main.py        — FastAPI app: REST + WebSocket, plan approval gate, CORS
└── run_manager.py — RunManager: adapter factory, config builder, run lifecycle

web/src/
├── App.tsx              — Full React app: graph, timeline, inspector, config, sessions
├── components/
│   └── ExecutionGraph.tsx — D3 SVG graph: nodes, edges, satellite clusters, pulsing ring
└── styles.css           — Layout, animations, dark theme
```

---

## Summary

The fundamental loop in RAF is:

```
Goal → [Model A proposes] [Model B proposes] [Model C proposes]
     → [Model D votes] [Model E votes] [Model F votes]
     → Best proposal wins
     → If too complex: break into sub-goals → repeat
     → Merge sub-results → validate → done
```

The power is in the separation of concerns: proposers diverge (temperature ladder, different models, different perspectives), voters converge (judgment, requirement checking, comparison). No single model can quietly underperform without being overruled by the group. Every decision is auditable in the trace.
