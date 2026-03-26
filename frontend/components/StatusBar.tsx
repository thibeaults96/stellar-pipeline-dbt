'use client'
import type { GameStatus } from '@/hooks/useGameApi'

const LEVELS = [
  { id: 1, name: 'First Day' },
  { id: 2, name: 'Kepler-7b' },
  { id: 3, name: "Smuggler's Ledger" },
  { id: 4, name: 'Refresh Crisis' },
  { id: 5, name: 'Time Ledger' },
  { id: 6, name: 'Clean Handoff' },
]

export default function StatusBar({
  status, isRunning, onRun, onReset, onSelectLevel,
}: {
  status: GameStatus | null
  isRunning: boolean
  onRun: () => void
  onReset: () => void
  onSelectLevel: (id: number) => void
}) {
  if (!status) return null
  const maxXP = 1000

  return (
    <div className="h-[52px] bg-panel border-b border-panel-border flex items-center px-4 gap-4">
      <div className="font-orbitron font-bold text-accent text-sm tracking-widest whitespace-nowrap">
        STELLAR <span className="text-stellar-text-dim">{"//"}</span> PIPELINE
      </div>
      <div className="w-px h-6 bg-panel-border" />
      <div className="flex items-center gap-1">
        {LEVELS.map(l => {
          const isCurrent = status.level.id === l.id
          const isDone = status.completedLevels.includes(l.id)
          return (
            <button
              key={l.id}
              onClick={() => onSelectLevel(l.id)}
              disabled={isRunning}
              className={`px-2 py-1 font-mono-tech text-xs rounded transition-colors ${
                isCurrent
                  ? 'bg-accent-dim text-accent border border-accent/40'
                  : isDone
                    ? 'text-stellar-green border border-stellar-green/30 hover:bg-stellar-green/10'
                    : 'text-stellar-text-dim border border-panel-border hover:text-stellar-text'
              }`}
              title={l.name}
            >
              {l.id}
            </button>
          )
        })}
        <span className="text-stellar-text-bright font-exo text-sm truncate ml-1">
          {status.level.title}
        </span>
      </div>
      <div className="flex-1" />
      <div className="flex items-center gap-2">
        <span className="font-mono-tech text-xs text-stellar-text-dim">XP</span>
        <div className="w-32 h-2 bg-deep rounded-full overflow-hidden">
          <div className="h-full bg-accent transition-all duration-500 rounded-full"
            style={{ width: `${Math.min(100, (status.totalXP / maxXP) * 100)}%` }} />
        </div>
        <span className="font-mono-tech text-xs text-accent">{status.totalXP}</span>
      </div>
      <div className="flex items-center gap-1">
        {status.earnedBadges.map(b => (
          <span key={b.id} className="text-lg" title={b.name}>{b.emoji}</span>
        ))}
      </div>
      <button onClick={onReset} disabled={isRunning}
        className="px-2 py-1.5 text-stellar-text-dim font-mono-tech text-xs border border-panel-border rounded hover:border-stellar-red hover:text-stellar-red transition-colors disabled:opacity-50"
        title="Reset level">
        ↺
      </button>
      <button onClick={onRun} disabled={isRunning}
        className="flex items-center gap-1.5 px-3 py-1.5 bg-accent-dim border border-accent text-accent font-orbitron text-xs rounded hover:bg-accent hover:text-void transition-colors disabled:opacity-50">
        {isRunning ? <span className="animate-spin">⟳</span> : <span>▶</span>}
        dbt run
      </button>
    </div>
  )
}
