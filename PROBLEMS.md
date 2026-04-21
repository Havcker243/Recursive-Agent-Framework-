# RAF — Known Problems Log

Every major bug encountered across all sessions: what it was, where it lived,
what you would actually see when it hit, why it happened, and how it was fixed.

---

## Concepts you need to know first

**Consortium** — a group of N LLM agents that each independently propose an answer
to the same question in parallel. The idea is that different models (or the same
model with different temperatures/personas) will produce genuinely different
proposals, giving you a richer set of options to choose from.

**Jury** — a separate group of M LLM agents that read all the consortium proposals
and vote on which is best, weighted by their self-reported confidence. The jury
never produces its own answer — it only evaluates.

**Node** — one task unit in the execution tree. Every goal gets one node. A node
either executes directly (base case) or splits into child nodes (recursive case).

**RafEngine** — the orchestrator. It owns the node budget, the adapters (LLM
connections), the trace logger, and the cancellation signal. Every node reports
back to the engine.

**Adapter** — a wrapper around one LLM provider (Gemini, Claude, OpenRouter, etc.)
that translates RAF task payloads into the provider's API format.

**Referee** — a deterministic external validator (NOT an LLM agent) that runs
after each node completes. It checks factual correctness / coverage progress
and injects grounded state into all subsequent agent prompts as read-only fact.

**Scope drift** — when an agent's output wanders off-topic. E.g. goal is
"write a login function" and the agent starts discussing database migrations.

**SSRF** — Server-Side Request Forgery. An attacker (or misbehaving agent) tricks
the server into making HTTP requests to internal services (localhost, AWS metadata
endpoints, etc.) that are normally unreachable from outside.

---

## Session 1 — Core stability

### 1. Scope drift in child nodes
- **File:** `raf/core/node.py`
- **Concept:** When you start a run, you can pass constraints like `scope_focus`
  ("only talk about Python") and `forbidden_topics` (["DevOps", "deployment"]).
  These constraints are supposed to follow every agent decision — mode choice,
  planning, child goal refinement, base execution.
- **Problem:** Constraints were being passed to base execution but NOT to mode
  decision, planning, or child refinement. So the top-level agents respected your
  scope, but as soon as children were planned, they had no idea constraints existed.
- **What you'd see:** You ask for a Python tutorial. The root node respects the
  scope. But child nodes start proposing things like "Set up Docker containers"
  and "Configure CI/CD pipelines" — completely outside what you asked for.
- **Why it happened:** The `_constraints()` helper method existed and was already
  wired into `_execute_base`, but nobody had added it to the other three decision
  point payloads. A case of partial implementation.
- **Fix:** Added `"constraints": self._constraints()` to all consortium payloads
  in `_decide_mode`, `_plan_children`, and `_refine_children`.

---

### 2. Consortium crash on single agent failure
- **File:** `raf/agents/consortium.py`
- **Concept:** The consortium runs N agents in parallel. If you have 3 agents and
  one of them hits a network timeout or returns garbage, the system should still
  have 2 good proposals to work with. Losing one agent should be recoverable.
- **Problem:** There was no try/except per agent. One failed agent threw an
  exception that immediately propagated up and killed the entire consortium call,
  taking down the run with it.
- **What you'd see:** The entire run crashes with a stack trace from inside the
  consortium, even though 2 out of 3 agents produced perfectly good responses.
  You'd see something like `RuntimeError: API timeout` with no output at all.
- **Why it happened:** The parallelism was implemented with `ThreadPoolExecutor`
  but results were collected without guarding each future individually.
- **Fix:** Wrapped each agent's future.result() in try/except. The consortium now
  only raises if zero agents succeed — one or two failures are silently skipped
  and the surviving proposals proceed to the jury.

---

### 3. Jury crash on single agent failure
- **File:** `raf/agents/jury.py`
- **Concept:** Same idea as #2 but on the voting side. If you have 3 jury voters
  and one fails, the other 2 votes should still decide the winner.
- **Problem:** Identical to #2 — no per-voter exception handling. One bad vote
  killed the entire jury round.
- **What you'd see:** Same symptom as #2 — run crashes on the voting step, all
  the consortium work is thrown away.
- **Fix:** Same pattern as #2 — per-voter try/except, raise only on total failure.

---

### 4. LLM returns integer confidence, validator crashes
- **File:** `raf/schemas.py`
- **Concept:** Every jury vote includes a confidence score (0.0 to 1.0) that acts
  as a voting weight. High confidence minority can outweigh low confidence majority.
  The schema validators check that this field is a float.
- **Problem:** LLMs often write `"confidence": 1` (integer) instead of
  `"confidence": 1.0` (float). JSON doesn't distinguish between the two, but
  Python's type checks do. The validator would reject `1` and crash.
- **What you'd see:** Any time an LLM expressed maximum confidence (1.0), the
  entire vote would fail with a schema validation error. The more confident the
  models, the more crashes you'd get — a backwards failure mode.
- **Why it happened:** JSON numbers have no float/int distinction. When LLMs
  write a round number like 1 or 0, they naturally omit the decimal point.
- **Fix:** Added `_require_number()` helper that accepts both int and float and
  coerces to float before validation. `1` becomes `1.0`, `0` becomes `0.0`.

---

### 5. Duplicate events in WebSocket stream
- **File:** `server/run_manager.py`
- **Concept:** The server stores all trace events from a run so that if you
  refresh the page or reconnect after a disconnect, it can replay everything
  from the beginning. On reconnect, it sends all stored events first, then
  switches to streaming new ones live from the queue.
- **Problem:** When switching from "replay stored events" to "stream live queue",
  the code didn't drain the events that had already been stored. So events
  that were added to the queue while replay was happening were replayed AND
  then received again from the live stream.
- **What you'd see:** Every node would appear twice in the timeline. The execution
  tree would show duplicate nodes. Vote counts would be doubled.
- **Fix:** After replaying stored events, drain those same events from the queue
  before entering the live stream loop, so there's no overlap.

---

### 6. Gemini repair prompt missing full context
- **File:** `raf/llm/gemini_adapter.py` / `raf/llm/prompt_adapter.py`
- **Concept:** When an LLM returns invalid JSON or JSON that doesn't match the
  expected schema, the system triggers a "repair" — it sends a follow-up prompt
  telling the model what went wrong and asking it to fix its response.
- **Problem:** The repair prompt included the error message and the bad raw
  response, but NOT the original task payload. So Gemini knew it produced
  bad JSON but had no idea what it was supposed to be producing JSON *for*.
- **What you'd see:** Gemini's repair attempts would produce completely wrong
  outputs — sometimes valid JSON but for a totally different task, because it
  was guessing context from the error message alone. Second attempts would fail
  the validator again, burning the retry budget.
- **Fix:** Repair prompt now includes the full original `task_payload` so the
  model has complete context to reconstruct a correct response.

---

### 7. Gemini plan prompt — no instruction to stay direct
- **File:** `raf/llm/prompt_adapter.py`
- **Concept:** When a node goes recursive, the planning step asks agents to
  decompose the goal into child tasks. Those children should be direct
  components of the goal — not setup tasks, not meta-tasks, not concerns
  that are tangentially related.
- **Problem:** Without explicit instruction, Gemini would plan children like
  "Set up version control", "Configure linting", "Write documentation" even
  for goals like "Write a sorting function". It treated every goal as a full
  software project.
- **What you'd see:** Simple goals would explode into 8+ children covering
  infrastructure concerns. The run would take forever and produce output about
  completely irrelevant topics.
- **Fix:** Added the line: "Only decompose into subtasks that directly accomplish
  the stated goal. Every child task must be a direct component of the goal,
  not a supporting concern."

---

### 8. Mock mode_decision not routing by keyword
- **File:** `raf/llm/mock_adapter.py`
- **Concept:** The mock adapter is a fake LLM used for testing — it returns
  deterministic responses without any API calls. For mode decisions, it needs
  to decide whether a goal should be executed directly (base) or decomposed
  into children (recursive). Depth >= 1 nodes should always be base, because
  the mock isn't sophisticated enough to handle multiple recursion levels.
- **Problem:** The mock always returned the same mode regardless of the goal
  text or the depth of the node. So even depth-3 nodes (grandchildren) would
  claim they needed recursive decomposition, causing infinite depth attempts
  that hit the max_depth wall every time.
- **What you'd see:** With the mock adapter, every node would try to go recursive,
  the depth limit would cut them off, and you'd see a flat tree where every
  node hit the budget wall instead of executing cleanly.
- **Fix:** Added keyword-based routing in the mock. Any node at depth >= 1
  returns "base" unconditionally.

---

### 9. Mock vote confidence below recursive threshold
- **File:** `raf/llm/mock_adapter.py`
- **Concept:** There's a config value `recursive_confidence_margin` (default 0.15)
  that acts as a "tiebreaker" — if the jury votes for base mode with low
  confidence, the system assumes uncertainty and forces recursive instead,
  since recursion is safer (more focused subtasks = better quality).
  The threshold is: if confidence < (confidence_threshold + margin) → force recursive.
  With defaults: if confidence < 0.6 + 0.15 = 0.75 → force recursive.
- **Problem:** The mock returned confidence 0.7, which is below 0.75. So every
  mock vote for "base" mode was overridden to "recursive" — even for leaf nodes
  that should clearly execute directly.
- **What you'd see:** With the mock, every node except the very deepest ones
  would be forced recursive regardless of the goal. The Hanoi demo would plan
  children forever instead of executing moves.
- **Fix:** Raised mock vote confidence to 0.85, above the forced-recursive threshold.

---

### 10. Multi-model: jury always used consortium adapter
- **File:** `raf/core/node.py`
- **Concept:** RAF supports using different LLM models for the consortium
  (proposals) and the jury (voting). For example: 3 fast/cheap models for
  proposals, 1 expensive/smart model as the jury judge. This requires the
  engine to track consortium adapters and jury adapters separately.
- **Problem:** `RafEngine` had a single `self.adapter` property. Even when jury
  adapters were explicitly configured, all jury calls went through the same
  adapter as the consortium — the separate jury configuration was completely
  ignored.
- **What you'd see:** No visible error, but the intended multi-model architecture
  didn't work. The "jury" was just more consortium agents calling the same model.
- **Fix:** Added `jury_adapters` parameter to `RafEngine.__init__`, with proper
  defaulting logic. Jury calls now use `self.jury_adapters` exclusively.

---

## Session 2 — Budget + threading

### 11. No cooperative cancellation
- **File:** `raf/core/node.py`, `server/run_manager.py`
- **Concept:** A RAF run can take minutes and cost significant API money.
  Users need to be able to cancel a run that's going in the wrong direction.
  "Cooperative cancellation" means the run checks for a cancel signal at
  safe checkpoints (between nodes, between API calls) and exits cleanly.
- **Problem:** There was no cancellation mechanism at all. Once you clicked
  "Run", the only way to stop it was to kill the server process. The run
  would keep spawning child nodes and making API calls until it hit max_nodes.
- **What you'd see:** Clicking cancel in the UI would appear to work (the
  button would react) but the server would keep processing. You'd see new
  nodes and events appearing in the timeline long after cancelling.
- **Fix:** Added `cancel_event: threading.Event` to `RafEngine`. A
  `_check_cancelled()` call at every key decision point checks whether the
  event is set. The server exposes `POST /api/run/{id}/cancel` which sets
  the event, and the run exits at the next checkpoint.

---

### 12. No proportional child budget
- **File:** `raf/core/node.py`
- **Concept:** `max_nodes_total` (default 50) is a hard cap on how many nodes
  a run can create. This exists to prevent runaway costs. But if you have
  45 nodes used and plan 8 more children, each child needs at least a few
  nodes of its own to do any meaningful work. Launching 8 children with
  only 5 nodes left means most of them fail immediately.
- **Problem:** The planner had no awareness of the remaining budget. It would
  propose as many children as it wanted, and they'd all start, immediately
  hit the node limit, and produce empty or error output.
- **What you'd see:** A burst of failed child nodes at the end of a deep run,
  all showing empty output. The merge step would try to combine 8 empty
  strings into a coherent answer.
