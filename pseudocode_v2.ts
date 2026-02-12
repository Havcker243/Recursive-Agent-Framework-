/// <reference lib="es2017" />

// RAF pseudocode v2: cleaned, explicit, cross-language description.
// This file is TypeScript-valid but intentionally non-executable.
// All external integrations (LLM calls, tool resolution, caching) are placeholders.

// Placeholder types for integration points.
type MCPTool = unknown

type JSONPrimitive = string | number | boolean | null
type JSONValue = JSONPrimitive | { [key: string]: JSONValue } | JSONValue[]
type JSONObject = { [key: string]: JSONValue }

type JSONSchema = JSONValue

type CachedInput = { cached: true; value: string | JSONValue }
type ModelIO = string | JSONValue | CachedInput

type BaseCaseDecision = "Base Case" | "Recursive Case"
type NodeState = "initialized" | "running" | "completed"

interface ModelAdapter {
    call: (model: ModelAdapter, tools: MCPTool[], outputSchema: JSONSchema, context: ModelIO) => Promise<ModelIO>
}

// Agent design spec is produced by an LLM (JSON-only). It must be compiled to a runtime AgentDesign.
type AgentDesignSpec = {
    [key: string]: JSONValue
    modelId: string
    toolIds: string[]
    outputSchema: JSONSchema
    context: JSONValue
}

// Runtime agent design with resolved tools/models.
interface AgentDesign {
    model: ModelAdapter
    tools: MCPTool[]
    outputSchema: JSONSchema
    context: ModelIO
}

type AnalysisResult = {
    [key: string]: JSONValue
    success: boolean
    info: string
}

// Child plan spec is produced by an LLM (JSON-only).
type ChildPlanSpec = {
    [key: string]: JSONValue
    name: string
    context: JSONValue
    dependsOn: string[]
}

interface NodeResult {
    name: string
    success?: boolean
    execSummary?: string
    childExecutions: { [name: string]: NodeResult }
}

interface DependencyLink {
    promise: Promise<NodeResult>
    nodes: RafNode[]
}

interface AgentCallResult {
    success: boolean
    json?: JSONValue
}

interface AgentClusterConfig {
    agents: Agent[]
    outputSchema: JSONSchema
    baseContext: string
    size?: number
    minTemp?: number
    maxTemp?: number
}

interface AgentJuryConfig extends AgentClusterConfig {
    options: JSONValue[]
}

interface RafConfig {
    baseCase: {
        decisionJury: AgentJuryConfig
        designConsortium: AgentClusterConfig
        designJury: AgentJuryConfig
    }
    recursiveCase: {
        planConsortium: AgentClusterConfig
        planMergeConsortium: AgentClusterConfig
        planMergeJury: AgentJuryConfig
        planJury: AgentJuryConfig
    }
    analysis: {
        consortium: AgentClusterConfig
        jury: AgentJuryConfig
    }
}

interface AgentDesignCompiler {
    compile: (spec: AgentDesignSpec) => AgentDesign
}

interface ChildContextResolver {
    resolve: (spec: JSONValue) => Promise<ModelIO>
}

interface PlanValidator {
    hasCircularDependency: (plan: ChildPlanSpec[]) => boolean
}

const BASE_CASE_OPTIONS: BaseCaseDecision[] = ["Base Case", "Recursive Case"]

const RAF_DEFAULT_CONFIG: RafConfig = {
    baseCase: {
        decisionJury: {
            minTemp: 0.1,
            maxTemp: 0.5,
            size: 10,
            agents: [],
            baseContext: "Is this a base case or recursive case?",
            options: BASE_CASE_OPTIONS,
            outputSchema: { type: "string" },
        },
        designConsortium: {
            minTemp: 0.1,
            maxTemp: 0.5,
            size: 10,
            agents: [],
            baseContext: "Design a base case executor agent",
            outputSchema: { type: "object" },
        },
        designJury: {
            minTemp: 0.1,
            maxTemp: 0.5,
            size: 10,
            agents: [],
            baseContext: "Vote on the best base case agent design",
            options: [],
            outputSchema: { type: "object" },
        },
    },
    recursiveCase: {
        planConsortium: {
            minTemp: 0.1,
            maxTemp: 0.5,
            size: 10,
            agents: [],
            baseContext: "Propose child plans that decompose the recursive case",
            outputSchema: { type: "array" },
        },
        planMergeConsortium: {
            minTemp: 0.1,
            maxTemp: 0.5,
            size: 10,
            agents: [],
            baseContext: "Union and merge similar plans; keep contradictory plans separate",
            outputSchema: { type: "array" },
        },
        planMergeJury: {
            minTemp: 0.1,
            maxTemp: 0.5,
            size: 10,
            agents: [],
            baseContext: "Vote on the best merged set of plans",
            options: [],
            outputSchema: { type: "array" },
        },
        planJury: {
            minTemp: 0.1,
            maxTemp: 0.5,
            size: 10,
            agents: [],
            baseContext: "Vote on the best final plan",
            options: [],
            outputSchema: { type: "array" },
        },
    },
    analysis: {
        consortium: {
            minTemp: 0.1,
            maxTemp: 0.5,
            size: 10,
            agents: [],
            baseContext: "Analyze the execution",
            outputSchema: { success: "boolean", info: "string" },
        },
        jury: {
            minTemp: 0.1,
            maxTemp: 0.5,
            size: 10,
            agents: [],
            baseContext: "Vote on the best analysis",
            options: [],
            outputSchema: { type: "object" },
        },
    },
}

