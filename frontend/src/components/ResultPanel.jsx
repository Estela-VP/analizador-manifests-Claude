import VideoTable from './VideoTable'
import AudioGrid  from './AudioGrid'
import './ResultPanel.css'

const MANIFEST_LABELS = { mpd: 'MPD', hls: 'HLS', unknown: 'Desconocido' }

const CONTENT_META = {
  Live:         { label: 'Live',       icon: '🔴', cls: 'badge--live' },
  VOD:          { label: 'VOD',        icon: '🎬', cls: 'badge--vod'  },
  CPVR:         { label: 'CPVR',       icon: '☁',  cls: 'badge--cpvr' },
  L7D:          { label: 'L7D',        icon: '📅', cls: 'badge--l7d'  },
  'Start Over': { label: 'Start Over', icon: '↩',  cls: 'badge--so'   },
  Unknown:      { label: 'Unknown',    icon: '?',   cls: 'badge--unk'  },
}

function Badge({ text, cls }) {
  return <span className={`badge ${cls}`}>{text}</span>
}

export default function ResultPanel({ data }) {
  const mType   = data.manifest_type || 'unknown'
  const cType   = data.content_type  || 'Unknown'
  const meta    = CONTENT_META[cType] || CONTENT_META.Unknown
  const conf    = Math.round((data.confidence || 0) * 100)

  return (
    <div className="result-panel">
      {/* ── Basic info ── */}
      <div className="card">
        <p className="card-label">Manifest</p>
        <div className="url-display">{data.url}</div>

        <div className="info-row">
          <Badge text={MANIFEST_LABELS[mType] || mType.toUpperCase()} cls={`badge--${mType}`} />
          <Badge text={`${meta.icon} ${meta.label}`} cls={meta.cls} />
          <span className="confidence">{conf}% confianza</span>
        </div>
      </div>

      {/* ── Content details ── */}
      {data.content && <ContentCard content={data.content} />}
    </div>
  )
}

function ContentCard({ content }) {
  if (content.error) {
    return (
      <div className="error-box">
        Error al analizar contenido: {content.error}
      </div>
    )
  }

  return (
    <div className="card">
      <p className="card-label">Contenido</p>

      {content.streaming_profile && content.streaming_profile !== 'Unknown' && (
        <div className="profile-chip">⚡ {content.streaming_profile}</div>
      )}

      <div className="flags-row">
        <Flag label={`Vídeo${content.num_video_layers ? ` (${content.video_layers.length} capas)` : ''}`} on={content.has_video} />
        <Flag label="Audio"      on={content.has_audio}      />
        <Flag label="Subtítulos" on={content.has_subtitles}  />
        <Flag label="Thumbnails" on={content.has_thumbnails} />
        {content.is_multikey && <span className="flag flag--warn">⚠ Multikey</span>}
      </div>

      {content.video_layers?.length > 0 && (
        <>
          <p className="section-label">Perfiles de vídeo</p>
          <VideoTable layers={content.video_layers} />
        </>
      )}

      {content.audio_tracks?.length > 0 && (
        <>
          <p className="section-label">Audio</p>
          <AudioGrid tracks={content.audio_tracks} />
        </>
      )}
    </div>
  )
}

function Flag({ label, on }) {
  return (
    <span className={`flag ${on ? 'flag--on' : 'flag--off'}`}>
      {on ? '✓' : '✗'} {label}
    </span>
  )
}
