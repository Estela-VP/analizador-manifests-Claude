import { useState } from 'react'
import './UrlForm.css'

export default function UrlForm({ onAnalyze, loading }) {
  const [url,          setUrl]          = useState('')
  const [fetchContent, setFetchContent] = useState(true)

  function submit() {
    const trimmed = url.trim()
    if (!trimmed || loading) return
    onAnalyze(trimmed, fetchContent)
  }

  return (
    <div className="card url-form">
      <div className="url-row">
        <input
          className="url-input"
          type="text"
          value={url}
          onChange={e => setUrl(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && submit()}
          placeholder="https://example.com/stream.mpd"
          spellCheck={false}
          autoComplete="off"
          disabled={loading}
        />
        <button
          className="btn-analyze"
          onClick={submit}
          disabled={loading || !url.trim()}
        >
          {loading ? 'Analizando…' : 'Analizar'}
        </button>
      </div>

      <label className="check-label">
        <input
          type="checkbox"
          checked={fetchContent}
          onChange={e => setFetchContent(e.target.checked)}
          disabled={loading}
        />
        Descargar y analizar contenido del manifest
      </label>
    </div>
  )
}
