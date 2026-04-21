import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

// ── Types ──────────────────────────────────────────────────────────────────────

export type NodeType =
  | 'raf-node'
  // legacy (kept for backwards compat with stored sessions)
  | 'consortium' | 'jury' | 'agent'
  // grouped satellite types (new)
  | 'consortium-group' | 'jury-group'
  | 'agent-proposal' | 'juror-vote'
  | 'merge-group' | 'referee-check'

export type GraphMode = 'simplified' | 'full'

export interface GraphNode {
  id: string
  type: NodeType
  label: string
  detail: string
  active: boolean
  success?: boolean
  depth?: number
  goal?: string
  output?: string
  confidence?: number
  mode?: string
  phase?: string
  hint?: string           // compact info shown below label on graph
  ownerNodeId?: string    // satellite nodes: the owning RAF node id
  task?: string           // satellite nodes: the decision task name
  candidateIndex?: number // agent-proposal / juror-vote: index in array
  caseType?: 'base' | 'recursive'
  error?: boolean
  abandoned?: boolean
  durationMs?: number
  x?: number; y?: number; fx?: number | null; fy?: number | null; vx?: number; vy?: number
}

export interface GraphEdge {
  id: string
  source: string | GraphNode
  target: string | GraphNode
  edgeType: 'flow' | 'parallel' | 'dependency' | 'merge'
}

export interface PhysicsParams {
  linkDistance: number
  linkStrength: number
  chargeStrength: number
  chargeDistanceMax: number
  outwardStrength: number
  progressiveLinkBase: number
  progressiveLinkScale: number
  collideRadiusOffset: number
  collideStrength: number
  alphaDecay: number
  velocityDecay: number
}

export const DEFAULT_PHYSICS: PhysicsParams = {
  linkDistance: 100,
  linkStrength: 0.8,
  chargeStrength: -1500,
  chargeDistanceMax: 1500,
  outwardStrength: 5,
  progressiveLinkBase: 150,
  progressiveLinkScale: 0.05,
  collideRadiusOffset: 40,
  collideStrength: 1,
  alphaDecay: 0.015,
  velocityDecay: 0.45,
}

// ── Node appearance ────────────────────────────────────────────────────────────

const NC: Record<string, string> = {
  'raf-node':         '#00e5ff',
  'consortium':       '#ffeb3b',
  'consortium-group': '#ffd600',
  'jury':             '#e040fb',
  'jury-group':       '#ce93d8',
  'agent':            '#69ff47',
  'agent-proposal':   '#69ff47',
  'juror-vote':       '#f3e5f5',
  'merge-group':      '#ff9100',
  'referee-check':    '#64b5f6',
}

const NR: Record<string, number> = {
  'raf-node':         22,
  'consortium':       16,
  'consortium-group': 19,
  'jury':             14,
  'jury-group':       16,
  'agent':            10,
  'agent-proposal':   10,
  'juror-vote':       9,
  'merge-group':      17,
  'referee-check':    12,
}

const EDGE_COLORS: Record<string, string> = {
  flow: '#444', parallel: '#00cccc', dependency: '#e040fb', merge: '#ff9100',
}

const INSIDE_TEXT: Record<string, string> = {
  'consortium-group': 'C', 'jury-group': 'J',
  'agent-proposal': 'A',  'juror-vote': 'V',
  'merge-group': 'M',      'referee-check': 'R',
  'consortium': 'C',       'jury': 'J', 'agent': 'A',
}

function nodeRadius(type: NodeType): number {
  return NR[type] ?? 12
}

// ── Custom forces ──────────────────────────────────────────────────────────────

function forceConstantOutward(cx: number, cy: number, strength: number) {
  let nodes: GraphNode[]
  function force(alpha: number) {
    for (let i = 0; i < nodes.length; i++) {
      const n = nodes[i]
      if (n.depth === 0) continue
      const dx = (n.x ?? 0) - cx
      const dy = (n.y ?? 0) - cy
      const dist = Math.sqrt(dx * dx + dy * dy) || 1
      n.vx = (n.vx ?? 0) + (dx / dist) * strength * alpha
      n.vy = (n.vy ?? 0) + (dy / dist) * strength * alpha
    }
  }
  force.initialize = (_nodes: GraphNode[]) => { nodes = _nodes }
  return force
}