- **Fix:** Added `_MIN_NODES_PER_CHILD = 3`. Before executing children, compute
  `max_affordable = remaining // 3`. If the plan has more children than affordable,
  truncate it. At least every kept child is guaranteed 3 nodes to work with.

---

### 13. Truncation KeyError after budget truncation
- **File:** `raf/core/node.py`
- **Concept:** Child tasks can depend on each other — e.g. "Write tests" depends
  on "Write the code". This dependency list (`depends_on`) determines execution
  order. `topo_sort` uses this to figure out which children can run in parallel
  and which must wait.
- **Problem:** When budget truncation dropped children from the plan (e.g. kept
  only the first 3 of 8), the remaining children's `depends_on` lists still
  referenced the dropped children. `topo_sort` would look for those IDs and
  crash with a KeyError because they no longer existed.
- **What you'd see:** After any budget truncation event, the run would immediately
  crash with a KeyError inside `topo_sort`. You'd never see any child nodes run.
- **Fix:** After truncation, iterate kept children and strip any `depends_on`
  entries that reference dropped IDs before passing the plan to `topo_sort`.

---

## Session 3 — Security + correctness

### 14. run_python in default available tools
- **File:** `raf/schemas.py`
- **Concept:** RAF agents can call tools — functions like `http_get` (fetch a
  URL), `run_python` (execute Python code), etc. The `available_tools` config
  determines which tools agents are allowed to call. This list defaults to
  "safe" tools that any agent can use without explicit permission.
- **Problem:** `run_python` was in the default list. This means by default,
  any LLM agent in any run could execute arbitrary Python code on your machine.
  A malicious or hallucinating LLM could run `os.system("rm -rf /")`.
- **What you'd see:** Nothing visible unless an agent chose to exploit it.
  But the attack surface was always open, silently, on every single run.
- **Fix:** Removed `run_python` from defaults entirely. You must explicitly
  add it to `available_tools` in your config if you want code execution.

---

### 15. run_python deny-list too narrow
- **File:** `raf/core/tools.py`
- **Concept:** Even with `run_python` opted-in, there's a sandbox that blocks
  dangerous operations. It checks the submitted code for forbidden patterns
  before executing it. Python sandbox escapes are notoriously difficult because
  the language has many paths to raw system access.
- **Problem:** The deny-list only blocked `import os` and `import sys`. But
  Python has dozens of ways to get system access: `__builtins__.__import__`,
  `().__class__.__bases__[0].__subclasses__()` to find subprocess classes,
  `getattr(builtins, 'eval')`, `ctypes` for direct memory, `pickle`/`marshal`
  for arbitrary code deserialization.
- **What you'd see:** An agent that tried hard enough could bypass the sandbox
  entirely by using class hierarchy traversal or ctypes instead of `import os`.
- **Fix:** Expanded deny-list to include: `__builtins__`, `__class__`,
  `__subclasses__`, `getattr`, `setattr`, `globals`, `locals`, `ctypes`,
  `pickle`, `marshal` — covering the most common escape vectors.

---

### 16. http_get SSRF vulnerability
- **File:** `raf/core/tools.py`
- **Concept:** SSRF (Server-Side Request Forgery) is when an agent tricks the
  server into making HTTP requests to internal addresses. Cloud providers like
  AWS expose sensitive metadata at `http://169.254.169.254/latest/meta-data/`
  (instance credentials, IAM roles). An LLM agent could access these.
- **Problem:** `http_get` accepted any URL with no validation. Agents could
  fetch `http://127.0.0.1:8001/api/runs` (the RAF server itself),
  `http://10.0.0.1` (internal network), or the AWS metadata endpoint.
- **What you'd see:** No visible error — the tool would happily return internal
  data. A compromised or misbehaving LLM could use this to exfiltrate
  credentials or probe your internal network.
- **Fix:** Added an IP guard that resolves the hostname and rejects requests
  to 127.x, 10.x, 192.168.x, 172.16-31.x, and ::1 before making the request.
  Also blocks non-http(s) schemes (file://, ftp://, etc.).

---

### 17. Tool follow-up always used first adapter
- **File:** `raf/core/node.py`
- **Concept:** When a base execution agent decides it needs to call a tool
  (e.g. fetch a URL to answer a question), the system runs a tool loop:
  call the tool, inject the result into the prompt, call the LLM again
  with the result to produce the final answer. In multi-model ensembles,
  the follow-up call should use the same model that won the jury vote —
  otherwise you're asking a different model to continue a train of thought
  it never started.
- **Problem:** The tool loop always used `consortium_adapters[0]` (the first
  adapter) regardless of which agent won the jury vote. If adapter[2] won
  but the tool follow-up went to adapter[0], the final output was incoherent.
- **What you'd see:** With multi-model ensembles, tool-using tasks would
  produce outputs that felt disconnected — the follow-up didn't match the
  winning proposal's style or reasoning.
- **Fix:** Each consortium result now embeds a hidden `_adapter_index` field
  tracking which adapter produced it. `_execute_base` reads this after the
  jury vote and uses the correct adapter for the tool loop.

---

### 18. Tool blocked — silent failure
- **File:** `raf/core/node.py`
- **Concept:** Agents can request tool calls by including a `tool_call` field
  in their output. If the requested tool isn't in `available_tools`, the
  system should refuse it. But refusing silently means the agent doesn't
  know why its request was ignored, and the user can't debug tool permission issues.
- **Problem:** When a tool was blocked, the code just broke out of the tool
  loop with no log, no trace event, no error — as if the tool request never
  happened. The agent's `tool_call` field was silently eaten.
- **What you'd see:** You configure an agent to use a tool, it requests it,
  nothing happens, the run completes but the tool result is missing. No
  indication of why in the timeline.
- **Fix:** Emits a `tool_blocked` trace event with the tool name and reason
  ("not in available_tools") so both the UI and logs show exactly what was
  refused and why.

---

### 19. Jury size not respected in multi-model mode
- **File:** `raf/core/node.py`
- **Concept:** `config.jury_size` (default 3) controls how many agents vote
  on each decision. This is separate from `config.consortium_size` (how many
  agents propose). You might want 3 proposers but 5 voters, or 5 proposers
  and only 1 voter.
- **Problem:** When no explicit jury adapters were provided, the code defaulted
  to `[adapter] * consortium_size` — so if you had 5 consortium agents, you'd
  silently get 5 jury voters regardless of what `jury_size` was set to.
  Setting `jury_size=1` for a cheap single-voter jury did nothing.
- **What you'd see:** Changing `jury_size` in config would have no effect.
  The jury always matched the consortium size. No error, just wrong behavior.
- **Fix:** Default now explicitly uses `config.jury_size`:
  `[self.consortium_adapters[0]] * config.jury_size`.

---

### 20. Approved field missing from node_result metadata
- **File:** `raf/core/node.py`
- **Concept:** After every execution (base or recursive), a separate analysis
  step uses Consortium + Jury to judge whether the output is good enough.
  This produces an `approved: true/false` field. The frontend uses this to
  show a pass/fail badge on each node in the graph.
- **Problem:** The `_analyze` call returned `approved`, but the code that built
  the `node_result` dict forgot to include it. The frontend always saw no
  approval status, and downstream nodes couldn't tell if a sibling's output
  had been approved.
- **What you'd see:** Every node in the UI would show no quality indicator.
  The approved/rejected status was computed but then thrown away.
- **Fix:** Added `"approved": analysis.get("approved", True)` to the
  `node_result["metadata"]` dict for both base and recursive cases.

---

## Session 4 — Run management

### 21. Unanimous confidence hardcoded to 0.95
- **File:** `raf/core/node.py`
- **Concept:** When all consortium agents propose the same answer (unanimous),
  the system skips the jury vote as an optimization (saves N LLM calls). But
  it still needs to assign a confidence score to that decision so downstream
  logic knows how certain the system is. This confidence affects whether the
  run continues recursing or trusts a base decision.
- **Problem:** The confidence was hardcoded to 0.95 regardless of how many
  agents agreed. 1 agent "unanimously" agreeing with itself got the same
  confidence as 5 agents all independently reaching the same conclusion.
  That's logically wrong — more independent agreement should mean higher certainty.
- **What you'd see:** A single-agent consortium would claim the same certainty
  as a 5-agent one. The confidence threshold logic would behave incorrectly,
  sometimes forcing recursive when it shouldn't.
- **Fix:** Scaled confidence by agent count:
  `0.75 + 0.20 * min(n, 3) / 3` → ~0.82 for 1 agent, ~0.88 for 2, ~0.95 for 3+.

---

### 22. Plan approval using hardcoded max_children=20
- **File:** `server/run_manager.py`
- **Concept:** RAF has a human-in-the-loop feature where before children are
  executed, the plan is shown to the user for approval/editing. The server
  validates the approved plan against config limits before accepting it.
- **Problem:** The validation used a hardcoded `max_children=20` instead of
  reading the run's actual `max_children_per_plan` config value. If you
  configured the run to allow 5 children max, you could still approve a plan
  with 20 children and it would bypass your own limit.
- **What you'd see:** Config-level child limits were silently ignored during
  human plan approval. You'd think your 5-child limit was enforced, but it wasn't.
- **Fix:** `max_children_per_plan` stored in `RunState` at run creation and
  read in `approve_plan` for validation.

---

### 23. Plan approval maps memory leak
- **File:** `server/run_manager.py`
- **Concept:** The plan approval flow uses two in-memory dicts per run:
  `_plan_events` (to pause execution while waiting for human input) and
  `_approved_plans` (to pass the approved plan back to the waiting thread).
  These are coordination primitives — they should exist only during the
  approval cycle and be cleaned up after.
- **Problem:** After the approval cycle completed, these dicts were never
  removed from the `RunState`. For runs with many planning nodes (deep
  recursive runs), these dicts would accumulate indefinitely.
- **What you'd see:** Memory usage would slowly grow over the lifetime of the
  server, especially for long runs with many plan approvals. No crash, just
  a slow leak.
- **Fix:** Both dicts are explicitly `.pop()`-ed (deleted) after use in
  both `request_plan_approval` and `approve_plan`.

---

### 24. Run eviction skipped active runs, then crashed
- **File:** `server/run_manager.py`
- **Concept:** The server keeps the last 50 runs in memory (for history and
  replay). When run #51 arrives, the oldest run gets evicted (deleted).
  But evicting an active run would break its WebSocket stream.
- **Problem:** Eviction logic iterated history looking for the oldest completed
  run to evict. But if somehow all 50 runs were still active (unlikely but
  possible during stress testing), it would find nothing and then crash with
  an index error, OR evict a random run anyway.
- **What you'd see:** Under heavy concurrent load, run #51 would either crash
  the server or disconnect an active run's WebSocket stream mid-execution.
- **Fix:** Eviction skips active runs by default. If all 50 are somehow active,
  it evicts the oldest one anyway (better to lose one stream than crash the server).

---

### 25. TraceLogger flooding stdout in server mode
- **File:** `raf/core/trace.py`, `server/run_manager.py`
- **Concept:** TraceLogger serves two purposes: in CLI mode, it prints events
  to stdout and shows a spinner on stderr so you can follow the run in the
  terminal. In server mode, events go over WebSocket to the frontend — stdout
  output is just noise that pollutes the server process logs.
- **Problem:** The server was using TraceLogger with default settings, so every
  trace event was printed to stdout AND sent over WebSocket. The server logs
  were flooded with raw JSON event objects.
- **What you'd see:** Running the server would produce an enormous amount of
  JSON log output in the terminal, making it impossible to spot real server
  errors. Piped output to a file would bloat rapidly.
- **Fix:** Added `quiet=True` flag to TraceLogger. When quiet, no stdout output.
  The spinner only writes to stderr when stderr is a real terminal (`isatty()`),
  so piped or redirected output stays clean.

---

### 26. Event list unbounded growth per run
- **File:** `server/run_manager.py`
- **Concept:** The server stores all events from each run so it can replay
  them for late-joining WebSocket clients or page refreshes. For a run with
  many nodes, each node emits 8-10 events (created, mode_decide, consortium,
  jury, done, etc.). With max 50 nodes and 10 events each, that's ~500 events.
  But without a cap, degenerate runs could produce thousands.
- **Problem:** `RunState.emit()` appended every event to a list with no size
  limit. A long run or a run caught in a retry loop could accumulate tens of
  thousands of events, all kept in memory indefinitely.
- **What you'd see:** Long-running servers would gradually consume more and
  more RAM. Eventually the process would be killed by the OS.
- **Fix:** Hard cap of 2000 events per run (`_MAX_EVENTS_PER_RUN`). Events
  beyond this cap are dropped (they're still sent over WebSocket, just not
  stored for replay).

---

### 27. CORS: wildcard + credentials invalid
- **File:** `server/main.py`
- **Concept:** CORS (Cross-Origin Resource Sharing) is a browser security
  mechanism that controls which websites can make API calls to your server.
  `allow_origins=["*"]` means any website. `allow_credentials=True` means
  include cookies/auth headers. The CORS spec forbids combining both — if
  origins is wildcard, credentials must be false.
- **Problem:** FastAPI CORS was configured with both `allow_origins=["*"]`
  and `allow_credentials=True`. Browsers would reject this with a CORS error,
  blocking all frontend-to-server communication in some security contexts.
- **What you'd see:** The frontend would fail to connect with a browser console
  error: "Response to preflight request doesn't pass access control check".
- **Fix:** Set `allow_credentials=False`. The frontend doesn't use cookies
  or auth headers, so credentials mode was never needed.

---

## Session 5 — Performance + correctness

### 28. O(n) child-future lookup in executor
- **File:** `raf/core/node.py`
- **Concept:** When running children in parallel, the code uses Python's
  `concurrent.futures.ThreadPoolExecutor`. As each child completes, you get
  back a `Future` object and need to figure out which `child_id` it corresponds
  to. O(n) means the lookup time grows linearly with the number of in-flight children.
- **Problem:** The code iterated `in_flight.values()` to find the matching
  future after each completion — effectively `O(n)` per child per batch.
  With 20 parallel children, each completion triggered 20 comparisons.
- **What you'd see:** No visible bug, just unnecessary slowness scaling with
  child count. With small plans it's negligible; with 20 children it wastes time.
- **Fix:** Built a reverse dict `future_to_cid = {v: k for k, v in in_flight.items()}`
  once per batch. Lookups are now O(1).

---

### 29. _adapter_index could be negative Python index
- **File:** `raf/core/node.py`
- **Concept:** Python lists support negative indexing: `lst[-1]` returns the
  last element. This is a feature for normal code but a trap when using an
  index that came from an external source (an LLM response).
- **Problem:** `_adapter_index` is embedded in consortium results by the
  framework, but in edge cases (e.g. repair prompt responses, mocked outputs)
  it could be -1 or another negative value. Using it directly to index into
  `consortium_adapters` would silently return the wrong adapter.
- **What you'd see:** In edge cases, the tool follow-up would use the last
  adapter instead of raising an error. Subtle wrong-model behavior with no
  error message.
- **Fix:** Guard with `max(0, min(_winning_idx, _n_adapters - 1))` to clamp
  the index to a valid range before using it.

---

### 30. Dependency context token blowout
- **File:** `raf/core/node.py`
- **Concept:** When a child node depends on a sibling that ran before it, the
  sibling's output is injected into the dependent child's goal so it has context.
  E.g. "Write tests" depends on "Write the code" — the code is injected so the
  test-writing node knows what to test.
- **Problem:** The full sibling output was injected with no length limit. If
  a sibling produced 10,000 characters of output and another child depended on
  3 such siblings, the dependent child's prompt would be 30,000+ characters
  before its own goal was even mentioned — often exceeding API token limits.
- **What you'd see:** API errors from token limit exceeded (`context_length_exceeded`,
  `max_tokens exceeded`) on nodes that had many or large dependencies. The
  run would crash at exactly the wrong time — right when context was most useful.
