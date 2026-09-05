const BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000"

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`)
  if (!response.ok) throw new Error(`${path}: ${response.status}`)
  return response.json() as Promise<T>
}

async function post<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE}${path}`, { method: "POST" })
  if (!response.ok) throw new Error(`${path}: ${response.status}`)
  return response.json() as Promise<T>
}

export const api = {
  status: () => get<import("./types").Status>("/api/status"),
  scenarios: () => get<import("./types").ScenarioReport[]>("/api/scenarios"),
  scenario: (id: string) => get<import("./types").ScenarioReport>(`/api/scenarios/${id}`),
  pairs: (id: string) => get<{ scenario: string; pairs: import("./types").PairFinding[] }>(`/api/pairs?sid=${id}`),
  observations: (target: string, days = 90) =>
    get<{ target: string; days: number; count: number; observations: import("./types").ObservationRow[] }>(
      `/api/observations?target=${target}&days=${days}`
    ),
  loopEvents: (after = 0, limit = 100) =>
    get<{ events: import("./types").LoopEvent[] }>(`/api/loop/events?after=${after}&limit=${limit}`),
  loopStart: () => post<{ running: boolean }>("/api/loop/start"),
  loopStop: () => post<{ running: boolean }>("/api/loop/stop"),
  verify: () => post<import("./types").LoopEvent>("/api/verify"),
}