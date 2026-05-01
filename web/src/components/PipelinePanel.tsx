// PipelinePanel.tsx
// Floating draggable panel for Goal Chaining (Feature 2).
// Each pipeline step runs as an independent RAF run; steps execute sequentially
// so the output of step N can be injected into step N+1's goal via {{output}}.
// The pipeline runs in parallel with (never replaces) the active main RAF run.

import type { PointerEvent } from "react"
import { Eye, Play, Plus, Square, Trash2, Link2 } from "lucide-react"
import { ScrollArea } from "./ui/scroll-area"

// ── Exported types ─────────────────────────────────────────────────────────────

export type PipelineStep = {
  id: string
  goal: string
}

export type PipelineStepResult = {
  stepId: string
  runId: string
  runToken: string
  sessionId: string
  // status of this individual step's execution
  status: "pending" | "running" | "done" | "error" | "cancelled"
  output?: string
  // resolved goal — {{output}} already substituted before the run started
  goal: string
}

// ── Component ──────────────────────────────────────────────────────────────────

type Props = {
  steps: PipelineStep[]
  results: PipelineStepResult[]
  running: boolean
  currentStepIdx: number   // -1 when idle
  panelPos: { left: number; top: number }
  onStepsChange: (steps: PipelineStep[]) => void
  onRun: () => void
  onCancel: () => void
  onViewStep: (result: PipelineStepResult) => void
  onClose: () => void
  // Pointer-capture drag handlers — attach to the drag-handle header
  onPointerDown: (e: PointerEvent<HTMLDivElement>) => void
  onPointerMove: (e: PointerEvent<HTMLDivElement>) => void
  onPointerUp: (e: PointerEvent<HTMLDivElement>) => void
  // Cancel fires when pointer capture is forcibly released (e.g. OS gesture interrupt)
  onPointerCancel: (e: PointerEvent<HTMLDivElement>) => void
}