- **Fix:** Added `_DEP_OUTPUT_MAX = 500`. Each dependency's output is truncated
  to 500 chars before injection. Enough context to know what happened, not so
  much that it blows the token budget.

---

### 31. Unanimous skip showed 0 jury voters in UI
- **File:** `raf/core/node.py`
- **Concept:** The frontend visualizes jury votes as a count of "voters" on
  each decision node. When the consortium is unanimous, the system skips the
  jury vote (optimization). But the `jury_votes` trace event still needs to
  be emitted so the frontend knows what happened — with the right voter count.
- **Problem:** When emitting the `jury_votes` event for a unanimous decision,
  the votes list was empty `[]`. The frontend saw 0 voters, which made it
  look like no one had voted on the decision.
- **What you'd see:** Unanimous decision nodes in the SVG graph would show
  "0 jury voters" even though all consortium agents agreed. Looked like a bug.
- **Fix:** Populated the votes list with synthetic entries — one per consortium
  agent, all voting for `option-0` with the same confidence. Visually correct.

---

### 32. scope_check default True — off-topic silently passed
- **File:** `raf/core/node.py`
- **Concept:** After a node produces output, a scope check asks the LLM:
  "Is this output actually on-topic for the goal?" The response is
  `{"on_topic": true/false, "reason": "..."}`. If `on_topic` is false,
  the output is retried with explicit feedback about what went wrong.
- **Problem:** The code used `scope.get("on_topic", True)` — if the LLM
  returned malformed JSON that was missing the `on_topic` field, Python's
  dict.get() would return the default `True`, and the off-topic output would
  silently pass the scope check.
- **What you'd see:** Scope drift would get through whenever the scope check
  model itself produced a bad response. Paradoxically, the better the drift
  detection, the more likely it was to produce complex JSON that might be
  malformed — so bad drift was MORE likely to pass.
- **Fix:** Changed default to `False`. A missing or malformed `on_topic`
  field now triggers a retry instead of silently passing.

---

### 33. queue.Empty caught by bare except
- **File:** `server/run_manager.py`
- **Concept:** The event streaming loop reads from a queue in a loop. When
  the queue is empty and there are no more events, it raises `queue.Empty`.
  This is expected and should be caught specifically. A bare `except Exception`
  catches everything — including real, unexpected errors that should be visible.
- **Problem:** The bare `except` was swallowing real errors (network issues,
  serialization failures) along with the expected `queue.Empty`. Debugging
  WebSocket streaming issues was nearly impossible because errors disappeared silently.
- **What you'd see:** Streaming would silently stop in some edge cases with
  no error in logs, no error event sent to the client. The frontend would just
  hang waiting for events that would never come.
- **Fix:** Changed to `except queue.Empty` specifically. All other exceptions
  now propagate normally and appear in server logs.

---

## Session 6 — Frontend + WebSocket

### 34. All agent clusters overlapping in SVG graph
- **File:** `web/src/App.tsx`
- **Concept:** In the execution tree visualization, each node shows satellite
  dots representing the consortium and jury agents that participated in each
  decision. Different decision types (mode, plan, execute, merge, analyze)
  have their clusters positioned at different angles around the node so they
  don't overlap each other.
- **Problem:** Only `mode_decision` had a specific position defined. All other
  task types (base_execute, plan, merge, analysis) fell into a single fallback
  offset `(+85, -78)`. All clusters for all task types stacked on top of each
  other at that one position.
- **What you'd see:** On any node with more than one decision type shown,
  the orange/purple dots would all pile up in one corner. Impossible to tell
  which dots belonged to which decision.
- **Fix:** Added a `TASK_OFFSETS` dict with unique `[dx, dy]` coordinates per
  task type — mode_decision at top-left, plan at top-right, base_execute at
  right, merge at bottom-right, analysis at bottom.

---

### 35. Provider dropdown only showed mock
- **File:** `server/run_manager.py`, `web/src/App.tsx`
- **Concept:** The multi-model panel lets you assign different LLM providers
  to each consortium/jury slot. The frontend populates the provider dropdown
  by fetching `GET /api/models` from the server, which lists available providers.
- **Problem:** `list_models` only returned providers that had API keys configured.
  If you hadn't yet added a Gemini or Claude key, those providers were completely
  absent from the dropdown. Mock was always available (no key needed), so
  it was often the only option visible.
- **What you'd see:** Open the multi-model panel, see only "mock" in the
  provider dropdown. No way to know other providers existed or how to add them.
- **Fix:** `list_models` now always returns all 7 providers. An `available`
  list indicates which ones have keys. Providers without keys show "(no key)"
  in the dropdown so you know they exist but need configuration.

---

### 36. Model field required typing to see options
- **File:** `web/src/App.tsx`
- **Concept:** After picking a provider (e.g. OpenRouter), you choose which
  specific model to use (e.g. `meta-llama/llama-3.3-70b-instruct:free`).
  The UI needs to make these options discoverable — users shouldn't have to
  memorize model names.
- **Problem:** The model field used an HTML `<input list="datalist">` — a
  text field with autocomplete suggestions. These suggestions only appear
  as you type characters. If you don't type anything, you see a blank field
  with no hint that dozens of models are available.
- **What you'd see:** A text box with a placeholder. No indication of what
  to type, no visible list of options. Most users would leave the default
  or type random things.
- **Fix:** Replaced with a `<select>` dropdown when the provider has known
  models. Click it and the full list appears immediately, sorted and labeled.

---

### 37. Vite duplicate key warnings in EVENT_LABELS
- **File:** `web/src/App.tsx`
- **Concept:** `EVENT_LABELS` is a JavaScript object mapping event type strings
  (like `"base_execute_start"`) to human-readable labels shown in the timeline.
  JavaScript objects silently accept duplicate keys — the second value wins —
  but Vite correctly warns about this because it almost always indicates a mistake.
- **Problem:** `base_execute_start`, `base_execute_done`, and `merge_done` each
  appeared twice in the object with different labels. The first (less descriptive)
  copy was the one being silently overridden by the second.
- **What you'd see:** Vite build output showed warnings for each duplicate key.
  No runtime bug, but noisy warnings that made it harder to spot real build issues.
- **Fix:** Removed the earlier, less descriptive duplicate entries.

---

### 38. WebSocket "Reconnecting…" loop never stopped on server error
- **File:** `web/src/App.tsx`
- **Concept:** The frontend implements WebSocket reconnection with exponential
  backoff — if the connection drops, it waits 500ms, then 1s, then 2s, up to
  a max of 6 attempts. The loop should stop when the run finishes OR when the
  server reports a real error (not a transient network drop).
- **Problem:** When the server sent an event with `event: "error"` (e.g.
  "run not found" when the run had expired), the reconnect loop treated this
  as a transient connection failure and kept retrying. It would retry 6 times
  over ~30 seconds against an error that would never resolve.
- **What you'd see:** The "Reconnecting…" pill would appear and stay visible
  for ~30 seconds after a real server error. The UI would appear stuck even
  though the run was gone.
- **Fix:** Handle `data.event === "error"` explicitly: clear `isRunningRef`
  to break the loop immediately. After exhausting all retry attempts, set
  `runStatus("error")` so the UI shows a proper error state.

---

## Session 7 — New adapters + Gemini migration

### 39. Gemini adapter using deprecated SDK
- **File:** `raf/llm/gemini_adapter.py`
- **Concept:** Google released a new version of their Python SDK for Gemini
  (`google.genai`) with a different API design than the original
  (`google.generativeai`). The old package shows a `FutureWarning` on import,
  indicating it will stop working in a future release.
- **Problem:** The adapter was using the deprecated package. Every import of
  the Gemini adapter would print a warning. More importantly, the old package
  would eventually break entirely when Google removes it.
- **What you'd see:** Server startup logs would show `FutureWarning: google.generativeai`
  on every start. If you updated the `google-generativeai` package, it might
  silently break.
- **Fix:** Migrated to `google.genai`: new client instantiation with
  `genai.Client(api_key=...)`, and new call style with
  `client.models.generate_content(model, contents, config=GenerateContentConfig(...))`.
  Installed `google-genai` package.

---

### 40. OpenRouter 404 — free model data policy
- **File:** N/A (external account setting)
- **Concept:** OpenRouter is a unified API that routes to many LLM providers.
  Free-tier models (those with `:free` suffix) are subsidized, and OpenRouter
  requires account holders to explicitly opt in to allowing their requests to
  be used for free model traffic — this is a data policy decision.
