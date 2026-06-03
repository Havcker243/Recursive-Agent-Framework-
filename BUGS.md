# RAF Bug & Error Log

Format: date | category | description | cause | fix | status

---

## 2026-06-02

### BUG-001 — OpenRouter 401 "User not found"
- **Category:** LLM API / Credentials
- **Reported:** User getting `Error code: 401 - {'error': {'message': 'User not found.', 'code': 401}}`
- **Cause:** OpenRouter API key in `.env` was deleted or invalidated on OpenRouter's side
- **Fix:** Regenerate key at openrouter.ai/keys and update `OPENROUTER_API_KEY` in `.env`
- **Status:** Open (user-side, key needs regenerating)

---

### BUG-002 — All adapters hang forever after laptop sleep / network drop
- **Category:** LLM Adapters / Reliability
- **Affected:** `openrouter_adapter.py`, `claude_adapter.py`, `gemini_adapter.py`, `groq_adapter.py`, `deepseek_adapter.py`
- **Cause:** No `timeout` set on LLM API calls. When TCP connection dies during sleep, the call blocks indefinitely — the run appears frozen and the queue never receives new events.
- **Fix:** Added `timeout=120` to all OpenAI-compatible adapters; `http_options=types.HttpOptions(timeout=120_000)` to Gemini adapter
- **Status:** Fixed

---

### BUG-003 — Groq, DeepSeek, HuggingFace, Claude adapters not tracking token usage
- **Category:** LLM Adapters / Token Budget
- **Affected:** `groq_adapter.py`, `deepseek_adapter.py`, `huggingface_adapter.py`, `claude_adapter.py`
- **Cause:** `_report_usage()` never called after API response — token budget counter in the engine received no data
- **Fix:** Added `_report_usage(tokens_in, tokens_out)` call in all four adapters using actual usage metadata from the API response, with char-length fallback
- **Status:** Fixed

---

### BUG-004 — Claude, Gemini, Groq, DeepSeek, HuggingFace adapters silently fell back to Mock
- **Category:** Backend / Adapter Routing
- **Cause:** `_build_adapter()` in `run_manager.py` only handled `"openrouter"` and `"mock"`. All other provider names fell through to `MockAdapter()` with no warning — a user selecting "gemini" or "claude" would get mock responses without knowing it.
- **Fix:** Added all six providers to `_build_adapter()` with proper key resolution (env var + user-supplied key fallback) and clear error messages when keys are missing
- **Status:** Fixed

---

### BUG-005 — Adapters not shown in frontend model picker
- **Category:** Frontend / UI
- **Cause:** `list_models()` in `run_manager.py` only returned `"openrouter"` and `"mock"` — the other five providers were never sent to the frontend
- **Fix:** Added Claude, Gemini, Groq, DeepSeek, HuggingFace to `all_models` in `list_models()` with their model lists; added key-based `available` detection so frontend can dim providers with no key set
- **Status:** Fixed

---

### BUG-006 — API key cleared on page refresh
- **Category:** Frontend / State Persistence
- **Cause:** `apiKey` state was intentionally kept in memory only (`useState("")`) — any page refresh wiped it
- **Fix:** Changed initialiser to `useState(() => localStorage.getItem("raf-api-key") ?? "")` and added `useEffect` to sync to localStorage on every change. Added green "✓ saved" label in the UI.
- **Status:** Fixed

---

### BUG-007 — runId + runToken lost on page refresh, cannot reconnect to in-progress run
- **Category:** Frontend / State Persistence
- **Cause:** `runId` and `runToken` were in React state only — refreshing the page lost them permanently, making it impossible to reconnect to a run still executing on the backend
- **Fix:** Added `useEffect` hooks to sync `runId`/`runToken` to `sessionStorage` (survives refresh, clears on tab close). Added mount effect that checks `sessionStorage` on load, fetches run status from server, and calls `connectWs()` if still running.
- **Status:** Fixed

---

### BUG-008 — Starting a new run while one is running silently abandons the old one
- **Category:** Frontend / Run Lifecycle
- **Cause:** `startRun()` had no guard — clicking Run while a run was active would overwrite `runId`/`runToken` state and open a new WebSocket, leaving the old run burning API credits on the backend with no way to cancel it
- **Fix:** Added confirm dialog before `startRun` when `runStatus === "running"`. If confirmed, cancels the old run via `/api/run/{id}/cancel` before starting the new one.
- **Status:** Fixed

---

### BUG-009 — WebSocket gave up after ~31 seconds of retries
- **Category:** Frontend / Connection Reliability
- **Cause:** `reconnectAttemptsRef.current >= 6` hard-stopped all reconnection. With exponential backoff capped at 16s, total retry window was only ~31.5s — not enough to survive laptop sleep.
- **Fix:** Raised limit to 10 attempts (~95s window). After exhausting retries, now schedules a 30s fallback loop that keeps trying indefinitely while the run is active.
- **Status:** Fixed

