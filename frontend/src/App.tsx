import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  BarChart3,
  Clock3,
  Crown,
  History,
  Home,
  Plus,
  Settings,
  Users,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api, AUTH_MODE, Group, GroupDashboard, PersonalReport, PoopLog, Profile } from './api'

type View = 'log' | 'history' | 'reports' | 'groups' | 'profile'
type LoadState = 'idle' | 'loading' | 'ready' | 'error'

const initialEmail = localStorage.getItem('poopr.email') ?? 'demo@poopr.local'
const usesManagedAuth = AUTH_MODE === 'easy_auth'

const stoolTypes = [
  { value: '1', label: 'Type 1 - hard lumps' },
  { value: '2', label: 'Type 2 - lumpy sausage' },
  { value: '3', label: 'Type 3 - cracked sausage' },
  { value: '4', label: 'Type 4 - smooth sausage' },
  { value: '5', label: 'Type 5 - soft blobs' },
  { value: '6', label: 'Type 6 - mushy' },
  { value: '7', label: 'Type 7 - liquid' },
]

const urgencyLabels: Record<string, string> = {
  '1': 'No rush',
  '2': 'Could wait',
  '3': 'Soon',
  '4': 'Hurry',
  '5': 'Emergency',
}

function localDateTimeValue(date = new Date()) {
  const offset = date.getTimezoneOffset()
  const local = new Date(date.getTime() - offset * 60_000)
  return local.toISOString().slice(0, 16)
}

function formatDateTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(value))
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="empty">
      <p>{title}</p>
      <span>{body}</span>
    </div>
  )
}

export function App() {
  const [view, setView] = useState<View>('log')
  const [email, setEmail] = useState(initialEmail)
  const [profile, setProfile] = useState<Profile | null>(null)
  const [logs, setLogs] = useState<PoopLog[]>([])
  const [report, setReport] = useState<PersonalReport | null>(null)
  const [groups, setGroups] = useState<Group[]>([])
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null)
  const [dashboard, setDashboard] = useState<GroupDashboard | null>(null)
  const [status, setStatus] = useState<LoadState>('idle')
  const [notice, setNotice] = useState('')

  async function refresh(nextEmail = email) {
    setStatus('loading')
    setNotice('')
    try {
      const [profileData, logsData, reportData, groupsData] = await Promise.all([
        api.profile(nextEmail),
        api.logs(nextEmail),
        api.report(nextEmail),
        api.groups(nextEmail),
      ])
      setProfile(profileData)
      setLogs(logsData)
      setReport(reportData)
      setGroups(groupsData)
      const groupId = selectedGroupId ?? groupsData[0]?.id ?? null
      setSelectedGroupId(groupId)
      if (groupId) {
        setDashboard(await api.groupDashboard(nextEmail, groupId))
      } else {
        setDashboard(null)
      }
      setStatus('ready')
    } catch (error) {
      setStatus('error')
      setNotice(error instanceof Error ? error.message : 'Could not reach the API')
    }
  }

  useEffect(() => {
    refresh()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!selectedGroupId) return
    api
      .groupDashboard(email, selectedGroupId)
      .then(setDashboard)
      .catch((error) => setNotice(error instanceof Error ? error.message : 'Dashboard failed'))
  }, [email, selectedGroupId])

  const title = useMemo(() => {
    if (view === 'log') return 'Poopr'
    if (view === 'history') return 'History'
    if (view === 'reports') return 'Reports'
    if (view === 'groups') return 'Groups'
    return 'Profile'
  }, [view])

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">Mobile-first poop stats</span>
          <h1>{title}</h1>
        </div>
        <button className="icon-button" onClick={() => refresh()} aria-label="Refresh">
          <Clock3 size={20} />
        </button>
      </header>

      {notice && <div className={`notice ${status === 'error' ? 'notice-error' : ''}`}>{notice}</div>}

      <main>
        {view === 'log' && (
          <LogView
            email={email}
            profile={profile}
            report={report}
            onLogged={() => refresh()}
            setNotice={setNotice}
          />
        )}
        {view === 'history' && <HistoryView logs={logs} />}
        {view === 'reports' && <ReportsView report={report} />}
        {view === 'groups' && (
          <GroupsView
            email={email}
            groups={groups}
            selectedGroupId={selectedGroupId}
            dashboard={dashboard}
            setSelectedGroupId={setSelectedGroupId}
            onChanged={() => refresh()}
            setNotice={setNotice}
          />
        )}
        {view === 'profile' && (
          <ProfileView
            email={email}
            setEmail={setEmail}
            profile={profile}
            onSaved={(nextEmail) => refresh(nextEmail)}
            setNotice={setNotice}
          />
        )}
      </main>

      <nav className="bottom-nav" aria-label="Primary navigation">
        {[
          ['log', Home, 'Log'],
          ['history', History, 'History'],
          ['reports', BarChart3, 'Reports'],
          ['groups', Users, 'Groups'],
          ['profile', Settings, 'Profile'],
        ].map(([key, Icon, label]) => (
          <button
            key={key as string}
            className={view === key ? 'active' : ''}
            onClick={() => setView(key as View)}
          >
            <Icon size={20} />
            <span>{label as string}</span>
          </button>
        ))}
      </nav>
    </div>
  )
}

