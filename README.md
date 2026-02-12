# RAF: Recursive Agent Framework

> A recursive agent orchestration framework for horizon-length agentic tasks.

**Status:** Research & Development  
**Patent:** Provisional application pending

---

## The Napkin Prototype

![RAF Whiteboard Diagram](./whiteboard.jpeg)

Original whiteboard sketch from the design session.

---

## What is RAF?

RAF (Recursive Agent Framework) is a method for running complex, long-horizon tasks by breaking them into smaller parts and managing them with multiple collaborating agents. Instead of forcing a single agent to handle an entire task in one context window, RAF continuously decomposes work until each piece is small and well-defined.

---

## How it Works (High Level)

1. **Decide whether to execute or decompose.**
   A proposal group suggests whether the task should be handled directly or broken down. A voting group makes the final choice.

2. **Direct execution path.**
   If the task is small enough, the system designs an executor, runs the task, and separately evaluates success.

3. **Decomposition path.**
   If the task is too large, the system proposes multiple decomposition plans, merges similar plans, and selects a final plan.

4. **Extra context processing layer.**
   Before any child task is launched, each child plan is refined in dependency order. This refinement clarifies:
   - The purpose of the child task
   - The specific information it must return
   - The success condition for that child

   Refinements incorporate the already-refined requirements of any dependencies.

5. **Parallel child execution with dependencies.**
   Children without dependencies start immediately; others wait for required siblings. Results are merged and evaluated at the parent level.

---

## Core Principles

- **Recursive decomposition** — reduce complexity until tasks are single-step
- **Multi-agent decision making** — proposals and votes at critical points
- **Context discipline** — each agent sees only the context it needs
- **Independent evaluation** — success is judged separately from execution
- **Structured outputs** — decisions and results are consistently shaped

---

## Repository Layout

- `version with extra context processing layer/`
  - `pseudocode-extra-context.ts` — the current pseudocode for the extra context refinement layer
- `version with error handling/`
  - *(empty for now)*
- `RAF-complete-flow.md` — full flow described in natural language
- `RAF-diagram.md` — conceptual views, also in natural language
- `RAF-project-spec.md` — technical specification
- `handmade files/` — handwritten reference materials (do not edit)
- `papers/` — reference papers
- `whiteboard.jpeg` — original whiteboard sketch
- `AGENTS.md` — AI agent instructions

---

## Diagrams and Explanations

See `RAF-complete-flow.md` and `RAF-diagram.md` for narrative descriptions of the system’s flow and structure.

---

## License

Patent pending. All rights reserved.

---

## Author

Bennett Vernon  
Vanderbilt University, Class of 2028

---

This framework is under active development as part of CS 3892 (Cloud Computing) at Vanderbilt University.
