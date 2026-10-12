import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * ShrutiAuditorium
 *
 * The analysis-aware heart of the Explorer: a 23-bin microtonal map of the
 * 22 Śruti (plus the octave Sa). Each key is auditioned as a pure sine tuned
 * to the recording's own tonic, and — when an analysis is supplied — the key
 * is shaded by the energy that Śruti carried in the recording and marked when
 * it was detected as a sung swara or fell inside the matched rāga scale.
 *
 * Props:
 *   analysis       – analysis result object (or null for a neutral reference grid)
 *   selected       – currently selected swara name (from the parent)
 *   onSelectSwara  – callback(swaraName) when a key is chosen
 */

const SHRUTI_GRID = [
  { name: 'Sa',  family: 'Sa',  ratio: '1/1',     cents: 0.0 },
  { name: 'Re1', family: 'Re',  ratio: '256/243', cents: 90.2 },
  { name: 'Re2', family: 'Re',  ratio: '16/15',   cents: 111.7 },
  { name: 'Re3', family: 'Re',  ratio: '10/9',    cents: 182.4 },
  { name: 'Re4', family: 'Re',  ratio: '9/8',     cents: 203.9 },
  { name: 'Ga1', family: 'Ga',  ratio: '32/27',   cents: 294.1 },
  { name: 'Ga2', family: 'Ga',  ratio: '6/5',     cents: 315.6 },
  { name: 'Ga3', family: 'Ga',  ratio: '5/4',     cents: 386.3 },
  { name: 'Ga4', family: 'Ga',  ratio: '81/64',   cents: 407.8 },
  { name: 'Ma1', family: 'Ma',  ratio: '4/3',     cents: 498.0 },
  { name: 'Ma2', family: 'Ma',  ratio: '27/20',   cents: 519.6 },
  { name: 'Ma3', family: 'Ma',  ratio: '45/32',   cents: 590.2 },
  { name: 'Ma4', family: 'Ma',  ratio: '729/512', cents: 611.7 },
  { name: 'Pa',  family: 'Pa',  ratio: '3/2',     cents: 702.0 },
  { name: 'Dha1', family: 'Dha', ratio: '128/81', cents: 792.2 },
  { name: 'Dha2', family: 'Dha', ratio: '8/5',    cents: 813.7 },
  { name: 'Dha3', family: 'Dha', ratio: '5/3',    cents: 884.4 },
  { name: 'Dha4', family: 'Dha', ratio: '27/16',  cents: 905.9 },
  { name: 'Ni1', family: 'Ni',  ratio: '16/9',    cents: 996.1 },
  { name: 'Ni2', family: 'Ni',  ratio: '9/5',     cents: 1017.6 },
  { name: 'Ni3', family: 'Ni',  ratio: '15/8',    cents: 1088.3 },
  { name: 'Ni4', family: 'Ni',  ratio: '243/128', cents: 1109.8 },
  { name: 'Sa’', family: 'Sa',  ratio: '2/1',     cents: 1200.0 },
]

const FAMILIES = ['Sa', 'Re', 'Ga', 'Ma', 'Pa', 'Dha', 'Ni']

function ratioValue(ratio) {
  const [num, den] = ratio.split('/').map(Number)
  return den ? num / den : 1
}

