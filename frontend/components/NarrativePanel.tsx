'use client'
import { useEffect, useRef } from 'react'
import type { NarrativeEvent } from '@/hooks/useGameApi'

const CHARACTER_COLORS: Record<string, string> = {
  'R0-B3RT': '#00ff9d', 'LYRA': '#00d4ff', 'KAEL': '#ffb800',
  'SABLE': '#a855f7', 'SYSTEM': '#4a6070', 'VOSS': '#c8d8e8',
}

function renderMsg(msg: string) {
  return msg.split(/(<highlight>.*?<\/highlight>)/g).map((part, i) =>
    part.startsWith('<highlight>')
      ? <span key={i} className="text-stellar-amber font-bold">{part.replace(/<\/?highlight>/g, '')}</span>
      : <span key={i}>{part}</span>
  )
}

export default function NarrativePanel({ narratives }: { narratives: NarrativeEvent[] }) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const prevLenRef = useRef(0)
  const batchStartRef = useRef(0)

  useEffect(() => {
    const prev = prevLenRef.current
    const curr = narratives.length

    if (curr > prev) {
      batchStartRef.current = prev
    } else if (curr < prev) {
      batchStartRef.current = 0
    }

    prevLenRef.current = curr
  }, [narratives.length])

  // Scroll to top when new messages arrive (newest are at top)
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0
    }
  }, [narratives.length])

  if (!narratives.length) {
    return (
      <div className="flex flex-col border-t border-panel-border max-h-[200px]">
        <div className="px-3 py-1.5 font-orbitron text-xs text-stellar-text-dim tracking-wider border-b border-panel-border bg-deep flex-shrink-0">COMMS</div>
        <div className="flex-1 flex items-center justify-center p-3">
          <span className="font-exo text-xs text-stellar-text-dim italic">Awaiting transmission...</span>
        </div>
      </div>
    )
  }

  const batchStart = batchStartRef.current
  // Reverse: newest messages first
  const reversed = [...narratives].reverse()

  return (
    <div className="flex flex-col border-t border-panel-border max-h-[200px]">
      <div className="px-3 py-1.5 font-orbitron text-xs text-stellar-text-dim tracking-wider border-b border-panel-border bg-deep flex-shrink-0">
        COMMS
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {reversed.map((event, ri) => {
          const originalIndex = narratives.length - 1 - ri
          const color = CHARACTER_COLORS[event.character] ?? '#c8d8e8'
          const isNew = originalIndex >= batchStart

          return (
            <div
              key={`${event.id}-${originalIndex}`}
              className={`px-3 py-2.5 border-b border-panel-border/30 ${
                isNew ? 'animate-fade-in' : 'opacity-50'
              }`}
            >
              <div className="flex items-center gap-1.5 mb-1">
                {isNew && <span style={{ color }} className="text-sm">⚡</span>}
                <span className="font-orbitron text-[10px] tracking-wider" style={{ color }}>
                  {event.character}
                </span>
              </div>
              <p className="font-exo text-sm text-stellar-text leading-relaxed">
                {renderMsg(event.message)}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
