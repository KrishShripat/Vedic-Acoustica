import { useEffect, useRef, useState } from 'react'
import { authFetch } from '../utils/auth'

const STAGES = [
  { key: 'Feature Extraction', icon: '🔬', label: 'Feature Extraction' },
  { key: 'Shruti Clustering',  icon: '🎵', label: 'Shruti Clustering (K=22)' },
  { key: 'Ghana Patha Validation', icon: '🕉️', label: 'Ghana Patha Validation' },
  { key: 'Raga Detection',     icon: '🪔', label: 'Raga Detection' },
  { key: 'Complete',           icon: '✅', label: 'Complete' },
]

const STAGE_ORDER = STAGES.map(s => s.key)
const SSE_READ_TIMEOUT_MS = 5000
const POLL_INTERVAL_MS = 2500
const MAX_POLL_FAILURES = 5

function retryDelay(response, fallback = 15000) {
  const retryAfter = response.headers.get('Retry-After')
  if (!retryAfter) return fallback

  const seconds = Number(retryAfter)
  if (Number.isFinite(seconds)) return Math.max(1000, seconds * 1000)

  const retryAt = Date.parse(retryAfter)
  return Number.isNaN(retryAt) ? fallback : Math.max(1000, retryAt - Date.now())
}

function stageIndex(stageName) {
  const idx = STAGE_ORDER.findIndex(s =>
    stageName && stageName.toLowerCase().includes(s.toLowerCase())
  )
  return idx === -1 ? 0 : idx
}

/**
 * AnalysisProgress
 *
 * Uses the existing GET /status/ SSE stream first. If a proxy buffers the
 * stream or the connection stalls, it falls back to the JSON progress
 * snapshot endpoint, with one request at a time and Retry-After support.
 *
 * Props:
 *   recordingId  – int, the PK of the recording being analysed
 *   apiBase      – string, base URL e.g. '/api'
 *   onDone       – callback fired when status='done'
 *   onError      – callback(errorMsg) fired when status='error'
 */
