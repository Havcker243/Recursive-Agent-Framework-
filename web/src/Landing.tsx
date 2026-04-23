import { motion } from "framer-motion"
import { useState, type ReactNode } from "react"
import {
  ArrowRight,
  CheckCircle2,
  ExternalLink,
  GitBranch,
  KeyRound,
  Layers,
  Network,
  Play,
  ShieldCheck,
  Sparkles,
  Vote,
} from "lucide-react"
import { Button } from "./components/ui/button"

function FadeIn({
  delay = 0,
  children,
  className,
}: {
  delay?: number
  children: ReactNode
  className?: string
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

function InView({
  delay = 0,
  children,
  className,
}: {
  delay?: number
  children: ReactNode
  className?: string
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ delay, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  )
}

function GraphPreview() {
  const nodes = [
    { id: "goal", x: 250, y: 44, label: "Goal", color: "#2dd4bf", r: 24 },
    { id: "plan", x: 128, y: 134, label: "Plan", color: "#facc15", r: 18 },
    { id: "vote", x: 372, y: 134, label: "Vote", color: "#fb7185", r: 18 },
    { id: "a", x: 70, y: 232, label: "A", color: "#34d399", r: 15 },
    { id: "b", x: 188, y: 232, label: "B", color: "#34d399", r: 15 },
    { id: "c", x: 312, y: 232, label: "C", color: "#38bdf8", r: 15 },
    { id: "d", x: 430, y: 232, label: "D", color: "#38bdf8", r: 15 },
  ]
  const edges = [
    ["goal", "plan"],
    ["goal", "vote"],
    ["plan", "a"],
    ["plan", "b"],
    ["vote", "c"],
    ["vote", "d"],
  ]
  const pos = Object.fromEntries(nodes.map((node) => [node.id, node]))

  return (
    <svg viewBox="0 0 500 285" className="h-full w-full" role="img" aria-label="Recursive task tree">
      {edges.map(([source, target], index) => (
        <motion.line
          key={`${source}-${target}`}
          x1={pos[source].x}
          y1={pos[source].y}
          x2={pos[target].x}
          y2={pos[target].y}
          stroke="#3f3f46"
          strokeWidth={1.5}
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: 1, opacity: 1 }}
          transition={{ delay: 0.25 + index * 0.06, duration: 0.35 }}
        />
      ))}
      {nodes.map((node, index) => (
        <motion.g
          key={node.id}
          initial={{ scale: 0.7, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ delay: 0.08 + index * 0.05, type: "spring", stiffness: 260, damping: 24 }}
          style={{ transformOrigin: `${node.x}px ${node.y}px` }}
        >
          <circle cx={node.x} cy={node.y} r={node.r} fill="#18181b" stroke={node.color} strokeWidth={2} />
          <circle cx={node.x} cy={node.y} r={node.r - 5} fill={node.color} fillOpacity={0.12} />
          <text
            x={node.x}
            y={node.y + 1}
            textAnchor="middle"
            dominantBaseline="middle"
            fill={node.color}
            fontSize={node.r > 20 ? 10 : 9}
            fontFamily="IBM Plex Mono, monospace"
            fontWeight="600"
          >
            {node.label}
          </text>
        </motion.g>
      ))}
    </svg>
  )
}

const FLOW = [
  {
    icon: Sparkles,
    title: "Start with a plain goal",
    body: "Write the task in normal language. RAF turns that goal into a runnable specification before work begins.",
  },
  {
    icon: GitBranch,
    title: "Split only when needed",
    body: "A node either solves the task directly or breaks it into smaller child nodes with dependency order.",
  },
  {
    icon: Vote,
    title: "Use proposals and votes",
    body: "Several agents propose. A separate jury chooses. The same pattern is used for planning, execution, and review.",
  },
  {
    icon: CheckCircle2,
    title: "Return a traceable answer",
    body: "The final answer comes with a run history, node outputs, votes, and recovery events for inspection.",
  },
]

const USE_CASES = [
  "Research tasks that need several passes over sources",
  "Planning work where one answer depends on earlier sub-results",
  "Code, writing, or analysis tasks that benefit from independent review",
  "Teaching demos for recursive agents, voting, and long-horizon execution",
  "Benchmarks for model routing, decomposition depth, and reliability",
  "Local experiments with mock mode before spending API credits",
]

