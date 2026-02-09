// AI AGENTS: DO NOT MODIFY THIS FILE. It was written by hand as a ground truth for the RAF algorithm.

//placeholder types
type MCPTool = any
type JSONSchema = any
type LiteLLMModel = any
type cachedInput = any
type ModelIO = cachedInput | string // can be cached for cloud models that support input token caching, can also be a promise to wait on

interface childPlan {
    purpose: string
    parentPlan: parentPlan
    dependsOn: childPlan[] // pointers to siblings that this agent will wait for the output of (if the siblings in this list are successful)
}

interface parentPlan { // placeholder for recursive step plan data type. Includes information about task breakdown, which planned children are independent (async) or dependent on the output of a sibling or siblings, and control flow between dependent siblings
    parentPurpose: string // current node's purpose
    plannedChildren: childPlan[]
}

interface nodeResult {

}

//Independent variables to test via benchmarks
const BASE_CASE_JURY_CONFIG = {  max_temp: 0.5, min_temp: 0.1, size: 10, agents: [], context: "Is this a base case or recursive case?", options: [{}, {}], format: {} } // agents: [] is a placeholder, example of the current set of agents being tested. Can have 1 or more agents. Test impacts of average compute level and compute level diversity. 
const BASE_CASE_CONSORTIUM_CONFIG = { max_temp: 0.5, min_temp: 0.1, size: 10, agents: [], context: "Design base case agent", format: {} } // format for this will be agent config ready to be called, including tooling, starting context, success condition, and other custom required JSON output fields. Can even force strings to fit regex.
const BASE_CASE_CONSORTIUM_JURY_CONFIG = { max_temp: 0.5, min_temp: 0.1, size: 10, agents: [], context: "Vote on the best base case agent", options: [{}, {}], format: {} }
const BASE_CASE_ANALYSIS_CONSORTIUM_CONFIG = { max_temp: 0.5, min_temp: 0.1, size: 10, agents: [], context: "Analyze on this excecution", format: { "success" : "boolean", "info" : "string" } } // also just a placeholder to conceptually outline whats happening
const BASE_CASE_ANALYSIS_CONSORTIUM_JURY_CONFIG = { max_temp: 0.5, min_temp: 0.1, size: 10, agents: [], context: "Vote on the best analysis", options: [{}, {}], format: {} }

const RECURSIVE_CASE_PLAN_CONSORTIUM_CONFIG = { max_temp: 0.5, min_temp: 0.1, size: 10, agents: [], context: "Come up with a plan for decomposing this recursive case into next-smallest cases", format: {} } // format will be parentPlan
const RECURSIVE_CASE_PLAN_CONCAT_CONSORTIUM_CONFIG = { max_temp: 0.5, min_temp: 0.1, size: 10, agents: [], context: "Perform a union operation on all the proposed plans into a final list of proposed plans. Merge any plans that are identical or nearly identical. If any two parts of a plan conflict/are contradictory, then they are seperate plans and should not be merged", format: {} } // format is list of parentPlan
const RECURSIVE_CASE_PLAN_CONCAT_JURY_CONFIG = { max_temp: 0.5, min_temp: 0.1, size: 10, agents: [], context: "Vote on which concatenated list of plans best represents all the proposed plans", options: [{}, {}], format: {} }
const RECURSIVE_CASE_PLAN_JURY_CONFIG = { max_temp: 0.5, min_temp: 0.1, size: 10, agents: [], context: "Vote on which concatenated plan for breaking down this recursive case into next-smallest parts is the best", options: [{}, {}], format: {} }
//etc.

// The recursive function behind the RAF.
class RafNode {
    // The result of the RAF node execution, and any relevant details about the success or failure for debugging purposes and context any nodes that are waiting for this node to complete.
    result: nodeResult
    state: "initialized" | "running" | "completed"
    children: RafNode[]
    context: string

    constructor(context: string) {
        this.context = context
        this.state = "initialized"
        this.result = { baseCase: false, success: false, resultAnalysis: "" }
        this.children = []
    }

    async base_case_vote(): Promise<boolean> {
        return await new AgentJury(BASE_CASE_JURY_CONFIG).do_voting()
    }

    async base_case(): Promise<nodeResult> {
        const AgentDesignConsortium = new AgentConsortium(BASE_CASE_CONSORTIUM_CONFIG) // A group of agents that, given a task, context, list of tools, and output format, generate a list of potential base case executor agent designs. A base case excecutor agent design is a full agent starting context window, including system prompt with task spec context, tooling, success condition, and output format, which includes all context nescessary to start excecution immediately. It should have a very focused context window, with very clear instructions, only the tools it will use, and should excecute only one step. Multiple steps should be split between sequential sibling recursive nodes.
        const AgentDesignJury = new AgentJury(BASE_CASE_CONSORTIUM_JURY_CONFIG)
        const AnalysisConsortium = new AgentConsortium(BASE_CASE_ANALYSIS_CONSORTIUM_CONFIG)
        const AnalysisJury = new AgentJury(BASE_CASE_ANALYSIS_CONSORTIUM_JURY_CONFIG)

        await AgentDesignJury.set_options(await AgentDesignConsortium.call())

        const BaseCaseAgentDesign = await AgentDesignJury.do_voting()

        const out = await new Agent(BaseCaseAgentDesign.tools, BaseCaseAgentDesign.output_format, BaseCaseAgentDesign.model).call()

        await AnalysisConsortium.set_context(out)

        AnalysisJury.set_options(await AnalysisConsortium.call())

        const analysis = await AnalysisJury.do_voting()

        return { baseCase: true, success: analysis.success, resultAnalysis: analysis.info }
    }

