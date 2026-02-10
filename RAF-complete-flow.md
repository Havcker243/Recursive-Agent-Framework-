# RAF Complete Algorithm Flow

This diagram shows all steps and agent clusters in the Recursive Agent Framework.

## Complete Flow Diagram

```mermaid
flowchart TB
    subgraph input ["INPUT"]
        TASK[/"Task + Context"/]
    end

    subgraph baseDecision ["1. BASE CASE DECISION"]
        direction TB
        BC_CON["🔷 AgentConsortium<br/><i>Generate base/recursive proposals</i>"]
        BC_JURY["🗳️ AgentJury<br/><i>Vote: Base Case or Recursive?</i>"]
        BC_CON --> BC_JURY
    end

    subgraph baseCase ["2. BASE CASE EXECUTION"]
        direction TB
        
        subgraph design ["2a. Agent Design"]
            DESIGN_CON["🔷 AgentConsortium<br/><i>Generate executor agent designs</i><br/>(tools, context, output format)"]
            DESIGN_JURY["🗳️ AgentJury<br/><i>Vote: Best agent design?</i>"]
            DESIGN_CON --> DESIGN_JURY
        end
        
        subgraph execute ["2b. Execution"]
            EXECUTOR["⚡ Agent<br/><i>Execute single-step task</i>"]
        end
        
        subgraph success ["2c. Success Decision"]
            SUCCESS_CON["🔷 AgentConsortium<br/><i>Analyze execution output</i>"]
            SUCCESS_JURY["🗳️ AgentJury<br/><i>Vote: Did it succeed?</i>"]
            SUCCESS_CON --> SUCCESS_JURY
        end
        
        design --> execute --> success
    end

    subgraph recursiveCase ["3. RECURSIVE CASE EXECUTION"]
        direction TB
        
        subgraph planning ["3a. Plan Generation"]
            PLAN_CON["🔷 AgentConsortium<br/><i>Generate decomposition plans</i><br/>(child tasks + dependencies)"]
        end
        
        subgraph filtering ["3b. Plan Processing"]
            FILTER["🔍 Filter<br/><i>Remove circular dependencies</i>"]
            CONCAT_CON["🔷 AgentConsortium<br/><i>Merge similar plans</i>"]
            CONCAT_JURY["🗳️ AgentJury<br/><i>Vote: Best merge?</i>"]
            FILTER --> CONCAT_CON --> CONCAT_JURY
        end
        
        subgraph selection ["3c. Plan Selection"]
            PLAN_JURY["🗳️ AgentJury<br/><i>Vote: Best final plan?</i>"]
        end
        
        subgraph spawn ["3d. Child Execution"]
            SPAWN["🌱 Spawn Child RafNodes<br/><i>Configure sibling dependencies</i>"]
            PARALLEL["⚡ Execute in Parallel<br/><i>Children wait on dependencies</i>"]
            SPAWN --> PARALLEL
        end
        
        subgraph recSuccess ["3e. Combined Success Decision"]
            REC_SUCCESS_CON["🔷 AgentConsortium<br/><i>Analyze combined child results</i>"]
            REC_SUCCESS_JURY["🗳️ AgentJury<br/><i>Vote: Overall success?</i>"]
            REC_SUCCESS_CON --> REC_SUCCESS_JURY
        end
        
        planning --> filtering --> selection --> spawn --> recSuccess
    end

    subgraph output ["OUTPUT"]
        RESULT[/"nodeResult<br/>{success, execSummary, childExecutions}"/]
    end

    TASK --> baseDecision
    BC_JURY -->|"Base Case"| baseCase
    BC_JURY -->|"Recursive"| recursiveCase
    SUCCESS_JURY --> RESULT
    REC_SUCCESS_JURY --> RESULT
    
    %% Recursive arrow
    PARALLEL -.->|"Each child is a RafNode"| baseDecision

    style BC_CON fill:#fff3e0
    style DESIGN_CON fill:#fff3e0
    style SUCCESS_CON fill:#fff3e0
    style PLAN_CON fill:#fff3e0
    style CONCAT_CON fill:#fff3e0
    style REC_SUCCESS_CON fill:#fff3e0
    
    style BC_JURY fill:#e3f2fd
    style DESIGN_JURY fill:#e3f2fd
    style SUCCESS_JURY fill:#e3f2fd
    style CONCAT_JURY fill:#e3f2fd
    style PLAN_JURY fill:#e3f2fd
    style REC_SUCCESS_JURY fill:#e3f2fd
    
    style EXECUTOR fill:#e8f5e9
```

## Agent Cluster Summary

| Step | Cluster Type | Purpose |
|------|-------------|---------|
| 1 | Consortium → Jury | Decide base case vs recursive |
| 2a | Consortium → Jury | Design executor agent |
| 2b | Agent | Execute task |
| 2c | Consortium → Jury | **Vote on success** (separate step) |
| 3a | Consortium | Generate decomposition plans |
| 3b | Consortium → Jury | Merge and select best plan merge |
| 3c | Jury | Select final plan |
| 3d | RafNodes | Spawn and execute children |
| 3e | Consortium → Jury | **Vote on combined success** |

## Legend

- 🔷 **AgentConsortium** (orange) — Multiple agents generating diverse proposals
- 🗳️ **AgentJury** (blue) — Multiple agents voting on best option  
- ⚡ **Agent/Execution** (green) — Single agent or parallel execution
- 🔍 **Filter** — Deterministic processing (no LLM)

## Key Design Decision: Separate Success Vote

The success determination is explicitly separated from execution:

1. **Executor runs** → produces raw output
2. **Success Consortium** → analyzes output, generates success assessments
3. **Success Jury** → votes on whether execution succeeded

This separation allows:
- Executor to focus purely on task completion
- Success criteria to be evaluated by fresh context
- Multiple perspectives on what constitutes success
- Clear audit trail of success reasoning
