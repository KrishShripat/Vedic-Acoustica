import { useState, useMemo } from 'react'
import Plot from 'react-plotly.js'

const SHRUTI_NAMES = [
  'Sa', 'Re¹', 'Re²', 'Ga¹', 'Ga²', 'Ga³',
  'Ma¹', 'Ma²', 'Ma³', 'Tivra Ma', 'Pa', 'Dha¹',
  'Dha²', 'Ni¹', 'Ni²', 'Ni³', 'Ni⁴', 'Ni⁵',
  'Ni⁶', 'Ga-Komal', 'Ma-Komal', 'Tivra Ma²',
  'Sa’',
]

/**
 * Custom "Vedic Thermal" colorscale:
 * transparent/deep-navy (silence) → indigo → crimson → amber (peak energy)
 */
const VEDIC_COLORSCALE = [
  [0.00, 'rgba(10,10,20,0)'],
  [0.05, 'rgba(20,20,50,0.6)'],
  [0.20, 'rgba(60,20,100,0.85)'],
  [0.45, 'rgba(150,20,80,0.92)'],
  [0.70, 'rgba(220,60,50,0.97)'],
  [0.88, 'rgba(240,130,30,1)'],
  [1.00, 'rgba(255,220,80,1)'],
]

// Mean-PCP bar fallback colour ramp
function energyColour(e) {
  const r = Math.round(42  + (233 - 42)  * e)
  const g = Math.round(180 + (69  - 180) * e)
  const b = Math.round(140 + (96  - 140) * e)
  return `rgba(${r},${g},${b},${0.4 + 0.6 * e})`
}

// ── Shruti category legend pills ─────────────────────────────────────────────
const CATEGORY_LEGEND = [
  { label: 'Sa / Sa\'', color: '#e94560' },
  { label: 'Re',        color: '#ff8c42' },
  { label: 'Ga',        color: '#ffd166' },
  { label: 'Ma',        color: '#06d6a0' },
  { label: 'Pa',        color: '#118ab2' },
  { label: 'Dha',       color: '#8338ec' },
  { label: 'Ni',        color: '#ff006e' },
]

