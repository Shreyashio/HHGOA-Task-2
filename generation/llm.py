"""
generation/llm.py
──────────────────
Grounded answer generation using LLMs (Claude / Anthropic, Groq, OpenAI).

Features:
  - Formulates strict grounding prompt (answers ONLY from retrieved context chunks)
  - Signals refusal/unsupported when context lacks sufficient information
  - Structured JSON output parsing: { answer, supported, confidence, used_chunk_indices }
  - Retries transient 5xx/429/network errors using tenacity with exponential backoff
  - Returns rich GenerationResult with citations and metadata for guardrails & UI
  - Full mock mode for offline dev and zero-credit test verification
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import structlog
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from backend.config import settings
from retrieval.retriever import RetrievedChunk

log = structlog.get_logger()

DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"
DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

SYSTEM_PROMPT = """You are a factual, concise question-answering assistant.
Your task is to answer the user's question STRICTLY and ONLY using the provided retrieved context chunks.

CRITICAL RULES:
1. Grounding: Answer ONLY from facts explicitly stated in the context chunks. Do NOT extrapolate, speculate, or introduce external knowledge.
2. Insufficient Context: If the provided context does NOT contain enough information to answer the question with certainty, answer: "I do not have enough information in the provided context to answer this question." and set supported to false.
3. Citations: Indicate exactly which chunk index or indices (1-indexed, e.g. [1], [2]) directly support your answer in `used_chunk_indices`.
4. Output Format: You MUST return a single valid JSON object with NO surrounding commentary or markdown format outside the JSON:
{
  "answer": "<concise, factual answer grounded in context>",
  "supported": true,
  "confidence": 0.95,
  "used_chunk_indices": [1, 2]
}
"""


@dataclass
class Citation:
    """Citation details for a chunk used in the answer."""
    chunk_index: int
    chunk_id: str
    doc_id: str
    lang: str
    snippet: str
    score: float


@dataclass
class GenerationResult:
    """Structured output from the LLM generation step."""
    answer: str
    confidence: float
    supported: bool                        # LLM self-reports if context supports answer
    model: str = ""
    tokens_used: int = 0
    latency_ms: float = 0.0
    context_chunks: List[str] = field(default_factory=list)
    used_chunks: List[RetrievedChunk] = field(default_factory=list)
    citations: List[Citation] = field(default_factory=list)
    raw_response: Optional[str] = None
    mock: bool = False


def _is_transient_llm_error(exc: BaseException) -> bool:
    """Check if exception is transient (5xx, rate limit 429, timeout, network error)."""
    exc_str = str(exc).lower()
    # Check status code attribute if available
    status_code = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if status_code:
        if status_code >= 500 or status_code == 429:
            return True
    if any(k in exc_str for k in ["rate limit", "429", "timeout", "timed out", "503", "502", "500", "connection"]):
        return True
    return False


def format_context_prompt(context_chunks: List[RetrievedChunk]) -> str:
    """Format retrieved chunks into numbered context blocks for LLM prompt."""
    blocks = []
    for i, chunk in enumerate(context_chunks, 1):
        header = f"[Chunk {i}] (doc_id: {chunk.doc_id}, lang: {chunk.lang}, score: {chunk.score:.3f})"
        blocks.append(f"{header}\n{chunk.text.strip()}")
    return "\n\n".join(blocks)


def _extract_json_payload(raw_text: str) -> Dict[str, Any]:
    """Robustly extract and parse JSON object from LLM response."""
    text = raw_text.strip()
    # Strip markdown ```json ... ``` code fence if present
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    elif text.startswith("{") and text.endswith("}"):
        pass
    else:
        # Search for first { to last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]

    try:
        return json.loads(text)
    except Exception:
        # Fallback if raw text wasn't valid JSON
        return {
            "answer": raw_text.strip(),
            "supported": True,
            "confidence": 0.85,
            "used_chunk_indices": [1],
        }


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
    retry=retry_if_exception(_is_transient_llm_error),
    reraise=True,
)
async def _call_anthropic(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> Tuple[str, int]:
    """Call Claude via Anthropic SDK with tenacity retries."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model=model,
        max_tokens=600,
        temperature=0.0,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text_content = ""
    for block in response.content:
        if getattr(block, "type", "") == "text":
            text_content += block.text
    tokens = (response.usage.input_tokens or 0) + (response.usage.output_tokens or 0)
    return text_content, tokens


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
    retry=retry_if_exception(_is_transient_llm_error),
    reraise=True,
)
async def _call_groq(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> Tuple[str, int]:
    """Call Groq API with tenacity retries."""
    import httpx

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return text, tokens


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
    retry=retry_if_exception(_is_transient_llm_error),
    reraise=True,
)
async def _call_openai(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
) -> Tuple[str, int]:
    """Call OpenAI API with tenacity retries."""
    import httpx

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0.0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
        return text, tokens


