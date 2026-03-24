'use client'

import { useEffect, useState, useMemo } from 'react'
import { api } from '@/hooks/useGameApi'

interface DagNode {
  id: string
  name: string
  type: string   // model, seed, source
  status: string // success, error, skipped, pending
}

interface DagEdge {
  source: string
  target: string
}

const STATUS_COLORS: Record<string, { fill: string; stroke: string; text: string }> = {
  success: { fill: 'rgba(0,255,157,0.1)', stroke: '#00ff9d', text: '#00ff9d' },
  error:   { fill: 'rgba(255,61,90,0.1)', stroke: '#ff3d5a', text: '#ff3d5a' },
  skipped: { fill: 'rgba(30,45,69,0.3)',  stroke: '#1e2d45', text: '#4a6070' },
  pending: { fill: 'rgba(30,45,69,0.5)',  stroke: '#1e2d45', text: '#4a6070' },
  pass:    { fill: 'rgba(0,255,157,0.1)', stroke: '#00ff9d', text: '#00ff9d' },
  fail:    { fill: 'rgba(255,61,90,0.1)', stroke: '#ff3d5a', text: '#ff3d5a' },
}

const TYPE_LABELS: Record<string, string> = {
  seed: 'SEED',
  source: 'SOURCE',
  model: 'MODEL',
}

const NODE_W = 140
const NODE_H = 44
const LAYER_GAP_X = 180
const NODE_GAP_Y = 60
const PAD_X = 40
const PAD_Y = 30

function layoutNodes(nodes: DagNode[], edges: DagEdge[]) {
  // Assign layers via topological sort
  const inDegree: Record<string, number> = {}
  const children: Record<string, string[]> = {}
  for (const n of nodes) { inDegree[n.id] = 0; children[n.id] = [] }
  for (const e of edges) {
    if (inDegree[e.target] !== undefined) inDegree[e.target]++
    if (children[e.source]) children[e.source].push(e.target)
  }

  const layers: Record<string, number> = {}
  const queue = Object.keys(inDegree).filter(id => inDegree[id] === 0)
  for (const id of queue) layers[id] = 0

  let idx = 0
  while (idx < queue.length) {
    const id = queue[idx++]
    for (const child of (children[id] || [])) {
      layers[child] = Math.max(layers[child] || 0, (layers[id] || 0) + 1)
      inDegree[child]--
      if (inDegree[child] === 0) queue.push(child)
    }
  }
  // Nodes not reached (cycles)
  for (const n of nodes) {
    if (layers[n.id] === undefined) layers[n.id] = 0
  }

  // Group by layer
  const byLayer: Record<number, DagNode[]> = {}
  for (const n of nodes) {
    const l = layers[n.id]
    if (!byLayer[l]) byLayer[l] = []
    byLayer[l].push(n)
  }

  // Assign positions
  const positions: Record<string, { x: number; y: number }> = {}
  const maxLayer = Math.max(...Object.keys(byLayer).map(Number), 0)

  for (let l = 0; l <= maxLayer; l++) {
    const group = byLayer[l] || []
    for (let i = 0; i < group.length; i++) {
      positions[group[i].id] = {
        x: PAD_X + l * LAYER_GAP_X,
        y: PAD_Y + i * NODE_GAP_Y,
      }
    }
  }

  const maxY = Math.max(...Object.values(positions).map(p => p.y), 0)
  const maxX = PAD_X + maxLayer * LAYER_GAP_X + NODE_W

  return { positions, width: maxX + PAD_X, height: maxY + NODE_H + PAD_Y }
}

export default function DagView() {
  const [nodes, setNodes] = useState<DagNode[]>([])
  const [edges, setEdges] = useState<DagEdge[]>([])

  const refresh = () => {
    api.getManifest().then((data: { nodes: DagNode[]; edges: DagEdge[] }) => {
      setNodes(data.nodes || [])
      setEdges(data.edges || [])
    }).catch(() => {})
  }

  useEffect(() => { refresh() }, [])

  // Re-fetch whenever window regains focus (catches post-run updates)
  useEffect(() => {
    window.addEventListener('focus', refresh)
    return () => window.removeEventListener('focus', refresh)
  }, [])

  const { positions, width, height } = useMemo(
    () => layoutNodes(nodes, edges), [nodes, edges]
  )

  if (!nodes.length) {
    return (
      <div className="h-full flex items-center justify-center">
        <span className="text-stellar-text-dim font-exo text-xs italic">
          Run `dbt run` to see the DAG
        </span>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto">
      <svg width={width} height={height} className="min-w-full min-h-full">
        {/* Edges */}
        {edges.map((e, i) => {
          const from = positions[e.source]
          const to = positions[e.target]
          if (!from || !to) return null
          const sourceStatus = nodes.find(n => n.id === e.source)?.status || 'pending'
          const color = STATUS_COLORS[sourceStatus]?.stroke || '#1e2d45'
          return (
            <line key={i}
              x1={from.x + NODE_W} y1={from.y + NODE_H / 2}
              x2={to.x} y2={to.y + NODE_H / 2}
              stroke={color} strokeWidth={1.5} opacity={0.6}
            />
          )
        })}

        {/* Nodes */}
        {nodes.map(n => {
          const pos = positions[n.id]
          if (!pos) return null
          const colors = STATUS_COLORS[n.status] || STATUS_COLORS.pending
          const isDashed = n.type === 'seed' || n.type === 'source'
          return (
            <g key={n.id}>
              <rect
                x={pos.x} y={pos.y}
                width={NODE_W} height={NODE_H}
                rx={4}
                fill={colors.fill}
                stroke={colors.stroke}
                strokeWidth={1.5}
                strokeDasharray={isDashed ? '4 2' : undefined}
              />
              <text
                x={pos.x + 8} y={pos.y + 14}
                fill={colors.text}
                fontSize={9}
                fontFamily="var(--font-orbitron), sans-serif"
                letterSpacing="0.08em"
              >
                {TYPE_LABELS[n.type] || 'MODEL'}
              </text>
              <text
                x={pos.x + 8} y={pos.y + 30}
                fill="#c8d8e8"
                fontSize={11}
                fontFamily="var(--font-mono-tech), monospace"
              >
                {n.name}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
