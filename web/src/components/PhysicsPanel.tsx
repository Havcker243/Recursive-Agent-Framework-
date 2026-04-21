import { useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import { Slider } from './ui/slider'
import { ChevronDown, ChevronRight, Info, Settings2 } from 'lucide-react'
import { type PhysicsParams, DEFAULT_PHYSICS } from './ExecutionGraph'

interface Props {
  physics: PhysicsParams
  onChange: (p: PhysicsParams) => void
}

export function PhysicsPanel({ physics, onChange }: Props) {
  const [open, setOpen] = useState(false)
  const [showInfo, setShowInfo] = useState(false)
  const [pos, setPos] = useState({ left: Math.max(16, window.innerWidth - 272), top: Math.max(16, window.innerHeight - 72) })
  const dragRef = useRef<{ x: number; y: number; left: number; top: number; moved: boolean } | null>(null)
  const suppressClickRef = useRef(false)

  const update = (key: keyof PhysicsParams, val: number) => {
    onChange({ ...physics, [key]: val })
  }

  const reset = () => onChange(DEFAULT_PHYSICS)

  const startDrag = (e: PointerEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest("input,button,[role='slider']")) return
    dragRef.current = { x: e.clientX, y: e.clientY, left: pos.left, top: pos.top, moved: false }
    e.currentTarget.setPointerCapture(e.pointerId)
  }

  const moveDrag = (e: PointerEvent<HTMLDivElement>) => {
    if (!dragRef.current) return
    const dx = e.clientX - dragRef.current.x
    const dy = e.clientY - dragRef.current.y
    if (Math.abs(dx) + Math.abs(dy) > 3) dragRef.current.moved = true
    const panelWidth = 256
    const panelHeight = open ? Math.min(window.innerHeight * 0.72, 560) : 44
    setPos({
      left: Math.min(Math.max(8, window.innerWidth - panelWidth - 8), Math.max(8, dragRef.current.left + dx)),
      top: Math.min(Math.max(8, window.innerHeight - panelHeight - 8), Math.max(8, dragRef.current.top + dy)),
    })
  }

  const endDrag = () => {
    suppressClickRef.current = Boolean(dragRef.current?.moved)
    dragRef.current = null
  }

  const Control = ({ label, prop, min, max, step }: {
    label: string
    prop: keyof PhysicsParams
    min: number
    max: number
    step: number
  }) => (
    <div className="flex flex-col gap-1 mb-3">
      <div className="flex justify-between items-center">
        <label className="text-xs text-muted-foreground font-medium">{label}</label>
        <input
          type="number"
          value={physics[prop]}
          onChange={e => update(prop, parseFloat(e.target.value) || 0)}
          className="w-16 h-6 text-xs text-right px-1 py-0 bg-background border border-border rounded"
          step={step}
        />
      </div>
      <Slider
        min={min}
        max={max}
        step={step}
        value={[physics[prop]]}
        onValueChange={v => update(prop, v[0])}
        className="mt-1"
      />
    </div>
  )

  return (
    <div
      className="fixed z-[80] w-64 bg-card/80 backdrop-blur-md border border-border rounded-md shadow-lg"
      style={{ left: pos.left, top: pos.top }}
    >
      <div
        className="flex items-center justify-between p-2 cursor-grab active:cursor-grabbing hover:bg-muted/50 rounded transition-colors"
        onPointerDown={startDrag}
        onPointerMove={moveDrag}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onClick={() => {
          if (suppressClickRef.current) {
            suppressClickRef.current = false
            return
          }
          setOpen(!open)
        }}
      >
        <div className="flex items-center gap-2 w-full text-sm font-semibold">
          <Settings2 className="w-4 h-4 text-primary" />
          <span>Physics Tuner</span>
          {open
            ? <ChevronDown className="w-4 h-4 ml-auto" />
            : <ChevronRight className="w-4 h-4 ml-auto" />
          }
        </div>
      </div>

      {open && (
        <div className="p-3 border-t border-border max-h-[60vh] overflow-y-auto">
          <button
            type="button"
            onClick={() => setShowInfo(v => !v)}
            className="mb-3 flex w-full items-center justify-between rounded-md border border-border/70 bg-background/35 px-2 py-1.5 text-left text-xs text-muted-foreground hover:bg-muted/60 hover:text-foreground"
          >
            <span className="flex items-center gap-1.5">
              <Info className="h-3.5 w-3.5 text-primary" />
              How the physics controls work
            </span>
            {showInfo ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          </button>

          {showInfo && (
            <div className="mb-3 space-y-2 rounded-md border border-primary/25 bg-primary/5 p-2 text-[10px] leading-relaxed text-muted-foreground">
              <p><span className="font-semibold text-foreground">If the graph shrinks:</span> raise Link Distance, make Charge more negative, or raise Outward Expansion.</p>
              <p><span className="font-semibold text-foreground">Link Distance</span> spreads connected nodes. Safe range: 140-220.</p>
              <p><span className="font-semibold text-foreground">Charge</span> is repulsion. More negative pushes nodes apart. Safe range: -900 to -1600.</p>
              <p><span className="font-semibold text-foreground">Outward Expansion</span> pushes the graph away from the center. Safe range: 60-130.</p>
              <p><span className="font-semibold text-foreground">Collide Padding</span> prevents nodes from overlapping. Safe range: 20-45.</p>
              <p><span className="font-semibold text-foreground">Alpha / Velocity Decay</span> controls how fast movement settles. Higher values calm the graph faster.</p>
            </div>
          )}

          <Control label="Link Distance" prop="linkDistance" min={10} max={300} step={5} />
          <Control label="Link Strength" prop="linkStrength" min={0} max={2} step={0.05} />
          <Control label="Charge (Repulsion)" prop="chargeStrength" min={-3000} max={0} step={50} />
          <Control label="Charge Max Dist" prop="chargeDistanceMax" min={100} max={3000} step={100} />
          <Control label="Outward Expansion" prop="outwardStrength" min={0} max={300} step={5} />
          <Control label="Elastic Base Dist" prop="progressiveLinkBase" min={50} max={500} step={10} />
          <Control label="Elastic Scale" prop="progressiveLinkScale" min={0} max={0.2} step={0.005} />
          <Control label="Collide Padding" prop="collideRadiusOffset" min={0} max={100} step={5} />
          <Control label="Collide Strength" prop="collideStrength" min={0} max={2} step={0.1} />
          <Control label="Alpha Decay" prop="alphaDecay" min={0.001} max={0.1} step={0.001} />
          <Control label="Velocity Decay" prop="velocityDecay" min={0.1} max={0.99} step={0.01} />

          <button
            onClick={reset}
            className="mt-2 w-full text-xs py-1.5 bg-muted hover:bg-muted/80 border border-border rounded transition-colors"
          >
            Reset to Defaults
          </button>
        </div>
      )}
    </div>
  )
}
