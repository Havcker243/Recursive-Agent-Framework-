# RAF Conceptual Views (Natural Language)

This file describes the core structural concepts of the Recursive Agent Framework in prose form.

---

## 1) Single-Node Lifecycle

A single node follows this progression:

1. **Spec extraction (root only)** — At the root node, the system reads the goal and extracts a frozen Spec: a list of required items, forbidden items, success criteria, domain, and domain-specific concreteness indicators. This Spec is injected into every agent prompt for the entire run.
2. **Initialization** — The node receives its task, the frozen Spec, and any locked decisions from the SpecLedger.
3. **Dependency merge** — If sibling results are required, they are folded into the context before any decision is made.
4. **Mode decision** — A proposal group and a voting group decide whether to execute directly or decompose. The tier of models used depends on the node's depth (see section 6).
5. **Direct execution path** — Multiple agents independently produce candidate outputs (Consortium). A voting group (Jury) selects the best. A quality gate filters low-signal candidates before the vote. The winning agent's locked decisions are written to the SpecLedger. A tool loop may follow if the winner requests tool calls. A spec repair loop then checks whether required items are satisfied and patches gaps if needed. Finally, a multi-agent analysis group judges success.
6. **Decomposition path** — The node generates a plan (Consortium → Jury), refines each child (Consortium → Jury per child), spawns children, merges their outputs (Consortium → Jury), runs a spec repair loop on the merged result, and evaluates success (Consortium → Jury).
7. **Return** — The node returns an approved/rejected flag, confidence score, execution summary, and child results.

---

## 2) Dependency Handling

When a parent creates multiple children, some children may rely on others:
- Children without dependencies start immediately.
- Children with dependencies wait until required siblings finish.
- Only after their dependencies complete do they proceed with their own execution.

This allows parallelism without violating ordering constraints. If a child fails, its failure is recorded and downstream dependents receive a graceful error context rather than crashing the tree.

---

## 3) Multi-Agent Decision Pattern

Most decisions use a two-stage pattern:

- **Divergence:** several agents propose options independently (Consortium).
- **Convergence:** another group of agents votes on the best option (Jury).

Two filters run before the vote:
- **Quality gate:** proposals shorter than a threshold, mere restatements of the goal, or outputs with no concrete content are removed before the Jury sees them. If all candidates are filtered, the gate is bypassed so the run does not stall.
- **Ledger gate:** proposals that contradict a decision already locked in the SpecLedger (e.g. proposing a different cuisine style after it was already committed) are removed before the vote.

This pattern applies to all six decision points:
1. Mode decision (base vs. recursive)
2. Plan generation
3. Child context refinement (per child)
4. Base execution
5. Merge of child outputs
6. Analysis (success/failure evaluation)

Clarification and scope-check remain single-agent steps since they are not spec-critical decision points.

---

## 4) Recursive Structure

The system builds a tree of work:
- The root node receives the overall task.
- It either finishes directly or spawns children.
- Children can themselves decompose into smaller children.
- Leaves of the tree are tasks that can be executed directly.
- A node budget (max_nodes_total) limits tree growth; if the budget is tight, plans are truncated and dangling dependencies on dropped children are removed.

---

## 5) Spec and Integrity System

Before any execution begins, the root node runs spec extraction:
- **Spec** — A frozen object containing: required items, forbidden items, success criteria, domain (technical / culinary / fitness / creative / business / academic / general), and domain-specific concreteness indicators. Every agent prompt receives the full Spec so no agent can claim ignorance of requirements.
- **SpecLedger** — A thread-safe store of committed key decisions. First-write-wins per key; later agents cannot override a locked decision. This prevents plan drift across parallel branches (e.g. a cuisine style committed at depth 0 stays committed throughout the tree).
- **SpecValidator** — Two-stage compliance check: Stage 1 uses a deterministic substring match (always runs, no API call); Stage 2 fires an LLM nuanced check only when Stage 1 fails. Neither stage hard-blocks execution; they degrade gracefully.
- **Spec repair loop** — After base execution and after merge, the system checks whether all required items are present in the output. If items are missing, a targeted "PATCH" node is spawned listing exactly what is missing. The loop runs up to a configured number of attempts. It only fires at depths within the configured repair depth limit (default: root only).

Forbidden items are filtered against the root goal — if the user explicitly mentioned a concept, it is removed from the forbidden list for that run so the system does not incorrectly penalise what the user asked for.

---

## 6) Three-Tier Model Routing

Models are selected based on where in the tree a decision is made:

- **Tier 2 — Root / Referee** — Used for the root node (depth 0), depth-1 planning and merging, all analysis steps, and spec repair. The strongest configured models are assigned here because mistakes at this level propagate through the whole tree.
- **Tier 1 — Mid / Planner** — Used for mid-level planning, merging, and mode decisions (depth 1+). Capable models that balance quality and cost.
- **Tier 0 — Leaf / Worker** — Used for base execution at depth 2 and below. Fast, cheap models where speed and parallel diversity matter more than raw power.

Jury floor rule: Tier 0 and Tier 1 consortium proposals are always graded by at least mid-tier jury models. Weak models never grade weak models.

If no tier-specific models are configured, all tiers fall back to the default consortium and jury adapters.

Consortium size is scaled adaptively within each tier: Tier 2 never scales down (always uses the full set), Tier 1 scales mildly, Tier 0 scales aggressively toward a minimum of one agent per child to stay within the node budget.
