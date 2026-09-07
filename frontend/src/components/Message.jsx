import { useState } from 'react'
import SourceCard from './SourceCard.jsx'

export default function Message({ role, text, sources = [], evidence = [], demoMode = false }) {
  const [showEvidence, setShowEvidence] = useState(false)

  if (role === 'user') {
    return (
      <div className="message message-user">
        <div className="bubble bubble-user">{text}</div>
      </div>
    )
  }

  return (
    <div className="message message-assistant">
      <div className="bubble bubble-assistant">
        {demoMode && <div className="demo-badge">DEMO DATA / DEMO MODE</div>}
        <div className="answer-text">{text}</div>

        {sources.length > 0 && (
          <div className="sources-section">
            <div className="section-label">Sources</div>
            <div className="source-cards">
              {sources.map((s, i) => (
                <SourceCard key={i} source={s} />
              ))}
            </div>
          </div>
        )}

        {evidence.length > 0 && (
          <div className="evidence-section">
            <button className="evidence-toggle" onClick={() => setShowEvidence(!showEvidence)}>
              🔎 Evidence Used ({evidence.length}) {showEvidence ? '▲' : '▼'}
            </button>
            {showEvidence && (
              <ul className="evidence-list">
                {evidence.map((e, i) => (
                  <li key={i}>
                    <strong>{e.title}</strong>
                    {e.page && e.page !== 'N/A' ? ` (p.${e.page})` : ''}: {e.text}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
