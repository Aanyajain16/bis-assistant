const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export async function sendMessage(message, conversationId) {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  })

  if (!response.ok) {
    throw new Error(`Backend returned ${response.status}`)
  }

  return response.json()
}

export async function checkHealth() {
  const response = await fetch(`${API_BASE}/api/health`)
  if (!response.ok) throw new Error('Health check failed')
  return response.json()
}