function forceProgressiveLink(baseDistance: number, strengthScale: number) {
  let nodes: GraphNode[]
  let links: GraphEdge[] = []
  function force(alpha: number) {
    if (!nodes || !links.length) return
    for (let i = 0; i < links.length; i++) {
      const link = links[i]
      const source = typeof link.source === 'object' ? link.source : null
      const target = typeof link.target === 'object' ? link.target : null
      if (!source || !target) continue
      const dx = (target.x ?? 0) - (source.x ?? 0)
      const dy = (target.y ?? 0) - (source.y ?? 0)
      const dist = Math.sqrt(dx * dx + dy * dy) || 1
      const stretch = Math.max(0, dist - baseDistance)
      if (stretch > 0) {
        const pull = Math.min(stretch * stretch * strengthScale * alpha * 0.01, 50)
        const pullX = (dx / dist) * pull
        const pullY = (dy / dist) * pull
        target.vx = (target.vx ?? 0) - pullX
        target.vy = (target.vy ?? 0) - pullY
        source.vx = (source.vx ?? 0) + pullX
        source.vy = (source.vy ?? 0) + pullY
      }
    }
  }
  force.initialize = (_nodes: GraphNode[]) => { nodes = _nodes }
  force.links = (_links: GraphEdge[]) => { links = _links; return force }
  return force
}

// ── Component ──────────────────────────────────────────────────────────────────

interface Props {
  nodes: GraphNode[]
  links: GraphEdge[]
  mode: GraphMode
  physics: PhysicsParams
  width: number
  height: number
  onNodeClick?: (node: GraphNode) => void
  onBackgroundClick?: () => void
  zoomCommand?: { action: 'in' | 'out' | 'reset'; nonce: number }
}

