'use client'

import { useState, useEffect } from 'react'
import { api } from '@/hooks/useGameApi'
import DagView from './DagView'
import ResultsPreview from './ResultsPreview'
import TerminalPanel from './TerminalPanel'
import DeployPanel from './DeployPanel'
import EnvironmentPanel from './EnvironmentPanel'
import SchedulePanel from './SchedulePanel'

export type Tab = 'dag' | 'preview' | 'terminal' | 'deploy' | 'environment' | 'schedule'

export default function BottomPane({
  dagKey,
  previewModel,
  onSelectModel,
  termOutput,
  termSuccess,
  activeTab,
  onTabChange,
  currentLevel,
  onReport,
}: {
  dagKey: number
  previewModel: string
  onSelectModel: (name: string) => void
  termOutput: string
  termSuccess: boolean | null
  activeTab: Tab
  onTabChange: (tab: Tab) => void
  currentLevel: number
  onReport: (r: import('@/hooks/useGameApi').ActionReport) => void
}) {
  const [modelNames, setModelNames] = useState<string[]>([])

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

  const tabClass = (t: Tab) =>
    `px-3 py-1.5 font-orbitron text-xs tracking-wider transition-colors ${
      activeTab === t
        ? 'text-accent border-b-2 border-accent bg-void'
        : 'text-stellar-text-dim hover:text-stellar-text'
    }`

  const showDeploy = currentLevel === 7
  const showEnvironment = currentLevel === 8
  const showSchedule = currentLevel === 9

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center bg-deep border-b border-panel-border flex-shrink-0">
        <button onClick={() => onTabChange('dag')} className={tabClass('dag')}>DAG</button>
        <button onClick={() => onTabChange('preview')} className={tabClass('preview')}>PREVIEW</button>
        <button onClick={() => onTabChange('terminal')} className={tabClass('terminal')}>
          TERMINAL
          {termSuccess === false && (
            <span className="ml-1.5 inline-block w-1.5 h-1.5 rounded-full bg-stellar-red" />
          )}
        </button>
        {showDeploy && (
          <button onClick={() => onTabChange('deploy')} className={tabClass('deploy')}>DEPLOY</button>
        )}
        {showEnvironment && (
          <button onClick={() => onTabChange('environment')} className={tabClass('environment')}>ENVIRONMENT</button>
        )}
        {showSchedule && (
          <button onClick={() => onTabChange('schedule')} className={tabClass('schedule')}>SCHEDULE</button>
        )}
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
      <div className="flex-1 min-h-0 bg-void overflow-auto">
        {activeTab === 'dag' && <DagView key={dagKey} />}
        {activeTab === 'preview' && <ResultsPreview key={previewModel + dagKey} modelName={previewModel} />}
        {activeTab === 'terminal' && (
          <TerminalPanel output={termOutput} success={termSuccess} />
        )}
        {activeTab === 'deploy' && showDeploy && (
          <DeployPanel onReport={onReport} />
        )}
        {activeTab === 'environment' && showEnvironment && (
          <EnvironmentPanel onReport={onReport} />
        )}
        {activeTab === 'schedule' && showSchedule && (
          <SchedulePanel onReport={onReport} />
        )}
      </div>
    </div>
  )
}