- **Problem:** Calling free models without opting in returns HTTP 404 with
  "No endpoints found matching your data policy (Free model publication)".
  This looks like a code error but is entirely an account configuration issue.
- **What you'd see:** Every OpenRouter call to a `:free` model would fail with
  a 404. Non-free models would work fine. Very confusing if you don't know
  about the data policy requirement.
- **Fix:** Not a code fix — go to OpenRouter account settings → Privacy →
  enable "Allow free model publication". The 404s immediately stop.

---

### 41. DEEPSEEK_API_KEY typo in .env
- **File:** `raf/.env`
- **Concept:** The server reads API keys from environment variables. The code
  checks for `DEEPSEEK_API_KEY` specifically. If the variable name in `.env`
  doesn't match exactly, the key is never loaded and the adapter is silently
  treated as having no credentials.
- **Problem:** The key was saved as `DEEPSEEKER_API_KEY` (extra "ER") in the
  `.env` file. The code checks `DEEPSEEK_API_KEY`. The DeepSeek adapter would
  always show as unavailable despite having a valid key set.
- **What you'd see:** DeepSeek would appear as "(no key)" in the provider
  dropdown, and attempts to use it would fail. No error message explaining why —
  just silent unavailability.
- **Fix:** Rename `DEEPSEEKER_API_KEY` to `DEEPSEEK_API_KEY` in `.env`.
  (Claude cannot edit .env files — this is a manual change.)

---

## Session 8 — Referee

### 42. Referee attributes not initialized on RafEngine
- **File:** `raf/core/node.py`
- **Concept:** The Referee is a deterministic progress tracker that runs after
  each node completes. It accumulates outputs, checks coverage against the root
  goal's requirements, and injects grounded state (progress %, covered/missing
  requirements, invariant violations) into every subsequent agent's prompt as
  read-only fact. The engine owns the referee instance and shares it with all nodes.
- **Problem:** `referee.py` was fully implemented and node-level calls to
  `self.engine.referee.evaluate()` were wired in. But `RafEngine.__init__`
  never declared `self.referee` or `self.last_referee_report`, and `run()`
  never instantiated the `Referee` object. The first node to complete would
  crash with `AttributeError: 'RafEngine' object has no attribute 'referee'`.
- **What you'd see:** Any run would crash the moment the first base node
  completed its execution — right at the referee evaluation step. The crash
  would happen consistently, making the referee completely non-functional
  despite all the implementation work.
- **Why it happened:** The implementation was split across a session boundary.
  Node-level wiring was done, but the session ran out of context before the
  engine-level initialization could be added.
- **Fix:** Added `self.referee: Optional[Referee] = None` and
  `self.last_referee_report: Optional[RefereeReport] = None` to `__init__`.
  `run()` now creates `Referee(goal, adapter=self.consortium_adapters[0])`
  before the root node is created, so all nodes can safely call `self.engine.referee`.

---

## Session 9 — Spec + Ledger + Repair

### 43. Spec drift / goal rewriting
- **File:** `raf/core/node.py`, `raf/llm/prompt_adapter.py`
- **Concept:** Every Consortium agent receives the user's goal and is asked to
  propose an output. Without a frozen reference copy of the requirements, agents
  can silently reinterpret the goal — adding features the user never asked for,
  dropping features they decided were redundant, or pivoting to a related but
  different problem entirely.
- **Problem:** Agents rewrote the user's goal mid-run. A goal of "build a REST
  API with JWT authentication" could become "build a full-stack app with OAuth
  and a React frontend" by the time a deep recursive node executed. Unsolicited
  technologies (blockchain, IPFS, NFT token-gating) were added because they
  appeared in training data alongside "authentication" and "security".
- **What you'd see:** The final output would be technically impressive but wrong.
  It would satisfy a different goal than what the user typed. Required features
  ("password reset flow") would be missing; unsolicited features ("on-chain
  credential verification") would be present.
- **Why it happened:** Without a fixed spec, each agent's understanding of the
  goal was derived from the goal string alone. LLMs generalise from training
  data: "auth" → "use the newest auth tech" → "add blockchain credentials".
  There was no authoritative checklist anchoring the agents to what was asked.
- **Fix:** Added `raf/core/spec.py` with a `Spec` dataclass (required, forbidden,
  success_criteria) extracted once from the root goal by `SpecExtractor` before
  any node runs. The Spec is injected into every agent prompt via the `_spec`
  meta-key as a "Frozen Spec — immutable, read-only" block listing exactly what
  must and must not appear in outputs.

---

### 44. Soft requirements — "must" meant "maybe"
- **File:** `raf/core/node.py`, `raf/core/spec.py`
- **Concept:** Even with a Spec listing required items, agents might not adhere
  to it unless there is a deterministic enforcement mechanism that checks whether
  each required item actually appears in the output.
- **Problem:** Agents would acknowledge the required items in their framing
  ("this output addresses the JWT login requirement") but omit the actual
  implementation. A required item like "rate limiting on login endpoint" would
  appear in the Spec block every agent saw, but the final merged output would
  contain a one-line mention ("rate limiting could be added later") instead of
  an actual implementation.
- **What you'd see:** Required items listed in the Spec would not be
  substantively present in the output. The run would complete with full
  confidence despite missing critical features.
- **Why it happened:** The Spec provided goal context but no enforcement.
  Agents are trained to acknowledge instructions, not necessarily implement them.
  Without a post-hoc check that verifies the presence of required items, the
  Spec was advisory, not binding.
- **Fix:** Added `SpecValidator` (two-stage: deterministic word-split check then
  LLM) and `_spec_repair_loop` in `RafNode`. After base execution and merge,
  the loop validates output against `spec.required` and `spec.forbidden`. On
  failure, it spawns a "PATCH" repair `RafNode` with explicit instructions to
  add missing sections without rewriting what is already correct. Runs up to
  `config.spec_repair_limit` times before emitting `spec_validation_final`.

---

### 45. Novelty bias in scoring — creative beats correct
- **File:** `raf/llm/prompt_adapter.py`
- **Concept:** Jury agents evaluate proposals from the Consortium and vote on
  the best one using a confidence-weighted score. Without explicit scoring
  criteria ordering, LLMs tend to score "impressive" or "creative" proposals
  higher even when those proposals violate the user's requirements.
- **Problem:** A Consortium proposal that added a machine-learning recommendation
  engine, real-time WebSocket sync, and a mobile app would beat a simpler but
  correct proposal that just implemented the requested JWT authentication.
  Jury agents scored novelty and complexity highly because that is what training
  data rewards.
- **What you'd see:** The winning proposal in every competitive jury vote would
  be the most feature-rich one, regardless of whether those features were asked
  for. Simple, correct answers lost to complex, unsolicited ones consistently.
- **Why it happened:** The jury prompt said "vote on the best proposal" without
  defining what "best" means. LLMs fill that gap with their training priors,
  which reward complexity, novelty, and comprehensive feature sets.
- **Fix:** Added a lexicographic scoring order in the jury's role block in
  `_build_frame`: (1) spec coverage, (2) ledger consistency, (3) security
  correctness, (4) clarity + implementability, (5) novelty (TIE-BREAKER ONLY,
  with unsolicited features penalised). Also added an ELIGIBILITY hard gate:
  proposals missing a Required item or containing a Forbidden item are scored 0
  before the ordering even begins.

---

### 46. Placeholder pollution — empty proposals entered jury vote
- **File:** `raf/core/node.py`
- **Concept:** The Consortium collects N proposals in parallel and passes them
  all to the Jury for voting. If any proposal is structurally empty — a single
  sentence, a restatement of the goal, or fluffy prose with no concrete content
  — it should be filtered before the jury sees it, not scored.
- **Problem:** Consortium agents occasionally returned one-paragraph placeholders
  like "We will implement the authentication system as described." These are
  not implementations — they are intent statements. The jury would sometimes
  vote for them because they had no negative signals (no wrong technology, no
  spec violations) and scored high on "clarity" relative to noisier proposals.
- **What you'd see:** The winning proposal would be a placeholder. The node's
  output would be a vague paragraph that says the right things without
  implementing any of them. Downstream nodes would have no concrete foundation
  to build on.
- **Why it happened:** No minimum quality bar existed before jury voting. The
  jury could only compare proposals to each other, not to an absolute standard.
  A placeholder that rephrases the goal is "correct" by the jury's relative
  comparison since it doesn't introduce errors.
- **Fix:** Added `_quality_gate()` in `RafNode`, called before jury voting on
  both base_execute and merge candidates. Three signals: (1) length < 100 chars,
  (2) word-overlap with goal > 0.85 (restatement, not execution), (3) no
  concrete structural element (endpoint path, code keyword, SQL, class name)
  in outputs shorter than 800 chars. Fallback: if all candidates are filtered,
  the full list passes through so the run never hard-blocks.

---

### 47. Branch inconsistency — siblings chose contradictory stacks
- **File:** `raf/core/node.py`, `raf/core/spec.py`
- **Concept:** In a recursive node, multiple child nodes execute in parallel.
  Each child independently chooses a technology stack for its sub-task.
  Without coordination, siblings can commit to contradictory choices that
  the merge step cannot reconcile.
- **Problem:** In a 4-child plan for "build a web app", child A chose FastAPI
  and PostgreSQL; child B chose Express and MongoDB; child C chose Rails and
  MySQL. When merge tried to synthesise these into a coherent design, it had to
  pick one stack — but the other three children's output was already written for
  a different stack. The merged output was incoherent or described three
  different systems at once.
- **What you'd see:** The final merged output would read like it was written by
  three different developers who never talked to each other. Endpoint definitions
  in Python would appear alongside MongoDB schemas and ActiveRecord migrations.
  Confidence scores would be low because the merge agent could tell something
  was wrong.
- **Why it happened:** Child nodes had no shared state for technology decisions.
  Each child was an isolated LLM call that picked what seemed locally reasonable.
  There was no cross-child coordination mechanism.
- **Fix:** Added `SpecLedger` in `raf/core/spec.py` with first-write-wins
  semantics. The first winning agent to declare `{"framework": "FastAPI"}` locks
  that choice. `_ledger_gate()` in `RafNode` filters proposals contradicting
  any locked decision before jury voting. `_lock_decisions()` commits the
  winning agent's explicit `decisions` dict to the ledger and warns (but does not
  lock) on implicit technology signals detected in the output text.

---

### 48. Validation recursion inflation — checkers became child nodes
- **File:** `raf/core/node.py`
- **Concept:** When an LLM plans a recursive decomposition, it tends to add
  meta-tasks alongside real tasks: "validate the above", "review the output",
  "pre-check before proceeding". These are not deliverables — they are internal
  quality checks that the framework already performs through _analyze() and
  the scope check. Including them as child nodes wastes budget and adds latency
  without producing artifacts.
- **Problem:** A plan for "implement user authentication" might include 5 real
  children (login, logout, password reset, JWT issuer, refresh tokens) plus 3
  meta-children (validate each of the above, review the overall design, quality
  check the security model). The 3 meta-children consumed ~30% of the node budget
  and produced analysis reports that no other node consumed.
- **What you'd see:** The node graph would show "validate the output", "quality
  gate", "pre-check" nodes that consumed budget and time but produced only
  approval verdicts. The actual features would be crowded out in deep trees.
- **Why it happened:** LLMs plan the way a careful human would plan — including
  review steps. But in RAF, review is already baked into the framework through
  _analyze() and the Jury. Adding LLM-planned review nodes duplicates this work.
