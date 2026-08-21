"""
generation/llm.py
──────────────────
Calls the LLM to generate a grounded answer from retrieved context.

What this will do (Step 5):
  - Build a structured prompt: system prompt + retrieved context + user query
  - Call Groq (default) or OpenAI via their respective SDKs
  - Wrap the call in the tenacity retry harness (3 attempts, exponential backoff)
  - Return a GenerationResult with:
      { answer, model, tokens_used, latency_ms, context_used }
  - Supports structured output mode (JSON) for the guardrails layer to parse

Prompt design:
  - System: role + grounding instruction ("answer ONLY from the context below")
  - Context block: top-K retrieved chunks, separated by --- delimiters
  - User turn: the transcribed question
  - The model is instructed to output a JSON object:
      { "answer": "...", "confidence": 0-1, "supported": true/false }
    `supported=false` triggers the guardrail to refuse the answer.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from retrieval.retriever import RetrievedChunk


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


async def generate(
    query: str,
    context_chunks: List[RetrievedChunk],
    model: str | None = None,
) -> GenerationResult:
    """
    Generate a grounded answer from retrieved context.

    Args:
        query:          the user's question (from STT)
        context_chunks: reranked top-K chunks from the retrieval pipeline
        model:          override the default LLM model

    Returns:
        GenerationResult — structured, parseable output.

    Raises:
        ValueError: if context_chunks is empty (caller should check guardrails first)
    """
    raise NotImplementedError("Implemented in Step 5")
