"""
generation/guardrails.py
─────────────────────────
Pre- and post-generation safety and quality checks.

What this will do (Step 5):

PRE-GENERATION checks (run before calling the LLM):
  1. Off-topic detection
     - Embeds the query and computes cosine similarity to a set of known
       "in-topic" seed phrases derived from MSMARCO-XI subject matter
     - If similarity < threshold → refuse with REASON_OFF_TOPIC
  2. Unsafe / inappropriate input detection
     - Keyword blocklist + simple pattern matching for hate speech, PII requests,
       prompt injection patterns ("ignore previous instructions", etc.)
     - If triggered → refuse with REASON_UNSAFE_INPUT

POST-GENERATION checks (run on the LLM's GenerationResult):
  3. No-context refusal
     - If GenerationResult.supported == False → refuse with REASON_NO_CONTEXT
  4. Hallucination check (lightweight)
     - For each sentence in the answer, check if at least one key noun-phrase
       appears verbatim or by fuzzy match in the retrieved chunks
     - If fewer than 50% of sentences are grounded → refuse with REASON_HALLUCINATION
     - This is intentionally conservative for a hackathon timeline

Output:
  GuardrailResult { passed: bool, reason: str | None, answer: str | None }
  - If passed=True, `answer` is the safe string to return to the user
  - If passed=False, `answer` is None and `reason` explains why
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List
from generation.llm import GenerationResult
from retrieval.retriever import RetrievedChunk


REASON_OFF_TOPIC = "off_topic"
REASON_UNSAFE_INPUT = "unsafe_input"
REASON_NO_CONTEXT = "no_context"
REASON_HALLUCINATION = "hallucination"


@dataclass
class GuardrailResult:
    """Output of the guardrail layer."""
    passed: bool
    reason: str | None = None          # one of the REASON_* constants, or None
    answer: str | None = None          # populated only if passed=True


def check_input(query: str) -> GuardrailResult:
    """
    Pre-generation guardrails on the raw user query.

    Args:
        query: transcribed text from STT

    Returns:
        GuardrailResult — if passed=False, the pipeline short-circuits here.
    """
    raise NotImplementedError("Implemented in Step 5")


def check_output(
    result: GenerationResult,
    context_chunks: List[RetrievedChunk],
) -> GuardrailResult:
    """
    Post-generation guardrails on the LLM's answer.

    Args:
        result:         output from `generate()`
        context_chunks: the same chunks passed to `generate()`

    Returns:
        GuardrailResult — if passed=False, the answer is suppressed.
    """
    raise NotImplementedError("Implemented in Step 5")
