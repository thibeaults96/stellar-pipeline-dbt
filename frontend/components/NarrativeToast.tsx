'use client'
import { useState, useEffect, useRef } from 'react'
import type { NarrativeEvent } from '@/hooks/useGameApi'

const CHARACTER_COLORS: Record<string, string> = {
  'R0-B3RT': '#00ff9d',
  'VOSS': '#c8d8e8',
}

export type ToastEntry = { key: number; narrative: NarrativeEvent }

function renderMessage(msg: string) {
  return msg.split(/(<highlight>.*?<\/highlight>)/g).map((part, i) =>
    part.startsWith('<highlight>') ? (
      <span key={i} className="text-stellar-amber font-bold">
        {part.replace(/<\/?highlight>/g, '')}
      </span>
    ) : (
      <span key={i}>{part}</span>
    ),
  )
}

export default function NarrativeToast({
  toasts,
  onDismiss,
}: {
  toasts: ToastEntry[]
  onDismiss: (key: number) => void
}) {
  // Show one transmission at a time. The user clicks through; the rest of
  // the queue waits behind the active one until then.
  const active = toasts[0]
  if (!active) return null

  return (
    <div
      className="fixed top-[72px] left-1/2 -translate-x-1/2 z-40 pointer-events-none w-[40rem] max-w-[92vw]"
      aria-live="polite"
    >
      <ToastCard
        key={active.key}
        entry={active}
        position={1}
        total={toasts.length}
        onDismiss={() => onDismiss(active.key)}
      />
    </div>
  )
}

function ToastCard({
  entry,
  position,
  total,
  onDismiss,
}: {
  entry: ToastEntry
  position: number
  total: number
  onDismiss: () => void
}) {
  const { narrative } = entry
  const color = CHARACTER_COLORS[narrative.character] ?? '#c8d8e8'
  const [leaving, setLeaving] = useState(false)
  const dismissedRef = useRef(false)

  const startLeave = () => {
    if (dismissedRef.current) return
    dismissedRef.current = true
    setLeaving(true)
  }

  useEffect(() => {
    if (!leaving) return
    const removeAfterAnim = setTimeout(onDismiss, 220)
    return () => clearTimeout(removeAfterAnim)
  }, [leaving, onDismiss])

  const queued = total - 1

  return (
    <button
      type="button"
      onClick={startLeave}
      className={`pointer-events-auto w-full text-left bg-panel border border-panel-border rounded-lg px-5 py-4 transition-shadow hover:shadow-accent/30 ${
        leaving ? 'animate-toast-out' : 'animate-toast-in'
      }`}
      style={{
        borderLeftColor: color,
        borderLeftWidth: 3,
        boxShadow: `0 12px 32px rgba(0,0,0,0.6), 0 0 0 1px ${color}33`,
      }}
    >
      <div className="flex items-center gap-2 mb-2">
        <span
          className="w-1.5 h-1.5 rounded-full animate-pulse-glow"
          style={{ backgroundColor: color }}
        />
        <span className="font-orbitron text-[10px] tracking-widest" style={{ color }}>
          {narrative.character}
        </span>
        <span className="ml-auto font-mono-tech text-[9px] text-stellar-text-dim">
          NEW TRANSMISSION
          {total > 1 && (
            <span className="ml-2 text-accent">
              {position} / {total}
            </span>
          )}
        </span>
      </div>
      <p className="font-exo text-sm text-stellar-text leading-relaxed">
        {renderMessage(narrative.message)}
      </p>
      <div className="mt-3 flex items-center justify-between font-mono-tech text-[10px] text-stellar-text-dim">
        <span>full log in COMMS →</span>
        <span className="text-accent">
          {queued > 0 ? `click to continue · ${queued} more →` : 'click to dismiss →'}
        </span>
      </div>
    </button>
  )
}
