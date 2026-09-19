"""
TrustLens Module 6.7 — AI-Generated Profile Image Detector · HTTP service wrapper.

This is a thin FastAPI layer over image_predict_core. It does NOT change any
inference logic: it loads the trained probe + CLIP once, and calls the same
analyze_image() the Streamlit app uses, so results are byte-identical.

Run (from this folder, using this module's own venv):
    .venv\\Scripts\\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8200

Endpoints (kept under /api/v1 to match the other TrustLens services):
    GET  /api/v1/health           readiness + which face backend is active
    POST /api/v1/analyze-url      { "image_url": "https://..." }  -> verdict
    POST /api/v1/analyze-upload   multipart file field "file"      -> verdict
"""
from __future__ import annotations

import io
import urllib.request

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel

import image_predict_core as core

app = FastAPI(title="TrustLens AI Image Detector", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Loaded once at startup and reused for every request.
_STATE: dict = {"probe": None, "scaler": None, "meta": None, "visual": None, "preprocess": None}

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def _ensure_loaded() -> None:
    if _STATE["probe"] is None:
        probe, scaler, meta = core.load_probe()
        visual, preprocess = core.load_clip()
        _STATE.update(probe=probe, scaler=scaler, meta=meta, visual=visual, preprocess=preprocess)


@app.on_event("startup")
def _startup() -> None:
    # Warm the model so the first real request is fast. If weights need to be
    # fetched this runs once; afterwards it is instant.
    _ensure_loaded()


class UrlRequest(BaseModel):
    image_url: str


def _to_contract(verdict: core.ImageVerdict) -> dict:
    """Normalise the module's native ImageVerdict into the shared TrustLens
    module-response shape the gateway consumes, keeping the full detail payload."""
    d = verdict.to_dict()
    return {
        "module": "ai_image_detector",
        "status": "ok",
        # image_risk is 0-100, or None when the picture is not a scorable face.
        "score": d.get("image_risk"),
        "verdict": d.get("verdict"),
        "band": d.get("band"),
        "applicable": d.get("band") not in (None, "not_applicable"),
        "details": d,
    }


def _analyze(img: Image.Image) -> dict:
    _ensure_loaded()
    verdict = core.analyze_image(
        img, _STATE["probe"], _STATE["scaler"], _STATE["visual"], _STATE["preprocess"]
    )
    return _to_contract(verdict)


@app.get("/api/v1/health")
def health() -> dict:
    return {
        "status": "ok",
        "module": "ai_image_detector",
        "version": "1.0.0",
        "model_loaded": _STATE["probe"] is not None,
        "face_backend": core.face_backend(),
    }


@app.post("/api/v1/analyze-url")
def analyze_url(req: UrlRequest) -> dict:
    if not req.image_url or not req.image_url.strip():
        raise HTTPException(status_code=400, detail="image_url is required")
    try:
        request = urllib.request.Request(req.image_url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(request, timeout=20) as resp:
            data = resp.read()
        img = Image.open(io.BytesIO(data))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Could not fetch/open image: {e}")
    return _analyze(img)


@app.post("/api/v1/analyze-upload")
async def analyze_upload(file: UploadFile = File(...)) -> dict:
    try:
        data = await file.read()
        img = Image.open(io.BytesIO(data))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read uploaded image: {e}")
    return _analyze(img)
