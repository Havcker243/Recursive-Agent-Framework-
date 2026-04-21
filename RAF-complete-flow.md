# RAF Complete Flow (Natural Language)

This document describes the full runtime behavior of the Recursive Agent Framework in plain language. It focuses on decisions, responsibilities, and information flow rather than implementation details.

---

## End-to-End Flow

1. **Intake and Spec Extraction**
   - A task arrives at the root node with any supporting context.
   - The system extracts a frozen **Spec** from the goal: required items, forbidden items, success criteria, domain (technical / culinary / fitness / creative / business / academic / general), and domain-specific concreteness indicators.
   - The Spec is injected into every agent prompt for the entire run. No agent can claim ignorance of requirements.
   - A **SpecLedger** is initialised to track locked key decisions as the run progresses.
   - If the node depends on siblings, their completed results are folded into the context before any decision is made.

2. **Base vs. Recursive Decision**
   - A small group of independent agents proposes whether the task should be handled directly or decomposed (Consortium).
   - A separate voting group selects the final decision (Jury).
   - The models used at this step depend on the node's depth (see Three-Tier Routing below).

3. **If the task is handled directly (base case)**
   - **Proposal:** Multiple agents independently produce execution outputs in parallel (Consortium). Each agent receives the full Spec and all locked SpecLedger decisions.
   - **Quality gate:** Candidates that are too short, merely restate the goal, or contain no concrete content are filtered out before the vote. If all candidates are filtered, the gate is bypassed.
   - **Ledger gate:** Candidates that contradict an already-locked decision are removed before the vote.
   - **Selection:** A voting group (Jury) picks the strongest output. Unanimous proposals skip the vote.
   - **Decision locking:** The winning agent's explicit key decisions are written to the SpecLedger so downstream nodes stay consistent.
   - **Tool loop:** If the winning proposal requests a tool call (web search, HTTP fetch, code execution), tools are invoked and the result is fed back into execution. This repeats up to a configured limit.
   - **Scope check:** The output is verified to stay on-topic; off-topic outputs trigger one retry with corrective feedback.
   - **Spec repair loop:** The output is checked for missing required items. If gaps are found, a targeted patch node is spawned listing exactly what is missing and the fixed output replaces the original. The loop runs up to a configured number of attempts (default: root only).
   - **Evaluation:** Multiple agents independently judge success and assign a confidence score (Consortium). A voting group selects the final assessment (Jury). Unanimous agreement skips the vote.

4. **If the task is decomposed (recursive case)**
   - **Plan generation:** Multiple agents propose ways to split the task into child tasks with dependencies (Consortium). A voting group selects the best plan (Jury).
   - **Plan validation:** Dependency cycles are detected and rejected. If the node budget is tight, the plan is truncated to an affordable number of children; dangling dependencies on dropped children are removed automatically. Meta-children that are purely validation steps ("check the above", "quality review") are filtered out of the plan.
   - **Human approval gate (optional):** If plan approval is enabled, execution pauses and the user may edit the plan before continuing.
   - **Context refinement:** Each planned child is independently refined by a proposal+vote round to clarify its goal, expected output, and success criteria.
   - **Child execution:** Children are spawned with refined context. Children with no pending dependencies run in parallel (up to a configured concurrency limit); others wait for their dependencies to complete. If a child fails, its failure is recorded gracefully and downstream dependents receive an error context rather than crashing the tree.
   - **Merge:** Multiple agents each produce a synthesis of the child outputs (Consortium). A quality gate and ledger gate run before the vote. A voting group selects the best merged result (Jury). The merge is then scope-checked.
   - **Spec repair loop:** The merged output is checked for missing required items. Patch nodes are spawned if gaps are found (same rules as base case).
   - **Evaluation:** Multiple agents independently judge the merged result — approved/rejected and confidence (Consortium). A quality gate and ledger gate run before the vote. A voting group selects the final assessment (Jury). Unanimous agreement skips the vote.

5. **Output**
   - The node returns an approved/rejected flag, a confidence score, an execution summary, and the collection of child results.
   - The root node's result is the final run output.

---

## The Proposal → Vote Pattern

At every decision point, RAF uses a two-stage pattern:
- A **Consortium** generates diverse candidate options independently.
- A **Jury** selects the best option by voting.

Two filters always run before the Jury sees candidates:
- **Quality gate** — removes low-signal proposals (too short, restatements, no concrete content).
- **Ledger gate** — removes proposals that contradict locked SpecLedger decisions.

If all candidates are filtered, both gates are bypassed so the run never stalls.

This pattern applies to all six decision points: mode decision, plan generation, child context refinement, base execution, merge, and analysis.

---

## Three-Tier Model Routing

The system routes decisions to different model tiers based on depth and task type:

- **Tier 2 (Root / Referee)** — Root node, depth-1 planning and merging, all analysis, spec repair. Strongest models; errors here propagate through the whole tree.
- **Tier 1 (Mid / Planner)** — Mid-level planning, merging, and mode decisions. Capable models balancing quality and cost.
- **Tier 0 (Leaf / Worker)** — Base execution at depth 2 and deeper. Fast, cheap models where parallel diversity matters more than raw power.

Jury floor rule: Tier 0 and Tier 1 consortium proposals are always graded by at least mid-tier jury models.

---

## Why Execution and Evaluation are Separate

Execution and success evaluation are intentionally split:
- Executors focus on producing results.
- Evaluators judge those results with fresh context.
- This separation gives clearer accountability and more reliable quality signals.

---

## Domain Awareness

The Spec system detects the domain of the root goal (technical, culinary, fitness, creative, business, academic, or general). Domain affects:
- Which concreteness indicators are used in the quality gate.
- Which key decision suggestions appear in the SpecLedger prompt.
- Which items are excluded from the forbidden list (e.g. if the user asked for a blockchain solution, "blockchain" is removed from the default forbidden list for that run).
- The jury scoring rubric (criterion 3 becomes "Domain quality — appropriate for domain X" instead of a generic security check).
