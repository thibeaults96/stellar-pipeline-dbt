'use client'

import { useState, useEffect, useCallback } from 'react'
import { api, type EnvironmentState, type ActionReport } from '@/hooks/useGameApi'

const DBT_VERSIONS = ['1.7', '1.8', '1.9', '1.10', '1.11']

/**
 * L8 — Set Up Production Environment.
 * The dbt platform's deployment environment maps roughly to:
 *   name + warehouse-target + target-schema + threads + dbt-version + vars
 * We expose those fields with light validation. The actual DuckDB warehouse
 * the runner talks to is fixed — this is metadata the Schedule level points
 * jobs at, mirroring how real platform jobs work.
 */
export default function EnvironmentPanel({ onReport }: { onReport: (r: ActionReport) => void }) {
  const [env, setEnv] = useState<EnvironmentState | null>(null)
  const [draft, setDraft] = useState<EnvironmentState | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const e = await api.getEnv()
      setEnv(e)
      setDraft(e)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load environment')
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const save = useCallback(async (patch: Partial<EnvironmentState>) => {
    setBusy(true); setError(null)
    try {
      const r = await api.setEnv(patch)
      onReport(r)
      await refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setBusy(false)
    }
  }, [onReport, refresh])

  if (!env || !draft) return <div className="p-4 text-stellar-text-dim font-mono-tech text-sm">loading…</div>

  const dirty = (
    draft.name !== env.name ||
    draft.git_branch !== env.git_branch ||
    draft.target_schema !== env.target_schema ||
    draft.threads !== env.threads ||
    draft.dbt_version !== env.dbt_version
  )

  return (
    <div className="p-4 font-exo text-sm h-full overflow-auto">
      <div className="mb-3 flex items-baseline gap-3 flex-wrap">
        <div className="font-orbitron text-accent tracking-wider text-sm">ENVIRONMENT // DEPLOYMENT TARGET</div>
        {env.name && (
          <div className="font-mono-tech text-xs text-stellar-text-dim">
            current: <span className="text-stellar-amber">{env.name}</span>
            {' @ '}<span className="text-stellar-text">{env.git_branch || '(no branch)'}</span>
            {' · '}<span className="text-stellar-text">{env.target_schema || '(no schema)'}</span>
            {' · '}<span className="text-stellar-text-dim">{env.threads || '?'} threads</span>
            {' · '}<span className="text-stellar-text-dim">dbt {env.dbt_version || '?'}</span>
          </div>
        )}
      </div>

      {error && (
        <div className="mb-3 p-2 bg-stellar-red/20 border border-stellar-red text-stellar-red font-mono-tech text-xs rounded">
          {error}
        </div>
      )}

      <div className="mb-3 p-3 bg-deep/40 border border-panel-border rounded text-stellar-text-dim text-xs leading-relaxed">
        An <span className="text-stellar-text">environment</span> packages everything dbt needs to run against a specific warehouse target: connection, schema, parallelism, dbt version. In production you typically have <span className="text-stellar-amber">at least two</span> — a development environment where engineers write models against their own schema, and a deployment environment where scheduled jobs run against shared production tables.
      </div>

      <Field label="Environment name" hint="Convention: capitalize, no spaces. The job in the next level will point here by name.">
        <input
          type="text"
          value={draft.name}
          onChange={e => setDraft({ ...draft, name: e.target.value })}
          placeholder="Production"
          className="w-full px-2 py-1 bg-deep border border-panel-border text-stellar-text font-mono-tech text-xs rounded"
        />
      </Field>

      <Field label="Git branch" hint="The branch this environment builds from. Prod usually tracks `main` — the same branch you merged into last level. Dev environments typically point at long-lived branches like `develop`, or per-engineer branches.">
        <input
          type="text"
          value={draft.git_branch}
          onChange={e => setDraft({ ...draft, git_branch: e.target.value })}
          placeholder="main"
          className="w-full px-2 py-1 bg-deep border border-panel-border text-stellar-text font-mono-tech text-xs rounded"
        />
      </Field>

      <Field label="Target schema" hint="The schema dbt writes models into. Convention: prefix with environment so prod tables can't collide with dev.">
        <input
          type="text"
          value={draft.target_schema}
          onChange={e => setDraft({ ...draft, target_schema: e.target.value })}
          placeholder="prod_helios"
          className="w-full px-2 py-1 bg-deep border border-panel-border text-stellar-text font-mono-tech text-xs rounded"
        />
      </Field>

      <Field label="Threads" hint="How many models dbt builds in parallel. 4–8 is normal in prod. More threads ≠ faster if the warehouse can't keep up.">
        <input
          type="number"
          min={1}
          max={32}
          value={draft.threads || ''}
          onChange={e => setDraft({ ...draft, threads: parseInt(e.target.value || '0', 10) || 0 })}
          placeholder="4"
          className="w-full px-2 py-1 bg-deep border border-panel-border text-stellar-text font-mono-tech text-xs rounded"
        />
      </Field>

      <Field label="dbt version" hint="In real deployments you pin a specific version so your prod environment doesn't unexpectedly upgrade on you. Newer ≠ better mid-cycle.">
        <select
          value={draft.dbt_version}
          onChange={e => setDraft({ ...draft, dbt_version: e.target.value })}
          className="w-full px-2 py-1 bg-deep border border-panel-border text-stellar-text font-mono-tech text-xs rounded"
        >
          <option value="">(pick a version)</option>
          {DBT_VERSIONS.map(v => <option key={v} value={v}>dbt {v}</option>)}
        </select>
      </Field>

      <div className="mt-3 flex gap-2">
        <button
          disabled={!dirty || busy || !draft.name || !draft.git_branch || !draft.target_schema || !draft.threads || !draft.dbt_version}
          onClick={() => save({
            name: draft.name,
            git_branch: draft.git_branch,
            target_schema: draft.target_schema,
            threads: draft.threads,
            dbt_version: draft.dbt_version,
          })}
          className="px-3 py-1.5 font-mono-tech text-xs border border-accent text-accent rounded hover:bg-accent hover:text-void disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-accent transition-colors"
        >
          {dirty ? 'Save environment' : 'saved ✓'}
        </button>
      </div>

    </div>
  )
}

function Field({ label, hint, children }: { label: string; hint: string; children: React.ReactNode }) {
  return (
    <div className="mb-3">
      <label className="block font-mono-tech text-xs text-stellar-text mb-1">{label}</label>
      <div className="mb-1 text-stellar-text-dim text-[11px] leading-relaxed">{hint}</div>
      {children}
    </div>
  )
}
