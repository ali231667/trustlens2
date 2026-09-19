import { useEffect, useState } from 'react'
import { useLocation, Navigate } from 'react-router-dom'
import Navbar from '../components/Navbar'
import '../components/Navbar.css'
import './Results.css'
import { transcribeUrl } from '../api/trustlens'

function Results() {
  const location = useLocation()
  const result = location.state?.result
  const [revealed, setRevealed] = useState(0)

  // On-demand reel analysis (transcribe latest reel -> misinformation)
  const [reelLoading, setReelLoading] = useState(false)
  const [reelError, setReelError] = useState('')
  const [reelData, setReelData] = useState(null)

  // Prefer a video reel; fall back to the latest post of any kind.
  const latestPostCode =
    result?.engagement_data?.reel_codes?.[0] || result?.engagement_data?.post_codes?.[0]

  async function analyzeReel() {
    if (!latestPostCode) return
    setReelLoading(true)
    setReelError('')
    setReelData(null)
    try {
      const url = `https://www.instagram.com/reel/${latestPostCode}/`
      const res = await transcribeUrl(url)
      setReelData(res)
    } catch (err) {
      setReelError(err.message || 'Could not analyze the reel.')
    } finally {
      setReelLoading(false)
    }
  }

  if (!result) {
    return <Navigate to="/" replace />
  }

  const colorFromVerdict = (verdict) => {
    if (verdict === 'Trusted') return 'green'
    if (verdict === 'Moderate Risk') return 'yellow'
    return 'red'
  }

  const profile = {
    username: result.username,
    fullName: result.full_name,
    isVerified: result.is_verified,
    trustScore: result.trust_score.trust_score,
    verdict: result.trust_score.verdict,
    color: colorFromVerdict(result.trust_score.verdict),
  }

  const img = result.image_analysis || {}
  const imgDisplay = (() => {
    if (img.status === 'ok' && img.band === 'real') {
      return { score: `${100 - (img.score ?? 0)}%`, color: 'score-green', desc: img.verdict }
    }
    if (img.status === 'ok' && img.band === 'fake') {
      return { score: `${img.score}% AI`, color: 'score-red', desc: img.verdict }
    }
    if (img.band === 'uncertain') {
      return { score: '—', color: 'score-yellow', desc: img.details?.reason || 'Uncertain — needs review' }
    }
    if (img.band === 'not_applicable') {
      return { score: '—', color: '', desc: 'Profile picture is not a human face' }
    }
    if (img.status === 'unavailable') {
      return { score: '—', color: '', desc: 'Detector service offline' }
    }
    return { score: '—', color: '', desc: 'No profile picture to analyze' }
  })()

  const checks = [
    { label: 'Followers analyzed', value: result.raw_profile_data.followers.toLocaleString() },
    { label: 'Fake follower risk', value: `${result.fake_follower_analysis.bot_percentage}%` },
    { label: 'Engagement rate', value: `${result.engagement_analysis.engagement_rate}% — ${result.engagement_analysis.status}` },
    { label: 'Profile completeness', value: profile.isVerified ? 'Verified account' : 'Not verified' },
  ]

  useEffect(() => {
    const timer = setInterval(() => {
      setRevealed((prev) => (prev < checks.length ? prev + 1 : prev))
    }, 350)
    return () => clearInterval(timer)
  }, [])

  const circumference = 2 * Math.PI * 90
  const targetOffset = circumference - (profile.trustScore / 100) * circumference
  const [ringOffset, setRingOffset] = useState(circumference)

  useEffect(() => {
    const timer = setTimeout(() => setRingOffset(targetOffset), 200)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="results-page">
      <Navbar />

      <div className="results-content">
        <div className="results-profile-strip">
          <div className="results-avatar">
            {profile.username.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="results-fullname">
              {profile.fullName}
              {profile.isVerified && <span className="verified-badge">✓ verified</span>}
            </div>
            <div className="results-username">@{profile.username}</div>
          </div>
        </div>

        <div className="results-main">
          <div className="score-panel">
            <svg className="score-ring" viewBox="0 0 200 200">
              <circle cx="100" cy="100" r="90" className="score-ring-bg" />
              <circle
                cx="100" cy="100" r="90"
                className={`score-ring-fill ring-${profile.color}`}
                style={{
                  strokeDasharray: circumference,
                  strokeDashoffset: ringOffset,
                }}
              />
            </svg>
            <div className="score-ring-center">
              <span className="score-number">{profile.trustScore}</span>
              <span className={`score-verdict verdict-text-${profile.color}`}>
                {profile.verdict}
              </span>
            </div>
          </div>

          <div className="checks-panel">
            <div className="checks-eyebrow">SCAN LOG</div>
            {checks.map((check, i) => (
              <div
                key={check.label}
                className={`check-row ${i < revealed ? 'check-visible' : ''}`}
              >
                <span className="check-mark">{i < revealed ? '✓' : ''}</span>
                <span className="check-label">{check.label}</span>
                <span className="check-value">{i < revealed ? check.value : ''}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="modules-grid">
          <div className="module-card">
            <div className="module-eyebrow">FAKE FOLLOWER DETECTION</div>
            <div className="module-score score-green">{100 - result.fake_follower_analysis.bot_percentage}%</div>
            <div className="module-desc">{result.fake_follower_analysis.verdict}</div>
          </div>
          <div className="module-card">
            <div className="module-eyebrow">ENGAGEMENT ANALYSIS</div>
            <div className="module-score score-green">{result.engagement_analysis.status}</div>
            <div className="module-desc">{result.engagement_analysis.engagement_rate}% engagement rate — {result.engagement_analysis.tier} tier</div>
          </div>
          <div className="module-card">
            <div className="module-eyebrow">AI PROFILE IMAGE</div>
            <div className={`module-score ${imgDisplay.color}`}>{imgDisplay.score}</div>
            <div className="module-desc">{imgDisplay.desc}</div>
          </div>
          <div className="module-card module-pending">
            <div className="module-eyebrow">MISINFORMATION CHECK</div>
            <div className="module-score">—</div>
            <div className="module-desc">Module in development</div>
          </div>
        </div>

        <div className="reel-section">
          <div className="reel-header">
            <div>
              <div className="reel-eyebrow">CONTENT ANALYSIS</div>
              <div className="reel-title">Latest reel</div>
            </div>
            <button
              className="reel-button"
              onClick={analyzeReel}
              disabled={reelLoading || !latestPostCode}
            >
              {reelLoading ? 'Analyzing…' : 'Analyze latest reel'}
            </button>
          </div>

          {!latestPostCode && (
            <p className="reel-hint">No recent posts available to analyze.</p>
          )}
          {reelLoading && (
            <p className="reel-hint">
              Downloading and transcribing on CPU — this can take 20–140s.
            </p>
          )}
          {reelError && <p className="reel-error">{reelError}</p>}

          {reelData?.transcription && (
            <div className="reel-result">
              <div className="reel-tags">
                <span className="tag">
                  {(reelData.transcription.detected_language || '—').toUpperCase()}
                </span>
                <span className="tag">
                  confidence: {Math.round((reelData.transcription.confidence || 0) * 100)}%
                </span>
              </div>
              <div className="reel-transcript">
                {reelData.transcription.result?.classifier_input?.text ||
                  reelData.transcription.result?.text ||
                  'No speech text extracted.'}
              </div>
              <div className="reel-misinfo">
                {reelData.misinfo?.status === 'success' ? (
                  <span
                    className={
                      reelData.misinfo.misinformation_flag ? 'verdict-bad' : 'verdict-good'
                    }
                  >
                    {reelData.misinfo.primary_category} · risk {reelData.misinfo.risk_score}
                  </span>
                ) : (
                  <span className="muted">
                    Misinformation classifier offline — transcript ready.
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default Results