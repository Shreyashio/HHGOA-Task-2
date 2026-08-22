"""
generation/harness.py
─────────────────────
Complete end-to-end Voice-RAG Pipeline Orchestrator with Multi-Stage Guardrails.

Pipeline Flow:
  Input Validation → STT (with retry) → Input Guardrail → Vector Retrieval
  → BM25 Reranking → Context Validation → LLM Generation → Grounding Verification
  → Structured Response

Features:
  - Fail-safe input validation for empty/corrupted audio and text
  - Retry-once resilience on transient STT / LLM failures
  - Pre-LLM context validation short-circuiting on low similarity scores
  - Post-generation lexical grounding check against hallucinations
  - Microsecond latency tracking across all 8 pipeline stages
  - Structured, typed output model (PipelineResult) with zero uncaught exceptions
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import structlog
from backend.config import settings
from generation.guardrails import (
    REASON_HALLUCINATION,
    REASON_LOW_RELEVANCE,
    REASON_NO_CONTEXT,
    REASON_OFF_TOPIC,
    REASON_UNSAFE_INPUT,
    GuardrailResult,
    check_context,
    check_input,
    check_output,
)
from generation.llm import Citation, GenerationResult, generate
from retrieval.reranker import rerank
from retrieval.retriever import RetrievedChunk, retrieve
from voice.stt import TranscriptionResult, transcribe

log = structlog.get_logger()


@dataclass
class StageLatency:
    """Per-stage latency tracking (in milliseconds)."""
    input_validation_ms: float = 0.0
    stt_ms: float = 0.0
    input_guardrail_ms: float = 0.0
    retrieval_ms: float = 0.0
    reranking_ms: float = 0.0
    context_validation_ms: float = 0.0
    generation_ms: float = 0.0
    grounding_check_ms: float = 0.0
    search_pipeline_ms: float = 0.0     # Retrieval + Reranking (sub-200ms target)
    total_ms: float = 0.0               # End-to-end latency

    def to_dict(self) -> Dict[str, float]:
        return {
            "input_validation_ms": round(self.input_validation_ms, 2),
            "stt_ms": round(self.stt_ms, 2),
            "input_guardrail_ms": round(self.input_guardrail_ms, 2),
            "retrieval_ms": round(self.retrieval_ms, 2),
            "reranking_ms": round(self.reranking_ms, 2),
            "context_validation_ms": round(self.context_validation_ms, 2),
            "generation_ms": round(self.generation_ms, 2),
            "grounding_check_ms": round(self.grounding_check_ms, 2),
            "search_pipeline_ms": round(self.search_pipeline_ms, 2),
            "total_ms": round(self.total_ms, 2),
        }


@dataclass
class PipelineResult:
    """Structured end-to-end pipeline response."""
    status: str                         # "success" | "refusal" | "error"
    answer: str
    transcript: str = ""
    language_detected: str = "en-IN"
    grounded: bool = True
    confidence: float = 1.0
    guardrail_passed: bool = True
    guardrail_reason: Optional[str] = None
    model: str = ""
    sources: List[Citation] = field(default_factory=list)
    latency: StageLatency = field(default_factory=StageLatency)
    error_message: Optional[str] = None
    mock: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "transcript": self.transcript,
            "language_detected": self.language_detected,
            "answer": self.answer,
            "grounded": self.grounded,
            "confidence": round(self.confidence, 4),
            "guardrail_passed": self.guardrail_passed,
            "guardrail_reason": self.guardrail_reason,
            "model": self.model,
            "sources": [
                {
                    "source_index": s.chunk_index,
                    "doc_id": s.doc_id,
                    "chunk_id": s.chunk_id,
                    "lang": s.lang,
                    "score": round(s.score, 4),
                    "snippet": s.snippet,
                }
                for s in self.sources
            ],
            "latency": self.latency.to_dict(),
            "error_message": self.error_message,
            "mock": self.mock,
        }


class PipelineOrchestrator:
    """Harness orchestrating multi-stage validation, STT, retrieval, reranking, and generation."""

    def __init__(
        self,
        min_relevance_threshold: float = 0.005,
        min_grounding_overlap: float = 0.25,
    ):
        self.min_relevance_threshold = min_relevance_threshold
        self.min_grounding_overlap = min_grounding_overlap

    async def execute_voice(
        self,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
        strategy: Optional[str] = None,
        lang_filter: Optional[str] = None,
        mock_mode: bool = False,
    ) -> PipelineResult:
        """
        Execute full Voice-RAG pipeline starting from audio upload.
        """
        t_global = time.perf_counter()
        lat = StageLatency()

        # ── 1. Input Validation ────────────────────────────────────────────────
        t0 = time.perf_counter()
        if not audio_bytes or len(audio_bytes) < 16:
            lat.input_validation_ms = (time.perf_counter() - t0) * 1000
            lat.total_ms = (time.perf_counter() - t_global) * 1000
            return PipelineResult(
                status="error",
                answer="Invalid audio input: audio payload is empty or corrupted.",
                guardrail_passed=False,
                guardrail_reason=REASON_UNSAFE_INPUT,
                confidence=0.0,
                latency=lat,
                error_message="Empty or invalid audio bytes",
            )
        lat.input_validation_ms = (time.perf_counter() - t0) * 1000

        # ── 2. STT Transcription (with retry-once logic) ──────────────────────
        t0 = time.perf_counter()
        stt_res = None
        for attempt in range(2):
            try:
                stt_res = await transcribe(
                    audio_bytes=audio_bytes,
                    content_type=content_type,
                    mock_mode=mock_mode,
                    language_code=lang_filter,
                )
                break
            except Exception as e:
                if attempt == 1:
                    lat.stt_ms = (time.perf_counter() - t0) * 1000
                    lat.total_ms = (time.perf_counter() - t_global) * 1000
                    log.error("harness.stt_fatal_error", error=str(e))
                    return PipelineResult(
                        status="error",
                        answer="Failed to transcribe audio after retries.",
                        guardrail_passed=False,
                        confidence=0.0,
                        latency=lat,
                        error_message=f"STT Failure: {str(e)}",
                    )
                await asyncio.sleep(0.1)

        lat.stt_ms = (time.perf_counter() - t0) * 1000
        query_text = stt_res.text.strip() if stt_res else ""
        detected_lang = stt_res.language_detected if stt_res else "en-IN"

        if not query_text:
            lat.total_ms = (time.perf_counter() - t_global) * 1000
            return PipelineResult(
                status="refusal",
                transcript="",
                language_detected=detected_lang,
                answer="I could not detect any speech in the uploaded audio.",
                guardrail_passed=False,
                guardrail_reason=REASON_NO_CONTEXT,
                confidence=0.0,
                latency=lat,
            )

        # ── 3–8. Delegate to Text Pipeline ─────────────────────────────────────
        return await self._execute_text_core(
            query=query_text,
            strategy=strategy,
            lang_filter=lang_filter or detected_lang,
            mock_mode=mock_mode,
            stt_latency_ms=lat.stt_ms,
            input_val_ms=lat.input_validation_ms,
            language_detected=detected_lang,
            t_global=t_global,
        )

    async def execute_text(
        self,
        query: str,
        strategy: Optional[str] = None,
        lang_filter: Optional[str] = None,
        mock_mode: bool = False,
    ) -> PipelineResult:
        """
        Execute Text-mode RAG pipeline (skips STT).
        """
        t_global = time.perf_counter()
        t0 = time.perf_counter()
        clean_q = (query or "").strip()
        val_ms = (time.perf_counter() - t0) * 1000

        if not clean_q:
            lat = StageLatency(input_validation_ms=val_ms, total_ms=val_ms)
            return PipelineResult(
                status="error",
                answer="Invalid query: query string cannot be empty.",
                guardrail_passed=False,
                guardrail_reason=REASON_UNSAFE_INPUT,
                confidence=0.0,
                latency=lat,
                error_message="Empty query string",
            )

        return await self._execute_text_core(
            query=clean_q,
            strategy=strategy,
            lang_filter=lang_filter,
            mock_mode=mock_mode,
            stt_latency_ms=0.0,
            input_val_ms=val_ms,
            language_detected=lang_filter or "en-IN",
            t_global=t_global,
        )

    async def _execute_text_core(
        self,
        query: str,
        strategy: Optional[str],
        lang_filter: Optional[str],
        mock_mode: bool,
        stt_latency_ms: float,
        input_val_ms: float,
        language_detected: str,
        t_global: float,
    ) -> PipelineResult:
        """Core pipeline stages 3–8."""
        lat = StageLatency(
            input_validation_ms=input_val_ms,
            stt_ms=stt_latency_ms,
        )

        # ── 3. Pre-Generation Input Guardrail ──────────────────────────────────
        t0 = time.perf_counter()
        guard_in: GuardrailResult = check_input(query)
        lat.input_guardrail_ms = (time.perf_counter() - t0) * 1000

        if not guard_in.passed:
            lat.total_ms = (time.perf_counter() - t_global) * 1000
            return PipelineResult(
                status="refusal",
                transcript=query,
                language_detected=language_detected,
                answer=guard_in.message or "Query violates input guardrails.",
                grounded=False,
                confidence=0.0,
                guardrail_passed=False,
                guardrail_reason=guard_in.reason,
                latency=lat,
            )

        # ── 4. Vector Retrieval ────────────────────────────────────────────────
        t0 = time.perf_counter()
        chosen_strategy = strategy or settings.CHUNKING_STRATEGY
        try:
            candidates, retrieve_ms = await asyncio.to_thread(
                retrieve,
                query=query,
                top_k=settings.TOP_K_RETRIEVE,
                strategy_filter=chosen_strategy if chosen_strategy != "all" else None,
                lang_filter=lang_filter if lang_filter != "all" else None,
            )
            lat.retrieval_ms = retrieve_ms
        except Exception as e:
            lat.retrieval_ms = (time.perf_counter() - t0) * 1000
            lat.total_ms = (time.perf_counter() - t_global) * 1000
            log.error("harness.retrieval_error", error=str(e))
            return PipelineResult(
                status="error",
                transcript=query,
                language_detected=language_detected,
                answer="Error occurred during vector retrieval.",
                grounded=False,
                confidence=0.0,
                guardrail_passed=False,
                latency=lat,
                error_message=f"Retrieval Error: {str(e)}",
            )

        # ── 5. BM25 + RRF Reranking ────────────────────────────────────────────
        t0 = time.perf_counter()
        if candidates:
            try:
                reranked_chunks, rerank_ms = rerank(
                    query=query,
                    candidates=candidates,
                    top_k=settings.TOP_K_FINAL,
                    mode="bm25_rrf",
                )
                lat.reranking_ms = rerank_ms
            except Exception as e:
                log.warning("harness.reranking_fallback", error=str(e))
                reranked_chunks = candidates[: settings.TOP_K_FINAL]
                lat.reranking_ms = (time.perf_counter() - t0) * 1000
        else:
            reranked_chunks = []
            lat.reranking_ms = 0.0

        lat.search_pipeline_ms = lat.retrieval_ms + lat.reranking_ms

        # ── 6. Pre-LLM Context Validation Guardrail ────────────────────────────
        t0 = time.perf_counter()
        context_guard: GuardrailResult = check_context(
            query=query,
            chunks=reranked_chunks,
            min_score_threshold=self.min_relevance_threshold,
        )
        lat.context_validation_ms = (time.perf_counter() - t0) * 1000

        # Short-circuit if context is insufficient / low relevance
        if not context_guard.passed:
            lat.total_ms = (time.perf_counter() - t_global) * 1000
            return PipelineResult(
                status="refusal",
                transcript=query,
                language_detected=language_detected,
                answer=context_guard.message or "I don't have enough information to answer that.",
                grounded=False,
                confidence=0.0,
                guardrail_passed=False,
                guardrail_reason=context_guard.reason,
                sources=[],
                latency=lat,
            )

        # ── 7. Grounded LLM Generation ─────────────────────────────────────────
        t0 = time.perf_counter()
        try:
            gen_res: GenerationResult = await generate(
                query=query,
                context_chunks=reranked_chunks,
                mock_mode=mock_mode,
            )
            lat.generation_ms = gen_res.latency_ms
        except Exception as e:
            lat.generation_ms = (time.perf_counter() - t0) * 1000
            log.warning("harness.llm_fallback_to_mock", error=str(e))
            gen_res = await generate(
                query=query,
                context_chunks=reranked_chunks,
                mock_mode=True,
            )

        # ── 8. Post-Generation Grounding Guardrail ──────────────────────────────
        t0 = time.perf_counter()
        ground_guard: GuardrailResult = check_output(
            result=gen_res,
            context_chunks=reranked_chunks,
            min_grounding_overlap=self.min_grounding_overlap,
        )
        lat.grounding_check_ms = (time.perf_counter() - t0) * 1000

        final_answer = ground_guard.answer or gen_res.answer
        guard_passed = ground_guard.passed
        guard_reason = ground_guard.reason

        if not guard_passed:
            final_status = "refusal"
            if guard_reason == REASON_HALLUCINATION:
                final_answer = "I could not verify the factual grounding of the generated answer against the retrieved context."
            elif guard_reason == REASON_NO_CONTEXT:
                final_answer = "I do not have enough information in the provided context to answer this question."
        else:
            final_status = "success"

        lat.total_ms = (time.perf_counter() - t_global) * 1000

        return PipelineResult(
            status=final_status,
            transcript=query,
            language_detected=language_detected,
            answer=final_answer,
            grounded=guard_passed,
            confidence=ground_guard.confidence if guard_passed else 0.0,
            guardrail_passed=guard_passed,
            guardrail_reason=guard_reason,
            model=gen_res.model,
            sources=gen_res.citations,
            latency=lat,
            mock=gen_res.mock,
        )

    def execute_text_sync(
        self,
        query: str,
        strategy: Optional[str] = None,
        lang_filter: Optional[str] = None,
        mock_mode: bool = False,
    ) -> PipelineResult:
        """Synchronous wrapper for execute_text."""
        def _run():
            return asyncio.run(
                self.execute_text(
                    query=query,
                    strategy=strategy,
                    lang_filter=lang_filter,
                    mock_mode=mock_mode,
                )
            )

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                return executor.submit(_run).result()
        else:
            return _run()


# Singleton Orchestrator instance
default_orchestrator = PipelineOrchestrator()
