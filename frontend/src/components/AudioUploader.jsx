import { useRef, useState } from 'react'

const MAX_FILE_SIZE = 50 * 1024 * 1024

export default function AudioUploader({ onUpload }) {
  const fileInputRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)

  const handleFile = async (file) => {
    if (!file) return
    if (!file.type.startsWith('audio/')) {
      alert('Please select an audio file.')
      return
    }
    if (file.size > MAX_FILE_SIZE) {
      alert(`File too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Maximum is 50 MB.`)
      return
    }
    setUploading(true)
    await onUpload(file)
    setUploading(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    handleFile(e.dataTransfer.files[0])
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setDragOver(true)
  }

  return (
    <div
      className={`card upload-zone ${dragOver ? 'drag-over' : ''}`}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={() => setDragOver(false)}
      onClick={() => fileInputRef.current?.click()}
      style={{
        border: `2px dashed ${dragOver ? 'var(--accent)' : 'var(--border)'}`,
        textAlign: 'center',
        cursor: 'pointer',
        padding: '3rem',
        transition: 'all 0.2s',
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".wav,.mp3,.ogg,.flac,audio/wav,audio/mpeg,audio/ogg,audio/flac"
        onChange={(e) => handleFile(e.target.files[0])}
        style={{ display: 'none' }}
      />
      {uploading ? (
        <p><span className="loading-spinner"></span> Uploading...</p>
      ) : (
        <>
          <p style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>&#x1f3b5;</p>
          <p>Drop a .wav file here or click to upload</p>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.8rem', marginTop: '0.5rem' }}>
            Supports WAV · MP3 · OGG · FLAC &nbsp;(max 50 MB)
          </p>
        </>
      )}
    </div>
  )
}
