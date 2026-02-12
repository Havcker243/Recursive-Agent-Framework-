# RAF: Recursive Agent Framework

A recursive agent orchestration framework for any horizon-length agentic task. RAF implements a divide-and-conquer approach where tasks are recursively decomposed until they reach executable base cases, with multi-agent voting at each decision point.

## Design Dogmas

- **Signal-to-noise ratio optimization:** Each agent in the system handles as little noise and as much signal as possible. Context windows are minimized to only what's necessary for the current decision or execution.

- **Recursion:** Tasks are broken down into minimum-viable context windows. No context window should be used for something that would benefit from being split up.

- **Multi-Model:** The system improves with more model diversity. Heterogeneous model selection enables mixture-of-experts approaches, appropriate compute allocation per task, and epistemic diversity in decision-making.

- **Decision aggregation:** Critical decisions are voted on by agent juries. When decomposing a task, a consortium generates proposals, then a jury votes on the best option.

- **Strong output format enforcement:** All agent outputs conform to JSON schemas. This enables hard-coded validation logic and provides a reliable signal for detecting bad responses. Require strictly structured output JSON for all LLMs in the system to easily parse out tool responses and use hard-coded logic as much as possible.

## Core Architecture

### RafNode

The recursive execution unit. Each RafNode:

1. **Decides base case vs recursive case** via AgentJury vote
2. **If base case:** Designs and executes a focused single-step agent
3. **If recursive case:** Plans child nodes with optional inter-sibling dependencies

#### RafNode State

Stores information about what point of execution the node currently is, how how its running went.

#### RafNode Lifecycle

```
initialized → running → completed
     ↓
  wait for dependency resolution from parent
     ↓
  wait for dependent siblings (if any)
     ↓
  base_case_vote() → AgentJury decides
     ↓
  ├── base_case()      → design agent → execute → analyze
  └── recursive_case() → plan children → spawn RafNodes → analyze
```

### Agent

A single LLM instance configured with:

- **context:** Starting input (supports prompt caching via `cachedInput`)
- **tools:** MCP tool definitions available to the model
- **output_format:** JSON Schema for structured output
- **model:** LiteLLM model configuration (includes thinking level, verbosity)

Returns `AgentCallResult<T>` with success flag and typed JSON output.

### AgentCluster

Base class for agent groups. Manages:

- **agents:** Pool of agents (different models for diversity)
- **unified_output_format:** Schema all outputs must match
- **context:** Shared cached context for all members
- **size:** Number of parallel invocations

Supports input caching for cloud providers (via `cache_input_raw`/`cache_input_json`).

### AgentConsortium

Extends AgentCluster. Calls all agents and returns list of valid outputs (excluding format violations). Used to generate diverse proposals.

### AgentJury

Extends AgentCluster. Takes a list of options, has all agents vote, then aggregates votes to select winner.

- **options:** List of choices to vote on
- **ballot_format:** Schema for vote output
- **gather_votes():** Parallel vote collection
- **process_votes():** Vote aggregation algorithm (MVP: winner-takes-all)

## Execution Flow

### Base Case Flow

```
1. AgentConsortium generates agent designs
   - Each design: full agent config (tools, context, output format, success condition)
   - Designs should be single-step executors

2. AgentJury votes on best design

3. Agent executes the winning design

4. AgentJury votes on base agent success (separate from analysis)
   - Binary success/failure determination based on execution output

5. AgentConsortium analyzes execution result
   - Returns {success: boolean, info: string}

6. AgentJury votes on best analysis

7. Return nodeResult with analysis
```

### Recursive Case Flow

```
1. AgentConsortium generates decomposition plans
   - Each plan: list of childNodePlan objects

2. Filter out plans with circular sibling dependencies

3. AgentConsortium merges/concatenates similar plans
   - Merge identical/near-identical plans
   - Keep conflicting plans separate

4. AgentJury votes on best concatenation

5. AgentJury votes on best final plan from concatenation

6. Spawn child RafNodes with their contexts
   - Configure sibling dependencies per plan

7. Execute all children in parallel
   - Children with dependencies wait for dependent siblings

8. AgentConsortium analyzes combined child results

9. AgentJury votes on best analysis

10. Return nodeResult with child executions
```

### Sibling Dependencies

Child nodes can depend on sibling nodes' output:

```typescript
interface childNodePlan {
    context: ModelInput       // Starting context for this child
    name: string              // Identifier
    dependsOn: string[]       // Names of siblings to wait for
}
```

When a child has dependencies:
1. It waits for parent to call `set_dependencies()`
2. It awaits all dependent sibling promises
3. Dependent results are prepended to its context
4. Then it proceeds with base case/recursive decision

## Configuration

Key tunable parameters in jury/consortium configs:

```typescript
{
    agents: Agent[]        // Pool of agents (model diversity)
    format: JSONSchema     // Output schema
    context: string        // Base context
    max_temp?: number      // Temperature ceiling
    min_temp?: number      // Temperature floor
    size?: number          // Number of parallel calls
    options?: T[]          // Voting options (jury only)
}
```

### Context Window Optimization

Each node should use an ideal context window size—large enough to contain necessary information but small enough to maintain signal-to-noise ratio. Determining optimal context windows per node type is an open research question that should be tuned empirically.

## Entry Point

The root RafNode is instantiated with the initial task context and no parent. It has no dependencies to wait for and immediately proceeds to the base case vote.

```typescript
const root = new RafNode(taskContext)
const result = await root.call()
```

## Implementation Notes

- Use LiteLLM for model abstraction
- Use MCP for tool definitions
- Prompt caching reduces cost for repeated context
- All outputs are validated against JSON schemas before use
- Invalid outputs are filtered, not retried (consortium handles diversity)
- Circular dependency detection prevents deadlocks in sibling plans

## Benchmarking Variables

Independent variables for evaluating system performance:

- **Agent counts:** Number of voters and consortium agents per decision point
- **Compute allocation:** Total compute and compute diversity across voters and consortium members
- **Signal variability:** Diversity of signals/perspectives from consortium members
- **System prompt design:** Whether consortium members and voters include evaluation reasoning in their prompts (with or without going into eval on each step)

## Future Work

Potential post-MVP features and optimizations:

- **Voter trust tracking:** Track and weight voter reliability over time based on historical accuracy
- **Observable WAAS workspaces:** Provide visibility into agent workspace states for debugging and monitoring
- **Context clustering:** Cluster similar contexts for optimal instance reuse and routing
- **Prompt caching optimization:** Aggressive prompt caching for cost reduction in consortium calls and retries
- **MCTS RLtF:** Implement Monte Carlo Tree Search with Reinforcement Learning from Feedback for navigating larger proof/task stacks

### Tech Stack Considerations

- **LiteLLM/LiteLLM.rs:** Model abstraction layer (already planned)
- **V8/OS isolates:** Lightweight workspaces for agent execution
- **Rust/python:** Performance-critical paths
- **D3:** Visualization of execution trees and voting patterns
- **Langchain → Langgraph:** Agent orchestration primitives
- **Kubeflow:** ML pipeline orchestration for training/evaluation
- **Temporal:** Durable workflow execution for long-running tasks
