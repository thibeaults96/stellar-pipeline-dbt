'use client'

import { useState, useEffect } from 'react'
import { api } from '@/hooks/useGameApi'
import DagView from './DagView'
import ResultsPreview from './ResultsPreview'

export default function BottomPane({
  dagKey,
  previewModel,
  onSelectModel,
}: {
  dagKey: number
  previewModel: string
  onSelectModel: (name: string) => void
}) {
  const [activeTab, setActiveTab] = useState<'dag' | 'preview'>('dag')
  const [modelNames, setModelNames] = useState<string[]>([])

  // Fetch model names from manifest
  useEffect(() => {
    api.getManifest()
      .then((data: { nodes: { name: string; type: string }[] }) => {
        const names = (data.nodes || [])
          .filter(n => n.type === 'model')
          .map(n => n.name)
          .sort()
        setModelNames(names)
        if (names.length > 0 && !names.includes(previewModel)) {
          onSelectModel(names[0])
        }
      })
      .catch(() => {})
  }, [dagKey, previewModel, onSelectModel])

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center bg-deep border-b border-panel-border flex-shrink-0">
        <button
          onClick={() => setActiveTab('dag')}
          className={`px-3 py-1.5 font-orbitron text-xs tracking-wider transition-colors ${
            activeTab === 'dag'
              ? 'text-accent border-b-2 border-accent bg-void'
              : 'text-stellar-text-dim hover:text-stellar-text'
          }`}
        >
          DAG
        </button>
        <button
          onClick={() => setActiveTab('preview')}
          className={`px-3 py-1.5 font-orbitron text-xs tracking-wider transition-colors ${
            activeTab === 'preview'
              ? 'text-accent border-b-2 border-accent bg-void'
              : 'text-stellar-text-dim hover:text-stellar-text'
          }`}
        >
          PREVIEW
        </button>
        {activeTab === 'preview' && modelNames.length > 0 && (
          <div className="flex items-center ml-2 gap-1">
            {modelNames.map(name => (
              <button
                key={name}
                onClick={() => onSelectModel(name)}
                className={`px-2 py-0.5 font-mono-tech text-[10px] rounded transition-colors ${
                  previewModel === name
                    ? 'bg-accent-dim text-accent border border-accent/40'
                    : 'text-stellar-text-dim hover:text-stellar-text border border-panel-border'
                }`}
              >
                {name}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="flex-1 min-h-0 bg-void">
        {activeTab === 'dag' ? (
          <DagView key={dagKey} />
        ) : (
          <ResultsPreview key={previewModel + dagKey} modelName={previewModel} />
        )}
      </div>
    </div>
  )
}
