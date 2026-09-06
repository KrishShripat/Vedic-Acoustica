import { useState } from 'react'
import { setAuth } from '../utils/auth'

/**
 * AuthScreen — functional login/register scaffold.
 *
 * This is a placeholder UI so the app works end-to-end against the real
 * /api/auth/* contract.  The final visual design (Vedic Dawn) is being built
 * separately; only the API behaviour below is guaranteed to stay.
 *
 * Contract (matches backend/api/auth_views.py):
 *   POST /api/auth/register/  { username, email, password, ... } → { token, user }
 *   POST /api/auth/login/     { username | email, password }    → { token, user }
 */
export default function AuthScreen({ apiBase, onAuthed }) {
  const [mode, setMode] = useState('login') // 'login' | 'register'
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setError(null)

    if (mode === 'register') {
      if (password !== confirm) {
        setError('Passwords do not match.')
        return
      }
      if (password.length < 8) {
        setError('Password must be at least 8 characters long.')
        return
      }
    }

    setBusy(true)
    try {
      const res = await fetch(`${apiBase}/auth/${mode}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || data.detail || `Request failed (HTTP ${res.status})`)
      }
      setAuth({ token: data.token, user: data.user })
      onAuthed?.(data.user)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card auth-card">
      <h2>Vedic Acoustica</h2>
      <p className="subtitle">
        {mode === 'login'
          ? 'Sign in to upload recordings and run analysis'
          : 'Create an account to upload recordings and run analysis'}
      </p>

      <div className="auth-tabs">
        <button
          type="button"
          className={`auth-tab ${mode === 'login' ? 'active' : ''}`}
          onClick={() => { setMode('login'); setError(null) }}
        >
          Login
        </button>
        <button
          type="button"
          className={`auth-tab ${mode === 'register' ? 'active' : ''}`}
          onClick={() => { setMode('register'); setError(null) }}
        >
          Register
        </button>
      </div>

      <form onSubmit={submit} className="auth-form">
        <label className="auth-field">
          <span>Username</span>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </label>

        {mode === 'register' && (
          <label className="auth-field">
            <span>Email (optional)</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </label>
        )}

        <label className="auth-field">
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            required
          />
        </label>

        {mode === 'register' && (
          <label className="auth-field">
            <span>Confirm password</span>
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
              required
            />
          </label>
        )}

        {error && <p className="text-error auth-error">{error}</p>}

        <button type="submit" className="btn auth-submit" disabled={busy}>
          {busy
            ? <><span className="loading-spinner" /> Please wait…</>
            : mode === 'login' ? 'Sign in' : 'Create account'}
        </button>
      </form>
    </div>
  )
}