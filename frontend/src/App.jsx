import { useState } from 'react'
import UrlForm     from './components/UrlForm'
import ResultPanel from './components/ResultPanel'
import './App.css'

export default function App() {
  const [result,  setResult]  = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)

  async function handleAnalyze(url, fetchContent) {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const base = import.meta.env.VITE_API_URL ?? ''
      const res  = await fetch(`${base}/api/analyze`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ url, fetch_content: fetchContent }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `Error ${res.status}`)
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Analizador de Manifests</h1>
        <p>DASH (.mpd) · HLS (.m3u8)</p>
      </header>

      <main className="app-main">
        <UrlForm onAnalyze={handleAnalyze} loading={loading} />

        {loading && (
          <div className="loading-box">
            <span className="spinner" />
            Analizando manifest…
          </div>
        )}

        {error && (
          <div className="error-box">
            {error}
          </div>
        )}

        {result && <ResultPanel data={result} />}
      </main>
    </div>
  )
}