- **Fix:** Added `_VALIDATOR_CHILD_RE` regex and a filter in `_plan_children()`
  that removes children whose goals match the pattern (e.g. "validate the above
  implementation", "quality check the output", "pre-check"). The filter is
  bypassed when the root goal itself matches the pattern (e.g. "audit this
  codebase for vulnerabilities") because in that case, review children are
  intentional.

---

### 49. Hardcoded forbidden list — blocked legitimate tech when user asked for it
- **File:** `raf/core/spec.py`
- **Concept:** The forbidden list in the Spec is intended to block high-drift
  primitives (blockchain, ZK proofs, IPFS) that no reasonable web/backend
  request needs. But a static hardcoded list does not know about the user's
  specific goal — if the user explicitly asked for one of these technologies,
  banning it is wrong.
- **Problem:** A user goal of "build a blockchain voting system" would cause
  the SpecValidator to fail any output that mentioned "blockchain" — the very
  technology the user asked for. Every base node output would be flagged as a
  violation, the repair loop would try to remove "blockchain" from the output,
  and the final result would be a voting system that doesn't use blockchain.
- **What you'd see:** A run with "blockchain" in the goal would produce outputs
  without blockchain content. Repair loops would fire repeatedly without
  succeeding (because the repair output correctly mentioned blockchain, then
  got flagged, causing another repair attempt). The spec_validation_final event
  would always show "violations: [blockchain]".
- **Why it happened:** The forbidden list was populated before looking at the
  goal. It was treated as universally applicable rather than as a default for
  goals that don't mention the item.
- **Fix:** Added `_goal_relevant_forbidden()` in `raf/core/spec.py`. This
  function filters `_DEFAULT_FORBIDDEN` by removing any term whose significant
  words appear in the root goal. The LLM-identified forbidden items returned by
  `SpecExtractor` are run through the same filter before being merged into the
  final Spec. Items the user asked for are never placed on the forbidden list.

---

## Session 10 — Domain-Agnostic Spec System

### 50. Quality gate Signal 3 rejected valid non-technical outputs
- **File:** `raf/core/spec.py`, `raf/core/node.py`
- **Concept:** The quality gate in `_quality_gate()` uses three signals to
  reject placeholder proposals before jury voting. Signal 3 checks short outputs
  (< 800 chars) for the presence of at least one "concrete structural element".
- **Problem:** The concrete-element check was powered by `_CONCRETE_ELEMENT_RE`,
  a regex that matched REST paths (`/api/`), HTTP methods (`POST`, `GET`), SQL
  keywords (`SELECT`, `CREATE TABLE`), code keywords (`function`, `class`, `async`),
  and MVC class names (`UserController`). A valid 600-character recipe output with
  "Day 1: Oatmeal — 300 calories. Ingredients: ..." contains none of these patterns
  and would be rejected by Signal 3 as a "placeholder". The same problem applied to
  fitness plans, essays, business strategies, and any other non-technical domain.
- **What you'd see:** On a culinary or fitness goal, ALL consortium proposals would
  be filtered by Signal 3, the quality gate fallback would return them all anyway
  (it never hard-blocks), but the jury would see proposals that may already be valid.
  In edge cases where proposals were also caught by Signal 1 or 2, the run could end
  up with degraded outputs.
- **Why it happened:** `_CONCRETE_ELEMENT_RE` was written when RAF was only used for
  software engineering tasks. The patterns were appropriate for API/database design
  but made a tech-specific assumption that "concrete = code or SQL".
- **Fix:** Removed `_CONCRETE_ELEMENT_RE`. Added `_DOMAIN_CONCRETE` (a dict of
  domain-specific regex patterns for 7 domains: technical, culinary, fitness,
  creative, business, academic, general) and `_is_concrete_output(output, spec)`.
  The new function checks Spec.concrete_indicators first (LLM-extracted,
  goal-specific), then the domain's built-in patterns, then universal fallback
  patterns ("step 1", numbers with units, "for example"). Signal 3 in `_quality_gate`
  now calls `_is_concrete_output(content, self.engine.spec)` instead of the old regex.

---

### 51. Jury scoring rubric contained a tech-specific criterion
- **File:** `raf/llm/prompt_adapter.py`
- **Concept:** The jury's lexicographic scoring order tells agents how to rank
  competing proposals. Criteria are applied in priority order; criterion 1 dominates
  criterion 2, etc.
- **Problem:** Criterion 3 was "Security correctness — no known vulnerabilities
  introduced". This is meaningful for technical goals (SQL injection, auth bypass,
  insecure defaults) but entirely irrelevant for a recipe, fitness plan, essay, or
  business strategy. A jury agent evaluating three pasta recipe proposals would
  have no idea how to apply "security correctness" and would likely either skip it
  silently or apply it in a nonsensical way. Criterion 4 said "a developer can use
  this directly" — again, meaningless for culinary or creative domains.
- **What you'd see:** Jury agents evaluating non-tech proposals might produce
  inconsistent or confused scoring rationales, or the criterion would simply be
  ignored, reducing the value of the lexicographic ordering.
- **Why it happened:** The jury rubric was written for software engineering tasks
  and never updated to be domain-agnostic.
- **Fix:** Replaced criterion 3 with "Domain quality — appropriate for domain
  '{domain}'; no off-domain elements introduced" and criterion 4 with "Clarity +
  usability — can be directly used by the intended audience for this domain". The
  domain string is read from `_spec["domain"]` in the payload so the rubric
  adapts dynamically to whatever domain the run detected. A recipe run sees
  "domain 'culinary'"; a fitness run sees "domain 'fitness'".

---

### 52. Tech-only forbidden terms injected as noise into non-tech run prompts
- **File:** `raf/core/spec.py`
- **Concept:** `_DEFAULT_FORBIDDEN` contains 12 Web3/blockchain terms (blockchain,
  NFT, IPFS, Chainlink, ZK proof, etc.) that are placed on the Spec's forbidden
  list for every run via `_goal_relevant_forbidden()`. The forbidden list is then
  injected into every agent prompt as the "Frozen Spec — forbidden items" block.
- **Problem:** For a goal like "create a 3-day meal plan for a vegetarian athlete",
  the forbidden list would contain "blockchain, smart contract, IPFS, Chainlink,
  zero-knowledge, ZK proof, DID, verifiable credential, on-chain, NFT, token gating,
  Web3 wallet". These terms would never appear in a recipe output, so they wouldn't
  cause failures — but agents would see them in their context and potentially waste
  reasoning budget wondering why blockchain is forbidden from a meal plan. The
  forbidden block cluttered every prompt with irrelevant tech jargon.
- **What you'd see:** All agent prompts for non-tech goals would show a Frozen Spec
  block with a long list of blockchain-related forbidden items. The `spec_extracted`
  trace event would log all 12 terms as forbidden. No actual execution failures
  would occur, but token waste and prompt confusion were real.
- **Why it happened:** `_goal_relevant_forbidden()` only filtered items whose words
  appeared in the goal (e.g. removing "blockchain" if the user asked for a blockchain
  app). For non-tech goals, no blockchain words appear, so the full list survived the
  filter and was injected regardless of domain.
- **Fix:** Added a domain gate to `_goal_relevant_forbidden(root_goal, domain)`.
  When `domain != "technical"`, the function returns an empty list immediately —
  tech drift terms are simply irrelevant for non-tech domains. The existing goal-text
  filtering logic is preserved for `domain="technical"` runs. Domain is determined
  by `_detect_domain_from_goal()` (keyword pre-filter) and confirmed by the LLM
  spec_extract call.

---

### 53. SpecExtractor had no domain awareness — Spec was always tech-shaped
- **File:** `raf/core/spec.py`, `raf/llm/prompt_adapter.py`, `raf/schemas.py`
- **Concept:** The `SpecExtractor` makes one LLM call per run to extract
  `required`, `forbidden`, and `success_criteria` from the root goal. The extracted
  Spec is injected into every agent prompt for that run.
- **Problem:** The `spec_extract` prompt instructed the LLM with tech-only examples:
  "forbidden — HIGH-DRIFT PRIMITIVES ONLY: blockchain, smart contracts, IPFS,
  Chainlink, ZK proofs, NFTs..." This framing made the LLM think in tech terms even
  when the goal was culinary or fitness. The LLM had no way to classify the domain
  or extract domain-appropriate concreteness signals. The DECISIONS block suggested
  tech-only keys (backend_language, framework, db, cache) regardless of goal domain.
- **What you'd see:** A fitness run's DECISIONS block would suggest
  "backend_language, db, cache" as the keys for committing to design choices —
  confusing for agents planning workout schedules. The spec_extract prompt would
  frame forbidden detection around tech drift even for a recipe goal.
- **Fix:** Added `domain` and `concrete_indicators` to the `Spec` dataclass.
  `_detect_domain_from_goal()` runs a fast keyword pre-filter (no LLM) to guess
  the domain. `SpecExtractor.extract()` passes this as `domain_hint` to the
  spec_extract LLM call. The updated prompt asks the LLM to classify domain,
  extract 3-5 domain-specific concrete_indicators (phrases that signal actionable
  content in THIS domain), and provide domain-appropriate forbidden examples.
  Added `_DOMAIN_DECISION_KEYS` in prompt_adapter.py so DECISIONS block suggests
  keys matching the detected domain (culinary → cuisine_style, dietary_restriction;
  fitness → training_style, equipment; etc.). `RafConfig.domain` allows manual
  override. Zero extra API calls — all new fields piggyback on the existing
  spec_extract call.

---

## Session 11 — UI Polish, Domain Wiring, PDF Export

### 54. Domain field existed in RafConfig but was never reachable from the API
- **File:** `server/main.py`, `server/run_manager.py`
- **Concept:** `RafConfig.domain` was added in session 10 so users could manually override
  auto-detected domain. But `RunRequest` never declared the field, so the frontend had no way
  to pass it, and `_build_config()` never read it even if someone sent it manually.
- **Problem:** The domain override was dead code — it existed in RafConfig but no API
  caller could reach it.
- **What you'd see:** POST /api/run with `{"domain": "culinary"}` would silently ignore the
  field and always auto-detect domain, even when the user had set it explicitly.
- **Fix:** Added `domain: str | None = None` to `RunRequest`. In the run endpoint, if
  `request.domain is not None`, it is pushed into `config_overrides`. In `_build_config()`,
  the domain key is read and set on the config: `config.domain = domain`.

---

### 55. Demo view shared the same provider UI as Concepts — mock was not enforced
- **File:** `web/src/App.tsx`
- **Concept:** The "Demo (Hanoi)" tab is meant to showcase RAF without needing any API key.
  The mock adapter has a built-in Hanoi solver.
- **Problem:** Clicking the Demo tab only changed the view state — it did not force the
  provider to mock. If the user had previously selected Gemini or OpenRouter, the Hanoi run
  would attempt to use that provider, requiring an API key.
- **What you'd see:** Clicking "Run Hanoi" with a non-mock provider would error with
  "GEMINI_API_KEY is required" instead of running the deterministic mock.
- **Fix:** The Demo tab `onClick` now also calls `setProvider("mock"); setModel("")`. The
  `startHanoi()` function hard-codes `provider: "mock"` in its POST body regardless of
  current state. The provider/model selection row (Row 2) is hidden in Demo view, replaced
  with a "Using: Mock — demo mode runs without an API key" badge.

---

### 56. Provider and model dropdowns visible when multi-model was ON
- **File:** `web/src/App.tsx`
- **Concept:** When `multiModel=true`, each consortium and jury agent slot has its own
  provider/model picker. The top Row 2 (single provider + model dropdowns) becomes redundant.
- **Problem:** Both rows were visible at the same time — the single-provider dropdowns above
  and the per-slot pickers below. The single-provider row had no effect when multi-model was
  active, but it looked like it should, causing confusion about which settings would apply.
- **What you'd see:** Enabling "Use multiple models" would show per-slot controls while the
  top provider/model dropdowns remained visible.
- **Fix:** Row 2 is now wrapped in `{view === "concepts" && !multiModel && (...)}`. When
  multi-model is on OR when the Demo view is active, Row 2 is hidden entirely.

---

### 57. exportTrace() only downloaded raw JSON — no human-readable export existed
- **File:** `web/src/App.tsx`
- **Problem:** The only export was a JSON dump of the raw event array, which is useful for
  debugging but not for sharing or reviewing a run's decisions. There was no way to export
  the execution graph, the vote decisions, or a formatted trace.
- **Fix:** Added `exportPDF()` using jspdf + html2canvas. The exported PDF is multi-page
  landscape A4: (1) cover page with run ID, goal, detected domain, and timestamp; (2) graph
  page — html2canvas capture of the `.graph-scroll` div; (3) trace events page — all events
  as formatted text; (4) vote decisions page — per-agent votes with scores and reasons.
  The existing "Export" button was renamed "Export JSON"; "Export PDF" was added next to it.

---

### 58. microsoft/phi-4:free and qwen/qwen3-30b-a3b:free missing from _JSON_MODE_MODELS
- **File:** `raf/llm/openrouter_adapter.py`
- **Problem:** Both models were listed in the UI catalogue and in the docstring but were
  not in `_JSON_MODE_MODELS`, so `response_format: json_object` was never sent when using
  them. This meant JSON compliance fell back to prompt-only, making these models more
  likely to produce malformed JSON that requires repair.
- **Fix:** Added both to `_JSON_MODE_MODELS` in session 11.

---

## Session 11.5 — OpenRouter Capability Audit

Full live audit of all 11 catalogue models against OpenRouter model pages (March 2026).
Four bugs found and corrected.

### 59. openai/gpt-oss-120b:free wrongly in _JSON_MODE_MODELS
- **File:** `raf/llm/openrouter_adapter.py`
- **Problem:** The model's `supported_parameters` on OpenRouter does NOT include
  `response_format`. Sending `response_format: json_object` to this model via OpenRouter
  either silently ignores it or raises an API error. The model is reasoning-only: its
  supported parameters are `reasoning, include_reasoning, temperature, max_tokens, stop, seed`.
- **What you'd see:** Runs using gpt-oss-120b could return unexpected API errors or the
  response_format flag would be silently dropped, giving no guarantee of JSON compliance.
- **Fix:** Removed from `_JSON_MODE_MODELS`. It remains in `_REASONING_MODELS` (correctly).

---

### 60. meta-llama/llama-3.3-70b-instruct:free wrongly in _JSON_MODE_MODELS
- **File:** `raf/llm/openrouter_adapter.py`
- **Problem:** OpenRouter API shows `supported_parameters` for this model as
  `temperature, max_tokens, stop, seed, tools, tool_choice` — no `response_format`.
  `supports_reasoning` is explicitly false. The model has no JSON mode and no reasoning.
- **What you'd see:** Sending `response_format: json_object` to this model would likely
  be silently ignored. JSON compliance relied on the flag working, so responses could be
  inconsistently formatted.
- **Fix:** Removed from `_JSON_MODE_MODELS`. Falls back to prompt-only JSON compliance
  (json_utils repair handles malformed responses).

---

### 61. arcee-ai/trinity-large-preview:free wrongly in _REASONING_MODELS
- **File:** `raf/llm/openrouter_adapter.py`
- **Problem:** OpenRouter API reports `supports_reasoning: false` for this model. Sending
  `extra_body: {"reasoning": {"enabled": True}}` would either be ignored or cause errors.
  The model is a creative writing / roleplay model, not a reasoning model.
- **What you'd see:** The reasoning extension header was sent on every call to this model
  with no benefit and potential API errors.
- **Fix:** Removed from `_REASONING_MODELS`.

---

### 62. arcee-ai/trinity-large-preview:free missing from _JSON_MODE_MODELS
- **File:** `raf/llm/openrouter_adapter.py`
- **Problem:** The same audit confirmed `response_format` IS in this model's
  `supported_parameters` list (along with `structured_outputs`). It was never added to
  `_JSON_MODE_MODELS`, so JSON mode was never enabled for it.
- **Fix:** Added to `_JSON_MODE_MODELS`.

---

### 63. qwen/qwen3-30b-a3b:free missing from _REASONING_MODELS
- **File:** `raf/llm/openrouter_adapter.py`
- **Problem:** OpenRouter API confirms `supports_reasoning: true` for this model. It has
  a "thinking mode" that uses reasoning tokens before generating the final answer. The model
  was added to `_JSON_MODE_MODELS` in session 11 (JSON support unconfirmed but plausible)
  but was never added to `_REASONING_MODELS`.
- **What you'd see:** Qwen3-30B would not receive the reasoning extension header, so it
  would respond in non-thinking mode only — losing its main capability advantage.
- **Fix:** Added to `_REASONING_MODELS`.

---

## Phase Assessment — Gemini 2.5 Pro Hanoi Run Analysis

The following are documented observations and next priorities from a real Gemini 2.5 Pro run
on the Hanoi demo. These are NOT yet fixed — they define the next development phase.

### 64. Spec correct but too weak to steer execution style
- **Observed:** The extracted Spec correctly captured the Hanoi goal, 15-move count, peg
  roles, and legality constraints. But it did not prevent nodes from choosing "enterprise"
  execution styles — audit trails, transaction logs, verification protocols.
- **Root cause:** `required` and `forbidden` constrain content but not method. Nothing
  prevents an agent from wrapping a disk move in a distributed transaction protocol.
- **Next step (P7):** Add `task_class` field to Spec ("deterministic", "creative",
  "analytical") and a `disallow_meta_protocols` flag. Deterministic tasks with this flag
  would have prompts that explicitly forbid style invention.

### 65. Recursive decomposition on atomic deterministic steps
- **Observed:** Depth-2 nodes turned a HANOI(1) step (one disk move) into AUDIT +
  TRANSACT + VERIFY children. Those then decomposed further into source validation,
  destination validation, and report compilation.
- **Root cause:** The mode_decision prompt gives no guidance about when NOT to recurse.
  A single disk move has one atomic action — no decomposition is needed or useful.
- **Next step (P4):** Add heuristic to mode_decision: if goal length < ~12 words and
  contains no conjunction ("and", "then", "also", "while"), strongly bias toward base.
  Add explicit examples to the prompt showing that a single state transition = base.

### 66. SpecLedger locking implementation style decisions
- **Observed:** At depth 4, nodes locked decisions including `approach: pessimistic-locking`,
  `style: fault-tolerant`, `format: procedural-mandate`, `format: json_rpc_style`,
  `state_integrity: holographic_hashing`, `verification_model: event_sourcing_audit`.
  Once locked, these caused candidate rejections in sibling nodes that didn't use the
  same style.
- **Root cause:** `_lock_decisions()` accepts any key the LLM provides in the DECISIONS
  block. There is no filter on what constitutes a meaningful decision vs. stylistic fluff.
- **Next step (P2):** Add a Ledger key allowlist. Only lock keys matching a canonical
  format (e.g. `category.subtype` like `stack.backend`, `execution.mode`). Keys that are
  single bare words, contain adjectives, or don't match the format are logged but not
  committed to the Ledger.

### 67. System inventing distributed systems machinery for deterministic puzzles
- **Observed:** The Hanoi trace contained: pessimistic locking, event sourcing audit,
  read-after-write checksum, holographic hashing, distributed lock manager, write-ahead log.
- **Root cause:** The framework rewards "robust-sounding" outputs because the jury
  scoring rubric rewards completeness and security correctness. A verbose distributed
  protocol scores higher than a simple move list, even for a toy puzzle.
- **Next step (P3):** Expand `_VALIDATOR_CHILD_RE` to filter children whose goals contain
  words like "audit", "verify", "validate", "check", "report", "log", "confirm" when they
  appear as the primary verb. These should only be allowed if the root goal explicitly
  requested verification.

### 68. Validator children bypassing the existing filter
- **Observed:** Children named "source peg validation", "destination peg validation",
  "validation report compilation" appeared in the tree despite `_VALIDATOR_CHILD_RE`.
- **Root cause:** The regex only matches exact phrases like "validate the above" or
  "quality check". Variations with different verb forms or domain-specific language
  (e.g. "peg validation") slip through.
- **Next step (P3):** Broaden the regex to match the pattern at the word level (e.g.
  any goal starting with or containing "audit", "verify", "validate", "confirm", "check"
  as the primary action verb).

### 69. Referee progress score masking incomplete goal completion
- **Observed:** Referee reports showed `progress: 0.5`, `covered: ["execution_valid"]`,
  `missing: ["goal_not_reached"]`. Nodes that were locally valid but hadn't completed
  the subgoal still reported as 50% done, which is indistinguishable from halfway through
  a long task.
- **Root cause:** The referee returns a single float `progress` that conflates local
  structural validity with actual goal completion.
- **Next step (P6):** Split referee verdict into two independent booleans:
  `locally_valid` (structure is sound) and `goal_completed` (the subgoal is actually
  done). The repair loop should only trigger when `goal_completed=false`, not on
  `locally_valid=false`.

### 70. No deterministic fast path — algorithmic tasks run full RAF overhead
- **Observed:** Every HANOI(n) subgoal went through consortium proposals + jury voting +
  repair loop at each depth level. For a mathematically-defined puzzle with an exact
  solution, this is pure overhead.
- **Root cause:** RAF has no concept of "this task has a provable solution I can compute
  directly." Everything routes through the full multi-agent pipeline.
- **Next step (P1, highest ROI):** Add a pre-mode-decision router that checks if the
  goal matches known algorithmic patterns (Hanoi format, sorting, arithmetic, etc.) and
  if so, calls a deterministic solver directly, bypassing consortium and jury entirely.
  For Hanoi specifically, the mock adapter already has this solver — it just never fires
  for real LLM providers.

---

## Session 12 — Phase 2 General Improvements (2026-03-08)

### 71. _DOMAIN_DECISION_KEYS used free-form keys inconsistent with ledger format
- **Observed:** Suggested keys like `backend_language`, `cuisine_style`, `training_style` were
  single-component and did not match any canonical format, making it impossible for the
  ledger allowlist to accept them.
- **Root cause:** Keys were defined before the `category.subtype` dot-notation standard.
- **Fix applied:** All 7 domain key sets updated to dot-notation format (e.g. `lang.backend`,
  `cuisine.style`, `training.style`). Agent prompt updated to instruct dot-notation explicitly.

### 72. _VALIDATOR_CHILD_RE didn't catch noun-form validator goals (P3)
- **Observed:** "source peg validation", "audit report", "confirm that state is correct" all
  slipped through the existing regex.
- **Fix applied (session 12):** Added 4 new branches to `_VALIDATOR_CHILD_RE` in `node.py`:
  `\b\w+\s+(validation|verification)\b`, `\baudit\s+(report|trail|log|summary)\b`,
  `\bconfirm\s+(that|whether|the|all|each)\b`, `\binspect\s+(the|all|each|every)\b`.

### 73. Mode decision prompt said "Default to 'recursive'" (P4)
- **Observed:** Root cause of over-decomposition — every node including atomic leaf tasks
  went recursive because the prompt explicitly instructed that default.
- **Fix applied (session 12):** Removed "Default to 'recursive'" from `mode_decision`
  prompt in `prompt_adapter.py`. Replaced with "Default to 'base' unless goal CLEARLY
  contains multiple independent sub-goals." Added short-goal guidance (<15 words, no
  conjunctions = almost always base).

