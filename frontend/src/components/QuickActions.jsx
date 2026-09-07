const ACTIONS = [
  { label: '🔍 Find a Standard', prompt: 'Help me find the relevant BIS standard for my product.' },
  { label: '📦 Product Compliance', prompt: 'I manufacture LED lighting products. What BIS standards and certification requirements may apply?' },
  { label: '✅ Certification', prompt: 'What is the process to get BIS certification for a product?' },
  { label: '🧪 Testing & Labs', prompt: 'Which BIS-recognized laboratories can test my product?' },
]

export default function QuickActions({ onSelect, disabled }) {
  return (
    <div className="quick-actions">
      {ACTIONS.map((action) => (
        <button
          key={action.label}
          className="quick-action-btn"
          onClick={() => onSelect(action.prompt)}
          disabled={disabled}
        >
          {action.label}
        </button>
      ))}
    </div>
  )
}
