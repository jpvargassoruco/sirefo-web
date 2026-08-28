export default function Badge({ text, className = 'badge-gray' }) {
  if (!text) return <span className="badge badge-gray">—</span>
  return <span className={`badge ${className}`}>{text}</span>
}