export default function ShrutiMap({ data, onReady }) {
  const [view, setView] = useState('heatmap') // 'heatmap' | 'bar'

  // ── Derive heatmap matrix ─────────────────────────────────────────────────
  const heatmapTrace = useMemo(() => {
    const pcpMatrix = data?.pcp_data       // (23, n_cols)
    const timeAxis  = data?.pcp_time_axis  // [seconds …]

    if (!Array.isArray(pcpMatrix) || pcpMatrix.length !== 23) return null

    const nCols = pcpMatrix[0]?.length ?? 0
    if (nCols === 0) return null

    // Plotly heatmap expects z[row][col] = value
    // Our pcp_data is already (23, n_cols) — rows = Shrutis, cols = time
    // We flip row order so Sa is at the bottom of the chart (low → high)
    const zFlipped = [...pcpMatrix].reverse()
    const yLabels  = [...SHRUTI_NAMES].reverse()

    const xLabels = Array.isArray(timeAxis)
      ? timeAxis
      : Array.from({ length: nCols }, (_, i) => i)

    return { z: zFlipped, x: xLabels, y: yLabels }
  }, [data])

  // ── Derive mean-PCP bar data ──────────────────────────────────────────────
  const barTrace = useMemo(() => {
    if (!Array.isArray(data?.mean_pcp) || data.mean_pcp.length !== 23) return null
    const rawMax = Math.max(...data.mean_pcp, 1e-9)
    const energies = data.mean_pcp.map(v => v / rawMax)
    return energies
  }, [data])

  if (!heatmapTrace && !barTrace) {
    return <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>No Shruti data available.</p>
  }

  const canShowHeatmap = heatmapTrace !== null
  const activeView = canShowHeatmap ? view : 'bar'

  return (
    <div>
      {/* ── View toggle ── */}
      {canShowHeatmap && (
        <div className="shruti-toggle">
          <button
            className={`shruti-toggle-btn ${activeView === 'heatmap' ? 'active' : ''}`}
            onClick={() => setView('heatmap')}
          >
            🌡 Heatmap
          </button>
          <button
            className={`shruti-toggle-btn ${activeView === 'bar' ? 'active' : ''}`}
            onClick={() => setView('bar')}
          >
            📊 Bar
          </button>
        </div>
      )}

      {/* ── Heatmap view ── */}
      {activeView === 'heatmap' && canShowHeatmap && (
        <>
          {/* Category legend */}
          <div className="shruti-legend">
            {CATEGORY_LEGEND.map(c => (
              <span key={c.label} className="shruti-legend-pill" style={{ '--pill-color': c.color }}>
                {c.label}
              </span>
            ))}
          </div>

          <Plot
            data={[
              {
                type: 'heatmap',
                z: heatmapTrace.z,
                x: heatmapTrace.x,
                y: heatmapTrace.y,
                colorscale: VEDIC_COLORSCALE,
                zmin: 0,
                zmax: 1,
                showscale: true,
                colorbar: {
                  title: { text: 'PCP Energy', font: { color: '#888', size: 10 }, side: 'right' },
                  tickfont: { color: '#888', size: 9 },
                  thickness: 12,
                  len: 0.9,
                  bgcolor: 'transparent',
                  bordercolor: '#2a2a3e',
                },
                hoverongaps: false,
                hovertemplate:
                  '<b>%{y}</b><br>t = %{x:.2f}s<br>Energy: %{z:.3f}<extra></extra>',
                xgap: 0,
                ygap: 0.5,
              },
            ]}
            layout={{
              paper_bgcolor: 'transparent',
              plot_bgcolor: '#0d0d18',
              margin: { t: 8, r: 72, b: 48, l: 52 },
              xaxis: {
                title: { text: 'Time (s)', font: { color: '#888', size: 11 } },
                tickfont: { color: '#888', size: 9 },
                gridcolor: 'rgba(42,42,62,0.5)',
                zeroline: false,
              },
              yaxis: {
                tickfont: { color: '#aaa', size: 9 },
                gridcolor: 'rgba(42,42,62,0.4)',
                zeroline: false,
                tickmode: 'array',
                tickvals: [...SHRUTI_NAMES].reverse(),
                ticktext: [...SHRUTI_NAMES].reverse(),
              },
              height: 420,
              showlegend: false,
              shapes: [
                // Highlight Sa (index 0, bottom) and Pa (index 9) rows with subtle lines
                {
                  type: 'line', xref: 'paper', yref: 'y',
                  x0: 0, x1: 1, y0: 'Sa', y1: 'Sa',
                  line: { color: 'rgba(233,69,96,0.25)', width: 1, dash: 'dot' },
                },
                {
                  type: 'line', xref: 'paper', yref: 'y',
                  x0: 0, x1: 1, y0: 'Pa', y1: 'Pa',
                  line: { color: 'rgba(17,138,178,0.25)', width: 1, dash: 'dot' },
                },
              ],
            }}
            onInitialized={() => onReady?.()}

            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%' }}
          />

          <p className="shruti-caption">
            Time × Shruti heatmap — colour encodes per-frame PCP energy (pYIN F0 fusion).
            Bright bands reveal when each microtone was active during recitation.
          </p>
        </>
      )}

      {/* ── Bar view (mean PCP) ── */}
      {activeView === 'bar' && barTrace && (
        <>
          <Plot
            data={[
              {
                x: SHRUTI_NAMES,
                y: barTrace,
                type: 'bar',
                marker: {
                  color: barTrace.map(energyColour),
                  line: { color: barTrace.map(e => energyColour(Math.min(e + 0.2, 1))), width: 1.2 },
                },
                text: barTrace.map(e => e > 0.03 ? `${Math.round(e * 100)}%` : ''),
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

            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%' }}
          />
          <p className="shruti-caption">
            Mean Pitch-Class Profile energy across 23 Shruti bins (harmonic-weighted, octave-invariant)
          </p>
        </>
      )}
    </div>
  )
}
