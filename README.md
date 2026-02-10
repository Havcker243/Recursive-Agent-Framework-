# RAF: Recursive Agent Framework

> A recursive agent orchestration framework for horizon-length agentic tasks.

**Status:** Research & Development  
**Patent:** Provisional application pending

---

## The Napkin Prototype

![RAF Whiteboard Diagram](./whiteboard.jpeg)

*Original whiteboard sketch from the design session*

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

Every decision point uses the **Consortium → Jury** pattern:

| Step | AgentConsortium | AgentJury |
|------|-----------------|-----------|
| **1. Base Case Decision** | Generate base/recursive proposals | Vote: base case or recursive? |
| **2a. Agent Design** *(base case)* | Generate executor designs | Vote: best design? |
| **2b. Execution** | — | Agent executes task |
| **2c. Success Vote** | Analyze execution output | Vote: did it succeed? |
| **3a. Plan Generation** *(recursive)* | Generate decomposition plans | — |
| **3b. Plan Merge** | Merge similar plans | Vote: best merge? |
| **3c. Plan Selection** | — | Vote: best final plan? |
| **3d. Child Execution** | — | Spawn RafNodes, execute in parallel |
| **3e. Success Vote** | Analyze combined results | Vote: overall success? |

**Key design decision:** Success determination is a *separate* consortium→jury vote after execution, not part of execution itself.

See [RAF-complete-flow.md](./RAF-complete-flow.md) for the full diagram.

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
├── whiteboard.jpeg           # Original whiteboard sketch
├── RAF-pseudocode.ts         # Ground truth algorithm (DO NOT MODIFY)
├── RAF-project-spec.md       # Technical specification
├── RAF-complete-flow.md      # Complete algorithm flow with all agent clusters
├── RAF-diagram.md            # Additional Mermaid diagrams
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
