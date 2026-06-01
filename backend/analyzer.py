"""
Lógica de análisis de manifests DASH (.mpd) y HLS (.m3u8).
"""

from urllib.parse import urlparse, parse_qs
import urllib.request
import ssl
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Optional


# ── URL classification ────────────────────────────────────────────────────────

def detect_manifest_type(url: str) -> str:
    """Devuelve 'mpd', 'hls' o 'unknown'."""
    u = url.lower().split("?")[0]
    if u.endswith(".mpd"):
        return "mpd"
    if u.endswith(".m3u8"):
        return "hls"
    return "unknown"


def detect_content_type(url: str) -> str:
    """
    Clasifica la URL según el tipo de contenido:
      CPVR        → contiene /nPVR/ (case-insensitive)
      L7D         → /live/ + begin= + end= + movieId=
      Start Over  → /live/ + begin= + end= (sin movieId=)
      Live        → /live/ sin begin= ni end=
      VOD         → sin /live/ ni /nPVR/
    """
    parsed = urlparse(url)
    path_lower = parsed.path.lower()
    params = {k.lower() for k in parse_qs(parsed.query)}

    if "/npvr/" in path_lower:
        return "CPVR"

    if "/live/" in path_lower:
        has_begin = "begin" in params
        has_end   = "end"   in params
        has_movie = "movieid" in params
        if has_begin and has_end and has_movie:
            return "L7D"
        if has_begin and has_end:
            return "Start Over"
        return "Live"

    return "VOD"


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class VideoLayer:
    bandwidth: int
    width: Optional[int]   = None
    height: Optional[int]  = None
    framerate: Optional[str] = None
    codec: Optional[str]   = None


@dataclass
class AudioTrack:
    codec: Optional[str]     = None
    channels: Optional[int]  = None
    is_atmos: bool           = False

    @property
    def type(self) -> str:
        if self.is_atmos:
            return "Dolby Atmos"
        if self.codec in ("ec-3", "ac-3"):
            return "Dolby Digital"
        return "AAC"


@dataclass
class ManifestContent:
    has_video: bool      = False
    has_audio: bool      = False
    has_subtitles: bool  = False
    has_thumbnails: bool = False
    is_multikey: bool    = False

    video_layers: list[VideoLayer] = field(default_factory=list)
    audio_tracks: list[AudioTrack] = field(default_factory=list)
    streaming_profile: str         = "Unknown"
    error: Optional[str]           = None


# ── Streaming profiles ────────────────────────────────────────────────────────
# Cada perfil es un set de (height, fps) que lo define.

_PROFILES: list[tuple[str, set]] = [
    ("Sport Premium LATAM",    {(1080, 59.94), (720, 59.94), (720, 29.97), (576, 29.97), (432, 29.97), (270, 29.97)}),
    ("Sport Simplified LATAM", {(720, 59.94), (720, 29.97), (576, 29.97), (432, 29.97), (270, 29.97)}),
    ("Cinema LATAM",           {(1080, 29.97), (720, 29.97), (576, 29.97), (432, 29.97), (270, 29.97)}),
    ("SD LATAM",               {(720, 29.97), (576, 29.97), (432, 29.97), (270, 29.97)}),
    ("Germany HD-E3",          {(1080, 50.0), (720, 25.0), (540, 25.0), (360, 25.0)}),
    ("Germany HD-E2",          {(1080, 25.0), (720, 25.0), (540, 25.0), (360, 25.0)}),
    ("Germany HD-E1",          {(720, 50.0), (720, 25.0), (540, 25.0), (360, 25.0)}),
]


def _match_profile(layers: list[VideoLayer]) -> str:
    candidates: set[tuple[int, float]] = set()
    for layer in layers:
        if layer.height and layer.framerate:
            try:
                fps = float(layer.framerate)
                candidates.add((layer.height, fps))
            except ValueError:
                pass

    if not candidates:
        return "Unknown"

    best_name, best_score = "Unknown", 0
    for name, profile_set in _PROFILES:
        score = len(candidates & profile_set)
        if score > best_score:
            best_score, best_name = score, name
    return best_name


# ── MPD parsing ───────────────────────────────────────────────────────────────

_NS = "{urn:mpeg:dash:schema:mpd:2011}"  # namespace habitual


def _tag(local: str) -> str:
    return _NS + local


