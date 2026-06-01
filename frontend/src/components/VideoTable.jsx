import './VideoTable.css'

function fmtFps(raw) {
  if (!raw) return '—'
  const n = parseFloat(raw)
  if (isNaN(n)) return raw
  // Muestra 1 decimal solo si es necesario
  return Number.isInteger(n) ? `${n}` : n.toFixed(2).replace(/0+$/, '').replace(/\.$/, '')
}

function fmtMbps(bps) {
  if (!bps) return '—'
  return (bps / 1_000_000).toFixed(2) + ' Mbps'
}

export default function VideoTable({ layers }) {
  const sorted = [...layers].sort((a, b) => (b.bandwidth || 0) - (a.bandwidth || 0))

  return (
    <div className="table-wrap">
      <table className="video-table">
        <thead>
          <tr>
            <th>Calidad</th>
            <th>Bitrate</th>
            <th>Resolución</th>
            <th>FPS</th>
            <th>Codec</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((layer, i) => (
            <tr key={i}>
              <td>
                {layer.height
                  ? <span className="quality-tag">{layer.height}p</span>
                  : '—'}
              </td>
              <td>{fmtMbps(layer.bandwidth)}</td>
              <td>{layer.width && layer.height ? `${layer.width}×${layer.height}` : '—'}</td>
              <td>{fmtFps(layer.framerate)} fps</td>
              <td><code className="codec-tag">{layer.codec || '—'}</code></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
