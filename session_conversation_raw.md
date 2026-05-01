# Claude Code Session — Recursive Agent Framework

*2026-04-30 08:30 UTC*

---

## You

ok good now i want to add a new feature to our porject but before we start i want you to have a full understanding of this project , I want you to go through th rproject step by step

---

## Claude

Let me do a thorough exploration of the project structure and codebase.

---

## Subagent Output

Now I have a comprehensive understanding. Let me compile the complete report:

## COMPREHENSIVE PROJECT ANALYSIS: Recursive Agent Framework (RAF)

---

### **1. OVERALL PROJECT STRUCTURE**

The project is organized into three main layers with supporting files and directories:

```
Recursive-Agent-Framework/
├── raf/                          # Core Python implementation (27 .py files)
│   ├── agents/                   # Consortium and Jury orchestration
│   ├── core/                     # Core execution engine (node.py, spec.py, trace.py, deps.py, etc.)
│   ├── llm/                      # LLM adapter layer (multiple providers)
│   ├── cli/                      # Command-line interface
│   └── .env                      # Backend environment variables
├── server/                       # FastAPI backend server
│   ├── main.py                   # FastAPI app with REST + WebSocket
│   ├── run_manager.py            # Run lifecycle management
│   ├── requirements.txt          # Backend dependencies
│   └── __init__.py
├── web/                          # React + Vite frontend
│   ├── src/                      # 19 TypeScript/React source files
│   │   ├── App.tsx               # Main application component
│   │   ├── Landing.tsx           # Landing page
│   │   ├── components/           # UI components
│   │   └── lib/                  # Utilities
│   ├── index.html                # HTML entry point
│   ├── vite.config.ts            # Vite configuration
│   ├── tsconfig.json             # TypeScript config
│   ├── tailwind.config.js        # Tailwind CSS config
│   ├── package.json              # Frontend dependencies
│   └── dist/                     # Built frontend assets
├── .env.example                  # Example environment variables
├── .env                          # Live environment config
├── package.json                  # Root-level package (minimal)
├── vercel.json                   # Vercel deployment config
├── render.yaml                   # Render deployment config
├── README.md                     # Comprehensive project documentation
├── ARCHITECTURE.md               # Detailed architecture guide
├── AGENTS.md                     # Instructions for AI agents
├── .gitignore                    # Git ignore rules
└── docs/                         # Various design and planning documents
```

---

### **2. PROJECT PURPOSE & VISION**

**What It Does:**
The Recursive Agent Framework is a system for orchestrating multiple AI agents to solve complex, long, or multi-step tasks by:
1. **Recursively decomposing** tasks into smaller subtasks until each is simple enough to solve directly
2. **Using Consortium+Jury pattern**: Multiple agents (Consortium) propose solutions independently, then a separate voting group (Jury) selects the best one
3. **Managing dependencies** between subtasks so they execute in the correct order
4. **Validating outputs** against requirements (Spec) to ensure drift doesn't occur
5. **Providing real-time visibility** through a React web UI showing live execution graphs

**Larger Vision:**
It is the foundation for **Computer**: a universal substrate for recursive AI agent orchestration with experiential memory. The long-term goal is:
- A system where humans communicate intent, and the machine figures out procedures
- Multi-agent decision-making at every critical step (reducing single-model bias)
- Persistent experiential memory across sessions (agents learn from past work)
- A portable, observable substrate (Rust runtime with typed event bus)

**Core Problem It Solves:**
- **Context ceiling**: Tasks longer than a single model's context window
- **Single-agent fragility**: One model's biases and errors compound unchecked
- **No persistent cognition**: Agents forget everything between runs

---

### **3. TECHNOLOGY STACK**

| Layer | Technology | Key Libraries |
|-------|------------|--|
| **Backend** | Python 3.11+ | FastAPI (0.115+), Uvicorn, Pydantic, python-dotenv, websockets, httpx, openai |
| **Frontend** | TypeScript + React 18 | Vite, Tailwind CSS, Radix UI, D3.js, Framer Motion, DOMPurify, jsPDF, html2canvas |
| **LLM Providers** | Multi-provider abstraction | OpenRouter (primary), Claude, DeepSeek, Gemini, Groq, HuggingFace, Mock |
| **Output Validation** | JSON Schema validation | Pydantic for structured outputs |
| **Planned** | SurrealDB, Rust, Obsidian | For memory layer, substrate runtime, human-readable memory interface |

**Key Dependencies:**
- **Backend**: fastapi, uvicorn, httpx, openai, pydantic, websockets, python-dotenv
- **Frontend**: react, react-dom, d3, tailwindcss, framer-motion, dompurify, html2canvas, jspdf, lucide-react

---

### **4. ENTRY POINTS & KEY FILES**

#### **Backend Entry Points:**
- **`server/main.py`** (200+ lines) — FastAPI app with:
  - REST endpoints: `POST /api/run`, `GET /api/models`, `GET /api/health`
  - WebSocket: `/ws/{run_id}/{access_token}` for live event streaming
  - Plan approval gating: `POST /api/approve-plan`
  - CORS middleware for frontend
  - Environment-based configuration (allowed origins, API keys, run history)

- **`server/run_manager.py`** (150+ lines) — Manages run lifecycle:
  - `RunState` dataclass: stores run metadata, events, cancellation signals, plan approvals
  - `RunManager`: factory for creating runs, managing adapter selection, wiring configs
  - Handles tier-based routing (leaf/mid/root agents for different depths)
  - Thread-safe event emission and replay

#### **Core Engine:**
- **`raf/core/node.py`** (113KB) — The heart of the framework:
  - `RafNode`: Recursive execution unit that decides base vs. recursive mode
  - `RafEngine`: Orchestrates the entire run, manages config, adapters, spec, ledger, budget
  - Decision flow: mode → plan → refine → execute/recurse → merge → analyze
  - Spec repair loop to fix missing required items
  - Goal memoization cache to avoid redundant work
  - Depth-based consortium shrinking to control costs

#### **Agents:**
- **`raf/agents/consortium.py`** (200+ lines) — Parallel proposal generation:
  - Runs N agents in parallel, each producing a diverse candidate
  - Temperature ladder: agent-0 at base temp, agent-1 at +0.1, etc.
  - Early exit: stops waiting if agents agree early (unanimity shortcut)
  - Fallback adapter for when all primary agents timeout

- **`raf/agents/jury.py`** (200+ lines) — Multi-agent voting:
  - Confidence-weighted aggregation: votes weighted by voter confidence
  - Parallel voting (ThreadPoolExecutor)
  - Fallback adapter support
  - Returns ranked options and winner

#### **LLM Adapter Layer:**
- **`raf/llm/adapter.py`** — Base `ModelAdapter` class with usage callback
- **`raf/llm/prompt_adapter.py`** (150+ lines) — Shared prompt builder:
  - Injects Spec blocks (required/forbidden/success criteria)
  - Injects SpecLedger blocks (locked technology decisions)
  - Persona assignment per consortium index
  - Schemas for all task types (mode_decision, plan, vote, base_execute, merge, analysis)
  - Prompt version tracking (currently 12.2)

- **`raf/llm/openrouter_adapter.py`** — OpenRouter API adapter:
  - Access to 100+ models via single endpoint
  - Reasoning model support (extra_body with reasoning flag)
  - JSON mode for compatible models
  - Models: Qwen, Gemma, LLaMA, Mistral, grok, etc.

- **Other adapters**: claude_adapter.py, deepseek_adapter.py, gemini_adapter.py, groq_adapter.py, huggingface_adapter.py, mock_adapter.py
  - Mock adapter includes deterministic Hanoi tower solver and domain-aware fallbacks

#### **Spec & Validation:**
- **`raf/core/spec.py`** (41KB) — Frozen goal requirements:
  - `Spec`: extracted once at root (required items, forbidden items, success criteria, domain, task_class)
  - `SpecLedger`: thread-safe store of locked technology decisions (first-write-wins)
  - `SpecValidator`: two-stage validator (deterministic substring check, then LLM if needed)
  - `SpecExtractor`: LLM call to extract spec from root goal
  - Domain detection: culinary, fitness, creative, business, academic, technical, general

#### **Trace & Logging:**
- **`raf/core/trace.py`** (61 lines) — JSON event logging:
  - `TraceLogger`: emits structured JSON events to stdout, callback, and in-memory list
  - Spinner-based stderr progress display
  - Events: run_started, spec_extracted, node_created, mode_decided, consortium_candidates, jury_votes, model_call_start/done/failed, node_done, run_done

#### **Dependency Management:**
- **`raf/core/deps.py`** (50 lines) — Topological sort and validation:
  - `topo_sort()`: orders children respecting depends_on constraints
  - `validate_plan()`: checks for cycles and missing dependencies
  - `DependencyError` exception

#### **CLI:**
- **`raf/cli/run.py`**, **`raf/cli/chat.py`** — Command-line runners for testing

---

### **5. FRONTEND CODE (HTML, CSS, JavaScript)**

#### **Main Application:**
- **`web/src/App.tsx`** (200+ lines) — Central React component:
  - Manages session state, run state, graph visualization
  - Tabs: Landing, Graph, Timeline, Inspector, Config, Sessions
  - Real-time WebSocket connection to backend
  - Event stream processing to build execution graph
  - Model strategy presets: Uniform, Fast+Smart, Full Ensemble, Tiered Routing
  - Session persistence to localStorage
  - API key management with localStorage

- **`web/src/Landing.tsx`** — Landing page with welcome screen

#### **Visualization:**
- **`web/src/components/ExecutionGraph.tsx`** (150+ lines) — D3 force-directed graph:
  - Node types: raf-node, consortium-group, jury-group, agent-proposal, juror-vote, merge-group, referee-check
  - Custom D3 forces: constant outward, progressive link, collision
  - Physics params: link distance, charge strength, velocity decay, etc.
  - Color coding: cyan (raf-node), yellow (consortium), purple (jury), orange (merge)
  - Real-time node updates as events arrive
  - Tooltip support showing node details

- **`web/src/components/PhysicsPanel.tsx`** — Interactive physics parameter tuning:
  - Sliders for link distance, charge strength, decay rates
  - Live graph updates as parameters change

#### **UI Components** (from `web/src/components/ui/`):
- Radix UI components: badge, button, card, input, label, scroll-area, separator, slider, switch, tabs, textarea, select
- Styled with Tailwind CSS, using custom dark theme CSS variables
- Accessible, composable components

#### **Styles:**
- **`web/src/index.css`** (67 lines) — Tailwind imports + custom animations:
  - Dark theme (background: hsl(222 47% 4%), foreground: hsl(213 31% 91%))
  - Node glow animation (nodeGlow keyframe)
  - Edge flow animation (flowDash keyframe)
  - Custom scrollbar styling
  - Markdown output formatting with proper typography

- **`web/src/styles.css`** — Layout and additional styling

#### **Build Configuration:**
- **`vite.config.ts`** — Vite dev server on port 5173, React plugin, path alias
- **`tsconfig.json`** — ES2020 target, strict mode, React JSX
- **`package.json`** (web) — Scripts: dev, build, preview

---

### **6. BACKEND CODE (Python, FastAPI, WebSocket)**

#### **Server Infrastructure:**
- **`server/main.py`** — FastAPI application:
  - Configurable CORS (allowed origins from env)
  - Health check endpoint: `GET /api/health`
  - Model catalog: `GET /api/models`
  - Run creation: `POST /api/run` with rich config options
  - Plan approval: `POST /api/approve-plan`
  - WebSocket streaming: `WS /ws/{run_id}/{access_token}`
  - Environment variable loading from multiple .env files
  - Per-run access tokens for security

- **`server/run_manager.py`** — Run lifecycle:
  - `RunState`: stores goal, provider, model, config, events, cancellation signal
  - Background thread execution with event queue
  - Plan approval gating with 5-minute timeout
  - Tier-based agent routing (leaf, mid, root)
  - Per-slot multi-model configuration
  - Adapter factory and config builder

#### **Core Engine:**
- **`raf/core/engine.py`** — `RafEngine` orchestrator:
  - Global config holder
  - Adapter management and wiring
  - Spec extraction (once per run)
  - SpecLedger for locked decisions
  - Node budget tracking
  - Token budget tracking
  - Cancellation signal management

- **`raf/core/node.py`** — `RafNode` recursive executor:
  - **Decision points** (Consortium + Jury at each):
    1. Mode decision (base vs. recursive)
    2. Plan (decompose into children)
    3. Child refinement (clarify each child's purpose)
    4. Base execution (solve directly)
    5. Merge (synthesize child outputs)
    6. Analysis (evaluate success)
  - **Special nodes**: clarify (single-agent), scope check (single-agent)
  - **Execution modes**:
    - Base: solve directly with optional tool loop
    - Recursive: plan, refine, parallelize, merge
    - Single-pass policy for transformations (skip mode vote)
  - **Context injection**: Spec, SpecLedger, ancestor goals, dependency context
  - **Goal cache**: memoize repeated sub-goals using SHA-256 hash
  - **Spec repair loop**: targeted patch nodes when required items are missing
  - **Validator child filter**: removes pure-validation nodes from plans
  - **Node budget enforcement**: truncates plans if remaining budget insufficient

#### **Agents & Voting:**
- **Consortium** (`raf/agents/consortium.py`):
  - Parallel proposal generation
  - Each agent gets unique temperature (base + index * 0.1)
  - Retry loop for JSON parsing
  - Fallback adapter
  - Early exit on unanimity
  - Handles timeouts gracefully

- **Jury** (`raf/agents/jury.py`):
  - Parallel voting
  - Confidence-weighted aggregation
  - Uniform voting pattern (all vote on same options)
  - Fallback adapter
  - Timeout handling

#### **Referee** (`raf/core/referee.py`):
- Grounded state tracking (coverage, hash, invariant)
- Mentioned in referee blocks but implementation details for future

#### **LLM Adapters:**
- **Base class** (`raf/llm/adapter.py`): `ModelAdapter.call_raw(task, payload)`
- **PromptBasedAdapter** (`raf/llm/prompt_adapter.py`):
  - Shared prompt building for all text-based adapters
  - Persona assignment (methodical, creative, critical, pragmatic, strategic)
  - Frame building with role, spec, ledger, task blocks
  - Schema injection for each task type

- **Specific providers**:
  - **OpenRouter**: hundreds of models, JSON mode, reasoning support, temperature ladder
  - **Claude**: Anthropic API
  - **DeepSeek**: reasoning models
  - **Gemini**: Google models
  - **Groq**: fast inference
  - **HuggingFace**: open models
  - **Mock**: deterministic solver (Hanoi, domain-aware fallbacks)

#### **Validation & Schemas:**
- **`raf/core/spec.py`**:
  - SpecValidator: two-stage (deterministic, then LLM)
  - SpecExtractor: LLM call to extract frozen spec
  - Domain detection: keyword-based fast pre-filter
  - SpecLedger: thread-safe locked decision store

- **`raf/schemas.py`** (implied):
  - Pydantic validators for all task outputs
  - RafConfig dataclass with all configurable parameters

#### **JSON Output Handling:**
- **`raf/llm/json_utils.py`** (implied):
  - `call_json_with_repair()`: calls adapter, validates JSON, retries on failure
  - `call_json_with_guard()`: guard clause wrapper
  - JSON parsing and schema validation

---

### **7. AI/AGENT LOGIC**

#### **Multi-Agent Proposal & Vote Pattern:**

```python
# Every critical decision follows this pattern:
Consortium (proposal generation):
  - N agents run in parallel
  - Each receives same payload + unique _agent_index
  - Temperature varies: base + index*0.1 (creates diversity)
  - Each agent produces independent proposal
  
Jury (voting):
  - Separate group of agents votes on proposals
  - Confidence-weighted aggregation (high-confidence minority can win)
  - All jury agents see all proposals
  - Returns ranked options + winner
```

#### **Six Decision Points in a Run:**

| # | Decision | Consortium Proposes | Jury Votes On | Output Type |
|---|----------|---|---|---|
| 1 | **Mode** | base or recursive? | best mode | `{"mode": "base\|recursive"}` |
| 2 | **Plan** | child decomposition | best plan | `{"children": [...], "rationale": "..."}` |
| 3 | **Refinement** | clarified child goal | best refinement | `{"goal": "...", "success_criteria": "..."}` |
| 4 | **Base Execute** | solution output | best output | `{"output": "...", "decisions": {...}}` |
| 5 | **Merge** | synthesized results | best merge | `{"output": "...", "sections": [...]}` |
| 6 | **Analysis** | evaluation | success verdict | `{"approved": true, "goal_completed": true}` |

#### **Spec & Ledger System:**

1. **Spec** (frozen at root):
   - `required`: items that MUST appear in output
   - `forbidden`: high-drift primitives (blockchain, NFT, etc.) unless explicitly requested
   - `success_criteria`: measurable pass/fail conditions
   - `domain`: detected from goal keywords (technical, culinary, fitness, etc.)
   - `task_class`: implement, coordinate, analyze, create, transform, general

2. **SpecLedger** (accumulates during run):
   - First-write-wins: "db=PostgreSQL" locks for all downstream agents
   - Technology decisions only (dot-notation keys: "db.primary", "auth.method", etc.)
   - Thread-safe for parallel child execution
   - Quality gate filters proposals contradicting ledger before jury votes

#### **Sibling Dependencies:**

```
Parent Task
   |
   +-- Child A (no deps) ────────→ runs immediately
   +-- Child B (depends on A) ────→ waits for A's output, uses it as context
   +-- Child C (depends on A) ────→ waits for A, runs in parallel with B
   +-- Child D (depends on B, C) → waits for both, then executes
```

Children with dependencies receive their siblings' outputs (capped at 800 chars) as additional context.

#### **Context Refinement:**
Before any child executes, its goal is refined via Consortium+Jury:
- Clarify exact purpose
- Define success criteria
- Specify required output format
- Ensure child's goal aligns with locked decisions

#### **Quality Gates:**

1. **Proposal quality gate**:
   - Length check: <100 chars filtered
   - Restatement check: >0.85 word overlap with goal filtered
   - Concreteness check: domain-specific elements required for short outputs

2. **Ledger gate**:
   - Proposals contradicting SpecLedger filtered before jury vote

3. **Jury eligibility gate** (hard):
   - Missing required items → score 0
   - Contains forbidden items → score 0

#### **Spec Repair Loop:**

```
After base execution or merge:
  1. Validate output against Spec (two-stage: deterministic + LLM)
  2. If missing required items → spawn targeted "patch" RafNode
  3. Patch node runs full Consortium+Jury pipeline
  4. Repeat up to spec_repair_limit (default 2) times
  5. If repair fails, original output still returned (never hard-block)
```

#### **Execution Policies:**

- **Recursive decomposition**: complex tasks split into subtasks
- **Single-pass policy**: transformations (summarize, translate, reformat) skip mode vote, go straight to base
- **Depth-based consortium shrink**:
  - Depth 0 (root): full consortium size
  - Depth 1: max(2, size - 1)
  - Depth 2+: 1 agent (jury auto-skipped via unanimity)
- **Unanimity shortcut**: if all consortium agents agree on key field, jury skipped

---

### **8. DEPLOYMENT CONFIGURATION**

#### **Vercel (Frontend):**
- **File**: `vercel.json`
- **Build command**: `cd web && npm install && npm run build`
- **Output directory**: `web/dist`
- **Rewrites**: All routes → `/index.html` (SPA)
- **Config**: Set `VITE_API_URL` env var to backend URL

#### **Render (Backend):**
- **File**: `render.yaml`
- **Runtime**: Python 3.11.9
- **Region**: Oregon
- **Build command**: `pip install -r requirements.txt`
- **Start command**: `uvicorn server.main:app --host 0.0.0.0 --port $PORT`
- **Health check**: `/api/health`
- **Environment variables**:
  - `PYTHON_VERSION=3.11.9`
  - `RAF_ENABLE_RUN_LIST=false` (disable run history listing)
  - `RAF_REQUIRE_USER_API_KEY=true` (user provides own API key)
  - `RAF_ALLOWED_ORIGINS` (frontend URL)

#### **Local Development:**
- **`.env.example`** → copy to `.env`
- **Backend**: `OPENROUTER_API_KEY`, `RAF_ALLOWED_ORIGINS`, `RAF_ENABLE_RUN_LIST`, `RAF_REQUIRE_USER_API_KEY`
- **Frontend**: `VITE_API_URL` (default: http://localhost:8001)

#### **Security Considerations:**
- Per-run access tokens (secrets.token_urlsafe(24))
- No authentication in local dev (warning in main.py)
- Before public deploy: add API key check to POST endpoints
- Run history disabled by default (RAF_ENABLE_RUN_LIST=false)
- CORS restricted to configured origins

---

### **9. TESTS**

**Status**: No dedicated test files found in standard locations (pytest, unittest directories not present).

**Testing approach**:
- Mock adapter provides deterministic testing (Hanoi tower solver, domain-aware fallbacks)
- Run manager includes plan validation with DependencyError on cycles/invalid deps
- Spec validator includes two-stage validation (deterministic, then LLM)
- Trace system allows event inspection for debugging

**Validation mechanisms**:
- JSON schema validation (Pydantic)
- Spec coverage checks (required/forbidden items)
- SpecLedger consistency checks (no contradicting decisions)
- Dependency validation (topo_sort detects cycles)

---

### **10. ARCHITECTURE SUMMARY**

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                  │
│  Landing | Graph | Timeline | Inspector | Config | Sessions │
│  (D3 force graph, real-time WebSocket updates)              │
└──────────────────────────────────────┬──────────────────────┘
                                       │ WebSocket + REST
                    ┌──────────────────┴────────────────┐
                    │                                   │
        ┌───────────▼──────────┐         ┌──────────────▼────────┐
        │  FastAPI Server      │         │  WebSocket Handler    │
        │ (main.py)            │         │ (live event streaming)│
        │ REST: /api/run       │         └──────────────────────┘
        │ REST: /api/models    │
        │ REST: /approve-plan  │
        └───────────┬──────────┘
                    │
        ┌───────────▼──────────────────────────────────────┐
        │         RunManager (run_manager.py)             │
        │  - Run lifecycle                                 │
        │  - Adapter factory                               │
        │  - Config assembly                               │
        │  - Plan approval gating                          │
        └───────────┬──────────────────────────────────────┘
                    │
        ┌───────────▼──────────────────────────────────────┐
        │       RafEngine (core/engine.py)                │
        │  - Global config, adapters, spec, ledger        │
        │  - Budget tracking (nodes, tokens)              │
        │  - Cancellation signal                          │
        └───────────┬──────────────────────────────────────┘
                    │
        ┌───────────▼──────────────────────────────────────┐
        │         RafNode (core/node.py)                  │
        │  - Recursive task execution                     │
        │  - 6 decision points (mode, plan, refine, etc)  │
        │  - Consortium+Jury at each decision             │
        │  - Goal cache, spec repair loop                 │
        │  - Sibling dependency management                │
        └────┬────────────────────────┬───────────────────┘
             │                        │
    ┌────────▼──────────┐  ┌──────────▼──────────────┐
    │   Consortium      │  │      Jury              │
    │ (agents/consor...) │  │ (agents/jury.py)      │
    │ - N parallel agents│  │ - N parallel voters   │
    │ - Proposals       │  │ - Confidence-weighted │
    │ - Early exit      │  │ - Ranked options      │
    │ - Fallback        │  │ - Fallback            │
    └────┬──────────────┘  └──────────┬────────────┘
         │                           │
         └───────────────┬───────────┘
                        │
            ┌───────────▼────────────────┐
            │  LLM Adapter Layer         │
            │  (llm/adapter.py &         │
            │   llm/prompt_adapter.py)   │
            │                            │
            │  Providers:                │
            │  - OpenRouter (100+ models)│
            │  - Claude                  │
            │  - DeepSeek                │
            │  - Gemini                  │
            │  - Groq                    │
            │  - HuggingFace             │
            │  - Mock (deterministic)    │
            └────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│              Supporting Systems                        │
│  - Spec (core/spec.py): frozen goal requirements      │
│  - SpecLedger: locked technology decisions (thread-safe)
│  - SpecValidator: two-stage validation (fast + LLM)   │
│  - TraceLogger (core/trace.py): JSON event logging    │
│  - DependencyResolver (core/deps.py): topo sort       │
│  - Referee (core/referee.py): state tracking          │
└────────────────────────────────────────────────────────┘
```

---

### **11. KEY CONFIGURATION OPTIONS**

**RafConfig parameters** (inferred from code):
- `consortium_size`: number of proposing agents (default 3, shrinks with depth)
- `jury_size`: number of voting agents (default 2)
- `max_depth`: maximum recursion depth (default 5)
- `max_parallel_children`: max children executed in parallel (default 5)
- `max_nodes_total`: hard cap on total nodes per run (default 50)
- `node_budget`: soft budget enforcement
- `token_budget`: total token limit
- `system_prompt`: optional domain/persona framing
- `clarify_before_execute`: ask clarifying question if goal ambiguous (default True)
- `force_recursive`: always decompose at root, skip mode vote (default False)
- `plan_approval_required`: gate plan execution on user approval (default False)
- `plan_recovery`: recovery strategy on plan rejection
- `max_plan_retries`: how many times to retry planning
- `retry_limit`: JSON repair iterations per agent call
- `timeout_by_task`: per-task timeout in seconds
- `tools_enabled`: enable tool loop in base execution (default False)
- `domain`: override auto-detected domain (None = auto)
- `spec_repair_limit`: max repair attempts (default 2)
- `spec_repair_depth_limit`: max depth for repair nodes (default 0 = root only)
- `fallback_provider`: adapter to use if all primary timeout
- `fallback_model`: model for fallback adapter

**Model routing strategies** (from UI):
1. **Uniform**: same model everywhere (simplest)
2. **Fast+Smart**: fast/cheap proposers, 1 powerful judge (recommended)
3. **Full Ensemble**: diverse families propose, diverse families judge (high quality)
4. **Tiered Routing**: leaf workers (fast), mid planners (capable), root (strongest)

---

### **12. PROJECT STATUS & ROADMAP**

**What Is Built** ✅
- Recursive task decomposition (RafNode)
- Consortium multi-agent proposals
- Jury multi-agent voting with confidence weighting
- Sibling dependency execution with topological sort
- JSON schema output validation
- Context refinement layer
- FastAPI server with WebSocket streaming
- React + Vite web frontend with D3 execution graph
- OpenRouter + Mock LLM adapters
- Spec extraction and requirement enforcement
- SpecLedger for locked technology decisions
- Spec repair loop with targeted patch nodes
- Goal memoization cache
- Timeout and fallback handling
- Multiple LLM providers (adapters written)

**What Remains** 🔮
- **Experiential Memory System**: vector graph DB with position-relative retrieval
- **Observer + Injector**: always-on memory formation and pre-turn injection
- **Obsidian Sync**: make memory human-readable and git-versionable
- **Rust Substrate**: typed port/event bus runtime
- **Multi-target Compilation**: single binary to machine, CUDA cluster, cloud
- **Persistent Run Storage**: database-backed run history
- **Full Multi-provider Wiring**: connect all adapter implementations
- **Secret Vault**: tiered access control for API keys
- **Real-time UI**: expand execution tree visualization

---

### **13. NOTABLE DESIGN PATTERNS**

1. **Proposal + Vote Separation**: Proposers diverge (temperature, models), voters converge (judgment, requirements)
2. **Temperature Ladder**: agent-0 at base temp, agent-1 at +0.1, etc., creates diversity without separate prompts
3. **Confidence-Weighted Aggregation**: votes weighted by voter confidence, not simple majority
4. **Unanimity Shortcut**: skip jury if consortium unanimously agrees (saves calls)
5. **Spec Injection**: frozen requirements injected into EVERY agent prompt (prevents drift)
6. **Ledger Gate**: filter proposals contradicting locked decisions BEFORE jury vote
7. **Two-Stage Validation**: cheap deterministic check first, LLM only if needed
8. **Depth-Based Cost Control**: consortium shrinks with depth, full diversity at root
9. **Context Injection**: ancestors, dependencies, locked decisions all injected as structured blocks
10. **Persona Assignment**: each consortium agent gets different persona (methodical, creative, critical, pragmatic, strategic)

---

This is a sophisticated, well-architected system for multi-agent orchestration with strong emphasis on:
- **Reproducibility**: Spec/Ledger ensure runs stay true to requirements
- **Observability**: every event logged, trace system captures full history
- **Scalability**: recursive decomposition handles tasks of any complexity
- **Quality**: multi-agent voting reduces single-model bias
- **Flexibility**: pluggable LLM providers, configurable routing strategies

The codebase is clean, well-documented (with docstrings and ARCHITECTURE.md), and ready for both research and production use.

---

## Claude

Here's my full understanding of the project:

---

## Recursive Agent Framework (RAF) — Project Overview

### What It Does
RAF is a multi-agent orchestration system that solves complex tasks by:
1. **Recursively decomposing** tasks into smaller subtasks until each is simple enough to solve directly
2. **Consortium+Jury pattern**: Multiple agents independently propose solutions → a separate jury votes on the best one
3. **Managing sibling dependencies** via topological sort so subtasks run in the correct order
4. **Validating outputs** against a frozen `Spec` (required items, forbidden items, success criteria) to prevent drift

### Architecture

```
React Frontend (D3 graph, real-time)
        ↕ WebSocket + REST
FastAPI Server (main.py)
        ↓
RunManager (run lifecycle, adapter factory)
        ↓
RafEngine (config, spec, ledger, budgets)
        ↓
RafNode (recursive executor — 6 decision points each via Consortium+Jury)
        ↓
LLM Adapters (OpenRouter, Claude, DeepSeek, Gemini, Groq, HuggingFace, Mock)
```

### Tech Stack
| Layer | Stack |
|-------|-------|
| Frontend | React 18 + Vite + TypeScript + Tailwind + D3.js |
| Backend | Python 3.11 + FastAPI + WebSockets + Uvicorn |
| LLMs | OpenRouter (primary, 100+ models), Claude, DeepSeek, Gemini, Groq |
| Deployment | Frontend → Vercel, Backend → Render |

### Key Components
- **`raf/core/node.py`** — The heart: `RafNode` recursively executes tasks; `RafEngine` manages global state
- **`raf/agents/consortium.py`** — N agents in parallel, temperature ladder for diversity, early exit on unanimity
- **`raf/agents/jury.py`** — Confidence-weighted voting by separate jury agents
- **`raf/core/spec.py`** — `Spec` (frozen goal requirements) + `SpecLedger` (locked tech decisions, first-write-wins) + `SpecValidator` (2-stage: deterministic then LLM)
- **`server/main.py`** — REST + WebSocket API, per-run access tokens, plan approval gating
- **`web/src/App.tsx`** — Main UI: tabs for Graph, Timeline, Inspector, Config, Sessions
- **`web/src/components/ExecutionGraph.tsx`** — D3 force-directed live execution graph

### Six Decision Points Per Node (each uses Consortium+Jury)
1. **Mode** — base vs. recursive?
2. **Plan** — decompose into children
3. **Refinement** — clarify each child's goal
4. **Base Execute** — solve directly
5. **Merge** — synthesize child outputs
6. **Analysis** — did we succeed?

### Smart Cost Controls
- Consortium size shrinks with depth (full diversity at root, 1 agent at depth 2+)
- Unanimity shortcut skips jury when consortium all agrees
- Goal memoization cache avoids redundant work
- Spec repair loop patches missing required items (up to 2 attempts)

### What's Built vs. Planned
- **Built**: Full recursive execution, Consortium+Jury, WebSocket UI, LLM adapters, Spec/Ledger system
- **Planned**: Experiential memory (vector graph DB), Rust substrate runtime, Obsidian sync

---

I have a solid understanding of the whole system now. What new feature did you want to add?

---

## You

ok good now that you have a good inderstanding we are going to now add two features and we are going to work on this two step by step (  1. Run Forking                                                                                                                                      
  Click any node in the D3 graph, fork the run from that point, and try a different approach from there. Backend clones the RunState up to that node
  and re-runs. Right now every run is linear — forking would let you explore alternatives without starting from scratch.                              
                                                            
  2. Goal Chaining / Pipelines
  Chain multiple RAF runs so the output of one becomes the input of the next. Build a visual pipeline of goals. Right now each run is completely
  isolated.

---

## Claude

Let me first read the key files I'll need to modify before planning the implementation.

---

## Subagent Output

1	import os
2	from pathlib import Path
3	from typing import Any, Dict, List, Optional
4	
5	from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
6	from fastapi.middleware.cors import CORSMiddleware
7	from pydantic import BaseModel
8	
9	from server.run_manager import RunManager
10	
11	# ⚠ LOCAL DEV ONLY — this server has no authentication.
12	# Do not expose port 8001 on a shared/public network: any caller can start
13	# LLM runs (which may cost real API money) or read run history.
14	# Before deploying, add an API key check (e.g. X-Api-Key header) to all
15	# POST endpoints and restrict allow_origins to your actual frontend origin.
16	
17	# Load .env files at server startup using paths relative to this file's location
18	# so the server finds them regardless of the working directory.
19	# Both files are loaded (raf/.env first, then .env); first value wins (override=False).
20	_ROOT = Path(__file__).parent.parent
21	try:
22	    from dotenv import load_dotenv
23	    for _env_path in [_ROOT / "raf" / ".env", _ROOT / ".env"]:
24	        load_dotenv(_env_path, override=False)
25	except ImportError:
26	    # python-dotenv not installed — fall back to simple parser.
27	    # Handles: KEY=value, KEY="value", KEY='value', blank lines, # comments.
28	    # Does NOT handle: multiline values, export KEY=value, values containing #.
29	    for _env_path in [_ROOT / "raf" / ".env", _ROOT / ".env"]:
30	        if _env_path.exists():
31	            for _line in _env_path.read_text(encoding="utf-8").splitlines():
32	                _line = _line.strip()
33	                if not _line or _line.startswith("#") or "=" not in _line:
34	                    continue
35	                _k, _v = _line.split("=", 1)
36	                os.environ.setdefault(_k.strip(), _v.strip().strip("\"'"))
37	
38	
39	class AgentSpec(BaseModel):
40	    """Provider + model for a single agent slot."""
41	    provider: str
42	    model: str | None = None
43	
44	
45	class RunRequest(BaseModel):
46	    goal: str
47	    provider: str | None = None
48	    model: str | None = None
49	    adapter: str | None = "mock"
50	    jury_model: str | None = None
51	    # Per-slot multi-model lists (optional — overrides provider/model when set)
52	    consortium_agents: List[AgentSpec] | None = None
53	    jury_agents: List[AgentSpec] | None = None
54	    # Tier-based routing agents (optional — enables depth-aware model selection)
55	    # leaf_agents: Tier 0 — fast models for deep leaf base_execute workers
56	    # mid_agents:  Tier 1 — capable models for mid-level planning and merging
57	    # root_agents: Tier 2 — strongest models for root node + analysis/referee
58	    leaf_agents: List[AgentSpec] | None = None
59	    mid_agents: List[AgentSpec] | None = None
60	    root_agents: List[AgentSpec] | None = None
61	    consortium_size: int | None = None
62	    jury_size: int | None = None
63	    max_depth: int | None = None
64	    max_parallel_children: int | None = None
65	    max_nodes_total: int | None = None
66	    system_prompt: str | None = None
67	    plan_approval_required: bool = False
68	    plan_recovery: str | None = None
69	    max_plan_retries: int | None = None
70	    retry_limit: int | None = None
71	    timeout_by_task: Dict[str, int] | None = None
72	    tools_enabled: bool = False
73	    domain: str | None = None  # override auto-detected domain; None = auto
74	    skip_clarify: bool = False  # set True on clarification continuation runs
75	    force_recursive: bool = False  # always decompose at root, skip mode vote
76	    api_key: str | None = None  # user-supplied API key; overrides server env vars
77	
78	
79	class DemoRequest(BaseModel):
80	    disks: int = 3
81	    provider: str | None = None
82	    model: str | None = None
83	    consortium_size: int | None = None
84	    jury_size: int | None = None
85	    max_depth: int | None = None
86	    max_parallel_children: int | None = None
87	    max_nodes_total: int | None = None
88	    system_prompt: str | None = None
89	
90	
91	class ApprovePlanRequest(BaseModel):
92	    node_id: str
93	    children: List[Dict[str, Any]]
94	
95	
96	app = FastAPI()
97	manager = RunManager()
98	
99	
100	def _env_flag(name: str, default: bool = False) -> bool:
101	    value = os.getenv(name)
102	    if value is None:
103	        return default
104	    return value.strip().lower() in {"1", "true", "yes", "on"}
105	
106	
107	def _allowed_origins() -> List[str]:
108	    configured = os.getenv("RAF_ALLOWED_ORIGINS", "").strip()
109	    if configured:
110	        origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
111	        return origins or ["*"]
112	    return [
113	        "http://localhost:5173",
114	        "http://127.0.0.1:5173",
115	        "http://localhost:3000",
116	        "http://127.0.0.1:3000",
117	    ]
118	
119	
120	def _require_run_token(run_id: str, access_token: Optional[str]) -> Any:
121	    run_state = manager.get(run_id)
122	    if not run_state:
123	        raise HTTPException(status_code=404, detail="run not found")
124	    if not access_token or access_token != run_state.access_token:
125	        raise HTTPException(status_code=403, detail="invalid run token")
126	    return run_state
127	
128	_origins = _allowed_origins()
129	app.add_middleware(
130	    CORSMiddleware,
131	    allow_origins=_origins,
132	    allow_credentials=False,
133	    allow_methods=["*"],
134	    allow_headers=["*"],
135	)
136	
137	
138	@app.get("/api/health")
139	def health() -> Dict[str, Any]:
140	    return {"ok": True}
141	
142	
143	@app.get("/api/models")
144	def models() -> Dict[str, Any]:
145	    return manager.list_models()
146	
147	
148	@app.post("/api/run")
149	def run(request: RunRequest) -> Dict[str, Any]:
150	    provider = request.provider or request.adapter or "mock"
151	    require_user_key = _env_flag("RAF_REQUIRE_USER_API_KEY", default=False)
152	    if require_user_key and provider != "mock" and not (request.api_key or "").strip():
153	        raise HTTPException(status_code=400, detail="A user API key is required for non-mock providers.")
154	    consortium_agents = (
155	        [{"provider": a.provider, "model": a.model} for a in request.consortium_agents]
156	        if request.consortium_agents else []
157	    )
158	    jury_agents = (
159	        [{"provider": a.provider, "model": a.model} for a in request.jury_agents]
160	        if request.jury_agents else []
161	    )
162	    leaf_agents = (
163	        [{"provider": a.provider, "model": a.model} for a in request.leaf_agents]
164	        if request.leaf_agents else []
165	    )
166	    mid_agents = (
167	        [{"provider": a.provider, "model": a.model} for a in request.mid_agents]
168	        if request.mid_agents else []
169	    )
170	    root_agents = (
171	        [{"provider": a.provider, "model": a.model} for a in request.root_agents]
172	        if request.root_agents else []
173	    )
174	    # If per-slot agents are given, derive consortium_size/jury_size from list lengths
175	    config_overrides: Dict[str, Any] = {
176	        "consortium_size": len(consortium_agents) if consortium_agents else request.consortium_size,
177	        "jury_size": len(jury_agents) if jury_agents else request.jury_size,
178	        "max_depth": request.max_depth,
179	        "max_parallel_children": request.max_parallel_children,
180	        "max_nodes_total": request.max_nodes_total,
181	        "system_prompt": request.system_prompt,
182	        "plan_approval_required": request.plan_approval_required,
183	        "plan_recovery": request.plan_recovery,
184	        "max_plan_retries": request.max_plan_retries,
185	        "retry_limit": request.retry_limit,
186	        "timeout_by_task": request.timeout_by_task,
187	        "tools_enabled": request.tools_enabled,
188	    }
189	    if request.domain is not None:
190	        config_overrides["domain"] = request.domain
191	    if request.skip_clarify:
192	        config_overrides["clarify_before_execute"] = False
193	    if request.force_recursive:
194	        config_overrides["force_recursive"] = True
195	    run_state = manager.create_run(
196	        request.goal,
197	        provider,
198	        request.model,
199	        config_overrides,
200	        jury_model=request.jury_model,
201	        consortium_agents=consortium_agents,
202	        jury_agents=jury_agents,
203	        leaf_agents=leaf_agents,
204	        mid_agents=mid_agents,
205	        root_agents=root_agents,
206	        api_key=request.api_key or None,
207	    )
208	    return {"run_id": run_state.run_id, "access_token": run_state.access_token}
209	
210	
211	@app.post("/api/demo/hanoi")
212	def demo_hanoi(request: DemoRequest) -> Dict[str, Any]:
213	    disks = max(1, min(10, int(request.disks)))
214	    goal = f"HANOI({disks},0,2,1)"
215	    provider = request.provider or "mock"
216	    run_state = manager.create_run(
217	        goal,
218	        provider,
219	        request.model,
220	        {
221	            "consortium_size": request.consortium_size,
222	            "jury_size": request.jury_size,
223	            "max_depth": request.max_depth,
224	            "max_parallel_children": request.max_parallel_children,
225	            "max_nodes_total": request.max_nodes_total,
226	            "system_prompt": request.system_prompt,
227	        },
228	    )
229	    return {"run_id": run_state.run_id, "goal": goal, "access_token": run_state.access_token}
230	
231	
232	@app.get("/api/run/{run_id}")
233	def run_status(run_id: str, x_run_token: str | None = Header(default=None)) -> Dict[str, Any]:
234	    run_state = _require_run_token(run_id, x_run_token)
235	    return {"status": run_state.status, "result": run_state.result, "error": run_state.error}
236	
237	
238	@app.get("/api/run/{run_id}/events")
239	def run_events(run_id: str, x_run_token: str | None = Header(default=None)) -> Dict[str, Any]:
240	    """Return all stored events for a run (up to _MAX_EVENTS_PER_RUN).
241	
242	    Used by the frontend to replay a run's trace after a WebSocket disconnect.
243	    """
244	    run_state = _require_run_token(run_id, x_run_token)
245	    return {
246	        "run_id": run_id,
247	        "status": run_state.status,
248	        "events": run_state.events,
249	    }
250	
251	
252	@app.post("/api/run/{run_id}/approve_plan")
253	def approve_plan(run_id: str, body: ApprovePlanRequest, x_run_token: str | None = Header(default=None)) -> Dict[str, Any]:
254	    """Unblock a run waiting for plan approval (with optionally edited children)."""
255	    run_state = _require_run_token(run_id, x_run_token)
256	    try:
257	        run_state.approve_plan(body.node_id, body.children)
258	    except ValueError as exc:
259	        return {"ok": False, "error": str(exc)}
260	    return {"ok": True}
261	
262	
263	@app.post("/api/run/{run_id}/cancel")
264	def cancel_run(run_id: str, x_run_token: str | None = Header(default=None)) -> Dict[str, Any]:
265	    """Signal a running run to stop cooperatively."""
266	    _require_run_token(run_id, x_run_token)
267	    ok = manager.cancel_run(run_id)
268	    return {"ok": ok}
269	
270	
271	@app.get("/api/runs")
272	def list_runs() -> Dict[str, Any]:
273	    """Return metadata for recent runs (most recent first)."""
274	    if not _env_flag("RAF_ENABLE_RUN_LIST", default=False):
275	        raise HTTPException(status_code=404, detail="run list disabled")
276	    return {"runs": manager.list_runs()}
277	
278	
279	@app.websocket("/api/stream/{run_id}")
280	async def stream(run_id: str, websocket: WebSocket) -> None:
281	    token = websocket.query_params.get("token")
282	    run_state = manager.get(run_id)
283	    if not run_state or not token or token != run_state.access_token:
284	        await websocket.accept()
285	        await websocket.send_json({"event": "error", "message": "invalid run token"})
286	        await websocket.close(code=1008)
287	        return
288	    await websocket.accept()
289	    try:
290	        async for event in manager.stream_events(run_state):
291	            await websocket.send_json(event)
292	    except WebSocketDisconnect:
293	        return
294

---

## Subagent Output

1	"""
2	server.run_manager
3	==================
4	Manages the lifecycle of RAF runs spawned by the API server.
5	
6	Each run executes in a background daemon thread and emits JSON events into a
7	Queue.  WebSocket clients drain the queue in real time via :func:`stream_events`.
8	
9	Key classes
10	-----------
11	RunState
12	    All state for a single run: its events list, streaming queue, thread,
13	    cancellation event, plan-approval gates, and completion metadata.
14	RunManager
15	    Factory and registry for RunState objects.  Handles adapter selection,
16	    config assembly, and the optional jury adapter for multi-model setups.
17	"""
18	
19	import asyncio
20	import os
21	import secrets
22	import threading
23	import time
24	import uuid
25	from dataclasses import dataclass, field
26	from queue import Queue
27	from typing import Any, Dict, List, Optional
28	
29	from raf.core.deps import DependencyError, validate_plan
30	from raf.core.engine import RafEngine
31	from raf.core.trace import TraceLogger
32	from raf.llm.mock_adapter import MockAdapter
33	from raf.schemas import RafConfig
34	
35	# Maximum number of completed run summaries kept in history
36	_MAX_HISTORY = 50
37	# Maximum events kept per run in the replay list (guards against memory growth on deep runs)
38	_MAX_EVENTS_PER_RUN = 2000
39	
40	
41	@dataclass
42	class RunState:
43	    """All state for a single RAF run.
44	
45	    Parameters
46	    ----------
47	    run_id:
48	        UUID string identifying this run.
49	    goal:
50	        The top-level goal string passed to the engine.
51	    provider:
52	        LLM provider name (e.g. ``"openrouter"``, ``"mock"``).
53	    model:
54	        Optional specific model name within the provider.
55	    jury_model:
56	        Optional model name for the jury adapter (falls back to *model*).
57	    config_overrides:
58	        Dict of RafConfig field overrides supplied by the API caller.
59	    """
60	
61	    run_id: str
62	    goal: str
63	    provider: str
64	    model: Optional[str] = None
65	    jury_model: Optional[str] = None
66	    # Per-slot model specs — if non-empty these override provider/model/jury_model.
67	    # Each entry: {"provider": str, "model": str | None}
68	    consortium_agents: List[Dict[str, Optional[str]]] = field(default_factory=list)
69	    jury_agents: List[Dict[str, Optional[str]]] = field(default_factory=list)
70	    # Tier-based routing agents — when provided, override flat consortium/jury for
71	    # their respective depth tier.  See RafEngine for routing logic.
72	    leaf_agents: List[Dict[str, Optional[str]]] = field(default_factory=list)   # Tier 0: deep workers
73	    mid_agents: List[Dict[str, Optional[str]]] = field(default_factory=list)    # Tier 1: planners/mergers
74	    root_agents: List[Dict[str, Optional[str]]] = field(default_factory=list)   # Tier 2: root/referee
75	    config_overrides: Dict[str, object] = field(default_factory=dict)
76	    api_key: Optional[str] = None  # user-supplied key; overrides server env vars
77	    access_token: str = field(default_factory=lambda: secrets.token_urlsafe(24))
78	    status: str = "running"
79	    result: Optional[Dict[str, Any]] = None
80	    error: Optional[str] = None
81	    events: List[Dict[str, Any]] = field(default_factory=list)
82	    queue: Queue = field(default_factory=Queue)
83	    thread: Optional[threading.Thread] = None
84	
85	    # Timing
86	    started_at: float = field(default_factory=time.time)
87	    completed_at: Optional[float] = None
88	
89	    # Cooperative cancellation — set this event to ask the engine to stop.
90	    cancel_event: threading.Event = field(default_factory=threading.Event)
91	
92	    # Max children per plan — set by _execute() after config is built; used by approve_plan().
93	    max_children_per_plan: int = 20
94	
95	    # Plan approval: keyed by node_id
96	    _plan_events: Dict[str, threading.Event] = field(default_factory=dict)
97	    _approved_plans: Dict[str, Dict[str, Any]] = field(default_factory=dict)
98	
99	    # ── event helpers ─────────────────────────────────────────────────────────
100	
101	    def emit(self, event: Dict[str, Any]) -> None:
102	        """Append *event* to the replay list (capped) and push it to the live queue."""
103	        if len(self.events) < _MAX_EVENTS_PER_RUN:
104	            self.events.append(event)
105	        self.queue.put(event)
106	
107	    # ── cancellation ──────────────────────────────────────────────────────────
108	
109	    def cancel(self) -> None:
110	        """Signal the engine to stop at the next cancellation checkpoint."""
111	        self.cancel_event.set()
112	
113	    # ── plan approval ─────────────────────────────────────────────────────────
114	
115	    def request_plan_approval(self, node_id: str, plan: Dict[str, Any]) -> Dict[str, Any]:
116	        """Called from the engine background thread.  Emits ``plan_ready`` and blocks
117	        until the user approves (or up to 5 minutes, then falls back to the original plan).
118	        """
119	        event = threading.Event()
120	        self._plan_events[node_id] = event
121	        self.emit(
122	            {
123	                "event": "plan_ready",
124	                "node_id": node_id,
125	                "children": plan.get("children", []),
126	                "rationale": plan.get("rationale", ""),
127	            }
128	        )
129	        event.wait(timeout=300)
130	        # Pop both maps after the gate is released to avoid stale memory growth.
131	        result = self._approved_plans.pop(node_id, plan)
132	        self._plan_events.pop(node_id, None)
133	        return result
134	
135	    def approve_plan(self, node_id: str, children: List[Dict[str, Any]]) -> None:
136	        """Called from the API endpoint when the user approves (or edits) a plan.
137	
138	        Validates dependency structure using the run's configured max_children_per_plan
139	        before storing, so that a user-edited plan with invalid or circular dependencies
140	        fails fast here rather than crashing the engine during topo_sort at execution time.
141	        """
142	        plan = {"children": children}
143	        try:
144	            validate_plan(plan, max_children=self.max_children_per_plan)
145	        except DependencyError as exc:
146	            raise ValueError(f"Invalid plan: {exc}") from exc
147	        existing = self._approved_plans.get(node_id, {})
148	        self._approved_plans[node_id] = {**existing, "children": children}
149	        # Pop _plan_events here so the map doesn't grow; the engine thread will
150	        # also pop it in request_plan_approval after reading _approved_plans.
151	        ev = self._plan_events.pop(node_id, None)
152	        if ev:
153	            ev.set()
154	
155	
156	class RunManager:
157	    """Registry and factory for :class:`RunState` objects.
158	
159	    Creates runs, builds adapters and config, and provides helpers for
160	    cancellation, history listing, and model discovery.
161	    """
162	
163	    def __init__(self) -> None:
164	        self._runs: Dict[str, RunState] = {}
165	        self._history: List[str] = []  # run_ids ordered oldest→newest
166	
167	    # ── public accessors ──────────────────────────────────────────────────────
168	
169	    def get(self, run_id: str) -> Optional[RunState]:
170	        """Return the :class:`RunState` for *run_id*, or ``None``."""
171	        return self._runs.get(run_id)
172	
173	    def cancel_run(self, run_id: str) -> bool:
174	        """Signal *run_id* to cancel.  Returns ``True`` if the run exists."""
175	        run = self._runs.get(run_id)
176	        if not run:
177	            return False
178	        run.cancel()
179	        return True
180	
181	    def list_runs(self) -> List[Dict[str, Any]]:
182	        """Return summary dicts for the most recent runs (newest first)."""
183	        result = []
184	        for rid in reversed(self._history):
185	            run = self._runs.get(rid)
186	            if not run:
187	                continue
188	            result.append(
189	                {
190	                    "run_id": rid,
191	                    "goal": run.goal[:120],
192	                    "provider": run.provider,
193	                    "model": run.model,
194	                    "status": run.status,
195	                    "started_at": run.started_at,
196	                    "completed_at": run.completed_at,
197	                    "event_count": len(run.events),
198	                }
199	            )
200	        return result
201	
202	    # ── run creation ──────────────────────────────────────────────────────────
203	
204	    def create_run(
205	        self,
206	        goal: str,
207	        provider: str = "mock",
208	        model: Optional[str] = None,
209	        config_overrides: Optional[Dict[str, object]] = None,
210	        jury_model: Optional[str] = None,
211	        consortium_agents: Optional[List[Dict[str, Optional[str]]]] = None,
212	        jury_agents: Optional[List[Dict[str, Optional[str]]]] = None,
213	        leaf_agents: Optional[List[Dict[str, Optional[str]]]] = None,
214	        mid_agents: Optional[List[Dict[str, Optional[str]]]] = None,
215	        root_agents: Optional[List[Dict[str, Optional[str]]]] = None,
216	        api_key: Optional[str] = None,
217	    ) -> RunState:
218	        """Create, register, and immediately start a new run in a daemon thread."""
219	        run_id = str(uuid.uuid4())
220	        run = RunState(
221	            run_id=run_id,
222	            goal=goal,
223	            provider=provider,
224	            model=model,
225	            jury_model=jury_model,
226	            consortium_agents=consortium_agents or [],
227	            jury_agents=jury_agents or [],
228	            leaf_agents=leaf_agents or [],
229	            mid_agents=mid_agents or [],
230	            root_agents=root_agents or [],
231	            config_overrides=config_overrides or {},
232	            api_key=api_key,
233	        )
234	        self._runs[run_id] = run
235	        self._history.append(run_id)
236	        if len(self._history) > _MAX_HISTORY:
237	            # Prefer evicting the oldest *completed* run; fall back to oldest run
238	            # if every slot is still active (prevents unbounded history growth).
239	            evicted = False
240	            for i, rid in enumerate(self._history):
241	                candidate = self._runs.get(rid)
242	                if candidate is None or candidate.status != "running":
243	                    self._history.pop(i)
244	                    self._runs.pop(rid, None)
245	                    evicted = True
246	                    break
247	            if not evicted:
248	                oldest = self._history.pop(0)
249	                self._runs.pop(oldest, None)
250	
251	        run.thread = threading.Thread(target=self._execute, args=(run,), daemon=True)
252	        run.thread.start()
253	        return run
254	
255	    # ── model discovery ───────────────────────────────────────────────────────
256	
257	    def list_models(self) -> Dict[str, Any]:
258	        """Return all known providers and their models.
259	
260	        Every provider is always included so users can configure multi-model
261	        ensembles without needing all API keys upfront.  The ``available``
262	        list contains only providers whose API key is currently set — the
263	        frontend uses this to warn about missing keys.
264	        """
265	        # Static model catalogue — always returned regardless of API key status.
266	        # Two providers: "openrouter" for all cloud models, "mock" for local testing.
267	        all_models: Dict[str, List[str]] = {
268	            "mock": ["mock-deterministic"],
269	            "openrouter": [
270	                "openai/gpt-4.1",
271	                "openai/gpt-4.1-mini",
272	                "openai/o3-mini",
273	                "openai/gpt-5.4-nano",
274	                "anthropic/claude-3.7-sonnet",
275	                "anthropic/claude-3.5-sonnet",
276	                "google/gemini-2.5-pro",
277	                "google/gemini-2.5-flash",
278	                "meta-llama/llama-3.3-70b-instruct",
279	                "mistralai/mistral-large",
280	                "deepseek/deepseek-chat",
281	                "deepseek/deepseek-r1",
282	                "qwen/qwen-2.5-72b-instruct",
283	                "qwen/qwen3-coder",
284	                "qwen/qwen3.6-plus",
285	                "qwen/qwen3.5-35b-a3b",
286	                "qwen/qwen3.5-9b",
287	                "z-ai/glm-5.1",
288	                "stepfun/step-3.5-flash:free",
289	                "nvidia/nemotron-3-super-120b-a12b:free",
290	                "nvidia/nemotron-nano-12b-v2-vl:free",
291	                "qwen/qwen3-next-80b-a3b-instruct:free",
292	                "qwen/qwen3-coder:free",
293	                "liquid/lfm-2.5-1.2b-thinking:free",
294	                "arcee-ai/trinity-large-preview:free",
295	                "google/gemma-4-26b-a4b-it:free",
296	                "z-ai/glm-4.5-air:free",
297	                "moonshotai/kimi-k2-thinking",
298	                "mistralai/devstral-2512",
299	                "mistralai/ministral-14b-2512",
300	                "x-ai/grok-4.1-fast",
301	            ],
302	        }
303	        model_catalog = {
304	            provider: [
305	                {
306	                    "id": model,
307	                    "label": model.split("/")[-1],
308	                    "family": self._model_family(provider, model),
309	                    "tags": self._model_tags(provider, model),
310	                }
311	                for model in provider_models
312	            ]
313	            for provider, provider_models in all_models.items()
314	        }
315	
316	        # All non-mock providers are available — users supply their own API key via the UI.
317	        available: List[str] = list(all_models.keys())
318	
319	        priority = ["openrouter", "mock"]
320	        default_provider = next((p for p in priority if p in available), "mock")
321	        default_model = all_models[default_provider][0]
322	
323	        return {
324	            "providers": list(all_models.keys()),
325	            "models": all_models,
326	            "model_catalog": model_catalog,
327	            "available": available,
328	            "defaults": {"provider": default_provider, "model": default_model},
329	        }
330	
331	    # ── internals ─────────────────────────────────────────────────────────────
332	
333	    def _model_family(self, provider: str, model: str) -> str:
334	        """Small display hint for the frontend model browser."""
335	        if provider == "openrouter" and "/" in model:
336	            return model.split("/", 1)[0]
337	        if provider == "mock":
338	            return "local"
339	        return provider
340	
341	    def _model_tags(self, provider: str, model: str) -> List[str]:
342	        """Classify known model ids for display only; adapter behavior is unchanged."""
343	        tags: List[str] = []
344	        name = model.lower()
345	        if provider == "openrouter":
346	            tags.append("router")
347	        if ":free" in name:
348	            tags.append("free")
349	        if any(part in name for part in ["r1", "reason", "thinking", "o3"]):
350	            tags.append("reasoning")
351	        if any(part in name for part in ["flash", "mini", "nano", "haiku", "instant"]):
352	            tags.append("fast")
353	        if any(part in name for part in ["coder", "code"]):
354	            tags.append("coding")
355	        if not tags:
356	            tags.append("general")
357	        return tags
358	
359	    def _build_adapter(self, provider: str, model: Optional[str], api_key: Optional[str] = None) -> object:
360	        """Instantiate the LLM adapter for the given provider.
361	
362	        Supported providers: ``"openrouter"`` (all cloud models via OpenRouter API),
363	        ``"mock"`` (local deterministic testing — no API key needed).
364	
365	        *api_key* overrides the environment variable when supplied (user-provided key flow).
366	        """
367	        name = (provider or "mock").lower()
368	
369	        if name == "openrouter":
370	            from raf.llm.openrouter_adapter import OpenRouterAdapter
371	            resolved_key = api_key or os.getenv("OPENROUTER_API_KEY")
372	            if not resolved_key:
373	                raise RuntimeError("An OpenRouter API key is required. Paste yours into the key field in the UI.")
374	            model_name = model or "stepfun/step-3.5-flash:free"
375	            temperature = float(os.getenv("OPENROUTER_TEMPERATURE", "0.2"))
376	            return OpenRouterAdapter(api_key=resolved_key, model_name=model_name, temperature=temperature)
377	
378	        return MockAdapter()
379	
380	    def _build_config(self, overrides: Dict[str, object]) -> RafConfig:
381	        """Build a :class:`RafConfig` by applying non-None overrides from the API request."""
382	        config = RafConfig()
383	        for attr in (
384	            "consortium_size", "jury_size", "max_depth",
385	            "max_parallel_children", "max_nodes_total",
386	        ):
387	            
388	            value = overrides.get(attr)
389	            if value is not None and value > 0:
390	                setattr(config, attr, value)
391	
392	        system_prompt = overrides.get("system_prompt")
393	        if isinstance(system_prompt, str) and system_prompt.strip():
394	            config.system_prompt = system_prompt.strip()
395	
396	        if overrides.get("plan_approval_required"):
397	            config.plan_approval_required = True
398	
399	        plan_recovery = overrides.get("plan_recovery")
400	        if isinstance(plan_recovery, str) and plan_recovery in {"off", "auto", "ask"}:
401	            config.plan_recovery = plan_recovery
402	
403	        max_plan_retries = overrides.get("max_plan_retries")
404	        if isinstance(max_plan_retries, int) and max_plan_retries >= 0:
405	            config.max_plan_retries = max_plan_retries
406	
407	        retry_limit = overrides.get("retry_limit")
408	        if isinstance(retry_limit, int) and retry_limit >= 0:
409	            config.retry_limit = retry_limit
410	
411	        timeout_by_task = overrides.get("timeout_by_task")
412	        if isinstance(timeout_by_task, dict):
413	            for task, seconds in timeout_by_task.items():
414	                if isinstance(task, str) and isinstance(seconds, int) and seconds > 0:
415	                    config.timeout_by_task[task] = seconds
416	
417	        if overrides.get("tools_enabled"):
418	            config.tools_enabled = True
419	
420	        if overrides.get("force_recursive"):
421	            config.force_recursive = True
422	
423	        clarify = overrides.get("clarify_before_execute")
424	        if isinstance(clarify, bool):
425	            config.clarify_before_execute = clarify
426	
427	        domain = overrides.get("domain")
428	        if isinstance(domain, str) and domain:
429	            config.domain = domain
430	
431	        return config
432	
433	    def _execute(self, run: RunState) -> None:
434	        """Entry point for the background daemon thread that runs the engine."""
435	        try:
436	            config = self._build_config(run.config_overrides)
437	            # Expose the run-specific limit so approve_plan() validates correctly.
438	            run.max_children_per_plan = config.max_children_per_plan
439	
440	            # Build per-slot adapter lists.
441	            # If consortium_agents/jury_agents are specified, each slot gets its own model.
442	            # Otherwise fall back to a single adapter replicated across all slots
443	            # (RafEngine handles the replication internally).
444	            key = run.api_key  # user-supplied key (may be None — falls back to env var)
445	
446	            if run.consortium_agents:
447	                consortium_adapters = [
448	                    self._build_adapter(a["provider"], a.get("model"), key)
449	                    for a in run.consortium_agents
450	                ]
451	            else:
452	                consortium_adapters = self._build_adapter(run.provider, run.model, key)
453	
454	            if run.jury_agents:
455	                jury_adapters = [
456	                    self._build_adapter(a["provider"], a.get("model"), key)
457	                    for a in run.jury_agents
458	                ]
459	            elif run.jury_model:
460	                jury_adapters = self._build_adapter(run.provider, run.jury_model, key)
461	            else:
462	                jury_adapters = None  # engine defaults to consortium adapters
463	
464	            trace = TraceLogger(emit=run.emit, store=False, quiet=True)
465	
466	            on_plan_ready = run.request_plan_approval if config.plan_approval_required else None
467	
468	            # Build optional fallback adapter — used when all primary consortium/jury
469	            # agents time out and zero results are available.
470	            fallback_adapter = None
471	            fb_provider = getattr(config, "fallback_provider", "")
472	            fb_model = getattr(config, "fallback_model", "") or None
473	            if fb_provider:
474	                try:
475	                    fallback_adapter = self._build_adapter(fb_provider, fb_model, key)
476	                except Exception:
477	                    pass  # missing key — run without fallback
478	
479	            # ── Tier adapter lists for depth-based model routing ───────────────
480	            # When tier agents are provided: leaf → workers, mid → planners,
481	            # root → referee/analysis.  When empty, each tier falls back to the
482	            # flat consortium/jury adapters inside RafEngine.
483	            #
484	            # The mid-tier adapters also serve as jury for the leaf tier
485	            # (jury floor rule: weak models must not judge weak models).
486	            # The root-tier adapters serve as jury for root/analysis decisions.
487	            def _build_tier(agents):
488	                """Build an adapter list from a list of {provider, model} dicts."""
489	                if not agents:
490	                    return None
491	                return [self._build_adapter(a["provider"], a.get("model"), key) for a in agents]
492	
493	            leaf_adapters = _build_tier(run.leaf_agents)
494	            mid_adapters = _build_tier(run.mid_agents)
495	            root_adapters = _build_tier(run.root_agents)
496	            # Jury tiers — same objects as mid/root adapters (see RafEngine docstring)
497	            mid_jury_adapters = mid_adapters   # jury floor for Tier 0 + Tier 1
498	            root_jury_adapters = root_adapters  # jury for Tier 2 analysis/root
499	
500	            engine = RafEngine(
501	                config, consortium_adapters, trace,
502	                jury_adapters=jury_adapters,
503	                on_plan_ready=on_plan_ready,
504	                cancel_event=run.cancel_event,
505	                fallback_adapter=fallback_adapter,
506	                leaf_adapters=leaf_adapters,
507	                mid_adapters=mid_adapters,
508	                root_adapters=root_adapters,
509	                mid_jury_adapters=mid_jury_adapters,
510	                root_jury_adapters=root_jury_adapters,
511	            )
512	            result = engine.run(run.goal)
513	            run.result = result
514	            run.status = "cancelled" if run.cancel_event.is_set() else "done"
515	        except Exception as exc:
516	            run.status = "error"
517	            run.error = str(exc)
518	        finally:
519	            run.completed_at = time.time()
520	            run.emit(
521	                {
522	                    "event": "run_done",
523	                    "status": run.status,
524	                    "run_id": run.run_id,
525	                    "error": run.error,
526	                    "result": run.result,
527	                }
528	            )
529	
530	    async def stream_events(self, run: RunState):
531	        """Async generator that yields all events for a run.
532	
533	        First replays already-completed events from the in-memory list, then
534	        drains the live queue until ``run_done`` is emitted.
535	        """
536	        sent = 0
537	        for event in run.events:
538	            yield event
539	            sent += 1
540	        # Drain already-replayed events from the queue to avoid duplicates
541	        from queue import Empty
542	        for _ in range(sent):
543	            try:
544	                run.queue.get_nowait()
545	            except Empty:
546	                break
547	        while True:
548	            event = await asyncio.to_thread(run.queue.get)
549	            yield event
550	            if event.get("event") == "run_done":
551	                break
552

---

## Claude

Now let me read the frontend files.

---

## Subagent Output

File content (55694 tokens) exceeds maximum allowed tokens (25000). Use offset and limit parameters to read specific portions of the file, or search for specific content instead of reading the whole file.

---

## Subagent Output

1	import { useEffect, useRef } from 'react'
2	import * as d3 from 'd3'
3	
4	// ── Types ──────────────────────────────────────────────────────────────────────
5	
6	export type NodeType =
7	  | 'raf-node'
8	  // legacy (kept for backwards compat with stored sessions)
9	  | 'consortium' | 'jury' | 'agent'
10	  // grouped satellite types (new)
11	  | 'consortium-group' | 'jury-group'
12	  | 'agent-proposal' | 'juror-vote'
13	  | 'merge-group' | 'referee-check'
14	
15	export type GraphMode = 'simplified' | 'full'
16	
17	export interface GraphNode {
18	  id: string
19	  type: NodeType
20	  label: string
21	  detail: string
22	  active: boolean
23	  success?: boolean
24	  depth?: number
25	  goal?: string
26	  output?: string
27	  confidence?: number
28	  mode?: string
29	  phase?: string
30	  hint?: string           // compact info shown below label on graph
31	  ownerNodeId?: string    // satellite nodes: the owning RAF node id
32	  task?: string           // satellite nodes: the decision task name
33	  candidateIndex?: number // agent-proposal / juror-vote: index in array
34	  caseType?: 'base' | 'recursive'
35	  error?: boolean
36	  abandoned?: boolean
37	  durationMs?: number
38	  x?: number; y?: number; fx?: number | null; fy?: number | null; vx?: number; vy?: number
39	}
40	
41	export interface GraphEdge {
42	  id: string
43	  source: string | GraphNode
44	  target: string | GraphNode
45	  edgeType: 'flow' | 'parallel' | 'dependency' | 'merge'
46	}
47	
48	export interface PhysicsParams {
49	  linkDistance: number
50	  linkStrength: number
51	  chargeStrength: number
52	  chargeDistanceMax: number
53	  outwardStrength: number
54	  progressiveLinkBase: number
55	  progressiveLinkScale: number
56	  collideRadiusOffset: number
57	  collideStrength: number
58	  alphaDecay: number
59	  velocityDecay: number
60	}
61	
62	export const DEFAULT_PHYSICS: PhysicsParams = {
63	  linkDistance: 100,
64	  linkStrength: 0.8,
65	  chargeStrength: -1500,
66	  chargeDistanceMax: 1500,
67	  outwardStrength: 5,
68	  progressiveLinkBase: 150,
69	  progressiveLinkScale: 0.05,
70	  collideRadiusOffset: 40,
71	  collideStrength: 1,
72	  alphaDecay: 0.015,
73	  velocityDecay: 0.45,
74	}
75	
76	// ── Node appearance ────────────────────────────────────────────────────────────
77	
78	const NC: Record<string, string> = {
79	  'raf-node':         '#00e5ff',
80	  'consortium':       '#ffeb3b',
81	  'consortium-group': '#ffd600',
82	  'jury':             '#e040fb',
83	  'jury-group':       '#ce93d8',
84	  'agent':            '#69ff47',
85	  'agent-proposal':   '#69ff47',
86	  'juror-vote':       '#f3e5f5',
87	  'merge-group':      '#ff9100',
88	  'referee-check':    '#64b5f6',
89	}
90	
91	const NR: Record<string, number> = {
92	  'raf-node':         22,
93	  'consortium':       16,
94	  'consortium-group': 19,
95	  'jury':             14,
96	  'jury-group':       16,
97	  'agent':            10,
98	  'agent-proposal':   10,
99	  'juror-vote':       9,
100	  'merge-group':      17,
101	  'referee-check':    12,
102	}
103	
104	const EDGE_COLORS: Record<string, string> = {
105	  flow: '#444', parallel: '#00cccc', dependency: '#e040fb', merge: '#ff9100',
106	}
107	
108	const INSIDE_TEXT: Record<string, string> = {
109	  'consortium-group': 'C', 'jury-group': 'J',
110	  'agent-proposal': 'A',  'juror-vote': 'V',
111	  'merge-group': 'M',      'referee-check': 'R',
112	  'consortium': 'C',       'jury': 'J', 'agent': 'A',
113	}
114	
115	function nodeRadius(type: NodeType): number {
116	  return NR[type] ?? 12
117	}
118	
119	// ── Custom forces ──────────────────────────────────────────────────────────────
120	
121	function forceConstantOutward(cx: number, cy: number, strength: number) {
122	  let nodes: GraphNode[]
123	  function force(alpha: number) {
124	    for (let i = 0; i < nodes.length; i++) {
125	      const n = nodes[i]
126	      if (n.depth === 0) continue
127	      const dx = (n.x ?? 0) - cx
128	      const dy = (n.y ?? 0) - cy
129	      const dist = Math.sqrt(dx * dx + dy * dy) || 1
130	      n.vx = (n.vx ?? 0) + (dx / dist) * strength * alpha
131	      n.vy = (n.vy ?? 0) + (dy / dist) * strength * alpha
132	    }
133	  }
134	  force.initialize = (_nodes: GraphNode[]) => { nodes = _nodes }
135	  return force
136	}
137	
138	function forceProgressiveLink(baseDistance: number, strengthScale: number) {
139	  let nodes: GraphNode[]
140	  let links: GraphEdge[] = []
141	  function force(alpha: number) {
142	    if (!nodes || !links.length) return
143	    for (let i = 0; i < links.length; i++) {
144	      const link = links[i]
145	      const source = typeof link.source === 'object' ? link.source : null
146	      const target = typeof link.target === 'object' ? link.target : null
147	      if (!source || !target) continue
148	      const dx = (target.x ?? 0) - (source.x ?? 0)
149	      const dy = (target.y ?? 0) - (source.y ?? 0)
150	      const dist = Math.sqrt(dx * dx + dy * dy) || 1
151	      const stretch = Math.max(0, dist - baseDistance)
152	      if (stretch > 0) {
153	        const pull = Math.min(stretch * stretch * strengthScale * alpha * 0.01, 50)
154	        const pullX = (dx / dist) * pull
155	        const pullY = (dy / dist) * pull
156	        target.vx = (target.vx ?? 0) - pullX
157	        target.vy = (target.vy ?? 0) - pullY
158	        source.vx = (source.vx ?? 0) + pullX
159	        source.vy = (source.vy ?? 0) + pullY
160	      }
161	    }
162	  }
163	  force.initialize = (_nodes: GraphNode[]) => { nodes = _nodes }
164	  force.links = (_links: GraphEdge[]) => { links = _links; return force }
165	  return force
166	}
167	
168	// ── Component ──────────────────────────────────────────────────────────────────
169	
170	interface Props {
171	  nodes: GraphNode[]
172	  links: GraphEdge[]
173	  mode: GraphMode
174	  physics: PhysicsParams
175	  width: number
176	  height: number
177	  onNodeClick?: (node: GraphNode) => void
178	  onBackgroundClick?: () => void
179	  zoomCommand?: { action: 'in' | 'out' | 'reset'; nonce: number }
180	}
181	
182	export function ExecutionGraph({ nodes, links, mode, physics, width, height, onNodeClick, onBackgroundClick, zoomCommand }: Props) {
183	  const svgRef     = useRef<SVGSVGElement>(null)
184	  const simRef     = useRef<d3.Simulation<GraphNode, GraphEdge> | null>(null)
185	  const zlRef      = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null)
186	  const zoomRef    = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)
187	  const initRef    = useRef(false)
188	  const prevModeRef  = useRef(mode)
189	  const prevCountRef = useRef(0)
190	
191	  // ── Init once ──────────────────────────────────────────────────────────────
192	  useEffect(() => {
193	    if (!svgRef.current || initRef.current) return
194	    initRef.current = true
195	
196	    const svg = d3.select(svgRef.current)
197	    svg.selectAll('*').remove()
198	
199	    // SVG filters + arrow markers
200	    const defs = svg.append('defs')
201	    const f = defs.append('filter').attr('id', 'glow')
202	    f.append('feGaussianBlur').attr('stdDeviation', 3).attr('result', 'blur')
203	    const fm = f.append('feMerge')
204	    fm.append('feMergeNode').attr('in', 'blur')
205	    fm.append('feMergeNode').attr('in', 'SourceGraphic')
206	
207	    ;(['flow', 'parallel', 'dependency', 'merge'] as const).forEach(t => {
208	      const c = EDGE_COLORS[t]
209	      defs.append('marker').attr('id', `arr-${t}`)
210	        .attr('viewBox', '0 -5 10 10').attr('refX', 26).attr('refY', 0)
211	        .attr('markerWidth', 5).attr('markerHeight', 5).attr('orient', 'auto')
212	        .append('path').attr('d', 'M0,-5L10,0L0,5').attr('fill', c)
213	    })
214	
215	    const zl = svg.append('g')
216	    zlRef.current = zl
217	
218	    const zoom = d3.zoom<SVGSVGElement, unknown>()
219	      .scaleExtent([0.05, 6])
220	      .on('zoom', e => zl.attr('transform', e.transform.toString()))
221	    zoomRef.current = zoom
222	    svg.call(zoom)
223	    svg.on('click', event => {
224	      if (event.target === svgRef.current) onBackgroundClick?.()
225	    })
226	
227	    // Layer order matters: edges behind nodes, labels on top
228	    zl.append('g').attr('class', 'edges')
229	    zl.append('g').attr('class', 'nodes')
230	    zl.append('g').attr('class', 'labels')
231	    zl.append('g').attr('class', 'hints')
232	
233	    simRef.current = d3.forceSimulation<GraphNode>([])
234	      .force('link',            d3.forceLink<GraphNode, GraphEdge>([]).id(d => d.id).distance(physics.linkDistance).strength(physics.linkStrength))
235	      .force('charge',          d3.forceManyBody().strength(physics.chargeStrength).distanceMax(physics.chargeDistanceMax))
236	      .force('outward',         forceConstantOutward(width / 2, height / 2, physics.outwardStrength))
237	      .force('progressiveLink', forceProgressiveLink(physics.progressiveLinkBase, physics.progressiveLinkScale))
238	      .force('collide',         d3.forceCollide<GraphNode>().radius(d => nodeRadius(d.type) + physics.collideRadiusOffset).strength(physics.collideStrength))
239	      .alphaDecay(physics.alphaDecay)
240	      .velocityDecay(physics.velocityDecay)
241	
242	    simRef.current.on('tick', () => {
243	      if (!zlRef.current) return
244	      const g = zlRef.current
245	      g.select('.edges').selectAll<SVGLineElement, GraphEdge>('line')
246	        .attr('x1', d => (d.source as GraphNode).x ?? 0)
247	        .attr('y1', d => (d.source as GraphNode).y ?? 0)
248	        .attr('x2', d => (d.target as GraphNode).x ?? 0)
249	        .attr('y2', d => (d.target as GraphNode).y ?? 0)
250	      g.select('.nodes').selectAll<SVGGElement, GraphNode>('g.ngrp')
251	        .attr('transform', d => `translate(${d.x ?? 0},${d.y ?? 0})`)
252	      g.select('.labels').selectAll<SVGTextElement, GraphNode>('text')
253	        .attr('x', d => d.x ?? 0)
254	        .attr('y', d => (d.y ?? 0) + nodeRadius(d.type) + 13)
255	      g.select('.hints').selectAll<SVGTextElement, GraphNode>('text')
256	        .attr('x', d => d.x ?? 0)
257	        .attr('y', d => (d.y ?? 0) + nodeRadius(d.type) + 23)
258	    })
259	  }, []) // eslint-disable-line
260	
261	  // ── Zoom command ────────────────────────────────────────────────────────────
262	  useEffect(() => {
263	    if (!svgRef.current || !zoomRef.current || !zoomCommand) return
264	    const svg = d3.select(svgRef.current)
265	    const zoom = zoomRef.current
266	    const t = svg.transition().duration(220)
267	    // eslint-disable-next-line @typescript-eslint/no-explicit-any
268	    const svgAny = svg as any
269	    if (zoomCommand.action === 'in')       svgAny.transition(t).call(zoom.scaleBy, 1.25)
270	    else if (zoomCommand.action === 'out') svgAny.transition(t).call(zoom.scaleBy, 0.8)
271	    else                                   svgAny.transition(t).call(zoom.transform, d3.zoomIdentity)
272	  }, [zoomCommand])
273	
274	  // ── Update physics ──────────────────────────────────────────────────────────
275	  useEffect(() => {
276	    if (!simRef.current) return
277	    const sim = simRef.current
278	    ;(sim.force('link') as d3.ForceLink<GraphNode, GraphEdge>).distance(physics.linkDistance).strength(physics.linkStrength)
279	    ;(sim.force('charge') as d3.ForceManyBody<GraphNode>).strength(physics.chargeStrength).distanceMax(physics.chargeDistanceMax)
280	    sim.force('outward', forceConstantOutward(width / 2, height / 2, physics.outwardStrength))
281	    const vLinks = (sim.force('link') as d3.ForceLink<GraphNode, GraphEdge>).links()
282	    sim.force('progressiveLink', forceProgressiveLink(physics.progressiveLinkBase, physics.progressiveLinkScale))
283	    const pf = sim.force('progressiveLink') as any
284	    if (pf) pf.links(vLinks)
285	    ;(sim.force('collide') as d3.ForceCollide<GraphNode>).radius(d => nodeRadius(d.type) + physics.collideRadiusOffset).strength(physics.collideStrength)
286	    sim.alphaDecay(physics.alphaDecay).velocityDecay(physics.velocityDecay)
287	    sim.alpha(Math.max(sim.alpha(), 0.3)).restart()
288	  }, [physics, width, height])
289	
290	  // ── Update graph data ───────────────────────────────────────────────────────
291	  useEffect(() => {
292	    if (!simRef.current || !zlRef.current) return
293	    const sim = simRef.current
294	    const g   = zlRef.current
295	
296	    try {
297	      const modeChanged = prevModeRef.current !== mode
298	      prevModeRef.current = mode
299	      const isAddition = nodes.length > prevCountRef.current
300	      prevCountRef.current = nodes.length
301	
302	      const cx = width / 2; const cy = height / 2
303	      nodes.forEach(n => {
304	        if (n.depth === 0) { n.fx = n.active ? cx : null; n.fy = n.active ? cy : null }
305	      })
306	
307	      // Simplified: only RAF nodes + their dependency edges
308	      const vNodes = mode === 'full' ? nodes : nodes.filter(n => n.type === 'raf-node')
309	      const vIds   = new Set(vNodes.map(n => n.id))
310	      const vLinks = mode === 'full' ? links : links.filter(l => {
311	        const s = typeof l.source === 'string' ? l.source : (l.source as GraphNode).id
312	        const t = typeof l.target === 'string' ? l.target : (l.target as GraphNode).id
313	        return vIds.has(s) && vIds.has(t)
314	      })
315	
316	      const nodeById = new Map(vNodes.map(n => [n.id, n]))
317	      vLinks.forEach(l => {
318	        if (typeof l.source === 'object') { const c = nodeById.get((l.source as GraphNode).id); if (c && c !== l.source) l.source = c }
319	        if (typeof l.target === 'object') { const c = nodeById.get((l.target as GraphNode).id); if (c && c !== l.target) l.target = c }
320	      })
321	
322	      // ── Color helpers ──
323	      const getNodeColor = (d: GraphNode) => {
324	        if (d.error) return '#ef4444'
325	        if (d.abandoned) return '#4b5563'
326	        if (d.type === 'raf-node') {
327	          if (d.caseType === 'base') return '#69ff47'
328	          if (d.caseType === 'recursive') return '#f59e0b'
329	          return '#00e5ff'
330	        }
331	        return NC[d.type] ?? '#888'
332	      }
333	
334	      const getEdgeColor = (d: GraphEdge) => {
335	        const tgt = typeof d.target === 'object' ? d.target as GraphNode : nodeById.get(d.target as string)
336	        if (tgt?.abandoned) return '#374151'
337	        return EDGE_COLORS[d.edgeType] ?? '#444'
338	      }
339	
340	      // ── Edges ──
341	      const eSel = g.select<SVGGElement>('.edges').selectAll<SVGLineElement, GraphEdge>('line').data(vLinks, d => d.id)
342	      eSel.exit().transition().duration(200).attr('opacity', 0).remove()
343	      eSel.enter().append('line').attr('opacity', 0).attr('stroke-linecap', 'round')
344	        .call(e => e.transition().duration(300).attr('opacity', 1))
345	        .merge(eSel)
346	        .attr('stroke', getEdgeColor)
347	        .attr('stroke-width', d => (d.edgeType === 'dependency' || d.edgeType === 'merge') ? 1.5 : 2)
348	        .attr('stroke-dasharray', d => {
349	          const tgt = typeof d.target === 'object' ? d.target as GraphNode : nodeById.get(d.target as string)
350	          if (tgt?.abandoned) return '4 4'
351	          if (d.edgeType === 'merge')       return '6 3'
352	          if (d.edgeType === 'parallel')    return '8 4'
353	          if (d.edgeType === 'dependency')  return '3 3'
354	          return 'none'
355	        })
356	        .attr('marker-end', d => {
357	          const tgt = typeof d.target === 'object' ? d.target as GraphNode : nodeById.get(d.target as string)
358	          if (tgt?.abandoned) return null
359	          return `url(#arr-${d.edgeType})`
360	        })
361	
362	      // ── Nodes ──
363	      const nSel = g.select<SVGGElement>('.nodes').selectAll<SVGGElement, GraphNode>('g.ngrp').data(vNodes, d => d.id)
364	      nSel.exit().transition().duration(180).attr('opacity', 0).remove()
365	
366	      const nEnter = nSel.enter().append('g')
367	        .attr('class', d => `ngrp ngrp-${d.type}`)
368	        .style('cursor', 'grab')
369	      nEnter.append('circle').attr('class', 'fill-circle').attr('r', 0).attr('filter', 'url(#glow)')
370	        .attr('fill', getNodeColor)
371	        .attr('stroke', 'rgba(255,255,255,0.2)').attr('stroke-width', 1.5)
372	        .transition().duration(420).attr('r', d => nodeRadius(d.type))
373	      // Active-ring: pulses while the node is running
374	      nEnter.append('circle').attr('class', 'active-ring')
375	        .attr('fill', 'none').attr('stroke-opacity', 0).attr('pointer-events', 'none')
376	      // Error badge: red circle + ✕ at top-right, shown when d.error or d.abandoned
377	      nEnter.append('circle').attr('class', 'error-bg')
378	        .attr('r', 6).attr('fill', '#ef4444').attr('stroke', '#0f172a').attr('stroke-width', 1.5)
379	        .attr('pointer-events', 'none').attr('opacity', 0)
380	      nEnter.append('text').attr('class', 'error-x')
381	        .attr('text-anchor', 'middle').attr('dy', 3.5).attr('font-size', 7.5).attr('font-weight', 700)
382	        .attr('fill', 'white').attr('pointer-events', 'none').attr('opacity', 0)
383	        .text('✕')
384	      // Short inside-node text (phase for raf-node, type letter for others)
385	      nEnter.append('text')
386	        .attr('class', 'inside')
387	        .attr('text-anchor', 'middle')
388	        .attr('dy', 3)
389	        .attr('pointer-events', 'none')
390	        .attr('font-size', 6.5)
391	        .attr('font-weight', 700)
392	        .attr('fill', '#020617')
393	
394	      const nMerge = nEnter.merge(nSel)
395	      nMerge.attr('class', d => `ngrp ngrp-${d.type}${d.active ? ' raf-node-active' : ''}`)
396	      nMerge.select('circle.fill-circle')
397	        .attr('fill', getNodeColor)
398	        .attr('opacity', d => d.active ? 1 : 0.75)
399	      // Active ring: visible + coloured while running, hidden when done/idle
400	      nMerge.select('circle.active-ring')
401	        .attr('r', d => nodeRadius(d.type) + 6)
402	        .attr('stroke', d => getNodeColor(d))
403	        .attr('stroke-width', 2.5)
404	        .attr('stroke-opacity', d => d.active ? 0.85 : 0)
405	      // Error / abandoned badge: ✕ at top-right corner
406	      const showBadge = (d: GraphNode) => (d.error || d.abandoned) ? 1 : 0
407	      const badgeX = (d: GraphNode) => nodeRadius(d.type) * 0.72
408	      const badgeY = (d: GraphNode) => -nodeRadius(d.type) * 0.72
409	      nMerge.select('circle.error-bg')
410	        .attr('cx', badgeX).attr('cy', badgeY).attr('opacity', showBadge)
411	        .attr('fill', d => d.abandoned && !d.error ? '#6b7280' : '#ef4444')
412	      nMerge.select('text.error-x')
413	        .attr('x', badgeX).attr('y', badgeY).attr('opacity', showBadge)
414	      nMerge.select('text.inside')
415	        .text(d => {
416	          if (d.type === 'raf-node') {
417	            const p = d.phase || ''
418	            return p.length > 8 ? p.slice(0, 8) : p
419	          }
420	          return INSIDE_TEXT[d.type] || ''
421	        })
422	        .attr('fill', d =>
423	          d.type === 'raf-node'
424	            ? (d.caseType === 'recursive' ? '#111827' : '#020617')
425	            : 'rgba(0,0,0,0.75)'
426	        )
427	      nMerge
428	        .on('click', (e, d) => { onNodeClick?.(d); e.stopPropagation() })
429	        .on('mouseenter', function(_e, d) {
430	          d3.select(this).select('circle').transition().duration(100).attr('r', nodeRadius(d.type) * 1.3)
431	          d3.select(this).select('title').remove()
432	          d3.select(this).append('title').text(`${d.label}${d.hint ? '\n' + d.hint : ''}\n${d.detail}`)
433	        })
434	        .on('mouseleave', function(_e, d) {
435	          d3.select(this).select('circle').transition().duration(100).attr('r', nodeRadius(d.type))
436	        })
437	
438	      const drag = d3.drag<SVGGElement, GraphNode>()
439	        .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
440	        .on('drag',  (e, d) => { d.fx = e.x; d.fy = e.y })
441	        .on('end',   (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null })
442	      nMerge.call(drag)
443	
444	      // ── Node ID labels (below node) ──
445	      const lSel = g.select<SVGGElement>('.labels').selectAll<SVGTextElement, GraphNode>('text').data(vNodes, d => d.id)
446	      lSel.exit().remove()
447	      lSel.enter().append('text')
448	        .attr('text-anchor', 'middle').attr('font-size', 9).attr('pointer-events', 'none')
449	        .merge(lSel)
450	        .attr('fill', d => d.abandoned && !d.error ? '#4b5563' : '#888')
451	        .text(d => {
452	          const lbl = d.label || ''
453	          return lbl.length > 14 ? lbl.slice(0, 13) + '…' : lbl
454	        })
455	
456	      // ── Hint labels (compact info, below ID label) ──
457	      const hSel = g.select<SVGGElement>('.hints').selectAll<SVGTextElement, GraphNode>('text').data(vNodes, d => d.id)
458	      hSel.exit().remove()
459	      hSel.enter().append('text')
460	        .attr('text-anchor', 'middle').attr('font-size', 7.5).attr('pointer-events', 'none')
461	        .merge(hSel)
462	        .attr('fill', d => {
463	          if (d.type === 'raf-node') return d.caseType === 'base' ? '#69ff47' : d.caseType === 'recursive' ? '#f59e0b' : '#4b7c7c'
464	          return '#666'
465	        })
466	        .text(d => {
467	          // raf-node: show mode + confidence or just confidence
468	          if (d.type === 'raf-node') {
469	            const parts: string[] = []
470	            if (d.caseType) parts.push(d.caseType)
471	            if (d.confidence !== undefined) parts.push(`${(d.confidence * 100).toFixed(0)}%`)
472	            if (!d.active && d.success && parts.length === 0) parts.push('done')
473	            if (d.error) return 'error'
474	            return parts.join(' ')
475	          }
476	          const h = d.hint || ''
477	          return h.length > 16 ? h.slice(0, 15) + '…' : h
478	        })
479	
480	      sim.nodes(vNodes)
481	      ;(sim.force('link') as d3.ForceLink<GraphNode, GraphEdge>).links(vLinks)
482	      const pf = sim.force('progressiveLink') as any
483	      if (pf) pf.links(vLinks)
484	
485	      const targetAlpha = modeChanged ? 0.7 : isAddition ? 0.3 : 0.1
486	      sim.alpha(Math.max(sim.alpha(), targetAlpha)).restart()
487	    } catch (err) {
488	      console.error('[ExecutionGraph] update error:', err)
489	    }
490	  }, [nodes, links, mode, width, height])
491	
492	  // ── Cleanup ─────────────────────────────────────────────────────────────────
493	  useEffect(() => () => {
494	    simRef.current?.stop(); simRef.current = null
495	    initRef.current = false; prevCountRef.current = 0
496	  }, [])
497	
498	  return <svg ref={svgRef} style={{ width: '100%', height: '100%', background: 'hsl(222 47% 3%)' }} />
499	}
500

---

## Claude

Now let me read App.tsx in sections since it's large.

---

## Subagent Output

1	import { useEffect, useRef, useState, useCallback } from "react"
2	import Landing from "./Landing"
3	import type { PointerEvent } from "react"
4	import { motion, AnimatePresence } from "framer-motion"
5	import DOMPurify from "dompurify"
6	import { Zap, Network, Play, Square, Clock, Vote, FileText, Plus, Download, ZoomIn, ZoomOut, RotateCcw, History, SlidersHorizontal, Home } from "lucide-react"
7	import { Button } from "./components/ui/button"
8	import { Badge } from "./components/ui/badge"
9	import { ScrollArea } from "./components/ui/scroll-area"
10	import { Separator } from "./components/ui/separator"
11	import { Slider } from "./components/ui/slider"
12	import { Switch } from "./components/ui/switch"
13	import { Input } from "./components/ui/input"
14	import { Textarea } from "./components/ui/textarea"
15	import { Select } from "./components/ui/select"
16	import { Tabs, TabsList, TabsTrigger, TabsContent } from "./components/ui/tabs"
17	import { Card, CardContent } from "./components/ui/card"
18	import { ExecutionGraph, type GraphNode, type GraphEdge, type PhysicsParams, DEFAULT_PHYSICS } from "./components/ExecutionGraph"
19	import { PhysicsPanel } from "./components/PhysicsPanel"
20	
21	// ── types ─────────────────────────────────────────────────────────────────────
22	
23	type RafEvent = {
24	  event?: string; status?: string; node_id?: string; parent_id?: string | null
25	  depth?: number; goal?: string; output?: string; mode?: string; confidence?: number
26	  timestamp?: number; run_id?: string; error?: string; task?: string
27	  candidates?: unknown; options?: unknown; votes?: unknown; winner_id?: string
28	  children?: ChildSpec[]; result?: { output: string; metadata: { mode: string; questions?: string[]; confidence?: number } }
29	  question?: string; answer?: string; winner?: string; fast_path?: boolean; reason?: string
30	  domain?: string; required?: string[]; forbidden?: string[]; success_criteria?: string[]
31	  plan_child_id?: string; node_count?: number
32	  // plan recovery
33	  retry?: number; max_retries?: number; replaced_by?: string; plan_attempt?: number
34	  provider?: string; model?: string; role?: string; agent_index?: number
35	  duration_ms?: number; timeout_ms?: number
36	  cause?: "api_error" | "parse_error" | "schema_error"
37	}
38	
39	type ChildSpec = { child_id: string; goal: string; depends_on: string[] }
40	type NodeOutput = { output: string; mode: string; confidence: number; goal?: string }
41	type AgentSlot = { provider: string; model: string }
42	type ModelInfo = { id: string; label?: string; family?: string; tags?: string[] }
43	type SessionConfig = {
44	  provider: string; model: string; juryModel: string
45	  consortiumSize: number; jurySize: number; maxDepth: number; maxParallelChildren: number; maxNodesTotal: number
46	  forceRecursive: boolean; planGovernance: "auto" | "review" | "manual"; planRecovery: "off" | "auto" | "ask"; toolsEnabled: boolean
47	  multiModel: boolean; consortiumSlots: AgentSlot[]; jurySlots: AgentSlot[]
48	  tierRouting: boolean; leafSlots: AgentSlot[]; midSlots: AgentSlot[]; rootSlots: AgentSlot[]
49	  domainOverride: string; systemPrompt: string
50	}
51	type Session = {
52	  id: string; goal: string; provider: string; providerLabel?: string; status: string
53	  ts: number; nodeCount: number; output?: string; domain?: string; runId?: string | null; runToken?: string | null
54	  currentPhase?: string
55	  config?: SessionConfig
56	  events?: RafEvent[]
57	  graphNodes?: GraphNode[]
58	  graphLinks?: GraphEdge[]
59	  nodeOutputs?: Record<string, NodeOutput>
60	  result?: string | null
61	}
62	type ServerRunSummary = {
63	  run_id: string
64	  goal: string
65	  provider: string
66	  model?: string | null
67	  status: string
68	  started_at: number
69	  completed_at?: number | null
70	  event_count: number
71	}
72	
73	const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8001"
74	const SESSION_STORAGE_KEY = "raf-web-sessions-v1"
75	const API_KEY_STORAGE_KEY = "raf-openrouter-api-key"
76	const DOMAIN_OPTIONS = ["", "technical", "culinary", "fitness", "creative", "business", "academic", "general"]
77	
78	function authHeaders(runToken?: string | null, json = false): Record<string, string> {
79	  const headers: Record<string, string> = {}
80	  if (json) headers["Content-Type"] = "application/json"
81	  if (runToken) headers["X-Run-Token"] = runToken
82	  return headers
83	}
84	
85	// ── Model strategy presets ─────────────────────────────────────────────────────
86	// Each preset is a named configuration that sets consortium + jury slots.
87	// The "fast-smart" pattern is the key insight: fast/cheap models generate
88	// diverse proposals in parallel (consortum), a single powerful model judges them (jury).
89	// This gives near-top-model quality at a fraction of the cost.
90	type ModelStrategy = {
91	  id: string
92	  label: string
93	  badge: string        // short label shown on the card
94	  tagline: string
95	  description: string
96	  consortiumNote: string
97	  midNote?: string     // shown only for tier-routing strategies (planner tier)
98	  juryNote: string
99	  multiModel: boolean
100	  consortiumSize: number
101	  jurySize: number
102	  consortiumSlots: AgentSlot[]
103	  jurySlots: AgentSlot[]
104	  tierRouting?: boolean
105	  leafSlots?: AgentSlot[]
106	  midSlots?: AgentSlot[]
107	  rootSlots?: AgentSlot[]
108	}
109	
110	const MODEL_STRATEGIES: ModelStrategy[] = [
111	  {
112	    id: "uniform",
113	    label: "Uniform",
114	    badge: "simple",
115	    tagline: "One model, everywhere",
116	    description: "The same model generates all proposals and casts all votes. Simplest setup, easiest to debug.",
117	    consortiumNote: "Any capable model works. Try qwen/qwen3-next-80b-a3b-instruct:free or qwen/qwen3.5-35b-a3b for a free start.",
118	    juryNote: "Same model as consortium — no separate jury config needed.",
119	    multiModel: false,
120	    consortiumSize: 3,
121	    jurySize: 2,
122	    consortiumSlots: [],
123	    jurySlots: [],
124	  },
125	  {
126	    id: "fast-smart",
127	    label: "Fast + Smart",
128	    badge: "⭐ recommended",
129	    tagline: "Cheap proposers, powerful judge",
130	    description: "Fast, cheap models each propose a candidate answer in parallel (consortium). One strong reasoning model makes the final call (jury). Best quality-per-dollar — the jury only runs once per decision regardless of consortium size.",
131	    consortiumNote: "Use fast/free models — speed and diversity matter more than raw power for proposers.",
132	    juryNote: "Use a strong reasoning model — it only runs once per decision, so cost is low.",
133	    multiModel: true,
134	    consortiumSize: 4,
135	    jurySize: 1,
136	    consortiumSlots: [
137	      { provider: "openrouter", model: "google/gemma-4-26b-a4b-it:free" },
138	      { provider: "openrouter", model: "qwen/qwen3.5-9b" },
139	      { provider: "openrouter", model: "qwen/qwen3-next-80b-a3b-instruct:free" },
140	      { provider: "openrouter", model: "meta-llama/llama-3.2-3b-instruct:free" },
141	    ],
142	    jurySlots: [
143	      { provider: "openrouter", model: "moonshotai/kimi-k2-thinking" },
144	    ],
145	  },
146	  {
147	    id: "ensemble",
148	    label: "Full Ensemble",
149	    badge: "high quality",
150	    tagline: "Diverse families propose, diverse judges vote",
151	    description: "Different model families write proposals, different families vote. Cross-family consensus is hard to fool — best for adversarial or high-stakes tasks where you want maximum independence between proposers and judges.",
152	    consortiumNote: "Mix model families: coding model, reasoning model, general model. Family diversity beats raw size.",
153	    juryNote: "Mix jury families too. Three independent reasoning judges from different labs rarely all agree on a bad answer.",
154	    multiModel: true,
155	    consortiumSize: 4,
156	    jurySize: 4,
157	    consortiumSlots: [
158	      { provider: "openrouter", model: "mistralai/devstral-2512" },
159	      { provider: "openrouter", model: "qwen/qwen3.5-35b-a3b" },
160	      { provider: "openrouter", model: "google/gemma-4-26b-a4b-it:free" },
161	      { provider: "openrouter", model: "mistralai/mistral-nemo" },
162	    ],
163	    jurySlots: [
164	      { provider: "openrouter", model: "moonshotai/kimi-k2-thinking" },
165	      { provider: "openrouter", model: "x-ai/grok-4.1-fast" },
166	      { provider: "openrouter", model: "z-ai/glm-5.1" },
167	      { provider: "openrouter", model: "openai/gpt-oss-120b:free" },
168	    ],
169	  },
170	  {
171	    id: "tiered",
172	    label: "Tiered Routing",
173	    badge: "depth-aware",
174	    tagline: "Right model for the right depth",
175	    description: "Small fast models handle deep leaf workers, capable models handle mid-level planning and synthesis, and the strongest models serve as the final referee (root node + analysis). Saves cost without sacrificing quality where it matters.",
176	    consortiumNote: "Leaf workers use fast/free models — speed and diversity matter more than raw power for simple subtasks.",
177	    midNote: "Planners and mergers use capable mid-tier models — structured reasoning for decomposition and synthesis.",
178	    juryNote: "Root and analysis (referee) always use the strongest models. Mid-tier also serves as jury floor so weak models never grade weak models.",
179	    multiModel: true,
180	    tierRouting: true,
181	    consortiumSize: 2,
182	    jurySize: 1,
183	    consortiumSlots: [],
184	    jurySlots: [],
185	    leafSlots: [
186	      { provider: "openrouter", model: "google/gemma-4-26b-a4b-it:free" },
187	      { provider: "openrouter", model: "qwen/qwen3.5-9b" },
188	      { provider: "openrouter", model: "meta-llama/llama-3.2-3b-instruct:free" },
189	    ],
190	    midSlots: [
191	      { provider: "openrouter", model: "mistralai/devstral-2512" },
192	      { provider: "openrouter", model: "qwen/qwen3.5-35b-a3b" },
193	      { provider: "openrouter", model: "mistralai/mistral-nemo" },
194	    ],
195	    rootSlots: [
196	      { provider: "openrouter", model: "moonshotai/kimi-k2-thinking" },
197	      { provider: "openrouter", model: "x-ai/grok-4.1-fast" },
198	      { provider: "openrouter", model: "openai/gpt-oss-120b:free" },
199	    ],
200	  },

---

## Subagent Output

200	  },
201	]
202	
203	const EVENT_COLORS: Record<string, string> = {
204	  node_created: "#3b82f6", node_done: "#22c55e", jury_votes: "#a855f7",
205	  consortium_candidates: "#f59e0b", run_done: "#64748b", mode_decided: "#06b6d4",
206	  base_execute_start: "#f97316", base_execute_done: "#10b981", clarify_answered: "#3b82f6",
207	  spec_extracted: "#8b5cf6", scope_drift_detected: "#ef4444", tool_called: "#ef4444",
208	  plan_validation_failed: "#f97316", plan_retry_start: "#fb923c", plan_retry_done: "#22c55e",
209	  plan_abandoned: "#ef4444", plan_replaced: "#a3e635",
210	  model_call_start: "#38bdf8", model_call_done: "#22c55e", model_call_failed: "#ef4444",
211	  model_call_timeout: "#f59e0b", model_call_fallback: "#a855f7",
212	}
213	
214	// Tier badge display helpers
215	const TIER_LABELS: Record<number, { label: string; className: string }> = {
216	  0: { label: "T0·Leaf",    className: "bg-sky-950/60 text-sky-300" },
217	  1: { label: "T1·Plan",   className: "bg-amber-950/60 text-amber-300" },
218	  2: { label: "T2·Ref",    className: "bg-rose-950/60 text-rose-300" },
219	}
220	function tierBadge(tier: number | undefined): JSX.Element | null {
221	  if (tier === undefined || tier === null) return null
222	  const t = TIER_LABELS[tier]
223	  if (!t) return null
224	  return <span className={`rounded px-1 py-0.5 text-[9px] font-mono font-semibold shrink-0 ${t.className}`}>{t.label}</span>
225	}
226	
227	const TIMELINE_FILTER_EVENTS: Record<string, string[]> = {
228	  node:      ["node_created", "node_done", "mode_decided"],
229	  vote:      ["jury_votes", "consortium_candidates"],
230	  execution: ["base_execute_start", "base_execute_done", "merge_done", "plan_selected"],
231	  model:     ["model_call_start", "model_call_done", "model_call_failed", "model_call_timeout", "model_call_fallback"],
232	  error:     ["scope_drift_detected", "tool_blocked", "plan_validation_failed", "plan_abandoned", "model_call_failed", "model_call_timeout"],
233	}
234	
235	// Expected-next hints for the run health panel
236	const PHASE_NEXT_HINT: Record<string, string> = {
237	  "run_started":          "spec_extract → mode_decide",
238	  "spec_extracted":       "mode_decide → plan / base_execute",
239	  "mode_decided":         "plan_start or base_execute_start",
240	  "plan_start":           "consortium_candidates → jury_votes → plan_selected",
241	  "plan_selected":        "children_start → node_created × N",
242	  "children_start":       "node_created events for each child",
243	  "consortium_candidates":"jury_votes → decision",
244	  "jury_votes":           "next task or base_execute_done",
245	  "base_execute_start":   "base_execute_done → analysis_done",
246	  "base_execute_done":    "analysis_done → node_done",
247	  "merge_done":           "analysis_done → node_done",
248	  "analysis_done":        "node_done",
249	  "node_done":            "sibling nodes or merge_done → run_done",
250	  "plan_validation_failed": "plan_retry_start or plan_abandoned",
251	  "plan_retry_done":      "children_start → node_created × N",
252	}
253	
254	// ts = Python time.time() in seconds; start = Date.now() in ms
255	function relTs(ts: number | undefined, start: number | null): string {
256	  if (!ts || !start) return ""
257	  const ms = Math.round(ts * 1000 - start)
258	  if (Math.abs(ms) < 1000) return `+${ms}ms`
259	  return `+${(ms / 1000).toFixed(1)}s`
260	}
261	
262	const CAUSE_LABELS: Record<string, { label: string; detail: string }> = {
263	  api_error:    { label: "API Error",    detail: "Model was unreachable or provider returned an error" },
264	  parse_error:  { label: "Parse Error",  detail: "Model ran but returned invalid JSON" },
265	  schema_error: { label: "Schema Error", detail: "Model ran but output had the wrong shape" },
266	}
267	
268	function eventLabel(ev: RafEvent): string {
269	  const key = ev.event || ev.status || ""
270	  const map: Record<string, string> = {
271	    node_created: "Node Created", node_done: "Node Done", jury_votes: "Jury Vote",
272	    consortium_candidates: "Consortium Proposals", run_done: "Run Complete",
273	    clarify_answered: "Clarification answered", mode_decided: "Mode Decided",
274	    base_execute_start: "Base Executing", base_execute_done: "Base Done",
275	    spec_extracted: "Spec Extracted", merge_done: "Merge Done",
276	    plan_selected: "Plan Selected", scope_drift_detected: "Scope Drift",
277	    tool_called: "Tool Called", analysis_done: "Analysis Done",
278	    run_started: "Run Started",
279	    plan_validation_failed: "Plan Validation Failed", plan_retry_start: "Plan Retry",
280	    plan_retry_done: "Plan Retry Done", plan_abandoned: "Plan Abandoned",
281	    plan_replaced: "Plan Replaced",
282	    model_call_start: "Model Call Started", model_call_done: "Model Call Done",
283	    model_call_failed: "Model Call Failed", model_call_timeout: "Model Call Timeout",
284	    model_call_fallback: "Model Fallback",
285	  }
286	  const base = map[key] || key.replace(/_/g, " ")
287	  // For model call events, append role + model for quick identification
288	  if (key.startsWith("model_call_") && ev.role && ev.model) {
289	    return `${base} · ${ev.role} [${ev.model}]`
290	  }
291	  return base
292	}
293	
294	// Convert internal "option-N" IDs to human-readable "Option N+1" labels.
295	function optionLabel(id: string | undefined): string {
296	  if (!id) return "?"
297	  const m = id.match(/^option-(\d+)$/)
298	  return m ? `Option ${parseInt(m[1]) + 1}` : id
299	}
300	
301	function phaseForEvent(ev: RafEvent): string | null {
302	  const key = ev.event || ev.status || ""
303	  const map: Record<string, string> = {
304	    run_started: "Starting",
305	    node_created: "Queued",
306	    mode_decide_start: "Deciding",
307	    mode_decided: "Mode chosen",
308	    plan_start: "Planning",
309	    plan_selected: "Plan selected",
310	    plan_ready: "Waiting approval",
311	    children_start: "Spawning children",
312	    consortium_candidates: "Proposals",
313	    jury_votes: "Voting",
314	    model_call_start: "Waiting on model",
315	    model_call_done: "Model returned",
316	    model_call_failed: "Model failed",
317	    model_call_timeout: "Model timed out",
318	    base_execute_start: "Executing",
319	    base_execute_done: "Executed",
320	    merge_done: "Merged",
321	    analysis_done: "Analyzed",
322	    child_failed: "Child failed",
323	    node_done: "Done",
324	    run_done: ev.error ? "Error" : ev.status === "cancelled" ? "Cancelled" : "Done",
325	  }
326	  return map[key] || null
327	}
328	
329	function graphEndpointId(endpoint: string | GraphNode): string {
330	  return typeof endpoint === "string" ? endpoint : endpoint.id
331	}
332	
333	function cleanGraphLinks(links: GraphEdge[]): GraphEdge[] {
334	  return links.map(link => ({
335	    id: link.id,
336	    source: graphEndpointId(link.source),
337	    target: graphEndpointId(link.target),
338	    edgeType: link.edgeType,
339	  }))
340	}
341	
342	function cleanGraphNodes(nodes: GraphNode[]): GraphNode[] {
343	  return nodes.map(({ vx: _vx, vy: _vy, fx: _fx, fy: _fy, ...node }) => ({ ...node }))
344	}
345	
346	function outputMapToRecord(map: Map<string, NodeOutput>): Record<string, NodeOutput> {
347	  return Object.fromEntries(map.entries())
348	}
349	
350	function outputRecordToMap(record?: Record<string, NodeOutput>): Map<string, NodeOutput> {
351	  return new Map(Object.entries(record || {}))
352	}
353	
354	function normalizeSlots(slots: AgentSlot[], size: number, provider: string, model: string): AgentSlot[] {
355	  return Array.from({ length: size }, (_, i) => slots[i] || { provider, model })
356	}
357	
358	function loadStoredSessions(): Session[] {
359	  try {
360	    const raw = window.localStorage.getItem(SESSION_STORAGE_KEY)
361	    if (!raw) return []
362	    const parsed = JSON.parse(raw)
363	    return Array.isArray(parsed) ? parsed.slice(0, 20) : []
364	  } catch {
365	    return []
366	  }
367	}
368	
369	function formatOutput(text: string): string {
370	  // Sanitize FIRST, then apply safe formatting so no injected HTML survives
371	  const safe = DOMPurify.sanitize(text, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] })
372	  return safe
373	    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
374	    .replace(/^#{1,3}\s+(.+)$/gm, '<strong style="color:#60a5fa;font-size:1rem">$1</strong>')
375	    .replace(/^[-•]\s+(.+)$/gm, '• $1')
376	    .replace(/\n/g, '<br/>')
377	}
378	
379	// ── ExpandModal ───────────────────────────────────────────────────────────────
380	function tryPrettyJson(text: string): string {
381	  try {
382	    const parsed = JSON.parse(text)
383	    return JSON.stringify(parsed, null, 2)
384	  } catch {
385	    return text
386	  }
387	}
388	
389	function ExpandModal({ title, content, onClose }: { title: string; content: string; onClose: () => void }) {
390	  const formatted = tryPrettyJson(content)
391	  const [copied, setCopied] = useState(false)
392	
393	  useEffect(() => {
394	    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose() }
395	    window.addEventListener("keydown", handler)
396	    return () => window.removeEventListener("keydown", handler)
397	  }, [onClose])
398	
399	  const copy = () => {
400	    navigator.clipboard.writeText(content).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500) })
401	  }
402	
403	  return (
404	    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
405	      <div
406	        className="relative w-[min(90vw,860px)] max-h-[85vh] flex flex-col rounded-xl border border-border bg-card shadow-2xl overflow-hidden"
407	        onClick={e => e.stopPropagation()}
408	      >
409	        <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
410	          <span className="text-sm font-medium">{title}</span>
411	          <div className="flex items-center gap-2">
412	            <button
413	              onClick={copy}
414	              className="text-[10px] px-2 py-1 rounded border border-border text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors"
415	            >
416	              {copied ? "Copied!" : "Copy"}
417	            </button>
418	            <button onClick={onClose} className="text-muted-foreground hover:text-foreground text-base leading-none px-1">✕</button>
419	          </div>
420	        </div>
421	        <div className="flex-1 min-h-0 overflow-y-auto p-4">
422	          <pre className="text-xs font-mono whitespace-pre-wrap break-words text-foreground/90 leading-relaxed">{formatted}</pre>
423	        </div>
424	      </div>
425	    </div>
426	  )
427	}
428	
429	// ── main component ─────────────────────────────────────────────────────────────
430	
431	export default function App() {
432	  // landing page — shown once per session; dismissed on "Launch App" / "Try Demo"
433	  const [showLanding, setShowLanding] = useState<boolean>(() => !sessionStorage.getItem("raf-entered"))
434	
435	  // api key (user-supplied, persisted in localStorage)
436	  const [apiKey, setApiKey] = useState<string>(() => localStorage.getItem(API_KEY_STORAGE_KEY) || "")
437	
438	  // run config
439	  const [goal, setGoal] = useState("")
440	  const [provider, setProvider] = useState("mock")
441	  const [model, setModel] = useState("")
442	  const [juryModel, setJuryModel] = useState("")
443	  const [maxDepth, setMaxDepth] = useState(4)
444	  const [maxParallelChildren, setMaxParallelChildren] = useState(4)
445	  const [maxNodesTotal, setMaxNodesTotal] = useState(50)
446	  const [forceRecursive, setForceRecursive] = useState(false)
447	  const [planGovernance, setPlanGovernance] = useState<"auto" | "review" | "manual">("auto")
448	  const [planRecovery, setPlanRecovery] = useState<"off" | "auto" | "ask">("off")
449	  const [toolsEnabled, setToolsEnabled] = useState(false)
450	  const [domainOverride, setDomainOverride] = useState("")
451	  const [systemPrompt, setSystemPrompt] = useState("")
452	  const [providers, setProviders] = useState<string[]>(["mock"])
453	  const [models, setModels] = useState<Record<string, string[]>>({})
454	  const [modelCatalog, setModelCatalog] = useState<Record<string, ModelInfo[]>>({})
455	  const [availableProviders, setAvailableProviders] = useState<string[]>(["mock"])
456	  const [consortiumSize, setConsortiumSize] = useState(3)
457	  const [jurySize, setJurySize] = useState(3)
458	  const [multiModel, setMultiModel] = useState(false)
459	  const [consortiumSlots, setConsortiumSlots] = useState<AgentSlot[]>([])
460	  const [jurySlots, setJurySlots] = useState<AgentSlot[]>([])
461	  const [tierRouting, setTierRouting] = useState(false)
462	  const [leafSlots, setLeafSlots] = useState<AgentSlot[]>([])
463	  const [midSlots, setMidSlots] = useState<AgentSlot[]>([])
464	  const [rootSlots, setRootSlots] = useState<AgentSlot[]>([])
465	  const [modelPickerOpen, setModelPickerOpen] = useState(false)
466	  const [appliedStrategy, setAppliedStrategy] = useState<string | null>(null)
467	  const [expandModal, setExpandModal] = useState<{ title: string; content: string } | null>(null)
468	
469	  // ui state
470	  const [centerTab, setCenterTab] = useState<"output" | "timeline" | "votes" | "spec" | "tools" | "checks">("output")
471	  const [timelineFilter, setTimelineFilter] = useState<"all" | "node" | "vote" | "execution" | "model" | "error">("all")
472	  const [sessions, setSessions] = useState<Session[]>(() => loadStoredSessions())
473	  const [serverRuns, setServerRuns] = useState<ServerRunSummary[]>([])
474	  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
475	  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
476	  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
477	  const [sidebarWidth, setSidebarWidth] = useState(264)
478	  const [sidebarTab, setSidebarTab] = useState<"sessions" | "config">("sessions")
479	  const [workPanelOpen, setWorkPanelOpen] = useState(true)
480	  const [workspaceMode, setWorkspaceMode] = useState<"work" | "demo">("work")
481	  const [workPanelPos, setWorkPanelPos] = useState({ left: 272, top: 56 })
482	
483	  // run state
484	  const [runId, setRunId] = useState<string | null>(null)
485	  const [runToken, setRunToken] = useState<string | null>(null)
486	  const [runStatus, setRunStatus] = useState<"idle" | "running" | "done" | "error" | "cancelled">("idle")
487	  const [events, setEvents] = useState<RafEvent[]>([])
488	  const [nodeOutputs, setNodeOutputs] = useState<Map<string, NodeOutput>>(new Map())
489	  const [runResult, setRunResult] = useState<string | null>(null)
490	  const [detectedDomain, setDetectedDomain] = useState<string | null>(null)
491	  const [clarifyQuestion, setClarifyQuestion] = useState<string | null>(null)
492	  const [clarifyAnswer, setClarifyAnswer] = useState("")
493	  const [accumulatedGoal, setAccumulatedGoal] = useState("")
494	  const [pendingPlan, setPendingPlan] = useState<{ nodeId: string; children: ChildSpec[] } | null>(null)
495	  const [nodeCount, setNodeCount] = useState(0)
496	  const [currentPhase, setCurrentPhase] = useState("Idle")
497	  const [partialFailures, setPartialFailures] = useState(0)
498	  const [staleWarning, setStaleWarning] = useState(false)
499	  const [lastEventAge, setLastEventAge] = useState<number | null>(null)

---

## Subagent Output

500	
501	  // physics
502	  const [physics, setPhysics] = useState<PhysicsParams>({ ...DEFAULT_PHYSICS })
503	
504	  // graph state
505	  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([])
506	  const [graphLinks, setGraphLinks] = useState<GraphEdge[]>([])
507	  const [graphMode, setGraphMode] = useState<"simplified" | "full">("simplified")
508	  const [backendStatus, setBackendStatus] = useState<"checking" | "connected" | "offline">("checking")
509	  const [zoomCommand, setZoomCommand] = useState<{ action: "in" | "out" | "reset"; nonce: number } | undefined>()
510	  const graphModeRef = useRef<"simplified" | "full">("simplified")
511	  const graphNodesRef = useRef<GraphNode[]>([])
512	  const graphLinksRef = useRef<GraphEdge[]>([])
513	  const graphRef = useRef<HTMLDivElement>(null)
514	  const svgRef = useRef<SVGSVGElement | null>(null)
515	  const [gSize, setGSize] = useState({ w: 800, h: 600 })
516	
517	  // websocket
518	  const wsRef = useRef<WebSocket | null>(null)
519	  const isRunningRef = useRef(false)
520	  const reconnectAttemptsRef = useRef(0)
521	  const runStartRef = useRef<number | null>(null)
522	  const workPanelDragRef = useRef<{ x: number; y: number; left: number; top: number } | null>(null)
523	  const sidebarResizeRef = useRef<{ x: number; width: number } | null>(null)
524	  // dedup: prevents replay from doubling events on reconnect
525	  const seenEventsRef = useRef<Set<string>>(new Set())
526	  // store raw satellite events so toggling to "full" can retroactively add them
527	  const satelliteEventsRef = useRef<RafEvent[]>([])
528	  const planChildrenRef = useRef<Record<string, ChildSpec[]>>({})
529	  const planChildNodeRef = useRef<Record<string, string>>({})
530	  const nodeCreatedTsRef = useRef<Record<string, number>>({})
531	  const lastEventTsRef = useRef<number>(0)
532	
533	  useEffect(() => { graphModeRef.current = graphMode }, [graphMode])
534	
535	  // When switching to "full", retroactively add satellite nodes from stored events
536	  useEffect(() => {
537	    if (graphMode === "full") {
538	      satelliteEventsRef.current.forEach(ev => addSatelliteNodes(ev))
539	    }
540	    // simplified: leave nodes as-is (removing mid-run would be jarring)
541	  }, [graphMode]) // eslint-disable-line
542	
543	  // graph resize observer
544	  useEffect(() => {
545	    const upd = () => {
546	      if (!graphRef.current) return
547	      const r = graphRef.current.getBoundingClientRect()
548	      if (r.width > 10 && r.height > 10) setGSize({ w: r.width, h: r.height })
549	    }
550	    upd()
551	    const obs = new ResizeObserver(upd)
552	    if (graphRef.current) obs.observe(graphRef.current)
553	    return () => obs.disconnect()
554	  }, [])
555	
556	  // live timer: update lastEventAge every second while running; stale warning every 5s
557	  useEffect(() => {
558	    const tick = window.setInterval(() => {
559	      if (lastEventTsRef.current > 0) {
560	        const age = Date.now() - lastEventTsRef.current
561	        setLastEventAge(Math.floor(age / 1000))
562	        if (isRunningRef.current) setStaleWarning(age > 90_000)
563	      } else {
564	        setLastEventAge(null)
565	      }
566	    }, 1000)
567	    return () => window.clearInterval(tick)
568	  }, [])
569	
570	  // fetch providers on mount
571	  useEffect(() => {
572	    fetch(`${API_BASE}/api/models`)
573	      .then(r => r.json())
574	      .then(d => {
575	        setProviders(d.providers || ["mock"])
576	        setModels(d.models || {})
577	        setModelCatalog(d.model_catalog || {})
578	        setAvailableProviders(d.available || ["mock"])
579	        if (d.defaults?.provider) setProvider(d.defaults.provider)
580	        if (d.defaults?.model) setModel(d.defaults.model)
581	      })
582	      .catch(() => {})
583	  }, [])
584	
585	  useEffect(() => {
586	    let cancelled = false
587	    const check = () => {
588	      const controller = new AbortController()
589	      const timeout = window.setTimeout(() => controller.abort(), 2500)
590	      fetch(`${API_BASE}/api/health`, { signal: controller.signal })
591	        .then(r => { if (!cancelled) setBackendStatus(r.ok ? "connected" : "offline") })
592	        .catch(() => { if (!cancelled) setBackendStatus("offline") })
593	        .finally(() => window.clearTimeout(timeout))
594	    }
595	    check()
596	    const timer = window.setInterval(check, 10000)
597	    return () => { cancelled = true; window.clearInterval(timer) }
598	  }, [])
599	
600	  const refreshServerRuns = useCallback(async () => {
601	    try {
602	      const res = await fetch(`${API_BASE}/api/runs`)
603	      if (!res.ok) return
604	      const data = await res.json() as { runs?: ServerRunSummary[] }
605	      setServerRuns(data.runs || [])
606	    } catch {
607	      setServerRuns([])
608	    }
609	  }, [])
610	
611	  useEffect(() => {
612	    if (backendStatus === "connected") refreshServerRuns()
613	  }, [backendStatus, refreshServerRuns])
614	
615	  useEffect(() => {
616	    try {
617	      window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessions.slice(0, 20)))
618	    } catch {
619	      // Storage is best-effort; active runs should not depend on it.
620	    }
621	  }, [sessions])
622	
623	  useEffect(() => {
624	    if (!multiModel) return
625	    setConsortiumSlots(prev => normalizeSlots(prev, consortiumSize, provider, model))
626	  }, [multiModel, consortiumSize, provider, model])
627	
628	  useEffect(() => {
629	    if (!multiModel) return
630	    setJurySlots(prev => normalizeSlots(prev, jurySize, provider, juryModel || model))
631	  }, [multiModel, jurySize, provider, model, juryModel])
632	
633	  const currentConfig = useCallback((): SessionConfig => ({
634	    provider, model, juryModel, consortiumSize, jurySize, maxDepth, maxParallelChildren, maxNodesTotal,
635	    forceRecursive, planGovernance, planRecovery, toolsEnabled, multiModel, consortiumSlots, jurySlots,
636	    tierRouting, leafSlots, midSlots, rootSlots,
637	    domainOverride, systemPrompt,
638	  }), [provider, model, juryModel, consortiumSize, jurySize, maxDepth, maxParallelChildren, maxNodesTotal, forceRecursive, planGovernance, planRecovery, toolsEnabled, multiModel, consortiumSlots, jurySlots, tierRouting, leafSlots, midSlots, rootSlots, domainOverride, systemPrompt])
639	
640	  useEffect(() => {
641	    if (!activeSessionId) return
642	    const graphSnapshot = cleanGraphNodes(graphNodes)
643	    const linkSnapshot = cleanGraphLinks(graphLinks)
644	    const outputsSnapshot = outputMapToRecord(nodeOutputs)
645	    setSessions(prev => prev.map(s => s.id === activeSessionId ? {
646	      ...s,
647	      provider,
648	      runId,
649	      runToken,
650	      status: runStatus,
651	      nodeCount,
652	      output: runResult || s.output,
653	      result: runResult,
654	      domain: detectedDomain || s.domain,
655	      currentPhase,
656	      config: currentConfig(),
657	      events,
658	      graphNodes: graphSnapshot,
659	      graphLinks: linkSnapshot,
660	      nodeOutputs: outputsSnapshot,
661	    } : s))
662	  }, [activeSessionId, provider, runId, runToken, runStatus, nodeCount, runResult, detectedDomain, currentPhase, currentConfig, events, graphNodes, graphLinks, nodeOutputs])
663	
664	  const restoreSession = useCallback((session: Session) => {
665	    const restoredEvents = session.events || []
666	    const restoredNodes = cleanGraphNodes(session.graphNodes || [])
667	    const restoredLinks = cleanGraphLinks(session.graphLinks || [])
668	    setActiveSessionId(session.id)
669	    setGoal(session.goal)
670	    setProvider(session.config?.provider || session.provider)
671	    setModel(session.config?.model || "")
672	    setJuryModel(session.config?.juryModel || "")
673	    if (session.config) {
674	      setConsortiumSize(session.config.consortiumSize)
675	      setJurySize(session.config.jurySize)
676	      setMaxDepth(session.config.maxDepth)
677	      setMaxParallelChildren(session.config.maxParallelChildren || 4)
678	      setMaxNodesTotal(session.config.maxNodesTotal)
679	      setForceRecursive(session.config.forceRecursive)
680	      setPlanGovernance(session.config.planGovernance || "auto")
681	      setPlanRecovery(session.config.planRecovery || "off")
682	      setToolsEnabled(session.config.toolsEnabled)
683	      setMultiModel(session.config.multiModel)
684	      setConsortiumSlots(session.config.consortiumSlots || [])
685	      setJurySlots(session.config.jurySlots || [])
686	      setTierRouting(session.config.tierRouting || false)
687	      setLeafSlots(session.config.leafSlots || [])
688	      setMidSlots(session.config.midSlots || [])
689	      setRootSlots(session.config.rootSlots || [])
690	      setDomainOverride(session.config.domainOverride || "")
691	      setSystemPrompt(session.config.systemPrompt || "")
692	    }
693	    setRunId(session.runId || null)
694	    setRunToken(session.runToken || null)
695	    setRunStatus((session.status as typeof runStatus) || "idle")
696	    setEvents(restoredEvents)
697	    graphNodesRef.current = restoredNodes
698	    graphLinksRef.current = restoredLinks
699	    setGraphNodes(restoredNodes)
700	    setGraphLinks(restoredLinks)
701	    setNodeOutputs(outputRecordToMap(session.nodeOutputs))
702	    setRunResult(session.result || session.output || null)
703	    setDetectedDomain(session.domain || null)
704	    setSelectedNode(null)
705	    setClarifyQuestion(null)
706	    setPendingPlan(null)
707	    setNodeCount(session.nodeCount || restoredNodes.filter(n => n.type === "raf-node").length)
708	    setCurrentPhase(session.currentPhase || (session.status === "running" ? "Running" : "Idle"))
709	    runStartRef.current = restoredEvents.find(ev => ev.timestamp)?.timestamp
710	      ? (restoredEvents.find(ev => ev.timestamp)!.timestamp! * 1000)
711	      : null
712	    seenEventsRef.current = new Set(restoredEvents.map(ev => `${ev.event ?? ev.status ?? ""}:${ev.node_id ?? ""}:${String(ev.timestamp ?? "")}`))
713	    satelliteEventsRef.current = restoredEvents.filter(ev => ev.event === "consortium_candidates" || ev.event === "jury_votes")
714	    planChildrenRef.current = {}
715	    planChildNodeRef.current = {}
716	    nodeCreatedTsRef.current = {}
717	    restoredEvents.forEach(ev => {
718	      if ((ev.event === "plan_selected" || ev.event === "plan_ready") && ev.node_id && ev.children) {
719	        planChildrenRef.current[ev.node_id] = ev.children
720	      }
721	      if (ev.event === "node_created" && ev.node_id) {
722	        if (ev.timestamp) nodeCreatedTsRef.current[ev.node_id] = ev.timestamp
723	        if (ev.parent_id && ev.plan_child_id) {
724	          planChildNodeRef.current[`${ev.parent_id}:${ev.plan_child_id}`] = ev.node_id
725	        }
726	      }
727	    })
728	  }, [])
729	
730	  // add node to graph — idempotent: silently skips if id already exists
731	  const addGraphNode = useCallback((id: string, parentId: string | null | undefined, depth: number, goal?: string, type: GraphNode["type"] = "raf-node") => {
732	    if (graphNodesRef.current.some(n => n.id === id)) return
733	    const parent = parentId ? graphNodesRef.current.find(n => n.id === parentId) : null
734	    const node: GraphNode = {
735	      id, type,
736	      label: id === "root" ? "root" : id.replace("node-", "#"),
737	      detail: goal ? goal.slice(0, 60) : id,
738	      active: true, depth, goal,
739	      ...(parent && parent.x !== undefined ? {
740	        x: parent.x + (Math.random() - 0.5) * 60,
741	        y: parent.y! + 80,
742	      } : {}),
743	    }
744	    graphNodesRef.current = [...graphNodesRef.current, node]
745	    if (parentId) {
746	      const linkId = `${parentId}->${id}`
747	      if (!graphLinksRef.current.some(l => l.id === linkId)) {
748	        graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: parentId, target: id, edgeType: "parallel" }]
749	      }
750	    }
751	    setGraphNodes([...graphNodesRef.current])
752	    setGraphLinks([...graphLinksRef.current])
753	  }, [])
754	
755	  // add consortium/jury satellite nodes for a single event (used by both live and replay)
756	  // Pattern: RAF-node → consortium-group → agent-proposal (× N)
757	  //          RAF-node → jury-group       → juror-vote    (× N)
758	  const addSatelliteNodes = useCallback((ev: RafEvent) => {
759	    if (!ev.node_id) return
760	    const task = ev.task || ""
761	    const parentDepth = graphNodesRef.current.find(n => n.id === ev.node_id)?.depth ?? 0
762	
763	    if (ev.event === "consortium_candidates") {
764	      const candidates = (ev as any).candidates as any[] || []
765	      const groupId = `${ev.node_id}-consortium-${task}`
766	      // Create consortium-group node attached to the RAF node
767	      if (!graphNodesRef.current.some(n => n.id === groupId)) {
768	        const parent = graphNodesRef.current.find(n => n.id === ev.node_id)
769	        const groupNode: GraphNode = {
770	          id: groupId, type: "consortium-group",
771	          label: "C", detail: `Consortium (${task})`,
772	          active: true, depth: parentDepth + 1,
773	          ownerNodeId: ev.node_id, task,
774	          hint: task,
775	          ...(parent?.x !== undefined ? { x: parent.x + (Math.random() - 0.5) * 40, y: parent.y! + 60 } : {}),
776	        }
777	        graphNodesRef.current = [...graphNodesRef.current, groupNode]
778	        const linkId = `${ev.node_id}->${groupId}`
779	        if (!graphLinksRef.current.some(l => l.id === linkId)) {
780	          graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: ev.node_id!, target: groupId, edgeType: "flow" }]
781	        }
782	      }
783	      // Create agent-proposal nodes attached to the group
784	      candidates.forEach((cand: any, idx: number) => {
785	        const agentId = `${ev.node_id}-agent-${task}-${idx}`
786	        if (!graphNodesRef.current.some(n => n.id === agentId)) {
787	          const groupNode = graphNodesRef.current.find(n => n.id === groupId)
788	          const payload = cand?.payload || cand || {}
789	          const hint = payload.output ? payload.output.slice(0, 40) : payload.mode || `Agent ${idx + 1}`
790	          const agentNode: GraphNode = {
791	            id: agentId, type: "agent-proposal",
792	            label: `A${idx + 1}`, detail: hint,
793	            active: true, depth: parentDepth + 2,
794	            ownerNodeId: ev.node_id, task, candidateIndex: idx,
795	            hint,
796	            ...(groupNode?.x !== undefined ? { x: groupNode.x + (idx - (candidates.length - 1) / 2) * 30, y: groupNode.y! + 50 } : {}),
797	          }
798	          graphNodesRef.current = [...graphNodesRef.current, agentNode]
799	          const linkId = `${groupId}->${agentId}`

---

## Claude

Good, I have enough context. Let me now design a proper plan for both features.

---

## Subagent Output

Now I have a complete picture of the codebase. Let me compile the implementation plan.

---

## Implementation Plan

### Recommendation: Implement Feature 2 (Pipelines) First

Feature 2 is simpler, purely additive, and will validate the session-tab and multi-run patterns that Feature 1 also needs. Pipelines have zero backend risk (the frontend can orchestrate them entirely), whereas forking touches the engine's execution model and requires care. Build pipelines first, ship them, then tackle the more complex fork semantics.

---

## Feature 1: Run Forking

### How it actually works (the key constraint honoured)

The engine cannot re-enter mid-run state. A fork is a new full RAF run whose `goal` string is constructed as:

```
[FORK CONTEXT]
The following sub-goals were already completed in the parent run:
<ancestor node_created goals, in order>
The parent node produced this partial output:
<node's output from nodeOutputs>

[NEW SUB-GOAL]
<user-edited or original goal for the clicked node>
```

The backend endpoint finds the clicked node's `node_created` event, walks the ancestor chain through the event log, collects completed sibling context, and injects it as a prefix. The forked run starts from scratch as a real run but with that richer goal context.

### Step 1: Backend — `POST /api/run/{run_id}/fork`

**File: `server/main.py`**

Add a `ForkRequest` Pydantic model and the endpoint. The endpoint logic:

1. Validates the run token via `_require_run_token`.
2. Calls a new `RunManager.fork_run()` method.
3. Returns `{"run_id": fork_run_id, "access_token": fork_token}`.

```python
class ForkRequest(BaseModel):
    node_id: str
    goal: str | None = None        # override; None = use original node goal
    x_run_token: str | None = None # passed as header

@app.post("/api/run/{run_id}/fork")
def fork_run(run_id: str, body: ForkRequest, x_run_token: str | None = Header(default=None)) -> Dict[str, Any]:
    parent_state = _require_run_token(run_id, x_run_token)
    fork_state = manager.fork_run(parent_state, body.node_id, body.goal)
    if fork_state is None:
        raise HTTPException(status_code=404, detail="node_id not found in run events")
    return {"run_id": fork_state.run_id, "access_token": fork_state.access_token}
```

**File: `server/run_manager.py`**

Add `fork_run()` to `RunManager`. This method:

1. Scans `parent_state.events` for the `node_created` event matching `node_id`.
2. Collects all preceding `node_created` events (ancestors) — these are all events with `event == "node_created"` whose `timestamp` is earlier than the target node's timestamp.
3. Looks for a `node_done` event for the target `node_id` to get its prior output if it was completed (used as context).
4. Builds the enriched goal string.
5. Calls `create_run()` with the enriched goal and the same provider/model config as the parent.

The enriched goal format:
```python
def _build_fork_goal(parent_events, node_id, override_goal):
    # Find the target node_created event
    target_event = next(
        (e for e in parent_events if e.get("event") == "node_created" and e.get("node_id") == node_id),
        None
    )
    if target_event is None:
        return None, None
    
    original_goal = target_event.get("goal", "")
    fork_goal = override_goal or original_goal
    
    # Collect ancestor goals (nodes at smaller depth, created before this node)
    target_ts = target_event.get("timestamp", 0)
    target_depth = target_event.get("depth", 0)
    
    ancestor_goals = [
        e.get("goal", "")
        for e in parent_events
        if e.get("event") == "node_created"
        and e.get("timestamp", 0) < target_ts
        and e.get("depth", 99) < target_depth
    ]
    
    # Get prior output of this node if it was already done
    prior_output = next(
        (e.get("output", "") for e in parent_events
         if e.get("event") == "node_done" and e.get("node_id") == node_id),
        None
    )
    
    context_parts = []
    if ancestor_goals:
        context_parts.append("FORK CONTEXT — ancestor tasks already completed:")
        for g in ancestor_goals:
            context_parts.append(f"  - {g}")
    if prior_output:
        context_parts.append(f"\nPrior attempt output for this node:\n{prior_output[:1000]}")
    
    if context_parts:
        enriched = "\n".join(context_parts) + f"\n\nSUB-GOAL (this fork):\n{fork_goal}"
    else:
        enriched = fork_goal
    
    return enriched, original_goal
```

Add a `fork_source` field to `RunState` (optional `str`, stores parent `run_id`) for lineage tracking. This is a single extra field on the dataclass with `fork_source: Optional[str] = None`.

The `fork_run()` method returns `None` if `node_id` is not found so the endpoint can 404 cleanly.

### Step 2: Frontend — Fork Dialog

**File: `web/src/App.tsx`**

Add state and handler:

```typescript
// New state near selectedNode
const [forkDialogNode, setForkDialogNode] = useState<GraphNode | null>(null)
const [forkGoalOverride, setForkGoalOverride] = useState("")
const [forkLoading, setForkLoading] = useState(false)
```

Modify `onNodeClick` handler. Currently it sets `selectedNode`. Add a check: if the clicked node has `phase === "Done"` and `type === "raf-node"`, also set `forkDialogNode`:

```typescript
const handleNodeClick = useCallback((node: GraphNode) => {
  setSelectedNode(node)
  // Fork is only offered on completed raf-nodes
  if (node.type === "raf-node" && !node.active && node.success) {
    setForkDialogNode(node)
    setForkGoalOverride(node.goal || "")
  }
}, [])
```

Add a `forkRun` async function:

```typescript
const forkRun = async () => {
  if (!forkDialogNode || !runId) return
  setForkLoading(true)
  try {
    const res = await fetch(`${API_BASE}/api/run/${runId}/fork`, {
      method: "POST",
      headers: authHeaders(runToken, true),
      body: JSON.stringify({ node_id: forkDialogNode.id, goal: forkGoalOverride || null })
    })
    if (!res.ok) throw new Error(`Fork failed: ${res.status}`)
    const data = await res.json() as { run_id: string; access_token: string }
    
    // Open the fork as a new session
    const forkSessionId = `fork-${Date.now()}-${Math.random().toString(36).slice(2,6)}`
    const forkGoal = forkGoalOverride || forkDialogNode.goal || ""
    setSessions(prev => [{
      id: forkSessionId,
      goal: `[FORK] ${forkGoal.slice(0, 60)}`,
      provider,
      status: "running",
      ts: Date.now(),
      nodeCount: 0,
      runId: data.run_id,
      runToken: data.access_token,
      currentPhase: "Starting",
      config: currentConfig(),
      events: [], graphNodes: [], graphLinks: [], nodeOutputs: {},
    }, ...prev.slice(0, 19)])
    
    // Switch to the new fork session and connect its websocket
    setForkDialogNode(null)
    // Reset all run state, set active session, connect WS
    // ... (same pattern as startRun, but using data.run_id / data.access_token directly)
    loadForkSession(data.run_id, data.access_token, forkSessionId, forkGoal)
  } catch (err) {
    // show error in dialog
  } finally {
    setForkLoading(false)
  }
}
```

The `loadForkSession` function follows the same pattern as the `continueSession=false` branch of `startRun`: resets graph state, sets `runId`/`runToken`, connects WS.

**Fork Dialog JSX** — A small modal rendered near the node inspector panel (not a full-screen modal; more like an inline panel):

```tsx
{forkDialogNode && (
  <div className="fixed bottom-6 right-6 z-50 w-80 rounded-xl border border-primary/40 bg-card shadow-2xl p-4 space-y-3">
    <div className="flex items-center justify-between">
      <span className="text-sm font-semibold text-primary">Fork from node</span>
      <button onClick={() => setForkDialogNode(null)} className="text-muted-foreground hover:text-foreground">✕</button>
    </div>
    <p className="text-[10px] text-muted-foreground truncate">Node: {forkDialogNode.id}</p>
    <Textarea
      value={forkGoalOverride}
      onChange={e => setForkGoalOverride(e.target.value)}
      placeholder="Edit goal for this fork..."
      className="text-xs min-h-[80px]"
    />
    <Button onClick={forkRun} disabled={forkLoading} className="w-full text-xs gap-2">
      {forkLoading ? "Forking..." : "Fork from here"}
    </Button>
  </div>
)}
```

### Step 3: Session Type Extension

**File: `web/src/App.tsx`** — Extend the `Session` type:

```typescript
type Session = {
  // ... existing fields ...
  forkSourceRunId?: string    // if this session is a fork
  forkSourceNodeId?: string   // which node was forked
}
```

Sessions list items should show a fork badge when `forkSourceRunId` is set.

### Edge Cases

- **Node still running**: The `onNodeClick` fork dialog only appears if `!node.active && node.success` — no fork offered on active nodes.
- **node_id not found**: Backend returns 404; frontend shows an error inside the dialog.
- **Parent run evicted from memory**: The fork endpoint will fail with 404 run; the frontend needs to show a clear message: "Parent run is no longer in server memory. Re-run and fork immediately after completion."
- **Forked run token**: The forked run has its own fully independent `access_token`. No special handling needed beyond storing it in the session.
- **Goal too long after enrichment**: Clamp `prior_output` to 1000 chars, ancestor list to 5 entries (most recent ancestors only).

---

## Feature 2: Goal Chaining / Pipelines

### Architecture Decision: Frontend-Orchestrated

Use frontend orchestration. The backend does not need a new `/api/pipeline` endpoint. Rationale:
- Each pipeline step is just a `POST /api/run` — the contract already exists.
- Server-side pipeline management would require another `RunState`-like object, persistence for the pipeline state, and handling of partial failures — all new backend surface area.
- The frontend already manages multi-session state in localStorage and can sequence calls trivially.
- The one weakness (browser tab closed mid-pipeline) is acceptable for this use case and can be noted as a known limitation.

### Step 1: Type Definitions

**File: `web/src/App.tsx`** — Add new types near the existing type section:

```typescript
type PipelineStep = {
  id: string         // stable local id, e.g. `step-${i}`
  goalTemplate: string  // may contain {{output}} placeholder
  status: "pending" | "running" | "done" | "error" | "skipped"
  runId?: string
  runToken?: string
  output?: string
  error?: string
  sessionId?: string  // links to the session created for this step
}

type Pipeline = {
  id: string
  name: string
  steps: PipelineStep[]
  status: "idle" | "running" | "done" | "error"
  currentStepIndex: number
  createdAt: number
}
```

Add to App component state:

```typescript
const [pipelines, setPipelines] = useState<Pipeline[]>([])
const [activePipelineId, setActivePipelineId] = useState<string | null>(null)
const pipelineRunningRef = useRef(false)
```

### Step 2: Pipeline Panel Component

**New file: `web/src/components/PipelinePanel.tsx`**

This is a self-contained React component that receives props from `App.tsx`:

```typescript
interface PipelinePanelProps {
  pipelines: Pipeline[]
  activePipelineId: string | null
  onCreatePipeline: () => void
  onSelectPipeline: (id: string) => void
  onAddStep: (pipelineId: string) => void
  onUpdateStep: (pipelineId: string, stepId: string, goalTemplate: string) => void
  onDeleteStep: (pipelineId: string, stepId: string) => void
  onMoveStep: (pipelineId: string, stepId: string, direction: 'up' | 'down') => void
  onRunPipeline: (pipelineId: string) => void
  onCancelPipeline: (pipelineId: string) => void
  onViewStepSession: (sessionId: string) => void
  provider: string
  model: string
  running: boolean
}
```

The UI layout:
- Top section: list of saved pipelines (name, step count, status badge). Clicking selects it.
- "New Pipeline" button.
- Bottom section: for the active pipeline, a list of steps where each is an editable `Textarea` for the goal template. An `{{output}}` helper badge shows next to steps 2+ as a reminder. Drag handles for reorder (optional: use up/down buttons instead for simplicity).
- "Run Pipeline" button at the bottom. Disabled while any step is `"running"`.
- Per-step status badge and "View" button that calls `onViewStepSession`.

### Step 3: Pipeline Execution Logic

**File: `web/src/App.tsx`** — The `runPipeline` function:

```typescript
const runPipeline = async (pipelineId: string) => {
  const pipeline = pipelines.find(p => p.id === pipelineId)
  if (!pipeline || pipeline.status === "running") return
  
  pipelineRunningRef.current = true
  let previousOutput = ""
  
  setPipelines(prev => prev.map(p => p.id === pipelineId
    ? { ...p, status: "running", currentStepIndex: 0,
        steps: p.steps.map(s => ({ ...s, status: "pending", output: undefined, error: undefined })) }
    : p))
  
  for (let i = 0; i < pipeline.steps.length; i++) {
    if (!pipelineRunningRef.current) break  // cancelled
    
    const step = pipeline.steps[i]
    // Inject {{output}} from previous step
    const resolvedGoal = step.goalTemplate.replace(/\{\{output\}\}/g, previousOutput)
    
    // Mark step as running
    setPipelines(prev => prev.map(p => p.id === pipelineId
      ? { ...p, currentStepIndex: i,
          steps: p.steps.map((s, idx) => idx === i ? { ...s, status: "running" } : s) }
      : p))
    
    // Create a session for this step
    const stepSessionId = `pipeline-${pipelineId}-step-${i}-${Date.now()}`
    const stepGoal = resolvedGoal
    
    setSessions(prev => [{
      id: stepSessionId,
      goal: stepGoal,
      provider,
      status: "running",
      ts: Date.now(),
      nodeCount: 0,
      currentPhase: "Starting",
      config: currentConfig(),
      events: [], graphNodes: [], graphLinks: [], nodeOutputs: {},
    }, ...prev.slice(0, 19)])
    
    try {
      // POST /api/run
      const body = buildRunBody(stepGoal)  // extracted helper from startRun logic
      const res = await fetch(`${API_BASE}/api/run`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json() as { run_id: string; access_token: string }
      
      // Update the step with run info
      setPipelines(prev => prev.map(p => p.id === pipelineId
        ? { ...p, steps: p.steps.map((s, idx) => idx === i
            ? { ...s, runId: data.run_id, runToken: data.access_token, sessionId: stepSessionId }
            : s) }
        : p))
      
      // Wait for run_done by polling /api/run/{run_id}/events every 2s
      // OR connect a WebSocket and wait for run_done message
      const stepOutput = await waitForRunDone(data.run_id, data.access_token)
      previousOutput = stepOutput || ""
      
      // Mark step done
      setPipelines(prev => prev.map(p => p.id === pipelineId
        ? { ...p, steps: p.steps.map((s, idx) => idx === i
            ? { ...s, status: "done", output: stepOutput } : s) }
        : p))
      
    } catch (err) {
      setPipelines(prev => prev.map(p => p.id === pipelineId
        ? { ...p, status: "error",
            steps: p.steps.map((s, idx) => idx === i
              ? { ...s, status: "error", error: String(err) } : s) }
        : p))
      pipelineRunningRef.current = false
      return
    }
  }
  
  pipelineRunningRef.current = false
  setPipelines(prev => prev.map(p => p.id === pipelineId
    ? { ...p, status: "done" } : p))
}
```

The `waitForRunDone` helper uses a WebSocket (same pattern as `connectWs`):

```typescript
const waitForRunDone = (runId: string, token: string): Promise<string> => {
  return new Promise((resolve, reject) => {
    const wsUrl = API_BASE.replace(/^http/, "ws") + `/api/stream/${runId}?token=${encodeURIComponent(token)}`
    const ws = new WebSocket(wsUrl)
    ws.onmessage = (msg) => {
      try {
        const ev = JSON.parse(msg.data)
        if (ev.event === "run_done") {
          ws.close()
          if (ev.error) reject(new Error(ev.error))
          else resolve(ev.result?.output || "")
        }
      } catch {}
    }
    ws.onerror = () => reject(new Error("WebSocket error"))
    // 10 minute timeout guard
    const timeout = setTimeout(() => { ws.close(); reject(new Error("Timeout")) }, 600_000)
    ws.onclose = () => clearTimeout(timeout)
  })
}
```

### Step 4: Pipeline Persistence

**File: `web/src/App.tsx`**

Add a `PIPELINE_STORAGE_KEY` and persist pipelines to `localStorage`. Pipelines are stored without the live `status` field (always reset to `"idle"` on load) so stale "running" states never persist:

```typescript
const PIPELINE_STORAGE_KEY = "raf-web-pipelines-v1"

// On load:
const [pipelines, setPipelines] = useState<Pipeline[]>(() => {
  try {
    const raw = localStorage.getItem(PIPELINE_STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return (parsed as Pipeline[]).map(p => ({
      ...p,
      status: "idle",
      steps: p.steps.map(s => ({ ...s, status: "pending", output: undefined, error: undefined }))
    }))
  } catch { return [] }
})

// Persist on change:
useEffect(() => {
  try { localStorage.setItem(PIPELINE_STORAGE_KEY, JSON.stringify(pipelines.slice(0, 10))) }
  catch {}
}, [pipelines])
```

### Step 5: Pipeline Tab in the Sidebar

**File: `web/src/App.tsx`**

Add `"pipeline"` to the sidebar tab union type:

```typescript
const [sidebarTab, setSidebarTab] = useState<"sessions" | "config" | "pipeline">("sessions")
```

Add a third `TabsTrigger` for "Pipeline" in the `TabsList`. Render `PipelinePanel` inside the new `TabsContent`. Add a pipeline icon in the collapsed sidebar.

The collapsed sidebar icon for pipeline: use a `Network` icon (already imported).

### Edge Cases

- **`{{output}}` in step 1**: Step 1 has no prior output, so `{{output}}` resolves to `""`. This is visible in the UI — show a warning badge on step 1 if it contains `{{output}}`.
- **Pipeline cancelled mid-run**: Set `pipelineRunningRef.current = false`. The currently running step's WebSocket gets orphaned (its run continues on the server). Steps are marked as `"skipped"`. The UI shows a "Cancel" button that just sets the ref — it does not call the backend's `/cancel` for the active run by design (the user may want to inspect the running step's output).
- **Empty goal template**: Validate before running — if any step has an empty `goalTemplate` after `{{output}}` resolution, skip it (mark as "skipped") or block "Run Pipeline".
- **Pipeline with 1 step**: Perfectly valid. The `{{output}}` tag is meaningless on the only step, just runs normally.
- **Very long previous output injected into next goal**: Clamp `previousOutput` to 2000 characters before injection. Add a visible truncation notice.
- **Step fails partway**: Pipeline halts. Remaining steps stay `"pending"`. The user can fix the failing step's goal and re-run (which re-runs from step 1). No resume-from-step-N in this initial implementation — add that later.
- **Browser refresh while pipeline is running**: The pipeline WS is lost. On reload, pipelines come back from localStorage with `status: "idle"`. Running step's server-side run continues independently. This is the known limitation of frontend orchestration.

---

## Implementation Order

### Feature 2 (Pipelines) — 5 steps in order:

1. Add `Pipeline` and `PipelineStep` types to `App.tsx`.
2. Create `web/src/components/PipelinePanel.tsx` with the visual builder (static, no execution yet). Wire it into the sidebar as a third tab.
3. Add pipeline state to `App.tsx`, add localStorage persistence, wire all CRUD callbacks to `PipelinePanel`.
4. Implement `waitForRunDone` helper and `runPipeline` function.
5. Test with 2-step pipeline: `"Write a haiku about {{topic}}"` → `"Translate to French: {{output}}"`.

### Feature 1 (Forking) — 4 steps in order:

1. Backend: add `ForkRequest` model and `POST /api/run/{run_id}/fork` endpoint to `server/main.py`. Add `fork_run()` to `RunManager` and `_build_fork_goal()` helper in `server/run_manager.py`.
2. Add `fork_source` field to `RunState` dataclass.
3. Frontend: add fork dialog state, `forkRun()` function, and `loadForkSession()` helper to `App.tsx`.
4. Wire `onNodeClick` to show the fork dialog only for completed `raf-node` types, render the fork dialog JSX.

---

### Critical Files for Implementation

- `C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\main.py`
- `C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\run_manager.py`
- `C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx`
- `C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\components\ExecutionGraph.tsx`
- `C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\components\PipelinePanel.tsx` (new file to create)

---

## You

[Request interrupted by user]

I want us to go through this step by stpe first , think of what we need to implement in the right order for each of the features and let me know then we would work on how to implement it and the way forward for each but we would start with the first one

---

## Claude

Here's the clear implementation order for **Feature 1: Run Forking** before we touch a single line of code.

---

## Feature 1: Run Forking — Implementation Order

### The key constraint to understand first

The RAF engine runs start-to-finish in a background thread — you can't pause it mid-execution and branch. So a "fork" is not a true engine branch. It's a **new, independent run** whose goal string is enriched with ancestor context extracted from the parent's event log. The forked run starts fresh but knows what came before it.

---

### Step 1 — Backend: `run_manager.py`

Add two things to `RunManager`:

- `_build_fork_goal(parent_events, node_id, override_goal)` — scans the parent's `events` list, finds the clicked `node_created` event, collects ancestor node goals (nodes with smaller depth created before this one), grabs the node's prior output if it already completed, and builds an enriched goal string with that context prefixed
- `fork_run(parent_state, node_id, override_goal)` — calls `_build_fork_goal`, then calls the existing `create_run()` with the enriched goal and the same provider/model/config as the parent. Returns `None` if the `node_id` isn't found

This has to come first because everything else depends on this endpoint existing.

---

### Step 2 — Backend: `main.py`

Add a `ForkRequest` Pydantic model and the `POST /api/run/{run_id}/fork` endpoint. The endpoint:
- validates the run token (same `_require_run_token` pattern already in place)
- calls `manager.fork_run()`
- returns `{ run_id, access_token }` for the new forked run, or 404 if the node wasn't found

---

### Step 3 — Frontend: new state + `forkRun()` function in `App.tsx`

Before touching any JSX, add the fork wiring:
- New state: `forkDialogNode` (the `GraphNode` being forked), `forkGoalOverride` (editable goal text), `forkLoading`
- `forkRun()` async function: POSTs to the new endpoint, creates a new session (same shape as a normal session but with a `[FORK]` label and `forkSourceRunId` / `forkSourceNodeId` fields), switches to it and connects its WebSocket
- Extend the `Session` type with those two optional fork lineage fields

---

### Step 4 — Frontend: wire `onNodeClick` to trigger the fork dialog

Update the existing `handleNodeClick` (or wherever `setSelectedNode` is called) to also set `forkDialogNode` — but only when the clicked node is type `raf-node`, `active === false` (it's done), and `success === true`. Active or errored nodes don't get the fork option.

---

### Step 5 — Frontend: render the fork dialog

A small floating panel (bottom-right, not full-screen modal) with:
- The node ID + truncated original goal as a label
- An editable textarea pre-filled with the original goal so the user can modify it
- A "Fork from here" button that calls `forkRun()`
- A dismiss button
- An inline error message if the fork POST fails (e.g. parent run evicted from server memory)

---

### Key edge cases we'll handle as we go

| Case | Handling |
|------|----------|
| Node still running | Fork dialog only offered when `!node.active` |
| Parent run evicted from server memory | 404 → show clear error in the dialog |
| Prior output too long | Clamp ancestor list to 5 entries, prior output to 1000 chars |
| Fork of a fork | Works naturally — the enriched goal just layers another context block |
| User doesn't change the goal | Fork still runs with the original goal but with enriched ancestor context |

---

That's the full picture. Steps 1 and 2 are pure backend. Steps 3–5 are pure frontend with no backend changes. They can't overlap because the frontend step depends on the endpoint existing.

Want to start with **Step 1** (`run_manager.py`)?

---

## You

ok good i like this give me the code and add comments to it for each implementation , you understand that this is a featurw which we are adding to the current bigger project

---

## Claude

Let me read the remaining parts of App.tsx I haven't seen yet before writing any code.

---

## Subagent Output

800	          if (!graphLinksRef.current.some(l => l.id === linkId)) {
801	            graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: groupId, target: agentId, edgeType: "parallel" }]
802	          }
803	        }
804	      })
805	      setGraphNodes([...graphNodesRef.current])
806	      setGraphLinks([...graphLinksRef.current])
807	    }
808	
809	    if (ev.event === "jury_votes") {
810	      const votes = (ev as any).votes as any[] || []
811	      const winnerId = (ev as any).winner_id as string | undefined
812	      const groupId = `${ev.node_id}-jury-${task}`
813	      // Create jury-group node
814	      if (!graphNodesRef.current.some(n => n.id === groupId)) {
815	        const parent = graphNodesRef.current.find(n => n.id === ev.node_id)
816	        const groupNode: GraphNode = {
817	          id: groupId, type: "jury-group",
818	          label: "J", detail: `Jury (${task})`,
819	          active: true, depth: parentDepth + 1,
820	          ownerNodeId: ev.node_id, task,
821	          hint: `winner: ${winnerId || "?"}`,
822	          ...(parent?.x !== undefined ? { x: parent.x + (Math.random() - 0.5) * 40, y: parent.y! + 60 } : {}),
823	        }
824	        graphNodesRef.current = [...graphNodesRef.current, groupNode]
825	        const linkId = `${ev.node_id}->${groupId}`
826	        if (!graphLinksRef.current.some(l => l.id === linkId)) {
827	          graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: ev.node_id!, target: groupId, edgeType: "flow" }]
828	        }
829	      }
830	      // Create juror-vote nodes
831	      votes.forEach((v: any, idx: number) => {
832	        const jurorId = `${ev.node_id}-juror-${task}-${idx}`
833	        if (!graphNodesRef.current.some(n => n.id === jurorId)) {
834	          const groupNode = graphNodesRef.current.find(n => n.id === groupId)
835	          const vote = v.vote || v
836	          const isWinner = vote.winner_id === winnerId
837	          const hint = vote.winner_id ? `→ ${optionLabel(vote.winner_id)}` : `Juror ${idx + 1}`
838	          const jurorNode: GraphNode = {
839	            id: jurorId, type: "juror-vote",
840	            label: `V${idx + 1}`, detail: hint,
841	            active: false, depth: parentDepth + 2,
842	            ownerNodeId: ev.node_id, task, candidateIndex: idx,
843	            hint,
844	            success: isWinner,
845	            ...(groupNode?.x !== undefined ? { x: groupNode.x + (idx - (votes.length - 1) / 2) * 30, y: groupNode.y! + 50 } : {}),
846	          }
847	          graphNodesRef.current = [...graphNodesRef.current, jurorNode]
848	          const linkId = `${groupId}->${jurorId}`
849	          if (!graphLinksRef.current.some(l => l.id === linkId)) {
850	            graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: groupId, target: jurorId, edgeType: "parallel" }]
851	          }
852	        }
853	      })
854	      // Mark winning agent-proposal if present
855	      if (winnerId) {
856	        const winnerAgentId = `${ev.node_id}-agent-${task}-${winnerId}`
857	        // Try matching by option index embedded in winner_id (e.g. "option-0")
858	        const match = winnerId.match(/(\d+)$/)
859	        if (match) {
860	          const winIdx = parseInt(match[1])
861	          const winAgentId = `${ev.node_id}-agent-${task}-${winIdx}`
862	          graphNodesRef.current = graphNodesRef.current.map(n =>
863	            n.id === winAgentId ? { ...n, success: true, hint: (n.hint || "") + " ✓" } : n
864	          )
865	        } else if (graphNodesRef.current.some(n => n.id === winnerAgentId)) {
866	          graphNodesRef.current = graphNodesRef.current.map(n =>
867	            n.id === winnerAgentId ? { ...n, success: true } : n
868	          )
869	        }
870	      }
871	      setGraphNodes([...graphNodesRef.current])
872	      setGraphLinks([...graphLinksRef.current])
873	    }
874	  }, [addGraphNode])
875	
876	  const updateGraphNode = useCallback((id: string, patch: Partial<GraphNode>) => {
877	    graphNodesRef.current = graphNodesRef.current.map(n => n.id === id ? { ...n, ...patch } : n)
878	    setGraphNodes([...graphNodesRef.current])
879	  }, [])
880	
881	  const addDependencyEdgesForParent = useCallback((parentId: string) => {
882	    const children = planChildrenRef.current[parentId] || []
883	    if (children.length === 0) return
884	    let changed = false
885	    const nextLinks = [...graphLinksRef.current]
886	    for (const child of children) {
887	      const targetNodeId = planChildNodeRef.current[`${parentId}:${child.child_id}`]
888	      if (!targetNodeId) continue
889	      for (const depChildId of child.depends_on || []) {
890	        const sourceNodeId = planChildNodeRef.current[`${parentId}:${depChildId}`]
891	        if (!sourceNodeId) continue
892	        const linkId = `dep:${sourceNodeId}->${targetNodeId}`
893	        if (!nextLinks.some(link => link.id === linkId)) {
894	          nextLinks.push({ id: linkId, source: sourceNodeId, target: targetNodeId, edgeType: "dependency" })
895	          changed = true
896	        }
897	      }
898	    }
899	    if (changed) {
900	      graphLinksRef.current = nextLinks
901	      setGraphLinks([...graphLinksRef.current])
902	    }
903	  }, [])
904	
905	  // process a single event — deduplicated so reconnect replay is idempotent
906	  const processEvent = useCallback((ev: RafEvent) => {
907	    const key = `${ev.event ?? ev.status ?? ""}:${ev.node_id ?? ""}:${String(ev.timestamp ?? "")}`
908	    if (seenEventsRef.current.has(key)) return
909	    seenEventsRef.current.add(key)
910	    setEvents(prev => [...prev, ev])
911	    lastEventTsRef.current = Date.now()
912	    setStaleWarning(false)
913	    const phase = phaseForEvent(ev)
914	    if (phase) setCurrentPhase(phase)
915	    if (phase && ev.node_id) updateGraphNode(ev.node_id, { phase, active: ev.event !== "node_done" })
916	
917	    if (ev.event === "node_created") {
918	      if (ev.timestamp && ev.node_id) nodeCreatedTsRef.current[ev.node_id] = ev.timestamp
919	      addGraphNode(ev.node_id!, ev.parent_id, ev.depth ?? 0, ev.goal)
920	      if (phase && ev.node_id) updateGraphNode(ev.node_id, { phase })
921	      if (ev.parent_id && ev.plan_child_id && ev.node_id) {
922	        planChildNodeRef.current[`${ev.parent_id}:${ev.plan_child_id}`] = ev.node_id
923	        addDependencyEdgesForParent(ev.parent_id)
924	      }
925	      setNodeCount(c => c + 1)
926	    }
927	
928	    if (ev.event === "node_done") {
929	      const id = ev.node_id!
930	      const createdAt = nodeCreatedTsRef.current[id]
931	      const durationMs = createdAt && ev.timestamp ? Math.max(0, Math.round((ev.timestamp - createdAt) * 1000)) : undefined
932	      graphNodesRef.current = graphNodesRef.current.map(n =>
933	        n.id === id ? { ...n, active: false, success: true,
934	          caseType: ev.mode === "recursive" ? "recursive" : "base",
935	          output: ev.output, confidence: ev.confidence, phase: "Done", durationMs } : n
936	      )
937	      setGraphNodes([...graphNodesRef.current])
938	      if (ev.output) {
939	        setNodeOutputs(prev => new Map(prev).set(id, {
940	          output: ev.output!, mode: ev.mode || "base",
941	          confidence: ev.confidence || 0, goal: ev.goal,
942	        }))
943	      }
944	    }
945	
946	    if (ev.event === "mode_decided") {
947	      const id = ev.node_id!
948	      graphNodesRef.current = graphNodesRef.current.map(n =>
949	        n.id === id ? { ...n, caseType: (ev.winner === "recursive" || (ev as any).mode === "recursive") ? "recursive" : "base", phase: phase || n.phase } : n
950	      )
951	      setGraphNodes([...graphNodesRef.current])
952	    }
953	
954	    if (ev.event === "spec_extracted") {
955	      if ((ev as any).domain) setDetectedDomain((ev as any).domain)
956	    }
957	
958	    if (ev.event === "run_done") {
959	      isRunningRef.current = false
960	      const st = (ev as any).status
961	      setRunStatus(ev.error ? "error" : st === "cancelled" ? "cancelled" : "done")
962	      const result = (ev as any).result
963	      if (result?.output) { setRunResult(result.output); setCenterTab("output") }
964	      if (result?.metadata?.mode === "clarify") {
965	        const q = result.metadata.questions?.[0]
966	        if (q) setClarifyQuestion(q)
967	      }
968	      setActiveSessionId(prev => {
969	        if (prev) {
970	          const finalSt = ev.error ? "error" : st === "cancelled" ? "cancelled" : "done"
971	          setSessions(ss => ss.map(s => s.id === prev ? { ...s, status: finalSt, output: result?.output } : s))
972	        }
973	        return prev
974	      })
975	    }
976	
977	    if (ev.event === "child_failed") {
978	      setPartialFailures(prev => prev + 1)
979	    }
980	
981	    // Plan recovery: create visual nodes for each attempt so the graph shows the history
982	    if (ev.event === "plan_validation_failed" && ev.node_id) {
983	      const attempt = ev.plan_attempt ?? 0
984	      const failId = `${ev.node_id}-plan-fail-${attempt}`
985	      if (!graphNodesRef.current.some(n => n.id === failId)) {
986	        const parent = graphNodesRef.current.find(n => n.id === ev.node_id)
987	        graphNodesRef.current = [...graphNodesRef.current, {
988	          id: failId, type: "referee-check" as const,
989	          label: `PF${attempt}`, detail: "Plan failed validation",
990	          active: false, success: false,
991	          depth: (parent?.depth ?? 0) + 1,
992	          ownerNodeId: ev.node_id, task: "plan_validation_failed",
993	          hint: ev.reason ? ev.reason.slice(0, 30) : "validation failed",
994	          ...(parent?.x !== undefined ? { x: parent.x + (attempt - 1) * 50, y: parent.y! + 70 } : {}),
995	        }]
996	        const linkId = `${ev.node_id}->${failId}`
997	        if (!graphLinksRef.current.some(l => l.id === linkId)) {
998	          graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: ev.node_id!, target: failId, edgeType: "flow" as const }]
999	        }
1000	        setGraphNodes([...graphNodesRef.current])
1001	        setGraphLinks([...graphLinksRef.current])
1002	      }
1003	    }
1004	
1005	    if (ev.event === "plan_abandoned" && ev.node_id) {
1006	      updateGraphNode(ev.node_id, { phase: "Plan abandoned", success: false })
1007	    }
1008	
1009	    if (ev.event === "plan_replaced" && ev.node_id) {
1010	      updateGraphNode(ev.node_id, { phase: "Plan replaced" })
1011	    }
1012	
1013	    if (ev.event === "merge_done" && ev.node_id) {
1014	      const mergeId = `${ev.node_id}-merge`
1015	      if (!graphNodesRef.current.some(n => n.id === mergeId)) {
1016	        const parentNode = graphNodesRef.current.find(n => n.id === ev.node_id)
1017	        const mergeNode: GraphNode = {
1018	          id: mergeId, type: "merge-group",
1019	          label: "M", detail: "Merge",
1020	          active: false, depth: (parentNode?.depth ?? 0) + 1,
1021	          ownerNodeId: ev.node_id, task: "merge",
1022	          hint: "merge",
1023	          success: true,
1024	          ...(parentNode?.x !== undefined ? { x: parentNode.x, y: parentNode.y! + 70 } : {}),
1025	        }
1026	        graphNodesRef.current = [...graphNodesRef.current, mergeNode]
1027	        // Flow edge from parent to merge-group
1028	        const flowLinkId = `${ev.node_id}->${mergeId}`
1029	        if (!graphLinksRef.current.some(l => l.id === flowLinkId)) {
1030	          graphLinksRef.current = [...graphLinksRef.current, { id: flowLinkId, source: ev.node_id!, target: mergeId, edgeType: "flow" }]
1031	        }
1032	        // Merge (backflow) edges from each completed child to merge-group
1033	        const children = planChildrenRef.current[ev.node_id] || []
1034	        for (const child of children) {
1035	          const childNodeId = planChildNodeRef.current[`${ev.node_id}:${child.child_id}`]
1036	          if (childNodeId) {
1037	            const mergeLinkId = `merge:${childNodeId}->${mergeId}`
1038	            if (!graphLinksRef.current.some(l => l.id === mergeLinkId)) {
1039	              graphLinksRef.current = [...graphLinksRef.current, { id: mergeLinkId, source: childNodeId, target: mergeId, edgeType: "merge" }]
1040	            }
1041	          }
1042	        }
1043	        setGraphNodes([...graphNodesRef.current])
1044	        setGraphLinks([...graphLinksRef.current])
1045	      }
1046	    }
1047	
1048	    // plan_ready is the real backend event name
1049	    if ((ev.event === "plan_ready" || ev.event === "plan_selected") && ev.node_id) {
1050	      const kids = (ev as any).children as ChildSpec[] | undefined
1051	      if (kids) {
1052	        planChildrenRef.current[ev.node_id] = kids
1053	        addDependencyEdgesForParent(ev.node_id)
1054	        if (ev.event === "plan_ready") setPendingPlan({ nodeId: ev.node_id!, children: kids })
1055	      }
1056	    }
1057	
1058	    // Store satellite events regardless of mode so toggling to "full" can replay them
1059	    if ((ev.event === "consortium_candidates" || ev.event === "jury_votes") && ev.node_id) {
1060	      satelliteEventsRef.current = [...satelliteEventsRef.current, ev]
1061	    }
1062	    // Add satellite nodes now only if already in full mode
1063	    if (graphModeRef.current === "full") {
1064	      addSatelliteNodes(ev)
1065	    }
1066	  }, [addGraphNode, updateGraphNode, addDependencyEdgesForParent])
1067	
1068	  // websocket connection
1069	  const connectWs = useCallback((rid: string, token: string) => {
1070	    if (wsRef.current) { wsRef.current.onclose = null; wsRef.current.close() }
1071	    const wsUrl = API_BASE.replace(/^http/, "ws") + `/api/stream/${rid}?token=${encodeURIComponent(token)}`
1072	    const ws = new WebSocket(wsUrl)
1073	    wsRef.current = ws
1074	    ws.onopen = () => { reconnectAttemptsRef.current = 0 }
1075	    ws.onmessage = (msg) => {
1076	      try {
1077	        const ev: RafEvent = JSON.parse(msg.data)
1078	        if (ev.event === "run_started" && !runStartRef.current) runStartRef.current = Date.now()
1079	        processEvent(ev)
1080	      } catch {}
1081	    }
1082	    ws.onclose = () => {
1083	      if (!isRunningRef.current) return
1084	      const attempts = reconnectAttemptsRef.current
1085	      if (attempts >= 6) return
1086	      reconnectAttemptsRef.current = attempts + 1
1087	      setTimeout(() => { if (isRunningRef.current) connectWs(rid, token) }, Math.min(500 * Math.pow(2, attempts), 16000))
1088	    }
1089	  }, [processEvent])
1090	
1091	  // start run
1092	  // continueSession=true: clarification continuation — preserve existing timeline/graph,
1093	  // just append new events. Does NOT create a new session entry.
1094	  const startRun = async (goalText: string, skipClarify = false, continueSession = false) => {
1095	    if (!goalText.trim()) return
1096	    const runGoal = goalText.trim()
1097	
1098	    if (!continueSession) {
1099	      graphNodesRef.current = []; graphLinksRef.current = []

---

## Subagent Output

1100	      seenEventsRef.current = new Set()
1101	      satelliteEventsRef.current = []
1102	      planChildrenRef.current = {}
1103	      planChildNodeRef.current = {}
1104	      nodeCreatedTsRef.current = {}
1105	      setGraphNodes([]); setGraphLinks([]); setEvents([]); setNodeOutputs(new Map())
1106	      setRunResult(null); setDetectedDomain(null); setSelectedNode(null)
1107	      setPendingPlan(null); setNodeCount(0)
1108	      setCurrentPhase("Starting")
1109	      setRunToken(null)
1110	      setPartialFailures(0); setStaleWarning(false); setLastEventAge(null)
1111	      lastEventTsRef.current = 0
1112	      runStartRef.current = null
1113	      const sessionId = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
1114	      const sessionProviderLabel = multiModel
1115	        ? `multi · ${(consortiumSlots[0]?.model || "").split("/").pop() || consortiumSlots[0]?.provider || "multi-model"}`
1116	        : `${provider}${model ? ` · ${(model.split("/").pop() || model).replace(/:.*$/, "")}` : ""}`
1117	      setSessions(prev => [{
1118	        id: sessionId, goal: runGoal, provider, providerLabel: sessionProviderLabel, status: "running", ts: Date.now(), nodeCount: 0,
1119	        currentPhase: "Starting", config: currentConfig(), events: [], graphNodes: [], graphLinks: [], nodeOutputs: {},
1120	      }, ...prev.slice(0, 19)])
1121	      setActiveSessionId(sessionId)
1122	    } else {
1123	      // Clarification continuation: only reset seenEvents so the new run's
1124	      // events are not blocked, but keep graph/timeline visible.
1125	      seenEventsRef.current = new Set()
1126	      setPendingPlan(null)
1127	      setPartialFailures(0); setStaleWarning(false); setLastEventAge(null)
1128	      lastEventTsRef.current = 0
1129	      setCurrentPhase("Continuing")
1130	    }
1131	
1132	    isRunningRef.current = true
1133	    setRunStatus("running"); setCenterTab("timeline")
1134	
1135	    const body: Record<string, unknown> = {
1136	      goal: runGoal, provider, model: model || null, jury_model: juryModel || null,
1137	      consortium_size: consortiumSize, jury_size: jurySize,
1138	      max_depth: maxDepth, max_parallel_children: maxParallelChildren, max_nodes_total: maxNodesTotal,
1139	      plan_approval_required: planGovernance === "manual", tools_enabled: toolsEnabled,
1140	      plan_recovery: planRecovery,
1141	      max_plan_retries: 2,
1142	      force_recursive: forceRecursive, skip_clarify: skipClarify,
1143	      domain: domainOverride || null, system_prompt: systemPrompt || null,
1144	      api_key: provider !== "mock" && apiKey ? apiKey : null,
1145	    }
1146	    if (multiModel && consortiumSlots.length > 0) body.consortium_agents = consortiumSlots
1147	    if (multiModel && jurySlots.length > 0) body.jury_agents = jurySlots
1148	    // Tier routing overrides: send tier slots when tier routing is enabled
1149	    if (multiModel && tierRouting) {
1150	      if (leafSlots.length > 0) body.leaf_agents = leafSlots
1151	      if (midSlots.length > 0) body.mid_agents = midSlots
1152	      if (rootSlots.length > 0) body.root_agents = rootSlots
1153	    }
1154	
1155	    try {
1156	      const res = await fetch(`${API_BASE}/api/run`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
1157	      if (!res.ok) throw new Error(`Server error ${res.status}`)
1158	      const data = await res.json() as { run_id: string; access_token?: string }
1159	      if (!data.access_token) throw new Error("Server did not return a run access token")
1160	      setRunId(data.run_id)
1161	      setRunToken(data.access_token)
1162	      connectWs(data.run_id, data.access_token)
1163	    } catch (err) {
1164	      setRunStatus("error")
1165	      setEvents([{ event: "run_done", error: String(err) }])
1166	      isRunningRef.current = false
1167	    }
1168	  }
1169	
1170	  const cancelRun = async () => {
1171	    if (!runId) return
1172	    // Keep isRunningRef=true so reconnect can still fire and receive the
1173	    // authoritative run_done { status: "cancelled" } from the server.
1174	    await fetch(`${API_BASE}/api/run/${runId}/cancel`, { method: "POST", headers: authHeaders(runToken) }).catch(() => {})
1175	  }
1176	
1177	  const updateConsortiumSlot = (index: number, patch: Partial<AgentSlot>) => {
1178	    setAppliedStrategy(null) // manual edit clears the preset
1179	    setConsortiumSlots(prev => normalizeSlots(prev, consortiumSize, provider, model).map((slot, i) => i === index ? { ...slot, ...patch } : slot))
1180	  }
1181	
1182	  const updateJurySlot = (index: number, patch: Partial<AgentSlot>) => {
1183	    setAppliedStrategy(null)
1184	    setJurySlots(prev => normalizeSlots(prev, jurySize, provider, juryModel || model).map((slot, i) => i === index ? { ...slot, ...patch } : slot))
1185	  }
1186	
1187	  const updateLeafSlot = (index: number, patch: Partial<AgentSlot>) => {
1188	    setAppliedStrategy(null)
1189	    setLeafSlots(prev => normalizeSlots(prev, prev.length || 2, provider, model).map((slot, i) => i === index ? { ...slot, ...patch } : slot))
1190	  }
1191	
1192	  const updateMidSlot = (index: number, patch: Partial<AgentSlot>) => {
1193	    setAppliedStrategy(null)
1194	    setMidSlots(prev => normalizeSlots(prev, prev.length || 2, provider, model).map((slot, i) => i === index ? { ...slot, ...patch } : slot))
1195	  }
1196	
1197	  const updateRootSlot = (index: number, patch: Partial<AgentSlot>) => {
1198	    setAppliedStrategy(null)
1199	    setRootSlots(prev => normalizeSlots(prev, prev.length || 2, provider, model).map((slot, i) => i === index ? { ...slot, ...patch } : slot))
1200	  }
1201	
1202	  const applyStrategy = (strategyId: string) => {
1203	    // Click the active strategy again → deselect it (keep current settings, just clear the badge)
1204	    if (appliedStrategy === strategyId) {
1205	      setAppliedStrategy(null)
1206	      return
1207	    }
1208	    const s = MODEL_STRATEGIES.find(x => x.id === strategyId)
1209	    if (!s) return
1210	    setAppliedStrategy(s.id)
1211	    setMultiModel(s.multiModel)
1212	    setConsortiumSize(s.consortiumSize)
1213	    setJurySize(s.jurySize)
1214	    // Always set slots explicitly — clear stale state from any previously applied strategy
1215	    setConsortiumSlots(s.consortiumSlots)
1216	    setJurySlots(s.jurySlots)
1217	    // Tier routing — always reset all tier slots so switching strategies is clean
1218	    setTierRouting(s.tierRouting || false)
1219	    setLeafSlots(s.leafSlots || [])
1220	    setMidSlots(s.midSlots || [])
1221	    setRootSlots(s.rootSlots || [])
1222	  }
1223	
1224	  const replayServerRun = async (summary: ServerRunSummary) => {
1225	    try {
1226	      const [eventsRes, statusRes] = await Promise.all([
1227	        fetch(`${API_BASE}/api/run/${summary.run_id}/events`),
1228	        fetch(`${API_BASE}/api/run/${summary.run_id}`),
1229	      ])
1230	      if (!eventsRes.ok) return
1231	      const eventsData = await eventsRes.json() as { events?: RafEvent[]; status?: string }
1232	      const statusData = statusRes.ok ? await statusRes.json() as { status?: string; result?: { output?: string } | null; error?: string | null } : null
1233	      const replayEvents = eventsData.events || []
1234	
1235	      graphNodesRef.current = []; graphLinksRef.current = []
1236	      seenEventsRef.current = new Set()
1237	      satelliteEventsRef.current = []
1238	      planChildrenRef.current = {}
1239	      planChildNodeRef.current = {}
1240	      nodeCreatedTsRef.current = {}
1241	      setGraphNodes([]); setGraphLinks([]); setEvents([]); setNodeOutputs(new Map())
1242	      setRunResult(statusData?.result?.output || null)
1243	      setDetectedDomain(null); setSelectedNode(null); setPendingPlan(null)
1244	      setNodeCount(0); setCurrentPhase("Replayed")
1245	      setRunId(summary.run_id)
1246	      setRunStatus((statusData?.status as typeof runStatus) || (eventsData.status as typeof runStatus) || "idle")
1247	      setGoal(summary.goal)
1248	      setProvider(summary.provider)
1249	      runStartRef.current = replayEvents.find(ev => ev.timestamp)?.timestamp
1250	        ? replayEvents.find(ev => ev.timestamp)!.timestamp! * 1000
1251	        : null
1252	
1253	      replayEvents.forEach(ev => processEvent(ev))
1254	      setCenterTab("timeline")
1255	      setWorkPanelOpen(true)
1256	    } catch {
1257	      setRunStatus("error")
1258	    }
1259	  }
1260	
1261	  // Fetch freshest server state before exporting; falls back to local state on error
1262	  const fetchFreshExportData = async (): Promise<{ freshEvents: RafEvent[]; freshResult: string | null; freshStatus: string }> => {
1263	    if (!runId) return { freshEvents: events, freshResult: runResult, freshStatus: runStatus }
1264	    try {
1265	      const [evRes, stRes] = await Promise.all([
1266	        fetch(`${API_BASE}/api/run/${runId}/events`, { headers: authHeaders(runToken) }),
1267	        fetch(`${API_BASE}/api/run/${runId}`, { headers: authHeaders(runToken) }),
1268	      ])
1269	      const freshEvents: RafEvent[] = evRes.ok ? ((await evRes.json()) as { events?: RafEvent[] }).events || events : events
1270	      const stData = stRes.ok ? await stRes.json() as { status?: string; result?: { output?: string } | null } : null
1271	      const freshResult = stData?.result?.output ?? runResult
1272	      const freshStatus = stData?.status ?? runStatus
1273	      return { freshEvents, freshResult, freshStatus }
1274	    } catch {
1275	      return { freshEvents: events, freshResult: runResult, freshStatus: runStatus }
1276	    }
1277	  }
1278	
1279	  // Compute export completeness metadata for both JSON and PDF
1280	  const buildExportMeta = (evList: RafEvent[], status: string) => {
1281	    const hasRunDone = evList.some(ev => ev.event === "run_done")
1282	    const hasRootNodeDone = evList.some(ev => ev.event === "node_done" && (ev.node_id === "root" || ev.depth === 0))
1283	    const isMidRun = status === "running"
1284	    let exportCompleteness: string
1285	    if (isMidRun) exportCompleteness = "mid_run"
1286	    else if (!hasRunDone && hasRootNodeDone) exportCompleteness = "near_complete"
1287	    else if (hasRunDone) exportCompleteness = "complete"
1288	    else exportCompleteness = "partial"
1289	    return { hasRunDone, hasRootNodeDone, exportCompleteness, isMidRun }
1290	  }
1291	
1292	  const exportJSON = async () => {
1293	    const { freshEvents, freshResult, freshStatus } = await fetchFreshExportData()
1294	    const meta = buildExportMeta(freshEvents, freshStatus)
1295	    const data = {
1296	      run_id: runId,
1297	      goal,
1298	      provider,
1299	      model: model || null,
1300	      jury_model: juryModel || null,
1301	      status: freshStatus,
1302	      phase: currentPhase,
1303	      detected_domain: detectedDomain,
1304	      partial_failures: partialFailures,
1305	      exportCompleteness: meta.exportCompleteness,
1306	      hasRunDone: meta.hasRunDone,
1307	      hasRootNodeDone: meta.hasRootNodeDone,
1308	      note: meta.isMidRun ? "Exported mid-run. Final output may not be available yet." : undefined,
1309	      config: currentConfig(),
1310	      physics,
1311	      result: freshResult,
1312	      events: freshEvents,
1313	      graphNodes: cleanGraphNodes(graphNodes),
1314	      graphLinks: cleanGraphLinks(graphLinks),
1315	      nodeOutputs: outputMapToRecord(nodeOutputs),
1316	      selectedNodeId: selectedNode?.id || null,
1317	      exportedAt: new Date().toISOString(),
1318	    }
1319	    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
1320	    const url = URL.createObjectURL(blob)
1321	    const a = document.createElement("a"); a.href = url; a.download = `raf-trace-${runId || "export"}.json`
1322	    a.click(); URL.revokeObjectURL(url)
1323	  }
1324	
1325	  const exportPDF = async () => {
1326	    const [{ default: jsPDF }, { default: html2canvas }, { freshEvents, freshResult, freshStatus }] = await Promise.all([
1327	      import("jspdf"), import("html2canvas"), fetchFreshExportData(),
1328	    ])
1329	    const meta = buildExportMeta(freshEvents, freshStatus)
1330	    const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" })
1331	    const W = doc.internal.pageSize.getWidth()
1332	    const H = doc.internal.pageSize.getHeight()
1333	
1334	    // ── helpers ──────────────────────────────────────────────────────────────
1335	    const newPage = () => {
1336	      doc.addPage()
1337	      doc.setFillColor(10, 14, 23); doc.rect(0, 0, W, H, "F")
1338	    }
1339	    const sectionHeader = (title: string, yPos: number) => {
1340	      doc.setTextColor(96, 165, 250); doc.setFontSize(11)
1341	      doc.text(title, 10, yPos)
1342	      doc.setTextColor(148, 163, 184); doc.setFontSize(7.5)
1343	      return yPos + 7
1344	    }
1345	    const maybeNewPage = (y: number, needed = 10): number => {
1346	      if (y + needed > H - 10) { newPage(); return 15 }
1347	      return y
1348	    }
1349	    const row = (doc: InstanceType<typeof jsPDF>, label: string, value: string, y: number, indent = 10): number => {
1350	      doc.setTextColor(100, 116, 139); doc.text(label, indent, y)
1351	      doc.setTextColor(148, 163, 184); doc.text(value, indent + 42, y)
1352	      return y + 4.5
1353	    }
1354	
1355	    // ── Cover page ──────────────────────────────────────────────────────────
1356	    doc.setFillColor(10, 14, 23); doc.rect(0, 0, W, H, "F")
1357	    doc.setTextColor(96, 165, 250); doc.setFontSize(22)
1358	    doc.text("RAF Execution Report", 20, 28)
1359	
1360	    // Status badge — coloured based on completeness
1361	    const statusColors: Record<string, [number, number, number]> = {
1362	      complete: [34, 197, 94], mid_run: [59, 130, 246], near_complete: [234, 179, 8], partial: [239, 68, 68],
1363	    }
1364	    const [sr, sg, sb] = statusColors[meta.exportCompleteness] || [148, 163, 184]
1365	    doc.setFontSize(9); doc.setTextColor(sr, sg, sb)
1366	    const statusLabel = meta.isMidRun ? "⚡ EXPORTED MID-RUN" : meta.exportCompleteness === "near_complete" ? "⚠ NEAR COMPLETE (no run_done yet)" : meta.exportCompleteness === "complete" ? "✓ COMPLETE" : "~ PARTIAL"
1367	    doc.text(statusLabel, 20, 38)
1368	
1369	    doc.setTextColor(148, 163, 184); doc.setFontSize(9)
1370	    let cy = 50
1371	    cy = row(doc, "Run ID", runId || "—", cy)
1372	    cy = row(doc, "Goal", goal.slice(0, 100) + (goal.length > 100 ? "…" : ""), cy)
1373	    cy = row(doc, "Provider", provider, cy)
1374	    cy = row(doc, "Domain", detectedDomain || "auto", cy)
1375	    cy = row(doc, "Status", runStatus, cy)
1376	    cy = row(doc, "Phase", currentPhase, cy)
1377	    cy = row(doc, "Nodes", `${graphNodes.filter(n => n.type === "raf-node").length} RAF + ${graphNodes.filter(n => n.type !== "raf-node").length} satellite`, cy)
1378	    cy = row(doc, "Events", String(events.length), cy)
1379	    cy = row(doc, "Partial failures", String(partialFailures), cy)
1380	    cy = row(doc, "Exported at", new Date().toLocaleString(), cy)
1381	
1382	    if (meta.isMidRun) {
1383	      cy += 4
1384	      doc.setTextColor(59, 130, 246); doc.setFontSize(8)
1385	      doc.text("Note: exported while run was active. Final output may not be available.", 20, cy)
1386	      cy += 5; doc.text("Re-export after run_done for a complete report.", 20, cy)
1387	    }
1388	    if (!meta.hasRunDone && meta.hasRootNodeDone) {
1389	      cy += 4
1390	      doc.setTextColor(234, 179, 8); doc.setFontSize(8)
1391	      doc.text("Root node completed but run_done has not been received yet.", 20, cy)
1392	    }
1393	
1394	    // Run health summary box
1395	    cy += 8
1396	    doc.setDrawColor(30, 41, 59); doc.setFillColor(15, 23, 42); doc.roundedRect(18, cy, 100, 38, 2, 2, "FD")
1397	    doc.setTextColor(96, 165, 250); doc.setFontSize(8.5); doc.text("Run Health", 22, cy + 7)
1398	    doc.setFontSize(7.5); doc.setTextColor(148, 163, 184)
1399	    const hasRunDoneEv = meta.hasRunDone; const hasRootDoneEv = meta.hasRootNodeDone

---

## Subagent Output

1400	    doc.text(`  run_done received:   ${hasRunDoneEv ? "yes" : "no"}`, 20, cy + 13)
1401	    doc.text(`  root node_done:      ${hasRootDoneEv ? "yes" : "no"}`, 20, cy + 18)
1402	    doc.text(`  partial child fails: ${partialFailures}`, 20, cy + 23)
1403	    doc.text(`  export completeness: ${meta.exportCompleteness}`, 20, cy + 28)
1404	
1405	    // Plan recovery summary if any
1406	    const recoveryEvents = freshEvents.filter(ev => ["plan_validation_failed","plan_retry_start","plan_retry_done","plan_abandoned","plan_replaced"].includes(ev.event || ""))
1407	    if (recoveryEvents.length > 0) {
1408	      doc.setDrawColor(30, 41, 59); doc.setFillColor(40, 20, 10); doc.roundedRect(130, cy, 120, 38, 2, 2, "FD")
1409	      doc.setTextColor(251, 146, 60); doc.setFontSize(8.5); doc.text("Plan Recovery", 134, cy + 7)
1410	      doc.setFontSize(7.5); doc.setTextColor(148, 163, 184)
1411	      const retries = recoveryEvents.filter(ev => ev.event === "plan_retry_start").length
1412	      const abandoned = recoveryEvents.some(ev => ev.event === "plan_abandoned")
1413	      doc.text(`  retries: ${retries}`, 132, cy + 13)
1414	      doc.text(`  abandoned: ${abandoned ? "yes" : "no"}`, 132, cy + 18)
1415	      doc.text(`  events: ${recoveryEvents.length}`, 132, cy + 23)
1416	    }
1417	
1418	    // ── Graph page ──────────────────────────────────────────────────────────
1419	    const svgEl = graphRef.current?.querySelector("svg")
1420	    if (svgEl && graphNodesRef.current.length > 0) {
1421	      const ns = graphNodesRef.current.filter(n => n.x !== undefined && n.y !== undefined)
1422	      if (ns.length > 0) {
1423	        const pad = 60
1424	        const xs = ns.map(n => n.x!); const ys = ns.map(n => n.y!)
1425	        const x0 = Math.min(...xs) - pad; const y0 = Math.min(...ys) - pad
1426	        const bw = Math.max(...xs) - x0 + pad; const bh = Math.max(...ys) - y0 + pad
1427	        const savedVB = svgEl.getAttribute("viewBox") || ""
1428	        const zoomGroup = svgEl.querySelector("g") as SVGGElement | null
1429	        const savedTransform = zoomGroup?.getAttribute("transform") || ""
1430	        svgEl.setAttribute("viewBox", `${x0} ${y0} ${bw} ${bh}`)
1431	        if (zoomGroup) zoomGroup.setAttribute("transform", "")
1432	        const canvas = await html2canvas(svgEl as unknown as HTMLElement, { backgroundColor: "#070c17", scale: 1.5 })
1433	        if (savedVB) svgEl.setAttribute("viewBox", savedVB); else svgEl.removeAttribute("viewBox")
1434	        if (zoomGroup) zoomGroup.setAttribute("transform", savedTransform)
1435	        newPage()
1436	        // Graph legend
1437	        doc.setTextColor(96, 165, 250); doc.setFontSize(10); doc.text("Execution Graph", 10, 10)
1438	        doc.setFontSize(7); doc.setTextColor(148, 163, 184)
1439	        const legendItems: [string, string][] = [["RAF node","#00e5ff"],["Base","#69ff47"],["Recursive","#f59e0b"],["Consortium","#ffd600"],["Jury","#ce93d8"],["Merge","#ff9100"]]
1440	        legendItems.forEach(([label, color], i) => {
1441	          const lx = 10 + i * 40
1442	          doc.setTextColor(parseInt(color.slice(1,3),16), parseInt(color.slice(3,5),16), parseInt(color.slice(5,7),16))
1443	          doc.text(`● ${label}`, lx, 14)
1444	        })
1445	        doc.setTextColor(148, 163, 184)
1446	        doc.text(`Mode: ${graphMode} | Nodes: ${graphNodes.length} | Edges: ${graphLinks.length}`, 10, 18)
1447	        const imgW = W - 20; const imgH = (canvas.height / canvas.width) * imgW
1448	        doc.addImage(canvas.toDataURL("image/png"), "PNG", 10, 20, imgW, Math.min(imgH, H - 30))
1449	      }
1450	    }
1451	
1452	    // ── RAF Nodes section ───────────────────────────────────────────────────
1453	    newPage()
1454	    let y = sectionHeader("RAF Nodes", 12)
1455	    const rafNodes = graphNodes.filter(n => n.type === "raf-node")
1456	    for (const n of rafNodes) {
1457	      y = maybeNewPage(y, 28)
1458	      doc.setTextColor(96, 165, 250); doc.setFontSize(8.5); doc.text(n.id, 10, y); y += 5
1459	      doc.setFontSize(7.5); doc.setTextColor(148, 163, 184)
1460	      y = row(doc, "Depth", String(n.depth ?? "—"), y, 14)
1461	      y = row(doc, "Mode", n.caseType || "—", y, 14)
1462	      y = row(doc, "Phase", n.phase || "—", y, 14)
1463	      y = row(doc, "Confidence", n.confidence ? (n.confidence * 100).toFixed(0) + "%" : "—", y, 14)
1464	      if (n.durationMs !== undefined) { y = row(doc, "Duration", `${n.durationMs}ms`, y, 14) }
1465	      y = row(doc, "Status", n.success ? "success" : "in progress", y, 14)
1466	      if (n.goal) {
1467	        const goalLines = doc.splitTextToSize(`Goal: ${n.goal}`, W - 24)
1468	        doc.setTextColor(100, 116, 139); doc.text(goalLines.slice(0, 2), 14, y); y += goalLines.slice(0, 2).length * 4
1469	      }
1470	      if (n.output) {
1471	        const outLines = doc.splitTextToSize(`Output: ${n.output.slice(0, 200)}`, W - 24)
1472	        doc.text(outLines.slice(0, 3), 14, y); y += outLines.slice(0, 3).length * 4
1473	      }
1474	      y += 2
1475	      doc.setDrawColor(30, 41, 59); doc.line(10, y, W - 10, y); y += 3
1476	    }
1477	
1478	    // ── Consortium & Jury section ───────────────────────────────────────────
1479	    const voteEvs = freshEvents.filter(ev => ev.event === "jury_votes")
1480	    if (voteEvs.length > 0) {
1481	      newPage(); y = sectionHeader("Jury Votes", 12)
1482	      for (const ev of voteEvs) {
1483	        y = maybeNewPage(y, 20)
1484	        doc.setTextColor(168, 85, 247); doc.setFontSize(8.5)
1485	        doc.text(`${ev.node_id || "?"} — task: ${ev.task || "?"}`, 10, y); y += 5
1486	        doc.setFontSize(7.5); doc.setTextColor(148, 163, 184)
1487	        y = row(doc, "Winner", String(ev.winner_id || "—"), y)
1488	        y = row(doc, "Confidence", ev.confidence ? (ev.confidence * 100).toFixed(0) + "%" : "—", y)
1489	        const votes = (ev.votes as any[]) || []
1490	        votes.forEach((v: any, i: number) => {
1491	          y = maybeNewPage(y, 5)
1492	          const vote = v.vote || v
1493	          row(doc, `Juror ${i + 1}`, `→ ${vote.winner_id || "?"}  ${vote.confidence ? (vote.confidence * 100).toFixed(0) + "%" : ""}`, y, 14)
1494	          y += 4.5
1495	        })
1496	        y += 2
1497	      }
1498	    }
1499	
1500	    // ── Plan recovery events ────────────────────────────────────────────────
1501	    if (recoveryEvents.length > 0) {
1502	      newPage(); y = sectionHeader("Plan Recovery Events", 12)
1503	      for (const ev of recoveryEvents) {
1504	        y = maybeNewPage(y, 14)
1505	        doc.setTextColor(251, 146, 60); doc.setFontSize(8.5)
1506	        doc.text(`${ev.event || "?"} — ${ev.node_id || "?"}`, 10, y); y += 5
1507	        doc.setFontSize(7.5); doc.setTextColor(148, 163, 184)
1508	        if ((ev as any).reason) { y = row(doc, "Reason", String((ev as any).reason).slice(0, 100), y) }
1509	        if ((ev as any).retry) { y = row(doc, "Retry #", String((ev as any).retry), y) }
1510	        y += 2
1511	      }
1512	    }
1513	
1514	    // ── Checks / Spec / Tools sections ─────────────────────────────────────
1515	    const checkEvs = freshEvents.filter(ev => ["scope_drift_detected","referee_report","spec_validation_final","spec_repair_start","tool_called","tool_blocked"].includes(ev.event || ""))
1516	    if (checkEvs.length > 0) {
1517	      newPage(); y = sectionHeader("Checks, Spec & Tools", 12)
1518	      for (const ev of checkEvs) {
1519	        y = maybeNewPage(y, 10)
1520	        doc.setTextColor(100, 116, 139); doc.setFontSize(7.5)
1521	        const line = `${(ev.event || "").padEnd(28)} ${(ev.node_id || "").padEnd(18)} ${ev.task || ""}`
1522	        doc.setTextColor(148, 163, 184); doc.text(line, 10, y); y += 4.5
1523	      }
1524	    }
1525	
1526	    // ── Raw timeline ────────────────────────────────────────────────────────
1527	    newPage(); y = sectionHeader("Full Trace Timeline", 12)
1528	    for (const ev of freshEvents) {
1529	      y = maybeNewPage(y, 5)
1530	      doc.setFontSize(7)
1531	      const ts = ev.timestamp ? `+${((ev.timestamp * 1000) - (runStartRef.current || 0)).toFixed(0)}ms` : ""
1532	      const line = `${(ev.event || ev.status || "").padEnd(26)} ${(ev.node_id || "").padEnd(18)} ${ts.padEnd(10)} ${ev.confidence ? (ev.confidence * 100).toFixed(0) + "%" : ""}`
1533	      doc.setTextColor(148, 163, 184); doc.text(line, 10, y); y += 4
1534	    }
1535	
1536	    // ── Final output page ───────────────────────────────────────────────────
1537	    if (freshResult) {
1538	      newPage(); y = sectionHeader("Final Output", 12)
1539	      doc.setFontSize(8); doc.setTextColor(148, 163, 184)
1540	      const outputLines = doc.splitTextToSize(freshResult.slice(0, 3000), W - 20)
1541	      outputLines.forEach((line: string) => { y = maybeNewPage(y, 5); doc.text(line, 10, y); y += 4.5 })
1542	    }
1543	
1544	    doc.save(`raf-report-${runId || "export"}.pdf`)
1545	  }
1546	
1547	  const submitAnswer = async () => {
1548	    if (!clarifyAnswer.trim()) return
1549	    const merged = `${accumulatedGoal || goal}\n\nUser answer: ${clarifyAnswer}`
1550	    setAccumulatedGoal(merged); setClarifyQuestion(null); setClarifyAnswer("")
1551	    await startRun(merged, true, true) // continueSession=true preserves existing timeline
1552	  }
1553	
1554	  const approvePlan = async () => {
1555	    if (!pendingPlan || !runId) return
1556	    await fetch(`${API_BASE}/api/run/${runId}/approve_plan`, {
1557	      method: "POST", headers: authHeaders(runToken, true),
1558	      body: JSON.stringify({ node_id: pendingPlan.nodeId, children: pendingPlan.children }),
1559	    }).catch(() => {})
1560	    setPendingPlan(null)
1561	  }
1562	
1563	  const filteredEvents = events.filter(ev => {
1564	    if (timelineFilter === "all") return true
1565	    return (TIMELINE_FILTER_EVENTS[timelineFilter] || []).includes(ev.event || ev.status || "")
1566	  })
1567	  const voteEvents = events.filter(ev => ev.event === "jury_votes")
1568	  // Map of "node_id:task:role:agent_index" → short model label, built from model_call_done events.
1569	  // Used to replace generic "agent-N" labels with actual model names in votes and proposals.
1570	  const agentModelMap: Record<string, string> = {}
1571	  for (const ev of events) {
1572	    if (ev.event === "model_call_done" && ev.node_id && ev.task && ev.model !== undefined && ev.agent_index !== undefined && ev.role) {
1573	      const label = String(ev.model).split("/").pop()?.replace(/:.*$/, "") || String(ev.model)
1574	      agentModelMap[`${ev.node_id}:${ev.task}:${ev.role}:${ev.agent_index}`] = label
1575	    }
1576	  }
1577	  const modelCallEvents = events.filter(ev => (ev.event || "").startsWith("model_call_"))
1578	  const activeModelCall = (() => {
1579	    const starts = [...modelCallEvents].reverse().filter(ev => ev.event === "model_call_start")
1580	    return starts.find(start => !modelCallEvents.some(ev =>
1581	      ev !== start &&
1582	      ["model_call_done", "model_call_failed", "model_call_timeout"].includes(ev.event || "") &&
1583	      ev.node_id === start.node_id &&
1584	      ev.task === start.task &&
1585	      ev.role === start.role &&
1586	      ev.agent_index === start.agent_index &&
1587	      (ev.timestamp || 0) >= (start.timestamp || 0)
1588	    ))
1589	  })()
1590	  const slowestModelCalls = modelCallEvents
1591	    .filter(ev => ev.event === "model_call_done" && typeof ev.duration_ms === "number")
1592	    .slice()
1593	    .sort((a, b) => (b.duration_ms || 0) - (a.duration_ms || 0))
1594	    .slice(0, 3)
1595	  const timedOutModelCalls = modelCallEvents.filter(ev => ev.event === "model_call_timeout")
1596	  const specEvents = events.filter(ev => ["spec_extracted", "spec_validation_final", "spec_repair_start"].includes(ev.event || ""))
1597	  const toolEvents = events.filter(ev => ["tool_called", "tool_blocked"].includes(ev.event || ""))
1598	  const checkEvents = events.filter(ev => [
1599	    "scope_drift_detected", "referee_report", "validator_children_filtered",
1600	    "child_refined", "token_budget_exceeded", "mode_forced_recursive",
1601	    "plan_validation_failed", "plan_retry_start", "plan_retry_done",
1602	    "plan_abandoned", "plan_replaced", "model_call_failed", "model_call_timeout",
1603	  ].includes(ev.event || ""))
1604	  const latestSpec = [...events].reverse().find(ev => ev.event === "spec_extracted")
1605	  const latestError = [...events].reverse().find(ev => ev.error)?.error || null
1606	  const selectedOutput = selectedNode ? nodeOutputs.get(selectedNode.id) : null
1607	  const selectedNodeEvents = selectedNode ? events.filter(ev => ev.node_id === selectedNode.id) : []
1608	  const selectedNodeProposals = selectedNodeEvents.filter(ev => ev.event === "consortium_candidates")
1609	  const selectedNodeVotes = selectedNodeEvents.filter(ev => ev.event === "jury_votes")
1610	  const selectedNodeChildren = selectedNode
1611	    ? graphLinks
1612	      .filter(link => link.edgeType !== "dependency" && graphEndpointId(link.source) === selectedNode.id)
1613	      .map(link => graphNodes.find(node => node.id === graphEndpointId(link.target)))
1614	      .filter((node): node is GraphNode => Boolean(node))
1615	    : []
1616	
1617	  // Inspector: find source events for satellite nodes
1618	  const inspectorOwner = selectedNode?.ownerNodeId
1619	  const inspectorTask  = selectedNode?.task
1620	  const inspectorCandidatesEvent = inspectorOwner && inspectorTask
1621	    ? events.find(ev => ev.event === "consortium_candidates" && ev.node_id === inspectorOwner && ev.task === inspectorTask) as RafEvent | undefined
1622	    : undefined
1623	  const inspectorJuryEvent = inspectorOwner && inspectorTask
1624	    ? events.find(ev => ev.event === "jury_votes" && ev.node_id === inspectorOwner && ev.task === inspectorTask) as RafEvent | undefined
1625	    : undefined
1626	  const inspectorCandidates: any[] = (inspectorCandidatesEvent as any)?.candidates || []
1627	  const inspectorVotes: any[] = (inspectorJuryEvent as any)?.votes || []
1628	  const inspectorWinnerId: string | undefined = (inspectorJuryEvent as any)?.winner_id
1629	  const selectedDurationMs = selectedNode?.durationMs ?? (() => {
1630	    if (!selectedNode) return undefined
1631	    const created = selectedNodeEvents.find(ev => ev.event === "node_created")?.timestamp
1632	    const done = selectedNodeEvents.find(ev => ev.event === "node_done")?.timestamp
1633	    return created && done ? Math.max(0, Math.round((done - created) * 1000)) : undefined
1634	  })()
1635	  const running = runStatus === "running"
1636	  const sidebarMinLeft = sidebarCollapsed ? 64 : sidebarWidth + 8
1637	
1638	  const startSidebarResize = (e: PointerEvent<HTMLDivElement>) => {
1639	    if (sidebarCollapsed) return
1640	    sidebarResizeRef.current = { x: e.clientX, width: sidebarWidth }
1641	    e.currentTarget.setPointerCapture(e.pointerId)
1642	    e.preventDefault()
1643	  }
1644	
1645	  const moveSidebarResize = (e: PointerEvent<HTMLDivElement>) => {
1646	    if (!sidebarResizeRef.current) return
1647	    const dx = e.clientX - sidebarResizeRef.current.x
1648	    const nextWidth = Math.min(420, Math.max(224, sidebarResizeRef.current.width + dx))
1649	    setSidebarWidth(nextWidth)

---

## Subagent Output

1650	    setWorkPanelPos(pos => pos.left < nextWidth + 8 ? { ...pos, left: nextWidth + 8 } : pos)
1651	  }
1652	
1653	  const endSidebarResize = () => {
1654	    sidebarResizeRef.current = null
1655	  }
1656	
1657	  const startWorkPanelDrag = (e: PointerEvent<HTMLDivElement>) => {
1658	    if ((e.target as HTMLElement).closest("button")) return
1659	    workPanelDragRef.current = { x: e.clientX, y: e.clientY, left: workPanelPos.left, top: workPanelPos.top }
1660	    e.currentTarget.setPointerCapture(e.pointerId)
1661	  }
1662	
1663	  const moveWorkPanelDrag = (e: PointerEvent<HTMLDivElement>) => {
1664	    if (!workPanelDragRef.current) return
1665	    const dx = e.clientX - workPanelDragRef.current.x
1666	    const dy = e.clientY - workPanelDragRef.current.y
1667	    const maxLeft = Math.max(sidebarMinLeft, window.innerWidth - 440)
1668	    const maxTop = Math.max(48, window.innerHeight - 220)
1669	    setWorkPanelPos({
1670	      left: Math.min(maxLeft, Math.max(sidebarMinLeft, workPanelDragRef.current.left + dx)),
1671	      top: Math.min(maxTop, Math.max(48, workPanelDragRef.current.top + dy)),
1672	    })
1673	  }
1674	
1675	  const endWorkPanelDrag = () => {
1676	    workPanelDragRef.current = null
1677	  }
1678	
1679	  // ── render ────────────────────────────────────────────────────────────────────
1680	  if (showLanding) {
1681	    return (
1682	      <Landing onEnter={() => {
1683	        sessionStorage.setItem("raf-entered", "1")
1684	        setShowLanding(false)
1685	      }} />
1686	    )
1687	  }
1688	
1689	  return (
1690	    <div className="relative flex h-screen overflow-hidden bg-background text-foreground text-sm">
1691	
1692	      {/* ══ LEFT SIDEBAR ══════════════════════════════════════════════════════════ */}
1693	      <div
1694	        className="relative flex flex-col border-r border-border bg-card shrink-0 transition-[width] duration-200"
1695	        style={{ width: sidebarCollapsed ? 56 : sidebarWidth }}
1696	      >
1697	
1698	        {/* Logo */}
1699	        <div className={`${sidebarCollapsed ? "px-2 py-3" : "px-4 py-3"} border-b border-border shrink-0`}>
1700	          {sidebarCollapsed ? (
1701	            <button
1702	              type="button"
1703	              title="Open RAF panel"
1704	              onClick={() => setSidebarCollapsed(false)}
1705	              className="mx-auto flex h-9 w-9 items-center justify-center rounded-md border border-border/70 bg-background/40 text-primary hover:bg-accent/50"
1706	            >
1707	              <Zap className="h-4 w-4" />
1708	            </button>
1709	          ) : (
1710	            <>
1711	              <div className="flex items-center gap-2">
1712	                <button
1713	                  type="button"
1714	                  title="Collapse RAF panel"
1715	                  onClick={() => setSidebarCollapsed(true)}
1716	                  className="flex items-center gap-2 rounded-md px-1.5 py-1 -ml-1.5 hover:bg-accent/50"
1717	                >
1718	                  <Zap className="h-4 w-4 text-primary shrink-0" />
1719	                  <span className="font-semibold tracking-tight">RAF</span>
1720	                </button>
1721	                <Badge
1722	                  variant="outline"
1723	                  className={`text-[9px] ml-auto ${backendStatus === "connected" ? "border-green-500/40 text-green-400" : backendStatus === "offline" ? "border-red-500/40 text-red-400" : "border-yellow-500/40 text-yellow-400"}`}
1724	                >
1725	                  {backendStatus === "connected" ? "API on" : backendStatus === "offline" ? "API off" : "API check"}
1726	                </Badge>
1727	                {detectedDomain && (
1728	                  <Badge variant="outline" className="text-[10px] border-primary/40 text-primary">{detectedDomain}</Badge>
1729	                )}
1730	              </div>
1731	              <p className="text-[10px] text-muted-foreground mt-0.5">Recursive Agent Framework</p>
1732	              <button
1733	                type="button"
1734	                onClick={() => {
1735	                  sessionStorage.removeItem("raf-entered")
1736	                  setShowLanding(true)
1737	                }}
1738	                className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-border/70 px-2 py-1 text-[10px] text-muted-foreground hover:bg-accent/50 hover:text-foreground"
1739	              >
1740	                <Home className="h-3 w-3" />
1741	                Landing page
1742	              </button>
1743	            </>
1744	          )}
1745	        </div>
1746	
1747	        {/* Sidebar tabs */}
1748	        {sidebarCollapsed ? (
1749	          <div className="flex flex-col items-center gap-2 py-3">
1750	            <button
1751	              type="button"
1752	              title="Sessions"
1753	              onClick={() => { setSidebarTab("sessions"); setSidebarCollapsed(false) }}
1754	              className={`flex h-9 w-9 items-center justify-center rounded-md border ${sidebarTab === "sessions" ? "border-primary/50 bg-primary/10 text-primary" : "border-border/60 text-muted-foreground hover:bg-accent/50 hover:text-foreground"}`}
1755	            >
1756	              <History className="h-4 w-4" />
1757	            </button>
1758	            <button
1759	              type="button"
1760	              title="Params"
1761	              onClick={() => { setSidebarTab("config"); setSidebarCollapsed(false) }}
1762	              className={`flex h-9 w-9 items-center justify-center rounded-md border ${sidebarTab === "config" ? "border-primary/50 bg-primary/10 text-primary" : "border-border/60 text-muted-foreground hover:bg-accent/50 hover:text-foreground"}`}
1763	            >
1764	              <SlidersHorizontal className="h-4 w-4" />
1765	            </button>
1766	            <div className={`mt-1 h-2 w-2 rounded-full ${backendStatus === "connected" ? "bg-green-500" : backendStatus === "offline" ? "bg-red-500" : "bg-yellow-500"}`} title={backendStatus} />
1767	            {running && <div className="h-2 w-2 rounded-full bg-blue-400 animate-pulse" title="RAF running" />}
1768	          </div>
1769	        ) : (
1770	        <Tabs value={sidebarTab} onValueChange={v => setSidebarTab(v as "sessions" | "config")} className="flex w-full flex-col flex-1 min-h-0">
1771	          <TabsList className="w-full rounded-none border-b border-border bg-transparent h-9 shrink-0 px-0">
1772	            <TabsTrigger value="sessions" className="flex-1 rounded-none text-xs h-full data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
1773	              Sessions
1774	            </TabsTrigger>
1775	            <TabsTrigger value="config" className="flex-1 rounded-none text-xs h-full data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
1776	              Params
1777	            </TabsTrigger>
1778	          </TabsList>
1779	
1780	          {/* Sessions */}
1781	          <TabsContent value="sessions" className="flex flex-col flex-1 min-h-0 mt-0 data-[state=inactive]:hidden">
1782	            <div className="px-3 py-2 border-b border-border shrink-0">
1783	              <Button variant="outline" size="sm" className="w-full gap-1.5 text-xs"
1784	                onClick={() => {
1785	                  setGoal(""); setRunResult(null); setEvents([]); setGraphNodes([]); setGraphLinks([]); setNodeOutputs(new Map())
1786	                  setRunStatus("idle"); setActiveSessionId(null); setSelectedNode(null); setDetectedDomain(null); setCurrentPhase("Idle")
1787	                  graphNodesRef.current = []; graphLinksRef.current = []; seenEventsRef.current = new Set(); satelliteEventsRef.current = []
1788	                  planChildrenRef.current = {}; planChildNodeRef.current = {}; nodeCreatedTsRef.current = {}; runStartRef.current = null
1789	                }}>
1790	                <Plus className="h-3 w-3" /> Clear Run
1791	              </Button>
1792	            </div>
1793	            <ScrollArea className="h-full min-h-0 flex-1">
1794	              <div className="p-2 space-y-1">
1795	                {sessions.length === 0 && (
1796	                  <p className="text-xs text-center text-muted-foreground py-8 px-3 leading-relaxed">No runs yet. Enter a goal and run RAF.</p>
1797	                )}
1798	                {sessions.map(s => (
1799	                  <button key={s.id} onClick={() => restoreSession(s)}
1800	                    className={`w-full text-left px-2.5 py-2 rounded-md transition-colors ${s.id === activeSessionId ? "bg-accent" : "hover:bg-accent/40"}`}>
1801	                    <div className="flex items-center gap-1.5 mb-0.5">
1802	                      <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${s.status === "error" ? "bg-red-500" : s.status === "done" ? "bg-green-500" : s.status === "cancelled" ? "bg-yellow-500" : "bg-blue-400 animate-pulse"}`} />
1803	                      <span className="text-xs font-medium truncate flex-1">{s.goal.slice(0, 30)}{s.goal.length > 30 ? "…" : ""}</span>
1804	                    </div>
1805	                    <div className="text-[10px] text-muted-foreground pl-3">{s.providerLabel || s.provider} | {new Date(s.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</div>
1806	                  </button>
1807	                ))}
1808	                <div className="pt-2 mt-2 border-t border-border">
1809	                  <div className="flex items-center justify-between px-1 pb-1">
1810	                    <p className="text-[10px] uppercase tracking-widest text-muted-foreground">Server runs</p>
1811	                    <button onClick={refreshServerRuns} className="text-[10px] text-primary hover:underline">refresh</button>
1812	                  </div>
1813	                  {serverRuns.length === 0 && (
1814	                    <p className="text-[10px] text-muted-foreground px-1 py-2">No server history available.</p>
1815	                  )}
1816	                  {serverRuns.slice(0, 8).map(r => (
1817	                    <button key={r.run_id} onClick={() => replayServerRun(r)}
1818	                      className="w-full text-left px-2.5 py-2 rounded-md transition-colors hover:bg-accent/40">
1819	                      <div className="flex items-center gap-1.5 mb-0.5">
1820	                        <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${r.status === "error" ? "bg-red-500" : r.status === "done" ? "bg-green-500" : r.status === "cancelled" ? "bg-yellow-500" : "bg-blue-400"}`} />
1821	                        <span className="text-xs font-medium truncate flex-1">{r.goal || r.run_id}</span>
1822	                      </div>
1823	                      <div className="text-[10px] text-muted-foreground pl-3">{r.status} | {r.event_count} events</div>
1824	                    </button>
1825	                  ))}
1826	                </div>
1827	              </div>
1828	            </ScrollArea>
1829	            {/* Run health panel */}
1830	            {running && (
1831	              <div className="px-3 py-2 border-t border-border shrink-0 space-y-1.5">
1832	                {staleWarning && (
1833	                  <div className="flex items-center gap-1.5 rounded-md border border-yellow-500/40 bg-yellow-500/10 px-2 py-1 text-[10px] text-yellow-400">
1834	                    <span className="h-1.5 w-1.5 rounded-full bg-yellow-400 animate-pulse shrink-0" />
1835	                    No events for 90s — run may be stalled
1836	                  </div>
1837	                )}
1838	                <div className="flex items-center gap-2 text-xs text-muted-foreground">
1839	                  <div className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse shrink-0" />
1840	                  <span className="truncate flex-1">{currentPhase}</span>
1841	                  {partialFailures > 0 && (
1842	                    <span className="text-[10px] text-red-400 shrink-0">{partialFailures}✗</span>
1843	                  )}
1844	                </div>
1845	                <div className="h-1 bg-secondary rounded-full overflow-hidden">
1846	                  <div className="h-full bg-primary rounded-full transition-all duration-300" style={{ width: `${Math.min(100, (nodeCount / maxNodesTotal) * 100)}%` }} />
1847	                </div>
1848	                {/* Run health detail grid */}
1849	                <div className="rounded-md border border-border/50 bg-muted/20 p-2 space-y-1 text-[10px]">
1850	                  <div className="flex justify-between text-muted-foreground">
1851	                    <span>Nodes</span><span className="font-mono">{nodeCount} / {maxNodesTotal}</span>
1852	                  </div>
1853	                  <div className="flex justify-between text-muted-foreground">
1854	                    <span>Events</span><span className="font-mono">{events.length}</span>
1855	                  </div>
1856	                  {partialFailures > 0 && (
1857	                    <div className="flex justify-between text-red-400">
1858	                      <span>Partial fails</span><span className="font-mono">{partialFailures}</span>
1859	                    </div>
1860	                  )}
1861	                  {lastEventAge !== null && (
1862	                    <div className={`flex justify-between ${lastEventAge > 60 ? "text-yellow-400" : "text-muted-foreground"}`}>
1863	                      <span>Last event</span>
1864	                      <span className="font-mono">{lastEventAge < 60 ? `${lastEventAge}s ago` : `${Math.floor(lastEventAge / 60)}m ${lastEventAge % 60}s ago`}</span>
1865	                    </div>
1866	                  )}
1867	                  {modelCallEvents.length > 0 && (
1868	                    <div className="pt-1 border-t border-border/40 space-y-1">
1869	                      <div className="flex justify-between text-muted-foreground">
1870	                        <span>Model calls</span>
1871	                        <span className="font-mono">{modelCallEvents.filter(ev => ev.event === "model_call_done").length}/{modelCallEvents.filter(ev => ev.event === "model_call_start").length}</span>
1872	                      </div>
1873	                      {activeModelCall && (
1874	                        <div className="rounded border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-blue-300">
1875	                          <p className="text-[9px] uppercase tracking-widest">Waiting on model</p>
1876	                          <p className="truncate">{activeModelCall.role}/{activeModelCall.task} · {activeModelCall.provider}/{activeModelCall.model}</p>
1877	                        </div>
1878	                      )}
1879	                      {timedOutModelCalls.length > 0 && (
1880	                        <div className="flex justify-between text-yellow-400">
1881	                          <span>Timeouts</span>
1882	                          <span className="font-mono">{timedOutModelCalls.length}</span>
1883	                        </div>
1884	                      )}
1885	                      {slowestModelCalls.length > 0 && (
1886	                        <div className="space-y-0.5">
1887	                          <p className="text-muted-foreground/60">Slowest calls:</p>
1888	                          {slowestModelCalls.map((ev, i) => (
1889	                            <div key={`${ev.node_id}-${ev.task}-${ev.agent_index}-${i}`} className="flex gap-1 text-muted-foreground/80">
1890	                              <span className="min-w-0 flex-1 truncate">{ev.task} · {ev.provider}/{ev.model}</span>
1891	                              <span className="font-mono shrink-0">{Math.round((ev.duration_ms || 0) / 1000)}s</span>
1892	                            </div>
1893	                          ))}
1894	                        </div>
1895	                      )}
1896	                    </div>
1897	                  )}
1898	                  {(() => {
1899	                    const lastEv = [...events].reverse().find(ev => ev.event)
1900	                    const hint = lastEv ? PHASE_NEXT_HINT[lastEv.event || ""] : null
1901	                    return hint ? (
1902	                      <div className="pt-0.5 border-t border-border/40">
1903	                        <p className="text-muted-foreground/60">Expected next:</p>
1904	                        <p className="text-muted-foreground/80">{hint}</p>
1905	                      </div>
1906	                    ) : null
1907	                  })()}
1908	                </div>
1909	              </div>
1910	            )}
1911	          </TabsContent>
1912	
1913	          {/* Config */}
1914	          <TabsContent value="config" className="flex flex-col flex-1 min-h-0 mt-0 data-[state=inactive]:hidden">
1915	            <ScrollArea className="h-full min-h-0 flex-1">
1916	              <div className="p-2 space-y-1">
1917	
1918	                <ParamGroup label="Strategy">
1919	                  <div className="space-y-1.5">
1920	                    {MODEL_STRATEGIES.map(s => {
1921	                      const active = appliedStrategy === s.id
1922	                      return (
1923	                        <div key={s.id}
1924	                          className={`rounded-md border p-2.5 transition-colors ${active ? "border-primary/70 bg-primary/8" : "border-border/50 bg-card/40"}`}>
1925	                          <div className="flex items-start justify-between gap-2">
1926	                            <div className="min-w-0 flex-1">
1927	                              <div className="flex items-center gap-2 flex-wrap">
1928	                                <span className="text-xs font-semibold">{s.label}</span>
1929	                                <span className={`rounded px-1.5 py-0.5 text-[9px] font-mono font-semibold ${active ? "bg-primary/20 text-primary" : "bg-muted/60 text-muted-foreground"}`}>{s.badge}</span>
1930	                              </div>
1931	                              <p className="text-[10px] text-muted-foreground mt-0.5">{s.tagline}</p>
1932	                            </div>
1933	                            <button type="button" disabled={running}
1934	                              onClick={() => applyStrategy(s.id)}
1935	                              title={active ? "Click to deselect this strategy" : "Apply this strategy"}
1936	                              className={`shrink-0 rounded-md border px-2.5 py-1 text-[10px] font-medium transition-colors disabled:opacity-40 ${active ? "border-primary/60 bg-primary/15 text-primary hover:bg-destructive/20 hover:text-destructive hover:border-destructive/50" : "border-border/60 hover:bg-accent/50 text-muted-foreground hover:text-foreground"}`}>
1937	                              {active ? "applied ×" : "apply"}
1938	                            </button>
1939	                          </div>
1940	                          {active && (
1941	                            <div className="mt-2 space-y-1 border-t border-border/40 pt-2">
1942	                              <p className="text-[10px] text-muted-foreground">{s.description}</p>
1943	                              <div className="mt-1.5 grid grid-cols-1 gap-1">
1944	                                {s.tierRouting ? (
1945	                                  <>
1946	                                    <div className="flex gap-1.5 items-start">
1947	                                      <span className="rounded px-1 text-[9px] font-mono bg-sky-950/60 text-sky-300 shrink-0 mt-0.5">leaf</span>
1948	                                      <span className="text-[10px] text-muted-foreground">{s.consortiumNote}</span>
1949	                                    </div>

---

## Subagent Output

1950	                                    {s.midNote && (
1951	                                      <div className="flex gap-1.5 items-start">
1952	                                        <span className="rounded px-1 text-[9px] font-mono bg-amber-950/60 text-amber-300 shrink-0 mt-0.5">planner</span>
1953	                                        <span className="text-[10px] text-muted-foreground">{s.midNote}</span>
1954	                                      </div>
1955	                                    )}
1956	                                    <div className="flex gap-1.5 items-start">
1957	                                      <span className="rounded px-1 text-[9px] font-mono bg-rose-950/60 text-rose-300 shrink-0 mt-0.5">referee</span>
1958	                                      <span className="text-[10px] text-muted-foreground">{s.juryNote}</span>
1959	                                    </div>
1960	                                  </>
1961	                                ) : (
1962	                                  <>
1963	                                    <div className="flex gap-1.5 items-start">
1964	                                      <span className="rounded px-1 text-[9px] font-mono bg-amber-950/60 text-amber-300 shrink-0 mt-0.5">consortium</span>
1965	                                      <span className="text-[10px] text-muted-foreground">{s.consortiumNote}</span>
1966	                                    </div>
1967	                                    <div className="flex gap-1.5 items-start">
1968	                                      <span className="rounded px-1 text-[9px] font-mono bg-purple-950/60 text-purple-300 shrink-0 mt-0.5">jury</span>
1969	                                      <span className="text-[10px] text-muted-foreground">{s.juryNote}</span>
1970	                                    </div>
1971	                                  </>
1972	                                )}
1973	                              </div>
1974	                            </div>
1975	                          )}
1976	                        </div>
1977	                      )
1978	                    })}
1979	                  </div>
1980	                </ParamGroup>
1981	
1982	                <ParamGroup label="Model routing">
1983	                  <div className="flex items-center justify-between rounded-md border border-border/60 p-2">
1984	                    <div>
1985	                      <p className="text-xs font-medium">Multiple models</p>
1986	                      <p className="text-[10px] text-muted-foreground">{multiModel ? "Each slot chooses its own provider/model." : "Use one provider/model for the whole run."}</p>
1987	                    </div>
1988	                    <Switch checked={multiModel} onCheckedChange={setMultiModel} disabled={running} />
1989	                  </div>
1990	
1991	                  {provider !== "mock" && (
1992	                    <div className="space-y-1">
1993	                      <label className="text-[10px] text-muted-foreground font-medium">OpenRouter API Key</label>
1994	                      <Input
1995	                        type="password"
1996	                        placeholder="sk-or-v1-…  (stored locally, never sent to our servers)"
1997	                        value={apiKey}
1998	                        onChange={e => {
1999	                          setApiKey(e.target.value)
2000	                          localStorage.setItem(API_KEY_STORAGE_KEY, e.target.value)
2001	                        }}
2002	                        disabled={running}
2003	                        className="font-mono text-xs h-7"
2004	                      />
2005	                      <p className="text-[10px] leading-4 text-muted-foreground">
2006	                        Paste your own OpenRouter key here. It stays in this browser via local storage and is sent only
2007	                        with your run request.
2008	                      </p>
2009	                      <p className="text-[10px] leading-4 text-muted-foreground">
2010	                        Need one? Open <span className="font-mono">openrouter.ai/keys</span>, create a key, copy it,
2011	                        and paste it into this box.
2012	                      </p>
2013	                    </div>
2014	                  )}
2015	
2016	                  {!multiModel ? (
2017	                    <ModelChooser
2018	                      title="Single routing"
2019	                      provider={provider}
2020	                      model={model}
2021	                      juryModel={juryModel}
2022	                      providers={providers}
2023	                      availableProviders={availableProviders}
2024	                      models={models}
2025	                      modelCatalog={modelCatalog}
2026	                      disabled={running}
2027	                      open={modelPickerOpen}
2028	                      onOpenChange={setModelPickerOpen}
2029	                      onProviderChange={nextProvider => {
2030	                        setProvider(nextProvider)
2031	                        setModel(models[nextProvider]?.[0] || "")
2032	                        if (juryModel) setJuryModel(models[nextProvider]?.[0] || "")
2033	                      }}
2034	                      onModelChange={setModel}
2035	                      onJuryModelChange={setJuryModel}
2036	                    />
2037	                  ) : (
2038	                    <div className="space-y-3 rounded-md border border-border/60 p-2">
2039	                      {/* Tier routing toggle */}
2040	                      <div className="flex items-center justify-between">
2041	                        <div>
2042	                          <p className="text-xs font-medium">Depth-based tier routing</p>
2043	                          <p className="text-[10px] text-muted-foreground">
2044	                            {tierRouting
2045	                              ? "Leaf → Mid → Root tiers active. Flat consortium/jury slots are ignored."
2046	                              : "Use flat consortium + jury slots for all nodes."}
2047	                          </p>
2048	                        </div>
2049	                        <Switch checked={tierRouting} onCheckedChange={v => { setAppliedStrategy(null); setTierRouting(v) }} disabled={running} />
2050	                      </div>
2051	
2052	                      {tierRouting ? (
2053	                        <>
2054	                          <div className="space-y-1">
2055	                            <div className="flex items-center gap-1.5">
2056	                              <span className="rounded px-1.5 py-0.5 text-[9px] font-mono font-semibold bg-sky-950/60 text-sky-300">Tier 0 · Leaf workers</span>
2057	                              <span className="text-[10px] text-muted-foreground">deep base_execute nodes</span>
2058	                            </div>
2059	                            <SlotEditor
2060	                              title=""
2061	                              slots={normalizeSlots(leafSlots, leafSlots.length || 2, provider, model)}
2062	                              size={leafSlots.length || 2}
2063	                              minSize={1}
2064	                              maxSize={6}
2065	                              providers={providers}
2066	                              models={models}
2067	                              modelCatalog={modelCatalog}
2068	                              availableProviders={availableProviders}
2069	                              disabled={running}
2070	                              onSizeChange={n => setLeafSlots(normalizeSlots(leafSlots, n, provider, model))}
2071	                              onChange={updateLeafSlot}
2072	                            />
2073	                          </div>
2074	                          <Separator />
2075	                          <div className="space-y-1">
2076	                            <div className="flex items-center gap-1.5">
2077	                              <span className="rounded px-1.5 py-0.5 text-[9px] font-mono font-semibold bg-amber-950/60 text-amber-300">Tier 1 · Planners</span>
2078	                              <span className="text-[10px] text-muted-foreground">mid-level planning, merging · also jury floor for Tier 0</span>
2079	                            </div>
2080	                            <SlotEditor
2081	                              title=""
2082	                              slots={normalizeSlots(midSlots, midSlots.length || 2, provider, model)}
2083	                              size={midSlots.length || 2}
2084	                              minSize={1}
2085	                              maxSize={6}
2086	                              providers={providers}
2087	                              models={models}
2088	                              modelCatalog={modelCatalog}
2089	                              availableProviders={availableProviders}
2090	                              disabled={running}
2091	                              onSizeChange={n => setMidSlots(normalizeSlots(midSlots, n, provider, model))}
2092	                              onChange={updateMidSlot}
2093	                            />
2094	                          </div>
2095	                          <Separator />
2096	                          <div className="space-y-1">
2097	                            <div className="flex items-center gap-1.5">
2098	                              <span className="rounded px-1.5 py-0.5 text-[9px] font-mono font-semibold bg-rose-950/60 text-rose-300">Tier 2 · Referee</span>
2099	                              <span className="text-[10px] text-muted-foreground">root node + all analysis decisions · strongest models</span>
2100	                            </div>
2101	                            <SlotEditor
2102	                              title=""
2103	                              slots={normalizeSlots(rootSlots, rootSlots.length || 2, provider, model)}
2104	                              size={rootSlots.length || 2}
2105	                              minSize={1}
2106	                              maxSize={6}
2107	                              providers={providers}
2108	                              models={models}
2109	                              modelCatalog={modelCatalog}
2110	                              availableProviders={availableProviders}
2111	                              disabled={running}
2112	                              onSizeChange={n => setRootSlots(normalizeSlots(rootSlots, n, provider, model))}
2113	                              onChange={updateRootSlot}
2114	                            />
2115	                          </div>
2116	                        </>
2117	                      ) : (
2118	                        <>
2119	                          <SlotEditor
2120	                            title="Consortium slots"
2121	                            slots={normalizeSlots(consortiumSlots, consortiumSize, provider, model)}
2122	                            size={consortiumSize}
2123	                            minSize={1}
2124	                            maxSize={10}
2125	                            providers={providers}
2126	                            models={models}
2127	                            modelCatalog={modelCatalog}
2128	                            availableProviders={availableProviders}
2129	                            disabled={running}
2130	                            onSizeChange={setConsortiumSize}
2131	                            onChange={updateConsortiumSlot}
2132	                          />
2133	                          <Separator />
2134	                          <SlotEditor
2135	                            title="Jury slots"
2136	                            slots={normalizeSlots(jurySlots, jurySize, provider, juryModel || model)}
2137	                            size={jurySize}
2138	                            minSize={1}
2139	                            maxSize={10}
2140	                            providers={providers}
2141	                            models={models}
2142	                            modelCatalog={modelCatalog}
2143	                            availableProviders={availableProviders}
2144	                            disabled={running}
2145	                            onSizeChange={setJurySize}
2146	                            onChange={updateJurySlot}
2147	                          />
2148	                        </>
2149	                      )}

---

## Subagent Output

2400	                    <p className="font-mono text-xs text-primary">{selectedNode.id}</p></div>
2401	                  {selectedOutput.goal && (
2402	                    <div><p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-1">Goal</p>
2403	                      <p className="text-xs leading-relaxed">{selectedOutput.goal}</p></div>
2404	                  )}
2405	                  <div className="flex gap-4">
2406	                    <div><p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-1">Mode</p>
2407	                      <Badge variant="outline" className="text-[10px]">{selectedOutput.mode}</Badge></div>
2408	                    <div><p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-1">Confidence</p>
2409	                      <p className="text-xs font-mono">{(selectedOutput.confidence * 100).toFixed(0)}%</p></div>
2410	                  </div>
2411	                  <Separator />
2412	                  <div>
2413	                    <div className="flex items-center gap-2 mb-1">
2414	                      <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Output</p>
2415	                      <button
2416	                        className="ml-auto text-[10px] text-muted-foreground hover:text-foreground border border-border rounded px-2 py-0.5 transition-colors"
2417	                        onClick={() => setExpandModal({ title: "Node Output", content: selectedOutput.output })}
2418	                      >⤢ Expand</button>
2419	                    </div>
2420	                    <div className="output-body text-xs whitespace-pre-wrap" dangerouslySetInnerHTML={{ __html: formatOutput(selectedOutput.output) }} />
2421	                  </div>
2422	                </div>
2423	              </ScrollArea>
2424	            ) : (
2425	              <div className="h-full flex items-center justify-center text-center p-8">
2426	                <div>
2427	                  <Network className="h-10 w-10 text-muted-foreground/20 mx-auto mb-3" />
2428	                  <p className="text-sm text-muted-foreground">Output appears here when the run completes.</p>
2429	                  <p className="text-xs text-muted-foreground/60 mt-1">Click a graph node to inspect its output.</p>
2430	                </div>
2431	              </div>
2432	            )}
2433	          </TabsContent>
2434	
2435	          {/* Timeline tab */}
2436	          <TabsContent value="timeline" className="flex w-full flex-col flex-1 min-h-0 mt-0 overflow-hidden data-[state=inactive]:hidden">
2437	            <div className="flex gap-1 px-3 py-2 border-b border-border shrink-0 flex-wrap">
2438	              {(["all", "node", "vote", "execution", "model", "error"] as const).map(f => (
2439	                <button key={f} onClick={() => setTimelineFilter(f)}
2440	                  className={`text-[10px] px-2 py-0.5 rounded-full border font-medium transition-colors ${timelineFilter === f ? "border-primary text-primary bg-primary/10" : "border-border text-muted-foreground hover:border-primary/50"}`}>
2441	                  {f}
2442	                </button>
2443	              ))}
2444	            </div>
2445	            <ScrollArea className="flex-1">
2446	              <div className="p-2 space-y-1">
2447	                {filteredEvents.length === 0 && (
2448	                  <p className="text-xs text-center text-muted-foreground py-8">{running ? "Waiting for events…" : "No events yet."}</p>
2449	                )}
2450	                {filteredEvents.map((ev, i) => (
2451	                  <div key={i} className="group w-full text-left px-3 py-2 rounded-md bg-card hover:bg-accent/40 transition-colors">
2452	                    <div className="flex items-center gap-2">
2453	                      <div
2454	                        className="h-1.5 w-1.5 rounded-full shrink-0 cursor-pointer"
2455	                        style={{ background: EVENT_COLORS[ev.event || ""] || "#475569" }}
2456	                        onClick={() => { if (ev.node_id) { const n = graphNodes.find(g => g.id === ev.node_id); if (n) setSelectedNode(n) } }}
2457	                      />
2458	                      <span
2459	                        className="text-xs font-medium flex-1 cursor-pointer"
2460	                        onClick={() => { if (ev.node_id) { const n = graphNodes.find(g => g.id === ev.node_id); if (n) setSelectedNode(n) } }}
2461	                      >{eventLabel(ev)}</span>
2462	                      {ev.node_id && <span className="text-[10px] font-mono text-muted-foreground shrink-0">{ev.node_id}</span>}
2463	                      <span className="text-[10px] text-muted-foreground/60 shrink-0 font-mono">{relTs(ev.timestamp, runStartRef.current)}</span>
2464	                      <button
2465	                        className="opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground hover:text-foreground shrink-0 transition-opacity px-1"
2466	                        title="Expand full event"
2467	                        onClick={e => { e.stopPropagation(); setExpandModal({ title: eventLabel(ev), content: JSON.stringify(ev, null, 2) }) }}
2468	                      >⤢</button>
2469	                    </div>
2470	                    {ev.event === "consortium_candidates" && (ev as any).tier !== undefined && (
2471	                      <div className="pl-3.5 mt-0.5 flex items-center gap-1.5">
2472	                        {tierBadge((ev as any).tier)}
2473	                        <span className="text-[10px] text-muted-foreground font-mono">{(ev as any).task}</span>
2474	                        <span className="text-[10px] text-muted-foreground">· {(ev as any).candidates?.length ?? "?"} proposals</span>
2475	                      </div>
2476	                    )}
2477	                    {ev.event === "mode_decided" && (ev as any).winner && (
2478	                      <p className="text-[10px] text-muted-foreground pl-3.5 mt-0.5">→ {(ev as any).winner}{(ev as any).confidence ? ` (${((ev as any).confidence * 100).toFixed(0)}%)` : ""}</p>
2479	                    )}
2480	                    {ev.event === "node_done" && ev.confidence && (
2481	                      <p className="text-[10px] text-muted-foreground pl-3.5 mt-0.5">{ev.mode} | {(ev.confidence * 100).toFixed(0)}%</p>
2482	                    )}
2483	                    {ev.event === "model_call_failed" && (
2484	                      <p className="text-[10px] pl-3.5 mt-0.5 flex items-center gap-1.5">
2485	                        {ev.cause ? (
2486	                          <>
2487	                            <span className="rounded px-1 py-0.5 font-mono text-[9px] font-semibold"
2488	                              style={{ background: ev.cause === "api_error" ? "#7f1d1d" : ev.cause === "parse_error" ? "#78350f" : "#1e1b4b", color: "#fca5a5" }}>
2489	                              {CAUSE_LABELS[ev.cause]?.label ?? ev.cause}
2490	                            </span>
2491	                            <span className="text-muted-foreground">{CAUSE_LABELS[ev.cause]?.detail}</span>
2492	                          </>
2493	                        ) : (
2494	                          <span className="text-muted-foreground">{ev.error || "Unknown failure"}</span>
2495	                        )}
2496	                      </p>
2497	                    )}
2498	                    {ev.event === "model_call_timeout" && ev.timeout_ms !== undefined && (
2499	                      <p className="text-[10px] text-muted-foreground pl-3.5 mt-0.5">
2500	                        <span className="rounded px-1 py-0.5 font-mono text-[9px] font-semibold" style={{ background: "#451a03", color: "#fbbf24" }}>Timeout</span>
2501	                        {" "}waited {(ev.timeout_ms / 1000).toFixed(1)}s — model was still running
2502	                      </p>
2503	                    )}
2504	                  </div>
2505	                ))}
2506	              </div>
2507	            </ScrollArea>
2508	          </TabsContent>
2509	
2510	          {/* Votes tab */}
2511	          <TabsContent value="votes" className="flex w-full flex-col flex-1 min-h-0 mt-0 overflow-hidden data-[state=inactive]:hidden">
2512	            <div className="flex items-center justify-between border-b border-border px-3 py-2 text-[10px] text-muted-foreground shrink-0">
2513	              <span className="uppercase tracking-widest">Jury votes</span>
2514	              <span className="font-mono tabular-nums">{voteEvents.length} events</span>
2515	            </div>
2516	            <ScrollArea className="flex-1 min-h-0">
2517	              <div className="flex min-h-full w-full max-w-full flex-col gap-2 overflow-hidden p-3">
2518	                {voteEvents.length === 0 && (
2519	                  <p className="text-xs text-center text-muted-foreground py-8">No votes yet.</p>
2520	                )}
2521	                {voteEvents.map((ev, i) => {
2522	                  const options = (ev.options as any[]) || []
2523	                  const votes = (ev.votes as any[]) || []
2524	                  return (
2525	                    <Card key={i} className="w-full min-w-0 max-w-full overflow-hidden">
2526	                      <CardContent className="min-w-0 max-w-full overflow-hidden p-3 space-y-2">
2527	                        <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-start gap-2">
2528	                          <div className="flex min-w-0 flex-wrap items-center gap-2">
2529	                            <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wider text-purple-400">{ev.task}</span>
2530	                            {ev.node_id && <span className="min-w-0 break-all text-[10px] font-mono text-muted-foreground">{ev.node_id}</span>}
2531	                          </div>
2532	                          <span className="shrink-0 text-xs font-mono">{ev.confidence ? (ev.confidence * 100).toFixed(0) + "%" : "—"}</span>
2533	                        </div>
2534	
2535	                        {options.length > 0 && (
2536	                          <div className="min-w-0 max-w-full space-y-1.5 overflow-hidden">
2537	                            <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Proposals</p>
2538	                            {options.map((opt: any, oi: number) => {
2539	                              const payload = opt.payload || opt
2540	                              const isWinner = ev.winner_id === opt.option_id
2541	                              const fullText = payload.output || payload.mode || payload.plan || JSON.stringify(payload, null, 2)
2542	                              const preview = fullText.length > 300 ? fullText.slice(0, 300) + "…" : fullText
2543	                              return (
2544	                                <div key={oi} className={`group min-w-0 max-w-full overflow-hidden rounded-md p-2 text-xs border ${isWinner ? "border-primary/50 bg-primary/5" : "border-border"}`}>
2545	                                  <div className="flex min-w-0 max-w-full flex-wrap items-center gap-1.5 mb-1">
2546	                                    <span className="min-w-0 font-mono text-[10px] text-muted-foreground">{optionLabel(opt.option_id)}</span>
2547	                                    {isWinner && <Badge className="text-[9px] h-4 px-1 bg-primary/20 text-primary border-primary/30">winner</Badge>}
2548	                                    <button
2549	                                      className="ml-auto opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground hover:text-foreground transition-opacity"
2550	                                      onClick={() => setExpandModal({ title: `${optionLabel(opt.option_id)} · ${ev.task ?? "proposal"}`, content: fullText })}
2551	                                    >⤢</button>
2552	                                  </div>
2553	                                  <p className="min-w-0 max-w-full whitespace-pre-wrap break-all text-muted-foreground">{preview}</p>
2554	                                </div>
2555	                              )
2556	                            })}
2557	                          </div>
2558	                        )}
2559	
2560	                        {votes.length > 0 && (
2561	                          <div className="min-w-0 max-w-full space-y-1 overflow-hidden pt-1 border-t border-border">
2562	                            <p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-1">Votes</p>
2563	                            {votes.map((v: any, vi: number) => {
2564	                              const vote = v.vote || v
2565	                              const modelLabel = agentModelMap[`${ev.node_id}:${ev.task}:jury:${v.agent_id}`] || `agent-${v.agent_id}`
2566	                              return (
2567	                                <div key={vi} className="grid min-w-0 max-w-full grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)_auto] items-center gap-2 text-xs">
2568	                                  <span className="min-w-0 truncate font-mono text-[10px] text-purple-300" title={modelLabel}>{modelLabel}</span>
2569	                                  <span className="text-muted-foreground shrink-0">→</span>
2570	                                  <span className="min-w-0 font-mono text-[10px]">{optionLabel(vote.winner_id)}</span>
2571	                                  {vote.confidence && <span className="shrink-0 text-muted-foreground text-[10px]">{(vote.confidence * 100).toFixed(0)}%</span>}
2572	                                </div>
2573	                              )
2574	                            })}
2575	                          </div>
2576	                        )}
2577	                      </CardContent>
2578	                    </Card>
2579	                  )
2580	                })}
2581	              </div>
2582	            </ScrollArea>
2583	          </TabsContent>
2584	
2585	          <TabsContent value="spec" className="flex w-full flex-col flex-1 min-h-0 mt-0 overflow-hidden data-[state=inactive]:hidden">
2586	            <ScrollArea className="flex-1 min-h-0">
2587	              <div className="p-3 space-y-3">
2588	                {!latestSpec && specEvents.length === 0 && (
2589	                  <p className="text-xs text-center text-muted-foreground py-8">No spec events yet.</p>
2590	                )}
2591	                {latestSpec && (
2592	                  <Card className="min-w-0 overflow-hidden">
2593	                    <CardContent className="p-3 space-y-3">
2594	                      <div className="flex items-center gap-2">
2595	                        <Badge variant="outline" className="text-[10px]">{latestSpec.domain || "general"}</Badge>
2596	                        {(latestSpec as any).task_class && <Badge variant="outline" className="text-[10px]">{(latestSpec as any).task_class}</Badge>}
2597	                      </div>
2598	                      <SpecList label="Required" items={latestSpec.required || []} />
2599	                      <SpecList label="Forbidden" items={latestSpec.forbidden || []} />
2600	                      <SpecList label="Success criteria" items={latestSpec.success_criteria || []} />
2601	                    </CardContent>
2602	                  </Card>
2603	                )}
2604	                {specEvents.filter(ev => ev.event !== "spec_extracted").map((ev, i) => (
2605	                  <EventCard key={`${ev.event}-${i}`} ev={ev} />
2606	                ))}
2607	              </div>
2608	            </ScrollArea>
2609	          </TabsContent>
2610	
2611	          <TabsContent value="tools" className="flex w-full flex-col flex-1 min-h-0 mt-0 overflow-hidden data-[state=inactive]:hidden">
2612	            <ScrollArea className="flex-1 min-h-0">
2613	              <div className="p-3 space-y-2">
2614	                {toolEvents.length === 0 && (
2615	                  <p className="text-xs text-center text-muted-foreground py-8">No tool calls yet.</p>
2616	                )}
2617	                {toolEvents.map((ev, i) => <EventCard key={`${ev.event}-${i}`} ev={ev} />)}
2618	              </div>
2619	            </ScrollArea>
2620	          </TabsContent>
2621	
2622	          <TabsContent value="checks" className="flex w-full flex-col flex-1 min-h-0 mt-0 overflow-hidden data-[state=inactive]:hidden">
2623	            <ScrollArea className="flex-1 min-h-0">
2624	              <div className="p-3 space-y-2">
2625	                {checkEvents.length === 0 && (
2626	                  <p className="text-xs text-center text-muted-foreground py-8">No check events yet.</p>
2627	                )}
2628	                {checkEvents.map((ev, i) => <EventCard key={`${ev.event}-${i}`} ev={ev} />)}
2629	              </div>
2630	            </ScrollArea>
2631	          </TabsContent>
2632	        </Tabs>
2633	      </div>
2634	
2635	      {/* ══ RIGHT: D3 GRAPH ═══════════════════════════════════════════════════════ */}
2636	      <div className="flex flex-col flex-1 min-w-0">
2637	
2638	        {/* Graph toolbar */}
2639	        <div className="flex items-center justify-between px-4 py-2 border-b border-border shrink-0 bg-card/50">
2640	          <div className="flex items-center gap-2">
2641	            <Network className="h-4 w-4 text-muted-foreground" />
2642	            <span className="font-medium text-sm">Execution Graph</span>
2643	            <Badge variant="outline" className="text-xs tabular-nums">{graphNodes.length} nodes</Badge>
2644	            <Badge variant="outline" className="text-xs tabular-nums">{events.length} events</Badge>
2645	            {currentPhase !== "Idle" && <Badge variant="outline" className="text-xs">{currentPhase}</Badge>}
2646	            {running && <Badge className="text-xs tabular-nums animate-pulse bg-blue-500/20 text-blue-400 border-blue-500/30">{nodeCount} / {maxNodesTotal}</Badge>}
2647	          </div>
2648	          <div className="flex items-center gap-3">
2649	            {!workPanelOpen && (

---

## Subagent Output

2650	              <Button variant="outline" size="sm" className="h-7 gap-1 text-[10px]" onClick={() => setWorkPanelOpen(true)}>
2651	                <FileText className="h-3 w-3" /> Workspace
2652	              </Button>
2653	            )}
2654	            {/* Graph mode toggle */}
2655	            <div className="flex items-center gap-1 border border-border rounded-md overflow-hidden">
2656	              {(["simplified", "full"] as const).map(m => (
2657	                <button key={m} onClick={() => setGraphMode(m)}
2658	                  className={`px-2 py-0.5 text-[10px] font-medium transition-colors ${graphMode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>
2659	                  {m}
2660	                </button>
2661	              ))}
2662	            </div>
2663	            <div className="hidden lg:flex items-center gap-3">
2664	              {([["#00e5ff","Active"],["#69ff47","Base"],["#f59e0b","Recursive"],["#e040fb","Jury"],["#ffeb3b","Consortium"]] as [string,string][]).map(([c,l]) => (
2665	                <div key={l} className="flex items-center gap-1">
2666	                  <div className="h-2 w-2 rounded-full" style={{ background: c }} />
2667	                  <span className="text-[10px] text-muted-foreground">{l}</span>
2668	                </div>
2669	              ))}
2670	            </div>
2671	            <Separator orientation="vertical" className="h-5 hidden lg:block" />
2672	            <div className="flex items-center gap-1 border border-border rounded-md overflow-hidden">
2673	              <button
2674	                className="px-2 py-1 text-muted-foreground hover:bg-muted hover:text-foreground"
2675	                onClick={() => setZoomCommand({ action: "out", nonce: Date.now() })}
2676	                title="Zoom out"
2677	              >
2678	                <ZoomOut className="h-3.5 w-3.5" />
2679	              </button>
2680	              <button
2681	                className="px-2 py-1 text-muted-foreground hover:bg-muted hover:text-foreground"
2682	                onClick={() => setZoomCommand({ action: "reset", nonce: Date.now() })}
2683	                title="Reset zoom"
2684	              >
2685	                <RotateCcw className="h-3.5 w-3.5" />
2686	              </button>
2687	              <button
2688	                className="px-2 py-1 text-muted-foreground hover:bg-muted hover:text-foreground"
2689	                onClick={() => setZoomCommand({ action: "in", nonce: Date.now() })}
2690	                title="Zoom in"
2691	              >
2692	                <ZoomIn className="h-3.5 w-3.5" />
2693	              </button>
2694	            </div>
2695	            {(events.length > 0 || graphNodes.length > 0 || runResult) && (
2696	              <>
2697	                <Button variant="ghost" size="sm" className="h-7 gap-1 text-[10px]" onClick={exportJSON}>
2698	                  <Download className="h-3 w-3" /> JSON
2699	                </Button>
2700	                <Button variant="ghost" size="sm" className="h-7 gap-1 text-[10px]" onClick={exportPDF}>
2701	                  <Download className="h-3 w-3" /> PDF
2702	                </Button>
2703	              </>
2704	            )}
2705	            {selectedNode && (
2706	              <Button variant="ghost" size="sm" className="text-[10px] h-7 px-2" onClick={() => setSelectedNode(null)}>
2707	                Clear
2708	              </Button>
2709	            )}
2710	          </div>
2711	        </div>
2712	
2713	        {/* D3 graph */}
2714	        <div ref={graphRef} className="flex-1 relative select-none">
2715	          <ExecutionGraph
2716	            nodes={graphNodes} links={graphLinks}
2717	            mode={graphMode} physics={physics}
2718	            zoomCommand={zoomCommand}
2719	            width={gSize.w} height={gSize.h}
2720	            onNodeClick={n => { setSelectedNode(n); setCenterTab("output") }}
2721	            onBackgroundClick={() => setSelectedNode(null)}
2722	          />
2723	          {graphNodes.length === 0 && !running && (
2724	            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
2725	              <div className="text-center">
2726	                <Network className="h-16 w-16 text-muted-foreground/10 mx-auto mb-4" />
2727	                <p className="text-muted-foreground/40 text-sm">Graph will appear here as RAF runs</p>
2728	              </div>
2729	            </div>
2730	          )}
2731	
2732	          {/* Node Inspector — top-right frosted overlay */}
2733	          <AnimatePresence>
2734	            {selectedNode && (
2735	              <motion.div
2736	                initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}
2737	                className="absolute top-4 right-4 w-[360px] bg-card/95 backdrop-blur shadow-xl border border-border rounded-lg overflow-hidden flex flex-col z-10"
2738	              >
2739	                <div className="px-3 py-2 border-b border-border flex justify-between items-center shrink-0">
2740	                  <div className="flex items-center gap-2">
2741	                    <span className="h-2 w-2 rounded-full" style={{
2742	                      background: ({
2743	                        'raf-node': '#00e5ff', jury: '#e040fb', consortium: '#ffeb3b', agent: '#69ff47',
2744	                        'consortium-group': '#ffd600', 'jury-group': '#ce93d8',
2745	                        'agent-proposal': '#69ff47', 'juror-vote': '#f3e5f5',
2746	                        'merge-group': '#ff9100', 'referee-check': '#64b5f6',
2747	                      } as Record<string,string>)[selectedNode.type] || '#888'
2748	                    }} />
2749	                    <span className="font-medium text-xs truncate">{selectedNode.label}</span>
2750	                    {selectedNode.task && <Badge variant="outline" className="text-[9px] h-4 px-1">{selectedNode.task}</Badge>}
2751	                  </div>
2752	                  <button onClick={() => setSelectedNode(null)} className="text-muted-foreground hover:text-foreground text-sm leading-none px-1">✕</button>
2753	                </div>
2754	                <div className="p-3 text-xs overflow-y-auto max-h-[70vh] flex flex-col gap-3">
2755	
2756	                  {/* ── RAF node: full lifecycle detail ─────────────────── */}
2757	                  {selectedNode.type === "raf-node" && (
2758	                    <>
2759	                      <div className="grid grid-cols-2 gap-2">
2760	                        <div><span className="text-[10px] uppercase text-muted-foreground">Depth</span>
2761	                          <p className="mt-0.5">{selectedNode.depth ?? "—"}</p></div>
2762	                        {selectedNode.caseType && (
2763	                          <div><span className="text-[10px] uppercase text-muted-foreground">Case</span>
2764	                            <p className="mt-0.5 capitalize">{selectedNode.caseType}</p></div>
2765	                        )}
2766	                        {selectedNode.confidence !== undefined && (
2767	                          <div><span className="text-[10px] uppercase text-muted-foreground">Confidence</span>
2768	                            <p className="font-mono mt-0.5">{(selectedNode.confidence * 100).toFixed(0)}%</p></div>
2769	                        )}
2770	                        {selectedNode.phase && (
2771	                          <div><span className="text-[10px] uppercase text-muted-foreground">Phase</span>
2772	                            <p className="mt-0.5">{selectedNode.phase}</p></div>
2773	                        )}
2774	                        {selectedDurationMs !== undefined && (
2775	                          <div><span className="text-[10px] uppercase text-muted-foreground">Duration</span>
2776	                            <p className="font-mono mt-0.5">{selectedDurationMs}ms</p></div>
2777	                        )}
2778	                        {selectedNode.success !== undefined && (
2779	                          <div><span className="text-[10px] uppercase text-muted-foreground">Status</span>
2780	                            <p className={`mt-0.5 ${selectedNode.success ? 'text-green-400' : 'text-red-400'}`}>
2781	                              {selectedNode.success ? 'Success' : 'Failed'}</p></div>
2782	                        )}
2783	                        <div><span className="text-[10px] uppercase text-muted-foreground">Events</span>
2784	                          <p className="font-mono mt-0.5">{selectedNodeEvents.length}</p></div>
2785	                        <div><span className="text-[10px] uppercase text-muted-foreground">Children</span>
2786	                          <p className="font-mono mt-0.5">{selectedNodeChildren.length}</p></div>
2787	                      </div>
2788	
2789	                      {/* ── Lifecycle checklist ──────────────────────────── */}
2790	                      {(() => {
2791	                        const evSet = new Set(selectedNodeEvents.map(e => e.event))
2792	                        const childCount = selectedNodeChildren.filter(n => n.type === "raf-node").length
2793	                        const childDone  = selectedNodeEvents.filter(e => e.event === "node_done").length - (evSet.has("node_done") ? 1 : 0)
2794	                        const planChildCount = (planChildrenRef.current[selectedNode.id] || []).length
2795	
2796	                        type CheckState = "done" | "partial" | "waiting" | "pending"
2797	                        const step = (label: string, state: CheckState, detail?: string) => (
2798	                          <div key={label} className="flex items-center gap-2">
2799	                            <span className={`shrink-0 text-[11px] ${state === "done" ? "text-green-400" : state === "partial" ? "text-yellow-400" : state === "waiting" ? "text-blue-400 animate-pulse" : "text-muted-foreground/30"}`}>
2800	                              {state === "done" ? "✓" : state === "partial" ? "◑" : state === "waiting" ? "⏳" : "○"}
2801	                            </span>
2802	                            <span className={`text-[10px] ${state === "done" ? "text-foreground" : state === "waiting" ? "text-blue-300" : "text-muted-foreground"}`}>{label}</span>
2803	                            {detail && <span className="ml-auto text-[10px] font-mono text-muted-foreground/60">{detail}</span>}
2804	                          </div>
2805	                        )
2806	
2807	                        const isActive = selectedNode.active
2808	                        const isDone   = evSet.has("node_done")
2809	                        const hasMode  = evSet.has("mode_decided")
2810	                        const hasPlan  = evSet.has("plan_selected") || evSet.has("plan_ready")
2811	                        const hasChildren = childCount > 0
2812	                        const hasMerge = evSet.has("merge_done")
2813	                        const hasSpec  = evSet.has("spec_validation_final") || evSet.has("spec_repair_start")
2814	                        const hasAnalysis = evSet.has("analysis_done")
2815	                        const hasExec  = evSet.has("base_execute_done")
2816	                        const hasFail  = evSet.has("plan_validation_failed")
2817	
2818	                        const childState: CheckState = !hasChildren ? "pending" : (isDone || hasMerge) ? "done" : planChildCount > 0 && childDone < planChildCount ? "partial" : "done"
2819	
2820	                        return (
2821	                          <div className="rounded-md border border-border/50 bg-muted/20 p-2 space-y-1">
2822	                            <p className="text-[10px] uppercase text-muted-foreground font-medium mb-1.5">Lifecycle</p>
2823	                            {step("Node created",    "done")}
2824	                            {step("Mode decided",    hasMode ? "done" : isActive ? "waiting" : "pending")}
2825	                            {selectedNode.caseType === "recursive" || hasPlan ? step("Plan selected", hasFail ? "partial" : hasPlan ? "done" : isActive ? "waiting" : "pending", hasFail ? "retry" : undefined) : null}
2826	                            {(hasChildren || hasPlan) && step("Children running", childState, childState === "partial" ? `${childDone}/${planChildCount}` : undefined)}
2827	                            {(hasChildren || hasMerge) && step("Merge",           hasMerge ? "done" : hasChildren && !isDone ? "waiting" : "pending")}
2828	                            {step("Execute / output", hasExec ? "done" : !hasChildren && isActive ? "waiting" : hasExec || isDone ? "done" : "pending")}
2829	                            {step("Spec validation",  hasSpec ? "done" : isDone ? "done" : isActive ? "waiting" : "pending")}
2830	                            {step("Analysis",         hasAnalysis ? "done" : isDone ? "done" : isActive && (hasMerge || hasExec) ? "waiting" : "pending")}
2831	                            {step("Node done",        isDone ? "done" : isActive ? "waiting" : "pending")}
2832	                          </div>
2833	                        )
2834	                      })()}
2835	                      {selectedNode.goal && (
2836	                        <div className="group">
2837	                          <div className="flex items-center gap-2">
2838	                            <span className="text-[10px] uppercase text-muted-foreground">Goal</span>
2839	                            <button
2840	                              className="opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground hover:text-foreground transition-opacity"
2841	                              onClick={() => setExpandModal({ title: "Node Goal", content: selectedNode.goal! })}
2842	                            >⤢</button>
2843	                          </div>
2844	                          <p className="text-muted-foreground leading-relaxed mt-0.5">{selectedNode.goal}</p>
2845	                        </div>
2846	                      )}
2847	                      {selectedNode.output && (
2848	                        <div className="group">
2849	                          <div className="flex items-center gap-2">

---

## Claude

Now I have everything I need. Let me implement all 5 steps.

---

## Subagent Output

2847	                      {selectedNode.output && (
2848	                        <div className="group">
2849	                          <div className="flex items-center gap-2">
2850	                            <span className="text-[10px] uppercase text-muted-foreground">Output</span>
2851	                            <button
2852	                              className="opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground hover:text-foreground transition-opacity"
2853	                              onClick={() => setExpandModal({ title: "Node Output", content: selectedNode.output! })}
2854	                            >⤢</button>
2855	                          </div>
2856	                          <div className="bg-muted/50 p-2 rounded mt-1 whitespace-pre-wrap text-[10px] font-mono border border-border/50 text-muted-foreground overflow-y-auto">
2857	                            {selectedNode.output}</div>
2858	                        </div>
2859	                      )}
2860	                      {(selectedNodeProposals.length > 0 || selectedNodeVotes.length > 0) && (
2861	                        <div className="grid grid-cols-3 gap-2">
2862	                          <div className="rounded border border-border/60 p-2">
2863	                            <span className="text-[10px] uppercase text-muted-foreground">Proposals</span>
2864	                            <p className="font-mono mt-0.5">{selectedNodeProposals.length}</p></div>
2865	                          <div className="rounded border border-border/60 p-2">
2866	                            <span className="text-[10px] uppercase text-muted-foreground">Vote rounds</span>
2867	                            <p className="font-mono mt-0.5">{selectedNodeVotes.length}</p></div>
2868	                          <div className="rounded border border-border/60 p-2">
2869	                            <span className="text-[10px] uppercase text-muted-foreground">Links</span>
2870	                            <p className="font-mono mt-0.5">{selectedNodeChildren.length}</p></div>
2871	                        </div>
2872	                      )}
2873	                      {selectedNodeEvents.length > 0 && (
2874	                        <div><span className="text-[10px] uppercase text-muted-foreground">Event history</span>
2875	                          <div className="mt-1 space-y-1 overflow-y-auto">
2876	                            {selectedNodeEvents.map((ev, i) => (
2877	                              <div key={`${ev.event}-${ev.timestamp}-${i}`} className="flex items-center gap-2 rounded border border-border/50 px-2 py-1">
2878	                                <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: EVENT_COLORS[ev.event || ""] || "#64748b" }} />
2879	                                <span className="truncate">{eventLabel(ev)}</span>
2880	                                <span className="ml-auto font-mono text-[10px] text-muted-foreground">{relTs(ev.timestamp, runStartRef.current)}</span>
2881	                              </div>
2882	                            ))}</div></div>
2883	                      )}
2884	                    </>
2885	                  )}
2886	
2887	                  {/* ── Consortium-group: list all proposals ────────────── */}
2888	                  {selectedNode.type === "consortium-group" && (
2889	                    <>
2890	                      <div className="flex items-center gap-2 flex-wrap">
2891	                        <p className="text-muted-foreground text-[10px]">Task: <span className="text-foreground font-mono">{selectedNode.task}</span></p>
2892	                        {(inspectorCandidatesEvent as any)?.tier !== undefined && tierBadge((inspectorCandidatesEvent as any).tier)}
2893	                      </div>
2894	                      <p className="text-[10px] uppercase text-muted-foreground">{inspectorCandidates.length} proposals</p>
2895	                      <div className="space-y-2">
2896	                        {inspectorCandidates.map((cand: any, i: number) => {
2897	                          const payload = cand?.payload || cand || {}
2898	                          const fullText = payload.output || payload.mode || payload.plan || JSON.stringify(payload, null, 2)
2899	                          const preview = fullText.length > 300 ? fullText.slice(0, 300) + "…" : fullText
2900	                          return (
2901	                            <div key={i} className="group rounded-md border border-border/60 p-2 space-y-1">
2902	                              <div className="flex items-center gap-2">
2903	                                <span className="text-[10px] font-mono text-muted-foreground">Agent {i + 1}</span>
2904	                                <button
2905	                                  className="ml-auto opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground hover:text-foreground transition-opacity"
2906	                                  onClick={() => setExpandModal({ title: `Agent ${i + 1} Proposal`, content: fullText })}
2907	                                >⤢</button>
2908	                              </div>
2909	                              <p className="text-[10px] text-muted-foreground whitespace-pre-wrap">{preview}</p>
2910	                            </div>
2911	                          )
2912	                        })}
2913	                        {inspectorCandidates.length === 0 && <p className="text-[10px] text-muted-foreground/50">No candidate data yet.</p>}
2914	                      </div>
2915	                    </>
2916	                  )}
2917	
2918	                  {/* ── Jury-group: winner + all votes ──────────────────── */}
2919	                  {selectedNode.type === "jury-group" && (
2920	                    <>
2921	                      <div className="flex items-center gap-2 flex-wrap">
2922	                        <p className="text-muted-foreground text-[10px]">Task: <span className="text-foreground font-mono">{selectedNode.task}</span></p>
2923	                        {(inspectorCandidatesEvent as any)?.tier !== undefined && tierBadge((inspectorCandidatesEvent as any).tier)}
2924	                      </div>
2925	                      {inspectorWinnerId && (
2926	                        <div className="flex items-center gap-2">
2927	                          <span className="text-[10px] uppercase text-muted-foreground">Winner</span>
2928	                          <Badge className="text-[9px] bg-primary/20 text-primary border-primary/30">{optionLabel(inspectorWinnerId)}</Badge>
2929	                          {(inspectorJuryEvent as any)?.confidence !== undefined && (
2930	                            <span className="text-[10px] font-mono text-muted-foreground ml-auto">{((inspectorJuryEvent as any).confidence * 100).toFixed(0)}%</span>
2931	                          )}
2932	                        </div>
2933	                      )}
2934	                      <div className="space-y-1">
2935	                        {inspectorVotes.map((v: any, i: number) => {
2936	                          const vote = v.vote || v
2937	                          const agentIdx = v.agent_id ?? i
2938	                          const modelLabel = agentModelMap[`${inspectorOwner}:${inspectorTask}:jury:${agentIdx}`] || `agent-${agentIdx}`
2939	                          return (
2940	                            <div key={i} className="flex items-center gap-2 rounded border border-border/50 px-2 py-1 text-[10px]">
2941	                              <span className="font-mono text-purple-300 shrink-0 max-w-[100px] truncate" title={modelLabel}>{modelLabel}</span>
2942	                              <span className="text-muted-foreground">→</span>
2943	                              <span className="font-mono">{optionLabel(vote.winner_id)}</span>
2944	                              {vote.confidence && <span className="ml-auto font-mono text-muted-foreground">{(vote.confidence * 100).toFixed(0)}%</span>}
2945	                            </div>
2946	                          )
2947	                        })}
2948	                        {inspectorVotes.length === 0 && <p className="text-[10px] text-muted-foreground/50">No vote data yet.</p>}
2949	                      </div>
2950	                    </>
2951	                  )}
2952	
2953	                  {/* ── Agent proposal: full payload ─────────────────────── */}
2954	                  {selectedNode.type === "agent-proposal" && (
2955	                    <>
2956	                      <p className="text-muted-foreground text-[10px]">
2957	                        Proposer: <span className="font-mono text-amber-300">
2958	                          {agentModelMap[`${inspectorOwner}:${inspectorTask}:consortium:${selectedNode.candidateIndex}`] || `agent-${selectedNode.candidateIndex ?? "?"}`}
2959	                        </span>
2960	                      </p>
2961	                      {selectedNode.success && <Badge className="text-[9px] bg-primary/20 text-primary border-primary/30 w-fit">winner</Badge>}
2962	                      {(() => {
2963	                        const cand = inspectorCandidates[selectedNode.candidateIndex ?? -1]
2964	                        const payload = cand?.payload || cand || {}
2965	                        const fullText = payload.output || payload.mode || payload.plan || JSON.stringify(payload, null, 2)
2966	                        const preview = fullText.length > 500 ? fullText.slice(0, 500) + "…" : fullText
2967	                        return (
2968	                          <div className="group relative">
2969	                            <div className="bg-muted/50 p-2 rounded text-[10px] font-mono border border-border/50 text-muted-foreground whitespace-pre-wrap overflow-y-auto">
2970	                              {preview || "No payload data."}
2971	                            </div>
2972	                            {fullText.length > 500 && (
2973	                              <button
2974	                                className="mt-1 text-[10px] text-primary hover:underline"
2975	                                onClick={() => setExpandModal({ title: "Agent Proposal", content: fullText })}
2976	                              >Show full output ⤢</button>
2977	                            )}
2978	                          </div>
2979	                        )
2980	                      })()}
2981	                    </>
2982	                  )}
2983	
2984	                  {/* ── Juror vote: voted-for + ranked options ───────────── */}
2985	                  {selectedNode.type === "juror-vote" && (
2986	                    <>
2987	                      <p className="text-muted-foreground text-[10px]">
2988	                        Juror: <span className="font-mono text-purple-300">
2989	                          {agentModelMap[`${inspectorOwner}:${inspectorTask}:jury:${selectedNode.candidateIndex}`] || `agent-${selectedNode.candidateIndex ?? "?"}`}
2990	                        </span>
2991	                      </p>
2992	                      {(() => {
2993	                        const v = inspectorVotes[selectedNode.candidateIndex ?? -1]
2994	                        if (!v) return <p className="text-[10px] text-muted-foreground/50">No vote data.</p>
2995	                        const vote = v.vote || v
2996	                        return (

---

## Claude

Now I have everything I need. Let me implement all 5 steps cleanly and in order.

**Step 1 & 2 — Backend first:**

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\run_manager.py has been updated successfully.

---

## Claude

Now add `_build_fork_goal` and `fork_run` to `RunManager`. I'll insert them right before `_execute`:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\run_manager.py has been updated successfully.

---

## Claude

Now add the `ForkRequest` model and endpoint to `main.py`:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\main.py has been updated successfully.

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\main.py has been updated successfully.

---

## Claude

Backend is done. Now **Steps 3–5 — Frontend**. First extend the `Session` type:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Add the three fork state variables near the other run state variables:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Now add the `forkRun` async function after `cancelRun`:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Now update `onNodeClick` to pre-fill the fork goal when a completed raf-node is clicked:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Finally, add the fork UI section inside the raf-node inspector, after the event history block. This goes right before the closing `</>` of the raf-node section:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

All 5 steps are done. Now let me verify the whole thing compiles cleanly — check for TypeScript errors and Python syntax:

---

## Subagent Output

(Bash completed with no output)

---

## Subagent Output

run_manager.py OK
main.py OK

---

## Claude

Both clean. Let me do a final review of each changed file to confirm everything is correct:

---

## Subagent Output

Exit: 0

---

## Claude

Zero errors. Let me do a quick sanity grep to confirm all the new symbols are actually present in the right files:

---

## Subagent Output

C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\run_manager.py:78:    fork_source: Optional[str] = None
C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\run_manager.py:438:    def _build_fork_goal(
C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\run_manager.py:514:    def fork_run(
C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\run_manager.py:529:        enriched_goal = self._build_fork_goal(
C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\run_manager.py:552:        fork_state.fork_source = parent_state.run_id
C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\main.py:96:class ForkRequest(BaseModel):
C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\main.py:281:def fork_run(
C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\main.py:283:    body: ForkRequest,
C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\main.py:297:    fork_state = manager.fork_run(parent_state, body.node_id, body.goal)
C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\main.py:308:        "fork_source_run_id": run_id,
C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\main.py:309:        "fork_source_node_id": body.node_id,

---

## Subagent Output

62:  forkSourceRunId?: string
506:  const [forkGoalOverride, setForkGoalOverride] = useState("")
507:  const [forkLoading, setForkLoading] = useState(false)
508:  const [forkError, setForkError] = useState<string | null>(null)
1197:  const forkRun = async (nodeId: string, nodeGoal: string) => {
1214:          goal: forkGoalOverride.trim() !== nodeGoal.trim() ? forkGoalOverride.trim() || null : null,
1231:      const forkLabel = `[fork] ${(forkGoalOverride.trim() || nodeGoal).slice(0, 50)}`
1261:        forkSourceRunId: data.fork_source_run_id,
1266:      setGoal(forkGoalOverride.trim() || nodeGoal)
3017:                            <span className="text-[10px] font-semibold text-primary uppercase tracking-wider">Fork from here</span>
3027:                            value={forkGoalOverride}
3034:                          {forkError && (
3036:                              {forkError}
3040:                            onClick={() => forkRun(selectedNode.id, selectedNode.goal || "")}
3041:                            disabled={forkLoading || !forkGoalOverride.trim()}
3045:                            {forkLoading ? "Forking…" : "Fork from this node"}

---

## Claude

Everything is wired up exactly right. Here's a complete summary of what was built:

---

## Feature 1: Run Forking — Complete

### What changed and where

**`server/run_manager.py`**
- `RunState.fork_source: Optional[str]` (line 78) — tags a forked run with its parent's `run_id` for lineage
- `RunManager._build_fork_goal()` (line 438) — walks the parent's event list to find the clicked node, collects up to 5 ancestor goals as context, and optionally attaches the node's prior output (clamped to 1000 chars). Returns `None` if the node isn't found
- `RunManager.fork_run()` (line 514) — calls `_build_fork_goal`, then calls the existing `create_run()` with the enriched goal and the parent's full provider/model/agent config cloned

**`server/main.py`**
- `ForkRequest` model (line 96) — `node_id: str`, `goal: str | None`
- `POST /api/run/{run_id}/fork` endpoint (line 281) — validates the run token, calls `manager.fork_run()`, returns new `run_id + access_token + lineage fields`, or 404 if the node wasn't found

**`web/src/App.tsx`**
- `Session.forkSourceRunId / forkSourceNodeId` (line 62) — fork lineage stored on the session
- `forkGoalOverride / forkLoading / forkError` state (lines 506–508)
- `forkRun()` function (line 1197) — POSTs to the endpoint, resets all graph state, creates a new session entry with a `[fork]` label, and connects the WebSocket stream for the forked run
- `onNodeClick` updated (line ~2730) — pre-fills `forkGoalOverride` with the node's original goal whenever a completed `raf-node` is clicked
- **Fork panel in the node inspector** (line ~3010) — appears only on `success === true && !active` raf-nodes: shows an editable textarea pre-filled with the node's goal, an inline error display, and a "Fork from this node" button

### How to test
1. Run any task to completion
2. Click a green (base) or orange (recursive) completed node in the graph
3. The "Fork from here" panel appears at the bottom of the inspector
4. Edit the goal if you want a different approach, then click "Fork from this node"
5. A new `[fork]` session opens in the sidebar and its live graph appears

Ready to move on to Feature 2 (Goal Chaining / Pipelines) whenever you are.

---

## You

to be sure how this work , when i fork from this and i edit the goal it creats a whole new branh from that tree right , and it does not affect the current path that the orginal tree grapgh runs through right

---

## Claude

Yes, exactly right. Here's precisely what happens:

---

**The parent run is untouched.** It's already done — its graph, events, and output are all stored in the session. Forking never re-enters or modifies it in any way.

**The fork is a brand-new, completely independent run.** When you click "Fork from this node":

1. The backend creates a **new `run_id`** with its own thread, its own event queue, its own WebSocket stream
2. The goal sent to that new run is your edited goal, prefixed with the ancestor context pulled from the parent's events — that context is read-only, it's just text injected into the goal string
3. The new run starts from scratch and builds its own D3 graph from zero

**The session list shows both separately.** The parent session stays in the list with its original label and graph. The fork appears above it as `[fork] your edited goal…`. Clicking either one restores that session's graph independently.

**No shared mutable state.** The two runs don't know about each other at runtime. The only connection is the `fork_source_run_id` field stored on the fork's session object — that's purely metadata for display purposes, it has no effect on execution.

---

So in short: the original tree is frozen, the fork is a parallel universe that starts from where you clicked but goes wherever the new goal takes it. They can diverge completely.

Ready to move on to Feature 2?

---

## You

is it possible to fork in the middle of it runining or should we only fork at the end and why , my thought is that forking would either cause issues as a whole because it would not only affect the locked result that we had before from other stages if this was forked in a late stage but alsp affect it for future path if ti is forked in the earlier stages , a solution that I can think of is if when we fork we just copy it and make another path , what do you think

---

## Claude

Great question, and your instinct is correct. Let me break it down precisely.

---

## What our current implementation already enforces

The fork panel only appears when `!selectedNode.active && selectedNode.success` — so forking from a node that is **still running is already blocked**. You can only fork from a node that has fully completed and succeeded. That's the right guard.

---

## The scenario you're describing — forking a done node while the parent is still running

This is actually **completely safe** and we support it. Example:

```
Root (running)
  ├── Child A ✓ done  ← you fork from here
  ├── Child B ⏳ running
  └── Child C ⏳ running
```

Forking Child A while B and C are still running is fine because:
- The fork is a **new independent process** — it never touches the parent run
- The parent continues running B and C completely unaffected
- The fork just reads Child A's completed output and ancestor goals as **read-only text** to build context

---

## Your concern about the SpecLedger is the right one

The `SpecLedger` stores locked technology decisions that accumulate as the run progresses (e.g. `db=PostgreSQL` gets locked early and every downstream node is forced to respect it). Your concern is:

> If I fork from a late-stage node, do I inherit those locked decisions?

**Currently: No.** The fork starts a completely fresh `RafEngine` with an empty `SpecLedger`. The ancestor context is injected as plain text in the goal, not as actual locked ledger entries. This means the fork is free to make different decisions — which is usually *the point* of forking (trying a different approach).

**Is this a problem?** Only if you fork with the *same* goal and expect identical technology decisions to carry over. In that case the fork might re-derive the same decisions independently, or diverge. Right now that's acceptable because a fork is meant to be exploratory.

---

## Your proposed solution — "copy and make another path"

That's **exactly what we do**. The fork is a full copy of the config + enriched context, running as a completely independent path. The original tree is frozen. The two paths share nothing at runtime.

The one future enhancement worth considering: optionally letting the user **carry the parent's SpecLedger into the fork** when they want to explore a different goal but keep the same technology decisions locked. That would be an additional field on the `ForkRequest`. But for now, fresh engine per fork is the right default.

---

**Bottom line:** fork on completed nodes only (already enforced), parent run is always untouched, and your "two independent paths" mental model is exactly correct.

Ready to move to Feature 2?

---

## You

another is how would thid affect the amount of calls we do since forking still basically called the same agegent again and again and so on

---

## Claude

This is the right thing to worry about. Let me be precise about the actual call math.

---

## What a fork actually costs

A fork re-runs the **full Consortium+Jury pipeline from the forked node downward**. The ancestor context is just text injected into the goal — it doesn't add any extra agent calls, just slightly longer prompts. But everything from the forked node forward is a full re-run.

Each decision point costs `consortium_size + jury_size` calls. A single node has up to 6 decision points:

```
mode_decision    → C+J calls
plan             → C+J calls  (recursive only)
refine × N       → C+J calls per child (recursive only)
base_execute     → C+J calls
merge            → C+J calls  (recursive only)
analysis         → C+J calls
```

So with `consortium_size=3, jury_size=2` (5 calls per decision):

| Forked from | Rough call count |
|---|---|
| A base leaf node | ~15 calls (3 decisions × 5) |
| A recursive node with 3 children | ~90+ calls |
| The root of a deep run | Same as the entire original run |

**Multiple forks multiply this.** 3 forks from the root ≈ 3× the original run's total cost.

---

## The compounding risk you identified

You're right on both counts:

**Forking early (shallow node):** Re-runs the entire subtree beneath it — potentially as expensive as the full original run.

**Forking late (deep node):** Cheaper per call, but the ancestor context is longer (more tokens per call), and if the late node had locked SpecLedger decisions that the fork now re-derives differently, you may get a result that's internally inconsistent with what came before it in the original.

---

## Practical mitigations we should add

There are three things worth building into the fork flow:

**1. Reduced defaults for forks** — the fork should inherit the parent's config but override `consortium_size` and `jury_size` downward. Exploratory forks don't need the full ensemble. A `fork_consortium_size: 2, fork_jury_size: 1` default would cut costs roughly 60%.

**2. A cost warning in the UI** — before the fork fires, show the user what type of node they're forking from and a rough call estimate:

```
Forking a recursive node (depth 2, 3 children)
Estimated: ~60–90 agent calls
```

We can derive this from the node's `caseType` and `selectedNodeChildren.length` which we already have in the inspector.

**3. A tighter `max_nodes_total` cap for forks** — default the forked run to something like `min(parent_max_nodes, 20)` so an exploratory fork can't accidentally spin up a 50-node recursive explosion.

---

## What I'd recommend

Right now the fork inherits the parent's config verbatim which is the safe default for correctness but expensive for exploration. Before we move to Feature 2, I can add:
- A `max_nodes_total` slider in the fork panel (defaults to 15)
- A `consortium_size` override field in the fork panel (defaults to 2)
- A dynamic cost hint line beneath the fork button showing the node type + rough call estimate

This keeps the fork useful without letting it silently run up a large bill. Want me to add those now, or move to Feature 2 and come back to these later?

---

## You

i like this ideas but what if we have idk probably give the user the choice to change the amount of concsuotrum users and jury and also a cation information so they know what they getting into ?

---

## Claude

Good call. Let me implement all of that: consortium/jury size controls with sensible lower defaults, a dynamic cost estimate that reacts to the sliders, and a clear caution section. All three changes touch backend + frontend.

---

## Subagent Output

514	    def fork_run(
515	        self,
516	        parent_state: RunState,
517	        node_id: str,
518	        override_goal: Optional[str] = None,
519	    ) -> Optional[RunState]:
520	        """Create a new run forked from a specific node in an existing run.
521	
522	        The fork is a fully independent run whose goal is enriched with
523	        ancestor context from the parent's event log. It uses the same
524	        provider / model / agent configuration as the parent so the user
525	        doesn't have to re-configure anything.
526	
527	        Returns None (→ HTTP 404) if node_id is not found in parent events.
528	        """
529	        enriched_goal = self._build_fork_goal(
530	            parent_state.events, node_id, override_goal
531	        )
532	        if enriched_goal is None:
533	            return None
534	
535	        # Clone the parent's adapter config — fork inherits provider, model,
536	        # multi-model slots, tier routing, and API key.
537	        fork_state = self.create_run(
538	            enriched_goal,
539	            provider=parent_state.provider,
540	            model=parent_state.model,
541	            config_overrides=parent_state.config_overrides,
542	            jury_model=parent_state.jury_model,
543	            consortium_agents=parent_state.consortium_agents,
544	            jury_agents=parent_state.jury_agents,
545	            leaf_agents=parent_state.leaf_agents,
546	            mid_agents=parent_state.mid_agents,
547	            root_agents=parent_state.root_agents,
548	            api_key=parent_state.api_key,
549	        )
550	
551	        # Tag the new run with its origin so lineage is traceable
552	        fork_state.fork_source = parent_state.run_id
553	        return fork_state
554	
555	    def _execute(self, run: RunState) -> None:
556	        """Entry point for the background daemon thread that runs the engine."""
557	        try:
558	            config = self._build_config(run.config_overrides)
559	            # Expose the run-specific limit so approve_plan() validates correctly.
560	            run.max_children_per_plan = config.max_children_per_plan
561	
562	            # Build per-slot adapter lists.
563	            # If consortium_agents/jury_agents are specified, each slot gets its own model.

---

## Claude

Now update `fork_run` to accept size overrides, then update `ForkRequest`, then the frontend:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\run_manager.py has been updated successfully.

---

## Claude

Now update `ForkRequest` and the endpoint in `main.py`:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\main.py has been updated successfully.

---

## Claude

Now forward those fields from the endpoint to `fork_run`:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\main.py has been updated successfully.

---

## Claude

Backend done. Now the frontend. Add the two new state variables alongside the existing fork state:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Reset those two values when a new node is clicked, and update `onNodeClick`:

---

## Subagent Output

<tool_use_error>String to replace not found in file.
String:             onNodeClick={n => {
              setSelectedNode(n)
              setCenterTab("output")
              // Pre-fill the fork goal with the node's original goal
              if (n.type === "raf-node" && !n.active && n.success) {
                setForkGoalOverride(n.goal || "")
              } else {
                setForkGoalOverride("")
              }
              setForkError(null)
            }}</tool_use_error>

---

## Subagent Output

2834-            width={gSize.w} height={gSize.h}
2835-            onNodeClick={n => {
2836-              setSelectedNode(n)
2837-              setCenterTab("output")
2838-              // Pre-fill the fork goal whenever a completed raf-node is selected.
2839-              // This resets the textarea so it always reflects the clicked node's
2840-              // original goal rather than whatever was typed for a previous node.
2841-              if (n.type === "raf-node" && !n.active && n.success) {
2842:                setForkGoalOverride(n.goal || "")
2843-              } else {
2844-                setForkGoalOverride("")
2845-              }
2846-              setForkError(null)
2847-            }}
2848-            onBackgroundClick={() => setSelectedNode(null)}
2849-          />
2850-          {graphNodes.length === 0 && !running && (

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Pass the new values in `forkRun()`:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Now replace the fork panel UI with the full version including the caution section and size controls:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Now verify everything compiles:

---

## Subagent Output

Exit: 0

---

## Subagent Output

run_manager OK
main OK

---

## Claude

All clean. Here's exactly what the fork panel now looks like and how it works:

---

## What changed

**Backend (`run_manager.py` + `main.py`)**
- `ForkRequest` now accepts `consortium_size`, `jury_size`, `max_nodes_total`
- `fork_run()` merges those on top of the parent's config — everything else (domain, timeouts, model slots) carries over unchanged
- A hard `max_nodes_total: 20` cap is always sent from the frontend so a fork can never balloon into a 50-node run

**Frontend — the fork panel now has three sections:**

**1. Caution block** (color-coded, live-updating)
- Green `✓` — ≤15 calls (safe)
- Yellow `⚠` — 16–45 calls (moderate)
- Red `⚠` — 46+ calls (expensive, suggests reducing sizes)
- Shows the live call range `~6–12 agent calls` that recalculates instantly as the user moves the sliders
- Lists the three key facts the user needs to know before clicking

**2. Agent count controls** — `+/−` steppers for consortium (1–6) and jury (1–4), each showing the parent run's original value in parentheses so the user can see how much they're reducing

**3. Goal textarea + Fork button** — the button label itself shows the live call estimate: `Fork · ~6 calls`, so the user sees the cost on the button they're about to press

---

Ready to move on to Feature 2 (Goal Chaining)?

---

## You

ok good lets now move to feature 2

---

## Claude

Let me read the key parts of App.tsx I'll be touching before writing anything.

---

## Subagent Output

6:import { Zap, Network, Play, Square, Clock, Vote, FileText, Plus, Download, ZoomIn, ZoomOut, RotateCcw, History, SlidersHorizontal, Home } from "lucide-react"
16:import { Tabs, TabsList, TabsTrigger, TabsContent } from "./components/ui/tabs"
481:  const [sidebarTab, setSidebarTab] = useState<"sessions" | "config">("sessions")
1875:              className={`flex h-9 w-9 items-center justify-center rounded-md border ${sidebarTab === "sessions" ? "border-primary/50 bg-primary/10 text-primary" : "border-border/60 text-muted-foreground hover:bg-accent/50 hover:text-foreground"}`}
1877:              <History className="h-4 w-4" />
1883:              className={`flex h-9 w-9 items-center justify-center rounded-md border ${sidebarTab === "config" ? "border-primary/50 bg-primary/10 text-primary" : "border-border/60 text-muted-foreground hover:bg-accent/50 hover:text-foreground"}`}
1885:              <SlidersHorizontal className="h-4 w-4" />
1891:        <Tabs value={sidebarTab} onValueChange={v => setSidebarTab(v as "sessions" | "config")} className="flex w-full flex-col flex-1 min-h-0">
1893:            <TabsTrigger value="sessions" className="flex-1 rounded-none text-xs h-full data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
1895:            </TabsTrigger>
1896:            <TabsTrigger value="config" className="flex-1 rounded-none text-xs h-full data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
1898:            </TabsTrigger>
1902:          <TabsContent value="sessions" className="flex flex-col flex-1 min-h-0 mt-0 data-[state=inactive]:hidden">
2035:          <TabsContent value="config" className="flex flex-col flex-1 min-h-0 mt-0 data-[state=inactive]:hidden">
2462:            <TabsTrigger value="output" className="flex-1 px-1 rounded-none text-[10px] h-full gap-1 data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
2464:            </TabsTrigger>
2465:            <TabsTrigger value="timeline" className="flex-1 px-1 rounded-none text-[10px] h-full gap-1 data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
2467:            </TabsTrigger>
2468:            <TabsTrigger value="votes" className="flex-1 px-1 rounded-none text-[10px] h-full gap-1 data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
2471:            </TabsTrigger>
2472:            <TabsTrigger value="spec" className="flex-1 px-1 rounded-none text-[10px] h-full data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
2474:            </TabsTrigger>
2475:            <TabsTrigger value="tools" className="flex-1 px-1 rounded-none text-[10px] h-full data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
2477:            </TabsTrigger>
2478:            <TabsTrigger value="checks" className="flex-1 px-1 rounded-none text-[10px] h-full data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
2480:            </TabsTrigger>

---

## Claude

Let me stop and explain Feature 2 clearly before writing a single line of code.

---

## Feature 2: Goal Chaining / Pipelines — What it is

A **pipeline** is a saved sequence of goals where each step runs as a full RAF run, and the output of one step can automatically feed into the next.

---

### The core idea with a real example

Say you want to:
1. **Step 1** — Research a topic: `"Research the latest breakthroughs in quantum computing"`
2. **Step 2** — Write based on that research: `"Write a blog post about this: {{output}}"`
3. **Step 3** — Polish it: `"Make this more engaging for a general audience: {{output}}"`

The `{{output}}` placeholder gets replaced with whatever Step 1 produced before Step 2 starts. Step 3 gets Step 2's output. Each step is a completely normal RAF run — it goes through the full Consortium+Jury pipeline, can recurse, can spawn children. The pipeline just sequences them and pipes data between them.

---

### How it works under the hood

```
User clicks "Run Pipeline"
        ↓
POST /api/run  ←── Step 1 goal (no substitution needed)
        ↓
Wait for run_done via WebSocket
        ↓
Extract output from run_done event
        ↓
POST /api/run  ←── Step 2 goal with {{output}} replaced by Step 1's result
        ↓
Wait for run_done
        ↓
...and so on
```

The **frontend orchestrates this** — no new backend endpoint needed. Each step is just a regular `/api/run` POST. The sequencing and `{{output}}` substitution all happen in the browser.

---

### What the UI adds

**A third "Pipeline" tab** in the left sidebar with:
- A list of saved pipelines (persisted to `localStorage` so they survive refresh)
- A builder for the selected pipeline: numbered steps, each with an editable textarea
- A `{{output}}` insert button on steps 2+ so the user knows what to type
- Per-step status badges (pending / running / done / error) that update live as the pipeline runs
- A "View" button on each completed step that opens its full session in the graph

---

### What I'm about to build — implementation order

1. **`PipelinePanel.tsx`** (new file) — the entire visual builder component
2. **`App.tsx`** — add pipeline types, state, localStorage persistence, `waitForRunDone()` helper, `runPipeline()` execution function, CRUD operations, and the Pipeline tab in the sidebar

---

Is that what you had in mind? The key thing to confirm: each step is its own full RAF run (all agents, all recursion), and `{{output}}` is just a simple text substitution before the next step fires. Ready to implement?

---

## You

ok this is good but i do not want there to be another tab , it would look messy and to much infromation , is there a way we can show it or so on and does it run witht he raf program ? i want it to run with the raf program so they run parralllel to it

---

## Claude

Good call — a third tab would make the sidebar feel overloaded. Here are two cleaner options, then tell me which fits your vision:

---

## Option A — Floating Panel (my recommendation)

Add a **Pipeline** button to the graph toolbar (next to the zoom controls). Clicking it opens a draggable floating panel — same pattern as the existing work panel. The graph stays fully visible behind it, and the panel can be moved out of the way.

```
[Graph toolbar]  Simplified | Full  🔗 Pipeline  🔍 🔄 🔍  JSON  PDF
                                        ↑
                                  opens this ↓

┌─────────────────────────────┐
│ ⑂ Pipeline Builder     ✕   │  ← draggable, closeable
│─────────────────────────────│
│ Research → Write  ●  [▶ Run]│
│─────────────────────────────│
│ Step 1 ✓  Research QC       │
│ Step 2 ⏳  Write blog: {{}} │
│ Step 3 ○  Polish it         │
│                  [+ Step]   │
└─────────────────────────────┘
```

---

## Option B — Sessions tab section

Add a collapsible **"Pipelines"** section inside the existing Sessions tab, below the current session list. No new tab, no new panel — it lives where history already lives.

```
Sessions tab:
  [Clear Run]
  ────────────
  Session 1  ● done
  Session 2  ● done
  ────────────
  ▶ Pipelines (2)        ← collapses/expands
    Research → Write  ●
    Plan → Code        ○
  ────────────
  Server runs
```

---

## On running parallel with RAF

Both options support this. Each pipeline step fires its own **independent** `POST /api/run` with its own WebSocket — completely separate from the `wsRef` that drives the main graph. So:

- You can have a main RAF run showing live in the graph
- A pipeline running 3 steps in the background simultaneously
- Each step shows up as a session in the list when it completes
- The main graph is never touched by the pipeline

The pipeline doesn't interfere with the active run at all — it's background orchestration.

---

**Which option do you prefer — floating panel (A) or sessions tab section (B)?**

---

## You

lets do plan A

---

## Claude

Good choice. Let me read a few more things before writing — the toolbar area and where the work panel floats in the JSX so I follow the exact same pattern:

---

## Subagent Output

2640	                  <p className="text-xs text-center text-muted-foreground py-8">No votes yet.</p>
2641	                )}
2642	                {voteEvents.map((ev, i) => {
2643	                  const options = (ev.options as any[]) || []
2644	                  const votes = (ev.votes as any[]) || []
2645	                  return (
2646	                    <Card key={i} className="w-full min-w-0 max-w-full overflow-hidden">
2647	                      <CardContent className="min-w-0 max-w-full overflow-hidden p-3 space-y-2">
2648	                        <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-start gap-2">
2649	                          <div className="flex min-w-0 flex-wrap items-center gap-2">
2650	                            <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wider text-purple-400">{ev.task}</span>
2651	                            {ev.node_id && <span className="min-w-0 break-all text-[10px] font-mono text-muted-foreground">{ev.node_id}</span>}
2652	                          </div>
2653	                          <span className="shrink-0 text-xs font-mono">{ev.confidence ? (ev.confidence * 100).toFixed(0) + "%" : "—"}</span>
2654	                        </div>
2655	
2656	                        {options.length > 0 && (
2657	                          <div className="min-w-0 max-w-full space-y-1.5 overflow-hidden">
2658	                            <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Proposals</p>
2659	                            {options.map((opt: any, oi: number) => {
2660	                              const payload = opt.payload || opt
2661	                              const isWinner = ev.winner_id === opt.option_id
2662	                              const fullText = payload.output || payload.mode || payload.plan || JSON.stringify(payload, null, 2)
2663	                              const preview = fullText.length > 300 ? fullText.slice(0, 300) + "…" : fullText
2664	                              return (
2665	                                <div key={oi} className={`group min-w-0 max-w-full overflow-hidden rounded-md p-2 text-xs border ${isWinner ? "border-primary/50 bg-primary/5" : "border-border"}`}>
2666	                                  <div className="flex min-w-0 max-w-full flex-wrap items-center gap-1.5 mb-1">
2667	                                    <span className="min-w-0 font-mono text-[10px] text-muted-foreground">{optionLabel(opt.option_id)}</span>
2668	                                    {isWinner && <Badge className="text-[9px] h-4 px-1 bg-primary/20 text-primary border-primary/30">winner</Badge>}
2669	                                    <button

---

## Subagent Output

3398:        </div>
3399:      </div>
3403:        <ExpandModal
3406:          onClose={() => setExpandModal(null)}
3409:    </div>
3420:    </div>
3429:    </div>
3478:        </div>
3489:          </div>
3499:          </div>
3522:                  </div>
3528:                  </div>
3531:            </div>
3532:          </div>
3533:        </div>
3535:    </div>
3577:        </div>
3578:      </div>
3606:              </div>
3607:            </div>
3610:      </div>
3611:    </div>
3626:        </div>
3628:    </div>
3643:        </div>
3651:          </div>
3660:            </div>
3662:        </div>
3677:      </div>
3679:    </div>

---

## You

This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion of the conversation.

Summary:
1. Primary Request and Intent:
   The user owns the Recursive Agent Framework (RAF) project — a multi-agent orchestration system with a FastAPI backend, React/D3 frontend, and Consortium+Jury execution pattern. They requested two new features be added step by step:
   - **Feature 1: Run Forking** — Click any completed node in the D3 graph, branch from that point into a new independent run with the same ancestor context but optionally a different goal. The fork never affects the original run.
   - **Feature 2: Goal Chaining / Pipelines** — Chain multiple RAF runs sequentially so each step's output can feed the next via a `{{output}}` placeholder. Should run in parallel with (not replacing) the active RAF run. UI: a floating draggable panel opened from the graph toolbar (no new sidebar tab).
   
   Additional user constraints:
   - Comments on all new code
   - No new sidebar tabs (for Feature 2)
   - Pipelines run in parallel with the active main RAF run
   - Fork panel should show cost warnings and agent-count controls so users know what they're getting into

2. Key Technical Concepts:
   - **RunState** dataclass: stores run_id, goal, provider, model, events list, queue, thread, cancel_event, status, result
   - **RafEngine**: runs synchronously in a background thread (start-to-finish, cannot pause/resume)
   - **Consortium+Jury pattern**: N agents propose in parallel → separate jury votes on best answer
   - **SpecLedger**: locked technology decisions accumulating during a run (first-write-wins)
   - **Fork semantics**: new independent run with enriched goal (ancestor context as plain text prefix); fork gets fresh engine + empty SpecLedger
   - **WebSocket streaming**: `/api/stream/{run_id}?token=...` for live event delivery
   - **Session persistence**: localStorage via `SESSION_STORAGE_KEY`
   - **D3 force-directed graph**: `ExecutionGraph.tsx` with `onNodeClick` prop
   - **Node inspector**: floating overlay showing lifecycle, goal, output, events for selected node
   - **Fork restriction**: only offered on `!node.active && node.success` raf-nodes (completed nodes only)
   - **Cost estimation**: `perDecision = consortiumSize + jurySize`; base node ≈ 3×perDecision; recursive node ≈ (4+N)×perDecision + children
   - **Pipeline orchestration**: frontend-orchestrated sequential runs with `{{output}}` substitution; each step is an independent `/api/run` POST
   - **Floating panel pattern**: `fixed` positioning with pointer capture drag, same pattern as existing work panel

3. Files and Code Sections:

   - **`server/run_manager.py`**
     - Added `fork_source: Optional[str] = None` to `RunState` dataclass (after `api_key` field) for lineage tracking
     - Added `_build_fork_goal(parent_events, node_id, override_goal)` static method — scans events for `node_created`, collects up to 5 ancestor goals sorted by depth, gets prior `node_done` output (clamped 1000 chars), returns enriched goal string or `None` if node not found
     - Added `fork_run(parent_state, node_id, override_goal, consortium_size, jury_size, max_nodes_total)` method — merges size overrides into `fork_config = dict(parent_state.config_overrides)`, calls `create_run()` with cloned parent provider/model/agents, tags `fork_state.fork_source = parent_state.run_id`

   - **`server/main.py`**
     - Added `ForkRequest(BaseModel)` with fields:
       ```python
       class ForkRequest(BaseModel):
           node_id: str
           goal: str | None = None
           consortium_size: int | None = None
           jury_size: int | None = None
           max_nodes_total: int | None = None
       ```
     - Added `POST /api/run/{run_id}/fork` endpoint that validates token, calls `manager.fork_run(parent_state, body.node_id, body.goal, consortium_size=body.consortium_size, jury_size=body.jury_size, max_nodes_total=body.max_nodes_total)`, returns `{run_id, access_token, fork_source_run_id, fork_source_node_id}` or 404

   - **`web/src/App.tsx`**
     - Extended `Session` type: added `forkSourceRunId?: string` and `forkSourceNodeId?: string`
     - Added fork state variables:
       ```typescript
       const [forkGoalOverride, setForkGoalOverride] = useState("")
       const [forkLoading, setForkLoading] = useState(false)
       const [forkError, setForkError] = useState<string | null>(null)
       const [forkConsortiumSize, setForkConsortiumSize] = useState(2)
       const [forkJurySize, setForkJurySize] = useState(1)
       ```
     - Added `forkRun(nodeId, nodeGoal)` async function: POSTs to `/api/run/{runId}/fork` with `{node_id, goal, consortium_size, jury_size, max_nodes_total: 20}`, resets all graph/event state, creates `[fork]` labelled session, sets `runId`/`runToken`, calls `connectWs()`
     - Updated `onNodeClick` in ExecutionGraph props: pre-fills `forkGoalOverride` and resets `forkConsortiumSize=2`/`forkJurySize=1` when clicking completed raf-node; clears `forkError`
     - Added fork panel in node inspector (inside `!selectedNode.active && selectedNode.success && runId` check):
       - Inline IIFE `(() => { ... })()` for cost computation
       - `perDecision = forkConsortiumSize + forkJurySize`
       - Color-coded caution block (green ≤15, yellow 16-45, red 46+)
       - `Stepper` inline component for +/- controls with parent value shown
       - Consortium (1-6) and jury (1-4) steppers
       - Goal textarea pre-filled with node's original goal
       - Fork button label shows live call estimate: `Fork · ~N calls`

   - **`web/src/components/ExecutionGraph.tsx`** — Read for reference; has `onNodeClick?: (node: GraphNode) => void` prop; nodes have `type`, `active`, `success`, `goal`, `caseType`, `depth` fields

4. Errors and fixes:
   - **Edit tool string mismatch on `onNodeClick`**: The original `old_string` contained a comment text that didn't match exactly what was in the file after a previous edit. Fixed by running `grep -n "setForkGoalOverride\(n\.goal"` to find the exact content, then re-doing the edit with verbatim matched text.

5. Problem Solving:
   - **Fork cannot re-enter engine mid-run**: Solved by making forks brand-new independent runs with enriched goal (ancestor context injected as plain text). The fork gets a fresh `RafEngine` and fresh `SpecLedger`.
   - **Fork cost explosion**: Solved with: (1) reduced defaults (consortium=2, jury=1), (2) hard `max_nodes_total=20` cap, (3) live cost estimate UI that reacts to user slider changes, (4) color-coded caution block.
   - **SpecLedger not inherited by fork**: Confirmed intentional — fork is meant to explore different approaches; ancestor context is text-only, not locked decisions.
   - **Mid-run forking safety**: Fork panel only shows on `!node.active && node.success` so active nodes cannot be forked. Forking a completed child while the parent is still running is safe (independent processes).

6. All user messages:
   - "ok good now i want to add a new feature to our project but before we start i want you to have a full understanding of this project, I want you to go through the project step by step"
   - "ok good i like this give me the code and add comments to it for each implementation, you understand that this is a feature which we are adding to the current bigger project"
   - "to be sure how this work, when i fork from this and i edit the goal it creates a whole new branch from that tree right, and it does not affect the current path that the original tree graph runs through right"
   - "another is how would this affect the amount of calls we do since forking still basically called the same agent again and again and so on"
   - "i like this ideas but what if we have idk probably give the user the choice to change the amount of consortium users and jury and also a caution information so they know what they getting into?"
   - "ok good lets now move to feature 2"
   - "first i want you to explain it to me to make sure I understand exactly what I am saying" (interrupted the implementation to ask for explanation)
   - "ok this is good but i do not want there to be another tab, it would look messy and too much information, is there a way we can show it or so on and does it run with the raf program? i want it to run with the raf program so they run parallel to it"
   - "lets do plan A"

7. Pending Tasks:
   - **Feature 2: Goal Chaining / Pipelines** — Fully pending, not yet implemented. Chosen approach: floating draggable panel opened by a button in the graph toolbar. Each pipeline step is an independent `/api/run` POST. Steps run sequentially with `{{output}}` substitution. Pipeline runs in parallel with (does not replace) the active main RAF run.
   - Implementation requires:
     - New file: `web/src/components/PipelinePanel.tsx` with exported types `PipelineStep`, `Pipeline` and the panel component
     - `App.tsx` changes: types, state, persistence, `waitForRunDone()`, `runPipeline()`, `cancelPipeline()`, `viewPipelineStep()`, CRUD functions, drag handlers, toolbar button, floating panel JSX

8. Current Work:
   Feature 2 (Pipeline) implementation was about to begin. I had just read the toolbar area of `App.tsx` (lines 2640+) and grepped for the `ExpandModal` location (line 3403) to understand where the floating panel should be rendered. I determined:
   - The floating panel will use `fixed` positioning rendered at the top level of the App's return JSX
   - It follows the same drag-and-drop pattern as the existing work panel (`startWorkPanelDrag`/`moveWorkPanelDrag`/`endWorkPanelDrag` with pointer capture)
   - `GitBranch` icon from lucide-react for the toolbar button
   - `PipelinePanel.tsx` will export `PipelineStep` type, `Pipeline` type, and `PipelinePanel` component
   - `onViewStep(runId, token, goal)` callback pattern for viewing a step's session
   - `waitForRunDone` uses an isolated WebSocket per step, separate from the main `wsRef`
   - Pipeline steps use `plan_approval_required: false` and `skip_clarify: true` to run autonomously

9. Optional Next Step:
   Create `web/src/components/PipelinePanel.tsx` as a new file with the exported types and full UI component, then make all the corresponding `App.tsx` additions (state, functions, toolbar button, floating panel JSX).
   
   The user's last explicit instruction was: "lets do plan A" (Option A = floating draggable panel in graph toolbar). The implementation was in progress — I had read the relevant App.tsx sections and was about to write the code when the summary was requested.
   
   Direct quote showing exactly where I left off: I had just read lines 2640+ and run `grep -n "workPanelOpen\|workPanelPos\|ExpandModal"` and was about to write `PipelinePanel.tsx`. The next concrete step is creating that file and then making the targeted App.tsx additions.

If you need specific details from before compaction (like exact code snippets, error messages, or content you generated), read the full transcript at: C:\Users\dolap\.claude\projects\C--Users-dolap-Desktop-Projects-Recursive-Agent-Framework-Recursive-Agent-Framework-\9ae7dc15-7694-41a9-b8af-bab1cc84b796.jsonl
Continue the conversation from where it left off without asking the user any further questions. Resume directly — do not acknowledge the summary, do not recap what was happening, do not preface with "I'll continue" or similar. Pick up the last task as if the break never happened.

---

## Claude

You've hit your limit · resets 7:30am (America/New_York)

---

## You

ok now i want you to continue what we were doin g

---

## Claude

Let me read the current state of the key files before writing anything.

---

## Subagent Output

1	import { useEffect, useRef, useState, useCallback } from "react"
2	import Landing from "./Landing"
3	import type { PointerEvent } from "react"
4	import { motion, AnimatePresence } from "framer-motion"
5	import DOMPurify from "dompurify"
6	import { Zap, Network, Play, Square, Clock, Vote, FileText, Plus, Download, ZoomIn, ZoomOut, RotateCcw, History, SlidersHorizontal, Home } from "lucide-react"
7	import { Button } from "./components/ui/button"
8	import { Badge } from "./components/ui/badge"
9	import { ScrollArea } from "./components/ui/scroll-area"
10	import { Separator } from "./components/ui/separator"
11	import { Slider } from "./components/ui/slider"
12	import { Switch } from "./components/ui/switch"
13	import { Input } from "./components/ui/input"
14	import { Textarea } from "./components/ui/textarea"
15	import { Select } from "./components/ui/select"
16	import { Tabs, TabsList, TabsTrigger, TabsContent } from "./components/ui/tabs"
17	import { Card, CardContent } from "./components/ui/card"
18	import { ExecutionGraph, type GraphNode, type GraphEdge, type PhysicsParams, DEFAULT_PHYSICS } from "./components/ExecutionGraph"
19	import { PhysicsPanel } from "./components/PhysicsPanel"
20	
21	// ── types ─────────────────────────────────────────────────────────────────────
22	
23	type RafEvent = {
24	  event?: string; status?: string; node_id?: string; parent_id?: string | null
25	  depth?: number; goal?: string; output?: string; mode?: string; confidence?: number
26	  timestamp?: number; run_id?: string; error?: string; task?: string
27	  candidates?: unknown; options?: unknown; votes?: unknown; winner_id?: string
28	  children?: ChildSpec[]; result?: { output: string; metadata: { mode: string; questions?: string[]; confidence?: number } }
29	  question?: string; answer?: string; winner?: string; fast_path?: boolean; reason?: string
30	  domain?: string; required?: string[]; forbidden?: string[]; success_criteria?: string[]
31	  plan_child_id?: string; node_count?: number
32	  // plan recovery
33	  retry?: number; max_retries?: number; replaced_by?: string; plan_attempt?: number
34	  provider?: string; model?: string; role?: string; agent_index?: number
35	  duration_ms?: number; timeout_ms?: number
36	  cause?: "api_error" | "parse_error" | "schema_error"
37	}
38	
39	type ChildSpec = { child_id: string; goal: string; depends_on: string[] }
40	type NodeOutput = { output: string; mode: string; confidence: number; goal?: string }
41	type AgentSlot = { provider: string; model: string }
42	type ModelInfo = { id: string; label?: string; family?: string; tags?: string[] }
43	type SessionConfig = {
44	  provider: string; model: string; juryModel: string
45	  consortiumSize: number; jurySize: number; maxDepth: number; maxParallelChildren: number; maxNodesTotal: number
46	  forceRecursive: boolean; planGovernance: "auto" | "review" | "manual"; planRecovery: "off" | "auto" | "ask"; toolsEnabled: boolean
47	  multiModel: boolean; consortiumSlots: AgentSlot[]; jurySlots: AgentSlot[]
48	  tierRouting: boolean; leafSlots: AgentSlot[]; midSlots: AgentSlot[]; rootSlots: AgentSlot[]
49	  domainOverride: string; systemPrompt: string
50	}
51	type Session = {
52	  id: string; goal: string; provider: string; providerLabel?: string; status: string
53	  ts: number; nodeCount: number; output?: string; domain?: string; runId?: string | null; runToken?: string | null
54	  currentPhase?: string
55	  config?: SessionConfig
56	  events?: RafEvent[]
57	  graphNodes?: GraphNode[]
58	  graphLinks?: GraphEdge[]
59	  nodeOutputs?: Record<string, NodeOutput>
60	  result?: string | null
61	  // Fork lineage — present only when this session was created via the fork action
62	  forkSourceRunId?: string
63	  forkSourceNodeId?: string
64	}
65	type ServerRunSummary = {
66	  run_id: string
67	  goal: string
68	  provider: string
69	  model?: string | null
70	  status: string
71	  started_at: number
72	  completed_at?: number | null
73	  event_count: number
74	}
75	
76	const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8001"
77	const SESSION_STORAGE_KEY = "raf-web-sessions-v1"
78	const API_KEY_STORAGE_KEY = "raf-openrouter-api-key"
79	const DOMAIN_OPTIONS = ["", "technical", "culinary", "fitness", "creative", "business", "academic", "general"]
80

---

## Subagent Output

No files found

---

## Subagent Output

src\components\PhysicsPanel.tsx
src\components\ExecutionGraph.tsx

---

## Subagent Output

80	
81	function authHeaders(runToken?: string | null, json = false): Record<string, string> {
82	  const headers: Record<string, string> = {}
83	  if (json) headers["Content-Type"] = "application/json"
84	  if (runToken) headers["X-Run-Token"] = runToken
85	  return headers
86	}
87	
88	// ── Model strategy presets ─────────────────────────────────────────────────────
89	// Each preset is a named configuration that sets consortium + jury slots.
90	// The "fast-smart" pattern is the key insight: fast/cheap models generate
91	// diverse proposals in parallel (consortum), a single powerful model judges them (jury).
92	// This gives near-top-model quality at a fraction of the cost.
93	type ModelStrategy = {
94	  id: string
95	  label: string
96	  badge: string        // short label shown on the card
97	  tagline: string
98	  description: string
99	  consortiumNote: string
100	  midNote?: string     // shown only for tier-routing strategies (planner tier)
101	  juryNote: string
102	  multiModel: boolean
103	  consortiumSize: number
104	  jurySize: number
105	  consortiumSlots: AgentSlot[]
106	  jurySlots: AgentSlot[]
107	  tierRouting?: boolean
108	  leafSlots?: AgentSlot[]
109	  midSlots?: AgentSlot[]
110	  rootSlots?: AgentSlot[]
111	}
112	
113	const MODEL_STRATEGIES: ModelStrategy[] = [
114	  {
115	    id: "uniform",
116	    label: "Uniform",
117	    badge: "simple",
118	    tagline: "One model, everywhere",
119	    description: "The same model generates all proposals and casts all votes. Simplest setup, easiest to debug.",
120	    consortiumNote: "Any capable model works. Try qwen/qwen3-next-80b-a3b-instruct:free or qwen/qwen3.5-35b-a3b for a free start.",
121	    juryNote: "Same model as consortium — no separate jury config needed.",
122	    multiModel: false,
123	    consortiumSize: 3,
124	    jurySize: 2,
125	    consortiumSlots: [],
126	    jurySlots: [],
127	  },
128	  {
129	    id: "fast-smart",
130	    label: "Fast + Smart",
131	    badge: "⭐ recommended",
132	    tagline: "Cheap proposers, powerful judge",
133	    description: "Fast, cheap models each propose a candidate answer in parallel (consortium). One strong reasoning model makes the final call (jury). Best quality-per-dollar — the jury only runs once per decision regardless of consortium size.",
134	    consortiumNote: "Use fast/free models — speed and diversity matter more than raw power for proposers.",
135	    juryNote: "Use a strong reasoning model — it only runs once per decision, so cost is low.",
136	    multiModel: true,
137	    consortiumSize: 4,
138	    jurySize: 1,
139	    consortiumSlots: [
140	      { provider: "openrouter", model: "google/gemma-4-26b-a4b-it:free" },
141	      { provider: "openrouter", model: "qwen/qwen3.5-9b" },
142	      { provider: "openrouter", model: "qwen/qwen3-next-80b-a3b-instruct:free" },
143	      { provider: "openrouter", model: "meta-llama/llama-3.2-3b-instruct:free" },
144	    ],
145	    jurySlots: [
146	      { provider: "openrouter", model: "moonshotai/kimi-k2-thinking" },
147	    ],
148	  },
149	  {
150	    id: "ensemble",
151	    label: "Full Ensemble",
152	    badge: "high quality",
153	    tagline: "Diverse families propose, diverse judges vote",
154	    description: "Different model families write proposals, different families vote. Cross-family consensus is hard to fool — best for adversarial or high-stakes tasks where you want maximum independence between proposers and judges.",
155	    consortiumNote: "Mix model families: coding model, reasoning model, general model. Family diversity beats raw size.",
156	    juryNote: "Mix jury families too. Three independent reasoning judges from different labs rarely all agree on a bad answer.",
157	    multiModel: true,
158	    consortiumSize: 4,
159	    jurySize: 4,
160	    consortiumSlots: [
161	      { provider: "openrouter", model: "mistralai/devstral-2512" },
162	      { provider: "openrouter", model: "qwen/qwen3.5-35b-a3b" },
163	      { provider: "openrouter", model: "google/gemma-4-26b-a4b-it:free" },
164	      { provider: "openrouter", model: "mistralai/mistral-nemo" },
165	    ],
166	    jurySlots: [
167	      { provider: "openrouter", model: "moonshotai/kimi-k2-thinking" },
168	      { provider: "openrouter", model: "x-ai/grok-4.1-fast" },
169	      { provider: "openrouter", model: "z-ai/glm-5.1" },
170	      { provider: "openrouter", model: "openai/gpt-oss-120b:free" },
171	    ],
172	  },
173	  {
174	    id: "tiered",
175	    label: "Tiered Routing",
176	    badge: "depth-aware",
177	    tagline: "Right model for the right depth",
178	    description: "Small fast models handle deep leaf workers, capable models handle mid-level planning and synthesis, and the strongest models serve as the final referee (root node + analysis). Saves cost without sacrificing quality where it matters.",
179	    consortiumNote: "Leaf workers use fast/free models — speed and diversity matter more than raw power for simple subtasks.",
180	    midNote: "Planners and mergers use capable mid-tier models — structured reasoning for decomposition and synthesis.",
181	    juryNote: "Root and analysis (referee) always use the strongest models. Mid-tier also serves as jury floor so weak models never grade weak models.",
182	    multiModel: true,
183	    tierRouting: true,
184	    consortiumSize: 2,
185	    jurySize: 1,
186	    consortiumSlots: [],
187	    jurySlots: [],
188	    leafSlots: [
189	      { provider: "openrouter", model: "google/gemma-4-26b-a4b-it:free" },
190	      { provider: "openrouter", model: "qwen/qwen3.5-9b" },
191	      { provider: "openrouter", model: "meta-llama/llama-3.2-3b-instruct:free" },
192	    ],
193	    midSlots: [
194	      { provider: "openrouter", model: "mistralai/devstral-2512" },
195	      { provider: "openrouter", model: "qwen/qwen3.5-35b-a3b" },
196	      { provider: "openrouter", model: "mistralai/mistral-nemo" },
197	    ],
198	    rootSlots: [
199	      { provider: "openrouter", model: "moonshotai/kimi-k2-thinking" },

---

## Subagent Output

200	      { provider: "openrouter", model: "x-ai/grok-4.1-fast" },
201	      { provider: "openrouter", model: "openai/gpt-oss-120b:free" },
202	    ],
203	  },
204	]
205	
206	const EVENT_COLORS: Record<string, string> = {
207	  node_created: "#3b82f6", node_done: "#22c55e", jury_votes: "#a855f7",
208	  consortium_candidates: "#f59e0b", run_done: "#64748b", mode_decided: "#06b6d4",
209	  base_execute_start: "#f97316", base_execute_done: "#10b981", clarify_answered: "#3b82f6",
210	  spec_extracted: "#8b5cf6", scope_drift_detected: "#ef4444", tool_called: "#ef4444",
211	  plan_validation_failed: "#f97316", plan_retry_start: "#fb923c", plan_retry_done: "#22c55e",
212	  plan_abandoned: "#ef4444", plan_replaced: "#a3e635",
213	  model_call_start: "#38bdf8", model_call_done: "#22c55e", model_call_failed: "#ef4444",
214	  model_call_timeout: "#f59e0b", model_call_fallback: "#a855f7",
215	}
216	
217	// Tier badge display helpers
218	const TIER_LABELS: Record<number, { label: string; className: string }> = {
219	  0: { label: "T0·Leaf",    className: "bg-sky-950/60 text-sky-300" },
220	  1: { label: "T1·Plan",   className: "bg-amber-950/60 text-amber-300" },
221	  2: { label: "T2·Ref",    className: "bg-rose-950/60 text-rose-300" },
222	}
223	function tierBadge(tier: number | undefined): JSX.Element | null {
224	  if (tier === undefined || tier === null) return null
225	  const t = TIER_LABELS[tier]
226	  if (!t) return null
227	  return <span className={`rounded px-1 py-0.5 text-[9px] font-mono font-semibold shrink-0 ${t.className}`}>{t.label}</span>
228	}
229	
230	const TIMELINE_FILTER_EVENTS: Record<string, string[]> = {
231	  node:      ["node_created", "node_done", "mode_decided"],
232	  vote:      ["jury_votes", "consortium_candidates"],
233	  execution: ["base_execute_start", "base_execute_done", "merge_done", "plan_selected"],
234	  model:     ["model_call_start", "model_call_done", "model_call_failed", "model_call_timeout", "model_call_fallback"],
235	  error:     ["scope_drift_detected", "tool_blocked", "plan_validation_failed", "plan_abandoned", "model_call_failed", "model_call_timeout"],
236	}
237	
238	// Expected-next hints for the run health panel
239	const PHASE_NEXT_HINT: Record<string, string> = {
240	  "run_started":          "spec_extract → mode_decide",
241	  "spec_extracted":       "mode_decide → plan / base_execute",
242	  "mode_decided":         "plan_start or base_execute_start",
243	  "plan_start":           "consortium_candidates → jury_votes → plan_selected",
244	  "plan_selected":        "children_start → node_created × N",
245	  "children_start":       "node_created events for each child",
246	  "consortium_candidates":"jury_votes → decision",
247	  "jury_votes":           "next task or base_execute_done",
248	  "base_execute_start":   "base_execute_done → analysis_done",
249	  "base_execute_done":    "analysis_done → node_done",
250	  "merge_done":           "analysis_done → node_done",
251	  "analysis_done":        "node_done",
252	  "node_done":            "sibling nodes or merge_done → run_done",
253	  "plan_validation_failed": "plan_retry_start or plan_abandoned",
254	  "plan_retry_done":      "children_start → node_created × N",
255	}
256	
257	// ts = Python time.time() in seconds; start = Date.now() in ms
258	function relTs(ts: number | undefined, start: number | null): string {
259	  if (!ts || !start) return ""
260	  const ms = Math.round(ts * 1000 - start)
261	  if (Math.abs(ms) < 1000) return `+${ms}ms`
262	  return `+${(ms / 1000).toFixed(1)}s`
263	}
264	
265	const CAUSE_LABELS: Record<string, { label: string; detail: string }> = {
266	  api_error:    { label: "API Error",    detail: "Model was unreachable or provider returned an error" },
267	  parse_error:  { label: "Parse Error",  detail: "Model ran but returned invalid JSON" },
268	  schema_error: { label: "Schema Error", detail: "Model ran but output had the wrong shape" },
269	}
270	
271	function eventLabel(ev: RafEvent): string {
272	  const key = ev.event || ev.status || ""
273	  const map: Record<string, string> = {
274	    node_created: "Node Created", node_done: "Node Done", jury_votes: "Jury Vote",
275	    consortium_candidates: "Consortium Proposals", run_done: "Run Complete",
276	    clarify_answered: "Clarification answered", mode_decided: "Mode Decided",
277	    base_execute_start: "Base Executing", base_execute_done: "Base Done",
278	    spec_extracted: "Spec Extracted", merge_done: "Merge Done",
279	    plan_selected: "Plan Selected", scope_drift_detected: "Scope Drift",
280	    tool_called: "Tool Called", analysis_done: "Analysis Done",
281	    run_started: "Run Started",
282	    plan_validation_failed: "Plan Validation Failed", plan_retry_start: "Plan Retry",
283	    plan_retry_done: "Plan Retry Done", plan_abandoned: "Plan Abandoned",
284	    plan_replaced: "Plan Replaced",
285	    model_call_start: "Model Call Started", model_call_done: "Model Call Done",
286	    model_call_failed: "Model Call Failed", model_call_timeout: "Model Call Timeout",
287	    model_call_fallback: "Model Fallback",
288	  }
289	  const base = map[key] || key.replace(/_/g, " ")
290	  // For model call events, append role + model for quick identification
291	  if (key.startsWith("model_call_") && ev.role && ev.model) {
292	    return `${base} · ${ev.role} [${ev.model}]`
293	  }
294	  return base
295	}
296	
297	// Convert internal "option-N" IDs to human-readable "Option N+1" labels.
298	function optionLabel(id: string | undefined): string {
299	  if (!id) return "?"

---

## Subagent Output

300	  const m = id.match(/^option-(\d+)$/)
301	  return m ? `Option ${parseInt(m[1]) + 1}` : id
302	}
303	
304	function phaseForEvent(ev: RafEvent): string | null {
305	  const key = ev.event || ev.status || ""
306	  const map: Record<string, string> = {
307	    run_started: "Starting",
308	    node_created: "Queued",
309	    mode_decide_start: "Deciding",
310	    mode_decided: "Mode chosen",
311	    plan_start: "Planning",
312	    plan_selected: "Plan selected",
313	    plan_ready: "Waiting approval",
314	    children_start: "Spawning children",
315	    consortium_candidates: "Proposals",
316	    jury_votes: "Voting",
317	    model_call_start: "Waiting on model",
318	    model_call_done: "Model returned",
319	    model_call_failed: "Model failed",
320	    model_call_timeout: "Model timed out",
321	    base_execute_start: "Executing",
322	    base_execute_done: "Executed",
323	    merge_done: "Merged",
324	    analysis_done: "Analyzed",
325	    child_failed: "Child failed",
326	    node_done: "Done",
327	    run_done: ev.error ? "Error" : ev.status === "cancelled" ? "Cancelled" : "Done",
328	  }
329	  return map[key] || null
330	}
331	
332	function graphEndpointId(endpoint: string | GraphNode): string {
333	  return typeof endpoint === "string" ? endpoint : endpoint.id
334	}
335	
336	function cleanGraphLinks(links: GraphEdge[]): GraphEdge[] {
337	  return links.map(link => ({
338	    id: link.id,
339	    source: graphEndpointId(link.source),
340	    target: graphEndpointId(link.target),
341	    edgeType: link.edgeType,
342	  }))
343	}
344	
345	function cleanGraphNodes(nodes: GraphNode[]): GraphNode[] {
346	  return nodes.map(({ vx: _vx, vy: _vy, fx: _fx, fy: _fy, ...node }) => ({ ...node }))
347	}
348	
349	function outputMapToRecord(map: Map<string, NodeOutput>): Record<string, NodeOutput> {
350	  return Object.fromEntries(map.entries())
351	}
352	
353	function outputRecordToMap(record?: Record<string, NodeOutput>): Map<string, NodeOutput> {
354	  return new Map(Object.entries(record || {}))
355	}
356	
357	function normalizeSlots(slots: AgentSlot[], size: number, provider: string, model: string): AgentSlot[] {
358	  return Array.from({ length: size }, (_, i) => slots[i] || { provider, model })
359	}
360	
361	function loadStoredSessions(): Session[] {
362	  try {
363	    const raw = window.localStorage.getItem(SESSION_STORAGE_KEY)
364	    if (!raw) return []
365	    const parsed = JSON.parse(raw)
366	    return Array.isArray(parsed) ? parsed.slice(0, 20) : []
367	  } catch {
368	    return []
369	  }
370	}
371	
372	function formatOutput(text: string): string {
373	  // Sanitize FIRST, then apply safe formatting so no injected HTML survives
374	  const safe = DOMPurify.sanitize(text, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] })
375	  return safe
376	    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
377	    .replace(/^#{1,3}\s+(.+)$/gm, '<strong style="color:#60a5fa;font-size:1rem">$1</strong>')
378	    .replace(/^[-•]\s+(.+)$/gm, '• $1')
379	    .replace(/\n/g, '<br/>')
380	}
381	
382	// ── ExpandModal ───────────────────────────────────────────────────────────────
383	function tryPrettyJson(text: string): string {
384	  try {
385	    const parsed = JSON.parse(text)
386	    return JSON.stringify(parsed, null, 2)
387	  } catch {
388	    return text
389	  }
390	}
391	
392	function ExpandModal({ title, content, onClose }: { title: string; content: string; onClose: () => void }) {
393	  const formatted = tryPrettyJson(content)
394	  const [copied, setCopied] = useState(false)
395	
396	  useEffect(() => {
397	    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose() }
398	    window.addEventListener("keydown", handler)
399	    return () => window.removeEventListener("keydown", handler)
400	  }, [onClose])
401	
402	  const copy = () => {
403	    navigator.clipboard.writeText(content).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500) })
404	  }
405	
406	  return (
407	    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
408	      <div
409	        className="relative w-[min(90vw,860px)] max-h-[85vh] flex flex-col rounded-xl border border-border bg-card shadow-2xl overflow-hidden"
410	        onClick={e => e.stopPropagation()}
411	      >
412	        <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
413	          <span className="text-sm font-medium">{title}</span>
414	          <div className="flex items-center gap-2">
415	            <button
416	              onClick={copy}
417	              className="text-[10px] px-2 py-1 rounded border border-border text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors"
418	            >
419	              {copied ? "Copied!" : "Copy"}
420	            </button>
421	            <button onClick={onClose} className="text-muted-foreground hover:text-foreground text-base leading-none px-1">✕</button>
422	          </div>
423	        </div>
424	        <div className="flex-1 min-h-0 overflow-y-auto p-4">
425	          <pre className="text-xs font-mono whitespace-pre-wrap break-words text-foreground/90 leading-relaxed">{formatted}</pre>
426	        </div>
427	      </div>
428	    </div>
429	  )
430	}
431	
432	// ── main component ─────────────────────────────────────────────────────────────
433	
434	export default function App() {
435	  // landing page — shown once per session; dismissed on "Launch App" / "Try Demo"
436	  const [showLanding, setShowLanding] = useState<boolean>(() => !sessionStorage.getItem("raf-entered"))
437	
438	  // api key (user-supplied, persisted in localStorage)
439	  const [apiKey, setApiKey] = useState<string>(() => localStorage.getItem(API_KEY_STORAGE_KEY) || "")
440	
441	  // run config
442	  const [goal, setGoal] = useState("")
443	  const [provider, setProvider] = useState("mock")
444	  const [model, setModel] = useState("")
445	  const [juryModel, setJuryModel] = useState("")
446	  const [maxDepth, setMaxDepth] = useState(4)
447	  const [maxParallelChildren, setMaxParallelChildren] = useState(4)
448	  const [maxNodesTotal, setMaxNodesTotal] = useState(50)
449	  const [forceRecursive, setForceRecursive] = useState(false)

---

## Subagent Output

450	  const [planGovernance, setPlanGovernance] = useState<"auto" | "review" | "manual">("auto")
451	  const [planRecovery, setPlanRecovery] = useState<"off" | "auto" | "ask">("off")
452	  const [toolsEnabled, setToolsEnabled] = useState(false)
453	  const [domainOverride, setDomainOverride] = useState("")
454	  const [systemPrompt, setSystemPrompt] = useState("")
455	  const [providers, setProviders] = useState<string[]>(["mock"])
456	  const [models, setModels] = useState<Record<string, string[]>>({})
457	  const [modelCatalog, setModelCatalog] = useState<Record<string, ModelInfo[]>>({})
458	  const [availableProviders, setAvailableProviders] = useState<string[]>(["mock"])
459	  const [consortiumSize, setConsortiumSize] = useState(3)
460	  const [jurySize, setJurySize] = useState(3)
461	  const [multiModel, setMultiModel] = useState(false)
462	  const [consortiumSlots, setConsortiumSlots] = useState<AgentSlot[]>([])
463	  const [jurySlots, setJurySlots] = useState<AgentSlot[]>([])
464	  const [tierRouting, setTierRouting] = useState(false)
465	  const [leafSlots, setLeafSlots] = useState<AgentSlot[]>([])
466	  const [midSlots, setMidSlots] = useState<AgentSlot[]>([])
467	  const [rootSlots, setRootSlots] = useState<AgentSlot[]>([])
468	  const [modelPickerOpen, setModelPickerOpen] = useState(false)
469	  const [appliedStrategy, setAppliedStrategy] = useState<string | null>(null)
470	  const [expandModal, setExpandModal] = useState<{ title: string; content: string } | null>(null)
471	
472	  // ui state
473	  const [centerTab, setCenterTab] = useState<"output" | "timeline" | "votes" | "spec" | "tools" | "checks">("output")
474	  const [timelineFilter, setTimelineFilter] = useState<"all" | "node" | "vote" | "execution" | "model" | "error">("all")
475	  const [sessions, setSessions] = useState<Session[]>(() => loadStoredSessions())
476	  const [serverRuns, setServerRuns] = useState<ServerRunSummary[]>([])
477	  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
478	  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
479	  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
480	  const [sidebarWidth, setSidebarWidth] = useState(264)
481	  const [sidebarTab, setSidebarTab] = useState<"sessions" | "config">("sessions")
482	  const [workPanelOpen, setWorkPanelOpen] = useState(true)
483	  const [workspaceMode, setWorkspaceMode] = useState<"work" | "demo">("work")
484	  const [workPanelPos, setWorkPanelPos] = useState({ left: 272, top: 56 })
485	
486	  // run state
487	  const [runId, setRunId] = useState<string | null>(null)
488	  const [runToken, setRunToken] = useState<string | null>(null)
489	  const [runStatus, setRunStatus] = useState<"idle" | "running" | "done" | "error" | "cancelled">("idle")
490	  const [events, setEvents] = useState<RafEvent[]>([])
491	  const [nodeOutputs, setNodeOutputs] = useState<Map<string, NodeOutput>>(new Map())
492	  const [runResult, setRunResult] = useState<string | null>(null)
493	  const [detectedDomain, setDetectedDomain] = useState<string | null>(null)
494	  const [clarifyQuestion, setClarifyQuestion] = useState<string | null>(null)
495	  const [clarifyAnswer, setClarifyAnswer] = useState("")
496	  const [accumulatedGoal, setAccumulatedGoal] = useState("")
497	  const [pendingPlan, setPendingPlan] = useState<{ nodeId: string; children: ChildSpec[] } | null>(null)
498	  const [nodeCount, setNodeCount] = useState(0)
499	  const [currentPhase, setCurrentPhase] = useState("Idle")
500	  const [partialFailures, setPartialFailures] = useState(0)
501	  const [staleWarning, setStaleWarning] = useState(false)
502	  const [lastEventAge, setLastEventAge] = useState<number | null>(null)
503	
504	  // Fork state — controls the fork panel shown inside the node inspector
505	  // when the user selects a completed raf-node and wants to branch from it.
506	  const [forkGoalOverride, setForkGoalOverride] = useState("")
507	  const [forkLoading, setForkLoading] = useState(false)
508	  const [forkError, setForkError] = useState<string | null>(null)
509	  // Agent count overrides for the fork — default to reduced values so
510	  // exploratory forks don't automatically run at full parent cost.
511	  const [forkConsortiumSize, setForkConsortiumSize] = useState(2)
512	  const [forkJurySize, setForkJurySize] = useState(1)
513	
514	  // physics
515	  const [physics, setPhysics] = useState<PhysicsParams>({ ...DEFAULT_PHYSICS })
516	
517	  // graph state
518	  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([])
519	  const [graphLinks, setGraphLinks] = useState<GraphEdge[]>([])
520	  const [graphMode, setGraphMode] = useState<"simplified" | "full">("simplified")
521	  const [backendStatus, setBackendStatus] = useState<"checking" | "connected" | "offline">("checking")
522	  const [zoomCommand, setZoomCommand] = useState<{ action: "in" | "out" | "reset"; nonce: number } | undefined>()
523	  const graphModeRef = useRef<"simplified" | "full">("simplified")
524	  const graphNodesRef = useRef<GraphNode[]>([])
525	  const graphLinksRef = useRef<GraphEdge[]>([])
526	  const graphRef = useRef<HTMLDivElement>(null)
527	  const svgRef = useRef<SVGSVGElement | null>(null)
528	  const [gSize, setGSize] = useState({ w: 800, h: 600 })
529	
530	  // websocket
531	  const wsRef = useRef<WebSocket | null>(null)
532	  const isRunningRef = useRef(false)
533	  const reconnectAttemptsRef = useRef(0)
534	  const runStartRef = useRef<number | null>(null)
535	  const workPanelDragRef = useRef<{ x: number; y: number; left: number; top: number } | null>(null)
536	  const sidebarResizeRef = useRef<{ x: number; width: number } | null>(null)
537	  // dedup: prevents replay from doubling events on reconnect
538	  const seenEventsRef = useRef<Set<string>>(new Set())
539	  // store raw satellite events so toggling to "full" can retroactively add them
540	  const satelliteEventsRef = useRef<RafEvent[]>([])
541	  const planChildrenRef = useRef<Record<string, ChildSpec[]>>({})
542	  const planChildNodeRef = useRef<Record<string, string>>({})
543	  const nodeCreatedTsRef = useRef<Record<string, number>>({})
544	  const lastEventTsRef = useRef<number>(0)
545	
546	  useEffect(() => { graphModeRef.current = graphMode }, [graphMode])
547	
548	  // When switching to "full", retroactively add satellite nodes from stored events
549	  useEffect(() => {
550	    if (graphMode === "full") {
551	      satelliteEventsRef.current.forEach(ev => addSatelliteNodes(ev))
552	    }
553	    // simplified: leave nodes as-is (removing mid-run would be jarring)
554	  }, [graphMode]) // eslint-disable-line
555	
556	  // graph resize observer
557	  useEffect(() => {
558	    const upd = () => {
559	      if (!graphRef.current) return
560	      const r = graphRef.current.getBoundingClientRect()
561	      if (r.width > 10 && r.height > 10) setGSize({ w: r.width, h: r.height })
562	    }
563	    upd()
564	    const obs = new ResizeObserver(upd)
565	    if (graphRef.current) obs.observe(graphRef.current)
566	    return () => obs.disconnect()
567	  }, [])
568	
569	  // live timer: update lastEventAge every second while running; stale warning every 5s
570	  useEffect(() => {
571	    const tick = window.setInterval(() => {
572	      if (lastEventTsRef.current > 0) {
573	        const age = Date.now() - lastEventTsRef.current
574	        setLastEventAge(Math.floor(age / 1000))
575	        if (isRunningRef.current) setStaleWarning(age > 90_000)
576	      } else {
577	        setLastEventAge(null)
578	      }
579	    }, 1000)
580	    return () => window.clearInterval(tick)
581	  }, [])
582	
583	  // fetch providers on mount
584	  useEffect(() => {
585	    fetch(`${API_BASE}/api/models`)
586	      .then(r => r.json())
587	      .then(d => {
588	        setProviders(d.providers || ["mock"])
589	        setModels(d.models || {})
590	        setModelCatalog(d.model_catalog || {})
591	        setAvailableProviders(d.available || ["mock"])
592	        if (d.defaults?.provider) setProvider(d.defaults.provider)
593	        if (d.defaults?.model) setModel(d.defaults.model)
594	      })
595	      .catch(() => {})
596	  }, [])
597	
598	  useEffect(() => {
599	    let cancelled = false

---

## Subagent Output

600	    const check = () => {
601	      const controller = new AbortController()
602	      const timeout = window.setTimeout(() => controller.abort(), 2500)
603	      fetch(`${API_BASE}/api/health`, { signal: controller.signal })
604	        .then(r => { if (!cancelled) setBackendStatus(r.ok ? "connected" : "offline") })
605	        .catch(() => { if (!cancelled) setBackendStatus("offline") })
606	        .finally(() => window.clearTimeout(timeout))
607	    }
608	    check()
609	    const timer = window.setInterval(check, 10000)
610	    return () => { cancelled = true; window.clearInterval(timer) }
611	  }, [])
612	
613	  const refreshServerRuns = useCallback(async () => {
614	    try {
615	      const res = await fetch(`${API_BASE}/api/runs`)
616	      if (!res.ok) return
617	      const data = await res.json() as { runs?: ServerRunSummary[] }
618	      setServerRuns(data.runs || [])
619	    } catch {
620	      setServerRuns([])
621	    }
622	  }, [])
623	
624	  useEffect(() => {
625	    if (backendStatus === "connected") refreshServerRuns()
626	  }, [backendStatus, refreshServerRuns])
627	
628	  useEffect(() => {
629	    try {
630	      window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessions.slice(0, 20)))
631	    } catch {
632	      // Storage is best-effort; active runs should not depend on it.
633	    }
634	  }, [sessions])
635	
636	  useEffect(() => {
637	    if (!multiModel) return
638	    setConsortiumSlots(prev => normalizeSlots(prev, consortiumSize, provider, model))
639	  }, [multiModel, consortiumSize, provider, model])
640	
641	  useEffect(() => {
642	    if (!multiModel) return
643	    setJurySlots(prev => normalizeSlots(prev, jurySize, provider, juryModel || model))
644	  }, [multiModel, jurySize, provider, model, juryModel])
645	
646	  const currentConfig = useCallback((): SessionConfig => ({
647	    provider, model, juryModel, consortiumSize, jurySize, maxDepth, maxParallelChildren, maxNodesTotal,
648	    forceRecursive, planGovernance, planRecovery, toolsEnabled, multiModel, consortiumSlots, jurySlots,
649	    tierRouting, leafSlots, midSlots, rootSlots,
650	    domainOverride, systemPrompt,
651	  }), [provider, model, juryModel, consortiumSize, jurySize, maxDepth, maxParallelChildren, maxNodesTotal, forceRecursive, planGovernance, planRecovery, toolsEnabled, multiModel, consortiumSlots, jurySlots, tierRouting, leafSlots, midSlots, rootSlots, domainOverride, systemPrompt])
652	
653	  useEffect(() => {
654	    if (!activeSessionId) return
655	    const graphSnapshot = cleanGraphNodes(graphNodes)
656	    const linkSnapshot = cleanGraphLinks(graphLinks)
657	    const outputsSnapshot = outputMapToRecord(nodeOutputs)
658	    setSessions(prev => prev.map(s => s.id === activeSessionId ? {
659	      ...s,
660	      provider,
661	      runId,
662	      runToken,
663	      status: runStatus,
664	      nodeCount,
665	      output: runResult || s.output,
666	      result: runResult,
667	      domain: detectedDomain || s.domain,
668	      currentPhase,
669	      config: currentConfig(),
670	      events,
671	      graphNodes: graphSnapshot,
672	      graphLinks: linkSnapshot,
673	      nodeOutputs: outputsSnapshot,
674	    } : s))
675	  }, [activeSessionId, provider, runId, runToken, runStatus, nodeCount, runResult, detectedDomain, currentPhase, currentConfig, events, graphNodes, graphLinks, nodeOutputs])
676	
677	  const restoreSession = useCallback((session: Session) => {
678	    const restoredEvents = session.events || []
679	    const restoredNodes = cleanGraphNodes(session.graphNodes || [])
680	    const restoredLinks = cleanGraphLinks(session.graphLinks || [])
681	    setActiveSessionId(session.id)
682	    setGoal(session.goal)
683	    setProvider(session.config?.provider || session.provider)
684	    setModel(session.config?.model || "")
685	    setJuryModel(session.config?.juryModel || "")
686	    if (session.config) {
687	      setConsortiumSize(session.config.consortiumSize)
688	      setJurySize(session.config.jurySize)
689	      setMaxDepth(session.config.maxDepth)
690	      setMaxParallelChildren(session.config.maxParallelChildren || 4)
691	      setMaxNodesTotal(session.config.maxNodesTotal)
692	      setForceRecursive(session.config.forceRecursive)
693	      setPlanGovernance(session.config.planGovernance || "auto")
694	      setPlanRecovery(session.config.planRecovery || "off")
695	      setToolsEnabled(session.config.toolsEnabled)
696	      setMultiModel(session.config.multiModel)
697	      setConsortiumSlots(session.config.consortiumSlots || [])
698	      setJurySlots(session.config.jurySlots || [])
699	      setTierRouting(session.config.tierRouting || false)
700	      setLeafSlots(session.config.leafSlots || [])
701	      setMidSlots(session.config.midSlots || [])
702	      setRootSlots(session.config.rootSlots || [])
703	      setDomainOverride(session.config.domainOverride || "")
704	      setSystemPrompt(session.config.systemPrompt || "")
705	    }
706	    setRunId(session.runId || null)
707	    setRunToken(session.runToken || null)
708	    setRunStatus((session.status as typeof runStatus) || "idle")
709	    setEvents(restoredEvents)
710	    graphNodesRef.current = restoredNodes
711	    graphLinksRef.current = restoredLinks
712	    setGraphNodes(restoredNodes)
713	    setGraphLinks(restoredLinks)
714	    setNodeOutputs(outputRecordToMap(session.nodeOutputs))
715	    setRunResult(session.result || session.output || null)
716	    setDetectedDomain(session.domain || null)
717	    setSelectedNode(null)
718	    setClarifyQuestion(null)
719	    setPendingPlan(null)
720	    setNodeCount(session.nodeCount || restoredNodes.filter(n => n.type === "raf-node").length)
721	    setCurrentPhase(session.currentPhase || (session.status === "running" ? "Running" : "Idle"))
722	    runStartRef.current = restoredEvents.find(ev => ev.timestamp)?.timestamp
723	      ? (restoredEvents.find(ev => ev.timestamp)!.timestamp! * 1000)
724	      : null
725	    seenEventsRef.current = new Set(restoredEvents.map(ev => `${ev.event ?? ev.status ?? ""}:${ev.node_id ?? ""}:${String(ev.timestamp ?? "")}`))
726	    satelliteEventsRef.current = restoredEvents.filter(ev => ev.event === "consortium_candidates" || ev.event === "jury_votes")
727	    planChildrenRef.current = {}
728	    planChildNodeRef.current = {}
729	    nodeCreatedTsRef.current = {}
730	    restoredEvents.forEach(ev => {
731	      if ((ev.event === "plan_selected" || ev.event === "plan_ready") && ev.node_id && ev.children) {
732	        planChildrenRef.current[ev.node_id] = ev.children
733	      }
734	      if (ev.event === "node_created" && ev.node_id) {
735	        if (ev.timestamp) nodeCreatedTsRef.current[ev.node_id] = ev.timestamp
736	        if (ev.parent_id && ev.plan_child_id) {
737	          planChildNodeRef.current[`${ev.parent_id}:${ev.plan_child_id}`] = ev.node_id
738	        }
739	      }
740	    })
741	  }, [])
742	
743	  // add node to graph — idempotent: silently skips if id already exists
744	  const addGraphNode = useCallback((id: string, parentId: string | null | undefined, depth: number, goal?: string, type: GraphNode["type"] = "raf-node") => {
745	    if (graphNodesRef.current.some(n => n.id === id)) return
746	    const parent = parentId ? graphNodesRef.current.find(n => n.id === parentId) : null
747	    const node: GraphNode = {
748	      id, type,
749	      label: id === "root" ? "root" : id.replace("node-", "#"),

---

## Subagent Output

750	      detail: goal ? goal.slice(0, 60) : id,
751	      active: true, depth, goal,
752	      ...(parent && parent.x !== undefined ? {
753	        x: parent.x + (Math.random() - 0.5) * 60,
754	        y: parent.y! + 80,
755	      } : {}),
756	    }
757	    graphNodesRef.current = [...graphNodesRef.current, node]
758	    if (parentId) {
759	      const linkId = `${parentId}->${id}`
760	      if (!graphLinksRef.current.some(l => l.id === linkId)) {
761	        graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: parentId, target: id, edgeType: "parallel" }]
762	      }
763	    }
764	    setGraphNodes([...graphNodesRef.current])
765	    setGraphLinks([...graphLinksRef.current])
766	  }, [])
767	
768	  // add consortium/jury satellite nodes for a single event (used by both live and replay)
769	  // Pattern: RAF-node → consortium-group → agent-proposal (× N)
770	  //          RAF-node → jury-group       → juror-vote    (× N)
771	  const addSatelliteNodes = useCallback((ev: RafEvent) => {
772	    if (!ev.node_id) return
773	    const task = ev.task || ""
774	    const parentDepth = graphNodesRef.current.find(n => n.id === ev.node_id)?.depth ?? 0
775	
776	    if (ev.event === "consortium_candidates") {
777	      const candidates = (ev as any).candidates as any[] || []
778	      const groupId = `${ev.node_id}-consortium-${task}`
779	      // Create consortium-group node attached to the RAF node
780	      if (!graphNodesRef.current.some(n => n.id === groupId)) {
781	        const parent = graphNodesRef.current.find(n => n.id === ev.node_id)
782	        const groupNode: GraphNode = {
783	          id: groupId, type: "consortium-group",
784	          label: "C", detail: `Consortium (${task})`,
785	          active: true, depth: parentDepth + 1,
786	          ownerNodeId: ev.node_id, task,
787	          hint: task,
788	          ...(parent?.x !== undefined ? { x: parent.x + (Math.random() - 0.5) * 40, y: parent.y! + 60 } : {}),
789	        }
790	        graphNodesRef.current = [...graphNodesRef.current, groupNode]
791	        const linkId = `${ev.node_id}->${groupId}`
792	        if (!graphLinksRef.current.some(l => l.id === linkId)) {
793	          graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: ev.node_id!, target: groupId, edgeType: "flow" }]
794	        }
795	      }
796	      // Create agent-proposal nodes attached to the group
797	      candidates.forEach((cand: any, idx: number) => {
798	        const agentId = `${ev.node_id}-agent-${task}-${idx}`
799	        if (!graphNodesRef.current.some(n => n.id === agentId)) {
800	          const groupNode = graphNodesRef.current.find(n => n.id === groupId)
801	          const payload = cand?.payload || cand || {}
802	          const hint = payload.output ? payload.output.slice(0, 40) : payload.mode || `Agent ${idx + 1}`
803	          const agentNode: GraphNode = {
804	            id: agentId, type: "agent-proposal",
805	            label: `A${idx + 1}`, detail: hint,
806	            active: true, depth: parentDepth + 2,
807	            ownerNodeId: ev.node_id, task, candidateIndex: idx,
808	            hint,
809	            ...(groupNode?.x !== undefined ? { x: groupNode.x + (idx - (candidates.length - 1) / 2) * 30, y: groupNode.y! + 50 } : {}),
810	          }
811	          graphNodesRef.current = [...graphNodesRef.current, agentNode]
812	          const linkId = `${groupId}->${agentId}`
813	          if (!graphLinksRef.current.some(l => l.id === linkId)) {
814	            graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: groupId, target: agentId, edgeType: "parallel" }]
815	          }
816	        }
817	      })
818	      setGraphNodes([...graphNodesRef.current])
819	      setGraphLinks([...graphLinksRef.current])
820	    }
821	
822	    if (ev.event === "jury_votes") {
823	      const votes = (ev as any).votes as any[] || []
824	      const winnerId = (ev as any).winner_id as string | undefined
825	      const groupId = `${ev.node_id}-jury-${task}`
826	      // Create jury-group node
827	      if (!graphNodesRef.current.some(n => n.id === groupId)) {
828	        const parent = graphNodesRef.current.find(n => n.id === ev.node_id)
829	        const groupNode: GraphNode = {
830	          id: groupId, type: "jury-group",
831	          label: "J", detail: `Jury (${task})`,
832	          active: true, depth: parentDepth + 1,
833	          ownerNodeId: ev.node_id, task,
834	          hint: `winner: ${winnerId || "?"}`,
835	          ...(parent?.x !== undefined ? { x: parent.x + (Math.random() - 0.5) * 40, y: parent.y! + 60 } : {}),
836	        }
837	        graphNodesRef.current = [...graphNodesRef.current, groupNode]
838	        const linkId = `${ev.node_id}->${groupId}`
839	        if (!graphLinksRef.current.some(l => l.id === linkId)) {
840	          graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: ev.node_id!, target: groupId, edgeType: "flow" }]
841	        }
842	      }
843	      // Create juror-vote nodes
844	      votes.forEach((v: any, idx: number) => {
845	        const jurorId = `${ev.node_id}-juror-${task}-${idx}`
846	        if (!graphNodesRef.current.some(n => n.id === jurorId)) {
847	          const groupNode = graphNodesRef.current.find(n => n.id === groupId)
848	          const vote = v.vote || v
849	          const isWinner = vote.winner_id === winnerId
850	          const hint = vote.winner_id ? `→ ${optionLabel(vote.winner_id)}` : `Juror ${idx + 1}`
851	          const jurorNode: GraphNode = {
852	            id: jurorId, type: "juror-vote",
853	            label: `V${idx + 1}`, detail: hint,
854	            active: false, depth: parentDepth + 2,
855	            ownerNodeId: ev.node_id, task, candidateIndex: idx,
856	            hint,
857	            success: isWinner,
858	            ...(groupNode?.x !== undefined ? { x: groupNode.x + (idx - (votes.length - 1) / 2) * 30, y: groupNode.y! + 50 } : {}),
859	          }
860	          graphNodesRef.current = [...graphNodesRef.current, jurorNode]
861	          const linkId = `${groupId}->${jurorId}`
862	          if (!graphLinksRef.current.some(l => l.id === linkId)) {
863	            graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: groupId, target: jurorId, edgeType: "parallel" }]
864	          }
865	        }
866	      })
867	      // Mark winning agent-proposal if present
868	      if (winnerId) {
869	        const winnerAgentId = `${ev.node_id}-agent-${task}-${winnerId}`
870	        // Try matching by option index embedded in winner_id (e.g. "option-0")
871	        const match = winnerId.match(/(\d+)$/)
872	        if (match) {
873	          const winIdx = parseInt(match[1])
874	          const winAgentId = `${ev.node_id}-agent-${task}-${winIdx}`
875	          graphNodesRef.current = graphNodesRef.current.map(n =>
876	            n.id === winAgentId ? { ...n, success: true, hint: (n.hint || "") + " ✓" } : n
877	          )
878	        } else if (graphNodesRef.current.some(n => n.id === winnerAgentId)) {
879	          graphNodesRef.current = graphNodesRef.current.map(n =>
880	            n.id === winnerAgentId ? { ...n, success: true } : n
881	          )
882	        }
883	      }
884	      setGraphNodes([...graphNodesRef.current])
885	      setGraphLinks([...graphLinksRef.current])
886	    }
887	  }, [addGraphNode])
888	
889	  const updateGraphNode = useCallback((id: string, patch: Partial<GraphNode>) => {
890	    graphNodesRef.current = graphNodesRef.current.map(n => n.id === id ? { ...n, ...patch } : n)
891	    setGraphNodes([...graphNodesRef.current])
892	  }, [])
893	
894	  const addDependencyEdgesForParent = useCallback((parentId: string) => {
895	    const children = planChildrenRef.current[parentId] || []
896	    if (children.length === 0) return
897	    let changed = false
898	    const nextLinks = [...graphLinksRef.current]
899	    for (const child of children) {
900	      const targetNodeId = planChildNodeRef.current[`${parentId}:${child.child_id}`]
901	      if (!targetNodeId) continue
902	      for (const depChildId of child.depends_on || []) {
903	        const sourceNodeId = planChildNodeRef.current[`${parentId}:${depChildId}`]
904	        if (!sourceNodeId) continue
905	        const linkId = `dep:${sourceNodeId}->${targetNodeId}`
906	        if (!nextLinks.some(link => link.id === linkId)) {
907	          nextLinks.push({ id: linkId, source: sourceNodeId, target: targetNodeId, edgeType: "dependency" })
908	          changed = true
909	        }
910	      }
911	    }
912	    if (changed) {
913	      graphLinksRef.current = nextLinks
914	      setGraphLinks([...graphLinksRef.current])
915	    }
916	  }, [])
917	
918	  // process a single event — deduplicated so reconnect replay is idempotent
919	  const processEvent = useCallback((ev: RafEvent) => {
920	    const key = `${ev.event ?? ev.status ?? ""}:${ev.node_id ?? ""}:${String(ev.timestamp ?? "")}`
921	    if (seenEventsRef.current.has(key)) return
922	    seenEventsRef.current.add(key)
923	    setEvents(prev => [...prev, ev])
924	    lastEventTsRef.current = Date.now()
925	    setStaleWarning(false)
926	    const phase = phaseForEvent(ev)
927	    if (phase) setCurrentPhase(phase)
928	    if (phase && ev.node_id) updateGraphNode(ev.node_id, { phase, active: ev.event !== "node_done" })
929	
930	    if (ev.event === "node_created") {
931	      if (ev.timestamp && ev.node_id) nodeCreatedTsRef.current[ev.node_id] = ev.timestamp
932	      addGraphNode(ev.node_id!, ev.parent_id, ev.depth ?? 0, ev.goal)
933	      if (phase && ev.node_id) updateGraphNode(ev.node_id, { phase })
934	      if (ev.parent_id && ev.plan_child_id && ev.node_id) {
935	        planChildNodeRef.current[`${ev.parent_id}:${ev.plan_child_id}`] = ev.node_id
936	        addDependencyEdgesForParent(ev.parent_id)
937	      }
938	      setNodeCount(c => c + 1)
939	    }
940	
941	    if (ev.event === "node_done") {
942	      const id = ev.node_id!
943	      const createdAt = nodeCreatedTsRef.current[id]
944	      const durationMs = createdAt && ev.timestamp ? Math.max(0, Math.round((ev.timestamp - createdAt) * 1000)) : undefined
945	      graphNodesRef.current = graphNodesRef.current.map(n =>
946	        n.id === id ? { ...n, active: false, success: true,
947	          caseType: ev.mode === "recursive" ? "recursive" : "base",
948	          output: ev.output, confidence: ev.confidence, phase: "Done", durationMs } : n
949	      )

---

## Subagent Output

950	      setGraphNodes([...graphNodesRef.current])
951	      if (ev.output) {
952	        setNodeOutputs(prev => new Map(prev).set(id, {
953	          output: ev.output!, mode: ev.mode || "base",
954	          confidence: ev.confidence || 0, goal: ev.goal,
955	        }))
956	      }
957	    }
958	
959	    if (ev.event === "mode_decided") {
960	      const id = ev.node_id!
961	      graphNodesRef.current = graphNodesRef.current.map(n =>
962	        n.id === id ? { ...n, caseType: (ev.winner === "recursive" || (ev as any).mode === "recursive") ? "recursive" : "base", phase: phase || n.phase } : n
963	      )
964	      setGraphNodes([...graphNodesRef.current])
965	    }
966	
967	    if (ev.event === "spec_extracted") {
968	      if ((ev as any).domain) setDetectedDomain((ev as any).domain)
969	    }
970	
971	    if (ev.event === "run_done") {
972	      isRunningRef.current = false
973	      const st = (ev as any).status
974	      setRunStatus(ev.error ? "error" : st === "cancelled" ? "cancelled" : "done")
975	      const result = (ev as any).result
976	      if (result?.output) { setRunResult(result.output); setCenterTab("output") }
977	      if (result?.metadata?.mode === "clarify") {
978	        const q = result.metadata.questions?.[0]
979	        if (q) setClarifyQuestion(q)
980	      }
981	      setActiveSessionId(prev => {
982	        if (prev) {
983	          const finalSt = ev.error ? "error" : st === "cancelled" ? "cancelled" : "done"
984	          setSessions(ss => ss.map(s => s.id === prev ? { ...s, status: finalSt, output: result?.output } : s))
985	        }
986	        return prev
987	      })
988	    }
989	
990	    if (ev.event === "child_failed") {
991	      setPartialFailures(prev => prev + 1)
992	    }
993	
994	    // Plan recovery: create visual nodes for each attempt so the graph shows the history
995	    if (ev.event === "plan_validation_failed" && ev.node_id) {
996	      const attempt = ev.plan_attempt ?? 0
997	      const failId = `${ev.node_id}-plan-fail-${attempt}`
998	      if (!graphNodesRef.current.some(n => n.id === failId)) {
999	        const parent = graphNodesRef.current.find(n => n.id === ev.node_id)
1000	        graphNodesRef.current = [...graphNodesRef.current, {
1001	          id: failId, type: "referee-check" as const,
1002	          label: `PF${attempt}`, detail: "Plan failed validation",
1003	          active: false, success: false,
1004	          depth: (parent?.depth ?? 0) + 1,
1005	          ownerNodeId: ev.node_id, task: "plan_validation_failed",
1006	          hint: ev.reason ? ev.reason.slice(0, 30) : "validation failed",
1007	          ...(parent?.x !== undefined ? { x: parent.x + (attempt - 1) * 50, y: parent.y! + 70 } : {}),
1008	        }]
1009	        const linkId = `${ev.node_id}->${failId}`
1010	        if (!graphLinksRef.current.some(l => l.id === linkId)) {
1011	          graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: ev.node_id!, target: failId, edgeType: "flow" as const }]
1012	        }
1013	        setGraphNodes([...graphNodesRef.current])
1014	        setGraphLinks([...graphLinksRef.current])
1015	      }
1016	    }
1017	
1018	    if (ev.event === "plan_abandoned" && ev.node_id) {
1019	      updateGraphNode(ev.node_id, { phase: "Plan abandoned", success: false })
1020	    }
1021	
1022	    if (ev.event === "plan_replaced" && ev.node_id) {
1023	      updateGraphNode(ev.node_id, { phase: "Plan replaced" })
1024	    }
1025	
1026	    if (ev.event === "merge_done" && ev.node_id) {
1027	      const mergeId = `${ev.node_id}-merge`
1028	      if (!graphNodesRef.current.some(n => n.id === mergeId)) {
1029	        const parentNode = graphNodesRef.current.find(n => n.id === ev.node_id)
1030	        const mergeNode: GraphNode = {
1031	          id: mergeId, type: "merge-group",
1032	          label: "M", detail: "Merge",
1033	          active: false, depth: (parentNode?.depth ?? 0) + 1,
1034	          ownerNodeId: ev.node_id, task: "merge",
1035	          hint: "merge",
1036	          success: true,
1037	          ...(parentNode?.x !== undefined ? { x: parentNode.x, y: parentNode.y! + 70 } : {}),
1038	        }
1039	        graphNodesRef.current = [...graphNodesRef.current, mergeNode]
1040	        // Flow edge from parent to merge-group
1041	        const flowLinkId = `${ev.node_id}->${mergeId}`
1042	        if (!graphLinksRef.current.some(l => l.id === flowLinkId)) {
1043	          graphLinksRef.current = [...graphLinksRef.current, { id: flowLinkId, source: ev.node_id!, target: mergeId, edgeType: "flow" }]
1044	        }
1045	        // Merge (backflow) edges from each completed child to merge-group
1046	        const children = planChildrenRef.current[ev.node_id] || []
1047	        for (const child of children) {
1048	          const childNodeId = planChildNodeRef.current[`${ev.node_id}:${child.child_id}`]
1049	          if (childNodeId) {
1050	            const mergeLinkId = `merge:${childNodeId}->${mergeId}`
1051	            if (!graphLinksRef.current.some(l => l.id === mergeLinkId)) {
1052	              graphLinksRef.current = [...graphLinksRef.current, { id: mergeLinkId, source: childNodeId, target: mergeId, edgeType: "merge" }]
1053	            }
1054	          }
1055	        }
1056	        setGraphNodes([...graphNodesRef.current])
1057	        setGraphLinks([...graphLinksRef.current])
1058	      }
1059	    }
1060	
1061	    // plan_ready is the real backend event name
1062	    if ((ev.event === "plan_ready" || ev.event === "plan_selected") && ev.node_id) {
1063	      const kids = (ev as any).children as ChildSpec[] | undefined
1064	      if (kids) {
1065	        planChildrenRef.current[ev.node_id] = kids
1066	        addDependencyEdgesForParent(ev.node_id)
1067	        if (ev.event === "plan_ready") setPendingPlan({ nodeId: ev.node_id!, children: kids })
1068	      }
1069	    }
1070	
1071	    // Store satellite events regardless of mode so toggling to "full" can replay them
1072	    if ((ev.event === "consortium_candidates" || ev.event === "jury_votes") && ev.node_id) {
1073	      satelliteEventsRef.current = [...satelliteEventsRef.current, ev]
1074	    }
1075	    // Add satellite nodes now only if already in full mode
1076	    if (graphModeRef.current === "full") {
1077	      addSatelliteNodes(ev)
1078	    }
1079	  }, [addGraphNode, updateGraphNode, addDependencyEdgesForParent])
1080	
1081	  // websocket connection
1082	  const connectWs = useCallback((rid: string, token: string) => {
1083	    if (wsRef.current) { wsRef.current.onclose = null; wsRef.current.close() }
1084	    const wsUrl = API_BASE.replace(/^http/, "ws") + `/api/stream/${rid}?token=${encodeURIComponent(token)}`
1085	    const ws = new WebSocket(wsUrl)
1086	    wsRef.current = ws
1087	    ws.onopen = () => { reconnectAttemptsRef.current = 0 }
1088	    ws.onmessage = (msg) => {
1089	      try {
1090	        const ev: RafEvent = JSON.parse(msg.data)
1091	        if (ev.event === "run_started" && !runStartRef.current) runStartRef.current = Date.now()
1092	        processEvent(ev)
1093	      } catch {}
1094	    }
1095	    ws.onclose = () => {
1096	      if (!isRunningRef.current) return
1097	      const attempts = reconnectAttemptsRef.current
1098	      if (attempts >= 6) return
1099	      reconnectAttemptsRef.current = attempts + 1
1100	      setTimeout(() => { if (isRunningRef.current) connectWs(rid, token) }, Math.min(500 * Math.pow(2, attempts), 16000))
1101	    }
1102	  }, [processEvent])
1103	
1104	  // start run
1105	  // continueSession=true: clarification continuation — preserve existing timeline/graph,
1106	  // just append new events. Does NOT create a new session entry.
1107	  const startRun = async (goalText: string, skipClarify = false, continueSession = false) => {
1108	    if (!goalText.trim()) return
1109	    const runGoal = goalText.trim()
1110	
1111	    if (!continueSession) {
1112	      graphNodesRef.current = []; graphLinksRef.current = []
1113	      seenEventsRef.current = new Set()
1114	      satelliteEventsRef.current = []
1115	      planChildrenRef.current = {}
1116	      planChildNodeRef.current = {}
1117	      nodeCreatedTsRef.current = {}
1118	      setGraphNodes([]); setGraphLinks([]); setEvents([]); setNodeOutputs(new Map())
1119	      setRunResult(null); setDetectedDomain(null); setSelectedNode(null)
1120	      setPendingPlan(null); setNodeCount(0)
1121	      setCurrentPhase("Starting")
1122	      setRunToken(null)
1123	      setPartialFailures(0); setStaleWarning(false); setLastEventAge(null)
1124	      lastEventTsRef.current = 0
1125	      runStartRef.current = null
1126	      const sessionId = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
1127	      const sessionProviderLabel = multiModel
1128	        ? `multi · ${(consortiumSlots[0]?.model || "").split("/").pop() || consortiumSlots[0]?.provider || "multi-model"}`
1129	        : `${provider}${model ? ` · ${(model.split("/").pop() || model).replace(/:.*$/, "")}` : ""}`
1130	      setSessions(prev => [{
1131	        id: sessionId, goal: runGoal, provider, providerLabel: sessionProviderLabel, status: "running", ts: Date.now(), nodeCount: 0,
1132	        currentPhase: "Starting", config: currentConfig(), events: [], graphNodes: [], graphLinks: [], nodeOutputs: {},
1133	      }, ...prev.slice(0, 19)])
1134	      setActiveSessionId(sessionId)
1135	    } else {
1136	      // Clarification continuation: only reset seenEvents so the new run's
1137	      // events are not blocked, but keep graph/timeline visible.
1138	      seenEventsRef.current = new Set()
1139	      setPendingPlan(null)
1140	      setPartialFailures(0); setStaleWarning(false); setLastEventAge(null)
1141	      lastEventTsRef.current = 0
1142	      setCurrentPhase("Continuing")
1143	    }
1144	
1145	    isRunningRef.current = true
1146	    setRunStatus("running"); setCenterTab("timeline")
1147	
1148	    const body: Record<string, unknown> = {
1149	      goal: runGoal, provider, model: model || null, jury_model: juryModel || null,

---

## Subagent Output

1150	      consortium_size: consortiumSize, jury_size: jurySize,
1151	      max_depth: maxDepth, max_parallel_children: maxParallelChildren, max_nodes_total: maxNodesTotal,
1152	      plan_approval_required: planGovernance === "manual", tools_enabled: toolsEnabled,
1153	      plan_recovery: planRecovery,
1154	      max_plan_retries: 2,
1155	      force_recursive: forceRecursive, skip_clarify: skipClarify,
1156	      domain: domainOverride || null, system_prompt: systemPrompt || null,
1157	      api_key: provider !== "mock" && apiKey ? apiKey : null,
1158	    }
1159	    if (multiModel && consortiumSlots.length > 0) body.consortium_agents = consortiumSlots
1160	    if (multiModel && jurySlots.length > 0) body.jury_agents = jurySlots
1161	    // Tier routing overrides: send tier slots when tier routing is enabled
1162	    if (multiModel && tierRouting) {
1163	      if (leafSlots.length > 0) body.leaf_agents = leafSlots
1164	      if (midSlots.length > 0) body.mid_agents = midSlots
1165	      if (rootSlots.length > 0) body.root_agents = rootSlots
1166	    }
1167	
1168	    try {
1169	      const res = await fetch(`${API_BASE}/api/run`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
1170	      if (!res.ok) throw new Error(`Server error ${res.status}`)
1171	      const data = await res.json() as { run_id: string; access_token?: string }
1172	      if (!data.access_token) throw new Error("Server did not return a run access token")
1173	      setRunId(data.run_id)
1174	      setRunToken(data.access_token)
1175	      connectWs(data.run_id, data.access_token)
1176	    } catch (err) {
1177	      setRunStatus("error")
1178	      setEvents([{ event: "run_done", error: String(err) }])
1179	      isRunningRef.current = false
1180	    }
1181	  }
1182	
1183	  const cancelRun = async () => {
1184	    if (!runId) return
1185	    // Keep isRunningRef=true so reconnect can still fire and receive the
1186	    // authoritative run_done { status: "cancelled" } from the server.
1187	    await fetch(`${API_BASE}/api/run/${runId}/cancel`, { method: "POST", headers: authHeaders(runToken) }).catch(() => {})
1188	  }
1189	
1190	  /**
1191	   * Fork the current run from the selected node.
1192	   *
1193	   * Posts to /api/run/{run_id}/fork with the node_id and an optional goal
1194	   * override, then opens the forked run as a brand-new session so the user
1195	   * can watch it live without losing the parent session's graph.
1196	   *
1197	   * The forked run inherits all provider/model config from the parent run.
1198	   * The parent run must still be in server memory (not evicted by the 50-run
1199	   * history cap) — the backend returns 404 if it isn't.
1200	   */
1201	  const forkRun = async (nodeId: string, nodeGoal: string) => {
1202	    // runId is the parent run we're forking from; it must exist
1203	    if (!runId || !runToken) {
1204	      setForkError("No active run to fork from.")
1205	      return
1206	    }
1207	    setForkLoading(true)
1208	    setForkError(null)
1209	
1210	    try {
1211	      const res = await fetch(`${API_BASE}/api/run/${runId}/fork`, {
1212	        method: "POST",
1213	        headers: authHeaders(runToken, true),
1214	        body: JSON.stringify({
1215	          node_id: nodeId,
1216	          // Only send the goal override when the user actually changed it;
1217	          // backend treats null as "use the node's original goal"
1218	          goal: forkGoalOverride.trim() !== nodeGoal.trim() ? forkGoalOverride.trim() || null : null,
1219	          // Agent-count overrides — the user sets these in the fork panel
1220	          consortium_size: forkConsortiumSize,
1221	          jury_size: forkJurySize,
1222	          // Cap the fork's node budget to keep exploratory runs affordable;
1223	          // the user can always start a fresh full run if they want more depth.
1224	          max_nodes_total: 20,
1225	        }),
1226	      })
1227	
1228	      if (!res.ok) {
1229	        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` })) as { detail?: string }
1230	        throw new Error(err.detail || `HTTP ${res.status}`)
1231	      }
1232	
1233	      const data = await res.json() as {
1234	        run_id: string
1235	        access_token: string
1236	        fork_source_run_id: string
1237	        fork_source_node_id: string
1238	      }
1239	
1240	      // Build a session label that makes the fork easy to identify in the list
1241	      const forkLabel = `[fork] ${(forkGoalOverride.trim() || nodeGoal).slice(0, 50)}`
1242	      const forkSessionId = `fork-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
1243	
1244	      // Reset all graph/event state for the forked run — same as startRun's
1245	      // non-continuation path, since we're opening a fresh execution context.
1246	      graphNodesRef.current = []; graphLinksRef.current = []
1247	      seenEventsRef.current = new Set()
1248	      satelliteEventsRef.current = []
1249	      planChildrenRef.current = {}; planChildNodeRef.current = {}
1250	      nodeCreatedTsRef.current = {}
1251	      setGraphNodes([]); setGraphLinks([]); setEvents([]); setNodeOutputs(new Map())
1252	      setRunResult(null); setDetectedDomain(null); setSelectedNode(null)
1253	      setPendingPlan(null); setNodeCount(0)
1254	      setCurrentPhase("Starting")
1255	      setPartialFailures(0); setStaleWarning(false); setLastEventAge(null)
1256	      lastEventTsRef.current = 0; runStartRef.current = null
1257	
1258	      // Register the fork as a new session entry (prepended so it's first in the list)
1259	      setSessions(prev => [{
1260	        id: forkSessionId,
1261	        goal: forkLabel,
1262	        provider,
1263	        providerLabel: provider,
1264	        status: "running",
1265	        ts: Date.now(),
1266	        nodeCount: 0,
1267	        currentPhase: "Starting",
1268	        config: currentConfig(),
1269	        events: [], graphNodes: [], graphLinks: [], nodeOutputs: {},
1270	        // Store lineage so the session card can show a "forked from" badge
1271	        forkSourceRunId: data.fork_source_run_id,
1272	        forkSourceNodeId: data.fork_source_node_id,
1273	      }, ...prev.slice(0, 19)])
1274	
1275	      setActiveSessionId(forkSessionId)
1276	      setGoal(forkGoalOverride.trim() || nodeGoal)
1277	      setRunId(data.run_id)
1278	      setRunToken(data.access_token)
1279	      isRunningRef.current = true
1280	      setRunStatus("running")
1281	      setCenterTab("timeline")
1282	
1283	      // Open the WebSocket stream for the forked run — same connectWs the
1284	      // normal startRun uses, so all event processing is identical.
1285	      connectWs(data.run_id, data.access_token)
1286	
1287	      // Close the fork panel
1288	      setForkGoalOverride("")
1289	      setForkError(null)
1290	
1291	    } catch (err) {
1292	      setForkError(String(err))
1293	    } finally {
1294	      setForkLoading(false)
1295	    }
1296	  }
1297	
1298	  const updateConsortiumSlot = (index: number, patch: Partial<AgentSlot>) => {
1299	    setAppliedStrategy(null) // manual edit clears the preset
1300	    setConsortiumSlots(prev => normalizeSlots(prev, consortiumSize, provider, model).map((slot, i) => i === index ? { ...slot, ...patch } : slot))
1301	  }
1302	
1303	  const updateJurySlot = (index: number, patch: Partial<AgentSlot>) => {
1304	    setAppliedStrategy(null)
1305	    setJurySlots(prev => normalizeSlots(prev, jurySize, provider, juryModel || model).map((slot, i) => i === index ? { ...slot, ...patch } : slot))
1306	  }
1307	
1308	  const updateLeafSlot = (index: number, patch: Partial<AgentSlot>) => {
1309	    setAppliedStrategy(null)
1310	    setLeafSlots(prev => normalizeSlots(prev, prev.length || 2, provider, model).map((slot, i) => i === index ? { ...slot, ...patch } : slot))
1311	  }
1312	
1313	  const updateMidSlot = (index: number, patch: Partial<AgentSlot>) => {
1314	    setAppliedStrategy(null)
1315	    setMidSlots(prev => normalizeSlots(prev, prev.length || 2, provider, model).map((slot, i) => i === index ? { ...slot, ...patch } : slot))
1316	  }
1317	
1318	  const updateRootSlot = (index: number, patch: Partial<AgentSlot>) => {
1319	    setAppliedStrategy(null)
1320	    setRootSlots(prev => normalizeSlots(prev, prev.length || 2, provider, model).map((slot, i) => i === index ? { ...slot, ...patch } : slot))
1321	  }
1322	
1323	  const applyStrategy = (strategyId: string) => {
1324	    // Click the active strategy again → deselect it (keep current settings, just clear the badge)
1325	    if (appliedStrategy === strategyId) {
1326	      setAppliedStrategy(null)
1327	      return
1328	    }
1329	    const s = MODEL_STRATEGIES.find(x => x.id === strategyId)
1330	    if (!s) return
1331	    setAppliedStrategy(s.id)
1332	    setMultiModel(s.multiModel)
1333	    setConsortiumSize(s.consortiumSize)
1334	    setJurySize(s.jurySize)
1335	    // Always set slots explicitly — clear stale state from any previously applied strategy
1336	    setConsortiumSlots(s.consortiumSlots)
1337	    setJurySlots(s.jurySlots)
1338	    // Tier routing — always reset all tier slots so switching strategies is clean
1339	    setTierRouting(s.tierRouting || false)
1340	    setLeafSlots(s.leafSlots || [])
1341	    setMidSlots(s.midSlots || [])
1342	    setRootSlots(s.rootSlots || [])
1343	  }
1344	
1345	  const replayServerRun = async (summary: ServerRunSummary) => {
1346	    try {
1347	      const [eventsRes, statusRes] = await Promise.all([
1348	        fetch(`${API_BASE}/api/run/${summary.run_id}/events`),
1349	        fetch(`${API_BASE}/api/run/${summary.run_id}`),

---

## Subagent Output

1350	      ])
1351	      if (!eventsRes.ok) return
1352	      const eventsData = await eventsRes.json() as { events?: RafEvent[]; status?: string }
1353	      const statusData = statusRes.ok ? await statusRes.json() as { status?: string; result?: { output?: string } | null; error?: string | null } : null
1354	      const replayEvents = eventsData.events || []
1355	
1356	      graphNodesRef.current = []; graphLinksRef.current = []
1357	      seenEventsRef.current = new Set()
1358	      satelliteEventsRef.current = []
1359	      planChildrenRef.current = {}
1360	      planChildNodeRef.current = {}
1361	      nodeCreatedTsRef.current = {}
1362	      setGraphNodes([]); setGraphLinks([]); setEvents([]); setNodeOutputs(new Map())
1363	      setRunResult(statusData?.result?.output || null)
1364	      setDetectedDomain(null); setSelectedNode(null); setPendingPlan(null)
1365	      setNodeCount(0); setCurrentPhase("Replayed")
1366	      setRunId(summary.run_id)
1367	      setRunStatus((statusData?.status as typeof runStatus) || (eventsData.status as typeof runStatus) || "idle")
1368	      setGoal(summary.goal)
1369	      setProvider(summary.provider)
1370	      runStartRef.current = replayEvents.find(ev => ev.timestamp)?.timestamp
1371	        ? replayEvents.find(ev => ev.timestamp)!.timestamp! * 1000
1372	        : null
1373	
1374	      replayEvents.forEach(ev => processEvent(ev))
1375	      setCenterTab("timeline")
1376	      setWorkPanelOpen(true)
1377	    } catch {
1378	      setRunStatus("error")
1379	    }
1380	  }
1381	
1382	  // Fetch freshest server state before exporting; falls back to local state on error
1383	  const fetchFreshExportData = async (): Promise<{ freshEvents: RafEvent[]; freshResult: string | null; freshStatus: string }> => {
1384	    if (!runId) return { freshEvents: events, freshResult: runResult, freshStatus: runStatus }
1385	    try {
1386	      const [evRes, stRes] = await Promise.all([
1387	        fetch(`${API_BASE}/api/run/${runId}/events`, { headers: authHeaders(runToken) }),
1388	        fetch(`${API_BASE}/api/run/${runId}`, { headers: authHeaders(runToken) }),
1389	      ])
1390	      const freshEvents: RafEvent[] = evRes.ok ? ((await evRes.json()) as { events?: RafEvent[] }).events || events : events
1391	      const stData = stRes.ok ? await stRes.json() as { status?: string; result?: { output?: string } | null } : null
1392	      const freshResult = stData?.result?.output ?? runResult
1393	      const freshStatus = stData?.status ?? runStatus
1394	      return { freshEvents, freshResult, freshStatus }
1395	    } catch {
1396	      return { freshEvents: events, freshResult: runResult, freshStatus: runStatus }
1397	    }
1398	  }
1399	
1400	  // Compute export completeness metadata for both JSON and PDF
1401	  const buildExportMeta = (evList: RafEvent[], status: string) => {
1402	    const hasRunDone = evList.some(ev => ev.event === "run_done")
1403	    const hasRootNodeDone = evList.some(ev => ev.event === "node_done" && (ev.node_id === "root" || ev.depth === 0))
1404	    const isMidRun = status === "running"
1405	    let exportCompleteness: string
1406	    if (isMidRun) exportCompleteness = "mid_run"
1407	    else if (!hasRunDone && hasRootNodeDone) exportCompleteness = "near_complete"
1408	    else if (hasRunDone) exportCompleteness = "complete"
1409	    else exportCompleteness = "partial"
1410	    return { hasRunDone, hasRootNodeDone, exportCompleteness, isMidRun }
1411	  }
1412	
1413	  const exportJSON = async () => {
1414	    const { freshEvents, freshResult, freshStatus } = await fetchFreshExportData()
1415	    const meta = buildExportMeta(freshEvents, freshStatus)
1416	    const data = {
1417	      run_id: runId,
1418	      goal,
1419	      provider,
1420	      model: model || null,
1421	      jury_model: juryModel || null,
1422	      status: freshStatus,
1423	      phase: currentPhase,
1424	      detected_domain: detectedDomain,
1425	      partial_failures: partialFailures,
1426	      exportCompleteness: meta.exportCompleteness,
1427	      hasRunDone: meta.hasRunDone,
1428	      hasRootNodeDone: meta.hasRootNodeDone,
1429	      note: meta.isMidRun ? "Exported mid-run. Final output may not be available yet." : undefined,
1430	      config: currentConfig(),
1431	      physics,
1432	      result: freshResult,
1433	      events: freshEvents,
1434	      graphNodes: cleanGraphNodes(graphNodes),
1435	      graphLinks: cleanGraphLinks(graphLinks),
1436	      nodeOutputs: outputMapToRecord(nodeOutputs),
1437	      selectedNodeId: selectedNode?.id || null,
1438	      exportedAt: new Date().toISOString(),
1439	    }
1440	    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
1441	    const url = URL.createObjectURL(blob)
1442	    const a = document.createElement("a"); a.href = url; a.download = `raf-trace-${runId || "export"}.json`
1443	    a.click(); URL.revokeObjectURL(url)
1444	  }
1445	
1446	  const exportPDF = async () => {
1447	    const [{ default: jsPDF }, { default: html2canvas }, { freshEvents, freshResult, freshStatus }] = await Promise.all([
1448	      import("jspdf"), import("html2canvas"), fetchFreshExportData(),
1449	    ])
1450	    const meta = buildExportMeta(freshEvents, freshStatus)
1451	    const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" })
1452	    const W = doc.internal.pageSize.getWidth()
1453	    const H = doc.internal.pageSize.getHeight()
1454	
1455	    // ── helpers ──────────────────────────────────────────────────────────────
1456	    const newPage = () => {
1457	      doc.addPage()
1458	      doc.setFillColor(10, 14, 23); doc.rect(0, 0, W, H, "F")
1459	    }
1460	    const sectionHeader = (title: string, yPos: number) => {
1461	      doc.setTextColor(96, 165, 250); doc.setFontSize(11)
1462	      doc.text(title, 10, yPos)
1463	      doc.setTextColor(148, 163, 184); doc.setFontSize(7.5)
1464	      return yPos + 7
1465	    }
1466	    const maybeNewPage = (y: number, needed = 10): number => {
1467	      if (y + needed > H - 10) { newPage(); return 15 }
1468	      return y
1469	    }
1470	    const row = (doc: InstanceType<typeof jsPDF>, label: string, value: string, y: number, indent = 10): number => {
1471	      doc.setTextColor(100, 116, 139); doc.text(label, indent, y)
1472	      doc.setTextColor(148, 163, 184); doc.text(value, indent + 42, y)
1473	      return y + 4.5
1474	    }
1475	
1476	    // ── Cover page ──────────────────────────────────────────────────────────
1477	    doc.setFillColor(10, 14, 23); doc.rect(0, 0, W, H, "F")
1478	    doc.setTextColor(96, 165, 250); doc.setFontSize(22)
1479	    doc.text("RAF Execution Report", 20, 28)
1480	
1481	    // Status badge — coloured based on completeness
1482	    const statusColors: Record<string, [number, number, number]> = {
1483	      complete: [34, 197, 94], mid_run: [59, 130, 246], near_complete: [234, 179, 8], partial: [239, 68, 68],
1484	    }
1485	    const [sr, sg, sb] = statusColors[meta.exportCompleteness] || [148, 163, 184]
1486	    doc.setFontSize(9); doc.setTextColor(sr, sg, sb)
1487	    const statusLabel = meta.isMidRun ? "⚡ EXPORTED MID-RUN" : meta.exportCompleteness === "near_complete" ? "⚠ NEAR COMPLETE (no run_done yet)" : meta.exportCompleteness === "complete" ? "✓ COMPLETE" : "~ PARTIAL"
1488	    doc.text(statusLabel, 20, 38)
1489	
1490	    doc.setTextColor(148, 163, 184); doc.setFontSize(9)
1491	    let cy = 50
1492	    cy = row(doc, "Run ID", runId || "—", cy)
1493	    cy = row(doc, "Goal", goal.slice(0, 100) + (goal.length > 100 ? "…" : ""), cy)
1494	    cy = row(doc, "Provider", provider, cy)
1495	    cy = row(doc, "Domain", detectedDomain || "auto", cy)
1496	    cy = row(doc, "Status", runStatus, cy)
1497	    cy = row(doc, "Phase", currentPhase, cy)
1498	    cy = row(doc, "Nodes", `${graphNodes.filter(n => n.type === "raf-node").length} RAF + ${graphNodes.filter(n => n.type !== "raf-node").length} satellite`, cy)
1499	    cy = row(doc, "Events", String(events.length), cy)
1500	    cy = row(doc, "Partial failures", String(partialFailures), cy)
1501	    cy = row(doc, "Exported at", new Date().toLocaleString(), cy)
1502	
1503	    if (meta.isMidRun) {
1504	      cy += 4
1505	      doc.setTextColor(59, 130, 246); doc.setFontSize(8)
1506	      doc.text("Note: exported while run was active. Final output may not be available.", 20, cy)
1507	      cy += 5; doc.text("Re-export after run_done for a complete report.", 20, cy)
1508	    }
1509	    if (!meta.hasRunDone && meta.hasRootNodeDone) {
1510	      cy += 4
1511	      doc.setTextColor(234, 179, 8); doc.setFontSize(8)
1512	      doc.text("Root node completed but run_done has not been received yet.", 20, cy)
1513	    }
1514	
1515	    // Run health summary box
1516	    cy += 8
1517	    doc.setDrawColor(30, 41, 59); doc.setFillColor(15, 23, 42); doc.roundedRect(18, cy, 100, 38, 2, 2, "FD")
1518	    doc.setTextColor(96, 165, 250); doc.setFontSize(8.5); doc.text("Run Health", 22, cy + 7)
1519	    doc.setFontSize(7.5); doc.setTextColor(148, 163, 184)
1520	    const hasRunDoneEv = meta.hasRunDone; const hasRootDoneEv = meta.hasRootNodeDone
1521	    doc.text(`  run_done received:   ${hasRunDoneEv ? "yes" : "no"}`, 20, cy + 13)
1522	    doc.text(`  root node_done:      ${hasRootDoneEv ? "yes" : "no"}`, 20, cy + 18)
1523	    doc.text(`  partial child fails: ${partialFailures}`, 20, cy + 23)
1524	    doc.text(`  export completeness: ${meta.exportCompleteness}`, 20, cy + 28)
1525	
1526	    // Plan recovery summary if any
1527	    const recoveryEvents = freshEvents.filter(ev => ["plan_validation_failed","plan_retry_start","plan_retry_done","plan_abandoned","plan_replaced"].includes(ev.event || ""))
1528	    if (recoveryEvents.length > 0) {
1529	      doc.setDrawColor(30, 41, 59); doc.setFillColor(40, 20, 10); doc.roundedRect(130, cy, 120, 38, 2, 2, "FD")
1530	      doc.setTextColor(251, 146, 60); doc.setFontSize(8.5); doc.text("Plan Recovery", 134, cy + 7)
1531	      doc.setFontSize(7.5); doc.setTextColor(148, 163, 184)
1532	      const retries = recoveryEvents.filter(ev => ev.event === "plan_retry_start").length
1533	      const abandoned = recoveryEvents.some(ev => ev.event === "plan_abandoned")
1534	      doc.text(`  retries: ${retries}`, 132, cy + 13)
1535	      doc.text(`  abandoned: ${abandoned ? "yes" : "no"}`, 132, cy + 18)
1536	      doc.text(`  events: ${recoveryEvents.length}`, 132, cy + 23)
1537	    }
1538	
1539	    // ── Graph page ──────────────────────────────────────────────────────────
1540	    const svgEl = graphRef.current?.querySelector("svg")
1541	    if (svgEl && graphNodesRef.current.length > 0) {
1542	      const ns = graphNodesRef.current.filter(n => n.x !== undefined && n.y !== undefined)
1543	      if (ns.length > 0) {
1544	        const pad = 60
1545	        const xs = ns.map(n => n.x!); const ys = ns.map(n => n.y!)
1546	        const x0 = Math.min(...xs) - pad; const y0 = Math.min(...ys) - pad
1547	        const bw = Math.max(...xs) - x0 + pad; const bh = Math.max(...ys) - y0 + pad
1548	        const savedVB = svgEl.getAttribute("viewBox") || ""
1549	        const zoomGroup = svgEl.querySelector("g") as SVGGElement | null

---

## Claude

Let me jump to the toolbar and end-of-JSX area.

---

## Subagent Output

2600	                    )}
2601	                    {ev.event === "node_done" && ev.confidence && (
2602	                      <p className="text-[10px] text-muted-foreground pl-3.5 mt-0.5">{ev.mode} | {(ev.confidence * 100).toFixed(0)}%</p>
2603	                    )}
2604	                    {ev.event === "model_call_failed" && (
2605	                      <p className="text-[10px] pl-3.5 mt-0.5 flex items-center gap-1.5">
2606	                        {ev.cause ? (
2607	                          <>
2608	                            <span className="rounded px-1 py-0.5 font-mono text-[9px] font-semibold"
2609	                              style={{ background: ev.cause === "api_error" ? "#7f1d1d" : ev.cause === "parse_error" ? "#78350f" : "#1e1b4b", color: "#fca5a5" }}>
2610	                              {CAUSE_LABELS[ev.cause]?.label ?? ev.cause}
2611	                            </span>
2612	                            <span className="text-muted-foreground">{CAUSE_LABELS[ev.cause]?.detail}</span>
2613	                          </>
2614	                        ) : (
2615	                          <span className="text-muted-foreground">{ev.error || "Unknown failure"}</span>
2616	                        )}
2617	                      </p>
2618	                    )}
2619	                    {ev.event === "model_call_timeout" && ev.timeout_ms !== undefined && (
2620	                      <p className="text-[10px] text-muted-foreground pl-3.5 mt-0.5">
2621	                        <span className="rounded px-1 py-0.5 font-mono text-[9px] font-semibold" style={{ background: "#451a03", color: "#fbbf24" }}>Timeout</span>
2622	                        {" "}waited {(ev.timeout_ms / 1000).toFixed(1)}s — model was still running
2623	                      </p>
2624	                    )}
2625	                  </div>
2626	                ))}
2627	              </div>
2628	            </ScrollArea>
2629	          </TabsContent>
2630	
2631	          {/* Votes tab */}
2632	          <TabsContent value="votes" className="flex w-full flex-col flex-1 min-h-0 mt-0 overflow-hidden data-[state=inactive]:hidden">
2633	            <div className="flex items-center justify-between border-b border-border px-3 py-2 text-[10px] text-muted-foreground shrink-0">
2634	              <span className="uppercase tracking-widest">Jury votes</span>
2635	              <span className="font-mono tabular-nums">{voteEvents.length} events</span>
2636	            </div>
2637	            <ScrollArea className="flex-1 min-h-0">
2638	              <div className="flex min-h-full w-full max-w-full flex-col gap-2 overflow-hidden p-3">
2639	                {voteEvents.length === 0 && (
2640	                  <p className="text-xs text-center text-muted-foreground py-8">No votes yet.</p>
2641	                )}
2642	                {voteEvents.map((ev, i) => {
2643	                  const options = (ev.options as any[]) || []
2644	                  const votes = (ev.votes as any[]) || []
2645	                  return (
2646	                    <Card key={i} className="w-full min-w-0 max-w-full overflow-hidden">
2647	                      <CardContent className="min-w-0 max-w-full overflow-hidden p-3 space-y-2">
2648	                        <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-start gap-2">
2649	                          <div className="flex min-w-0 flex-wrap items-center gap-2">
2650	                            <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wider text-purple-400">{ev.task}</span>
2651	                            {ev.node_id && <span className="min-w-0 break-all text-[10px] font-mono text-muted-foreground">{ev.node_id}</span>}
2652	                          </div>
2653	                          <span className="shrink-0 text-xs font-mono">{ev.confidence ? (ev.confidence * 100).toFixed(0) + "%" : "—"}</span>
2654	                        </div>
2655	
2656	                        {options.length > 0 && (
2657	                          <div className="min-w-0 max-w-full space-y-1.5 overflow-hidden">
2658	                            <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Proposals</p>
2659	                            {options.map((opt: any, oi: number) => {
2660	                              const payload = opt.payload || opt
2661	                              const isWinner = ev.winner_id === opt.option_id
2662	                              const fullText = payload.output || payload.mode || payload.plan || JSON.stringify(payload, null, 2)
2663	                              const preview = fullText.length > 300 ? fullText.slice(0, 300) + "…" : fullText
2664	                              return (
2665	                                <div key={oi} className={`group min-w-0 max-w-full overflow-hidden rounded-md p-2 text-xs border ${isWinner ? "border-primary/50 bg-primary/5" : "border-border"}`}>
2666	                                  <div className="flex min-w-0 max-w-full flex-wrap items-center gap-1.5 mb-1">
2667	                                    <span className="min-w-0 font-mono text-[10px] text-muted-foreground">{optionLabel(opt.option_id)}</span>
2668	                                    {isWinner && <Badge className="text-[9px] h-4 px-1 bg-primary/20 text-primary border-primary/30">winner</Badge>}
2669	                                    <button
2670	                                      className="ml-auto opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground hover:text-foreground transition-opacity"
2671	                                      onClick={() => setExpandModal({ title: `${optionLabel(opt.option_id)} · ${ev.task ?? "proposal"}`, content: fullText })}
2672	                                    >⤢</button>
2673	                                  </div>
2674	                                  <p className="min-w-0 max-w-full whitespace-pre-wrap break-all text-muted-foreground">{preview}</p>
2675	                                </div>
2676	                              )
2677	                            })}
2678	                          </div>
2679	                        )}
2680	
2681	                        {votes.length > 0 && (
2682	                          <div className="min-w-0 max-w-full space-y-1 overflow-hidden pt-1 border-t border-border">
2683	                            <p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-1">Votes</p>
2684	                            {votes.map((v: any, vi: number) => {
2685	                              const vote = v.vote || v
2686	                              const modelLabel = agentModelMap[`${ev.node_id}:${ev.task}:jury:${v.agent_id}`] || `agent-${v.agent_id}`
2687	                              return (
2688	                                <div key={vi} className="grid min-w-0 max-w-full grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)_auto] items-center gap-2 text-xs">
2689	                                  <span className="min-w-0 truncate font-mono text-[10px] text-purple-300" title={modelLabel}>{modelLabel}</span>
2690	                                  <span className="text-muted-foreground shrink-0">→</span>
2691	                                  <span className="min-w-0 font-mono text-[10px]">{optionLabel(vote.winner_id)}</span>
2692	                                  {vote.confidence && <span className="shrink-0 text-muted-foreground text-[10px]">{(vote.confidence * 100).toFixed(0)}%</span>}
2693	                                </div>
2694	                              )
2695	                            })}
2696	                          </div>
2697	                        )}
2698	                      </CardContent>
2699	                    </Card>
2700	                  )
2701	                })}
2702	              </div>
2703	            </ScrollArea>
2704	          </TabsContent>
2705	
2706	          <TabsContent value="spec" className="flex w-full flex-col flex-1 min-h-0 mt-0 overflow-hidden data-[state=inactive]:hidden">
2707	            <ScrollArea className="flex-1 min-h-0">
2708	              <div className="p-3 space-y-3">
2709	                {!latestSpec && specEvents.length === 0 && (
2710	                  <p className="text-xs text-center text-muted-foreground py-8">No spec events yet.</p>
2711	                )}
2712	                {latestSpec && (
2713	                  <Card className="min-w-0 overflow-hidden">
2714	                    <CardContent className="p-3 space-y-3">
2715	                      <div className="flex items-center gap-2">
2716	                        <Badge variant="outline" className="text-[10px]">{latestSpec.domain || "general"}</Badge>
2717	                        {(latestSpec as any).task_class && <Badge variant="outline" className="text-[10px]">{(latestSpec as any).task_class}</Badge>}
2718	                      </div>
2719	                      <SpecList label="Required" items={latestSpec.required || []} />
2720	                      <SpecList label="Forbidden" items={latestSpec.forbidden || []} />
2721	                      <SpecList label="Success criteria" items={latestSpec.success_criteria || []} />
2722	                    </CardContent>
2723	                  </Card>
2724	                )}
2725	                {specEvents.filter(ev => ev.event !== "spec_extracted").map((ev, i) => (
2726	                  <EventCard key={`${ev.event}-${i}`} ev={ev} />
2727	                ))}
2728	              </div>
2729	            </ScrollArea>
2730	          </TabsContent>
2731	
2732	          <TabsContent value="tools" className="flex w-full flex-col flex-1 min-h-0 mt-0 overflow-hidden data-[state=inactive]:hidden">
2733	            <ScrollArea className="flex-1 min-h-0">
2734	              <div className="p-3 space-y-2">
2735	                {toolEvents.length === 0 && (
2736	                  <p className="text-xs text-center text-muted-foreground py-8">No tool calls yet.</p>
2737	                )}
2738	                {toolEvents.map((ev, i) => <EventCard key={`${ev.event}-${i}`} ev={ev} />)}
2739	              </div>
2740	            </ScrollArea>
2741	          </TabsContent>
2742	
2743	          <TabsContent value="checks" className="flex w-full flex-col flex-1 min-h-0 mt-0 overflow-hidden data-[state=inactive]:hidden">
2744	            <ScrollArea className="flex-1 min-h-0">
2745	              <div className="p-3 space-y-2">
2746	                {checkEvents.length === 0 && (
2747	                  <p className="text-xs text-center text-muted-foreground py-8">No check events yet.</p>
2748	                )}
2749	                {checkEvents.map((ev, i) => <EventCard key={`${ev.event}-${i}`} ev={ev} />)}

---

## Subagent Output

2750	              </div>
2751	            </ScrollArea>
2752	          </TabsContent>
2753	        </Tabs>
2754	      </div>
2755	
2756	      {/* ══ RIGHT: D3 GRAPH ═══════════════════════════════════════════════════════ */}
2757	      <div className="flex flex-col flex-1 min-w-0">
2758	
2759	        {/* Graph toolbar */}
2760	        <div className="flex items-center justify-between px-4 py-2 border-b border-border shrink-0 bg-card/50">
2761	          <div className="flex items-center gap-2">
2762	            <Network className="h-4 w-4 text-muted-foreground" />
2763	            <span className="font-medium text-sm">Execution Graph</span>
2764	            <Badge variant="outline" className="text-xs tabular-nums">{graphNodes.length} nodes</Badge>
2765	            <Badge variant="outline" className="text-xs tabular-nums">{events.length} events</Badge>
2766	            {currentPhase !== "Idle" && <Badge variant="outline" className="text-xs">{currentPhase}</Badge>}
2767	            {running && <Badge className="text-xs tabular-nums animate-pulse bg-blue-500/20 text-blue-400 border-blue-500/30">{nodeCount} / {maxNodesTotal}</Badge>}
2768	          </div>
2769	          <div className="flex items-center gap-3">
2770	            {!workPanelOpen && (
2771	              <Button variant="outline" size="sm" className="h-7 gap-1 text-[10px]" onClick={() => setWorkPanelOpen(true)}>
2772	                <FileText className="h-3 w-3" /> Workspace
2773	              </Button>
2774	            )}
2775	            {/* Graph mode toggle */}
2776	            <div className="flex items-center gap-1 border border-border rounded-md overflow-hidden">
2777	              {(["simplified", "full"] as const).map(m => (
2778	                <button key={m} onClick={() => setGraphMode(m)}
2779	                  className={`px-2 py-0.5 text-[10px] font-medium transition-colors ${graphMode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>
2780	                  {m}
2781	                </button>
2782	              ))}
2783	            </div>
2784	            <div className="hidden lg:flex items-center gap-3">
2785	              {([["#00e5ff","Active"],["#69ff47","Base"],["#f59e0b","Recursive"],["#e040fb","Jury"],["#ffeb3b","Consortium"]] as [string,string][]).map(([c,l]) => (
2786	                <div key={l} className="flex items-center gap-1">
2787	                  <div className="h-2 w-2 rounded-full" style={{ background: c }} />
2788	                  <span className="text-[10px] text-muted-foreground">{l}</span>
2789	                </div>
2790	              ))}
2791	            </div>
2792	            <Separator orientation="vertical" className="h-5 hidden lg:block" />
2793	            <div className="flex items-center gap-1 border border-border rounded-md overflow-hidden">
2794	              <button
2795	                className="px-2 py-1 text-muted-foreground hover:bg-muted hover:text-foreground"
2796	                onClick={() => setZoomCommand({ action: "out", nonce: Date.now() })}
2797	                title="Zoom out"
2798	              >
2799	                <ZoomOut className="h-3.5 w-3.5" />
2800	              </button>
2801	              <button
2802	                className="px-2 py-1 text-muted-foreground hover:bg-muted hover:text-foreground"
2803	                onClick={() => setZoomCommand({ action: "reset", nonce: Date.now() })}
2804	                title="Reset zoom"
2805	              >
2806	                <RotateCcw className="h-3.5 w-3.5" />
2807	              </button>
2808	              <button
2809	                className="px-2 py-1 text-muted-foreground hover:bg-muted hover:text-foreground"
2810	                onClick={() => setZoomCommand({ action: "in", nonce: Date.now() })}
2811	                title="Zoom in"
2812	              >
2813	                <ZoomIn className="h-3.5 w-3.5" />
2814	              </button>
2815	            </div>
2816	            {(events.length > 0 || graphNodes.length > 0 || runResult) && (
2817	              <>
2818	                <Button variant="ghost" size="sm" className="h-7 gap-1 text-[10px]" onClick={exportJSON}>
2819	                  <Download className="h-3 w-3" /> JSON
2820	                </Button>
2821	                <Button variant="ghost" size="sm" className="h-7 gap-1 text-[10px]" onClick={exportPDF}>
2822	                  <Download className="h-3 w-3" /> PDF
2823	                </Button>
2824	              </>
2825	            )}
2826	            {selectedNode && (
2827	              <Button variant="ghost" size="sm" className="text-[10px] h-7 px-2" onClick={() => setSelectedNode(null)}>
2828	                Clear
2829	              </Button>
2830	            )}
2831	          </div>
2832	        </div>
2833	
2834	        {/* D3 graph */}
2835	        <div ref={graphRef} className="flex-1 relative select-none">
2836	          <ExecutionGraph
2837	            nodes={graphNodes} links={graphLinks}
2838	            mode={graphMode} physics={physics}
2839	            zoomCommand={zoomCommand}
2840	            width={gSize.w} height={gSize.h}
2841	            onNodeClick={n => {
2842	              setSelectedNode(n)
2843	              setCenterTab("output")
2844	              if (n.type === "raf-node" && !n.active && n.success) {
2845	                // Pre-fill the fork goal and reset the agent-count controls to
2846	                // their reduced defaults each time a new node is selected, so
2847	                // the panel always starts from a known safe cost baseline.
2848	                setForkGoalOverride(n.goal || "")
2849	                setForkConsortiumSize(2)
2850	                setForkJurySize(1)
2851	              } else {
2852	                setForkGoalOverride("")
2853	              }
2854	              setForkError(null)
2855	            }}
2856	            onBackgroundClick={() => setSelectedNode(null)}
2857	          />
2858	          {graphNodes.length === 0 && !running && (
2859	            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
2860	              <div className="text-center">
2861	                <Network className="h-16 w-16 text-muted-foreground/10 mx-auto mb-4" />
2862	                <p className="text-muted-foreground/40 text-sm">Graph will appear here as RAF runs</p>
2863	              </div>
2864	            </div>
2865	          )}
2866	
2867	          {/* Node Inspector — top-right frosted overlay */}
2868	          <AnimatePresence>
2869	            {selectedNode && (
2870	              <motion.div
2871	                initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}
2872	                className="absolute top-4 right-4 w-[360px] bg-card/95 backdrop-blur shadow-xl border border-border rounded-lg overflow-hidden flex flex-col z-10"
2873	              >
2874	                <div className="px-3 py-2 border-b border-border flex justify-between items-center shrink-0">
2875	                  <div className="flex items-center gap-2">
2876	                    <span className="h-2 w-2 rounded-full" style={{
2877	                      background: ({
2878	                        'raf-node': '#00e5ff', jury: '#e040fb', consortium: '#ffeb3b', agent: '#69ff47',
2879	                        'consortium-group': '#ffd600', 'jury-group': '#ce93d8',
2880	                        'agent-proposal': '#69ff47', 'juror-vote': '#f3e5f5',
2881	                        'merge-group': '#ff9100', 'referee-check': '#64b5f6',
2882	                      } as Record<string,string>)[selectedNode.type] || '#888'
2883	                    }} />
2884	                    <span className="font-medium text-xs truncate">{selectedNode.label}</span>
2885	                    {selectedNode.task && <Badge variant="outline" className="text-[9px] h-4 px-1">{selectedNode.task}</Badge>}
2886	                  </div>
2887	                  <button onClick={() => setSelectedNode(null)} className="text-muted-foreground hover:text-foreground text-sm leading-none px-1">✕</button>
2888	                </div>
2889	                <div className="p-3 text-xs overflow-y-auto max-h-[70vh] flex flex-col gap-3">
2890	
2891	                  {/* ── RAF node: full lifecycle detail ─────────────────── */}
2892	                  {selectedNode.type === "raf-node" && (
2893	                    <>
2894	                      <div className="grid grid-cols-2 gap-2">
2895	                        <div><span className="text-[10px] uppercase text-muted-foreground">Depth</span>
2896	                          <p className="mt-0.5">{selectedNode.depth ?? "—"}</p></div>
2897	                        {selectedNode.caseType && (
2898	                          <div><span className="text-[10px] uppercase text-muted-foreground">Case</span>
2899	                            <p className="mt-0.5 capitalize">{selectedNode.caseType}</p></div>
2900	                        )}
2901	                        {selectedNode.confidence !== undefined && (
2902	                          <div><span className="text-[10px] uppercase text-muted-foreground">Confidence</span>
2903	                            <p className="font-mono mt-0.5">{(selectedNode.confidence * 100).toFixed(0)}%</p></div>
2904	                        )}
2905	                        {selectedNode.phase && (
2906	                          <div><span className="text-[10px] uppercase text-muted-foreground">Phase</span>
2907	                            <p className="mt-0.5">{selectedNode.phase}</p></div>
2908	                        )}
2909	                        {selectedDurationMs !== undefined && (
2910	                          <div><span className="text-[10px] uppercase text-muted-foreground">Duration</span>
2911	                            <p className="font-mono mt-0.5">{selectedDurationMs}ms</p></div>
2912	                        )}
2913	                        {selectedNode.success !== undefined && (
2914	                          <div><span className="text-[10px] uppercase text-muted-foreground">Status</span>
2915	                            <p className={`mt-0.5 ${selectedNode.success ? 'text-green-400' : 'text-red-400'}`}>
2916	                              {selectedNode.success ? 'Success' : 'Failed'}</p></div>
2917	                        )}
2918	                        <div><span className="text-[10px] uppercase text-muted-foreground">Events</span>
2919	                          <p className="font-mono mt-0.5">{selectedNodeEvents.length}</p></div>
2920	                        <div><span className="text-[10px] uppercase text-muted-foreground">Children</span>
2921	                          <p className="font-mono mt-0.5">{selectedNodeChildren.length}</p></div>
2922	                      </div>
2923	
2924	                      {/* ── Lifecycle checklist ──────────────────────────── */}
2925	                      {(() => {
2926	                        const evSet = new Set(selectedNodeEvents.map(e => e.event))
2927	                        const childCount = selectedNodeChildren.filter(n => n.type === "raf-node").length
2928	                        const childDone  = selectedNodeEvents.filter(e => e.event === "node_done").length - (evSet.has("node_done") ? 1 : 0)
2929	                        const planChildCount = (planChildrenRef.current[selectedNode.id] || []).length
2930	
2931	                        type CheckState = "done" | "partial" | "waiting" | "pending"
2932	                        const step = (label: string, state: CheckState, detail?: string) => (
2933	                          <div key={label} className="flex items-center gap-2">
2934	                            <span className={`shrink-0 text-[11px] ${state === "done" ? "text-green-400" : state === "partial" ? "text-yellow-400" : state === "waiting" ? "text-blue-400 animate-pulse" : "text-muted-foreground/30"}`}>
2935	                              {state === "done" ? "✓" : state === "partial" ? "◑" : state === "waiting" ? "⏳" : "○"}
2936	                            </span>
2937	                            <span className={`text-[10px] ${state === "done" ? "text-foreground" : state === "waiting" ? "text-blue-300" : "text-muted-foreground"}`}>{label}</span>
2938	                            {detail && <span className="ml-auto text-[10px] font-mono text-muted-foreground/60">{detail}</span>}
2939	                          </div>
2940	                        )
2941	
2942	                        const isActive = selectedNode.active
2943	                        const isDone   = evSet.has("node_done")
2944	                        const hasMode  = evSet.has("mode_decided")
2945	                        const hasPlan  = evSet.has("plan_selected") || evSet.has("plan_ready")
2946	                        const hasChildren = childCount > 0
2947	                        const hasMerge = evSet.has("merge_done")
2948	                        const hasSpec  = evSet.has("spec_validation_final") || evSet.has("spec_repair_start")
2949	                        const hasAnalysis = evSet.has("analysis_done")

---

## Subagent Output

2950	                        const hasExec  = evSet.has("base_execute_done")
2951	                        const hasFail  = evSet.has("plan_validation_failed")
2952	
2953	                        const childState: CheckState = !hasChildren ? "pending" : (isDone || hasMerge) ? "done" : planChildCount > 0 && childDone < planChildCount ? "partial" : "done"
2954	
2955	                        return (
2956	                          <div className="rounded-md border border-border/50 bg-muted/20 p-2 space-y-1">
2957	                            <p className="text-[10px] uppercase text-muted-foreground font-medium mb-1.5">Lifecycle</p>
2958	                            {step("Node created",    "done")}
2959	                            {step("Mode decided",    hasMode ? "done" : isActive ? "waiting" : "pending")}
2960	                            {selectedNode.caseType === "recursive" || hasPlan ? step("Plan selected", hasFail ? "partial" : hasPlan ? "done" : isActive ? "waiting" : "pending", hasFail ? "retry" : undefined) : null}
2961	                            {(hasChildren || hasPlan) && step("Children running", childState, childState === "partial" ? `${childDone}/${planChildCount}` : undefined)}
2962	                            {(hasChildren || hasMerge) && step("Merge",           hasMerge ? "done" : hasChildren && !isDone ? "waiting" : "pending")}
2963	                            {step("Execute / output", hasExec ? "done" : !hasChildren && isActive ? "waiting" : hasExec || isDone ? "done" : "pending")}
2964	                            {step("Spec validation",  hasSpec ? "done" : isDone ? "done" : isActive ? "waiting" : "pending")}
2965	                            {step("Analysis",         hasAnalysis ? "done" : isDone ? "done" : isActive && (hasMerge || hasExec) ? "waiting" : "pending")}
2966	                            {step("Node done",        isDone ? "done" : isActive ? "waiting" : "pending")}
2967	                          </div>
2968	                        )
2969	                      })()}
2970	                      {selectedNode.goal && (
2971	                        <div className="group">
2972	                          <div className="flex items-center gap-2">
2973	                            <span className="text-[10px] uppercase text-muted-foreground">Goal</span>
2974	                            <button
2975	                              className="opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground hover:text-foreground transition-opacity"
2976	                              onClick={() => setExpandModal({ title: "Node Goal", content: selectedNode.goal! })}
2977	                            >⤢</button>
2978	                          </div>
2979	                          <p className="text-muted-foreground leading-relaxed mt-0.5">{selectedNode.goal}</p>
2980	                        </div>
2981	                      )}
2982	                      {selectedNode.output && (
2983	                        <div className="group">
2984	                          <div className="flex items-center gap-2">
2985	                            <span className="text-[10px] uppercase text-muted-foreground">Output</span>
2986	                            <button
2987	                              className="opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground hover:text-foreground transition-opacity"
2988	                              onClick={() => setExpandModal({ title: "Node Output", content: selectedNode.output! })}
2989	                            >⤢</button>
2990	                          </div>
2991	                          <div className="bg-muted/50 p-2 rounded mt-1 whitespace-pre-wrap text-[10px] font-mono border border-border/50 text-muted-foreground overflow-y-auto">
2992	                            {selectedNode.output}</div>
2993	                        </div>
2994	                      )}
2995	                      {(selectedNodeProposals.length > 0 || selectedNodeVotes.length > 0) && (
2996	                        <div className="grid grid-cols-3 gap-2">
2997	                          <div className="rounded border border-border/60 p-2">
2998	                            <span className="text-[10px] uppercase text-muted-foreground">Proposals</span>
2999	                            <p className="font-mono mt-0.5">{selectedNodeProposals.length}</p></div>
3000	                          <div className="rounded border border-border/60 p-2">
3001	                            <span className="text-[10px] uppercase text-muted-foreground">Vote rounds</span>
3002	                            <p className="font-mono mt-0.5">{selectedNodeVotes.length}</p></div>
3003	                          <div className="rounded border border-border/60 p-2">
3004	                            <span className="text-[10px] uppercase text-muted-foreground">Links</span>
3005	                            <p className="font-mono mt-0.5">{selectedNodeChildren.length}</p></div>
3006	                        </div>
3007	                      )}
3008	                      {selectedNodeEvents.length > 0 && (
3009	                        <div><span className="text-[10px] uppercase text-muted-foreground">Event history</span>
3010	                          <div className="mt-1 space-y-1 overflow-y-auto">
3011	                            {selectedNodeEvents.map((ev, i) => (
3012	                              <div key={`${ev.event}-${ev.timestamp}-${i}`} className="flex items-center gap-2 rounded border border-border/50 px-2 py-1">
3013	                                <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: EVENT_COLORS[ev.event || ""] || "#64748b" }} />
3014	                                <span className="truncate">{eventLabel(ev)}</span>
3015	                                <span className="ml-auto font-mono text-[10px] text-muted-foreground">{relTs(ev.timestamp, runStartRef.current)}</span>
3016	                              </div>
3017	                            ))}</div></div>
3018	                      )}
3019	
3020	                      {/* ── Fork panel — only shown on completed nodes ───────
3021	                          Lets the user branch from this exact point in the run
3022	                          and try a different approach. The fork is a fully
3023	                          independent run; it never affects the parent graph. */}
3024	                      {!selectedNode.active && selectedNode.success && runId && (() => {
3025	                        // ── Cost estimate ─────────────────────────────────────
3026	                        // Computed per-render so it reacts to the consortium /
3027	                        // jury sliders below without needing a separate effect.
3028	                        const perDecision = forkConsortiumSize + forkJurySize
3029	                        const knownChildren = selectedNodeChildren.filter(n => n.type === "raf-node").length
3030	
3031	                        let minCalls: number, maxCalls: number, typeNote: string
3032	                        if (selectedNode.caseType === "base") {
3033	                          // mode_decision + base_execute + analysis = 3 decisions
3034	                          minCalls = 3 * perDecision
3035	                          maxCalls = 3 * perDecision
3036	                          typeNote = "Base node — direct execution, no recursive expansion."
3037	                        } else if (selectedNode.caseType === "recursive") {
3038	                          // mode + plan + refine×children + merge + analysis
3039	                          // Plus a rough multiplier for each child's own pipeline
3040	                          const thisNode = (4 + knownChildren) * perDecision
3041	                          minCalls = thisNode
3042	                          maxCalls = thisNode + knownChildren * 3 * perDecision
3043	                          typeNote = `Recursive node — ${knownChildren > 0 ? `${knownChildren} known children` : "unknown children count"}, each child runs its own pipeline.`
3044	                        } else {
3045	                          minCalls = 2 * perDecision
3046	                          maxCalls = 4 * perDecision
3047	                          typeNote = "Node type undetermined — estimate is a rough lower bound."
3048	                        }
3049	
3050	                        // Colour-code the estimate badge by severity
3051	                        const level = maxCalls <= 15 ? "low" : maxCalls <= 45 ? "medium" : "high"
3052	                        const levelStyle = {
3053	                          low:    "border-green-500/40 bg-green-500/10 text-green-400",
3054	                          medium: "border-yellow-500/40 bg-yellow-500/10 text-yellow-400",
3055	                          high:   "border-red-500/40 bg-red-500/10 text-red-400",
3056	                        }[level]
3057	                        const levelIcon = level === "low" ? "✓" : level === "medium" ? "⚠" : "⚠"
3058	
3059	                        // Helper for the +/- size stepper buttons
3060	                        const Stepper = ({
3061	                          label, value, min, max, parentValue, onChange,
3062	                        }: {
3063	                          label: string; value: number; min: number; max: number
3064	                          parentValue: number; onChange: (n: number) => void
3065	                        }) => (
3066	                          <div className="flex items-center justify-between">
3067	                            <div>
3068	                              <span className="text-[10px] text-muted-foreground">{label}</span>
3069	                              <span className="ml-1.5 text-[9px] text-muted-foreground/50">(parent: {parentValue})</span>
3070	                            </div>
3071	                            <div className="flex items-center gap-1.5">
3072	                              <button
3073	                                onClick={() => onChange(Math.max(min, value - 1))}
3074	                                disabled={value <= min}
3075	                                className="h-5 w-5 rounded border border-border text-muted-foreground hover:text-foreground hover:border-primary/50 disabled:opacity-30 text-xs leading-none"
3076	                              >−</button>
3077	                              <span className="w-4 text-center text-xs font-mono tabular-nums">{value}</span>
3078	                              <button
3079	                                onClick={() => onChange(Math.min(max, value + 1))}
3080	                                disabled={value >= max}
3081	                                className="h-5 w-5 rounded border border-border text-muted-foreground hover:text-foreground hover:border-primary/50 disabled:opacity-30 text-xs leading-none"
3082	                              >+</button>
3083	                            </div>
3084	                          </div>
3085	                        )
3086	
3087	                        return (
3088	                          <div className="rounded-md border border-primary/30 bg-primary/5 p-3 space-y-3 mt-1">
3089	
3090	                            {/* Header */}
3091	                            <div className="flex items-center gap-2">
3092	                              <span className="text-primary text-sm">⑂</span>
3093	                              <span className="text-[10px] font-semibold text-primary uppercase tracking-wider">Fork from here</span>
3094	                            </div>
3095	
3096	                            {/* ── Caution block ──────────────────────────────── */}
3097	                            <div className={`rounded border ${levelStyle} p-2 space-y-1.5`}>
3098	                              <div className="flex items-center justify-between">
3099	                                <span className="text-[10px] font-semibold uppercase tracking-wider">
3100	                                  {levelIcon} Estimated cost
3101	                                </span>
3102	                                {/* Live call count — updates as the sliders change */}
3103	                                <span className="font-mono text-xs">
3104	                                  {minCalls === maxCalls ? `~${minCalls}` : `~${minCalls}–${maxCalls}`} agent calls
3105	                                </span>
3106	                              </div>
3107	                              <p className="text-[10px] leading-relaxed opacity-90">{typeNote}</p>
3108	                              <ul className="text-[10px] opacity-80 space-y-0.5 list-none pl-0">
3109	                                <li>• Each agent call = one LLM request charged to your API key.</li>
3110	                                <li>• Ancestor context is text-only — no extra calls, just longer prompts.</li>
3111	                                <li>• The fork is capped at 20 nodes total to limit runaway expansion.</li>
3112	                                {level === "high" && (
3113	                                  <li className="font-medium">• Consider reducing consortium or jury size below.</li>
3114	                                )}
3115	                              </ul>
3116	                            </div>
3117	
3118	                            {/* ── Agent-count controls ───────────────────────── */}
3119	                            <div className="rounded-md border border-border/50 bg-muted/20 p-2 space-y-2">
3120	                              <p className="text-[10px] text-muted-foreground font-medium">Agent counts for this fork</p>
3121	                              <Stepper
3122	                                label="Consortium size"
3123	                                value={forkConsortiumSize}
3124	                                min={1} max={6}
3125	                                parentValue={consortiumSize}
3126	                                onChange={setForkConsortiumSize}
3127	                              />
3128	                              <Stepper
3129	                                label="Jury size"
3130	                                value={forkJurySize}
3131	                                min={1} max={4}
3132	                                parentValue={jurySize}
3133	                                onChange={setForkJurySize}
3134	                              />
3135	                            </div>
3136	
3137	                            {/* ── Goal textarea ──────────────────────────────── */}
3138	                            <div className="space-y-1">
3139	                              <p className="text-[10px] text-muted-foreground">
3140	                                Goal <span className="opacity-60">(edit to try a different approach)</span>
3141	                              </p>
3142	                              <textarea
3143	                                value={forkGoalOverride}
3144	                                onChange={e => setForkGoalOverride(e.target.value)}
3145	                                rows={3}
3146	                                placeholder="Edit the goal for this fork…"
3147	                                className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs font-mono resize-none focus:outline-none focus:ring-1 focus:ring-primary/50"
3148	                              />
3149	                            </div>

---

## Subagent Output

3150	
3151	                            {/* Inline error — shown when the backend rejects the request */}
3152	                            {forkError && (
3153	                              <p className="text-[10px] text-red-400 rounded border border-red-500/30 bg-red-500/10 px-2 py-1">
3154	                                {forkError}
3155	                              </p>
3156	                            )}
3157	
3158	                            <button
3159	                              onClick={() => forkRun(selectedNode.id, selectedNode.goal || "")}
3160	                              disabled={forkLoading || !forkGoalOverride.trim()}
3161	                              className="w-full rounded-md border border-primary/50 bg-primary/15 px-3 py-1.5 text-xs font-medium text-primary
3162	                                         hover:bg-primary/25 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
3163	                            >
3164	                              {forkLoading ? "Forking…" : `Fork · ~${minCalls === maxCalls ? minCalls : `${minCalls}–${maxCalls}`} calls`}
3165	                            </button>
3166	                          </div>
3167	                        )
3168	                      })()}
3169	                    </>
3170	                  )}
3171	
3172	                  {/* ── Consortium-group: list all proposals ────────────── */}
3173	                  {selectedNode.type === "consortium-group" && (
3174	                    <>
3175	                      <div className="flex items-center gap-2 flex-wrap">
3176	                        <p className="text-muted-foreground text-[10px]">Task: <span className="text-foreground font-mono">{selectedNode.task}</span></p>
3177	                        {(inspectorCandidatesEvent as any)?.tier !== undefined && tierBadge((inspectorCandidatesEvent as any).tier)}
3178	                      </div>
3179	                      <p className="text-[10px] uppercase text-muted-foreground">{inspectorCandidates.length} proposals</p>
3180	                      <div className="space-y-2">
3181	                        {inspectorCandidates.map((cand: any, i: number) => {
3182	                          const payload = cand?.payload || cand || {}
3183	                          const fullText = payload.output || payload.mode || payload.plan || JSON.stringify(payload, null, 2)
3184	                          const preview = fullText.length > 300 ? fullText.slice(0, 300) + "…" : fullText
3185	                          return (
3186	                            <div key={i} className="group rounded-md border border-border/60 p-2 space-y-1">
3187	                              <div className="flex items-center gap-2">
3188	                                <span className="text-[10px] font-mono text-muted-foreground">Agent {i + 1}</span>
3189	                                <button
3190	                                  className="ml-auto opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground hover:text-foreground transition-opacity"
3191	                                  onClick={() => setExpandModal({ title: `Agent ${i + 1} Proposal`, content: fullText })}
3192	                                >⤢</button>
3193	                              </div>
3194	                              <p className="text-[10px] text-muted-foreground whitespace-pre-wrap">{preview}</p>
3195	                            </div>
3196	                          )
3197	                        })}
3198	                        {inspectorCandidates.length === 0 && <p className="text-[10px] text-muted-foreground/50">No candidate data yet.</p>}
3199	                      </div>
3200	                    </>
3201	                  )}
3202	
3203	                  {/* ── Jury-group: winner + all votes ──────────────────── */}
3204	                  {selectedNode.type === "jury-group" && (
3205	                    <>
3206	                      <div className="flex items-center gap-2 flex-wrap">
3207	                        <p className="text-muted-foreground text-[10px]">Task: <span className="text-foreground font-mono">{selectedNode.task}</span></p>
3208	                        {(inspectorCandidatesEvent as any)?.tier !== undefined && tierBadge((inspectorCandidatesEvent as any).tier)}
3209	                      </div>
3210	                      {inspectorWinnerId && (
3211	                        <div className="flex items-center gap-2">
3212	                          <span className="text-[10px] uppercase text-muted-foreground">Winner</span>
3213	                          <Badge className="text-[9px] bg-primary/20 text-primary border-primary/30">{optionLabel(inspectorWinnerId)}</Badge>
3214	                          {(inspectorJuryEvent as any)?.confidence !== undefined && (
3215	                            <span className="text-[10px] font-mono text-muted-foreground ml-auto">{((inspectorJuryEvent as any).confidence * 100).toFixed(0)}%</span>
3216	                          )}
3217	                        </div>
3218	                      )}
3219	                      <div className="space-y-1">
3220	                        {inspectorVotes.map((v: any, i: number) => {
3221	                          const vote = v.vote || v
3222	                          const agentIdx = v.agent_id ?? i
3223	                          const modelLabel = agentModelMap[`${inspectorOwner}:${inspectorTask}:jury:${agentIdx}`] || `agent-${agentIdx}`
3224	                          return (
3225	                            <div key={i} className="flex items-center gap-2 rounded border border-border/50 px-2 py-1 text-[10px]">
3226	                              <span className="font-mono text-purple-300 shrink-0 max-w-[100px] truncate" title={modelLabel}>{modelLabel}</span>
3227	                              <span className="text-muted-foreground">→</span>
3228	                              <span className="font-mono">{optionLabel(vote.winner_id)}</span>
3229	                              {vote.confidence && <span className="ml-auto font-mono text-muted-foreground">{(vote.confidence * 100).toFixed(0)}%</span>}
3230	                            </div>
3231	                          )
3232	                        })}
3233	                        {inspectorVotes.length === 0 && <p className="text-[10px] text-muted-foreground/50">No vote data yet.</p>}
3234	                      </div>
3235	                    </>
3236	                  )}
3237	
3238	                  {/* ── Agent proposal: full payload ─────────────────────── */}
3239	                  {selectedNode.type === "agent-proposal" && (
3240	                    <>
3241	                      <p className="text-muted-foreground text-[10px]">
3242	                        Proposer: <span className="font-mono text-amber-300">
3243	                          {agentModelMap[`${inspectorOwner}:${inspectorTask}:consortium:${selectedNode.candidateIndex}`] || `agent-${selectedNode.candidateIndex ?? "?"}`}
3244	                        </span>
3245	                      </p>
3246	                      {selectedNode.success && <Badge className="text-[9px] bg-primary/20 text-primary border-primary/30 w-fit">winner</Badge>}
3247	                      {(() => {
3248	                        const cand = inspectorCandidates[selectedNode.candidateIndex ?? -1]
3249	                        const payload = cand?.payload || cand || {}
3250	                        const fullText = payload.output || payload.mode || payload.plan || JSON.stringify(payload, null, 2)
3251	                        const preview = fullText.length > 500 ? fullText.slice(0, 500) + "…" : fullText
3252	                        return (
3253	                          <div className="group relative">
3254	                            <div className="bg-muted/50 p-2 rounded text-[10px] font-mono border border-border/50 text-muted-foreground whitespace-pre-wrap overflow-y-auto">
3255	                              {preview || "No payload data."}
3256	                            </div>
3257	                            {fullText.length > 500 && (
3258	                              <button
3259	                                className="mt-1 text-[10px] text-primary hover:underline"
3260	                                onClick={() => setExpandModal({ title: "Agent Proposal", content: fullText })}
3261	                              >Show full output ⤢</button>
3262	                            )}
3263	                          </div>
3264	                        )
3265	                      })()}
3266	                    </>
3267	                  )}
3268	
3269	                  {/* ── Juror vote: voted-for + ranked options ───────────── */}
3270	                  {selectedNode.type === "juror-vote" && (
3271	                    <>
3272	                      <p className="text-muted-foreground text-[10px]">
3273	                        Juror: <span className="font-mono text-purple-300">
3274	                          {agentModelMap[`${inspectorOwner}:${inspectorTask}:jury:${selectedNode.candidateIndex}`] || `agent-${selectedNode.candidateIndex ?? "?"}`}
3275	                        </span>
3276	                      </p>
3277	                      {(() => {
3278	                        const v = inspectorVotes[selectedNode.candidateIndex ?? -1]
3279	                        if (!v) return <p className="text-[10px] text-muted-foreground/50">No vote data.</p>
3280	                        const vote = v.vote || v
3281	                        return (
3282	                          <div className="space-y-2">
3283	                            <div className="flex items-center gap-2">
3284	                              <span className="text-[10px] uppercase text-muted-foreground">Voted for</span>
3285	                              <span className="font-mono text-[10px]">{optionLabel(vote.winner_id)}</span>
3286	                              {vote.confidence && <span className="ml-auto text-[10px] font-mono text-muted-foreground">{(vote.confidence * 100).toFixed(0)}%</span>}
3287	                            </div>
3288	                            {(vote.ranked || []).length > 0 && (
3289	                              <div><p className="text-[10px] uppercase text-muted-foreground mb-1">Rankings</p>
3290	                                {(vote.ranked as any[]).map((r: any, ri: number) => (
3291	                                  <div key={ri} className="flex items-center gap-2 text-[10px] py-0.5">
3292	                                    <span className="font-mono text-muted-foreground w-4">{ri + 1}.</span>
3293	                                    <span className="font-mono">{optionLabel(r.option_id)}</span>
3294	                                    <span className="text-muted-foreground ml-auto">{r.score}</span>
3295	                                  </div>
3296	                                ))}
3297	                              </div>
3298	                            )}
3299	                          </div>
3300	                        )
3301	                      })()}
3302	                    </>
3303	                  )}
3304	
3305	                  {/* ── Merge-group: merge summary ───────────────────────── */}
3306	                  {selectedNode.type === "merge-group" && (
3307	                    <>
3308	                      <p className="text-muted-foreground text-[10px]">Merge result for <span className="font-mono text-foreground">{selectedNode.ownerNodeId}</span></p>
3309	                      {(() => {
3310	                        const mergeEv = events.find(ev => ev.event === "merge_done" && ev.node_id === selectedNode.ownerNodeId)
3311	                        if (!mergeEv) return <p className="text-[10px] text-muted-foreground/50">Merge event not found.</p>
3312	                        return (
3313	                          <div className="space-y-2">
3314	                            {(mergeEv as any).output && (
3315	                              <div className="group">
3316	                                <div className="flex items-center gap-2">
3317	                                  <span className="text-[10px] uppercase text-muted-foreground">Output</span>
3318	                                  <button
3319	                                    className="opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground hover:text-foreground transition-opacity"
3320	                                    onClick={() => setExpandModal({ title: "Merge Output", content: String((mergeEv as any).output) })}
3321	                                  >⤢</button>
3322	                                </div>
3323	                                <div className="bg-muted/50 p-2 rounded mt-1 text-[10px] font-mono border border-border/50 text-muted-foreground overflow-y-auto whitespace-pre-wrap">
3324	                                  {String((mergeEv as any).output)}
3325	                                </div>
3326	                              </div>
3327	                            )}
3328	                            {(mergeEv as any).confidence !== undefined && (
3329	                              <div><span className="text-[10px] uppercase text-muted-foreground">Confidence</span>
3330	                                <p className="font-mono mt-0.5">{((mergeEv as any).confidence * 100).toFixed(0)}%</p></div>
3331	                            )}
3332	                          </div>
3333	                        )
3334	                      })()}
3335	                    </>
3336	                  )}
3337	
3338	                  {/* ── Referee check / plan validation failure ──────────── */}
3339	                  {selectedNode.type === "referee-check" && (
3340	                    <>
3341	                      <p className="text-muted-foreground text-[10px]">Check on <span className="font-mono text-foreground">{selectedNode.ownerNodeId}</span></p>
3342	                      {selectedNode.hint && (
3343	                        <div className="rounded-md border border-red-500/30 bg-red-500/10 p-2 text-[10px] text-red-300">{selectedNode.hint}</div>
3344	                      )}
3345	                      {(() => {
3346	                        const failEv = events.find(ev =>
3347	                          ev.event === "plan_validation_failed" && ev.node_id === selectedNode.ownerNodeId &&
3348	                          ev.plan_attempt === (selectedNode.candidateIndex ?? 0)
3349	                        )

---

## Subagent Output

3350	                        if (!failEv) return <p className="text-[10px] text-muted-foreground/50">No validation failure details found.</p>
3351	                        return (
3352	                          <div className="space-y-1 text-[10px]">
3353	                            {failEv.reason && <div><span className="text-muted-foreground uppercase">Reason</span><p className="mt-0.5">{failEv.reason}</p></div>}
3354	                            {failEv.retry !== undefined && <div><span className="text-muted-foreground uppercase">Attempt</span><p className="font-mono mt-0.5">{failEv.retry} / {failEv.max_retries ?? "?"}</p></div>}
3355	                          </div>
3356	                        )
3357	                      })()}
3358	                      {/* Show plan recovery events for this parent node */}
3359	                      {(() => {
3360	                        const recEvs = events.filter(ev =>
3361	                          ["plan_retry_start","plan_retry_done","plan_abandoned","plan_replaced"].includes(ev.event || "") &&
3362	                          ev.node_id === selectedNode.ownerNodeId
3363	                        )
3364	                        if (recEvs.length === 0) return null
3365	                        return (
3366	                          <div><span className="text-[10px] uppercase text-muted-foreground">Recovery timeline</span>
3367	                            <div className="mt-1 space-y-1 max-h-28 overflow-y-auto">
3368	                              {recEvs.map((ev, i) => (
3369	                                <div key={i} className="flex items-center gap-2 rounded border border-border/50 px-2 py-1 text-[10px]">
3370	                                  <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: EVENT_COLORS[ev.event || ""] || "#64748b" }} />
3371	                                  <span className="truncate">{eventLabel(ev)}</span>
3372	                                  {ev.retry !== undefined && <span className="ml-auto font-mono text-muted-foreground">#{ev.retry}</span>}
3373	                                </div>
3374	                              ))}
3375	                            </div>
3376	                          </div>
3377	                        )
3378	                      })()}
3379	                    </>
3380	                  )}
3381	
3382	                  {/* ── Fallback for unknown satellite types ─────────────── */}
3383	                  {!["raf-node","consortium-group","jury-group","agent-proposal","juror-vote","merge-group","referee-check"].includes(selectedNode.type) && (
3384	                    <div className="grid grid-cols-2 gap-2">
3385	                      <div><span className="text-[10px] uppercase text-muted-foreground">Type</span>
3386	                        <p className="capitalize mt-0.5">{selectedNode.type.replace(/-/g,' ')}</p></div>
3387	                      <div><span className="text-[10px] uppercase text-muted-foreground">Depth</span>
3388	                        <p className="mt-0.5">{selectedNode.depth ?? "—"}</p></div>
3389	                    </div>
3390	                  )}
3391	                </div>
3392	              </motion.div>
3393	            )}
3394	          </AnimatePresence>
3395	
3396	          {/* Physics Tuner — bottom-right collapsible overlay */}
3397	          <PhysicsPanel physics={physics} onChange={setPhysics} />
3398	        </div>
3399	      </div>
3400	
3401	      {/* ══ EXPAND MODAL ══════════════════════════════════════════════════════════ */}
3402	      {expandModal && (
3403	        <ExpandModal
3404	          title={expandModal.title}
3405	          content={expandModal.content}
3406	          onClose={() => setExpandModal(null)}
3407	        />
3408	      )}
3409	    </div>
3410	  )
3411	}
3412	
3413	// ── helpers ────────────────────────────────────────────────────────────────────
3414	
3415	function ConfigSection({ label, children }: { label: string; children: React.ReactNode }) {
3416	  return (
3417	    <div className="min-w-0 space-y-1.5">
3418	      <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">{label}</p>
3419	      {children}
3420	    </div>
3421	  )
3422	}
3423	
3424	function ParamGroup({ label, children }: { label: string; children: React.ReactNode }) {
3425	  return (
3426	    <div className="w-full min-w-0 rounded-md px-0.5 py-1 space-y-1.5">
3427	      <span className="block px-0.5 text-[10px] font-semibold uppercase tracking-widest text-primary">{label}</span>
3428	      {children}
3429	    </div>
3430	  )
3431	}
3432	
3433	function providerLabel(provider: string, availableProviders: string[]): string {
3434	  return `${provider}${availableProviders.includes(provider) ? "" : " (key missing)"}`
3435	}
3436	
3437	function modelInfoList(provider: string, models: Record<string, string[]>, modelCatalog: Record<string, ModelInfo[]>): ModelInfo[] {
3438	  const catalog = modelCatalog[provider]
3439	  if (catalog?.length) return catalog
3440	  return (models[provider] || []).map(id => ({ id, label: id.split("/").pop(), family: provider, tags: ["general"] }))
3441	}
3442	
3443	function ModelChooser({ title, provider, model, juryModel, providers, availableProviders, models, modelCatalog, disabled, open, onOpenChange, onProviderChange, onModelChange, onJuryModelChange }: {
3444	  title: string
3445	  provider: string
3446	  model: string
3447	  juryModel: string
3448	  providers: string[]
3449	  availableProviders: string[]
3450	  models: Record<string, string[]>
3451	  modelCatalog: Record<string, ModelInfo[]>
3452	  disabled: boolean
3453	  open: boolean
3454	  onOpenChange: (open: boolean) => void
3455	  onProviderChange: (provider: string) => void
3456	  onModelChange: (model: string) => void
3457	  onJuryModelChange: (model: string) => void
3458	}) {
3459	  const [query, setQuery] = useState("")
3460	  const providerModels = modelInfoList(provider, models, modelCatalog)
3461	  const filteredModels = providerModels.filter(item => {
3462	    const haystack = `${item.id} ${item.label || ""} ${item.family || ""} ${(item.tags || []).join(" ")}`.toLowerCase()
3463	    return haystack.includes(query.toLowerCase())
3464	  })
3465	
3466	  return (
3467	    <div className="rounded-md border border-border/60 overflow-hidden">
3468	      <button
3469	        type="button"
3470	        className="w-full px-2.5 py-2 flex items-center justify-between text-left hover:bg-accent/40"
3471	        onClick={() => onOpenChange(!open)}
3472	      >
3473	        <div className="min-w-0 flex-1 pr-2">
3474	          <p className="text-xs font-medium">{title}</p>
3475	          <p className="text-[10px] text-muted-foreground break-words">
3476	            Provider: {provider} | Model: {model || "default"}
3477	          </p>
3478	        </div>
3479	        <span className="shrink-0 text-[10px] uppercase tracking-widest text-primary">{open ? "hide" : "models"}</span>
3480	      </button>
3481	
3482	      {open && (
3483	        <div className="border-t border-border/60 p-2 space-y-3">
3484	          <div className="rounded-md border border-border/50 bg-accent/20 px-2 py-2 text-[10px] leading-4 text-muted-foreground">
3485	            Public use currently supports <span className="font-medium text-foreground">mock</span> and{" "}
3486	            <span className="font-medium text-foreground">openrouter</span> as providers. To use real models, choose
3487	            <span className="font-medium text-foreground"> openrouter</span>, paste your OpenRouter API key above, and
3488	            then pick any supported model ID from the list below.
3489	          </div>
3490	          <div className="grid grid-cols-1 gap-2">
3491	            <ConfigSection label="Provider">
3492	              <Select value={provider} onChange={e => onProviderChange(e.target.value)} disabled={disabled}>
3493	                {providers.map(p => <option key={p} value={p}>{providerLabel(p, availableProviders)}</option>)}
3494	              </Select>
3495	            </ConfigSection>
3496	            <ConfigSection label="Jury model">
3497	              <Input value={juryModel} onChange={e => onJuryModelChange(e.target.value)} disabled={disabled} placeholder="same as consortium" />
3498	            </ConfigSection>
3499	          </div>
3500	
3501	          <ConfigSection label="Model">
3502	            <Input value={model} onChange={e => onModelChange(e.target.value)} disabled={disabled} placeholder="default" />
3503	          </ConfigSection>
3504	
3505	          <div className="space-y-2">
3506	            <Input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search models, families, tags" disabled={disabled} />
3507	            <div className="max-h-64 overflow-y-auto overflow-x-hidden space-y-1 pr-1">
3508	              {filteredModels.length === 0 && (
3509	                <p className="text-[10px] text-muted-foreground px-1 py-2">No matching models for this provider.</p>
3510	              )}
3511	              {filteredModels.map(item => (
3512	                <button
3513	                  key={item.id}
3514	                  type="button"
3515	                  disabled={disabled}
3516	                  onClick={() => onModelChange(item.id)}
3517	                  className={`w-full min-w-0 rounded-md border px-2 py-1.5 text-left transition-colors ${model === item.id ? "border-primary/60 bg-primary/10" : "border-border/50 hover:bg-accent/40"}`}
3518	                >
3519	                  <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
3520	                    <span className="min-w-0 break-words text-xs font-medium">{item.label || item.id}</span>
3521	                    <span className="rounded border border-border/40 px-1.5 py-0.5 text-[10px] text-muted-foreground">{item.family || provider}</span>
3522	                  </div>
3523	                  <div className="mt-1 flex min-w-0 flex-wrap items-center gap-1">
3524	                    <span className="min-w-0 max-w-full break-all font-mono text-[10px] text-muted-foreground">{item.id}</span>
3525	                    {(item.tags || []).slice(0, 3).map(tag => (
3526	                      <Badge key={tag} variant="outline" className="shrink-0 px-1 py-0 text-[9px] leading-4 text-muted-foreground">{tag}</Badge>
3527	                    ))}
3528	                  </div>
3529	                </button>
3530	              ))}
3531	            </div>
3532	          </div>
3533	        </div>
3534	      )}
3535	    </div>
3536	  )
3537	}
3538	
3539	function SlotEditor({ title, slots, size, minSize, maxSize, providers, models, modelCatalog, availableProviders, disabled, onSizeChange, onChange }: {
3540	  title: string
3541	  slots: AgentSlot[]
3542	  size: number
3543	  minSize: number
3544	  maxSize: number
3545	  providers: string[]
3546	  models: Record<string, string[]>
3547	  modelCatalog: Record<string, ModelInfo[]>
3548	  availableProviders: string[]
3549	  disabled: boolean

---

## Claude

Now I have a complete picture. I'll write `PipelinePanel.tsx` first, then make surgical edits to `App.tsx`.

---

## Subagent Output

File created successfully at: C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\components\PipelinePanel.tsx

---

## Claude

Now let me make the surgical edits to `App.tsx`. Starting with the imports:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Now add pipeline state variables after the fork state block:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Now add the pipeline functions and drag handlers after `cancelRun`:

---

## Subagent Output

1195	      isRunningRef.current = false
1196	    }
1197	  }
1198	
1199	  const cancelRun = async () => {
1200	    if (!runId) return
1201	    // Keep isRunningRef=true so reconnect can still fire and receive the
1202	    // authoritative run_done { status: "cancelled" } from the server.
1203	    await fetch(`${API_BASE}/api/run/${runId}/cancel`, { method: "POST", headers: authHeaders(runToken) }).catch(() => {})
1204	  }
1205	
1206	  /**
1207	   * Fork the current run from the selected node.
1208	   *
1209	   * Posts to /api/run/{run_id}/fork with the node_id and an optional goal
1210	   * override, then opens the forked run as a brand-new session so the user
1211	   * can watch it live without losing the parent session's graph.
1212	   *
1213	   * The forked run inherits all provider/model config from the parent run.
1214	   * The parent run must still be in server memory (not evicted by the 50-run

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Now add the toolbar button. Let me find the exact toolbar area:

---

## Subagent Output

<tool_use_error>InputValidationError: Grep failed due to the following issue:
An unexpected parameter `file_path` was provided</tool_use_error>

---

## Subagent Output

2992-            {currentPhase !== "Idle" && <Badge variant="outline" className="text-xs">{currentPhase}</Badge>}
2993-            {running && <Badge className="text-xs tabular-nums animate-pulse bg-blue-500/20 text-blue-400 border-blue-500/30">{nodeCount} / {maxNodesTotal}</Badge>}
2994-          </div>
2995-          <div className="flex items-center gap-3">
2996:            {!workPanelOpen && (
2997-              <Button variant="outline" size="sm" className="h-7 gap-1 text-[10px]" onClick={() => setWorkPanelOpen(true)}>
2998-                <FileText className="h-3 w-3" /> Workspace
2999-              </Button>
3000-            )}

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Now add the floating panel JSX before the ExpandModal:

---

## Subagent Output

3635-        </div>
3636-      </div>
3637-
3638:      {/* ══ EXPAND MODAL ══════════════════════════════════════════════════════════ */}
3639-      {expandModal && (
3640-        <ExpandModal
3641-          title={expandModal.title}

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Now let me verify the TypeScript compiles by checking for any obvious issues:

---

## Subagent Output

(Bash completed with no output)

---

## Claude

Clean compile. Let me do a quick sanity-check on the key parts of App.tsx to make sure everything landed correctly:

---

## Subagent Output

No matches found

---

## Subagent Output

20:import { PipelinePanel } from "./components/PipelinePanel"
21:import type { PipelineStep, PipelineStepResult } from "./components/PipelinePanel"
520:  const [pipelineOpen, setPipelineOpen] = useState(false)
521:  const [pipelinePanelPos, setPipelinePanelPos] = useState({ left: 300, top: 120 })
523:  const [pipelineRunning, setPipelineRunning] = useState(false)
1213:  const waitForRunDone = (stepRunId: string, stepToken: string): Promise<string | undefined> =>
1247:  const runPipeline = async () => {
1248:    if (pipelineRunning) return
1333:        const output = await waitForRunDone(data.run_id, data.access_token)
1405:  const startPipelinePanelDrag = (e: PointerEvent<HTMLDivElement>) => {
1409:  const movePipelinePanelDrag = (e: PointerEvent<HTMLDivElement>) => {
1412:    setPipelinePanelPos({ left: left + e.clientX - x, top: top + e.clientY - y })
1414:  const endPipelinePanelDrag = () => { pipelinePanelDragRef.current = null }
3003:              variant={pipelineOpen ? "default" : "outline"}
3005:              className={`h-7 gap-1 text-[10px] ${pipelineOpen ? "bg-primary/20 text-primary border-primary/50" : ""} ${pipelineRunning ? "animate-pulse" : ""}`}
3010:              {pipelineRunning ? `Pipeline · ${pipelineStepIdx + 1}/${pipelineSteps.length}` : "Pipeline"}
3641:      {pipelineOpen && (
3642:        <PipelinePanel
3645:          running={pipelineRunning}
3649:          onRun={runPipeline}
3653:          onPointerDown={startPipelinePanelDrag}
3654:          onPointerMove={movePipelinePanelDrag}
3655:          onPointerUp={endPipelinePanelDrag}

---

## Claude

All the pieces are in place. Let me also verify the `pipelineSteps` and `pipelineResults` state lines landed:

---

## Subagent Output

522:  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>([{ id: "step-1", goal: "" }])
524:  const [pipelineStepIdx, setPipelineStepIdx] = useState(-1)
525:  const [pipelineResults, setPipelineResults] = useState<PipelineStepResult[]>([])
527:  const pipelineCancelRef = useRef(false)
528:  const pipelinePanelDragRef = useRef<{ x: number; y: number; left: number; top: number } | null>(null)
1221:        if (pipelineCancelRef.current) {
1252:    pipelineCancelRef.current = false
1256:    for (let i = 0; i < pipelineSteps.length; i++) {
1257:      if (pipelineCancelRef.current) break
1259:      const step = pipelineSteps[i]
1361:  const cancelPipeline = () => { pipelineCancelRef.current = true }
1407:    pipelinePanelDragRef.current = { x: e.clientX, y: e.clientY, ...pipelinePanelPos }
1410:    if (!pipelinePanelDragRef.current) return
1411:    const { x, y, left, top } = pipelinePanelDragRef.current
1414:  const endPipelinePanelDrag = () => { pipelinePanelDragRef.current = null }
3010:              {pipelineRunning ? `Pipeline · ${pipelineStepIdx + 1}/${pipelineSteps.length}` : "Pipeline"}
3643:          steps={pipelineSteps}
3644:          results={pipelineResults}
3646:          currentStepIdx={pipelineStepIdx}

---

## Claude

Everything is wired up correctly. Here's what was built:

---

**Feature 2: Goal Chaining / Pipelines is now complete.**

**What was added:**

`web/src/components/PipelinePanel.tsx` (new file):
- `PipelineStep` and `PipelineStepResult` exported types
- Draggable floating panel with: step list, `{{output}}` hint, per-step status indicators (running pulse / ✓ done / ✕ error), output preview, "View run" button on completed steps, Add/Remove step controls, Run Pipeline / Cancel buttons

`web/src/App.tsx` (surgical additions):
- Imports `Link2` icon, `PipelinePanel`, and the two types
- 7 new state variables (`pipelineOpen`, `pipelinePanelPos`, `pipelineSteps`, `pipelineRunning`, `pipelineStepIdx`, `pipelineResults`) + 2 refs (`pipelineCancelRef`, `pipelinePanelDragRef`)
- `waitForRunDone(runId, token)` — isolated WebSocket per step that resolves on `run_done` and respects the cancel ref
- `runPipeline()` — sequential step executor; substitutes `{{output}}`, calls `/api/run`, waits, records results; stops on any error or cancel; **never touches the active session's state**
- `cancelPipeline()` — sets the cancel ref so the next check loop or `waitForRunDone` message handler exits cleanly
- `viewPipelineStep(result)` — replays a completed step's events into the main viewport (same as server-run replay)
- 3 drag handlers with pointer-capture
- Toolbar "Pipeline" button that pulses and shows step progress while running
- The floating `PipelinePanel` rendered at root JSX level (above graph and work panel)

---

## You

ok good now i want you to go back and do a simple review of what we did to make sure we are on the right path

---

## Subagent Output

Perfect. Now I have enough information to write a comprehensive code review. Let me compile my findings:

## Code Review: Fork Run & Pipeline Features

### BACKEND ISSUES

#### 1. **CRITICAL BUG: Fork Endpoint Header Mismatch** (main.py, line 291)
The frontend calls the fork endpoint with header `X-Run-Token`, but the backend expects `x_run_token` (snake_case in FastAPI). 

**File:** `/server/main.py`, line 288-291
```python
def fork_run(
    run_id: str,
    body: ForkRequest,
    x_run_token: str | None = Header(default=None),
```

**Frontend call** (App.tsx, line 1439):
```javascript
headers: authHeaders(runToken, true),  // produces "X-Run-Token"
```

FastAPI's `Header` parameter automatically converts to snake_case, so this should work, BUT line 291 uses the wrong parameter name format. The call will succeed but only because FastAPI internally handles the conversion. **This is not a direct blocker but is fragile**—the pattern is inconsistent with other endpoints. The backend should match what all other endpoints expect.

---

#### 2. **Fork Goal Building Logic Issue** (run_manager.py, lines 470-478)
The ancestor collection logic has a subtle bug in line 478. 

**File:** `/server/run_manager.py`, lines 470-478
```python
ancestor_events = sorted(ancestor_events, key=lambda e: e.get("depth", 0))[-5:]
```

**Problem:** This sorts by depth ascending (shallowest first), then takes the last 5, which gives you the deepest ancestors, not the shallowest-first ordering the comment claims. This reverses the intended order.

**Expected:** Should be `sorted(..., key=lambda e: e.get("depth", 0))[:5]` to keep the 5 shallowest.

**Impact:** Ancestor context is shown deepest→shallowest instead of root→parent. The fork still works, but the context ordering in the goal string is backwards. The comment on line 477 is also contradicted by the code.

---

#### 3. **Fork Source Lineage Bug** (run_manager.py, line 567)
The `fork_source` field is set *after* `create_run()` returns and before the run's thread starts. There's a race condition where the run thread could emit events before `fork_source` is assigned.

**File:** `/server/run_manager.py`, lines 552-568
```python
fork_state = self.create_run(...)  # thread starts here (line 254)
fork_state.fork_source = parent_state.run_id  # assigned here, after thread starts
```

**Impact:** If the run completes very quickly or logs early, `fork_source` may still be `None` when events are replayed. Not critical (UI doesn't crash), but lineage info can be lost for fast runs.

**Fix:** Set `fork_source` *before* creating the run, or pass it to `create_run()` and let it set the field on the `RunState` before starting the thread.

---

### FRONTEND ISSUES

#### 4. **Race Condition in `waitForRunDone`** (App.tsx, lines 1213-1237)
The `settle` guard correctly prevents double-settlement, but there's a subtle timing issue. If the WebSocket closes *immediately after* `run_done` is received but *before* `ws.close()` completes, the `ws.onclose` handler may fire.

**File:** `/web/src/App.tsx`, lines 1216-1236
```javascript
const settle = (fn: () => void) => { if (!settled) { settled = true; fn() } }
ws.onmessage = (msg) => {
  ...
  if (ev.event === "run_done") {
    ws.close()
    settle(() => resolve(...))
    return
  }
}
ws.onclose = () => settle(() => reject(...))
```

**Issue:** After `ws.close()` is called, `ws.onclose` will fire. The `settle` guard prevents double-settlement, but the promise resolves before the socket is actually closed, which is fine. However, if the server *closes the socket* at the same nanosecond as `run_done` arrives, both handlers could race. The guard prevents the bug, but the code is fragile.

**Not a blocker** because the guard works, but could add `ws.removeEventListener("close", onclose)` after `ws.close()` to be explicit.

---

#### 5. **`pipelineCancelRef` Closure Issue** (App.tsx, lines 1221, 1257, 1361)
The `runPipeline` async function correctly reads `pipelineCancelRef.current` at line 1257, and `waitForRunDone` reads it at line 1221. This pattern works because `useRef` values persist across renders and the ref is checked *during* the async wait, not after. **No bug here—this is correctly implemented.**

---

#### 6. **`viewPipelineStep` WebSocket Isolation** (App.tsx, lines 1368-1398)
The function correctly clears `seenEventsRef` and other refs before replaying events, so the main WebSocket's state is not clobbered. The flow is:
1. Fetch events from server (no live WS)
2. Clear replay tracking
3. Process events locally
4. Do NOT reconnect the WebSocket to a pipeline step

**This is correct.** The comment at line 1379-1383 clearly documents the reset. The main run's WebSocket remains untouched.

---

#### 7. **`{{output}}` Substitution Regex** (App.tsx, line 1262)
```javascript
step.goal.replace(/\{\{output\}\}/g, lastOutput)
```

**Correct.** The regex properly escapes the braces and uses the global flag `g` to replace all occurrences. No issues.

---

#### 8. **Pipeline Drag Handler Missing `onPointerCancel`** (PipelinePanel.tsx & App.tsx, lines 1405-1414 and 3641-3657)
The WorkPanel drag handlers include `onPointerCancel` (line 2611), but the PipelinePanel handlers do not.

**File:** `PipelinePanel.tsx`, lines 84-85
```javascript
onPointerMove={onPointerMove}
onPointerUp={onPointerUp}
// Missing: onPointerCancel
```

**Impact:** If the user drags the pipeline panel and the pointer is cancelled mid-drag (e.g., gesture interrupt on touch, or system event), `pipelinePanelDragRef.current` is not cleared. Subsequent drag attempts start from the stale ref state, causing erratic jumps.

**Fix:** Add `onPointerCancel={onPointerUp}` to the outer div in PipelinePanel.tsx, line 85.

---

#### 9. **Pointer Capture Pattern Inconsistency** (App.tsx, lines 1405-1414 vs 2004-2008)
**WorkPanel** (correct):
```javascript
const startWorkPanelDrag = (e: PointerEvent<HTMLDivElement>) => {
  if ((e.target as HTMLElement).closest("button")) return  // ignore button clicks
  workPanelDragRef.current = { ... }
  e.currentTarget.setPointerCapture(e.pointerId)
}
```

**PipelinePanel** (missing button check):
```javascript
const startPipelinePanelDrag = (e: PointerEvent<HTMLDivElement>) => {
  e.currentTarget.setPointerCapture(e.pointerId)
  pipelinePanelDragRef.current = { ... }
}
```

**Issue:** The PipelinePanel header contains buttons (remove step, cancel pipeline, etc.). If the user clicks a button, the drag handler fires and captures the pointer, potentially preventing the button click from registering.

**Fix:** Add the button check to `startPipelinePanelDrag`:
```javascript
if ((e.target as HTMLElement).closest("button")) return
```

---

#### 10. **TypeScript Type in PipelinePanel.tsx** (lines 7, 44-46)
The import uses `type { PointerEvent }`, but this is React's synthetic event type, not a separate export. The correct import should be implicit from React.

**File:** `PipelinePanel.tsx`, line 7
```typescript
import type { PointerEvent } from "react"
```

**Issue:** `PointerEvent` is not directly exported from "react". It's `React.PointerEvent`. This may not type-check correctly in strict mode or cause a runtime error if TypeScript is misconfigured.

**Fix:** 
```typescript
import React from "react"
// Then use: React.PointerEvent<HTMLDivElement>
// OR import it from the synthetic event types
```

Alternatively, use the built-in `PointerEvent` from the DOM:
```typescript
import type { PointerEvent as DOMPointerEvent } from "react"
```

Actually, checking the App.tsx (which compiles successfully), it uses the pattern without explicit imports. **This may not be a bug if using TypeScript 4.6+**, but it's worth verifying `tsconfig.json` has `"jsx": "react-jsx"` or similar.

---

#### 11. **Fork Endpoint Parameter Name** (App.tsx, line 307)
The backend function signature and the frontend call are consistent:

**Backend** (main.py, line 307):
```python
body.goal,  # optional, can be None
```

**Frontend** (App.tsx, line 1444):
```javascript
goal: forkGoalOverride.trim() !== nodeGoal.trim() ? forkGoalOverride.trim() || null : null,
```

**This is correct.** The frontend sends `goal` (string | null) and the backend expects it. The ForkRequest model at line 96-102 of main.py accepts `goal: str | None = None`, so this matches.

---

### SUMMARY TABLE

| Issue | Severity | File | Line(s) | Type |
|-------|----------|------|---------|------|
| Ancestor sort order reversed | High | run_manager.py | 478 | Logic error |
| Fork source race condition | Medium | run_manager.py | 567 | Race condition |
| Pipeline drag missing onPointerCancel | Medium | PipelinePanel.tsx | 85 | Missing handler |
| Pipeline drag ignores button clicks | Medium | App.tsx | 1405 | Logic error |
| PointerEvent import questionable | Low | PipelinePanel.tsx | 7 | Type issue |
| Header name consistency | Low | main.py | 291 | Fragile pattern |

---

### WHAT'S CORRECT

- `waitForRunDone` settlement guard works correctly (lines 1213-1237)
- `pipelineCancelRef` closure pattern is correct (lines 1221, 1257, 1361)
- `viewPipelineStep` correctly isolates WebSocket state (lines 1368-1398)
- `{{output}}` regex is correct (line 1262)
- Fork endpoint parameters match frontend/backend (main.py & App.tsx)
- Fork lineage info is correctly returned to frontend (main.py, line 322-323)
- Drag handler pointer capture pattern is correctly used (both panels capture pointers)

---

## Claude

Good findings. Let me read the actual backend code to verify the reported issues, then fix the real ones.

---

## Subagent Output

1	"""
2	server.run_manager
3	==================
4	Manages the lifecycle of RAF runs spawned by the API server.
5	
6	Each run executes in a background daemon thread and emits JSON events into a
7	Queue.  WebSocket clients drain the queue in real time via :func:`stream_events`.
8	
9	Key classes
10	-----------
11	RunState
12	    All state for a single run: its events list, streaming queue, thread,
13	    cancellation event, plan-approval gates, and completion metadata.
14	RunManager
15	    Factory and registry for RunState objects.  Handles adapter selection,
16	    config assembly, and the optional jury adapter for multi-model setups.
17	"""
18	
19	import asyncio
20	import os
21	import secrets
22	import threading
23	import time
24	import uuid
25	from dataclasses import dataclass, field
26	from queue import Queue
27	from typing import Any, Dict, List, Optional
28	
29	from raf.core.deps import DependencyError, validate_plan
30	from raf.core.engine import RafEngine
31	from raf.core.trace import TraceLogger
32	from raf.llm.mock_adapter import MockAdapter
33	from raf.schemas import RafConfig
34	
35	# Maximum number of completed run summaries kept in history
36	_MAX_HISTORY = 50
37	# Maximum events kept per run in the replay list (guards against memory growth on deep runs)
38	_MAX_EVENTS_PER_RUN = 2000
39	
40	
41	@dataclass
42	class RunState:
43	    """All state for a single RAF run.
44	
45	    Parameters
46	    ----------
47	    run_id:
48	        UUID string identifying this run.
49	    goal:
50	        The top-level goal string passed to the engine.

---

## Subagent Output

78:    fork_source: Optional[str] = None
438:    def _build_fork_goal(
446:        ancestor node goals as context, and optionally attaches the node's
468:        # Collect ancestor node goals: nodes at shallower depth created before
470:        ancestor_events = [
478:        ancestor_events = sorted(ancestor_events, key=lambda e: e.get("depth", 0))[-5:]
490:        if ancestor_events:
492:                "[FORK CONTEXT — ancestor tasks completed in parent run]"
494:            for e in ancestor_events:
510:        # No ancestor context (e.g. forking the root node itself) — run the
514:    def fork_run(
526:        ancestor context from the parent's event log. It inherits the parent's
533:        enriched_goal = self._build_fork_goal(
567:        fork_state.fork_source = parent_state.run_id

---

## Subagent Output

438	    def _build_fork_goal(
439	        parent_events: List[Dict[str, Any]],
440	        node_id: str,
441	        override_goal: Optional[str],
442	    ) -> Optional[str]:
443	        """Build an enriched goal string for a forked run.
444	
445	        Walks the parent run's event log to find the clicked node, collects
446	        ancestor node goals as context, and optionally attaches the node's
447	        prior output so the fork knows what was already attempted.
448	
449	        Returns None if node_id cannot be found in the event log (→ 404).
450	        """
451	        # Find the node_created event for the target node
452	        target_event = next(
453	            (e for e in parent_events
454	             if e.get("event") == "node_created" and e.get("node_id") == node_id),
455	            None,
456	        )
457	        if target_event is None:
458	            return None
459	
460	        original_goal = target_event.get("goal", "")
461	        # Use the user-supplied override if provided, else fall back to the
462	        # original goal from the parent run's event log.
463	        fork_goal = (override_goal or "").strip() or original_goal
464	
465	        target_depth = target_event.get("depth", 0)
466	        target_ts = target_event.get("timestamp", 0)
467	
468	        # Collect ancestor node goals: nodes at shallower depth created before
469	        # the target. Limit to 5 entries so the enriched goal stays concise.
470	        ancestor_events = [
471	            e for e in parent_events
472	            if e.get("event") == "node_created"
473	            and e.get("depth", 99) < target_depth
474	            and e.get("timestamp", 0) < target_ts
475	            and e.get("goal")
476	        ]
477	        # Sort shallowest-first (root → parent) and cap at 5
478	        ancestor_events = sorted(ancestor_events, key=lambda e: e.get("depth", 0))[-5:]
479	
480	        # Pull the prior output for this node if it already completed in the
481	        # parent run. This lets the fork know what was tried before.
482	        prior_output: Optional[str] = next(
483	            (e.get("output", "") for e in parent_events
484	             if e.get("event") == "node_done" and e.get("node_id") == node_id),
485	            None,
486	        )
487	
488	        context_parts: List[str] = []
489	
490	        if ancestor_events:
491	            context_parts.append(
492	                "[FORK CONTEXT — ancestor tasks completed in parent run]"
493	            )
494	            for e in ancestor_events:
495	                goal_text = (e.get("goal") or "").replace("\n", " ").strip()
496	                if goal_text:
497	                    context_parts.append(f"  - {goal_text}")
498	
499	        if prior_output:
500	            # Clamp to 1000 chars so we don't blow up the context window
501	            clamped = prior_output[:1000] + ("…" if len(prior_output) > 1000 else "")
502	            context_parts.append(
503	                f"\n[PRIOR OUTPUT for this node in parent run]\n{clamped}"
504	            )
505	
506	        if context_parts:
507	            header = "\n".join(context_parts)
508	            return f"{header}\n\n[FORK SUB-GOAL]\n{fork_goal}"
509	
510	        # No ancestor context (e.g. forking the root node itself) — run the
511	        # goal directly so the fork behaves like a plain re-run.
512	        return fork_goal
513	
514	    def fork_run(
515	        self,
516	        parent_state: RunState,
517	        node_id: str,
518	        override_goal: Optional[str] = None,
519	        consortium_size: Optional[int] = None,
520	        jury_size: Optional[int] = None,
521	        max_nodes_total: Optional[int] = None,
522	    ) -> Optional[RunState]:
523	        """Create a new run forked from a specific node in an existing run.
524	
525	        The fork is a fully independent run whose goal is enriched with
526	        ancestor context from the parent's event log. It inherits the parent's
527	        provider / model / agent config, but the caller can override the agent
528	        counts and node budget so exploratory forks don't accidentally spin up
529	        a run as large as the original.
530	
531	        Returns None (→ HTTP 404) if node_id is not found in parent events.
532	        """
533	        enriched_goal = self._build_fork_goal(
534	            parent_state.events, node_id, override_goal
535	        )
536	        if enriched_goal is None:
537	            return None
538	
539	        # Start from the parent's config and layer the fork-specific overrides
540	        # on top. This way any settings the parent had (timeouts, domain, etc.)
541	        # carry over while the user-controlled cost knobs take effect.
542	        fork_config = dict(parent_state.config_overrides)
543	        if consortium_size is not None and consortium_size > 0:
544	            fork_config["consortium_size"] = consortium_size
545	        if jury_size is not None and jury_size > 0:
546	            fork_config["jury_size"] = jury_size
547	        if max_nodes_total is not None and max_nodes_total > 0:
548	            fork_config["max_nodes_total"] = max_nodes_total
549	
550	        # Clone the parent's adapter slots. If the user reduced the consortium
551	        # size below the number of slots, the engine will only use the first N.
552	        fork_state = self.create_run(
553	            enriched_goal,
554	            provider=parent_state.provider,
555	            model=parent_state.model,
556	            config_overrides=fork_config,
557	            jury_model=parent_state.jury_model,
558	            consortium_agents=parent_state.consortium_agents,
559	            jury_agents=parent_state.jury_agents,
560	            leaf_agents=parent_state.leaf_agents,
561	            mid_agents=parent_state.mid_agents,
562	            root_agents=parent_state.root_agents,
563	            api_key=parent_state.api_key,
564	        )
565	
566	        # Tag the new run with its origin so lineage is traceable
567	        fork_state.fork_source = parent_state.run_id
568	        return fork_state
569	
570	    def _execute(self, run: RunState) -> None:
571	        """Entry point for the background daemon thread that runs the engine."""
572	        try:
573	            config = self._build_config(run.config_overrides)
574	            # Expose the run-specific limit so approve_plan() validates correctly.
575	            run.max_children_per_plan = config.max_children_per_plan
576	
577	            # Build per-slot adapter lists.

---

## Claude

Let me check the workPanel drag pattern to verify the onPointerCancel claim and the button check:

---

## Subagent Output

2004:  const startWorkPanelDrag = (e: PointerEvent<HTMLDivElement>) => {
2005:    if ((e.target as HTMLElement).closest("button")) return
2010:  const moveWorkPanelDrag = (e: PointerEvent<HTMLDivElement>) => {
2022:  const endWorkPanelDrag = () => {
2591:            onPointerCancel={endSidebarResize}
2608:            onPointerDown={startWorkPanelDrag}
2609:            onPointerMove={moveWorkPanelDrag}
2610:            onPointerUp={endWorkPanelDrag}
2611:            onPointerCancel={endWorkPanelDrag}

---

## Claude

Confirmed. Three real fixes needed. Let me also check `create_run` to understand the fork_source race condition:

---

## Subagent Output

6:Each run executes in a background daemon thread and emits JSON events into a
12:    All state for a single run: its events list, streaming queue, thread,
22:import threading
85:    thread: Optional[threading.Thread] = None
92:    cancel_event: threading.Event = field(default_factory=threading.Event)
98:    _plan_events: Dict[str, threading.Event] = field(default_factory=dict)
118:        """Called from the engine background thread.  Emits ``plan_ready`` and blocks
121:        event = threading.Event()
151:        # Pop _plan_events here so the map doesn't grow; the engine thread will
206:    def create_run(
220:        """Create, register, and immediately start a new run in a daemon thread."""
253:        run.thread = threading.Thread(target=self._execute, args=(run,), daemon=True)
254:        run.thread.start()
571:        """Entry point for the background daemon thread that runs the engine."""
685:            event = await asyncio.to_thread(run.queue.get)

---

## Subagent Output

206	    def create_run(
207	        self,
208	        goal: str,
209	        provider: str = "mock",
210	        model: Optional[str] = None,
211	        config_overrides: Optional[Dict[str, object]] = None,
212	        jury_model: Optional[str] = None,
213	        consortium_agents: Optional[List[Dict[str, Optional[str]]]] = None,
214	        jury_agents: Optional[List[Dict[str, Optional[str]]]] = None,
215	        leaf_agents: Optional[List[Dict[str, Optional[str]]]] = None,
216	        mid_agents: Optional[List[Dict[str, Optional[str]]]] = None,
217	        root_agents: Optional[List[Dict[str, Optional[str]]]] = None,
218	        api_key: Optional[str] = None,
219	    ) -> RunState:
220	        """Create, register, and immediately start a new run in a daemon thread."""
221	        run_id = str(uuid.uuid4())
222	        run = RunState(
223	            run_id=run_id,
224	            goal=goal,
225	            provider=provider,
226	            model=model,
227	            jury_model=jury_model,
228	            consortium_agents=consortium_agents or [],
229	            jury_agents=jury_agents or [],
230	            leaf_agents=leaf_agents or [],
231	            mid_agents=mid_agents or [],
232	            root_agents=root_agents or [],
233	            config_overrides=config_overrides or {},
234	            api_key=api_key,
235	        )
236	        self._runs[run_id] = run
237	        self._history.append(run_id)
238	        if len(self._history) > _MAX_HISTORY:
239	            # Prefer evicting the oldest *completed* run; fall back to oldest run
240	            # if every slot is still active (prevents unbounded history growth).
241	            evicted = False
242	            for i, rid in enumerate(self._history):
243	                candidate = self._runs.get(rid)
244	                if candidate is None or candidate.status != "running":
245	                    self._history.pop(i)
246	                    self._runs.pop(rid, None)
247	                    evicted = True
248	                    break
249	            if not evicted:
250	                oldest = self._history.pop(0)
251	                self._runs.pop(oldest, None)
252	
253	        run.thread = threading.Thread(target=self._execute, args=(run,), daemon=True)
254	        run.thread.start()
255	        return run

---

## Claude

Confirmed: `create_run` starts the thread at line 254, so setting `fork_source` at line 567 is technically after thread start. However, `fork_source` is never read by the engine thread — it's only used for lineage display — so it's not a real problem.

Three real fixes to make:
1. `run_manager.py` line 478: `[-5:]` should be `[:5]` (takes deepest 5, not shallowest 5)
2. `PipelinePanel.tsx`: missing `onPointerCancel` prop + handler
3. `App.tsx`: `startPipelinePanelDrag` missing button-click guard

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\run_manager.py has been updated successfully.

---

## Subagent Output

40	  onCancel: () => void
41	  onViewStep: (result: PipelineStepResult) => void
42	  onClose: () => void
43	  // Pointer-capture drag handlers — attach to the drag-handle header
44	  onPointerDown: (e: PointerEvent<HTMLDivElement>) => void
45	  onPointerMove: (e: PointerEvent<HTMLDivElement>) => void
46	  onPointerUp: (e: PointerEvent<HTMLDivElement>) => void
47	}
48	
49	export function PipelinePanel({
50	  steps, results, running, currentStepIdx, panelPos,
51	  onStepsChange, onRun, onCancel, onViewStep, onClose,
52	  onPointerDown, onPointerMove, onPointerUp,
53	}: Props) {
54	  // ── step helpers ────────────────────────────────────────────────────────────
55	  const addStep = () =>
56	    onStepsChange([...steps, { id: `step-${Date.now()}`, goal: "" }])
57	
58	  const removeStep = (id: string) =>
59	    onStepsChange(steps.filter(s => s.id !== id))

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\components\PipelinePanel.tsx has been updated successfully.

---

## Claude

Now find the outer div in PipelinePanel that needs `onPointerCancel`:

---

## Subagent Output

80	  return (
81	    // The outer div captures pointer moves/ups so dragging stays smooth even
82	    // when the cursor leaves the header during fast movement.
83	    <div
84	      className="fixed z-30 w-[380px] bg-card border border-border rounded-lg shadow-xl flex flex-col overflow-hidden"
85	      style={{ left: panelPos.left, top: panelPos.top, maxHeight: "80vh" }}
86	      onPointerMove={onPointerMove}
87	      onPointerUp={onPointerUp}
88	    >
89	      {/* ── Drag-handle header ─────────────────────────────────────────────── */}
90	      <div
91	        className="flex items-center justify-between px-3 py-2 border-b border-border bg-card/80 cursor-move select-none shrink-0"
92	        onPointerDown={onPointerDown}
93	      >
94	        <div className="flex items-center gap-2">

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\components\PipelinePanel.tsx has been updated successfully.

---

## Claude

Now fix App.tsx — add button guard to the drag start handler, and pass `onPointerCancel` to the panel:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Now pass `onPointerCancel` to the `PipelinePanel` JSX:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Final type-check to confirm everything is clean:

---

## Subagent Output

(Bash completed with no output)

---

## Claude

Still clean. Here's a summary of what the review found and what was fixed:

---

**Issues found and fixed:**

| | File | What was wrong | Fix |
|---|---|---|---|
| 1 | `run_manager.py:478` | `[-5:]` took the 5 *deepest* ancestors instead of the 5 *shallowest* (root→parent order) | Changed to `[:5]` |
| 2 | `PipelinePanel.tsx` | Missing `onPointerCancel` — if the OS interrupts a drag (e.g. touch gesture), the drag ref would be left set, causing erratic jumps on the next drag | Added `onPointerCancel` prop + wired it to the outer div |
| 3 | `App.tsx:startPipelinePanelDrag` | No button-click guard — clicking the close ✕ would capture the pointer before the click could fire | Added `if (closest("button")) return` matching the existing workPanel pattern |

**Issues reviewed and dismissed:**
- `fork_source` race condition: not real — the engine thread never reads `fork_source`, only the HTTP response layer does
- `waitForRunDone` settlement: the `settled` guard correctly handles the close-after-run_done race
- `PointerEvent` import: same pattern as App.tsx line 3, already confirmed by TypeScript passing
- Header name FastAPI: auto-converts `X-Run-Token` → `x_run_token`, all other endpoints use the same pattern

---

## You

ok good this is good , i want to make sure that you are also adding the right error handing  to be sure  reeber it is not supposed to show in the frontend but in the logs

---

## Claude

Let me audit the error handling in all the new code before touching anything.

---

## Subagent Output

147:        except DependencyError as exc:
148:            raise ValueError(f"Invalid plan: {exc}") from exc
375:                raise RuntimeError("An OpenRouter API key is required. Paste yours into the key field in the UI.")
613:                except Exception:
652:        except Exception as exc:
682:            except Empty:

---

## Subagent Output

(Bash completed with no output)

---

## Subagent Output

600	
601	            trace = TraceLogger(emit=run.emit, store=False, quiet=True)
602	
603	            on_plan_ready = run.request_plan_approval if config.plan_approval_required else None
604	
605	            # Build optional fallback adapter — used when all primary consortium/jury
606	            # agents time out and zero results are available.
607	            fallback_adapter = None
608	            fb_provider = getattr(config, "fallback_provider", "")
609	            fb_model = getattr(config, "fallback_model", "") or None
610	            if fb_provider:
611	                try:
612	                    fallback_adapter = self._build_adapter(fb_provider, fb_model, key)
613	                except Exception:
614	                    pass  # missing key — run without fallback
615	
616	            # ── Tier adapter lists for depth-based model routing ───────────────
617	            # When tier agents are provided: leaf → workers, mid → planners,
618	            # root → referee/analysis.  When empty, each tier falls back to the
619	            # flat consortium/jury adapters inside RafEngine.
620	            #
621	            # The mid-tier adapters also serve as jury for the leaf tier
622	            # (jury floor rule: weak models must not judge weak models).
623	            # The root-tier adapters serve as jury for root/analysis decisions.
624	            def _build_tier(agents):
625	                """Build an adapter list from a list of {provider, model} dicts."""
626	                if not agents:
627	                    return None
628	                return [self._build_adapter(a["provider"], a.get("model"), key) for a in agents]
629	
630	            leaf_adapters = _build_tier(run.leaf_agents)
631	            mid_adapters = _build_tier(run.mid_agents)
632	            root_adapters = _build_tier(run.root_agents)
633	            # Jury tiers — same objects as mid/root adapters (see RafEngine docstring)
634	            mid_jury_adapters = mid_adapters   # jury floor for Tier 0 + Tier 1
635	            root_jury_adapters = root_adapters  # jury for Tier 2 analysis/root
636	
637	            engine = RafEngine(
638	                config, consortium_adapters, trace,
639	                jury_adapters=jury_adapters,
640	                on_plan_ready=on_plan_ready,
641	                cancel_event=run.cancel_event,
642	                fallback_adapter=fallback_adapter,
643	                leaf_adapters=leaf_adapters,
644	                mid_adapters=mid_adapters,
645	                root_adapters=root_adapters,
646	                mid_jury_adapters=mid_jury_adapters,
647	                root_jury_adapters=root_jury_adapters,
648	            )
649	            result = engine.run(run.goal)
650	            run.result = result
651	            run.status = "cancelled" if run.cancel_event.is_set() else "done"
652	        except Exception as exc:
653	            run.status = "error"
654	            run.error = str(exc)
655	        finally:
656	            run.completed_at = time.time()
657	            run.emit(
658	                {
659	                    "event": "run_done",
660	                    "status": run.status,
661	                    "run_id": run.run_id,
662	                    "error": run.error,
663	                    "result": run.result,
664	                }
665	            )
666	
667	    async def stream_events(self, run: RunState):
668	        """Async generator that yields all events for a run.
669	
670	        First replays already-completed events from the in-memory list, then
671	        drains the live queue until ``run_done`` is emitted.
672	        """
673	        sent = 0
674	        for event in run.events:
675	            yield event
676	            sent += 1
677	        # Drain already-replayed events from the queue to avoid duplicates
678	        from queue import Empty
679	        for _ in range(sent):
680	            try:
681	                run.queue.get_nowait()
682	            except Empty:
683	                break
684	        while True:
685	            event = await asyncio.to_thread(run.queue.get)
686	            yield event
687	            if event.get("event") == "run_done":
688	                break
689

---

## Subagent Output

(Bash completed with no output)

---

## Subagent Output

369:  } catch {
389:  } catch {
611:      .catch(() => {})
621:        .catch(() => { if (!cancelled) setBackendStatus("offline") })
635:    } catch {
647:    } catch {
1109:      } catch {}
1192:    } catch (err) {
1203:    await fetch(`${API_BASE}/api/run/${runId}/cancel`, { method: "POST", headers: authHeaders(runToken) }).catch(() => {})
1232:        } catch {}
1344:      } catch (err) {
1399:    } catch {
1457:        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` })) as { detail?: string }
1519:    } catch (err) {
1605:    } catch {
1623:    } catch {
1908:    }).catch(() => {})

---

## Claude

I can see the pattern clearly now:
- Backend has **no `logging`** calls at all — exceptions are silently swallowed or set in `run.error`
- Frontend uses bare `catch {}` blocks everywhere — no `console.error` either
- Our new pipeline code follows the same silent pattern

The user wants errors going to **logs** (`console.error` frontend, Python `logging` backend) — not swallowed, and not popped up in the UI. Let me fix all three layers.

First, backend logging:

---

## Subagent Output

19	import asyncio
20	import os
21	import secrets
22	import threading
23	import time
24	import uuid
25	from dataclasses import dataclass, field
26	from queue import Queue
27	from typing import Any, Dict, List, Optional
28	
29	from raf.core.deps import DependencyError, validate_plan
30	from raf.core.engine import RafEngine
31	from raf.core.trace import TraceLogger
32	from raf.llm.mock_adapter import MockAdapter
33	from raf.schemas import RafConfig

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\run_manager.py has been updated successfully.

---

## Claude

Now add `logger.exception` to the engine's top-level catch, the fallback adapter silent catch, and the fork goal build:

---

## Subagent Output

612	            fb_model = getattr(config, "fallback_model", "") or None
613	            if fb_provider:
614	                try:
615	                    fallback_adapter = self._build_adapter(fb_provider, fb_model, key)
616	                except Exception:
617	                    pass  # missing key — run without fallback
618	
619	            # ── Tier adapter lists for depth-based model routing ───────────────
620	            # When tier agents are provided: leaf → workers, mid → planners,
621	            # root → referee/analysis.  When empty, each tier falls back to the
622	            # flat consortium/jury adapters inside RafEngine.
623	            #

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\run_manager.py has been updated successfully.

---

## Claude

Now the main run exception handler:

---

## Subagent Output

652	            result = engine.run(run.goal)
653	            run.result = result
654	            run.status = "cancelled" if run.cancel_event.is_set() else "done"
655	        except Exception as exc:
656	            run.status = "error"
657	            run.error = str(exc)
658	        finally:
659	            run.completed_at = time.time()
660	            run.emit(
661	                {
662	                    "event": "run_done",
663	                    "status": run.status,
664	                    "run_id": run.run_id,
665	                    "error": run.error,
666	                    "result": run.result,
667	                }

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\run_manager.py has been updated successfully.

---

## Claude

Now log warnings for unexpected situations in `fork_run`:

---

## Subagent Output

534	        Returns None (→ HTTP 404) if node_id is not found in parent events.
535	        """
536	        enriched_goal = self._build_fork_goal(
537	            parent_state.events, node_id, override_goal
538	        )
539	        if enriched_goal is None:
540	            return None
541	
542	        # Start from the parent's config and layer the fork-specific overrides
543	        # on top. This way any settings the parent had (timeouts, domain, etc.)

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\run_manager.py has been updated successfully.

---

## Claude

Now the frontend — add `console.error` to all the new pipeline catch blocks without surfacing anything to the UI:

---

## Subagent Output

1213	  const waitForRunDone = (stepRunId: string, stepToken: string): Promise<string | undefined> =>
1214	    new Promise((resolve, reject) => {
1215	      let settled = false
1216	      const settle = (fn: () => void) => { if (!settled) { settled = true; fn() } }
1217	      const wsUrl = API_BASE.replace(/^http/, "ws") + `/api/stream/${stepRunId}?token=${encodeURIComponent(stepToken)}`
1218	      const ws = new WebSocket(wsUrl)
1219	      ws.onmessage = (msg) => {
1220	        // Honour a cooperative cancel requested from the UI
1221	        if (pipelineCancelRef.current) {
1222	          ws.close()
1223	          settle(() => reject(new Error("cancelled")))
1224	          return
1225	        }
1226	        try {
1227	          const ev: RafEvent = JSON.parse(msg.data)
1228	          if (ev.event === "run_done") {
1229	            ws.close()
1230	            settle(() => resolve((ev as any).result?.output))
1231	          }
1232	        } catch {}
1233	      }
1234	      ws.onerror = () => settle(() => reject(new Error("WebSocket connection failed")))
1235	      // Only reject on close if not already settled (e.g. connection dropped mid-run)
1236	      ws.onclose = () => settle(() => reject(new Error("Connection closed before run completed")))
1237	    })
1238	
1239	  /**
1240	   * Run the pipeline sequentially. Each step becomes an independent /api/run
1241	   * call and a session entry in the sidebar. Steps run in the background; the
1242	   * main run's graph/events are left untouched.
1243	   *
1244	   * {{output}} in a step's goal is replaced with the previous step's output
1245	   * before the run starts. If a step fails, the pipeline stops at that step.
1246	   */
1247	  const runPipeline = async () => {

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Now add logging to the `runPipeline` catch block:

---

## Subagent Output

1348	          next[i] = { ...next[i], status: "done", output }
1349	          return next
1350	        })
1351	
1352	      } catch (err) {
1353	        const errMsg = String(err)
1354	        const isCancelled = errMsg.includes("cancelled")
1355	        setPipelineResults(prev => {
1356	          const next = [...prev]
1357	          if (next[i]) next[i] = { ...next[i], status: isCancelled ? "cancelled" : "error" }
1358	          return next
1359	        })
1360	        break  // stop the pipeline on any error or cancellation
1361	      }
1362	    }
1363	
1364	    setPipelineRunning(false)
1365	    setPipelineStepIdx(-1)
1366	  }
1367	
1368	  /** Signal the running pipeline to stop after the current step finishes. */
1369	  const cancelPipeline = () => { pipelineCancelRef.current = true }
1370	
1371	  /**
1372	   * Replay a completed pipeline step's events into the main viewport,

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Now `viewPipelineStep`:

---

## Subagent Output

1402	      setRunId(result.runId)
1403	      setRunToken(result.runToken)
1404	      setRunStatus((stData?.status as typeof runStatus) || "done")
1405	      setGoal(result.goal)
1406	      runStartRef.current = replayEvents.find(ev => ev.timestamp)?.timestamp
1407	        ? replayEvents.find(ev => ev.timestamp)!.timestamp! * 1000
1408	        : null
1409	
1410	      replayEvents.forEach(ev => processEvent(ev))
1411	      setCenterTab("timeline")
1412	      setWorkPanelOpen(true)
1413	    } catch {
1414	      // silently ignore — step may have been evicted from server memory
1415	    }
1416	  }

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Also fix the one silent `catch {}` inside `waitForRunDone` where a malformed message could be dropped without trace:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Final type-check:

---

## Subagent Output

(Bash completed with no output)

---

## Claude

Clean. Here's a precise summary of what changed and why:

---

**Backend (`run_manager.py`):**
- Added `import logging` + `logger = logging.getLogger(__name__)` — the standard Python pattern; FastAPI/uvicorn will pick this up automatically in its log output
- `_execute` catch block: added `logger.exception(...)` — logs the full stack trace to server output. The string `run.error = str(exc)` still flows to the client via `run_done`, but that's just the message, never the traceback
- Fallback adapter build: changed `pass` → `logger.debug(...)` — previously completely invisible; now visible at debug level without being alarming
- `fork_run`: added `logger.warning(...)` when a node_id isn't found — helps diagnose "why did the fork return 404" without any user-facing change

**Frontend (`App.tsx`):**
- `waitForRunDone` message parse error: was bare `catch {}` → now `console.error("[pipeline] Failed to parse...")`
- `waitForRunDone` WebSocket error/close: now logs run ID and close code. The `!e.wasClean` check means a normal server-initiated close (after `run_done`) doesn't produce noise
- `runPipeline` step catch: logs full error with step number. UI still only shows the ✕ status icon — users see "step failed", developers see why
- `viewPipelineStep`: was `// silently ignore` → now `console.error("[pipeline] viewPipelineStep failed...")`

All `[pipeline]` prefixed so they're easy to filter in the browser console.

---

## You

does the logging also consider all  the other parts and errros as a whole

---

## Claude

Let me do a full audit across the entire codebase, not just the new code.

---

## Subagent Output

API Error: Unable to connect to API (FailedToOpenSocket)

---

## Claude

Let me do the audit directly.

---

## Subagent Output

25:except ImportError:
274:    except ValueError as exc:
348:    except WebSocketDisconnect:

---

## Subagent Output

150:        except DependencyError as exc:
620:                except Exception as exc:
659:        except Exception as exc:
664:            logger.exception("Run %s failed: %s", run.run_id, exc)
692:            except Empty:

---

## Subagent Output

369:  } catch {
389:  } catch {
611:      .catch(() => {})
621:        .catch(() => { if (!cancelled) setBackendStatus("offline") })
635:    } catch {
647:    } catch {
1109:      } catch {}
1192:    } catch (err) {
1203:    await fetch(`${API_BASE}/api/run/${runId}/cancel`, { method: "POST", headers: authHeaders(runToken) }).catch(() => {})
1232:        } catch (parseErr) {
1354:      } catch (err) {
1415:    } catch (err) {
1475:        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` })) as { detail?: string }
1537:    } catch (err) {
1623:    } catch {
1641:    } catch {
1926:    }).catch(() => {})

---

## Claude

Now let me read each one in context to understand what it does:

---

## Subagent Output

365	    const raw = window.localStorage.getItem(SESSION_STORAGE_KEY)
366	    if (!raw) return []
367	    const parsed = JSON.parse(raw)
368	    return Array.isArray(parsed) ? parsed.slice(0, 20) : []
369	  } catch {
370	    return []
371	  }
372	}

---

## Subagent Output

383	
384	// ── ExpandModal ───────────────────────────────────────────────────────────────
385	function tryPrettyJson(text: string): string {
386	  try {
387	    const parsed = JSON.parse(text)
388	    return JSON.stringify(parsed, null, 2)
389	  } catch {
390	    return text
391	  }
392	}

---

## Subagent Output

607	        setAvailableProviders(d.available || ["mock"])
608	        if (d.defaults?.provider) setProvider(d.defaults.provider)
609	        if (d.defaults?.model) setModel(d.defaults.model)
610	      })
611	      .catch(() => {})
612	  }, [])
613	
614	  useEffect(() => {
615	    let cancelled = false
616	    const check = () => {
617	      const controller = new AbortController()
618	      const timeout = window.setTimeout(() => controller.abort(), 2500)
619	      fetch(`${API_BASE}/api/health`, { signal: controller.signal })
620	        .then(r => { if (!cancelled) setBackendStatus(r.ok ? "connected" : "offline") })
621	        .catch(() => { if (!cancelled) setBackendStatus("offline") })
622	        .finally(() => window.clearTimeout(timeout))
623	    }
624	    check()
625	    const timer = window.setInterval(check, 10000)
626	    return () => { cancelled = true; window.clearInterval(timer) }
627	  }, [])
628	
629	  const refreshServerRuns = useCallback(async () => {
630	    try {
631	      const res = await fetch(`${API_BASE}/api/runs`)
632	      if (!res.ok) return
633	      const data = await res.json() as { runs?: ServerRunSummary[] }
634	      setServerRuns(data.runs || [])
635	    } catch {
636	      setServerRuns([])
637	    }
638	  }, [])
639	
640	  useEffect(() => {
641	    if (backendStatus === "connected") refreshServerRuns()
642	  }, [backendStatus, refreshServerRuns])
643	
644	  useEffect(() => {
645	    try {
646	      window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessions.slice(0, 20)))

---

## Subagent Output

644	  useEffect(() => {
645	    try {
646	      window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessions.slice(0, 20)))
647	    } catch {
648	      // Storage is best-effort; active runs should not depend on it.
649	    }
650	  }, [sessions])
651	
652	  useEffect(() => {
653	    if (!multiModel) return

---

## Subagent Output

1105	      try {
1106	        const ev: RafEvent = JSON.parse(msg.data)
1107	        if (ev.event === "run_started" && !runStartRef.current) runStartRef.current = Date.now()
1108	        processEvent(ev)
1109	      } catch {}
1110	    }
1111	    ws.onclose = () => {
1112	      if (!isRunningRef.current) return
1113	      const attempts = reconnectAttemptsRef.current
1114	      if (attempts >= 6) return

---

## Subagent Output

1186	      if (!res.ok) throw new Error(`Server error ${res.status}`)
1187	      const data = await res.json() as { run_id: string; access_token?: string }
1188	      if (!data.access_token) throw new Error("Server did not return a run access token")
1189	      setRunId(data.run_id)
1190	      setRunToken(data.access_token)
1191	      connectWs(data.run_id, data.access_token)
1192	    } catch (err) {
1193	      setRunStatus("error")
1194	      setEvents([{ event: "run_done", error: String(err) }])
1195	      isRunningRef.current = false
1196	    }
1197	  }
1198	
1199	  const cancelRun = async () => {
1200	    if (!runId) return
1201	    // Keep isRunningRef=true so reconnect can still fire and receive the
1202	    // authoritative run_done { status: "cancelled" } from the server.
1203	    await fetch(`${API_BASE}/api/run/${runId}/cancel`, { method: "POST", headers: authHeaders(runToken) }).catch(() => {})
1204	  }
1205

---

## Subagent Output

1530	      // normal startRun uses, so all event processing is identical.
1531	      connectWs(data.run_id, data.access_token)
1532	
1533	      // Close the fork panel
1534	      setForkGoalOverride("")
1535	      setForkError(null)
1536	
1537	    } catch (err) {
1538	      setForkError(String(err))
1539	    } finally {
1540	      setForkLoading(false)
1541	    }
1542	  }
1543	
1544	  const updateConsortiumSlot = (index: number, patch: Partial<AgentSlot>) => {

---

## Subagent Output

1618	        : null
1619	
1620	      replayEvents.forEach(ev => processEvent(ev))
1621	      setCenterTab("timeline")
1622	      setWorkPanelOpen(true)
1623	    } catch {
1624	      setRunStatus("error")
1625	    }
1626	  }
1627	
1628	  // Fetch freshest server state before exporting; falls back to local state on error
1629	  const fetchFreshExportData = async (): Promise<{ freshEvents: RafEvent[]; freshResult: string | null; freshStatus: string }> => {
1630	    if (!runId) return { freshEvents: events, freshResult: runResult, freshStatus: runStatus }
1631	    try {
1632	      const [evRes, stRes] = await Promise.all([
1633	        fetch(`${API_BASE}/api/run/${runId}/events`, { headers: authHeaders(runToken) }),
1634	        fetch(`${API_BASE}/api/run/${runId}`, { headers: authHeaders(runToken) }),
1635	      ])
1636	      const freshEvents: RafEvent[] = evRes.ok ? ((await evRes.json()) as { events?: RafEvent[] }).events || events : events
1637	      const stData = stRes.ok ? await stRes.json() as { status?: string; result?: { output?: string } | null } : null
1638	      const freshResult = stData?.result?.output ?? runResult
1639	      const freshStatus = stData?.status ?? runStatus
1640	      return { freshEvents, freshResult, freshStatus }
1641	    } catch {
1642	      return { freshEvents: events, freshResult: runResult, freshStatus: runStatus }
1643	    }
1644	  }
1645	
1646	  // Compute export completeness metadata for both JSON and PDF
1647	  const buildExportMeta = (evList: RafEvent[], status: string) => {

---

## Subagent Output

1920	
1921	  const approvePlan = async () => {
1922	    if (!pendingPlan || !runId) return
1923	    await fetch(`${API_BASE}/api/run/${runId}/approve_plan`, {
1924	      method: "POST", headers: authHeaders(runToken, true),
1925	      body: JSON.stringify({ node_id: pendingPlan.nodeId, children: pendingPlan.children }),
1926	    }).catch(() => {})
1927	    setPendingPlan(null)
1928	  }
1929	
1930	  const filteredEvents = events.filter(ev => {
1931	    if (timelineFilter === "all") return true

---

## Claude

Now let me also check `main.py` context on each of its catches:

---

## Subagent Output

20	_ROOT = Path(__file__).parent.parent
21	try:
22	    from dotenv import load_dotenv
23	    for _env_path in [_ROOT / "raf" / ".env", _ROOT / ".env"]:
24	        load_dotenv(_env_path, override=False)
25	except ImportError:
26	    # python-dotenv not installed — fall back to simple parser.
27	    # Handles: KEY=value, KEY="value", KEY='value', blank lines, # comments.
28	    # Does NOT handle: multiline values, export KEY=value, values containing #.
29	    for _env_path in [_ROOT / "raf" / ".env", _ROOT / ".env"]:
30	        if _env_path.exists():
31	            for _line in _env_path.read_text(encoding="utf-8").splitlines():
32	                _line = _line.strip()
33	                if not _line or _line.startswith("#") or "=" not in _line:
34	                    continue

---

## Subagent Output

268	@app.post("/api/run/{run_id}/approve_plan")
269	def approve_plan(run_id: str, body: ApprovePlanRequest, x_run_token: str | None = Header(default=None)) -> Dict[str, Any]:
270	    """Unblock a run waiting for plan approval (with optionally edited children)."""
271	    run_state = _require_run_token(run_id, x_run_token)
272	    try:
273	        run_state.approve_plan(body.node_id, body.children)
274	    except ValueError as exc:
275	        return {"ok": False, "error": str(exc)}
276	    return {"ok": True}
277	
278	
279	@app.post("/api/run/{run_id}/cancel")
280	def cancel_run(run_id: str, x_run_token: str | None = Header(default=None)) -> Dict[str, Any]:
281	    """Signal a running run to stop cooperatively."""
282	    _require_run_token(run_id, x_run_token)

---

## Subagent Output

335	@app.websocket("/api/stream/{run_id}")
336	async def stream(run_id: str, websocket: WebSocket) -> None:
337	    token = websocket.query_params.get("token")
338	    run_state = manager.get(run_id)
339	    if not run_state or not token or token != run_state.access_token:
340	        await websocket.accept()
341	        await websocket.send_json({"event": "error", "message": "invalid run token"})
342	        await websocket.close(code=1008)
343	        return
344	    await websocket.accept()
345	    try:
346	        async for event in manager.stream_events(run_state):
347	            await websocket.send_json(event)
348	    except WebSocketDisconnect:
349	        return
350

---

## Subagent Output

(Bash completed with no output)

---

## Subagent Output

146	        """
147	        plan = {"children": children}
148	        try:
149	            validate_plan(plan, max_children=self.max_children_per_plan)
150	        except DependencyError as exc:
151	            raise ValueError(f"Invalid plan: {exc}") from exc
152	        existing = self._approved_plans.get(node_id, {})
153	        self._approved_plans[node_id] = {**existing, "children": children}

---

## Claude

Good. I now have a complete picture. Let me map every catch block:

**Backend `run_manager.py`** — all covered after our earlier fixes  
**Backend `main.py`** — no `logging` at all; `WebSocketDisconnect` and `ImportError` are silent  
**Frontend `App.tsx`** — 8 silent swallows that should have `console.error`/`console.warn`

Let me fix them all systematically:

---

## Subagent Output

1	import os
2	from pathlib import Path
3	from typing import Any, Dict, List, Optional
4	
5	from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
6	from fastapi.middleware.cors import CORSMiddleware
7	from pydantic import BaseModel
8	
9	from server.run_manager import RunManager
10	
11	# ⚠ LOCAL DEV ONLY — this server has no authentication.
12	# Do not expose port 8001 on a shared/public network: any caller can start
13	# LLM runs (which may cost real API money) or read run history.
14	# Before deploying, add an API key check (e.g. X-Api-Key header) to all
15	# POST endpoints and restrict allow_origins to your actual frontend origin.
16	
17	# Load .env files at server startup using paths relative to this file's location
18	# so the server finds them regardless of the working directory.
19	# Both files are loaded (raf/.env first, then .env); first value wins (override=False).
20	_ROOT = Path(__file__).parent.parent

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\main.py has been updated successfully.

---

## Claude

Now log the dotenv `ImportError` (it's a setup signal worth knowing about) and the `WebSocketDisconnect`:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\main.py has been updated successfully.

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\server\main.py has been updated successfully.

---

## Claude

Now all the frontend gaps. Starting with the main WebSocket message parse error (line ~1109) — this is the most critical silent swallow:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

`loadStoredSessions` — corrupted localStorage should warn, not silently return empty:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

`/api/models` silent failure on mount:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

`refreshServerRuns` and `cancelRun` and `approvePlan`:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

`startRun` catch — it already sets user-visible error state, but should also log:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

`forkRun` catch — sets user-visible `forkError`, also needs a log:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

`replayServerRun` — silently sets error status with no log:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

`fetchFreshExportData` — falls back silently when export fetch fails:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Final type-check across everything:

---

## Subagent Output

(Bash completed with no output)

---

## Claude

Clean. Here's the full picture of every catch block and what it now does:

---

**Backend `main.py`** (was missing logging entirely)
| Location | Before | After |
|---|---|---|
| `ImportError` (dotenv fallback) | silent | `logger.debug(...)` |
| `except WebSocketDisconnect` | silent `return` | `logger.debug("client disconnected...")` |
| `except ValueError` in `approve_plan` | returns `{"ok": False}` to caller | unchanged — this is controlled user feedback, not an error |

**Backend `run_manager.py`** (already fixed earlier, noted for completeness)
| Location | Status |
|---|---|
| `_execute` main catch | `logger.exception(...)` — full traceback to server log |
| fallback adapter catch | `logger.debug(...)` |
| `fork_run` node-not-found | `logger.warning(...)` |
| `except Empty` in stream drain | unchanged — normal queue behaviour, not an error |

**Frontend `App.tsx`** — every silent swallow now has a prefixed log:
| Location | Prefix | Level |
|---|---|---|
| `loadStoredSessions` | `[sessions]` | `warn` |
| `/api/models` fetch on mount | `[models]` | `warn` |
| `refreshServerRuns` | `[runs]` | `warn` |
| `startRun` | `[run]` | `error` |
| `cancelRun` | `[run]` | `warn` |
| main WebSocket message parse | `[ws]` | `error` |
| `forkRun` | `[fork]` | `error` |
| `replayServerRun` | `[replay]` | `error` |
| `fetchFreshExportData` | `[export]` | `warn` |
| `approvePlan` | `[plan]` | `warn` |
| `waitForRunDone` WS errors | `[pipeline]` | `error` |
| `runPipeline` step failures | `[pipeline]` | `error` |
| `viewPipelineStep` | `[pipeline]` | `error` |

The two intentional silent catches that stay untouched:
- `tryPrettyJson` — `JSON.parse` failing on non-JSON input is the expected path, not an error
- `localStorage.setItem` — storage is explicitly best-effort; the comment in the code explains why

---

## You

ok this is good now tell me what you have done and where we are now

---

## Claude

Here's a full picture of everything done in this session.

---

## What was built

### Feature 1: Run Forking

Lets you click any completed node in the graph and branch from that exact point into a fully independent new run. The original run is never touched.

**Backend (`server/run_manager.py`):**
- `_build_fork_goal()` — walks the parent run's event log, collects up to 5 ancestor goals (shallowest-first, root → parent), attaches the node's prior output if it had one, and assembles an enriched goal string
- `fork_run()` — clones the parent's provider/model/agent config, applies cost overrides (consortium size, jury size, node cap), creates a fresh independent run
- `RunState.fork_source` field for lineage tracking

**Backend (`server/main.py`):**
- `ForkRequest` model with `node_id`, optional `goal` override, `consortium_size`, `jury_size`, `max_nodes_total`
- `POST /api/run/{run_id}/fork` endpoint — validates the run token, calls `fork_run`, returns the new `run_id` + `access_token` + lineage info

**Frontend (`web/src/App.tsx`):**
- `forkRun()` function — posts the fork request, creates a `[fork]` labelled session in the sidebar, resets graph/event state, connects WebSocket to the new run
- Fork panel inside the node inspector (only on completed raf-nodes) with:
  - Live cost estimate that reacts to slider changes
  - Colour-coded caution block (green / yellow / red by call count)
  - Consortium and jury size steppers with parent values shown
  - Goal textarea pre-filled with the node's original goal, editable
  - Fork button showing live call estimate

---

### Feature 2: Goal Chaining / Pipelines

A floating draggable panel (opened from the graph toolbar) that lets you chain multiple RAF goals sequentially. Each step runs as a fully independent `/api/run` call. `{{output}}` in any step's goal is replaced with the previous step's output before that run starts. The pipeline runs in parallel with the active main run — it never replaces the session you're watching.

**New file (`web/src/components/PipelinePanel.tsx`):**
- Exported types: `PipelineStep`, `PipelineStepResult`
- Draggable panel UI: numbered steps, status indicators (● running / ✓ done / ✕ failed), output preview, "View run" button on completed steps, Add/Remove step controls, Run Pipeline / Cancel buttons

**Frontend (`web/src/App.tsx`):**
- `waitForRunDone()` — opens an isolated WebSocket per step, resolves when `run_done` fires, honours the cancel ref, fully separate from the main `wsRef`
- `runPipeline()` — sequential loop: substitutes `{{output}}`, calls `/api/run`, creates a session entry per step, waits for completion, passes output to next step
- `cancelPipeline()` — cooperative cancel via `pipelineCancelRef`
- `viewPipelineStep()` — replays a completed step's events into the main viewport on demand (same as `replayServerRun`)
- Pointer-capture drag handlers matching the existing work panel pattern
- "Pipeline" toolbar button that pulses and shows live step progress while running

---

## What was reviewed and fixed

**Code review pass** found and fixed:
- `run_manager.py line 478` — ancestor sort was `[-5:]` (took deepest 5) instead of `[:5]` (shallowest 5, root → parent). Fork context was being assembled in the wrong order
- `PipelinePanel.tsx` — missing `onPointerCancel` prop; if OS interrupted a drag the panel position ref was never cleared, causing erratic jumps on the next drag
- `App.tsx startPipelinePanelDrag` — missing button-click guard; clicking the close ✕ would capture the pointer before the click fired. Added `if (closest("button")) return`, matching the existing work panel pattern

**Full logging audit** — covered every catch block in the entire codebase:
- **`server/main.py`** — added `logging` module, `logger.debug` on dotenv fallback and WebSocket disconnect
- **`server/run_manager.py`** — `logger.exception` on run failure (full traceback to server log), `logger.debug` on fallback adapter miss, `logger.warning` on fork node-not-found
- **`web/src/App.tsx`** — 10 previously silent swallows now log to the browser console with `[prefix]` labels so they're filterable: `[ws]`, `[run]`, `[fork]`, `[sessions]`, `[models]`, `[runs]`, `[replay]`, `[export]`, `[plan]`, `[pipeline]`. All at the right severity — `console.error` for things that should not happen, `console.warn` for degraded-but-recoverable paths. Nothing new is shown to users in the UI.

---

## Where things stand

The TypeScript compiler passes clean with no errors. The two features are complete and reviewed. The codebase now has consistent error logging across all layers — errors go to server logs and browser console, never as raw exception strings in the UI.

What's left before shipping would be real end-to-end testing with a live provider (OpenRouter) to verify the fork context injection reads well and the pipeline `{{output}}` substitution produces coherent goals.

---

## You

the last feature i want to add is this (  5. Node Replay — re-run a single node without restarting the whole run)

---

## Subagent Output

514	  const [forkConsortiumSize, setForkConsortiumSize] = useState(2)
515	  const [forkJurySize, setForkJurySize] = useState(1)
516	
517	  // Pipeline state — Goal Chaining feature.
518	  // The pipeline panel opens as a floating overlay from the graph toolbar.
519	  // Each step runs as a fully independent RAF run; the pipeline never
520	  // touches the active main run's state (runId, events, graph, etc.).
521	  const [pipelineOpen, setPipelineOpen] = useState(false)
522	  const [pipelinePanelPos, setPipelinePanelPos] = useState({ left: 300, top: 120 })
523	  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>([{ id: "step-1", goal: "" }])
524	  const [pipelineRunning, setPipelineRunning] = useState(false)
525	  const [pipelineStepIdx, setPipelineStepIdx] = useState(-1)
526	  const [pipelineResults, setPipelineResults] = useState<PipelineStepResult[]>([])
527	  // Ref used to cooperatively cancel a running pipeline without async state lag
528	  const pipelineCancelRef = useRef(false)
529	  const pipelinePanelDragRef = useRef<{ x: number; y: number; left: number; top: number } | null>(null)
530	
531	  // physics
532	  const [physics, setPhysics] = useState<PhysicsParams>({ ...DEFAULT_PHYSICS })
533

---

## Claude

Before writing code, let me explain the approach so we're aligned, then implement.

**What "Node Replay" means here:**
- Re-run a single node's goal as a brand-new isolated execution, without touching the current session
- Runs in the **background** (like the pipeline) — your main run's graph stays visible while it executes
- When done, a "View result" button appears in the inspector to load it
- Shows on **all completed nodes** — including failed ones (where it acts as a "Retry")
- Capped at 1 node (`max_nodes_total: 1`) so it stays a single atomic execution. For anything bigger, Fork exists

The distinction from Fork is intentional: Fork is "explore a different direction from this point with ancestor context." Replay is "run this exact task again, clean, and see if you get a better result."

No backend changes needed — it uses the existing `/api/run` endpoint.

Let me read the exact spots I need to edit:

---

## Subagent Output

509:  const [forkGoalOverride, setForkGoalOverride] = useState("")
511:  const [forkError, setForkError] = useState<string | null>(null)
514:  const [forkConsortiumSize, setForkConsortiumSize] = useState(2)
515:  const [forkJurySize, setForkJurySize] = useState(1)
1456:      setForkError("No active run to fork from.")
1460:    setForkError(null)
1540:      setForkGoalOverride("")
1541:      setForkError(null)
1545:      setForkError(String(err))
3107:            onNodeClick={n => {
3114:                setForkGoalOverride(n.goal || "")
3115:                setForkConsortiumSize(2)
3116:                setForkJurySize(1)
3118:                setForkGoalOverride("")
3120:              setForkError(null)
3286:                      {/* ── Fork panel — only shown on completed nodes ───────
3392:                                onChange={setForkConsortiumSize}
3399:                                onChange={setForkJurySize}
3410:                                onChange={e => setForkGoalOverride(e.target.value)}

---

## Subagent Output

3420	                                {forkError}
3421	                              </p>
3422	                            )}
3423	
3424	                            <button
3425	                              onClick={() => forkRun(selectedNode.id, selectedNode.goal || "")}
3426	                              disabled={forkLoading || !forkGoalOverride.trim()}
3427	                              className="w-full rounded-md border border-primary/50 bg-primary/15 px-3 py-1.5 text-xs font-medium text-primary
3428	                                         hover:bg-primary/25 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
3429	                            >
3430	                              {forkLoading ? "Forking…" : `Fork · ~${minCalls === maxCalls ? minCalls : `${minCalls}–${maxCalls}`} calls`}
3431	                            </button>
3432	                          </div>
3433	                        )
3434	                      })()}
3435	                    </>
3436	                  )}
3437	
3438	                  {/* ── Consortium-group: list all proposals ────────────── */}
3439	                  {selectedNode.type === "consortium-group" && (
3440	                    <>
3441	                      <div className="flex items-center gap-2 flex-wrap">
3442	                        <p className="text-muted-foreground text-[10px]">Task: <span className="text-foreground font-mono">{selectedNode.task}</span></p>
3443	                        {(inspectorCandidatesEvent as any)?.tier !== undefined && tierBadge((inspectorCandidatesEvent as any).tier)}
3444	                      </div>
3445	                      <p className="text-[10px] uppercase text-muted-foreground">{inspectorCandidates.length} proposals</p>
3446	                      <div className="space-y-2">
3447	                        {inspectorCandidates.map((cand: any, i: number) => {
3448	                          const payload = cand?.payload || cand || {}
3449	                          const fullText = payload.output || payload.mode || payload.plan || JSON.stringify(payload, null, 2)

---

## Claude

Now I have exactly what I need. Let me implement everything:

**1. State variables:**

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

**2. `replayNode` and `viewReplayResult` functions** — add them right after `cancelPipeline`:

---

## Subagent Output

1392-    setPipelineStepIdx(-1)
1393-  }
1394-
1395:  /** Signal the running pipeline to stop after the current step finishes. */
1396-  const cancelPipeline = () => { pipelineCancelRef.current = true }
1397-
1398-  /**

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

**3. Reset replay controls in `onNodeClick`:**

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

**4. Replay panel JSX** — insert right before the `</>` that closes the raf-node inspector block:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Subagent Output

(Bash completed with no output)

---

## Claude

Clean. Let me verify the key parts landed correctly:

---

## Subagent Output

518:  // replayForNodeId links the result back to the node that triggered it so that
520:  const [replayForNodeId, setReplayForNodeId] = useState<string | null>(null)
521:  const [replayStatus, setReplayStatus] = useState<"idle" | "running" | "done" | "error">("idle")
522:  const [replayRunId, setReplayRunId] = useState<string | null>(null)
528:  const replayForNodeIdRef = useRef<string | null>(null)
1411:  const replayNode = async (nodeId: string, nodeGoal: string) => {
1412:    if (!nodeGoal.trim() || replayStatus === "running") return
1416:    replayForNodeIdRef.current = nodeId
1497:              if (replayForNodeIdRef.current === capturedNodeId) {
1522:      if (replayForNodeIdRef.current === nodeId) setReplayStatus("error")
1531:  const viewReplayResult = async () => {
1532:    if (!replayRunId || !replayRunToken) return
1535:        fetch(`${API_BASE}/api/run/${replayRunId}/events`, { headers: authHeaders(replayRunToken) }),
1536:        fetch(`${API_BASE}/api/run/${replayRunId}`, { headers: authHeaders(replayRunToken) }),
1551:      setRunId(replayRunId)
1561:      console.error("[replay] viewReplayResult failed:", err)
3302:              // We intentionally do NOT clear replayStatus/replayRunId here —
3304:              // still show its result. The replayForNodeId check in the panel
3629:                        const thisStatus = replayForNodeId === selectedNode.id ? replayStatus : "idle"
3630:                        const thisOutput = replayForNodeId === selectedNode.id ? replayOutput : null
3671:                                  {isFailed ? "Retry this node" : "Replay this node"}
3715:                                  onClick={() => replayNode(selectedNode.id, selectedNode.goal || "")}
3728:                                  onClick={viewReplayResult}

---

## Claude

Everything is wired up. Here's what was built:

---

**Node Replay — what it does:**

**On a successful node:** shows a neutral "Replay this node" panel at the bottom of the inspector. Re-runs the same goal fresh to see if you get a different or better result.

**On a failed node:** shows an amber "Retry this node" panel — same mechanism but visually distinguished so it's obvious this is the recovery path.

**How it works:**
- Runs entirely in the **background** using an isolated WebSocket — your current session's graph, timeline, and events are completely untouched while it executes
- Capped at 1 node (`max_nodes_total: 1`) — atomic, predictable cost
- `skip_clarify: true` — runs autonomously with no prompts
- Creates a `[replay]` session entry in the sidebar
- Shows live status in the panel: `Running…` → `✓ Done` / `✕ Failed`
- When done, shows a 200-char output preview inline
- "View full result" button loads the replay's full graph and timeline into the main viewport
- A small ↺ reset button returns the panel to idle so you can replay again

**Node-switching safety:** the `replayForNodeId`/`replayForNodeIdRef` pairing ensures that if you click to a different node while a replay is running, the async WebSocket callback only updates state if `replayForNodeIdRef.current` still matches the node that triggered it — so fast node switching never corrupts the panel's state.

---

## You

so how does this now affect the calls and would this affect the future results like lets say the project is running , and i belive this only works on nodes which have been completed , if i rerun it and i like the idea would it affect the child nodes which taken the output from it  and if i like the new answer how would i insert that , would it break the tree or should i just use fork to get through that in that sitation , and even if i do use fork , does the node ( completed node ) pass than from acoenstors also  and also how would the us desplay this also

---

## Claude

These are really important questions about the architecture. Let me answer each one honestly and directly.

---

## How replay affects call count

With defaults (consortium=2, jury=1): **~9 calls**. The engine runs 3 decisions — mode_decide, base_execute, analysis — each costing `consortiumSize + jurySize`. That's it. Predictable and bounded because the 1-node cap prevents it from spawning children regardless of what the task is.

---

## The core limitation you spotted

**Replay cannot feed back into the original tree. Ever.**

Here's why: when you replay a completed node, the original run has already finished that branch. The children already ran using the original node's output. The RAF engine has no mechanism to say "replace node-3's output with this new value and re-propagate downstream." The engine runs once, linearly, in a background thread. It doesn't support mid-run replacement.

So replaying a node gives you a new result in a separate session — but the original tree is frozen. The children in the original run will always show the output they computed against the original answer.

---

## If you like the replay result — your actual options

**Option 1 — Just take the output manually.** Click "View full result", copy the output, use it wherever you need it. The replay session is fully viewable.

**Option 2 — Fork from the parent node.** If the original node's bad output affected its siblings or the merge step, fork from the *parent* (not the node itself). The fork re-runs the parent's full planning+execution cycle with ancestor context, which means the children will be regenerated using whatever the new run produces.

**Option 3 — Fork from the node itself.** Fork the node you replayed, set the goal to something more specific based on what you learned from the replay. The fork gets ancestor context (root → parent chain) plus the node's prior output attached, so it knows what was tried before. You'd be branching from that exact point with your improved framing.

**Option 4 — Pipeline.** Chain a step that builds on the replay's output using `{{output}}`.

---

## Does fork include ancestor context from a completed node?

Yes, fully. When you fork a node, `_build_fork_goal` in `run_manager.py` does this:

1. Finds the node's `node_created` event in the parent run's event log
2. Collects up to 5 ancestor goals at shallower depths, sorted root → parent
3. Attaches the node's prior output (clamped to 1000 chars) so the fork knows what was already attempted
4. Assembles everything as a text prefix before the fork goal

So a fork from node-5 would start its run with something like:

```
[FORK CONTEXT — ancestor tasks completed in parent run]
  - Root goal: design a recommendation system
  - Sub-goal: design the ranking module

[PRIOR OUTPUT for this node in parent run]
The ranking module used collaborative filtering...

[FORK SUB-GOAL]
Design a better ranking module using transformer-based embeddings
```

The fork is fully aware of where it sits in the original tree.

---

## What replay is actually for vs what fork is for

| | Replay | Fork |
|---|---|---|
| **Purpose** | Did this specific task get a good answer? Let me try again clean. | I want to explore a different direction from this point. |
| **Ancestor context** | None — clean re-run | Yes — full root→parent chain |
| **Prior output attached** | No | Yes |
| **Can have children** | No (1-node cap) | Yes |
| **Affects original tree** | No | No (independent run) |
| **When to use** | Node failed, or output was weak | You want to branch and go deeper |

Replay is essentially a quick sanity check — "was that a fluke or is this task genuinely hard?" Fork is for genuine exploration.

---

## The UI as it stands

Right now:
- **Replay panel** appears at the bottom of the node inspector for every completed node (amber styling for failed, neutral for success)
- Status shows live: `Running…` → `✓ Done` / `✕ Failed`
- Output preview (200 chars) appears inline when done
- "View full result" loads the replay graph into the main viewport
- The session appears in the sidebar as `[replay] ...` so you can get back to it later
- A small ↺ button resets the panel so you can replay again

What's **not** shown yet that would be useful: a small indicator dot on the graph node itself showing "a replay exists for this node." That would let you see at a glance which nodes have been retried without opening the inspector for each one. That would be a natural next improvement if you want it.

---

## You

ok good , i like the fact that we have 4 different options if we want to use the reply and fork and now lets add that ui

---

## Claude

Let me read the current replay panel code to write the edits precisely:

---

## Subagent Output

3625	                          background. The current session graph stays untouched.              */}
3626	                      {!selectedNode.active && (() => {
3627	                        // Compute the status that applies to THIS specific node —
3628	                        // guards against stale state from a previously replayed node.
3629	                        const thisStatus = replayForNodeId === selectedNode.id ? replayStatus : "idle"
3630	                        const thisOutput = replayForNodeId === selectedNode.id ? replayOutput : null
3631	                        const isFailed = !selectedNode.success
3632	
3633	                        const perDecision = replayConsortiumSize + replayJurySize
3634	                        // ~3 decisions: mode_decide + base_execute + analysis
3635	                        const estCalls = 3 * perDecision
3636	
3637	                        // +/- stepper — same pattern as fork panel
3638	                        const Stepper = ({
3639	                          label, value, min, max, parentValue, onChange,
3640	                        }: {
3641	                          label: string; value: number; min: number; max: number
3642	                          parentValue: number; onChange: (n: number) => void
3643	                        }) => (
3644	                          <div className="flex items-center justify-between">
3645	                            <div>
3646	                              <span className="text-[10px] text-muted-foreground">{label}</span>
3647	                              <span className="ml-1.5 text-[9px] text-muted-foreground/50">(parent: {parentValue})</span>
3648	                            </div>
3649	                            <div className="flex items-center gap-1.5">
3650	                              <button onClick={() => onChange(Math.max(min, value - 1))} disabled={value <= min || thisStatus === "running"}
3651	                                className="h-5 w-5 rounded border border-border text-muted-foreground hover:text-foreground hover:border-primary/50 disabled:opacity-30 text-xs leading-none">−</button>
3652	                              <span className="w-4 text-center text-xs font-mono tabular-nums">{value}</span>
3653	                              <button onClick={() => onChange(Math.min(max, value + 1))} disabled={value >= max || thisStatus === "running"}
3654	                                className="h-5 w-5 rounded border border-border text-muted-foreground hover:text-foreground hover:border-primary/50 disabled:opacity-30 text-xs leading-none">+</button>
3655	                            </div>
3656	                          </div>
3657	                        )
3658	
3659	                        return (
3660	                          <div className={`rounded-md border p-3 space-y-3 mt-1 ${
3661	                            isFailed
3662	                              ? "border-amber-500/30 bg-amber-500/5"
3663	                              : "border-border/40 bg-muted/10"
3664	                          }`}>
3665	
3666	                            {/* Header */}
3667	                            <div className="flex items-center justify-between">
3668	                              <div className="flex items-center gap-2">
3669	                                <span className="text-sm">↺</span>
3670	                                <span className={`text-[10px] font-semibold uppercase tracking-wider ${isFailed ? "text-amber-400" : "text-muted-foreground"}`}>
3671	                                  {isFailed ? "Retry this node" : "Replay this node"}
3672	                                </span>
3673	                              </div>
3674	                              {/* Live status badge */}
3675	                              {thisStatus === "running" && (
3676	                                <span className="text-[10px] text-blue-400 animate-pulse">Running…</span>
3677	                              )}
3678	                              {thisStatus === "done" && (
3679	                                <span className="text-[10px] text-green-400">✓ Done</span>
3680	                              )}
3681	                              {thisStatus === "error" && (
3682	                                <span className="text-[10px] text-red-400">✕ Failed</span>
3683	                              )}
3684	                            </div>
3685	
3686	                            {/* Description */}
3687	                            <p className="text-[10px] text-muted-foreground leading-relaxed">
3688	                              {isFailed
3689	                                ? "Re-runs this node's goal fresh — useful when a model call failed or the output was poor."
3690	                                : "Re-runs this node's goal as a clean attempt. Runs in the background; your current graph stays visible."}
3691	                            </p>
3692	
3693	                            {/* Agent count controls — hidden when already running */}
3694	                            {thisStatus === "idle" && (
3695	                              <div className="rounded-md border border-border/50 bg-muted/20 p-2 space-y-2">
3696	                                <p className="text-[10px] text-muted-foreground font-medium">
3697	                                  Agent counts · ~{estCalls} calls · 1 node cap
3698	                                </p>
3699	                                <Stepper label="Consortium" value={replayConsortiumSize} min={1} max={6} parentValue={consortiumSize} onChange={setReplayConsortiumSize} />
3700	                                <Stepper label="Jury" value={replayJurySize} min={1} max={4} parentValue={jurySize} onChange={setReplayJurySize} />
3701	                              </div>
3702	                            )}
3703	
3704	                            {/* Output preview when done */}
3705	                            {thisStatus === "done" && thisOutput && (
3706	                              <div className="rounded bg-green-500/10 border border-green-500/20 px-2 py-1.5 text-[10px] text-green-300 font-mono whitespace-pre-wrap">
3707	                                {thisOutput.slice(0, 200)}{thisOutput.length > 200 ? "…" : ""}
3708	                              </div>
3709	                            )}
3710	
3711	                            {/* Action buttons */}
3712	                            <div className="flex gap-2">
3713	                              {(thisStatus === "idle" || thisStatus === "error") && (
3714	                                <button
3715	                                  onClick={() => replayNode(selectedNode.id, selectedNode.goal || "")}
3716	                                  disabled={!selectedNode.goal?.trim()}
3717	                                  className={`flex-1 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
3718	                                    isFailed
3719	                                      ? "border-amber-500/40 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20"
3720	                                      : "border-border/50 bg-muted/20 text-muted-foreground hover:text-foreground hover:border-primary/40"
3721	                                  }`}
3722	                                >
3723	                                  {thisStatus === "error" ? "Retry again" : `${isFailed ? "Retry" : "Replay"} · ~${estCalls} calls`}
3724	                                </button>
3725	                              )}
3726	                              {thisStatus === "done" && (
3727	                                <button
3728	                                  onClick={viewReplayResult}
3729	                                  className="flex-1 rounded-md border border-green-500/40 bg-green-500/10 px-3 py-1.5 text-xs font-medium text-green-400 hover:bg-green-500/20 transition-colors"
3730	                                >
3731	                                  View full result
3732	                                </button>
3733	                              )}
3734	                              {thisStatus === "done" && (
3735	                                <button
3736	                                  onClick={() => { setReplayStatus("idle"); setReplayForNodeId(null) }}
3737	                                  className="rounded-md border border-border/40 px-2 py-1.5 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
3738	                                  title="Reset replay panel"
3739	                                >↺</button>
3740	                              )}
3741	                            </div>
3742	                          </div>
3743	                        )
3744	                      })()}

---

## You

This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion of the conversation.

Summary:
1. Primary Request and Intent:
   The user owns the Recursive Agent Framework (RAF) — a multi-agent orchestration system with a FastAPI backend, React/D3 frontend, Consortium+Jury execution pattern. Over this session they requested:
   - **Feature 2: Goal Chaining / Pipelines** — chain multiple RAF runs sequentially, `{{output}}` placeholder support, runs in parallel with the active main run, floating draggable panel from graph toolbar (no new sidebar tab)
   - **Code review** of all features built so far (fork + pipeline)
   - **Full error handling audit** — errors must go to logs (console.error/console.warn frontend, Python logging backend), NOT shown in the UI as raw strings
   - **Feature 3: Node Replay** — re-run a single completed node without restarting the whole run; runs in background, current session untouched
   - **"What to do with this result" UI** — when replay completes, show 4 actionable options inside the replay panel: Copy output, Fork from here, Go to parent → Fork, Add to pipeline

2. Key Technical Concepts:
   - **PipelinePanel**: Floating draggable panel, sequential step runner, `{{output}}` substitution, `waitForRunDone` isolated WebSocket per step
   - **Pointer-capture drag pattern**: `setPointerCapture`, `onPointerCancel`, button-click guard (`closest("button") return`)
   - **Isolated WebSocket**: Each pipeline step / replay uses its own WebSocket separate from main `wsRef` so the active session's events are never disrupted
   - **replayForNodeIdRef**: Ref-based guard that prevents async WebSocket callbacks from corrupting state when the user switches nodes mid-replay
   - **Replay vs Fork**: Replay = clean re-run, no ancestor context, 1-node cap, background. Fork = branches with root→parent context + prior output, can have children, switches session
   - **`_build_fork_goal`**: Collects up to 5 shallowest ancestors (bug fixed: was `[-5:]` not `[:5:]`), attaches prior output, assembles enriched goal string
   - **Python `logging` module**: `logger = logging.getLogger(__name__)` in both `main.py` and `run_manager.py`
   - **Console prefix pattern**: All frontend log calls prefixed `[module]` (e.g. `[pipeline]`, `[fork]`, `[ws]`, `[replay]`) for filterability
   - **`pipelineCancelRef`**: `useRef(false)` for cooperative cancel checked inside async WebSocket handler

3. Files and Code Sections:

   - **`web/src/components/PipelinePanel.tsx`** (NEW FILE)
     - Exports `PipelineStep`, `PipelineStepResult` types and `PipelinePanel` component
     - Draggable floating panel for goal chaining
     - Props include `onPointerCancel` to clear drag ref on OS gesture interrupt
     - Key types:
     ```typescript
     export type PipelineStep = { id: string; goal: string }
     export type PipelineStepResult = {
       stepId: string; runId: string; runToken: string; sessionId: string
       status: "pending" | "running" | "done" | "error" | "cancelled"
       output?: string; goal: string
     }
     ```
     - Outer div has `onPointerMove`, `onPointerUp`, `onPointerCancel` (for smooth drag even when cursor leaves header)
     - Header div has `onPointerDown` only

   - **`server/run_manager.py`**
     - Added `import logging` and `logger = logging.getLogger(__name__)`
     - Fixed `_build_fork_goal` line 478: `[-5:]` → `[:5]` (was taking 5 deepest ancestors, should be 5 shallowest)
     - Added `logger.exception("Run %s failed: %s", run.run_id, exc)` in `_execute` main catch
     - Changed fallback adapter `except Exception: pass` → `logger.debug("Fallback adapter unavailable for provider %r: %s", fb_provider, exc)`
     - Added `logger.warning("fork_run: node_id %r not found in run %s events", node_id, parent_state.run_id)` when enriched_goal is None

   - **`server/main.py`**
     - Added `import logging` and `logger = logging.getLogger(__name__)`
     - Added `logger.debug("python-dotenv not installed — using built-in .env parser")` on ImportError
     - Added `logger.debug("WebSocket client disconnected from run %s", run_id)` on WebSocketDisconnect

   - **`web/src/App.tsx`** (major additions)
     
     **Imports (lines 6, 20-21):**
     ```typescript
     import { ..., Link2 } from "lucide-react"
     import { PipelinePanel } from "./components/PipelinePanel"
     import type { PipelineStep, PipelineStepResult } from "./components/PipelinePanel"
     ```

     **Pipeline state (after forkJurySize):**
     ```typescript
     const [pipelineOpen, setPipelineOpen] = useState(false)
     const [pipelinePanelPos, setPipelinePanelPos] = useState({ left: 300, top: 120 })
     const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>([{ id: "step-1", goal: "" }])
     const [pipelineRunning, setPipelineRunning] = useState(false)
     const [pipelineStepIdx, setPipelineStepIdx] = useState(-1)
     const [pipelineResults, setPipelineResults] = useState<PipelineStepResult[]>([])
     const pipelineCancelRef = useRef(false)
     const pipelinePanelDragRef = useRef<{ x: number; y: number; left: number; top: number } | null>(null)
     ```

     **Node Replay state (after pipeline state):**
     ```typescript
     const [replayForNodeId, setReplayForNodeId] = useState<string | null>(null)
     const [replayStatus, setReplayStatus] = useState<"idle" | "running" | "done" | "error">("idle")
     const [replayRunId, setReplayRunId] = useState<string | null>(null)
     const [replayRunToken, setReplayRunToken] = useState<string | null>(null)
     const [replayOutput, setReplayOutput] = useState<string | null>(null)
     const [replayConsortiumSize, setReplayConsortiumSize] = useState(2)
     const [replayJurySize, setReplayJurySize] = useState(1)
     const replayForNodeIdRef = useRef<string | null>(null)
     ```

     **`waitForRunDone` function:**
     ```typescript
     const waitForRunDone = (stepRunId: string, stepToken: string): Promise<string | undefined> =>
       new Promise((resolve, reject) => {
         let settled = false
         const settle = (fn: () => void) => { if (!settled) { settled = true; fn() } }
         const wsUrl = API_BASE.replace(/^http/, "ws") + `/api/stream/${stepRunId}?token=${encodeURIComponent(stepToken)}`
         const ws = new WebSocket(wsUrl)
         ws.onmessage = (msg) => {
           if (pipelineCancelRef.current) { ws.close(); settle(() => reject(new Error("cancelled"))); return }
           try {
             const ev: RafEvent = JSON.parse(msg.data)
             if (ev.event === "run_done") { ws.close(); settle(() => resolve((ev as any).result?.output)) }
           } catch (parseErr) { console.error("[pipeline] Failed to parse WebSocket message for run", stepRunId, parseErr) }
         }
         ws.onerror = (e) => { console.error("[pipeline] WebSocket error for run", stepRunId, e); settle(() => reject(new Error("WebSocket connection failed"))) }
         ws.onclose = (e) => {
           if (!e.wasClean) console.error("[pipeline] WebSocket closed unexpectedly for run", stepRunId, "code:", e.code)
           settle(() => reject(new Error("Connection closed before run completed")))
         }
       })
     ```

     **`runPipeline` function** — sequential loop, `{{output}}` substitution with `/\{\{output\}\}/g`, creates `[pipeline:N]` session per step, calls `waitForRunDone`, marks results done/error/cancelled

     **`cancelPipeline`:** `const cancelPipeline = () => { pipelineCancelRef.current = true }`

     **`viewPipelineStep(result)`** — fetches `/api/run/{runId}/events` + `/api/run/{runId}`, replays events into main viewport without clobbering main wsRef

     **Pipeline drag handlers:**
     ```typescript
     const startPipelinePanelDrag = (e: PointerEvent<HTMLDivElement>) => {
       if ((e.target as HTMLElement).closest("button")) return  // button-click guard
       e.currentTarget.setPointerCapture(e.pointerId)
       pipelinePanelDragRef.current = { x: e.clientX, y: e.clientY, ...pipelinePanelPos }
     }
     const movePipelinePanelDrag = (e: PointerEvent<HTMLDivElement>) => {
       if (!pipelinePanelDragRef.current) return
       const { x, y, left, top } = pipelinePanelDragRef.current
       setPipelinePanelPos({ left: left + e.clientX - x, top: top + e.clientY - y })
     }
     const endPipelinePanelDrag = () => { pipelinePanelDragRef.current = null }
     ```

     **`replayNode(nodeId, nodeGoal)` function** — POSTs to `/api/run` with `max_nodes_total: 1`, `skip_clarify: true`, opens isolated WebSocket, guards completion with `replayForNodeIdRef.current === capturedNodeId`, creates `[replay]` session, sets `replayOutput`/`replayStatus`

     **`viewReplayResult()` function** — fetches replay run events, replays into main viewport (same pattern as `replayServerRun`)

     **Replay panel in node inspector** — shown on `!selectedNode.active` (ALL completed nodes):
     - Amber border for failed nodes ("Retry this node")
     - Neutral border for success ("Replay this node")
     - Status badge: Running… / ✓ Done / ✕ Failed
     - Agent count Steppers (consortium 1-6, jury 1-4)
     - 200-char output preview when done
     - "View full result" + ↺ reset buttons

     **Error handling additions across all catch blocks:**
     - `[ws]` main WebSocket parse: `console.error`
     - `[sessions]` localStorage: `console.warn`
     - `[models]` /api/models: `console.warn`
     - `[runs]` refreshServerRuns: `console.warn`
     - `[run]` startRun + cancelRun: `console.error`/`console.warn`
     - `[fork]` forkRun: `console.error`
     - `[replay]` replayServerRun + fetchFreshExportData: `console.error`/`console.warn`
     - `[plan]` approvePlan: `console.warn`
     - `[pipeline]` all pipeline functions: `console.error`

4. Errors and fixes:
   - **Ancestor sort order bug** (`run_manager.py`): `[-5:]` was taking the 5 deepest ancestors instead of shallowest (root→parent). Fixed to `[:5]`.
   - **Missing `onPointerCancel`** (`PipelinePanel.tsx`): If OS interrupted a drag, `pipelinePanelDragRef` was never cleared causing erratic jumps on next drag. Fixed by adding `onPointerCancel` to Props type, outer div, and passing `endPipelinePanelDrag` from App.tsx.
   - **No button-click guard** (`startPipelinePanelDrag`): Clicking the close ✕ in the header would capture the pointer before the click fired. Fixed by adding `if ((e.target as HTMLElement).closest("button")) return` matching existing workPanel pattern.
   - All TypeScript compilations passed clean (`npx tsc --noEmit` returned no output).

5. Problem Solving:
   - **Pipeline parallel to main run**: Solved by using completely separate state management for pipeline runs — `waitForRunDone` uses its own WebSocket, `runPipeline` doesn't touch `runId`/`runToken`/`graphNodes`/`events`
   - **Node switching during replay**: Solved with `replayForNodeIdRef` — async callback checks `replayForNodeIdRef.current === capturedNodeId` before updating state, so switching nodes mid-replay never corrupts the display
   - **`pipelineCancelRef` in `waitForRunDone`**: Confirmed correct — `useRef` persists across renders and the ref value is checked during the async WebSocket handler (not after)
   - **`viewPipelineStep` WebSocket isolation**: Correctly replays events without connecting a new live WebSocket — only fetches from `/api/run/{id}/events` endpoint

6. All user messages:
   - "ok now i want you to continue what we were doing"
   - "ok good now i want you to go back and do a simple review of what we did to make sure we are on the right path"
   - "ok good this is good, i want to make sure that you are also adding the right error handling to be sure remember it is not supposed to show in the frontend but in the logs"
   - "does the logging also consider all the other parts and errors as a whole"
   - "ok good now tell me what you have done and where we are now"
   - "the last feature i want to add is this (5. Node Replay — re-run a single node without restarting the whole run)"
   - "so how does this now affect the calls and would this affect the future results like lets say the project is running, and i believe this only works on nodes which have been completed, if i rerun it and i like the idea would it affect the child nodes which taken the output from it and if i like the new answer how would i insert that, would it break the tree or should i just use fork to get through that in that situation, and even if i do use fork, does the node (completed node) pass than from ancestors also and also how would the us display this also"
   - "ok good, i like the fact that we have 4 different options if we want to use the reply and fork and now lets add that ui"

7. Pending Tasks:
   - **"What to do with this result" UI** — add 4 actionable options inside the replay panel when `thisStatus === "done"`:
     1. **Copy output** → `navigator.clipboard.writeText(thisOutput)`
     2. **Fork from here** → set `forkHighlight` state, call `forkPanelRef.current?.scrollIntoView()` (requires adding `forkHighlight` state, `replayCopied` state, `forkPanelRef` ref, and `ref={forkPanelRef}` + highlight ring to fork panel div)
     3. **Go to parent → Fork** → find parent from `graphLinks` (edge where target === selectedNode.id and edgeType === "parallel"), call `setSelectedNode(parentRafNode)`
     4. **Add to pipeline** → `setPipelineOpen(true)` + add pipeline step pre-filled with replay context prefix

8. Current Work:
   The assistant had just read the current replay panel code (App.tsx lines 3625–3744) to understand the exact structure before writing the "What to do with this result" UI expansion. The replay panel's current done-state shows only "View full result" and ↺ reset buttons. The planned expansion replaces/augments these with the 4-option section.

   The full plan for the pending implementation:
   - **State additions** (after `replayJurySize`):
     ```typescript
     const [forkHighlight, setForkHighlight] = useState(false)
     const [replayCopied, setReplayCopied] = useState(false)
     const forkPanelRef = useRef<HTMLDivElement>(null)
     ```
   - **Fork panel div** — add `ref={forkPanelRef}` and dynamic ring class when `forkHighlight` is true
   - **Replay panel IIFE expansion** — at the top of the IIFE, compute `parentRafNode` from `graphLinks`, define `handleCopyOutput`, `handleForkFromHere`, `handleGoToParent`, `handleAddToPipeline`, then add "Use this result" 2×2 grid section before the action buttons

9. Optional Next Step:
   Complete the "What to do with this result" UI that was being implemented when the summary was requested. The user's exact words: "ok good, i like the fact that we have 4 different options if we want to use the reply and fork and now lets add that ui"

   The work was interrupted immediately after reading the existing replay panel code (lines 3625-3744). The next concrete step is to make three edits to App.tsx:
   1. Add `forkHighlight`, `replayCopied` state and `forkPanelRef` ref to the state section
   2. Add `ref={forkPanelRef}` and conditional ring class to the fork panel container div
   3. Expand the replay panel IIFE to include parent node lookup, 4 action handlers, and the "Use this result" 2×2 option grid inside the `thisStatus === "done"` section

If you need specific details from before compaction (like exact code snippets, error messages, or content you generated), read the full transcript at: C:\Users\dolap\.claude\projects\C--Users-dolap-Desktop-Projects-Recursive-Agent-Framework-Recursive-Agent-Framework-\9ae7dc15-7694-41a9-b8af-bab1cc84b796.jsonl
Continue the conversation from where it left off without asking the user any further questions. Resume directly — do not acknowledge the summary, do not recap what was happening, do not preface with "I'll continue" or similar. Pick up the last task as if the break never happened.

---

## Claude

Let me read the relevant sections of App.tsx to make the precise edits needed.

---

## Subagent Output

1	import { useEffect, useRef, useState, useCallback } from "react"
2	import Landing from "./Landing"
3	import type { PointerEvent } from "react"
4	import { motion, AnimatePresence } from "framer-motion"
5	import DOMPurify from "dompurify"
6	import { Zap, Network, Play, Square, Clock, Vote, FileText, Plus, Download, ZoomIn, ZoomOut, RotateCcw, History, SlidersHorizontal, Home, Link2 } from "lucide-react"
7	import { Button } from "./components/ui/button"
8	import { Badge } from "./components/ui/badge"
9	import { ScrollArea } from "./components/ui/scroll-area"
10	import { Separator } from "./components/ui/separator"
11	import { Slider } from "./components/ui/slider"
12	import { Switch } from "./components/ui/switch"
13	import { Input } from "./components/ui/input"
14	import { Textarea } from "./components/ui/textarea"
15	import { Select } from "./components/ui/select"
16	import { Tabs, TabsList, TabsTrigger, TabsContent } from "./components/ui/tabs"
17	import { Card, CardContent } from "./components/ui/card"
18	import { ExecutionGraph, type GraphNode, type GraphEdge, type PhysicsParams, DEFAULT_PHYSICS } from "./components/ExecutionGraph"
19	import { PhysicsPanel } from "./components/PhysicsPanel"
20	import { PipelinePanel } from "./components/PipelinePanel"
21	import type { PipelineStep, PipelineStepResult } from "./components/PipelinePanel"
22	
23	// ── types ─────────────────────────────────────────────────────────────────────
24	
25	type RafEvent = {
26	  event?: string; status?: string; node_id?: string; parent_id?: string | null
27	  depth?: number; goal?: string; output?: string; mode?: string; confidence?: number
28	  timestamp?: number; run_id?: string; error?: string; task?: string
29	  candidates?: unknown; options?: unknown; votes?: unknown; winner_id?: string
30	  children?: ChildSpec[]; result?: { output: string; metadata: { mode: string; questions?: string[]; confidence?: number } }
31	  question?: string; answer?: string; winner?: string; fast_path?: boolean; reason?: string
32	  domain?: string; required?: string[]; forbidden?: string[]; success_criteria?: string[]
33	  plan_child_id?: string; node_count?: number
34	  // plan recovery
35	  retry?: number; max_retries?: number; replaced_by?: string; plan_attempt?: number
36	  provider?: string; model?: string; role?: string; agent_index?: number
37	  duration_ms?: number; timeout_ms?: number
38	  cause?: "api_error" | "parse_error" | "schema_error"
39	}
40	
41	type ChildSpec = { child_id: string; goal: string; depends_on: string[] }
42	type NodeOutput = { output: string; mode: string; confidence: number; goal?: string }
43	type AgentSlot = { provider: string; model: string }
44	type ModelInfo = { id: string; label?: string; family?: string; tags?: string[] }
45	type SessionConfig = {
46	  provider: string; model: string; juryModel: string
47	  consortiumSize: number; jurySize: number; maxDepth: number; maxParallelChildren: number; maxNodesTotal: number
48	  forceRecursive: boolean; planGovernance: "auto" | "review" | "manual"; planRecovery: "off" | "auto" | "ask"; toolsEnabled: boolean
49	  multiModel: boolean; consortiumSlots: AgentSlot[]; jurySlots: AgentSlot[]
50	  tierRouting: boolean; leafSlots: AgentSlot[]; midSlots: AgentSlot[]; rootSlots: AgentSlot[]
51	  domainOverride: string; systemPrompt: string
52	}
53	type Session = {
54	  id: string; goal: string; provider: string; providerLabel?: string; status: string
55	  ts: number; nodeCount: number; output?: string; domain?: string; runId?: string | null; runToken?: string | null
56	  currentPhase?: string
57	  config?: SessionConfig
58	  events?: RafEvent[]
59	  graphNodes?: GraphNode[]
60	  graphLinks?: GraphEdge[]
61	  nodeOutputs?: Record<string, NodeOutput>
62	  result?: string | null
63	  // Fork lineage — present only when this session was created via the fork action
64	  forkSourceRunId?: string
65	  forkSourceNodeId?: string
66	}
67	type ServerRunSummary = {
68	  run_id: string
69	  goal: string
70	  provider: string
71	  model?: string | null
72	  status: string
73	  started_at: number
74	  completed_at?: number | null
75	  event_count: number
76	}
77	
78	const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8001"
79	const SESSION_STORAGE_KEY = "raf-web-sessions-v1"
80	const API_KEY_STORAGE_KEY = "raf-openrouter-api-key"

---

## Subagent Output

526:  const [replayJurySize, setReplayJurySize] = useState(1)
1431:        jury_size: replayJurySize,
3633:                        const perDecision = replayConsortiumSize + replayJurySize
3700:                                <Stepper label="Jury" value={replayJurySize} min={1} max={4} parentValue={jurySize} onChange={setReplayJurySize} />

---

## Subagent Output

515	  const [forkJurySize, setForkJurySize] = useState(1)
516	
517	  // Node Replay state — tracks a single in-background re-execution of one node.
518	  // replayForNodeId links the result back to the node that triggered it so that
519	  // switching between nodes doesn't corrupt the status shown in the panel.
520	  const [replayForNodeId, setReplayForNodeId] = useState<string | null>(null)
521	  const [replayStatus, setReplayStatus] = useState<"idle" | "running" | "done" | "error">("idle")
522	  const [replayRunId, setReplayRunId] = useState<string | null>(null)
523	  const [replayRunToken, setReplayRunToken] = useState<string | null>(null)
524	  const [replayOutput, setReplayOutput] = useState<string | null>(null)
525	  const [replayConsortiumSize, setReplayConsortiumSize] = useState(2)
526	  const [replayJurySize, setReplayJurySize] = useState(1)
527	  // Ref used inside the async WebSocket callback to guard against node switching
528	  const replayForNodeIdRef = useRef<string | null>(null)
529	
530	  // Pipeline state — Goal Chaining feature.
531	  // The pipeline panel opens as a floating overlay from the graph toolbar.
532	  // Each step runs as a fully independent RAF run; the pipeline never
533	  // touches the active main run's state (runId, events, graph, etc.).
534	  const [pipelineOpen, setPipelineOpen] = useState(false)
535	  const [pipelinePanelPos, setPipelinePanelPos] = useState({ left: 300, top: 120 })
536	  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>([{ id: "step-1", goal: "" }])
537	  const [pipelineRunning, setPipelineRunning] = useState(false)
538	  const [pipelineStepIdx, setPipelineStepIdx] = useState(-1)
539	  const [pipelineResults, setPipelineResults] = useState<PipelineStepResult[]>([])
540	  // Ref used to cooperatively cancel a running pipeline without async state lag
541	  const pipelineCancelRef = useRef(false)
542	  const pipelinePanelDragRef = useRef<{ x: number; y: number; left: number; top: number } | null>(null)
543	
544	  // physics

---

## Subagent Output

65:  forkSourceNodeId?: string
507:  // Fork state — controls the fork panel shown inside the node inspector
1651:          // Agent-count overrides — the user sets these in the fork panel
1704:        forkSourceNodeId: data.fork_source_node_id,
1719:      // Close the fork panel
3637:                        // +/- stepper — same pattern as fork panel

---

## Subagent Output

63:  // Fork lineage — present only when this session was created via the fork action
507:  // Fork state — controls the fork panel shown inside the node inspector
1651:          // Agent-count overrides — the user sets these in the fork panel
1719:      // Close the fork panel
3637:                        // +/- stepper — same pattern as fork panel

---

## Subagent Output

507	  // Fork state — controls the fork panel shown inside the node inspector
508	  // when the user selects a completed raf-node and wants to branch from it.
509	  const [forkGoalOverride, setForkGoalOverride] = useState("")
510	  const [forkLoading, setForkLoading] = useState(false)
511	  const [forkError, setForkError] = useState<string | null>(null)
512	  // Agent count overrides for the fork — default to reduced values so
513	  // exploratory forks don't automatically run at full parent cost.
514	  const [forkConsortiumSize, setForkConsortiumSize] = useState(2)
515	  const [forkJurySize, setForkJurySize] = useState(1)
516	
517	  // Node Replay state — tracks a single in-background re-execution of one node.
518	  // replayForNodeId links the result back to the node that triggered it so that
519	  // switching between nodes doesn't corrupt the status shown in the panel.
520	  const [replayForNodeId, setReplayForNodeId] = useState<string | null>(null)
521	  const [replayStatus, setReplayStatus] = useState<"idle" | "running" | "done" | "error">("idle")

---

## Claude

Now let me find where the fork panel UI is rendered:

---

## Subagent Output

509:  const [forkGoalOverride, setForkGoalOverride] = useState("")
510:  const [forkLoading, setForkLoading] = useState(false)
1650:          goal: forkGoalOverride.trim() !== nodeGoal.trim() ? forkGoalOverride.trim() || null : null,
1673:      const forkLabel = `[fork] ${(forkGoalOverride.trim() || nodeGoal).slice(0, 50)}`
1708:      setGoal(forkGoalOverride.trim() || nodeGoal)
3546:                              <span className="text-[10px] font-semibold text-primary uppercase tracking-wider">Fork from here</span>
3596:                                value={forkGoalOverride}
3613:                              disabled={forkLoading || !forkGoalOverride.trim()}
3617:                              {forkLoading ? "Forking…" : `Fork · ~${minCalls === maxCalls ? minCalls : `${minCalls}–${maxCalls}`} calls`}

---

## Subagent Output

3535	                              >+</button>
3536	                            </div>
3537	                          </div>
3538	                        )
3539	
3540	                        return (
3541	                          <div className="rounded-md border border-primary/30 bg-primary/5 p-3 space-y-3 mt-1">
3542	
3543	                            {/* Header */}
3544	                            <div className="flex items-center gap-2">
3545	                              <span className="text-primary text-sm">⑂</span>
3546	                              <span className="text-[10px] font-semibold text-primary uppercase tracking-wider">Fork from here</span>
3547	                            </div>
3548	
3549	                            {/* ── Caution block ──────────────────────────────── */}
3550	                            <div className={`rounded border ${levelStyle} p-2 space-y-1.5`}>
3551	                              <div className="flex items-center justify-between">
3552	                                <span className="text-[10px] font-semibold uppercase tracking-wider">
3553	                                  {levelIcon} Estimated cost
3554	                                </span>
3555	                                {/* Live call count — updates as the sliders change */}
3556	                                <span className="font-mono text-xs">
3557	                                  {minCalls === maxCalls ? `~${minCalls}` : `~${minCalls}–${maxCalls}`} agent calls
3558	                                </span>
3559	                              </div>
3560	                              <p className="text-[10px] leading-relaxed opacity-90">{typeNote}</p>
3561	                              <ul className="text-[10px] opacity-80 space-y-0.5 list-none pl-0">
3562	                                <li>• Each agent call = one LLM request charged to your API key.</li>
3563	                                <li>• Ancestor context is text-only — no extra calls, just longer prompts.</li>
3564	                                <li>• The fork is capped at 20 nodes total to limit runaway expansion.</li>
3565	                                {level === "high" && (
3566	                                  <li className="font-medium">• Consider reducing consortium or jury size below.</li>
3567	                                )}
3568	                              </ul>
3569	                            </div>
3570	
3571	                            {/* ── Agent-count controls ───────────────────────── */}
3572	                            <div className="rounded-md border border-border/50 bg-muted/20 p-2 space-y-2">
3573	                              <p className="text-[10px] text-muted-foreground font-medium">Agent counts for this fork</p>
3574	                              <Stepper
3575	                                label="Consortium size"
3576	                                value={forkConsortiumSize}
3577	                                min={1} max={6}
3578	                                parentValue={consortiumSize}
3579	                                onChange={setForkConsortiumSize}
3580	                              />
3581	                              <Stepper
3582	                                label="Jury size"
3583	                                value={forkJurySize}
3584	                                min={1} max={4}
3585	                                parentValue={jurySize}
3586	                                onChange={setForkJurySize}
3587	                              />
3588	                            </div>
3589	
3590	                            {/* ── Goal textarea ──────────────────────────────── */}
3591	                            <div className="space-y-1">
3592	                              <p className="text-[10px] text-muted-foreground">
3593	                                Goal <span className="opacity-60">(edit to try a different approach)</span>
3594	                              </p>
3595	                              <textarea
3596	                                value={forkGoalOverride}
3597	                                onChange={e => setForkGoalOverride(e.target.value)}
3598	                                rows={3}
3599	                                placeholder="Edit the goal for this fork…"
3600	                                className="w-full rounded-md border border-border bg-background px-2 py-1.5 text-xs font-mono resize-none focus:outline-none focus:ring-1 focus:ring-primary/50"
3601	                              />
3602	                            </div>
3603	
3604	                            {/* Inline error — shown when the backend rejects the request */}
3605	                            {forkError && (
3606	                              <p className="text-[10px] text-red-400 rounded border border-red-500/30 bg-red-500/10 px-2 py-1">
3607	                                {forkError}
3608	                              </p>
3609	                            )}
3610	
3611	                            <button
3612	                              onClick={() => forkRun(selectedNode.id, selectedNode.goal || "")}
3613	                              disabled={forkLoading || !forkGoalOverride.trim()}
3614	                              className="w-full rounded-md border border-primary/50 bg-primary/15 px-3 py-1.5 text-xs font-medium text-primary
3615	                                         hover:bg-primary/25 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
3616	                            >
3617	                              {forkLoading ? "Forking…" : `Fork · ~${minCalls === maxCalls ? minCalls : `${minCalls}–${maxCalls}`} calls`}
3618	                            </button>
3619	                          </div>
3620	                        )
3621	                      })()}
3622	
3623	                      {/* ── Replay panel — shown on ALL completed nodes (success OR failed) ──
3624	                          Re-runs the node's exact goal as a fresh isolated execution in the
3625	                          background. The current session graph stays untouched.              */}
3626	                      {!selectedNode.active && (() => {
3627	                        // Compute the status that applies to THIS specific node —
3628	                        // guards against stale state from a previously replayed node.
3629	                        const thisStatus = replayForNodeId === selectedNode.id ? replayStatus : "idle"
3630	                        const thisOutput = replayForNodeId === selectedNode.id ? replayOutput : null
3631	                        const isFailed = !selectedNode.success
3632	
3633	                        const perDecision = replayConsortiumSize + replayJurySize
3634	                        // ~3 decisions: mode_decide + base_execute + analysis

---

## Subagent Output

3634	                        // ~3 decisions: mode_decide + base_execute + analysis
3635	                        const estCalls = 3 * perDecision
3636	
3637	                        // +/- stepper — same pattern as fork panel
3638	                        const Stepper = ({
3639	                          label, value, min, max, parentValue, onChange,
3640	                        }: {
3641	                          label: string; value: number; min: number; max: number
3642	                          parentValue: number; onChange: (n: number) => void
3643	                        }) => (
3644	                          <div className="flex items-center justify-between">
3645	                            <div>
3646	                              <span className="text-[10px] text-muted-foreground">{label}</span>
3647	                              <span className="ml-1.5 text-[9px] text-muted-foreground/50">(parent: {parentValue})</span>
3648	                            </div>
3649	                            <div className="flex items-center gap-1.5">
3650	                              <button onClick={() => onChange(Math.max(min, value - 1))} disabled={value <= min || thisStatus === "running"}
3651	                                className="h-5 w-5 rounded border border-border text-muted-foreground hover:text-foreground hover:border-primary/50 disabled:opacity-30 text-xs leading-none">−</button>
3652	                              <span className="w-4 text-center text-xs font-mono tabular-nums">{value}</span>
3653	                              <button onClick={() => onChange(Math.min(max, value + 1))} disabled={value >= max || thisStatus === "running"}
3654	                                className="h-5 w-5 rounded border border-border text-muted-foreground hover:text-foreground hover:border-primary/50 disabled:opacity-30 text-xs leading-none">+</button>
3655	                            </div>
3656	                          </div>
3657	                        )
3658	
3659	                        return (
3660	                          <div className={`rounded-md border p-3 space-y-3 mt-1 ${
3661	                            isFailed
3662	                              ? "border-amber-500/30 bg-amber-500/5"
3663	                              : "border-border/40 bg-muted/10"
3664	                          }`}>
3665	
3666	                            {/* Header */}
3667	                            <div className="flex items-center justify-between">
3668	                              <div className="flex items-center gap-2">
3669	                                <span className="text-sm">↺</span>
3670	                                <span className={`text-[10px] font-semibold uppercase tracking-wider ${isFailed ? "text-amber-400" : "text-muted-foreground"}`}>
3671	                                  {isFailed ? "Retry this node" : "Replay this node"}
3672	                                </span>
3673	                              </div>
3674	                              {/* Live status badge */}
3675	                              {thisStatus === "running" && (
3676	                                <span className="text-[10px] text-blue-400 animate-pulse">Running…</span>
3677	                              )}
3678	                              {thisStatus === "done" && (
3679	                                <span className="text-[10px] text-green-400">✓ Done</span>
3680	                              )}
3681	                              {thisStatus === "error" && (
3682	                                <span className="text-[10px] text-red-400">✕ Failed</span>
3683	                              )}
3684	                            </div>
3685	
3686	                            {/* Description */}
3687	                            <p className="text-[10px] text-muted-foreground leading-relaxed">
3688	                              {isFailed
3689	                                ? "Re-runs this node's goal fresh — useful when a model call failed or the output was poor."
3690	                                : "Re-runs this node's goal as a clean attempt. Runs in the background; your current graph stays visible."}
3691	                            </p>
3692	
3693	                            {/* Agent count controls — hidden when already running */}
3694	                            {thisStatus === "idle" && (
3695	                              <div className="rounded-md border border-border/50 bg-muted/20 p-2 space-y-2">
3696	                                <p className="text-[10px] text-muted-foreground font-medium">
3697	                                  Agent counts · ~{estCalls} calls · 1 node cap
3698	                                </p>
3699	                                <Stepper label="Consortium" value={replayConsortiumSize} min={1} max={6} parentValue={consortiumSize} onChange={setReplayConsortiumSize} />
3700	                                <Stepper label="Jury" value={replayJurySize} min={1} max={4} parentValue={jurySize} onChange={setReplayJurySize} />
3701	                              </div>
3702	                            )}
3703	
3704	                            {/* Output preview when done */}
3705	                            {thisStatus === "done" && thisOutput && (
3706	                              <div className="rounded bg-green-500/10 border border-green-500/20 px-2 py-1.5 text-[10px] text-green-300 font-mono whitespace-pre-wrap">
3707	                                {thisOutput.slice(0, 200)}{thisOutput.length > 200 ? "…" : ""}
3708	                              </div>
3709	                            )}
3710	
3711	                            {/* Action buttons */}
3712	                            <div className="flex gap-2">
3713	                              {(thisStatus === "idle" || thisStatus === "error") && (
3714	                                <button
3715	                                  onClick={() => replayNode(selectedNode.id, selectedNode.goal || "")}
3716	                                  disabled={!selectedNode.goal?.trim()}
3717	                                  className={`flex-1 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
3718	                                    isFailed
3719	                                      ? "border-amber-500/40 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20"
3720	                                      : "border-border/50 bg-muted/20 text-muted-foreground hover:text-foreground hover:border-primary/40"
3721	                                  }`}
3722	                                >
3723	                                  {thisStatus === "error" ? "Retry again" : `${isFailed ? "Retry" : "Replay"} · ~${estCalls} calls`}
3724	                                </button>
3725	                              )}
3726	                              {thisStatus === "done" && (
3727	                                <button
3728	                                  onClick={viewReplayResult}
3729	                                  className="flex-1 rounded-md border border-green-500/40 bg-green-500/10 px-3 py-1.5 text-xs font-medium text-green-400 hover:bg-green-500/20 transition-colors"
3730	                                >
3731	                                  View full result
3732	                                </button>
3733	                              )}
3734	                              {thisStatus === "done" && (
3735	                                <button
3736	                                  onClick={() => { setReplayStatus("idle"); setReplayForNodeId(null) }}
3737	                                  className="rounded-md border border-border/40 px-2 py-1.5 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
3738	                                  title="Reset replay panel"
3739	                                >↺</button>
3740	                              )}
3741	                            </div>
3742	                          </div>
3743	                        )
3744	                      })()}
3745	                    </>
3746	                  )}
3747	
3748	                  {/* ── Consortium-group: list all proposals ────────────── */}
3749	                  {selectedNode.type === "consortium-group" && (
3750	                    <>
3751	                      <div className="flex items-center gap-2 flex-wrap">
3752	                        <p className="text-muted-foreground text-[10px]">Task: <span className="text-foreground font-mono">{selectedNode.task}</span></p>
3753	                        {(inspectorCandidatesEvent as any)?.tier !== undefined && tierBadge((inspectorCandidatesEvent as any).tier)}

---

## Claude

Let me check graphLinks accessibility in this scope and find the selectedNode context:

---

## Subagent Output

60:  graphLinks?: GraphEdge[]
481:  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
549:  const [graphLinks, setGraphLinks] = useState<GraphEdge[]>([])
555:  const graphLinksRef = useRef<GraphEdge[]>([])
687:    const linkSnapshot = cleanGraphLinks(graphLinks)
703:      graphLinks: linkSnapshot,
706:  }, [activeSessionId, provider, runId, runToken, runStatus, nodeCount, runResult, detectedDomain, currentPhase, currentConfig, events, graphNodes, graphLinks, nodeOutputs])
711:    const restoredLinks = cleanGraphLinks(session.graphLinks || [])
742:    graphLinksRef.current = restoredLinks
748:    setSelectedNode(null)
791:      if (!graphLinksRef.current.some(l => l.id === linkId)) {
792:        graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: parentId, target: id, edgeType: "parallel" }]
796:    setGraphLinks([...graphLinksRef.current])
823:        if (!graphLinksRef.current.some(l => l.id === linkId)) {
824:          graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: ev.node_id!, target: groupId, edgeType: "flow" }]
844:          if (!graphLinksRef.current.some(l => l.id === linkId)) {
845:            graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: groupId, target: agentId, edgeType: "parallel" }]
850:      setGraphLinks([...graphLinksRef.current])
870:        if (!graphLinksRef.current.some(l => l.id === linkId)) {
871:          graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: ev.node_id!, target: groupId, edgeType: "flow" }]
893:          if (!graphLinksRef.current.some(l => l.id === linkId)) {
894:            graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: groupId, target: jurorId, edgeType: "parallel" }]
916:      setGraphLinks([...graphLinksRef.current])
929:    const nextLinks = [...graphLinksRef.current]
944:      graphLinksRef.current = nextLinks
945:      setGraphLinks([...graphLinksRef.current])
1041:        if (!graphLinksRef.current.some(l => l.id === linkId)) {
1042:          graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: ev.node_id!, target: failId, edgeType: "flow" as const }]
1045:        setGraphLinks([...graphLinksRef.current])
1073:        if (!graphLinksRef.current.some(l => l.id === flowLinkId)) {

[Showing results with pagination = limit: 30]

---

## Subagent Output

59:  graphNodes?: GraphNode[]
548:  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([])
686:    const graphSnapshot = cleanGraphNodes(graphNodes)
702:      graphNodes: graphSnapshot,
706:  }, [activeSessionId, provider, runId, runToken, runStatus, nodeCount, runResult, detectedDomain, currentPhase, currentConfig, events, graphNodes, graphLinks, nodeOutputs])
710:    const restoredNodes = cleanGraphNodes(session.graphNodes || [])
1165:        currentPhase: "Starting", config: currentConfig(), events: [], graphNodes: [], graphLinks: [], nodeOutputs: {},
1351:          events: [], graphNodes: [], graphLinks: [], nodeOutputs: {},
1476:        events: [], graphNodes: [], graphLinks: [], nodeOutputs: {},
1701:        events: [], graphNodes: [], graphLinks: [], nodeOutputs: {},

[Showing results with pagination = limit: 10]

---

## Claude

Good. Both `graphLinks` and `graphNodes` are in scope. Now I have all I need to make the three edits. Let me do them:

**Edit 1: Add `forkHighlight`, `replayCopied`, and `forkPanelRef` state**

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

**Edit 2: Add `ref` and highlight ring to the fork panel container div**

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

**Edit 3: Expand the replay panel with "Use this result" section**

Now I'll replace the done-state section (output preview + action buttons) with the expanded version including the 4-option grid:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web\src\App.tsx has been updated successfully.

---

## Claude

Now I need to check if `setForkGoalOverride` is accessible in the replay panel scope. The replay panel is inside the node inspector IIFE which is inside the same component, so it should be fine — but let me verify `setForkGoalOverride` is in scope there:

---

## Subagent Output

509:  const [forkGoalOverride, setForkGoalOverride] = useState("")
1724:      setForkGoalOverride("")
3298:                setForkGoalOverride(n.goal || "")
3302:                setForkGoalOverride("")
3604:                                onChange={e => setForkGoalOverride(e.target.value)}
3681:                          setForkGoalOverride(selectedNode.goal || "")

---

## Claude

Good — `setForkGoalOverride` is a top-level state setter, accessible everywhere. Now let me run a TypeScript check to confirm no type errors:

---

## Subagent Output

(Bash completed with no output)

---

## Claude

Clean. Let me do a quick visual check on the final replay panel to confirm the structure looks right:

---

## Subagent Output

3659	                              <span className="w-4 text-center text-xs font-mono tabular-nums">{value}</span>
3660	                              <button onClick={() => onChange(Math.min(max, value + 1))} disabled={value >= max || thisStatus === "running"}
3661	                                className="h-5 w-5 rounded border border-border text-muted-foreground hover:text-foreground hover:border-primary/50 disabled:opacity-30 text-xs leading-none">+</button>
3662	                            </div>
3663	                          </div>
3664	                        )
3665	
3666	                        // Parent node lookup (used by "Go to parent → Fork")
3667	                        const parentLink = graphLinks.find(l => l.target === selectedNode.id && l.edgeType === "parallel")
3668	                        const parentRafNode = parentLink
3669	                          ? graphNodes.find(n => n.id === parentLink.source && n.type === "raf-node") ?? null
3670	                          : null
3671	
3672	                        const handleCopyOutput = () => {
3673	                          if (!thisOutput) return
3674	                          navigator.clipboard.writeText(thisOutput).then(() => {
3675	                            setReplayCopied(true)
3676	                            setTimeout(() => setReplayCopied(false), 2000)
3677	                          }).catch(err => console.error("[replay] clipboard write failed:", err))
3678	                        }
3679	
3680	                        const handleForkFromHere = () => {
3681	                          setForkGoalOverride(selectedNode.goal || "")
3682	                          setForkHighlight(true)
3683	                          setTimeout(() => setForkHighlight(false), 1800)
3684	                          forkPanelRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" })
3685	                        }
3686	
3687	                        const handleGoToParent = () => {
3688	                          if (parentRafNode) setSelectedNode(parentRafNode)
3689	                        }
3690	
3691	                        const handleAddToPipeline = () => {
3692	                          const prefix = thisOutput
3693	                            ? `Context from replay of "${(selectedNode.goal || "").slice(0, 60)}": ${thisOutput.slice(0, 120)}\n\nGoal: `
3694	                            : `Based on replay of "${(selectedNode.goal || "").slice(0, 60)}":\n\n`
3695	                          setPipelineOpen(true)
3696	                          setPipelineSteps(prev => [
3697	                            ...prev,
3698	                            { id: `step-${Date.now()}`, goal: prefix },
3699	                          ])
3700	                        }
3701	
3702	                        return (
3703	                          <div className={`rounded-md border p-3 space-y-3 mt-1 ${
3704	                            isFailed
3705	                              ? "border-amber-500/30 bg-amber-500/5"
3706	                              : "border-border/40 bg-muted/10"
3707	                          }`}>
3708	
3709	                            {/* Header */}
3710	                            <div className="flex items-center justify-between">
3711	                              <div className="flex items-center gap-2">
3712	                                <span className="text-sm">↺</span>
3713	                                <span className={`text-[10px] font-semibold uppercase tracking-wider ${isFailed ? "text-amber-400" : "text-muted-foreground"}`}>
3714	                                  {isFailed ? "Retry this node" : "Replay this node"}
3715	                                </span>
3716	                              </div>
3717	                              {/* Live status badge */}
3718	                              {thisStatus === "running" && (
3719	                                <span className="text-[10px] text-blue-400 animate-pulse">Running…</span>
3720	                              )}
3721	                              {thisStatus === "done" && (
3722	                                <span className="text-[10px] text-green-400">✓ Done</span>
3723	                              )}
3724	                              {thisStatus === "error" && (
3725	                                <span className="text-[10px] text-red-400">✕ Failed</span>
3726	                              )}
3727	                            </div>
3728	
3729	                            {/* Description */}
3730	                            <p className="text-[10px] text-muted-foreground leading-relaxed">
3731	                              {isFailed
3732	                                ? "Re-runs this node's goal fresh — useful when a model call failed or the output was poor."
3733	                                : "Re-runs this node's goal as a clean attempt. Runs in the background; your current graph stays visible."}
3734	                            </p>
3735	
3736	                            {/* Agent count controls — hidden when already running */}
3737	                            {thisStatus === "idle" && (
3738	                              <div className="rounded-md border border-border/50 bg-muted/20 p-2 space-y-2">
3739	                                <p className="text-[10px] text-muted-foreground font-medium">
3740	                                  Agent counts · ~{estCalls} calls · 1 node cap
3741	                                </p>
3742	                                <Stepper label="Consortium" value={replayConsortiumSize} min={1} max={6} parentValue={consortiumSize} onChange={setReplayConsortiumSize} />
3743	                                <Stepper label="Jury" value={replayJurySize} min={1} max={4} parentValue={jurySize} onChange={setReplayJurySize} />
3744	                              </div>
3745	                            )}
3746	
3747	                            {/* Output preview when done */}
3748	                            {thisStatus === "done" && thisOutput && (
3749	                              <div className="rounded bg-green-500/10 border border-green-500/20 px-2 py-1.5 text-[10px] text-green-300 font-mono whitespace-pre-wrap">
3750	                                {thisOutput.slice(0, 200)}{thisOutput.length > 200 ? "…" : ""}
3751	                              </div>
3752	                            )}
3753	
3754	                            {/* ── "Use this result" options — shown only when done ── */}
3755	                            {thisStatus === "done" && (
3756	                              <div className="space-y-1.5">
3757	                                <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Use this result</p>
3758	                                <div className="grid grid-cols-2 gap-1.5">
3759	
3760	                                  {/* 1 — Copy output */}
3761	                                  <button
3762	                                    onClick={handleCopyOutput}
3763	                                    disabled={!thisOutput}
3764	                                    className="flex flex-col items-start gap-0.5 rounded-md border border-border/50 bg-muted/10 px-2 py-1.5 text-left hover:border-primary/40 hover:bg-muted/20 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
3765	                                  >
3766	                                    <span className="text-[10px] font-medium text-foreground">
3767	                                      {replayCopied ? "✓ Copied!" : "Copy output"}
3768	                                    </span>
3769	                                    <span className="text-[9px] text-muted-foreground leading-snug">Save text to clipboard</span>
3770	                                  </button>
3771	
3772	                                  {/* 2 — Fork from here */}
3773	                                  <button
3774	                                    onClick={handleForkFromHere}
3775	                                    className="flex flex-col items-start gap-0.5 rounded-md border border-border/50 bg-muted/10 px-2 py-1.5 text-left hover:border-primary/40 hover:bg-muted/20 transition-colors"
3776	                                  >
3777	                                    <span className="text-[10px] font-medium text-foreground">Fork from here</span>
3778	                                    <span className="text-[9px] text-muted-foreground leading-snug">Branch with new goal</span>

---

## Subagent Output

3778	                                    <span className="text-[9px] text-muted-foreground leading-snug">Branch with new goal</span>
3779	                                  </button>
3780	
3781	                                  {/* 3 — Go to parent → Fork */}
3782	                                  <button
3783	                                    onClick={handleGoToParent}
3784	                                    disabled={!parentRafNode}
3785	                                    className="flex flex-col items-start gap-0.5 rounded-md border border-border/50 bg-muted/10 px-2 py-1.5 text-left hover:border-primary/40 hover:bg-muted/20 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
3786	                                    title={parentRafNode ? `Go to ${parentRafNode.goal?.slice(0, 40)}` : "No parent raf-node found"}
3787	                                  >
3788	                                    <span className="text-[10px] font-medium text-foreground">Go to parent</span>
3789	                                    <span className="text-[9px] text-muted-foreground leading-snug">Select parent node to fork</span>
3790	                                  </button>
3791	
3792	                                  {/* 4 — Add to pipeline */}
3793	                                  <button
3794	                                    onClick={handleAddToPipeline}
3795	                                    className="flex flex-col items-start gap-0.5 rounded-md border border-border/50 bg-muted/10 px-2 py-1.5 text-left hover:border-primary/40 hover:bg-muted/20 transition-colors"
3796	                                  >
3797	                                    <span className="text-[10px] font-medium text-foreground">Add to pipeline</span>
3798	                                    <span className="text-[9px] text-muted-foreground leading-snug">Chain into next step</span>
3799	                                  </button>
3800	
3801	                                </div>
3802	                              </div>
3803	                            )}
3804	
3805	                            {/* Action buttons */}
3806	                            <div className="flex gap-2">
3807	                              {(thisStatus === "idle" || thisStatus === "error") && (
3808	                                <button
3809	                                  onClick={() => replayNode(selectedNode.id, selectedNode.goal || "")}
3810	                                  disabled={!selectedNode.goal?.trim()}
3811	                                  className={`flex-1 rounded-md border px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
3812	                                    isFailed
3813	                                      ? "border-amber-500/40 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20"
3814	                                      : "border-border/50 bg-muted/20 text-muted-foreground hover:text-foreground hover:border-primary/40"
3815	                                  }`}
3816	                                >
3817	                                  {thisStatus === "error" ? "Retry again" : `${isFailed ? "Retry" : "Replay"} · ~${estCalls} calls`}
3818	                                </button>
3819	                              )}
3820	                              {thisStatus === "done" && (
3821	                                <button
3822	                                  onClick={viewReplayResult}
3823	                                  className="flex-1 rounded-md border border-green-500/40 bg-green-500/10 px-3 py-1.5 text-xs font-medium text-green-400 hover:bg-green-500/20 transition-colors"
3824	                                >
3825	                                  View full result
3826	                                </button>
3827	                              )}
3828	                              {thisStatus === "done" && (
3829	                                <button
3830	                                  onClick={() => { setReplayStatus("idle"); setReplayForNodeId(null); setReplayCopied(false) }}
3831	                                  className="rounded-md border border-border/40 px-2 py-1.5 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
3832	                                  title="Reset replay panel"
3833	                                >↺</button>
3834	                              )}
3835	                            </div>
3836	                          </div>
3837	                        )
3838	                      })()}
3839	                    </>
3840	                  )}
3841	
3842	                  {/* ── Consortium-group: list all proposals ────────────── */}
3843	                  {selectedNode.type === "consortium-group" && (
3844	                    <>
3845	                      <div className="flex items-center gap-2 flex-wrap">
3846	                        <p className="text-muted-foreground text-[10px]">Task: <span className="text-foreground font-mono">{selectedNode.task}</span></p>
3847	                        {(inspectorCandidatesEvent as any)?.tier !== undefined && tierBadge((inspectorCandidatesEvent as any).tier)}

---

## Claude

Everything looks correct. The structure is clean and TypeScript compiled with no errors. Here's what was added:

**State additions** (`App.tsx` ~line 527):
- `replayCopied` — boolean that flips to show "✓ Copied!" for 2 seconds after clipboard write
- `forkHighlight` — boolean that briefly rings the fork panel with `ring-2 ring-primary/60`
- `forkPanelRef` — ref attached to the fork panel container div

**Fork panel** (`~line 3548`): now has `ref={forkPanelRef}` and a conditional ring class driven by `forkHighlight`.

**Replay panel done-state** now shows a "Use this result" 2×2 grid above the existing action buttons:
1. **Copy output** — `navigator.clipboard.writeText`, label flips to "✓ Copied!" for 2s, errors go to `console.error("[replay]")`
2. **Fork from here** — pre-fills `forkGoalOverride` with the node's goal, briefly highlights the fork panel, and scrolls it into view
3. **Go to parent** — finds the nearest parent `raf-node` via `graphLinks` and calls `setSelectedNode`; disabled (grayed) if no parent exists, tooltip shows the parent goal
4. **Add to pipeline** — opens the pipeline panel and appends a new step pre-filled with replay context + a "Goal: " prefix for the user to complete

---

## You

good now i want you to do two things , udpate the readme and help me get this coding session in an md or pdf file

---

## Subagent Output

File does not exist. Note: your current working directory is C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\web.

---

## Claude

Let me read the current README and memory files first.

---

## Subagent Output

node_modules\@types\estree\README.md
node_modules\@babel\helper-string-parser\README.md
node_modules\@babel\helper-globals\README.md
node_modules\@babel\helper-validator-identifier\README.md
node_modules\@babel\helper-validator-option\README.md
node_modules\@babel\code-frame\README.md
node_modules\@types\prop-types\README.md
node_modules\@types\react-dom\README.md
node_modules\@babel\helper-plugin-utils\README.md
node_modules\@babel\helper-module-imports\README.md
node_modules\@rollup\rollup-win32-x64-gnu\README.md
node_modules\@rollup\rollup-win32-x64-msvc\README.md
node_modules\@types\babel__template\README.md
node_modules\@babel\compat-data\README.md
node_modules\@babel\helpers\README.md
node_modules\@babel\traverse\README.md
node_modules\@babel\types\README.md
node_modules\@types\babel__traverse\README.md
node_modules\@types\babel__generator\README.md
node_modules\@babel\helper-compilation-targets\README.md
node_modules\@babel\helper-module-transforms\README.md
node_modules\@babel\generator\README.md
node_modules\@babel\plugin-transform-react-jsx-source\README.md
node_modules\@babel\template\README.md
node_modules\@types\react\README.md
node_modules\@babel\core\README.md
node_modules\@types\babel__core\README.md
node_modules\@babel\parser\README.md
node_modules\@babel\plugin-transform-react-jsx-self\README.md
node_modules\lru-cache\README.md
node_modules\convert-source-map\README.md
node_modules\picocolors\README.md
node_modules\yallist\README.md
node_modules\js-tokens\README.md
node_modules\jsesc\README.md
node_modules\@jridgewell\resolve-uri\README.md
node_modules\loose-envify\README.md
node_modules\update-browserslist-db\README.md
node_modules\semver\README.md
node_modules\debug\README.md
node_modules\gensync\README.md
node_modules\esbuild\README.md
node_modules\@vitejs\plugin-react\README.md
node_modules\csstype\README.md
node_modules\react-refresh\README.md
node_modules\json5\README.md
node_modules\source-map-js\README.md
node_modules\scheduler\README.md
node_modules\@jridgewell\sourcemap-codec\README.md
node_modules\@jridgewell\gen-mapping\README.md
node_modules\@jridgewell\remapping\README.md
node_modules\nanoid\README.md
node_modules\react\README.md
node_modules\@jridgewell\trace-mapping\README.md
node_modules\rollup\README.md
node_modules\vite\README.md
node_modules\react-dom\README.md
node_modules\@esbuild\win32-x64\README.md
node_modules\typescript\README.md
C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\.venv\Lib\site-packages\pip\_vendor\README.rst
node_modules\@types\trusted-types\README.md
node_modules\iobuffer\README.md
node_modules\svg-pathdata\README.md
node_modules\performance-now\README.md
node_modules\pako\lib\zlib\README
node_modules\base64-arraybuffer\README.md
node_modules\fast-png\README.md
node_modules\rgbcolor\README.md
node_modules\@types\pako\README.md
node_modules\@types\raf\README.md
node_modules\text-segmentation\README.md
node_modules\regenerator-runtime\README.md
node_modules\@babel\runtime\README.md
node_modules\raf\README.md
node_modules\stackblur-canvas\README.md
node_modules\css-line-break\README.md
node_modules\fflate\README.md
node_modules\pako\README.md
node_modules\canvg\README.md
node_modules\html2canvas\README.md
node_modules\core-js\actual\README.md
node_modules\core-js\es\README.md
node_modules\core-js\full\README.md
node_modules\core-js\internals\README.md
node_modules\core-js\modules\README.md
node_modules\core-js\README.md
node_modules\core-js\stable\README.md
node_modules\core-js\stage\README.md
node_modules\core-js\web\README.md
node_modules\jspdf\README.md
node_modules\@radix-ui\number\README.md
node_modules\@radix-ui\react-compose-refs\README.md
node_modules\@radix-ui\react-context\README.md
node_modules\@radix-ui\react-direction\README.md
node_modules\@radix-ui\react-id\README.md
node_modules\@radix-ui\react-use-callback-ref\README.md
node_modules\@radix-ui\react-use-layout-effect\README.md
node_modules\@radix-ui\react-use-previous\README.md
node_modules\@radix-ui\react-use-size\README.md
node_modules\rw\README.md
(Results are truncated. Consider using a more specific path or pattern.)

---

## Subagent Output

node_modules\@types\estree\README.md
node_modules\@babel\helper-string-parser\README.md
node_modules\@babel\helper-globals\README.md
node_modules\@babel\helper-validator-identifier\README.md
node_modules\@babel\helper-validator-option\README.md
node_modules\@babel\code-frame\README.md
node_modules\@types\prop-types\README.md
node_modules\@types\react-dom\README.md
node_modules\@babel\helper-plugin-utils\README.md
node_modules\@babel\helper-module-imports\README.md
node_modules\@rollup\rollup-win32-x64-gnu\README.md
node_modules\@rollup\rollup-win32-x64-msvc\README.md
node_modules\@types\babel__template\README.md
node_modules\@babel\compat-data\README.md
node_modules\@babel\helpers\README.md
node_modules\@babel\traverse\README.md
node_modules\@babel\types\README.md
node_modules\@types\babel__traverse\README.md
node_modules\@types\babel__generator\README.md
node_modules\@babel\helper-compilation-targets\README.md
node_modules\@babel\helper-module-transforms\README.md
node_modules\@babel\generator\README.md
node_modules\@babel\plugin-transform-react-jsx-source\README.md
node_modules\@babel\template\README.md
node_modules\@types\react\README.md
node_modules\@babel\core\README.md
node_modules\@types\babel__core\README.md
node_modules\@babel\parser\README.md
node_modules\@babel\plugin-transform-react-jsx-self\README.md
node_modules\lru-cache\README.md
node_modules\convert-source-map\README.md
node_modules\picocolors\README.md
node_modules\yallist\README.md
node_modules\js-tokens\README.md
node_modules\jsesc\README.md
node_modules\@jridgewell\resolve-uri\README.md
node_modules\loose-envify\README.md
node_modules\update-browserslist-db\README.md
node_modules\semver\README.md
node_modules\debug\README.md
node_modules\gensync\README.md
node_modules\esbuild\README.md
node_modules\@vitejs\plugin-react\README.md
node_modules\csstype\README.md
node_modules\react-refresh\README.md
node_modules\json5\README.md
node_modules\source-map-js\README.md
node_modules\scheduler\README.md
node_modules\@jridgewell\sourcemap-codec\README.md
node_modules\@jridgewell\gen-mapping\README.md
node_modules\@jridgewell\remapping\README.md
node_modules\nanoid\README.md
node_modules\react\README.md
node_modules\@jridgewell\trace-mapping\README.md
node_modules\rollup\README.md
node_modules\vite\README.md
node_modules\react-dom\README.md
node_modules\@esbuild\win32-x64\README.md
node_modules\typescript\README.md
C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\.venv\Lib\site-packages\pip\_vendor\README.rst
node_modules\@types\trusted-types\README.md
node_modules\iobuffer\README.md
node_modules\svg-pathdata\README.md
node_modules\performance-now\README.md
node_modules\pako\lib\zlib\README
node_modules\base64-arraybuffer\README.md
node_modules\fast-png\README.md
node_modules\rgbcolor\README.md
node_modules\@types\pako\README.md
node_modules\@types\raf\README.md
node_modules\text-segmentation\README.md
node_modules\regenerator-runtime\README.md
node_modules\@babel\runtime\README.md
node_modules\raf\README.md
node_modules\stackblur-canvas\README.md
node_modules\css-line-break\README.md
node_modules\fflate\README.md
node_modules\pako\README.md
node_modules\canvg\README.md
node_modules\html2canvas\README.md
node_modules\core-js\actual\README.md
node_modules\core-js\es\README.md
node_modules\core-js\full\README.md
node_modules\core-js\internals\README.md
node_modules\core-js\modules\README.md
node_modules\core-js\README.md
node_modules\core-js\stable\README.md
node_modules\core-js\stage\README.md
node_modules\core-js\web\README.md
node_modules\jspdf\README.md
node_modules\@radix-ui\number\README.md
node_modules\@radix-ui\react-compose-refs\README.md
node_modules\@radix-ui\react-context\README.md
node_modules\@radix-ui\react-direction\README.md
node_modules\@radix-ui\react-id\README.md
node_modules\@radix-ui\react-use-callback-ref\README.md
node_modules\@radix-ui\react-use-layout-effect\README.md
node_modules\@radix-ui\react-use-previous\README.md
node_modules\@radix-ui\react-use-size\README.md
node_modules\rw\README.md
(Results are truncated. Consider using a more specific path or pattern.)

---

## Subagent Output

AGENTS.md
ARCHITECTURE.md
export_session.py
Full impementation.png
FUTURE-UI-PLAN.md
handmade files
image.png
mode_decision.txt
package.json
package-lock.json
papers
PROBLEMS.md
raf
raf_runs.db
raf_session_yc.md
RAF-complete-flow.md
RAF-diagram.md
RAF-project-spec.md
railway.json
README.md
render.yaml
requirements.txt
run_output.json
server
vercel.json
version with extra context processing layer
vite-dev.err.log
vite-dev.log
web
whiteboard.jpeg

---

## Subagent Output

1	# Recursive Agent Framework
2	
3	**Author:** Oludolapo Adegbesan
4	**Institution:** Fisk University, Class of 2026
5	**Status:** Active Research and Development
6	**Patent:** Provisional application pending
7	
8	---
9	
10	![RAF execution graph UI](./image.png)
11	
12	*RAF web interface showing a live recursive execution graph, run timeline, and model activity.*
13	
14	---
15	
16	## What Is This?
17	
18	The Recursive Agent Framework (RAF) is a system for orchestrating artificial intelligence agents to solve tasks of any complexity and length. It is the foundation of a larger platform called **Computer**: a universal substrate for recursive AI agent orchestration with experiential memory.
19	
20	Most AI systems today assign a task to a single model and let it reason through everything at once. This works for simple tasks but breaks down quickly when tasks are long, multi-step, or require different kinds of reasoning at different stages. A single agent has a limited context window, a single perspective, and no memory of what it has done before.
21	
22	RAF solves this with a different approach: **divide and conquer, with committees at every decision point.** Complex tasks are recursively broken down into smaller pieces until each piece is simple enough to execute directly. Every critical decision along the way is made not by one agent, but by a group of agents that propose options and vote on the best one.
23	
24	The result is a system that can take on problems no single model could handle, execute them with multi-agent checks at every step, and grow more capable over time as memory and substrate layers are added.
25	
26	![RAF concept whiteboard](./whiteboard.jpeg)
27	
28	*Early whiteboard sketch of the recursive planning, voting, and base-case execution flow.*
29	
30	---
31	
32	## Why Are We Building This?
33	
34	Current AI agent frameworks have three fundamental problems.
35	
36	**The context ceiling.** Every model has a limit on how much it can process at once. Long or complex tasks hit that ceiling, forcing the model to either truncate information or hallucinate continuity. There is no principled mechanism for handling tasks that exceed what any one model can hold.
37	
38	**Single-agent fragility.** When one model makes every decision, its biases, blind spots, and errors compound. There is no check on bad reasoning, no diversity of perspective, and no separation between the agent that does the work and the agent that judges whether it was done correctly.
39	
40	**No persistent cognition.** Agents forget everything between sessions. They cannot learn from experience, build up institutional knowledge, or carry context from one task into another. Every run starts from zero.
41	
42	RAF addresses the first two problems today. The memory system and substrate layers address the third. Together, they form **Computer**: a machine for sustained, recursive, multi-agent thought.
43	
44	---
45	
46	## How It Works
47	
48	### The Core Idea
49	
50	When a task arrives, it enters a **RafNode**, the fundamental unit of execution. The node faces one question: is this task small enough to solve directly, or does it need to be broken down first?
51	
52	A group of agents (a Consortium) proposes an answer. A separate group (a Jury) votes on it. This two-stage pattern repeats at every decision point throughout the system.
53	
54	```
55	Task arrives
56	     |
57	     v
58	[Consortium proposes: execute or decompose?]
59	[Jury votes on decision]
60	     |
61	     +-------> BASE CASE (small enough to execute directly)
62	     |              |
63	     |         [Consortium proposes executor designs]
64	     |         [Jury selects best design]
65	     |         [Executor runs the task]
66	     |         [Jury evaluates success]
67	     |              |
68	     |         Return result
69	     |
70	     +-------> RECURSIVE CASE (too complex, must decompose)
71	                    |
72	               [Consortium proposes decomposition plans]
73	               [Invalid plans filtered. Similar plans merged.]
74	               [Jury selects final plan]
75	               [Each child context refined in dependency order]
76	               [Children execute in parallel, respecting dependencies]
77	               [Consortium analyzes combined results]
78	               [Jury evaluates overall success]
79	                    |
80	               Return result
81	```
82	
83	### Proposal and Vote
84	
85	Every critical decision follows the same two-stage pattern. A **Consortium** runs multiple agents in parallel to generate diverse proposals. An **AgentJury** collects votes from a separate set of agents and aggregates them to select a winner.
86	
87	This separation matters. The agents proposing options and the agents judging them are distinct. The executor that runs a task and the evaluator that judges its success are distinct. This reduces bias, catches errors, and produces more reliable decisions than any single model acting alone.
88	
89	### Sibling Dependencies
90	
91	When a task is decomposed into children, those children can depend on each other. A child with dependencies waits for its siblings to finish, receives their results as additional context, and only then proceeds. Children without dependencies run immediately in parallel.
92	
93	```
94	Parent Task
95	   |
96	   +-- Child A (no dependencies)         runs immediately
97	   +-- Child B (depends on A)            waits for A
98	   +-- Child C (depends on A)            waits for A
99	   +-- Child D (depends on B and C)      waits for B and C
100	```
101	
102	### Context Refinement Layer
103	
104	Before any child task launches, each child plan is refined in dependency order. A Consortium proposes a refined version of each child's context, clarifying its exact purpose, what information it must return, and what success looks like. A Jury selects the best refinement. Children with dependencies have their refinements informed by the already-refined contexts of what they depend on.
105	
106	This ensures every child starts with precisely the context it needs and nothing more.
107	
108	---
109	
110	## Architecture
111	
112	The full system is built in three layers. The first is implemented. The second and third are designed and in development.
113	
114	### Layer 1: RAF (Recursive Agent Framework)
115	
116	The orchestration brain. Handles task decomposition, multi-agent decision-making, sibling dependencies, and context refinement. This layer is the core of what is built today.
117	
118	**Components:**
119	
120	| Component | Role |
121	|---|---|
122	| RafNode | Recursive execution unit. One per task. Decides and runs. |
123	| AgentConsortium | Runs N agents in parallel to generate diverse proposals. |
124	| AgentJury | Collects votes from N agents and aggregates to a winner. |
125	| LLM Adapters | Provider-agnostic interface for OpenRouter, Claude, Gemini, and others. |
126	| FastAPI Server | HTTP and WebSocket API for running and observing tasks. |
127	| React Frontend | Web interface for launching runs and streaming results. |
128	
129	### Layer 2: Experiential Memory System
130	
131	The cognitive continuity layer. Agents do not just store facts; they store experiences: what they were doing when they learned something, what preceded it, what followed, and how significant it was.
132	
133	Memory is stored as a vector graph database where nodes are high-dimensional vectors and edges are typed relationships (temporal, causal, associative, hierarchical, contradictory, experiential). Retrieval is position-relative: the same memory has different relevance depending on where in the execution graph the query originates, analogous to variable scoping in programming languages.
134	
135	An always-on Observer watches all model IO across the system, extracts memories with full experiential context, and writes them into the graph. A pre-turn Injector retrieves relevant memories before each LLM call and composes them into the context window.
136	
137	The memory graph syncs bidirectionally with an Obsidian vault, making it human-readable, editable, and git-versionable.
138	
139	**Status:** Designed. Research complete. Implementation not yet started.
140	
141	### Layer 3: Universal Substrate
142	
143	The execution infrastructure. A Rust runtime where everything in the system is a node with typed input and output ports. Nodes communicate via a typed event bus. Ports speak HTTP, MCP, native Rust, or WebSocket. The substrate can be compiled to a single machine, a CUDA cluster, distributed cloud, or a static Rust binary.
144	
145	This layer makes the system fast, portable, and observable. The event bus drives the real-time UI: execution trees lighting up as nodes run, token streams from individual agents, consortium proposals forming in parallel, and the memory graph growing as the system works.
146	
147	**Status:** Designed. Implementation not yet started.
148	
149	![RAF full implementation view](./Full%20impementation.png)
150	
151	*Expanded execution graph view with recursive nodes, consortium activity, jury decisions, and trace inspection.*
152	
153	---
154	
155	## Project Vision
156	
157	The long-term vision is a system called **Computer**: a universal substrate for recursive AI agent orchestration with experiential memory.
158	
159	The name is intentional. This is not a chatbot wrapper, a framework convenience layer, or an automation tool. It is a programmable machine for thought. A substrate on which cognitive architectures are built. Something closer to what J.C.R. Licklider described in 1960 in "Man-Computer Symbiosis": a system where humans communicate intent and goals, and the machine figures out procedures and details.
160	
161	The design is built on a set of core principles:
162	
163	**Signal-to-noise optimization.** Each agent handles as little noise and as much signal as possible. Context windows are minimized to only what is necessary for the current decision or execution.
164	
165	**Recursion over monoliths.** No context window should be used for something that would benefit from being split. Tasks are broken into minimum-viable units of work.
166	
167	**Multi-model diversity.** The system improves with more model diversity. Using different models for different decisions introduces epistemic diversity and enables mixture-of-experts reasoning.
168	
169	**Decision aggregation.** Critical decisions are voted on. Proposals come from one group. Votes come from another. No single model makes a unilateral choice.
170	
171	**Memory is experiential.** Agents do not just store what happened. They store what they were doing when it happened, what preceded it, what followed, and how significant it was. Retrieval is shaped by where in the execution graph the query comes from.
172	
173	**Everything is a node.** LLM calls, tool invocations, memory reads and writes, context composition, UI rendering: all are nodes in the substrate with typed ports. Nodes connect to each other via the event bus.
174	
175	---
176	
177	## Goals
178	
179	1. Enable reliable execution of tasks of any complexity or length by decomposing them recursively until each piece is individually solvable.
180	
181	2. Replace single-agent decision-making with multi-agent proposal and vote at every critical step, reducing bias and improving robustness.
182	
183	3. Give agents persistent cognition across sessions through an experiential memory system that encodes not just facts but the context in which those facts were learned.
184	
185	4. Build a substrate that is observable in real-time, where every decision, token, proposal, and memory write is visible and inspectable.
186	
187	5. Create an open research artifact with tunable parameters (agent count, model diversity, compute allocation, prompt design) that can be benchmarked and improved empirically.
188	
189	6. Produce a system general enough to serve as infrastructure: something others can fork, extend, and build cognitive architectures on top of.
190	
191	---
192	
193	## Current State
194	
195	### What Is Built
196	
197	| Component | Status |
198	|---|---|
199	| Recursive task decomposition (RafNode) | Complete |
200	| AgentConsortium (multi-agent proposals) | Complete |
201	| AgentJury (multi-agent voting) | Complete |
202	| Sibling dependency execution | Complete |
203	| JSON schema output validation | Complete |
204	| Context refinement layer (pseudocode) | Complete |
205	| FastAPI server with WebSocket streaming | Complete |
206	| React and Vite web frontend | Complete |
207	| OpenRouter and Mock LLM adapters | Complete |
208	| Additional adapters (Claude, DeepSeek, Groq, HuggingFace) | Written, not yet wired |
209	
210	### What Remains
211	
212	| Component | Status |
213	|---|---|
214	| Experiential memory system | Designed, not yet implemented |
215	| Vector graph database integration | Not started |
216	| Position-relative memory retrieval | Not started |
217	| Always-on Observer for memory formation | Not started |
218	| Pre-turn memory Injector | Not started |
219	| Obsidian vault sync layer | Not started |
220	| Dynamic context window manager | Not started |
221	| Rust substrate runtime | Not started |
222	| Typed port and event bus system | Not started |
223	| Multi-target compilation | Not started |
224	| Persistent run storage (database-backed) | Not started |
225	| Full multi-provider adapter wiring | Not started |
226	| Secret vault and tiered access control | Not started |
227	| Real-time execution tree UI | Partial |
228	
229	---
230	
231	## Repository Layout
232	
233	```
234	raf/                    Core Python implementation of RAF
235	  agents/               Consortium and Jury classes
236	  llm/                  LLM adapter layer (OpenRouter, Mock, and others)
237	  cli/                  Command-line runner
238	
239	server/                 FastAPI backend server
240	
241	web/                    React and Vite frontend
242	  src/
243	    components/         UI components
244	
245	papers/                 Reference research papers
246	handmade files/         Original handwritten design materials
247	RAF-complete-flow.md    Full system flow in natural language
248	RAF-diagram.md          Conceptual diagrams
249	RAF-project-spec.md     Full technical specification
250	whiteboard.jpeg         Original design sketch
251	AGENTS.md               Instructions for AI agents working in this repo
252	```
253	
254	---
255	
256	## Technology Stack
257	
258	| Layer | Technology |
259	|---|---|
260	| Orchestration framework | Python |
261	| LLM abstraction | OpenRouter API (multi-model) |
262	| API server | FastAPI |
263	| Frontend | React, Vite, Tailwind CSS |
264	| Output validation | JSON Schema |
265	| Planned memory database | SurrealDB (native vector and graph in a single query) |
266	| Planned substrate | Rust |
267	| Planned visualization | D3 |
268	| Planned human memory interface | Obsidian |
269	
270	---
271	
272	## Deployment
273	
274	This repo is set up for a public deploy with **Vercel** for the frontend and **Render** for the FastAPI backend.
275	
276	### Frontend: Vercel
277	
278	- Import the repo into Vercel.
279	- Keep the existing root `vercel.json` config.
280	- Set `VITE_API_URL` to your Render backend URL, for example: `https://recursive-agent-framework-api.onrender.com`
281	
282	### Backend: Render
283	
284	- Create a new Render **Web Service** from this repo, or deploy from the included `render.yaml`.
285	- Use the root directory of the repo.
286	- Render should use:
287	  - Build command: `pip install -r requirements.txt`
288	  - Start command: `uvicorn server.main:app --host 0.0.0.0 --port $PORT`
289	  - Health check path: `/api/health`
290	
291	Set these backend environment variables on Render:
292	
293	- `RAF_ALLOWED_ORIGINS=https://your-vercel-app.vercel.app`
294	- `RAF_ENABLE_RUN_LIST=false`
295	- `RAF_REQUIRE_USER_API_KEY=true`
296	
297	Optional:
298	
299	- `OPENROUTER_API_KEY=...`
300	
301	If you set `RAF_REQUIRE_USER_API_KEY=true`, public users must paste in their own API key in the web UI for non-mock providers. That is the safer public setup.
302	
303	### Public-use defaults
304	
305	The backend is configured so public users cannot read arbitrary run history by default:
306	
307	- recent run listing is disabled unless explicitly enabled
308	- each run gets its own access token
309	- run status, event replay, cancellation, and plan approval require that token
310	- WebSocket streaming requires the same token
311	
312	For local development, copy `.env.example` into `.env` and adjust values as needed.
313	
314	---
315	
316	## Research Foundations
317	
318	This project draws from several fields.
319	
320	**Cognitive science.** Tulving's distinction between semantic memory (knowing facts) and episodic memory (remembering experiences) informs the memory system design. Anderson's ACT-R activation model, Howard and Kahana's Temporal Context Model, and DeepMind's MERLIN architecture all contribute to how memory formation and retrieval are designed.
321	
322	**Computer science.** Relative memory space is directly analogous to lexical variable scoping. Capability-based security models inform the tiered secret vault. Monte Carlo Tree Search informs tree-shaped memory formation at points of uncertainty.
323	
324	**Recent AI research.** Pink et al. (2025) on episodic memory for long-term LLM agents, A-MEM (NeurIPS 2025) on Zettelkasten-style agent memory, Zep (2025) on temporal knowledge graphs, and MemGPT (2023) on virtual context management all contribute to the memory system direction.
325	
326	---
327	
328	## License
329	
330	Patent pending. All rights reserved.
331	
332	---
333	
334	## Author
335	
336	**Oludolapo Adegbesan**
337	Fisk University, Class of 2026
338	
339	This is an original research and engineering project developed independently as part of ongoing work in AI systems, multi-agent architectures, and machine cognition.
340

---

## Claude

Now let me check what was already in the UI plan doc and what features are already tracked:

---

## Subagent Output

1	# RAF UI Future Plan
2	
3	This file tracks planned UI changes for the RAF web app. It is intentionally separate from `RAF-project-spec.md`.
4	
5	## How To Read This
6	
7	This is not a request for a new backend architecture. It is a frontend visualization and inspection plan for the existing RAF trace.
8	
9	## Current Status
10	
11	Implemented now:
12	
13	- Frontend grouped full graph, recursive child nodes, dependency edges, node click inspection, live run health, stale warning, session replay/export refresh, JSON/PDF export flow, plan governance UI, plan recovery UI, zoom controls, model slot selection, and full-panel tab layout cleanup for Params and Votes.
14	- Backend plan recovery config and events are wired through the API: `plan_recovery`, `max_plan_retries`, `plan_validation_failed`, `plan_retry_start`, `plan_retry_done`, `plan_abandoned`, and `plan_replaced`.
15	- Backend model timing events are wired for consortium and jury calls: `model_call_start`, `model_call_done`, and `model_call_failed`.
16	
17	Still remaining:
18	
19	- Per-task timeout and fallback behavior: `model_call_timeout`, `model_call_fallback`, timeout config, and partial-result continuation rules.
20	- PDF graph capture still needs final verification against very wide/deep graphs to ensure the full graph image is never cropped.
21	- Physics tuner still needs reliability polish: always-reachable handle, drag/slider separation, and a more transparent expanded overlay.
22	- Live UI display for the new model timing events can be made richer by adding active-call and slowest-call summaries once real traces confirm the event shape.
23	
24	The user's intent:
25	
26	- In full graph mode, show the real RAF process as grouped decision structures.
27	- Do not show only voting nodes. Show recursive child nodes, deeper children, dependencies, and merge/backflow.
28	- When a node is clicked, show the full available details for that exact node.
29	- Keep the graph readable with compact labels, but put complete information in the node details panel.
30	
31	Do not fake missing data. Use trace events that already exist. If a field is not emitted, show a clean empty state or mark it as unavailable.
32	
33	## Goal
34	
35	Make the graph show the full recursive RAF process clearly:
36	
37	- what each RAF node decided
38	- what children each node created
39	- how child nodes depend on each other
40	- how child outputs merge back into the parent
41	- what each consortium proposed
42	- what each jury voted
43	- what the referee or validator checked
44	- what output, error, or decision belongs to each exact node
45	
46	The graph should show structure. The clicked-node panel should show full details.
47	
48	## 1. Grouped Full Graph
49	
50	Full graph mode should group agent activity instead of attaching every proposal and juror directly to the RAF node.
51	
52	Target shape:
53	
54	```text
55	Root RAF node
56	  -> Mode Consortium
57	       -> Agent 1 proposal
58	       -> Agent 2 proposal
59	  -> Mode Jury
60	       -> Juror 1 vote
61	       -> Juror 2 vote
62	  -> Plan Consortium
63	       -> Agent 1 plan
64	       -> Agent 2 plan
65	  -> Plan Jury
66	       -> Juror 1 vote
67	       -> Juror 2 vote
68	```
69	
70	This should stay in full mode. Simplified mode should stay clean and mostly show RAF nodes.
71	
72	## 2. Recursive Child Graph Story
73	
74	The UI should show more than votes. It should show the actual recursive tree.
75	
76	Current behavior:
77	
78	- Child RAF nodes already appear from `node_created.parent_id`.
79	- Dependency edges already use `plan_selected.children[].depends_on` and `node_created.plan_child_id`.
80	- A recursive child can create its own children.
81	
82	Future behavior:
83	
84	- Show planned children as a clear branch from the parent plan.
85	- Show deeper child nodes as nested recursive branches.
86	- Show dependency edges between sibling children.
87	- Show merge/backflow edges from completed child outputs back into the parent merge step.
88	
89	Target shape:
90	
91	```text
92	Root RAF node
93	  -> Plan group
94	       -> child A RAF node
95	       -> child B RAF node
96	       -> child C RAF node
97	
98	child A RAF node
99	  -> Plan group
100	       -> child A.1 RAF node
101	       -> child A.2 RAF node
102	
103	child A / B / C complete
104	  -> Parent Merge group
105	       -> merged parent output
106	```
107	
108	Edge meanings:
109	
110	- Parent-child edge: decomposition.
111	- Dependency edge: sibling execution ordering.
112	- Merge/backflow edge: child output returning to the parent result.
113	
114	## 3. Full Node Details Panel
115	
116	When a user clicks any node, the panel should show all available details for that exact node. It should not be only a small summary.
117	
118	The panel should adapt by node type.
119	
120	RAF node details:
121	
122	- node id
123	- parent id
124	- goal
125	- depth
126	- current phase
127	- mode decision
128	- selected mode
129	- plan selected
130	- children created by this node
131	- child dependencies
132	- child statuses
133	- merge result
134	- final output
135	- confidence
136	- duration
137	- errors
138	- full event history for this node
139	
140	Consortium group details:
141	
142	- task name, such as `mode_decision`, `plan`, `base_execute`, `merge`, or `analysis`
143	- parent RAF node
144	- candidate count
145	- every candidate payload available in the trace
146	- candidate output, mode, plan, or analysis data
147	- which candidate later won, if a jury selected it
148	- model/agent index if available
149	
150	Agent proposal details:
151	
152	- agent number
153	- task
154	- proposal payload
155	- output, mode, plan, or analysis result
156	- whether this proposal was selected
157	- source event
158	
159	Jury group details:
160	
161	- task name
162	- parent RAF node
163	- options reviewed
164	- winner id
165	- confidence
166	- all juror votes
167	- rankings and reasons if emitted
168	- link back to the winning proposal
169	
170	Juror vote details:
171	
172	- juror number
173	- selected option
174	- confidence
175	- ranked options
176	- reason text if emitted
177	
178	Referee / validator / check details:
179	
180	- check type
181	- pass/fail status
182	- missing requirements
183	- forbidden violations
184	- scope drift result
185	- repair attempts
186	- filtered children
187	- token budget events
188	- structured trace fields that are useful to the user
189	
190	If the trace has no details for a clicked node yet, show a clean empty state:
191	
192	```text
193	No detailed trace data has arrived for this node yet.
194	```
195	
196	## 4. Compact Graph Labels
197	
198	Nodes can show short hints directly on the graph, but full details belong in the clicked-node panel.
199	
200	Good graph hints:
201	
202	```text
203	mode: recursive
204	winner: option-0
205	88%
206	3 children
207	output ready
208	error
209	```
210	
211	Avoid putting long text, full proposals, raw output, or long error messages inside the graph node.
212	
213	## 5. Physics Tuner Reliability and Overlay Design
214	
215	The physics tuner still needs more work.
216	
217	Observed issue:
218	
219	- It may not open consistently.
220	- Drag/click behavior can feel unreliable.
221	- When expanded, it can block too much of the execution graph.
222	
223	Future behavior:
224	
225	- The tuner should always be reachable from a small visible handle.
226	- Opening and closing should be reliable.
227	- Dragging the tuner should not conflict with sliders or controls.
228	- When expanded, the panel should be transparent/frosted enough that the graph remains visible behind it.
229	- The tuner should feel like a graph overlay, not a separate blocking panel.
230	
231	Design target:
232	
233	```text
234	collapsed: small "Physics" handle over graph
235	expanded: translucent overlay with drag handle and sliders
236	```
237	
238	Implementation notes:
239	
240	- Keep it mounted even when collapsed; only collapse its content.
241	- Separate panel dragging from slider dragging.
242	- Add a clear open/close affordance.
243	- Use a transparent or frosted background when expanded.
244	- Verify it over the live graph in desktop and narrow viewports.
245	
246	## 6. Plan Governance
247	
248	The current `Plan approval` switch should become a clearer governance setting.
249	
250	Planned modes:
251	
252	```text
253	Auto approve
254	Review only
255	Manual approval
256	```
257	
258	Behavior:
259	
260	- `Auto approve`: consortium proposes, jury selects, validator/referee checks, RAF continues.
261	- `Review only`: UI shows the selected plan, votes, checks, and dependencies without blocking execution.
262	- `Manual approval`: current blocking behavior. User approves or edits the selected plan.
263	
264	Backend mapping:
265	
266	- `Auto approve` -> `plan_approval_required = false`
267	- `Review only` -> `plan_approval_required = false`, plus stronger UI highlighting
268	- `Manual approval` -> `plan_approval_required = true`
269	
270	## 7. Plan Recovery
271	
272	Plan recovery is a later backend-assisted feature. It should not be faked only in the frontend.
273	
274	Intent:
275	
276	If the selected plan is invalid, unsolvable, incomplete, or fails validation, RAF should preserve that failed plan attempt and create a new replacement attempt instead of silently hiding the failure.
277	
278	Target behavior:
279	
280	```text
281	Plan Consortium proposes plans
282	Plan Jury selects best plan
283	Validator / Referee checks selected plan
284	
285	If valid:
286	  execute children
287	
288	If invalid:
289	  mark plan attempt as failed
290	  explain why it failed
291	  generate a replacement plan
292	  show the new attempt as a new graph node/branch
293	  retry only up to a fixed limit
294	```
295	
296	Target graph shape:
297	
298	```text
299	RAF node
300	  -> Plan attempt 1
301	       -> Plan Consortium
302	       -> Plan Jury
303	       -> Validator: failed
304	  -> Plan attempt 2
305	       -> Plan Consortium
306	       -> Plan Jury
307	       -> Validator: passed
308	       -> child RAF nodes execute
309	```
310	
311	Important safeguards:
312	
313	- Do not retry forever.
314	- Use a small limit such as `max_plan_retries = 2`.
315	- Keep failed attempts visible in the trace.
316	- Show the reason a plan was rejected.
317	- Show which plan replaced it.
318	- Make recovery optional.
319	
320	Possible UI setting:
321	
322	```text
323	Plan recovery:
324	Off / Auto retry / Ask before retry
325	```
326	
327	Suggested backend trace events:
328	
329	```text
330	plan_validation_failed
331	plan_retry_start
332	plan_retry_done
333	plan_abandoned
334	plan_replaced
335	```
336	
337	Frontend display:
338	
339	- Full graph mode shows each plan attempt as its own node or group.
340	- Failed attempts get a failed/error state.
341	- Replacement attempts connect back to the same RAF parent node.
342	- The node inspector shows the rejected plan, failure reason, replacement plan, retry count, and final outcome.
343	
344	This feature changes RAF behavior, so it should be implemented after the frontend-only grouped graph and full node inspector work.
345	
346	## 8. Mid-Run Observability and Stuck-State UX
347	
348	The UI must handle traces exported while the run is still active. A `running` status in an export does not automatically mean the system is broken.
349	
350	Intent:
351	
352	- Make active progress visible.
353	- Distinguish normal long-running LLM calls from a truly stale run.
354	- Make partial failures visible without treating them as final run failure.
355	- Make mid-run JSON/PDF exports clearly marked as incomplete.
356	
357	Run state display:
358	
359	```text
360	Currently: root -> spec validation
361	Waiting on: root analysis
362	Last event: spec_validation_final
363	Time since last event: 2m 14s
364	```
365	
366	Stale-state warning:
367	
368	```text
369	No new trace events for 90 seconds.
370	The run may still be waiting on an LLM call.
371	```
372	
373	Active node highlighting:
374	
375	- Highlight the node that most recently emitted an event.
376	- Show the current inferred phase on the node.
377	- Examples: `root validating`, `node-9 executing`, `node-2 merging`.
378	
379	Partial failure summary:
380	
381	```text
382	Partial failures: 5
383	- node-2 mode_decision failed twice
384	- node-2 plan failed once
385	- node-2 refine_context failed once
386	```
387	
388	Important distinction:
389	
390	- A `child_failed` event is not necessarily a final `run_done` failure.
391	- RAF may recover from failed child calls and still complete.
392	- The UI should show both partial failures and final status separately.
393	
394	In-progress export labels:
395	
396	- JSON already includes `status`, but the PDF cover page should visibly say when an export is mid-run.
397	- Add labels such as:
398	
399	```text
400	Status: running
401	Exported mid-run
402	Final output not available yet
403	```
404	
405	Completion expectation hints:
406	
407	For known RAF phases, show what is likely expected next:
408	
409	```text
410	Last completed: spec_validation_final
411	Expected next: analysis -> merge_done -> node_done -> run_done
412	```
413	
414	Per-node progress checklist:
415	
416	When clicking a RAF node, show the node's progress through the RAF lifecycle:
417	
418	```text
419	Spec extracted: done
420	Mode decided: done
421	Plan selected: done
422	Children started: done
423	Children done: partial
424	Merge: done
425	Spec validation: done
426	Analysis: waiting
427	Node done: pending
428	```
429	
430	Long-running model call indicator:
431	
432	If the last trace event suggests the system is waiting on a model call, show:
433	
434	```text
435	Waiting on model call
436	Provider: gemini
437	Task: analysis
438	Node: root
439	```
440	
441	Some of this can be inferred from the latest event. Exact active-call tracking may need backend support later.
442	
443	Run health panel:
444	
445	```text
446	Run health
447	Events: 137
448	Nodes: 9
449	Partial failures: 5
450	Last event: spec_validation_final
451	Last event age: 1m 42s
452	Status: running
453	```
454	
455	Finalization guard:
456	
457	If a run remains `running` long after a terminal-looking event, show a careful message:
458	
459	```text
460	Run has passed validation but has not emitted run_done yet.
461	Waiting for final analysis or completion event.
462	```
463	
464	Do not call this a failure unless the backend emits a final error or the user-defined stale timeout is exceeded.
465	
466	## 9. Complete Export and Report Quality
467	
468	Exports should be useful as standalone artifacts, especially after long RAF runs.
469	
470	Observed issue:
471	
472	- A downloaded JSON trace can still say `status: running` and `result: false` if it is exported before the frontend receives the final `run_done`, even when the backend completes moments later.
473	- The PDF report must include the full graph image, not a cropped or partially visible graph.
474	- The PDF trace section should be neatly organized, not just a sparse list of event names.
475	
476	### 9.1 Final-State-Aware Export
477	
478	Before exporting, the frontend should refresh the latest run state when `runId` exists:
479	
480	```text
481	GET /api/run/{run_id}
482	GET /api/run/{run_id}/events
483	```
484	
485	Then export using the freshest server state.
486	
487	Rules:
488	
489	- If the backend says `done`, export should include final `result`, final status, and final `run_done` if available.
490	- If the backend says `running`, mark the export clearly as mid-run.
491	- If the graph has root `node_done` but no `run_done`, label it as near-complete but not terminal.
492	- The export should include `exportCompleteness` metadata.
493	
494	Example:
495	
496	```json
497	{
498	  "status": "running",
499	  "exportCompleteness": "mid_run",
500	  "hasRunDone": false,
501	  "hasRootNodeDone": true,
502	  "note": "Root completed but run_done was not present when exported."
503	}
504	```
505	
506	### 9.2 Full Graph PDF Capture
507	
508	The PDF graph page should show the entire graph in full form.
509	
510	Requirements:
511	
512	- Capture all visible graph nodes and links.
513	- Fit graph bounds using node positions plus padding.
514	- Temporarily reset zoom/pan before capture.
515	- Prefer full graph mode capture if full-mode nodes exist, or clearly label which mode was captured.
516	- Avoid cropping wide graphs.
517	- If the graph is too large for one page, either scale it down cleanly or split across multiple pages.
518	
519	The report should include:
520	
521	```text
522	Graph page:
523	- full graph image
524	- node count
525	- edge count
526	- graph mode
527	- legend
528	```
529	
530	### 9.3 Neatly Organized Trace PDF
531	
532	The PDF trace section should be readable as a report.
533	
534	Organize by sections:
535	
536	```text
537	Run summary
538	Final output
539	Run health
540	Partial failures
541	RAF nodes
542	Plans and children
543	Consortium proposals
544	Jury votes
545	Referee/spec/check events
546	Tools
547	Timeline / raw trace table
548	```
549	
550	Each section should show useful fields, not just event names.
551	
552	Examples:
553	
554	```text
555	RAF node:
556	- node id
557	- parent id
558	- depth
559	- mode
560	- goal
561	- output summary
562	- confidence
563	- duration
564	- status
565	
566	Jury vote:
567	- node id
568	- task
569	- winner
570	- confidence
571	- option count
572	- juror count
573	
574	Plan:
575	- parent node
576	- child count
577	- child ids
578	- dependencies
579	```
580	
581	The raw trace table can stay at the end, but the report should first present the information in a human-readable structure.
582	
583	### 9.4 JSON Export Completeness
584	
585	JSON export should remain complete and machine-readable.
586	
587	Include:
588	
589	- latest server status
590	- latest server result
591	- all events available from `/api/run/{run_id}/events`
592	- graph nodes/links
593	- node outputs
594	- config
595	- physics
596	- model/provider settings
597	- selected node id
598	- export timestamp
599	- export completeness metadata
600	
601	Do not remove raw event arrays from JSON; the PDF can be organized, but JSON should preserve the trace.
602	
603	## 10. First Performance Work: Timing Events and Timeouts
604	
605	These are the first backend performance items to implement before faster model routing.
606	
607	Priority:
608	
609	```text
610	1. Model call timing events
611	2. Per-task timeout and fallback behavior
612	3. Faster model routing later
613	```
614	
615	### 10.1 Model Call Timing Events
616	
617	Every model call should emit timing events so slow runs are explainable.
618	
619	Events:
620	
621	```text
622	model_call_start
623	model_call_done
624	model_call_failed
625	model_call_timeout
626	model_call_fallback
627	```
628	
629	Example start event:
630	
631	```json
632	{
633	  "event": "model_call_start",
634	  "node_id": "node-2",
635	  "task": "refine_context",
636	  "role": "consortium",
637	  "provider": "gemini",
638	  "model": "gemini-2.5-pro",
639	  "agent_index": 0,
640	  "attempt": 1,
641	  "timestamp": 1234567890.12
642	}
643	```
644	
645	Example done event:
646	
647	```json
648	{
649	  "event": "model_call_done",
650	  "node_id": "node-2",
651	  "task": "refine_context",
652	  "role": "consortium",
653	  "provider": "gemini",
654	  "model": "gemini-2.5-pro",
655	  "duration_ms": 253000,
656	  "attempt": 1,
657	  "timestamp": 1234568143.12
658	}
659	```
660	
661	Why this comes first:
662	
663	- It explains exactly where time is going.
664	- It makes mid-run waiting visible.
665	- It avoids guessing from gaps between unrelated events.
666	- It gives the UI real data for the Run Health panel.
667	
668	Likely backend touch points:
669	
670	- `raf/agents/consortium.py`
671	- `raf/agents/jury.py`
672	- `raf/llm/json_utils.py`
673	- `raf/core/trace.py`
674	- possibly adapter metadata in `raf/llm/*_adapter.py`
675	
676	Implementation note:
677	
678	Start with `Consortium.call()` and `Jury.vote()` if adding trace context to `call_json_with_repair()` is too invasive. The goal is practical visibility first.
679	
680	### 10.2 Per-Task Timeout and Fallback Behavior
681	
682	After timing events exist, add per-task timeout limits.
683	
684	Suggested defaults:
685	
686	```text
687	mode_decision: 60s
688	plan: 120s
689	refine_context: 60s
690	base_execute: 120s
691	jury vote: 60s
692	merge: 180s
693	analysis: 90s
694	```
695	
696	Timeout behavior:
697	
698	```text
699	emit model_call_timeout
700	ignore the timed-out result if it arrives later
701	retry once if configured
702	fallback to a configured faster model if available
703	otherwise continue with partial results if the consortium/jury has enough valid responses
704	```
705	
706	Important Python constraint:
707	
708	Python worker threads cannot be safely force-killed. First implementation should use `future.result(timeout=...)`, emit timeout, and stop waiting for that result. The underlying call may finish later in the background, but RAF should not block on it.
709	
710	Suggested config:
711	
712	```text
713	timeout_by_task
714	enable_fallback
715	fallback_provider
716	fallback_model
717	max_retries_per_task
718	```
719	
720	Suggested frontend display:
721	
722	```text
723	model_call_timeout
724	Task: refine_context
725	Node: node-2
726	Provider/model: gemini/gemini-2.5-pro
727	Timeout: 60s
728	Fallback used: gemini/gemini-2.5-flash
729	```
730	
731	### 10.3 Faster Model Routing Later
732	
733	Faster model routing is still valuable, but it should come after timing and timeout visibility.
734	
735	Later routing goal:
736	
737	```text
738	Root planning/final merge: strong model
739	Inner child tasks: faster model
740	Refine context: faster model
741	Jury votes: faster model
742	Analysis/checks: faster model
743	```
744	
745	Do not implement routing first. Without timing events, it is hard to prove which tasks need faster routing.
746	
747	## 11. Implementation Notes
748	
749	Main frontend areas:
750	
751	- `web/src/App.tsx`
752	  - `addSatelliteNodes`
753	  - `processEvent`
754	  - selected-node inspector data derivation
755	  - event correlation for plan children, proposals, jury votes, and merge events
756	- `web/src/components/ExecutionGraph.tsx`
757	  - group-node rendering
758	  - edge types for flow, parallel, dependency, and merge/backflow
759	
760	Backend changes are not required for the first pass because the trace already includes:
761	
762	- `node_created.parent_id`
763	- `node_created.plan_child_id`
764	- `plan_selected.children`
765	- `consortium_candidates`
766	- `jury_votes`
767	- `merge_done`
768	- referee/spec/check events
769	
770	## 12. Concrete Implementation Checklist
771	
772	Use this checklist when implementing the plan.
773	
774	1. Add graph node types for decision groups.
775	
776	Suggested types:
777	
778	```text
779	consortium-group
780	jury-group
781	agent-proposal
782	juror-vote
783	referee-check
784	merge-group
785	```
786	
787	If changing `GraphNode["type"]` is too wide at first, reuse existing `consortium`, `jury`, and `agent` types but add a `task` or `groupKind` field.
788	
789	2. Change satellite node creation.
790	
791	Current pattern:
792	
793	```text
794	RAF node -> Agent proposal
795	RAF node -> Juror
796	```
797	
798	Target pattern:
799	
800	```text
801	RAF node -> Consortium group -> Agent proposal
802	RAF node -> Jury group -> Juror
803	```
804	
805	Group ids should be stable and deterministic:
806	
807	```text
808	{node_id}-consortium-{task}
809	{node_id}-jury-{task}
810	{node_id}-agent-{task}-{index}
811	{node_id}-juror-{task}-{index}
812	```
813	
814	3. Preserve recursive child RAF nodes.
815	
816	Do not replace the existing child node behavior. Keep using:
817	
818	```text
819	node_created.parent_id
820	node_created.plan_child_id
821	plan_selected.children[].depends_on
822	```
823	
824	The child graph is the core RAF structure. Agent/jury nodes are detail around that structure.
825	
826	4. Add merge/backflow visualization.
827	
828	When child nodes finish and the parent emits merge events, create a parent merge group:
829	
830	```text
831	Parent RAF node -> Merge group
832	Child RAF node -> Merge group
833	Merge group -> Parent RAF node or Parent output state
834	```
835	
836	If that feels visually too busy, only show these edges in full mode.
837	
838	5. Build a derived `NodeInspectorData` object.
839	
840	Do not store a lot of duplicated UI-only state. Derive inspector data from:
841	
842	```text
843	selectedNode
844	events[]
845	graphNodes[]
846	graphLinks[]
847	nodeOutputs
848	```
849	
850	The derivation should answer:
851	
852	```text
853	What node was clicked?
854	What RAF node owns this node?
855	What task does it belong to?
856	What events belong to it?
857	What proposal/vote/output/check data belongs to it?
858	What child nodes and dependency edges belong to it?
859	```
860	
861	6. Make the inspector type-aware.
862	
863	Use node type and task to decide which sections to render:
864	
865	```text
866	RAF summary
867	Mode decision
868	Plan and children
869	Consortium proposals
870	Jury votes
871	Output
872	Merge
873	Checks
874	Errors
875	Raw event history
876	```
877	
878	7. Show full details in the inspector.
879	
880	The inspector should show complete useful data, not only counters:
881	
882	- full proposal payloads
883	- all vote options
884	- all juror votes
885	- winner and confidence
886	- selected plan children
887	- dependency lists
888	- outputs
889	- errors
890	- check results
891	- structured trace fields when they are useful
892	
893	8. Keep graph labels compact.
894	
895	The graph should not become a document. Use small hints only:
896	```text
897	plan
898	3 children
899	winner option-0
900	88%
901	output ready
902	error
903	```
904	
905	9. Keep simplified/full mode behavior.
906	
907	Simplified mode:
908	
909	- RAF nodes
910	- main parent-child edges
911	- maybe dependency edges
912	
913	Full mode:
914	
915	- RAF nodes
916	- grouped consortium/jury/agent nodes
917	- dependency edges
918	- merge/backflow
919	- referee/check nodes
920	
921	10. Verify with a recursive prompt.
922	
923	Use a prompt that creates multiple children and deeper recursion, then check:
924	
925	- parent creates children
926	- child creates its own children when recursive
927	- dependency edges connect sibling children
928	- full mode shows grouped consortium and jury nodes
929	- clicking each node type shows the correct full details
930	- error and output states are visible
931

---

## Claude

Now I have everything I need. Let me write both files in parallel — the updated README and the session log.

---

## Subagent Output

b0089f9 feat: add environment configuration, deployment instructions, and access token management
bed97d3 feat: add UI components and styles
3022599 feat: Initialize server with FastAPI and WebSocket support
a62866d docs: complete professional README with full Computer vision and roadmap
813af63 docs: rewrite README with project vision, goals, and authorship
8fecddd Add high-level-plan.md for architecture visualizer (Bennett's requirements)
d7f2a88 more thinking
2c9debb more ideas
732dfaf more thinking
decfc43 doing some thinking
7460861 Add benchmarking variables, future work, and flow refinements from whiteboard session
d9f06d4 Clean up repo: add .gitignore, remove old images and .DS_Store, update README
140f7cd Add files via upload
8d1f74f Rename IMG_4862.jpeg to whiteboard_brainstorm.jpeg
1d6edff Add napkin prototype, complete flow diagram with all agent clusters

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\README.md has been updated successfully.

---

## Claude

Now update the Web section of the repo layout and the tech stack to reflect D3 as implemented:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\README.md has been updated successfully.

---

## Claude

Also update the repo layout to mention the new component file:

---

## Subagent Output

The file C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\README.md has been updated successfully.

---

## Claude

Now write the session documentation file:

---

## Subagent Output

File created successfully at: C:\Users\dolap\Desktop\Projects\Recursive-Agent-Framework\Recursive-Agent-Framework-\SESSION-2025-05-01.md

---

## Claude

Both files are written. Here's what changed:

**README.md** — updated three sections:
- "What Is Built" table: added 11 new completed items covering the D3 graph, fork, pipeline, node replay, post-replay actions, access token auth, and structured logging
- "What Remains" table: replaced "Real-time execution tree UI: Partial" with the two genuinely remaining items (per-task timeouts, model timing events)
- Tech stack: D3 changed from "Planned" to "Graph visualization (force-directed, live streaming)"
- Repo layout: expanded the `web/src/components/` section with the three main component files

**SESSION-2025-05-01.md** — a full engineering log at `Recursive-Agent-Framework-/SESSION-2025-05-01.md` covering:
- All 4 features with architecture diagrams, key code snippets, and rationale
- The error handling audit (frontend prefixes + backend `logging` module)
- The ancestor sort bug fix
- Design decision notes explaining the non-obvious choices (`replayForNodeIdRef`, `pipelineCancelRef`, `settled` guard, fork highlight pattern)

For a PDF: open the `.md` file in VS Code and use `Ctrl+Shift+P → Markdown: Export to PDF` (requires the Markdown PDF extension), or paste it into any Markdown-to-PDF converter.

---

