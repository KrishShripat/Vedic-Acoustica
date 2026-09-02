import Plot from 'react-plotly.js'

const SWARA_NAMES = [
  'Sa', 'Re1', 'Re2', 'Ga1', 'Ga2', 'Ga3',
  'Ma1', 'Ma2', 'Ma3', 'Pa', 'Dha1', 'Dha2',
  'Ni1', 'Ni2', 'Ni3',
]

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

export default function RagaViz({ data, onReady }) {
  if (!data?.raga_detection) return <p>No raga detection data</p>

  const raga = data.raga_detection
  const matches = raga.matches || []
  const detectedSwaras = raga.detected_swaras || []

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
                {s.swara} ({s.hits})
              </span>
            ))}
          </div>
        )}
      </div>
    )
  }

  const best = matches[0]

  return (
    <div>
      <div style={{
        padding: '1rem', marginBottom: '1rem',
        background: 'rgba(233, 69, 96, 0.08)',
        borderRadius: '8px', border: '1px solid #e94560',
      }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '0.25rem' }}>
          <strong style={{ color: '#e94560', fontSize: '1.15rem' }}>{best.raga_name}</strong>
          <span style={{
            fontSize: '0.7rem', padding: '0.15rem 0.4rem',
            borderRadius: '3px', background: 'rgba(233, 69, 96, 0.2)',
            color: '#e94560',
          }}>
            {best.tradition}
          </span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginLeft: 'auto' }}>
            {(best.confidence * 100).toFixed(1)}% match
          </span>
        </div>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.25rem 0' }}>
          {best.time} &middot; {best.mood}
        </p>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.25rem 0' }}>
          Vadi: {best.vadi} &middot; Samvadi: {best.samvadi}
        </p>
        <ScaleStrip swaras={best.arohana} label="Arohana" highlight={best.details?.matched_swaras} />
        <ScaleStrip swaras={best.avarohana} label="Avarohana" highlight={best.details?.matched_swaras} />
      </div>

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

      <Plot
        data={[
          {
            x: matches.slice(0, 5).map(m => m.raga_name),
            y: matches.slice(0, 5).map(m => m.confidence * 100),
            type: 'bar',
            marker: {
              color: matches.slice(0, 5).map((_, i) =>
                i === 0 ? 'rgba(233, 69, 96, 0.8)' : 'rgba(233, 69, 96, 0.35)'
              ),
              line: {
                color: matches.slice(0, 5).map((_, i) =>
                  i === 0 ? '#e94560' : 'rgba(233, 69, 96, 0.5)'
                ),
                width: 1,
              },
            },
            text: matches.slice(0, 5).map(m => `${(m.confidence * 100).toFixed(1)}%`),
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
          height: 220,
          showlegend: false,
        }}
        onInitialized={() => onReady?.()}
        onUpdate={() => onReady?.()}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: '100%' }}
      />

      {detectedSwaras.length > 0 && (
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textAlign: 'center', marginTop: '0.5rem' }}>
          {detectedSwaras.length} unique swaras detected across {raga.total_frames_analyzed} frames
        </p>
      )}
    </div>
  )
}
