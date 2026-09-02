import { useEffect, useRef, useState, useCallback, useImperativeHandle, forwardRef } from 'react'
import WaveSurfer from 'wavesurfer.js'

/**
 * AudioPlayer
 *
 * Props:
 *   audioUrl      – URL of the audio file to load
 *   title         – display name
 *   onTimeUpdate  – optional callback(currentTime, duration) fired every
 *                   audioprocess tick (~every 50 ms while playing) and on
 *                   seek. Used by the parent to sync the spectrogram cursor.
 *
 * Ref handle (use with forwardRef / useRef):
 *   seekTo(seconds)  – jump playback to the given time and start playing
 */
const AudioPlayer = forwardRef(function AudioPlayer({ audioUrl, title, onTimeUpdate }, ref) {
  const containerRef = useRef(null)
  const wsRef        = useRef(null)
  const [playing,     setPlaying]     = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration,    setDuration]    = useState(0)
  const [loadError,   setLoadError]   = useState(null)

  // Stable ref so the WaveSurfer closure always calls the latest callback
  const onTimeUpdateRef = useRef(onTimeUpdate)
  useEffect(() => { onTimeUpdateRef.current = onTimeUpdate }, [onTimeUpdate])

  useEffect(() => {
    if (!containerRef.current || !audioUrl) return
    setLoadError(null)

    const ws = WaveSurfer.create({
      container:     containerRef.current,
      waveColor:     '#3a3a5c',
      progressColor: '#e94560',
      cursorColor:   '#ff6b6b',
      barWidth:      2,
      barRadius:     3,
      barGap:        1,
      height:        80,
      url:           audioUrl,
    })

    const _notify = (ws) => {
      const ct  = ws.getCurrentTime()
      const dur = ws.getDuration()
      setCurrentTime(ct)
      onTimeUpdateRef.current?.(ct, dur)
    }

    ws.on('ready', () => {
      const dur = ws.getDuration()
      setDuration(dur)
      // Emit once so parent knows total duration before play starts
      onTimeUpdateRef.current?.(0, dur)
    })

    ws.on('error', (err) => {
      console.error('WaveSurfer error:', err)
      setLoadError(err?.message || 'Failed to load audio')
    })

    ws.on('audioprocess', () => _notify(ws))
    ws.on('seek',         () => _notify(ws))   // scrub-click sync

    ws.on('play',   () => setPlaying(true))
    ws.on('pause',  () => setPlaying(false))
    ws.on('finish', () => {
      setPlaying(false)
      // Reset cursor on finish
      onTimeUpdateRef.current?.(0, ws.getDuration())
    })

    wsRef.current = ws

    return () => {
      ws.destroy()
      wsRef.current = null
    }
  }, [audioUrl])

  // ── Imperative handle: seekTo(seconds) ─────────────────────────────────
  useImperativeHandle(ref, () => ({
    seekTo(seconds) {
      const ws = wsRef.current
      if (!ws) return
      const dur = ws.getDuration()
      if (!dur || dur === 0) return
      const progress = Math.min(Math.max(seconds / dur, 0), 1)
      ws.seekTo(progress)   // WaveSurfer seekTo expects [0, 1]
      if (!ws.isPlaying()) ws.play()
    },
  }), [])

  const togglePlay = useCallback(() => wsRef.current?.playPause(), [])

  const formatTime = (s) => {
    if (!s || !isFinite(s)) return '0:00'
    const m   = Math.floor(s / 60)
    const sec = Math.floor(s % 60)
    return `${m}:${sec.toString().padStart(2, '0')}`
  }

  return (
    <div className="card audio-player">
      <div className="audio-player-header">
        <h2>Now Playing</h2>
        <span className="audio-player-title">{title}</span>
      </div>

      {loadError ? (
        <p style={{ color: '#e94560', fontSize: '0.85rem', margin: '0.5rem 0' }}>
          {loadError}
        </p>
      ) : (
        <div className="audio-player-controls">
          <button className="btn audio-play-btn" onClick={togglePlay}>
            {playing ? '⏸' : '▶'}
          </button>
          <span className="audio-time">{formatTime(currentTime)}</span>
          <div className="audio-waveform" ref={containerRef} />
          <span className="audio-time">{formatTime(duration)}</span>
        </div>
      )}
    </div>
  )
})

export default AudioPlayer
