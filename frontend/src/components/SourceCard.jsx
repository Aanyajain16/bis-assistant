export default function SourceCard({ source }) {
  return (
    <div className="source-card">
      <div className="source-title">📄 {source.title || 'Untitled document'}</div>
      <div className="source-meta">
        {source.source && <span>{source.source}</span>}
        {source.page && source.page !== 'N/A' && <span> · Page {source.page}</span>}
        {source.category && <span className="source-category">{source.category}</span>}
      </div>
      {source.url && source.url !== 'N/A' && (
        <a href={source.url} target="_blank" rel="noreferrer" className="source-link">
          View source ↗
        </a>
      )}
    </div>
  )
}
