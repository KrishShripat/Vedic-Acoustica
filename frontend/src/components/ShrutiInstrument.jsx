import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

/**
 * ShrutiInstrument — the interactive Śruti Yantra wheel.
 *
 * A rotary 22-step microtonal dial. Beyond selecting a degree it can:
 *   • sound each śruti as a pure sine at the recording's own tonic,
 *   • glide continuously between śrutis while you drag round the wheel,
 *   • show the recording's śruti energy as a radiating rosette,
 *   • spin the wheel so the chosen degree snaps to 12 o'clock,
 *   • auto-play a detected rāga's arohana / avarohana, and
 *   • answer to arrow keys, Enter/Space and hover.
 */

const SHRUTIS = [
  { name: 'Sa',   family: 'Sa',  ratio: '1/1',     cents: 0.0 },
  { name: 'Re1',  family: 'Re',  ratio: '256/243', cents: 90.2 },
  { name: 'Re2',  family: 'Re',  ratio: '16/15',   cents: 111.7 },
  { name: 'Re3',  family: 'Re',  ratio: '10/9',    cents: 182.4 },
  { name: 'Re4',  family: 'Re',  ratio: '9/8',     cents: 203.9 },
  { name: 'Ga1',  family: 'Ga',  ratio: '32/27',   cents: 294.1 },
  { name: 'Ga2',  family: 'Ga',  ratio: '6/5',     cents: 315.6 },
  { name: 'Ga3',  family: 'Ga',  ratio: '5/4',     cents: 386.3 },
  { name: 'Ga4',  family: 'Ga',  ratio: '81/64',   cents: 407.8 },
  { name: 'Ma1',  family: 'Ma',  ratio: '4/3',     cents: 498.0 },
  { name: 'Ma2',  family: 'Ma',  ratio: '27/20',   cents: 519.6 },
  { name: 'Ma3',  family: 'Ma',  ratio: '45/32',   cents: 590.2 },
  { name: 'Ma4',  family: 'Ma',  ratio: '729/512', cents: 611.7 },
  { name: 'Pa',   family: 'Pa',  ratio: '3/2',     cents: 702.0 },
  { name: 'Dha1', family: 'Dha', ratio: '128/81',  cents: 792.2 },
  { name: 'Dha2', family: 'Dha', ratio: '8/5',     cents: 813.7 },
  { name: 'Dha3', family: 'Dha', ratio: '5/3',     cents: 884.4 },
  { name: 'Dha4', family: 'Dha', ratio: '27/16',   cents: 905.9 },
  { name: 'Ni1',  family: 'Ni',  ratio: '16/9',    cents: 996.1 },
  { name: 'Ni2',  family: 'Ni',  ratio: '9/5',     cents: 1017.6 },
  { name: 'Ni3',  family: 'Ni',  ratio: '15/8',    cents: 1088.3 },
  { name: 'Ni4',  family: 'Ni',  ratio: '243/128', cents: 1109.8 },
]

// The 23 pitch-class grid used by the analysis (22 śrutis + the octave Sa).
const CENTS_23 = [...SHRUTIS.map(s => s.cents), 1200]

const FAMILIES = ['Sa', 'Re', 'Ga', 'Ma', 'Pa', 'Dha', 'Ni']
const STEP = 360 / SHRUTIS.length

// Bring `target` (deg) to the value congruent to it that sits nearest `current`,
// so snapping never spins the wheel the long way round.
function nearestAngle(target, current) {
  let t = target
  while (t - current > 180) t -= 360
  while (current - t > 180) t += 360
  return t
}

