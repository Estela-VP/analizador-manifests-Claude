# Analizador de Manifests

Herramienta web para analizar manifests de streaming **DASH (.mpd)** y **HLS (.m3u8)**.

Dado una URL de manifest, muestra:

- Tipo de manifest (DASH / HLS) y tipo de contenido (Live, VOD, CPVR, L7D, Start Over)
- Perfil de streaming detectado (Cinema LATAM, Sport Premium, Germany HD, etc.)
- Capas de vídeo: resolución, bitrate, FPS y codec
- Pistas de audio: formato (AAC, Dolby Digital, Dolby Atmos) y canales
- Presencia de subtítulos, thumbnails y multikey

## Requisitos

- Python 3.10+
- Node.js 18+

## Instalación y arranque

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --port 8001 --reload
```

El backend queda escuchando en `http://localhost:8001`.

### 2. Frontend

```bash
cd frontend
npm install        # solo la primera vez
npm run dev
```

Abre el navegador en `http://localhost:5173`.

## Estructura del proyecto

```
├── backend/
│   ├── main.py          # API FastAPI (POST /api/analyze)
│   ├── analyzer.py      # Lógica de análisis DASH y HLS
│   └── requirements.txt
└── frontend/
    ├── src/
    │   ├── App.jsx
    │   └── components/
    │       ├── UrlForm.jsx      # Input de URL
    │       ├── ResultPanel.jsx  # Panel de resultados
    │       ├── VideoTable.jsx   # Tabla de perfiles de vídeo
    │       └── AudioGrid.jsx    # Cards de pistas de audio
    └── vite.config.js
```

## API

```
POST /api/analyze
Content-Type: application/json

{ "url": "https://...", "fetch_content": true }
```

`fetch_content: false` devuelve solo la clasificación de la URL sin descargar el manifest.