const RESEARCH_POINTS = [
  "Recursive language models treat large context as an environment to inspect and decompose instead of forcing every token into one prompt.",
  "Massively decomposed agentic processes reduce long-horizon failure by making each step smaller and adding error correction at the step level.",
  "RAF combines both ideas: small context windows, recursive execution, structured outputs, and multi-agent voting.",
]

const WINDOWS_STEPS = [
  {
    title: "Install basics",
    body: "Install Python 3.11+ and Node.js 20+. Restart PowerShell after installing them.",
    command: "python --version\nnode --version\nnpm --version",
  },
  {
    title: "Install backend packages",
    body: "Run this from the project root.",
    command: "python -m venv .venv\n.\\.venv\\Scripts\\python -m pip install -r requirements.txt",
  },
  {
    title: "Start the backend",
    body: "Keep this PowerShell window open. The API should listen on port 8001.",
    command: ".\\.venv\\Scripts\\python -m uvicorn server.main:app --reload --host 127.0.0.1 --port 8001",
  },
  {
    title: "Start the web app",
    body: "Open a second PowerShell window from the project root.",
    command: "cd web\nnpm install\nnpm run dev",
  },
]

const MAC_STEPS = [
  {
    title: "Install basics",
    body: "Install Python 3.11+ and Node.js 20+. Homebrew is the simplest path for many users.",
    command: "python3 --version\nnode --version\nnpm --version",
  },
  {
    title: "Install backend packages",
    body: "Run this from the project root.",
    command: "python3 -m venv .venv\n. .venv/bin/activate\npython -m pip install -r requirements.txt",
  },
  {
    title: "Start the backend",
    body: "Keep this Terminal window open. The API should listen on port 8001.",
    command: "python -m uvicorn server.main:app --reload --host 127.0.0.1 --port 8001",
  },
  {
    title: "Start the web app",
    body: "Open a second Terminal window from the project root.",
    command: "cd web\nnpm install\nnpm run dev",
  },
]

function SetupSteps({
  steps,
  label,
}: {
  steps: Array<{ title: string; body: string; command: string }>
  label: string
}) {
  return (
    <div className="space-y-3">
      {steps.map((step, index) => (
        <details key={step.title} className="group rounded-md border border-zinc-800 bg-zinc-900 p-4" open={index === 0}>
          <summary className="flex cursor-pointer list-none items-start gap-3">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-teal-300 font-mono text-xs font-bold text-zinc-950">
              {index + 1}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block font-semibold text-white">{step.title}</span>
              <span className="mt-1 block text-sm leading-6 text-zinc-400">{step.body}</span>
            </span>
            <span className="rounded-md border border-zinc-700 px-2 py-1 font-mono text-[10px] text-zinc-400">
              {label}
            </span>
          </summary>
          <pre className="mt-4 overflow-x-auto rounded-md border border-zinc-800 bg-zinc-950 p-3 text-left font-mono text-xs leading-6 text-teal-100">
            <code>{step.command}</code>
          </pre>
        </details>
      ))}
    </div>
  )
}

const INTERACTIVE_TASKS = [
  {
    title: "Research brief",
    prompt: "Compare three papers and return the strongest implementation takeaways.",
    nodes: ["Extract claims", "Compare evidence", "Draft summary", "Review answer"],
    result: "Best for dense reading and synthesis.",
  },
  {
    title: "Planning task",
    prompt: "Plan a 3-day beginner fitness routine with meals and recovery.",
    nodes: ["Define goals", "Build schedule", "Check constraints", "Return plan"],
    result: "Best for work with dependencies.",
  },
  {
    title: "Engineering task",
    prompt: "Design and document a REST API for a task management system.",
    nodes: ["Entity model", "Endpoint plan", "Validation rules", "Final spec"],
    result: "Best for technical decomposition.",
  },
]