export function PipelinePanel({
  steps, results, running, currentStepIdx, panelPos,
  onStepsChange, onRun, onCancel, onViewStep, onClose,
  onPointerDown, onPointerMove, onPointerUp, onPointerCancel,
}: Props) {
  // ── step helpers ────────────────────────────────────────────────────────────
  const addStep = () =>
    onStepsChange([...steps, { id: `step-${Date.now()}`, goal: "" }])

  const removeStep = (id: string) =>
    onStepsChange(steps.filter(s => s.id !== id))

  const updateGoal = (id: string, goal: string) =>
    onStepsChange(steps.map(s => s.id === id ? { ...s, goal } : s))

  const canRun = !running && steps.some(s => s.goal.trim())

  // Small inline status indicator shown beside the step number
  const StatusDot = ({ idx }: { idx: number }) => {
    const r = results[idx]
    if (!r) return null
    if (r.status === "running") return <span className="text-blue-400 animate-pulse text-[10px]">●</span>
    if (r.status === "done")    return <span className="text-green-400 text-[10px]">✓</span>
    if (r.status === "error")   return <span className="text-red-400 text-[10px]">✕</span>
    if (r.status === "cancelled") return <span className="text-yellow-400 text-[10px]">—</span>
    return null
  }

  // ── render ──────────────────────────────────────────────────────────────────
  return (
    // The outer div captures pointer moves/ups so dragging stays smooth even
    // when the cursor leaves the header during fast movement.
    <div
      className="fixed z-30 w-[380px] bg-card border border-border rounded-lg shadow-xl flex flex-col overflow-hidden"
      style={{ left: panelPos.left, top: panelPos.top, maxHeight: "80vh" }}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerCancel}
    >
      {/* ── Drag-handle header ─────────────────────────────────────────────── */}
      <div
        className="flex items-center justify-between px-3 py-2 border-b border-border bg-card/80 cursor-move select-none shrink-0"
        onPointerDown={onPointerDown}
      >
        <div className="flex items-center gap-2">
          <Link2 className="h-3.5 w-3.5 text-primary" />
          <span className="text-xs font-semibold">Goal Pipeline</span>
          {running && (
            <span className="text-[10px] text-blue-400 animate-pulse">
              step {currentStepIdx + 1} / {steps.length}
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          className="text-muted-foreground hover:text-foreground text-sm leading-none px-1"
        >
          ✕
        </button>
      </div>

      {/* ── Steps list ─────────────────────────────────────────────────────── */}
      <ScrollArea className="flex-1 min-h-0">
        <div className="p-3 space-y-2">

          {/* Usage hint */}
          <div className="rounded border border-border/50 bg-muted/20 px-2 py-1.5 text-[10px] text-muted-foreground leading-relaxed">
            Steps run one after another. Use{" "}
            <code className="font-mono text-primary px-0.5">{"{{output}}"}</code>
            {" "}in any step goal to inject the previous step's output.
            Runs in parallel with the active RAF run — it never replaces it.
          </div>

          {steps.map((step, idx) => {
            const result  = results[idx]
            const isActive = currentStepIdx === idx && running
            const borderCls =
              isActive               ? "border-blue-500/50 bg-blue-500/5"
              : result?.status === "done"      ? "border-green-500/30 bg-green-500/5"
              : result?.status === "error"     ? "border-red-500/30 bg-red-500/5"
              : result?.status === "cancelled" ? "border-yellow-500/30 bg-yellow-500/5"
              : "border-border/60 bg-muted/10"

            return (
              <div
                key={step.id}
                className={`rounded-md border p-2 space-y-1.5 transition-colors ${borderCls}`}
              >
                {/* Step header row */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-mono text-muted-foreground w-4">{idx + 1}.</span>
                    <StatusDot idx={idx} />
                    {isActive && (
                      <span className="text-[10px] text-blue-400">Running…</span>
                    )}
                    {result?.status === "done" && result.runId && (
                      // "View" loads this step's graph/events into the main viewport
                      <button
                        className="text-[10px] text-green-400 hover:text-green-300 flex items-center gap-0.5 transition-colors"
                        onClick={() => onViewStep(result)}
                      >
                        <Eye className="h-2.5 w-2.5" /> View run
                      </button>
                    )}
                    {result?.status === "error" && (
                      <span className="text-[10px] text-red-400">Failed</span>
                    )}
                  </div>
                  {/* Remove button — hidden while pipeline is running */}
                  {!running && (
                    <button
                      onClick={() => removeStep(step.id)}
                      className="text-muted-foreground hover:text-red-400 transition-colors"
                      title="Remove step"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  )}
                </div>

                {/* Goal textarea */}
                <textarea
                  value={step.goal}
                  onChange={e => updateGoal(step.id, e.target.value)}
                  disabled={running}
                  rows={2}
                  placeholder={
                    idx === 0
                      ? "Step 1 goal…"
                      : `Step ${idx + 1} goal — use {{output}} to reference step ${idx} result`
                  }
                  className="w-full rounded border border-border/50 bg-background px-2 py-1 text-[11px] font-mono resize-none focus:outline-none focus:ring-1 focus:ring-primary/50 disabled:opacity-50"
                />

                {/* Output preview — shown when step completes */}
                {result?.status === "done" && result.output && (
                  <div className="rounded bg-green-500/10 border border-green-500/20 px-2 py-1 text-[10px] text-green-300 font-mono">
                    {result.output.slice(0, 120)}{result.output.length > 120 ? "…" : ""}
                  </div>
                )}
              </div>
            )
          })}

          {/* Add step — hidden while running */}
          {!running && (
            <button
              onClick={addStep}
              className="w-full rounded-md border border-dashed border-border/50 py-1.5 text-[10px] text-muted-foreground hover:text-foreground hover:border-primary/40 transition-colors flex items-center justify-center gap-1"
            >
              <Plus className="h-3 w-3" /> Add step
            </button>
          )}
        </div>
      </ScrollArea>

      {/* ── Footer ─────────────────────────────────────────────────────────── */}
      <div className="px-3 py-2 border-t border-border flex items-center justify-between shrink-0 bg-card/60">
        <span className="text-[10px] text-muted-foreground">
          {steps.length} step{steps.length !== 1 ? "s" : ""}
          {results.filter(r => r.status === "done").length > 0 && (
            <> · {results.filter(r => r.status === "done").length} done</>
          )}
        </span>

        {running ? (
          <button
            onClick={onCancel}
            className="flex items-center gap-1 rounded-md border border-red-500/40 bg-red-500/10 px-3 py-1 text-[11px] font-medium text-red-400 hover:bg-red-500/20 transition-colors"
          >
            <Square className="h-3 w-3" /> Cancel
          </button>
        ) : (
          <button
            onClick={onRun}
            disabled={!canRun}
            className="flex items-center gap-1 rounded-md border border-primary/40 bg-primary/10 px-3 py-1 text-[11px] font-medium text-primary hover:bg-primary/20 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            <Play className="h-3 w-3" /> Run Pipeline
          </button>
        )}
      </div>
    </div>
  )
}
