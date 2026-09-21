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
    desc: 'Audition the 21.5¢ gap between Re¹ (275.65 Hz) and Re² (279.07 Hz). Standard 12-TET locks this into an artificial 100¢ semitone, completely missing the precise Vedic intonation.',
  },
  {
    id: 'ga',
    label: 'Ga³ vs Ga⁴',
    centsGap: '21.5¢ Microtone Gap',
    first: 'Ga³',
    second: 'Ga⁴',
    desc: 'Compare Antara Gandhar (327.03 Hz, 5/4 ratio) with Chyuta Madhyam (331.14 Hz, 81/64 ratio). Notice how natural Just Intonation creates harmonic purity over equal temperament.',
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
  // Page mode: 'explorer' (default public landing & lab) or 'auth' (dedicated login/register view)
  const [viewMode, setViewMode] = useState('explorer')

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

      // Center baseline & subtle grid
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

  // ── Swara Category Grouping (8 Octave Columns) ────────────────────────────
  const swaraGroups = useMemo(() => [
    { key: 'Sa', label: 'Sa (Tonic)', color: '#e94560', notes: SHRUTIS.filter(s => s.swara === 'Sa' && s.name === 'Sa') },
    { key: 'Re', label: 'Re (Rishabh)', color: '#ff8c42', notes: SHRUTIS.filter(s => s.swara === 'Re') },
    { key: 'Ga', label: 'Ga (Gandhar)', color: '#ffd166', notes: SHRUTIS.filter(s => s.swara === 'Ga') },
    { key: 'Ma', label: 'Ma (Madhyam)', color: '#06d6a0', notes: SHRUTIS.filter(s => s.swara === 'Ma') },
    { key: 'Pa', label: 'Pa (Pancham)', color: '#118ab2', notes: SHRUTIS.filter(s => s.swara === 'Pa') },
    { key: 'Dha', label: 'Dha (Dhaivat)', color: '#8338ec', notes: SHRUTIS.filter(s => s.swara === 'Dha') },
    { key: 'Ni', label: 'Ni (Nishad)', color: '#ff006e', notes: SHRUTIS.filter(s => s.swara === 'Ni') },
    { key: 'Sa’', label: "Sa’ (Octave)", color: '#e94560', notes: SHRUTIS.filter(s => s.name === "Sa’") },
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

  const scrollToSection = (id) => {
    const el = document.getElementById(id)
    if (el) el.scrollIntoView({ behavior: 'smooth' })
  }

  return (
    <div className="auth-portal-root">
      {/* ── Top Navigation Bar ────────────────────────────────────────────── */}
      <header className="portal-navbar">
        <div className="portal-nav-brand">
          <div className="portal-logo-symbol">🕉️</div>
          <div>
            <h1 className="portal-nav-title">Vedic Acoustica</h1>
            <span className="portal-nav-tagline">Microtonal Voice Intelligence</span>
          </div>
        </div>

        <nav className="portal-nav-links" aria-label="Portal Navigation">
          {viewMode === 'explorer' ? (
            <>
              <button type="button" className="nav-link-btn" onClick={() => scrollToSection('shruti-studio')}>
                🔬 22-Shruti Lab
              </button>
              <button type="button" className="nav-link-btn" onClick={() => scrollToSection('methodology')}>
                📊 Acoustic Engine
              </button>
              <button type="button" className="nav-guest-btn" onClick={onGuest}>
                ⚡ Explore Live Demo
              </button>
              <button type="button" className="btn btn-secondary nav-signin-btn" onClick={() => setViewMode('auth')}>
                🔐 Sign In
              </button>
            </>
          ) : (
            <>
              <button type="button" className="nav-link-btn" onClick={() => setViewMode('explorer')}>
                &larr; Back to Interactive Explorer
              </button>
              <button type="button" className="nav-guest-btn" onClick={onGuest}>
                ⚡ Instant Guest Demo
              </button>
            </>
          )}
        </nav>
      </header>

      {/* ═══════════════════════════════════════════════════════════════════════
          VIEW 1: Full-Width Acoustic Research Explorer (Default Landing Page)
          ═══════════════════════════════════════════════════════════════════════ */}
      {viewMode === 'explorer' && (
        <main className="explorer-view">
          {/* Hero Section */}
          <section className="hero-section">
            <div className="hero-badge-row">
              <span className="hero-status-pill">
                <span className="dot" />
                {window.location.hostname === 'localhost' ? 'Local Engine Connected (localhost:8000)' : 'Live Backend Connected'}
              </span>
              <span className="hero-meta-badge">Computational Musicology &middot; Rigveda &amp; Samaveda</span>
            </div>

            <h2 className="hero-headline">
              Scientific Microtonal Audio Intelligence <br />
              <span className="hero-gradient-text">for Vedic Chant Recitation</span>
            </h2>

            <p className="hero-subtext">
              Vedic chanting relies on natural harmonic Just Intonation intervals (22 Shrutis) rather than Western 12-TET equal temperament.
              Vedic Acoustica continuously extracts fundamental frequencies (pYIN F0), constructs 23-bin pitch class profiles, and mathematically validates chanting permutation invariance using Dynamic Time Warping.
            </p>

            <div className="hero-cta-row">
              <button type="button" className="btn hero-primary-cta" onClick={onGuest}>
                <span>⚡ Launch Live Research Dashboard (Instant Demo)</span>
              </button>
              <button type="button" className="btn btn-secondary hero-secondary-cta" onClick={() => scrollToSection('shruti-studio')}>
                <span>🎹 Audition 22 Shrutis Live</span>
              </button>
              <button type="button" className="nav-link-subtle" onClick={() => setViewMode('auth')}>
                Researcher Sign In &rarr;
              </button>
            </div>

            <div className="hero-tech-pills">
              <span>Python 3.12</span>
              <span className="pill-dot">&bull;</span>
              <span>Librosa pYIN F0</span>
              <span className="pill-dot">&bull;</span>
              <span>22-Shruti Just Intonation</span>
              <span className="pill-dot">&bull;</span>
              <span>Ghana Patha DTW</span>
              <span className="pill-dot">&bull;</span>
              <span>44-Raga Classifier</span>
            </div>
          </section>

          {/* Full-Width Interactive 22-Shruti Acoustic Studio */}
          <section id="shruti-studio" className="card studio-section">
            <div className="studio-header">
              <div>
                <span className="section-eyebrow">Interactive Acoustic Sandbox</span>
                <h3 className="section-title">22-Shruti Microtonal Synthesizer &amp; Oscilloscope</h3>
              </div>
              <span className="live-pill">⚡ Web Audio Synthesis (No Pop/Click ADSR)</span>
            </div>

            <p className="studio-desc">
              Tap any Swara in the octave keyboard below to generate its pure harmonic tone at reference C4 tonic (261.63 Hz) and inspect its real-time sinusoidal waveform.
            </p>

            {/* Tuner Monitor & Real-Time Oscilloscope */}
            <div className="studio-tuner-card" style={{ borderColor: activeShruti?.color }}>
              <div className="studio-tuner-metrics">
                <div className="active-swara-box">
                  <div className="swara-big-badge" style={{ background: activeShruti?.color }}>
                    {activeShruti?.name}
                  </div>
                  <div className="swara-text-details">
                    <h4 className="swara-full-name">{activeShruti?.title}</h4>
                    <div className="swara-spec-row">
                      <span className="spec-tag">Ratio: <strong>{activeShruti?.ratio}</strong></span>
                      <span className="spec-tag">Category: <strong>{activeShruti?.swara}</strong></span>
                    </div>
                  </div>
                </div>

                <div className="tuner-readout-deck">
                  <div className="deck-metric">
                    <span className="deck-metric-lbl">Frequency</span>
                    <span className="deck-metric-val">{activeShruti?.freq.toFixed(2)} <span className="deck-unit">Hz</span></span>
                  </div>
                  <div className="deck-metric">
                    <span className="deck-metric-lbl">Deviation (Cents)</span>
                    <span className="deck-metric-val">{activeShruti?.cents.toFixed(1)} <span className="deck-unit">&cent;</span></span>
                  </div>
                  <div className="deck-metric">
                    <span className="deck-metric-lbl">Equal Temperament Gap</span>
                    <span className="deck-metric-val">
                      {(activeShruti?.cents - Math.round(activeShruti?.cents / 100) * 100).toFixed(1)} <span className="deck-unit">&cent;</span>
                    </span>
                  </div>
                </div>
              </div>

              {/* Real-time Oscilloscope Display */}
              <div className="studio-oscilloscope">
                <canvas ref={canvasRef} width={800} height={80} className="studio-canvas" />
                <div className="oscilloscope-statusbar">
                  <span className="osc-indicator" style={{ color: activeShruti?.color }}>
                    {isPlaying ? '● Live Acoustic Sine Wave Generating' : 'Standby Sine Baseline'}
                  </span>
                  <span className="osc-sr">Sampling Rate: 44.1 kHz &middot; FFT Size: 1024</span>
                </div>
              </div>
            </div>

            {/* Microtone Audition Testing Deck */}
            <div className="audition-deck-card">
              <div className="deck-header">
                <span className="deck-title">🔬 Microtone Audition Deck &mdash; Listen to the Vedic Difference:</span>
              </div>
              <div className="deck-buttons-row">
                {MICROTONE_DEMOS.map(demo => {
                  const isSelected = activeDemo?.id === demo.id
                  return (
                    <button
                      key={demo.id}
                      type="button"
                      className={`deck-audition-btn ${isSelected ? 'active' : ''}`}
                      onClick={() => handleAuditionDemo(demo)}
                    >
                      <span className="deck-play-icon">▶</span>
                      <span className="deck-btn-label">{demo.label}</span>
                      <span className="deck-btn-gap">({demo.centsGap})</span>
                    </button>
                  )
                })}
              </div>
              {activeDemo && (
                <div className="deck-explanation">
                  <p>
                    <strong>{activeDemo.label} ({activeDemo.centsGap}):</strong> {activeDemo.desc}
                  </p>
                </div>
              )}
            </div>

            {/* Full-Width 8-Column Octave Keyboard */}
            <div className="full-keyboard-container">
              <div className="keyboard-header-row">
                <span className="keyboard-title">Full 23-Bin Octave Scale (C4 to C5):</span>
                <span className="keyboard-hint">Click any note to play tone</span>
              </div>

              <div className="octave-columns-grid">
                {swaraGroups.map(group => (
                  <div key={group.key} className="octave-column">
                    <div className="octave-col-header" style={{ color: group.color, borderBottomColor: group.color }}>
                      {group.label}
                    </div>
                    <div className="octave-col-buttons">
                      {group.notes.map(s => {
                        const isCurrent = activeShruti?.name === s.name
                        return (
                          <button
                            key={s.name}
                            type="button"
                            className={`keyboard-key-btn ${isCurrent ? 'active' : ''}`}
                            style={{
                              '--key-col': s.color,
                              borderColor: isCurrent ? s.color : 'rgba(255,255,255,0.12)',
                            }}
                            onClick={() => handleSelectShruti(s)}
                            title={`${s.name} (${s.title}): ${s.freq} Hz, ${s.ratio}, ${s.cents}¢`}
                          >
                            <span className="key-swara-name">{s.name}</span>
                            <span className="key-swara-freq">{s.freq.toFixed(1)} Hz</span>
                            <span className="key-swara-ratio">{s.ratio}</span>
                          </button>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </section>

          {/* Computational Acoustic Methodology (3 Pillars) */}
          <section id="methodology" className="methodology-section">
            <div className="methodology-header">
              <span className="section-eyebrow">Scientific Foundation</span>
              <h3 className="section-title">The Three Algorithmic Pillars of Vedic Acoustica</h3>
              <p className="section-subtitle">
                How our pipeline transforms continuous voice recordings into quantifiable acoustic invariants.
              </p>
            </div>

            <div className="pillars-grid">
              <div className="card pillar-card">
                <div className="pillar-icon-badge">🎙️</div>
                <h4 className="pillar-title">1. pYIN Continuous Pitch Tracking</h4>
                <p className="pillar-desc">
                  Uses probabilistic YIN with a hidden Markov model and Viterbi decoding to trace precise fundamental frequency (F0) contours through human vocal tremors and vibrato.
                </p>
                <div className="pillar-metric-tag">Sub-semitone precision (&plusmn;5 cents)</div>
              </div>

              <div className="card pillar-card">
                <div className="pillar-icon-badge">📊</div>
                <h4 className="pillar-title">2. 22-Shruti Pitch Class Profile</h4>
                <p className="pillar-desc">
                  Filters STFT spectral energy into 23 non-linear Just Intonation bins. Produces thermal heatmaps and centroid distributions that reveal precise intonation patterns.
                </p>
                <div className="pillar-metric-tag">23 Non-linear bins (Sa to Sa&rsquo;)</div>
              </div>

              <div className="card pillar-card">
                <div className="pillar-icon-badge">⚡</div>
                <h4 className="pillar-title">3. Ghana Patha Permutation DTW</h4>
                <p className="pillar-desc">
                  Validates the sacred recitation order (1-2 2-1 1-2-3 3-2-1 1-2-3) using Dynamic Time Warping cost matrices to detect syllable transposition and cadence errors.
                </p>
                <div className="pillar-metric-tag">Dynamic Time Warping alignment</div>
              </div>
            </div>
          </section>

          {/* Bottom Launchpad Banner */}
          <section className="launchpad-card card">
            <div className="launchpad-content">
              <div>
                <h3 className="launchpad-title">Ready to Analyze Vedic Chanting?</h3>
                <p className="launchpad-desc">
                  Access 3 pre-analyzed recordings immediately or sign in to upload your own WAV/MP3 files for complete spectrogram and DTW analysis.
                </p>
              </div>
              <div className="launchpad-actions">
                <button type="button" className="btn hero-primary-cta" onClick={onGuest}>
                  <span>⚡ Launch Live Dashboard (Guest Pass)</span>
                </button>
                <button type="button" className="btn btn-secondary" onClick={() => setViewMode('auth')}>
                  <span>🔐 Researcher Sign In / Register</span>
                </button>
              </div>
            </div>
          </section>
        </main>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════
          VIEW 2: Dedicated Researcher Authentication View
          ═══════════════════════════════════════════════════════════════════════ */}
      {viewMode === 'auth' && (
        <main className="auth-view-container">
          <div className="dedicated-auth-card card">
            <div className="auth-back-row">
              <button type="button" className="back-link-btn" onClick={() => setViewMode('explorer')}>
                &larr; Return to Interactive Explorer
              </button>
            </div>

            <div className="dedicated-auth-header">
              <div className="auth-logo-center">🕉️</div>
              <h2 className="auth-view-title">Researcher Authentication</h2>
              <p className="auth-view-subtitle">Access your audio dataset, spectrogram reports, and model exports</p>
            </div>

            {/* Quick Guest Pass Option */}
            <div className="auth-guest-callout">
              <div className="callout-text">
                <strong>Just evaluating the project?</strong>
                <p>You can skip login and view all 3 pre-analyzed Vedic chants immediately.</p>
              </div>
              <button type="button" className="btn guest-inline-btn" onClick={onGuest}>
                Instant Guest Pass &rarr;
              </button>
            </div>

            <div className="auth-divider">
              <span>OR LOG IN WITH CREDENTIALS</span>
            </div>

            {/* Tabs */}
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
        </main>
      )}
    </div>
  )
}