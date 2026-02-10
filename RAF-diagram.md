# RAF Algorithm Diagrams

## Figure 1: RafNode Execution Flow

```mermaid
flowchart TB
    subgraph entry ["Entry Point"]
        START([Task Input]) --> INIT[Initialize RafNode]
    end

    subgraph deps ["Dependency Resolution"]
        INIT --> WAIT_DEPS{Has Parent?}
        WAIT_DEPS -->|Yes| AWAIT_DEPS[Await dependency<br/>configuration]
        WAIT_DEPS -->|No| AWAIT_SIBS
        AWAIT_DEPS --> AWAIT_SIBS[Await dependent<br/>sibling results]
        AWAIT_SIBS --> MERGE_CTX[Merge sibling results<br/>into context]
    end

    subgraph decision ["Base Case Decision"]
        MERGE_CTX --> VOTE_BC[/"AgentJury<br/>Base Case Vote"/]
        VOTE_BC --> BC_DEC{Base Case?}
    end

    subgraph basecase ["Base Case Execution"]
        BC_DEC -->|Yes| DESIGN_CON[/"AgentConsortium<br/>Generate Agent Designs"/]
        DESIGN_CON --> DESIGN_JURY[/"AgentJury<br/>Select Best Design"/]
        DESIGN_JURY --> EXEC_AGENT[Execute Agent]
        EXEC_AGENT --> ANAL_CON[/"AgentConsortium<br/>Analyze Result"/]
        ANAL_CON --> ANAL_JURY[/"AgentJury<br/>Vote on Analysis"/]
        ANAL_JURY --> BC_RESULT[Return nodeResult]
    end

    subgraph recursive ["Recursive Case Execution"]
        BC_DEC -->|No| PLAN_CON[/"AgentConsortium<br/>Generate Decomposition Plans"/]
        PLAN_CON --> FILTER[Filter Circular<br/>Dependencies]
        FILTER --> CONCAT_CON[/"AgentConsortium<br/>Merge Similar Plans"/]
        CONCAT_CON --> CONCAT_JURY[/"AgentJury<br/>Select Best Merge"/]
        CONCAT_JURY --> PLAN_JURY[/"AgentJury<br/>Select Final Plan"/]
        PLAN_JURY --> SPAWN[Spawn Child RafNodes]
        SPAWN --> CONFIG_DEPS[Configure Sibling<br/>Dependencies]
        CONFIG_DEPS --> PARALLEL[Execute Children<br/>in Parallel]
        PARALLEL --> CHILD_RESULTS[Collect Child Results]
        CHILD_RESULTS --> REC_ANAL_CON[/"AgentConsortium<br/>Analyze Combined Results"/]
        REC_ANAL_CON --> REC_ANAL_JURY[/"AgentJury<br/>Vote on Analysis"/]
        REC_ANAL_JURY --> REC_RESULT[Return nodeResult]
    end

    BC_RESULT --> DONE([Complete])
    REC_RESULT --> DONE

    style VOTE_BC fill:#e1f5fe
    style DESIGN_CON fill:#fff3e0
    style DESIGN_JURY fill:#e1f5fe
    style ANAL_CON fill:#fff3e0
    style ANAL_JURY fill:#e1f5fe
    style PLAN_CON fill:#fff3e0
    style CONCAT_CON fill:#fff3e0
    style CONCAT_JURY fill:#e1f5fe
    style PLAN_JURY fill:#e1f5fe
    style REC_ANAL_CON fill:#fff3e0
    style REC_ANAL_JURY fill:#e1f5fe
```

## Figure 2: Class Hierarchy

