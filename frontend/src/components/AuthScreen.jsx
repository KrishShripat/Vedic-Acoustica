import { useState, useRef, useEffect, useCallback, useMemo } from 'react'
import { setAuth } from '../utils/auth'
import './AuthScreen.css'

// ── Canonical 23 Vedic Shruti definitions (1:1 with backend ml_engine/shruti_mapping.py) ──
const SHRUTIS = [
  { name: 'Sa', ratio: '1/1', freq: 261.63, cents: 0.0, swara: 'Sa', color: '#f43f5e', title: 'Shadja (Tonic)', devanagari: 'षड्ज', tetFreq: 261.63, tetDiff: 0 },
  { name: 'Re¹', ratio: '256/243', freq: 275.65, cents: 90.2, swara: 'Re', color: '#f97316', title: 'Eka-shruti Rishabh', devanagari: 'एक-श्रुति ऋषभ', tetFreq: 277.18, tetDiff: -9.8 },
  { name: 'Re²', ratio: '16/15', freq: 279.07, cents: 111.7, swara: 'Re', color: '#f97316', title: 'Dvi-shruti Rishabh', devanagari: 'द्वि-श्रुति ऋषभ', tetFreq: 277.18, tetDiff: +11.7 },
  { name: 'Re³', ratio: '10/9', freq: 290.70, cents: 182.4, swara: 'Re', color: '#f97316', title: 'Tri-shruti Rishabh', devanagari: 'त्रि-श्रुति ऋषभ', tetFreq: 293.66, tetDiff: -17.6 },
  { name: 'Re⁴', ratio: '9/8', freq: 294.33, cents: 203.9, swara: 'Re', color: '#f97316', title: 'Chatushruti Rishabh', devanagari: 'चतुःश्रुति ऋषभ', tetFreq: 293.66, tetDiff: +3.9 },
  { name: 'Ga¹', ratio: '32/27', freq: 310.07, cents: 294.1, swara: 'Ga', color: '#eab308', title: 'Shuddha Gandhar', devanagari: 'शुद्ध गान्धार', tetFreq: 311.13, tetDiff: -5.9 },
  { name: 'Ga²', ratio: '6/5', freq: 313.95, cents: 315.6, swara: 'Ga', color: '#eab308', title: 'Sadharana Gandhar', devanagari: 'साधारण गान्धार', tetFreq: 311.13, tetDiff: +15.6 },
  { name: 'Ga³', ratio: '5/4', freq: 327.03, cents: 386.3, swara: 'Ga', color: '#eab308', title: 'Antara Gandhar', devanagari: 'अन्तर गान्धार', tetFreq: 329.63, tetDiff: -13.7 },
  { name: 'Ga⁴', ratio: '81/64', freq: 331.14, cents: 407.8, swara: 'Ga', color: '#eab308', title: 'Chyuta Madhyam', devanagari: 'च्युत मध्यम', tetFreq: 329.63, tetDiff: +7.8 },
  { name: 'Ma¹', ratio: '4/3', freq: 348.84, cents: 498.0, swara: 'Ma', color: '#10b981', title: 'Shuddha Madhyam', devanagari: 'शुद्ध मध्यम', tetFreq: 349.23, tetDiff: -2.0 },
  { name: 'Ma²', ratio: '27/20', freq: 353.20, cents: 519.6, swara: 'Ma', color: '#10b981', title: 'Tivra Madhyam (low)', devanagari: 'मृदु तीव्र मध्यम', tetFreq: 349.23, tetDiff: +19.6 },
  { name: 'Ma³', ratio: '45/32', freq: 367.91, cents: 590.2, swara: 'Ma', color: '#10b981', title: 'Prati Madhyam', devanagari: 'प्रति मध्यम', tetFreq: 369.99, tetDiff: -9.8 },
  { name: 'Ma⁴', ratio: '729/512', freq: 372.51, cents: 611.7, swara: 'Ma', color: '#10b981', title: 'Tivratama Madhyam', devanagari: 'तीव्रतम मध्यम', tetFreq: 369.99, tetDiff: +11.7 },
  { name: 'Pa', ratio: '3/2', freq: 392.44, cents: 702.0, swara: 'Pa', color: '#06b6d4', title: 'Pancham (Dominant)', devanagari: 'पञ्चम', tetFreq: 392.00, tetDiff: +2.0 },
  { name: 'Dha¹', ratio: '128/81', freq: 413.43, cents: 792.2, swara: 'Dha', color: '#8b5cf6', title: 'Shuddha Dhaivat', devanagari: 'शुद्ध धैवत', tetFreq: 415.30, tetDiff: -7.8 },
  { name: 'Dha²', ratio: '8/5', freq: 418.60, cents: 813.7, swara: 'Dha', color: '#8b5cf6', title: 'Komal Dhaivat', devanagari: 'कोमल धैवत', tetFreq: 415.30, tetDiff: +13.7 },
  { name: 'Dha³', ratio: '5/3', freq: 436.04, cents: 884.4, swara: 'Dha', color: '#8b5cf6', title: 'Trishruti Dhaivat', devanagari: 'त्रि-श्रुति धैवत', tetFreq: 440.00, tetDiff: -15.6 },
  { name: 'Dha⁴', ratio: '27/16', freq: 441.49, cents: 905.9, swara: 'Dha', color: '#8b5cf6', title: 'Chatushruti Dhaivat', devanagari: 'चतुःश्रुति धैवत', tetFreq: 440.00, tetDiff: +5.9 },
  { name: 'Ni¹', ratio: '16/9', freq: 465.11, cents: 996.1, swara: 'Ni', color: '#ec4899', title: 'Komal Nishad', devanagari: 'कोमल निषाद', tetFreq: 466.16, tetDiff: -3.9 },
  { name: 'Ni²', ratio: '9/5', freq: 470.93, cents: 1017.6, swara: 'Ni', color: '#ec4899', title: 'Kaishiki Nishad', devanagari: 'कैशिकी निषाद', tetFreq: 466.16, tetDiff: +17.6 },
  { name: 'Ni³', ratio: '15/8', freq: 490.55, cents: 1088.3, swara: 'Ni', color: '#ec4899', title: 'Shuddha Nishad', devanagari: 'शुद्ध निषाद', tetFreq: 493.88, tetDiff: -11.7 },
  { name: 'Ni⁴', ratio: '243/128', freq: 496.71, cents: 1109.8, swara: 'Ni', color: '#ec4899', title: 'Kakali Nishad', devanagari: 'काकली निषाद', tetFreq: 493.88, tetDiff: +9.8 },
  { name: 'Sa’', ratio: '2/1', freq: 523.25, cents: 1200.0, swara: 'Sa', color: '#f43f5e', title: 'Tara Shadja (Octave)', devanagari: 'तार षड्ज', tetFreq: 523.25, tetDiff: 0 },
]