export function ExecutionGraph({ nodes, links, mode, physics, width, height, onNodeClick, onBackgroundClick, zoomCommand }: Props) {
  const svgRef     = useRef<SVGSVGElement>(null)
  const simRef     = useRef<d3.Simulation<GraphNode, GraphEdge> | null>(null)
  const zlRef      = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null)
  const zoomRef    = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)
  const initRef    = useRef(false)
  const prevModeRef  = useRef(mode)
  const prevCountRef = useRef(0)

  // ── Init once ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!svgRef.current || initRef.current) return
    initRef.current = true

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    // SVG filters + arrow markers
    const defs = svg.append('defs')
    const f = defs.append('filter').attr('id', 'glow')
    f.append('feGaussianBlur').attr('stdDeviation', 3).attr('result', 'blur')
    const fm = f.append('feMerge')
    fm.append('feMergeNode').attr('in', 'blur')
    fm.append('feMergeNode').attr('in', 'SourceGraphic')

    ;(['flow', 'parallel', 'dependency', 'merge'] as const).forEach(t => {
      const c = EDGE_COLORS[t]
      defs.append('marker').attr('id', `arr-${t}`)
        .attr('viewBox', '0 -5 10 10').attr('refX', 26).attr('refY', 0)
        .attr('markerWidth', 5).attr('markerHeight', 5).attr('orient', 'auto')
        .append('path').attr('d', 'M0,-5L10,0L0,5').attr('fill', c)
    })

    const zl = svg.append('g')
    zlRef.current = zl

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.05, 6])
      .on('zoom', e => zl.attr('transform', e.transform.toString()))
    zoomRef.current = zoom
    svg.call(zoom)
    svg.on('click', event => {
      if (event.target === svgRef.current) onBackgroundClick?.()
    })

    // Layer order matters: edges behind nodes, labels on top
    zl.append('g').attr('class', 'edges')
    zl.append('g').attr('class', 'nodes')
    zl.append('g').attr('class', 'labels')
    zl.append('g').attr('class', 'hints')

    simRef.current = d3.forceSimulation<GraphNode>([])
      .force('link',            d3.forceLink<GraphNode, GraphEdge>([]).id(d => d.id).distance(physics.linkDistance).strength(physics.linkStrength))
      .force('charge',          d3.forceManyBody().strength(physics.chargeStrength).distanceMax(physics.chargeDistanceMax))
      .force('outward',         forceConstantOutward(width / 2, height / 2, physics.outwardStrength))
      .force('progressiveLink', forceProgressiveLink(physics.progressiveLinkBase, physics.progressiveLinkScale))
      .force('collide',         d3.forceCollide<GraphNode>().radius(d => nodeRadius(d.type) + physics.collideRadiusOffset).strength(physics.collideStrength))
      .alphaDecay(physics.alphaDecay)
      .velocityDecay(physics.velocityDecay)

    simRef.current.on('tick', () => {
      if (!zlRef.current) return
      const g = zlRef.current
      g.select('.edges').selectAll<SVGLineElement, GraphEdge>('line')
        .attr('x1', d => (d.source as GraphNode).x ?? 0)
        .attr('y1', d => (d.source as GraphNode).y ?? 0)
        .attr('x2', d => (d.target as GraphNode).x ?? 0)
        .attr('y2', d => (d.target as GraphNode).y ?? 0)
      g.select('.nodes').selectAll<SVGGElement, GraphNode>('g.ngrp')
        .attr('transform', d => `translate(${d.x ?? 0},${d.y ?? 0})`)
      g.select('.labels').selectAll<SVGTextElement, GraphNode>('text')
        .attr('x', d => d.x ?? 0)
        .attr('y', d => (d.y ?? 0) + nodeRadius(d.type) + 13)
      g.select('.hints').selectAll<SVGTextElement, GraphNode>('text')
        .attr('x', d => d.x ?? 0)
        .attr('y', d => (d.y ?? 0) + nodeRadius(d.type) + 23)
    })
  }, []) // eslint-disable-line

  // ── Zoom command ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!svgRef.current || !zoomRef.current || !zoomCommand) return
    const svg = d3.select(svgRef.current)
    const zoom = zoomRef.current
    const t = svg.transition().duration(220)
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const svgAny = svg as any
    if (zoomCommand.action === 'in')       svgAny.transition(t).call(zoom.scaleBy, 1.25)
    else if (zoomCommand.action === 'out') svgAny.transition(t).call(zoom.scaleBy, 0.8)
    else                                   svgAny.transition(t).call(zoom.transform, d3.zoomIdentity)
  }, [zoomCommand])

  // ── Update physics ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (!simRef.current) return
    const sim = simRef.current
    ;(sim.force('link') as d3.ForceLink<GraphNode, GraphEdge>).distance(physics.linkDistance).strength(physics.linkStrength)
    ;(sim.force('charge') as d3.ForceManyBody<GraphNode>).strength(physics.chargeStrength).distanceMax(physics.chargeDistanceMax)
    sim.force('outward', forceConstantOutward(width / 2, height / 2, physics.outwardStrength))
    const vLinks = (sim.force('link') as d3.ForceLink<GraphNode, GraphEdge>).links()
    sim.force('progressiveLink', forceProgressiveLink(physics.progressiveLinkBase, physics.progressiveLinkScale))
    const pf = sim.force('progressiveLink') as any
    if (pf) pf.links(vLinks)
    ;(sim.force('collide') as d3.ForceCollide<GraphNode>).radius(d => nodeRadius(d.type) + physics.collideRadiusOffset).strength(physics.collideStrength)
    sim.alphaDecay(physics.alphaDecay).velocityDecay(physics.velocityDecay)
    sim.alpha(Math.max(sim.alpha(), 0.3)).restart()
  }, [physics, width, height])

  // ── Update graph data ───────────────────────────────────────────────────────
  useEffect(() => {
    if (!simRef.current || !zlRef.current) return
    const sim = simRef.current
    const g   = zlRef.current

    try {
      const modeChanged = prevModeRef.current !== mode
      prevModeRef.current = mode
      const isAddition = nodes.length > prevCountRef.current
      prevCountRef.current = nodes.length

      const cx = width / 2; const cy = height / 2
      nodes.forEach(n => {
        if (n.depth === 0) { n.fx = n.active ? cx : null; n.fy = n.active ? cy : null }
      })

      // Simplified: only RAF nodes + their dependency edges
      const vNodes = mode === 'full' ? nodes : nodes.filter(n => n.type === 'raf-node')
      const vIds   = new Set(vNodes.map(n => n.id))
      const vLinks = mode === 'full' ? links : links.filter(l => {
        const s = typeof l.source === 'string' ? l.source : (l.source as GraphNode).id
        const t = typeof l.target === 'string' ? l.target : (l.target as GraphNode).id
        return vIds.has(s) && vIds.has(t)
      })

      const nodeById = new Map(vNodes.map(n => [n.id, n]))
      vLinks.forEach(l => {
        if (typeof l.source === 'object') { const c = nodeById.get((l.source as GraphNode).id); if (c && c !== l.source) l.source = c }
        if (typeof l.target === 'object') { const c = nodeById.get((l.target as GraphNode).id); if (c && c !== l.target) l.target = c }
      })

      // ── Color helpers ──
      const getNodeColor = (d: GraphNode) => {
        if (d.error) return '#ef4444'
        if (d.abandoned) return '#4b5563'
        if (d.type === 'raf-node') {
          if (d.caseType === 'base') return '#69ff47'
          if (d.caseType === 'recursive') return '#f59e0b'
          return '#00e5ff'
        }
        return NC[d.type] ?? '#888'
      }

      const getEdgeColor = (d: GraphEdge) => {
        const tgt = typeof d.target === 'object' ? d.target as GraphNode : nodeById.get(d.target as string)
        if (tgt?.abandoned) return '#374151'
        return EDGE_COLORS[d.edgeType] ?? '#444'
      }

      // ── Edges ──
      const eSel = g.select<SVGGElement>('.edges').selectAll<SVGLineElement, GraphEdge>('line').data(vLinks, d => d.id)
      eSel.exit().transition().duration(200).attr('opacity', 0).remove()
      eSel.enter().append('line').attr('opacity', 0).attr('stroke-linecap', 'round')
        .call(e => e.transition().duration(300).attr('opacity', 1))
        .merge(eSel)
        .attr('stroke', getEdgeColor)
        .attr('stroke-width', d => (d.edgeType === 'dependency' || d.edgeType === 'merge') ? 1.5 : 2)
        .attr('stroke-dasharray', d => {
          const tgt = typeof d.target === 'object' ? d.target as GraphNode : nodeById.get(d.target as string)
          if (tgt?.abandoned) return '4 4'
          if (d.edgeType === 'merge')       return '6 3'
          if (d.edgeType === 'parallel')    return '8 4'
          if (d.edgeType === 'dependency')  return '3 3'
          return 'none'
        })
        .attr('marker-end', d => {
          const tgt = typeof d.target === 'object' ? d.target as GraphNode : nodeById.get(d.target as string)
          if (tgt?.abandoned) return null
          return `url(#arr-${d.edgeType})`
        })

      // ── Nodes ──
      const nSel = g.select<SVGGElement>('.nodes').selectAll<SVGGElement, GraphNode>('g.ngrp').data(vNodes, d => d.id)
      nSel.exit().transition().duration(180).attr('opacity', 0).remove()

      const nEnter = nSel.enter().append('g')
        .attr('class', d => `ngrp ngrp-${d.type}`)
        .style('cursor', 'grab')
      nEnter.append('circle').attr('class', 'fill-circle').attr('r', 0).attr('filter', 'url(#glow)')
        .attr('fill', getNodeColor)
        .attr('stroke', 'rgba(255,255,255,0.2)').attr('stroke-width', 1.5)
        .transition().duration(420).attr('r', d => nodeRadius(d.type))
      // Active-ring: pulses while the node is running
      nEnter.append('circle').attr('class', 'active-ring')
        .attr('fill', 'none').attr('stroke-opacity', 0).attr('pointer-events', 'none')
      // Error badge: red circle + ✕ at top-right, shown when d.error or d.abandoned
      nEnter.append('circle').attr('class', 'error-bg')
        .attr('r', 6).attr('fill', '#ef4444').attr('stroke', '#0f172a').attr('stroke-width', 1.5)
        .attr('pointer-events', 'none').attr('opacity', 0)
      nEnter.append('text').attr('class', 'error-x')
        .attr('text-anchor', 'middle').attr('dy', 3.5).attr('font-size', 7.5).attr('font-weight', 700)
        .attr('fill', 'white').attr('pointer-events', 'none').attr('opacity', 0)
        .text('✕')
      // Short inside-node text (phase for raf-node, type letter for others)
      nEnter.append('text')
        .attr('class', 'inside')
        .attr('text-anchor', 'middle')
        .attr('dy', 3)
        .attr('pointer-events', 'none')
        .attr('font-size', 6.5)
        .attr('font-weight', 700)
        .attr('fill', '#020617')

      const nMerge = nEnter.merge(nSel)
      nMerge.attr('class', d => `ngrp ngrp-${d.type}${d.active ? ' raf-node-active' : ''}`)
      nMerge.select('circle.fill-circle')
        .attr('fill', getNodeColor)
        .attr('opacity', d => d.active ? 1 : 0.75)
      // Active ring: visible + coloured while running, hidden when done/idle
      nMerge.select('circle.active-ring')
        .attr('r', d => nodeRadius(d.type) + 6)
        .attr('stroke', d => getNodeColor(d))
        .attr('stroke-width', 2.5)
        .attr('stroke-opacity', d => d.active ? 0.85 : 0)
      // Error / abandoned badge: ✕ at top-right corner
      const showBadge = (d: GraphNode) => (d.error || d.abandoned) ? 1 : 0
      const badgeX = (d: GraphNode) => nodeRadius(d.type) * 0.72
      const badgeY = (d: GraphNode) => -nodeRadius(d.type) * 0.72
      nMerge.select('circle.error-bg')
        .attr('cx', badgeX).attr('cy', badgeY).attr('opacity', showBadge)
        .attr('fill', d => d.abandoned && !d.error ? '#6b7280' : '#ef4444')
      nMerge.select('text.error-x')
        .attr('x', badgeX).attr('y', badgeY).attr('opacity', showBadge)
      nMerge.select('text.inside')
        .text(d => {
          if (d.type === 'raf-node') {
            const p = d.phase || ''
            return p.length > 8 ? p.slice(0, 8) : p
          }
          return INSIDE_TEXT[d.type] || ''
        })
        .attr('fill', d =>
          d.type === 'raf-node'
            ? (d.caseType === 'recursive' ? '#111827' : '#020617')
            : 'rgba(0,0,0,0.75)'
        )
      nMerge
        .on('click', (e, d) => { onNodeClick?.(d); e.stopPropagation() })
        .on('mouseenter', function(_e, d) {
          d3.select(this).select('circle').transition().duration(100).attr('r', nodeRadius(d.type) * 1.3)
          d3.select(this).select('title').remove()
          d3.select(this).append('title').text(`${d.label}${d.hint ? '\n' + d.hint : ''}\n${d.detail}`)
        })
        .on('mouseleave', function(_e, d) {
          d3.select(this).select('circle').transition().duration(100).attr('r', nodeRadius(d.type))
        })

      const drag = d3.drag<SVGGElement, GraphNode>()
        .on('start', (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
        .on('drag',  (e, d) => { d.fx = e.x; d.fy = e.y })
        .on('end',   (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null })
      nMerge.call(drag)

      // ── Node ID labels (below node) ──
      const lSel = g.select<SVGGElement>('.labels').selectAll<SVGTextElement, GraphNode>('text').data(vNodes, d => d.id)
      lSel.exit().remove()
      lSel.enter().append('text')
        .attr('text-anchor', 'middle').attr('font-size', 9).attr('pointer-events', 'none')
        .merge(lSel)
        .attr('fill', d => d.abandoned && !d.error ? '#4b5563' : '#888')
        .text(d => {
          const lbl = d.label || ''
          return lbl.length > 14 ? lbl.slice(0, 13) + '…' : lbl
        })

      // ── Hint labels (compact info, below ID label) ──
      const hSel = g.select<SVGGElement>('.hints').selectAll<SVGTextElement, GraphNode>('text').data(vNodes, d => d.id)
      hSel.exit().remove()
      hSel.enter().append('text')
        .attr('text-anchor', 'middle').attr('font-size', 7.5).attr('pointer-events', 'none')
        .merge(hSel)
        .attr('fill', d => {
          if (d.type === 'raf-node') return d.caseType === 'base' ? '#69ff47' : d.caseType === 'recursive' ? '#f59e0b' : '#4b7c7c'
          return '#666'
        })
        .text(d => {
          // raf-node: show mode + confidence or just confidence
          if (d.type === 'raf-node') {
            const parts: string[] = []
            if (d.caseType) parts.push(d.caseType)
            if (d.confidence !== undefined) parts.push(`${(d.confidence * 100).toFixed(0)}%`)
            if (!d.active && d.success && parts.length === 0) parts.push('done')
            if (d.error) return 'error'
            return parts.join(' ')
          }
          const h = d.hint || ''
          return h.length > 16 ? h.slice(0, 15) + '…' : h
        })

      sim.nodes(vNodes)
      ;(sim.force('link') as d3.ForceLink<GraphNode, GraphEdge>).links(vLinks)
      const pf = sim.force('progressiveLink') as any
      if (pf) pf.links(vLinks)

      const targetAlpha = modeChanged ? 0.7 : isAddition ? 0.3 : 0.1
      sim.alpha(Math.max(sim.alpha(), targetAlpha)).restart()
    } catch (err) {
      console.error('[ExecutionGraph] update error:', err)
    }
  }, [nodes, links, mode, width, height])

  // ── Cleanup ─────────────────────────────────────────────────────────────────
  useEffect(() => () => {
    simRef.current?.stop(); simRef.current = null
    initRef.current = false; prevCountRef.current = 0
  }, [])

  return <svg ref={svgRef} style={{ width: '100%', height: '100%', background: 'hsl(222 47% 3%)' }} />
}
