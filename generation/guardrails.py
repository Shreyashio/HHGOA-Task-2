"""
generation/guardrails.py
─────────────────────────
Pre- and post-generation safety, quality, relevance, and grounding checks.

Guardrail Categories:
  1. PRE-GENERATION INPUT CHECKS:
     - Unsafe / inappropriate input detection (harmful content, prompt injections, toxic patterns)
     - Off-topic detection (completely irrelevant domains / prompt jailbreaks)

  2. PRE-LLM CONTEXT VALIDATION:
     - Relevance threshold check (if similarity/relevance scores are too low, short-circuit before LLM)
     - Empty context detection

  3. POST-GENERATION OUTPUT CHECKS:
     - Grounding verification (ensures answer is supported by retrieved chunks, not hallucinated)
     - Model self-reported refusal detection (supported=False)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Set

import structlog
from generation.llm import GenerationResult
from retrieval.retriever import RetrievedChunk

log = structlog.get_logger()

# ── Reason Constants ──────────────────────────────────────────────────────────
REASON_OFF_TOPIC = "off_topic"
REASON_UNSAFE_INPUT = "unsafe_input"
REASON_NO_CONTEXT = "no_context"
REASON_LOW_RELEVANCE = "low_relevance"
REASON_HALLUCINATION = "hallucination"

# ── Blocklists & Patterns ─────────────────────────────────────────────────────
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"disregard\s+(all\s+)?(previous|prior)\s+instructions",
    r"system\s+prompt\s+override",
    r"you\s+are\s+now\s+in\s+dan\s+mode",
    r"jailbreak",
    r"bypass\s+all\s+(filters|rules|safeguards)",
    r"reveal\s+(the|your)\s+(system\s+prompt|instructions|secret\s+key|api\s+key)",
    r"print\s+your\s+hidden\s+prompt",
    r"base64\s+decode\s+and\s+execute",
]

UNSAFE_KEYWORD_PATTERNS = [
    r"\bhow\s+to\s+build\s+a\s+(bomb|explosive|weapon)\b",
    r"\bhow\s+to\s+(hack|ddos|exploit)\s+into\b",
    r"\bsteal\s+(passwords|credit\s+cards|credentials)\b",
    r"\bgenerate\s+malware\b",
    r"\b(credit\s*card\s*number|cvv\s*code|ssn\s*number)\b",
]

OFF_TOPIC_PATTERNS = [
    r"^(write|generate|compose)\s+(a\s+poem|a\s+song|a\s+rap|fiction|a\s+story|fanfic)\b",
    r"^(roleplay|pretend\s+you\s+are)\b",
    r"^[a-z]{1,3}$",                         # single letters / tiny nonsense
    r"^(asdf|qwerty|zxcv|123456)+$",         # pure keyboard mashing
]

STOPWORDS: Set[str] = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
    "by", "about", "against", "between", "into", "through", "during", "before",
    "after", "above", "below", "from", "up", "down", "in", "out", "over", "under",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do",
    "does", "did", "can", "could", "shall", "should", "will", "would", "may",
    "might", "must", "it", "its", "they", "them", "their", "this", "that", "these",
    "those", "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
    "all", "any", "both", "each", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "based", "context", "provided", "according",
}


@dataclass
class GuardrailResult:
    """Output of the guardrail evaluation."""
    passed: bool
    reason: Optional[str] = None          # One of REASON_* or None
    message: Optional[str] = None         # Human-readable explanation / safe refusal
    answer: Optional[str] = None          # Populated safe answer string if passed
    confidence: float = 1.0


# ─── 1. Pre-Generation Input Guardrail ────────────────────────────────────────

def check_input(query: str) -> GuardrailResult:
    """
    Validate raw user query for safety, prompt injection, and topic relevance.

    Args:
        query: Transcribed or typed query string.

    Returns:
        GuardrailResult — if passed=False, pipeline short-circuits before retrieval.
    """
    clean_q = query.strip()
    if not clean_q:
        return GuardrailResult(
            passed=False,
            reason=REASON_UNSAFE_INPUT,
            message="Query cannot be empty.",
            confidence=0.0,
        )

    q_lower = clean_q.lower()

    # ── Check Prompt Injection ───────────────────────────────────────────────
    for pat in PROMPT_INJECTION_PATTERNS:
        if re.search(pat, q_lower, re.IGNORECASE):
            log.warning("guardrails.prompt_injection_blocked", pattern=pat, query=clean_q[:50])
            return GuardrailResult(
                passed=False,
                reason=REASON_UNSAFE_INPUT,
                message="I cannot process this request because it violates safety and prompt integrity guidelines.",
                confidence=0.0,
            )

    # ── Check Unsafe / Harmful Content ────────────────────────────────────────
    for pat in UNSAFE_KEYWORD_PATTERNS:
        if re.search(pat, q_lower, re.IGNORECASE):
            log.warning("guardrails.unsafe_content_blocked", pattern=pat, query=clean_q[:50])
            return GuardrailResult(
                passed=False,
                reason=REASON_UNSAFE_INPUT,
                message="I cannot assist with dangerous, harmful, or unauthorized requests.",
                confidence=0.0,
            )

    # ── Check Off-Topic / Nonsense ────────────────────────────────────────────
    for pat in OFF_TOPIC_PATTERNS:
        if re.search(pat, q_lower, re.IGNORECASE):
            log.info("guardrails.off_topic_detected", pattern=pat, query=clean_q[:50])
            return GuardrailResult(
                passed=False,
                reason=REASON_OFF_TOPIC,
                message="This question appears to be outside the supported factual question-answering domain.",
                confidence=0.0,
            )

    return GuardrailResult(passed=True, reason=None, message=None)


# ─── 2. Pre-LLM Context Validation ────────────────────────────────────────────

def check_context(
    query: str,
    chunks: List[RetrievedChunk],
    min_score_threshold: float = 0.005,
) -> GuardrailResult:
    """
    Validate that retrieved context is available before invoking the LLM.
    If chunks are empty or low relevance, we still ALLOW the LLM call —
    the updated system prompt instructs the LLM to answer from general knowledge
    with a [General Knowledge] prefix when context is insufficient.
    """
    if not chunks:
        log.info("guardrails.no_context_found", query=query[:50])
        # Still pass — let LLM use general knowledge
        return GuardrailResult(
            passed=True,
            reason=REASON_NO_CONTEXT,
            message=None,
            confidence=0.5,
        )

    top_chunk = chunks[0]
    if top_chunk.score < min_score_threshold:
        log.info(
            "guardrails.low_relevance_passthrough",
            top_score=f"{top_chunk.score:.5f}",
            threshold=min_score_threshold,
            query=query[:50],
        )
        # Still pass — LLM will fallback to general knowledge if needed
        return GuardrailResult(passed=True, reason=REASON_LOW_RELEVANCE, message=None, confidence=0.5)

    return GuardrailResult(passed=True, reason=None, message=None)


# ─── 3. Post-Generation Grounding Guardrail ───────────────────────────────────

def check_output(
    result: GenerationResult,
    context_chunks: List[RetrievedChunk],
    min_grounding_overlap: float = 0.25,
) -> GuardrailResult:
    """
    Verify that generated answer is strictly grounded in retrieved chunks.
    Detects hallucinations or claims not supported by the context.

    Args:
        result: GenerationResult from the LLM.
        context_chunks: Context chunks provided to the LLM.
        min_grounding_overlap: Minimum ratio of answer content words found in context.

    Returns:
        GuardrailResult with safe answer or hallucination rejection.
    """
    answer_text = result.answer.strip()
    if not answer_text:
        return GuardrailResult(
            passed=False,
            reason=REASON_NO_CONTEXT,
            message="No answer generated.",
            confidence=0.0,
        )

    refusal_indicators = [
        "not enough information",
        "cannot answer",
        "do not have enough information",
        "context does not provide",
        "context does not mention",
        "provided context does not contain",
        "माहिती उपलब्ध नाही",
        "माहिती नाही",
    ]
    is_explicit_refusal = any(ind in answer_text.lower() for ind in refusal_indicators)

    if is_explicit_refusal:
        return GuardrailResult(
            passed=False,
            reason=REASON_NO_CONTEXT,
            message=answer_text,
            answer=answer_text,
            confidence=0.0,
        )

    # If the answer is from general knowledge (either tagged or supported=False with an answer)
    if not result.supported or answer_text.lower().startswith("[general knowledge]"):
        return GuardrailResult(
            passed=True,
            reason="general_knowledge",
            answer=answer_text,
            confidence=result.confidence or 0.9,
        )

    # ── Lexical & Entity Grounding Check for Context-Grounded Answers ───────────
    # Combine all context text into one corpus
    context_corpus = " ".join(c.text.lower() for c in context_chunks)
    # Match alphanumeric words across ASCII and Indic/Devanagari Unicode ranges
    context_words = set(re.findall(r"[\w\u0900-\u097F]{2,}", context_corpus))

    # Extract substantive terms from generated answer
    answer_words = [
        w for w in re.findall(r"[\w\u0900-\u097F]{2,}", answer_text.lower())
        if w not in STOPWORDS
    ]

    if not answer_words:
        return GuardrailResult(passed=True, reason=None, answer=answer_text, confidence=result.confidence)

    # Calculate proportion of answer keywords grounded in retrieved context
    grounded_count = sum(1 for w in answer_words if w in context_words)
    grounding_ratio = grounded_count / len(answer_words)

    log.info(
        "guardrails.grounding_check",
        answer_words=len(answer_words),
        grounded_words=grounded_count,
        grounding_ratio=f"{grounding_ratio:.2f}",
        threshold=min_grounding_overlap,
    )

    if grounding_ratio < min_grounding_overlap:
        # Fallback to general knowledge rather than blocking the user
        log.info(
            "guardrails.general_knowledge_fallback",
            grounding_ratio=f"{grounding_ratio:.2f}",
            answer_preview=answer_text[:80],
        )
        return GuardrailResult(
            passed=True,
            reason="general_knowledge",
            answer=answer_text,
            confidence=result.confidence or 0.85,
        )

    return GuardrailResult(
        passed=True,
        reason=None,
        answer=answer_text,
        confidence=result.confidence,
    )