export default function ShrutiAuditorium({ analysis, selected, onSelectSwara }) {
  const [selectedIdx, setSelectedIdx] = useState(() => {
    const idx = SHRUTI_GRID.findIndex(s => s.name === selected)
    return idx === -1 ? 0 : idx
  })
  const [playingIdx, setPlayingIdx] = useState(null)
  const audioCtxRef = useRef(null)
  const stopTimerRef = useRef(null)
  const gapTimerRef = useRef(null)

  const tonicHz = typeof analysis?.tonic_hz === 'number' && analysis.tonic_hz > 0
    ? analysis.tonic_hz
    : 261.63

  // Keep the highlighted key in step when the selection changes elsewhere
  // (e.g. the hero Śruti instrument).
  useEffect(() => {
    const idx = SHRUTI_GRID.findIndex(s => s.name === selected)
    if (idx !== -1) setSelectedIdx(idx)
  }, [selected])

  // Normalised Śruti energy from the recording's mean pitch-class profile.
  const energies = (() => {
    const mpcp = analysis?.mean_pcp
    if (!Array.isArray(mpcp) || mpcp.length !== SHRUTI_GRID.length) return null
    const max = Math.max(...mpcp, 1e-9)
    return mpcp.map(v => Math.max(0, Math.min(1, v / max)))
  })()

  const detectedSet = new Set(
    (analysis?.raga_detection?.detected_swaras ?? []).map(item => item.index)
  )

  const ragaScale = new Set([
    ...(analysis?.raga_detection?.best_match?.arohana ?? []),
    ...(analysis?.raga_detection?.best_match?.avarohana ?? []),
  ])

  const getAudioContext = useCallback(() => {
    if (!audioCtxRef.current) {
      const Ctx = window.AudioContext || window.webkitAudioContext
      if (!Ctx) throw new Error('Web Audio is not supported in this browser.')
      audioCtxRef.current = new Ctx()
    }
    if (audioCtxRef.current.state === 'suspended') void audioCtxRef.current.resume()
    return audioCtxRef.current
  }, [])

  const playTone = useCallback((frequency, idx, duration = 0.6) => {
    try {
      const ctx = getAudioContext()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.setValueAtTime(frequency, ctx.currentTime)
      gain.gain.setValueAtTime(0.0001, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.28, ctx.currentTime + 0.04)
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration)
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start(ctx.currentTime)
      osc.stop(ctx.currentTime + duration)
      setPlayingIdx(idx)
      clearTimeout(stopTimerRef.current)
      stopTimerRef.current = setTimeout(() => setPlayingIdx(null), duration * 1000)
    } catch (err) {
      console.error('Shruti audition failed:', err)
    }
  }, [getAudioContext])

  const selectKey = useCallback((grid, idx) => {
    setSelectedIdx(idx)
    onSelectSwara?.(grid.name)
    playTone(tonicHz * ratioValue(grid.ratio), idx)
  }, [onSelectSwara, playTone, tonicHz])

  const playMicrotoneGap = useCallback(() => {
    const re1 = SHRUTI_GRID.findIndex(s => s.name === 'Re1')
    const re2 = SHRUTI_GRID.findIndex(s => s.name === 'Re2')
    setSelectedIdx(re1)
    onSelectSwara?.(SHRUTI_GRID[re1].name)
    playTone(tonicHz * ratioValue(SHRUTI_GRID[re1].ratio), re1, 0.5)
    clearTimeout(gapTimerRef.current)
    gapTimerRef.current = setTimeout(() => {
      setSelectedIdx(re2)
      onSelectSwara?.(SHRUTI_GRID[re2].name)
      playTone(tonicHz * ratioValue(SHRUTI_GRID[re2].ratio), re2, 0.6)
    }, 560)
  }, [onSelectSwara, playTone, tonicHz])

  useEffect(() => () => {
    clearTimeout(stopTimerRef.current)
    clearTimeout(gapTimerRef.current)
    if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
      audioCtxRef.current.close().catch(() => {})
    }
  }, [])

  const active = SHRUTI_GRID[selectedIdx]
  const activeFreq = tonicHz * ratioValue(active.ratio)
  const activeEnergy = energies ? energies[selectedIdx] : null
  const hasAnalysis = Boolean(energies)

  return (
    <div className="shruti-auditorium">
      <div className="sa-readout">
        <div className="sa-readout-main">
          <span className="sa-chip" style={{ '--family-tone': `var(--tone-${active.family})` }}>
            {active.name}
          </span>
          <div>
            <strong>{activeFreq.toFixed(1)} Hz</strong>
            <span className="sa-readout-sub">
              ratio {active.ratio} · {active.cents.toFixed(1)}¢ from Sa
            </span>
          </div>
        </div>
        <div className="sa-readout-flags">
          <span className="sa-tonic">Tonic Sa {tonicHz.toFixed(1)} Hz</span>
          {hasAnalysis && (
            <span className="sa-energy">
              In voice: {activeEnergy > 0.02 ? `${Math.round(activeEnergy * 100)}% energy` : 'not traced'}
            </span>
          )}
          {detectedSet.has(selectedIdx) && <span className="sa-badge detected">sung swara</span>}
          {ragaScale.has(selectedIdx) && <span className="sa-badge scale">in rāga scale</span>}
        </div>
      </div>

      <div className="sa-grid" role="toolbar" aria-label="23 Shruti audition grid">
        {FAMILIES.map(family => (
          <div className="sa-family" key={family}>
            <span className="sa-family-tag" style={{ '--family-tone': `var(--tone-${family})` }}>{family}</span>
            <div className="sa-family-keys">
              {SHRUTI_GRID.map((s, idx) => {
                if (s.family !== family) return null
                const isSelected = idx === selectedIdx
                const isPlaying = idx === playingIdx
                const isDetected = detectedSet.has(idx)
                const inScale = ragaScale.has(idx)
                const energy = energies ? energies[idx] : 0
                return (
                  <button
                    key={s.name}
                    type="button"
                    className={[
                      'sa-key',
                      isSelected ? 'is-selected' : '',
                      isPlaying ? 'is-playing' : '',
                      isDetected ? 'is-detected' : '',
                      inScale ? 'is-scale' : '',
                    ].join(' ')}
                    style={{
                      '--family-tone': `var(--tone-${s.family})`,
                      '--energy': hasAnalysis ? energy : 0.12,
                    }}
                    title={hasAnalysis
                      ? `${s.name} · ${(tonicHz * ratioValue(s.ratio)).toFixed(1)} Hz · ${Math.round(energy * 100)}% energy`
                      : `${s.name} · ${(tonicHz * ratioValue(s.ratio)).toFixed(1)} Hz`}
                    onClick={() => selectKey(s, idx)}
                    aria-pressed={isSelected}
                  >
                    <span className="sa-key-name">{s.name}</span>
                    <span className="sa-key-cents">{s.cents.toFixed(0)}¢</span>
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="sa-foot">
        <button type="button" className="engraved-button small" onClick={playMicrotoneGap}>
          ▶ Audition the 21.5¢ gap (Re¹ → Re²)
        </button>
        <p className="sa-note">
          {hasAnalysis
            ? 'Keys glow with the energy that Śruti carried in this recording; ● marks swaras the analysis heard. Tap any key to hear it at the recording\'s tonic.'
            : 'A neutral reference grid at A₄ = 261.63 Hz. Analyse a recording to shade these keys with the microtones your voice actually traced.'}
        </p>
      </div>
    </div>
  )
}
