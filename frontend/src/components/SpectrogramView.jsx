import { useEffect, useRef, useCallback } from 'react'
import { Plotly } from './Plot'

/**
 * SpectrogramView
 *
 * Props:
 *   data         – 2D array (frequency bins × time frames), dB values
 *   duration     – total duration in seconds (used to label the x-axis)
 *   onReady      – called once after the plot is first rendered
 *   playbackTime – current audio playback position in seconds; when non-null
 *                  a glowing red cursor line is drawn/moved on the spectrogram
 *   f0Track      – optional array of per-frame F0 (Hz, null/NaN for unvoiced).
 *                  When supplied, a pitch trace is overlaid on a right-hand Hz
 *                  axis so the observer can read the melodic contour directly.
 *   onSeek       – optional callback(seconds) fired when the plot is clicked;
 *                  lets the spectrogram act as a scrubbable timeline.
 */
export default function SpectrogramView({ data, duration, onReady, playbackTime, f0Track, onSeek }) {
  const divRef         = useRef(null)
  const plotInitedRef  = useRef(false)  // true after Plotly.newPlot has run
  const onReadyRef     = useRef(onReady)
  const onSeekRef      = useRef(onSeek)
  const durationRef    = useRef(duration)
  useEffect(() => { onReadyRef.current = onReady }, [onReady])
  useEffect(() => { onSeekRef.current = onSeek }, [onSeek])
  useEffect(() => { durationRef.current = duration }, [duration])

  // ── Build static traces + layout once ──────────────────────────────────────
  const buildLayout = useCallback((cursorX) => {
    const xMax    = duration || 10

    const cursorShape = cursorX != null
      ? [{
          type:  'line',
          xref:  'x',
          yref:  'paper',
          x0:    cursorX,
          x1:    cursorX,
          y0:    0,
          y1:    1,
          line:  {
            color: 'rgba(255, 107, 107, 0.92)',
            width: 2,
            dash:  'solid',
          },
        }]
      : []

    return {
      paper_bgcolor: 'transparent',
      plot_bgcolor:  'transparent',
      margin:        { t: 10, r: 60, b: 40, l: 45 },
      xaxis: {
        title:      { text: 'Time (s)', font: { color: '#888' } },
        tickfont:   { color: '#888' },
        gridcolor:  '#2a2a3e',
        range:      [0, xMax],
      },
      yaxis: {
        title:      { text: 'Freq Bin', font: { color: '#888' } },
        tickfont:   { color: '#888' },
        gridcolor:  '#2a2a3e',
      },
      height:     300,
      shapes:     cursorShape,
      // Attach a cursor-time annotation that sits at the top of the line
      annotations: cursorX != null ? [{
        xref:      'x',
        yref:      'paper',
        x:         cursorX,
        y:         1.02,
        text:      `${cursorX.toFixed(2)}s`,
        showarrow: false,
        font:      { color: 'rgba(255,107,107,0.9)', size: 9 },
        bgcolor:   'rgba(10,10,20,0.7)',
        borderpad: 2,
      }] : [],
    }
  }, [duration])

  // ── Initial plot (only when data changes) ──────────────────────────────────
  useEffect(() => {
    const div = divRef.current
    if (!div || !data || data.length === 0) return

    const nFrames = data[0]?.length || 0
    const nBins   = data.length
    const xMax    = duration || 10

    const x = Array.from({ length: nFrames }, (_, i) => (i * xMax) / nFrames)
    const y = Array.from({ length: nBins },   (_, i) => i)

    const traces = [{
      z:          data,
      x,
      y,
      type:       'heatmap',
      colorscale: [
        [0,   '#0a0a0f'],
        [0.2, '#1a1a4e'],
        [0.4, '#4a1a6e'],
        [0.6, '#e94560'],
        [0.8, '#ff8a65'],
        [1,   '#fff3e0'],
      ],
      colorbar: {
        title:    { text: 'dB', font: { color: '#888' } },
        tickfont: { color: '#888' },
        thickness: 12,
      },
      hovertemplate: 't = %{x:.2f}s<br>bin %{y}<br>%{z:.1f} dB<extra></extra>',
    }]

    const hasF0 = Array.isArray(f0Track) && f0Track.length > 0

    if (hasF0) {
      // Downsample very long pitch tracks — a line trace only needs enough
      // points to read the melodic contour, not one per analysis frame.
      const step = Math.max(1, Math.ceil(f0Track.length / 2000))
      const fx = []
      const fy = []
      for (let i = 0; i < f0Track.length; i += step) {
        const v = f0Track[i]
        const t = f0Track.length > 1 ? (i / (f0Track.length - 1)) * xMax : 0
        fx.push(t)
        fy.push(v == null || !isFinite(v) ? null : v)
      }
      traces.push({
        x: fx,
        y: fy,
        type: 'scatter',
        mode: 'lines',
        name: 'F0 pitch',
        yaxis: 'y2',
        line: { color: '#ff7a59', width: 1.5 },
        connectgaps: false,
        hovertemplate: 't = %{x:.2f}s<br>F0 = %{y:.1f} Hz<extra></extra>',
      })
    }

    const layout = buildLayout(null)
    if (hasF0) {
      layout.yaxis2 = {
        title:     { text: 'F0 (Hz)', font: { color: '#ff7a59', size: 10 } },
        tickfont:  { color: '#ff7a59', size: 9 },
        overlaying: 'y',
        side:      'right',
        showgrid:  false,
        rangemode: 'normal',
      }
      layout.margin = { ...layout.margin, r: 78 }
    }

    const handleClick = (ev) => {
      if (!onSeekRef.current) return
      const px = ev?.points?.[0]?.x
      if (typeof px === 'number' && isFinite(px)) {
        const max = durationRef.current || xMax
        onSeekRef.current(Math.min(Math.max(px, 0), max))
      }
    }

    Plotly.newPlot(div, traces, layout, {
      displayModeBar: false,
      responsive:     true,
    }).then(() => {
      plotInitedRef.current = true
      if (onSeekRef.current) {
        div.on('plotly_click', handleClick)
      }
      onReadyRef.current?.()
    })

    return () => {
      if (div) {
        Plotly.purge(div)
        plotInitedRef.current = false
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, duration, f0Track])

  // ── Cursor update — bypass React, call Plotly.relayout directly ────────────
  // This runs on every animation frame (~50 ms) without triggering a re-render.
  useEffect(() => {
    if (!plotInitedRef.current || !divRef.current) return

    const cursorX = (playbackTime != null && isFinite(playbackTime))
      ? playbackTime
      : null

    const cursorShape = cursorX != null
      ? [{
          type: 'line', xref: 'x', yref: 'paper',
          x0: cursorX, x1: cursorX, y0: 0, y1: 1,
          line: { color: 'rgba(255,107,107,0.92)', width: 2 },
        }]
      : []

    const annotations = cursorX != null
      ? [{
          xref: 'x', yref: 'paper',
          x: cursorX, y: 1.02,
          text: `${cursorX.toFixed(2)}s`,
          showarrow: false,
          font:    { color: 'rgba(255,107,107,0.9)', size: 9 },
          bgcolor: 'rgba(10,10,20,0.7)',
          borderpad: 2,
        }]
      : []

    // relayout is the lightest Plotly update — only touches shapes + annotations
    Plotly.relayout(divRef.current, { shapes: cursorShape, annotations })
  }, [playbackTime])

  return <div ref={divRef} style={{ width: '100%' }} />
}