def _find_all(elem, local: str):
    """Busca con namespace MPEG-DASH; si no encuentra, intenta sin namespace."""
    result = elem.findall(".//" + _tag(local))
    if not result:
        result = elem.findall(".//" + local)
    return result


def _find_direct(elem, local: str):
    result = elem.findall(_tag(local))
    if not result:
        result = elem.findall(local)
    return result


def _attr(elem, *names: str) -> Optional[str]:
    """Devuelve el primer atributo que exista."""
    for name in names:
        v = elem.get(name)
        if v is not None:
            return v
    return None


def _parse_framerate(raw: Optional[str]) -> Optional[str]:
    """
    Acepta '25', '30000/1001' (→ 29.97), '50', etc.
    Devuelve None para valores inválidos.
    """
    if not raw:
        return None
    raw = raw.strip()
    if "/" in raw:
        parts = raw.split("/")
        if len(parts) == 2:
            try:
                num, den = float(parts[0]), float(parts[1])
                if den == 0:
                    return None
                return str(round(num / den, 2))
            except ValueError:
                return None
    try:
        float(raw)
        return raw
    except ValueError:
        return None


def _is_trick_mode(adaptation) -> bool:
    """
    Detecta AdaptationSets de trick play (iframes para seeking visual).
    Señales: EssentialProperty trickmode (DASH-IF) o atributo maxPlayoutRate.
    """
    for ep in _find_all(adaptation, "EssentialProperty"):
        scheme = (ep.get("schemeIdUri") or "").lower()
        if "trickmode" in scheme:
            return True
    # maxPlayoutRate indica que el track está diseñado para reproducción acelerada
    if adaptation.get("maxPlayoutRate"):
        return True
    return False


def _parse_video_adaptation(adaptation) -> list[VideoLayer]:
    layers = []

    # Framerate a nivel de AdaptationSet (puede ser heredado por las Representations)
    as_framerate = _parse_framerate(_attr(adaptation, "frameRate", "FrameRate"))

    for rep in _find_direct(adaptation, "Representation"):
        bandwidth = int(_attr(rep, "bandwidth", "Bandwidth") or 0)
        width  = int(_attr(rep, "width",  "Width")  or 0) or None
        height = int(_attr(rep, "height", "Height") or 0) or None
        codec  = _attr(rep, "codecs", "Codecs")
        fps    = _parse_framerate(_attr(rep, "frameRate", "FrameRate")) or as_framerate

        if bandwidth:
            layers.append(VideoLayer(bandwidth=bandwidth, width=width,
                                     height=height, framerate=fps, codec=codec))
    return layers


def _parse_channel_config(elem) -> Optional[int]:
    """
    Extrae número de canales de AudioChannelConfiguration.
    Soporta el esquema MPEG estándar (valor numérico simple) y el esquema
    Dolby (tag:dolby.com,...) cuyo valor es un bitmask hexadecimal:
      bit 15=L, 14=C, 13=R, 12=Ls, 11=Rs, 10=Cs, 9=LFE, ... (AC-3 acmod)
    Mapeamos los valores más comunes directamente.
    """
    scheme = (elem.get("schemeIdUri") or "").lower()
    val = (elem.get("value") or "").strip()

    # Esquema MPEG estándar — valor es un entero simple
    if "23003:3" in scheme or "mpeg" in scheme:
        try:
            return int(val)
        except ValueError:
            return None

    # Esquema Dolby — valor es un bitmask hex de 4 caracteres (p.ej. "A000", "F801")
    if "dolby" in scheme or "tag:" in scheme:
        _DOLBY_CH = {
            "A000": 6,   # 5.1
            "F801": 6,   # 5.1
            "2000": 2,   # Stereo
            "4000": 1,   # Mono
            "E000": 8,   # 7.1
        }
        if val.upper() in _DOLBY_CH:
            return _DOLBY_CH[val.upper()]
        # Fallback: contar bits activos en los primeros 4 bits del bitmask
        try:
            bits = int(val, 16)
            count = bin(bits >> 12).count("1")  # 4 bits más significativos = canales principales
            return count if count > 0 else None
        except ValueError:
            return None

    # Fallback genérico: intentar leer como entero
    try:
        return int(val)
    except ValueError:
        return None


