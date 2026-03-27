'use client'
import { useState } from 'react'
import type { Objective } from '@/hooks/useGameApi'

export default function ObjectivePanel({ objectives, newlyCompleted }: {
  objectives: Objective[]; newlyCompleted: string[]
}) {
  const firstIncomplete = objectives.findIndex(o => !o.passed)
  const [showHint, setShowHint] = useState<string | null>(null)

  return (
    <div className="p-2">
      <div className="font-orbitron text-xs text-stellar-text-dim mb-2 px-2 tracking-wider">MISSION OBJECTIVES</div>
      <div className="space-y-1">
        {objectives.map((obj, i) => {
          const isCurrent = i === firstIncomplete
          const isNew = newlyCompleted.includes(obj.id)
          const hintVisible = showHint === obj.id
          return (
            <div key={obj.id} className={`px-2 py-1.5 rounded text-sm font-exo
              ${obj.passed ? 'opacity-50' : ''} ${isCurrent ? 'bg-accent-dim' : ''}
              ${isNew ? 'bg-stellar-green/10 border border-stellar-green/30' : ''}`}>
              <div className="flex items-start gap-2">
                <span className={`mt-0.5 flex-shrink-0 w-4 h-4 rounded border flex items-center justify-center text-xs ${
                  obj.passed ? 'bg-stellar-green border-stellar-green text-void'
                    : isCurrent ? 'border-accent text-accent'
                    : 'border-panel-border text-transparent'
                }`}>
                  {obj.passed ? '✓' : isCurrent ? '▸' : ''}
                </span>
                <span className={`flex-1 ${obj.passed ? 'line-through text-stellar-text-dim' : ''}`}>{obj.label}</span>
              </div>
              {!obj.passed && obj.hint && (
                <div className="mt-1 ml-6">
                  <button
                    onClick={() => setShowHint(hintVisible ? null : obj.id)}
                    className={`px-1.5 py-0.5 rounded text-[10px] font-mono-tech transition-colors ${
                      hintVisible
                        ? 'bg-stellar-amber/20 text-stellar-amber'
                        : 'text-stellar-text-dim hover:text-stellar-amber border border-panel-border hover:border-stellar-amber/40'
                    }`}
                  >
                    hint
                  </button>
                </div>
              )}
              {hintVisible && obj.hint && (
                <div className="mt-1 ml-6 text-xs text-stellar-amber font-mono-tech leading-relaxed">
                  {obj.hint}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
