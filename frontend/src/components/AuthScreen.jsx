import { useState, useRef, useEffect, useCallback } from 'react'
import { setAuth } from '../utils/auth'
import './AuthScreen.css'

// Canonical 22 Shrutis grouped by 7 Swara families
const SWARA_FAMILIES = [
  {
    key: 'Sa',
    name: 'Sa',
    label: 'Tonic',
    color: '#f43f5e',
    shrutis: [
      { name: 'Sa', ratio: '1/1', freq: 261.63, cents: 0.0, desc: 'Shadja (Base Tonic)', pianoDiff: '0.0¢' },
    ],
  },
  {
    key: 'Re',
    name: 'Re',
    label: 'Rishabh',
    color: '#f97316',
    shrutis: [
      { name: 'Re¹', ratio: '256/243', freq: 275.65, cents: 90.2, desc: 'Eka-shruti Rishabh', pianoDiff: '-9.8¢ flat from D♭' },
      { name: 'Re²', ratio: '16/15', freq: 279.07, cents: 111.7, desc: 'Dvi-shruti Rishabh (21.5¢ gap from Re¹)', pianoDiff: '+11.7¢ sharp from D♭' },
      { name: 'Re³', ratio: '10/9', freq: 290.70, cents: 182.4, desc: 'Tri-shruti Rishabh', pianoDiff: '-17.6¢ flat from D' },
      { name: 'Re⁴', ratio: '9/8', freq: 294.33, cents: 203.9, desc: 'Chatushruti Rishabh', pianoDiff: '+3.9¢ sharp from D' },
    ],
  },
  {
    key: 'Ga',
    name: 'Ga',
    label: 'Gandhar',
    color: '#eab308',
    shrutis: [
      { name: 'Ga¹', ratio: '32/27', freq: 310.07, cents: 294.1, desc: 'Shuddha Gandhar', pianoDiff: '-5.9¢ flat from E♭' },
      { name: 'Ga²', ratio: '6/5', freq: 313.95, cents: 315.6, desc: 'Sadharana Gandhar', pianoDiff: '+15.6¢ sharp from E♭' },
      { name: 'Ga³', ratio: '5/4', freq: 327.03, cents: 386.3, desc: 'Antara Gandhar (Natural 3rd)', pianoDiff: '-13.7¢ flat from E' },
      { name: 'Ga⁴', ratio: '81/64', freq: 331.14, cents: 407.8, desc: 'Chyuta Madhyam', pianoDiff: '+7.8¢ sharp from E' },
    ],
  },
  {
    key: 'Ma',
    name: 'Ma',
    label: 'Madhyam',
    color: '#10b981',
    shrutis: [
      { name: 'Ma¹', ratio: '4/3', freq: 348.84, cents: 498.0, desc: 'Shuddha Madhyam (Consonant 4th)', pianoDiff: '-2.0¢ flat from F' },
      { name: 'Ma²', ratio: '27/20', freq: 353.20, cents: 519.6, desc: 'Tivra Madhyam (Low)', pianoDiff: '+19.6¢ sharp from F' },
      { name: 'Ma³', ratio: '45/32', freq: 367.91, cents: 590.2, desc: 'Prati Madhyam', pianoDiff: '-9.8¢ flat from F#' },
      { name: 'Ma⁴', ratio: '729/512', freq: 372.51, cents: 611.7, desc: 'Tivratama Madhyam', pianoDiff: '+11.7¢ sharp from F#' },
    ],
  },
  {
    key: 'Pa',
    name: 'Pa',
    label: 'Pancham',
    color: '#06b6d4',
    shrutis: [
      { name: 'Pa', ratio: '3/2', freq: 392.44, cents: 702.0, desc: 'Pancham (Perfect 5th)', pianoDiff: '+2.0¢ sharp from G' },
    ],
  },
  {
    key: 'Dha',
    name: 'Dha',
    label: 'Dhaivat',
    color: '#8b5cf6',
    shrutis: [
      { name: 'Dha¹', ratio: '128/81', freq: 413.43, cents: 792.2, desc: 'Shuddha Dhaivat', pianoDiff: '-7.8¢ flat from A♭' },
      { name: 'Dha²', ratio: '8/5', freq: 418.60, cents: 813.7, desc: 'Komal Dhaivat', pianoDiff: '+13.7¢ sharp from A♭' },
      { name: 'Dha³', ratio: '5/3', freq: 436.04, cents: 884.4, desc: 'Trishruti Dhaivat', pianoDiff: '-15.6¢ flat from A' },
      { name: 'Dha⁴', ratio: '27/16', freq: 441.49, cents: 905.9, desc: 'Chatushruti Dhaivat', pianoDiff: '+5.9¢ sharp from A' },
    ],
  },
  {
    key: 'Ni',
    name: 'Ni',
    label: 'Nishad',
    color: '#ec4899',
    shrutis: [
      { name: 'Ni¹', ratio: '16/9', freq: 465.11, cents: 996.1, desc: 'Komal Nishad', pianoDiff: '-3.9¢ flat from B♭' },
      { name: 'Ni²', ratio: '9/5', freq: 470.93, cents: 1017.6, desc: 'Kaishiki Nishad', pianoDiff: '+17.6¢ sharp from B♭' },
      { name: 'Ni³', ratio: '15/8', freq: 490.55, cents: 1088.3, desc: 'Shuddha Nishad', pianoDiff: '-11.7¢ flat from B' },
      { name: 'Ni⁴', ratio: '243/128', freq: 496.71, cents: 1109.8, desc: 'Kakali Nishad', pianoDiff: '+9.8¢ sharp from B' },
    ],
  },
  {
    key: 'Sa2',
    name: "Sa’",
    label: 'Octave',
    color: '#f43f5e',
    shrutis: [
      { name: "Sa’", ratio: '2/1', freq: 523.25, cents: 1200.0, desc: 'Tara Shadja (Octave Tonic)', pianoDiff: '0.0¢' },
    ],
  },
]

