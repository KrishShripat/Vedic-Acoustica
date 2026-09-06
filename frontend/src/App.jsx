import { useState, useCallback, useEffect, useRef } from 'react'
import AudioUploader from './components/AudioUploader'
import SpectrogramView from './components/SpectrogramView'
import ClusterPlot from './components/ClusterPlot'
import ShrutiMap from './components/ShrutiMap'
import GhanaPathaViz from './components/GhanaPathaViz'
import RagaViz from './components/RagaViz'
import AudioPlayer from './components/AudioPlayer'
import AnalysisProgress from './components/AnalysisProgress'
import AuthScreen from './components/AuthScreen'
import AdminOverview from './components/AdminOverview'
import exportReport from './utils/exportReport'
import { getUser, clearAuth, authFetch } from './utils/auth'
import './App.css'

const API_BASE = '/api'
const NUM_CHARTS = 5

// /media/... is relative on purpose: the Vite dev proxy (localhost:8000)
// and the Vercel rewrite (HF Space) both resolve it for their environment.
const resolveMediaUrl = (url) => url

function App() {
  const [recordings, setRecordings] = useState([])
  const [selectedRecording, setSelectedRecording] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzeError, setAnalyzeError] = useState(null)
  const [downloading, setDownloading] = useState(false)
  const [chartsReady, setChartsReady] = useState(0)
  const [fetchError, setFetchError] = useState(null)
  // Playback cursor shared between AudioPlayer → SpectrogramView
  const [playbackTime, setPlaybackTime] = useState(null)
  // Imperative ref to AudioPlayer — lets GhanaPathaViz call seekTo(seconds)
  const playerRef = useRef(null)

  // ── Auth: user identity + token gate (backend /api/auth/*) ────────────────
  const [user, setUser] = useState(() => getUser())
  const [authLoading, setAuthLoading] = useState(true)
  const [showAdmin, setShowAdmin] = useState(false)

  // Validate a stored token on load; clear it if the backend rejects it.
  useEffect(() => {
    let cancelled = false
    const verify = async () => {
      if (!getUser()) {
        setAuthLoading(false)
        return
      }
      try {
        const res = await authFetch(`${API_BASE}/auth/me/`)
        if (!res.ok) {
          clearAuth()
          if (!cancelled) setUser(null)
        } else {
          const data = await res.json()
          if (!cancelled) setUser(data.user)
        }
      } catch {
        clearAuth()
        if (!cancelled) setUser(null)
      } finally {
        if (!cancelled) setAuthLoading(false)
      }
    }
    verify()
    return () => { cancelled = true }
  }, [])

  // AdminOverview signals an expired token → bounce to the login screen.
  useEffect(() => {
    const onExpired = () => { clearAuth(); setUser(null) }
    window.addEventListener('auth-expired', onExpired)
    return () => window.removeEventListener('auth-expired', onExpired)
  }, [])

  const handleGuest = useCallback(() => {
    clearAuth()
    setUser({ username: 'Guest', email: '', is_staff: false, is_superuser: false, is_guest: true })
  }, [])

  const handleLogout = useCallback(async () => {
    const tokenExists = !!localStorage.getItem('va_token')
    if (tokenExists) {
      try {
        await authFetch(`${API_BASE}/auth/logout/`, { method: 'POST' })
      } catch { /* token is cleared client-side regardless */}
    }
    clearAuth()
    setUser(null)
    setAnalysis(null)
    setSelectedRecording(null)
  }, [])

  const markChartReady = useCallback(() => {
    setChartsReady(prev => (prev >= NUM_CHARTS ? prev : prev + 1))
  }, [])

  const fetchRecordings = useCallback(async () => {
    try {
      const res = await authFetch(`${API_BASE}/recordings/`)
      if (!res.ok) throw new Error(`Backend returned ${res.status}`)
      const data = await res.json()
      setRecordings(data.results ?? data)
      setFetchError(null)
    } catch (err) {
      console.error('Failed to fetch recordings:', err)
      setFetchError(err.message)
    }
  }, [])

  useEffect(() => {
    fetchRecordings()
  }, [fetchRecordings])

  useEffect(() => {
    setChartsReady(0)
  }, [analysis])

  const handleUpload = useCallback(async (file) => {
    const formData = new FormData()
    formData.append('audio_file', file)
    formData.append('title', file.name)

    try {
      const res = await authFetch(`${API_BASE}/upload/`, {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        // DRF field errors arrive as { audio_file: ['msg'], title: ['msg'] }
        const msg =
          err.audio_file?.[0] ||
          err.title?.[0] ||
          err.detail ||
          err.error ||
          `Upload failed (HTTP ${res.status})`
        alert(msg)
        return
      }
      const recording = await res.json()
      setRecordings(prev => [recording, ...prev])
      setSelectedRecording(recording)
      setAnalysis(null)
    } catch (err) {
      alert(`Upload failed: ${err.message}`)
    }
  }, [])

  // Called by AnalysisProgress when the SSE stream reports status='done'.
  // Fetches the actual analysis payload from the recording detail endpoint.
  const handleAnalysisDone = useCallback(async () => {
    if (!selectedRecording) return
    try {
      const res = await authFetch(`${API_BASE}/recordings/${selectedRecording.id}/`)
      if (!res.ok) throw new Error(`Backend returned ${res.status}`)
      const recording = await res.json()
      const result = recording.analysis_result ?? null
      setAnalysis(result)
      setRecordings(prev =>
        prev.map(r =>
          r.id === selectedRecording.id
            ? { ...r, analysis_result: result, is_analyzed: true }
            : r
        )
      )
    } catch (err) {
      console.error('Failed to fetch analysis result:', err)
      setAnalyzeError(err.message)
    } finally {
      setAnalyzing(false)
    }
  }, [selectedRecording])

  const handleAnalyze = useCallback(async () => {
    if (!selectedRecording) return
    setAnalyzing(true)
    setAnalyzeError(null)
    try {
      const res = await authFetch(`${API_BASE}/analyze/${selectedRecording.id}/`, {
        method: 'POST',
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`)
      // POST returned HTTP 202 — analysis is now queued.
      // AnalysisProgress will call handleAnalysisDone when the SSE stream
      // reports status='done', at which point we fetch the real results.
    } catch (err) {
      console.error('Analysis failed:', err)
      setAnalyzeError(err.message)
      setAnalyzing(false)
    }
  }, [selectedRecording])

  const handleSelectRecording = useCallback((recording) => {
    setSelectedRecording(recording)
    // The list serializer excludes analysis_result (too large).
    // Fetch the full detail endpoint to get the analysis payload.
    if (recording.is_analyzed) {
      authFetch(`${API_BASE}/recordings/${recording.id}/`)
        .then(r => r.json())
        .then(data => setAnalysis(data.analysis_result ?? null))
        .catch(() => setAnalysis(null))
    } else {
      setAnalysis(null)
    }
  }, [])

  const handleDownloadReport = useCallback(async () => {
    if (!analysis || !selectedRecording) return
    setDownloading(true)
    try {
      await exportReport(selectedRecording, analysis)
    } catch (err) {
      console.error('Report export failed:', err)
      alert(`Failed to generate PDF report: ${err.message}`)
    } finally {
      setDownloading(false)
    }
  }, [analysis, selectedRecording])

  // ── Auth gate: show login until identity is confirmed ────────────────────
  if (authLoading) {
    return (
      <div className="card" style={{ textAlign: 'center' }}>
        <span className="loading-spinner" style={{ width: 26, height: 26 }} /> Loading…
      </div>
    )
  }

  if (!user) {
    return <AuthScreen apiBase={API_BASE} onAuthed={setUser} onGuest={handleGuest} />
  }

  return (
    <div>
      <h1>Vedic Acoustica</h1>
      <p className="subtitle">Microtonal Voice Analysis &middot; 22 Shrutis &middot; Raga Detection &middot; Ghana Patha Validation</p>

      <div className="status-bar">
        <span className="dot"></span>
        {window.location.hostname === 'localhost' ? 'Backend: localhost:8000' : '● Backend Connected'}
        {analysis && <span style={{ marginLeft: 'auto', color: '#4caf50' }}>Analysis Complete</span>}
        <span className="auth-badge">👤 {user.username}{user.is_staff ? ' (admin)' : user.is_guest ? ' (read-only)' : ''}</span>
        {user.is_staff && (
          <button type="button" className="btn btn-secondary auth-btn" onClick={() => setShowAdmin(s => !s)}>
            {showAdmin ? 'Hide Admin' : 'Admin'}
          </button>
        )}
        <button type="button" className="btn btn-secondary auth-btn" onClick={handleLogout}>Logout</button>
      </div>

      {showAdmin && (
        <div style={{ marginTop: '1rem' }}>
          <AdminOverview apiBase={API_BASE} />
        </div>
      )}

      <AudioUploader onUpload={handleUpload} />

      {fetchError && (
        <div className="card" style={{ borderColor: '#e94560', background: 'rgba(233, 69, 96, 0.08)' }}>
          <p style={{ color: '#e94560', fontSize: '0.85rem', margin: 0 }}>
            Could not reach backend: {fetchError}
          </p>
        </div>
      )}

      {recordings.length > 0 && (
        <div className="card">
          <h2>Recordings</h2>
          <div className="recording-list">
            {recordings.map(r => (
              <div
                key={r.id}
                className={`recording-item ${selectedRecording?.id === r.id ? 'active' : ''}`}
                onClick={() => handleSelectRecording(r)}
              >
                <span>{r.title}</span>
                {r.is_analyzed && <span className="badge">Analyzed</span>}
              </div>
            ))}
          </div>
          {selectedRecording && (
            <>
              <button
                className="btn"
                onClick={handleAnalyze}
                disabled={analyzing}
                style={{ marginTop: '1rem' }}
              >
                {analyzing ? <><span className="loading-spinner" /> Analysing…</> : 'Run Analysis'}
              </button>

              {analyzing && (
                <div style={{ marginTop: '1.25rem' }}>
                  <AnalysisProgress
                    recordingId={selectedRecording.id}
                    apiBase={API_BASE}
                    onDone={handleAnalysisDone}
                    onError={(msg) => setAnalyzeError(msg)}
                  />
                </div>
              )}

              {analyzeError && !analyzing && (
                <p style={{ marginTop: '0.75rem', color: '#e94560', fontSize: '0.85rem' }}>
                  ⚠️ {analyzeError}
                </p>
              )}
            </>
          )}
        </div>
      )}

      {selectedRecording && (
        <AudioPlayer
          ref={playerRef}
          audioUrl={resolveMediaUrl(selectedRecording.playback_file || selectedRecording.audio_file)}
          title={selectedRecording.title}
          onTimeUpdate={(t) => setPlaybackTime(t)}
        />
      )}

      {analysis && (
        <>
          <div className="report-bar">
            <button
              className="btn btn-secondary report-btn"
              onClick={handleDownloadReport}
              disabled={downloading || chartsReady < NUM_CHARTS}
            >
              {downloading
                ? <><span className="loading-spinner"></span> Generating...</>
                : chartsReady < NUM_CHARTS
                  ? '⏳ Preparing report...'
                  : '⬇ Download PDF Report'}
            </button>
          </div>
          <div className="grid">
            <div className="card" id="chart-spectrogram">
              <h2>Spectrogram</h2>
              <SpectrogramView
                data={analysis.spectrogram_data}
                duration={analysis.duration}
                onReady={markChartReady}
                playbackTime={playbackTime}
              />
            </div>
            <div className="card" id="chart-clusters">
              <h2>Shruti Clusters (K=22)</h2>
              <ClusterPlot data={analysis} onReady={markChartReady} />
            </div>
          </div>
          <div className="grid">
            <div className="card" id="chart-shruti-map">
              <h2>22 Shruti Frequency Map</h2>
              <ShrutiMap data={analysis} onReady={markChartReady} />
            </div>
            <div className="card" id="chart-ghana-path">
              <h2>Ghana Patha Validation</h2>
              <GhanaPathaViz
                data={analysis}
                duration={analysis.duration}
                playerRef={playerRef}
                onReady={markChartReady}
              />
            </div>
          </div>
          <div className="grid">
            <div className="card" id="chart-raga-detection" style={{ gridColumn: '1 / -1' }}>
              <h2>Raga Detection</h2>
              <RagaViz data={analysis} onReady={markChartReady} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default App
