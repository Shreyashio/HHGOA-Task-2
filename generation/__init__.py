"""
generation/__init__.py
──────────────────────
Answer generation, guardrails, and orchestration harness for Voice-RAG pipeline.
"""

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
from generation.harness import (
    PipelineOrchestrator,
    PipelineResult,
    StageLatency,
    default_orchestrator,
)
from generation.llm import (
    Citation,
    GenerationResult,
    generate,
    generate_sync,
)

__all__ = [
    "generate",
    "generate_sync",
    "GenerationResult",
    "Citation",
    "PipelineOrchestrator",
    "PipelineResult",
    "StageLatency",
    "default_orchestrator",
    "GuardrailResult",
    "check_input",
    "check_context",
    "check_output",
    "REASON_OFF_TOPIC",
    "REASON_UNSAFE_INPUT",
    "REASON_NO_CONTEXT",
    "REASON_LOW_RELEVANCE",
    "REASON_HALLUCINATION",
]