export default function ShrutiInstrument({
  selectedSwara,
  detectedSwaras = [],
  onSelect,
  tonicHz,
  meanPcp,
  ragaBest,
}) {
  const detectedNames = useMemo(
    () => new Set(detectedSwaras.map(item => item.swara)),
    [detectedSwaras],
  )

  const tonic = typeof tonicHz === 'number' && tonicHz > 0 ? tonicHz : 261.63

  const activeIndex = Math.max(0, SHRUTIS.findIndex(s => s.name === selectedSwara))

  const [rotationDeg, setRotationDeg] = useState(() => -activeIndex * STEP)
  const [dragging, setDragging] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [playingIdx, setPlayingIdx] = useState(null)
  const [hoveredIdx, setHoveredIdx] = useState(null)

  const wheelRef = useRef(null)
  const audioCtxRef = useRef(null)
  const glideOscRef = useRef(null)
  const glideGainRef = useRef(null)
  const dragRef = useRef({ active: false, startAngle: 0, startRotation: 0, moved: false })
  const scanningRef = useRef(false)
  const scaleTimersRef = useRef([])

  // ── Recording fingerprint: normalised śruti energy around the 22 degrees ───
  const energy = useMemo(() => {
    if (!Array.isArray(meanPcp) || meanPcp.length === 0) return null
    const vals = new Array(SHRUTIS.length).fill(0)
    for (let i = 0; i < meanPcp.length; i++) vals[i % SHRUTIS.length] += meanPcp[i]
    const max = Math.max(...vals, 1e-9)
    return vals.map(v => Math.max(0, Math.min(1, v / max)))
  }, [meanPcp])

  const ragaScale = useMemo(() => {
    const up = ragaBest?.arohana ?? []
    const down = ragaBest?.avarohana ?? []
    return new Set([...up, ...down])
  }, [ragaBest])

  const ragaSequence = useMemo(() => {
    const up = (ragaBest?.arohana ?? []).filter(b => Number.isInteger(b) && b >= 0 && b <= 22)
    const down = [...(ragaBest?.avarohana ?? [])]
      .reverse()
      .filter(b => Number.isInteger(b) && b >= 0 && b <= 22)
    return [...up, ...down]
  }, [ragaBest])

  // ── Keep the wheel aligned with the chosen degree (unless mid-gesture) ─────
  useEffect(() => {
    if (dragRef.current.active || scanningRef.current) return
    setRotationDeg(prev => nearestAngle(-activeIndex * STEP, prev))
  }, [activeIndex])

  // ── Audio helpers ─────────────────────────────────────────────────────────
  const ensureCtx = useCallback(() => {
    if (!audioCtxRef.current) {
      const Ctx = window.AudioContext || window.webkitAudioContext
      if (!Ctx) throw new Error('Web Audio is not supported in this browser.')
      audioCtxRef.current = new Ctx()
    }
    if (audioCtxRef.current.state === 'suspended') void audioCtxRef.current.resume()
    return audioCtxRef.current
  }, [])

  const freqForCents = useCallback((cents) => tonic * Math.pow(2, cents / 1200), [tonic])

  const playNote = useCallback((cents, duration = 0.55) => {
    try {
      const ctx = ensureCtx()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.type = 'sine'
      osc.frequency.setValueAtTime(freqForCents(cents), ctx.currentTime)
      gain.gain.setValueAtTime(0.0001, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.26, ctx.currentTime + 0.03)
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + duration)
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.start()
      osc.stop(ctx.currentTime + duration + 0.03)
    } catch (err) {
      console.error('Śruti audition failed:', err)
    }
  }, [ensureCtx, freqForCents])

  const stopGlide = useCallback((fade = 0.16) => {
    const ctx = audioCtxRef.current
    const osc = glideOscRef.current
    const gain = glideGainRef.current
    glideOscRef.current = null
    glideGainRef.current = null
    if (!ctx || !osc || !gain) return
    const end = ctx.currentTime + fade
    try {
      gain.gain.cancelScheduledValues(ctx.currentTime)
      gain.gain.setValueAtTime(Math.max(gain.gain.value, 0.0001), ctx.currentTime)
      gain.gain.linearRampToValueAtTime(0.0001, end)
      osc.stop(end + 0.04)
    } catch {
      try { osc.stop() } catch { /* already stopped */ }
    }
  }, [])

  const startGlide = useCallback((cents) => {
    const ctx = ensureCtx()
    const osc = ctx.createOscillator()
    const gain = ctx.createGain()
    osc.type = 'sine'
    osc.frequency.setValueAtTime(freqForCents(cents), ctx.currentTime)
    gain.gain.setValueAtTime(0.0001, ctx.currentTime)
    gain.gain.exponentialRampToValueAtTime(0.24, ctx.currentTime + 0.04)
    osc.connect(gain)
    gain.connect(ctx.destination)
    osc.start()
    glideOscRef.current = osc
    glideGainRef.current = gain
  }, [ensureCtx, freqForCents])

  // Fractional dial position → interpolated cents (octave-wrapping) → glide.
  const glideToFraction = useCallback((frac) => {
    const ctx = audioCtxRef.current
    const osc = glideOscRef.current
    if (!ctx || !osc) return
    const base = Math.floor(frac)
    const i0 = ((base % SHRUTIS.length) + SHRUTIS.length) % SHRUTIS.length
    const i1 = (i0 + 1) % SHRUTIS.length
    const c0 = CENTS_23[i0]
    const c1 = i1 === 0 ? 1200 : CENTS_23[i1]
    const t = frac - base
    const cents = c0 + (c1 - c0) * t
    osc.frequency.setTargetAtTime(freqForCents(cents), ctx.currentTime, 0.012)
  }, [freqForCents])

  // ── Geometry: pointer angle around the wheel ──────────────────────────────
  const pointerAngle = useCallback((clientX, clientY) => {
    const el = wheelRef.current
    if (!el) return 0
    const rect = el.getBoundingClientRect()
    const dx = clientX - (rect.left + rect.width / 2)
    const dy = clientY - (rect.top + rect.height / 2)
    let deg = Math.atan2(dx, -dy) * (180 / Math.PI)
    if (deg < 0) deg += 360
    return deg
  }, [])

  const indexFromRotation = useCallback((rot) => {
    const raw = -rot / STEP
    const wrapped = ((raw % SHRUTIS.length) + SHRUTIS.length) % SHRUTIS.length
    return { nearest: Math.round(wrapped) % SHRUTIS.length, frac: wrapped }
  }, [])

  // ── Drag gesture ──────────────────────────────────────────────────────────
  const handlePointerDown = useCallback((event) => {
    if (scanningRef.current) return
    event.preventDefault()
    wheelRef.current?.focus({ preventScroll: true })
    const angle = pointerAngle(event.clientX, event.clientY)
    dragRef.current = {
      active: true,
      startAngle: angle,
      startRotation: rotationDeg,
      moved: false,
    }
    setDragging(true)
    try { event.currentTarget.setPointerCapture(event.pointerId) } catch { /* ignore */ }
    const { frac } = indexFromRotation(rotationDeg)
    startGlide(CENTS_23[Math.floor(frac) % SHRUTIS.length])
    setPlayingIdx(activeIndex)
  }, [pointerAngle, rotationDeg, indexFromRotation, startGlide, activeIndex])

  const handlePointerMove = useCallback((event) => {
    if (!dragRef.current.active) return
    const angle = pointerAngle(event.clientX, event.clientY)
    let delta = angle - dragRef.current.startAngle
    delta = ((delta + 540) % 360) - 180
    if (Math.abs(delta) > 3) dragRef.current.moved = true
    const rot = dragRef.current.startRotation + delta
    setRotationDeg(rot)
    const { nearest, frac } = indexFromRotation(rot)
    glideToFraction(frac)
    setPlayingIdx(nearest)
    if (SHRUTIS[nearest].name !== selectedSwara) onSelect?.(SHRUTIS[nearest].name)
  }, [pointerAngle, indexFromRotation, glideToFraction, onSelect, selectedSwara])

  const endDrag = useCallback(() => {
    if (!dragRef.current.active) return
    const moved = dragRef.current.moved
    dragRef.current.active = false
    setDragging(false)
    const { nearest } = indexFromRotation(rotationDeg)
    onSelect?.(SHRUTIS[nearest].name)
    setRotationDeg(prev => nearestAngle(-nearest * STEP, prev))
    stopGlide(moved ? 0.14 : 0.4)
    window.setTimeout(() => setPlayingIdx(null), moved ? 180 : 520)
  }, [indexFromRotation, rotationDeg, onSelect, stopGlide])

  // ── Keyboard navigation ───────────────────────────────────────────────────
  const selectAndPlay = useCallback((index) => {
    const i = ((index % SHRUTIS.length) + SHRUTIS.length) % SHRUTIS.length
    onSelect?.(SHRUTIS[i].name)
    playNote(SHRUTIS[i].cents)
    setPlayingIdx(i)
    window.setTimeout(() => setPlayingIdx(prev => (prev === i ? null : prev)), 560)
  }, [onSelect, playNote])

  const handleKeyDown = useCallback((event) => {
    const key = event.key
    if (key === 'ArrowRight' || key === 'ArrowDown') {
      event.preventDefault()
      selectAndPlay(activeIndex + 1)
    } else if (key === 'ArrowLeft' || key === 'ArrowUp') {
      event.preventDefault()
      selectAndPlay(activeIndex - 1)
    } else if (key === 'Home') {
      event.preventDefault()
      selectAndPlay(0)
    } else if (key === 'End') {
      event.preventDefault()
      selectAndPlay(SHRUTIS.length - 1)
    } else if (key === 'Enter' || key === ' ') {
      event.preventDefault()
      selectAndPlay(activeIndex)
    }
  }, [activeIndex, selectAndPlay])

  // ── Rāga scale playback ───────────────────────────────────────────────────
  const stopScale = useCallback(() => {
    scanningRef.current = false
    setScanning(false)
    scaleTimersRef.current.forEach(clearTimeout)
    scaleTimersRef.current = []
    setPlayingIdx(null)
    setRotationDeg(prev => nearestAngle(-activeIndex * STEP, prev))
  }, [activeIndex])

  const playRagaScale = useCallback(() => {
    if (scanningRef.current) {
      stopScale()
      return
    }
    if (ragaSequence.length === 0) return
    scanningRef.current = true
    setScanning(true)
    const run = (step) => {
      if (step >= ragaSequence.length) {
        scanningRef.current = false
        setScanning(false)
        setPlayingIdx(null)
        return
      }
      const bin = ragaSequence[step]
      const keyIdx = bin % SHRUTIS.length
      const cents = CENTS_23[bin]
      setPlayingIdx(keyIdx)
      setRotationDeg(-keyIdx * STEP)
      onSelect?.(SHRUTIS[keyIdx].name)
      playNote(cents, 0.42)
      scaleTimersRef.current.push(window.setTimeout(() => run(step + 1), 440))
    }
    run(0)
  }, [ragaSequence, playNote, onSelect, stopScale])

  // ── Teardown ──────────────────────────────────────────────────────────────
  useEffect(() => () => {
    scaleTimersRef.current.forEach(clearTimeout)
    stopGlide(0.05)
    if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
      audioCtxRef.current.close().catch(() => {})
    }
  }, [stopGlide])

  const displayIdx = hoveredIdx ?? activeIndex
  const display = SHRUTIS[displayIdx]
  const isPreview = hoveredIdx != null && hoveredIdx !== activeIndex
  const sideKnob = dragging ? 'grabbing' : 'grab'

  return (
    <section className="instrument-panel" aria-label="Interactive 22 Shruti acoustic instrument">
      <div className="instrument-heading">
        <span className="eyebrow">The 22-fold scale</span>
        <span className="instrument-index">ŚRUTI YANTRA · I</span>
      </div>

      <div className="instrument-stage">
        <div
          className={`instrument-wheel ${dragging ? 'is-dragging' : ''} ${scanning ? 'is-scanning' : ''}`}
          ref={wheelRef}
          role="slider"
          tabIndex={0}
          aria-label="22 Shruti rotary dial — drag, or use arrow keys"
          aria-valuemin={0}
          aria-valuemax={SHRUTIS.length - 1}
          aria-valuenow={activeIndex}
          aria-valuetext={SHRUTIS[activeIndex].name}
          style={{ cursor: sideKnob, touchAction: 'none' }}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
          onKeyDown={handleKeyDown}
        >
          <div
            className="wheel-needle"
            aria-hidden="true"
            data-active={playingIdx != null ? 'true' : 'false'}
          />

          <div
            className="wheel-rotor"
            style={{ transform: `rotate(${rotationDeg}deg)` }}
          >
            <div className="wheel-engraving" aria-hidden="true" />

            <svg className="wheel-geometry" viewBox="0 0 500 500" aria-hidden="true">
              <circle cx="250" cy="250" r="212" />
              <circle cx="250" cy="250" r="177" />
              <circle cx="250" cy="250" r="132" />
              {SHRUTIS.map((_, index) => {
                const angle = (index / SHRUTIS.length) * Math.PI * 2 - Math.PI / 2
                const inner = 139
                const outer = index % 3 === 0 ? 210 : 199
                return (
                  <line
                    key={index}
                    x1={250 + Math.cos(angle) * inner}
                    y1={250 + Math.sin(angle) * inner}
                    x2={250 + Math.cos(angle) * outer}
                    y2={250 + Math.sin(angle) * outer}
                  />
                )
              })}
              <path d="M250 78 422 250 250 422 78 250Z" />
              <path d="M250 118 382 250 250 382 118 250Z" />
            </svg>

            {energy && (
              <svg className="wheel-energy" viewBox="0 0 500 500" aria-hidden="true">
                {energy.map((e, index) => {
                  const a = (index / SHRUTIS.length) * Math.PI * 2 - Math.PI / 2
                  const r0 = 150
                  const r1 = r0 + e * 96
                  return (
                    <line
                      key={`spoke-${index}`}
                      x1={250 + Math.cos(a) * r0}
                      y1={250 + Math.sin(a) * r0}
                      x2={250 + Math.cos(a) * r1}
                      y2={250 + Math.sin(a) * r1}
                      style={{ stroke: `var(--tone-${SHRUTIS[index].family})` }}
                      strokeWidth={index === displayIdx ? 3 : 1.6}
                      opacity={0.35 + e * 0.6}
                    />
                  )
                })}
                <polygon
                  points={energy.map((e, index) => {
                    const a = (index / SHRUTIS.length) * Math.PI * 2 - Math.PI / 2
                    const r = 150 + e * 96
                    return `${250 + Math.cos(a) * r},${250 + Math.sin(a) * r}`
                  }).join(' ')}
                />
              </svg>
            )}

            {SHRUTIS.map((shruti, index) => {
              const angle = (index / SHRUTIS.length) * Math.PI * 2 - Math.PI / 2
              const radius = 43
              const left = 50 + (Math.cos(angle) * radius)
              const top = 50 + (Math.sin(angle) * radius)
              const isDetected = detectedNames.has(shruti.name)
              const isSelected = index === activeIndex
              const isHovered = index === hoveredIdx
              const isPlaying = index === playingIdx
              const inScale = ragaScale.has(index)
              return (
                <button
                  key={shruti.name}
                  type="button"
                  className={[
                    'shruti-mark',
                    isSelected ? 'is-selected' : '',
                    isHovered ? 'is-hovered' : '',
                    isPlaying ? 'is-playing' : '',
                    isDetected ? 'is-detected' : '',
                    inScale ? 'is-scale' : '',
                  ].join(' ')}
                  style={{
                    left: `${left}%`,
                    top: `${top}%`,
                    '--family-tone': `var(--tone-${shruti.family})`,
                    transform: `translate(-50%, -50%) rotate(${-rotationDeg}deg)`,
                  }}
                  tabIndex={-1}
                  onMouseEnter={() => setHoveredIdx(index)}
                  onMouseLeave={() => setHoveredIdx(prev => (prev === index ? null : prev))}
                  aria-label={`${shruti.name}${isDetected ? ', detected in this recording' : ''}`}
                  title={isDetected ? `${shruti.name} · detected in analysis` : shruti.name}
                >
                  {shruti.name}
                </button>
              )
            })}
          </div>

          <div className="instrument-heart">
            <span className="heart-caption">{isPreview ? 'PREVIEW' : 'SWARA'}</span>
            <strong>{display.name}</strong>
            <span className="heart-rule" />
            <span className="heart-readout">
              {(tonic * Math.pow(2, display.cents / 1200)).toFixed(1)} Hz
            </span>
            <span className="heart-caption">
              {display.cents.toFixed(1)}¢ · ratio {display.ratio}
            </span>
            <span className="heart-caption">
              {detectedNames.has(display.name) ? 'FOUND IN RECORDING' : 'SELECTED DEGREE'}
            </span>
          </div>
        </div>
      </div>

      <div className="yantra-controls">
        <button
          type="button"
          className="engraved-button small"
          onClick={playRagaScale}
          disabled={ragaSequence.length === 0}
          title={ragaSequence.length === 0 ? 'Analyse a recording to play its rāga scale' : 'Play the detected rāga up and down'}
        >
          {scanning ? '■ Stop scale' : '▶ Play rāga scale'}
        </button>
        <span className="yantra-hint">
          {dragging
            ? 'Gliding through the 22 śrutis…'
            : 'Drag round the wheel to glide · arrows to step · Enter to sound'}
        </span>
      </div>

      <div className="instrument-legend">
        {FAMILIES.map(family => (
          <span className="legend-entry" key={family}>
            <i style={{ '--family-tone': `var(--tone-${family})` }} />
            {family}
          </span>
        ))}
      </div>
      <p className="instrument-note">
        {detectedNames.size
          ? `${detectedNames.size} swara${detectedNames.size === 1 ? '' : 's'} marked from this analysis${energy ? ' · spokes show where the voice lingered' : ''}`
          : 'Select an engraved degree to inspect the 22-step scale'}
      </p>
    </section>
  )
}
