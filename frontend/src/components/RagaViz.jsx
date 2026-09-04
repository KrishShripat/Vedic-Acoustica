import Plot from 'react-plotly.js'

const SWARA_NAMES = [
  'Sa', 'Re1', 'Re2', 'Ga1', 'Ga2', 'Ga3',
  'Ma1', 'Ma2', 'Ma3', 'Tivra Ma', 'Pa', 'Dha1',
  'Dha2', 'Ni1', 'Ni2', 'Ni3',
]

const THRESHOLD_PCT = 40   // kept in sync with backend CONFIDENCE_THRESHOLD * 100

function swaraLabel(idx) {
  return SWARA_NAMES[idx] ?? String(idx)
}

function ScaleStrip({ swaras, label, highlight }) {
  return (
    <div style={{ marginBottom: '0.5rem' }}>
      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginRight: '0.5rem' }}>
        {label}:
      </span>
      {swaras.map((s, i) => (
        <span
          key={i}
          style={{
            display: 'inline-block',
            padding: '0.15rem 0.45rem',
            margin: '0.1rem',
            borderRadius: '4px',
            fontSize: '0.75rem',
            fontWeight: highlight?.includes(s) ? 700 : 400,
            background: highlight?.includes(s)
              ? 'rgba(233, 69, 96, 0.25)'
              : 'rgba(42, 42, 62, 0.6)',
            color: highlight?.includes(s) ? '#e94560' : '#aaa',
            border: `1px solid ${highlight?.includes(s) ? '#e94560' : '#3a3a4e'}`,
          }}
        >
          {swaraLabel(s)}
        </span>
      ))}
    </div>
  )
}

/** Amber "Inconclusive" banner shown when confidence < threshold */
function InconclusiveCard({ raga, onReady }) {
  const detectedSwaras = raga.detected_swaras || []
  const best = raga.best_match   // may be null or low-confidence

  return (
    <div>
      {/* ── Main warning card ─────────────────────────────────────────────── */}
      <div
        id="raga-inconclusive-card"
        style={{
          padding: '1rem 1.25rem',
          marginBottom: '1rem',
          background: 'rgba(245, 158, 11, 0.08)',
          borderRadius: '10px',
          border: '1px solid rgba(245, 158, 11, 0.55)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem' }}>
          {/* amber warning icon */}
          <span style={{ fontSize: '1.1rem' }}>⚠️</span>
          <strong style={{ color: '#f59e0b', fontSize: '1.05rem', letterSpacing: '0.01em' }}>
            Inconclusive
          </strong>
          <span style={{
            marginLeft: 'auto',
            fontSize: '0.7rem',
            padding: '0.15rem 0.45rem',
            borderRadius: '4px',
            background: 'rgba(245, 158, 11, 0.15)',
            color: '#f59e0b',
            border: '1px solid rgba(245, 158, 11, 0.4)',
          }}>
            &lt; {THRESHOLD_PCT}% confidence
          </span>
        </div>

        <p style={{
          fontSize: '0.82rem',
          color: 'var(--text-secondary)',
          margin: '0 0 0.6rem',
          lineHeight: 1.5,
        }}>
          {raga.inconclusive_reason || 'Confidence too low to make a reliable raga identification.'}
        </p>

        {/* Best guess (shown but clearly marked as speculative) */}
        {best && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: '0.6rem',
            padding: '0.5rem 0.75rem',
            background: 'rgba(42, 42, 62, 0.5)',
            borderRadius: '6px',
            border: '1px solid #3a3a4e',
          }}>
            <span style={{ fontSize: '0.75rem', color: '#888' }}>Closest guess:</span>
            <span style={{ fontSize: '0.85rem', color: '#ccc', fontWeight: 600 }}>{best.raga_name}</span>
            <span style={{
              fontSize: '0.65rem', padding: '0.1rem 0.3rem', borderRadius: '3px',
              background: 'rgba(42, 42, 62, 0.8)', color: '#888',
            }}>
              {best.tradition}
            </span>
            <span style={{ marginLeft: 'auto', fontSize: '0.8rem', color: '#f59e0b' }}>
              {(best.confidence * 100).toFixed(1)}%
            </span>
          </div>
        )}
      </div>

      {/* ── Detected swaras ───────────────────────────────────────────────── */}
      {detectedSwaras.length > 0 && (
        <div style={{ marginBottom: '0.75rem' }}>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Detected swaras: </span>
          {detectedSwaras.map((s, i) => (
            <span key={i} style={{
              display: 'inline-block', padding: '0.15rem 0.45rem', margin: '0.1rem',
              borderRadius: '4px', fontSize: '0.75rem',
              background: 'rgba(245, 158, 11, 0.12)', color: '#f59e0b',
              border: '1px solid rgba(245, 158, 11, 0.4)',
            }}>
              {s.swara}
            </span>
          ))}
        </div>
      )}

      {/* ── Candidate bar chart (still useful for research) ───────────────── */}
      {raga.matches?.length > 0 && (
        <ConfidenceChart matches={raga.matches} inconclusive onReady={onReady} />
      )}

      <p style={{ fontSize: '0.75rem', color: '#666', textAlign: 'center', marginTop: '0.5rem' }}>
        {detectedSwaras.length} swara{detectedSwaras.length !== 1 ? 's' : ''} detected
        across {raga.total_frames_analyzed} frames
      </p>
    </div>
  )
}

