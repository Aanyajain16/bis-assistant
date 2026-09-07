import { useState, useRef, useEffect } from 'react'
import Message from './Message.jsx'
import QuickActions from './QuickActions.jsx'
import { sendMessage } from '../api.js'

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [conversationId, setConversationId] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function handleSend(overrideText) {
    const text = (overrideText ?? input).trim()
    if (!text || loading) return

    setError(null)
    setMessages((prev) => [...prev, { role: 'user', text }])
    setInput('')
    setLoading(true)

    try {
      const data = await sendMessage(text, conversationId)
      setConversationId(data.conversation_id)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: data.answer,
          sources: data.sources || [],
          evidence: data.evidence || [],
          demoMode: data.demo_mode,
        },
      ])
    } catch (err) {
      setError('Could not reach the BIS Assistant backend. Is it running on http://localhost:8000?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-container">
      {messages.length === 0 && (
        <div className="empty-state">
          <p>Ask about BIS standards, certification, testing, or laboratories.</p>
          <p className="example-question" onClick={() => handleSend(
            'I manufacture LED lighting products. What BIS standards and certification requirements may apply?'
          )}>
            💡 "I manufacture LED lighting products. What BIS standards and certification requirements may apply?"
          </p>
          <QuickActions onSelect={handleSend} disabled={loading} />
        </div>
      )}

      <div className="message-list">
        {messages.map((m, i) => (
          <Message key={i} {...m} />
        ))}
        {loading && (
          <div className="message message-assistant">
            <div className="bubble bubble-assistant loading-bubble">Searching BIS knowledge base...</div>
          </div>
        )}
        {error && <div className="error-banner">⚠️ {error}</div>}
        <div ref={bottomRef} />
      </div>

      {messages.length > 0 && (
        <QuickActions onSelect={handleSend} disabled={loading} />
      )}

      <div className="input-row">
        <input
          type="text"
          value={input}
          placeholder="Ask about a BIS standard, certification, or testing requirement..."
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          disabled={loading}
        />
        <button onClick={() => handleSend()} disabled={loading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  )
}
