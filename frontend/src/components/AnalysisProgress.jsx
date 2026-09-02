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
 * Props:
 *   recordingId  – int, the PK of the recording being analysed
 *   apiBase      – string, base URL e.g. '/api'
 *   onDone       – callback fired when SSE reports status='done'
 *   onError      – callback(errorMsg) fired when SSE reports status='error'
 */
export default function AnalysisProgress({ recordingId, apiBase, onDone, onError }) {
  const [progress, setProgress] = useState({ stage: 'Queued', percent: 0, status: 'running' })
  const esRef = useRef(null)

  useEffect(() => {
    if (!recordingId) return

    const url = `${apiBase}/analyze/${recordingId}/status/`
    const es = new EventSource(url)
    esRef.current = es

    es.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data)
        setProgress(data)
        if (data.status === 'done') {
          es.close()
          onDone?.()
        } else if (data.status === 'error') {
          es.close()
          onError?.(data.error || 'Analysis failed')
        }
      } catch { /* ignore parse errors */ }
    }

    es.onerror = () => {
      // EventSource auto-reconnects on network errors; only close on terminal state
      if (progress.status === 'done' || progress.status === 'error') {
        es.close()
      }
    }

    return () => {
      es.close()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recordingId, apiBase])

  const currentStageIdx = stageIndex(progress.stage)
  const pct = Math.min(Math.max(progress.percent ?? 0, 0), 100)
  const isDone = progress.status === 'done'
  const isError = progress.status === 'error'

  return (
    <div className="analysis-progress-wrap">
      {/* ── Header ── */}
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
        </span>
        <span className="ap-pct">{pct}%</span>
      </div>

      {/* ── Master progress bar ── */}
      <div className="ap-bar-track">
        <div
          className={`ap-bar-fill ${isDone ? 'ap-bar-done' : isError ? 'ap-bar-error' : ''}`}
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* ── Stage pills ── */}
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
