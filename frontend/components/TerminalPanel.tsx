'use client'
import { useRef, useEffect } from 'react'

function stripAnsi(text: string): string {
  return text.replace(/\x1b\[[0-9;]*m/g, '')
}

export default function TerminalPanel({ output, success }: {
  output: string; success: boolean | null
}) {
  const scrollRef = useRef<HTMLDivElement>(null)
  useEffect(() => { if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight }, [output])

  return (
    <div ref={scrollRef} className="h-full overflow-y-auto p-2 font-mono-tech text-xs leading-5 bg-void">
      {output ? (
        <pre className={`whitespace-pre-wrap ${success === false ? 'text-stellar-red' : 'text-stellar-text'}`}>
          {stripAnsi(output)}
        </pre>
      ) : (
        <span className="text-stellar-text-dim italic font-exo">Run a command from the toolbar to see output here...</span>
      )}
    </div>
  )
}
