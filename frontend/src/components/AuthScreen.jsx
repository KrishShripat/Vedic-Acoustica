import { useState } from 'react'
import { setAuth } from '../utils/auth'

export default function AuthScreen({ apiBase, onAuthed, onGuest }) {
  const [mode, setMode] = useState('login')
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

  const selectMode = (next) => {
    setMode(next)
    setError(null)
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-slate-900/70 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-8 shadow-2xl">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white">Vedic Acoustica</h1>
          <p className="mt-2 text-sm text-slate-400">
            Microtonal Voice Analysis &middot; 22 Shrutis &middot; Raga Detection
          </p>
        </div>

        <div className="flex p-1 mb-8 bg-slate-950/60 border border-slate-700/50 rounded-xl" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'login'}
            onClick={() => selectMode('login')}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors focus:outline-none ${
              mode === 'login'
                ? 'bg-cyan-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'register'}
            onClick={() => selectMode('register')}
            className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors focus:outline-none ${
              mode === 'register'
                ? 'bg-cyan-500 text-slate-950 shadow'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Register
          </button>
        </div>

        <form onSubmit={submit} className="space-y-5">
          <label className="block">
            <span className="block mb-1.5 text-xs font-medium text-slate-400 uppercase tracking-wider">
              Username
            </span>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              placeholder="Enter your username"
              required
              className="w-full px-4 py-2.5 rounded-xl bg-slate-950/60 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </label>

          {mode === 'register' && (
            <label className="block">
              <span className="block mb-1.5 text-xs font-medium text-slate-400 uppercase tracking-wider">
                Email (optional)
              </span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                placeholder="you@example.com"
                className="w-full px-4 py-2.5 rounded-xl bg-slate-950/60 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </label>
          )}

          <label className="block">
            <span className="block mb-1.5 text-xs font-medium text-slate-400 uppercase tracking-wider">
              Password
            </span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              placeholder={mode === 'login' ? 'Enter your password' : 'At least 8 characters'}
              required
              className="w-full px-4 py-2.5 rounded-xl bg-slate-950/60 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
            />
          </label>

          {mode === 'register' && (
            <label className="block">
              <span className="block mb-1.5 text-xs font-medium text-slate-400 uppercase tracking-wider">
                Confirm password
              </span>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
                placeholder="Re-enter your password"
                required
                className="w-full px-4 py-2.5 rounded-xl bg-slate-950/60 border border-slate-700 text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500"
              />
            </label>
          )}

          {error && (
            <p
              role="alert"
              className="text-sm text-red-400 bg-red-950/40 border border-red-900/50 rounded-lg px-3 py-2"
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="w-full px-4 py-3 rounded-xl font-semibold bg-gradient-to-r from-cyan-500 to-cyan-600 text-slate-950 hover:from-cyan-400 hover:to-cyan-500 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {busy
              ? <span className="inline-flex items-center gap-2"><span className="loading-spinner" /> Please wait…</span>
              : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <div className="mt-4">
          <button
            type="button"
            onClick={onGuest}
            className="w-full px-4 py-2.5 rounded-xl border border-slate-700 text-sm font-medium text-slate-400 hover:text-white hover:border-slate-500 transition-colors"
          >
            Continue as Guest / Demo Mode
          </button>
        </div>
      </div>
    </div>
  )
}