/** Confidence bar chart — shared between conclusive and inconclusive views */
function ConfidenceChart({ matches, inconclusive, onReady }) {
  const top = matches.slice(0, 5)
  const barColors = top.map((_, i) => {
    if (i !== 0) return 'rgba(233, 69, 96, 0.3)'
    return inconclusive ? 'rgba(245, 158, 11, 0.7)' : 'rgba(233, 69, 96, 0.8)'
  })
  const borderColors = top.map((_, i) => {
    if (i !== 0) return 'rgba(233, 69, 96, 0.45)'
    return inconclusive ? '#f59e0b' : '#e94560'
  })

  return (
    <Plot
      data={[
        {
          x: top.map(m => m.raga_name),
          y: top.map(m => m.confidence * 100),
          type: 'bar',
          marker: {
            color: barColors,
            line: { color: borderColors, width: 1 },
          },
          text: top.map(m => `${(m.confidence * 100).toFixed(1)}%`),
          textposition: 'outside',
          textfont: { color: '#888', size: 9 },
        },
      ]}
      layout={{
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        margin: { t: 10, r: 10, b: 80, l: 50 },
        xaxis: {
          tickangle: -30,
          tickfont: { color: '#888', size: 9 },
        },
        yaxis: {
          title: { text: 'Confidence (%)', font: { color: '#888' } },
          tickfont: { color: '#888' },
          gridcolor: '#2a2a3e',
          range: [0, 100],
        },
        // Threshold reference line
        shapes: [{
          type: 'line',
          xref: 'paper', x0: 0, x1: 1,
          yref: 'y', y0: THRESHOLD_PCT, y1: THRESHOLD_PCT,
          line: { color: 'rgba(245, 158, 11, 0.6)', width: 1.5, dash: 'dash' },
        }],
        annotations: [{
          xref: 'paper', x: 1,
          yref: 'y', y: THRESHOLD_PCT,
          text: `${THRESHOLD_PCT}% threshold`,
          showarrow: false,
          font: { color: 'rgba(245, 158, 11, 0.75)', size: 8 },
          xanchor: 'right',
          yanchor: 'bottom',
        }],
        height: 220,
        showlegend: false,
      }}
      onInitialized={() => onReady?.()}
      onUpdate={() => onReady?.()}
      config={{ displayModeBar: false, responsive: true }}
    />
  )
}

