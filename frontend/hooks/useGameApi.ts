const API = '/api'

async function post(path: string) {
  const res = await fetch(`${API}${path}`, { method: 'POST' })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed: ${res.status}`)
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

export const api = {
  getStatus: (): Promise<GameStatus> => get('/status'),
  startLevel: (id: number): Promise<ActionReport> => post(`/start/${id}`),
  run: (): Promise<ActionReport> => post('/run'),
  test: (): Promise<ActionReport> => post('/test'),
  build: (): Promise<ActionReport> => post('/build'),
  snapshot: (): Promise<ActionReport> => post('/snapshot'),
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
}
