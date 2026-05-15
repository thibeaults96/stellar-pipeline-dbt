'use client'

import type { SourcePreview } from '@/hooks/useGameApi'

export default function DataPreview({ data, onClose }: {
  data: SourcePreview; onClose: () => void
}) {
  if (!data.rows.length) {
    return (
      <div className="h-full flex items-center justify-center text-stellar-text-dim font-exo">
        No data available
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full bg-deep">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-panel-border bg-panel">
        <span className="font-orbitron text-xs text-stellar-text-dim tracking-wider">
          DATA PREVIEW — {data.name}
        </span>
        <div className="flex items-center gap-3">
          <span className="font-mono-tech text-xs text-stellar-text-dim">{data.totalRows} rows</span>
          <button onClick={onClose}
            className="text-stellar-text-dim hover:text-stellar-red text-sm transition-colors">
            ×
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-2">
        <table className="w-full text-xs font-mono-tech border-collapse">
          <thead>
            <tr>
              {data.columns.map(col => (
                <th key={col}
                  className="text-left px-2 py-1.5 text-stellar-text-dim border-b border-panel-border whitespace-nowrap sticky top-0 bg-deep">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row, i) => (
              <tr key={i} className="hover:bg-panel/50">
                {data.columns.map(col => {
                  const val = row[col]
                  const isNull = val === null || val === undefined || val === ''
                  return (
                    <td key={col}
                      className={`px-2 py-1 border-b border-panel-border/50 whitespace-nowrap ${
                        isNull ? 'text-stellar-red italic' : 'text-stellar-text'
                      }`}>
                      {isNull ? 'NULL' : String(val)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
