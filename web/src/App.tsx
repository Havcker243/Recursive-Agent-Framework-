import { useEffect, useRef, useState, useCallback } from "react"
import Landing from "./Landing"
import type { PointerEvent } from "react"
import { motion, AnimatePresence } from "framer-motion"
import DOMPurify from "dompurify"
import { Zap, Network, Play, Square, Clock, Vote, FileText, Plus, Download, ZoomIn, ZoomOut, RotateCcw, History, SlidersHorizontal, Home } from "lucide-react"
import { Button } from "./components/ui/button"
import { Badge } from "./components/ui/badge"
import { ScrollArea } from "./components/ui/scroll-area"
import { Separator } from "./components/ui/separator"
import { Slider } from "./components/ui/slider"
import { Switch } from "./components/ui/switch"
import { Input } from "./components/ui/input"
import { Textarea } from "./components/ui/textarea"
import { Select } from "./components/ui/select"
import { Tabs, TabsList, TabsTrigger, TabsContent } from "./components/ui/tabs"
import { Card, CardContent } from "./components/ui/card"
import { ExecutionGraph, type GraphNode, type GraphEdge, type PhysicsParams, DEFAULT_PHYSICS } from "./components/ExecutionGraph"
import { PhysicsPanel } from "./components/PhysicsPanel"

// ── types ─────────────────────────────────────────────────────────────────────

type RafEvent = {
  event?: string; status?: string; node_id?: string; parent_id?: string | null
  depth?: number; goal?: string; output?: string; mode?: string; confidence?: number
  timestamp?: number; run_id?: string; error?: string; task?: string
  candidates?: unknown; options?: unknown; votes?: unknown; winner_id?: string
  children?: ChildSpec[]; result?: { output: string; metadata: { mode: string; questions?: string[]; confidence?: number } }
  question?: string; answer?: string; winner?: string; fast_path?: boolean; reason?: string
  domain?: string; required?: string[]; forbidden?: string[]; success_criteria?: string[]
  plan_child_id?: string; node_count?: number
  // plan recovery
  retry?: number; max_retries?: number; replaced_by?: string; plan_attempt?: number
  provider?: string; model?: string; role?: string; agent_index?: number
  duration_ms?: number; timeout_ms?: number
  cause?: "api_error" | "parse_error" | "schema_error"
}

type ChildSpec = { child_id: string; goal: string; depends_on: string[] }
type NodeOutput = { output: string; mode: string; confidence: number; goal?: string }
type AgentSlot = { provider: string; model: string }
type ModelInfo = { id: string; label?: string; family?: string; tags?: string[] }
type SessionConfig = {
  provider: string; model: string; juryModel: string
  consortiumSize: number; jurySize: number; maxDepth: number; maxParallelChildren: number; maxNodesTotal: number
  forceRecursive: boolean; planGovernance: "auto" | "review" | "manual"; planRecovery: "off" | "auto" | "ask"; toolsEnabled: boolean
  multiModel: boolean; consortiumSlots: AgentSlot[]; jurySlots: AgentSlot[]
  tierRouting: boolean; leafSlots: AgentSlot[]; midSlots: AgentSlot[]; rootSlots: AgentSlot[]
  domainOverride: string; systemPrompt: string
}
type Session = {
  id: string; goal: string; provider: string; providerLabel?: string; status: string
  ts: number; nodeCount: number; output?: string; domain?: string; runId?: string | null; runToken?: string | null
  currentPhase?: string
  config?: SessionConfig
  events?: RafEvent[]
  graphNodes?: GraphNode[]
  graphLinks?: GraphEdge[]
  nodeOutputs?: Record<string, NodeOutput>
  result?: string | null
}
type ServerRunSummary = {
  run_id: string
  goal: string
  provider: string
  model?: string | null
  status: string
  started_at: number
  completed_at?: number | null
  event_count: number
}

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8001"
const SESSION_STORAGE_KEY = "raf-web-sessions-v1"
const API_KEY_STORAGE_KEY = "raf-openrouter-api-key"
const DOMAIN_OPTIONS = ["", "technical", "culinary", "fitness", "creative", "business", "academic", "general"]

function authHeaders(runToken?: string | null, json = false): Record<string, string> {
  const headers: Record<string, string> = {}
  if (json) headers["Content-Type"] = "application/json"
  if (runToken) headers["X-Run-Token"] = runToken
  return headers
}

// ── Model strategy presets ─────────────────────────────────────────────────────
// Each preset is a named configuration that sets consortium + jury slots.
// The "fast-smart" pattern is the key insight: fast/cheap models generate
// diverse proposals in parallel (consortum), a single powerful model judges them (jury).
// This gives near-top-model quality at a fraction of the cost.
type ModelStrategy = {
  id: string
  label: string
  badge: string        // short label shown on the card
  tagline: string
  description: string
  consortiumNote: string
  midNote?: string     // shown only for tier-routing strategies (planner tier)
  juryNote: string
  multiModel: boolean
  consortiumSize: number
  jurySize: number
  consortiumSlots: AgentSlot[]
  jurySlots: AgentSlot[]
  tierRouting?: boolean
  leafSlots?: AgentSlot[]
  midSlots?: AgentSlot[]
  rootSlots?: AgentSlot[]
}

const MODEL_STRATEGIES: ModelStrategy[] = [
  {
    id: "uniform",
    label: "Uniform",
    badge: "simple",
    tagline: "One model, everywhere",
    description: "The same model generates all proposals and casts all votes. Simplest setup, easiest to debug.",
    consortiumNote: "Any capable model works. Try qwen/qwen3-next-80b-a3b-instruct:free or qwen/qwen3.5-35b-a3b for a free start.",
    juryNote: "Same model as consortium — no separate jury config needed.",
    multiModel: false,
    consortiumSize: 3,
    jurySize: 2,
    consortiumSlots: [],
    jurySlots: [],
  },
  {
    id: "fast-smart",
    label: "Fast + Smart",
    badge: "⭐ recommended",
    tagline: "Cheap proposers, powerful judge",
    description: "Fast, cheap models each propose a candidate answer in parallel (consortium). One strong reasoning model makes the final call (jury). Best quality-per-dollar — the jury only runs once per decision regardless of consortium size.",
    consortiumNote: "Use fast/free models — speed and diversity matter more than raw power for proposers.",
    juryNote: "Use a strong reasoning model — it only runs once per decision, so cost is low.",
    multiModel: true,
    consortiumSize: 4,
    jurySize: 1,
    consortiumSlots: [
      { provider: "openrouter", model: "google/gemma-4-26b-a4b-it:free" },
      { provider: "openrouter", model: "qwen/qwen3.5-9b" },
      { provider: "openrouter", model: "qwen/qwen3-next-80b-a3b-instruct:free" },
      { provider: "openrouter", model: "meta-llama/llama-3.2-3b-instruct:free" },
    ],
    jurySlots: [
      { provider: "openrouter", model: "moonshotai/kimi-k2-thinking" },
    ],
  },
  {
    id: "ensemble",
    label: "Full Ensemble",
    badge: "high quality",
    tagline: "Diverse families propose, diverse judges vote",
    description: "Different model families write proposals, different families vote. Cross-family consensus is hard to fool — best for adversarial or high-stakes tasks where you want maximum independence between proposers and judges.",
    consortiumNote: "Mix model families: coding model, reasoning model, general model. Family diversity beats raw size.",
    juryNote: "Mix jury families too. Three independent reasoning judges from different labs rarely all agree on a bad answer.",
    multiModel: true,
    consortiumSize: 4,
    jurySize: 4,
    consortiumSlots: [
      { provider: "openrouter", model: "mistralai/devstral-2512" },
      { provider: "openrouter", model: "qwen/qwen3.5-35b-a3b" },
      { provider: "openrouter", model: "google/gemma-4-26b-a4b-it:free" },
      { provider: "openrouter", model: "mistralai/mistral-nemo" },
    ],
    jurySlots: [
      { provider: "openrouter", model: "moonshotai/kimi-k2-thinking" },
      { provider: "openrouter", model: "x-ai/grok-4.1-fast" },
      { provider: "openrouter", model: "z-ai/glm-5.1" },
      { provider: "openrouter", model: "openai/gpt-oss-120b:free" },
    ],
  },
  {
    id: "tiered",
    label: "Tiered Routing",
    badge: "depth-aware",
    tagline: "Right model for the right depth",
    description: "Small fast models handle deep leaf workers, capable models handle mid-level planning and synthesis, and the strongest models serve as the final referee (root node + analysis). Saves cost without sacrificing quality where it matters.",
    consortiumNote: "Leaf workers use fast/free models — speed and diversity matter more than raw power for simple subtasks.",
    midNote: "Planners and mergers use capable mid-tier models — structured reasoning for decomposition and synthesis.",
    juryNote: "Root and analysis (referee) always use the strongest models. Mid-tier also serves as jury floor so weak models never grade weak models.",
    multiModel: true,
    tierRouting: true,
    consortiumSize: 2,
    jurySize: 1,
    consortiumSlots: [],
    jurySlots: [],
    leafSlots: [
      { provider: "openrouter", model: "google/gemma-4-26b-a4b-it:free" },
      { provider: "openrouter", model: "qwen/qwen3.5-9b" },
      { provider: "openrouter", model: "meta-llama/llama-3.2-3b-instruct:free" },
    ],
    midSlots: [
      { provider: "openrouter", model: "mistralai/devstral-2512" },
      { provider: "openrouter", model: "qwen/qwen3.5-35b-a3b" },
      { provider: "openrouter", model: "mistralai/mistral-nemo" },
    ],
    rootSlots: [
      { provider: "openrouter", model: "moonshotai/kimi-k2-thinking" },
      { provider: "openrouter", model: "x-ai/grok-4.1-fast" },
      { provider: "openrouter", model: "openai/gpt-oss-120b:free" },
    ],
  },
]

const EVENT_COLORS: Record<string, string> = {
  node_created: "#3b82f6", node_done: "#22c55e", jury_votes: "#a855f7",
  consortium_candidates: "#f59e0b", run_done: "#64748b", mode_decided: "#06b6d4",
  base_execute_start: "#f97316", base_execute_done: "#10b981", clarify_answered: "#3b82f6",
  spec_extracted: "#8b5cf6", scope_drift_detected: "#ef4444", tool_called: "#ef4444",
  plan_validation_failed: "#f97316", plan_retry_start: "#fb923c", plan_retry_done: "#22c55e",
  plan_abandoned: "#ef4444", plan_replaced: "#a3e635",
  model_call_start: "#38bdf8", model_call_done: "#22c55e", model_call_failed: "#ef4444",
  model_call_timeout: "#f59e0b", model_call_fallback: "#a855f7",
}

// Tier badge display helpers
const TIER_LABELS: Record<number, { label: string; className: string }> = {
  0: { label: "T0·Leaf",    className: "bg-sky-950/60 text-sky-300" },
  1: { label: "T1·Plan",   className: "bg-amber-950/60 text-amber-300" },
  2: { label: "T2·Ref",    className: "bg-rose-950/60 text-rose-300" },
}
function tierBadge(tier: number | undefined): JSX.Element | null {
  if (tier === undefined || tier === null) return null
  const t = TIER_LABELS[tier]
  if (!t) return null
  return <span className={`rounded px-1 py-0.5 text-[9px] font-mono font-semibold shrink-0 ${t.className}`}>{t.label}</span>
}

const TIMELINE_FILTER_EVENTS: Record<string, string[]> = {
  node:      ["node_created", "node_done", "mode_decided"],
  vote:      ["jury_votes", "consortium_candidates"],
  execution: ["base_execute_start", "base_execute_done", "merge_done", "plan_selected"],
  model:     ["model_call_start", "model_call_done", "model_call_failed", "model_call_timeout", "model_call_fallback"],
  error:     ["scope_drift_detected", "tool_blocked", "plan_validation_failed", "plan_abandoned", "model_call_failed", "model_call_timeout"],
}

// Expected-next hints for the run health panel
const PHASE_NEXT_HINT: Record<string, string> = {
  "run_started":          "spec_extract → mode_decide",
  "spec_extracted":       "mode_decide → plan / base_execute",
  "mode_decided":         "plan_start or base_execute_start",
  "plan_start":           "consortium_candidates → jury_votes → plan_selected",
  "plan_selected":        "children_start → node_created × N",
  "children_start":       "node_created events for each child",
  "consortium_candidates":"jury_votes → decision",
  "jury_votes":           "next task or base_execute_done",
  "base_execute_start":   "base_execute_done → analysis_done",
  "base_execute_done":    "analysis_done → node_done",
  "merge_done":           "analysis_done → node_done",
  "analysis_done":        "node_done",
  "node_done":            "sibling nodes or merge_done → run_done",
  "plan_validation_failed": "plan_retry_start or plan_abandoned",
  "plan_retry_done":      "children_start → node_created × N",
}

// ts = Python time.time() in seconds; start = Date.now() in ms
function relTs(ts: number | undefined, start: number | null): string {
  if (!ts || !start) return ""
  const ms = Math.round(ts * 1000 - start)
  if (Math.abs(ms) < 1000) return `+${ms}ms`
  return `+${(ms / 1000).toFixed(1)}s`
}

const CAUSE_LABELS: Record<string, { label: string; detail: string }> = {
  api_error:    { label: "API Error",    detail: "Model was unreachable or provider returned an error" },
  parse_error:  { label: "Parse Error",  detail: "Model ran but returned invalid JSON" },
  schema_error: { label: "Schema Error", detail: "Model ran but output had the wrong shape" },
}

function eventLabel(ev: RafEvent): string {
  const key = ev.event || ev.status || ""
  const map: Record<string, string> = {
    node_created: "Node Created", node_done: "Node Done", jury_votes: "Jury Vote",
    consortium_candidates: "Consortium Proposals", run_done: "Run Complete",
    clarify_answered: "Clarification answered", mode_decided: "Mode Decided",
    base_execute_start: "Base Executing", base_execute_done: "Base Done",
    spec_extracted: "Spec Extracted", merge_done: "Merge Done",
    plan_selected: "Plan Selected", scope_drift_detected: "Scope Drift",
    tool_called: "Tool Called", analysis_done: "Analysis Done",
    run_started: "Run Started",
    plan_validation_failed: "Plan Validation Failed", plan_retry_start: "Plan Retry",
    plan_retry_done: "Plan Retry Done", plan_abandoned: "Plan Abandoned",
    plan_replaced: "Plan Replaced",
    model_call_start: "Model Call Started", model_call_done: "Model Call Done",
    model_call_failed: "Model Call Failed", model_call_timeout: "Model Call Timeout",
    model_call_fallback: "Model Fallback",
  }
  const base = map[key] || key.replace(/_/g, " ")
  // For model call events, append role + model for quick identification
  if (key.startsWith("model_call_") && ev.role && ev.model) {
    return `${base} · ${ev.role} [${ev.model}]`
  }
  return base
}

// Convert internal "option-N" IDs to human-readable "Option N+1" labels.
function optionLabel(id: string | undefined): string {
  if (!id) return "?"
  const m = id.match(/^option-(\d+)$/)
  return m ? `Option ${parseInt(m[1]) + 1}` : id
}

function phaseForEvent(ev: RafEvent): string | null {
  const key = ev.event || ev.status || ""
  const map: Record<string, string> = {
    run_started: "Starting",
    node_created: "Queued",
    mode_decide_start: "Deciding",
    mode_decided: "Mode chosen",
    plan_start: "Planning",
    plan_selected: "Plan selected",
    plan_ready: "Waiting approval",
    children_start: "Spawning children",
    consortium_candidates: "Proposals",
    jury_votes: "Voting",
    model_call_start: "Waiting on model",
    model_call_done: "Model returned",
    model_call_failed: "Model failed",
    model_call_timeout: "Model timed out",
    base_execute_start: "Executing",
    base_execute_done: "Executed",
    merge_done: "Merged",
    analysis_done: "Analyzed",
    child_failed: "Child failed",
    node_done: "Done",
    run_done: ev.error ? "Error" : ev.status === "cancelled" ? "Cancelled" : "Done",
  }
  return map[key] || null
}

function graphEndpointId(endpoint: string | GraphNode): string {
  return typeof endpoint === "string" ? endpoint : endpoint.id
}

function cleanGraphLinks(links: GraphEdge[]): GraphEdge[] {
  return links.map(link => ({
    id: link.id,
    source: graphEndpointId(link.source),
    target: graphEndpointId(link.target),
    edgeType: link.edgeType,
  }))
}

function cleanGraphNodes(nodes: GraphNode[]): GraphNode[] {
  return nodes.map(({ vx: _vx, vy: _vy, fx: _fx, fy: _fy, ...node }) => ({ ...node }))
}

function outputMapToRecord(map: Map<string, NodeOutput>): Record<string, NodeOutput> {
  return Object.fromEntries(map.entries())
}

function outputRecordToMap(record?: Record<string, NodeOutput>): Map<string, NodeOutput> {
  return new Map(Object.entries(record || {}))
}

function normalizeSlots(slots: AgentSlot[], size: number, provider: string, model: string): AgentSlot[] {
  return Array.from({ length: size }, (_, i) => slots[i] || { provider, model })
}

function loadStoredSessions(): Session[] {
  try {
    const raw = window.localStorage.getItem(SESSION_STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed.slice(0, 20) : []
  } catch {
    return []
  }
}

function formatOutput(text: string): string {
  // Sanitize FIRST, then apply safe formatting so no injected HTML survives
  const safe = DOMPurify.sanitize(text, { ALLOWED_TAGS: [], ALLOWED_ATTR: [] })
  return safe
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^#{1,3}\s+(.+)$/gm, '<strong style="color:#60a5fa;font-size:1rem">$1</strong>')
    .replace(/^[-•]\s+(.+)$/gm, '• $1')
    .replace(/\n/g, '<br/>')
}

// ── ExpandModal ───────────────────────────────────────────────────────────────
function tryPrettyJson(text: string): string {
  try {
    const parsed = JSON.parse(text)
    return JSON.stringify(parsed, null, 2)
  } catch {
    return text
  }
}

function ExpandModal({ title, content, onClose }: { title: string; content: string; onClose: () => void }) {
  const formatted = tryPrettyJson(content)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") onClose() }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [onClose])

  const copy = () => {
    navigator.clipboard.writeText(content).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500) })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div
        className="relative w-[min(90vw,860px)] max-h-[85vh] flex flex-col rounded-xl border border-border bg-card shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-border shrink-0">
          <span className="text-sm font-medium">{title}</span>
          <div className="flex items-center gap-2">
            <button
              onClick={copy}
              className="text-[10px] px-2 py-1 rounded border border-border text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
            <button onClick={onClose} className="text-muted-foreground hover:text-foreground text-base leading-none px-1">✕</button>
          </div>
        </div>
        <div className="flex-1 min-h-0 overflow-y-auto p-4">
          <pre className="text-xs font-mono whitespace-pre-wrap break-words text-foreground/90 leading-relaxed">{formatted}</pre>
        </div>
      </div>
    </div>
  )
}

// ── main component ─────────────────────────────────────────────────────────────