### 74. No atomicity pre-check before Consortium+Jury in _decide_mode() (P4)
- **Observed:** Goals of ≤12 words with no conjunction still triggered full multi-agent
  mode decision round-trip — wasting 3+3 API calls on trivially atomic tasks.
- **Fix applied (session 12):** Added deterministic atomicity pre-check in `_decide_mode()`
  before Consortium call. Fires for goals ≤12 words, no conjunction words, not a question.
  Emits `mode_decided` trace event with `fast_path=True`.

### 75. No fast path in RafNode.run() — even trivial goals triggered _decide_mode() (P1)
- **Observed:** Goals ≤10 words still ran through the full mode-decision machinery.
- **Fix applied (session 12):** Added `_is_atomic_goal()` method and fast-path branch
  at the top of `RafNode.run()`. Goals ≤10 words with no conjunction and no question mark
  skip `_decide_mode()` entirely and call `_execute_base()` directly.

### 76. Ledger accepted any key the LLM invented (P2)
- **Observed:** Keys like `holographic_hashing`, `fault-tolerant`, `state_integrity` got
  locked into the ledger, polluting it and causing legitimate proposals to be rejected.
- **Fix applied (session 12):** Added `_LEDGER_KEY_RE` allowlist regex in `node.py`.
  `_lock_decisions()` now skips keys that don't match `^[a-z][a-z0-9_]{1,30}\.[a-z][a-z0-9_]{1,30}$`.
  Skipped keys emit a `decisions_key_skipped` trace event.