// ── A/B Acoustic Comparison Experiments ──
const COMPARISON_EXPERIMENTS = [
  {
    id: 'pramana',
    title: 'Pramāṇa Śruti (The 21.5¢ Microtone Gap)',
    subtitle: 'Re¹ (275.65 Hz, 256/243) vs Re² (279.07 Hz, 16/15)',
    noteA: SHRUTIS[1], // Re1
    noteB: SHRUTIS[2], // Re2
    deltaHz: '3.42 Hz',
    deltaCents: '21.51¢',
    math: '81/80 (Didymic Comma)',
    explanation:
      'Western 12-TET collapses these two distinct vocal placements into a single synthetic D♭ (277.18 Hz). In Vedic recitations of the Rigveda, singing Re¹ instead of Re² alters the mathematical resonance and vowel formants.',
  },
  {
    id: 'antara_ga',
    title: 'Natural Major Third vs 12-TET Beating',
    subtitle: 'Vedic Ga³ (327.03 Hz, 5/4) vs Equal Temperament E (329.63 Hz)',
    noteA: SHRUTIS[7], // Ga3
    noteB: { name: '12-TET E4', freq: 329.63, ratio: '2^(4/12)', cents: 400.0, color: '#94a3b8', title: 'Equal Tempered E4' },
    deltaHz: '2.60 Hz',
    deltaCents: '13.7¢ sharp in 12-TET',
    math: '5/4 pure harmonic vs 2^(4/12)',
    explanation:
      'Equal temperament intentionally sharpens the major 3rd by 13.7 cents to allow key modulation. This creates an audible 2.6 Hz acoustic beating (pulsing distortion). Vedic chanting demands the pure 5/4 ratio for calm meditative stability.',
  },
  {
    id: 'shuddha_ma',
    title: 'The Perfect Consonant Fourth',
    subtitle: 'Vedic Ma¹ (348.84 Hz, 4/3) vs 12-TET F4 (349.23 Hz)',
    noteA: SHRUTIS[9], // Ma1
    noteB: { name: '12-TET F4', freq: 349.23, ratio: '2^(5/12)', cents: 500.0, color: '#94a3b8', title: 'Equal Tempered F4' },
    deltaHz: '0.39 Hz',
    deltaCents: '1.96¢',
    math: '4/3 Helmholtz resonance',
    explanation:
      'The natural fourth is nearly identical to equal temperament (-1.96¢), demonstrating why the ancient Samavedic chants preserved the Shadja-Madhyama (Sa-Ma) consonant concord with near zero acoustic interference.',
  },
]

// ── Ghana Patha Permutation Steps ──
const GHANA_STEPS = [
  { step: 1, notation: '1 - 2', label: 'Anuloma (Forward)', words: ['ओम् (Om)', 'ईशा (Īśā)'], cadence: [261.63, 294.33] },
  { step: 2, notation: '2 - 1', label: 'Viloma (Reverse)', words: ['ईशा (Īśā)', 'ओम् (Om)'], cadence: [294.33, 261.63] },
  { step: 3, notation: '1 - 2 - 3', label: 'Triad Forward', words: ['ओम् (Om)', 'ईशा (Īśā)', 'वास्यम् (Vāsyam)'], cadence: [261.63, 294.33, 327.03] },
  { step: 4, notation: '3 - 2 - 1', label: 'Triad Reverse', words: ['वास्यम् (Vāsyam)', 'ईशा (Īśā)', 'ओम् (Om)'], cadence: [327.03, 294.33, 261.63] },
  { step: 5, notation: '1 - 2 - 3', label: 'Ghana Sthiti', words: ['ओम् (Om)', 'ईशा (Īśā)', 'वास्यम् (Vāsyam)'], cadence: [261.63, 294.33, 261.63] },
]