def _mock_generate(
    query: str,
    context_chunks: List[RetrievedChunk],
) -> Tuple[str, int]:
    """Generate deterministic grounded mock answer from top chunks without external API call."""
    if not context_chunks:
        return json.dumps({
            "answer": "I do not have enough information in the provided context to answer this question.",
            "supported": False,
            "confidence": 0.0,
            "used_chunk_indices": [],
        }), 40

    # Pick the most relevant sentence from the top chunk
    top_chunk = context_chunks[0]
    sentences = [s.strip() for s in re.split(r"[.!?]\s+", top_chunk.text) if len(s.strip()) > 10]
    best_sentence = sentences[0] if sentences else top_chunk.text[:150]

    mock_data = {
        "answer": f"Based on the retrieved context: {best_sentence}.",
        "supported": True,
        "confidence": 0.95,
        "used_chunk_indices": [1],
    }
    return json.dumps(mock_data), 120


async def generate(
    query: str,
    context_chunks: List[RetrievedChunk],
    model: Optional[str] = None,
    provider: Optional[str] = None,
    mock_mode: bool = False,
) -> GenerationResult:
    """
    Generate a grounded answer from retrieved context.

    Args:
        query:          The user's question (from STT or text query).
        context_chunks: Top-K reranked chunks from the retrieval pipeline.
        model:          Override the LLM model name.
        provider:       Override the provider ('anthropic' | 'groq' | 'openai' | 'mock').
        mock_mode:      If True, run offline mock generation without API keys.

    Returns:
        GenerationResult containing structured answer, confidence, grounding signal, and citations.

    Raises:
        ValueError: If context_chunks is empty.
    """
    if not context_chunks:
        raise ValueError("context_chunks cannot be empty (at least 1 chunk required for generation)")

    # ── Determine Provider & Key ───────────────────────────────────────────────
    chosen_provider = (provider or settings.LLM_PROVIDER or "").lower().strip()
    anthropic_key = (settings.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")).strip()
    groq_key = (settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "")).strip()
    openai_key = (settings.OPENAI_API_KEY or os.environ.get("OPENAI_API_KEY", "")).strip()

    # Auto-select provider if key is available
    if not chosen_provider or chosen_provider in ("anthropic", "claude"):
        if anthropic_key and not anthropic_key.startswith("your_"):
            chosen_provider = "anthropic"
        elif groq_key and not groq_key.startswith("your_"):
            chosen_provider = "groq"
        elif openai_key and not openai_key.startswith("your_"):
            chosen_provider = "openai"
        else:
            chosen_provider = "anthropic"

    is_placeholder_key = False
    if chosen_provider in ("anthropic", "claude"):
        is_placeholder_key = not anthropic_key or anthropic_key.startswith("your_") or anthropic_key in ("mock", "none")
    elif chosen_provider == "groq":
        is_placeholder_key = not groq_key or groq_key.startswith("your_") or groq_key in ("mock", "none")
    elif chosen_provider == "openai":
        is_placeholder_key = not openai_key or openai_key.startswith("your_") or openai_key in ("mock", "none")

    # ── Build Prompts ──────────────────────────────────────────────────────────
    context_text = format_context_prompt(context_chunks)
    user_prompt = f"Retrieved Context:\n{context_text}\n\nQuestion: {query}\n\nProvide your JSON answer:"

    raw_response = ""
    tokens_used = 0
    is_mock = False
    used_model = model or settings.LLM_MODEL

    t0 = time.perf_counter()

    # ── Execute Generation ─────────────────────────────────────────────────────
    if mock_mode or is_placeholder_key or chosen_provider == "mock":
        is_mock = True
        used_model = "mock-grounded-generator"
        # Simulate slight inference latency
        await asyncio.sleep(0.015)
        raw_response, tokens_used = _mock_generate(query, context_chunks)
        log.info("llm.generate_mock", query=query[:50], chunks_count=len(context_chunks))
    else:
        try:
            if chosen_provider in ("anthropic", "claude"):
                used_model = model or settings.LLM_MODEL or DEFAULT_ANTHROPIC_MODEL
                if not used_model.startswith("claude"):
                    used_model = DEFAULT_ANTHROPIC_MODEL
                raw_response, tokens_used = await _call_anthropic(
                    api_key=anthropic_key,
                    model=used_model,
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                )
            elif chosen_provider == "groq":
                used_model = model or DEFAULT_GROQ_MODEL
                raw_response, tokens_used = await _call_groq(
                    api_key=groq_key,
                    model=used_model,
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                )
            elif chosen_provider == "openai":
                used_model = model or DEFAULT_OPENAI_MODEL
                raw_response, tokens_used = await _call_openai(
                    api_key=openai_key,
                    model=used_model,
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                )
            else:
                raise ValueError(f"Unknown LLM provider: {chosen_provider}")
        except Exception as e:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            log.error("llm.generation_failed", error=str(e), provider=chosen_provider, model=used_model)
            raise

    elapsed_ms = (time.perf_counter() - t0) * 1000

    # ── Parse Structured Output ────────────────────────────────────────────────
    parsed = _extract_json_payload(raw_response)
    answer = parsed.get("answer", "").strip()
    supported = bool(parsed.get("supported", True))
    confidence = float(parsed.get("confidence", 0.9 if supported else 0.0))
    used_indices = parsed.get("used_chunk_indices", [])

    # Map used indices to chunks and build citations
    used_chunks: List[RetrievedChunk] = []
    citations: List[Citation] = []

    for idx in used_indices:
        if isinstance(idx, int) and 1 <= idx <= len(context_chunks):
            ch = context_chunks[idx - 1]
            used_chunks.append(ch)
            snippet = ch.text.strip().replace("\n", " ")
            if len(snippet) > 140:
                snippet = snippet[:137] + "..."
            citations.append(
                Citation(
                    chunk_index=idx,
                    chunk_id=ch.chunk_id,
                    doc_id=ch.doc_id,
                    lang=ch.lang,
                    snippet=snippet,
                    score=ch.score,
                )
            )

    # Fallback to chunk 1 citation if supported but no indices provided
    if supported and not citations and context_chunks:
        ch = context_chunks[0]
        used_chunks.append(ch)
        snippet = ch.text.strip().replace("\n", " ")
        if len(snippet) > 140:
            snippet = snippet[:137] + "..."
        citations.append(
            Citation(
                chunk_index=1,
                chunk_id=ch.chunk_id,
                doc_id=ch.doc_id,
                lang=ch.lang,
                snippet=snippet,
                score=ch.score,
            )
        )

    log.info(
        "llm.generate_success",
        model=used_model,
        supported=supported,
        confidence=f"{confidence:.2f}",
        citations_count=len(citations),
        latency_ms=f"{elapsed_ms:.1f}",
    )

    return GenerationResult(
        answer=answer,
        confidence=confidence,
        supported=supported,
        model=used_model,
        tokens_used=tokens_used,
        latency_ms=elapsed_ms,
        context_chunks=[c.text for c in context_chunks],
        used_chunks=used_chunks,
        citations=citations,
        raw_response=raw_response,
        mock=is_mock,
    )


def generate_sync(
    query: str,
    context_chunks: List[RetrievedChunk],
    model: Optional[str] = None,
    provider: Optional[str] = None,
    mock_mode: bool = False,
) -> GenerationResult:
    """
    Synchronous wrapper for generate().
    Safely executes whether an event loop is currently active or not.
    """
    def _run():
        return asyncio.run(
            generate(
                query=query,
                context_chunks=context_chunks,
                model=model,
                provider=provider,
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
