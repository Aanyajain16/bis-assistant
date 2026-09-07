import Chat from './components/Chat.jsx'

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>🇮🇳 BIS INTELLIGENCE ASSISTANT</h1>
        <p className="subtitle">AI-powered Standards & Compliance Assistant</p>
      </header>
      <main>
        <Chat />
      </main>
      <footer className="app-footer">
        Prototype for SIH26107 · Answers are grounded in retrieved BIS evidence only
      </footer>
    </div>
  )
}
