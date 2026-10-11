import { useState, useEffect, useRef } from 'react'
import { setAuth } from '../utils/auth'
import './AuthScreen.css'
import './AuthObservatory.css'

// Google OAuth client IDs are public (shipped to the browser), so a fallback
// is safe.  Override per-environment with VITE_GOOGLE_CLIENT_ID when needed.
const googleClientId =
  import.meta.env.VITE_GOOGLE_CLIENT_ID ||
  '358793622628-pfi05ejcf4pqpr2lu51qdga8n7eo8fuv.apps.googleusercontent.com'

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

  // Password reset.  `forgotMode` shows the "enter your email" panel; a reset
  // link opened from email (?reset=1&uid=..&token=..) shows the "choose a new
  // password" panel instead of the usual sign-in form.
  const readResetParams = () => {
    if (typeof window === 'undefined') return null
    const params = new URLSearchParams(window.location.search)
    const uid = params.get('uid')
    const token = params.get('token')
    if (params.get('reset') && uid && token) return { uid, token }
    return null
  }
  const readVerifyParams = () => {
    if (typeof window === 'undefined') return null
    const params = new URLSearchParams(window.location.search)
    const uid = params.get('uid')
    const token = params.get('token')
    if (params.get('verify') && uid && token) return { uid, token }
    return null
  }
  const [forgotMode, setForgotMode] = useState(false)
  const [forgotEmail, setForgotEmail] = useState('')
  const [resetParams, setResetParams] = useState(readResetParams)
  const [resetPassword, setResetPassword] = useState('')
  const [resetConfirm, setResetConfirm] = useState('')
  const [resetVisibility, setResetVisibility] = useState({ password: false, confirm: false })

  // Email verification: `verifyParams` comes from the emailed link; the
  // `pendingEmail` panel is shown after a successful sign-up (and after a
  // blocked login) to prompt the user to confirm their address.
  const [verifyParams, setVerifyParams] = useState(readVerifyParams)
  const [verifyStatus, setVerifyStatus] = useState(verifyParams ? 'checking' : 'idle')
  const [showVerifyPanel, setShowVerifyPanel] = useState(false)
  const [pendingEmail, setPendingEmail] = useState('')
  const [resendStatus, setResendStatus] = useState(null)
  const [resendLoading, setResendLoading] = useState(false)

  const clearUrlParams = () => {
    if (typeof window !== 'undefined' && window.location.search) {
      window.history.replaceState({}, '', window.location.pathname)
    }
  }

  const loginFieldRef = useRef(null)

  useEffect(() => {
    if (authTab === 'login' && authSuccess) {
      loginFieldRef.current?.focus()
    }
  }, [authTab, authSuccess])

  // Verify the emailed link automatically when the app loads with ?verify=1.
  useEffect(() => {
    if (!verifyParams) return
    let cancelled = false
    const run = async () => {
      setVerifyStatus('checking')
      try {
        const res = await fetch(`${apiBase}/auth/verify-email/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ uid: verifyParams.uid, token: verifyParams.token }),
        })
        const data = await res.json().catch(() => ({}))
        if (cancelled) return
        if (res.ok) {
          setVerifyStatus('ok')
        } else {
          setVerifyStatus('error')
          setAuthError(data.error || 'This verification link is invalid or has expired.')
        }
      } catch {
        if (!cancelled) {
          setVerifyStatus('error')
          setAuthError('Connection error while verifying your email.')
        }
      }
    }
    run()
    return () => { cancelled = true }
  }, [verifyParams, apiBase])

  const googleButtonRef = useRef(null)
  const handleGoogleCredentialRef = useRef(null)

  useEffect(() => {
    if (!googleClientId) return
    const renderGoogleButton = () => {
      if (!window.google?.accounts?.id || !googleButtonRef.current) return
      window.google.accounts.id.initialize({
        client_id: googleClientId,
        auto_select: false,
        callback: (response) => handleGoogleCredentialRef.current?.(response),
      })
      window.google.accounts.id.renderButton(googleButtonRef.current, {
        theme: 'outline',
        size: 'large',
        shape: 'rectangular',
        text: 'continue_with',
        width: 260,
        locale: 'en',
      })
    }
    if (window.google?.accounts?.id) {
      renderGoogleButton()
      return
    }
    const script = document.createElement('script')
    script.id = 'va-google-gsi'
    script.src = 'https://accounts.google.com/gsi/client'
    script.async = true
    script.defer = true
    script.onload = renderGoogleButton
    document.head.appendChild(script)
    return () => {
      const el = document.getElementById('va-google-gsi')
      if (el) el.remove()
    }
  }, [])

  const handleGoogleCredential = async (response) => {
    if (!response?.credential) return
    setAuthError(null)
    setAuthSuccess('')
    setAuthLoading(true)
    try {
      const res = await fetch(`${apiBase}/auth/google/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: response.credential }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Google sign-in failed')
      setAuth({ token: data.token, user: data.user })
      onAuthed(data.user)
    } catch (err) {
      setAuthError(`Google sign-in failed: ${err.message}`)
    } finally {
      setAuthLoading(false)
    }
  }

  handleGoogleCredentialRef.current = handleGoogleCredential

  const switchTab = (nextTab) => {
    setAuthTab(nextTab)
    setAuthError(null)
    setAuthSuccess('')
  }

  const handleForgotPasswordClick = () => {
    setForgotMode(true)
    setForgotEmail(username.trim())
    setAuthError(null)
    setAuthSuccess('')
  }

  const exitForgotMode = () => {
    setForgotMode(false)
    setAuthError(null)
    setAuthSuccess('')
  }

  const handleResetCancel = () => {
    clearUrlParams()
    setResetParams(null)
    setAuthTab('login')
    setAuthError(null)
    setAuthSuccess('')
  }

  const handleForgotSubmit = async (e) => {
    e.preventDefault()
    setAuthError(null)
    setAuthSuccess('')
    const email = forgotEmail.trim()
    if (!email) {
      setAuthError('Please enter your email address.')
      return
    }
    setAuthLoading(true)
    try {
      const res = await fetch(`${apiBase}/auth/password-reset/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.error || 'Could not send the reset email.')
      setAuthSuccess(data.message || 'If an account exists for that email, a reset link is on its way.')
    } catch (err) {
      setAuthError(err.message)
    } finally {
      setAuthLoading(false)
    }
  }

  const handleResetSubmit = async (e) => {
    e.preventDefault()
    setAuthError(null)
    setAuthSuccess('')
    if (resetPassword.length < 8) {
      setAuthError('Password must be at least 8 characters long.')
      return
    }
    if (resetPassword !== resetConfirm) {
      setAuthError('The passwords do not match.')
      return
    }
    setAuthLoading(true)
    try {
      const res = await fetch(`${apiBase}/auth/password-reset/confirm/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          uid: resetParams?.uid,
          token: resetParams?.token,
          password: resetPassword,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.error || 'This reset link is invalid or has expired.')
      clearUrlParams()
      setResetParams(null)
      setResetPassword('')
      setResetConfirm('')
      setAuthTab('login')
      setAuthSuccess('Password updated. Please sign in with your new password.')
    } catch (err) {
      setAuthError(err.message)
    } finally {
      setAuthLoading(false)
    }
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
      if (!email.trim()) {
        setAuthError('Email is required to create an account.')
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

        return {
          username: username.trim(),
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
        if (data.verification_required) {
          const id = username.trim()
          setPendingEmail(id.includes('@') ? id : '')
          setShowVerifyPanel(true)
          setAuthError('')
          setAuthSuccess('')
          return
        }
        const msg = data.error || data.detail || Object.values(data).flat().join(' ') || 'Authentication failed'
        setAuthError(msg)
        return
      }

      if (authTab === 'login') {
        setAuth({ token: data.token, user: data.user })
        onAuthed(data.user)
        return
      }

      // Registration succeeded: the account is locked until the emailed link
      // is opened, so surface the "verify your email" panel instead.
      setFullName('')
      setEmail('')
      setPassword('')
      setConfirmPassword('')
      setUsername(data.user?.username || username.trim())
      setAuthSuccess('')
      setPendingEmail(email.trim())
      setShowVerifyPanel(true)
    } catch (err) {
      setAuthError(`Connection error: ${err.message}`)
    } finally {
      setAuthLoading(false)
    }
  }

  const handleResendVerification = async (e) => {
    e?.preventDefault?.()
    setAuthError(null)
    setResendStatus(null)
    const target = (pendingEmail || '').trim()
    if (!target) {
      setAuthError('Please enter your email address.')
      return
    }
    setResendLoading(true)
    try {
      const res = await fetch(`${apiBase}/auth/verify-email/resend/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: target }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.error || 'Could not resend the verification email.')
      setResendStatus(data.message || 'Verification email sent.')
    } catch (err) {
      setAuthError(err.message)
    } finally {
      setResendLoading(false)
    }
  }

  const handleLeaveVerification = () => {
    clearUrlParams()
    setVerifyParams(null)
    setVerifyStatus('idle')
    setShowVerifyPanel(false)
    setPendingEmail('')
    setResendStatus(null)
    setAuthTab('login')
    setAuthError(null)
    setAuthSuccess('')
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
            <h2 id="auth-title">
              {verifyParams
                ? (verifyStatus === 'ok' ? 'Email verified' : verifyStatus === 'error' ? 'Verification failed' : 'Verifying your email…')
                : resetParams
                  ? 'Set a new password'
                  : showVerifyPanel
                    ? 'Verify your email'
                    : forgotMode
                      ? 'Reset your password'
                      : authTab === 'login'
                        ? 'Researcher Sign In'
                        : 'Create your account'}
            </h2>
            <p>
              {verifyParams
                ? (verifyStatus === 'ok'
                  ? 'Your account is active. You can sign in now.'
                  : verifyStatus === 'error'
                    ? 'This link may have expired — request a new one below.'
                    : 'Just a moment.')
                : resetParams
                ? 'Choose a new password for your account.'
                : showVerifyPanel
                  ? 'We sent a confirmation link to your inbox. Click it to activate your account.'
                  : forgotMode
                    ? 'Enter your email and we’ll send you a reset link.'
                    : authTab === 'login'
                      ? 'Sign in to continue your acoustic research.'
                      : 'Create an account to upload audio and run analysis.'}
            </p>
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

          {verifyParams ? (
            <div className="clean-form">
              {verifyStatus === 'checking' && (
                <div className="clean-success-alert" role="status">Verifying your email…</div>
              )}
              {verifyStatus === 'ok' && (
                <div className="clean-success-alert" role="status">
                  ✓ Your email is verified. You can sign in now.
                </div>
              )}
              {verifyStatus === 'error' && (
                <div className="clean-error-alert" role="alert">
                  ⚠️ {authError || 'This verification link is invalid or has expired.'}
                </div>
              )}
              <button type="button" className="btn btn-submit-clean" onClick={handleLeaveVerification}>
                Go to sign in
              </button>
              <div className="auth-form-row">
                <button
                  type="button"
                  className="clean-link-button"
                  onClick={() => {
                    clearUrlParams()
                    setVerifyParams(null)
                    setVerifyStatus('idle')
                    setAuthError(null)
                    setPendingEmail('')
                    setShowVerifyPanel(true)
                  }}
                >
                  Resend verification email
                </button>
              </div>
            </div>
          ) : resetParams ? (
            <form onSubmit={handleResetSubmit} className="clean-form">
              <div className="clean-form-group">
                <label htmlFor="reset-pass">New password</label>
                <div className="password-input-wrap">
                  <input
                    id="reset-pass"
                    type={resetVisibility.password ? 'text' : 'password'}
                    required
                    minLength={8}
                    placeholder="••••••••"
                    value={resetPassword}
                    onChange={(e) => setResetPassword(e.target.value)}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    aria-label={resetVisibility.password ? 'Hide password' : 'Show password'}
                    onClick={() => setResetVisibility((c) => ({ ...c, password: !c.password }))}
                  >
                    <span aria-hidden="true">{resetVisibility.password ? '🙈' : '👁'}</span>
                  </button>
                </div>
              </div>

              <div className="clean-form-group">
                <label htmlFor="reset-confirm">Confirm new password</label>
                <div className="password-input-wrap">
                  <input
                    id="reset-confirm"
                    type={resetVisibility.confirm ? 'text' : 'password'}
                    required
                    minLength={8}
                    placeholder="Repeat new password"
                    value={resetConfirm}
                    onChange={(e) => setResetConfirm(e.target.value)}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    aria-label={resetVisibility.confirm ? 'Hide password' : 'Show password'}
                    onClick={() => setResetVisibility((c) => ({ ...c, confirm: !c.confirm }))}
                  >
                    <span aria-hidden="true">{resetVisibility.confirm ? '🙈' : '👁'}</span>
                  </button>
                </div>
              </div>

              <button type="submit" className="btn btn-submit-clean" disabled={authLoading}>
                {authLoading ? 'Updating…' : 'Update password'}
              </button>

              <div className="auth-form-row">
                <button type="button" className="clean-link-button" onClick={handleResetCancel}>
                  Back to sign in
                </button>
              </div>
            </form>
          ) : showVerifyPanel ? (
            <form onSubmit={handleResendVerification} className="clean-form">
              <div className="clean-success-alert" role="status">
                ✓ We sent a verification link to your email. Open it to activate your account.
              </div>
              <div className="clean-form-group">
                <label htmlFor="verify-email">Email</label>
                <input
                  id="verify-email"
                  type="email"
                  required
                  placeholder="you@example.com"
                  value={pendingEmail}
                  onChange={(e) => setPendingEmail(e.target.value)}
                  autoComplete="email"
                />
              </div>

              {resendStatus && (
                <div className="clean-success-alert" role="status">✓ {resendStatus}</div>
              )}

              <button type="submit" className="btn btn-submit-clean" disabled={resendLoading}>
                {resendLoading ? 'Sending…' : 'Resend verification email'}
              </button>

              <div className="auth-form-row">
                <button type="button" className="clean-link-button" onClick={handleLeaveVerification}>
                  Back to sign in
                </button>
              </div>
            </form>
          ) : forgotMode ? (
            <form onSubmit={handleForgotSubmit} className="clean-form">
              <div className="clean-form-group">
                <label htmlFor="forgot-email">Email</label>
                <input
                  id="forgot-email"
                  type="email"
                  required
                  placeholder="you@example.com"
                  value={forgotEmail}
                  onChange={(e) => setForgotEmail(e.target.value)}
                  autoComplete="email"
                />
              </div>

              <button type="submit" className="btn btn-submit-clean" disabled={authLoading}>
                {authLoading ? 'Sending…' : 'Send reset link'}
              </button>

              <div className="auth-form-row">
                <button type="button" className="clean-link-button" onClick={exitForgotMode}>
                  Back to sign in
                </button>
              </div>
            </form>
          ) : (
            <>
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
                      required
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
                {googleClientId ? (
                  <div className="google-auth-wrap">
                    <div ref={googleButtonRef} />
                  </div>
                ) : (
                  <button type="button" className="google-auth-button" disabled title="Google OAuth is not configured">
                    <span className="google-mark" aria-hidden="true">G</span>
                    Continue with Google
                  </button>
                )}
                <p className="oauth-note">
                  {googleClientId
                    ? 'Sign in securely with your Google account.'
                    : 'Google sign-in is not configured (set VITE_GOOGLE_CLIENT_ID).'}
                </p>
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  )
}
