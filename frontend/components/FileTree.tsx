'use client'
import type { FileEntry, SourceEntry } from '@/hooks/useGameApi'

export default function FileTree({ files, sources, activeFile, onSelect, onPreviewSource }: {
  files: FileEntry[]
  sources: SourceEntry[]
  activeFile: string
  onSelect: (path: string) => void
  onPreviewSource: (name: string) => void
}) {
  const groups: Record<string, FileEntry[]> = {}
  for (const f of files) {
    const folder = f.path.split('/').slice(0, -1).join('/')
    if (!groups[folder]) groups[folder] = []
    groups[folder].push(f)
  }
  return (
    <div className="p-2">
      <div className="font-orbitron text-xs text-stellar-text-dim mb-2 px-2 tracking-wider">FILES</div>
      {Object.entries(groups).map(([folder, entries]) => (
        <div key={folder} className="mb-1">
          <div className="font-mono-tech text-xs text-stellar-text-dim px-2 py-1">{folder}/</div>
          {entries.map(f => {
            const name = f.path.split('/').pop()!
            const active = f.path === activeFile
            return (
              <button key={f.path} onClick={() => onSelect(f.path)}
                className={`w-full text-left flex items-center gap-2 px-2 py-1 rounded text-sm font-mono-tech transition-colors
                  ${active
                    ? 'bg-accent-dim text-stellar-text-bright border-l-2 border-accent'
                    : 'text-stellar-text hover:bg-deep border-l-2 border-transparent'}`}>
                <span className="text-stellar-text-dim text-xs">{name.endsWith('.sql') ? '⟨⟩' : '☰'}</span>
                <span className="truncate flex-1">{name}</span>
                {f.locked && <span className="text-stellar-text-dim text-xs">🔒</span>}
              </button>
            )
          })}
        </div>
      ))}

      {sources.length > 0 && (
        <div className="mt-3">
          <div className="font-orbitron text-xs text-stellar-text-dim mb-2 px-2 tracking-wider">SOURCE DATA</div>
          {sources.map(s => (
            <button key={s.name} onClick={() => onPreviewSource(s.name)}
              className="w-full text-left flex items-center gap-2 px-2 py-1 rounded text-sm font-mono-tech text-stellar-text hover:bg-deep border-l-2 border-transparent transition-colors">
              <span className="text-stellar-amber text-xs">⊞</span>
              <span className="truncate flex-1">{s.name}</span>
              <span className="text-stellar-text-dim text-[10px]">{s.rowCount} rows</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
