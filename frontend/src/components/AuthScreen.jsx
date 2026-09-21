import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { setAuth } from '../utils/auth'
import './AuthScreen.css'

// 1:1 Canonical 23 Vedic Shruti definitions matching backend ml_engine/shruti_mapping.py
const SHRUTIS = [
  { name: 'Sa', ratio: '1/1', freq: 261.63, cents: 0.0, swara: 'Sa', color: '#e94560', title: 'Shadja (Tonic)' },
  { name: 'Re¹', ratio: '256/243', freq: 275.65, cents: 90.2, swara: 'Re', color: '#ff8c42', title: 'Eka-shruti Rishabh' },
  { name: 'Re²', ratio: '16/15', freq: 279.07, cents: 111.7, swara: 'Re', color: '#ff8c42', title: 'Dvi-shruti Rishabh' },
  { name: 'Re³', ratio: '10/9', freq: 290.70, cents: 182.4, swara: 'Re', color: '#ff8c42', title: 'Tri-shruti Rishabh' },
  { name: 'Re⁴', ratio: '9/8', freq: 294.33, cents: 203.9, swara: 'Re', color: '#ff8c42', title: 'Chatushruti Rishabh' },
  { name: 'Ga¹', ratio: '32/27', freq: 310.07, cents: 294.1, swara: 'Ga', color: '#ffd166', title: 'Shuddha Gandhar' },
  { name: 'Ga²', ratio: '6/5', freq: 313.95, cents: 315.6, swara: 'Ga', color: '#ffd166', title: 'Sadharana Gandhar' },
  { name: 'Ga³', ratio: '5/4', freq: 327.03, cents: 386.3, swara: 'Ga', color: '#ffd166', title: 'Antara Gandhar' },
  { name: 'Ga⁴', ratio: '81/64', freq: 331.14, cents: 407.8, swara: 'Ga', color: '#ffd166', title: 'Chyuta Madhyam' },
  { name: 'Ma¹', ratio: '4/3', freq: 348.84, cents: 498.0, swara: 'Ma', color: '#06d6a0', title: 'Shuddha Madhyam' },
  { name: 'Ma²', ratio: '27/20', freq: 353.20, cents: 519.6, swara: 'Ma', color: '#06d6a0', title: 'Tivra Madhyam (low)' },
  { name: 'Ma³', ratio: '45/32', freq: 367.91, cents: 590.2, swara: 'Ma', color: '#06d6a0', title: 'Prati Madhyam' },
  { name: 'Ma⁴', ratio: '729/512', freq: 372.51, cents: 611.7, swara: 'Ma', color: '#06d6a0', title: 'Tivratama Madhyam' },
  { name: 'Pa', ratio: '3/2', freq: 392.44, cents: 702.0, swara: 'Pa', color: '#118ab2', title: 'Pancham (Dominant)' },
  { name: 'Dha¹', ratio: '128/81', freq: 413.43, cents: 792.2, swara: 'Dha', color: '#8338ec', title: 'Shuddha Dhaivat' },
  { name: 'Dha²', ratio: '8/5', freq: 418.60, cents: 813.7, swara: 'Dha', color: '#8338ec', title: 'Komal Dhaivat' },
  { name: 'Dha³', ratio: '5/3', freq: 436.04, cents: 884.4, swara: 'Dha', color: '#8338ec', title: 'Trishruti Dhaivat' },
  { name: 'Dha⁴', ratio: '27/16', freq: 441.49, cents: 905.9, swara: 'Dha', color: '#8338ec', title: 'Chatushruti Dhaivat' },
  { name: 'Ni¹', ratio: '16/9', freq: 465.11, cents: 996.1, swara: 'Ni', color: '#ff006e', title: 'Komal Nishad' },
  { name: 'Ni²', ratio: '9/5', freq: 470.93, cents: 1017.6, swara: 'Ni', color: '#ff006e', title: 'Kaishiki Nishad' },
  { name: 'Ni³', ratio: '15/8', freq: 490.55, cents: 1088.3, swara: 'Ni', color: '#ff006e', title: 'Shuddha Nishad' },
  { name: 'Ni⁴', ratio: '243/128', freq: 496.71, cents: 1109.8, swara: 'Ni', color: '#ff006e', title: 'Kakali Nishad' },
  { name: 'Sa’', ratio: '2/1', freq: 523.25, cents: 1200.0, swara: 'Sa', color: '#e94560', title: 'Tara Shadja (Octave)' },
]

