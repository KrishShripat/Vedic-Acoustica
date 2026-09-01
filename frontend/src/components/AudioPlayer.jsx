import { useEffect, useRef, useState, useCallback } from 'react'
import WaveSurfer from 'wavesurfer.js'

export default function AudioPlayer({ audioUrl, title }) {
  const containerRef = useRef(null)
  const wsRef = useRef(null)
  const [playing, setPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)

  useEffect(() => {
    if (!containerRef.current || !audioUrl) return

    const ws = WaveSurfer.create({
      container: containerRef.current,
      waveColor: '#444',
      progressColor: '#e94560',
      cursorColor: '#ff6b6b',
      barWidth: 2,
      barRadius: 3,
      barGap: 1,
      height: 80,
      responsive: true,
      url: audioUrl,
    })

    ws.on('ready', () => {
      setDuration(ws.getDuration())
    })

    ws.on('audioprocess', () => {
      setCurrentTime(ws.getCurrentTime())
    })

    ws.on('play', () => setPlaying(true))
    ws.on('pause', () => setPlaying(false))
    ws.on('finish', () => setPlaying(false))

    wsRef.current = ws

    return () => {
      ws.destroy()
      wsRef.current = null
    }
  }, [audioUrl])

  const togglePlay = useCallback(() => {
    wsRef.current?.playPause()
  }, [])

  const formatTime = (s) => {
    if (!s || !isFinite(s)) return '0:00'
    const m = Math.floor(s / 60)
    const sec = Math.floor(s % 60)
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  return (
    <div className="card audio-player">
      <div className="audio-player-header">
        <h2>Now Playing</h2>
        <span className="audio-player-title">{title}</span>
      </div>
      <div className="audio-player-controls">
        <button className="btn audio-play-btn" onClick={togglePlay}>
          {playing ? '⏸' : '▶'}
        </button>
        <span className="audio-time">{formatTime(currentTime)}</span>
        <div className="audio-waveform" ref={containerRef}></div>
        <span className="audio-time">{formatTime(duration)}</span>
      </div>
    </div>
  )
}