export default function RagaViz({ data, onReady }) {
  if (!data?.raga_detection) return <p>No raga detection data</p>

  const raga = data.raga_detection
  const matches = raga.matches || []
  const detectedSwaras = raga.detected_swaras || []

  // ── Zero-match path (pre-threshold filter removed everything) ────────────
  if (matches.length === 0) {
    return (
      <div>
        <p style={{
          fontSize: '0.85rem', color: 'var(--text-secondary)',
          padding: '0.75rem 1rem',
          background: 'rgba(136, 136, 152, 0.1)',
          borderRadius: '8px', marginBottom: '1rem',
        }}>
          No confident raga match found from {raga.total_frames_analyzed} analyzed frames.
        </p>
        {detectedSwaras.length > 0 && (
          <div style={{ marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Detected swaras: </span>
            {detectedSwaras.map((s, i) => (
              <span key={i} style={{
                display: 'inline-block', padding: '0.15rem 0.45rem', margin: '0.1rem',
                borderRadius: '4px', fontSize: '0.75rem',
                background: 'rgba(233, 69, 96, 0.15)', color: '#e94560',
                border: '1px solid #e94560',
              }}>
                {s.swara} ({s.weight?.toFixed(2) ?? '—'})
              </span>
            ))}
          </div>
        )}
      </div>
    )
  }

  // ── Inconclusive path (matches exist but all below threshold) ────────────
  if (raga.is_inconclusive) {
    return <InconclusiveCard raga={raga} onReady={onReady} />
  }

  // ── Conclusive match ─────────────────────────────────────────────────────
  const best = matches[0]
  const confidencePct = best.confidence * 100
  // Colour ramps from amber (40–60%) to red (≥60%) so the user sees gradation
  const isLowConfidence = confidencePct < 60
  const accentColor = isLowConfidence ? '#f59e0b' : '#e94560'
  const accentBg = isLowConfidence ? 'rgba(245,158,11,0.08)' : 'rgba(233,69,96,0.08)'
  const accentBorder = isLowConfidence ? 'rgba(245,158,11,0.55)' : '#e94560'
  const badgeBg = isLowConfidence ? 'rgba(245,158,11,0.2)' : 'rgba(233,69,96,0.2)'

  return (
    <div>
      {/* ── Best match card ─────────────────────────────────────────────── */}
      <div
        id="raga-best-match-card"
        style={{
          padding: '1rem', marginBottom: '1rem',
          background: accentBg,
          borderRadius: '8px', border: `1px solid ${accentBorder}`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '0.25rem' }}>
          <strong style={{ color: accentColor, fontSize: '1.15rem' }}>{best.raga_name}</strong>
          <span style={{
            fontSize: '0.7rem', padding: '0.15rem 0.4rem',
            borderRadius: '3px', background: badgeBg,
            color: accentColor,
          }}>
            {best.tradition}
          </span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginLeft: 'auto' }}>
            {confidencePct.toFixed(1)}% match
          </span>
          {isLowConfidence && (
            <span style={{
              fontSize: '0.65rem', padding: '0.12rem 0.4rem',
              borderRadius: '3px',
              background: 'rgba(245,158,11,0.15)',
              color: '#f59e0b',
              border: '1px solid rgba(245,158,11,0.4)',
            }}>
              Low confidence
            </span>
          )}
        </div>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.25rem 0' }}>
          {best.time} &middot; {best.mood}
        </p>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.25rem 0' }}>
          Vadi: {best.vadi} &middot; Samvadi: {best.samvadi}
        </p>
        <ScaleStrip swaras={best.arohana} label="Arohana" highlight={best.details?.matched_swaras} />
        <ScaleStrip swaras={best.avarohana} label="Avarohana" highlight={best.details?.matched_swaras} />
        {isLowConfidence && (
          <p style={{
            fontSize: '0.75rem', color: 'rgba(245,158,11,0.8)',
            marginTop: '0.5rem', marginBottom: 0,
            padding: '0.4rem 0.6rem',
            background: 'rgba(245,158,11,0.07)',
            borderRadius: '5px',
            borderLeft: '2px solid rgba(245,158,11,0.5)',
          }}>
            Match confidence is between 40–60%. Treat this result as a provisional
            identification — consider recording a longer or cleaner sample.
          </p>
        )}
      </div>

      {/* ── Other candidates ────────────────────────────────────────────── */}
      {matches.length > 1 && (
        <div style={{ marginBottom: '1rem' }}>
          <h3 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
            Other Candidates
          </h3>
          {matches.slice(1).map((m, i) => (
            <div
              key={i}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '0.5rem 0.75rem', marginBottom: '0.35rem',
                background: 'rgba(42, 42, 62, 0.4)',
                borderRadius: '6px', border: '1px solid #3a3a4e',
              }}
            >
              <div>
                <span style={{ fontSize: '0.85rem', color: '#ccc' }}>{m.raga_name}</span>
                <span style={{
                  fontSize: '0.65rem', marginLeft: '0.5rem',
                  padding: '0.1rem 0.3rem', borderRadius: '3px',
                  background: 'rgba(42, 42, 62, 0.8)', color: '#888',
                }}>
                  {m.tradition}
                </span>
              </div>
              <span style={{ fontSize: '0.8rem', color: '#e94560' }}>
                {(m.confidence * 100).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      )}

      <ConfidenceChart matches={matches} inconclusive={false} onReady={onReady} />

      {detectedSwaras.length > 0 && (
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textAlign: 'center', marginTop: '0.5rem' }}>
          {detectedSwaras.length} unique swaras detected across {raga.total_frames_analyzed} frames
        </p>
      )}
    </div>
  )
}
