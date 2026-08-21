"""
backend/main.py
───────────────
FastAPI application entry point.

Wires together:
  - CORS middleware
  - Health-check endpoint
  - Route inclusion from api/server.py (voice-RAG pipeline routes)
  - Startup/shutdown lifecycle (loads vector store, warms embeddings)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from backend.config import settings

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: warm the embedding model and open the Chroma collection."""
    log.info("startup", msg="Server starting up...")
    # warm_up() will be enabled in Step 3 once retriever is implemented.
    # from retrieval.retriever import warm_up
    # warm_up()
    log.info("startup", msg="Ready.")
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


# ── Import pipeline routes (added in later steps) ──────────────────
# from api.server import router as pipeline_router
# app.include_router(pipeline_router, prefix="/api/v1")
