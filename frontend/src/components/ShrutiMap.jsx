import Plot from 'react-plotly.js'

const SHRUTI_NAMES = [
  'Sa', 'Re1', 'Re2', 'Ga1', 'Ga2', 'Ga3',
  'Ma1', 'Ma2', 'Ma3', 'Pa', 'Dha1', 'Dha2',
  'Ni1', 'Ni2', 'Ni3', 'Sa\'', 'Re\'', 'Ga\'',
  'Ma\'', 'Pa\'', 'Dha\'', 'Ni\'',
]

const REFERENCE_FREQ = 261.626
const SHRUTI_RATIOS = [
  1.0, 256/243, 16/15, 10/9, 9/8, 32/27,
  5/4, 81/64, 4/3, 729/512, 3/2, 128/81,
  8/5, 5/3, 27/16, 16/9, 9/5, 15/8,
  243/128, 2/1, 25/8, 3,
]

const SHRUTI_FREQS = SHRUTI_RATIOS.map(r => REFERENCE_FREQ * r)

export default function ShrutiMap({ data, onReady }) {
  if (!data?.dominant_frequencies) return <p>No frequency data</p>

  const detectedFreqs = data.dominant_frequencies
  const histogram = new Array(22).fill(0)
  detectedFreqs.forEach(f => {
    let minDist = Infinity
    let closestIdx = 0
    SHRUTI_FREQS.forEach((sf, i) => {
      const dist = Math.abs(f - sf)
      if (dist < minDist) {
        minDist = dist
        closestIdx = i
      }
    })
    histogram[closestIdx]++
  })

  return (
    <div>
      <Plot
        data={[
          {
            x: SHRUTI_NAMES.slice(0, 22),
            y: SHRUTI_FREQS.slice(0, 22),
            type: 'bar',
            marker: {
              color: histogram.map(count =>
                count > 0 ? 'rgba(233, 69, 96, 0.8)' : 'rgba(42, 42, 62, 0.6)'
              ),
              line: {
                color: histogram.map(count =>
                  count > 0 ? '#e94560' : '#3a3a4e'
                ),
                width: 1,
              },
            },
            text: histogram.map(c => c > 0 ? `${c} hits` : ''),
            textposition: 'outside',
            textfont: { color: '#888', size: 9 },
          },
        ]}
        layout={{
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          margin: { t: 10, r: 10, b: 100, l: 50 },
          xaxis: {
            tickangle: -45,
            tickfont: { color: '#888', size: 8 },
          },
          yaxis: {
            title: { text: 'Frequency (Hz)', font: { color: '#888' } },
            tickfont: { color: '#888' },
            gridcolor: '#2a2a3e',
          },
          height: 320,
          showlegend: false,
        }}
        onInitialized={() => onReady?.()}
        onUpdate={() => onReady?.()}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: '100%' }}
      />
      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textAlign: 'center', marginTop: '0.5rem' }}>
        Detected frequencies mapped to 22 Shruti microtonal bins
      </p>
    </div>
  )
}
