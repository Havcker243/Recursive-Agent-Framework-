This is just a plan, and I'm carefully curating it. I'm rarely going to want you to change more than 1 sentence at a time, so don't make changes to RAF-project-spec.md without my explicit instructions. Every time you make changes, read all the papers in the papers folder. You are not allowed to modify files in the handmade files folder.

<claude-mem-context>
# Memory Context

# [Recursive-Agent-Framework-] recent context, 2026-05-22 2:46pm PDT

Legend: 🎯session 🔴bugfix 🟣feature 🔄refactor ✅change 🔵discovery ⚖️decision 🚨security_alert 🔐security_note
Format: ID TIME TYPE TITLE
Fetch details: get_observations([IDs]) | Search: mem-search skill

Stats: 19 obs (8,629t read) | 1,773,272t work | 100% savings

### May 17, 2026
62 11:46p ⚖️ User Access Strategy Discussion: API Key vs Login vs Demo
63 11:48p 🔵 RAF Project: Full-Stack Multi-Agent Framework — Architecture Audit
64 " 🟣 User API Key Changed from localStorage to In-Memory Only
65 " 🔵 Backend Security Model for Public Access
66 " ⚖️ Session-Only API Key Chosen Over Login System or Demo-Only Mode
67 " 🔵 Live Deployment State: Vercel Frontend Lags Behind Local Changes
68 " 🔵 Mock Adapter Behavior: Deterministic Domain-Aware Decomposition
### May 19, 2026
69 5:48p 🔵 Recursive Agent Framework Project Structure Mapped
70 " 🔵 RecursiveAgentEngine Core Implementation Revealed
72 " 🔵 RAF Is a Full-Stack Production-Ready Multi-Agent Framework
73 " 🔵 ARCHITECTURE.md Documents Full Decision Pipeline and Component Design
74 " 🔵 RAF Full Tech Stack: FastAPI + React/Vite/D3 + Supabase Integration Planned
75 " 🔵 DependencyGraph Uses Kahn's Topological Sort with Cycle Detection
76 " 🔵 AgentRegistry and BaseTool Define the Plugin Interface for RAF Agents
77 5:50p ✅ Added inline documentation comments to server/main.py WebSocket and API endpoints
78 " 🔵 RunManager class structure in server/run_manager.py confirmed
71 5:51p 🔵 RAF Has a Node.js Frontend Layer with Tailwind CSS
### May 20, 2026
79 6:42a ✅ README.md completely rewritten as a personal narrative research story
80 6:43a 🔵 Tool cards in App.tsx confirmed with inline comment describing available agent tools
S54 RAF project polish pass: completeness audit, user-visible tool descriptions, inline code navigation comments, and README rewrite as personal founder story (May 20, 6:43 AM)
S53 RAF project completeness review + user-navigable tools UI + inline code comments + README rewrite as founder narrative (May 20, 6:43 AM)
**Investigated**: Reviewed server/main.py full API surface (445 lines), run_manager.py RunManager class structure (699 lines), and App.tsx tool toggle section to understand what was already documented vs. what needed clarification for new users.

**Learned**: The RAF project is production-deployed with a substantial feature set already complete. The frontend already rendered tool cards with descriptions — the session confirmed this. server/main.py already had ASCII section banners for three of four logical groups; the WebSocket section was the only one missing a comment block. The README was written in third-person technical reference style, not in the author's voice.

**Completed**: 1. README.md fully rewritten as a first-person founder narrative: origin story → three problems identified → core idea (6 decision points per node explicitly enumerated) → conscious design decisions (separate jury, temperature laddering, confidence-weighted voting, sibling DAG, Spec+Ledger, deterministic Referee) → research paper grounding (Meyerson et al. arXiv:2511.09030 and Zhang/Kraska/Khattab arXiv:2512.24601) → three-layer architecture (Layer 1 built, Layers 2+3 designed) → honest status tables (what's complete vs. not started) → vision for "Computer" system.
    2. server/main.py: Added # ── WebSocket live stream section header with 3-line comment explaining the endpoint drains the run event queue in real time, token is validated via query param, and frontend replays from /api/run/{id}/events on disconnect.
    3. App.tsx: Tool cards already present with inline descriptions for web_search, http_get, run_python — confirmed working, no changes needed there.
    4. server/main.py section banners confirmed complete across all four sections: Utility/discovery (line 178), Run lifecycle (line 190), Run history/public gallery (line 360), WebSocket live stream (line 429).

**Next Steps**: Session appears complete. All four deliverables from the user request were addressed: completeness review done, tool visibility confirmed, inline comments added to server code and App.tsx event/websocket groups, and README rewritten as a project story. No active work in progress.


Access 1773k tokens of past work via get_observations([IDs]) or mem-search skill.
</claude-mem-context>