'use client'
import { useState, useEffect, useRef } from 'react'
import type { NarrativeEvent } from '@/hooks/useGameApi'

const CHARACTER_COLORS: Record<string, string> = {
  'R0-B3RT': '#00ff9d', 'VOSS': '#c8d8e8',
}

function renderMsg(msg: string) {
  return msg.split(/(<highlight>.*?<\/highlight>)/g).map((part, i) =>
    part.startsWith('<highlight>')
      ? <span key={i} className="text-stellar-amber font-bold">{part.replace(/<\/?highlight>/g, '')}</span>
      : <span key={i}>{part}</span>
  )
}

export default function NarrativePanel({ narratives }: { narratives: NarrativeEvent[] }) {
  const [showLog, setShowLog] = useState(false)
  const prevLenRef = useRef(0)
  const [latestIndex, setLatestIndex] = useState(0)
  const [hasUnread, setHasUnread] = useState(false)

  useEffect(() => {
    if (narratives.length > prevLenRef.current) {
      // New messages arrived — show the first one of the new batch and flag unread
      setLatestIndex(prevLenRef.current)
      setShowLog(false)
      setHasUnread(true)
    } else if (narratives.length < prevLenRef.current) {
      // Level reset — start from the beginning
      setLatestIndex(0)
      setShowLog(false)
      setHasUnread(false)
    }
    prevLenRef.current = narratives.length
  }, [narratives.length])

  const markRead = () => setHasUnread(false)

  if (!narratives.length) {
    return (
      <div className="flex flex-col h-full border-b border-panel-border">
        <div className="px-3 py-1.5 font-orbitron text-xs text-stellar-text-dim tracking-wider border-b border-panel-border bg-deep flex-shrink-0">COMMS</div>
        <div className="flex-1 flex items-center justify-center">
          <span className="font-mono-tech text-xs text-stellar-text-dim animate-pulse-glow">awaiting signal...</span>
        </div>
      </div>
    )
  }

  const latest = narratives[latestIndex] ?? narratives[narratives.length - 1]
  const color = CHARACTER_COLORS[latest?.character] ?? '#c8d8e8'
  const logCount = narratives.length

  return (
    <div
      className={`flex flex-col h-full border-b transition-colors ${
        hasUnread ? 'border-stellar-amber/60' : 'border-panel-border'
      }`}
      onClick={markRead}
    >
      {/* Header */}
      <div className="px-3 py-1.5 font-orbitron text-xs text-stellar-text-dim tracking-wider border-b border-panel-border bg-deep flex-shrink-0 flex items-center">
        <span className="flex-1 flex items-center gap-2">
          COMMS
          {hasUnread && (
            <span
              className="inline-block w-2 h-2 rounded-full bg-stellar-amber animate-pulse-glow"
              aria-label="new transmission"
            />
          )}
        </span>
        {logCount > 1 && (
          <button
            onClick={() => { markRead(); setShowLog(!showLog) }}
            className={`font-mono-tech text-[10px] px-1.5 py-0.5 rounded transition-colors ${
              showLog
                ? 'bg-accent-dim text-accent'
                : 'text-stellar-text-dim hover:text-stellar-text'
            }`}
          >
            log ({logCount})
          </button>
        )}
      </div>

      {showLog ? (
        /* Transmission log — full scrollable history */
        <div className="flex-1 overflow-y-auto">
          {[...narratives].reverse().map((event, ri) => {
            const idx = narratives.length - 1 - ri
            const c = CHARACTER_COLORS[event.character] ?? '#c8d8e8'
            const isCurrent = idx === latestIndex
            return (
              <button
                key={`${event.id}-${idx}`}
                onClick={() => { setLatestIndex(idx); setShowLog(false) }}
                className={`w-full text-left px-3 py-2 border-b border-panel-border/20 transition-colors hover:bg-deep/80 ${
                  isCurrent ? 'bg-deep/50' : ''
                }`}
              >
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ backgroundColor: c }} />
                  <span className="font-orbitron text-[9px] tracking-wider" style={{ color: c }}>
                    {event.character}
                  </span>
                  {isCurrent && <span className="font-mono-tech text-[8px] text-accent ml-auto">current</span>}
                </div>
                <p className="font-exo text-xs text-stellar-text-dim leading-snug line-clamp-2">
                  {event.message.replace(/<\/?highlight>/g, '')}
                </p>
              </button>
            )
          })}
        </div>
      ) : (
        /* Active transmission — single message focus */
        <div className="flex-1 overflow-y-auto px-3 py-3">
          {/* Signal indicator */}
          <div className="flex items-center gap-2 mb-2">
            <div className="flex gap-0.5">
              <span className="w-1 h-3 rounded-sm animate-pulse-glow" style={{ backgroundColor: color, opacity: 0.9 }} />
              <span className="w-1 h-2 rounded-sm animate-pulse-glow" style={{ backgroundColor: color, opacity: 0.6, animationDelay: '0.1s' }} />
              <span className="w-1 h-3.5 rounded-sm animate-pulse-glow" style={{ backgroundColor: color, opacity: 0.8, animationDelay: '0.2s' }} />
              <span className="w-1 h-2 rounded-sm animate-pulse-glow" style={{ backgroundColor: color, opacity: 0.5, animationDelay: '0.3s' }} />
            </div>
            <span className="font-orbitron text-[10px] tracking-widest" style={{ color }}>
              {latest.character}
            </span>
            <span className="font-mono-tech text-[9px] text-stellar-text-dim ml-auto">
              {latestIndex + 1}/{logCount}
            </span>
          </div>

          {/* Message */}
          <div className="animate-fade-in">
            <p className="font-exo text-sm text-stellar-text leading-relaxed">
              {renderMsg(latest.message)}
            </p>
          </div>

          {/* Navigation */}
          {logCount > 1 && (
            <div className="flex items-center gap-2 mt-3 pt-2 border-t border-panel-border/30">
              <button
                onClick={() => setLatestIndex(Math.max(0, latestIndex - 1))}
                disabled={latestIndex <= 0}
                className="font-mono-tech text-[10px] text-stellar-text-dim hover:text-stellar-text disabled:opacity-30 transition-colors"
              >
                prev
              </button>
              <div className="flex-1 flex justify-center gap-1">
                {narratives.map((_, i) => (
                  <button
                    key={i}
                    onClick={() => setLatestIndex(i)}
                    className={`w-1.5 h-1.5 rounded-full transition-colors ${
                      i === latestIndex ? 'bg-accent' : i < latestIndex ? 'bg-stellar-text-dim/50' : 'bg-panel-border'
                    }`}
                  />
                ))}
              </div>
              <button
                onClick={() => setLatestIndex(Math.min(narratives.length - 1, latestIndex + 1))}
                disabled={latestIndex >= narratives.length - 1}
                className="font-mono-tech text-[10px] text-stellar-text-dim hover:text-stellar-text disabled:opacity-30 transition-colors"
              >
                next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