def _parse_audio_adaptation(adaptation) -> AudioTrack:
    # Detectar Atmos: SupplementalProperty con value="JOC"
    is_atmos = False
    for sp in _find_all(adaptation, "SupplementalProperty"):
        if "JOC" in (sp.get("value") or ""):
            is_atmos = True
        scheme = sp.get("schemeIdUri") or ""
        if "ec3" in scheme.lower() and "complexity" in scheme.lower():
            is_atmos = True

    # Codec desde la primera Representation
    codec = None
    channels = None
    for rep in _find_direct(adaptation, "Representation"):
        if not codec:
            raw_codec = _attr(rep, "codecs", "Codecs") or ""
            # Normalizar: mp4a.40.2 → mp4a.40.2 | ec-3 → ec-3 | ac-3 → ac-3
            if "ec-3" in raw_codec or "ec3" in raw_codec:
                codec = "ec-3"
            elif "ac-3" in raw_codec or "ac3" in raw_codec:
                codec = "ac-3"
            elif "mp4a" in raw_codec:
                codec = raw_codec.split(",")[0].strip()

        # Canales desde AudioChannelConfiguration
        for acc in _find_all(rep, "AudioChannelConfiguration"):
            ch = _parse_channel_config(acc)
            if ch:
                channels = ch
                break

        if not channels:
            for acc in _find_all(adaptation, "AudioChannelConfiguration"):
                ch = _parse_channel_config(acc)
                if ch:
                    channels = ch
                    break

    return AudioTrack(codec=codec, channels=channels, is_atmos=is_atmos)


def parse_mpd(xml_text: str) -> ManifestContent:
    content = ManifestContent()
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        content.error = f"XML inválido: {e}"
        return content

    video_adaptation_count = 0

    for adaptation in _find_all(root, "AdaptationSet"):
        content_type = (
            _attr(adaptation, "contentType", "mimeType") or ""
        ).lower()

        # Inferir por mimeType si contentType no está explícito
        if not content_type or content_type == "":
            mime = _attr(adaptation, "mimeType") or ""
            if "video" in mime:
                content_type = "video"
            elif "audio" in mime:
                content_type = "audio"
            elif "text" in mime:
                content_type = "text"
            elif "image" in mime:
                content_type = "image"

        if "video" in content_type:
            if _is_trick_mode(adaptation):
                content.has_thumbnails = True
                continue
            video_adaptation_count += 1
            layers = _parse_video_adaptation(adaptation)
            content.video_layers.extend(layers)
            if layers:
                content.has_video = True

        elif "audio" in content_type:
            track = _parse_audio_adaptation(adaptation)
            content.audio_tracks.append(track)
            content.has_audio = True

        elif "text" in content_type:
            content.has_subtitles = True

        elif "image" in content_type:
            content.has_thumbnails = True

    content.is_multikey = video_adaptation_count > 1
    content.streaming_profile = _match_profile(content.video_layers)
    return content


# ── Download ──────────────────────────────────────────────────────────────────

def download_manifest(url: str, timeout: int = 15) -> str:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (manifest-analyzer/2.0)"},
    )
    with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


# ── Public API ────────────────────────────────────────────────────────────────

def analyze(url: str, fetch_content: bool = True) -> dict:
    manifest_type  = detect_manifest_type(url)
    content_type   = detect_content_type(url)
    confidence     = 0.95 if content_type != "Unknown" else 0.3

    result: dict = {
        "url":           url,
        "manifest_type": manifest_type,
        "content_type":  content_type,
        "confidence":    confidence,
        "content":       None,
    }

    if not fetch_content or manifest_type != "mpd":
        return result

    # Download + parse
    content = ManifestContent()
    try:
        xml_text = download_manifest(url)
        content  = parse_mpd(xml_text)
    except Exception as e:
        content.error = str(e)

    result["content"] = {
        "has_video":          content.has_video,
        "has_audio":          content.has_audio,
        "has_subtitles":      content.has_subtitles,
        "has_thumbnails":     content.has_thumbnails,
        "is_multikey":        content.is_multikey,
        "streaming_profile":  content.streaming_profile,
        "video_layers": [
            {
                "bandwidth": v.bandwidth,
                "width":     v.width,
                "height":    v.height,
                "framerate": v.framerate,
                "codec":     v.codec,
            }
            for v in sorted(content.video_layers, key=lambda v: v.bandwidth, reverse=True)
        ],
        "audio_tracks": [
            {
                "type":     a.type,
                "codec":    a.codec,
                "channels": a.channels,
                "is_atmos": a.is_atmos,
            }
            for a in content.audio_tracks
        ],
        "error": content.error,
    }
    return result
