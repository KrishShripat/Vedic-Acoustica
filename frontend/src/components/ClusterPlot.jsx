import Plot from 'react-plotly.js'

export default function ClusterPlot({ data }) {
  if (!data?.shruti_clusters) return <p>No cluster data</p>

  const clusterNames = Object.keys(data.shruti_clusters)
  const frameCounts = clusterNames.map(k => data.shruti_clusters[k].frame_count)

  const dominantFreqs = data.dominant_frequencies || []
  const freqBuckets = new Array(22).fill(0)
  dominantFreqs.forEach(f => {
    const idx = Math.min(Math.floor((f / 1000) * 22), 21)
    if (idx >= 0) freqBuckets[idx]++
  })

  return (
    <div>
      <Plot
        data={[
          {
            x: clusterNames,
            y: frameCounts,
            type: 'bar',
            marker: {
              color: clusterNames.map((_, i) => {
                const hue = (i / 22) * 360
                return `hsl(${hue}, 70%, 55%)`
              }),
            },
          },
        ]}
        layout={{
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          margin: { t: 10, r: 10, b: 80, l: 50 },
          xaxis: {
            tickangle: -45,
            tickfont: { color: '#888', size: 8 },
            gridcolor: '#2a2a3e',
          },
          yaxis: {
            title: { text: 'Frames', font: { color: '#888' } },
            tickfont: { color: '#888' },
            gridcolor: '#2a2a3e',
          },
          height: 280,
        }}
        config={{ displayModeBar: false, responsive: true }}
        style={{ width: '100%' }}
      />
      <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textAlign: 'center', marginTop: '0.5rem' }}>
        {dominantFreqs.length} dominant frequency samples mapped to 22 Shruti bins
      </p>
    </div>
  )
}
