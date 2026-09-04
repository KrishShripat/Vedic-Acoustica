import { useState } from 'react'
import Plot from 'react-plotly.js'

// Phrase-level direction cycle: forward=2, reverse=1
// Matches backend GHANA_CYCLE — repeated to cover all detected segments.
const PHRASE_DIR = { forward: 2, reverse: 1 }
const FALLBACK_CYCLE = [2, 1, 2, 1, 2]

// ── Phrase-type styling ───────────────────────────────────────────────────────
const PHRASE_STYLE = {
  forward: { color: '#06d6a0', label: 'Fwd ↑', icon: '↑' },
  reverse: { color: '#e94560', label: 'Rev ↓', icon: '↓' },
}

function getPhraseStyle(seg) {
  if (seg?.phrase_type === 'forward') return PHRASE_STYLE.forward
  if (seg?.phrase_type === 'reverse') return PHRASE_STYLE.reverse
  // Legacy cluster_label path: odd = forward, even = reverse heuristic
  const lbl = seg?.cluster_label
  if (typeof lbl === 'number') return lbl % 2 === 1 ? PHRASE_STYLE.forward : PHRASE_STYLE.reverse
  return { color: '#888', label: '?', icon: '·' }
}

/**
 * GhanaPathaViz
 *
 * Props:
 *   data       – analysis result object
 *   duration   – total audio duration in seconds
 *   playerRef  – React ref to AudioPlayer; exposes .seekTo(seconds)
 *   onReady    – called after Plotly chart initialises
 */
