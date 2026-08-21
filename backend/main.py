"""
backend/main.py
───────────────
FastAPI application entry point.

Wires together:
  - CORS middleware
  - Health-check endpoint (/health)
  - Pipeline routes from api/server.py (/ask-voice, /ask-text, /chunking/strategies, /stats)
  - Static files & SPA serving for React frontend (MATRUBHASHA)
  - Startup/shutdown lifecycle (loads vector store, warms embeddings)

Access the app at http://127.0.0.1:8000 after starting.
"""

import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure voice-rag root is in sys.path regardless of execution directory
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Ensure Windows stdout/stderr handles Marathi & Indic Unicode
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from api.server import router as pipeline_router
from backend.config import settings
from retrieval.retriever import warm_up

log = structlog.get_logger()

_DIST_DIR = _ROOT / "frontend" / "dist"
_INDEX_HTML = _DIST_DIR / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: warm the embedding model and open the Chroma collection."""
    log.info("startup", msg="Server starting up...")
    try:
        warm_up()
        log.info("startup", msg="Retriever and embedding model ready.")
    except Exception as e:
        log.warning("startup.warmup_deferred", error=str(e))
    yield
    log.info("shutdown", msg="Cleaning up resources.")


app = FastAPI(
    title="Voice-RAG API (MATRUBHASHA)",
    description="Voice-enabled Retrieval-Augmented Generation — HH Goa 2026 Task 2",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — accept all dev origins
cors_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
async def health():
    """Quick liveness probe — returns 200 if the server is up."""
    return {"status": "ok", "version": app.version}


# ── Pipeline Routes ───────────────────────────────────────────────────────────
app.include_router(pipeline_router)


# ── SPA Static File Serving ───────────────────────────────────────────────────
# Mount /assets separately for proper MIME type handling
if _DIST_DIR.exists():
    _assets_dir = _DIST_DIR / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="ui-assets")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def serve_root():
        if _INDEX_HTML.exists():
            return HTMLResponse(content=_INDEX_HTML.read_bytes().decode("utf-8"))
        return HTMLResponse("<h1>Frontend not built. Run: npm run build</h1>", status_code=503)

    @app.get("/{full_path:path}", response_class=HTMLResponse, include_in_schema=False)
    async def serve_spa(full_path: str):
        # Try exact file match first
        candidate = _DIST_DIR / full_path
        if candidate.is_file():
            return FileResponse(str(candidate))
        # SPA fallback — always return index.html for client-side routes
        if _INDEX_HTML.exists():
            return HTMLResponse(content=_INDEX_HTML.read_bytes().decode("utf-8"))
        return HTMLResponse("<h1>Frontend not built. Run: npm run build</h1>", status_code=503)
else:
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def serve_root_missing():
        return HTMLResponse(
            "<h3>Frontend dist not found. Run <code>npm run build</code> inside "
            "<code>frontend/</code> then restart the server.</h3>",
            status_code=503,
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=False,  # reload=False for stable static file serving
    )
