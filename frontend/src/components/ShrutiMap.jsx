import Plot from 'react-plotly.js'

const SHRUTI_NAMES = [
  'Sa', 'Re1', 'Re2', 'Ga1', 'Ga2', 'Ga3',
  'Ma1', 'Ma2', 'Ma3', 'Pa', 'Dha1', 'Dha2',
  'Ni1', 'Ni2', 'Ni3', "Sa'", "Re'", "Ga'",
  "Ma'", "Pa'", "Dha'", "Ni'",
]

// Colour ramps: cold (low energy) → hot (high energy)
function energyColour(energy) {
  // energy in [0, 1]; interpolate from dim teal to vivid amber/rose
  const r = Math.round(42  + (233 - 42)  * energy)
  const g = Math.round(180 + (69  - 180) * energy)
  const b = Math.round(140 + (96  - 140) * energy)
  const a = 0.4 + 0.6 * energy
  return `rgba(${r},${g},${b},${a})`
}

function energyBorderColour(energy) {
  if (energy < 0.05) return '#3a3a4e'
  const r = Math.round(160 + (255 - 160) * energy)
  const g = Math.round(100 + (50  - 100) * energy)
  const b = Math.round(120 + (70  - 120) * energy)
  return `rgb(${r},${g},${b})`
}

export default function ShrutiMap({ data, onReady }) {
  // Prefer the PCP mean_pcp vector when available; fall back to building a
  // normalised histogram from the old dominant_frequencies for backward compat.
  let energies

  if (Array.isArray(data?.mean_pcp) && data.mean_pcp.length === 22) {
    // PCP path (ML-2): values are already normalised 0-1
    const rawMax = Math.max(...data.mean_pcp, 1e-9)
    energies = data.mean_pcp.map(v => v / rawMax)
  } else if (Array.isArray(data?.dominant_frequencies)) {
    // Legacy path: build hit counts and normalise
    const REFERENCE_FREQ = 261.626
    const SHRUTI_RATIOS = [
      1.0,       256/243, 16/15,   10/9,    9/8,   32/27,
      5/4,       81/64,   4/3,     729/512, 3/2,   128/81,
      8/5,       5/3,     27/16,   16/9,    9/5,   15/8,
      243/128,   2/1,     8/3,     3,
    ]
    const shrutiFreqs = SHRUTI_RATIOS.map(r => REFERENCE_FREQ * r)
    const histogram = new Array(22).fill(0)
    data.dominant_frequencies.forEach(f => {
      let minDist = Infinity, closestIdx = 0
      shrutiFreqs.forEach((sf, i) => {
        const dist = Math.abs(f - sf)
        if (dist < minDist) { minDist = dist; closestIdx = i }
      })
      histogram[closestIdx]++
    })
    const maxCount = Math.max(...histogram, 1)
    energies = histogram.map(c => c / maxCount)
  } else {
    return <p>No Shruti data available</p>
  }

  const pctLabels = energies.map(e =>
    e > 0.03 ? `${Math.round(e * 100)}%` : ''
  )

  return (
    <div>
      <Plot
        data={[
          {
            x: SHRUTI_NAMES,
            y: energies,
            type: 'bar',
            marker: {
              color: energies.map(energyColour),
              line: {
                color: energies.map(energyBorderColour),
                width: 1.5,
              },
            },
            text: pctLabels,
            textposition: 'outside',
            textfont: { color: '#aaa', size: 9 },
            hovertemplate: '<b>%{x}</b><br>Energy: %{y:.3f}<extra></extra>',
          },
        ]}
        layout={{
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          margin: { t: 10, r: 10, b: 100, l: 55 },
          xaxis: {
            tickangle: -45,
            tickfont: { color: '#888', size: 8 },
          },
          yaxis: {
            title: { text: 'Relative PCP Energy', font: { color: '#888', size: 11 } },
            tickfont: { color: '#888' },
            gridcolor: '#2a2a3e',
            range: [0, 1.15],
          },
          height: 320,
          showlegend: false,
        }}
        onInitialized={() => onReady?.()}
        onUpdate={() => onReady?.()}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: '100%' }}
      />
      <p style={{
        fontSize: '0.8rem',
        color: 'var(--text-secondary)',
        textAlign: 'center',
        marginTop: '0.5rem',
      }}>
        Pitch-Class Profile energy across 22 Shruti microtonal bins
        (harmonic-weighted, octave-invariant)
      </p>
    </div>
  )
}
