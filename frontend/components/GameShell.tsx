'use client'

import { useState, useEffect, useCallback } from 'react'
import { api, type GameStatus, type ActionReport, type FileEntry, type SourceEntry, type SourcePreview, type NarrativeEvent, type Objective } from '@/hooks/useGameApi'
import StatusBar from './StatusBar'
import FileTree from './FileTree'
import CodeEditor from './CodeEditor'
import DataPreview from './DataPreview'
import ObjectivePanel from './ObjectivePanel'
import TerminalPanel from './TerminalPanel'
import NarrativePanel from './NarrativePanel'
import LevelComplete from './LevelComplete'
import BottomPane from './BottomPane'

export default function GameShell() {
  const [status, setStatus] = useState<GameStatus | null>(null)
  const [files, setFiles] = useState<FileEntry[]>([])
  const [sources, setSources] = useState<SourceEntry[]>([])
  const [activeFile, setActiveFile] = useState('')
  const [fileContent, setFileContent] = useState('')
  const [fileLocked, setFileLocked] = useState(false)
  const [previewData, setPreviewData] = useState<SourcePreview | null>(null)
  const [termOutput, setTermOutput] = useState('')
  const [termSuccess, setTermSuccess] = useState<boolean | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [narratives, setNarratives] = useState<NarrativeEvent[]>([])
  const [objectives, setObjectives] = useState<Objective[]>([])
  const [newlyCompleted, setNewlyCompleted] = useState<string[]>([])
  const [levelComplete, setLevelComplete] = useState<{ badge: { emoji: string; name: string }; xp: number } | null>(null)
  const [dagKey, setDagKey] = useState(0)
  const [previewModel, setPreviewModel] = useState('stg_shipments')

  // Start Level 1 on mount (player just clicked "Begin Mission")
  const loadLevel = useCallback(async (levelId: number) => {
    const report = await api.startLevel(levelId)
    setNarratives(report.narratives)
    setObjectives(report.objectives)
    setNewlyCompleted([])
    setTermOutput('')
    setTermSuccess(null)
    setPreviewData(null)
    setActiveFile('')
    setFileContent('')
    setFileLocked(false)
    setLevelComplete(null)
    setDagKey(k => k + 1)
    // Await these so the file list is current before auto-open triggers
    const [s, newFiles, newSources] = await Promise.all([
      api.getStatus(),
      api.listFiles(),
      api.listSources(),
    ])
    setStatus(s)
    setFiles(newFiles)
    setSources(newSources)
  }, [])

  useEffect(() => {
    loadLevel(1)
  }, [loadLevel])

  const openFile = useCallback(async (path: string) => {
    setPreviewData(null)
    try {
      const f = await api.getFile(path)
      setActiveFile(f.path); setFileContent(f.content); setFileLocked(f.locked)
    } catch {
      // File may not exist after level switch — clear and let auto-open pick a new file
      setActiveFile('')
      setFileContent('')
    }
  }, [])

  const openSourcePreview = useCallback(async (name: string) => {
    const data = await api.previewSource(name)
    setPreviewData(data)
    setActiveFile('')
  }, [])

  useEffect(() => {
    if (files.length > 0 && !activeFile && !previewData) {
      const first = files.find(f => !f.locked && f.path.endsWith('.sql'))
      if (first) openFile(first.path)
    }
  }, [files, activeFile, previewData, openFile])

  const saveFile = useCallback(async (content: string) => {
    if (!activeFile || fileLocked) return
    try {
      await api.saveFile(activeFile, content)
      setFileContent(content)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Save failed'
      setTermOutput(prev => prev + `\n[SAVE ERROR] ${msg}`)
      setTermSuccess(false)
    }
  }, [activeFile, fileLocked])

  const handleReport = useCallback(async (report: ActionReport) => {
    setObjectives(report.objectives)
    setNewlyCompleted(report.newlyCompleted)
    if (report.narratives.length) setNarratives(prev => [...prev, ...report.narratives])
    if (report.levelComplete && report.badge) setLevelComplete({ badge: report.badge, xp: report.xpEarned })
    setDagKey(k => k + 1)
    const s = await api.getStatus()
    setStatus(s)
  }, [])

  const handleRun = useCallback(async () => {
    setIsRunning(true)
    try {
      const r = await api.run()
      setTermOutput(r.dbtOutput); setTermSuccess(r.dbtSuccess)
      await handleReport(r)
    } finally { setIsRunning(false) }
  }, [handleReport])

  const handleTest = useCallback(async () => {
    setIsRunning(true)
    try {
      const r = await api.test()
      setTermOutput(r.dbtOutput); setTermSuccess(r.dbtSuccess)
      await handleReport(r)
    } finally { setIsRunning(false) }
  }, [handleReport])

  const handleBuild = useCallback(async () => {
    setIsRunning(true)
    try {
      const r = await api.build()
      setTermOutput(r.dbtOutput); setTermSuccess(r.dbtSuccess)
      await handleReport(r)
    } finally { setIsRunning(false) }
  }, [handleReport])

  const handleSnapshot = useCallback(async () => {
    setIsRunning(true)
    try {
      const r = await api.snapshot()
      setTermOutput(r.dbtOutput); setTermSuccess(r.dbtSuccess)
      await handleReport(r)
    } finally { setIsRunning(false) }
  }, [handleReport])

  const handleReset = useCallback(async () => {
    setLevelComplete(null)
    const currentLevel = status?.level?.id ?? 1
    await loadLevel(currentLevel)
  }, [status, loadLevel])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); handleRun() }
      if (e.key === 'Escape' && previewData) { setPreviewData(null) }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [handleRun, previewData])

  if (!status) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-void">
        <div className="text-center">
          <div className="font-orbitron text-accent text-2xl mb-2 tracking-widest">
            STELLAR <span className="text-stellar-text-dim">{"//"}</span> PIPELINE
          </div>
          <div className="font-exo text-stellar-text-dim text-sm">Connecting to server...</div>
        </div>
      </div>
    )
  }

  const language = activeFile.endsWith('.yml') || activeFile.endsWith('.yaml') ? 'yaml' : 'sql'

  return (
    <div className="h-screen w-screen flex flex-col bg-void overflow-hidden">
      <StatusBar status={status} isRunning={isRunning} onRun={handleRun} onReset={handleReset} onSelectLevel={loadLevel} />

      <div className="flex-1 grid grid-cols-[220px_1fr_340px] overflow-hidden">
        {/* Left sidebar: files + objectives */}
        <div className="border-r border-panel-border flex flex-col overflow-hidden">
          <div className="flex-1 min-h-0 overflow-y-auto border-b border-panel-border">
            <FileTree files={files} sources={sources} activeFile={activeFile}
              onSelect={openFile} onPreviewSource={openSourcePreview} />
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto">
            <ObjectivePanel objectives={objectives} newlyCompleted={newlyCompleted} />
          </div>
        </div>

        {/* Center: editor + DAG */}
        <div className="flex flex-col overflow-hidden">
          {previewData ? (
            <div className="flex-1 min-h-0">
              <DataPreview data={previewData} onClose={() => setPreviewData(null)} />
            </div>
          ) : activeFile ? (
            <>
              <div className="flex items-center bg-deep border-b border-panel-border overflow-x-auto">
                {files.map(f => {
                  const basename = f.path.split('/').pop()!
                  const isActive = f.path === activeFile
                  return (
                    <button key={f.path} onClick={() => openFile(f.path)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-mono-tech border-r border-panel-border whitespace-nowrap transition-colors
                        ${isActive
                          ? 'bg-void text-stellar-text-bright border-t-2 border-t-accent'
                          : 'text-stellar-text-dim hover:text-stellar-text hover:bg-panel border-t-2 border-t-transparent'}`}>
                      {f.locked && <span className="text-stellar-amber text-[10px]">🔒</span>}
                      {basename}
                    </button>
                  )
                })}
              </div>
              <div className="flex-1 min-h-0">
                <CodeEditor filePath={activeFile} content={fileContent} language={language} readOnly={fileLocked} onSave={saveFile} />
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-stellar-text-dim font-exo">
              Select a file to edit
            </div>
          )}
          {/* Bottom pane: DAG / Preview toggle */}
          <div className="h-[180px] border-t border-panel-border">
            <BottomPane dagKey={dagKey} previewModel={previewModel} onSelectModel={setPreviewModel} />
          </div>
        </div>

        {/* Right: narrative + terminal */}
        <div className="border-l border-panel-border flex flex-col overflow-hidden">
          <div className="max-h-[45%] min-h-[120px] flex-shrink-0 overflow-hidden">
            <NarrativePanel narratives={narratives} />
          </div>
          <div className="flex-1 min-h-0">
            <TerminalPanel output={termOutput} success={termSuccess} isRunning={isRunning}
              onRun={handleRun} onTest={handleTest} onBuild={handleBuild} onSnapshot={handleSnapshot} />
          </div>
        </div>
      </div>

      {levelComplete && (
        <LevelComplete badge={levelComplete.badge} xpEarned={levelComplete.xp} onDismiss={() => setLevelComplete(null)} />
      )}
    </div>
  )
}
