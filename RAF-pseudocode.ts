//placeholder types
type MCPTool = any
type JSONSchema = any
type LiteLLMModel = any
type TokenStream = any

//Independent variables to test via benchmarks
const BASE_CASE_JURY_CONFIG = {  max_temp: 0.5, min_temp: 0.1, size: 10, agents: [] } // agents: [] is a placeholder, example of the current set of agents being tested. Can have 1 or more agents. Test impacts of average compute level and compute level diversity. 
const BASE_CASE_CONSORTIUM_CONFIG = {  max_temp: 0.5, min_temp: 0.1, size: 10, agents: [] }
const BASE_CASE_CONSORTIUM_JURY_CONFIG = { max_temp: 0.5, min_temp: 0.1, size: 10, agents: [] }
const RECURSIVE_CASE_PLAN_CONSORTIUM_CONFIG = { max_temp: 0.5, min_temp: 0.1, size: 10, agents: [] }
const RECURSIVE_CASE_PLAN_CONCAT_CONSORTIUM_CONFIG = { max_temp: 0.5, min_temp: 0.1, size: 10, agents: [] }
//etc.

interface nodeResult {
    baseCase: boolean | unknown
    success: boolean | unknown
    resultSummary: string | unknown
}

// The recursive function behind the RAF.
class RafNode {
    // The result of the RAF node execution, and any relevant details about the success or failure for debugging purposes and context any nodes that are waiting for this node to complete.
    result: nodeResult
    state: "initialized" | "running" | "completed"
    children: RafNode[]

    constructor() {
        this.state = "initialized"
        this.result = { baseCase: false, success: false, resultSummary: "" }
        this.children = []
    }

    base_case_vote(agents: Agent[]) {
        const options = ["Base Case", "Recursive Case"]
        const context = "Is this a base case or a recursive case?"
        const output_format = 
        
        new AgentJury(context, options, agents)
    }

    call(agents: Agent[]): nodeResult {
        this.state = "running"



        return this.result;
    }
}

// One LLM instance.
class Agent {
    // The starting context that is passed to the LLM that's already cached, if the model is running on a cloud provider that supports input token caching.
    cached_starting_input_tokens: string | undefined
    // The starting context that is passed to the LLM.
    starting_input_tokens: string | undefined
    // The list of tools that are available to the LLM.
    tools: MCPTool[]
    //could use pedantic, JSON schema using schema.org, etc. Choose something that even small models could adhere to.
    // A JSON Schema that describes the expected output format of the LLM call.
    output_format: JSONSchema //could have | undefined, but one of the core design dogmas is to always require structured output
    // The model that is being used by the agent. Use LiteLLM for this, and type should be a valid LiteLLM model with config options such as thinking level and verbosity.
    model: LiteLLMModel

    constructor(tools: MCPTool[], output_format: JSONSchema, model: LiteLLMModel) {
        this.tools = tools
        this.output_format = output_format
        this.model = model
    }

    call(): TokenStream {
        return this.model.call(this.model, this.tools, this.output_format, this.cached_starting_input_tokens);
    }
}

class AgentCluster {
    // A list of agent objects that can be used in the cluster. Multiple could be passed for agent diversity. All must share the same output format. Part of function will be a for each loop over the agents setting agent.output_format to args.unified_output_format.
    agents: Agent[]
    // The unified output format that all agents in the cluster must use.
    unified_output_format: JSONSchema
    //shared context for all cluster members
    context: string
    //number of members
    size: number

    constructor(agents: Agent[], unified_output_format: JSONSchema, context: string) {
        this.agents = agents
        this.unified_output_format = unified_output_format
        this.context = cache_input_tokens_if_possible(context)
        this.size = agents.length
    }
}

// A group of agents that, given a set of parameters (for example a task spec, list of tools, and output format), return a list of each output that each agent in the consortium produces, excluding the outputs that don't match the expected output format.
class AgentConsortium extends AgentCluster {
    constructor(context: string, agents: Agent[], unified_output_format: JSONSchema) {
        super(agents, unified_output_format, context)
    }

    call(): TokenStream[] {
        return []
    }
}

// A consortium of agents that vote on options from a list. Expriment with different voting methods.
class AgentJury extends AgentCluster {
    // A list of options to be voted on by the agents.
    options: string[]
    ballot_format: JSONSchema

    constructor(context: string, options: string[], agents: Agent[]) {
        const ballot_format = {} // MVP can just be index of selected vote or ranked choice where winner is computed

        super(agents, ballot_format, context + options.join("\n")) // not the real logic just a basic representation)
        this.options = options
    }

    gather_votes(): object[] { //MVP example, just uses "voters choose one, winner takes all" system and returns index of selected option, will be replaced with more advanced algorithm.
        const members: Agent[] = Array.from({ length: this.size }, (_, i) => this.agents[i % this.agents.length]);
        const votes: object[] = []

        for (const member of members) {
            member.output_format = this.unified_output_format
            member.starting_input_tokens = this.context

            votes.push(verify_agent_output(member.call(), this.unified_output_format))
        }

        return votes
    }
}

// A group of agents that, given a task, context, list of tools, and output format, generate a list of potential base case executor agent designs. A base case excecutor agent design is a full agent starting context window, including system prompt with task spec context, tooling, success condition, and output format, which includes all context nescessary to start excecution immediately. It should have a very focused context window, with very clear instructions, only the tools it will use, and should excecute only one step. Multiple steps should be split between sequential sibling recursive nodes.
class BaseCaseAgentDesignConsortium extends AgentConsortium {

}
function cache_input_tokens_if_possible(tokens: any): any { //placeholder for prompt caching on cloud hosted models. In this pseudocode this method returns a pointer to cached tokens or the tokens themselves if caching is unavailable, both of which the agent object accepts.
    return
}

function verify_agent_output(output: any, expected_format: JSONSchema): object { //placeholder, use pydantic or similar
    return {}
}