const ModelIOUtils = {
    isCached(value: ModelIO): value is CachedInput {
        return typeof value === "object" && value !== null && (value as CachedInput).cached === true
    },

    async resolve(input: ModelIO | Promise<ModelIO>): Promise<ModelIO> {
        return Promise.resolve(input)
    },

    toString(value: ModelIO): string {
        if (typeof value === "string") return value
        if (ModelIOUtils.isCached(value)) {
            return typeof value.value === "string" ? value.value : JSON.stringify(value.value)
        }
        return JSON.stringify(value)
    },
}

const Validators = {
    isObject(value: JSONValue): value is JSONObject {
        return typeof value === "object" && value !== null && !Array.isArray(value)
    },

    isStringArray(value: JSONValue): value is string[] {
        return Array.isArray(value) && value.every((item) => typeof item === "string")
    },

    asBaseCaseDecision(value: JSONValue): BaseCaseDecision {
        if (value === "Base Case" || value === "Recursive Case") {
            return value
        }
        throw new Error("Invalid base case decision")
    },

    asAnalysisResult(value: JSONValue): AnalysisResult {
        if (Validators.isObject(value) && typeof value.success === "boolean" && typeof value.info === "string") {
            return { success: value.success, info: value.info }
        }
        throw new Error("Invalid analysis result")
    },

    asAgentDesignSpec(value: JSONValue): AgentDesignSpec {
        if (!Validators.isObject(value)) {
            throw new Error("Invalid agent design spec")
        }
        const modelId = value.modelId
        const toolIds = value.toolIds
        const outputSchema = value.outputSchema
        const context = value.context
        if (typeof modelId !== "string") throw new Error("Invalid agent design spec: modelId")
        if (!Validators.isStringArray(toolIds)) throw new Error("Invalid agent design spec: toolIds")
        if (outputSchema === undefined) throw new Error("Invalid agent design spec: outputSchema")
        if (context === undefined) throw new Error("Invalid agent design spec: context")
        return {
            modelId,
            toolIds,
            outputSchema: outputSchema as JSONSchema,
            context,
        }
    },

    asChildPlanSpec(value: JSONValue): ChildPlanSpec {
        if (!Validators.isObject(value)) throw new Error("Invalid child plan spec")
        const name = value.name
        const context = value.context
        const dependsOn = value.dependsOn
        if (typeof name !== "string") throw new Error("Invalid child plan spec: name")
        if (!Validators.isStringArray(dependsOn)) throw new Error("Invalid child plan spec: dependsOn")
        if (context === undefined) throw new Error("Invalid child plan spec: context")
        return { name, context, dependsOn }
    },

    asChildPlanList(value: JSONValue): ChildPlanSpec[] {
        if (!Array.isArray(value)) throw new Error("Invalid plan list")
        return value.map((item) => Validators.asChildPlanSpec(item as JSONValue))
    },

    asPlanListList(value: JSONValue): ChildPlanSpec[][] {
        if (!Array.isArray(value)) throw new Error("Invalid list of plans")
        return value.map((plan) => Validators.asChildPlanList(plan as JSONValue))
    },

    filterAgentDesignSpecs(values: JSONValue[]): AgentDesignSpec[] {
        const specs: AgentDesignSpec[] = []
        for (const value of values) {
            try {
                specs.push(Validators.asAgentDesignSpec(value))
            } catch {
                // ignore invalid
            }
        }
        return specs
    },

    filterAnalysisResults(values: JSONValue[]): AnalysisResult[] {
        const results: AnalysisResult[] = []
        for (const value of values) {
            try {
                results.push(Validators.asAnalysisResult(value))
            } catch {
                // ignore invalid
            }
        }
        return results
    },

    filterChildPlanLists(values: JSONValue[]): ChildPlanSpec[][] {
        const plans: ChildPlanSpec[][] = []
        for (const value of values) {
            try {
                plans.push(Validators.asChildPlanList(value))
            } catch {
                // ignore invalid
            }
        }
        return plans
    },

    filterPlanListLists(values: JSONValue[]): ChildPlanSpec[][][] {
        const planLists: ChildPlanSpec[][][] = []
        for (const value of values) {
            try {
                planLists.push(Validators.asPlanListList(value))
            } catch {
                // ignore invalid
            }
        }
        return planLists
    },
}

