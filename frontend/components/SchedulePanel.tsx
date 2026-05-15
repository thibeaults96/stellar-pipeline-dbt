'use client'

import { useState, useEffect, useCallback } from 'react'
import { api, type ScheduleState, type EnvironmentState, type ActionReport } from '@/hooks/useGameApi'

type Kind = 'manual' | 'interval' | 'cron' | 'on_merge'

const KINDS: { id: Kind; label: string; tagline: string; explainer: string; needsExpression: boolean; placeholder: string }[] = [
  {
    id: 'manual',
    label: 'Manual',
    tagline: 'A human clicks Run',
    explainer: "Pipeline only runs when someone presses a button. Fine for dev or one-off analyses — terrible for prod (you'll forget).",
    needsExpression: false,
    placeholder: '',
  },
  {
    id: 'interval',
    label: 'Interval',
    tagline: 'Every N minutes / hours',
    explainer: 'Runs on a fixed cadence. Simplest possible scheduler — but it doesn\'t know what time it is, so 3am refreshes still happen.',
    needsExpression: true,
    placeholder: '6h',
  },
  {
    id: 'cron',
    label: 'Cron',
    tagline: 'Calendar-aware (m h dom mon dow)',
    explainer: 'A 5-field expression: minute, hour, day-of-month, month, day-of-week. `*` means "every". So `0 6 * * 1-5` runs at 6:00 on weekdays. Most production schedulers default to this.',
    needsExpression: true,
    placeholder: '0 */6 * * *',
  },
  {
    id: 'on_merge',
    label: 'On-merge',
    tagline: 'Triggered by CI/CD',
    explainer: 'Fires whenever a PR lands on main. Tightly couples the refresh to deployment. Elegant for small projects, painful at scale (every code change triggers a full build).',
    needsExpression: false,
    placeholder: '',
  },
]

const KNOWN_COMMANDS = [
  'dbt seed',
  'dbt run',
  'dbt test',
  'dbt build',
  'dbt source freshness',
  'dbt snapshot',
  'dbt compile',
]

function nextRunsPreview(kind: Kind, expr: string): string[] {
  if (kind === 'manual') return ['(runs only when you click)']
  if (kind === 'on_merge') return ['(runs whenever a PR merges to main)']
  if (kind === 'interval') {
    const m = expr.trim().match(/^(\d+)\s*([mhd]?)$/i)
    if (!m) return ['(set an interval like `6h`, `30m`, `1d`)']
    const n = parseInt(m[1], 10)
    const unit = (m[2] || 'h').toLowerCase()
    const ms = n * (unit === 'm' ? 60_000 : unit === 'd' ? 86_400_000 : 3_600_000)
    const now = Date.now()
    return Array.from({ length: 4 }, (_, i) => new Date(now + ms * (i + 1)).toISOString().replace('T', ' ').replace(/\..*/, ' UTC'))
  }
  if (kind === 'cron') {
    const fields = expr.trim().split(/\s+/)
    if (fields.length !== 5) return ['(cron expression should have 5 fields: m h dom mon dow)']
    return ['(next run computed by the scheduler at deploy time)']
  }
  return []
}

