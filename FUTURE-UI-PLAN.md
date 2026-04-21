# RAF UI Future Plan

This file tracks planned UI changes for the RAF web app. It is intentionally separate from `RAF-project-spec.md`.

## How To Read This

This is not a request for a new backend architecture. It is a frontend visualization and inspection plan for the existing RAF trace.

## Current Status

Implemented now:

- Frontend grouped full graph, recursive child nodes, dependency edges, node click inspection, live run health, stale warning, session replay/export refresh, JSON/PDF export flow, plan governance UI, plan recovery UI, zoom controls, model slot selection, and full-panel tab layout cleanup for Params and Votes.
- Backend plan recovery config and events are wired through the API: `plan_recovery`, `max_plan_retries`, `plan_validation_failed`, `plan_retry_start`, `plan_retry_done`, `plan_abandoned`, and `plan_replaced`.
- Backend model timing events are wired for consortium and jury calls: `model_call_start`, `model_call_done`, and `model_call_failed`.

Still remaining:

- Per-task timeout and fallback behavior: `model_call_timeout`, `model_call_fallback`, timeout config, and partial-result continuation rules.
- PDF graph capture still needs final verification against very wide/deep graphs to ensure the full graph image is never cropped.
- Physics tuner still needs reliability polish: always-reachable handle, drag/slider separation, and a more transparent expanded overlay.
- Live UI display for the new model timing events can be made richer by adding active-call and slowest-call summaries once real traces confirm the event shape.

The user's intent:

- In full graph mode, show the real RAF process as grouped decision structures.
- Do not show only voting nodes. Show recursive child nodes, deeper children, dependencies, and merge/backflow.
- When a node is clicked, show the full available details for that exact node.
- Keep the graph readable with compact labels, but put complete information in the node details panel.

Do not fake missing data. Use trace events that already exist. If a field is not emitted, show a clean empty state or mark it as unavailable.

## Goal

Make the graph show the full recursive RAF process clearly:

- what each RAF node decided
- what children each node created
- how child nodes depend on each other
- how child outputs merge back into the parent
- what each consortium proposed
- what each jury voted
- what the referee or validator checked
- what output, error, or decision belongs to each exact node

The graph should show structure. The clicked-node panel should show full details.

## 1. Grouped Full Graph

Full graph mode should group agent activity instead of attaching every proposal and juror directly to the RAF node.

Target shape:

```text
Root RAF node
  -> Mode Consortium
       -> Agent 1 proposal
       -> Agent 2 proposal
  -> Mode Jury
       -> Juror 1 vote
       -> Juror 2 vote
  -> Plan Consortium
       -> Agent 1 plan
       -> Agent 2 plan
  -> Plan Jury
       -> Juror 1 vote
       -> Juror 2 vote
```

This should stay in full mode. Simplified mode should stay clean and mostly show RAF nodes.

## 2. Recursive Child Graph Story

The UI should show more than votes. It should show the actual recursive tree.

Current behavior:

- Child RAF nodes already appear from `node_created.parent_id`.
- Dependency edges already use `plan_selected.children[].depends_on` and `node_created.plan_child_id`.
- A recursive child can create its own children.

Future behavior:

- Show planned children as a clear branch from the parent plan.
- Show deeper child nodes as nested recursive branches.
- Show dependency edges between sibling children.
- Show merge/backflow edges from completed child outputs back into the parent merge step.

Target shape:

```text
Root RAF node
  -> Plan group
       -> child A RAF node
       -> child B RAF node
       -> child C RAF node

child A RAF node
  -> Plan group
       -> child A.1 RAF node
       -> child A.2 RAF node

child A / B / C complete
  -> Parent Merge group
       -> merged parent output
```

Edge meanings:

- Parent-child edge: decomposition.
- Dependency edge: sibling execution ordering.
- Merge/backflow edge: child output returning to the parent result.

## 3. Full Node Details Panel

When a user clicks any node, the panel should show all available details for that exact node. It should not be only a small summary.

The panel should adapt by node type.

RAF node details:

- node id
- parent id
- goal
- depth
- current phase
- mode decision
- selected mode
- plan selected
- children created by this node
- child dependencies
- child statuses
- merge result
- final output
- confidence
- duration
- errors
- full event history for this node