// One LLM instance.
class Agent {
    tools: MCPTool[]
    outputSchema: JSONSchema
    model: ModelAdapter
    context: ModelIO

    constructor(design: AgentDesign) {
        this.tools = design.tools
        this.outputSchema = design.outputSchema
        this.model = design.model
        this.context = design.context
    }

    private parseOutput(output: ModelIO): AgentCallResult {
        if (typeof output === "string") {
            try {
                return { success: true, json: JSON.parse(output) as JSONValue }
            } catch {
                return { success: false }
            }
        }

        if (ModelIOUtils.isCached(output)) {
            if (typeof output.value === "string") {
                try {
                    return { success: true, json: JSON.parse(output.value) as JSONValue }
                } catch {
                    return { success: false }
                }
            }
            return { success: true, json: output.value as JSONValue }
        }

        return { success: true, json: output as JSONValue }
    }

    async call(): Promise<AgentCallResult> {
        const raw = await this.model.call(this.model, this.tools, this.outputSchema, this.context)
        return this.parseOutput(raw)
    }
}

class AgentCluster {
    agents: Agent[]
    outputSchema: JSONSchema
    context: ModelIO
    size: number

    constructor(config: AgentClusterConfig) {
        this.agents = config.agents
        this.outputSchema = config.outputSchema
        this.context = config.baseContext
        this.size = config.size ?? config.agents.length
    }

    async cacheInputRaw(context: string): Promise<ModelIO> {
        return { cached: true, value: context }
    }

    async cacheInputJson(context: JSONValue): Promise<ModelIO> {
        return { cached: true, value: context }
    }

    async setContext(context: ModelIO | Promise<ModelIO>) {
        const resolved = await ModelIOUtils.resolve(context)
        if (ModelIOUtils.isCached(resolved)) {
            this.context = resolved
            return
        }

        if (typeof resolved === "string") {
            this.context = await this.cacheInputRaw(resolved)
        } else {
            this.context = await this.cacheInputJson(resolved)
        }
    }

    protected async callAll(): Promise<AgentCallResult[]> {
        if (this.agents.length === 0) {
            throw new Error("No agents available")
        }

        const members: Agent[] = []
        for (let i = 0; i < this.size; i += 1) {
            members.push(this.agents[i % this.agents.length])
        }

        const calls = members.map((agent) => {
            agent.outputSchema = this.outputSchema
            agent.context = this.context
            return agent.call()
        })

        return Promise.all(calls)
    }

    protected async callAllValid(): Promise<JSONValue[]> {
        const results = await this.callAll()
        const valid: JSONValue[] = []
        for (const result of results) {
            if (result.success && result.json !== undefined) {
                valid.push(result.json)
            }
        }
        return valid
    }
}

class AgentConsortium extends AgentCluster {
    constructor(config: AgentClusterConfig) {
        super(config)
    }

    async call(): Promise<JSONValue[]> {
        return this.callAllValid()
    }
}

class AgentJury extends AgentCluster {
    private options: JSONValue[]
    private baseContext: string

    constructor(config: AgentJuryConfig) {
        super(config)
        this.options = config.options
        this.baseContext = config.baseContext
    }

    async setOptions(options: JSONValue[]) {
        this.options = options
        await this.setContext(this.buildContext())
    }

    async setContextWithOptions(extraContext: ModelIO | Promise<ModelIO>) {
        const resolved = await ModelIOUtils.resolve(extraContext)
        const extra = ModelIOUtils.toString(resolved)
        await this.setContext(this.buildContext(extra))
    }

    private buildContext(extra?: string): string {
        const optionsText = this.options.map((o) => JSON.stringify(o)).join("\n")
        if (extra) {
            return `${this.baseContext}\n${optionsText}\n${extra}`
        }
        return `${this.baseContext}\n${optionsText}`
    }

