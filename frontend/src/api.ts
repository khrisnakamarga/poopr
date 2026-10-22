export type Profile = {
  id: string
  email: string
  display_name: string
  avatar_url: string | null
  timezone: string
}

export type PoopLog = {
  id: string
  occurred_at: string
  duration_seconds: number | null
  stool_type: number | null
  urgency: number | null
  notes: string | null
  created_at: string
}

export type MetricPoint = { label: string; value: number }
export type LeaderboardRow = { user_id: string; display_name: string; value: number }
export type Activity = {
  id: string
  display_name: string
  occurred_at: string
  activity_type: string
}

export type PersonalReport = {
  total_count: number
  current_streak_days: number
  average_per_week: number
  daily_counts: MetricPoint[]
  hourly_distribution: MetricPoint[]
}

export type Group = {
  id: string
  name: string
  role: string
  member_count: number
}

export type GroupDashboard = {
  group_id: string
  group_name: string
  member_count: number
  total_count: number
  leaderboards: { most_logs: LeaderboardRow[] }
  hourly_distribution: MetricPoint[]
  recent_activity: Activity[]
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
export const AUTH_MODE = import.meta.env.VITE_AUTH_MODE ?? 'dev'

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message)
  }
}

async function request<T>(path: string, email: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  headers.set('Content-Type', 'application/json')
  if (AUTH_MODE !== 'easy_auth') {
    headers.set('X-User-Email', email)
  }

  const response = await fetch(`${API_BASE_URL}/api/v1${path}`, {
    ...init,
    headers,
  })

  if (response.status === 401 && AUTH_MODE === 'easy_auth') {
    window.location.assign('/auth/google/login')
    throw new ApiError('Redirecting to sign in', 401)
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }))
    throw new ApiError(body.detail ?? 'Request failed', response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json()
}

export const api = {
  profile: (email: string) => request<Profile>('/profile/me', email),
  updateProfile: (email: string, payload: Partial<Profile>) =>
    request<Profile>('/profile/me', email, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
  logs: (email: string) => request<PoopLog[]>('/poop-logs', email),
  createLog: (
    email: string,
    payload: {
      occurred_at: string
      duration_seconds?: number | null
      stool_type?: number | null
      urgency?: number | null
      notes?: string | null
    },
  ) =>
    request<PoopLog>('/poop-logs', email, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  report: (email: string) => request<PersonalReport>('/reports/me', email),
  groups: (email: string) => request<Group[]>('/groups', email),
  createGroup: (email: string, name: string) =>
    request<Group>('/groups', email, { method: 'POST', body: JSON.stringify({ name }) }),
  createInvite: (email: string, groupId: string) =>
    request<{ code: string }>(`/groups/${groupId}/invite-codes`, email, { method: 'POST' }),
  joinGroup: (email: string, code: string) =>
    request<Group>('/groups/join', email, { method: 'POST', body: JSON.stringify({ code }) }),
  groupDashboard: (email: string, groupId: string) =>
    request<GroupDashboard>(`/groups/${groupId}/dashboard`, email),
}