export default function SchedulePanel({ onReport }: { onReport: (r: ActionReport) => void }) {
  const [sched, setSched] = useState<ScheduleState | null>(null)
  const [env, setEnv] = useState<EnvironmentState | null>(null)
  // `null` until the player picks a kind — keeps section 3 unbiased instead
  // of nudging them toward Interval just because that's where we'd default.
  const [kind, setKind] = useState<Kind | null>(null)
  const [expression, setExpression] = useState('')
  const [commands, setCommands] = useState('dbt seed\ndbt build')
  const [envName, setEnvName] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Pull the latest server-side schedule + env. Does NOT touch the local form
  // state — saving one section (e.g. environment) shouldn't blow away another
  // section's in-progress edits (commands typed but not yet saved, etc.).
  const refresh = useCallback(async () => {
    try {
      const [s, e] = await Promise.all([api.getSchedule(), api.getEnv()])
      setSched(s)
      setEnv(e)
      return { sched: s, env: e }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
      return null
    }
  }, [])

  // Initial-load sync: only runs once per mount. Seeds the local form fields
  // from whatever the server already has so a returning player picks up where
  // they left off. After that, the form state is owned by the user — refresh()
  // never overwrites it.
  useEffect(() => {
    let mounted = true
    ;(async () => {
      const result = await refresh()
      if (!mounted || !result) return
      const { sched: s, env: e } = result
      if (s.kind) {
        setKind(s.kind as Kind)
        setExpression(s.expression)
      }
      if (s.commands.length > 0) setCommands(s.commands.join('\n'))
      // Only pre-fill the dropdown if the player has already pointed the job
      // somewhere — don't auto-select the only available env, force a
      // deliberate pick so they learn the "job → environment" wiring.
      if (s.environment_name) setEnvName(s.environment_name)
    })()
    return () => { mounted = false }
  }, [refresh])

  const save = useCallback(async (patch: Partial<ScheduleState>) => {
    setBusy(true); setError(null)
    try {
      const r = await api.setSchedule({
        kind: patch.kind,
        expression: patch.expression,
        commands: patch.commands,
        environment_name: patch.environment_name,
      })
      onReport(r)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setBusy(false)
    }
  }, [onReport, refresh])

  const trigger = useCallback(async () => {
    setBusy(true); setError(null)
    try {
      const r = await api.triggerSchedule()
      onReport(r)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Trigger failed')
    } finally {
      setBusy(false)
    }
  }, [onReport, refresh])

  if (!sched || !env) return <div className="p-4 text-stellar-text-dim font-mono-tech text-sm">loading…</div>

  const meta = kind ? KINDS.find(k => k.id === kind) ?? null : null
  const exprToSubmit = meta?.needsExpression ? expression : ''
  const cmdsList = commands.split('\n').map(c => c.trim()).filter(Boolean)
  const envOptions = env.name ? [env.name] : []

  return (
    <div className="p-4 font-exo text-sm h-full overflow-auto">
      <div className="mb-3 flex items-baseline gap-3 flex-wrap">
        <div className="font-orbitron text-accent tracking-wider text-sm">SCHEDULE // JOB DEFINITION</div>
        {sched.kind && (
          <div className="font-mono-tech text-xs text-stellar-text-dim">
            <span className="text-stellar-amber">{sched.kind}</span>
            {sched.expression && <> ({sched.expression})</>}
            {sched.environment_name && <> → <span className="text-stellar-text">{sched.environment_name}</span></>}
            {' · '}
            <span className="text-stellar-text">{sched.run_count} run{sched.run_count === 1 ? '' : 's'}</span>
          </div>
        )}
      </div>

      {error && (
        <div className="mb-3 p-2 bg-stellar-red/20 border border-stellar-red text-stellar-red font-mono-tech text-xs rounded">
          {error}
        </div>
      )}

      {/* ── 1. Environment ─────────────────────────────────────────── */}
      <Section title="1. Target environment">
        <p className="text-stellar-text-dim text-[11px] mb-2 leading-relaxed">
          A job runs <span className="text-stellar-text">in</span> an environment — the warehouse target, schema, threads, and dbt version configured in the previous level. Without an environment, the scheduler has no idea where to point.
        </p>
        {envOptions.length === 0 ? (
          <div className="text-stellar-red font-mono-tech text-xs">
            No environment configured. Go back to the previous level and set one up in the ENVIRONMENT tab.
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <select
              value={envName}
              onChange={e => setEnvName(e.target.value)}
              className="px-2 py-1 bg-deep border border-panel-border text-stellar-text font-mono-tech text-xs rounded"
            >
              <option value="">(pick one)</option>
              {envOptions.map(n => <option key={n} value={n}>{n}</option>)}
            </select>
            <button
              disabled={!envName || busy || sched.environment_name === envName}
              onClick={() => save({ environment_name: envName })}
              className="px-2 py-1 font-mono-tech text-xs border border-accent text-accent rounded hover:bg-accent hover:text-void disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-accent"
            >
              {sched.environment_name === envName && envName ? 'set ✓' : 'Set environment'}
            </button>
          </div>
        )}
      </Section>

      {/* ── 2. Commands ───────────────────────────────────────────── */}
      <Section title="2. Commands the job runs">
        <p className="text-stellar-text-dim text-[11px] mb-2 leading-relaxed">
          One dbt command per line. The scheduler runs them top to bottom, stopping if anything fails. A typical production job is <span className="font-mono-tech text-stellar-amber">dbt seed</span> → <span className="font-mono-tech text-stellar-amber">dbt build</span> → <span className="font-mono-tech text-stellar-amber">dbt source freshness</span>. dbt build itself is run+test+snapshot in dependency order.
        </p>
        <textarea
          value={commands}
          onChange={e => setCommands(e.target.value)}
          rows={5}
          spellCheck={false}
          className="w-full px-2 py-1 bg-deep border border-panel-border text-stellar-text font-mono-tech text-xs rounded resize-y leading-snug"
          placeholder="dbt seed&#10;dbt build"
        />
        <div className="mt-1 flex flex-wrap gap-1">
          <span className="text-stellar-text-dim text-[10px] font-mono-tech">recognized:</span>
          {KNOWN_COMMANDS.map(c => (
            <code key={c} className="text-[10px] text-stellar-text-dim font-mono-tech">{c}</code>
          ))}
        </div>
        <div className="mt-2 flex gap-2">
          <button
            disabled={busy || cmdsList.length === 0 || JSON.stringify(cmdsList) === JSON.stringify(sched.commands)}
            onClick={() => save({ commands: cmdsList })}
            className="px-2 py-1 font-mono-tech text-xs border border-accent text-accent rounded hover:bg-accent hover:text-void disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-accent"
          >
            {JSON.stringify(cmdsList) === JSON.stringify(sched.commands) && cmdsList.length > 0 ? 'saved ✓' : 'Save commands'}
          </button>
          <span className="text-stellar-text-dim text-[11px] self-center">
            {cmdsList.length} command{cmdsList.length === 1 ? '' : 's'}
          </span>
        </div>
      </Section>

      {/* ── 3. Schedule ──────────────────────────────────────────── */}
      <Section title="3. When it runs">
        <div className="grid grid-cols-2 gap-2 mb-3">
          {KINDS.map(k => {
            const active = kind === k.id
            const isCurrent = sched.kind === k.id
            return (
              <button
                key={k.id}
                onClick={() => setKind(k.id)}
                className={`text-left p-2 rounded border transition-colors ${
                  active
                    ? 'border-accent bg-accent-dim'
                    : 'border-panel-border bg-deep/40 hover:border-stellar-text-dim'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className={`font-orbitron text-xs tracking-wider ${active ? 'text-accent' : 'text-stellar-text'}`}>
                    {k.label.toUpperCase()}
                  </span>
                  {isCurrent && (
                    <span className="font-mono-tech text-[10px] text-stellar-green">● ACTIVE</span>
                  )}
                </div>
                <div className="text-stellar-text-dim font-mono-tech text-[11px]">{k.tagline}</div>
              </button>
            )
          })}
        </div>

        {meta ? (
          <>
            <div className="mb-3 p-3 bg-deep/40 border border-panel-border rounded">
              <div className="font-orbitron text-xs text-stellar-text tracking-wider mb-1">
                {meta.label.toUpperCase()}
              </div>
              <p className="text-stellar-text-dim text-xs leading-relaxed">{meta.explainer}</p>
            </div>

            {meta.needsExpression && (
              <div className="mb-3">
                <label className="block font-mono-tech text-xs text-stellar-text-dim mb-1">
                  {kind === 'cron' ? 'cron expression (m h dom mon dow)' : 'interval (e.g. `6h`, `30m`, `1d`)'}
                </label>
                <input
                  type="text"
                  value={expression}
                  onChange={e => setExpression(e.target.value)}
                  placeholder={meta.placeholder}
                  className="w-full px-2 py-1 bg-deep border border-panel-border text-stellar-text font-mono-tech text-xs rounded"
                />
              </div>
            )}

            <div className="mb-3 p-2 border border-panel-border rounded">
              <div className="font-mono-tech text-[10px] text-stellar-text-dim mb-1 tracking-wider">NEXT RUNS</div>
              {nextRunsPreview(kind!, expression).map((line, i) => (
                <div key={i} className="font-mono-tech text-xs text-stellar-text">{line}</div>
              ))}
            </div>

            <button
              disabled={busy || (sched.kind === kind && sched.expression === exprToSubmit)}
              onClick={() => save({ kind: kind!, expression: exprToSubmit })}
              className="px-3 py-1.5 font-mono-tech text-xs border border-accent text-accent rounded hover:bg-accent hover:text-void disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-accent transition-colors"
            >
              {sched.kind === kind && sched.expression === exprToSubmit ? 'saved ✓' : 'Save schedule'}
            </button>
          </>
        ) : (
          <div className="p-3 bg-deep/20 border border-panel-border border-dashed rounded text-stellar-text-dim text-xs font-mono-tech">
            Pick a schedule kind above to see its details.
          </div>
        )}
      </Section>

      {/* ── 4. Trigger ──────────────────────────────────────────── */}
      <div className="mt-4 pt-3 border-t border-panel-border">
        <button
          disabled={busy || !sched.kind || !sched.environment_name || sched.commands.length === 0}
          onClick={trigger}
          className="px-3 py-1.5 font-mono-tech text-xs border border-stellar-green text-stellar-green rounded hover:bg-stellar-green hover:text-void disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-stellar-green transition-colors"
          title="Run the configured command list as if the scheduler invoked it"
        >
          ▶ Trigger scheduled run
        </button>
        {(!sched.environment_name || sched.commands.length === 0) && (
          <div className="mt-2 text-stellar-text-dim font-mono-tech text-[11px]">
            Pick an environment and add at least one command before you can trigger.
          </div>
        )}
        <div className="mt-2 text-stellar-text-dim font-mono-tech text-[10px]">
          Trigger runs the command list against {sched.environment_name || 'the configured environment'}. In production the platform invokes this on the cadence above.
        </div>
      </div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-4 p-3 rounded border border-panel-border bg-deep/40">
      <div className="font-orbitron text-xs tracking-wider mb-2 text-stellar-text">
        {title.toUpperCase()}
      </div>
      {children}
    </div>
  )
}
