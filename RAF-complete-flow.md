# RAF Complete Flow (Natural Language)

This document describes the full behavior of the Recursive Agent Framework in plain language. It focuses on decisions, responsibilities, and information flow rather than implementation details.

## End-to-End Flow

1. **Intake**
   - A task arrives with any supporting context.
   - If this node depends on siblings, their completed results are folded into the context before any decision is made.

2. **Base vs. Recursive Decision**
   - A small group of independent agents proposes whether the task should be handled directly or decomposed.
   - A separate voting group selects the final decision.

3. **If the task is handled directly (base case)**
   - **Design step:** Multiple agents propose how to execute the task, including tools, expected output shape, and any constraints.
   - **Selection:** A voting group picks the strongest proposal.
   - **Execution:** A single executor runs the task.
   - **Evaluation:** A separate analysis group judges success, and a voting group selects the final assessment.

4. **If the task is decomposed (recursive case)**
   - **Plan generation:** Multiple agents propose ways to split the task into child tasks with dependencies.
   - **Plan processing:** Invalid cycles are removed. Similar plans are merged, then a voting group selects the best merged set.
   - **Plan selection:** A voting group chooses the final plan to execute.
   - **Context refinement layer (extra context engineering):**
     - Child plans are processed in dependency order.
     - Each child plan is refined by a proposal group to clarify its purpose, the information it must return, and its success condition.
     - The refined plan for a child includes insights from already-refined dependencies.
     - A voting group selects the best refined version for each child.
   - **Child execution:** Children are spawned with the refined context. Each child waits for any required dependencies, then runs in parallel where possible.
   - **Combined evaluation:** Child summaries are aggregated and judged by an analysis group, then finalized by a voting group.

5. **Output**
   - The node returns a success/failure decision, an execution summary, and the collection of child results.

## The Proposal → Vote Pattern

At every decision point, RAF uses a two-stage pattern:
- A **proposal group** generates diverse options.
- A **voting group** selects the best option.

This reduces single-agent bias and improves robustness.

## Why the Success Check is Separate

Execution and success evaluation are intentionally split:
- Executors focus on producing results.
- Evaluators judge those results with fresh context.
- This separation yields clearer accountability and more reliable success decisions.