function InteractiveRunDemo({ onEnter }: { onEnter: () => void }) {
  const [selected, setSelected] = useState(0)
  const [activeNode, setActiveNode] = useState(0)
  const task = INTERACTIVE_TASKS[selected]

  return (
    <div className="rounded-md border border-zinc-800 bg-zinc-950">
      <div className="border-b border-zinc-800 p-4">
        <p className="text-sm font-semibold text-white">Try a run shape</p>
        <p className="mt-1 text-sm leading-6 text-zinc-400">
          Pick a task and step through the kind of execution tree RAF creates.
        </p>
      </div>

      <div className="grid gap-0 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="border-b border-zinc-800 p-4 lg:border-b-0 lg:border-r">
          <div className="space-y-2">
            {INTERACTIVE_TASKS.map((item, index) => (
              <button
                key={item.title}
                type="button"
                onClick={() => {
                  setSelected(index)
                  setActiveNode(0)
                }}
                className={`w-full rounded-md border px-3 py-3 text-left transition-colors ${
                  selected === index
                    ? "border-teal-400/50 bg-teal-400/10"
                    : "border-zinc-800 bg-zinc-900 hover:border-zinc-700"
                }`}
              >
                <span className="block text-sm font-semibold text-white">{item.title}</span>
                <span className="mt-1 block text-xs leading-5 text-zinc-400">{item.prompt}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="p-4">
          <div className="rounded-md border border-zinc-800 bg-zinc-900 p-4">
            <p className="font-mono text-xs uppercase tracking-wide text-zinc-500">Goal</p>
            <p className="mt-2 text-sm leading-6 text-zinc-200">{task.prompt}</p>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {task.nodes.map((node, index) => (
              <button
                key={node}
                type="button"
                onClick={() => setActiveNode(index)}
                className={`min-h-24 rounded-md border p-3 text-left transition-colors ${
                  activeNode === index
                    ? "border-amber-300/60 bg-amber-300/10"
                    : "border-zinc-800 bg-zinc-900 hover:border-zinc-700"
                }`}
              >
                <span className="font-mono text-xs text-zinc-500">0{index + 1}</span>
                <span className="mt-2 block text-sm font-semibold text-white">{node}</span>
                <span className="mt-2 block text-xs leading-5 text-zinc-400">
                  {index === activeNode ? "Active node" : index < activeNode ? "Dependency ready" : "Waiting"}
                </span>
              </button>
            ))}
          </div>

          <div className="mt-4 flex flex-col gap-3 rounded-md border border-zinc-800 bg-zinc-900 p-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm leading-6 text-zinc-300">{task.result}</p>
            <Button onClick={onEnter} className="h-10 gap-2">
              Run this style <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function Landing({ onEnter }: { onEnter: () => void }) {
  return (
    <div className="fixed inset-0 overflow-y-auto bg-zinc-950 text-zinc-100">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[100] focus:rounded-md focus:bg-teal-300 focus:px-3 focus:py-2 focus:text-sm focus:font-semibold focus:text-zinc-950"
      >
        Skip to content
      </a>

      <nav className="sticky top-0 z-50 border-b border-zinc-800 bg-zinc-950/92 px-4 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-teal-400/40 bg-teal-400/10">
              <span className="font-mono text-xs font-bold text-teal-300">R</span>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold tracking-normal">RAF</p>
              <p className="hidden text-xs text-zinc-400 sm:block">Recursive Agent Framework</p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <a
              href="#setup"
              className="hidden rounded-md px-3 py-2 text-xs text-zinc-300 hover:bg-zinc-900 hover:text-white sm:inline-flex"
            >
              Setup
            </a>
            <a
              href="https://openrouter.ai/keys"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden items-center gap-1 rounded-md px-3 py-2 text-xs text-zinc-300 hover:bg-zinc-900 hover:text-white md:inline-flex"
            >
              API key <ExternalLink className="h-3 w-3" />
            </a>
            <Button size="sm" onClick={onEnter} className="gap-2">
              Open app <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </nav>

      <main id="main">
        <section className="border-b border-zinc-800 bg-zinc-950">
          <div className="mx-auto grid max-w-6xl gap-10 px-4 py-16 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:py-20">
            <div>
              <FadeIn>
                <p className="mb-5 inline-flex rounded-md border border-teal-400/30 bg-teal-400/10 px-3 py-1 text-xs font-medium text-teal-200">
                  A simple way to run recursive agents
                </p>
              </FadeIn>

              <FadeIn delay={0.08}>
                <h1 className="max-w-3xl text-4xl font-semibold leading-tight tracking-normal text-white sm:text-5xl">
                  Break big tasks into small agents that plan, vote, and finish.
                </h1>
              </FadeIn>

              <FadeIn delay={0.16}>
                <p className="mt-6 max-w-2xl text-base leading-8 text-zinc-300">
                  RAF turns one goal into a tree of focused work. Each node decides whether to solve directly or
                  split again. Proposals, votes, dependency handling, and final review happen in one visible run.
                </p>
              </FadeIn>

              <FadeIn delay={0.24}>
                <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                  <Button onClick={onEnter} className="h-11 gap-2 px-5">
                    <Play className="h-4 w-4" />
                    Try mock mode
                  </Button>
                  <Button variant="outline" onClick={onEnter} className="h-11 gap-2 px-5">
                    Run with a model <ArrowRight className="h-4 w-4" />
                  </Button>
                </div>
              </FadeIn>

              <FadeIn delay={0.32}>
                <div className="mt-8 grid max-w-2xl grid-cols-1 gap-3 text-sm text-zinc-300 sm:grid-cols-3">
                  <div className="rounded-md border border-zinc-800 bg-zinc-900/60 p-3">
                    <p className="font-mono text-lg text-teal-300">Mock</p>
                    <p className="mt-1 text-xs leading-5 text-zinc-400">Try the flow without an API key.</p>
                  </div>
                  <div className="rounded-md border border-zinc-800 bg-zinc-900/60 p-3">
                    <p className="font-mono text-lg text-amber-300">Votes</p>
                    <p className="mt-1 text-xs leading-5 text-zinc-400">Compare model proposals before acting.</p>
                  </div>
                  <div className="rounded-md border border-zinc-800 bg-zinc-900/60 p-3">
                    <p className="font-mono text-lg text-rose-300">Trace</p>
                    <p className="mt-1 text-xs leading-5 text-zinc-400">Review every node after the run.</p>
                  </div>
                </div>
              </FadeIn>
            </div>

            <FadeIn delay={0.2} className="min-w-0">
              <div className="overflow-hidden rounded-md border border-zinc-800 bg-zinc-900">
                <div className="flex items-center justify-between border-b border-zinc-800 px-3 py-2">
                  <span className="font-mono text-xs text-zinc-400">recursive run preview</span>
                  <span className="rounded bg-teal-400/10 px-2 py-1 font-mono text-[10px] text-teal-200">live trace</span>
                </div>
                <div className="h-72 p-4">
                  <GraphPreview />
                </div>
              </div>
            </FadeIn>
          </div>
        </section>

        <section className="border-b border-zinc-800 bg-zinc-900" aria-labelledby="product-heading">
          <div className="mx-auto grid max-w-6xl gap-8 px-4 py-16 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
            <InView>
              <div>
                <p className="text-sm font-semibold text-teal-300">The working app</p>
                <h2 id="product-heading" className="mt-3 text-3xl font-semibold tracking-normal text-white">
                  Watch a task turn into a live execution graph.
                </h2>
                <p className="mt-5 text-base leading-8 text-zinc-300">
                  The interface keeps the main answer, run history, model calls, votes, graph layout, and exports in one
                  place. New users can stay in simple mode. Advanced users can open the trace and tune model strategy.
                </p>
                <div className="mt-6 flex flex-wrap gap-2">
                  {["Live graph", "Timeline", "Votes", "Exports"].map((tag) => (
                    <span key={tag} className="rounded-md border border-zinc-700 px-3 py-1 text-xs text-zinc-300">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </InView>

            <InView delay={0.1}>
              <div className="overflow-hidden rounded-md border border-zinc-800 bg-zinc-950">
                <img
                  src="/image.png"
                  alt="RAF app showing the execution graph, timeline, sessions, model status, and export controls"
                  className="w-full bg-zinc-950"
                  loading="lazy"
                />
              </div>
            </InView>
          </div>
        </section>

        <section className="border-b border-zinc-800 bg-zinc-900" aria-labelledby="why-heading">
          <div className="mx-auto grid max-w-6xl gap-8 px-4 py-14 lg:grid-cols-[0.85fr_1.15fr] lg:items-start">
            <InView>
              <div>
                <p className="text-sm font-semibold text-amber-300">Why RAF exists</p>
                <h2 id="why-heading" className="mt-3 text-3xl font-semibold tracking-normal text-white">
                  Long tasks fail when one model has to hold everything.
                </h2>
              </div>
            </InView>
            <InView delay={0.1}>
              <div className="space-y-5 text-base leading-8 text-zinc-300">
                <p>
                  A single-agent run can lose context, skip checks, or compound a small mistake across many steps.
                  RAF makes the task tree explicit. The system can split the goal, run independent workers, wait for
                  dependencies, and evaluate the merged result.
                </p>
                <p>
                  The first experience stays simple: write a goal, press run, read the answer. The deeper controls are
                  available when you want to inspect models, votes, graph state, recovery events, or exports.
                </p>
              </div>
            </InView>
          </div>
        </section>

        <section className="border-b border-zinc-800 bg-zinc-950" aria-labelledby="flow-heading">
          <div className="mx-auto max-w-6xl px-4 py-16">
            <InView className="max-w-2xl">
              <p className="text-sm font-semibold text-teal-300">The run loop</p>
              <h2 id="flow-heading" className="mt-3 text-3xl font-semibold tracking-normal text-white">
                Four ideas, one workflow.
              </h2>
            </InView>

            <div className="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
              {FLOW.map((item, index) => (
                <InView key={item.title} delay={index * 0.06}>
                  <article className="h-full rounded-md border border-zinc-800 bg-zinc-900 p-5">
                    <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-md border border-teal-400/30 bg-teal-400/10">
                      <item.icon className="h-5 w-5 text-teal-200" />
                    </div>
                    <h3 className="text-base font-semibold text-white">{item.title}</h3>
                    <p className="mt-3 text-sm leading-7 text-zinc-400">{item.body}</p>
                  </article>
                </InView>
              ))}
            </div>
          </div>
        </section>

        <section className="border-b border-zinc-800 bg-zinc-900" aria-labelledby="interactive-heading">
          <div className="mx-auto max-w-6xl px-4 py-16">
            <InView className="max-w-2xl">
              <p className="text-sm font-semibold text-rose-300">Interactive preview</p>
              <h2 id="interactive-heading" className="mt-3 text-3xl font-semibold tracking-normal text-white">
                Click through the shape of a RAF run.
              </h2>
              <p className="mt-5 text-base leading-8 text-zinc-300">
                This preview is not a model call. It gives people a fast mental model before they open the full app.
              </p>
            </InView>
            <InView delay={0.1} className="mt-10">
              <InteractiveRunDemo onEnter={onEnter} />
            </InView>
          </div>
        </section>

        <section className="border-b border-zinc-800 bg-zinc-900" aria-labelledby="visual-heading">
          <div className="mx-auto grid max-w-6xl gap-8 px-4 py-16 lg:grid-cols-[1fr_1fr] lg:items-center">
            <InView>
              <div className="overflow-hidden rounded-md border border-zinc-800 bg-zinc-950">
                <img
                  src="/full-implementation.png"
                  alt="RAF implementation architecture with frontend, FastAPI server, recursive engine, adapters, and streaming trace"
                  className="w-full bg-zinc-950"
                  loading="lazy"
                />
              </div>
            </InView>
            <InView delay={0.1}>
              <div>
                <p className="text-sm font-semibold text-rose-300">What is inside</p>
                <h2 id="visual-heading" className="mt-3 text-3xl font-semibold tracking-normal text-white">
                  A full stack for observable agent work.
                </h2>
                <p className="mt-5 text-base leading-8 text-zinc-300">
                  The web app starts runs and listens over WebSocket. The server manages model routing, cancellation,
                  replay, and plan approval. RAF nodes handle recursive decomposition, child dependencies, votes, and
                  final analysis.
                </p>
                <ul className="mt-6 space-y-3 text-sm leading-6 text-zinc-300">
                  <li className="flex gap-3">
                    <Network className="mt-0.5 h-5 w-5 shrink-0 text-teal-300" />
                    Real-time event stream for graph and timeline views.
                  </li>
                  <li className="flex gap-3">
                    <Layers className="mt-0.5 h-5 w-5 shrink-0 text-amber-300" />
                    Tiered routing for leaf, planning, and root-level model choices.
                  </li>
                  <li className="flex gap-3">
                    <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-rose-300" />
                    Structured outputs and validation before decisions are accepted.
                  </li>
                </ul>
              </div>
            </InView>
          </div>
        </section>

        <section className="border-b border-zinc-800 bg-zinc-950" aria-labelledby="uses-heading">
          <div className="mx-auto max-w-6xl px-4 py-16">
            <InView className="max-w-2xl">
              <p className="text-sm font-semibold text-amber-300">Use it for</p>
              <h2 id="uses-heading" className="mt-3 text-3xl font-semibold tracking-normal text-white">
                Tasks that need more than a single answer.
              </h2>
            </InView>
            <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {USE_CASES.map((item, index) => (
                <InView key={item} delay={index * 0.04}>
                  <div className="flex h-full gap-3 rounded-md border border-zinc-800 bg-zinc-900 p-4">
                    <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-teal-300" />
                    <p className="text-sm leading-6 text-zinc-300">{item}</p>
                  </div>
                </InView>
              ))}
            </div>
          </div>
        </section>

        <section className="border-b border-zinc-800 bg-zinc-900" aria-labelledby="research-heading">
          <div className="mx-auto max-w-6xl px-4 py-16">
            <InView className="max-w-3xl">
              <p className="text-sm font-semibold text-teal-300">Research grounding</p>
              <h2 id="research-heading" className="mt-3 text-3xl font-semibold tracking-normal text-white">
                Built around decomposition and error correction.
              </h2>
            </InView>
            <div className="mt-10 grid gap-4 lg:grid-cols-3">
              {RESEARCH_POINTS.map((item, index) => (
                <InView key={item} delay={index * 0.06}>
                  <article className="h-full rounded-md border border-zinc-800 bg-zinc-950 p-5">
                    <p className="font-mono text-sm text-amber-300">0{index + 1}</p>
                    <p className="mt-4 text-sm leading-7 text-zinc-300">{item}</p>
                  </article>
                </InView>
              ))}
            </div>
          </div>
        </section>

        <section id="setup" className="border-b border-zinc-800 bg-zinc-950" aria-labelledby="setup-heading">
          <div className="mx-auto max-w-6xl px-4 py-16">
            <InView>
              <div className="max-w-3xl">
                <p className="text-sm font-semibold text-rose-300">Start simple</p>
                <h2 id="setup-heading" className="mt-3 text-3xl font-semibold tracking-normal text-white">
                  Everything needed to run RAF locally.
                </h2>
                <p className="mt-5 text-base leading-8 text-zinc-300">
                  Mock mode lets you test the app, graph, run history, and output flow without paying for model calls.
                  Add an OpenRouter key when you are ready to use real models.
                </p>
              </div>
            </InView>

            <InView delay={0.1}>
              <div className="mt-10 grid gap-4 lg:grid-cols-3">
                <article className="rounded-md border border-zinc-800 bg-zinc-900 p-5">
                  <p className="font-semibold text-white">Fastest test</p>
                  <p className="mt-3 text-sm leading-7 text-zinc-400">
                    Start the backend and frontend, open the app, choose mock mode, type a short goal, and press run.
                    If the graph moves and a final answer appears, the local stack is connected.
                  </p>
                </article>
                <article className="rounded-md border border-zinc-800 bg-zinc-900 p-5">
                  <p className="font-semibold text-white">Real model calls</p>
                  <p className="mt-3 text-sm leading-7 text-zinc-400">
                    Use OpenRouter when you want real LLM output. The key link asks visitors to sign in or create an
                    account, then opens the API key page for their own workspace.
                  </p>
                </article>
                <article className="rounded-md border border-zinc-800 bg-zinc-900 p-5">
                  <p className="font-semibold text-white">Ports to expect</p>
                  <p className="mt-3 text-sm leading-7 text-zinc-400">
                    Backend: <span className="font-mono text-teal-200">http://localhost:8001</span>. Frontend: usually{" "}
                    <span className="font-mono text-teal-200">http://localhost:5173</span>.
                  </p>
                </article>
              </div>
            </InView>

            <InView delay={0.15}>
              <div className="mt-8 grid gap-8 lg:grid-cols-2">
                <div>
                  <h3 className="mb-4 text-xl font-semibold text-white">Windows setup</h3>
                  <SetupSteps steps={WINDOWS_STEPS} label="PowerShell" />
                </div>
                <div>
                  <h3 className="mb-4 text-xl font-semibold text-white">Mac setup</h3>
                  <SetupSteps steps={MAC_STEPS} label="Terminal" />
                </div>
              </div>
            </InView>

            <InView delay={0.2}>
              <div className="mt-8 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
                <article className="rounded-md border border-zinc-800 bg-zinc-900 p-5">
                  <h3 className="text-xl font-semibold text-white">OpenRouter key guide</h3>
                  <ol className="mt-4 space-y-3 text-sm leading-7 text-zinc-300">
                    <li>1. Open the key page with the button below.</li>
                    <li>2. Sign in or create an OpenRouter account.</li>
                    <li>3. Create a new API key in your workspace.</li>
                    <li>4. Copy the key and paste it into RAF's OpenRouter API key field.</li>
                    <li>5. Select OpenRouter as the provider and run a small test first.</li>
                  </ol>
                  <a
                    href="https://openrouter.ai/keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-5 inline-flex h-10 items-center justify-center gap-2 rounded-md bg-teal-300 px-4 text-sm font-semibold text-zinc-950 hover:bg-teal-200"
                  >
                    Create OpenRouter API key <ExternalLink className="h-4 w-4" />
                  </a>
                  <p className="mt-3 text-xs leading-5 text-zinc-500">
                    If you are already signed in, OpenRouter may open your account directly. New users will be taken
                    through sign-in first.
                  </p>
                  <p className="mt-2 text-xs leading-5 text-zinc-500">
                    In the public app, real model calls currently go through OpenRouter. Mock mode is still available if
                    you want to test the interface without a key.
                  </p>
                </article>

                <article className="rounded-md border border-zinc-800 bg-zinc-900 p-5">
                  <h3 className="text-xl font-semibold text-white">Troubleshooting checklist</h3>
                  <div className="mt-4 grid gap-3 text-sm leading-6 text-zinc-300 sm:grid-cols-2">
                    {[
                      ["API off", "Make sure the backend command is still running on port 8001."],
                      ["Frontend blank", "Run npm install inside web, then npm run dev again."],
                      ["Mock fails", "Use provider mock and keep consortium/jury sizes small for the first test."],
                      ["Real model fails", "Check the API key, provider, model name, and OpenRouter account credits."],
                      ["Port conflict", "Close the old server or run Vite/backend on another port."],
                      ["Browser cache", "Hard refresh after a new build if the old UI stays visible."],
                    ].map(([title, body]) => (
                      <div key={title} className="rounded-md border border-zinc-800 bg-zinc-950 p-3">
                        <p className="font-semibold text-white">{title}</p>
                        <p className="mt-1 text-xs leading-5 text-zinc-400">{body}</p>
                      </div>
                    ))}
                  </div>
                </article>
              </div>
            </InView>
          </div>
        </section>

        <section className="bg-zinc-900" aria-labelledby="final-heading">
          <div className="mx-auto max-w-4xl px-4 py-16 text-center">
            <InView>
              <KeyRound className="mx-auto h-8 w-8 text-teal-300" />
              <h2 id="final-heading" className="mt-4 text-3xl font-semibold tracking-normal text-white">
                Run locally first. Scale when you are ready.
              </h2>
              <p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-zinc-300">
                RAF is easiest to understand by running it. Start with mock mode, then bring your model key and tune the
                agent strategy after the first trace makes sense.
              </p>
              <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
                <Button onClick={onEnter} className="h-11 gap-2 px-6">
                  Open RAF <ArrowRight className="h-4 w-4" />
                </Button>
                <a
                  href="https://openrouter.ai/keys"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex h-11 items-center justify-center gap-2 rounded-md border border-zinc-700 px-6 text-sm text-zinc-200 hover:bg-zinc-800"
                >
                  Get an OpenRouter key <ExternalLink className="h-4 w-4" />
                </a>
              </div>
            </InView>
          </div>
        </section>
      </main>

      <footer className="border-t border-zinc-800 bg-zinc-950 px-4 py-6">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 text-xs text-zinc-500 sm:flex-row sm:items-center sm:justify-between">
          <span>RAF, Recursive Agent Framework</span>
          <span>Local-first agent orchestration for recursive tasks</span>
        </div>
      </footer>
    </div>
  )
}
