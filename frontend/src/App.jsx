import { useState, useCallback, useEffect, useRef } from 'react'
import AudioUploader from './components/AudioUploader'
import SpectrogramView from './components/SpectrogramView'
import ClusterPlot from './components/ClusterPlot'
import ShrutiMap from './components/ShrutiMap'
import GhanaPathaViz from './components/GhanaPathaViz'
import RagaViz from './components/RagaViz'
import AudioPlayer from './components/AudioPlayer'
import AnalysisProgress from './components/AnalysisProgress'
import ShrutiInstrument from './components/ShrutiInstrument'
import SoundExplorer from './components/SoundExplorer'
import AuthScreen from './components/AuthScreen'
import AdminOverview from './components/AdminOverview'
import { getUser, getToken, clearAuth, authFetch } from './utils/auth'
import './observatory.css'

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
  const [selectedSwara, setSelectedSwara] = useState('Sa')
  const [activeSection, setActiveSection] = useState('upload')
  // Imperative ref to AudioPlayer — lets GhanaPathaViz call seekTo(seconds)
  const playerRef = useRef(null)

  // ── Auth: user identity + token gate (backend /api/auth/*) ────────────────
  const [user, setUser] = useState(() => getUser())
  const [authLoading, setAuthLoading] = useState(true)
  const [showAdmin, setShowAdmin] = useState(false)

  const getDisplayName = useCallback((userData) => {
    if (!userData) return 'Researcher'
    const first = (userData.first_name || '').trim()
    const last = (userData.last_name || '').trim()
    const fullName = [first, last].filter(Boolean).join(' ')
    return fullName || userData.username || 'Researcher'
  }, [])

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
    const onExpired = () => {
      clearAuth()
      setUser(null)
      setRecordings([])
    }
    window.addEventListener('auth-expired', onExpired)
    return () => window.removeEventListener('auth-expired', onExpired)
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
    setRecordings([])
  }, [])

  const markChartReady = useCallback(() => {
    setChartsReady(prev => (prev >= NUM_CHARTS ? prev : prev + 1))
  }, [])

  const fetchRecordings = useCallback(async () => {
    if (!getToken()) return
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
    if (user) {
      fetchRecordings()
    }
  }, [user, fetchRecordings])

  useEffect(() => {
    setChartsReady(0)
  }, [analysis])

  useEffect(() => {
    setSelectedSwara(analysis?.raga_detection?.detected_swaras?.[0]?.swara || 'Sa')
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
      const { default: exportReport } = await import('./utils/exportReport')
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
      <div className="observatory-loading">
        <span className="loading-spinner" />
        <span>Opening the acoustic observatory…</span>
      </div>
    )
  }

  if (!user) {
    return <AuthScreen apiBase={API_BASE} onAuthed={setUser} />
  }

  const displayName = getDisplayName(user)

  return (
    <div className="observatory dashboard-shell">
      <header className="observatory-nav">
        <a className="observatory-brand" href="#top" aria-label="Vedic Acoustica home">
          <span className="brand-seal" aria-hidden="true">ॐ</span>
          <span className="brand-wordmark">
            <strong>VEDIC ACŪSTICA</strong>
            <small>Ancient Sound • Modern Intelligence</small>
          </span>
        </a>
        <nav className="observatory-links" aria-label="Main navigation">
          <button
            type="button"
            className={`workspace-tab ${activeSection === 'upload' ? 'active' : ''}`}
            aria-pressed={activeSection === 'upload'}
            onClick={() => setActiveSection('upload')}
          >
            Upload
          </button>
          <button
            type="button"
            className={`workspace-tab ${activeSection === 'explorer' ? 'active' : ''}`}
            aria-pressed={activeSection === 'explorer'}
            onClick={() => setActiveSection('explorer')}
          >
            Explorer
          </button>
          {analysis && activeSection === 'upload' && <a href="#research-folio">Research</a>}
        </nav>
        <div className="nav-identity">
          <span className="auth-badge">Welcome back, {displayName}</span>
          {user.is_staff && (
            <button type="button" className="engraved-button small" onClick={() => setShowAdmin(s => !s)}>
              {showAdmin ? 'Close ledger' : 'Admin ledger'}
            </button>
          )}
          <button type="button" className="engraved-button small" onClick={handleLogout}>Leave</button>
        </div>
      </header>

      <main id="top">
        <section className="observatory-hero dashboard-hero">
          <div className="hero-copy">
            <span className="eyebrow">VEDIC ACŪSTICA</span>
            <h1>Welcome back,<em>{displayName}</em></h1>
            <p className="hero-subtitle">Ancient Sound • Modern Intelligence</p>
            <p className="hero-description">
              Enter the acoustic chamber to explore the 22 Śruti, study a recording,
              and follow its melodic and recitation patterns.
            </p>
            <div className="hero-index">
              <span>22 ŚRUTI</span><i />
              <span>RĀGA</span><i />
              <span>GHANA PATHA</span>
            </div>
            <a className="hero-invitation" href="#acoustic-chamber">
              <span>Continue to the listening chamber</span><b aria-hidden="true">↓</b>
            </a>
          </div>
          <ShrutiInstrument
            selectedSwara={selectedSwara}
            detectedSwaras={analysis?.raga_detection?.detected_swaras ?? []}
            onSelect={setSelectedSwara}
          />
        </section>

        {showAdmin && (
          <section className="admin-ledger">
            <AdminOverview apiBase={API_BASE} />
          </section>
        )}

        {activeSection === 'upload' && <section className="dashboard-tools" id="acoustic-chamber">
          <div className="dashboard-tool-heading" id="recording-archive">
            <span className="eyebrow">I · The listening chamber</span>
            <h2>Offer a recording to the instrument</h2>
            <p>Choose a recording to begin an acoustic study.</p>
          </div>
          <AudioUploader onUpload={handleUpload} />

          {fetchError && (
            <p className="error-inscription" role="alert">
              The recording archive could not be opened. Please try again later.
            </p>
          )}

          {recordings.length > 0 && (
            <div className="archive-panel card">
              <div className="archive-heading">
                <div>
                  <span className="eyebrow">II · Recordings</span>
                  <h2>Listening archive</h2>
                </div>
                <span className="archive-count">{recordings.length.toString().padStart(2, '0')} ENTRIES</span>
              </div>
              <div className="recording-list">
                {recordings.map((recording, index) => (
                  <button
                    type="button"
                    key={recording.id}
                    className={`recording-item ${selectedRecording?.id === recording.id ? 'active' : ''}`}
                    onClick={() => handleSelectRecording(recording)}
                    aria-pressed={selectedRecording?.id === recording.id}
                  >
                    <span className="recording-index">{String(index + 1).padStart(2, '0')}</span>
                    <span className="recording-title">{recording.title}</span>
                    <span className={`recording-state ${recording.is_analyzed ? 'is-analyzed' : ''}`}>
                      {recording.is_analyzed ? 'Examined' : 'Unexamined'}
                    </span>
                  </button>
                ))}
              </div>
              {selectedRecording && (
                <>
                  <button className="engraved-button" onClick={handleAnalyze} disabled={analyzing}>
                    {analyzing
                      ? <><span className="loading-spinner" /> Tracing the sound…</>
                      : 'Begin acoustic analysis'}
                  </button>
                  {analyzing && (
                    <div className="progress-manuscript">
                      <AnalysisProgress
                        recordingId={selectedRecording.id}
                        apiBase={API_BASE}
                        onDone={handleAnalysisDone}
                        onError={(msg) => setAnalyzeError(msg)}
                      />
                    </div>
                  )}
                  {analyzeError && !analyzing && (
                    <p className="error-inscription" role="alert">{analyzeError}</p>
                  )}
                </>
              )}
            </div>
          )}
        </section>}

        {activeSection === 'explorer' && (
          <section className="explorer-section" id="explorer">
            <div className="dashboard-tool-heading">
              <span className="eyebrow">I · The acoustic explorer</span>
              <h2>Study the architecture of sound</h2>
              <p>Explore the 22 Śruti instrument and inspect real observations from your selected recording.</p>
            </div>

            <SoundExplorer
              onOpenUpload={() => setActiveSection('upload')}
              onSelectSwara={setSelectedSwara}
            />

            <div className="explorer-feature-grid">
              <div className="folio-panel explorer-scale">
                <div className="folio-heading">
                  <h2>The 22-fold scale</h2>
                  <span className="folio-number">ŚRUTI YANTRA</span>
                </div>
                <p>Select an engraved degree to focus it on the observatory instrument above.</p>
                <div className="explorer-family-list" aria-label="Swara families">
                  {['Sa', 'Re', 'Ga', 'Ma', 'Pa', 'Dha', 'Ni'].map((family) => (
                    <button
                      key={family}
                      type="button"
                      className={`engraved-button small ${selectedSwara.startsWith(family) ? 'selected' : ''}`}
                      onClick={() => setSelectedSwara(family === 'Sa' || family === 'Pa' ? family : `${family}1`)}
                      aria-pressed={selectedSwara.startsWith(family)}
                    >
                      {family}
                    </button>
                  ))}
                </div>
                <p className="instrument-note">
                  Selected degree: <strong>{selectedSwara}</strong>
                  {analysis?.raga_detection?.detected_swaras?.some(item => item.swara === selectedSwara)
                    ? ' · present in the selected analysis'
                    : ''}
                </p>
              </div>

              <div className="folio-panel explorer-recordings">
                <div className="folio-heading">
                  <h2>Listening archive</h2>
                  <span className="folio-number">{recordings.length.toString().padStart(2, '0')} ENTRIES</span>
                </div>
                {recordings.length ? (
                  <div className="recording-list">
                    {recordings.map((recording, index) => (
                      <button
                        type="button"
                        key={recording.id}
                        className={`recording-item ${selectedRecording?.id === recording.id ? 'active' : ''}`}
                        onClick={() => handleSelectRecording(recording)}
                        aria-pressed={selectedRecording?.id === recording.id}
                      >
                        <span className="recording-index">{String(index + 1).padStart(2, '0')}</span>
                        <span className="recording-title">{recording.title}</span>
                        <span className={`recording-state ${recording.is_analyzed ? 'is-analyzed' : ''}`}>
                          {recording.is_analyzed ? 'Examined' : 'Unexamined'}
                        </span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="archive-empty">
                    {fetchError ? 'The archive is unavailable until its connection is restored.' : 'No recordings are held in this archive yet.'}
                  </p>
                )}
              </div>
            </div>

            <div className="explorer-feature-grid explorer-observations">
              <div className="folio-panel">
                <div className="folio-heading">
                  <h2>Rāga observation</h2>
                  <span className="folio-number">FROM ANALYSIS</span>
                </div>
                {analysis
                  ? <RagaViz data={analysis} />
                  : <p className="archive-empty">Select an analyzed recording in the Upload section to inspect its detected rāga.</p>}
              </div>
              <div className="folio-panel">
                <div className="folio-heading">
                  <h2>Ghana Patha observation</h2>
                  <span className="folio-number">FROM ANALYSIS</span>
                </div>
                {analysis
                  ? <GhanaPathaViz data={analysis} duration={analysis.duration} playerRef={playerRef} />
                  : <p className="archive-empty">Ghana Patha findings appear here after a recording has been analyzed.</p>}
              </div>
            </div>
          </section>
        )}

        {selectedRecording && (
          <section className="playback-chamber" aria-label="Selected recording playback">
            <div className="playback-caption">
              <span className="eyebrow">Listening instrument</span>
              <p>Follow the voice through the sound trace</p>
            </div>
            <AudioPlayer
              ref={playerRef}
              audioUrl={resolveMediaUrl(selectedRecording.playback_file || selectedRecording.audio_file)}
              title={selectedRecording.title}
              onTimeUpdate={(t) => setPlaybackTime(t)}
            />
          </section>
        )}

        {analysis && activeSection === 'upload' && (
          <section className="research-section" id="research-folio">
            <div className="research-title-row">
              <div className="dashboard-tool-heading">
                <span className="eyebrow">III · Observations from the instrument</span>
                <h2>Research folio</h2>
              </div>
              <button
                className="engraved-button report-btn"
                onClick={handleDownloadReport}
                disabled={downloading || chartsReady < NUM_CHARTS}
              >
                {downloading
                  ? <><span className="loading-spinner" /> Preparing folio…</>
                  : chartsReady < NUM_CHARTS
                    ? 'Preparing folio…'
                    : 'Download research folio'}
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
                <h2>23 Shruti Frequency Map</h2>
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
          </section>
        )}
      </main>

      <footer className="observatory-footer">
        <span>VEDIC ACŪSTICA</span>
        <span>AN INSTRUMENT FOR THE STUDY OF SACRED SOUND</span>
      </footer>
    </div>
  )
}

export default App