Consortium group details:

- task name, such as `mode_decision`, `plan`, `base_execute`, `merge`, or `analysis`
- parent RAF node
- candidate count
- every candidate payload available in the trace
- candidate output, mode, plan, or analysis data
- which candidate later won, if a jury selected it
- model/agent index if available

Agent proposal details:

- agent number
- task
- proposal payload
- output, mode, plan, or analysis result
- whether this proposal was selected
- source event

Jury group details:

- task name
- parent RAF node
- options reviewed
- winner id
- confidence
- all juror votes
- rankings and reasons if emitted
- link back to the winning proposal

Juror vote details:

- juror number
- selected option
- confidence
- ranked options
- reason text if emitted

Referee / validator / check details:

- check type
- pass/fail status
- missing requirements
- forbidden violations
- scope drift result
- repair attempts
- filtered children
- token budget events
- structured trace fields that are useful to the user

If the trace has no details for a clicked node yet, show a clean empty state:

```text
No detailed trace data has arrived for this node yet.
```

## 4. Compact Graph Labels

Nodes can show short hints directly on the graph, but full details belong in the clicked-node panel.

Good graph hints:

```text
mode: recursive
winner: option-0
88%
3 children
output ready
error
```

Avoid putting long text, full proposals, raw output, or long error messages inside the graph node.

## 5. Physics Tuner Reliability and Overlay Design

The physics tuner still needs more work.

Observed issue:

- It may not open consistently.
- Drag/click behavior can feel unreliable.
- When expanded, it can block too much of the execution graph.

Future behavior:

- The tuner should always be reachable from a small visible handle.
- Opening and closing should be reliable.
- Dragging the tuner should not conflict with sliders or controls.
- When expanded, the panel should be transparent/frosted enough that the graph remains visible behind it.
- The tuner should feel like a graph overlay, not a separate blocking panel.

Design target:

```text
collapsed: small "Physics" handle over graph
expanded: translucent overlay with drag handle and sliders
```

Implementation notes:

- Keep it mounted even when collapsed; only collapse its content.
- Separate panel dragging from slider dragging.
- Add a clear open/close affordance.
- Use a transparent or frosted background when expanded.
- Verify it over the live graph in desktop and narrow viewports.

## 6. Plan Governance

The current `Plan approval` switch should become a clearer governance setting.

Planned modes:

```text
Auto approve
Review only
Manual approval
```

Behavior:

- `Auto approve`: consortium proposes, jury selects, validator/referee checks, RAF continues.
- `Review only`: UI shows the selected plan, votes, checks, and dependencies without blocking execution.
- `Manual approval`: current blocking behavior. User approves or edits the selected plan.

Backend mapping:

- `Auto approve` -> `plan_approval_required = false`
- `Review only` -> `plan_approval_required = false`, plus stronger UI highlighting
- `Manual approval` -> `plan_approval_required = true`

## 7. Plan Recovery

Plan recovery is a later backend-assisted feature. It should not be faked only in the frontend.

Intent:

If the selected plan is invalid, unsolvable, incomplete, or fails validation, RAF should preserve that failed plan attempt and create a new replacement attempt instead of silently hiding the failure.

Target behavior:

```text
Plan Consortium proposes plans
Plan Jury selects best plan
Validator / Referee checks selected plan

If valid:
  execute children

If invalid:
  mark plan attempt as failed
  explain why it failed
  generate a replacement plan
  show the new attempt as a new graph node/branch
  retry only up to a fixed limit
```

Target graph shape:

```text
RAF node
  -> Plan attempt 1
       -> Plan Consortium
       -> Plan Jury
       -> Validator: failed
  -> Plan attempt 2
       -> Plan Consortium
       -> Plan Jury
       -> Validator: passed
       -> child RAF nodes execute
```

Important safeguards:

- Do not retry forever.
- Use a small limit such as `max_plan_retries = 2`.
- Keep failed attempts visible in the trace.
- Show the reason a plan was rejected.
- Show which plan replaced it.
- Make recovery optional.

Possible UI setting:

```text
Plan recovery:
Off / Auto retry / Ask before retry
```

