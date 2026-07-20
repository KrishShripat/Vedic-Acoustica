import Plot from 'react-plotly.js'

const EXPECTED_PATTERN = [1, 2, 2, 1, 1, 2, 3, 3, 2, 1, 1, 2, 3]

export default function GhanaPathaViz({ data }) {
  if (!data) return <p>No Ghana Patha data</p>

  const isValid = data.ghana_patha_valid
  const confidence = data.ghana_patha_confidence
  const segments = data.segments || data.ghana_patha_segments || []

  const detectedPattern = segments.map(s => s.cluster_label)

  return (
    <div>
      <div style={{
        display: 'flex', alignItems: 'center', gap: '1rem',
        marginBottom: '1rem', padding: '1rem',
        background: isValid ? 'rgba(76, 175, 80, 0.1)' : 'rgba(233, 69, 96, 0.1)',
        borderRadius: '8px', border: `1px solid ${isValid ? '#4caf50' : '#e94560'}`,
      }}>
        <span style={{ fontSize: '2rem' }}>{isValid ? '\u2705' : '\u274c'}</span>
        <div>
          <strong style={{ color: isValid ? '#4caf50' : '#e94560' }}>
            {isValid ? 'Pattern Valid' : 'Pattern Invalid'}
          </strong>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Confidence: {(confidence * 100).toFixed(1)}%
          </p>
        </div>
      </div>

      {detectedPattern.length > 0 && (
        <Plot
          data={[
            {
              x: detectedPattern.map((_, i) => i + 1),
              y: detectedPattern,
              type: 'scatter',
              mode: 'lines+markers',
              name: 'Detected',
              line: { color: '#e94560', width: 2 },
              marker: { size: 8, color: '#e94560' },
            },
            {
              x: EXPECTED_PATTERN.map((_, i) => i + 1),
              y: EXPECTED_PATTERN,
              type: 'scatter',
              mode: 'lines+markers',
              name: 'Expected (1-2, 2-1, 1-2-3, 3-2-1, 1-2-3)',
              line: { color: '#4caf50', width: 2, dash: 'dash' },
              marker: { size: 8, color: '#4caf50' },
            },
          ]}
          layout={{
            paper_bgcolor: 'transparent',
            plot_bgcolor: 'transparent',
            margin: { t: 10, r: 10, b: 40, l: 40 },
            xaxis: {
              title: { text: 'Segment Index', font: { color: '#888' } },
              tickfont: { color: '#888' },
              gridcolor: '#2a2a3e',
            },
            yaxis: {
              title: { text: 'Cluster Label', font: { color: '#888' } },
              tickfont: { color: '#888' },
              gridcolor: '#2a2a3e',
            },
            height: 250,
            legend: {
              font: { color: '#888', size: 10 },
              bgcolor: 'transparent',
            },
          }}
          config={{ displayModeBar: false, responsive: true }}
          style={{ width: '100%' }}
        />
      )}

      {data.detected_pattern && (
        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
          Detected sequence: [{data.detected_pattern.join(', ')}]
        </p>
      )}
    </div>
  )
}
