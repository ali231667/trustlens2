# TrustLens — Integration Guide

How this app is put together, how to run it, and **how to add a new module**.

TrustLens is built as a set of **independent microservices** behind a single
**API gateway**. Each module (fake-follower, engagement, AI image, transcriber,
misinformation, …) is its own small service. The gateway calls them, merges the
results, and the React frontend shows them. You can develop and run your module
completely on its own, then register it with one line.

---

## Architecture

```
                 React frontend (Vite, :5173)
                          |
                          v
              API Gateway  (backend/main.py, :8000)
        POST /analyze-live   POST /transcribe/*   GET /services/health
                          |
        +-----------------+---------------------+--------------------+
        v                 v                     v                    v
  fake-follower &    AI image detector    transcriber          misinformation
  engagement         (:8200)              (:8300)              (:8100)
  (in-process)       own service          own service          own service
```

- The gateway holds a **service registry** in `backend/module_gateway.py`
  (`MODULE_SERVICES`). Each entry is `name -> base_url`, overridable via `.env`.
- Every module helper **degrades gracefully**: if a service is down, the scan
  still completes and that module is reported `unavailable` instead of crashing.

### Port map

| Service | Port | Lives in |
|---|---|---|
| Frontend (Vite) | 5173 | `frontend/` |
| API gateway | 8000 | `backend/` |
| Misinformation classifier | 8100 | `trustlens_misinfo_classifier2/` |
| AI image detector | 8200 | its own repo/service |
| Transcriber | 8300 | its own repo/service |

---

## Running it locally

Each Python service uses **its own virtual environment**. Python **3.13** is
recommended (some ML deps have no 3.14 wheels yet).

**1. Gateway (backend)**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install fastapi uvicorn requests python-dotenv scikit-learn==1.7.2 numpy python-multipart
copy .env.example .env        # then paste your RapidAPI key
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**2. Frontend**
```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173
```

**3. Module services** — start each one on its port (see that module's README).
The gateway finds them through the URLs in `.env`. Any module that isn't running
simply shows as `unavailable` in the results; the rest keep working.

---

## The module contract

A module is just an HTTP service. Keep it small and predictable:

- `GET  /api/v1/health` → `{ "status": "ok", "module": "<name>", ... }`
- One analyze endpoint that returns a **normalized** shape the gateway can merge:

```json
{
  "module":    "your_module",
  "status":    "ok",
  "score":     0-100,          // your module's headline number (or null)
  "verdict":   "human-readable",
  "details":   { ...anything your module wants to expose... }
}
```

`score` is whatever your module measures on a 0–100 scale (risk, authenticity,
confidence…). Put everything else under `details`. Return `status: "ok"` when you
produced a result; the gateway handles the `unavailable` case for you.

---

## Adding a new module (the whole checklist)

Say you're adding a **caption sentiment** module.

**1. Build it as a service** in its own folder/repo. Expose `GET /api/v1/health`
and e.g. `POST /api/v1/analyze` returning the normalized shape above. Run it on a
free port (say **8400**).

**2. Register it** in `backend/module_gateway.py`:
```python
MODULE_SERVICES = {
    ...
    "sentiment": os.getenv("SENTIMENT_SERVICE_URL", "http://127.0.0.1:8400"),
}

def analyze_sentiment(text: str, timeout: int = 30) -> dict:
    base = MODULE_SERVICES["sentiment"]
    try:
        r = requests.post(f"{base}/api/v1/analyze", json={"text": text}, timeout=timeout)
        if r.status_code != 200:
            return _unavailable("sentiment", f"HTTP {r.status_code}: {r.text[:200]}")
        return r.json()
    except requests.RequestException as e:
        return _unavailable("sentiment", str(e))
```
Add its probe to `services_health()` too (one line), so it shows up on
`GET /services/health`.

**3. Call it** in `backend/main.py` — inside `/analyze-live` (to run on every
scan) or as its own endpoint. Add the result to the response dict, e.g.
`"sentiment_analysis": gateway.analyze_sentiment(text)`.

**4. Show it** in the frontend — add a card in `frontend/src/pages/Results.jsx`
that reads `result.sentiment_analysis`, or a new page under `frontend/src/pages/`
plus a route in `App.jsx` and a link in `components/Navbar.jsx`.

**5. Add the env line** to `backend/.env.example`
(`SENTIMENT_SERVICE_URL=http://127.0.0.1:8400`) so the next person knows about it.

That's it — no changes to anyone else's module.

### Worked example already in the repo: AI image detector

- Service: a thin FastAPI wrapper over the module's inference code, exposing
  `/api/v1/health` and `/api/v1/analyze-url`.
- Registered as `ai_image_detector` in `module_gateway.py`
  (`analyze_profile_image`).
- Called in `main.py` `/analyze-live`; its `image_risk` feeds `trust_score.py`
  (10% weight + a deepfake kill-switch).
- Shown as the **AI PROFILE IMAGE** card in `Results.jsx`.

Follow the same five steps and your module drops straight in.

---

## Notes

- **Secrets never get committed.** `backend/.env` (RapidAPI key) and any
  `cookies.txt` are gitignored. Share keys out-of-band, not in the repo.
- **Trust score** lives in `backend/trust_score.py`. It takes optional per-module
  inputs and is backward-compatible — add your module's weight there when you're
  ready to have it affect the final score.
- **The transcriber** exposes a `classifier_input` payload designed to feed the
  misinformation module directly — see its README.
