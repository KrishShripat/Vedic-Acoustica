import { useEffect, useRef, useCallback } from 'react'
import Plotly from 'plotly.js-dist'

/**
 * SpectrogramView
 *
 * Props:
 *   data         – 2D array (frequency bins × time frames), dB values
 *   duration     – total duration in seconds (used to label the x-axis)
 *   onReady      – called once after the plot is first rendered
 *   playbackTime – current audio playback position in seconds; when non-null
 *                  a glowing red cursor line is drawn/moved on the spectrogram
 */
export default function SpectrogramView({ data, duration, onReady, playbackTime }) {
  const divRef         = useRef(null)
  const plotInitedRef  = useRef(false)  // true after Plotly.newPlot has run
  const onReadyRef     = useRef(onReady)
  useEffect(() => { onReadyRef.current = onReady }, [onReady])

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

    Plotly.newPlot(div, traces, buildLayout(null), {
      displayModeBar: false,
      responsive:     true,
    }).then(() => {
      plotInitedRef.current = true
      onReadyRef.current?.()
    })

    return () => {
      if (div) {
        Plotly.purge(div)
        plotInitedRef.current = false
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, duration])

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