export default function App() {
  // landing page — shown once per session; dismissed on "Launch App" / "Try Demo"
  const [showLanding, setShowLanding] = useState<boolean>(() => !sessionStorage.getItem("raf-entered"))

  // api key (user-supplied, persisted in localStorage)
  const [apiKey, setApiKey] = useState<string>(() => localStorage.getItem(API_KEY_STORAGE_KEY) || "")

  // run config
  const [goal, setGoal] = useState("")
  const [provider, setProvider] = useState("mock")
  const [model, setModel] = useState("")
  const [juryModel, setJuryModel] = useState("")
  const [maxDepth, setMaxDepth] = useState(4)
  const [maxParallelChildren, setMaxParallelChildren] = useState(4)
  const [maxNodesTotal, setMaxNodesTotal] = useState(50)
  const [forceRecursive, setForceRecursive] = useState(false)
  const [planGovernance, setPlanGovernance] = useState<"auto" | "review" | "manual">("auto")
  const [planRecovery, setPlanRecovery] = useState<"off" | "auto" | "ask">("off")
  const [toolsEnabled, setToolsEnabled] = useState(false)
  const [domainOverride, setDomainOverride] = useState("")
  const [systemPrompt, setSystemPrompt] = useState("")
  const [providers, setProviders] = useState<string[]>(["mock"])
  const [models, setModels] = useState<Record<string, string[]>>({})
  const [modelCatalog, setModelCatalog] = useState<Record<string, ModelInfo[]>>({})
  const [availableProviders, setAvailableProviders] = useState<string[]>(["mock"])
  const [consortiumSize, setConsortiumSize] = useState(3)
  const [jurySize, setJurySize] = useState(3)
  const [multiModel, setMultiModel] = useState(false)
  const [consortiumSlots, setConsortiumSlots] = useState<AgentSlot[]>([])
  const [jurySlots, setJurySlots] = useState<AgentSlot[]>([])
  const [tierRouting, setTierRouting] = useState(false)
  const [leafSlots, setLeafSlots] = useState<AgentSlot[]>([])
  const [midSlots, setMidSlots] = useState<AgentSlot[]>([])
  const [rootSlots, setRootSlots] = useState<AgentSlot[]>([])
  const [modelPickerOpen, setModelPickerOpen] = useState(false)
  const [appliedStrategy, setAppliedStrategy] = useState<string | null>(null)
  const [expandModal, setExpandModal] = useState<{ title: string; content: string } | null>(null)

  // ui state
  const [centerTab, setCenterTab] = useState<"output" | "timeline" | "votes" | "spec" | "tools" | "checks">("output")
  const [timelineFilter, setTimelineFilter] = useState<"all" | "node" | "vote" | "execution" | "model" | "error">("all")
  const [sessions, setSessions] = useState<Session[]>(() => loadStoredSessions())
  const [serverRuns, setServerRuns] = useState<ServerRunSummary[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState(264)
  const [sidebarTab, setSidebarTab] = useState<"sessions" | "config">("sessions")
  const [workPanelOpen, setWorkPanelOpen] = useState(true)
  const [workspaceMode, setWorkspaceMode] = useState<"work" | "demo">("work")
  const [workPanelPos, setWorkPanelPos] = useState({ left: 272, top: 56 })

  // run state
  const [runId, setRunId] = useState<string | null>(null)
  const [runToken, setRunToken] = useState<string | null>(null)
  const [runStatus, setRunStatus] = useState<"idle" | "running" | "done" | "error" | "cancelled">("idle")
  const [events, setEvents] = useState<RafEvent[]>([])
  const [nodeOutputs, setNodeOutputs] = useState<Map<string, NodeOutput>>(new Map())
  const [runResult, setRunResult] = useState<string | null>(null)
  const [detectedDomain, setDetectedDomain] = useState<string | null>(null)
  const [clarifyQuestion, setClarifyQuestion] = useState<string | null>(null)
  const [clarifyAnswer, setClarifyAnswer] = useState("")
  const [accumulatedGoal, setAccumulatedGoal] = useState("")
  const [pendingPlan, setPendingPlan] = useState<{ nodeId: string; children: ChildSpec[] } | null>(null)
  const [nodeCount, setNodeCount] = useState(0)
  const [currentPhase, setCurrentPhase] = useState("Idle")
  const [partialFailures, setPartialFailures] = useState(0)
  const [staleWarning, setStaleWarning] = useState(false)
  const [lastEventAge, setLastEventAge] = useState<number | null>(null)

  // physics
  const [physics, setPhysics] = useState<PhysicsParams>({ ...DEFAULT_PHYSICS })

  // graph state
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([])
  const [graphLinks, setGraphLinks] = useState<GraphEdge[]>([])
  const [graphMode, setGraphMode] = useState<"simplified" | "full">("simplified")
  const [backendStatus, setBackendStatus] = useState<"checking" | "connected" | "offline">("checking")
  const [zoomCommand, setZoomCommand] = useState<{ action: "in" | "out" | "reset"; nonce: number } | undefined>()
  const graphModeRef = useRef<"simplified" | "full">("simplified")
  const graphNodesRef = useRef<GraphNode[]>([])
  const graphLinksRef = useRef<GraphEdge[]>([])
  const graphRef = useRef<HTMLDivElement>(null)
  const svgRef = useRef<SVGSVGElement | null>(null)
  const [gSize, setGSize] = useState({ w: 800, h: 600 })

  // websocket
  const wsRef = useRef<WebSocket | null>(null)
  const isRunningRef = useRef(false)
  const reconnectAttemptsRef = useRef(0)
  const runStartRef = useRef<number | null>(null)
  const workPanelDragRef = useRef<{ x: number; y: number; left: number; top: number } | null>(null)
  const sidebarResizeRef = useRef<{ x: number; width: number } | null>(null)
  // dedup: prevents replay from doubling events on reconnect
  const seenEventsRef = useRef<Set<string>>(new Set())
  // store raw satellite events so toggling to "full" can retroactively add them
  const satelliteEventsRef = useRef<RafEvent[]>([])
  const planChildrenRef = useRef<Record<string, ChildSpec[]>>({})
  const planChildNodeRef = useRef<Record<string, string>>({})
  const nodeCreatedTsRef = useRef<Record<string, number>>({})
  const lastEventTsRef = useRef<number>(0)

  useEffect(() => { graphModeRef.current = graphMode }, [graphMode])

  // When switching to "full", retroactively add satellite nodes from stored events
  useEffect(() => {
    if (graphMode === "full") {
      satelliteEventsRef.current.forEach(ev => addSatelliteNodes(ev))
    }
    // simplified: leave nodes as-is (removing mid-run would be jarring)
  }, [graphMode]) // eslint-disable-line

  // graph resize observer
  useEffect(() => {
    const upd = () => {
      if (!graphRef.current) return
      const r = graphRef.current.getBoundingClientRect()
      if (r.width > 10 && r.height > 10) setGSize({ w: r.width, h: r.height })
    }
    upd()
    const obs = new ResizeObserver(upd)
    if (graphRef.current) obs.observe(graphRef.current)
    return () => obs.disconnect()
  }, [])

  // live timer: update lastEventAge every second while running; stale warning every 5s
  useEffect(() => {
    const tick = window.setInterval(() => {
      if (lastEventTsRef.current > 0) {
        const age = Date.now() - lastEventTsRef.current
        setLastEventAge(Math.floor(age / 1000))
        if (isRunningRef.current) setStaleWarning(age > 90_000)
      } else {
        setLastEventAge(null)
      }
    }, 1000)
    return () => window.clearInterval(tick)
  }, [])

  // fetch providers on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/models`)
      .then(r => r.json())
      .then(d => {
        setProviders(d.providers || ["mock"])
        setModels(d.models || {})
        setModelCatalog(d.model_catalog || {})
        setAvailableProviders(d.available || ["mock"])
        if (d.defaults?.provider) setProvider(d.defaults.provider)
        if (d.defaults?.model) setModel(d.defaults.model)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    let cancelled = false
    const check = () => {
      const controller = new AbortController()
      const timeout = window.setTimeout(() => controller.abort(), 2500)
      fetch(`${API_BASE}/api/health`, { signal: controller.signal })
        .then(r => { if (!cancelled) setBackendStatus(r.ok ? "connected" : "offline") })
        .catch(() => { if (!cancelled) setBackendStatus("offline") })
        .finally(() => window.clearTimeout(timeout))
    }
    check()
    const timer = window.setInterval(check, 10000)
    return () => { cancelled = true; window.clearInterval(timer) }
  }, [])

  const refreshServerRuns = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/runs`)
      if (!res.ok) return
      const data = await res.json() as { runs?: ServerRunSummary[] }
      setServerRuns(data.runs || [])
    } catch {
      setServerRuns([])
    }
  }, [])

  useEffect(() => {
    if (backendStatus === "connected") refreshServerRuns()
  }, [backendStatus, refreshServerRuns])

  useEffect(() => {
    try {
      window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(sessions.slice(0, 20)))
    } catch {
      // Storage is best-effort; active runs should not depend on it.
    }
  }, [sessions])

  useEffect(() => {
    if (!multiModel) return
    setConsortiumSlots(prev => normalizeSlots(prev, consortiumSize, provider, model))
  }, [multiModel, consortiumSize, provider, model])

  useEffect(() => {
    if (!multiModel) return
    setJurySlots(prev => normalizeSlots(prev, jurySize, provider, juryModel || model))
  }, [multiModel, jurySize, provider, model, juryModel])

  const currentConfig = useCallback((): SessionConfig => ({
    provider, model, juryModel, consortiumSize, jurySize, maxDepth, maxParallelChildren, maxNodesTotal,
    forceRecursive, planGovernance, planRecovery, toolsEnabled, multiModel, consortiumSlots, jurySlots,
    tierRouting, leafSlots, midSlots, rootSlots,
    domainOverride, systemPrompt,
  }), [provider, model, juryModel, consortiumSize, jurySize, maxDepth, maxParallelChildren, maxNodesTotal, forceRecursive, planGovernance, planRecovery, toolsEnabled, multiModel, consortiumSlots, jurySlots, tierRouting, leafSlots, midSlots, rootSlots, domainOverride, systemPrompt])

  useEffect(() => {
    if (!activeSessionId) return
    const graphSnapshot = cleanGraphNodes(graphNodes)
    const linkSnapshot = cleanGraphLinks(graphLinks)
    const outputsSnapshot = outputMapToRecord(nodeOutputs)
    setSessions(prev => prev.map(s => s.id === activeSessionId ? {
      ...s,
      provider,
      runId,
      runToken,
      status: runStatus,
      nodeCount,
      output: runResult || s.output,
      result: runResult,
      domain: detectedDomain || s.domain,
      currentPhase,
      config: currentConfig(),
      events,
      graphNodes: graphSnapshot,
      graphLinks: linkSnapshot,
      nodeOutputs: outputsSnapshot,
    } : s))
  }, [activeSessionId, provider, runId, runToken, runStatus, nodeCount, runResult, detectedDomain, currentPhase, currentConfig, events, graphNodes, graphLinks, nodeOutputs])

  const restoreSession = useCallback((session: Session) => {
    const restoredEvents = session.events || []
    const restoredNodes = cleanGraphNodes(session.graphNodes || [])
    const restoredLinks = cleanGraphLinks(session.graphLinks || [])
    setActiveSessionId(session.id)
    setGoal(session.goal)
    setProvider(session.config?.provider || session.provider)
    setModel(session.config?.model || "")
    setJuryModel(session.config?.juryModel || "")
    if (session.config) {
      setConsortiumSize(session.config.consortiumSize)
      setJurySize(session.config.jurySize)
      setMaxDepth(session.config.maxDepth)
      setMaxParallelChildren(session.config.maxParallelChildren || 4)
      setMaxNodesTotal(session.config.maxNodesTotal)
      setForceRecursive(session.config.forceRecursive)
      setPlanGovernance(session.config.planGovernance || "auto")
      setPlanRecovery(session.config.planRecovery || "off")
      setToolsEnabled(session.config.toolsEnabled)
      setMultiModel(session.config.multiModel)
      setConsortiumSlots(session.config.consortiumSlots || [])
      setJurySlots(session.config.jurySlots || [])
      setTierRouting(session.config.tierRouting || false)
      setLeafSlots(session.config.leafSlots || [])
      setMidSlots(session.config.midSlots || [])
      setRootSlots(session.config.rootSlots || [])
      setDomainOverride(session.config.domainOverride || "")
      setSystemPrompt(session.config.systemPrompt || "")
    }
    setRunId(session.runId || null)
    setRunToken(session.runToken || null)
    setRunStatus((session.status as typeof runStatus) || "idle")
    setEvents(restoredEvents)
    graphNodesRef.current = restoredNodes
    graphLinksRef.current = restoredLinks
    setGraphNodes(restoredNodes)
    setGraphLinks(restoredLinks)
    setNodeOutputs(outputRecordToMap(session.nodeOutputs))
    setRunResult(session.result || session.output || null)
    setDetectedDomain(session.domain || null)
    setSelectedNode(null)
    setClarifyQuestion(null)
    setPendingPlan(null)
    setNodeCount(session.nodeCount || restoredNodes.filter(n => n.type === "raf-node").length)
    setCurrentPhase(session.currentPhase || (session.status === "running" ? "Running" : "Idle"))
    runStartRef.current = restoredEvents.find(ev => ev.timestamp)?.timestamp
      ? (restoredEvents.find(ev => ev.timestamp)!.timestamp! * 1000)
      : null
    seenEventsRef.current = new Set(restoredEvents.map(ev => `${ev.event ?? ev.status ?? ""}:${ev.node_id ?? ""}:${String(ev.timestamp ?? "")}`))
    satelliteEventsRef.current = restoredEvents.filter(ev => ev.event === "consortium_candidates" || ev.event === "jury_votes")
    planChildrenRef.current = {}
    planChildNodeRef.current = {}
    nodeCreatedTsRef.current = {}
    restoredEvents.forEach(ev => {
      if ((ev.event === "plan_selected" || ev.event === "plan_ready") && ev.node_id && ev.children) {
        planChildrenRef.current[ev.node_id] = ev.children
      }
      if (ev.event === "node_created" && ev.node_id) {
        if (ev.timestamp) nodeCreatedTsRef.current[ev.node_id] = ev.timestamp
        if (ev.parent_id && ev.plan_child_id) {
          planChildNodeRef.current[`${ev.parent_id}:${ev.plan_child_id}`] = ev.node_id
        }
      }
    })
  }, [])

  // add node to graph — idempotent: silently skips if id already exists
  const addGraphNode = useCallback((id: string, parentId: string | null | undefined, depth: number, goal?: string, type: GraphNode["type"] = "raf-node") => {
    if (graphNodesRef.current.some(n => n.id === id)) return
    const parent = parentId ? graphNodesRef.current.find(n => n.id === parentId) : null
    const node: GraphNode = {
      id, type,
      label: id === "root" ? "root" : id.replace("node-", "#"),
      detail: goal ? goal.slice(0, 60) : id,
      active: true, depth, goal,
      ...(parent && parent.x !== undefined ? {
        x: parent.x + (Math.random() - 0.5) * 60,
        y: parent.y! + 80,
      } : {}),
    }
    graphNodesRef.current = [...graphNodesRef.current, node]
    if (parentId) {
      const linkId = `${parentId}->${id}`
      if (!graphLinksRef.current.some(l => l.id === linkId)) {
        graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: parentId, target: id, edgeType: "parallel" }]
      }
    }
    setGraphNodes([...graphNodesRef.current])
    setGraphLinks([...graphLinksRef.current])
  }, [])

  // add consortium/jury satellite nodes for a single event (used by both live and replay)
  // Pattern: RAF-node → consortium-group → agent-proposal (× N)
  //          RAF-node → jury-group       → juror-vote    (× N)
  const addSatelliteNodes = useCallback((ev: RafEvent) => {
    if (!ev.node_id) return
    const task = ev.task || ""
    const parentDepth = graphNodesRef.current.find(n => n.id === ev.node_id)?.depth ?? 0

    if (ev.event === "consortium_candidates") {
      const candidates = (ev as any).candidates as any[] || []
      const groupId = `${ev.node_id}-consortium-${task}`
      // Create consortium-group node attached to the RAF node
      if (!graphNodesRef.current.some(n => n.id === groupId)) {
        const parent = graphNodesRef.current.find(n => n.id === ev.node_id)
        const groupNode: GraphNode = {
          id: groupId, type: "consortium-group",
          label: "C", detail: `Consortium (${task})`,
          active: true, depth: parentDepth + 1,
          ownerNodeId: ev.node_id, task,
          hint: task,
          ...(parent?.x !== undefined ? { x: parent.x + (Math.random() - 0.5) * 40, y: parent.y! + 60 } : {}),
        }
        graphNodesRef.current = [...graphNodesRef.current, groupNode]
        const linkId = `${ev.node_id}->${groupId}`
        if (!graphLinksRef.current.some(l => l.id === linkId)) {
          graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: ev.node_id!, target: groupId, edgeType: "flow" }]
        }
      }
      // Create agent-proposal nodes attached to the group
      candidates.forEach((cand: any, idx: number) => {
        const agentId = `${ev.node_id}-agent-${task}-${idx}`
        if (!graphNodesRef.current.some(n => n.id === agentId)) {
          const groupNode = graphNodesRef.current.find(n => n.id === groupId)
          const payload = cand?.payload || cand || {}
          const hint = payload.output ? payload.output.slice(0, 40) : payload.mode || `Agent ${idx + 1}`
          const agentNode: GraphNode = {
            id: agentId, type: "agent-proposal",
            label: `A${idx + 1}`, detail: hint,
            active: true, depth: parentDepth + 2,
            ownerNodeId: ev.node_id, task, candidateIndex: idx,
            hint,
            ...(groupNode?.x !== undefined ? { x: groupNode.x + (idx - (candidates.length - 1) / 2) * 30, y: groupNode.y! + 50 } : {}),
          }
          graphNodesRef.current = [...graphNodesRef.current, agentNode]
          const linkId = `${groupId}->${agentId}`
          if (!graphLinksRef.current.some(l => l.id === linkId)) {
            graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: groupId, target: agentId, edgeType: "parallel" }]
          }
        }
      })
      setGraphNodes([...graphNodesRef.current])
      setGraphLinks([...graphLinksRef.current])
    }

    if (ev.event === "jury_votes") {
      const votes = (ev as any).votes as any[] || []
      const winnerId = (ev as any).winner_id as string | undefined
      const groupId = `${ev.node_id}-jury-${task}`
      // Create jury-group node
      if (!graphNodesRef.current.some(n => n.id === groupId)) {
        const parent = graphNodesRef.current.find(n => n.id === ev.node_id)
        const groupNode: GraphNode = {
          id: groupId, type: "jury-group",
          label: "J", detail: `Jury (${task})`,
          active: true, depth: parentDepth + 1,
          ownerNodeId: ev.node_id, task,
          hint: `winner: ${winnerId || "?"}`,
          ...(parent?.x !== undefined ? { x: parent.x + (Math.random() - 0.5) * 40, y: parent.y! + 60 } : {}),
        }
        graphNodesRef.current = [...graphNodesRef.current, groupNode]
        const linkId = `${ev.node_id}->${groupId}`
        if (!graphLinksRef.current.some(l => l.id === linkId)) {
          graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: ev.node_id!, target: groupId, edgeType: "flow" }]
        }
      }
      // Create juror-vote nodes
      votes.forEach((v: any, idx: number) => {
        const jurorId = `${ev.node_id}-juror-${task}-${idx}`
        if (!graphNodesRef.current.some(n => n.id === jurorId)) {
          const groupNode = graphNodesRef.current.find(n => n.id === groupId)
          const vote = v.vote || v
          const isWinner = vote.winner_id === winnerId
          const hint = vote.winner_id ? `→ ${optionLabel(vote.winner_id)}` : `Juror ${idx + 1}`
          const jurorNode: GraphNode = {
            id: jurorId, type: "juror-vote",
            label: `V${idx + 1}`, detail: hint,
            active: false, depth: parentDepth + 2,
            ownerNodeId: ev.node_id, task, candidateIndex: idx,
            hint,
            success: isWinner,
            ...(groupNode?.x !== undefined ? { x: groupNode.x + (idx - (votes.length - 1) / 2) * 30, y: groupNode.y! + 50 } : {}),
          }
          graphNodesRef.current = [...graphNodesRef.current, jurorNode]
          const linkId = `${groupId}->${jurorId}`
          if (!graphLinksRef.current.some(l => l.id === linkId)) {
            graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: groupId, target: jurorId, edgeType: "parallel" }]
          }
        }
      })
      // Mark winning agent-proposal if present
      if (winnerId) {
        const winnerAgentId = `${ev.node_id}-agent-${task}-${winnerId}`
        // Try matching by option index embedded in winner_id (e.g. "option-0")
        const match = winnerId.match(/(\d+)$/)
        if (match) {
          const winIdx = parseInt(match[1])
          const winAgentId = `${ev.node_id}-agent-${task}-${winIdx}`
          graphNodesRef.current = graphNodesRef.current.map(n =>
            n.id === winAgentId ? { ...n, success: true, hint: (n.hint || "") + " ✓" } : n
          )
        } else if (graphNodesRef.current.some(n => n.id === winnerAgentId)) {
          graphNodesRef.current = graphNodesRef.current.map(n =>
            n.id === winnerAgentId ? { ...n, success: true } : n
          )
        }
      }
      setGraphNodes([...graphNodesRef.current])
      setGraphLinks([...graphLinksRef.current])
    }
  }, [addGraphNode])

  const updateGraphNode = useCallback((id: string, patch: Partial<GraphNode>) => {
    graphNodesRef.current = graphNodesRef.current.map(n => n.id === id ? { ...n, ...patch } : n)
    setGraphNodes([...graphNodesRef.current])
  }, [])

  const addDependencyEdgesForParent = useCallback((parentId: string) => {
    const children = planChildrenRef.current[parentId] || []
    if (children.length === 0) return
    let changed = false
    const nextLinks = [...graphLinksRef.current]
    for (const child of children) {
      const targetNodeId = planChildNodeRef.current[`${parentId}:${child.child_id}`]
      if (!targetNodeId) continue
      for (const depChildId of child.depends_on || []) {
        const sourceNodeId = planChildNodeRef.current[`${parentId}:${depChildId}`]
        if (!sourceNodeId) continue
        const linkId = `dep:${sourceNodeId}->${targetNodeId}`
        if (!nextLinks.some(link => link.id === linkId)) {
          nextLinks.push({ id: linkId, source: sourceNodeId, target: targetNodeId, edgeType: "dependency" })
          changed = true
        }
      }
    }
    if (changed) {
      graphLinksRef.current = nextLinks
      setGraphLinks([...graphLinksRef.current])
    }
  }, [])

  // process a single event — deduplicated so reconnect replay is idempotent
  const processEvent = useCallback((ev: RafEvent) => {
    const key = `${ev.event ?? ev.status ?? ""}:${ev.node_id ?? ""}:${String(ev.timestamp ?? "")}`
    if (seenEventsRef.current.has(key)) return
    seenEventsRef.current.add(key)
    setEvents(prev => [...prev, ev])
    lastEventTsRef.current = Date.now()
    setStaleWarning(false)
    const phase = phaseForEvent(ev)
    if (phase) setCurrentPhase(phase)
    if (phase && ev.node_id) updateGraphNode(ev.node_id, { phase, active: ev.event !== "node_done" })

    if (ev.event === "node_created") {
      if (ev.timestamp && ev.node_id) nodeCreatedTsRef.current[ev.node_id] = ev.timestamp
      addGraphNode(ev.node_id!, ev.parent_id, ev.depth ?? 0, ev.goal)
      if (phase && ev.node_id) updateGraphNode(ev.node_id, { phase })
      if (ev.parent_id && ev.plan_child_id && ev.node_id) {
        planChildNodeRef.current[`${ev.parent_id}:${ev.plan_child_id}`] = ev.node_id
        addDependencyEdgesForParent(ev.parent_id)
      }
      setNodeCount(c => c + 1)
    }

    if (ev.event === "node_done") {
      const id = ev.node_id!
      const createdAt = nodeCreatedTsRef.current[id]
      const durationMs = createdAt && ev.timestamp ? Math.max(0, Math.round((ev.timestamp - createdAt) * 1000)) : undefined
      graphNodesRef.current = graphNodesRef.current.map(n =>
        n.id === id ? { ...n, active: false, success: true,
          caseType: ev.mode === "recursive" ? "recursive" : "base",
          output: ev.output, confidence: ev.confidence, phase: "Done", durationMs } : n
      )
      setGraphNodes([...graphNodesRef.current])
      if (ev.output) {
        setNodeOutputs(prev => new Map(prev).set(id, {
          output: ev.output!, mode: ev.mode || "base",
          confidence: ev.confidence || 0, goal: ev.goal,
        }))
      }
    }

    if (ev.event === "mode_decided") {
      const id = ev.node_id!
      graphNodesRef.current = graphNodesRef.current.map(n =>
        n.id === id ? { ...n, caseType: (ev.winner === "recursive" || (ev as any).mode === "recursive") ? "recursive" : "base", phase: phase || n.phase } : n
      )
      setGraphNodes([...graphNodesRef.current])
    }

    if (ev.event === "spec_extracted") {
      if ((ev as any).domain) setDetectedDomain((ev as any).domain)
    }

    if (ev.event === "run_done") {
      isRunningRef.current = false
      const st = (ev as any).status
      setRunStatus(ev.error ? "error" : st === "cancelled" ? "cancelled" : "done")
      const result = (ev as any).result
      if (result?.output) { setRunResult(result.output); setCenterTab("output") }
      if (result?.metadata?.mode === "clarify") {
        const q = result.metadata.questions?.[0]
        if (q) setClarifyQuestion(q)
      }
      setActiveSessionId(prev => {
        if (prev) {
          const finalSt = ev.error ? "error" : st === "cancelled" ? "cancelled" : "done"
          setSessions(ss => ss.map(s => s.id === prev ? { ...s, status: finalSt, output: result?.output } : s))
        }
        return prev
      })
    }

    if (ev.event === "child_failed") {
      setPartialFailures(prev => prev + 1)
    }

    // Plan recovery: create visual nodes for each attempt so the graph shows the history
    if (ev.event === "plan_validation_failed" && ev.node_id) {
      const attempt = ev.plan_attempt ?? 0
      const failId = `${ev.node_id}-plan-fail-${attempt}`
      if (!graphNodesRef.current.some(n => n.id === failId)) {
        const parent = graphNodesRef.current.find(n => n.id === ev.node_id)
        graphNodesRef.current = [...graphNodesRef.current, {
          id: failId, type: "referee-check" as const,
          label: `PF${attempt}`, detail: "Plan failed validation",
          active: false, success: false,
          depth: (parent?.depth ?? 0) + 1,
          ownerNodeId: ev.node_id, task: "plan_validation_failed",
          hint: ev.reason ? ev.reason.slice(0, 30) : "validation failed",
          ...(parent?.x !== undefined ? { x: parent.x + (attempt - 1) * 50, y: parent.y! + 70 } : {}),
        }]
        const linkId = `${ev.node_id}->${failId}`
        if (!graphLinksRef.current.some(l => l.id === linkId)) {
          graphLinksRef.current = [...graphLinksRef.current, { id: linkId, source: ev.node_id!, target: failId, edgeType: "flow" as const }]
        }
        setGraphNodes([...graphNodesRef.current])
        setGraphLinks([...graphLinksRef.current])
      }
    }

    if (ev.event === "plan_abandoned" && ev.node_id) {
      updateGraphNode(ev.node_id, { phase: "Plan abandoned", success: false })
    }

    if (ev.event === "plan_replaced" && ev.node_id) {
      updateGraphNode(ev.node_id, { phase: "Plan replaced" })
    }

    if (ev.event === "merge_done" && ev.node_id) {
      const mergeId = `${ev.node_id}-merge`
      if (!graphNodesRef.current.some(n => n.id === mergeId)) {
        const parentNode = graphNodesRef.current.find(n => n.id === ev.node_id)
        const mergeNode: GraphNode = {
          id: mergeId, type: "merge-group",
          label: "M", detail: "Merge",
          active: false, depth: (parentNode?.depth ?? 0) + 1,
          ownerNodeId: ev.node_id, task: "merge",
          hint: "merge",
          success: true,
          ...(parentNode?.x !== undefined ? { x: parentNode.x, y: parentNode.y! + 70 } : {}),
        }
        graphNodesRef.current = [...graphNodesRef.current, mergeNode]
        // Flow edge from parent to merge-group
        const flowLinkId = `${ev.node_id}->${mergeId}`
        if (!graphLinksRef.current.some(l => l.id === flowLinkId)) {
          graphLinksRef.current = [...graphLinksRef.current, { id: flowLinkId, source: ev.node_id!, target: mergeId, edgeType: "flow" }]
        }
        // Merge (backflow) edges from each completed child to merge-group
        const children = planChildrenRef.current[ev.node_id] || []
        for (const child of children) {
          const childNodeId = planChildNodeRef.current[`${ev.node_id}:${child.child_id}`]
          if (childNodeId) {
            const mergeLinkId = `merge:${childNodeId}->${mergeId}`
            if (!graphLinksRef.current.some(l => l.id === mergeLinkId)) {
              graphLinksRef.current = [...graphLinksRef.current, { id: mergeLinkId, source: childNodeId, target: mergeId, edgeType: "merge" }]
            }
          }
        }
        setGraphNodes([...graphNodesRef.current])
        setGraphLinks([...graphLinksRef.current])
      }
    }

    // plan_ready is the real backend event name
    if ((ev.event === "plan_ready" || ev.event === "plan_selected") && ev.node_id) {
      const kids = (ev as any).children as ChildSpec[] | undefined
      if (kids) {
        planChildrenRef.current[ev.node_id] = kids
        addDependencyEdgesForParent(ev.node_id)
        if (ev.event === "plan_ready") setPendingPlan({ nodeId: ev.node_id!, children: kids })
      }
    }

    // Store satellite events regardless of mode so toggling to "full" can replay them
    if ((ev.event === "consortium_candidates" || ev.event === "jury_votes") && ev.node_id) {
      satelliteEventsRef.current = [...satelliteEventsRef.current, ev]
    }
    // Add satellite nodes now only if already in full mode
    if (graphModeRef.current === "full") {
      addSatelliteNodes(ev)
    }
  }, [addGraphNode, updateGraphNode, addDependencyEdgesForParent])

  // websocket connection
  const connectWs = useCallback((rid: string, token: string) => {
    if (wsRef.current) { wsRef.current.onclose = null; wsRef.current.close() }
    const wsUrl = API_BASE.replace(/^http/, "ws") + `/api/stream/${rid}?token=${encodeURIComponent(token)}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    ws.onopen = () => { reconnectAttemptsRef.current = 0 }
    ws.onmessage = (msg) => {
      try {
        const ev: RafEvent = JSON.parse(msg.data)
        if (ev.event === "run_started" && !runStartRef.current) runStartRef.current = Date.now()
        processEvent(ev)
      } catch {}
    }
    ws.onclose = () => {
      if (!isRunningRef.current) return
      const attempts = reconnectAttemptsRef.current
      if (attempts >= 6) return
      reconnectAttemptsRef.current = attempts + 1
      setTimeout(() => { if (isRunningRef.current) connectWs(rid, token) }, Math.min(500 * Math.pow(2, attempts), 16000))
    }
  }, [processEvent])

  // start run
  // continueSession=true: clarification continuation — preserve existing timeline/graph,
  // just append new events. Does NOT create a new session entry.
  const startRun = async (goalText: string, skipClarify = false, continueSession = false) => {
    if (!goalText.trim()) return
    const runGoal = goalText.trim()

    if (!continueSession) {
      graphNodesRef.current = []; graphLinksRef.current = []
      seenEventsRef.current = new Set()
      satelliteEventsRef.current = []
      planChildrenRef.current = {}
      planChildNodeRef.current = {}
      nodeCreatedTsRef.current = {}
      setGraphNodes([]); setGraphLinks([]); setEvents([]); setNodeOutputs(new Map())
      setRunResult(null); setDetectedDomain(null); setSelectedNode(null)
      setPendingPlan(null); setNodeCount(0)
      setCurrentPhase("Starting")
      setRunToken(null)
      setPartialFailures(0); setStaleWarning(false); setLastEventAge(null)
      lastEventTsRef.current = 0
      runStartRef.current = null
      const sessionId = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`
      const sessionProviderLabel = multiModel
        ? `multi · ${(consortiumSlots[0]?.model || "").split("/").pop() || consortiumSlots[0]?.provider || "multi-model"}`
        : `${provider}${model ? ` · ${(model.split("/").pop() || model).replace(/:.*$/, "")}` : ""}`
      setSessions(prev => [{
        id: sessionId, goal: runGoal, provider, providerLabel: sessionProviderLabel, status: "running", ts: Date.now(), nodeCount: 0,
        currentPhase: "Starting", config: currentConfig(), events: [], graphNodes: [], graphLinks: [], nodeOutputs: {},
      }, ...prev.slice(0, 19)])
      setActiveSessionId(sessionId)
    } else {
      // Clarification continuation: only reset seenEvents so the new run's
      // events are not blocked, but keep graph/timeline visible.
      seenEventsRef.current = new Set()
      setPendingPlan(null)
      setPartialFailures(0); setStaleWarning(false); setLastEventAge(null)
      lastEventTsRef.current = 0
      setCurrentPhase("Continuing")
    }

    isRunningRef.current = true
    setRunStatus("running"); setCenterTab("timeline")

    const body: Record<string, unknown> = {
      goal: runGoal, provider, model: model || null, jury_model: juryModel || null,
      consortium_size: consortiumSize, jury_size: jurySize,
      max_depth: maxDepth, max_parallel_children: maxParallelChildren, max_nodes_total: maxNodesTotal,
      plan_approval_required: planGovernance === "manual", tools_enabled: toolsEnabled,
      plan_recovery: planRecovery,
      max_plan_retries: 2,
      force_recursive: forceRecursive, skip_clarify: skipClarify,
      domain: domainOverride || null, system_prompt: systemPrompt || null,
      api_key: provider !== "mock" && apiKey ? apiKey : null,
    }
    if (multiModel && consortiumSlots.length > 0) body.consortium_agents = consortiumSlots
    if (multiModel && jurySlots.length > 0) body.jury_agents = jurySlots
    // Tier routing overrides: send tier slots when tier routing is enabled
    if (multiModel && tierRouting) {
      if (leafSlots.length > 0) body.leaf_agents = leafSlots
      if (midSlots.length > 0) body.mid_agents = midSlots
      if (rootSlots.length > 0) body.root_agents = rootSlots
    }

    try {
      const res = await fetch(`${API_BASE}/api/run`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      if (!res.ok) throw new Error(`Server error ${res.status}`)
      const data = await res.json() as { run_id: string; access_token?: string }
      if (!data.access_token) throw new Error("Server did not return a run access token")
      setRunId(data.run_id)
      setRunToken(data.access_token)
      connectWs(data.run_id, data.access_token)
    } catch (err) {
      setRunStatus("error")
      setEvents([{ event: "run_done", error: String(err) }])
      isRunningRef.current = false
    }
  }

  const cancelRun = async () => {
    if (!runId) return
    // Keep isRunningRef=true so reconnect can still fire and receive the
    // authoritative run_done { status: "cancelled" } from the server.
    await fetch(`${API_BASE}/api/run/${runId}/cancel`, { method: "POST", headers: authHeaders(runToken) }).catch(() => {})
  }

  const updateConsortiumSlot = (index: number, patch: Partial<AgentSlot>) => {
    setAppliedStrategy(null) // manual edit clears the preset
    setConsortiumSlots(prev => normalizeSlots(prev, consortiumSize, provider, model).map((slot, i) => i === index ? { ...slot, ...patch } : slot))
  }

  const updateJurySlot = (index: number, patch: Partial<AgentSlot>) => {
    setAppliedStrategy(null)
    setJurySlots(prev => normalizeSlots(prev, jurySize, provider, juryModel || model).map((slot, i) => i === index ? { ...slot, ...patch } : slot))
  }

  const updateLeafSlot = (index: number, patch: Partial<AgentSlot>) => {
    setAppliedStrategy(null)
    setLeafSlots(prev => normalizeSlots(prev, prev.length || 2, provider, model).map((slot, i) => i === index ? { ...slot, ...patch } : slot))
  }

  const updateMidSlot = (index: number, patch: Partial<AgentSlot>) => {
    setAppliedStrategy(null)
    setMidSlots(prev => normalizeSlots(prev, prev.length || 2, provider, model).map((slot, i) => i === index ? { ...slot, ...patch } : slot))
  }

  const updateRootSlot = (index: number, patch: Partial<AgentSlot>) => {
    setAppliedStrategy(null)
    setRootSlots(prev => normalizeSlots(prev, prev.length || 2, provider, model).map((slot, i) => i === index ? { ...slot, ...patch } : slot))
  }

  const applyStrategy = (strategyId: string) => {
    // Click the active strategy again → deselect it (keep current settings, just clear the badge)
    if (appliedStrategy === strategyId) {
      setAppliedStrategy(null)
      return
    }
    const s = MODEL_STRATEGIES.find(x => x.id === strategyId)
    if (!s) return
    setAppliedStrategy(s.id)
    setMultiModel(s.multiModel)
    setConsortiumSize(s.consortiumSize)
    setJurySize(s.jurySize)
    // Always set slots explicitly — clear stale state from any previously applied strategy
    setConsortiumSlots(s.consortiumSlots)
    setJurySlots(s.jurySlots)
    // Tier routing — always reset all tier slots so switching strategies is clean
    setTierRouting(s.tierRouting || false)
    setLeafSlots(s.leafSlots || [])
    setMidSlots(s.midSlots || [])
    setRootSlots(s.rootSlots || [])
  }

  const replayServerRun = async (summary: ServerRunSummary) => {
    try {
      const [eventsRes, statusRes] = await Promise.all([
        fetch(`${API_BASE}/api/run/${summary.run_id}/events`),
        fetch(`${API_BASE}/api/run/${summary.run_id}`),
      ])
      if (!eventsRes.ok) return
      const eventsData = await eventsRes.json() as { events?: RafEvent[]; status?: string }
      const statusData = statusRes.ok ? await statusRes.json() as { status?: string; result?: { output?: string } | null; error?: string | null } : null
      const replayEvents = eventsData.events || []

      graphNodesRef.current = []; graphLinksRef.current = []
      seenEventsRef.current = new Set()
      satelliteEventsRef.current = []
      planChildrenRef.current = {}
      planChildNodeRef.current = {}
      nodeCreatedTsRef.current = {}
      setGraphNodes([]); setGraphLinks([]); setEvents([]); setNodeOutputs(new Map())
      setRunResult(statusData?.result?.output || null)
      setDetectedDomain(null); setSelectedNode(null); setPendingPlan(null)
      setNodeCount(0); setCurrentPhase("Replayed")
      setRunId(summary.run_id)
      setRunStatus((statusData?.status as typeof runStatus) || (eventsData.status as typeof runStatus) || "idle")
      setGoal(summary.goal)
      setProvider(summary.provider)
      runStartRef.current = replayEvents.find(ev => ev.timestamp)?.timestamp
        ? replayEvents.find(ev => ev.timestamp)!.timestamp! * 1000
        : null

      replayEvents.forEach(ev => processEvent(ev))
      setCenterTab("timeline")
      setWorkPanelOpen(true)
    } catch {
      setRunStatus("error")
    }
  }

  // Fetch freshest server state before exporting; falls back to local state on error
  const fetchFreshExportData = async (): Promise<{ freshEvents: RafEvent[]; freshResult: string | null; freshStatus: string }> => {
    if (!runId) return { freshEvents: events, freshResult: runResult, freshStatus: runStatus }
    try {
      const [evRes, stRes] = await Promise.all([
        fetch(`${API_BASE}/api/run/${runId}/events`, { headers: authHeaders(runToken) }),
        fetch(`${API_BASE}/api/run/${runId}`, { headers: authHeaders(runToken) }),
      ])
      const freshEvents: RafEvent[] = evRes.ok ? ((await evRes.json()) as { events?: RafEvent[] }).events || events : events
      const stData = stRes.ok ? await stRes.json() as { status?: string; result?: { output?: string } | null } : null
      const freshResult = stData?.result?.output ?? runResult
      const freshStatus = stData?.status ?? runStatus
      return { freshEvents, freshResult, freshStatus }
    } catch {
      return { freshEvents: events, freshResult: runResult, freshStatus: runStatus }
    }
  }

  // Compute export completeness metadata for both JSON and PDF
  const buildExportMeta = (evList: RafEvent[], status: string) => {
    const hasRunDone = evList.some(ev => ev.event === "run_done")
    const hasRootNodeDone = evList.some(ev => ev.event === "node_done" && (ev.node_id === "root" || ev.depth === 0))
    const isMidRun = status === "running"
    let exportCompleteness: string
    if (isMidRun) exportCompleteness = "mid_run"
    else if (!hasRunDone && hasRootNodeDone) exportCompleteness = "near_complete"
    else if (hasRunDone) exportCompleteness = "complete"
    else exportCompleteness = "partial"
    return { hasRunDone, hasRootNodeDone, exportCompleteness, isMidRun }
  }

  const exportJSON = async () => {
    const { freshEvents, freshResult, freshStatus } = await fetchFreshExportData()
    const meta = buildExportMeta(freshEvents, freshStatus)
    const data = {
      run_id: runId,
      goal,
      provider,
      model: model || null,
      jury_model: juryModel || null,
      status: freshStatus,
      phase: currentPhase,
      detected_domain: detectedDomain,
      partial_failures: partialFailures,
      exportCompleteness: meta.exportCompleteness,
      hasRunDone: meta.hasRunDone,
      hasRootNodeDone: meta.hasRootNodeDone,
      note: meta.isMidRun ? "Exported mid-run. Final output may not be available yet." : undefined,
      config: currentConfig(),
      physics,
      result: freshResult,
      events: freshEvents,
      graphNodes: cleanGraphNodes(graphNodes),
      graphLinks: cleanGraphLinks(graphLinks),
      nodeOutputs: outputMapToRecord(nodeOutputs),
      selectedNodeId: selectedNode?.id || null,
      exportedAt: new Date().toISOString(),
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a"); a.href = url; a.download = `raf-trace-${runId || "export"}.json`
    a.click(); URL.revokeObjectURL(url)
  }

  const exportPDF = async () => {
    const [{ default: jsPDF }, { default: html2canvas }, { freshEvents, freshResult, freshStatus }] = await Promise.all([
      import("jspdf"), import("html2canvas"), fetchFreshExportData(),
    ])
    const meta = buildExportMeta(freshEvents, freshStatus)
    const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" })
    const W = doc.internal.pageSize.getWidth()
    const H = doc.internal.pageSize.getHeight()

    // ── helpers ──────────────────────────────────────────────────────────────
    const newPage = () => {
      doc.addPage()
      doc.setFillColor(10, 14, 23); doc.rect(0, 0, W, H, "F")
    }
    const sectionHeader = (title: string, yPos: number) => {
      doc.setTextColor(96, 165, 250); doc.setFontSize(11)
      doc.text(title, 10, yPos)
      doc.setTextColor(148, 163, 184); doc.setFontSize(7.5)
      return yPos + 7
    }
    const maybeNewPage = (y: number, needed = 10): number => {
      if (y + needed > H - 10) { newPage(); return 15 }
      return y
    }
    const row = (doc: InstanceType<typeof jsPDF>, label: string, value: string, y: number, indent = 10): number => {
      doc.setTextColor(100, 116, 139); doc.text(label, indent, y)
      doc.setTextColor(148, 163, 184); doc.text(value, indent + 42, y)
      return y + 4.5
    }

    // ── Cover page ──────────────────────────────────────────────────────────
    doc.setFillColor(10, 14, 23); doc.rect(0, 0, W, H, "F")
    doc.setTextColor(96, 165, 250); doc.setFontSize(22)
    doc.text("RAF Execution Report", 20, 28)

    // Status badge — coloured based on completeness
    const statusColors: Record<string, [number, number, number]> = {
      complete: [34, 197, 94], mid_run: [59, 130, 246], near_complete: [234, 179, 8], partial: [239, 68, 68],
    }
    const [sr, sg, sb] = statusColors[meta.exportCompleteness] || [148, 163, 184]
    doc.setFontSize(9); doc.setTextColor(sr, sg, sb)
    const statusLabel = meta.isMidRun ? "⚡ EXPORTED MID-RUN" : meta.exportCompleteness === "near_complete" ? "⚠ NEAR COMPLETE (no run_done yet)" : meta.exportCompleteness === "complete" ? "✓ COMPLETE" : "~ PARTIAL"
    doc.text(statusLabel, 20, 38)

    doc.setTextColor(148, 163, 184); doc.setFontSize(9)
    let cy = 50
    cy = row(doc, "Run ID", runId || "—", cy)
    cy = row(doc, "Goal", goal.slice(0, 100) + (goal.length > 100 ? "…" : ""), cy)
    cy = row(doc, "Provider", provider, cy)
    cy = row(doc, "Domain", detectedDomain || "auto", cy)
    cy = row(doc, "Status", runStatus, cy)
    cy = row(doc, "Phase", currentPhase, cy)
    cy = row(doc, "Nodes", `${graphNodes.filter(n => n.type === "raf-node").length} RAF + ${graphNodes.filter(n => n.type !== "raf-node").length} satellite`, cy)
    cy = row(doc, "Events", String(events.length), cy)
    cy = row(doc, "Partial failures", String(partialFailures), cy)
    cy = row(doc, "Exported at", new Date().toLocaleString(), cy)

    if (meta.isMidRun) {
      cy += 4
      doc.setTextColor(59, 130, 246); doc.setFontSize(8)
      doc.text("Note: exported while run was active. Final output may not be available.", 20, cy)
      cy += 5; doc.text("Re-export after run_done for a complete report.", 20, cy)
    }
    if (!meta.hasRunDone && meta.hasRootNodeDone) {
      cy += 4
      doc.setTextColor(234, 179, 8); doc.setFontSize(8)
      doc.text("Root node completed but run_done has not been received yet.", 20, cy)
    }

    // Run health summary box
    cy += 8
    doc.setDrawColor(30, 41, 59); doc.setFillColor(15, 23, 42); doc.roundedRect(18, cy, 100, 38, 2, 2, "FD")
    doc.setTextColor(96, 165, 250); doc.setFontSize(8.5); doc.text("Run Health", 22, cy + 7)
    doc.setFontSize(7.5); doc.setTextColor(148, 163, 184)
    const hasRunDoneEv = meta.hasRunDone; const hasRootDoneEv = meta.hasRootNodeDone
    doc.text(`  run_done received:   ${hasRunDoneEv ? "yes" : "no"}`, 20, cy + 13)
    doc.text(`  root node_done:      ${hasRootDoneEv ? "yes" : "no"}`, 20, cy + 18)
    doc.text(`  partial child fails: ${partialFailures}`, 20, cy + 23)
    doc.text(`  export completeness: ${meta.exportCompleteness}`, 20, cy + 28)

    // Plan recovery summary if any
    const recoveryEvents = freshEvents.filter(ev => ["plan_validation_failed","plan_retry_start","plan_retry_done","plan_abandoned","plan_replaced"].includes(ev.event || ""))
    if (recoveryEvents.length > 0) {
      doc.setDrawColor(30, 41, 59); doc.setFillColor(40, 20, 10); doc.roundedRect(130, cy, 120, 38, 2, 2, "FD")
      doc.setTextColor(251, 146, 60); doc.setFontSize(8.5); doc.text("Plan Recovery", 134, cy + 7)
      doc.setFontSize(7.5); doc.setTextColor(148, 163, 184)
      const retries = recoveryEvents.filter(ev => ev.event === "plan_retry_start").length
      const abandoned = recoveryEvents.some(ev => ev.event === "plan_abandoned")
      doc.text(`  retries: ${retries}`, 132, cy + 13)
      doc.text(`  abandoned: ${abandoned ? "yes" : "no"}`, 132, cy + 18)
      doc.text(`  events: ${recoveryEvents.length}`, 132, cy + 23)
    }

    // ── Graph page ──────────────────────────────────────────────────────────
    const svgEl = graphRef.current?.querySelector("svg")
    if (svgEl && graphNodesRef.current.length > 0) {
      const ns = graphNodesRef.current.filter(n => n.x !== undefined && n.y !== undefined)
      if (ns.length > 0) {
        const pad = 60
        const xs = ns.map(n => n.x!); const ys = ns.map(n => n.y!)
        const x0 = Math.min(...xs) - pad; const y0 = Math.min(...ys) - pad
        const bw = Math.max(...xs) - x0 + pad; const bh = Math.max(...ys) - y0 + pad
        const savedVB = svgEl.getAttribute("viewBox") || ""
        const zoomGroup = svgEl.querySelector("g") as SVGGElement | null
        const savedTransform = zoomGroup?.getAttribute("transform") || ""
        svgEl.setAttribute("viewBox", `${x0} ${y0} ${bw} ${bh}`)
        if (zoomGroup) zoomGroup.setAttribute("transform", "")
        const canvas = await html2canvas(svgEl as unknown as HTMLElement, { backgroundColor: "#070c17", scale: 1.5 })
        if (savedVB) svgEl.setAttribute("viewBox", savedVB); else svgEl.removeAttribute("viewBox")
        if (zoomGroup) zoomGroup.setAttribute("transform", savedTransform)
        newPage()
        // Graph legend
        doc.setTextColor(96, 165, 250); doc.setFontSize(10); doc.text("Execution Graph", 10, 10)
        doc.setFontSize(7); doc.setTextColor(148, 163, 184)
        const legendItems: [string, string][] = [["RAF node","#00e5ff"],["Base","#69ff47"],["Recursive","#f59e0b"],["Consortium","#ffd600"],["Jury","#ce93d8"],["Merge","#ff9100"]]
        legendItems.forEach(([label, color], i) => {
          const lx = 10 + i * 40
          doc.setTextColor(parseInt(color.slice(1,3),16), parseInt(color.slice(3,5),16), parseInt(color.slice(5,7),16))
          doc.text(`● ${label}`, lx, 14)
        })
        doc.setTextColor(148, 163, 184)
        doc.text(`Mode: ${graphMode} | Nodes: ${graphNodes.length} | Edges: ${graphLinks.length}`, 10, 18)
        const imgW = W - 20; const imgH = (canvas.height / canvas.width) * imgW
        doc.addImage(canvas.toDataURL("image/png"), "PNG", 10, 20, imgW, Math.min(imgH, H - 30))
      }
    }

    // ── RAF Nodes section ───────────────────────────────────────────────────
    newPage()
    let y = sectionHeader("RAF Nodes", 12)
    const rafNodes = graphNodes.filter(n => n.type === "raf-node")
    for (const n of rafNodes) {
      y = maybeNewPage(y, 28)
      doc.setTextColor(96, 165, 250); doc.setFontSize(8.5); doc.text(n.id, 10, y); y += 5
      doc.setFontSize(7.5); doc.setTextColor(148, 163, 184)
      y = row(doc, "Depth", String(n.depth ?? "—"), y, 14)
      y = row(doc, "Mode", n.caseType || "—", y, 14)
      y = row(doc, "Phase", n.phase || "—", y, 14)
      y = row(doc, "Confidence", n.confidence ? (n.confidence * 100).toFixed(0) + "%" : "—", y, 14)
      if (n.durationMs !== undefined) { y = row(doc, "Duration", `${n.durationMs}ms`, y, 14) }
      y = row(doc, "Status", n.success ? "success" : "in progress", y, 14)
      if (n.goal) {
        const goalLines = doc.splitTextToSize(`Goal: ${n.goal}`, W - 24)
        doc.setTextColor(100, 116, 139); doc.text(goalLines.slice(0, 2), 14, y); y += goalLines.slice(0, 2).length * 4
      }
      if (n.output) {
        const outLines = doc.splitTextToSize(`Output: ${n.output.slice(0, 200)}`, W - 24)
        doc.text(outLines.slice(0, 3), 14, y); y += outLines.slice(0, 3).length * 4
      }
      y += 2
      doc.setDrawColor(30, 41, 59); doc.line(10, y, W - 10, y); y += 3
    }

    // ── Consortium & Jury section ───────────────────────────────────────────
    const voteEvs = freshEvents.filter(ev => ev.event === "jury_votes")
    if (voteEvs.length > 0) {
      newPage(); y = sectionHeader("Jury Votes", 12)
      for (const ev of voteEvs) {
        y = maybeNewPage(y, 20)
        doc.setTextColor(168, 85, 247); doc.setFontSize(8.5)
        doc.text(`${ev.node_id || "?"} — task: ${ev.task || "?"}`, 10, y); y += 5
        doc.setFontSize(7.5); doc.setTextColor(148, 163, 184)
        y = row(doc, "Winner", String(ev.winner_id || "—"), y)
        y = row(doc, "Confidence", ev.confidence ? (ev.confidence * 100).toFixed(0) + "%" : "—", y)
        const votes = (ev.votes as any[]) || []
        votes.forEach((v: any, i: number) => {
          y = maybeNewPage(y, 5)
          const vote = v.vote || v
          row(doc, `Juror ${i + 1}`, `→ ${vote.winner_id || "?"}  ${vote.confidence ? (vote.confidence * 100).toFixed(0) + "%" : ""}`, y, 14)
          y += 4.5
        })
        y += 2
      }
    }

    // ── Plan recovery events ────────────────────────────────────────────────
    if (recoveryEvents.length > 0) {
      newPage(); y = sectionHeader("Plan Recovery Events", 12)
      for (const ev of recoveryEvents) {
        y = maybeNewPage(y, 14)
        doc.setTextColor(251, 146, 60); doc.setFontSize(8.5)
        doc.text(`${ev.event || "?"} — ${ev.node_id || "?"}`, 10, y); y += 5
        doc.setFontSize(7.5); doc.setTextColor(148, 163, 184)
        if ((ev as any).reason) { y = row(doc, "Reason", String((ev as any).reason).slice(0, 100), y) }
        if ((ev as any).retry) { y = row(doc, "Retry #", String((ev as any).retry), y) }
        y += 2
      }
    }

    // ── Checks / Spec / Tools sections ─────────────────────────────────────
    const checkEvs = freshEvents.filter(ev => ["scope_drift_detected","referee_report","spec_validation_final","spec_repair_start","tool_called","tool_blocked"].includes(ev.event || ""))
    if (checkEvs.length > 0) {
      newPage(); y = sectionHeader("Checks, Spec & Tools", 12)
      for (const ev of checkEvs) {
        y = maybeNewPage(y, 10)
        doc.setTextColor(100, 116, 139); doc.setFontSize(7.5)
        const line = `${(ev.event || "").padEnd(28)} ${(ev.node_id || "").padEnd(18)} ${ev.task || ""}`
        doc.setTextColor(148, 163, 184); doc.text(line, 10, y); y += 4.5
      }
    }

    // ── Raw timeline ────────────────────────────────────────────────────────
    newPage(); y = sectionHeader("Full Trace Timeline", 12)
    for (const ev of freshEvents) {
      y = maybeNewPage(y, 5)
      doc.setFontSize(7)
      const ts = ev.timestamp ? `+${((ev.timestamp * 1000) - (runStartRef.current || 0)).toFixed(0)}ms` : ""
      const line = `${(ev.event || ev.status || "").padEnd(26)} ${(ev.node_id || "").padEnd(18)} ${ts.padEnd(10)} ${ev.confidence ? (ev.confidence * 100).toFixed(0) + "%" : ""}`
      doc.setTextColor(148, 163, 184); doc.text(line, 10, y); y += 4
    }

    // ── Final output page ───────────────────────────────────────────────────
    if (freshResult) {
      newPage(); y = sectionHeader("Final Output", 12)
      doc.setFontSize(8); doc.setTextColor(148, 163, 184)
      const outputLines = doc.splitTextToSize(freshResult.slice(0, 3000), W - 20)
      outputLines.forEach((line: string) => { y = maybeNewPage(y, 5); doc.text(line, 10, y); y += 4.5 })
    }

    doc.save(`raf-report-${runId || "export"}.pdf`)
  }

  const submitAnswer = async () => {
    if (!clarifyAnswer.trim()) return
    const merged = `${accumulatedGoal || goal}\n\nUser answer: ${clarifyAnswer}`
    setAccumulatedGoal(merged); setClarifyQuestion(null); setClarifyAnswer("")
    await startRun(merged, true, true) // continueSession=true preserves existing timeline
  }

  const approvePlan = async () => {
    if (!pendingPlan || !runId) return
    await fetch(`${API_BASE}/api/run/${runId}/approve_plan`, {
      method: "POST", headers: authHeaders(runToken, true),
      body: JSON.stringify({ node_id: pendingPlan.nodeId, children: pendingPlan.children }),
    }).catch(() => {})
    setPendingPlan(null)
  }

  const filteredEvents = events.filter(ev => {
    if (timelineFilter === "all") return true
    return (TIMELINE_FILTER_EVENTS[timelineFilter] || []).includes(ev.event || ev.status || "")
  })
  const voteEvents = events.filter(ev => ev.event === "jury_votes")
  // Map of "node_id:task:role:agent_index" → short model label, built from model_call_done events.
  // Used to replace generic "agent-N" labels with actual model names in votes and proposals.
  const agentModelMap: Record<string, string> = {}
  for (const ev of events) {
    if (ev.event === "model_call_done" && ev.node_id && ev.task && ev.model !== undefined && ev.agent_index !== undefined && ev.role) {
      const label = String(ev.model).split("/").pop()?.replace(/:.*$/, "") || String(ev.model)
      agentModelMap[`${ev.node_id}:${ev.task}:${ev.role}:${ev.agent_index}`] = label
    }
  }
  const modelCallEvents = events.filter(ev => (ev.event || "").startsWith("model_call_"))
  const activeModelCall = (() => {
    const starts = [...modelCallEvents].reverse().filter(ev => ev.event === "model_call_start")
    return starts.find(start => !modelCallEvents.some(ev =>
      ev !== start &&
      ["model_call_done", "model_call_failed", "model_call_timeout"].includes(ev.event || "") &&
      ev.node_id === start.node_id &&
      ev.task === start.task &&
      ev.role === start.role &&
      ev.agent_index === start.agent_index &&
      (ev.timestamp || 0) >= (start.timestamp || 0)
    ))
  })()
  const slowestModelCalls = modelCallEvents
    .filter(ev => ev.event === "model_call_done" && typeof ev.duration_ms === "number")
    .slice()
    .sort((a, b) => (b.duration_ms || 0) - (a.duration_ms || 0))
    .slice(0, 3)
  const timedOutModelCalls = modelCallEvents.filter(ev => ev.event === "model_call_timeout")
  const specEvents = events.filter(ev => ["spec_extracted", "spec_validation_final", "spec_repair_start"].includes(ev.event || ""))
  const toolEvents = events.filter(ev => ["tool_called", "tool_blocked"].includes(ev.event || ""))
  const checkEvents = events.filter(ev => [
    "scope_drift_detected", "referee_report", "validator_children_filtered",
    "child_refined", "token_budget_exceeded", "mode_forced_recursive",
    "plan_validation_failed", "plan_retry_start", "plan_retry_done",
    "plan_abandoned", "plan_replaced", "model_call_failed", "model_call_timeout",
  ].includes(ev.event || ""))
  const latestSpec = [...events].reverse().find(ev => ev.event === "spec_extracted")
  const latestError = [...events].reverse().find(ev => ev.error)?.error || null
  const selectedOutput = selectedNode ? nodeOutputs.get(selectedNode.id) : null
  const selectedNodeEvents = selectedNode ? events.filter(ev => ev.node_id === selectedNode.id) : []
  const selectedNodeProposals = selectedNodeEvents.filter(ev => ev.event === "consortium_candidates")
  const selectedNodeVotes = selectedNodeEvents.filter(ev => ev.event === "jury_votes")
  const selectedNodeChildren = selectedNode
    ? graphLinks
      .filter(link => link.edgeType !== "dependency" && graphEndpointId(link.source) === selectedNode.id)
      .map(link => graphNodes.find(node => node.id === graphEndpointId(link.target)))
      .filter((node): node is GraphNode => Boolean(node))
    : []

  // Inspector: find source events for satellite nodes
  const inspectorOwner = selectedNode?.ownerNodeId
  const inspectorTask  = selectedNode?.task
  const inspectorCandidatesEvent = inspectorOwner && inspectorTask
    ? events.find(ev => ev.event === "consortium_candidates" && ev.node_id === inspectorOwner && ev.task === inspectorTask) as RafEvent | undefined
    : undefined
  const inspectorJuryEvent = inspectorOwner && inspectorTask
    ? events.find(ev => ev.event === "jury_votes" && ev.node_id === inspectorOwner && ev.task === inspectorTask) as RafEvent | undefined
    : undefined
  const inspectorCandidates: any[] = (inspectorCandidatesEvent as any)?.candidates || []
  const inspectorVotes: any[] = (inspectorJuryEvent as any)?.votes || []
  const inspectorWinnerId: string | undefined = (inspectorJuryEvent as any)?.winner_id
  const selectedDurationMs = selectedNode?.durationMs ?? (() => {
    if (!selectedNode) return undefined
    const created = selectedNodeEvents.find(ev => ev.event === "node_created")?.timestamp
    const done = selectedNodeEvents.find(ev => ev.event === "node_done")?.timestamp
    return created && done ? Math.max(0, Math.round((done - created) * 1000)) : undefined
  })()
  const running = runStatus === "running"
  const sidebarMinLeft = sidebarCollapsed ? 64 : sidebarWidth + 8

  const startSidebarResize = (e: PointerEvent<HTMLDivElement>) => {
    if (sidebarCollapsed) return
    sidebarResizeRef.current = { x: e.clientX, width: sidebarWidth }
    e.currentTarget.setPointerCapture(e.pointerId)
    e.preventDefault()
  }

  const moveSidebarResize = (e: PointerEvent<HTMLDivElement>) => {
    if (!sidebarResizeRef.current) return
    const dx = e.clientX - sidebarResizeRef.current.x
    const nextWidth = Math.min(420, Math.max(224, sidebarResizeRef.current.width + dx))
    setSidebarWidth(nextWidth)
    setWorkPanelPos(pos => pos.left < nextWidth + 8 ? { ...pos, left: nextWidth + 8 } : pos)
  }

  const endSidebarResize = () => {
    sidebarResizeRef.current = null
  }

  const startWorkPanelDrag = (e: PointerEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest("button")) return
    workPanelDragRef.current = { x: e.clientX, y: e.clientY, left: workPanelPos.left, top: workPanelPos.top }
    e.currentTarget.setPointerCapture(e.pointerId)
  }

  const moveWorkPanelDrag = (e: PointerEvent<HTMLDivElement>) => {
    if (!workPanelDragRef.current) return
    const dx = e.clientX - workPanelDragRef.current.x
    const dy = e.clientY - workPanelDragRef.current.y
    const maxLeft = Math.max(sidebarMinLeft, window.innerWidth - 440)
    const maxTop = Math.max(48, window.innerHeight - 220)
    setWorkPanelPos({
      left: Math.min(maxLeft, Math.max(sidebarMinLeft, workPanelDragRef.current.left + dx)),
      top: Math.min(maxTop, Math.max(48, workPanelDragRef.current.top + dy)),
    })
  }

  const endWorkPanelDrag = () => {
    workPanelDragRef.current = null
  }

  // ── render ────────────────────────────────────────────────────────────────────
  if (showLanding) {
    return (
      <Landing onEnter={() => {
        sessionStorage.setItem("raf-entered", "1")
        setShowLanding(false)
      }} />
    )
  }

  return (
    <div className="relative flex h-screen overflow-hidden bg-background text-foreground text-sm">

      {/* ══ LEFT SIDEBAR ══════════════════════════════════════════════════════════ */}
      <div
        className="relative flex flex-col border-r border-border bg-card shrink-0 transition-[width] duration-200"
        style={{ width: sidebarCollapsed ? 56 : sidebarWidth }}
      >

        {/* Logo */}
        <div className={`${sidebarCollapsed ? "px-2 py-3" : "px-4 py-3"} border-b border-border shrink-0`}>
          {sidebarCollapsed ? (
            <button
              type="button"
              title="Open RAF panel"
              onClick={() => setSidebarCollapsed(false)}
              className="mx-auto flex h-9 w-9 items-center justify-center rounded-md border border-border/70 bg-background/40 text-primary hover:bg-accent/50"
            >
              <Zap className="h-4 w-4" />
            </button>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  title="Collapse RAF panel"
                  onClick={() => setSidebarCollapsed(true)}
                  className="flex items-center gap-2 rounded-md px-1.5 py-1 -ml-1.5 hover:bg-accent/50"
                >
                  <Zap className="h-4 w-4 text-primary shrink-0" />
                  <span className="font-semibold tracking-tight">RAF</span>
                </button>
                <Badge
                  variant="outline"
                  className={`text-[9px] ml-auto ${backendStatus === "connected" ? "border-green-500/40 text-green-400" : backendStatus === "offline" ? "border-red-500/40 text-red-400" : "border-yellow-500/40 text-yellow-400"}`}
                >
                  {backendStatus === "connected" ? "API on" : backendStatus === "offline" ? "API off" : "API check"}
                </Badge>
                {detectedDomain && (
                  <Badge variant="outline" className="text-[10px] border-primary/40 text-primary">{detectedDomain}</Badge>
                )}
              </div>
              <p className="text-[10px] text-muted-foreground mt-0.5">Recursive Agent Framework</p>
              <button
                type="button"
                onClick={() => {
                  sessionStorage.removeItem("raf-entered")
                  setShowLanding(true)
                }}
                className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-border/70 px-2 py-1 text-[10px] text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              >
                <Home className="h-3 w-3" />
                Landing page
              </button>
            </>
          )}
        </div>

        {/* Sidebar tabs */}
        {sidebarCollapsed ? (
          <div className="flex flex-col items-center gap-2 py-3">
            <button
              type="button"
              title="Sessions"
              onClick={() => { setSidebarTab("sessions"); setSidebarCollapsed(false) }}
              className={`flex h-9 w-9 items-center justify-center rounded-md border ${sidebarTab === "sessions" ? "border-primary/50 bg-primary/10 text-primary" : "border-border/60 text-muted-foreground hover:bg-accent/50 hover:text-foreground"}`}
            >
              <History className="h-4 w-4" />
            </button>
            <button
              type="button"
              title="Params"
              onClick={() => { setSidebarTab("config"); setSidebarCollapsed(false) }}
              className={`flex h-9 w-9 items-center justify-center rounded-md border ${sidebarTab === "config" ? "border-primary/50 bg-primary/10 text-primary" : "border-border/60 text-muted-foreground hover:bg-accent/50 hover:text-foreground"}`}
            >
              <SlidersHorizontal className="h-4 w-4" />
            </button>
            <div className={`mt-1 h-2 w-2 rounded-full ${backendStatus === "connected" ? "bg-green-500" : backendStatus === "offline" ? "bg-red-500" : "bg-yellow-500"}`} title={backendStatus} />
            {running && <div className="h-2 w-2 rounded-full bg-blue-400 animate-pulse" title="RAF running" />}
          </div>
        ) : (
        <Tabs value={sidebarTab} onValueChange={v => setSidebarTab(v as "sessions" | "config")} className="flex w-full flex-col flex-1 min-h-0">
          <TabsList className="w-full rounded-none border-b border-border bg-transparent h-9 shrink-0 px-0">
            <TabsTrigger value="sessions" className="flex-1 rounded-none text-xs h-full data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
              Sessions
            </TabsTrigger>
            <TabsTrigger value="config" className="flex-1 rounded-none text-xs h-full data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
              Params
            </TabsTrigger>
          </TabsList>

          {/* Sessions */}
          <TabsContent value="sessions" className="flex flex-col flex-1 min-h-0 mt-0 data-[state=inactive]:hidden">
            <div className="px-3 py-2 border-b border-border shrink-0">
              <Button variant="outline" size="sm" className="w-full gap-1.5 text-xs"
                onClick={() => {
                  setGoal(""); setRunResult(null); setEvents([]); setGraphNodes([]); setGraphLinks([]); setNodeOutputs(new Map())
                  setRunStatus("idle"); setActiveSessionId(null); setSelectedNode(null); setDetectedDomain(null); setCurrentPhase("Idle")
                  graphNodesRef.current = []; graphLinksRef.current = []; seenEventsRef.current = new Set(); satelliteEventsRef.current = []
                  planChildrenRef.current = {}; planChildNodeRef.current = {}; nodeCreatedTsRef.current = {}; runStartRef.current = null
                }}>
                <Plus className="h-3 w-3" /> Clear Run
              </Button>
            </div>
            <ScrollArea className="h-full min-h-0 flex-1">
              <div className="p-2 space-y-1">
                {sessions.length === 0 && (
                  <p className="text-xs text-center text-muted-foreground py-8 px-3 leading-relaxed">No runs yet. Enter a goal and run RAF.</p>
                )}
                {sessions.map(s => (
                  <button key={s.id} onClick={() => restoreSession(s)}
                    className={`w-full text-left px-2.5 py-2 rounded-md transition-colors ${s.id === activeSessionId ? "bg-accent" : "hover:bg-accent/40"}`}>
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${s.status === "error" ? "bg-red-500" : s.status === "done" ? "bg-green-500" : s.status === "cancelled" ? "bg-yellow-500" : "bg-blue-400 animate-pulse"}`} />
                      <span className="text-xs font-medium truncate flex-1">{s.goal.slice(0, 30)}{s.goal.length > 30 ? "…" : ""}</span>
                    </div>
                    <div className="text-[10px] text-muted-foreground pl-3">{s.providerLabel || s.provider} | {new Date(s.ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</div>
                  </button>
                ))}
                <div className="pt-2 mt-2 border-t border-border">
                  <div className="flex items-center justify-between px-1 pb-1">
                    <p className="text-[10px] uppercase tracking-widest text-muted-foreground">Server runs</p>
                    <button onClick={refreshServerRuns} className="text-[10px] text-primary hover:underline">refresh</button>
                  </div>
                  {serverRuns.length === 0 && (
                    <p className="text-[10px] text-muted-foreground px-1 py-2">No server history available.</p>
                  )}
                  {serverRuns.slice(0, 8).map(r => (
                    <button key={r.run_id} onClick={() => replayServerRun(r)}
                      className="w-full text-left px-2.5 py-2 rounded-md transition-colors hover:bg-accent/40">
                      <div className="flex items-center gap-1.5 mb-0.5">
                        <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${r.status === "error" ? "bg-red-500" : r.status === "done" ? "bg-green-500" : r.status === "cancelled" ? "bg-yellow-500" : "bg-blue-400"}`} />
                        <span className="text-xs font-medium truncate flex-1">{r.goal || r.run_id}</span>
                      </div>
                      <div className="text-[10px] text-muted-foreground pl-3">{r.status} | {r.event_count} events</div>
                    </button>
                  ))}
                </div>
              </div>
            </ScrollArea>
            {/* Run health panel */}
            {running && (
              <div className="px-3 py-2 border-t border-border shrink-0 space-y-1.5">
                {staleWarning && (
                  <div className="flex items-center gap-1.5 rounded-md border border-yellow-500/40 bg-yellow-500/10 px-2 py-1 text-[10px] text-yellow-400">
                    <span className="h-1.5 w-1.5 rounded-full bg-yellow-400 animate-pulse shrink-0" />
                    No events for 90s — run may be stalled
                  </div>
                )}
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <div className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-pulse shrink-0" />
                  <span className="truncate flex-1">{currentPhase}</span>
                  {partialFailures > 0 && (
                    <span className="text-[10px] text-red-400 shrink-0">{partialFailures}✗</span>
                  )}
                </div>
                <div className="h-1 bg-secondary rounded-full overflow-hidden">
                  <div className="h-full bg-primary rounded-full transition-all duration-300" style={{ width: `${Math.min(100, (nodeCount / maxNodesTotal) * 100)}%` }} />
                </div>
                {/* Run health detail grid */}
                <div className="rounded-md border border-border/50 bg-muted/20 p-2 space-y-1 text-[10px]">
                  <div className="flex justify-between text-muted-foreground">
                    <span>Nodes</span><span className="font-mono">{nodeCount} / {maxNodesTotal}</span>
                  </div>
                  <div className="flex justify-between text-muted-foreground">
                    <span>Events</span><span className="font-mono">{events.length}</span>
                  </div>
                  {partialFailures > 0 && (
                    <div className="flex justify-between text-red-400">
                      <span>Partial fails</span><span className="font-mono">{partialFailures}</span>
                    </div>
                  )}
                  {lastEventAge !== null && (
                    <div className={`flex justify-between ${lastEventAge > 60 ? "text-yellow-400" : "text-muted-foreground"}`}>
                      <span>Last event</span>
                      <span className="font-mono">{lastEventAge < 60 ? `${lastEventAge}s ago` : `${Math.floor(lastEventAge / 60)}m ${lastEventAge % 60}s ago`}</span>
                    </div>
                  )}
                  {modelCallEvents.length > 0 && (
                    <div className="pt-1 border-t border-border/40 space-y-1">
                      <div className="flex justify-between text-muted-foreground">
                        <span>Model calls</span>
                        <span className="font-mono">{modelCallEvents.filter(ev => ev.event === "model_call_done").length}/{modelCallEvents.filter(ev => ev.event === "model_call_start").length}</span>
                      </div>
                      {activeModelCall && (
                        <div className="rounded border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-blue-300">
                          <p className="text-[9px] uppercase tracking-widest">Waiting on model</p>
                          <p className="truncate">{activeModelCall.role}/{activeModelCall.task} · {activeModelCall.provider}/{activeModelCall.model}</p>
                        </div>
                      )}
                      {timedOutModelCalls.length > 0 && (
                        <div className="flex justify-between text-yellow-400">
                          <span>Timeouts</span>
                          <span className="font-mono">{timedOutModelCalls.length}</span>
                        </div>
                      )}
                      {slowestModelCalls.length > 0 && (
                        <div className="space-y-0.5">
                          <p className="text-muted-foreground/60">Slowest calls:</p>
                          {slowestModelCalls.map((ev, i) => (
                            <div key={`${ev.node_id}-${ev.task}-${ev.agent_index}-${i}`} className="flex gap-1 text-muted-foreground/80">
                              <span className="min-w-0 flex-1 truncate">{ev.task} · {ev.provider}/{ev.model}</span>
                              <span className="font-mono shrink-0">{Math.round((ev.duration_ms || 0) / 1000)}s</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  {(() => {
                    const lastEv = [...events].reverse().find(ev => ev.event)
                    const hint = lastEv ? PHASE_NEXT_HINT[lastEv.event || ""] : null
                    return hint ? (
                      <div className="pt-0.5 border-t border-border/40">
                        <p className="text-muted-foreground/60">Expected next:</p>
                        <p className="text-muted-foreground/80">{hint}</p>
                      </div>
                    ) : null
                  })()}
                </div>
              </div>
            )}
          </TabsContent>

          {/* Config */}
          <TabsContent value="config" className="flex flex-col flex-1 min-h-0 mt-0 data-[state=inactive]:hidden">
            <ScrollArea className="h-full min-h-0 flex-1">
              <div className="p-2 space-y-1">

                <ParamGroup label="Strategy">
                  <div className="space-y-1.5">
                    {MODEL_STRATEGIES.map(s => {
                      const active = appliedStrategy === s.id
                      return (
                        <div key={s.id}
                          className={`rounded-md border p-2.5 transition-colors ${active ? "border-primary/70 bg-primary/8" : "border-border/50 bg-card/40"}`}>
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-xs font-semibold">{s.label}</span>
                                <span className={`rounded px-1.5 py-0.5 text-[9px] font-mono font-semibold ${active ? "bg-primary/20 text-primary" : "bg-muted/60 text-muted-foreground"}`}>{s.badge}</span>
                              </div>
                              <p className="text-[10px] text-muted-foreground mt-0.5">{s.tagline}</p>
                            </div>
                            <button type="button" disabled={running}
                              onClick={() => applyStrategy(s.id)}
                              title={active ? "Click to deselect this strategy" : "Apply this strategy"}
                              className={`shrink-0 rounded-md border px-2.5 py-1 text-[10px] font-medium transition-colors disabled:opacity-40 ${active ? "border-primary/60 bg-primary/15 text-primary hover:bg-destructive/20 hover:text-destructive hover:border-destructive/50" : "border-border/60 hover:bg-accent/50 text-muted-foreground hover:text-foreground"}`}>
                              {active ? "applied ×" : "apply"}
                            </button>
                          </div>
                          {active && (
                            <div className="mt-2 space-y-1 border-t border-border/40 pt-2">
                              <p className="text-[10px] text-muted-foreground">{s.description}</p>
                              <div className="mt-1.5 grid grid-cols-1 gap-1">
                                {s.tierRouting ? (
                                  <>
                                    <div className="flex gap-1.5 items-start">
                                      <span className="rounded px-1 text-[9px] font-mono bg-sky-950/60 text-sky-300 shrink-0 mt-0.5">leaf</span>
                                      <span className="text-[10px] text-muted-foreground">{s.consortiumNote}</span>
                                    </div>
                                    {s.midNote && (
                                      <div className="flex gap-1.5 items-start">
                                        <span className="rounded px-1 text-[9px] font-mono bg-amber-950/60 text-amber-300 shrink-0 mt-0.5">planner</span>
                                        <span className="text-[10px] text-muted-foreground">{s.midNote}</span>
                                      </div>
                                    )}
                                    <div className="flex gap-1.5 items-start">
                                      <span className="rounded px-1 text-[9px] font-mono bg-rose-950/60 text-rose-300 shrink-0 mt-0.5">referee</span>
                                      <span className="text-[10px] text-muted-foreground">{s.juryNote}</span>
                                    </div>
                                  </>
                                ) : (
                                  <>
                                    <div className="flex gap-1.5 items-start">
                                      <span className="rounded px-1 text-[9px] font-mono bg-amber-950/60 text-amber-300 shrink-0 mt-0.5">consortium</span>
                                      <span className="text-[10px] text-muted-foreground">{s.consortiumNote}</span>
                                    </div>
                                    <div className="flex gap-1.5 items-start">
                                      <span className="rounded px-1 text-[9px] font-mono bg-purple-950/60 text-purple-300 shrink-0 mt-0.5">jury</span>
                                      <span className="text-[10px] text-muted-foreground">{s.juryNote}</span>
                                    </div>
                                  </>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </ParamGroup>

                <ParamGroup label="Model routing">
                  <div className="flex items-center justify-between rounded-md border border-border/60 p-2">
                    <div>
                      <p className="text-xs font-medium">Multiple models</p>
                      <p className="text-[10px] text-muted-foreground">{multiModel ? "Each slot chooses its own provider/model." : "Use one provider/model for the whole run."}</p>
                    </div>
                    <Switch checked={multiModel} onCheckedChange={setMultiModel} disabled={running} />
                  </div>

                  {provider !== "mock" && (
                    <div className="space-y-1">
                      <label className="text-[10px] text-muted-foreground font-medium">OpenRouter API Key</label>
                      <Input
                        type="password"
                        placeholder="sk-or-v1-…  (stored locally, never sent to our servers)"
                        value={apiKey}
                        onChange={e => {
                          setApiKey(e.target.value)
                          localStorage.setItem(API_KEY_STORAGE_KEY, e.target.value)
                        }}
                        disabled={running}
                        className="font-mono text-xs h-7"
                      />
                      <p className="text-[10px] leading-4 text-muted-foreground">
                        Paste your own OpenRouter key here. It stays in this browser via local storage and is sent only
                        with your run request.
                      </p>
                      <p className="text-[10px] leading-4 text-muted-foreground">
                        Need one? Open <span className="font-mono">openrouter.ai/keys</span>, create a key, copy it,
                        and paste it into this box.
                      </p>
                    </div>
                  )}

                  {!multiModel ? (
                    <ModelChooser
                      title="Single routing"
                      provider={provider}
                      model={model}
                      juryModel={juryModel}
                      providers={providers}
                      availableProviders={availableProviders}
                      models={models}
                      modelCatalog={modelCatalog}
                      disabled={running}
                      open={modelPickerOpen}
                      onOpenChange={setModelPickerOpen}
                      onProviderChange={nextProvider => {
                        setProvider(nextProvider)
                        setModel(models[nextProvider]?.[0] || "")
                        if (juryModel) setJuryModel(models[nextProvider]?.[0] || "")
                      }}
                      onModelChange={setModel}
                      onJuryModelChange={setJuryModel}
                    />
                  ) : (
                    <div className="space-y-3 rounded-md border border-border/60 p-2">
                      {/* Tier routing toggle */}
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-xs font-medium">Depth-based tier routing</p>
                          <p className="text-[10px] text-muted-foreground">
                            {tierRouting
                              ? "Leaf → Mid → Root tiers active. Flat consortium/jury slots are ignored."
                              : "Use flat consortium + jury slots for all nodes."}
                          </p>
                        </div>
                        <Switch checked={tierRouting} onCheckedChange={v => { setAppliedStrategy(null); setTierRouting(v) }} disabled={running} />
                      </div>

                      {tierRouting ? (
                        <>
                          <div className="space-y-1">
                            <div className="flex items-center gap-1.5">
                              <span className="rounded px-1.5 py-0.5 text-[9px] font-mono font-semibold bg-sky-950/60 text-sky-300">Tier 0 · Leaf workers</span>
                              <span className="text-[10px] text-muted-foreground">deep base_execute nodes</span>
                            </div>
                            <SlotEditor
                              title=""
                              slots={normalizeSlots(leafSlots, leafSlots.length || 2, provider, model)}
                              size={leafSlots.length || 2}
                              minSize={1}
                              maxSize={6}
                              providers={providers}
                              models={models}
                              modelCatalog={modelCatalog}
                              availableProviders={availableProviders}
                              disabled={running}
                              onSizeChange={n => setLeafSlots(normalizeSlots(leafSlots, n, provider, model))}
                              onChange={updateLeafSlot}
                            />
                          </div>
                          <Separator />
                          <div className="space-y-1">
                            <div className="flex items-center gap-1.5">
                              <span className="rounded px-1.5 py-0.5 text-[9px] font-mono font-semibold bg-amber-950/60 text-amber-300">Tier 1 · Planners</span>
                              <span className="text-[10px] text-muted-foreground">mid-level planning, merging · also jury floor for Tier 0</span>
                            </div>
                            <SlotEditor
                              title=""
                              slots={normalizeSlots(midSlots, midSlots.length || 2, provider, model)}
                              size={midSlots.length || 2}
                              minSize={1}
                              maxSize={6}
                              providers={providers}
                              models={models}
                              modelCatalog={modelCatalog}
                              availableProviders={availableProviders}
                              disabled={running}
                              onSizeChange={n => setMidSlots(normalizeSlots(midSlots, n, provider, model))}
                              onChange={updateMidSlot}
                            />
                          </div>
                          <Separator />
                          <div className="space-y-1">
                            <div className="flex items-center gap-1.5">
                              <span className="rounded px-1.5 py-0.5 text-[9px] font-mono font-semibold bg-rose-950/60 text-rose-300">Tier 2 · Referee</span>
                              <span className="text-[10px] text-muted-foreground">root node + all analysis decisions · strongest models</span>
                            </div>
                            <SlotEditor
                              title=""
                              slots={normalizeSlots(rootSlots, rootSlots.length || 2, provider, model)}
                              size={rootSlots.length || 2}
                              minSize={1}
                              maxSize={6}
                              providers={providers}
                              models={models}
                              modelCatalog={modelCatalog}
                              availableProviders={availableProviders}
                              disabled={running}
                              onSizeChange={n => setRootSlots(normalizeSlots(rootSlots, n, provider, model))}
                              onChange={updateRootSlot}
                            />
                          </div>
                        </>
                      ) : (
                        <>
                          <SlotEditor
                            title="Consortium slots"
                            slots={normalizeSlots(consortiumSlots, consortiumSize, provider, model)}
                            size={consortiumSize}
                            minSize={1}
                            maxSize={10}
                            providers={providers}
                            models={models}
                            modelCatalog={modelCatalog}
                            availableProviders={availableProviders}
                            disabled={running}
                            onSizeChange={setConsortiumSize}
                            onChange={updateConsortiumSlot}
                          />
                          <Separator />
                          <SlotEditor
                            title="Jury slots"
                            slots={normalizeSlots(jurySlots, jurySize, provider, juryModel || model)}
                            size={jurySize}
                            minSize={1}
                            maxSize={10}
                            providers={providers}
                            models={models}
                            modelCatalog={modelCatalog}
                            availableProviders={availableProviders}
                            disabled={running}
                            onSizeChange={setJurySize}
                            onChange={updateJurySlot}
                          />
                        </>
                      )}
                    </div>
                  )}
                </ParamGroup>

                <ParamGroup label="Run context">
                  <ConfigSection label="Domain override">
                    <Select value={domainOverride} onChange={e => setDomainOverride(e.target.value)} disabled={running}>
                      {DOMAIN_OPTIONS.map(d => <option key={d || "auto"} value={d}>{d || "auto detect"}</option>)}
                    </Select>
                  </ConfigSection>

                  <ConfigSection label="System prompt">
                    <Textarea
                      value={systemPrompt}
                      onChange={e => setSystemPrompt(e.target.value)}
                      disabled={running}
                      placeholder="Optional extra instruction for all RAF agents"
                      rows={3}
                      className="text-xs leading-relaxed"
                    />
                  </ConfigSection>
                </ParamGroup>

                <ParamGroup label="Agent counts">
                  <PS label="Consortium size" value={consortiumSize} min={1} max={10} disabled={running} onChange={setConsortiumSize} />
                  <PS label="Jury size" value={jurySize} min={1} max={10} disabled={running} onChange={setJurySize} />
                </ParamGroup>

                {/* Always decompose — prominent toggle */}
                <div className={`rounded-md border px-3 py-2.5 flex items-center justify-between transition-colors ${forceRecursive ? "border-primary/50 bg-primary/5" : "border-border"}`}>
                  <div>
                    <p className="text-xs font-medium">Always decompose</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">Force full recursive tree — shows all system capabilities</p>
                  </div>
                  <Switch checked={forceRecursive} onCheckedChange={setForceRecursive} disabled={running} />
                </div>

                <ParamGroup label="Recursion">
                  <PS label="Max depth" value={maxDepth} min={1} max={12} disabled={running} onChange={setMaxDepth} />
                  <PS label="Max parallel children" value={maxParallelChildren} min={1} max={20} disabled={running} onChange={setMaxParallelChildren} />
                  <PS label="Max nodes" value={maxNodesTotal} min={5} max={200} step={5} disabled={running} onChange={setMaxNodesTotal} />
                </ParamGroup>

                <ParamGroup label="Controls">
                  <div className="space-y-3">
                    {([
                      [toolsEnabled, setToolsEnabled, "Enable tools (web_search, http_get)"] as const,
                    ]).map(([val, setter, label]) => (
                      <div key={label} className="flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">{label}</span>
                        <Switch checked={val} onCheckedChange={v => setter(v)} disabled={running} />
                      </div>
                    ))}
                    <ConfigSection label="Plan governance">
                      <Select
                        value={planGovernance}
                        onChange={e => setPlanGovernance(e.target.value as "auto" | "review" | "manual")}
                        disabled={running}
                      >
                        <option value="auto">auto — RAF decides</option>
                        <option value="review">review — show plan, auto-approve</option>
                        <option value="manual">manual — block until approved</option>
                      </Select>
                    </ConfigSection>
                    <ConfigSection label="Plan recovery">
                      <Select
                        value={planRecovery}
                        onChange={e => setPlanRecovery(e.target.value as "off" | "auto" | "ask")}
                        disabled={running}
                      >
                        <option value="off">off — no retry on bad plan</option>
                        <option value="auto">auto retry — backend replans (requires backend support)</option>
                        <option value="ask">ask — UI prompt before retry (requires backend support)</option>
                      </Select>
                      {planRecovery !== "off" && (
                        <p className="text-[10px] text-yellow-500/80 mt-1">Requires backend plan_validation_failed events to activate.</p>
                      )}
                    </ConfigSection>
                  </div>
                </ParamGroup>

              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
        )}
        {!sidebarCollapsed && (
          <div
            role="separator"
            aria-orientation="vertical"
            title="Drag to resize RAF panel"
            onPointerDown={startSidebarResize}
            onPointerMove={moveSidebarResize}
            onPointerUp={endSidebarResize}
            onPointerCancel={endSidebarResize}
            onDoubleClick={() => setSidebarWidth(264)}
            className="absolute right-[-3px] top-0 z-30 h-full w-2 cursor-col-resize touch-none border-r border-transparent hover:border-primary/60 hover:bg-primary/10"
          />
        )}
      </div>

      {/* ══ CENTER PANEL ══════════════════════════════════════════════════════════ */}
      <div
        className={`${workPanelOpen ? "flex" : "hidden"} absolute bottom-4 z-20 flex-col w-[420px] max-w-[calc(100vw-20rem)] min-h-0 overflow-hidden rounded-lg border border-border bg-card/88 backdrop-blur-md shadow-2xl`}
        style={{ left: workPanelPos.left, top: workPanelPos.top }}
      >

        {/* Goal input area */}
        <div className="p-3 border-b border-border shrink-0 space-y-3">
          <div
            className="flex cursor-grab items-center justify-between active:cursor-grabbing"
            onPointerDown={startWorkPanelDrag}
            onPointerMove={moveWorkPanelDrag}
            onPointerUp={endWorkPanelDrag}
            onPointerCancel={endWorkPanelDrag}
          >
            <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">Run workspace</span>
            <Button variant="ghost" size="sm" className="h-6 px-2 text-[10px]" onClick={() => setWorkPanelOpen(false)}>
              Hide
            </Button>
          </div>
          <Textarea
            value={goal}
            onChange={e => setGoal(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && !running) startRun(goal) }}
            placeholder="Enter a goal for RAF to solve recursively… (Ctrl+Enter to run)"
            rows={4}
            disabled={running}
            className="font-mono text-sm leading-relaxed"
          />
          <div className="flex gap-2">
            {running ? (
              <Button variant="destructive" size="sm" className="flex-1 gap-2" onClick={cancelRun}>
                <Square className="h-3.5 w-3.5" /> Cancel
              </Button>
            ) : (
              <Button size="sm" className="flex-1 gap-2" onClick={() => startRun(goal)} disabled={!goal.trim()}>
                <Play className="h-3.5 w-3.5" /> Run RAF
              </Button>
            )}
            <Button variant="outline" size="sm" disabled={running}
              onClick={() => { setGoal("HANOI(3,0,2,1)"); setProvider("mock") }}>
              Demo
            </Button>
          </div>

          {/* Clarification card */}
          <AnimatePresence>
            {clarifyQuestion && (
              <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <Card className="border-primary/40 bg-primary/5">
                  <CardContent className="pt-3 space-y-2">
                    <p className="text-xs font-medium text-primary">Clarification needed</p>
                    <p className="text-sm leading-relaxed">{clarifyQuestion}</p>
                    <div className="flex gap-2">
                      <Input value={clarifyAnswer} onChange={e => setClarifyAnswer(e.target.value)}
                        onKeyDown={e => e.key === "Enter" && submitAnswer()}
                        placeholder="Your answer…" />
                      <Button size="sm" disabled={!clarifyAnswer.trim()} onClick={submitAnswer}>Send</Button>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Plan approval card */}
          <AnimatePresence>
            {pendingPlan && (
              <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                <Card className="border-amber-500/40 bg-amber-500/5">
                  <CardContent className="pt-3 space-y-2">
                    <p className="text-xs font-medium text-amber-400">Plan approval — {pendingPlan.children.length} children</p>
                    <div className="space-y-1 max-h-28 overflow-y-auto">
                      {pendingPlan.children.map((c, i) => (
                        <p key={i} className="text-xs text-muted-foreground">• {c.goal}</p>
                      ))}
                    </div>
                    <Button variant="outline" size="sm" className="w-full border-amber-500/40 text-amber-400 hover:bg-amber-500/10 hover:text-amber-300" onClick={approvePlan}>
                      Approve Plan
                    </Button>
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Center tabs */}
        <Tabs value={centerTab} onValueChange={v => setCenterTab(v as typeof centerTab)} className="flex w-full flex-col flex-1 min-h-0">
          <TabsList className="w-full rounded-none border-b border-border bg-transparent h-10 shrink-0 px-0">
            <TabsTrigger value="output" className="flex-1 px-1 rounded-none text-[10px] h-full gap-1 data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
              <FileText className="h-3 w-3" /> Output
            </TabsTrigger>
            <TabsTrigger value="timeline" className="flex-1 px-1 rounded-none text-[10px] h-full gap-1 data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
              <Clock className="h-3 w-3" /> Timeline
            </TabsTrigger>
            <TabsTrigger value="votes" className="flex-1 px-1 rounded-none text-[10px] h-full gap-1 data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
              <Vote className="h-3 w-3" /> Votes
              {voteEvents.length > 0 && <Badge variant="outline" className="text-[9px] h-4 px-1 ml-0.5">{voteEvents.length}</Badge>}
            </TabsTrigger>
            <TabsTrigger value="spec" className="flex-1 px-1 rounded-none text-[10px] h-full data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
              Spec
            </TabsTrigger>
            <TabsTrigger value="tools" className="flex-1 px-1 rounded-none text-[10px] h-full data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
              Tools
            </TabsTrigger>
            <TabsTrigger value="checks" className="flex-1 px-1 rounded-none text-[10px] h-full data-[state=active]:border-b-2 data-[state=active]:border-primary data-[state=active]:shadow-none">
              Checks
            </TabsTrigger>
          </TabsList>

          {/* Output tab */}
          <TabsContent value="output" className="flex w-full flex-col flex-1 min-h-0 mt-0 overflow-hidden data-[state=inactive]:hidden">
            {runStatus === "error" && latestError ? (
              <ScrollArea className="flex-1 min-h-0">
                <div className="p-5 space-y-3">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 rounded-full bg-red-500" />
                    <span className="text-xs font-medium text-red-400">Run failed</span>
                    {runId && <Badge variant="outline" className="text-[10px] font-mono">{runId.slice(0, 8)}</Badge>}
                  </div>
                  <div className="rounded-md border border-red-500/30 bg-red-500/10 p-3">
                    <p className="text-[10px] uppercase tracking-widest text-red-300 mb-1">Error</p>
                    <p className="break-words font-mono text-xs leading-relaxed text-red-100">{latestError}</p>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Timeline and Checks keep the trace events that arrived before the failure.
                  </p>
                </div>
              </ScrollArea>
            ) : runResult ? (
              <ScrollArea className="flex-1 min-h-0">
                <div className="p-5">
                  <div className="flex items-center gap-2 mb-4">
                    <div className="h-2 w-2 rounded-full bg-green-500" />
                    <span className="text-xs font-medium text-green-400">Run complete</span>
                    {detectedDomain && <Badge variant="outline" className="text-[10px] border-primary/40 text-primary">{detectedDomain}</Badge>}
                    <button
                      className="ml-auto text-[10px] text-muted-foreground hover:text-foreground border border-border rounded px-2 py-0.5 transition-colors"
                      onClick={() => setExpandModal({ title: "Run Output", content: runResult })}
                    >⤢ Expand</button>
                  </div>
                  <div className="output-body whitespace-pre-wrap" dangerouslySetInnerHTML={{ __html: formatOutput(runResult) }} />
                </div>
              </ScrollArea>
            ) : selectedNode && selectedOutput ? (
              <ScrollArea className="flex-1 min-h-0">
                <div className="p-4 space-y-3">
                  <div><p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-1">Node</p>
                    <p className="font-mono text-xs text-primary">{selectedNode.id}</p></div>
                  {selectedOutput.goal && (
                    <div><p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-1">Goal</p>
                      <p className="text-xs leading-relaxed">{selectedOutput.goal}</p></div>
                  )}
                  <div className="flex gap-4">
                    <div><p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-1">Mode</p>
                      <Badge variant="outline" className="text-[10px]">{selectedOutput.mode}</Badge></div>
                    <div><p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-1">Confidence</p>
                      <p className="text-xs font-mono">{(selectedOutput.confidence * 100).toFixed(0)}%</p></div>
                  </div>
                  <Separator />
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Output</p>
                      <button
                        className="ml-auto text-[10px] text-muted-foreground hover:text-foreground border border-border rounded px-2 py-0.5 transition-colors"
                        onClick={() => setExpandModal({ title: "Node Output", content: selectedOutput.output })}
                      >⤢ Expand</button>
                    </div>
                    <div className="output-body text-xs whitespace-pre-wrap" dangerouslySetInnerHTML={{ __html: formatOutput(selectedOutput.output) }} />
                  </div>
                </div>
              </ScrollArea>
            ) : (
              <div className="h-full flex items-center justify-center text-center p-8">
                <div>
                  <Network className="h-10 w-10 text-muted-foreground/20 mx-auto mb-3" />
                  <p className="text-sm text-muted-foreground">Output appears here when the run completes.</p>
                  <p className="text-xs text-muted-foreground/60 mt-1">Click a graph node to inspect its output.</p>
                </div>
              </div>
            )}
          </TabsContent>

          {/* Timeline tab */}
          <TabsContent value="timeline" className="flex w-full flex-col flex-1 min-h-0 mt-0 overflow-hidden data-[state=inactive]:hidden">
            <div className="flex gap-1 px-3 py-2 border-b border-border shrink-0 flex-wrap">
              {(["all", "node", "vote", "execution", "model", "error"] as const).map(f => (
                <button key={f} onClick={() => setTimelineFilter(f)}
                  className={`text-[10px] px-2 py-0.5 rounded-full border font-medium transition-colors ${timelineFilter === f ? "border-primary text-primary bg-primary/10" : "border-border text-muted-foreground hover:border-primary/50"}`}>
                  {f}
                </button>
              ))}
            </div>
            <ScrollArea className="flex-1">
              <div className="p-2 space-y-1">
                {filteredEvents.length === 0 && (
                  <p className="text-xs text-center text-muted-foreground py-8">{running ? "Waiting for events…" : "No events yet."}</p>
                )}
                {filteredEvents.map((ev, i) => (
                  <div key={i} className="group w-full text-left px-3 py-2 rounded-md bg-card hover:bg-accent/40 transition-colors">
                    <div className="flex items-center gap-2">
                      <div
                        className="h-1.5 w-1.5 rounded-full shrink-0 cursor-pointer"
                        style={{ background: EVENT_COLORS[ev.event || ""] || "#475569" }}
                        onClick={() => { if (ev.node_id) { const n = graphNodes.find(g => g.id === ev.node_id); if (n) setSelectedNode(n) } }}
                      />
                      <span
                        className="text-xs font-medium flex-1 cursor-pointer"
                        onClick={() => { if (ev.node_id) { const n = graphNodes.find(g => g.id === ev.node_id); if (n) setSelectedNode(n) } }}
                      >{eventLabel(ev)}</span>
                      {ev.node_id && <span className="text-[10px] font-mono text-muted-foreground shrink-0">{ev.node_id}</span>}
                      <span className="text-[10px] text-muted-foreground/60 shrink-0 font-mono">{relTs(ev.timestamp, runStartRef.current)}</span>
                      <button
                        className="opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground hover:text-foreground shrink-0 transition-opacity px-1"
                        title="Expand full event"
                        onClick={e => { e.stopPropagation(); setExpandModal({ title: eventLabel(ev), content: JSON.stringify(ev, null, 2) }) }}
                      >⤢</button>
                    </div>
                    {ev.event === "consortium_candidates" && (ev as any).tier !== undefined && (
                      <div className="pl-3.5 mt-0.5 flex items-center gap-1.5">
                        {tierBadge((ev as any).tier)}
                        <span className="text-[10px] text-muted-foreground font-mono">{(ev as any).task}</span>
                        <span className="text-[10px] text-muted-foreground">· {(ev as any).candidates?.length ?? "?"} proposals</span>
                      </div>
                    )}
                    {ev.event === "mode_decided" && (ev as any).winner && (
                      <p className="text-[10px] text-muted-foreground pl-3.5 mt-0.5">→ {(ev as any).winner}{(ev as any).confidence ? ` (${((ev as any).confidence * 100).toFixed(0)}%)` : ""}</p>
                    )}
                    {ev.event === "node_done" && ev.confidence && (
                      <p className="text-[10px] text-muted-foreground pl-3.5 mt-0.5">{ev.mode} | {(ev.confidence * 100).toFixed(0)}%</p>
                    )}
                    {ev.event === "model_call_failed" && (
                      <p className="text-[10px] pl-3.5 mt-0.5 flex items-center gap-1.5">
                        {ev.cause ? (
                          <>
                            <span className="rounded px-1 py-0.5 font-mono text-[9px] font-semibold"
                              style={{ background: ev.cause === "api_error" ? "#7f1d1d" : ev.cause === "parse_error" ? "#78350f" : "#1e1b4b", color: "#fca5a5" }}>
                              {CAUSE_LABELS[ev.cause]?.label ?? ev.cause}
                            </span>
                            <span className="text-muted-foreground">{CAUSE_LABELS[ev.cause]?.detail}</span>
                          </>
                        ) : (
                          <span className="text-muted-foreground">{ev.error || "Unknown failure"}</span>
                        )}
                      </p>
                    )}
                    {ev.event === "model_call_timeout" && ev.timeout_ms !== undefined && (
                      <p className="text-[10px] text-muted-foreground pl-3.5 mt-0.5">
                        <span className="rounded px-1 py-0.5 font-mono text-[9px] font-semibold" style={{ background: "#451a03", color: "#fbbf24" }}>Timeout</span>
                        {" "}waited {(ev.timeout_ms / 1000).toFixed(1)}s — model was still running
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>

          {/* Votes tab */}
          <TabsContent value="votes" className="flex w-full flex-col flex-1 min-h-0 mt-0 overflow-hidden data-[state=inactive]:hidden">
            <div className="flex items-center justify-between border-b border-border px-3 py-2 text-[10px] text-muted-foreground shrink-0">
              <span className="uppercase tracking-widest">Jury votes</span>
              <span className="font-mono tabular-nums">{voteEvents.length} events</span>
            </div>
            <ScrollArea className="flex-1 min-h-0">
              <div className="flex min-h-full w-full max-w-full flex-col gap-2 overflow-hidden p-3">
                {voteEvents.length === 0 && (
                  <p className="text-xs text-center text-muted-foreground py-8">No votes yet.</p>
                )}
                {voteEvents.map((ev, i) => {
                  const options = (ev.options as any[]) || []
                  const votes = (ev.votes as any[]) || []
                  return (
                    <Card key={i} className="w-full min-w-0 max-w-full overflow-hidden">
                      <CardContent className="min-w-0 max-w-full overflow-hidden p-3 space-y-2">
                        <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-start gap-2">
                          <div className="flex min-w-0 flex-wrap items-center gap-2">
                            <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wider text-purple-400">{ev.task}</span>
                            {ev.node_id && <span className="min-w-0 break-all text-[10px] font-mono text-muted-foreground">{ev.node_id}</span>}
                          </div>
                          <span className="shrink-0 text-xs font-mono">{ev.confidence ? (ev.confidence * 100).toFixed(0) + "%" : "—"}</span>
                        </div>

                        {options.length > 0 && (
                          <div className="min-w-0 max-w-full space-y-1.5 overflow-hidden">
                            <p className="text-[10px] text-muted-foreground uppercase tracking-widest">Proposals</p>
                            {options.map((opt: any, oi: number) => {
                              const payload = opt.payload || opt
                              const isWinner = ev.winner_id === opt.option_id
                              const fullText = payload.output || payload.mode || payload.plan || JSON.stringify(payload, null, 2)
                              const preview = fullText.length > 300 ? fullText.slice(0, 300) + "…" : fullText
                              return (
                                <div key={oi} className={`group min-w-0 max-w-full overflow-hidden rounded-md p-2 text-xs border ${isWinner ? "border-primary/50 bg-primary/5" : "border-border"}`}>
                                  <div className="flex min-w-0 max-w-full flex-wrap items-center gap-1.5 mb-1">
                                    <span className="min-w-0 font-mono text-[10px] text-muted-foreground">{optionLabel(opt.option_id)}</span>
                                    {isWinner && <Badge className="text-[9px] h-4 px-1 bg-primary/20 text-primary border-primary/30">winner</Badge>}
                                    <button
                                      className="ml-auto opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground hover:text-foreground transition-opacity"
                                      onClick={() => setExpandModal({ title: `${optionLabel(opt.option_id)} · ${ev.task ?? "proposal"}`, content: fullText })}
                                    >⤢</button>
                                  </div>
                                  <p className="min-w-0 max-w-full whitespace-pre-wrap break-all text-muted-foreground">{preview}</p>
                                </div>
                              )
                            })}
                          </div>
                        )}

                        {votes.length > 0 && (
                          <div className="min-w-0 max-w-full space-y-1 overflow-hidden pt-1 border-t border-border">
                            <p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-1">Votes</p>
                            {votes.map((v: any, vi: number) => {
                              const vote = v.vote || v
                              const modelLabel = agentModelMap[`${ev.node_id}:${ev.task}:jury:${v.agent_id}`] || `agent-${v.agent_id}`
                              return (
                                <div key={vi} className="grid min-w-0 max-w-full grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)_auto] items-center gap-2 text-xs">
                                  <span className="min-w-0 truncate font-mono text-[10px] text-purple-300" title={modelLabel}>{modelLabel}</span>
                                  <span className="text-muted-foreground shrink-0">→</span>
                                  <span className="min-w-0 font-mono text-[10px]">{optionLabel(vote.winner_id)}</span>
                                  {vote.confidence && <span className="shrink-0 text-muted-foreground text-[10px]">{(vote.confidence * 100).toFixed(0)}%</span>}
                                </div>
                              )
                            })}
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="spec" className="flex w-full flex-col flex-1 min-h-0 mt-0 overflow-hidden data-[state=inactive]:hidden">
            <ScrollArea className="flex-1 min-h-0">
              <div className="p-3 space-y-3">
                {!latestSpec && specEvents.length === 0 && (
                  <p className="text-xs text-center text-muted-foreground py-8">No spec events yet.</p>
                )}
                {latestSpec && (
                  <Card className="min-w-0 overflow-hidden">
                    <CardContent className="p-3 space-y-3">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-[10px]">{latestSpec.domain || "general"}</Badge>
                        {(latestSpec as any).task_class && <Badge variant="outline" className="text-[10px]">{(latestSpec as any).task_class}</Badge>}
                      </div>
                      <SpecList label="Required" items={latestSpec.required || []} />
                      <SpecList label="Forbidden" items={latestSpec.forbidden || []} />
                      <SpecList label="Success criteria" items={latestSpec.success_criteria || []} />
                    </CardContent>
                  </Card>
                )}
                {specEvents.filter(ev => ev.event !== "spec_extracted").map((ev, i) => (
                  <EventCard key={`${ev.event}-${i}`} ev={ev} />
                ))}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="tools" className="flex w-full flex-col flex-1 min-h-0 mt-0 overflow-hidden data-[state=inactive]:hidden">
            <ScrollArea className="flex-1 min-h-0">
              <div className="p-3 space-y-2">
                {toolEvents.length === 0 && (
                  <p className="text-xs text-center text-muted-foreground py-8">No tool calls yet.</p>
                )}
                {toolEvents.map((ev, i) => <EventCard key={`${ev.event}-${i}`} ev={ev} />)}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="checks" className="flex w-full flex-col flex-1 min-h-0 mt-0 overflow-hidden data-[state=inactive]:hidden">
            <ScrollArea className="flex-1 min-h-0">
              <div className="p-3 space-y-2">
                {checkEvents.length === 0 && (
                  <p className="text-xs text-center text-muted-foreground py-8">No check events yet.</p>
                )}
                {checkEvents.map((ev, i) => <EventCard key={`${ev.event}-${i}`} ev={ev} />)}
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      </div>

      {/* ══ RIGHT: D3 GRAPH ═══════════════════════════════════════════════════════ */}
      <div className="flex flex-col flex-1 min-w-0">

        {/* Graph toolbar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-border shrink-0 bg-card/50">
          <div className="flex items-center gap-2">
            <Network className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium text-sm">Execution Graph</span>
            <Badge variant="outline" className="text-xs tabular-nums">{graphNodes.length} nodes</Badge>
            <Badge variant="outline" className="text-xs tabular-nums">{events.length} events</Badge>
            {currentPhase !== "Idle" && <Badge variant="outline" className="text-xs">{currentPhase}</Badge>}
            {running && <Badge className="text-xs tabular-nums animate-pulse bg-blue-500/20 text-blue-400 border-blue-500/30">{nodeCount} / {maxNodesTotal}</Badge>}
          </div>
          <div className="flex items-center gap-3">
            {!workPanelOpen && (
              <Button variant="outline" size="sm" className="h-7 gap-1 text-[10px]" onClick={() => setWorkPanelOpen(true)}>
                <FileText className="h-3 w-3" /> Workspace
              </Button>
            )}
            {/* Graph mode toggle */}
            <div className="flex items-center gap-1 border border-border rounded-md overflow-hidden">
              {(["simplified", "full"] as const).map(m => (
                <button key={m} onClick={() => setGraphMode(m)}
                  className={`px-2 py-0.5 text-[10px] font-medium transition-colors ${graphMode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"}`}>
                  {m}
                </button>
              ))}
            </div>
            <div className="hidden lg:flex items-center gap-3">
              {([["#00e5ff","Active"],["#69ff47","Base"],["#f59e0b","Recursive"],["#e040fb","Jury"],["#ffeb3b","Consortium"]] as [string,string][]).map(([c,l]) => (
                <div key={l} className="flex items-center gap-1">
                  <div className="h-2 w-2 rounded-full" style={{ background: c }} />
                  <span className="text-[10px] text-muted-foreground">{l}</span>
                </div>
              ))}
            </div>
            <Separator orientation="vertical" className="h-5 hidden lg:block" />
            <div className="flex items-center gap-1 border border-border rounded-md overflow-hidden">
              <button
                className="px-2 py-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                onClick={() => setZoomCommand({ action: "out", nonce: Date.now() })}
                title="Zoom out"
              >
                <ZoomOut className="h-3.5 w-3.5" />
              </button>
              <button
                className="px-2 py-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                onClick={() => setZoomCommand({ action: "reset", nonce: Date.now() })}
                title="Reset zoom"
              >
                <RotateCcw className="h-3.5 w-3.5" />
              </button>
              <button
                className="px-2 py-1 text-muted-foreground hover:bg-muted hover:text-foreground"
                onClick={() => setZoomCommand({ action: "in", nonce: Date.now() })}
                title="Zoom in"
              >
                <ZoomIn className="h-3.5 w-3.5" />
              </button>
            </div>
            {(events.length > 0 || graphNodes.length > 0 || runResult) && (
              <>
                <Button variant="ghost" size="sm" className="h-7 gap-1 text-[10px]" onClick={exportJSON}>
                  <Download className="h-3 w-3" /> JSON
                </Button>
                <Button variant="ghost" size="sm" className="h-7 gap-1 text-[10px]" onClick={exportPDF}>
                  <Download className="h-3 w-3" /> PDF
                </Button>
              </>
            )}
            {selectedNode && (
              <Button variant="ghost" size="sm" className="text-[10px] h-7 px-2" onClick={() => setSelectedNode(null)}>
                Clear
              </Button>
            )}
          </div>
        </div>

        {/* D3 graph */}
        <div ref={graphRef} className="flex-1 relative select-none">
          <ExecutionGraph
            nodes={graphNodes} links={graphLinks}
            mode={graphMode} physics={physics}
            zoomCommand={zoomCommand}
            width={gSize.w} height={gSize.h}
            onNodeClick={n => { setSelectedNode(n); setCenterTab("output") }}
            onBackgroundClick={() => setSelectedNode(null)}
          />
          {graphNodes.length === 0 && !running && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="text-center">
                <Network className="h-16 w-16 text-muted-foreground/10 mx-auto mb-4" />
                <p className="text-muted-foreground/40 text-sm">Graph will appear here as RAF runs</p>
              </div>
            </div>
          )}

          {/* Node Inspector — top-right frosted overlay */}
          <AnimatePresence>
            {selectedNode && (
              <motion.div
                initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }}
                className="absolute top-4 right-4 w-[360px] bg-card/95 backdrop-blur shadow-xl border border-border rounded-lg overflow-hidden flex flex-col z-10"
              >
                <div className="px-3 py-2 border-b border-border flex justify-between items-center shrink-0">
                  <div className="flex items-center gap-2">
                    <span className="h-2 w-2 rounded-full" style={{
                      background: ({
                        'raf-node': '#00e5ff', jury: '#e040fb', consortium: '#ffeb3b', agent: '#69ff47',
                        'consortium-group': '#ffd600', 'jury-group': '#ce93d8',
                        'agent-proposal': '#69ff47', 'juror-vote': '#f3e5f5',
                        'merge-group': '#ff9100', 'referee-check': '#64b5f6',
                      } as Record<string,string>)[selectedNode.type] || '#888'
                    }} />
                    <span className="font-medium text-xs truncate">{selectedNode.label}</span>
                    {selectedNode.task && <Badge variant="outline" className="text-[9px] h-4 px-1">{selectedNode.task}</Badge>}
                  </div>
                  <button onClick={() => setSelectedNode(null)} className="text-muted-foreground hover:text-foreground text-sm leading-none px-1">✕</button>
                </div>
                <div className="p-3 text-xs overflow-y-auto max-h-[70vh] flex flex-col gap-3">

                  {/* ── RAF node: full lifecycle detail ─────────────────── */}
                  {selectedNode.type === "raf-node" && (
                    <>
                      <div className="grid grid-cols-2 gap-2">
                        <div><span className="text-[10px] uppercase text-muted-foreground">Depth</span>
                          <p className="mt-0.5">{selectedNode.depth ?? "—"}</p></div>
                        {selectedNode.caseType && (
                          <div><span className="text-[10px] uppercase text-muted-foreground">Case</span>
                            <p className="mt-0.5 capitalize">{selectedNode.caseType}</p></div>
                        )}
                        {selectedNode.confidence !== undefined && (
                          <div><span className="text-[10px] uppercase text-muted-foreground">Confidence</span>
                            <p className="font-mono mt-0.5">{(selectedNode.confidence * 100).toFixed(0)}%</p></div>
                        )}
                        {selectedNode.phase && (
                          <div><span className="text-[10px] uppercase text-muted-foreground">Phase</span>
                            <p className="mt-0.5">{selectedNode.phase}</p></div>
                        )}
                        {selectedDurationMs !== undefined && (
                          <div><span className="text-[10px] uppercase text-muted-foreground">Duration</span>
                            <p className="font-mono mt-0.5">{selectedDurationMs}ms</p></div>
                        )}
                        {selectedNode.success !== undefined && (
                          <div><span className="text-[10px] uppercase text-muted-foreground">Status</span>
                            <p className={`mt-0.5 ${selectedNode.success ? 'text-green-400' : 'text-red-400'}`}>
                              {selectedNode.success ? 'Success' : 'Failed'}</p></div>
                        )}
                        <div><span className="text-[10px] uppercase text-muted-foreground">Events</span>
                          <p className="font-mono mt-0.5">{selectedNodeEvents.length}</p></div>
                        <div><span className="text-[10px] uppercase text-muted-foreground">Children</span>
                          <p className="font-mono mt-0.5">{selectedNodeChildren.length}</p></div>
                      </div>

                      {/* ── Lifecycle checklist ──────────────────────────── */}
                      {(() => {
                        const evSet = new Set(selectedNodeEvents.map(e => e.event))
                        const childCount = selectedNodeChildren.filter(n => n.type === "raf-node").length
                        const childDone  = selectedNodeEvents.filter(e => e.event === "node_done").length - (evSet.has("node_done") ? 1 : 0)
                        const planChildCount = (planChildrenRef.current[selectedNode.id] || []).length

                        type CheckState = "done" | "partial" | "waiting" | "pending"
                        const step = (label: string, state: CheckState, detail?: string) => (
                          <div key={label} className="flex items-center gap-2">
                            <span className={`shrink-0 text-[11px] ${state === "done" ? "text-green-400" : state === "partial" ? "text-yellow-400" : state === "waiting" ? "text-blue-400 animate-pulse" : "text-muted-foreground/30"}`}>
                              {state === "done" ? "✓" : state === "partial" ? "◑" : state === "waiting" ? "⏳" : "○"}
                            </span>
                            <span className={`text-[10px] ${state === "done" ? "text-foreground" : state === "waiting" ? "text-blue-300" : "text-muted-foreground"}`}>{label}</span>
                            {detail && <span className="ml-auto text-[10px] font-mono text-muted-foreground/60">{detail}</span>}
                          </div>
                        )

                        const isActive = selectedNode.active
                        const isDone   = evSet.has("node_done")
                        const hasMode  = evSet.has("mode_decided")
                        const hasPlan  = evSet.has("plan_selected") || evSet.has("plan_ready")
                        const hasChildren = childCount > 0
                        const hasMerge = evSet.has("merge_done")
                        const hasSpec  = evSet.has("spec_validation_final") || evSet.has("spec_repair_start")
                        const hasAnalysis = evSet.has("analysis_done")
                        const hasExec  = evSet.has("base_execute_done")
                        const hasFail  = evSet.has("plan_validation_failed")

                        const childState: CheckState = !hasChildren ? "pending" : (isDone || hasMerge) ? "done" : planChildCount > 0 && childDone < planChildCount ? "partial" : "done"

                        return (
                          <div className="rounded-md border border-border/50 bg-muted/20 p-2 space-y-1">
                            <p className="text-[10px] uppercase text-muted-foreground font-medium mb-1.5">Lifecycle</p>
                            {step("Node created",    "done")}
                            {step("Mode decided",    hasMode ? "done" : isActive ? "waiting" : "pending")}
                            {selectedNode.caseType === "recursive" || hasPlan ? step("Plan selected", hasFail ? "partial" : hasPlan ? "done" : isActive ? "waiting" : "pending", hasFail ? "retry" : undefined) : null}
                            {(hasChildren || hasPlan) && step("Children running", childState, childState === "partial" ? `${childDone}/${planChildCount}` : undefined)}
                            {(hasChildren || hasMerge) && step("Merge",           hasMerge ? "done" : hasChildren && !isDone ? "waiting" : "pending")}
                            {step("Execute / output", hasExec ? "done" : !hasChildren && isActive ? "waiting" : hasExec || isDone ? "done" : "pending")}
                            {step("Spec validation",  hasSpec ? "done" : isDone ? "done" : isActive ? "waiting" : "pending")}
                            {step("Analysis",         hasAnalysis ? "done" : isDone ? "done" : isActive && (hasMerge || hasExec) ? "waiting" : "pending")}
                            {step("Node done",        isDone ? "done" : isActive ? "waiting" : "pending")}
                          </div>
                        )
                      })()}
                      {selectedNode.goal && (
                        <div className="group">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] uppercase text-muted-foreground">Goal</span>
                            <button
                              className="opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground hover:text-foreground transition-opacity"
                              onClick={() => setExpandModal({ title: "Node Goal", content: selectedNode.goal! })}
                            >⤢</button>
                          </div>
                          <p className="text-muted-foreground leading-relaxed mt-0.5">{selectedNode.goal}</p>
                        </div>
                      )}
                      {selectedNode.output && (
                        <div className="group">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] uppercase text-muted-foreground">Output</span>
                            <button
                              className="opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground hover:text-foreground transition-opacity"
                              onClick={() => setExpandModal({ title: "Node Output", content: selectedNode.output! })}
                            >⤢</button>
                          </div>
                          <div className="bg-muted/50 p-2 rounded mt-1 whitespace-pre-wrap text-[10px] font-mono border border-border/50 text-muted-foreground overflow-y-auto">
                            {selectedNode.output}</div>
                        </div>
                      )}
                      {(selectedNodeProposals.length > 0 || selectedNodeVotes.length > 0) && (
                        <div className="grid grid-cols-3 gap-2">
                          <div className="rounded border border-border/60 p-2">
                            <span className="text-[10px] uppercase text-muted-foreground">Proposals</span>
                            <p className="font-mono mt-0.5">{selectedNodeProposals.length}</p></div>
                          <div className="rounded border border-border/60 p-2">
                            <span className="text-[10px] uppercase text-muted-foreground">Vote rounds</span>
                            <p className="font-mono mt-0.5">{selectedNodeVotes.length}</p></div>
                          <div className="rounded border border-border/60 p-2">
                            <span className="text-[10px] uppercase text-muted-foreground">Links</span>
                            <p className="font-mono mt-0.5">{selectedNodeChildren.length}</p></div>
                        </div>
                      )}
                      {selectedNodeEvents.length > 0 && (
                        <div><span className="text-[10px] uppercase text-muted-foreground">Event history</span>
                          <div className="mt-1 space-y-1 overflow-y-auto">
                            {selectedNodeEvents.map((ev, i) => (
                              <div key={`${ev.event}-${ev.timestamp}-${i}`} className="flex items-center gap-2 rounded border border-border/50 px-2 py-1">
                                <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: EVENT_COLORS[ev.event || ""] || "#64748b" }} />
                                <span className="truncate">{eventLabel(ev)}</span>
                                <span className="ml-auto font-mono text-[10px] text-muted-foreground">{relTs(ev.timestamp, runStartRef.current)}</span>
                              </div>
                            ))}</div></div>
                      )}
                    </>
                  )}

                  {/* ── Consortium-group: list all proposals ────────────── */}
                  {selectedNode.type === "consortium-group" && (
                    <>
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-muted-foreground text-[10px]">Task: <span className="text-foreground font-mono">{selectedNode.task}</span></p>
                        {(inspectorCandidatesEvent as any)?.tier !== undefined && tierBadge((inspectorCandidatesEvent as any).tier)}
                      </div>
                      <p className="text-[10px] uppercase text-muted-foreground">{inspectorCandidates.length} proposals</p>
                      <div className="space-y-2">
                        {inspectorCandidates.map((cand: any, i: number) => {
                          const payload = cand?.payload || cand || {}
                          const fullText = payload.output || payload.mode || payload.plan || JSON.stringify(payload, null, 2)
                          const preview = fullText.length > 300 ? fullText.slice(0, 300) + "…" : fullText
                          return (
                            <div key={i} className="group rounded-md border border-border/60 p-2 space-y-1">
                              <div className="flex items-center gap-2">
                                <span className="text-[10px] font-mono text-muted-foreground">Agent {i + 1}</span>
                                <button
                                  className="ml-auto opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground hover:text-foreground transition-opacity"
                                  onClick={() => setExpandModal({ title: `Agent ${i + 1} Proposal`, content: fullText })}
                                >⤢</button>
                              </div>
                              <p className="text-[10px] text-muted-foreground whitespace-pre-wrap">{preview}</p>
                            </div>
                          )
                        })}
                        {inspectorCandidates.length === 0 && <p className="text-[10px] text-muted-foreground/50">No candidate data yet.</p>}
                      </div>
                    </>
                  )}

                  {/* ── Jury-group: winner + all votes ──────────────────── */}
                  {selectedNode.type === "jury-group" && (
                    <>
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="text-muted-foreground text-[10px]">Task: <span className="text-foreground font-mono">{selectedNode.task}</span></p>
                        {(inspectorCandidatesEvent as any)?.tier !== undefined && tierBadge((inspectorCandidatesEvent as any).tier)}
                      </div>
                      {inspectorWinnerId && (
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] uppercase text-muted-foreground">Winner</span>
                          <Badge className="text-[9px] bg-primary/20 text-primary border-primary/30">{optionLabel(inspectorWinnerId)}</Badge>
                          {(inspectorJuryEvent as any)?.confidence !== undefined && (
                            <span className="text-[10px] font-mono text-muted-foreground ml-auto">{((inspectorJuryEvent as any).confidence * 100).toFixed(0)}%</span>
                          )}
                        </div>
                      )}
                      <div className="space-y-1">
                        {inspectorVotes.map((v: any, i: number) => {
                          const vote = v.vote || v
                          const agentIdx = v.agent_id ?? i
                          const modelLabel = agentModelMap[`${inspectorOwner}:${inspectorTask}:jury:${agentIdx}`] || `agent-${agentIdx}`
                          return (
                            <div key={i} className="flex items-center gap-2 rounded border border-border/50 px-2 py-1 text-[10px]">
                              <span className="font-mono text-purple-300 shrink-0 max-w-[100px] truncate" title={modelLabel}>{modelLabel}</span>
                              <span className="text-muted-foreground">→</span>
                              <span className="font-mono">{optionLabel(vote.winner_id)}</span>
                              {vote.confidence && <span className="ml-auto font-mono text-muted-foreground">{(vote.confidence * 100).toFixed(0)}%</span>}
                            </div>
                          )
                        })}
                        {inspectorVotes.length === 0 && <p className="text-[10px] text-muted-foreground/50">No vote data yet.</p>}
                      </div>
                    </>
                  )}

                  {/* ── Agent proposal: full payload ─────────────────────── */}
                  {selectedNode.type === "agent-proposal" && (
                    <>
                      <p className="text-muted-foreground text-[10px]">
                        Proposer: <span className="font-mono text-amber-300">
                          {agentModelMap[`${inspectorOwner}:${inspectorTask}:consortium:${selectedNode.candidateIndex}`] || `agent-${selectedNode.candidateIndex ?? "?"}`}
                        </span>
                      </p>
                      {selectedNode.success && <Badge className="text-[9px] bg-primary/20 text-primary border-primary/30 w-fit">winner</Badge>}
                      {(() => {
                        const cand = inspectorCandidates[selectedNode.candidateIndex ?? -1]
                        const payload = cand?.payload || cand || {}
                        const fullText = payload.output || payload.mode || payload.plan || JSON.stringify(payload, null, 2)
                        const preview = fullText.length > 500 ? fullText.slice(0, 500) + "…" : fullText
                        return (
                          <div className="group relative">
                            <div className="bg-muted/50 p-2 rounded text-[10px] font-mono border border-border/50 text-muted-foreground whitespace-pre-wrap overflow-y-auto">
                              {preview || "No payload data."}
                            </div>
                            {fullText.length > 500 && (
                              <button
                                className="mt-1 text-[10px] text-primary hover:underline"
                                onClick={() => setExpandModal({ title: "Agent Proposal", content: fullText })}
                              >Show full output ⤢</button>
                            )}
                          </div>
                        )
                      })()}
                    </>
                  )}

                  {/* ── Juror vote: voted-for + ranked options ───────────── */}
                  {selectedNode.type === "juror-vote" && (
                    <>
                      <p className="text-muted-foreground text-[10px]">
                        Juror: <span className="font-mono text-purple-300">
                          {agentModelMap[`${inspectorOwner}:${inspectorTask}:jury:${selectedNode.candidateIndex}`] || `agent-${selectedNode.candidateIndex ?? "?"}`}
                        </span>
                      </p>
                      {(() => {
                        const v = inspectorVotes[selectedNode.candidateIndex ?? -1]
                        if (!v) return <p className="text-[10px] text-muted-foreground/50">No vote data.</p>
                        const vote = v.vote || v
                        return (
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] uppercase text-muted-foreground">Voted for</span>
                              <span className="font-mono text-[10px]">{optionLabel(vote.winner_id)}</span>
                              {vote.confidence && <span className="ml-auto text-[10px] font-mono text-muted-foreground">{(vote.confidence * 100).toFixed(0)}%</span>}
                            </div>
                            {(vote.ranked || []).length > 0 && (
                              <div><p className="text-[10px] uppercase text-muted-foreground mb-1">Rankings</p>
                                {(vote.ranked as any[]).map((r: any, ri: number) => (
                                  <div key={ri} className="flex items-center gap-2 text-[10px] py-0.5">
                                    <span className="font-mono text-muted-foreground w-4">{ri + 1}.</span>
                                    <span className="font-mono">{optionLabel(r.option_id)}</span>
                                    <span className="text-muted-foreground ml-auto">{r.score}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )
                      })()}
                    </>
                  )}

                  {/* ── Merge-group: merge summary ───────────────────────── */}
                  {selectedNode.type === "merge-group" && (
                    <>
                      <p className="text-muted-foreground text-[10px]">Merge result for <span className="font-mono text-foreground">{selectedNode.ownerNodeId}</span></p>
                      {(() => {
                        const mergeEv = events.find(ev => ev.event === "merge_done" && ev.node_id === selectedNode.ownerNodeId)
                        if (!mergeEv) return <p className="text-[10px] text-muted-foreground/50">Merge event not found.</p>
                        return (
                          <div className="space-y-2">
                            {(mergeEv as any).output && (
                              <div className="group">
                                <div className="flex items-center gap-2">
                                  <span className="text-[10px] uppercase text-muted-foreground">Output</span>
                                  <button
                                    className="opacity-0 group-hover:opacity-100 text-[10px] text-muted-foreground hover:text-foreground transition-opacity"
                                    onClick={() => setExpandModal({ title: "Merge Output", content: String((mergeEv as any).output) })}
                                  >⤢</button>
                                </div>
                                <div className="bg-muted/50 p-2 rounded mt-1 text-[10px] font-mono border border-border/50 text-muted-foreground overflow-y-auto whitespace-pre-wrap">
                                  {String((mergeEv as any).output)}
                                </div>
                              </div>
                            )}
                            {(mergeEv as any).confidence !== undefined && (
                              <div><span className="text-[10px] uppercase text-muted-foreground">Confidence</span>
                                <p className="font-mono mt-0.5">{((mergeEv as any).confidence * 100).toFixed(0)}%</p></div>
                            )}
                          </div>
                        )
                      })()}
                    </>
                  )}

                  {/* ── Referee check / plan validation failure ──────────── */}
                  {selectedNode.type === "referee-check" && (
                    <>
                      <p className="text-muted-foreground text-[10px]">Check on <span className="font-mono text-foreground">{selectedNode.ownerNodeId}</span></p>
                      {selectedNode.hint && (
                        <div className="rounded-md border border-red-500/30 bg-red-500/10 p-2 text-[10px] text-red-300">{selectedNode.hint}</div>
                      )}
                      {(() => {
                        const failEv = events.find(ev =>
                          ev.event === "plan_validation_failed" && ev.node_id === selectedNode.ownerNodeId &&
                          ev.plan_attempt === (selectedNode.candidateIndex ?? 0)
                        )
                        if (!failEv) return <p className="text-[10px] text-muted-foreground/50">No validation failure details found.</p>
                        return (
                          <div className="space-y-1 text-[10px]">
                            {failEv.reason && <div><span className="text-muted-foreground uppercase">Reason</span><p className="mt-0.5">{failEv.reason}</p></div>}
                            {failEv.retry !== undefined && <div><span className="text-muted-foreground uppercase">Attempt</span><p className="font-mono mt-0.5">{failEv.retry} / {failEv.max_retries ?? "?"}</p></div>}
                          </div>
                        )
                      })()}
                      {/* Show plan recovery events for this parent node */}
                      {(() => {
                        const recEvs = events.filter(ev =>
                          ["plan_retry_start","plan_retry_done","plan_abandoned","plan_replaced"].includes(ev.event || "") &&
                          ev.node_id === selectedNode.ownerNodeId
                        )
                        if (recEvs.length === 0) return null
                        return (
                          <div><span className="text-[10px] uppercase text-muted-foreground">Recovery timeline</span>
                            <div className="mt-1 space-y-1 max-h-28 overflow-y-auto">
                              {recEvs.map((ev, i) => (
                                <div key={i} className="flex items-center gap-2 rounded border border-border/50 px-2 py-1 text-[10px]">
                                  <span className="h-1.5 w-1.5 rounded-full shrink-0" style={{ background: EVENT_COLORS[ev.event || ""] || "#64748b" }} />
                                  <span className="truncate">{eventLabel(ev)}</span>
                                  {ev.retry !== undefined && <span className="ml-auto font-mono text-muted-foreground">#{ev.retry}</span>}
                                </div>
                              ))}
                            </div>
                          </div>
                        )
                      })()}
                    </>
                  )}

                  {/* ── Fallback for unknown satellite types ─────────────── */}
                  {!["raf-node","consortium-group","jury-group","agent-proposal","juror-vote","merge-group","referee-check"].includes(selectedNode.type) && (
                    <div className="grid grid-cols-2 gap-2">
                      <div><span className="text-[10px] uppercase text-muted-foreground">Type</span>
                        <p className="capitalize mt-0.5">{selectedNode.type.replace(/-/g,' ')}</p></div>
                      <div><span className="text-[10px] uppercase text-muted-foreground">Depth</span>
                        <p className="mt-0.5">{selectedNode.depth ?? "—"}</p></div>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Physics Tuner — bottom-right collapsible overlay */}
          <PhysicsPanel physics={physics} onChange={setPhysics} />
        </div>
      </div>

      {/* ══ EXPAND MODAL ══════════════════════════════════════════════════════════ */}
      {expandModal && (
        <ExpandModal
          title={expandModal.title}
          content={expandModal.content}
          onClose={() => setExpandModal(null)}
        />
      )}
    </div>
  )
}

// ── helpers ────────────────────────────────────────────────────────────────────

function ConfigSection({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="min-w-0 space-y-1.5">
      <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">{label}</p>
      {children}
    </div>
  )
}

function ParamGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="w-full min-w-0 rounded-md px-0.5 py-1 space-y-1.5">
      <span className="block px-0.5 text-[10px] font-semibold uppercase tracking-widest text-primary">{label}</span>
      {children}
    </div>
  )
}

function providerLabel(provider: string, availableProviders: string[]): string {
  return `${provider}${availableProviders.includes(provider) ? "" : " (key missing)"}`
}

function modelInfoList(provider: string, models: Record<string, string[]>, modelCatalog: Record<string, ModelInfo[]>): ModelInfo[] {
  const catalog = modelCatalog[provider]
  if (catalog?.length) return catalog
  return (models[provider] || []).map(id => ({ id, label: id.split("/").pop(), family: provider, tags: ["general"] }))
}

function ModelChooser({ title, provider, model, juryModel, providers, availableProviders, models, modelCatalog, disabled, open, onOpenChange, onProviderChange, onModelChange, onJuryModelChange }: {
  title: string
  provider: string
  model: string
  juryModel: string
  providers: string[]
  availableProviders: string[]
  models: Record<string, string[]>
  modelCatalog: Record<string, ModelInfo[]>
  disabled: boolean
  open: boolean
  onOpenChange: (open: boolean) => void
  onProviderChange: (provider: string) => void
  onModelChange: (model: string) => void
  onJuryModelChange: (model: string) => void
}) {
  const [query, setQuery] = useState("")
  const providerModels = modelInfoList(provider, models, modelCatalog)
  const filteredModels = providerModels.filter(item => {
    const haystack = `${item.id} ${item.label || ""} ${item.family || ""} ${(item.tags || []).join(" ")}`.toLowerCase()
    return haystack.includes(query.toLowerCase())
  })

  return (
    <div className="rounded-md border border-border/60 overflow-hidden">
      <button
        type="button"
        className="w-full px-2.5 py-2 flex items-center justify-between text-left hover:bg-accent/40"
        onClick={() => onOpenChange(!open)}
      >
        <div className="min-w-0 flex-1 pr-2">
          <p className="text-xs font-medium">{title}</p>
          <p className="text-[10px] text-muted-foreground break-words">
            Provider: {provider} | Model: {model || "default"}
          </p>
        </div>
        <span className="shrink-0 text-[10px] uppercase tracking-widest text-primary">{open ? "hide" : "models"}</span>
      </button>

      {open && (
        <div className="border-t border-border/60 p-2 space-y-3">
          <div className="rounded-md border border-border/50 bg-accent/20 px-2 py-2 text-[10px] leading-4 text-muted-foreground">
            Public use currently supports <span className="font-medium text-foreground">mock</span> and{" "}
            <span className="font-medium text-foreground">openrouter</span> as providers. To use real models, choose
            <span className="font-medium text-foreground"> openrouter</span>, paste your OpenRouter API key above, and
            then pick any supported model ID from the list below.
          </div>
          <div className="grid grid-cols-1 gap-2">
            <ConfigSection label="Provider">
              <Select value={provider} onChange={e => onProviderChange(e.target.value)} disabled={disabled}>
                {providers.map(p => <option key={p} value={p}>{providerLabel(p, availableProviders)}</option>)}
              </Select>
            </ConfigSection>
            <ConfigSection label="Jury model">
              <Input value={juryModel} onChange={e => onJuryModelChange(e.target.value)} disabled={disabled} placeholder="same as consortium" />
            </ConfigSection>
          </div>

          <ConfigSection label="Model">
            <Input value={model} onChange={e => onModelChange(e.target.value)} disabled={disabled} placeholder="default" />
          </ConfigSection>

          <div className="space-y-2">
            <Input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search models, families, tags" disabled={disabled} />
            <div className="max-h-64 overflow-y-auto overflow-x-hidden space-y-1 pr-1">
              {filteredModels.length === 0 && (
                <p className="text-[10px] text-muted-foreground px-1 py-2">No matching models for this provider.</p>
              )}
              {filteredModels.map(item => (
                <button
                  key={item.id}
                  type="button"
                  disabled={disabled}
                  onClick={() => onModelChange(item.id)}
                  className={`w-full min-w-0 rounded-md border px-2 py-1.5 text-left transition-colors ${model === item.id ? "border-primary/60 bg-primary/10" : "border-border/50 hover:bg-accent/40"}`}
                >
                  <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
                    <span className="min-w-0 break-words text-xs font-medium">{item.label || item.id}</span>
                    <span className="rounded border border-border/40 px-1.5 py-0.5 text-[10px] text-muted-foreground">{item.family || provider}</span>
                  </div>
                  <div className="mt-1 flex min-w-0 flex-wrap items-center gap-1">
                    <span className="min-w-0 max-w-full break-all font-mono text-[10px] text-muted-foreground">{item.id}</span>
                    {(item.tags || []).slice(0, 3).map(tag => (
                      <Badge key={tag} variant="outline" className="shrink-0 px-1 py-0 text-[9px] leading-4 text-muted-foreground">{tag}</Badge>
                    ))}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function SlotEditor({ title, slots, size, minSize, maxSize, providers, models, modelCatalog, availableProviders, disabled, onSizeChange, onChange }: {
  title: string
  slots: AgentSlot[]
  size: number
  minSize: number
  maxSize: number
  providers: string[]
  models: Record<string, string[]>
  modelCatalog: Record<string, ModelInfo[]>
  availableProviders: string[]
  disabled: boolean
  onSizeChange: (size: number) => void
  onChange: (index: number, patch: Partial<AgentSlot>) => void
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium">{title}</p>
        <div className="flex items-center overflow-hidden rounded-md border border-border/60">
          <button
            type="button"
            disabled={disabled || size <= minSize}
            onClick={() => onSizeChange(Math.max(minSize, size - 1))}
            className="h-7 w-7 text-xs text-muted-foreground hover:bg-accent hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
            title={`Remove ${title.toLowerCase()} slot`}
          >
            -
          </button>
          <span className="min-w-7 border-x border-border/60 px-2 text-center font-mono text-[10px] leading-7">{size}</span>
          <button
            type="button"
            disabled={disabled || size >= maxSize}
            onClick={() => onSizeChange(Math.min(maxSize, size + 1))}
            className="h-7 w-7 text-xs text-muted-foreground hover:bg-accent hover:text-foreground disabled:pointer-events-none disabled:opacity-40"
            title={`Add ${title.toLowerCase()} slot`}
          >
            +
          </button>
        </div>
      </div>
      <div className="space-y-2">
        {slots.map((slot, index) => {
          const slotModels = modelInfoList(slot.provider, models, modelCatalog)
          const modelIds = slotModels.map(m => m.id)
          const selectedModel = slot.model || slotModels[0]?.id || ""
          const hasSelectedModel = selectedModel === "" || modelIds.includes(selectedModel)
          return (
            <div key={`${title}-${index}`} className="grid grid-cols-[22px_1fr] gap-2 items-start">
              <span className="text-[10px] font-mono text-muted-foreground pt-2">#{index + 1}</span>
              <div className="grid min-w-0 grid-cols-1 gap-2">
                <Select
                  value={slot.provider}
                  onChange={e => {
                    const nextProvider = e.target.value
                    const nextModel = modelInfoList(nextProvider, models, modelCatalog)[0]?.id || ""
                    onChange(index, { provider: nextProvider, model: nextModel })
                  }}
                  disabled={disabled}
                >
                  {providers.map(p => <option key={p} value={p}>{providerLabel(p, availableProviders)}</option>)}
                </Select>
                <Select value={selectedModel} onChange={e => onChange(index, { model: e.target.value })} disabled={disabled}>
                  {!hasSelectedModel && <option value={selectedModel}>{selectedModel}</option>}
                  {slotModels.map(m => (
                    <option key={m.id} value={m.id}>{m.label ? `${m.label} - ${m.id}` : m.id}</option>
                  ))}
                </Select>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function SpecList({ label, items }: { label: string; items: string[] }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-widest text-muted-foreground mb-1">{label}</p>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground/60">None</p>
      ) : (
        <div className="space-y-1">
          {items.map((item, i) => (
            <p key={i} className="min-w-0 break-words rounded border border-border/50 px-2 py-1 text-xs text-muted-foreground">{item}</p>
          ))}
        </div>
      )}
    </div>
  )
}

function EventCard({ ev }: { ev: RafEvent }) {
  const hidden = new Set(["event", "status", "timestamp"])
  const entries = Object.entries(ev).filter(([key, value]) => !hidden.has(key) && value !== undefined && value !== null && value !== "")
  const causeInfo = ev.cause ? CAUSE_LABELS[ev.cause] : null
  return (
    <Card className="min-w-0 overflow-hidden">
      <CardContent className="p-3 space-y-2">
        <div className="flex min-w-0 items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full" style={{ background: EVENT_COLORS[ev.event || ""] || "#64748b" }} />
          <p className="min-w-0 flex-1 truncate text-xs font-medium">{eventLabel(ev)}</p>
          {ev.node_id && <span className="min-w-0 break-all text-[10px] font-mono text-muted-foreground">{ev.node_id}</span>}
        </div>
        {causeInfo && (
          <div className="flex items-start gap-2 rounded-md border border-red-900/40 bg-red-950/30 px-2 py-1.5">
            <span className="rounded px-1 py-0.5 font-mono text-[9px] font-bold shrink-0"
              style={{ background: ev.cause === "api_error" ? "#7f1d1d" : ev.cause === "parse_error" ? "#78350f" : "#1e1b4b", color: "#fca5a5" }}>
              {causeInfo.label}
            </span>
            <span className="text-[10px] text-red-300/80">{causeInfo.detail}</span>
          </div>
        )}
        <div className="space-y-1">
          {entries.slice(0, 8).map(([key, value]) => (
            <div key={key} className="grid grid-cols-[88px_1fr] gap-2 text-[10px]">
              <span className="uppercase text-muted-foreground">{key}</span>
              <span className="min-w-0 break-words font-mono text-muted-foreground">
                {typeof value === "string" ? value : JSON.stringify(value).slice(0, 300)}
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function PS({ label, value, min, max, step = 1, disabled, onChange }: {
  label: string; value: number; min: number; max: number; step?: number
  disabled: boolean; onChange: (v: number) => void
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono tabular-nums">{value}</span>
      </div>
      <Slider min={min} max={max} step={step} value={[value]} onValueChange={([v]) => onChange(v)} disabled={disabled} />
    </div>
  )
}