### 77. Consortium ran at full size even at depth 2+ (P5)
- **Observed:** 3-agent Consortium + 3-agent Jury at depth 3 leaf nodes — 6 API calls
  for trivial sub-tasks that don't need multi-agent deliberation.
- **Fix applied (session 12):** Added `_adapters_for_depth()` helper. Scales adapter
  list to full size at depth 0, max(2, size-1) at depth 1, and 1 adapter at depth 2+.
  When size=1 the unanimous check auto-skips the jury. Applied to all 6 Consortium calls.

### 78. _analyze() returned one `approved` bool — no local vs global distinction (P6)
- **Observed:** A node that correctly moved one disk (locally valid) was marked `approved=false`
  because it hadn't solved the full Hanoi puzzle (goal not completed). Indistinguishable
  from a structurally wrong output.
- **Fix applied (session 12):** Added `locally_valid` and `goal_completed` fields to
  `validate_analysis_result` in `schemas.py`. Updated analysis schema string in
  `prompt_adapter.py`. Both fields now appear in node result metadata. Analysis prompt
  includes definitions and an example to guide correct agent responses.

### 79. No task_class in Spec — validator child filter couldn't distinguish coordinator tasks (P7)
- **Observed:** A `coordinate` or `analyze` root goal had its legitimate audit/review
  children filtered out by `_VALIDATOR_CHILD_RE`, breaking the plan.
- **Fix applied (session 12):** Added `task_class` field to `Spec` dataclass in `spec.py`.
  SpecExtractor now extracts it (one of: implement/coordinate/analyze/create/transform/general).
  Added to `validate_spec_extract` in `schemas.py`. `_plan_children()` now bypasses
  `_VALIDATOR_CHILD_RE` when `task_class in {"coordinate", "analyze"}`. Injected into
  Frozen Spec block in every agent prompt via `_spec_context()`.

### 80. No prompt version in traces — couldn't attribute improvement to prompt vs. model (item 8 / session 12c)
- **Observed:** After each session, improvements in output quality couldn't be attributed
  to prompt changes vs. model changes vs. routing changes — all had the same trace format.
- **Fix applied (session 12c):** Added `_PROMPT_VERSION = "12.2"` constant to `prompt_adapter.py`.
  Added `run_started` trace event at `RafEngine.run()` start containing: `prompt_version`,
  `schema_version`, full config snapshot, and adapter counts. Added `prompt_version` and
  `task_class` to `spec_extracted` event. Every trace is now self-describing.

### 81. task_class was metadata only — every class still ran the full Consortium+Jury pipeline (item 2 / session 12c)
- **Observed:** `task_class="transform"` (e.g. "summarize this text") ran a full
  Consortium→Jury mode decision, proposing and voting on base vs. recursive, adding
  2–3 unnecessary API calls before reaching the obvious answer (base case).
- **Fix applied (session 12c):** Added `_TASK_CLASS_POLICY` dict and `_execution_policy()`
  method to `RafNode`. `transform` → `SINGLE_PASS` skips `_decide_mode()` entirely and goes
  straight to `_execute_base()`. Emits `mode_decided` with `fast_path=True`,
  `reason="single_pass_policy"`. Other classes remain `FULL_RAF`. Applied after atomic fast path
  in `RafNode.run()` so all fast-exit paths are in one place.

### 82. Merge output was an opaque text blob — no attribution, no conflict surfacing (item 12 / session 12c)
- **Observed:** After a multi-child merge, the output was a single string. There was no
  way to know which child contributed which section, or which contradictions the merger
  had resolved (or failed to resolve).
- **Fix applied (session 12c):** Added `validate_merge_result` to `schemas.py` with three new
  optional fields: `sections` (list of {title, content, source_child_ids}), `unresolved_conflicts`
  (list of conflict descriptions), `decisions` (same as base_execute ledger). Updated merge
  Consortium call in `node.py` to use `validate_merge_result`. `child_outputs` now passes
  `{"child_id": cid, "output": str}` dicts instead of raw strings, enabling merger to attribute
  sections to specific children. Added `merge_attribution` and `merge_conflicts_detected` trace events.
  Updated merger role framing and merge schema string in `prompt_adapter.py`.

### 83. No token budget — runaway recursion could exhaust API quota silently (F1 / session 13)
- **Observed:** A misconfigured run with high max_depth could spawn 50+ nodes, each making
  3 consortium + 3 jury calls, consuming tens of thousands of tokens with no stopping criterion
  other than `max_nodes_total`.  API quota exhaustion manifested as late-run errors.
- **Fix applied (session 13):** Added `token_budget: Optional[int] = None` to `RafConfig`.
  Added `_usage_callback` to `ModelAdapter` base class. `RafEngine._wire_usage_callbacks()`
  sets `engine.record_tokens` as the callback on every unique adapter object in `__init__`.
  `GeminiAdapter` and `OpenRouterAdapter` report actual token counts from API response metadata;
  `MockAdapter` wraps `_call_raw_inner` to estimate from string length.  `_check_cancelled()`
  now also checks `_tokens_used >= config.token_budget` and emits `token_budget_exceeded`
  trace event before raising.  `tokens_used` and `nodes_used` injected into run result metadata.
  Token budget included in `run_started` config snapshot for self-describing traces.

### 84. Long child outputs injected verbatim into merge/dep prompts — token blowout risk (F4 / session 13)
- **Observed:** A 10-child plan where each child produced a 2000-char output would inject
  ~20k chars into the merge Consortium prompt before the merge instructions even begin.
  Similarly, a child depending on a large sibling output received a 500-char raw truncation
  that might cut off mid-sentence, losing meaning rather than preserving it.
- **Fix applied (session 13):** Added `_compress_output(result, max_chars=800)` static method
  to `RafNode`.  When `output` exceeds `max_chars`, it returns a structured `[Summary]` prefix
  followed by `key_points` joined by ` | ` — no extra API call (key_points are already
  generated by each executing agent).  Falls back to truncation with `…` if key_points absent.
  Applied to `child_outputs` in merge payload (800-char threshold) and to `dep_context`
  injection in `run_child()` (500-char threshold, replacing the raw `[:500]` slice).

### 85. Repair loop produced validator-shaped outputs rather than goal-shaped additions (F12 / session 13)
- **Observed:** When spec_validate returned abstract missing items like "ensure correctness"
  or "address all edge cases", the repair agent focused on those phrases and produced
  meta-commentary ("I have now ensured correctness by...") rather than concrete additions.
- **Fix applied (session 13):** Repair feedback capped to top 3 missing items, joined to
  ≤200 chars total. Renamed "Original goal:" to "PRIMARY OBJECTIVE (never deviate from this):"
  as the very first line of the repair goal. Added rule: "The PRIMARY OBJECTIVE above is the
  source of truth — not the missing list." Violations capped to top 3. All in `_spec_repair_loop()`.

### 86. Identical sub-goals re-executed on every occurrence in recursive tasks (F2 / session 13)
- **Observed:** In Hanoi(3) and other divide-and-conquer tasks, the same atomic goal
  (e.g. "move disk 1 from A to C") could appear multiple times in the execution tree.
  Each occurrence ran the full Consortium+Jury pipeline, wasting API calls and tokens.
- **Fix applied (session 13):** Added `_goal_cache: Dict[str, Dict]` + `_cache_lock` to
  `RafEngine.__init__`; reset at each `run()` call for clean per-run semantics. Added
  `_cache_key()` to `RafNode` (16-hex SHA-256 of goal + sorted spec.required + sorted ledger
  snapshot — different ledger states get separate slots). Added `_cache_write(result)` helper
  (skips root/depth=0, skips empty output, skips clarify mode; first writer wins via setdefault).
  Cache check at top of `run()` (after `node_created`) emits `cache_hit` + `node_done` trace
  events and returns immediately.

---

## Future Planning Backlog — External Assessment (2026-03-08)

15 gaps identified from an external architectural review. Status column shows
whether the issue is already addressed, partially addressed, or genuinely missing.

| # | Area | Status | Priority |
|---|------|--------|----------|
| 1a | Token/cost budget tracking per run | **Done** (session 13, token_budget in RafConfig, record_tokens callback, _check_cancelled enforcement) | — |
| 1b | Cost budget per provider/model | **Missing** (token_budget done; per-provider USD cost requires pricing table — future work) | Medium |
| 1c | Early stopping when confidence already high | Partial (unanimous shortcut exists) | Medium |
| 1d | Adaptive consortium size | **Done** (session 12, _adapters_for_depth) | — |
| 1e | Adaptive jury size | **Done** (unanimous skip already in place) | — |
| 1f | Cache / memoize identical subproblems | **Done** (session 13, _goal_cache on RafEngine, _cache_key/_cache_write on RafNode) | — |
| 2  | Task router with per-class execution policy | **Done** (session 12c, _execution_policy + _TASK_CLASS_POLICY; transform→SINGLE_PASS) | — |
| 3  | State compression / rolling context summary | **Done** (session 13, _compress_output + key_points summaries in merge and dep_context) | — |
| 4  | Semantic contradiction detection at merge | **Missing** | Medium |
| 5  | Formal evaluation metrics + benchmark suite | **Missing** | Medium |
| 6  | Prompt feedback loop anchoring (repair) | **Done** (session 13, top-3 cap + 200-char limit + PRIMARY OBJECTIVE label) | — |
| 7  | Plan quality pre-scorer before child launch | **Missing** | Medium |
| 8  | Per-node observability (tokens, cost, prompt version) | Partial (prompt_version + run_started event done; per-node token counts still missing) | Low-Med |
| 9  | Provider reliability metadata / model-role matching | **Missing** | Low |
| 10 | Sandbox security (container isolation, allowlist) | Partial (deny-list exists; no container) | Future |
| 11 | Cross-run learning / plan template library | **Missing** | Future |
| 12 | Structured merge with source attribution | **Done** (session 12c, validate_merge_result + merge_attribution + merge_conflicts_detected trace events) | — |
| 13 | Anti-overengineering in jury + prompts | **Done** (session 12, this batch) | — |
| 14 | Hierarchical confidence (understand/plan/output/fact) | **Missing** | Low-Med |
| 15 | Smarter human-in-the-loop triggers | Partial (plan approval only) | Low-Med |

---

### Detailed notes on each missing item

#### F1. Token/cost budget tracking (item 1a–b)
- **RESOLVED (session 13):** `token_budget: Optional[int]` added to `RafConfig`. `ModelAdapter`
  has `_usage_callback`; all adapters call `_report_usage(tokens_in, tokens_out)` after each call.
  Gemini and OpenRouter use actual API token counts; Mock estimates from string length.
  `RafEngine._wire_usage_callbacks()` wires all unique adapters at init time. `_check_cancelled()`
  enforces `token_budget` and emits `token_budget_exceeded` event. `tokens_used` and
  `nodes_used` added to run result metadata.
- **Remaining gap:** Per-provider USD cost tracking (`cost_budget_usd`) requires model-specific
  pricing tables — future work.

#### F2. Memoization of repeated sub-goals (item 1f)
- **RESOLVED (session 13):** `_goal_cache: Dict[str, Dict]` + `_cache_lock` added to
  `RafEngine`. Cache reset at each `run()` call. `_cache_key()` hashes `(goal, sorted
  spec.required, sorted ledger.locked())` — 16-hex SHA-256 prefix. `_cache_write(result)`
  writes only for depth>0, non-empty, non-clarify results; first writer wins (setdefault).
  Cache check at top of `RafNode.run()` (after node_created, before clarify) emits
  `cache_hit` + `node_done` trace events and returns immediately without any API calls.

#### F3. Task router with execution policy per class (item 2)
- **RESOLVED (session 12c):** `_execution_policy()` + `_TASK_CLASS_POLICY` added to `RafNode`.
  `transform` → `SINGLE_PASS` (skips `_decide_mode()`, goes directly to `_execute_base()`).
  All other classes → `FULL_RAF`. Applied before `_decide_mode()` in `RafNode.run()`, after
  atomic fast path. Emits `mode_decided` with `fast_path=True, reason="single_pass_policy"`.
