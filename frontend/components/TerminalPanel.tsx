'use client'
import { useRef, useEffect } from 'react'

function stripAnsi(text: string): string {
  return text.replace(/\x1b\[[0-9;]*m/g, '')
}

export default function TerminalPanel({ output, success, isRunning, onRun, onTest, onBuild, onSnapshot }: {
  output: string; success: boolean | null; isRunning: boolean
  onRun: () => void; onTest: () => void; onBuild: () => void; onSnapshot: () => void
}) {
  const scrollRef = useRef<HTMLDivElement>(null)
  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight }, [output])

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-3 py-1.5 bg-deep border-b border-panel-border">
        <span className="font-orbitron text-xs text-stellar-text-dim tracking-wider flex-1">TERMINAL</span>
        <button onClick={onRun} disabled={isRunning}
          className="px-2.5 py-1 text-xs font-mono-tech bg-accent-dim text-accent border border-accent/40 rounded hover:bg-accent hover:text-void transition-colors disabled:opacity-40">
          {isRunning ? '⟳' : '▶'} dbt run
        </button>
        <button onClick={onTest} disabled={isRunning}
          className="px-2.5 py-1 text-xs font-mono-tech bg-deep text-stellar-text border border-panel-border rounded hover:bg-panel-border transition-colors disabled:opacity-40">
          dbt test
        </button>
        <button onClick={onBuild} disabled={isRunning}
          className="px-2.5 py-1 text-xs font-mono-tech bg-deep text-stellar-text border border-panel-border rounded hover:bg-panel-border transition-colors disabled:opacity-40">
          dbt build
        </button>
        <button onClick={onSnapshot} disabled={isRunning}
          className="px-2.5 py-1 text-xs font-mono-tech bg-deep text-stellar-text border border-panel-border rounded hover:bg-panel-border transition-colors disabled:opacity-40">
          dbt snapshot
        </button>
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-2 font-mono-tech text-xs leading-5 bg-void">
        {output ? (
          <pre className={`whitespace-pre-wrap ${success === false ? 'text-stellar-red' : 'text-stellar-text'}`}>
            {stripAnsi(output)}
          </pre>
        ) : (
          <span className="text-stellar-text-dim italic font-exo">Run a command to see output here...</span>
        )}
      </div>
    </div>
  )
}
