# RAF Conceptual Views (Natural Language)

This file replaces code-like diagrams with prose descriptions of the same concepts.

## 1) Single-Node Lifecycle

A single node follows this progression:
1. **Initialization** — The node receives its task and any available context.
2. **Dependency merge** — If sibling results are required, they are merged into the context before decisions are made.
3. **Decision** — A proposal group and a voting group decide whether to execute directly or decompose.
4. **Direct execution path** — The node designs an executor, runs the task, and then evaluates success with a separate analysis vote.
5. **Decomposition path** — The node creates a plan, refines each child’s purpose and success criteria, spawns children, and evaluates combined outcomes.
6. **Return** — The node returns a success decision, an execution summary, and child results.

## 2) Dependency Handling

When a parent creates multiple children, some children may rely on others:
- Children without dependencies start immediately.
- Children with dependencies wait until required siblings finish.
- Only after their dependencies complete do they proceed with their own execution.

This allows parallelism without violating ordering constraints.

## 3) Multi-Agent Decision Pattern

Most decisions are made using a two-stage process:
- **Divergence:** several agents propose options independently.
- **Convergence:** another group of agents votes on the best option.

This pattern is used for:
- Direct-vs-recursive decisions
- Task execution design
- Plan generation and selection
- Success evaluation

## 4) Recursive Structure

The system builds a tree of work:
- The root node receives the overall task.
- It either finishes directly or spawns children.
- Children can themselves decompose into smaller children.
- Leaves of the tree are tasks that can be executed directly.

The result is a layered structure where complexity is reduced at each level.