    private processVotes(votes: AgentCallResult[]): JSONValue {
        for (const vote of votes) {
            if (vote.success && vote.json !== undefined) {
                return vote.json
            }
        }
        if (this.options.length > 0) {
            return this.options[0]
        }
        throw new Error("No valid votes to process")
    }

    async doVoting(): Promise<JSONValue> {
        const votes = await this.callAll()
        return this.processVotes(votes)
    }
}

class DefaultPlanValidator implements PlanValidator {
    hasCircularDependency(_plan: ChildPlanSpec[]): boolean {
        return false
    }
}

class DefaultContextResolver implements ChildContextResolver {
    async resolve(spec: JSONValue): Promise<ModelIO> {
        return spec
    }
}

class DefaultDesignCompiler implements AgentDesignCompiler {
    compile(spec: AgentDesignSpec): AgentDesign {
        return {
            model: {} as ModelAdapter,
            tools: [],
            outputSchema: spec.outputSchema,
            context: spec.context,
        }
    }
}

class RafEngine {
    private config: RafConfig
    private compiler: AgentDesignCompiler
    private contextResolver: ChildContextResolver
    private planValidator: PlanValidator

    constructor(
        config: RafConfig = RAF_DEFAULT_CONFIG,
        compiler: AgentDesignCompiler = new DefaultDesignCompiler(),
        contextResolver: ChildContextResolver = new DefaultContextResolver(),
        planValidator: PlanValidator = new DefaultPlanValidator()
    ) {
        this.config = config
        this.compiler = compiler
        this.contextResolver = contextResolver
        this.planValidator = planValidator
    }

    createRoot(context: ModelIO, name: string = "root"): RafNode {
        return new RafNode(this, context, undefined, name)
    }

    createChild(context: ModelIO, parent: RafNode, name: string): RafNode {
        return new RafNode(this, context, parent, name)
    }

    getConfig(): RafConfig {
        return this.config
    }

    getCompiler(): AgentDesignCompiler {
        return this.compiler
    }

    getContextResolver(): ChildContextResolver {
        return this.contextResolver
    }

    getPlanValidator(): PlanValidator {
        return this.planValidator
    }
}

class RafNode {
    private engine: RafEngine
    private parent?: RafNode
    private dependencies: Promise<DependencyLink[]>
    private resolveDependencies: (value: DependencyLink[] | PromiseLike<DependencyLink[]>) => void

    name: string
    state: NodeState
    context: ModelIO
    children: { [name: string]: RafNode }
    result: NodeResult

    constructor(engine: RafEngine, context: ModelIO, parent?: RafNode, name: string = "root") {
        this.engine = engine
        this.context = context
        this.parent = parent
        this.name = name
        this.state = "initialized"
        this.children = {}
        this.result = { name: this.name, childExecutions: {} }
        this.resolveDependencies = () => {}
        this.dependencies = parent
            ? new Promise<DependencyLink[]>((resolve) => {
                  this.resolveDependencies = resolve
              })
            : Promise.resolve([])
    }

    setDependencies(dependencies: DependencyLink[]) {
        this.resolveDependencies(dependencies)
    }

    private async applyDependencyContext() {
        const dependencies = await this.dependencies
        if (dependencies.length === 0) return

        const dependentResults = await Promise.all(dependencies.map((dep) => dep.promise))
        const dependencyContext = JSON.stringify(dependentResults)
        this.context = `Dependency executions: ${dependencyContext}\n${ModelIOUtils.toString(this.context)}`
    }

    private async decideBaseCase(): Promise<boolean> {
        const config = this.engine.getConfig().baseCase.decisionJury
        const jury = new AgentJury(config)
        await jury.setOptions(config.options)
        await jury.setContextWithOptions(this.context)
        const decisionValue = await jury.doVoting()
        const decision = Validators.asBaseCaseDecision(decisionValue)
        return decision === "Base Case"
    }