- **Remaining gap:** Only two policies implemented (SINGLE_PASS / FULL_RAF). A true
  `DETERMINISTIC` policy (skip LLM entirely, run code/algorithm) is still future work.

#### F4. State compression / rolling context (item 3)
- **RESOLVED (session 13):** Added `_compress_output(result, max_chars=800)` static method
  to `RafNode`. When output exceeds `max_chars`, uses pre-generated `key_points` as a
  structured `[Summary] point1 | point2 | …` — zero extra API calls. Applied to both:
  (a) `child_outputs` in merge payload (800-char threshold), and
  (b) `dep_context` in `run_child()` (500-char threshold, replaces raw `[:500]` slice).
- **Remaining gap:** Ancestor goal chain itself is not compressed (goals are short strings,
  so this is low priority). Per-node rolling context summary (F8) is still future work.

#### F5. Semantic contradiction detection at merge (item 4)
- **Gap:** Ledger catches explicit key contradictions, but a child that says
  "stateless architecture with no DB" and a sibling that says "PostgreSQL for state"
  will both pass the ledger and produce a contradictory merged output.
- **Next step:** At merge time, before Consortium call, run a lightweight single-agent
  contradiction scan: "List any explicit contradictions between these child outputs."
  If contradictions found, inject them as a "RESOLVE THESE CONTRADICTIONS" block
  into the merge payload.

#### F6. Formal evaluation metrics + benchmark suite (item 5)
- **Gap:** No way to know if RAF is better than a single-model baseline. No metrics.
- **Next step:** Create `raf/eval/` module with:
  - Standard tasks: Hanoi(n), summarization, code generation, planning
  - Metrics: task_success_rate, cost_per_success, latency, recursion_depth_used,
    repair_rate, agreement_rate, validator_correction_rate
  - Baseline comparators: one-shot, single-model+repair, planner-executor

#### F7. Plan quality pre-scorer (item 7)
- **Gap:** After Consortium+Jury selects a plan, it launches children immediately.
  There is no check for: are children atomic enough? overlapping? affordable?
- **Next step:** Add `_score_plan(plan, budget_remaining) -> float` before child
  launch in `_execute_recursive()`. Score based on: avg child goal word count,
  overlap between child goals (cosine or word-overlap), meta-children remaining,
  budget coverage. Reject plans below threshold and re-plan up to 1 time.

#### F8. Per-node observability (item 8)
- **Gap:** Trace events have node_id, goal, output but no token counts, no cost,
  no which prompt version was used, no which validator triggered a repair.
- **Next step:** Add `tokens_in`, `tokens_out`, `cost_usd`, `prompt_version` fields
  to trace events emitted by adapters. Add `triggered_by` to repair/retry events.
  Show per-node cost in the web UI node inspector panel.

#### F9. Provider reliability metadata (item 9)
- **Gap:** All adapters are interchangeable. A cheap proposer and a reliable judge
  should use different models, but users have to configure this manually.
- **Next step:** Add an optional `adapter_metadata` dict per adapter with:
  `json_reliability`, `reasoning_strength`, `latency_tier`, `cost_tier`.
  Use metadata to auto-assign roles: lowest-cost for consortium proposers,
  highest-reliability for jury voters, fastest for repair attempts.

#### F10. Structured merge with source attribution (item 12)
- **RESOLVED (session 12c):** `validate_merge_result` added to `schemas.py` with `sections`
  (list of {title, content, source_child_ids}), `unresolved_conflicts`, and `decisions`.
  `child_outputs` now passes `{"child_id": cid, "output": str}` so merger can attribute
  sections. `merge_attribution` and `merge_conflicts_detected` trace events emitted.
  Merger role framing updated in `prompt_adapter.py` to explain the contract.

#### F11. Hierarchical confidence (item 14)
- **Gap:** One `confidence` float on each result conflates: did I understand the goal?
  is my plan minimal? is my output correct? is the merged result coherent?
- **Next step:** Add `confidence_breakdown: {"understanding", "plan", "output", "coherence"}`
  as an optional field in `validate_base_execution_result` and `validate_analysis_result`.
  Use breakdown to diagnose where failures come from (misunderstood goal vs. bad execution).

#### F12. Repair prompt feedback loop protection (item 6)
- **RESOLVED (session 13):** Repair feedback capped to top 3 missing items + 200-char total
  limit. "PRIMARY OBJECTIVE (never deviate from this):" now appears as the first line of
  every repair goal. Added rule: "The PRIMARY OBJECTIVE above is the source of truth — not
  the missing list." Violations also capped to top 3. All in `_spec_repair_loop()` in `node.py`.

---

## Session 14 — Code review fixes

### 1. Debug artifacts committed to git
- **Files:** `mode_decision.txt`, `run_output.json`, `raf/run_output.json`
- **Problem:** Raw LLM debug dumps were tracked in git (mode_decision.txt was 8,555 lines).
  No `.gitignore` entries existed for these patterns, so they silently accumulated.
- **What you'd see:** `git diff` against main showed 8,555-line file addition; binary blob in repo.
- **Fix:** `git rm --cached` on all three files; added entries to `.gitignore` under
  `# Debug / run artifacts (never commit these)`.

### 2. Hand-rolled `.env` parser replaced with python-dotenv
- **File:** `server/main.py`, `server/requirements.txt`
- **Problem:** The custom line-by-line parser didn't handle multiline values, `export KEY=value`,
  values containing `#`, or Windows CRLF line endings — any of which can silently drop an API key.
- **What you'd see:** API key with a `#` comment character in the value would be truncated;
  CRLF `.env` files on Windows would fail to parse; `export GEMINI_API_KEY=...` style (common in
  shell profiles) would be silently skipped.
- **Fix:** `server/main.py` now tries `from dotenv import load_dotenv` first. On success, calls
  `load_dotenv(path, override=False)` for each `.env` file (first value wins). Falls back to the
  old parser with an inline comment listing its limitations. `python-dotenv>=1.0.0` added to
  `server/requirements.txt`.

### 3. No authentication warning on API server
- **File:** `server/main.py`
- **Problem:** `POST /api/run` starts LLM runs with no API key, no rate limiting, and
  `allow_origins=["*"]`. Exposing port 8001 on a shared network is an open spend endpoint.
- **Fix:** Added a prominent `⚠ LOCAL DEV ONLY` block comment at the top of `server/main.py`
  explaining the risk. Added the same warning to README.md Step 4.

### 4. `_VALIDATOR_CHILD_RE` false positives on legitimate child goals
- **File:** `raf/core/node.py`
- **Concept:** The regex filters meta-validator children from plans ("validate the above output",
  "quality check") since they produce no artifact and waste budget.
- **Problem:** The pattern `\b\w+\s+(validation|verification)\b` was too broad — it blocked
  `"input validation middleware"`, `"token verification service"`, `"email validation layer"` which
  are all legitimate deliverable artifacts, not meta-checks.
- **What you'd see:** Plans containing reasonable children like "JWT token verification service"
  would have those children silently stripped, resulting in incomplete plans.
- **Fix:** Narrowed to `\b(output|result|plan|above|previous)\s+(validation|verification)\b` —
  only blocks checks explicitly targeting *another node's output*, not artifacts in their own right.

### 5. Repair loop budget race — unhandled RuntimeError from create_node()
- **File:** `raf/core/node.py`, `_spec_repair_loop()`
- **Concept:** Before spawning a repair node, the loop checks `remaining_nodes() < 2`.
  If budget is sufficient, it calls `create_node()` which also checks the budget.
- **Problem:** Two parallel sibling nodes could both pass the `remaining_nodes() < 2` check
  simultaneously (check-then-act race), then both call `create_node()`. The second call would
  raise `RuntimeError("Max nodes limit reached")` which was unhandled — crashing the repair loop
  and propagating up as an unexpected exception.
- **What you'd see:** Near-budget-limit runs with parallel children would occasionally crash with
  a RuntimeError from inside `_spec_repair_loop`, losing the node's output entirely.
- **Fix:** Wrapped the `create_node()` call in `try/except RuntimeError` — on budget exhaustion,
  breaks out of the repair loop gracefully and proceeds to final validation emit.
 
---

## Session 15 - Runtime performance and observability

### 1. Long RAF runs are opaque because model calls have no timing events
- **Files:** `raf/agents/consortium.py`, `raf/agents/jury.py`, `raf/llm/json_utils.py`,
  `raf/core/trace.py`, `web/src/App.tsx`
- **Observed trace:** `raf-trace-27e065be-9b81-4be2-b07b-dbad3a24a2ed.json`
- **Problem:** A Gemini run took about 130 minutes end-to-end. The trace showed RAF was
  structurally working (planning, voting, recursive child nodes, merge, referee/spec checks),
  but the UI could only infer slowness from large gaps between events. There were no
  first-class `model_call_start` / `model_call_done` / duration events to show exactly which
  task, model, node, or role was waiting.
- **What you'd see:** The run remains `running` for many minutes at a time with no obvious
  explanation. Users cannot tell whether RAF is stuck, waiting on Gemini/OpenRouter, retrying
  JSON repair, refining child context, voting, or validating.
- **Why it happened:** Model calls are hidden inside Consortium/Jury/JSON repair execution.
  Trace events are emitted around RAF phases, but not around every provider call. Large waits
  therefore appear as silent gaps.
- **Status:** Backend timing events have now been added for consortium and jury calls.
  The UI should use real traces to confirm the exact display before adding richer active-call
  summaries.
- **Next step:** Keep timing events visible in the frontend and then add the remaining timeout/fallback events:
  - `model_call_start`
  - `model_call_done`
  - `model_call_failed`
  - `model_call_timeout`
  - `model_call_fallback`
- **Event fields needed:** `node_id`, `task`, `role`, `provider`, `model`, `agent_index`,
  `attempt`, `duration_ms`, `timeout_ms`, `fallback_used`, `error`.
- **UI follow-up:** Show these in a Run Health / Checks area with slowest calls, active call,
  last event age, partial failures, and mid-run export status.

### 2. No per-task timeout/fallback policy for slow or hung model calls
- **Files:** `raf/agents/consortium.py`, `raf/agents/jury.py`, `server/run_manager.py`,
  `raf/schemas.py`
- **Problem:** A single slow model call can make the whole RAF run feel frozen for several
  minutes. The trace had multiple event gaps in the 4-7 minute range. Without task-level
  timeouts, a slow call can dominate total runtime even if the rest of the graph is healthy.
- **What you'd see:** `refine_context`, `plan`, `base_execute`, `merge`, or `analysis` appears
  to do nothing for minutes. If it eventually fails, the user only sees a later `child_failed`
  or consortium failure, not the timeout cause.
- **Why it happened:** ThreadPoolExecutor waits for futures, and provider adapters do not have
  a consistent RAF-level timeout/fallback contract. Python threads also cannot be safely killed
  once a provider call is running.
- **Next step:** After timing events exist, add per-task timeout limits and fallback behavior.
  Suggested defaults:
  - `mode_decision`: 60s
  - `plan`: 120s
  - `refine_context`: 60s
  - `base_execute`: 120s
  - `jury vote`: 60s
  - `merge`: 180s
  - `analysis`: 90s
- **Implementation note:** Use `future.result(timeout=...)`; on timeout, emit
  `model_call_timeout`, stop waiting for that result, and continue with partial results if
  enough valid responses exist. Do not pretend the underlying thread was killed.
- **Fallback plan:** Add config for `enable_fallback`, `fallback_provider`, `fallback_model`,
  `timeout_by_task`, and `max_retries_per_task`. Faster model routing should come after timing
  and timeout observability, not before.

### 3. Physics tuner is still unreliable and too blocking as an overlay
- **File:** `web/src/components/PhysicsPanel.tsx`
- **Problem:** The physics tuner may not open consistently, and its drag/click behavior can
  still feel unreliable. When expanded, it can block too much of the graph instead of feeling
  like a lightweight graph overlay.
- **What you'd see:** User clicks or drags near the tuner and it may not open/close as expected,
  or the expanded panel covers graph context while tuning physics.
- **Next step:** Keep a small always-visible Physics handle, make open/close reliable, separate
  panel dragging from slider dragging, and use a transparent/frosted expanded panel so the graph
  remains visible behind it.
