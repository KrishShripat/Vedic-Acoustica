/**
 * AnalyzedRecordingChips
 *
 * A compact selector limited to recordings that have already been analysed —
 * lets the observer switch the "voice under study" from inside the Explorer
 * without returning to the listening chamber.
 */
export default function AnalyzedRecordingChips({ recordings = [], selectedId, onSelect }) {
  const analyzed = recordings.filter(r => r.is_analyzed)
  if (analyzed.length === 0) return null

  return (
    <div className="explorer-voice-bar">
      <span className="explorer-voice-label">Voice under study</span>
      <div className="explorer-voice-chips">
        {analyzed.map(recording => {
          const isActive = recording.id === selectedId
          const when = recording.uploaded_at ? new Date(recording.uploaded_at) : null
          return (
            <button
              key={recording.id}
              type="button"
              className={`explorer-voice-chip ${isActive ? 'active' : ''}`}
              onClick={() => onSelect(recording)}
              aria-pressed={isActive}
            >
              <span className="evc-title">{recording.title}</span>
              {when && <span className="evc-when">{when.toLocaleDateString()}</span>}
            </button>
          )
        })}
      </div>
    </div>
  )
}
