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
    <div className="min-h-screen w-full flex items-center justify-center p-6 bg-slate-950">
      <div className="w-full max-w-md bg-slate-900/80 border border-slate-800 rounded-2xl p-8 shadow-2xl backdrop-blur-xl flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold tracking-wide text-center text-rose-500">
            Vedic Acoustica
          </h1>
          <p className="text-xs text-slate-400 text-center -mt-4">
            Microtonal Voice Analysis &middot; 22 Shrutis &middot; Raga Detection
          </p>
        </div>

        <div className="grid grid-cols-2 p-1 bg-slate-950/80 rounded-xl border border-slate-800" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'login'}
            onClick={() => selectMode('login')}
            className={`py-2 text-xs font-semibold rounded-lg text-center transition-all cursor-pointer ${
              mode === 'login'
                ? 'bg-cyan-500 text-slate-950 shadow-md'
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
            className={`py-2 text-xs font-semibold rounded-lg text-center transition-all cursor-pointer ${
              mode === 'register'
                ? 'bg-cyan-500 text-slate-950 shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Register
          </button>
        </div>

        <form onSubmit={submit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-slate-300 tracking-wider">Username</span>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              placeholder="Enter your username"
              required
              className="w-full h-11 px-3.5 rounded-xl bg-slate-950/90 border border-slate-800 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors"
            />
          </label>

          {mode === 'register' && (
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-slate-300 tracking-wider">
                Email (optional)
              </span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                placeholder="you@example.com"
                className="w-full h-11 px-3.5 rounded-xl bg-slate-950/90 border border-slate-800 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors"
              />
            </label>
          )}

          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-slate-300 tracking-wider">Password</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              placeholder={mode === 'login' ? 'Enter your password' : 'At least 8 characters'}
              required
              className="w-full h-11 px-3.5 rounded-xl bg-slate-950/90 border border-slate-800 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors"
            />
          </label>

          {mode === 'register' && (
            <label className="flex flex-col gap-1.5">
              <span className="text-xs font-medium text-slate-300 tracking-wider">
                Confirm password
              </span>
              <input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
                placeholder="Re-enter your password"
                required
                className="w-full h-11 px-3.5 rounded-xl bg-slate-950/90 border border-slate-800 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-500 focus:ring-1 focus:ring-cyan-500 transition-colors"
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
            className="w-full h-11 mt-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold text-sm transition-colors shadow-lg shadow-cyan-500/20 flex items-center justify-center disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {busy
              ? <span className="inline-flex items-center gap-2"><span className="loading-spinner" /> Please wait…</span>
              : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>

        <button
          type="button"
          onClick={onGuest}
          className="w-full text-center text-xs text-slate-400 hover:text-slate-200 transition-colors py-2 cursor-pointer"
        >
          Continue as Guest / Demo Mode
        </button>
      </div>
    </div>
  )
}