Suggested backend trace events:

```text
plan_validation_failed
plan_retry_start
plan_retry_done
plan_abandoned
plan_replaced
```

Frontend display:

- Full graph mode shows each plan attempt as its own node or group.
- Failed attempts get a failed/error state.
- Replacement attempts connect back to the same RAF parent node.
- The node inspector shows the rejected plan, failure reason, replacement plan, retry count, and final outcome.

This feature changes RAF behavior, so it should be implemented after the frontend-only grouped graph and full node inspector work.

## 8. Mid-Run Observability and Stuck-State UX

The UI must handle traces exported while the run is still active. A `running` status in an export does not automatically mean the system is broken.

Intent:

- Make active progress visible.
- Distinguish normal long-running LLM calls from a truly stale run.
- Make partial failures visible without treating them as final run failure.
- Make mid-run JSON/PDF exports clearly marked as incomplete.

Run state display:

```text
Currently: root -> spec validation
Waiting on: root analysis
Last event: spec_validation_final
Time since last event: 2m 14s
```

Stale-state warning:

```text
No new trace events for 90 seconds.
The run may still be waiting on an LLM call.
```

Active node highlighting:

- Highlight the node that most recently emitted an event.
- Show the current inferred phase on the node.
- Examples: `root validating`, `node-9 executing`, `node-2 merging`.

Partial failure summary:

```text
Partial failures: 5
- node-2 mode_decision failed twice
- node-2 plan failed once
- node-2 refine_context failed once
```

Important distinction:

- A `child_failed` event is not necessarily a final `run_done` failure.
- RAF may recover from failed child calls and still complete.
- The UI should show both partial failures and final status separately.

In-progress export labels:

- JSON already includes `status`, but the PDF cover page should visibly say when an export is mid-run.
- Add labels such as:

```text
Status: running
Exported mid-run
Final output not available yet
```

Completion expectation hints:

For known RAF phases, show what is likely expected next:

```text
Last completed: spec_validation_final
Expected next: analysis -> merge_done -> node_done -> run_done
```

Per-node progress checklist:

When clicking a RAF node, show the node's progress through the RAF lifecycle:

```text
Spec extracted: done
Mode decided: done
Plan selected: done
Children started: done
Children done: partial
Merge: done
Spec validation: done
Analysis: waiting
Node done: pending
```

Long-running model call indicator:

If the last trace event suggests the system is waiting on a model call, show:

```text
Waiting on model call
Provider: gemini
Task: analysis
Node: root
```

Some of this can be inferred from the latest event. Exact active-call tracking may need backend support later.

Run health panel:

```text
Run health
Events: 137
Nodes: 9
Partial failures: 5
Last event: spec_validation_final
Last event age: 1m 42s
Status: running
```

Finalization guard:

If a run remains `running` long after a terminal-looking event, show a careful message:

```text
Run has passed validation but has not emitted run_done yet.
Waiting for final analysis or completion event.
```

Do not call this a failure unless the backend emits a final error or the user-defined stale timeout is exceeded.

## 9. Complete Export and Report Quality

Exports should be useful as standalone artifacts, especially after long RAF runs.

Observed issue:

- A downloaded JSON trace can still say `status: running` and `result: false` if it is exported before the frontend receives the final `run_done`, even when the backend completes moments later.
- The PDF report must include the full graph image, not a cropped or partially visible graph.
- The PDF trace section should be neatly organized, not just a sparse list of event names.

### 9.1 Final-State-Aware Export

Before exporting, the frontend should refresh the latest run state when `runId` exists:

```text
GET /api/run/{run_id}
GET /api/run/{run_id}/events
```

Then export using the freshest server state.

Rules:

- If the backend says `done`, export should include final `result`, final status, and final `run_done` if available.
- If the backend says `running`, mark the export clearly as mid-run.
- If the graph has root `node_done` but no `run_done`, label it as near-complete but not terminal.
- The export should include `exportCompleteness` metadata.

Example:

```json
{
  "status": "running",
  "exportCompleteness": "mid_run",
  "hasRunDone": false,
  "hasRootNodeDone": true,
  "note": "Root completed but run_done was not present when exported."
}
```

### 9.2 Full Graph PDF Capture

