"""
backend/main.py
───────────────
FastAPI application entry point.

Wires together:
  - CORS middleware
  - Health-check endpoint (/health)
  - Pipeline routes from api/server.py (/ask-voice, /ask-text, /chunking/strategies, /stats)
  - Startup/shutdown lifecycle (loads vector store, warms embeddings)
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.server import router as pipeline_router
from backend.config import settings
from retrieval.retriever import warm_up

log = structlog.get_logger()


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
    title="Voice-RAG API",
    description="Voice-enabled Retrieval-Augmented Generation — HH Goa 2026 Task 2",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health():
    """Quick liveness probe — returns 200 if the server is up."""
    return {"status": "ok", "version": app.version}


# ── Include Pipeline Routes ──────────────────────────────────────────
app.include_router(pipeline_router)