---

### BUG-010 — Stale warning triggered too late (90s threshold)
- **Category:** Frontend / Connection Monitoring
- **Cause:** `staleWarning` was set at `age > 90_000` (90 seconds with no events) — by then the run had been silent for a long time with no user feedback
- **Fix:** Lowered to 45 seconds. Added auto-reconnect loop that triggers every 15s when stale and WS is not connected.
- **Status:** Fixed

---

### BUG-011 — `stepfun/step-3.5-flash:free` left in model list after being removed from OpenRouter
- **Category:** Config / Model Catalogue
- **Cause:** Model was removed from OpenRouter (returns "No endpoints found" 404) but remained in the UI model list and `_REASONING_MODELS` set
- **Fix:** Removed from `_REASONING_MODELS` and from the model list in `run_manager.py`
- **Status:** Fixed

---

### BUG-012 — `qwen/qwen3-next-80b-a3b-instruct:free` incorrectly in `_REASONING_MODELS`
- **Category:** LLM Adapters / Model Configuration
- **Cause:** The `-instruct:free` variant is a standard chat model; the reasoning variant is the separate `-thinking` model. Having the instruct model in `_REASONING_MODELS` caused it to receive `extra_body={"reasoning": {"enabled": True}}` which is unsupported.
- **Fix:** Removed from `_REASONING_MODELS`. Added `qwen/qwen3-next-80b-a3b-thinking` as the correct reasoning variant.
- **Status:** Fixed

---

### BUG-013 — `liquid/lfm-2.5-1.2b-thinking:free` and `z-ai/glm-5.1` no longer valid
- **Category:** Config / Model Catalogue
- **Cause:** User confirmed these models should be dropped from the list
- **Fix:** Removed from `_REASONING_MODELS` in `openrouter_adapter.py` and from the model list in `run_manager.py`
- **Status:** Fixed

---

### BUG-014 — No connection health monitoring across layers
- **Category:** Frontend / Observability
- **Cause:** No indicators for backend health, WebSocket state, HTTP API failures, or LLM API errors — when something went wrong the UI just showed a frozen run with no explanation
- **Fix:** Added four-layer monitoring system:
  - Backend: `/api/health` poll every 20s → `backendOnline` state
  - WebSocket: `wsStatus` ("connected" / "reconnecting" / "disconnected") updated inside `connectWs`
  - HTTP API: `apiFetch` wrapper with 2× retry + `apiError` state on all critical POSTs (start, cancel, fork, approve)
  - LLM API: `llmError` state set from `ev.error` field in `processEvent` event stream
  - All four shown in the health panel in the Work Panel with a manual Reconnect button
- **Status:** Fixed

---

### BUG-015 — Clarification continuation and replay run POSTs not wrapped with apiFetch
- **Category:** Frontend / Connection Reliability
- **Cause:** Only the main `startRun` POST was initially wrapped with `apiFetch`. The clarification continuation run and the node replay run each had their own `fetch(\`${API_BASE}/api/run\`, ...)` calls that bypassed retry logic and error tracking.
- **Fix:** Replaced both remaining plain `fetch` calls with `apiFetch`
- **Status:** Fixed

---

### BUG-016 — Supabase inserts may silently fail with new opaque key format
- **Category:** Backend / Supabase
- **Cause:** `_headers()` in `public_runs.py` only set `Authorization: Bearer` for JWT keys (`eyJ...`). New Supabase opaque keys (`sb_secret_...`) only got the `apikey` header. Without `Authorization`, the service role cannot bypass RLS, so `publish_run()` inserts would fail silently because there is no anon INSERT policy on `public_runs`.
- **Reported via:** Supabase dashboard log showing `relation "supabase_migrations.schema_migrations" does not exist` — investigation revealed the auth header gap
- **Fix:** Always set `Authorization: Bearer <key>` regardless of key format. Added `service_role` INSERT and UPDATE policies to `supabase-public-runs.sql` as a safety net.
- **Note:** The dashboard migration error itself is harmless — it means the `public_runs` table was created manually (not via Supabase CLI), so the CLI migration history table doesn't exist. This does not affect the application.
- **Status:** Fixed

---

### BUG-017 — refine_context using full consortium+jury for every child (massive cost overrun)
- **Category:** Engine / Cost
- **Discovered:** Trace analysis — job tracker: 145/279 model calls were refinement; GitHub dashboard: 235/603
- **Cause:** `_refine_children()` created a full Consortium+Jury and called them for every planned child regardless of whether the goal needed sharpening. 9 children × (3 consortium + 3 jury) = 54 model calls before real work began.
- **Fix:** Replaced full Consortium+Jury with a single cheap model call per child. Added `_needs_refinement()` gate — children with specific goals (≥12 words, no dependencies) are accepted as-is with zero model calls. Only vague or dependency-bearing children get the single-model refinement.
- **Status:** Fixed

