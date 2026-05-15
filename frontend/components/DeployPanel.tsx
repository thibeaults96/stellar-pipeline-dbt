'use client'

import { useState, useEffect, useCallback } from 'react'
import { api, type GitState, type ActionReport } from '@/hooks/useGameApi'

const STEPS: { id: keyof GitState; label: string; explainer: string }[] = [
  {
    id: 'staged',
    label: 'Stage changes',
    explainer: 'Mark which edited files go into the next commit. In real git: `git add <file>`.',
  },
  {
    id: 'committed',
    label: 'Commit',
    explainer: 'A commit is a labeled snapshot. The message describes what changed and why.',
  },
  {
    id: 'pr_opened',
    label: 'Open pull request',
    explainer: 'A PR asks the owners of `main` to review and accept your commit. CI runs automatically against your branch.',
  },
  {
    id: 'merged',
    label: 'Merge to main',
    explainer: 'Once CI is green and a reviewer approves, you merge — and your changes become part of production.',
  },
]

export default function DeployPanel({ onReport }: { onReport: (r: ActionReport) => void }) {
  const [git, setGit] = useState<GitState | null>(null)
  const [commitMsg, setCommitMsg] = useState('Configure prod materializations and ship to main')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      setGit(await api.getGit())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load git state')
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const run = useCallback(async (action: () => Promise<ActionReport>) => {
    setBusy(true)
    setError(null)
    try {
      const r = await action()
      onReport(r)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Action failed')
    } finally {
      setBusy(false)
    }
  }, [onReport, refresh])

  if (!git) return <div className="p-4 text-stellar-text-dim font-mono-tech text-sm">loading…</div>

  const can = {
    stage: !git.staged,
    commit: git.staged && !git.committed,
    pr: git.committed && !git.pr_opened,
    merge: git.pr_opened && git.ci_passing && !git.merged,
  }

  return (
    <div className="p-4 font-exo text-sm h-full overflow-auto">
      <div className="mb-3 flex items-baseline gap-3">
        <div className="font-orbitron text-accent tracking-wider text-sm">DEPLOY // GIT PROMOTION</div>
        <div className="font-mono-tech text-stellar-text-dim text-xs">
          branch: <span className="text-stellar-amber">{git.branch}</span> → main
        </div>
      </div>

      {error && (
        <div className="mb-3 p-2 bg-stellar-red/20 border border-stellar-red text-stellar-red font-mono-tech text-xs rounded">
          {error}
        </div>
      )}

      {/* Pipeline visualization */}
      <div className="mb-4 flex items-center gap-1 font-mono-tech text-xs">
        {STEPS.map((s, i) => {
          const done = Boolean(git[s.id])
          return (
            <div key={s.id} className="flex items-center gap-1">
              <div className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] ${
                done ? 'bg-stellar-green/20 border-stellar-green text-stellar-green' : 'border-panel-border text-stellar-text-dim'
              }`}>
                {done ? '✓' : i + 1}
              </div>
              <span className={done ? 'text-stellar-text' : 'text-stellar-text-dim'}>{s.label}</span>
              {i < STEPS.length - 1 && (
                <span className={`mx-1 ${done ? 'text-stellar-green' : 'text-stellar-text-dim'}`}>→</span>
              )}
            </div>
          )
        })}
      </div>

      {/* Step 1: Stage */}
      <Section index={1} title="Stage changes" done={git.staged}>
        <p className="text-stellar-text-dim mb-2 text-xs">{STEPS[0].explainer}</p>
        <div className="mb-2 font-mono-tech text-xs text-stellar-text-dim border border-panel-border rounded p-2">
          <div className="text-stellar-text mb-1">Files changed on this branch:</div>
          <div>M  dbt_project.yml</div>
          <div>M  models/sources/helios_sources.yml</div>
          <div>M  models/staging/_stg_shipments.yml</div>
          <div>M  models/marts/_fct_trade_routes.yml</div>
          <div>A  models/_docs.md</div>
        </div>
        <button disabled={!can.stage || busy} onClick={() => run(api.gitStage)}
          className="px-3 py-1 font-mono-tech text-xs border border-accent text-accent rounded hover:bg-accent hover:text-void disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-accent transition-colors">
          {git.staged ? 'staged ✓' : '+ Stage all'}
        </button>
      </Section>

      {/* Step 2: Commit */}
      <Section index={2} title="Commit" done={git.committed}>
        <p className="text-stellar-text-dim mb-2 text-xs">{STEPS[1].explainer}</p>
        <input
          type="text"
          value={git.committed ? git.commit_message : commitMsg}
          onChange={e => setCommitMsg(e.target.value)}
          disabled={git.committed || !can.commit || busy}
          className="w-full mb-2 px-2 py-1 bg-deep border border-panel-border text-stellar-text font-mono-tech text-xs rounded disabled:opacity-60"
          placeholder="Commit message"
        />
        <button disabled={!can.commit || busy || !commitMsg.trim()} onClick={() => run(() => api.gitCommit(commitMsg))}
          className="px-3 py-1 font-mono-tech text-xs border border-accent text-accent rounded hover:bg-accent hover:text-void disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-accent transition-colors">
          {git.committed ? 'committed ✓' : 'Commit'}
        </button>
      </Section>

      {/* Step 3: PR */}
      <Section index={3} title="Open pull request" done={git.pr_opened}>
        <p className="text-stellar-text-dim mb-2 text-xs">{STEPS[2].explainer}</p>
        {git.pr_opened && (
          <div className="mb-2 font-mono-tech text-xs border border-panel-border rounded p-2">
            <div className="text-stellar-text-bright">#1 {git.commit_message}</div>
            <div className="text-stellar-text-dim mt-1">{git.branch} → main</div>
            <div className={`mt-1 ${git.ci_passing ? 'text-stellar-green' : 'text-stellar-red'}`}>
              CI: {git.ci_passing ? 'dbt build passing ✓' : 'dbt build failing ✗ — run dbt build until it passes, then re-open'}
            </div>
          </div>
        )}
        <button disabled={!can.pr || busy} onClick={() => run(api.gitOpenPr)}
          className="px-3 py-1 font-mono-tech text-xs border border-accent text-accent rounded hover:bg-accent hover:text-void disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-accent transition-colors">
          {git.pr_opened ? 'PR open ✓' : 'Open PR'}
        </button>
      </Section>

      {/* Step 4: Merge */}
      <Section index={4} title="Merge to main" done={git.merged}>
        <p className="text-stellar-text-dim mb-2 text-xs">{STEPS[3].explainer}</p>
        <button disabled={!can.merge || busy} onClick={() => run(api.gitMerge)}
          className="px-3 py-1 font-mono-tech text-xs border border-stellar-green text-stellar-green rounded hover:bg-stellar-green hover:text-void disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-stellar-green transition-colors">
          {git.merged ? 'merged to main ✓' : 'Merge'}
        </button>
      </Section>
    </div>
  )
}

function Section({ index, title, done, children }: {
  index: number; title: string; done: boolean; children: React.ReactNode
}) {
  return (
    <div className={`mb-3 p-3 rounded border ${done ? 'border-stellar-green/40 bg-stellar-green/5' : 'border-panel-border bg-deep/40'}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-mono-tech ${
          done ? 'bg-stellar-green/20 text-stellar-green border border-stellar-green' : 'bg-deep text-stellar-text-dim border border-panel-border'
        }`}>
          {done ? '✓' : index}
        </span>
        <span className={`font-orbitron text-xs tracking-wider ${done ? 'text-stellar-green' : 'text-stellar-text'}`}>
          {title.toUpperCase()}
        </span>
      </div>
      {children}
    </div>
  )
}
