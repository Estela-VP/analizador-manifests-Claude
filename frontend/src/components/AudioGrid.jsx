import './AudioGrid.css'

const CHANNEL_LABELS = {
  1: 'Mono (1.0)',
  2: 'Estéreo (2.0)',
  6: 'Surround (5.1)',
  8: 'Surround (7.1)',
}

export default function AudioGrid({ tracks }) {
  return (
    <div className="audio-grid">
      {tracks.map((track, i) => (
        <AudioCard key={i} track={track} />
      ))}
    </div>
  )
}

function AudioCard({ track }) {
  const cls = track.is_atmos
    ? 'audio-card audio-card--atmos'
    : track.type === 'Dolby Digital'
      ? 'audio-card audio-card--dolby'
      : 'audio-card audio-card--aac'

  return (
    <div className={cls}>
      <p className="audio-type">{track.type}</p>
      {track.codec    && <p className="audio-codec">{track.codec}</p>}
      {track.channels && (
        <p className="audio-ch">
          {CHANNEL_LABELS[track.channels] ?? `${track.channels} canales`}
        </p>
      )}
    </div>
  )
}
