"""
FastAPI backend para el Analizador de Manifests.
Arrancar: uvicorn backend.main:app --reload  (desde la raíz del proyecto)
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, field_validator
from analyzer import analyze

app = FastAPI(title="Analizador de Manifests", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    url: str
    fetch_content: bool = True

    @field_validator("url")
    @classmethod
    def url_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("La URL no puede estar vacía")
        return v


@app.post("/api/analyze")
async def api_analyze(req: AnalyzeRequest):
    try:
        return analyze(req.url, fetch_content=req.fetch_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    return {"status": "ok"}