export default function GhanaPathaViz({ data, duration, playerRef, onReady }) {
  const [activeSegIdx, setActiveSegIdx] = useState(null)

  if (!data) return <p>No Ghana Patha data</p>

  const isValid    = data.ghana_patha_valid
  const confidence = data.ghana_patha_confidence
  const nSegments  = data.ghana_patha_n_segments || 0
  const segments   = data.segments ?? data.ghana_patha_segments ?? []

  // Detected pattern for the scatter plot
  // New PCP/DTW path emits per-segment `phrase_type` ('forward'|'reverse');
  // the legacy path emitted a numeric `cluster_label`. Normalise both to a
  // numeric phrase level so the Detected trace renders regardless of backend.
  const detectedPattern = Array.isArray(segments)
    ? segments
        .map(s => {
          if (s?.phrase_type === 'forward') return PHRASE_DIR.forward
          if (s?.phrase_type === 'reverse') return PHRASE_DIR.reverse
          if (typeof s?.cluster_label === 'number') return s.cluster_label
          return null
        })
        .filter(v => typeof v === 'number')
    : []

  // Derive expected phrase-level line from backend data.
  // ghana_patha_expected_cycle is ['forward','reverse',...] from GHANA_CYCLE.
  // Repeat it to match detected segment count so both traces share the same
  // x-axis length.
  const expectedPattern = (() => {
    const raw = data.ghana_patha_expected_cycle
    if (Array.isArray(raw) && raw.length > 0) {
      const cycle = raw.map(v => (v === 'forward') ? PHRASE_DIR.forward : PHRASE_DIR.reverse)
      const n = detectedPattern.length || cycle.length
      return Array.from({ length: n }, (_, i) => cycle[i % cycle.length])
    }
    // Fallback: repeat the canonical 5-phase cycle
    const n = detectedPattern.length || FALLBACK_CYCLE.length
    return Array.from({ length: n }, (_, i) => FALLBACK_CYCLE[i % FALLBACK_CYCLE.length])
  })()

  // ── Compute per-segment timestamps ─────────────────────────────────────────
  // The backend divides the audio into n_segments equal slices, so each
  // segment spans duration / n_segments seconds.
  const n = nSegments || segments.length || 1
  const segDuration = duration > 0 ? duration / n : 0

  const segmentTimestamp = (idx) => idx * segDuration   // start time of segment

  // ── Seek handler ────────────────────────────────────────────────────────────
  const handleSegmentClick = (idx) => {
    setActiveSegIdx(idx)
    const t = segmentTimestamp(idx)
    playerRef?.current?.seekTo(t)
  }

  const formatTime = (s) => {
    if (!s || !isFinite(s)) return '0:00'
    const m   = Math.floor(s / 60)
    const sec = Math.floor(s % 60)
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  return (
    <div>
      {/* ── Verdict banner ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: '1rem',
        marginBottom: '1rem', padding: '1rem',
        background: isValid ? 'rgba(76,175,80,0.1)' : 'rgba(233,69,96,0.1)',
        borderRadius: '8px',
        border: `1px solid ${isValid ? '#4caf50' : '#e94560'}`,
      }}>
        <span style={{ fontSize: '2rem' }}>{isValid ? '✅' : '❌'}</span>
        <div>
          <strong style={{ color: isValid ? '#4caf50' : '#e94560' }}>
            {isValid ? 'Pattern Valid' : 'Pattern Invalid'}
          </strong>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>
            Confidence: {(confidence * 100).toFixed(1)}%
            {nSegments > 0 && <> &middot; {nSegments} segments</>}
            {segDuration > 0 && <> &middot; ~{segDuration.toFixed(1)}s each</>}
          </p>
        </div>
      </div>

      {/* ── Clickable segment timeline ──────────────────────────────────────── */}
      {segments.length > 0 ? (
        <div style={{ marginBottom: '1.25rem' }}>
          <p style={{
            fontSize: '0.78rem', color: 'var(--text-secondary)',
            marginBottom: '0.6rem', display: 'flex', alignItems: 'center', gap: '0.5rem',
          }}>
            <span style={{ fontSize: '0.9rem' }}>🎯</span>
            Click a segment to jump AudioPlayer to that position
          </p>

          {/* Legend */}
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.6rem' }}>
            {Object.values(PHRASE_STYLE).map(ps => (
              <span key={ps.label} style={{
                fontSize: '0.72rem', display: 'flex', alignItems: 'center', gap: '0.3rem',
                color: ps.color,
              }}>
                <span style={{
                  display: 'inline-block', width: 10, height: 10,
                  borderRadius: '50%', background: ps.color,
                }} />
                {ps.label}
              </span>
            ))}
            <span style={{
              fontSize: '0.72rem', color: 'var(--text-secondary)',
              marginLeft: 'auto',
            }}>
              DTW similarity shown inside dot
            </span>
          </div>

          {/* Segment dots row */}
          <div className="ghana-timeline">
            {segments.map((seg, i) => {
              const ps        = getPhraseStyle(seg)
              const sim       = seg.dtw_similarity ?? null
              const t         = segmentTimestamp(seg.index ?? i)
              const isActive  = activeSegIdx === (seg.index ?? i)
              const simLabel  = sim !== null ? `${Math.round(sim * 100)}` : '?'

              return (
                <button
                  key={seg.index ?? i}
                  className={`ghana-seg-btn ${isActive ? 'active' : ''}`}
                  style={{ '--seg-color': ps.color }}
                  onClick={() => handleSegmentClick(seg.index ?? i)}
                  title={`Segment ${(seg.index ?? i) + 1} · ${ps.label} · t=${formatTime(t)} · sim=${sim !== null ? (sim * 100).toFixed(1) + '%' : 'n/a'}`}
                >
                  <span className="ghana-seg-icon">{ps.icon}</span>
                  <span className="ghana-seg-sim">{simLabel}</span>
                  <span className="ghana-seg-time">{formatTime(t)}</span>
                </button>
              )
            })}
          </div>

          {activeSegIdx !== null && segments[activeSegIdx] && (
            <p style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
              ▶ Jumped to segment {activeSegIdx + 1} at {formatTime(segmentTimestamp(activeSegIdx))}
              {' '}— {getPhraseStyle(segments[activeSegIdx]).label}
            </p>
          )}
        </div>
      ) : (
        <p style={{
          fontSize: '0.85rem', color: 'var(--text-secondary)',
          marginBottom: '1rem', padding: '0.6rem 1rem',
          background: 'rgba(136,136,152,0.1)', borderRadius: '8px',
        }}>
          No segment-level pattern data — showing expected Ghana Patha phrase pattern only.
        </p>
      )}

      {/* ── Scatter plot (pattern shape) ─────────────────────────────────────── */}
      <Plot
        data={[
          {
            x: expectedPattern.map((_, i) => i + 1),
            y: expectedPattern,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Expected',
            line:   { color: '#4caf50', width: 2, dash: 'dash' },
            marker: { size: 8, color: '#4caf50' },
          },
          ...(detectedPattern.length > 0 ? [{
            x: detectedPattern.map((_, i) => i + 1),
            y: detectedPattern,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Detected',
            line:   { color: '#e94560', width: 2 },
            marker: { size: 8, color: '#e94560' },
          }] : []),
          // Highlight active segment with a vertical band
          ...(activeSegIdx !== null && detectedPattern.length > 0 ? [{
            x: [activeSegIdx + 1, activeSegIdx + 1],
            y: [0, Math.max(...expectedPattern) + 1],
            type: 'scatter',
            mode: 'lines',
            name: 'Selected',
            line: { color: 'rgba(255,107,107,0.4)', width: 18 },
            showlegend: false,
            hoverinfo: 'skip',
          }] : []),
        ]}
        layout={{
          paper_bgcolor: 'transparent',
          plot_bgcolor:  'transparent',
          margin: { t: 10, r: 20, b: 40, l: 40 },
          xaxis: {
            title:    { text: 'Segment', font: { color: '#888' } },
            tickfont: { color: '#888' },
            gridcolor: '#2a2a3e',
          },
          yaxis: {
            title:    { text: 'Phrase Level', font: { color: '#888' } },
            tickfont: { color: '#888' },
            gridcolor: '#2a2a3e',
          },
          height: 220,
          legend: { font: { color: '#888', size: 10 }, bgcolor: 'transparent' },
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: '100%' }}
        onInitialized={() => onReady?.()}

      />

      {data.ghana_patha_detected_pattern && (
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
          Detected sequence: [{data.ghana_patha_detected_pattern.join(', ')}]
        </p>
      )}
    </div>
  )
}
