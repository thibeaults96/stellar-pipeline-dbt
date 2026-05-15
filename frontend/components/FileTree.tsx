'use client'
import type { FileEntry, SourceEntry } from '@/hooks/useGameApi'

// Natural reading order of a dbt project: root config → seeds → sources →
// staging → marts → other models → macros → snapshots. Unknown folders fall
// to the end alphabetically.
const FOLDER_ORDER: string[] = [
  '',
  'seeds',
  'models/sources',
  'models/staging',
  'models/marts',
  'models',
  'macros',
  'snapshots',
]

function folderRank(folder: string): number {
  const idx = FOLDER_ORDER.indexOf(folder)
  return idx === -1 ? FOLDER_ORDER.length : idx
}

function folderLabel(folder: string): string {
  return folder === '' ? '/' : `${folder}/`
}

function fileIcon(name: string): string {
  if (name.endsWith('.sql')) return '⟨⟩'
  if (name.endsWith('.csv')) return '⊞'
  if (name.endsWith('.md')) return '¶'
  return '☰'
}

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
  const ordered = Object.entries(groups).sort(([a], [b]) => {
    const ra = folderRank(a), rb = folderRank(b)
    if (ra !== rb) return ra - rb
    return a.localeCompare(b)
  })

  return (
    <div className="p-2">
      <div className="font-orbitron text-xs text-stellar-text-dim mb-2 px-2 tracking-wider">PROJECT</div>
      {ordered.map(([folder, entries]) => (
        <div key={folder || 'root'} className="mb-1">
          <div className="font-mono-tech text-xs text-stellar-text-dim px-2 py-1">{folderLabel(folder)}</div>
          {entries.map(f => {
            const name = f.path.split('/').pop()!
            const active = f.path === activeFile
            return (
              <button key={f.path} onClick={() => onSelect(f.path)}
                className={`w-full text-left flex items-center gap-2 px-2 py-1 rounded text-sm font-mono-tech transition-colors
                  ${active
                    ? 'bg-accent-dim text-stellar-text-bright border-l-2 border-accent'
                    : 'text-stellar-text hover:bg-deep border-l-2 border-transparent'}`}>
                <span className="text-stellar-text-dim text-xs">{fileIcon(name)}</span>
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
