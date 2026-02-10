# RAF: Recursive Agent Framework

> A recursive agent orchestration framework for horizon-length agentic tasks.

**Status:** Research & Development  
**Patent:** Provisional application pending

---

## What is RAF?

RAF (Recursive Agent Framework) is a novel approach to AI agent orchestration that solves the fundamental problem of **context window limitations** in large language models.

Instead of trying to fit an entire complex task into a single agent's context, RAF **recursively decomposes** tasks into smaller, manageable pieces—each with its own optimized context window. At every decision point, **multiple agents vote** to ensure robust, error-resistant execution.

### The Core Insight

Current agent frameworks fail on long-horizon tasks because:
- Single agents accumulate noise in their context windows
- No graceful handling of task complexity
- Single points of failure at each decision

RAF solves this with:
- **Recursive decomposition** — Tasks break down until they're single-step executable
- **Multi-agent voting** — Consortiums propose, juries decide
- **Minimal context windows** — Each agent sees only what it needs

---

## Architecture

```
                    ┌─────────────┐
                    │   RafNode   │
                    │   (root)    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Base Case  │
                    │    Vote     │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │                         │
       ┌──────▼──────┐          ┌───────▼───────┐
       │  Base Case  │          │ Recursive Case│
       │  (execute)  │          │ (decompose)   │
       └─────────────┘          └───────┬───────┘
                                        │
                          ┌─────────────┼─────────────┐
                          │             │             │
                    ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
                    │  RafNode  │ │  RafNode  │ │  RafNode  │
                    │  (child)  │ │  (child)  │ │  (child)  │
                    └───────────┘ └───────────┘ └───────────┘
```

### Key Components

| Component | Purpose |
|-----------|---------|
| **RafNode** | Recursive execution unit — decides base case or decompose |
| **Agent** | Single LLM instance with tools, output schema, and model config |
| **AgentConsortium** | Multiple agents generating diverse proposals |
| **AgentJury** | Multiple agents voting on best option |

### Execution Flow

1. **RafNode receives task** with context
2. **AgentJury votes:** Is this a base case or recursive case?
3. **If base case:**
   - AgentConsortium designs executor agents
   - AgentJury selects best design
   - Agent executes
   - AgentConsortium + AgentJury analyze result
4. **If recursive:**
   - AgentConsortium proposes decomposition plans
   - Plans filtered for circular dependencies
   - AgentJury selects best plan
   - Child RafNodes spawned (with optional sibling dependencies)
   - Results analyzed and returned

---

## Design Principles

1. **Signal-to-noise optimization** — Each agent handles minimal noise, maximum signal
2. **Recursion** — Break down until single-step executable
3. **Multi-model diversity** — Heterogeneous models improve robustness
4. **Decision aggregation** — Votes over single decisions
5. **Strong typing** — JSON schemas enforce output structure

---

## Repository Structure

```
raf-plan/
├── README.md                 # This file
├── RAF-pseudocode.ts         # Ground truth algorithm (DO NOT MODIFY)
├── RAF-project-spec.md       # Technical specification
├── RAF-architecture.jsonc    # Type definitions
├── RAF-diagram.md            # Mermaid diagrams
├── AGENTS.md                 # AI agent instructions
└── papers/                   # Reference papers
```

---

## Diagrams

See [RAF-diagram.md](./RAF-diagram.md) for detailed Mermaid diagrams:
- Main execution flow
- Class hierarchy
- Sibling dependency model
- Consortium-Jury pattern
- Recursive tree structure

---

## Prior Art & Differentiation

RAF differs from existing frameworks:

| Framework | Limitation | RAF Solution |
|-----------|-----------|--------------|
| AutoGPT, BabyAGI | Single-agent loops, context bloat | Recursive decomposition |
| CrewAI, AutoGen | Multi-agent but no recursive structure | Hierarchical + recursive |
| Tree of Thoughts | Search-based, not execution | Execution-focused with voting |
| LangChain | Orchestration without decomposition | Automatic task breakdown |

---

## License

Patent Pending. All rights reserved.

---

## Author

Bennett Vernon  
Vanderbilt University, Class of 2028

---

*This framework is under active development as part of CS 3892 (Cloud Computing) at Vanderbilt University.*