// Comparison demo pairs highlighting microtonal intervals
const MICROTONE_DEMOS = [
  {
    id: 're',
    label: 'Re¹ vs Re²',
    centsGap: '21.5¢ Pramana Shruti',
    first: 'Re¹',
    second: 'Re²',
    desc: 'Audition the 21.5¢ gap between Re¹ (275.65 Hz) and Re² (279.07 Hz). Standard 12-TET locks this into an artificial 100¢ semitone, missing the precise Vedic intonation.',
  },
  {
    id: 'ga',
    label: 'Ga³ vs Ga⁴',
    centsGap: '21.5¢ Microtone Gap',
    first: 'Ga³',
    second: 'Ga⁴',
    desc: 'Compare Antara Gandhar (327.03 Hz, 5/4 ratio) with Chyuta Madhyam (331.14 Hz, 81/64 ratio). Notice the subtle brightening of the harmonic overtone.',
  },
  {
    id: 'ma',
    label: 'Ma¹ vs Ma²',
    centsGap: '21.6¢ Shuddha Shift',
    first: 'Ma¹',
    second: 'Ma²',
    desc: 'Contrast Shuddha Madhyam (348.84 Hz, 4/3 ratio) with Tivra Madhyam-low (353.20 Hz, 27/20 ratio). This microtone defines traditional Carnatic and Samavedic chants.',
  },
]