The PDF graph page should show the entire graph in full form.

Requirements:

- Capture all visible graph nodes and links.
- Fit graph bounds using node positions plus padding.
- Temporarily reset zoom/pan before capture.
- Prefer full graph mode capture if full-mode nodes exist, or clearly label which mode was captured.
- Avoid cropping wide graphs.
- If the graph is too large for one page, either scale it down cleanly or split across multiple pages.

The report should include:

```text
Graph page:
- full graph image
- node count
- edge count
- graph mode
- legend
```

### 9.3 Neatly Organized Trace PDF

The PDF trace section should be readable as a report.

Organize by sections:

```text
Run summary
Final output
Run health
Partial failures
RAF nodes
Plans and children
Consortium proposals
Jury votes
Referee/spec/check events
Tools
Timeline / raw trace table
```

Each section should show useful fields, not just event names.

Examples:

```text
RAF node:
- node id
- parent id
- depth
- mode
- goal
- output summary
- confidence
- duration
- status

Jury vote:
- node id
- task
- winner
- confidence
- option count
- juror count

Plan:
- parent node
- child count
- child ids
- dependencies
```

The raw trace table can stay at the end, but the report should first present the information in a human-readable structure.

### 9.4 JSON Export Completeness

JSON export should remain complete and machine-readable.

Include:

- latest server status
- latest server result
- all events available from `/api/run/{run_id}/events`
- graph nodes/links
- node outputs
- config
- physics
- model/provider settings
- selected node id
- export timestamp
- export completeness metadata

Do not remove raw event arrays from JSON; the PDF can be organized, but JSON should preserve the trace.

## 10. First Performance Work: Timing Events and Timeouts

These are the first backend performance items to implement before faster model routing.

Priority:

```text
1. Model call timing events
2. Per-task timeout and fallback behavior
3. Faster model routing later
```

### 10.1 Model Call Timing Events

Every model call should emit timing events so slow runs are explainable.

Events:

```text
model_call_start
model_call_done
model_call_failed
model_call_timeout
model_call_fallback
```

Example start event:

```json
{
  "event": "model_call_start",
  "node_id": "node-2",
  "task": "refine_context",
  "role": "consortium",
  "provider": "gemini",
  "model": "gemini-2.5-pro",
  "agent_index": 0,
  "attempt": 1,
  "timestamp": 1234567890.12
}
```

Example done event:

```json
{
  "event": "model_call_done",
  "node_id": "node-2",
  "task": "refine_context",
  "role": "consortium",
  "provider": "gemini",
  "model": "gemini-2.5-pro",
  "duration_ms": 253000,
  "attempt": 1,
  "timestamp": 1234568143.12
}
```

Why this comes first:

- It explains exactly where time is going.
- It makes mid-run waiting visible.
- It avoids guessing from gaps between unrelated events.
- It gives the UI real data for the Run Health panel.

Likely backend touch points:

- `raf/agents/consortium.py`
- `raf/agents/jury.py`
- `raf/llm/json_utils.py`
- `raf/core/trace.py`
- possibly adapter metadata in `raf/llm/*_adapter.py`

Implementation note:

Start with `Consortium.call()` and `Jury.vote()` if adding trace context to `call_json_with_repair()` is too invasive. The goal is practical visibility first.

### 10.2 Per-Task Timeout and Fallback Behavior

After timing events exist, add per-task timeout limits.

Suggested defaults:

```text
mode_decision: 60s
plan: 120s
refine_context: 60s
base_execute: 120s
jury vote: 60s
merge: 180s
analysis: 90s
```

Timeout behavior:

```text
emit model_call_timeout
ignore the timed-out result if it arrives later
retry once if configured
fallback to a configured faster model if available
otherwise continue with partial results if the consortium/jury has enough valid responses
```

Important Python constraint:

Python worker threads cannot be safely force-killed. First implementation should use `future.result(timeout=...)`, emit timeout, and stop waiting for that result. The underlying call may finish later in the background, but RAF should not block on it.

Suggested config:

```text
timeout_by_task
enable_fallback
fallback_provider
fallback_model
max_retries_per_task
```

Suggested frontend display:

