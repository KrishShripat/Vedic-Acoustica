import { useEffect, useRef, useState } from 'react'

const STAGES = [
  { key: 'Feature Extraction', icon: '🔬', label: 'Feature Extraction' },
  { key: 'Shruti Clustering',  icon: '🎵', label: 'Shruti Clustering (K=22)' },
  { key: 'Ghana Patha Validation', icon: '🕉️', label: 'Ghana Patha Validation' },
  { key: 'Raga Detection',     icon: '🪔', label: 'Raga Detection' },
  { key: 'Complete',           icon: '✅', label: 'Complete' },
]

const STAGE_ORDER = STAGES.map(s => s.key)

function stageIndex(stageName) {
  const idx = STAGE_ORDER.findIndex(s =>
    stageName && stageName.toLowerCase().includes(s.toLowerCase())
  )
  return idx === -1 ? 0 : idx
}

/**
 * AnalysisProgress
 *
 * Polls GET /api/analyze/<id>/progress/ (a small JSON snapshot) instead of
 * holding an SSE stream — streaming EventSource through the Vercel proxy gets
 * buffered, which made the progress bar freeze mid-analysis.  JSON polling is
 * robust behind any buffering proxy.
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

    const url = `${apiBase}/analyze/${recordingId}/progress/`
    let failedPolls = 0

    const poll = async () => {
      if (doneRef.current) return
      try {
        const res = await fetch(url)
        if (!res.ok) {
          if (++failedPolls > 5) {
            clearInterval(timerRef.current)
            onError?.(`Progress endpoint failed (HTTP ${res.status}).`)
          }
          return
        }
        failedPolls = 0
        const data = await res.json()
        setProgress(data)
        if (data.status === 'done') {
          doneRef.current = true
          clearInterval(timerRef.current)
          onDone?.()
        } else if (data.status === 'error') {
          doneRef.current = true
          clearInterval(timerRef.current)
          onError?.(data.error || 'Analysis failed')
        }
      } catch {
        if (++failedPolls > 5) {
          clearInterval(timerRef.current)
          onError?.('Connection to analysis progress was lost.')
        }
      }
    }

    poll()
    timerRef.current = setInterval(poll, 1000)

    return () => {
      clearInterval(timerRef.current)
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