export default function AuthScreen({ apiBase, onAuthed, onGuest }) {
  // Auth Form State
  const [tab, setTab] = useState('login') // 'login' | 'register'
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  // Web Audio Synthesizer State
  const [activeShruti, setActiveShruti] = useState(SHRUTIS[2]) // Default: Re²
  const [activeDemo, setActiveDemo] = useState(MICROTONE_DEMOS[0])
  const [isPlaying, setIsPlaying] = useState(false)

  const audioCtxRef = useRef(null)
  const analyserRef = useRef(null)
  const canvasRef = useRef(null)
  const animFrameRef = useRef(null)

  // ── Web Audio Synth Setup ──────────────────────────────────────────────────
  const getAudioContext = useCallback(() => {
    if (!audioCtxRef.current) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext
      const ctx = new AudioContextClass()
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 1024
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

  // Clean tone generation with soft ADSR sine envelope
  const playTone = useCallback((freq, duration = 0.45) => {
    try {
      const { ctx, analyser } = getAudioContext()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()

      osc.type = 'sine'
      osc.frequency.setValueAtTime(freq, ctx.currentTime)

      const now = ctx.currentTime
      gain.gain.setValueAtTime(0.0001, now)
      gain.gain.exponentialRampToValueAtTime(0.35, now + 0.04)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration)

      osc.connect(gain)
      gain.connect(analyser)

      osc.start(now)
      osc.stop(now + duration)
      setIsPlaying(true)
      setTimeout(() => setIsPlaying(false), duration * 1000)
    } catch (err) {
      console.warn('Web Audio synthesis error:', err)
    }
  }, [getAudioContext])

  const handleSelectShruti = useCallback((shruti) => {
    setActiveShruti(shruti)
    playTone(shruti.freq, 0.45)
  }, [playTone])

  // Sequentially audition two microtones for direct comparison
  const handleAuditionDemo = useCallback((demo) => {
    setActiveDemo(demo)
    const s1 = SHRUTIS.find(s => s.name === demo.first)
    const s2 = SHRUTIS.find(s => s.name === demo.second)
    if (!s1 || !s2) return

    setActiveShruti(s1)
    playTone(s1.freq, 0.4)

    setTimeout(() => {
      setActiveShruti(s2)
      playTone(s2.freq, 0.45)
    }, 450)
  }, [playTone])

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

      // Center baseline
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.08)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(0, height / 2)
      ctx.lineTo(width, height / 2)
      ctx.stroke()

      const analyser = analyserRef.current
      if (analyser && isPlaying) {
        const bufferLength = analyser.fftSize
        const dataArray = new Uint8Array(bufferLength)
        analyser.getByteTimeDomainData(dataArray)

        ctx.lineWidth = 2.5
        ctx.strokeStyle = activeShruti?.color || '#06d6a0'
        ctx.shadowColor = activeShruti?.color || '#06d6a0'
        ctx.shadowBlur = 10
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
        // Subtle resting harmonic sine wave
        phase += 0.035
        ctx.lineWidth = 1.8
        ctx.strokeStyle = 'rgba(233, 69, 96, 0.5)'
        ctx.shadowColor = 'rgba(233, 69, 96, 0.2)'
        ctx.shadowBlur = 4
        ctx.beginPath()
        for (let x = 0; x < width; x += 2) {
          const y = height / 2 + Math.sin(x * 0.035 + phase) * 7
          if (x === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        }
        ctx.stroke()
        ctx.shadowBlur = 0
      }

      animFrameRef.current = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      running = false
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current)
    }
  }, [isPlaying, activeShruti])

  // Cleanup Web Audio context on unmount
  useEffect(() => {
    return () => {
      if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
        audioCtxRef.current.close().catch(() => {})
      }
    }
  }, [])

  // ── Swara Category Grouping ────────────────────────────────────────────────
  const swaraGroups = useMemo(() => [
    { key: 'Sa', label: 'Sa', color: '#e94560', notes: SHRUTIS.filter(s => s.swara === 'Sa' && s.name === 'Sa') },
    { key: 'Re', label: 'Re', color: '#ff8c42', notes: SHRUTIS.filter(s => s.swara === 'Re') },
    { key: 'Ga', label: 'Ga', color: '#ffd166', notes: SHRUTIS.filter(s => s.swara === 'Ga') },
    { key: 'Ma', label: 'Ma', color: '#06d6a0', notes: SHRUTIS.filter(s => s.swara === 'Ma') },
    { key: 'Pa', label: 'Pa', color: '#118ab2', notes: SHRUTIS.filter(s => s.swara === 'Pa') },
    { key: 'Dha', label: 'Dha', color: '#8338ec', notes: SHRUTIS.filter(s => s.swara === 'Dha') },
    { key: 'Ni', label: 'Ni', color: '#ff006e', notes: SHRUTIS.filter(s => s.swara === 'Ni') },
    { key: 'Sa’', label: "Sa’", color: '#e94560', notes: SHRUTIS.filter(s => s.name === "Sa’") },
  ], [])

  // ── Auth Form Handlers ─────────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    const endpoint = tab === 'login' ? `${apiBase}/auth/login/` : `${apiBase}/auth/register/`
    const payload = tab === 'login'
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
        setError(msg)
        return
      }

      setAuth(data.token, data.user)
      onAuthed(data.user)
    } catch (err) {
      setError(`Connection error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      {/* Top Application Header matching inside layout exactly */}
      <div className="auth-header">
        <h1>Vedic Acoustica</h1>
        <p className="subtitle">
          Microtonal Voice Analysis &middot; 22 Shrutis &middot; Raga Detection &middot; Ghana Patha Validation
        </p>

        <div className="status-bar">
          <span className="dot"></span>
          {window.location.hostname === 'localhost' ? 'Backend: localhost:8000 (Connected)' : '● Backend Connected'}
          <span className="auth-portal-badge">Research Portal v2.0 &middot; Microtonal Acoustic Gateway</span>
        </div>
      </div>

      {/* Main Expanded 2-Column Desktop Grid */}
      <div className="auth-grid">
        {/* ── LEFT COLUMN: Interactive Acoustic Lab & 22-Shruti Synthesizer ── */}
        <div className="auth-col-left">
          <div className="card acoustic-lab-card">
            <div className="lab-header">
              <h2>22-Shruti Microtonal Acoustic Explorer</h2>
              <span className="live-badge">⚡ Real-time Web Audio</span>
            </div>
            <p className="lab-desc">
              Vedic chanting relies on natural harmonic Just Intonation ratios rather than Western 12-TET equal temperament.
              Tap any Swara below to play its exact frequency and inspect its acoustic sinusoidal waveform.
            </p>

            {/* Live Tuner & Oscilloscope Card */}
            <div className="tuner-monitor" style={{ borderColor: activeShruti?.color }}>
              <div className="tuner-top-row">
                <div className="tuner-note-info">
                  <span className="tuner-swara-tag" style={{ background: activeShruti?.color }}>
                    {activeShruti?.name}
                  </span>
                  <div>
                    <h3 className="tuner-title">{activeShruti?.title}</h3>
                    <span className="tuner-ratio-pill">Ratio: {activeShruti?.ratio}</span>
                  </div>
                </div>

                <div className="tuner-readout-metrics">
                  <div className="metric-box">
                    <span className="metric-lbl">Frequency</span>
                    <span className="metric-num">{activeShruti?.freq.toFixed(2)} <span className="metric-unit">Hz</span></span>
                  </div>
                  <div className="metric-box">
                    <span className="metric-lbl">Microtone Cents</span>
                    <span className="metric-num">{activeShruti?.cents.toFixed(1)} <span className="metric-unit">&cent;</span></span>
                  </div>
                </div>
              </div>

              {/* Real-time Oscilloscope Display */}
              <div className="oscilloscope-wrap">
                <canvas ref={canvasRef} width={500} height={70} className="oscilloscope-canvas" />
                <span className="oscilloscope-label">
                  {isPlaying ? '● Audio Active (Sine Wave)' : 'Ambient Standby'}
                </span>
              </div>
            </div>

            {/* Microtone Comparison Quick-Audition Bar */}
            <div className="microtone-audition-section">
              <div className="audition-header">
                <span className="audition-title">🔬 Microtone Audition Tests (Hear the Vedic Difference):</span>
              </div>
              <div className="audition-buttons">
                {MICROTONE_DEMOS.map(demo => {
                  const isSelected = activeDemo?.id === demo.id
                  return (
                    <button
                      key={demo.id}
                      type="button"
                      className={`audition-btn ${isSelected ? 'active' : ''}`}
                      onClick={() => handleAuditionDemo(demo)}
                    >
                      <span className="audition-btn-icon">▶</span>
                      <span className="audition-btn-name">{demo.label}</span>
                      <span className="audition-btn-gap">({demo.centsGap})</span>
                    </button>
                  )
                })}
              </div>
              {activeDemo && (
                <div className="audition-insight-box">
                  <p className="audition-insight-text">
                    <strong>{activeDemo.label} ({activeDemo.centsGap}):</strong> {activeDemo.desc}
                  </p>
                </div>
              )}
            </div>

            {/* 22-Shruti Swara Groups Keyboard */}
            <div className="swara-groups-container">
              <div className="swara-groups-header">
                <span className="swara-groups-title">Canonical 23-Bin Shruti Keyboard (C4 Tonic = 261.63 Hz):</span>
              </div>

              <div className="swara-groups-grid">
                {swaraGroups.map(group => (
                  <div key={group.key} className="swara-group-col">
                    <span className="swara-group-tag" style={{ color: group.color, borderColor: group.color }}>
                      {group.label}
                    </span>
                    <div className="swara-buttons-stack">
                      {group.notes.map(s => {
                        const isCurrent = activeShruti?.name === s.name
                        return (
                          <button
                            key={s.name}
                            type="button"
                            className={`shruti-btn ${isCurrent ? 'active' : ''}`}
                            style={{
                              '--shruti-col': s.color,
                              borderColor: isCurrent ? s.color : 'rgba(255,255,255,0.12)',
                            }}
                            onClick={() => handleSelectShruti(s)}
                            title={`${s.name} (${s.title}): ${s.freq} Hz, ${s.ratio}, ${s.cents}¢`}
                          >
                            <span className="shruti-btn-name">{s.name}</span>
                            <span className="shruti-btn-freq">{Math.round(s.freq)} Hz</span>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Research Architecture Highlights Preview */}
            <div className="pipeline-preview-row">
              <div className="pipeline-pill">
                <span className="pipeline-icon">🎙️</span>
                <div>
                  <strong>pYIN Pitch Tracking</strong>
                  <p>Probabilistic YIN F0 extraction with sub-semitone pitch estimation</p>
                </div>
              </div>
              <div className="pipeline-pill">
                <span className="pipeline-icon">📊</span>
                <div>
                  <strong>22-Shruti PCP</strong>
                  <p>Harmonic energy mapped into 23 non-linear Just Intonation bins</p>
                </div>
              </div>
              <div className="pipeline-pill">
                <span className="pipeline-icon">⚡</span>
                <div>
                  <strong>Ghana Patha DTW</strong>
                  <p>Dynamic Time Warping for Vedic chant permutation validation</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* ── RIGHT COLUMN: Access Gateway & Authentication ── */}
        <div className="auth-col-right">
          {/* Prominent Instant Guest Pass Card */}
          <div className="card guest-access-card">
            <div className="guest-badge-row">
              <span className="guest-pass-tag">⚡ Immediate Evaluator Pass</span>
              <span className="guest-badge-free">No Credentials Needed</span>
            </div>

            <h2 className="guest-card-title">Explore Live Research Dashboard</h2>
            <p className="guest-card-desc">
              Jump straight into the platform with 3 pre-loaded Vedic chant recordings and pre-computed analytical models:
            </p>

            <ul className="guest-perks-list">
              <li>
                <span className="perk-check">✓</span>
                <span>Interactive <strong>Time-Frequency Spectrogram</strong> with live F0 tracking</span>
              </li>
              <li>
                <span className="perk-check">✓</span>
                <span><strong>22-Shruti Thermal Heatmap</strong> & Cent deviation histogram</span>
              </li>
              <li>
                <span className="perk-check">✓</span>
                <span><strong>44-Raga Classifier</strong> with multi-scale probability ranks</span>
              </li>
              <li>
                <span className="perk-check">✓</span>
                <span><strong>Ghana Patha Permutation DTW</strong> alignment matrix</span>
              </li>
            </ul>

            <button
              type="button"
              className="btn guest-primary-btn"
              onClick={onGuest}
            >
              <span>Explore as Guest (Instant Access) &rarr;</span>
            </button>
          </div>

          {/* Regular Researcher Sign In / Register Card */}
          <div className="card researcher-auth-card">
            <div className="auth-tabs">
              <button
                type="button"
                className={`auth-tab-btn ${tab === 'login' ? 'active' : ''}`}
                onClick={() => { setTab('login'); setError(null) }}
              >
                Sign In
              </button>
              <button
                type="button"
                className={`auth-tab-btn ${tab === 'register' ? 'active' : ''}`}
                onClick={() => { setTab('register'); setError(null) }}
              >
                Create Account
              </button>
            </div>

            {error && (
              <div className="auth-error-banner" role="alert">
                <span>⚠️ {error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="auth-form">
              <div className="form-group">
                <label htmlFor="auth-username">Researcher Username</label>
                <div className="input-wrap">
                  <span className="input-icon">👤</span>
                  <input
                    id="auth-username"
                    type="text"
                    required
                    placeholder="Enter your username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="username"
                  />
                </div>
              </div>

              {tab === 'register' && (
                <div className="form-group">
                  <label htmlFor="auth-email">Academic / Institutional Email</label>
                  <div className="input-wrap">
                    <span className="input-icon">✉️</span>
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
                </div>
              )}

              <div className="form-group">
                <label htmlFor="auth-password">Password</label>
                <div className="input-wrap">
                  <span className="input-icon">🔒</span>
                  <input
                    id="auth-password"
                    type="password"
                    required
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete={tab === 'login' ? 'current-password' : 'new-password'}
                  />
                </div>
              </div>

              <button
                type="submit"
                className="btn auth-submit-btn"
                disabled={loading}
              >
                {loading ? (
                  <><span className="loading-spinner" /> Authenticating…</>
                ) : (
                  tab === 'login' ? 'Sign In to Portal' : 'Register Account'
                )}
              </button>
            </form>

            <div className="auth-specs-footer">
              <span>Stack: Python 3.12 &middot; Django 5.1 &middot; PyTorch &middot; Librosa &middot; React</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}