---

### BUG-018 — Run marked "done" when root node produced no output (false success state)
- **Category:** Engine / State
- **Discovered:** Traces showing `status: "done"`, `hasRunDone: true`, `hasRootNodeDone: false`, `result: null` simultaneously
- **Affected:** Job application tracker, Multi-tenant API, Customer support dashboard
- **Cause:** `run.status = "done"` was set whenever `engine.run()` returned without raising an exception — even if the return value was None or empty (e.g. root merge failed silently, or a child failure blocked parent finalization)
- **Fix:** Now checks `result and result.get("output")` before marking done. If root returned but produced no output, status is set to `"error"` with an explicit message. Cancelled runs still get `"cancelled"`.
- **Status:** Fixed

---

### BUG-019 — child_id missing from model_call_start/done during refinement
- **Category:** Observability / Tracing
- **Discovered:** Trace analysis — many `task: "refine_context", node_id: "root"` events with no context showing which child was being refined, making it look like duplicate model calls
- **Cause:** `consortium.py` `model_call_start`/`model_call_done` log events did not include `child_id` even when it was present in the payload
- **Fix:** Both log events in `consortium.py` now extract `child_id` from payload and include it when present. Refinement events in `node.py` also log `child_id` directly.
- **Status:** Fixed

---

### BUG-020 — Models returning tool_call name="none" or name="" creating noisy log entries
- **Category:** Engine / Tool Handling
- **Discovered:** Trace analysis — GitHub dashboard trace showed blocked tools including "execute_sql", "sql_schema_generator", "none", and empty tool names even with tools disabled
- **Cause:** Some models return `tool_call: {"name": "none"}` when they don't want a tool — this was not filtered before logging, creating spurious `tool_blocked` events
- **Fix:** Added guard: if `tool_name` is empty, "none", "null", or "n/a" after stripping, treat as no-op and break the tool loop silently. Also the existing `tools_enabled` check already prevents tool processing when disabled.
- **Status:** Fixed

---

### BUG-021 — Deprecated/rate-limited models cause cascading run failures (no circuit breaker)
- **Category:** Engine / Reliability
- **Discovered:** Customer support trace failed immediately — grok-4.1-fast deprecated, OpenRouter recommends grok-4.3. GitHub dashboard had many failures from rate limits (429) and insufficient credits (402).
- **Cause:** No pre-flight model check, no circuit breaker — a deprecated or rate-limited model keeps being retried until the run exhausts retries and fails
- **Fix:** Pending — circuit breaker and model health check not yet implemented
- **Status:** Open

---

### BUG-022 — Export config does not match models that actually ran
- **Category:** Observability / Export
- **Discovered:** One trace showed `multiModel: false, consortiumSlots: []` in config but events showed Gemini, Llama, Mistral, O3 Mini all running
- **Cause:** Session export saved only the UI state config (`currentConfig()`), not the resolved runtime config. These diverge when presets, tier routing, or server-side defaults are applied.
- **Fix:** Extended `run_started` event in `RafEngine.run()` to include `resolved_runtime_config` with actual model names/providers for consortium, jury, leaf, mid, and root slots. Frontend captures this in `processEvent` and stores it as `resolvedRuntimeConfig` state. Export now includes both `requestedConfig` (what the UI sent) and `resolvedRuntimeConfig` (what actually ran).
- **Status:** Fixed

---

### BUG-023 — One failed child blocks entire parent merge
- **Category:** Engine / Resilience
- **Discovered:** Multiple traces showing leaf `node_done` events and `merge_done` for some nodes, but root never finalizing — `result: null`
- **Cause:** Failed children were tracked in `completed` with error placeholder output. All children including failures were passed to the merge consortium. If all children failed, merge tried to synthesize `"[child X failed: Y]"` strings, producing garbage or failing itself, leaving the root stuck with `result: null`.
- **Fix:** Added `failed_cids` set tracking which children explicitly errored. Before merge, splits children into successful and failed. Only merges successful outputs. If zero successful children, raises a clear `RuntimeError` instead of silently returning None. Emits `partial_child_failure` trace event when some children fail but merge proceeds. Passes `failed_children` context into merge payload so the merger knows what was missed.
- **Status:** Fixed

---

## Open / Unconfirmed

| ID | Issue | Status |
|---|---|---|
| BUG-011 | `stepfun/step-3.5-flash:free` still in UI model list | Needs removal |
| — | Several OpenRouter models in `_REASONING_MODELS` unconfirmed by user (nvidia, qwen3-coder:free, etc.) | Needs verification at openrouter.ai/models |
| — | Render free tier may spin down mid-run after inactivity | User on paid plan — monitor |