function LogView({
  email,
  profile,
  report,
  onLogged,
  setNotice,
}: {
  email: string
  profile: Profile | null
  report: PersonalReport | null
  onLogged: () => void
  setNotice: (notice: string) => void
}) {
  const [occurredAt, setOccurredAt] = useState(localDateTimeValue())
  const [stoolType, setStoolType] = useState('4')
  const [urgency, setUrgency] = useState('3')
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    try {
      await api.createLog(email, {
        occurred_at: new Date(occurredAt).toISOString(),
        stool_type: stoolType ? Number(stoolType) : null,
        urgency: urgency ? Number(urgency) : null,
        notes: notes || null,
      })
      setNotes('')
      setOccurredAt(localDateTimeValue())
      setNotice('Logged. Nice and tidy.')
      onLogged()
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Could not log poop')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="screen stack">
      <div className="hero-panel">
        <span>{profile ? `Hi, ${profile.display_name}` : 'Ready when you are'}</span>
        <strong>{report?.total_count ?? 0}</strong>
        <p>Total logged poops</p>
      </div>

      <form className="form-panel stack" onSubmit={submit}>
        <label>
          Poop time
          <input type="datetime-local" value={occurredAt} onChange={(e) => setOccurredAt(e.target.value)} />
        </label>

        <label>
          Stool type
          <select value={stoolType} onChange={(e) => setStoolType(e.target.value)}>
            <option value="">Not sure</option>
            {stoolTypes.map((type) => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
          <span className="field-help">Based on the Bristol stool scale: 1 is hardest, 7 is liquid.</span>
        </label>

        <label>
          Urgency
          <div className="slider-field">
            <input
              type="range"
              min="1"
              max="5"
              step="1"
              value={urgency}
              onChange={(e) => setUrgency(e.target.value)}
            />
            <div className="slider-scale">
              <span>No rush</span>
              <strong>{urgencyLabels[urgency]}</strong>
              <span>Emergency</span>
            </div>
          </div>
        </label>

        <label>
          Notes
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={3} />
        </label>

        <button className="primary-action" type="submit" disabled={saving}>
          <Plus size={22} />
          <span>{saving ? 'Logging...' : 'Log poop now'}</span>
        </button>
      </form>
    </section>
  )
}

function HistoryView({ logs }: { logs: PoopLog[] }) {
  return (
    <section className="screen stack">
      {logs.length === 0 ? (
        <EmptyState title="No poops yet" body="Your history will appear after the first log." />
      ) : (
        <div className="timeline">
          {logs.map((log) => (
            <article className="timeline-item" key={log.id}>
              <div>
                <strong>{formatDateTime(log.occurred_at)}</strong>
                <span>
                  {log.stool_type ? `Type ${log.stool_type}` : 'Type not set'}
                  {log.urgency ? ` · Urgency ${log.urgency}` : ''}
                </span>
              </div>
              {log.notes && <p>{log.notes}</p>}
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

function ReportsView({ report }: { report: PersonalReport | null }) {
  if (!report) return <EmptyState title="Loading reports" body="Stats appear after the API responds." />

  return (
    <section className="screen stack">
      <div className="metric-row">
        <div>
          <span>Total</span>
          <strong>{report.total_count}</strong>
        </div>
        <div>
          <span>Streak</span>
          <strong>{report.current_streak_days}d</strong>
        </div>
        <div>
          <span>Weekly avg</span>
          <strong>{report.average_per_week}</strong>
        </div>
      </div>

      <ChartPanel title="Last 14 days">
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={report.daily_counts}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" hide />
            <YAxis allowDecimals={false} width={28} />
            <Tooltip />
            <Line type="monotone" dataKey="value" stroke="#0f766e" strokeWidth={3} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartPanel>

      <ChartPanel title="Time of day">
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={report.hourly_distribution}>
            <XAxis dataKey="label" interval={5} />
            <YAxis allowDecimals={false} width={28} />
            <Tooltip />
            <Bar dataKey="value" fill="#c2410c" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartPanel>
    </section>
  )
}

function GroupsView({
  email,
  groups,
  selectedGroupId,
  dashboard,
  setSelectedGroupId,
  onChanged,
  setNotice,
}: {
  email: string
  groups: Group[]
  selectedGroupId: string | null
  dashboard: GroupDashboard | null
  setSelectedGroupId: (id: string) => void
  onChanged: () => void
  setNotice: (notice: string) => void
}) {
  const [newGroupName, setNewGroupName] = useState('')
  const [joinCode, setJoinCode] = useState('')

  async function createGroup(event: FormEvent) {
    event.preventDefault()
    if (!newGroupName.trim()) return
    await api.createGroup(email, newGroupName.trim())
    setNewGroupName('')
    onChanged()
  }

  async function joinGroup(event: FormEvent) {
    event.preventDefault()
    if (!joinCode.trim()) return
    await api.joinGroup(email, joinCode.trim().toUpperCase())
    setJoinCode('')
    onChanged()
  }

  async function createInvite() {
    if (!selectedGroupId) return
    const invite = await api.createInvite(email, selectedGroupId)
    setNotice(`Invite code: ${invite.code}`)
  }

  return (
    <section className="screen stack">
      <div className="split-actions">
        <form onSubmit={createGroup}>
          <input
            placeholder="New group name"
            value={newGroupName}
            onChange={(e) => setNewGroupName(e.target.value)}
          />
          <button type="submit">Create</button>
        </form>
        <form onSubmit={joinGroup}>
          <input placeholder="Invite code" value={joinCode} onChange={(e) => setJoinCode(e.target.value)} />
          <button type="submit">Join</button>
        </form>
      </div>

      {groups.length === 0 ? (
        <EmptyState title="No groups" body="Create a group or join with an invite code." />
      ) : (
        <>
          <div className="group-tabs">
            {groups.map((group) => (
              <button
                key={group.id}
                className={selectedGroupId === group.id ? 'selected' : ''}
                onClick={() => setSelectedGroupId(group.id)}
              >
                {group.name}
              </button>
            ))}
          </div>
          <button className="secondary-action" onClick={createInvite}>
            Generate invite code
          </button>
          <GroupDashboardPanel dashboard={dashboard} />
        </>
      )}
    </section>
  )
}

function GroupDashboardPanel({ dashboard }: { dashboard: GroupDashboard | null }) {
  if (!dashboard) return null

  return (
    <div className="stack">
      <div className="metric-row">
        <div>
          <span>Members</span>
          <strong>{dashboard.member_count}</strong>
        </div>
        <div>
          <span>Group logs</span>
          <strong>{dashboard.total_count}</strong>
        </div>
      </div>

      <section className="panel">
        <h2>
          <Crown size={18} />
          Leaderboard
        </h2>
        {dashboard.leaderboards.most_logs.length === 0 ? (
          <p className="subtle">No group logs yet.</p>
        ) : (
          dashboard.leaderboards.most_logs.map((row, index) => (
            <div className="leader-row" key={row.user_id}>
              <span>{index + 1}</span>
              <strong>{row.display_name}</strong>
              <em>{row.value}</em>
            </div>
          ))
        )}
      </section>

      <section className="panel">
        <h2>Recent activity</h2>
        {dashboard.recent_activity.length === 0 ? (
          <p className="subtle">Activity appears when members log poops.</p>
        ) : (
          dashboard.recent_activity.map((activity) => (
            <div className="activity-row" key={activity.id}>
              <strong>{activity.display_name}</strong>
              <span>{formatDateTime(activity.occurred_at)}</span>
            </div>
          ))
        )}
      </section>
    </div>
  )
}

function ProfileView({
  email,
  setEmail,
  profile,
  onSaved,
  setNotice,
}: {
  email: string
  setEmail: (email: string) => void
  profile: Profile | null
  onSaved: (email: string) => void
  setNotice: (notice: string) => void
}) {
  const [draftEmail, setDraftEmail] = useState(email)
  const [displayName, setDisplayName] = useState(profile?.display_name ?? '')
  const [timezone, setTimezone] = useState(profile?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone)

  useEffect(() => {
    setDisplayName(profile?.display_name ?? '')
    setTimezone(profile?.timezone ?? Intl.DateTimeFormat().resolvedOptions().timeZone)
  }, [profile])

  async function submit(event: FormEvent) {
    event.preventDefault()
    localStorage.setItem('poopr.email', draftEmail)
    setEmail(draftEmail)
    await api.updateProfile(draftEmail, {
      display_name: displayName || draftEmail.split('@')[0],
      timezone,
      avatar_url: profile?.avatar_url ?? null,
    })
    setNotice('Profile saved.')
    onSaved(draftEmail)
  }

  return (
    <section className="screen stack">
      <form className="form-panel stack" onSubmit={submit}>
        {usesManagedAuth ? (
          <div className="managed-auth-row">
            <span>Signed in as</span>
            <strong>{profile?.email ?? 'Loading account...'}</strong>
          </div>
        ) : (
          <label>
            Email
            <input value={draftEmail} onChange={(e) => setDraftEmail(e.target.value)} type="email" />
          </label>
        )}
        <label>
          Display name
          <input value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        </label>
        <label>
          Timezone
          <input value={timezone} onChange={(e) => setTimezone(e.target.value)} />
        </label>
        <button className="primary-action" type="submit">
          Save profile
        </button>
      </form>
    </section>
  )
}

function ChartPanel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      {children}
    </section>
  )
}