// Sample chant recordings available in project
const CHANT_SAMPLES = [
  {
    id: 'isavasya',
    title: 'Isavasya Upanishad (Ghana Patha)',
    tag: 'Permutation Chanting (1-2 2-1 1-2-3)',
    url: '/media/recordings/isavasya_ghanam_60s.wav',
    duration: '60s',
  },
  {
    id: 'sample',
    title: 'Rigvedic Chanting Test Sequence',
    tag: 'Continuous Pitch & Microtonal Shifts',
    url: '/media/recordings/test_10s.wav',
    duration: '10s',
  },
]

export default function AuthScreen({ apiBase, onAuthed, onGuest }) {
  const [viewMode, setViewMode] = useState('explorer') // 'explorer' | 'auth'

  // Interactive Keyboard State
  const [selectedFamily, setSelectedFamily] = useState(SWARA_FAMILIES[1]) // Re
  const [selectedShruti, setSelectedShruti] = useState(SWARA_FAMILIES[1].shrutis[1]) // Re²
  const [isPlayingSynth, setIsPlayingSynth] = useState(false)

  // Audio Player State for Chants
  const [activeChant, setActiveChant] = useState(null)
  const [isChantPlaying, setIsChantPlaying] = useState(false)
  const audioPlayerRef = useRef(null)

  // Auth Form State
  const [authTab, setAuthTab] = useState('login') // 'login' | 'register'
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState(null)
  const [authLoading, setAuthLoading] = useState(false)

  // Web Audio Context & Canvas
  const audioCtxRef = useRef(null)
  const analyserRef = useRef(null)
  const canvasRef = useRef(null)
  const animFrameRef = useRef(null)

  // ── Web Audio Synth Setup ──────────────────────────────────────────────────
  const getAudioContext = useCallback(() => {
    if (!audioCtxRef.current) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext
      const ctx = new AudioCtx()
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 512
      analyser.smoothingTimeConstant = 0.85
      analyser.connect(ctx.destination)

      audioCtxRef.current = ctx
      analyserRef.current = analyser
    }
    if (audioCtxRef.current.state === 'suspended') {
      audioCtxRef.current.resume()
    }
    return { ctx: audioCtxRef.current, analyser: analyserRef.current }
  }, [])

  // Play clean soft sine tone
  const playTone = useCallback((freq, duration = 0.45) => {
    try {
      const { ctx, analyser } = getAudioContext()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()

      osc.type = 'sine'
      osc.frequency.setValueAtTime(freq, ctx.currentTime)

      const now = ctx.currentTime
      gain.gain.setValueAtTime(0.0001, now)
      gain.gain.exponentialRampToValueAtTime(0.3, now + 0.03)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration)

      osc.connect(gain)
      gain.connect(analyser)

      osc.start(now)
      osc.stop(now + duration)

      setIsPlayingSynth(true)
      setTimeout(() => setIsPlayingSynth(false), duration * 1000)
    } catch (err) {
      console.warn('Synth error:', err)
    }
  }, [getAudioContext])

  // Audition 21.5 cent gap test (Re1 then Re2)
  const playMicrotoneGap = useCallback(() => {
    const re1 = SWARA_FAMILIES[1].shrutis[0] // Re1
    const re2 = SWARA_FAMILIES[1].shrutis[1] // Re2
    setSelectedFamily(SWARA_FAMILIES[1])
    setSelectedShruti(re1)
    playTone(re1.freq, 0.45)

    setTimeout(() => {
      setSelectedShruti(re2)
      playTone(re2.freq, 0.5)
    }, 500)
  }, [playTone])

  // ── Audio Player for Chant Samples ─────────────────────────────────────────
  const handleToggleChant = (sample) => {
    if (activeChant?.id === sample.id && isChantPlaying) {
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause()
        setIsChantPlaying(false)
      }
      return
    }

    setActiveChant(sample)
    setIsChantPlaying(true)
    if (audioPlayerRef.current) {
      audioPlayerRef.current.src = sample.url
      audioPlayerRef.current.play().catch(() => setIsChantPlaying(false))
    }
  }

  // ── Oscilloscope Canvas Animation ──────────────────────────────────────────
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let running = true
    let phase = 0

    const draw = () => {
      if (!running) return
      const width = canvas.width
      const height = canvas.height
      ctx.clearRect(0, 0, width, height)

      // Center guide line
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(0, height / 2)
      ctx.lineTo(width, height / 2)
      ctx.stroke()

      const analyser = analyserRef.current
      if (analyser && (isPlayingSynth || isChantPlaying)) {
        const bufferLength = analyser.fftSize
        const dataArray = new Uint8Array(bufferLength)
        analyser.getByteTimeDomainData(dataArray)

        ctx.lineWidth = 2.5
        ctx.strokeStyle = selectedShruti?.color || '#f43f5e'
        ctx.shadowColor = selectedShruti?.color || '#f43f5e'
        ctx.shadowBlur = 8
        ctx.beginPath()

        const sliceWidth = width / bufferLength
        let x = 0

        for (let i = 0; i < bufferLength; i++) {
          const v = dataArray[i] / 128.0
          const y = (v * height) / 2
          if (i === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
          x += sliceWidth
        }
        ctx.stroke()
        ctx.shadowBlur = 0
      } else {
        // Resting harmonic wave
        phase += 0.035
        ctx.lineWidth = 1.8
        ctx.strokeStyle = 'rgba(244, 63, 94, 0.4)'
        ctx.beginPath()
        for (let x = 0; x < width; x += 2) {
          const y = height / 2 + Math.sin(x * 0.035 + phase) * 6
          if (x === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        }
        ctx.stroke()
      }

      animFrameRef.current = requestAnimationFrame(draw)
    }

    draw()
    return () => {
      running = false
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
    }
  }, [isPlayingSynth, isChantPlaying, selectedShruti])

  useEffect(() => {
    return () => {
      if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
        audioCtxRef.current.close().catch(() => {})
      }
    }
  }, [])

  // ── Auth Form Submission ───────────────────────────────────────────────────
  const handleAuthSubmit = async (e) => {
    e.preventDefault()
    setAuthError(null)
    setAuthLoading(true)

    const endpoint = authTab === 'login' ? `${apiBase}/auth/login/` : `${apiBase}/auth/register/`
    const payload = authTab === 'login'
      ? { username, password }
      : { username, email, password }

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

      setAuth({ token: data.token, user: data.user })
      onAuthed(data.user)
    } catch (err) {
      setAuthError(`Connection error: ${err.message}`)
    } finally {
      setAuthLoading(false)
    }
  }

  return (
    <div className="portal-wrapper">
      {/* Hidden audio element for authentic chant playback */}
      <audio
        ref={audioPlayerRef}
        onEnded={() => setIsChantPlaying(false)}
        onError={() => setIsChantPlaying(false)}
        style={{ display: 'none' }}
      />

      {/* ── Minimal Top Navigation ────────────────────────────────────────── */}
      <header className="clean-nav">
        <div className="nav-brand">
          <span className="nav-logo-icon">🕉️</span>
          <div>
            <h1 className="nav-logo-text">Vedic Acoustica</h1>
            <span className="nav-status-badge">● Live Analysis Engine Ready</span>
          </div>
        </div>

        <div className="nav-actions">
          {viewMode === 'explorer' ? (
            <>
              <button type="button" className="btn btn-guest-hero" onClick={onGuest}>
                ⚡ Explore Live Dashboard (Guest)
              </button>
              <button type="button" className="btn btn-secondary-nav" onClick={() => setViewMode('auth')}>
                Sign In
              </button>
            </>
          ) : (
            <>
              <button type="button" className="nav-back-link" onClick={() => setViewMode('explorer')}>
                &larr; Back to Sound Explorer
              </button>
              <button type="button" className="btn btn-guest-hero" onClick={onGuest}>
                ⚡ Instant Guest Pass
              </button>
            </>
          )}
        </div>
      </header>

      {/* ═══════════════════════════════════════════════════════════════════════
          VIEW 1: Simple, Interactive Sound Explorer (Landing Page)
          ═══════════════════════════════════════════════════════════════════════ */}
      {viewMode === 'explorer' && (
        <main className="explorer-content">
          {/* Simple, Punchy Hero */}
          <section className="clean-hero">
            <h2 className="hero-title">
              Explore the Sound of <span className="hero-highlight">Vedic Chanting</span>
            </h2>
            <p className="hero-tagline">
              Interactive 22-Shruti microtonal tuning, real voice recordings, and ancient recitation analysis.
            </p>
            <div className="hero-buttons">
              <button type="button" className="btn btn-hero-primary" onClick={onGuest}>
                ⚡ Launch Live Research Dashboard (Instant Demo)
              </button>
              <a href="#interactive-keyboard" className="btn btn-hero-secondary">
                🎹 Play 22-Shruti Keyboard &darr;
              </a>
            </div>
          </section>

          {/* Interactive Keyboard Sandbox */}
          <section id="interactive-keyboard" className="interactive-card">
            <div className="card-header-clean">
              <div>
                <span className="pill-category">Interactive Tool</span>
                <h3 className="card-clean-title">22-Shruti Microtone Tuner</h3>
              </div>
              <button type="button" className="btn-audition-gap" onClick={playMicrotoneGap}>
                ▶ Listen: 21.5¢ Microtone Gap (Re¹ vs Re²)
              </button>
            </div>

            {/* Visualizer & Tuner Readout */}
            <div className="tuner-strip" style={{ borderColor: selectedShruti?.color }}>
              <div className="tuner-note-badge" style={{ background: selectedShruti?.color }}>
                {selectedShruti?.name}
              </div>

              <div className="tuner-info-col">
                <span className="tuner-desc">{selectedShruti?.desc}</span>
                <div className="tuner-metrics-row">
                  <span className="metric-tag">Frequency: <strong>{selectedShruti?.freq.toFixed(1)} Hz</strong></span>
                  <span className="metric-tag">Ratio: <strong>{selectedShruti?.ratio}</strong></span>
                  <span className="metric-tag">Cents: <strong>{selectedShruti?.cents.toFixed(1)}&cent;</strong></span>
                  <span className="metric-tag diff-tag">{selectedShruti?.pianoDiff}</span>
                </div>
              </div>

              <div className="tuner-wave-col">
                <canvas ref={canvasRef} width={280} height={50} className="tuner-canvas" />
                <span className="tuner-wave-label">
                  {isPlayingSynth ? '● Playing Pure Sine Wave' : 'Touch any note below'}
                </span>
              </div>
            </div>

            {/* 7 Swara Selector Keys */}
            <div className="swara-keys-bar" role="toolbar" aria-label="Select Swara">
              {SWARA_FAMILIES.map((family) => {
                const isSelected = selectedFamily.key === family.key
                return (
                  <button
                    key={family.key}
                    type="button"
                    className={`swara-main-key ${isSelected ? 'active' : ''}`}
                    style={{ '--key-accent': family.color }}
                    onClick={() => {
                      setSelectedFamily(family)
                      setSelectedShruti(family.shrutis[0])
                      playTone(family.shrutis[0].freq)
                    }}
                  >
                    <span className="swara-letter">{family.name}</span>
                    <span className="swara-subname">{family.label}</span>
                  </button>
                )
              })}
            </div>

            {/* Microtone Variants for Active Swara */}
            <div className="microtone-variants-box">
              <span className="variants-label">
                Microtonal variations of <strong>{selectedFamily.name}</strong> ({selectedFamily.shrutis.length} Shrutis):
              </span>
              <div className="variants-row">
                {selectedFamily.shrutis.map((shruti) => {
                  const isActive = selectedShruti?.name === shruti.name
                  return (
                    <button
                      key={shruti.name}
                      type="button"
                      className={`shruti-pill-btn ${isActive ? 'active' : ''}`}
                      style={{ '--shruti-color': selectedFamily.color }}
                      onClick={() => {
                        setSelectedShruti(shruti)
                        playTone(shruti.freq)
                      }}
                    >
                      <span className="pill-name">{shruti.name}</span>
                      <span className="pill-freq">{shruti.freq.toFixed(1)} Hz</span>
                      <span className="pill-ratio">({shruti.ratio})</span>
                    </button>
                  )
                })}
              </div>
            </div>
          </section>

          {/* Real Vedic Chant Audio Audition */}
          <section className="interactive-card">
            <div className="card-header-clean">
              <div>
                <span className="pill-category">Real Audio</span>
                <h3 className="card-clean-title">Listen to Vedic Chant Recordings</h3>
              </div>
              <span className="audio-status-pill">
                {isChantPlaying ? `▶ Playing ${activeChant?.title}` : 'Tap Play to Listen'}
              </span>
            </div>

            <div className="chant-cards-grid">
              {CHANT_SAMPLES.map((sample) => {
                const isPlayingThis = activeChant?.id === sample.id && isChantPlaying
                return (
                  <div key={sample.id} className={`chant-card ${isPlayingThis ? 'playing' : ''}`}>
                    <div className="chant-card-info">
                      <span className="chant-duration">{sample.duration} WAV</span>
                      <h4 className="chant-title">{sample.title}</h4>
                      <p className="chant-tag">{sample.tag}</p>
                    </div>

                    <button
                      type="button"
                      className={`btn-chant-play ${isPlayingThis ? 'playing' : ''}`}
                      onClick={() => handleToggleChant(sample)}
                    >
                      {isPlayingThis ? '⏸ Pause' : '▶ Play Chant'}
                    </button>
                  </div>
                )
              })}
            </div>
          </section>

          {/* 3 Simple Value Pillars (1-sentence each, no essays) */}
          <section className="clean-pillars-row">
            <div className="clean-pillar">
              <span className="pillar-emoji">🎯</span>
              <h4>22 Shrutis</h4>
              <p>Detects subtle vocal microtones that standard 12-key pianos cannot play.</p>
            </div>
            <div className="clean-pillar">
              <span className="pillar-emoji">🔁</span>
              <h4>Ghana Patha</h4>
              <p>Validates the sacred recitation order (1-2 2-1 1-2-3) with Dynamic Time Warping.</p>
            </div>
            <div className="clean-pillar">
              <span className="pillar-emoji">🎼</span>
              <h4>Raga Detection</h4>
              <p>Automatically identifies 44 Indian melodic modes using voice pitch AI.</p>
            </div>
          </section>

          {/* Bottom Call to Action */}
          <section className="bottom-cta-banner">
            <div>
              <h3>Ready to explore full spectrograms &amp; analyses?</h3>
              <p>Jump right into the research dashboard with pre-loaded recordings and charts.</p>
            </div>
            <div className="cta-btns-right">
              <button type="button" className="btn btn-hero-primary" onClick={onGuest}>
                ⚡ Launch Live Dashboard (Guest)
              </button>
              <button type="button" className="btn btn-secondary-nav" onClick={() => setViewMode('auth')}>
                Researcher Sign In &rarr;
              </button>
            </div>
          </section>
        </main>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════
          VIEW 2: Dedicated Clean Authentication Card
          ═══════════════════════════════════════════════════════════════════════ */}
      {viewMode === 'auth' && (
        <main className="auth-clean-viewport">
          <div className="auth-clean-card">
            <button type="button" className="btn-back-clean" onClick={() => setViewMode('explorer')}>
              &larr; Back to Sound Explorer
            </button>

            <div className="auth-card-head">
              <h2>Researcher Sign In</h2>
              <p>Sign in to upload audio and run customized analysis pipelines</p>
            </div>

            {/* Quick Guest Pass Callout */}
            <div className="guest-quick-box">
              <div>
                <strong>Just testing the app?</strong>
                <p>Skip credentials and view all live charts right away.</p>
              </div>
              <button type="button" className="btn btn-guest-hero" onClick={onGuest}>
                Guest Access &rarr;
              </button>
            </div>

            <div className="clean-divider">
              <span>OR LOG IN</span>
            </div>

            {/* Tabs */}
            <div className="clean-tabs">
              <button
                type="button"
                className={`clean-tab-btn ${authTab === 'login' ? 'active' : ''}`}
                onClick={() => { setAuthTab('login'); setAuthError(null) }}
              >
                Sign In
              </button>
              <button
                type="button"
                className={`clean-tab-btn ${authTab === 'register' ? 'active' : ''}`}
                onClick={() => { setAuthTab('register'); setAuthError(null) }}
              >
                Register
              </button>
            </div>

            {authError && (
              <div className="clean-error-alert" role="alert">
                ⚠️ {authError}
              </div>
            )}

            <form onSubmit={handleAuthSubmit} className="clean-form">
              <div className="clean-form-group">
                <label htmlFor="auth-user">Username</label>
                <input
                  id="auth-user"
                  type="text"
                  required
                  placeholder="Enter username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                />
              </div>

              {authTab === 'register' && (
                <div className="clean-form-group">
                  <label htmlFor="auth-email">Email (Optional)</label>
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
                <input
                  id="auth-pass"
                  type="password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete={authTab === 'login' ? 'current-password' : 'new-password'}
                />
              </div>

              <button type="submit" className="btn btn-submit-clean" disabled={authLoading}>
                {authLoading ? 'Signing In…' : (authTab === 'login' ? 'Sign In' : 'Create Account')}
              </button>
            </form>
          </div>
        </main>
      )}
    </div>
  )
}