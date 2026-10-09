import { useCallback, useEffect, useRef, useState } from 'react'

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

function appSwaraFor(family, shruti) {
  if (family.key === 'Sa2') return 'Sa'
  if (family.key === 'Sa' || family.key === 'Pa') return family.key
  return `${family.key}${family.shrutis.indexOf(shruti) + 1}`
}

export default function SoundExplorer({ onOpenUpload, onSelectSwara }) {
  const [selectedFamily, setSelectedFamily] = useState(SWARA_FAMILIES[1])
  const [selectedShruti, setSelectedShruti] = useState(SWARA_FAMILIES[1].shrutis[1])
  const [isPlayingSynth, setIsPlayingSynth] = useState(false)
  const [activeChant, setActiveChant] = useState(null)
  const [isChantPlaying, setIsChantPlaying] = useState(false)
  const [chantError, setChantError] = useState(null)
  const audioPlayerRef = useRef(null)
  const audioCtxRef = useRef(null)
  const analyserRef = useRef(null)
  const canvasRef = useRef(null)
  const stopToneTimerRef = useRef(null)
  const gapTimerRef = useRef(null)

  const getAudioContext = useCallback(() => {
    if (!audioCtxRef.current) {
      const AudioContextType = window.AudioContext || window.webkitAudioContext
      if (!AudioContextType) throw new Error('Web Audio is not supported in this browser.')
      const context = new AudioContextType()
      const analyser = context.createAnalyser()
      analyser.fftSize = 512
      analyser.smoothingTimeConstant = 0.85
      analyser.connect(context.destination)
      audioCtxRef.current = context
      analyserRef.current = analyser
    }
    if (audioCtxRef.current.state === 'suspended') {
      void audioCtxRef.current.resume()
    }
    return { context: audioCtxRef.current, analyser: analyserRef.current }
  }, [])

  const playTone = useCallback((frequency, duration = 0.45) => {
    try {
      const { context, analyser } = getAudioContext()
      const oscillator = context.createOscillator()
      const gain = context.createGain()
      oscillator.type = 'sine'
      oscillator.frequency.setValueAtTime(frequency, context.currentTime)
      gain.gain.setValueAtTime(0.0001, context.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.3, context.currentTime + 0.03)
      gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + duration)
      oscillator.connect(gain)
      gain.connect(analyser)
      oscillator.start(context.currentTime)
      oscillator.stop(context.currentTime + duration)
      setIsPlayingSynth(true)
      clearTimeout(stopToneTimerRef.current)
      stopToneTimerRef.current = setTimeout(() => setIsPlayingSynth(false), duration * 1000)
    } catch (error) {
      console.error('Shruti tone playback failed:', error)
    }
  }, [getAudioContext])

  const playMicrotoneGap = useCallback(() => {
    const [re1, re2] = SWARA_FAMILIES[1].shrutis
    setSelectedFamily(SWARA_FAMILIES[1])
    setSelectedShruti(re1)
    onSelectSwara(appSwaraFor(SWARA_FAMILIES[1], re1))
    playTone(re1.freq, 0.45)
    clearTimeout(gapTimerRef.current)
    gapTimerRef.current = setTimeout(() => {
      setSelectedShruti(re2)
      onSelectSwara(appSwaraFor(SWARA_FAMILIES[1], re2))
      playTone(re2.freq, 0.5)
    }, 500)
  }, [onSelectSwara, playTone])

  const handleToggleChant = useCallback((sample) => {
    const player = audioPlayerRef.current
    if (!player) return

    if (activeChant?.id === sample.id && isChantPlaying) {
      player.pause()
      setIsChantPlaying(false)
      return
    }

    setActiveChant(sample)
    setChantError(null)
    player.src = sample.url
    player.play().catch((error) => {
      setIsChantPlaying(false)
      setChantError(`Could not play ${sample.title}.`)
      console.error(`Chant playback failed for ${sample.title}:`, error)
    })
  }, [activeChant, isChantPlaying])

  useEffect(() => {
    const canvas = canvasRef.current
    const context = canvas?.getContext('2d')
    if (!canvas || !context) return undefined

    let running = true
    let phase = 0
    let frameId = 0
    const draw = () => {
      if (!running) return
      const { width, height } = canvas
      context.clearRect(0, 0, width, height)
      context.strokeStyle = 'rgba(255, 236, 196, 0.12)'
      context.lineWidth = 1
      context.beginPath()
      context.moveTo(0, height / 2)
      context.lineTo(width, height / 2)
      context.stroke()

      const analyser = analyserRef.current
      if (analyser && (isPlayingSynth || isChantPlaying)) {
        const samples = new Uint8Array(analyser.fftSize)
        analyser.getByteTimeDomainData(samples)
        context.lineWidth = 2
        context.strokeStyle = selectedShruti.color
        context.shadowColor = selectedShruti.color
        context.shadowBlur = 5
        context.beginPath()
        const sliceWidth = width / samples.length
        samples.forEach((sample, index) => {
          const x = index * sliceWidth
          const y = (sample / 128) * height / 2
          if (index === 0) context.moveTo(x, y)
          else context.lineTo(x, y)
        })
        context.stroke()
        context.shadowBlur = 0
      } else {
        phase += 0.035
        context.lineWidth = 1.5
        context.strokeStyle = 'rgba(210, 170, 102, 0.58)'
        context.beginPath()
        for (let x = 0; x < width; x += 2) {
          const y = height / 2 + Math.sin(x * 0.035 + phase) * 6
          if (x === 0) context.moveTo(x, y)
          else context.lineTo(x, y)
        }
        context.stroke()
      }
      frameId = requestAnimationFrame(draw)
    }

    frameId = requestAnimationFrame(draw)
    return () => {
      running = false
      cancelAnimationFrame(frameId)
    }
  }, [isPlayingSynth, isChantPlaying, selectedShruti])

  useEffect(() => () => {
    clearTimeout(stopToneTimerRef.current)
    clearTimeout(gapTimerRef.current)
    audioPlayerRef.current?.pause()
    if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
      audioCtxRef.current.close().catch((error) => {
        console.error('Could not close Shruti audio context:', error)
      })
    }
  }, [])

  return (
    <div className="sound-explorer-content">
      <section className="clean-hero">
        <span className="eyebrow">THE ACOUSTIC EXPLORER</span>
        <h2 className="hero-title">
          Explore the Sound of <span className="hero-highlight">Vedic Chanting</span>
        </h2>
        <p className="hero-tagline">
          Interactive 22-Shruti microtonal tuning, real voice recordings, and ancient recitation analysis.
        </p>
      </section>

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

        <div className="tuner-strip" style={{ borderColor: selectedShruti.color }}>
          <div className="tuner-note-badge" style={{ background: selectedShruti.color }}>
            {selectedShruti.name}
          </div>
          <div className="tuner-info-col">
            <span className="tuner-desc">{selectedShruti.desc}</span>
            <div className="tuner-metrics-row">
              <span className="metric-tag">Frequency: <strong>{selectedShruti.freq.toFixed(1)} Hz</strong></span>
              <span className="metric-tag">Ratio: <strong>{selectedShruti.ratio}</strong></span>
              <span className="metric-tag">Cents: <strong>{selectedShruti.cents.toFixed(1)}&cent;</strong></span>
              <span className="metric-tag diff-tag">{selectedShruti.pianoDiff}</span>
            </div>
          </div>
          <div className="tuner-wave-col">
            <canvas ref={canvasRef} width={280} height={50} className="tuner-canvas" aria-label="Live Shruti tone waveform" />
            <span className="tuner-wave-label">
              {isPlayingSynth ? '● Playing Pure Sine Wave' : 'Touch any note below'}
            </span>
          </div>
        </div>

        <div className="swara-keys-bar" role="toolbar" aria-label="Select Swara">
          {SWARA_FAMILIES.map(family => {
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
                  onSelectSwara(appSwaraFor(family, family.shrutis[0]))
                  playTone(family.shrutis[0].freq)
                }}
                aria-pressed={isSelected}
              >
                <span className="swara-letter">{family.name}</span>
                <span className="swara-subname">{family.label}</span>
              </button>
            )
          })}
        </div>

        <div className="microtone-variants-box">
          <span className="variants-label">
            Microtonal variations of <strong>{selectedFamily.name}</strong> ({selectedFamily.shrutis.length} Shrutis):
          </span>
          <div className="variants-row">
            {selectedFamily.shrutis.map(shruti => {
              const isActive = selectedShruti.name === shruti.name
              return (
                <button
                  key={shruti.name}
                  type="button"
                  className={`shruti-pill-btn ${isActive ? 'active' : ''}`}
                  style={{ '--shruti-color': selectedFamily.color }}
                  onClick={() => {
                    setSelectedShruti(shruti)
                    onSelectSwara(appSwaraFor(selectedFamily, shruti))
                    playTone(shruti.freq)
                  }}
                  aria-pressed={isActive}
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
        <audio
          ref={audioPlayerRef}
          onPlay={() => setIsChantPlaying(true)}
          onPause={() => setIsChantPlaying(false)}
          onEnded={() => setIsChantPlaying(false)}
          onError={() => {
            setIsChantPlaying(false)
            setChantError('The selected chant recording could not be loaded.')
            console.error('Chant audio element failed to load:', audioPlayerRef.current?.error)
          }}
          className="sound-explorer-audio"
          aria-label="Vedic chant audio playback"
        />
        {chantError && <p className="error-inscription" role="alert">{chantError}</p>}
        <div className="chant-cards-grid">
          {CHANT_SAMPLES.map(sample => {
            const isPlayingThis = activeChant?.id === sample.id && isChantPlaying
            return (
              <article key={sample.id} className={`chant-card ${isPlayingThis ? 'playing' : ''}`}>
                <div className="chant-card-info">
                  <span className="chant-duration">{sample.duration} WAV</span>
                  <h4 className="chant-title">{sample.title}</h4>
                  <p className="chant-tag">{sample.tag}</p>
                </div>
                <button
                  type="button"
                  className={`btn-chant-play ${isPlayingThis ? 'playing' : ''}`}
                  onClick={() => handleToggleChant(sample)}
                  aria-pressed={isPlayingThis}
                >
                  {isPlayingThis ? '⏸ Pause' : '▶ Play Chant'}
                </button>
              </article>
            )
          })}
        </div>
      </section>

      <section className="clean-pillars-row" aria-label="Acoustic research methods">
        <article className="clean-pillar">
          <span className="pillar-emoji" aria-hidden="true">🎯</span>
          <h4>22 Shrutis</h4>
          <p>Detects subtle vocal microtones that standard 12-key pianos cannot play.</p>
        </article>
        <article className="clean-pillar">
          <span className="pillar-emoji" aria-hidden="true">🔁</span>
          <h4>Ghana Patha</h4>
          <p>Validates the sacred recitation order (1-2 2-1 1-2-3) with Dynamic Time Warping.</p>
        </article>
        <article className="clean-pillar">
          <span className="pillar-emoji" aria-hidden="true">🎼</span>
          <h4>Raga Detection</h4>
          <p>Automatically identifies 44 Indian melodic modes using voice pitch AI.</p>
        </article>
      </section>

      <section className="bottom-cta-banner sound-explorer-cta">
        <div>
          <h3>Ready to explore full spectrograms &amp; analyses?</h3>
          <p>Continue to the recording archive to select audio and begin an acoustic study.</p>
        </div>
        <button type="button" className="btn btn-hero-primary" onClick={onOpenUpload}>
          Open recording chamber →
        </button>
      </section>
    </div>
  )
}