    async recursive_case(): Promise<nodeResult> {
        const RecursiveCasePlanConsortium = new AgentConsortium(RECURSIVE_CASE_PLAN_CONSORTIUM_CONFIG)
        const RecursiveCasePlanConcatConsortium = new AgentConsortium(RECURSIVE_CASE_PLAN_CONCAT_CONSORTIUM_CONFIG)
        const RecursiveCasePlanConcatJury = new AgentJury(RECURSIVE_CASE_PLAN_CONCAT_JURY_CONFIG)
        const RecursiveCasePlanJury = new AgentJury(RECURSIVE_CASE_PLAN_JURY_CONFIG)

        const plans: parentPlan[] = await RecursiveCasePlanConsortium.call()

        // check for circular sibling dependencies and throw out plans that have circular dependence
        const plansWithoutCircularDeps = plans.filter(plan => !this.hasCircularDependency(plan));

        RecursiveCasePlanConcatConsortium.set_context(plans)

        const planConcatenations: parentPlan[][] = await RecursiveCasePlanConcatConsortium.call()

        await RecursiveCasePlanConcatJury.set_options(planConcatenations)
        const bestPlanConcatenation = await RecursiveCasePlanConcatJury.do_voting()

        await RecursiveCasePlanJury.set_options(bestPlanConcatenation)
        const bestPlan: parentPlan = await RecursiveCasePlanJury.do_voting()



        // TODO: start running independent children asynchronously, then run dependent siblings in the right order
    }
    hasCircularDependency(plan: parentPlan): boolean {
        return false // TODO: figure out this algorithm
    }

    async call(agents: Agent[]): Promise<nodeResult> {
        this.state = "running"

        return await this.base_case_vote() ? await this.base_case() : await this.recursive_case()
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

    async validate_output(output: any): Promise<any> { // code to convert raw model output into a structured response matching this.output_format. not needed for pseudocode.
        return {}
    }

    async call(): Promise<object> {
        return await this.validate_output(this.model.call(this.model, this.tools, this.output_format, this.cached_starting_input_tokens));
    }
}

class AgentCluster {
    // A list of agent objects that can be used in the cluster. Multiple could be passed for agent diversity. All must share the same output format. Part of function will be a for each loop over the agents setting agent.output_format to args.unified_output_format.
    agents: Agent[]
    // The unified output format that all agents in the cluster must use.
    unified_output_format: JSONSchema
    //shared context for all cluster members
    context: ModelIO
    //number of members
    size: number

    constructor(agents: Agent[], unified_output_format: JSONSchema, context: ModelIO) {
        this.agents = agents
        this.unified_output_format = unified_output_format
        this.context = this.cache_input(context)
        this.size = agents.length
    }

    async cache_input(context: ModelIO): Promise<ModelIO> { //placeholder for prompt caching on cloud hosted models. In this pseudocode this method returns a pointer to cached tokens or the tokens themselves if caching is unavailable, both of which the agent object accepts.
        return undefined as cachedInput as ModelIO
    }

    async set_context(context: ModelIO) {
        this.context = await this.cache_input(context)
    }

    async call(): Promise<any[]> {
        const rawResults: any[] = []
        for (const agent of this.agents) {
            agent.output_format = this.unified_output_format
            agent.starting_input_tokens = this.context
            rawResults.push(agent.call())
        }

        return Promise.all(rawResults)
    }
}

// A group of agents that, given a set of parameters (for example a task spec, list of tools, and output format), return a list of each output that each agent in the consortium produces, excluding the outputs that don't match the expected output format.
class AgentConsortium extends AgentCluster {
    constructor(config: { agents: Agent[], format: JSONSchema, context: string }) {
        super(config.agents, config.format, config.context)
    }
}

// A consortium of agents that vote on options from a list. Expriment with different voting methods.
class AgentJury extends AgentCluster {
    // A list of options to be voted on by the agents.
    options: object[]
    ballot_format: JSONSchema

    constructor(config: { max_temp: number, min_temp: number, size: number, agents: Agent[], context: string, options: object[], format: JSONSchema }) {
        super(config.agents, config.format, config.context + config.options.map(o => JSON.stringify(o)).join("\n"))
        this.options = config.options
    }

    async set_options(options: object[]) {
        this.options = await this.cache_input(options)
    }

    async gather_votes(): Promise<object[]> {
        const members: Agent[] = Array.from({ length: this.size }, (_, i) => this.agents[i % this.agents.length]);
        const votes: Promise<object>[] = []

        for (const member of members) {
            member.output_format = this.unified_output_format
            member.starting_input_tokens = this.context

            votes.push(member.call())
        }

        return Promise.all(votes)
    }

    process_votes(votes: object[]): any { // Pseudocode placeholder for vote selection algorithm. MVP can just use winner takes all voting. Down the road, could use advanced voting algorithms and voter self-improvement through tracking failiures and successes.
        return {}
    }

    async do_voting() {
        const votes = await this.gather_votes()
        return this.process_votes(votes)
    }
}

