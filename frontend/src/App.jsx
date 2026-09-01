import { useState, useCallback } from 'react'
import AudioUploader from './components/AudioUploader'
import SpectrogramView from './components/SpectrogramView'
import ClusterPlot from './components/ClusterPlot'
import ShrutiMap from './components/ShrutiMap'
import GhanaPathaViz from './components/GhanaPathaViz'
import AudioPlayer from './components/AudioPlayer'
import exportReport from './utils/exportReport'
import './App.css'

const API_BASE = '/api'

function App() {
  const [recordings, setRecordings] = useState([])
  const [selectedRecording, setSelectedRecording] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [downloading, setDownloading] = useState(false)

  const fetchRecordings = useCallback(async () => {
    const res = await fetch(`${API_BASE}/recordings/`)
    const data = await res.json()
    setRecordings(data)
  }, [])

  const handleUpload = useCallback(async (file) => {
    const formData = new FormData()
    formData.append('audio_file', file)
    formData.append('title', file.name)

    const res = await fetch(`${API_BASE}/upload/`, {
      method: 'POST',
      body: formData,
    })
    const recording = await res.json()
    setRecordings(prev => [recording, ...prev])
    setSelectedRecording(recording)
    setAnalysis(null)
  }, [])

  const handleAnalyze = useCallback(async () => {
    if (!selectedRecording) return
    setAnalyzing(true)
    try {
      const res = await fetch(`${API_BASE}/analyze/${selectedRecording.id}/`, {
        method: 'POST',
      })
      const data = await res.json()
      setAnalysis(data)
      setRecordings(prev =>
        prev.map(r => r.id === selectedRecording.id ? { ...r, analysis_result: data, is_analyzed: true } : r)
      )
    } catch (err) {
      console.error('Analysis failed:', err)
    } finally {
      setAnalyzing(false)
    }
  }, [selectedRecording])

  const handleSelectRecording = useCallback((recording) => {
    setSelectedRecording(recording)
    setAnalysis(recording.analysis_result || null)
  }, [])

  const handleDownloadReport = useCallback(async () => {
    if (!analysis || !selectedRecording) return
    setDownloading(true)
    try {
      await exportReport(selectedRecording, analysis)
    } catch (err) {
      console.error('Report export failed:', err)
      alert('Failed to generate PDF report. Please try again.')
    } finally {
      setDownloading(false)
    }
  }, [analysis, selectedRecording])

  return (
    <div>
      <h1>Vedic Acoustica</h1>
      <p className="subtitle">Microtonal Voice Analysis &middot; 22 Shrutis &middot; Ghana Patha Validation</p>

      <div className="status-bar">
        <span className="dot"></span>
        Backend: localhost:8000
        {analysis && <span style={{ marginLeft: 'auto', color: '#4caf50' }}>Analysis Complete</span>}
      </div>

      <AudioUploader onUpload={handleUpload} />

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
            <button
              className="btn"
              onClick={handleAnalyze}
              disabled={analyzing}
              style={{ marginTop: '1rem' }}
            >
              {analyzing ? <><span className="loading-spinner"></span> Analyzing...</> : 'Run Analysis'}
            </button>
          )}
        </div>
      )}

      {selectedRecording && (
        <AudioPlayer audioUrl={selectedRecording.audio_file} title={selectedRecording.title} />
      )}

      {analysis && (
        <>
          <div className="report-bar">
            <button
              className="btn btn-secondary report-btn"
              onClick={handleDownloadReport}
              disabled={downloading}
            >
              {downloading ? <><span className="loading-spinner"></span> Generating...</> : '⬇ Download PDF Report'}
            </button>
          </div>
          <div className="grid">
            <div className="card" id="chart-spectrogram">
              <h2>Spectrogram</h2>
              <SpectrogramView data={analysis.spectrogram_data} duration={analysis.duration} />
            </div>
            <div className="card" id="chart-clusters">
              <h2>Shruti Clusters (K=22)</h2>
              <ClusterPlot data={analysis} />
            </div>
          </div>
          <div className="grid">
            <div className="card" id="chart-shruti-map">
              <h2>22 Shruti Frequency Map</h2>
              <ShrutiMap data={analysis} />
            </div>
            <div className="card" id="chart-ghana-path">
              <h2>Ghana Patha Validation</h2>
              <GhanaPathaViz data={analysis} />
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default App
