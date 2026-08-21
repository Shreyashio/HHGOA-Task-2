"""
api/server.py
──────────────
FastAPI router containing all pipeline endpoints.

What this will do (Step 5):

Endpoints:
  POST /api/v1/query/voice
    - Accepts: multipart/form-data with `audio` file + optional `strategy` field
    - Runs: STT → guardrail_input → retrieve → rerank → generate → guardrail_output
    - Returns: PipelineResponse (answer, latency breakdown, chunks used, guardrail status)

  POST /api/v1/query/text
    - Same as above but accepts `{ "query": "..." }` JSON (skips STT step)
    - Used by the frontend for text-mode testing

  GET /api/v1/chunking/strategies
    - Returns the list of available chunking strategies and current active one

  GET /api/v1/stats
    - Returns aggregate latency stats (P50/P70/P100) from the current session's
      LatencyTracker instance

Harness:
  - All endpoint handlers use `tenacity` for external call retries
  - Input/output are typed Pydantic models — no raw dicts flowing through
  - Structured error responses (never raw Python exceptions to the client)
"""

from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional


router = APIRouter()


class TextQueryRequest(BaseModel):
    query: str
    strategy: Optional[str] = None   # override chunking strategy for this query
    lang_filter: Optional[str] = None


class ChunkInfo(BaseModel):
    chunk_id: str
    text: str
    score: float


class LatencyBreakdown(BaseModel):
    stt_ms: float = 0.0
    retrieval_ms: float = 0.0
    reranking_ms: float = 0.0
    generation_ms: float = 0.0
    pipeline_ms: float = 0.0          # retrieval + reranking (the sub-200ms target)
    total_ms: float = 0.0             # everything including STT + LLM


class PipelineResponse(BaseModel):
    answer: Optional[str]
    guardrail_passed: bool
    guardrail_reason: Optional[str] = None
    chunks_used: List[ChunkInfo] = []
    latency: LatencyBreakdown = LatencyBreakdown()
    model: str = ""


@router.post("/query/text", response_model=PipelineResponse, tags=["pipeline"])
async def query_text(req: TextQueryRequest) -> PipelineResponse:
    """Text-mode RAG query — skip STT, run retrieval → generation."""
    raise NotImplementedError("Implemented in Step 5")


@router.post("/query/voice", response_model=PipelineResponse, tags=["pipeline"])
async def query_voice() -> PipelineResponse:
    """Voice-mode RAG query — STT → retrieval → generation."""
    raise NotImplementedError("Implemented in Step 5")


@router.get("/chunking/strategies", tags=["config"])
async def get_strategies():
    """Return available chunking strategies."""
    return {
        "available": ["fixed", "sentence", "metadata"],
        "current": "sentence",   # will read from settings in Step 3
    }


@router.get("/stats", tags=["observability"])
async def get_stats():
    """Return per-session latency percentiles."""
    return {"message": "Implemented in Step 6"}