```mermaid
classDiagram
    class Agent~T~ {
        +ModelIO context
        +MCPTool[] tools
        +JSONSchema output_format
        +LiteLLMModel model
        +call() AgentCallResult~T~
        -validate_output(output, schema)
    }

    class AgentCluster~T~ {
        +Agent~T~[] agents
        +JSONSchema unified_output_format
        +ModelIO context
        +int size
        +set_context(context)
        +cache_input_raw(context)
        +cache_input_json(context)
        +call() T[]
    }

    class AgentConsortium~T~ {
        +call() T[]
    }

    class AgentJury~T~ {
        +T[] options
        +JSONSchema ballot_format
        +string base_context
        +set_options(options)
        +gather_votes() AgentCallResult~T~[]
        +process_votes(votes) T
        +do_voting() T
    }

    class RafNode {
        +nodeResult result
        +string state
        +RafNode[] children
        +ModelIO context
        +RafNode parent
        +Promise dependencies
        +string name
        +base_case_vote() boolean
        +base_case() nodeResult
        +recursive_case() nodeResult
        +set_dependencies(deps)
        +has_circular_dependency(plan)
        +call() nodeResult
    }

    AgentCluster <|-- AgentConsortium
    AgentCluster <|-- AgentJury
    RafNode o-- RafNode : children
    RafNode ..> AgentConsortium : uses
    RafNode ..> AgentJury : uses
    RafNode ..> Agent : spawns
```

## Figure 3: Sibling Dependency Model

```mermaid
flowchart LR
    subgraph parent ["Parent RafNode"]
        P[Recursive Case]
    end

    subgraph children ["Child RafNodes"]
        A[Child A]
        B[Child B]
        C[Child C]
        D[Child D]
    end

    P -->|spawns| A
    P -->|spawns| B
    P -->|spawns| C
    P -->|spawns| D

    A -.->|dependsOn| B
    A -.->|dependsOn| C
    D -.->|dependsOn| C

    subgraph execution ["Execution Order"]
        direction TB
        E1[B, C execute immediately]
        E2[A waits for B, C]
        E3[D waits for C]
        E4[A, D execute after deps]
        E1 --> E2 --> E3 --> E4
    end

    style A fill:#ffcdd2
    style D fill:#ffcdd2
    style B fill:#c8e6c9
    style C fill:#c8e6c9
```

## Figure 4: Consortium-Jury Pattern

```mermaid
flowchart LR
    subgraph consortium ["AgentConsortium (Divergent)"]
        direction TB
        C1[Agent 1<br/>Model A]
        C2[Agent 2<br/>Model B]
        C3[Agent 3<br/>Model C]
        CN[Agent N<br/>...]
    end

    subgraph proposals ["Proposals"]
        P1[Proposal 1]
        P2[Proposal 2]
        P3[Proposal 3]
        PN[...]
    end

    subgraph jury ["AgentJury (Convergent)"]
        direction TB
        J1[Voter 1]
        J2[Voter 2]
        J3[Voter 3]
        JN[Voter N]
    end

    INPUT([Context]) --> C1 & C2 & C3 & CN
    C1 --> P1
    C2 --> P2
    C3 --> P3
    CN --> PN

    P1 & P2 & P3 & PN --> J1 & J2 & J3 & JN

    J1 & J2 & J3 & JN --> AGG[Vote Aggregation]
    AGG --> OUTPUT([Selected Option])

    style consortium fill:#fff3e0
    style jury fill:#e1f5fe
```

## Figure 5: Recursive Tree Structure

```mermaid
flowchart TB
    subgraph level0 ["Level 0"]
        ROOT[RafNode: root<br/>Recursive Case]
    end

    subgraph level1 ["Level 1"]
        L1A[RafNode: parse<br/>Base Case]
        L1B[RafNode: process<br/>Recursive Case]
        L1C[RafNode: format<br/>Base Case]
    end

    subgraph level2 ["Level 2"]
        L2A[RafNode: validate<br/>Base Case]
        L2B[RafNode: transform<br/>Base Case]
        L2C[RafNode: aggregate<br/>Base Case]
    end

    ROOT --> L1A
    ROOT --> L1B
    ROOT --> L1C

    L1B --> L2A
    L1B --> L2B
    L1B --> L2C

    L1C -.->|depends on| L1B

    style L1A fill:#c8e6c9
    style L1C fill:#c8e6c9
    style L2A fill:#c8e6c9
    style L2B fill:#c8e6c9
    style L2C fill:#c8e6c9
    style ROOT fill:#bbdefb
    style L1B fill:#bbdefb
```

---

**Legend:**
- 🟦 Blue nodes: AgentJury (voting/convergent)
- 🟧 Orange nodes: AgentConsortium (proposal/divergent)
- 🟩 Green nodes: Base Case (execution)
- 🟦 Light blue nodes: Recursive Case (decomposition)
- ⋯⋯ Dashed lines: Dependencies