```text
model_call_timeout
Task: refine_context
Node: node-2
Provider/model: gemini/gemini-2.5-pro
Timeout: 60s
Fallback used: gemini/gemini-2.5-flash
```

### 10.3 Faster Model Routing Later

Faster model routing is still valuable, but it should come after timing and timeout visibility.

Later routing goal:

```text
Root planning/final merge: strong model
Inner child tasks: faster model
Refine context: faster model
Jury votes: faster model
Analysis/checks: faster model
```

Do not implement routing first. Without timing events, it is hard to prove which tasks need faster routing.

## 11. Implementation Notes

Main frontend areas:

- `web/src/App.tsx`
  - `addSatelliteNodes`
  - `processEvent`
  - selected-node inspector data derivation
  - event correlation for plan children, proposals, jury votes, and merge events
- `web/src/components/ExecutionGraph.tsx`
  - group-node rendering
  - edge types for flow, parallel, dependency, and merge/backflow

Backend changes are not required for the first pass because the trace already includes:

- `node_created.parent_id`
- `node_created.plan_child_id`
- `plan_selected.children`
- `consortium_candidates`
- `jury_votes`
- `merge_done`
- referee/spec/check events

## 12. Concrete Implementation Checklist

Use this checklist when implementing the plan.

1. Add graph node types for decision groups.

Suggested types:

```text
consortium-group
jury-group
agent-proposal
juror-vote
referee-check
merge-group
```

If changing `GraphNode["type"]` is too wide at first, reuse existing `consortium`, `jury`, and `agent` types but add a `task` or `groupKind` field.

2. Change satellite node creation.

Current pattern:

```text
RAF node -> Agent proposal
RAF node -> Juror
```

Target pattern:

```text
RAF node -> Consortium group -> Agent proposal
RAF node -> Jury group -> Juror
```

Group ids should be stable and deterministic:

```text
{node_id}-consortium-{task}
{node_id}-jury-{task}
{node_id}-agent-{task}-{index}
{node_id}-juror-{task}-{index}
```

3. Preserve recursive child RAF nodes.

Do not replace the existing child node behavior. Keep using:

```text
node_created.parent_id
node_created.plan_child_id
plan_selected.children[].depends_on
```

The child graph is the core RAF structure. Agent/jury nodes are detail around that structure.

4. Add merge/backflow visualization.

When child nodes finish and the parent emits merge events, create a parent merge group:

```text
Parent RAF node -> Merge group
Child RAF node -> Merge group
Merge group -> Parent RAF node or Parent output state
```

If that feels visually too busy, only show these edges in full mode.

5. Build a derived `NodeInspectorData` object.

Do not store a lot of duplicated UI-only state. Derive inspector data from:

```text
selectedNode
events[]
graphNodes[]
graphLinks[]
nodeOutputs
```

The derivation should answer:

```text
What node was clicked?
What RAF node owns this node?
What task does it belong to?
What events belong to it?
What proposal/vote/output/check data belongs to it?
What child nodes and dependency edges belong to it?
```

6. Make the inspector type-aware.

Use node type and task to decide which sections to render:

```text
RAF summary
Mode decision
Plan and children
Consortium proposals
Jury votes
Output
Merge
Checks
Errors
Raw event history
```

7. Show full details in the inspector.

The inspector should show complete useful data, not only counters:

- full proposal payloads
- all vote options
- all juror votes
- winner and confidence
- selected plan children
- dependency lists
- outputs
- errors
- check results
- structured trace fields when they are useful

8. Keep graph labels compact.

The graph should not become a document. Use small hints only:
```text
plan
3 children
winner option-0
88%
output ready
error
```

9. Keep simplified/full mode behavior.

Simplified mode:

- RAF nodes
- main parent-child edges
- maybe dependency edges

Full mode:

- RAF nodes
- grouped consortium/jury/agent nodes
- dependency edges
- merge/backflow
- referee/check nodes

10. Verify with a recursive prompt.

Use a prompt that creates multiple children and deeper recursion, then check:

- parent creates children
- child creates its own children when recursive
- dependency edges connect sibling children
- full mode shows grouped consortium and jury nodes
- clicking each node type shows the correct full details
- error and output states are visible