    private async executeBaseCase(): Promise<NodeResult> {
        const config = this.engine.getConfig()

        const designConsortium = new AgentConsortium(config.baseCase.designConsortium)
        const designJury = new AgentJury(config.baseCase.designJury)
        const analysisConsortium = new AgentConsortium(config.analysis.consortium)
        const analysisJury = new AgentJury(config.analysis.jury)

        const designCandidates = await designConsortium.call()
        const designSpecs = Validators.filterAgentDesignSpecs(designCandidates)
        if (designSpecs.length === 0) {
            throw new Error("No valid agent designs produced")
        }

        await designJury.setOptions(designSpecs)
        const designValue = await designJury.doVoting()
        const designSpec = Validators.asAgentDesignSpec(designValue)
        const design = this.engine.getCompiler().compile(designSpec)

        const baseCaseAgent = new Agent(design)
        const output = await baseCaseAgent.call()
        if (!output.success || output.json === undefined) {
            throw new Error("Base case agent failed to produce valid output")
        }

        await analysisConsortium.setContext(output.json)
        const analysisCandidates = await analysisConsortium.call()
        const analyses = Validators.filterAnalysisResults(analysisCandidates)
        if (analyses.length === 0) {
            throw new Error("No valid analysis produced")
        }

        await analysisJury.setOptions(analyses)
        const analysisValue = await analysisJury.doVoting()
        const analysis = Validators.asAnalysisResult(analysisValue)

        return { name: this.name, success: analysis.success, execSummary: analysis.info, childExecutions: {} }
    }

    private async executeRecursiveCase(): Promise<NodeResult> {
        const config = this.engine.getConfig()
        const validator = this.engine.getPlanValidator()
        const contextResolver = this.engine.getContextResolver()

        const planConsortium = new AgentConsortium(config.recursiveCase.planConsortium)
        const planMergeConsortium = new AgentConsortium(config.recursiveCase.planMergeConsortium)
        const planMergeJury = new AgentJury(config.recursiveCase.planMergeJury)
        const planJury = new AgentJury(config.recursiveCase.planJury)

        const analysisConsortium = new AgentConsortium(config.analysis.consortium)
        const analysisJury = new AgentJury(config.analysis.jury)

        const planCandidateValues = await planConsortium.call()
        const candidatePlans = Validators.filterChildPlanLists(planCandidateValues)
        const filteredPlans = candidatePlans.filter((plan) => !validator.hasCircularDependency(plan))
        if (filteredPlans.length === 0) {
            throw new Error("No valid recursive plans produced")
        }

        await planMergeConsortium.setContext(filteredPlans)
        const mergedPlanValues = await planMergeConsortium.call()
        const mergedPlanOptions = Validators.filterPlanListLists(mergedPlanValues)
        if (mergedPlanOptions.length === 0) {
            throw new Error("No valid merged plans produced")
        }

        await planMergeJury.setOptions(mergedPlanOptions)
        const mergedValue = await planMergeJury.doVoting()
        const mergedPlans = Validators.asPlanListList(mergedValue)

        await planJury.setOptions(mergedPlans)
        const planValue = await planJury.doVoting()
        const plan = Validators.asChildPlanList(planValue)

        const dependencyMap: { [name: string]: string[] } = {}
        for (const childPlan of plan) {
            const resolvedContext = await contextResolver.resolve(childPlan.context)
            this.children[childPlan.name] = this.engine.createChild(resolvedContext, this, childPlan.name)
            dependencyMap[childPlan.name] = childPlan.dependsOn
        }

        const childPromises: { [name: string]: Promise<NodeResult> } = {}
        for (const childName in this.children) {
            childPromises[childName] = this.children[childName].call()
        }

        for (const childName in this.children) {
            const deps = dependencyMap[childName] || []
            const links: DependencyLink[] = []
            for (const depName of deps) {
                const depNode = this.children[depName]
                if (!depNode) continue
                links.push({ promise: childPromises[depName], nodes: [depNode] })
            }
            this.children[childName].setDependencies(links)
        }

        const results: { [name: string]: NodeResult } = {}
        const childPromiseList: Array<Promise<NodeResult>> = []
        for (const childName in childPromises) {
            childPromiseList.push(childPromises[childName])
        }
        const allResults = await Promise.all(childPromiseList)
        for (const childResult of allResults) {
            results[childResult.name] = childResult
        }

        const summaries = Object.keys(results)
            .map((name) => `${name}: ${results[name].execSummary ?? ""}`)
            .join("\n")

        await analysisConsortium.setContext(summaries)
        const analysisCandidates = await analysisConsortium.call()
        const analyses = Validators.filterAnalysisResults(analysisCandidates)
        if (analyses.length === 0) {
            throw new Error("No valid analysis produced")
        }

        await analysisJury.setOptions(analyses)
        const analysisValue = await analysisJury.doVoting()
        const analysis = Validators.asAnalysisResult(analysisValue)

        return { name: this.name, success: analysis.success, execSummary: analysis.info, childExecutions: results }
    }

    async call(): Promise<NodeResult> {
        await this.applyDependencyContext()
        this.state = "running"

        const result = (await this.decideBaseCase()) ? await this.executeBaseCase() : await this.executeRecursiveCase()

        this.state = "completed"
        this.result = result
        return result
    }
}
