'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { api, type GameStatus, type ActionReport, type FileEntry, type SourceEntry, type SourcePreview, type NarrativeEvent, type Objective, type Quiz } from '@/hooks/useGameApi'
import StatusBar from './StatusBar'
import FileTree from './FileTree'
import CodeEditor from './CodeEditor'
import DataPreview from './DataPreview'
import ObjectivePanel from './ObjectivePanel'
import NarrativePanel from './NarrativePanel'
import NarrativeToast, { type ToastEntry } from './NarrativeToast'
import LevelComplete from './LevelComplete'
import QuizModal from './QuizModal'
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
  // Hold the level-complete payload here while end-of-level transmissions are
  // still in the toast queue, so the modal doesn't pop over the closing comms.
  const [pendingLevelComplete, setPendingLevelComplete] = useState<{ badge: { emoji: string; name: string }; xp: number } | null>(null)
  const [dagKey, setDagKey] = useState(0)
  const [previewModel, setPreviewModel] = useState('stg_shipments')
  const [bottomTab, setBottomTab] = useState<import('./BottomPane').Tab>('dag')
  const [toasts, setToasts] = useState<ToastEntry[]>([])
  const toastKeyRef = useRef(0)
  // Quiz shown between levels — populated when the player clicks Next Mission
  // on LevelComplete. `pendingNextLevel` is the level we'll load once the
  // player clicks Continue on the quiz.
  const [activeQuiz, setActiveQuiz] = useState<Quiz | null>(null)
  const [pendingNextLevel, setPendingNextLevel] = useState<number | null>(null)

  const pushToasts = useCallback((events: NarrativeEvent[]) => {
    if (!events.length) return
    setToasts(prev => [
      ...prev,
      ...events.map(n => ({ key: ++toastKeyRef.current, narrative: n })),
    ])
  }, [])

  const dismissToast = useCallback((key: number) => {
    setToasts(prev => prev.filter(t => t.key !== key))
  }, [])

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
    setPendingLevelComplete(null)
    setActiveQuiz(null)
    setPendingNextLevel(null)
    // Deploy / Environment / Schedule levels surface their dedicated tab on
    // entry so the player doesn't have to discover the UI affordance.
    if (levelId === 7) setBottomTab('deploy')
    else if (levelId === 8) setBottomTab('environment')
    else if (levelId === 9) setBottomTab('schedule')
    else setBottomTab('dag')
    // Clear any leftover toasts before queuing this level's intro narratives.
    setToasts([])
    pushToasts(report.narratives)
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
      // Prefer an unlocked .sql, but fall back to .yml/.yaml so YAML-only
      // levels (L3, L5) don't strand the player on "Select a file to edit".
      const first =
        files.find(f => !f.locked && f.path.endsWith('.sql')) ??
        files.find(f => !f.locked && (f.path.endsWith('.yml') || f.path.endsWith('.yaml')))
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
    if (report.narratives.length) {
      setNarratives(prev => [...prev, ...report.narratives])
      pushToasts(report.narratives)
    }
    if (report.levelComplete && report.badge) {
      const payload = { badge: report.badge, xp: report.xpEarned }
      // If there are end-of-level transmissions to play, park the modal
      // payload and let the toast-queue effect promote it once the player
      // has clicked through the comms. Otherwise show it immediately.
      if (report.narratives.length > 0) {
        setPendingLevelComplete(payload)
      } else {
        setLevelComplete(payload)
      }
    }
    setDagKey(k => k + 1)
    const s = await api.getStatus()
    setStatus(s)
  }, [pushToasts])

  // Promote the parked level-complete payload to the visible modal once the
  // end-of-level toast queue has drained.
  useEffect(() => {
    if (pendingLevelComplete && toasts.length === 0) {
      setLevelComplete(pendingLevelComplete)
      setPendingLevelComplete(null)
    }
  }, [pendingLevelComplete, toasts.length])

  const handleRun = useCallback(async () => {
    setIsRunning(true)
    setBottomTab('terminal')
    try {
      const r = await api.run()
      setTermOutput(r.dbtOutput); setTermSuccess(r.dbtSuccess)
      await handleReport(r)
      // Show the lineage on success so the user sees the pipeline turn green;
      // keep terminal visible on failure so they can read the error.
      if (r.dbtSuccess) setBottomTab('dag')
    } finally { setIsRunning(false) }
  }, [handleReport])

  const handleTest = useCallback(async () => {
    setIsRunning(true)
    setBottomTab('terminal')
    try {
      const r = await api.test()
      setTermOutput(r.dbtOutput); setTermSuccess(r.dbtSuccess)
      await handleReport(r)
    } finally { setIsRunning(false) }
  }, [handleReport])

  const handleBuild = useCallback(async () => {
    setIsRunning(true)
    setBottomTab('terminal')
    try {
      const r = await api.build()
      setTermOutput(r.dbtOutput); setTermSuccess(r.dbtSuccess)
      await handleReport(r)
      if (r.dbtSuccess) setBottomTab('dag')
    } finally { setIsRunning(false) }
  }, [handleReport])

  const handleSnapshot = useCallback(async () => {
    setIsRunning(true)
    setBottomTab('terminal')
    try {
      const r = await api.snapshot()
      setTermOutput(r.dbtOutput); setTermSuccess(r.dbtSuccess)
      await handleReport(r)
    } finally { setIsRunning(false) }
  }, [handleReport])

  const handleFreshness = useCallback(async () => {
    setIsRunning(true)
    setBottomTab('terminal')
    try {
      const r = await api.freshness()
      setTermOutput(r.dbtOutput); setTermSuccess(r.dbtSuccess)
      await handleReport(r)
    } finally { setIsRunning(false) }
  }, [handleReport])

  const handleSeed = useCallback(async () => {
    setIsRunning(true)
    setBottomTab('terminal')
    try {
      const r = await api.seed()
      setTermOutput(r.dbtOutput); setTermSuccess(r.dbtSuccess)
      await handleReport(r)
    } finally { setIsRunning(false) }
  }, [handleReport])

  const handleDeps = useCallback(async () => {
    setIsRunning(true)
    setBottomTab('terminal')
    try {
      const r = await api.deps()
      setTermOutput(r.dbtOutput); setTermSuccess(r.dbtSuccess)
      await handleReport(r)
    } finally { setIsRunning(false) }
  }, [handleReport])

  const handleReset = useCallback(async () => {
    setLevelComplete(null)
    const currentLevel = status?.level?.id ?? 1
    await loadLevel(currentLevel)
  }, [status, loadLevel])

  // When the player clicks Next Mission on LevelComplete: dismiss the modal,
  // fetch the just-finished level's quiz, and either show it (if there are
  // questions) or skip straight to loading the next level.
  const handleAdvanceLevel = useCallback(async (finishedLevelId: number, nextLevelId: number) => {
    setLevelComplete(null)
    try {
      const quiz = await api.getQuiz(finishedLevelId)
      if (quiz.questions.length > 0) {
        setActiveQuiz(quiz)
        setPendingNextLevel(nextLevelId)
        return
      }
    } catch {
      // Quiz fetch failure shouldn't block progression — fall through to load.
    }
    await loadLevel(nextLevelId)
  }, [loadLevel])

  const dismissQuizAndAdvance = useCallback(async () => {
    const next = pendingNextLevel
    setActiveQuiz(null)
    setPendingNextLevel(null)
    if (next !== null) await loadLevel(next)
  }, [pendingNextLevel, loadLevel])

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

  const language = activeFile.endsWith('.yml') || activeFile.endsWith('.yaml')
    ? 'yaml'
    : activeFile.endsWith('.md')
      ? 'markdown'
      : activeFile.endsWith('.csv')
        ? 'plaintext'
        : 'sql'

  return (
    <div className="h-screen w-screen flex flex-col bg-void overflow-hidden">
      <StatusBar
        status={status}
        isRunning={isRunning}
        onSeed={handleSeed}
        onDeps={handleDeps}
        onRun={handleRun}
        onTest={handleTest}
        onBuild={handleBuild}
        onSnapshot={handleSnapshot}
        onFreshness={handleFreshness}
        onReset={handleReset}
        onSelectLevel={loadLevel}
      />

      {/* dbt-Studio-style three-column layout:
          Left  = file tree (browser).
          Center = editor on top, lineage/preview/terminal tabs on bottom.
          Right = comms + objectives (mission context). */}
      <div className="flex-1 grid grid-cols-[220px_1fr_320px] overflow-hidden">
        {/* Left: file tree */}
        <div className="border-r border-panel-border flex flex-col overflow-hidden">
          <FileTree files={files} sources={sources} activeFile={activeFile}
            onSelect={openFile} onPreviewSource={openSourcePreview} />
        </div>

        {/* Center: editor + bottom tabs (DAG / Preview / Terminal) */}
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
          <div className="h-[280px] border-t border-panel-border">
            <BottomPane
              dagKey={dagKey}
              previewModel={previewModel}
              onSelectModel={setPreviewModel}
              termOutput={termOutput}
              termSuccess={termSuccess}
              activeTab={bottomTab}
              onTabChange={setBottomTab}
              currentLevel={status?.level?.id ?? 1}
              onReport={handleReport}
            />
          </div>
        </div>

        {/* Right: comms (top) + objectives (bottom) */}
        <div className="border-l border-panel-border flex flex-col overflow-hidden">
          <div className="h-[40%] min-h-[160px] flex-shrink-0 overflow-hidden">
            <NarrativePanel narratives={narratives} />
          </div>
          <div className="flex-1 min-h-0 overflow-y-auto border-t border-panel-border">
            <ObjectivePanel objectives={objectives} newlyCompleted={newlyCompleted} />
          </div>
        </div>
      </div>

      <NarrativeToast toasts={toasts} onDismiss={dismissToast} />

      {activeQuiz && (
        <QuizModal
          quiz={activeQuiz}
          onContinue={dismissQuizAndAdvance}
          onSkip={dismissQuizAndAdvance}
        />
      )}

      {levelComplete && status && (() => {
        const id = status.level.id
        const TOTAL_LEVELS = 13
        // Per-level modal config:
        //  • L9 ends the core arc — offer dbt docs AND the first bonus level.
        //  • L12 is the final level — offer dbt docs only, no Next.
        //  • Everything else — the normal Next Mission button to the next level.
        const isCoreFinale = id === 9
        const isFinal = id === TOTAL_LEVELS
        const onNext = (!isFinal && id < TOTAL_LEVELS)
          ? () => handleAdvanceLevel(id, id + 1)
          : undefined
        const nextLabel = isCoreFinale ? 'Start bonus arc ▶' : undefined
        return (
          <LevelComplete
            badge={levelComplete.badge}
            xpEarned={levelComplete.xp}
            onDismiss={() => setLevelComplete(null)}
            onNext={onNext}
            nextLabel={nextLabel}
            showDocsLink={isCoreFinale || isFinal}
            title={isFinal ? 'TRAINING COMPLETE' : undefined}
            outroMessage={isFinal
              ? "You've cleared the training arc. Take what you've built and apply it to a real project."
              : undefined}
          />
        )
      })()}
    </div>
  )
}
