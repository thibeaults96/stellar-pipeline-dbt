const API = '/api'

async function post(path: string, body?: unknown) {
  const res = await fetch(`${API}${path}`, {
    method: 'POST',
    ...(body !== undefined ? {
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    } : {}),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

async function get(path: string) {
  const res = await fetch(`${API}${path}`)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

export interface Objective {
  id: string; label: string; hint: string; passed: boolean; reason: string | null
}

export interface NarrativeEvent {
  id: string; character: string; message: string; priority: string
}

export interface ActionReport {
  dbtOutput: string; dbtSuccess: boolean; objectives: Objective[]
  newlyCompleted: string[]; narratives: NarrativeEvent[]
  levelComplete: boolean; badge: { id: string; emoji: string; name: string } | null; xpEarned: number
}

export interface GameStatus {
  currentLevel: number; totalXP: number
  earnedBadges: { id: string; emoji: string; name: string }[]
  completedLevels: number[]; runCount: number; testCount: number
  level: { id: number; title: string; subtitle: string }
  objectives: Objective[]
}

export interface FileEntry { path: string; locked: boolean }
export interface FileContent { path: string; content: string; locked: boolean }

export interface SourceEntry { name: string; rowCount: number }
export interface SourcePreview {
  name: string; columns: string[]
  rows: Record<string, string | number | boolean | null>[]; totalRows: number
}

export interface GitState {
  branch: string; staged: boolean; committed: boolean; commit_message: string
  pr_opened: boolean; ci_passing: boolean; merged: boolean
}

export interface ScheduleState {
  kind: string; expression: string
  commands: string[]; environment_name: string
  run_count: number; last_run_output: string
}

export interface EnvironmentState {
  name: string; git_branch: string
  target_schema: string; threads: number
  dbt_version: string
}

export interface EnvironmentSetRequest {
  name?: string; git_branch?: string
  target_schema?: string; threads?: number
  dbt_version?: string
}

export interface ScheduleSetRequest {
  kind?: string; expression?: string
  commands?: string[]; environment_name?: string
}

export const api = {
  getStatus: (): Promise<GameStatus> => get('/status'),
  startLevel: (id: number): Promise<ActionReport> => post(`/start/${id}`),
  seed: (): Promise<ActionReport> => post('/seed'),
  deps: (): Promise<ActionReport> => post('/deps'),
  run: (): Promise<ActionReport> => post('/run'),
  test: (): Promise<ActionReport> => post('/test'),
  build: (): Promise<ActionReport> => post('/build'),
  snapshot: (): Promise<ActionReport> => post('/snapshot'),
  freshness: (): Promise<ActionReport> => post('/freshness'),
  reset: (): Promise<ActionReport> => post('/reset'),
  listFiles: (): Promise<FileEntry[]> => get('/files'),
  getFile: (path: string): Promise<FileContent> => get(`/files/${path}`),
  saveFile: async (path: string, content: string) => {
    const res = await fetch(`${API}/files/${path}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail || `Save failed: ${res.status}`)
    }
  },
  listSources: (): Promise<SourceEntry[]> => get('/sources'),
  previewSource: (name: string): Promise<SourcePreview> => get(`/sources/${name}`),
  getManifest: () => get('/manifest'),
  previewModel: (name: string): Promise<SourcePreview> => get(`/preview/${name}`),
  // Deploy (L7) — simulated git promotion flow.
  getGit: (): Promise<GitState> => get('/git'),
  gitStage: (): Promise<ActionReport> => post('/git/stage'),
  gitCommit: (message: string): Promise<ActionReport> => post('/git/commit', { message }),
  gitOpenPr: (): Promise<ActionReport> => post('/git/pr'),
  gitMerge: (): Promise<ActionReport> => post('/git/merge'),
  // Environment (L8) — simulated production environment config.
  getEnv: (): Promise<EnvironmentState> => get('/env'),
  setEnv: (body: EnvironmentSetRequest): Promise<ActionReport> => post('/env', body),
  // Schedule (L9) — simulated job-scheduling (job = commands + env + schedule).
  getSchedule: (): Promise<ScheduleState> => get('/schedule'),
  setSchedule: (body: ScheduleSetRequest): Promise<ActionReport> => post('/schedule', body),
  triggerSchedule: (): Promise<ActionReport> => post('/schedule/trigger'),
}
