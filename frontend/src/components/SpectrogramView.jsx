import Plot from 'react-plotly.js'

export default function SpectrogramView({ data, duration, onReady }) {
  if (!data || data.length === 0) return <p>No spectrogram data</p>

  const z = data
  const nFrames = z[0]?.length || 0
  const nBins = z.length

  const x = Array.from({ length: nFrames }, (_, i) => (i * (duration || 10)) / nFrames)
  const y = Array.from({ length: nBins }, (_, i) => i)

  return (
    <Plot
      data={[{
        z: z,
        x: x,
        y: y,
        type: 'heatmap',
        colorscale: [
          [0, '#0a0a0f'],
          [0.2, '#1a1a4e'],
          [0.4, '#4a1a6e'],
          [0.6, '#e94560'],
          [0.8, '#ff8a65'],
          [1, '#fff3e0'],
        ],
        colorbar: {
          title: { text: 'dB', font: { color: '#888' } },
          tickfont: { color: '#888' },
        },
      }]}
      layout={{
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        margin: { t: 10, r: 60, b: 40, l: 40 },
        xaxis: {
          title: { text: 'Time (s)', font: { color: '#888' } },
          tickfont: { color: '#888' },
          gridcolor: '#2a2a3e',
        },
        yaxis: {
          title: { text: 'Frequency Bin', font: { color: '#888' } },
          tickfont: { color: '#888' },
          gridcolor: '#2a2a3e',
        },
        height: 300,
      }}
      onInitialized={() => onReady?.()}
      onUpdate={() => onReady?.()}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: '100%' }}
    />
  )
}
