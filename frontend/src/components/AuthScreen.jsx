import { useState, useEffect, useRef } from 'react'
import { setAuth } from '../utils/auth'
import './AuthScreen.css'
import './AuthObservatory.css'

export default function AuthScreen({ apiBase, onAuthed }) {
  const [authTab, setAuthTab] = useState('login')
  const [username, setUsername] = useState('')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [authError, setAuthError] = useState(null)
  const [authSuccess, setAuthSuccess] = useState('')
  const [authLoading, setAuthLoading] = useState(false)
  const [passwordVisibility, setPasswordVisibility] = useState({
    login: false,
    register: false,
    confirm: false,
  })

  const loginFieldRef = useRef(null)

  useEffect(() => {
    if (authTab === 'login' && authSuccess) {
      loginFieldRef.current?.focus()
    }
  }, [authTab, authSuccess])

  const switchTab = (nextTab) => {
    setAuthTab(nextTab)
    setAuthError(null)
    setAuthSuccess('')
  }

  const handleForgotPasswordClick = () => {
    setAuthError('Password reset is not currently available in this project. No backend password-reset endpoint is configured, so this flow cannot be completed safely.')
    setAuthSuccess('')
  }

  const togglePasswordVisibility = (field) => {
    setPasswordVisibility((current) => ({
      ...current,
      [field]: !current[field],
    }))
  }

  const handleAuthSubmit = async (e) => {
    e.preventDefault()
    setAuthError(null)
    setAuthSuccess('')
    setAuthLoading(true)

    if (authTab === 'login') {
      const identifier = username.trim()
      if (!identifier || !password) {
        setAuthError('Username and password are required.')
        setAuthLoading(false)
        return
      }
    } else {
      const fullNameValue = fullName.trim()
      const usernameValue = username.trim()
      if (!fullNameValue) {
        setAuthError('Full name is required to create an account.')
        setAuthLoading(false)
        return
      }
      if (!usernameValue) {
        setAuthError('Username is required to create an account.')
        setAuthLoading(false)
        return
      }
      if (password.length < 8) {
        setAuthError('Password must be at least 8 characters long.')
        setAuthLoading(false)
        return
      }
      if (password !== confirmPassword) {
        setAuthError('The passwords do not match.')
        setAuthLoading(false)
        return
      }
    }

    const endpoint = authTab === 'login'
      ? `${apiBase}/auth/login/`
      : `${apiBase}/auth/register/`

    const payload = authTab === 'login'
      ? { username: username.trim(), password }
      : (() => {
        const [firstName, ...rest] = fullName.trim().split(/\s+/)
        const lastName = rest.join(' ')
        const usernameBase = username.trim()
          .replace(/[^a-zA-Z0-9._-]+/g, '')
          .toLowerCase() || 'vedic-user'

        return {
          username: usernameBase,
          email: email.trim(),
          password,
          first_name: firstName || '',
          last_name: lastName || '',
        }
      })()

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      const data = await res.json()
      if (!res.ok) {
        const msg = data.error || data.detail || Object.values(data).flat().join(' ') || 'Authentication failed'
        setAuthError(msg)
        return
      }

      if (authTab === 'login') {
        setAuth({ token: data.token, user: data.user })
        onAuthed(data.user)
        return
      }

      setFullName('')
      setEmail('')
      setPassword('')
      setConfirmPassword('')
      setUsername('')
      setAuthSuccess('Registration successful. Please sign in to continue.')
      setAuthTab('login')
    } catch (err) {
      setAuthError(`Connection error: ${err.message}`)
    } finally {
      setAuthLoading(false)
    }
  }

  return (
    <div className="portal-wrapper">
      <header className="clean-nav">
        <div className="nav-brand">
          <span className="nav-logo-icon" aria-hidden="true" />
          <div>
            <h1 className="nav-logo-text">Vedic Acoustica</h1>
            <span className="nav-status-badge">● 22 Śruti · Rāga · Ghana Patha</span>
          </div>
        </div>
      </header>

      <main className="auth-clean-viewport">
        <div className="auth-ambient" aria-hidden="true">
          <span className="ambient-ring ring-outer" />
          <span className="ambient-ring ring-inner" />
          <span className="ambient-note note-sa">Sa</span>
          <span className="ambient-note note-re">Re</span>
          <span className="ambient-note note-ga">Ga</span>
          <span className="ambient-note note-ma">Ma</span>
          <span className="ambient-note note-pa">Pa</span>
          <span className="ambient-note note-dha">Dha</span>
          <span className="ambient-note note-ni">Ni</span>
          <span className="ambient-om">ॐ</span>
          <span className="ambient-caption">The science of sacred sound</span>
        </div>

        <section className="auth-clean-card" aria-labelledby="auth-title">
          <div className="auth-card-head">
            <h2 id="auth-title">{authTab === 'login' ? 'Researcher Sign In' : 'Create your account'}</h2>
            <p>
              {authTab === 'login'
                ? 'Sign in to continue your acoustic research.'
                : 'Create an account to upload audio and run analysis.'}
            </p>
          </div>

          <div className="clean-tabs" role="tablist" aria-label="Authentication">
            <button
              type="button"
              role="tab"
              aria-selected={authTab === 'login'}
              className={`clean-tab-btn ${authTab === 'login' ? 'active' : ''}`}
              onClick={() => switchTab('login')}
            >
              Sign In
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={authTab === 'register'}
              className={`clean-tab-btn ${authTab === 'register' ? 'active' : ''}`}
              onClick={() => switchTab('register')}
            >
              Register
            </button>
          </div>

          {authError && (
            <div className="clean-error-alert" role="alert">
              ⚠️ {authError}
            </div>
          )}

          {authSuccess && (
            <div className="clean-success-alert" role="status">
              ✓ {authSuccess}
            </div>
          )}

          <form onSubmit={handleAuthSubmit} className="clean-form">
            {authTab === 'register' && (
              <div className="clean-form-group">
                <label htmlFor="auth-full-name">Full Name</label>
                <input
                  id="auth-full-name"
                  type="text"
                  required
                  placeholder="Your full name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  autoComplete="name"
                />
              </div>
            )}

            <div className="clean-form-group">
              <label htmlFor="auth-user">{authTab === 'login' ? 'Email or username' : 'Username'}</label>
              <input
                id="auth-user"
                type="text"
                required
                placeholder={authTab === 'login' ? 'Enter email or username' : 'Choose a username'}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                ref={authTab === 'login' ? loginFieldRef : null}
              />
            </div>

            {authTab === 'register' && (
              <div className="clean-form-group">
                <label htmlFor="auth-email">Email</label>
                <input
                  id="auth-email"
                  type="email"
                  placeholder="researcher@university.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                />
              </div>
            )}

            <div className="clean-form-group">
              <label htmlFor="auth-pass">Password</label>
              <div className="password-input-wrap">
                <input
                  id="auth-pass"
                  type={passwordVisibility[authTab === 'login' ? 'login' : 'register'] ? 'text' : 'password'}
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete={authTab === 'login' ? 'current-password' : 'new-password'}
                />
                <button
                  type="button"
                  className="password-toggle"
                  aria-label={passwordVisibility[authTab === 'login' ? 'login' : 'register'] ? 'Hide password' : 'Show password'}
                  onClick={() => togglePasswordVisibility(authTab === 'login' ? 'login' : 'register')}
                >
                  <span aria-hidden="true">{passwordVisibility[authTab === 'login' ? 'login' : 'register'] ? '🙈' : '👁'}</span>
                </button>
              </div>
            </div>

            {authTab === 'register' && (
              <div className="clean-form-group">
                <label htmlFor="auth-confirm-pass">Confirm password</label>
                <div className="password-input-wrap">
                  <input
                    id="auth-confirm-pass"
                    type={passwordVisibility.confirm ? 'text' : 'password'}
                    required
                    placeholder="Repeat password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    aria-label={passwordVisibility.confirm ? 'Hide password' : 'Show password'}
                    onClick={() => togglePasswordVisibility('confirm')}
                  >
                    <span aria-hidden="true">{passwordVisibility.confirm ? '🙈' : '👁'}</span>
                  </button>
                </div>
              </div>
            )}

            {authTab === 'login' && (
              <div className="auth-form-row">
                <button
                  type="button"
                  className="clean-link-button"
                  onClick={handleForgotPasswordClick}
                >
                  Forgot password?
                </button>
              </div>
            )}

            <button type="submit" className="btn btn-submit-clean" disabled={authLoading}>
              {authLoading ? (authTab === 'login' ? 'Signing In…' : 'Registering…') : (authTab === 'login' ? 'Sign In' : 'Create Account')}
            </button>
          </form>

          <div className="auth-provider">
            <div className="clean-divider"><span>OR</span></div>
            <button type="button" className="google-auth-button" disabled title="Google OAuth is not configured">
              <span className="google-mark" aria-hidden="true">G</span>
              Continue with Google
            </button>
            <p className="oauth-note">
              Google sign-in is not available: the existing backend has no configured Google OAuth provider.
            </p>
          </div>
        </section>
      </main>
    </div>
  )
}
