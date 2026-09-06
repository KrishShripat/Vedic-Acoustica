import { useEffect, useState } from 'react'
import { authFetch, clearAuth } from '../utils/auth'

/**
 * AdminOverview — staff-only usage dashboard.
 *
 * Fetches GET /api/admin/overview/ (IsAdminUser on the backend) and renders
 * aggregate counts plus recent recordings and users.  Functional scaffold —
 * the visual design is being replaced by the new frontend.
 */
export default function AdminOverview({ apiBase }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    authFetch(`${apiBase}/admin/overview/`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Admin overview failed (HTTP ${res.status})`)
        const json = await res.json()
        if (!cancelled) setData(json)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err.message)
        clearAuth()
        window.dispatchEvent(new CustomEvent('auth-expired'))
      })
    return () => { cancelled = true }
  }, [apiBase])

  if (error) return <p className="text-error">Could not load admin overview: {error}</p>
  if (!data) return <p>Loading admin overview…</p>

  const stats = [
    { label: 'Users', value: data.counts.total_users },
    { label: 'Staff', value: data.counts.staff_users },
    { label: 'Recordings', value: data.counts.total_recordings },
    { label: 'Analyzed', value: data.counts.analyzed_recordings },
    { label: 'Pending', value: data.counts.pending_recordings },
  ]

  return (
    <div className="card">
      <h2>Admin Overview</h2>
      <div className="admin-stats">
        {stats.map(s => (
          <div key={s.label} className="admin-stat">
            <span className="admin-stat-value">{s.value}</span>
            <span className="admin-stat-label">{s.label}</span>
          </div>
        ))}
      </div>

      <h3>Recordings</h3>
      <table className="admin-table">
        <thead>
          <tr><th>ID</th><th>Title</th><th>Uploaded</th><th>Status</th></tr>
        </thead>
        <tbody>
          {data.recordings.length === 0 && (
            <tr><td colSpan="4">No recordings yet.</td></tr>
          )}
          {data.recordings.map(r => (
            <tr key={r.id}>
              <td>{r.id}</td>
              <td>{r.title}</td>
              <td>{new Date(r.uploaded_at).toLocaleString()}</td>
              <td>{r.is_analyzed ? <span className="badge">Analyzed</span> : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <h3>Users</h3>
      <table className="admin-table">
        <thead>
          <tr><th>ID</th><th>Username</th><th>Email</th><th>Role</th><th>Joined</th></tr>
        </thead>
        <tbody>
          {data.users.map(u => (
            <tr key={u.id}>
              <td>{u.id}</td>
              <td>{u.username}</td>
              <td>{u.email || '—'}</td>
              <td>{u.is_staff ? 'admin' : 'user'}</td>
              <td>{new Date(u.date_joined).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}