export default function AnalysisProgress({ recordingId, apiBase, onDone, onError }) {
  const [progress, setProgress] = useState({ stage: 'Queued', percent: 0, status: 'running' })
  const timerRef = useRef(null)
  const doneRef  = useRef(false)

  useEffect(() => {
    if (!recordingId) return
    doneRef.current = false
    setProgress({ stage: 'Queued', percent: 0, status: 'running' })

    const statusUrl = `${apiBase}/analyze/${recordingId}/status/`
    const progressUrl = `${apiBase}/analyze/${recordingId}/progress/`
    let failedPolls = 0
    let cancelled = false
    let controller = null

    const finish = (data) => {
      if (cancelled || doneRef.current) return
      setProgress(data)
      if (data.status === 'done') {
        doneRef.current = true
        onDone?.()
      } else if (data.status === 'error') {
        doneRef.current = true
        onError?.(data.error || 'Analysis failed')
      }
    }

    const schedulePoll = (delay) => {
      if (cancelled || doneRef.current) return
      clearTimeout(timerRef.current)
      timerRef.current = setTimeout(poll, delay)
    }

    const poll = async () => {
      if (cancelled || doneRef.current) return
      try {
        const res = await authFetch(progressUrl)
        if (res.status === 429) {
          schedulePoll(retryDelay(res))
          return
        }
        if (!res.ok) {
          if (++failedPolls > MAX_POLL_FAILURES) {
            doneRef.current = true
            onError?.(`Progress endpoint failed (HTTP ${res.status}).`)
            return
          }
          schedulePoll(Math.min(POLL_INTERVAL_MS * (2 ** (failedPolls - 1)), 30000))
          return
        }
        failedPolls = 0
        const data = await res.json()
        finish(data)
        if (!doneRef.current) schedulePoll(POLL_INTERVAL_MS)
      } catch {
        if (cancelled) return
        if (++failedPolls > MAX_POLL_FAILURES) {
          doneRef.current = true
          onError?.('Connection to analysis progress was lost.')
          return
        }
        schedulePoll(Math.min(POLL_INTERVAL_MS * (2 ** (failedPolls - 1)), 30000))
      }
    }

    const consumeSse = async () => {
      controller = new AbortController()
      try {
        const res = await authFetch(statusUrl, {
          headers: { Accept: 'text/event-stream' },
          signal: controller.signal,
        })

        if (res.status === 429) {
          schedulePoll(retryDelay(res))
          return
        }
        if (!res.ok || !res.body) {
          schedulePoll(POLL_INTERVAL_MS)
          return
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        const handleEvent = (eventText) => {
          const data = eventText
            .split('\n')
            .filter(line => line.startsWith('data:'))
            .map(line => line.slice(5).trim())
            .join('\n')
          if (!data) return

          try {
            const snapshot = JSON.parse(data)
            if (
              typeof snapshot.error === 'string' &&
              snapshot.error.toLowerCase().includes('too many status requests')
            ) {
              schedulePoll(retryDelay(res))
              controller.abort()
              return
            }
            finish(snapshot)
            if (doneRef.current) controller.abort()
          } catch (err) {
            if (err instanceof SyntaxError) {
              console.error('Invalid analysis progress event:', err)
              schedulePoll(POLL_INTERVAL_MS)
              controller.abort()
              return
            }
            throw err
          }
        }

        while (!cancelled && !doneRef.current) {
          let timeoutId
          const timeout = new Promise((_, reject) => {
            timeoutId = setTimeout(() => reject(new Error('SSE progress stream stalled')), SSE_READ_TIMEOUT_MS)
          })
          let result
          try {
            result = await Promise.race([reader.read(), timeout])
          } finally {
            clearTimeout(timeoutId)
          }
          if (result.done) break

          buffer += decoder.decode(result.value, { stream: true }).replace(/\r\n/g, '\n')
          let boundary = buffer.indexOf('\n\n')
          while (boundary !== -1) {
            const eventText = buffer.slice(0, boundary)
            buffer = buffer.slice(boundary + 2)
            handleEvent(eventText)
            boundary = buffer.indexOf('\n\n')
          }
        }

        if (!cancelled && !doneRef.current) schedulePoll(POLL_INTERVAL_MS)
      } catch (err) {
        if (cancelled || doneRef.current) return
        if (err.name !== 'AbortError') {
          controller?.abort()
          schedulePoll(POLL_INTERVAL_MS)
        }
      }
    }

    consumeSse()

    return () => {
      cancelled = true
      clearTimeout(timerRef.current)
      controller?.abort()
      doneRef.current = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recordingId, apiBase])

  const currentStageIdx = stageIndex(progress.stage)
  const pct = Math.min(Math.max(progress.percent ?? 0, 0), 100)
  const isDone = progress.status === 'done'
  const isError = progress.status === 'error'

  return (
    <div className="analysis-progress-wrap">
      <div className="ap-header">
        {isError ? (
          <span className="ap-status-icon ap-error">⚠️</span>
        ) : isDone ? (
          <span className="ap-status-icon ap-done">✅</span>
        ) : (
          <span className="loading-spinner ap-spinner" />
        )}
        <span className="ap-title">
          {isError ? 'Analysis Failed' : isDone ? 'Analysis Complete' : 'Analysing…'}
          {!isDone && !isError && progress.detail && (
            <span className="ap-detail"> — {progress.detail}</span>
          )}
        </span>
        <span className="ap-pct">{pct}%</span>
      </div>

      <div className="ap-bar-track">
        <div
          className={`ap-bar-fill ${isDone ? 'ap-bar-done' : isError ? 'ap-bar-error' : ''}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="ap-stages">
        {STAGES.map((s, i) => {
          const isPast    = i < currentStageIdx
          const isCurrent = i === currentStageIdx && !isDone && !isError
          const isFuture  = i > currentStageIdx && !isDone

          return (
            <div
              key={s.key}
              className={[
                'ap-stage',
                isPast || isDone  ? 'ap-stage-done' : '',
                isCurrent         ? 'ap-stage-active' : '',
                isFuture          ? 'ap-stage-future' : '',
                isError && isCurrent ? 'ap-stage-error' : '',
              ].join(' ')}
            >
              <span className="ap-stage-icon">{s.icon}</span>
              <span className="ap-stage-label">{s.label}</span>
              {(isPast || isDone) && <span className="ap-check">✓</span>}
              {isCurrent && !isError && <span className="ap-pulse" />}
            </div>
          )
        })}
      </div>

      {isError && progress.error && (
        <p className="ap-error-msg">{progress.error}</p>
      )}
    </div>
  )
}