export default function AuthScreen({ apiBase, onAuthed, onGuest }) {
  // Navigation & View Mode: 'explorer' | 'auth'
  const [viewMode, setViewMode] = useState('explorer')
  const [activeTab, setActiveTab] = useState('tuner') // 'tuner' | 'ab_test' | 'ghana' | 'specs'

  // Auth Form State
  const [authFormTab, setAuthFormTab] = useState('login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [authError, setAuthError] = useState(null)
  const [authLoading, setAuthLoading] = useState(false)

  // Interactive Synthesizer State
  const [selectedShruti, setSelectedShruti] = useState(SHRUTIS[2]) // Re²
  const [activeExperiment, setActiveExperiment] = useState(COMPARISON_EXPERIMENTS[0])
  const [activeGhanaStep, setActiveGhanaStep] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)

  // Audio Context & Nodes
  const audioCtxRef = useRef(null)
  const analyserRef = useRef(null)
  const canvasRef = useRef(null)
  const animFrameRef = useRef(null)

  // ── Web Audio Synthesizer Engine ──────────────────────────────────────────
  const getAudioContext = useCallback(() => {
    if (!audioCtxRef.current) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext
      const ctx = new AudioCtx()
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

  // Pure click-free sine wave generation
  const playTone = useCallback((freq, duration = 0.5, volume = 0.3) => {
    try {
      const { ctx, analyser } = getAudioContext()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()

      osc.type = 'sine'
      osc.frequency.setValueAtTime(freq, ctx.currentTime)

      const now = ctx.currentTime
      gain.gain.setValueAtTime(0.0001, now)
      gain.gain.exponentialRampToValueAtTime(volume, now + 0.035)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration)

      osc.connect(gain)
      gain.connect(analyser)

      osc.start(now)
      osc.stop(now + duration)

      setIsPlaying(true)
      setTimeout(() => setIsPlaying(false), duration * 1000)
    } catch (err) {
      console.warn('Audio synthesis error:', err)
    }
  }, [getAudioContext])

  // Play two tones simultaneously to hear acoustic beating
  const playDualBeating = useCallback((freqA, freqB, duration = 1.6) => {
    try {
      const { ctx, analyser } = getAudioContext()
      const now = ctx.currentTime

      const osc1 = ctx.createOscillator()
      const osc2 = ctx.createOscillator()
      const gain = ctx.createGain()

      osc1.type = 'sine'
      osc2.type = 'sine'
      osc1.frequency.setValueAtTime(freqA, now)
      osc2.frequency.setValueAtTime(freqB, now)

      gain.gain.setValueAtTime(0.0001, now)
      gain.gain.exponentialRampToValueAtTime(0.28, now + 0.05)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + duration)

      osc1.connect(gain)
      osc2.connect(gain)
      gain.connect(analyser)

      osc1.start(now)
      osc2.start(now)
      osc1.stop(now + duration)
      osc2.stop(now + duration)

      setIsPlaying(true)
      setTimeout(() => setIsPlaying(false), duration * 1000)
    } catch (err) {
      console.warn('Dual beating error:', err)
    }
  }, [getAudioContext])

  // Play Ghana Patha musical cadence sequence
  const playGhanaCadence = useCallback((stepIdx) => {
    setActiveGhanaStep(stepIdx)
    const step = GHANA_STEPS[stepIdx]
    if (!step) return

    step.cadence.forEach((freq, i) => {
      setTimeout(() => {
        playTone(freq, 0.35, 0.28)
      }, i * 380)
    })
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

      // Oscilloscope reticle lines
      ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.moveTo(0, height / 2)
      ctx.lineTo(width, height / 2)
      ctx.moveTo(width / 2, 0)
      ctx.lineTo(width / 2, height)
      ctx.stroke()

      const analyser = analyserRef.current
      if (analyser && isPlaying) {
        const bufferLength = analyser.fftSize
        const dataArray = new Uint8Array(bufferLength)
        analyser.getByteTimeDomainData(dataArray)

        ctx.lineWidth = 2.2
        ctx.strokeStyle = selectedShruti?.color || '#10b981'
        ctx.shadowColor = selectedShruti?.color || '#10b981'
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
        // Resting ambient wave
        phase += 0.04
        ctx.lineWidth = 1.5
        ctx.strokeStyle = 'rgba(244, 63, 94, 0.45)'
        ctx.shadowColor = 'rgba(244, 63, 94, 0.2)'
        ctx.shadowBlur = 4
        ctx.beginPath()
        for (let x = 0; x < width; x += 2) {
          const y = height / 2 + Math.sin(x * 0.03 + phase) * 6
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
  }, [isPlaying, selectedShruti])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
        audioCtxRef.current.close().catch(() => {})
      }
    }
  }, [])

  // ── Swara Category Groups (8 Physical Channel Strips) ─────────────────────
  const octaveChannels = useMemo(() => [
    { key: 'Sa', name: 'Sa', label: 'Shadja (Tonic)', color: '#f43f5e', notes: SHRUTIS.filter(s => s.swara === 'Sa' && s.name === 'Sa') },
    { key: 'Re', name: 'Re', label: 'Rishabh (2nd)', color: '#f97316', notes: SHRUTIS.filter(s => s.swara === 'Re') },
    { key: 'Ga', name: 'Ga', label: 'Gandhar (3rd)', color: '#eab308', notes: SHRUTIS.filter(s => s.swara === 'Ga') },
    { key: 'Ma', name: 'Ma', label: 'Madhyam (4th)', color: '#10b981', notes: SHRUTIS.filter(s => s.swara === 'Ma') },
    { key: 'Pa', name: 'Pa', label: 'Pancham (5th)', color: '#06b6d4', notes: SHRUTIS.filter(s => s.swara === 'Pa') },
    { key: 'Dha', name: 'Dha', label: 'Dhaivat (6th)', color: '#8b5cf6', notes: SHRUTIS.filter(s => s.swara === 'Dha') },
    { key: 'Ni', name: 'Ni', label: 'Nishad (7th)', color: '#ec4899', notes: SHRUTIS.filter(s => s.swara === 'Ni') },
    { key: 'Sa2', name: "Sa’", label: 'Tara Shadja (8ve)', color: '#f43f5e', notes: SHRUTIS.filter(s => s.name === "Sa’") },
  ], [])

  // ── Auth Handlers ─────────────────────────────────────────────────────────
  const handleAuthSubmit = async (e) => {
    e.preventDefault()
    setAuthError(null)
    setAuthLoading(true)

    const endpoint = authFormTab === 'login' ? `${apiBase}/auth/login/` : `${apiBase}/auth/register/`
    const payload = authFormTab === 'login'
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

      setAuth(data.token, data.user)
      onAuthed(data.user)
    } catch (err) {
      setAuthError(`Connection failure: ${err.message}`)
    } finally {
      setAuthLoading(false)
    }
  }

  return (
    <div className="research-portal">
      {/* ── Precision Industrial Navbar ────────────────────────────────────── */}
      <header className="console-nav">
        <div className="nav-brand-group">
          <div className="brand-badge">VA</div>
          <div className="brand-meta">
            <span className="brand-title">VEDIC ACOUSTICA</span>
            <span className="brand-subtitle">COMPUTATIONAL ACOUSTIC INTELLIGENCE &middot; V2.4</span>
          </div>
        </div>

        <nav className="console-nav-actions">
          {viewMode === 'explorer' ? (
            <>
              <div className="console-tabs-bar" role="tablist">
                <button
                  type="button"
                  className={`console-tab ${activeTab === 'tuner' ? 'active' : ''}`}
                  onClick={() => setActiveTab('tuner')}
                >
                  01 // 22-SHRUTI LAB
                </button>
                <button
                  type="button"
                  className={`console-tab ${activeTab === 'ab_test' ? 'active' : ''}`}
                  onClick={() => setActiveTab('ab_test')}
                >
                  02 // 12-TET vs JUST INTONATION
                </button>
                <button
                  type="button"
                  className={`console-tab ${activeTab === 'ghana' ? 'active' : ''}`}
                  onClick={() => setActiveTab('ghana')}
                >
                  03 // GHANA PATHA SEQUENCER
                </button>
                <button
                  type="button"
                  className={`console-tab ${activeTab === 'specs' ? 'active' : ''}`}
                  onClick={() => setActiveTab('specs')}
                >
                  04 // ARCHITECTURE &amp; DTW
                </button>
              </div>

              <div className="nav-btn-cluster">
                <button type="button" className="btn-signal-guest" onClick={onGuest}>
                  <span className="signal-led" />
                  <span>LAUNCH LIVE DASHBOARD</span>
                </button>
                <button type="button" className="btn-console-secondary" onClick={() => setViewMode('auth')}>
                  RESEARCHER LOGIN
                </button>
              </div>
            </>
          ) : (
            <div className="nav-btn-cluster">
              <button type="button" className="btn-console-secondary" onClick={() => setViewMode('explorer')}>
                &larr; RETURN TO RESEARCH EXPLORER
              </button>
              <button type="button" className="btn-signal-guest" onClick={onGuest}>
                <span className="signal-led" />
                <span>EXPLORE DEMO DASHBOARD</span>
              </button>
            </div>
          )}
        </nav>
      </header>

      {/* ═══════════════════════════════════════════════════════════════════════
          VIEW 1: Interactive Scientific Research Explorer
          ═══════════════════════════════════════════════════════════════════════ */}
      {viewMode === 'explorer' && (
        <main className="explorer-container">
          {/* Scientific Status Bar */}
          <div className="telemetry-bar">
            <div className="telemetry-item">
              <span className="telemetry-key">SYSTEM STATUS:</span>
              <span className="telemetry-val-good">
                ● {window.location.hostname === 'localhost' ? 'ONLINE (LOCALHOST:8000)' : 'ONLINE (PROD SPACE)'}
              </span>
            </div>
            <div className="telemetry-item">
              <span className="telemetry-key">REFERENCE TONIC:</span>
              <span className="telemetry-val">C4 = 261.626 Hz (JUST INTONATION)</span>
            </div>
            <div className="telemetry-item">
              <span className="telemetry-key">MICROTONE RESOLUTION:</span>
              <span className="telemetry-val">22 BINS &middot; &plusmn;21.5¢ MIN INTERVAL</span>
            </div>
            <div className="telemetry-item">
              <span className="telemetry-key">ALGORITHMS:</span>
              <span className="telemetry-val">pYIN F0 &middot; 22-PCP &middot; DTW MATRICES</span>
            </div>
          </div>

          {/* ── TAB 1: 22-Shruti Interactive Acoustic Console ───────────────── */}
          {activeTab === 'tuner' && (
            <section className="console-module">
              <div className="module-title-bar">
                <div>
                  <span className="module-index">SECTION 01 // INTERACTIVE INSTRUMENT</span>
                  <h2 className="module-heading">22-Shruti Natural Microtonal Synthesizer</h2>
                </div>
                <div className="module-tag">Pure Sine Oscillator &middot; ADSR Enveloping</div>
              </div>

              {/* Instrument HUD: Monospace Telemetry + Real Oscilloscope */}
              <div className="instrument-hud" style={{ '--accent-theme': selectedShruti?.color }}>
                <div className="hud-left-panel">
                  <div className="hud-swara-box">
                    <span className="hud-swara-symbol" style={{ color: selectedShruti?.color }}>
                      {selectedShruti?.name}
                    </span>
                    <span className="hud-swara-devanagari">{selectedShruti?.devanagari}</span>
                  </div>

                  <div className="hud-metadata">
                    <h3 className="hud-title">{selectedShruti?.title}</h3>
                    <div className="hud-pills-row">
                      <span className="hud-mono-tag">RATIO: {selectedShruti?.ratio}</span>
                      <span className="hud-mono-tag">CATEGORY: {selectedShruti?.swara}</span>
                      <span className="hud-mono-tag">
                        12-TET OFFSET: {selectedShruti?.tetDiff > 0 ? `+${selectedShruti?.tetDiff}` : selectedShruti?.tetDiff}&cent;
                      </span>
                    </div>
                  </div>
                </div>

                <div className="hud-center-telemetry">
                  <div className="hud-dial">
                    <span className="hud-dial-lbl">EXACT FREQUENCY</span>
                    <span className="hud-dial-num">
                      {selectedShruti?.freq.toFixed(2)} <span className="hud-unit">Hz</span>
                    </span>
                  </div>
                  <div className="hud-dial">
                    <span className="hud-dial-lbl">OCTAVE CENTS</span>
                    <span className="hud-dial-num">
                      {selectedShruti?.cents.toFixed(1)} <span className="hud-unit">&cent;</span>
                    </span>
                  </div>
                  <div className="hud-dial">
                    <span className="hud-dial-lbl">WESTERN 12-TET</span>
                    <span className="hud-dial-num">
                      {selectedShruti?.tetFreq.toFixed(2)} <span className="hud-unit">Hz</span>
                    </span>
                  </div>
                </div>

                <div className="hud-right-scope">
                  <canvas ref={canvasRef} width={360} height={70} className="hud-canvas" />
                  <div className="scope-meta">
                    <span>{isPlaying ? 'AUDIO ENGINE ACTIVE' : 'SCOPE STANDBY'}</span>
                    <span>1024 FFT</span>
                  </div>
                </div>
              </div>

              {/* Physical Keyboard Channel Strips (Full Octave Console) */}
              <div className="octave-console-deck">
                <div className="deck-toolbar">
                  <span className="deck-toolbar-label">SELECT ANY SHRUTI TO TRIGGER PURE SYNTHESIS TONE:</span>
                  <span className="deck-toolbar-hint">C4 (261.6 Hz) &rarr; C5 (523.3 Hz)</span>
                </div>

                <div className="console-channels-grid">
                  {octaveChannels.map(channel => (
                    <div key={channel.key} className="console-channel">
                      <div className="channel-strip-header" style={{ color: channel.color, borderBottomColor: channel.color }}>
                        <span className="channel-name">{channel.name}</span>
                        <span className="channel-sub">{channel.label}</span>
                      </div>

                      <div className="channel-pads">
                        {channel.notes.map(note => {
                          const isCurrent = selectedShruti?.name === note.name
                          return (
                            <button
                              key={note.name}
                              type="button"
                              className={`synth-pad ${isCurrent ? 'active' : ''}`}
                              style={{
                                '--pad-glow': note.color,
                                borderColor: isCurrent ? note.color : 'rgba(255, 255, 255, 0.1)',
                              }}
                              onClick={() => {
                                setSelectedShruti(note)
                                playTone(note.freq, 0.45, 0.32)
                              }}
                            >
                              <div className="pad-top-row">
                                <span className="pad-swara-name">{note.name}</span>
                                <span className="pad-ratio">{note.ratio}</span>
                              </div>
                              <div className="pad-bottom-row">
                                <span className="pad-freq">{note.freq.toFixed(1)} Hz</span>
                                <span className="pad-cents">{note.cents.toFixed(0)}&cent;</span>
                              </div>
                            </button>
                          )
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* ── TAB 2: A/B Acoustic Difference Engine (Hear The Science) ─────── */}
          {activeTab === 'ab_test' && (
            <section className="console-module">
              <div className="module-title-bar">
                <div>
                  <span className="module-index">SECTION 02 // ACOUSTIC COMPARATOR</span>
                  <h2 className="module-heading">Vedic Just Intonation vs Western Equal Temperament (12-TET)</h2>
                </div>
                <div className="module-tag">A/B Dissonance &amp; Acoustic Beating Analysis</div>
              </div>

              <div className="ab-selector-strip">
                {COMPARISON_EXPERIMENTS.map(exp => (
                  <button
                    key={exp.id}
                    type="button"
                    className={`ab-tab-btn ${activeExperiment.id === exp.id ? 'active' : ''}`}
                    onClick={() => setActiveExperiment(exp)}
                  >
                    <span className="ab-btn-title">{exp.title}</span>
                    <span className="ab-btn-delta">&Delta; {exp.deltaCents}</span>
                  </button>
                ))}
              </div>

              {/* Active Experiment Workbench */}
              <div className="ab-workbench">
                <div className="workbench-top">
                  <div>
                    <h3 className="workbench-heading">{activeExperiment.title}</h3>
                    <p className="workbench-sub">{activeExperiment.subtitle}</p>
                  </div>
                  <div className="workbench-stats">
                    <div className="stat-pill">
                      <span>PITCH OFFSET:</span>
                      <strong>{activeExperiment.deltaCents}</strong>
                    </div>
                    <div className="stat-pill">
                      <span>FREQUENCY BEAT:</span>
                      <strong>{activeExperiment.deltaHz}</strong>
                    </div>
                    <div className="stat-pill">
                      <span>MATHEMATICAL RATIO:</span>
                      <strong>{activeExperiment.math}</strong>
                    </div>
                  </div>
                </div>

                {/* Audible Triggers: Side by Side Bench */}
                <div className="ab-audition-deck">
                  <div className="ab-panel panel-left">
                    <div className="panel-badge-row">
                      <span className="panel-badge-vedic">PURE VEDIC JUST INTONATION</span>
                      <span className="panel-hz">{activeExperiment.noteA.freq.toFixed(2)} Hz</span>
                    </div>
                    <h4 className="panel-title">{activeExperiment.noteA.name} &mdash; {activeExperiment.noteA.title}</h4>
                    <p className="panel-desc">Calculated via natural integer harmonic ratio ({activeExperiment.noteA.ratio}). Delivers pure harmonic resonance.</p>
                    <button
                      type="button"
                      className="btn-audition-primary"
                      onClick={() => playTone(activeExperiment.noteA.freq, 0.6, 0.32)}
                    >
                      ▶ AUDITION VEDIC TONE ({activeExperiment.noteA.name})
                    </button>
                  </div>

                  <div className="ab-vs-column">
                    <div className="vs-circle">VS</div>
                    <button
                      type="button"
                      className="btn-audition-beating"
                      onClick={() => playDualBeating(activeExperiment.noteA.freq, activeExperiment.noteB.freq, 1.8)}
                    >
                      ⚡ HEAR ACOUSTIC BEATING (DUAL)
                    </button>
                  </div>

                  <div className="ab-panel panel-right">
                    <div className="panel-badge-row">
                      <span className="panel-badge-tet">WESTERN 12-TET SYNTHETIC</span>
                      <span className="panel-hz">{activeExperiment.noteB.freq.toFixed(2)} Hz</span>
                    </div>
                    <h4 className="panel-title">{activeExperiment.noteB.name} &mdash; {activeExperiment.noteB.title}</h4>
                    <p className="panel-desc">Arbitrary geometric division ($2^{'{n/12}'}$). Causes audible harmonic phase interference and beating.</p>
                    <button
                      type="button"
                      className="btn-audition-secondary"
                      onClick={() => playTone(activeExperiment.noteB.freq, 0.6, 0.32)}
                    >
                      ▶ AUDITION 12-TET TONE ({activeExperiment.noteB.name})
                    </button>
                  </div>
                </div>

                <div className="ab-explanation-box">
                  <div className="exp-icon">💡</div>
                  <div>
                    <strong>Scientific Analysis:</strong>
                    <p>{activeExperiment.explanation}</p>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* ── TAB 3: Ghana Patha Permutation Sequencer ─────────────────────── */}
          {activeTab === 'ghana' && (
            <section className="console-module">
              <div className="module-title-bar">
                <div>
                  <span className="module-index">SECTION 03 // ALGORITHMIC PERMUTATION</span>
                  <h2 className="module-heading">Ghana Patha: Ancient 2-Step Error-Correction Algorithm</h2>
                </div>
                <div className="module-tag">Dynamic Time Warping (DTW) Sequence Alignment</div>
              </div>

              <p className="module-intro">
                The Ghana Patha is the most rigorous oral preservation technique in human history. Words ($1, 2, 3$) are recited in a formal forward-reverse permutation ($1-2 \rightarrow 2-1 \rightarrow 1-2-3 \rightarrow 3-2-1 \rightarrow 1-2-3$). Click any step below to audition its melodic cadence and observe the mathematical invariant.
              </p>

              {/* Interactive Sequencer Steps */}
              <div className="ghana-steps-deck">
                {GHANA_STEPS.map((step, idx) => {
                  const isActive = activeGhanaStep === idx
                  return (
                    <div
                      key={step.step}
                      className={`ghana-step-card ${isActive ? 'active' : ''}`}
                      onClick={() => playGhanaCadence(idx)}
                    >
                      <div className="step-card-header">
                        <span className="step-num">STEP 0{step.step}</span>
                        <span className="step-formula">{step.notation}</span>
                      </div>
                      <h4 className="step-label">{step.label}</h4>
                      <div className="step-words-list">
                        {step.words.map((w) => (
                          <span key={w} className="step-word-tag">{w}</span>
                        ))}
                      </div>
                      <button type="button" className="btn-step-play">
                        {isActive ? '▶ AUDITIONING' : '▶ AUDITION CADENCE'}
                      </button>
                    </div>
                  )
                })}
              </div>

              {/* Sequencer Cadence Inspector */}
              <div className="ghana-inspector">
                <div className="inspector-left">
                  <span className="inspector-badge">ACTIVE RECITATION SEGMENT:</span>
                  <h3 className="inspector-active-title">
                    Step 0{GHANA_STEPS[activeGhanaStep].step}: {GHANA_STEPS[activeGhanaStep].notation} &mdash; {GHANA_STEPS[activeGhanaStep].label}
                  </h3>
                  <div className="inspector-sequence">
                    {GHANA_STEPS[activeGhanaStep].words.map((word) => (
                      <div key={word} className="inspector-word-node">
                        <span className="node-text">{word}</span>
                        <span className="node-f0">Vedic Accent: Svarita</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="inspector-right">
                  <span className="dtw-metric-tag">DTW VERIFICATION ENGINE:</span>
                  <p className="dtw-explanation">
                    Vedic Acoustica computes a local cost matrix using Euclidean distance between consecutive pitch trajectories:
                  </p>
                  <code className="dtw-math-snippet">
                    D(i, j) = || F0_chant(i) - F0_reference(j) || + min[ D(i-1, j), D(i, j-1), D(i-1, j-1) ]
                  </code>
                  <p className="dtw-sub-desc">
                    If any word is transposed, deleted, or mispronounced, the warping cost exceeds the validation threshold ($\tau = 0.65$), immediately flagging an oral recitation error.
                  </p>
                </div>
              </div>
            </section>
          )}

          {/* ── TAB 4: Architecture & DTW Engine Specifications ────────────── */}
          {activeTab === 'specs' && (
            <section className="console-module">
              <div className="module-title-bar">
                <div>
                  <span className="module-index">SECTION 04 // MACHINE LEARNING ARCHITECTURE</span>
                  <h2 className="module-heading">Continuous Audio Extraction Pipeline</h2>
                </div>
                <div className="module-tag">Librosa &middot; PyTorch &middot; Django REST Framework</div>
              </div>

              <div className="specs-grid">
                <div className="spec-card">
                  <div className="spec-icon">01</div>
                  <h3 className="spec-title">Probabilistic YIN (pYIN) Pitch Tracking</h3>
                  <p className="spec-desc">
                    Calculates cumulative mean normalized difference functions across overlapping 2048-sample windows. Applies Viterbi path decoding across candidate pitch states to eliminate octave transposition errors.
                  </p>
                  <ul className="spec-checklist">
                    <li>Sample rate: 22,050 Hz (Nyquist 11.025 kHz)</li>
                    <li>Hop length: 512 samples (~23.2 ms frame rate)</li>
                    <li>F0 range: 65 Hz (C2) to 1046 Hz (C6)</li>
                  </ul>
                </div>

                <div className="spec-card">
                  <div className="spec-icon">02</div>
                  <h3 className="spec-title">22-Shruti Pitch Class Profile (PCP)</h3>
                  <p className="spec-desc">
                    Unlike standard 12-chroma vectors, our PCP algorithm establishes 23 non-linear harmonic filters calibrated to the Daniélou and Bharata Natyashastra ratios with tonic normalization to $C_4$.
                  </p>
                  <ul className="spec-checklist">
                    <li>23 Non-linear bins covering 1200 cents</li>
                    <li>Median-filtered cents deviation tracking</li>
                    <li>Continuous thermal energy spectrogram generation</li>
                  </ul>
                </div>

                <div className="spec-card">
                  <div className="spec-icon">03</div>
                  <h3 className="spec-title">44 Raga Melodic Identification</h3>
                  <p className="spec-desc">
                    Constructs an invariant melodic signature from pitch histograms and transitions, computing cosine similarity against canonical Carnatic and Hindustani scale dictionaries.
                  </p>
                  <ul className="spec-checklist">
                    <li>44 Canonical Ragas indexed</li>
                    <li>Arohana &amp; Avarohana transition matrices</li>
                    <li>Spectral centroid and roll-off clustering</li>
                  </ul>
                </div>
              </div>
            </section>
          )}

          {/* Bottom Direct Action Bar */}
          <footer className="console-footer-cta">
            <div className="cta-meta">
              <h3 className="cta-headline">Ready to Inspect Real Audio Data?</h3>
              <p className="cta-description">
                Explore 3 pre-loaded Vedic chant recordings (Isavasya Ghanam, Rudram Chamakam, and Scales) with interactive Spectrogram, 22-Shruti Heatmaps, and Ghana Patha DTW matrices.
              </p>
            </div>
            <div className="cta-button-group">
              <button type="button" className="btn-signal-guest-large" onClick={onGuest}>
                <span>⚡ LAUNCH LIVE RESEARCH DASHBOARD (GUEST DEMO)</span>
              </button>
              <button type="button" className="btn-console-secondary-large" onClick={() => setViewMode('auth')}>
                <span>RESEARCHER SIGN IN &rarr;</span>
              </button>
            </div>
          </footer>
        </main>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════
          VIEW 2: Dedicated Focused Authentication Console
          ═══════════════════════════════════════════════════════════════════════ */}
      {viewMode === 'auth' && (
        <main className="dedicated-auth-viewport">
          <div className="auth-box">
            <div className="auth-top-bar">
              <button type="button" className="auth-return-link" onClick={() => setViewMode('explorer')}>
                &larr; RETURN TO RESEARCH EXPLORER
              </button>
              <span className="auth-sys-tag">GATEWAY ACCESS</span>
            </div>

            <div className="auth-box-header">
              <div className="auth-box-brand">VA</div>
              <h2 className="auth-box-title">Researcher Authentication</h2>
              <p className="auth-box-sub">Sign in to manage recordings, trigger ML pipelines, and export PDF reports</p>
            </div>

            {/* Guest Pass Banner */}
            <div className="auth-guest-banner">
              <div>
                <strong>Just evaluating Vedic Acoustica?</strong>
                <p>Skip credentials and access all analyzed charts immediately.</p>
              </div>
              <button type="button" className="btn-guest-pass-quick" onClick={onGuest}>
                Instant Guest Pass &rarr;
              </button>
            </div>

            <div className="auth-or-line">
              <span>OR AUTHENTICATE VIA CREDENTIALS</span>
            </div>

            {/* Mode Switcher */}
            <div className="auth-mode-switch">
              <button
                type="button"
                className={`switch-btn ${authFormTab === 'login' ? 'active' : ''}`}
                onClick={() => { setAuthFormTab('login'); setAuthError(null) }}
              >
                SIGN IN
              </button>
              <button
                type="button"
                className={`switch-btn ${authFormTab === 'register' ? 'active' : ''}`}
                onClick={() => { setAuthFormTab('register'); setAuthError(null) }}
              >
                REGISTER NEW ACCOUNT
              </button>
            </div>

            {authError && (
              <div className="auth-error-alert" role="alert">
                <span>[ERROR] {authError}</span>
              </div>
            )}

            <form onSubmit={handleAuthSubmit} className="auth-form-body">
              <div className="input-field-group">
                <label htmlFor="input-username">RESEARCHER IDENTIFIER / USERNAME</label>
                <div className="input-shell">
                  <input
                    id="input-username"
                    type="text"
                    required
                    placeholder="e.g. shripat_lab"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="username"
                  />
                </div>
              </div>

              {authFormTab === 'register' && (
                <div className="input-field-group">
                  <label htmlFor="input-email">INSTITUTIONAL EMAIL</label>
                  <div className="input-shell">
                    <input
                      id="input-email"
                      type="email"
                      required
                      placeholder="researcher@institution.edu"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      autoComplete="email"
                    />
                  </div>
                </div>
              )}

              <div className="input-field-group">
                <label htmlFor="input-password">ACCESS KEY / PASSWORD</label>
                <div className="input-shell">
                  <input
                    id="input-password"
                    type="password"
                    required
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete={authFormTab === 'login' ? 'current-password' : 'new-password'}
                  />
                </div>
              </div>

              <button type="submit" className="btn-auth-action" disabled={authLoading}>
                {authLoading ? 'AUTHENTICATING ENCRYPTED SESSION...' : (authFormTab === 'login' ? 'SIGN IN TO PORTAL' : 'REGISTER RESEARCHER ACCOUNT')}
              </button>
            </form>

            <div className="auth-footer-tech">
              <span>SECURITY: JWT TOKEN AUTH &middot; ARGON2 HASHING &middot; RESTFUL ENCRYPTED ENDPOINTS</span>
            </div>
          </div>
        </main>
      )}
    </div>
  )
}