import { useState } from 'react'
import Navbar from '../components/Navbar'
import '../components/Navbar.css'
import './Transcribe.css'
import { transcribeUrl, transcribeFile } from '../api/trustlens'

function Transcribe() {
  const [mode, setMode] = useState('upload') // 'upload' | 'url'
  const [url, setUrl] = useState('')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [data, setData] = useState(null)

  async function run() {
    setError('')
    setData(null)
    if (mode === 'url' && !url.trim()) return
    if (mode === 'upload' && !file) return

    setLoading(true)
    try {
      const res = mode === 'url' ? await transcribeUrl(url.trim()) : await transcribeFile(file)
      setData(res)
    } catch (err) {
      setError(err.message || 'Transcription failed.')
    } finally {
      setLoading(false)
    }
  }

  const t = data?.transcription
  const result = t?.result
  const transcript =
    result?.classifier_input?.text || result?.transcript?.text || result?.text || ''
  const misinfo = data?.misinfo

  const qualityColor =
    t?.quality === 'good' ? 'tag-green' : t?.quality === 'poor' ? 'tag-red' : 'tag-yellow'

  return (
    <div className="transcribe-page">
      <Navbar />

      <div className="transcribe-content">
        <div className="transcribe-eyebrow">VIDEO-TO-TEXT</div>
        <h1 className="transcribe-title">Transcribe a reel</h1>
        <p className="transcribe-sub">
          Pull the speech out of an Instagram reel or an uploaded clip. Urdu and English,
          on-device. The transcript is passed to the misinformation classifier when it is online.
        </p>

        <div className="transcribe-tabs">
          <button
            className={`transcribe-tab ${mode === 'upload' ? 'active' : ''}`}
            onClick={() => setMode('upload')}
          >
            Upload file
          </button>
          <button
            className={`transcribe-tab ${mode === 'url' ? 'active' : ''}`}
            onClick={() => setMode('url')}
          >
            Paste URL
          </button>
        </div>

        {mode === 'upload' ? (
          <div className="transcribe-input-row">
            <input
              type="file"
              accept="video/*,audio/*"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              disabled={loading}
              className="transcribe-file"
            />
            <button className="transcribe-run" onClick={run} disabled={loading || !file}>
              {loading ? 'Transcribing…' : 'Transcribe'}
            </button>
          </div>
        ) : (
          <div className="transcribe-input-row">
            <input
              type="text"
              placeholder="https://www.instagram.com/reel/…"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              disabled={loading}
              className="transcribe-url"
            />
            <button className="transcribe-run" onClick={run} disabled={loading || !url.trim()}>
              {loading ? 'Transcribing…' : 'Transcribe'}
            </button>
          </div>
        )}

        {mode === 'url' && (
          <p className="transcribe-hint">
            URL fetching needs a logged-in <code>cookies.txt</code>. If it fails, use file upload.
          </p>
        )}
        {loading && (
          <p className="transcribe-hint">
            Running Whisper locally on CPU — a short reel takes ~20s, longer clips more.
          </p>
        )}
        {error && <p className="transcribe-error">{error}</p>}

        {t && (
          <div className="transcribe-result">
            <div className="transcribe-tags">
              <span className="tag">{(t.detected_language || '—').toUpperCase()}</span>
              <span className={`tag ${qualityColor}`}>quality: {t.quality || '—'}</span>
              <span className="tag">confidence: {Math.round((t.confidence || 0) * 100)}%</span>
              {result?.classifier_input?.is_reliable === false && (
                <span className="tag tag-yellow">low reliability</span>
              )}
            </div>

            <div className="transcribe-transcript">
              {transcript || <span className="muted">No speech text extracted.</span>}
            </div>

            <div className="misinfo-panel">
              <div className="misinfo-eyebrow">MISINFORMATION CHECK</div>
              {misinfo?.status === 'success' ? (
                <div>
                  <div
                    className={`misinfo-verdict ${
                      misinfo.misinformation_flag ? 'tag-red' : 'tag-green'
                    }`}
                  >
                    {misinfo.primary_category} · risk {misinfo.risk_score}
                  </div>
                  <div className="muted">
                    confidence {Math.round((misinfo.confidence || 0) * 100)}%
                  </div>
                </div>
              ) : (
                <div className="muted">
                  Classifier service offline — transcript ready, verdict will appear once the
                  misinformation module is running.
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default Transcribe
