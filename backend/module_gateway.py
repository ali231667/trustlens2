# ============================================================
# TrustLens — Module Gateway
# ------------------------------------------------------------
# TrustLens is built as independent microservices, one per module.
# This gateway is the single place the main API talks to them.
#
# To add a module: run its service, then register its base URL below
# (or via an env var) and add a small helper that calls it. Every
# helper degrades gracefully — if a service is down, the scan still
# completes and that module is reported "unavailable" instead of
# crashing the whole request.
# ============================================================

import os
import requests

# ---- Service registry (override via .env / environment) ----
MODULE_SERVICES = {
    "ai_image_detector": os.getenv("IMAGE_SERVICE_URL", "http://127.0.0.1:8200"),
    "transcriber":       os.getenv("TRANSCRIBER_SERVICE_URL", "http://127.0.0.1:8300"),
    "misinfo":           os.getenv("MISINFO_SERVICE_URL", "http://127.0.0.1:8100"),
}


def _unavailable(module: str, err: str) -> dict:
    return {"module": module, "status": "unavailable", "error": err}


# ------------------------------------------------------------------ AI image
def analyze_profile_image(image_url: str, timeout: int = 45) -> dict:
    """Send a profile-picture URL to the AI-image-detector service."""
    if not image_url:
        return {"module": "ai_image_detector", "status": "skipped",
                "reason": "No profile picture URL available"}
    base = MODULE_SERVICES["ai_image_detector"]
    try:
        r = requests.post(f"{base}/api/v1/analyze-url",
                          json={"image_url": image_url}, timeout=timeout)
        if r.status_code != 200:
            return _unavailable("ai_image_detector", f"HTTP {r.status_code}: {r.text[:200]}")
        return r.json()
    except requests.RequestException as e:
        return _unavailable("ai_image_detector", str(e))


# ------------------------------------------------------------------ transcriber
def transcribe_url(url: str, wait: bool = True, timeout: int = 600) -> dict:
    """Transcribe an Instagram/TikTok reel by URL (synchronous when wait=True)."""
    base = MODULE_SERVICES["transcriber"]
    try:
        r = requests.post(f"{base}/api/v1/transcribe/url",
                          json={"url": url, "wait": wait}, timeout=timeout)
        if r.status_code != 200:
            return _unavailable("transcriber", f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json()
    except requests.RequestException as e:
        return _unavailable("transcriber", str(e))


def transcribe_upload(filename: str, content: bytes, content_type: str,
                      wait: bool = True, timeout: int = 600) -> dict:
    """Forward an uploaded media file to the transcriber service."""
    base = MODULE_SERVICES["transcriber"]
    try:
        files = {"file": (filename, content, content_type or "application/octet-stream")}
        r = requests.post(f"{base}/api/v1/transcribe/upload",
                          files=files, data={"wait": str(wait).lower()}, timeout=timeout)
        if r.status_code != 200:
            return _unavailable("transcriber", f"HTTP {r.status_code}: {r.text[:300]}")
        return r.json()
    except requests.RequestException as e:
        return _unavailable("transcriber", str(e))


# ------------------------------------------------------------------ misinfo
def classify_text(text: str, timeout: int = 60) -> dict:
    """Classify a caption/transcript with the misinformation service."""
    if not text or not text.strip():
        return {"module": "misinfo", "status": "skipped", "reason": "No text to classify"}
    base = MODULE_SERVICES["misinfo"]
    try:
        r = requests.post(f"{base}/classify", json={"text": text}, timeout=timeout)
        if r.status_code != 200:
            return _unavailable("misinfo", f"HTTP {r.status_code}: {r.text[:200]}")
        return r.json()
    except requests.RequestException as e:
        return _unavailable("misinfo", str(e))


# ------------------------------------------------------------------ health
def services_health() -> dict:
    """Ping every registered module service so the UI can show what's live."""
    health = {}
    probes = {
        "ai_image_detector": "/api/v1/health",
        "transcriber":       "/api/v1/health",
        "misinfo":           "/health",
    }
    for name, base in MODULE_SERVICES.items():
        try:
            r = requests.get(f"{base}{probes[name]}", timeout=5)
            health[name] = {"url": base, "up": r.status_code == 200,
                            "detail": r.json() if r.status_code == 200 else r.status_code}
        except requests.RequestException as e:
            health[name] = {"url": base, "up": False, "error": str(e)}
    return health
