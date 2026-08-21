"""
api/server.py
──────────────
FastAPI router containing all Voice-RAG pipeline endpoints powered by PipelineOrchestrator.

Endpoints:
  POST /ask-voice (and /api/v1/query/voice)
    - Accepts: multipart/form-data with audio file (`audio` or `file`) + optional `strategy`, `lang`, `mock`
    - Runs: Input Validation → STT → Guardrails → Retrieval → BM25 Rerank → Context Validation → LLM → Grounding Check

  POST /ask-text (and /api/v1/query/text)
    - Accepts: JSON body { query, strategy, lang_filter, mock }
    - Runs text-mode RAG query through the orchestrator harness

  GET /chunking/strategies
    - Returns available chunking strategies

  GET /stats
    - Returns session latency statistics & configuration
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from backend.config import settings
from generation.harness import PipelineResult, default_orchestrator

log = structlog.get_logger()

router = APIRouter()


# ─── Pydantic Models ────────────────────────────────────────────────────────────

class TextQueryRequest(BaseModel):
    query: str = Field(..., description="User question or query text")
    strategy: Optional[str] = Field(None, description="Chunking strategy ('sentence', 'fixed', 'metadata')")
    lang_filter: Optional[str] = Field(None, description="Language filter ('en', 'hi', 'ta', etc.)")
    mock: Optional[bool] = Field(False, description="Run offline in mock mode without API keys")


class SourceItem(BaseModel):
    source_index: int
    doc_id: str
    chunk_id: str
    lang: str
    score: float
    snippet: str


class LatencyBreakdown(BaseModel):
    input_validation_ms: float = 0.0
    stt_ms: float = 0.0
    input_guardrail_ms: float = 0.0
    retrieval_ms: float = 0.0
    reranking_ms: float = 0.0
    context_validation_ms: float = 0.0
    generation_ms: float = 0.0
    grounding_check_ms: float = 0.0
    search_pipeline_ms: float = 0.0     # Vector retrieve + rerank (<200ms target)
    total_ms: float = 0.0               # Total end-to-end latency


class PipelineResponse(BaseModel):
    status: str = "success"             # "success" | "refusal" | "error"
    transcript: Optional[str] = None    # Transcribed text from audio (or input query)
    language_detected: Optional[str] = None
    answer: str
    grounded: bool = True               # True if answer passed grounding check
    confidence: float = 1.0
    guardrail_passed: bool = True
    guardrail_reason: Optional[str] = None
    model: str = ""
    sources: List[SourceItem] = []
    latency: LatencyBreakdown = Field(default_factory=LatencyBreakdown)
    error: Optional[str] = None
    mock: bool = False


def _to_pipeline_response(result: PipelineResult) -> PipelineResponse:
    """Convert internal PipelineResult to API response model."""
    lat_dict = result.latency.to_dict()
    sources = [
        SourceItem(
            source_index=s.chunk_index,
            doc_id=s.doc_id,
            chunk_id=s.chunk_id,
            lang=s.lang,
            score=s.score,
            snippet=s.snippet,
        )
        for s in result.sources
    ]

    return PipelineResponse(
        status=result.status,
        transcript=result.transcript,
        language_detected=result.language_detected,
        answer=result.answer,
        grounded=result.grounded,
        confidence=result.confidence,
        guardrail_passed=result.guardrail_passed,
        guardrail_reason=result.guardrail_reason,
        model=result.model,
        sources=sources,
        latency=LatencyBreakdown(**lat_dict),
        error=result.error_message,
        mock=result.mock,
    )


# ─── Endpoint: POST /ask-voice (and aliases) ──────────────────────────────────

@router.post("/ask-voice", response_model=PipelineResponse, tags=["voice-pipeline"])
@router.post("/query/voice", response_model=PipelineResponse, tags=["voice-pipeline"])
@router.post("/api/v1/query/voice", response_model=PipelineResponse, tags=["voice-pipeline"])
async def ask_voice(
    file: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
    strategy: Optional[str] = Form(None),
    lang: Optional[str] = Form(None),
    mock: Optional[bool] = Form(False),
) -> PipelineResponse:
    """
    Voice-mode RAG query:
    1. Validates audio input
    2. Transcribes audio via Sarvam AI STT
    3. Evaluates input guardrails
    4. Retrieves top candidates from ChromaDB
    5. Reranks with BM25+RRF
    6. Validates context relevance (short-circuit on low score)
    7. Generates grounded answer with Claude / LLM
    8. Performs post-generation grounding check
    """
    upload = file or audio
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing audio file. Upload an audio file under multipart form field 'audio' or 'file'.",
        )

    try:
        audio_bytes = await upload.read()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read audio file: {str(e)}",
        )

    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file payload is empty.",
        )

    content_type = upload.content_type or "audio/wav"
    result = await default_orchestrator.execute_voice(
        audio_bytes=audio_bytes,
        content_type=content_type,
        strategy=strategy,
        lang_filter=lang,
        mock_mode=bool(mock),
    )

    if result.status == "error" and not result.guardrail_passed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error_message or result.answer,
        )

    return _to_pipeline_response(result)


# ─── Endpoint: POST /ask-text (and aliases) ───────────────────────────────────

@router.post("/ask-text", response_model=PipelineResponse, tags=["text-pipeline"])
@router.post("/query/text", response_model=PipelineResponse, tags=["text-pipeline"])
@router.post("/api/v1/query/text", response_model=PipelineResponse, tags=["text-pipeline"])
async def ask_text(req: TextQueryRequest) -> PipelineResponse:
    """
    Text-mode RAG query:
    Executes the multi-stage pipeline harness starting from query text.
    """
    cleaned_query = (req.query or "").strip()
    if not cleaned_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query string cannot be empty.",
        )

    result = await default_orchestrator.execute_text(
        query=cleaned_query,
        strategy=req.strategy,
        lang_filter=req.lang_filter,
        mock_mode=bool(req.mock),
    )

    return _to_pipeline_response(result)


# ─── Endpoint: GET /chunking/strategies ────────────────────────────────────────

@router.get("/chunking/strategies", tags=["config"])
@router.get("/api/v1/chunking/strategies", tags=["config"])
async def get_strategies() -> Dict[str, Any]:
    """Return list of available chunking strategies and active default."""
    return {
        "available": ["fixed", "sentence", "metadata"],
        "current": settings.CHUNKING_STRATEGY,
    }


# ─── Endpoint: GET /stats ──────────────────────────────────────────────────────

@router.get("/stats", tags=["observability"])
@router.get("/api/v1/stats", tags=["observability"])
async def get_stats() -> Dict[str, Any]:
    """Return pipeline configuration and target metrics."""
    return {
        "pipeline_target_latency_ms": 200.0,
        "stt_provider": "Sarvam AI (saaras:v3)",
        "embedding_model": settings.EMBEDDING_MODEL,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "top_k_retrieve": settings.TOP_K_RETRIEVE,
        "top_k_final": settings.TOP_K_FINAL,
        "guardrails_enabled": True,
    }
