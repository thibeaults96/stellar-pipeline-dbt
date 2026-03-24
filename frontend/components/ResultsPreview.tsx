'use client'

import { useState, useEffect } from 'react'
import { api, type SourcePreview } from '@/hooks/useGameApi'

export default function ResultsPreview({ modelName }: { modelName: string }) {
  const [data, setData] = useState<SourcePreview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    setError(null)
    api.previewModel(modelName)
      .then(d => { setData(d); setLoading(false) })
      .catch(() => { setError(`Could not load ${modelName}. Run 'dbt run' first.`); setLoading(false) })
  }, [modelName])

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <span className="text-stellar-text-dim font-mono-tech text-xs animate-pulse-glow">Querying {modelName}...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center">
        <span className="text-stellar-text-dim font-exo text-xs">{error}</span>
      </div>
    )
  }

  if (!data || !data.rows || !data.rows.length) {
    return (
      <div className="h-full flex items-center justify-center">
        <span className="text-stellar-text-dim font-exo text-xs">No rows in {modelName}</span>
      </div>
    )
  }

  return (
    <div className="h-full overflow-auto">
      <table className="w-full text-xs font-mono-tech border-collapse">
        <thead>
          <tr>
            {data.columns.map(col => (
              <th key={col} className="text-left px-2 py-1.5 text-stellar-text-dim border-b border-panel-border whitespace-nowrap sticky top-0 bg-deep">
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
                  <td key={col} className={`px-2 py-1 border-b border-panel-border/50 whitespace-nowrap ${isNull ? 'text-stellar-red italic' : 'text-stellar-text'}`}>
                    {isNull ? 'NULL' : String(val)}
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="px-2 py-1 text-stellar-text-dim text-xs font-mono-tech">
        {data.totalRows} row{data.totalRows !== 1 ? 's' : ''} total
      </div>
    </div>
  )
}
