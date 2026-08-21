"""
test_generation.py
──────────────────
CLI test script and test harness for the full end-to-end pipeline:
  Query → Vector Retrieval → BM25+RRF Reranking → Grounded LLM Generation (Step 5)

Usage:
  python test_generation.py "what is photosynthesis"
  python test_generation.py "who was the first president of India" --strategy sentence
  python test_generation.py "what is diabetes" --mock
  python test_generation.py --unit-tests
"""

import argparse
import asyncio
import os
import sys
import time
from unittest.mock import AsyncMock, patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

import structlog
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(30),  # WARNING only for CLI
)

from backend.config import settings
from generation.llm import (
    GenerationResult,
    _extract_json_payload,
    format_context_prompt,
    generate,
    generate_sync,
)
from retrieval.reranker import rerank
from retrieval.retriever import RetrievedChunk, retrieve, warm_up


def run_unit_tests():
    print("\n" + "=" * 65)
    print("  LLM Generation Layer Unit Tests (Step 5)")
    print("=" * 65)

    dummy_chunks = [
        RetrievedChunk(
            chunk_id="chunk_1",
            doc_id="doc_101",
            text="Photosynthesis is the process used by plants and other organisms to convert light energy into chemical energy.",
            score=0.92,
            strategy="sentence",
            lang="en",
        ),
        RetrievedChunk(
            chunk_id="chunk_2",
            doc_id="doc_102",
            text="During oxygenic photosynthesis, light energy transfers electrons from water to carbon dioxide, producing carbohydrates and oxygen.",
            score=0.88,
            strategy="sentence",
            lang="en",
        ),
    ]

    passed = 0
    total = 0

    def test_assert(condition: bool, name: str, details: str = ""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {name}" + (f" ({details})" if details else ""))
        else:
            print(f"  [FAIL] {name}" + (f" ({details})" if details else ""))
            raise AssertionError(f"Test failed: {name} - {details}")

    # ── Test 1: Empty chunks rejection ─────────────────────────────────────────
    print("\n[1] Input Validation")
    try:
        generate_sync("what is photosynthesis", [])
        test_assert(False, "empty chunks raises ValueError", "No error was raised")
    except ValueError as e:
        test_assert(True, "empty chunks raises ValueError", str(e))

    # ── Test 2: Prompt formatting ──────────────────────────────────────────────
    print("\n[2] Prompt Context Formatting")
    prompt = format_context_prompt(dummy_chunks)
    test_assert("[Chunk 1]" in prompt and "[Chunk 2]" in prompt, "chunk headers present")
    test_assert("doc_101" in prompt and "doc_102" in prompt, "document IDs present")
    test_assert("Photosynthesis" in prompt, "chunk text preserved")

    # ── Test 3: JSON parsing ───────────────────────────────────────────────────
    print("\n[3] JSON Payload Parsing")
    sample_json = '```json\n{"answer": "It converts light to chemical energy.", "supported": true, "confidence": 0.96, "used_chunk_indices": [1]}\n```'
    parsed = _extract_json_payload(sample_json)
    test_assert(parsed["answer"] == "It converts light to chemical energy.", "extracts answer from code block")
    test_assert(parsed["supported"] is True, "extracts supported flag")
    test_assert(parsed["used_chunk_indices"] == [1], "extracts used_chunk_indices")

    # ── Test 4: Mock generation & Citations ────────────────────────────────────
    print("\n[4] Mock Generation & Citation Resolution")
    res = generate_sync(
        query="what is photosynthesis",
        context_chunks=dummy_chunks,
        mock_mode=True,
    )
    test_assert(isinstance(res, GenerationResult), "returns GenerationResult")
    test_assert(bool(res.answer), "contains answer", res.answer[:50] + "...")
    test_assert(res.supported is True, "supported signal is True")
    test_assert(res.confidence > 0.8, "confidence is high", f"{res.confidence}")
    test_assert(len(res.citations) > 0, "citations populated", f"count={len(res.citations)}")
    test_assert(res.citations[0].doc_id == "doc_101", "citation maps to doc_101")
    test_assert(res.mock is True, "mock flag is True")

    # ── Test 5: Tenacity retry on transient errors ─────────────────────────────
    print("\n[5] Tenacity Retries on Transient API Errors")
    attempt_count = 0

    class MockContent:
        type = "text"
        text = '{"answer": "Recovered answer", "supported": true, "confidence": 0.99, "used_chunk_indices": [1]}'

    class MockUsage:
        input_tokens = 20
        output_tokens = 30

    class MockMessageResponse:
        content = [MockContent()]
        usage = MockUsage()

    async def mock_messages_create(*args, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            class Mock503Error(Exception):
                status_code = 503
            raise Mock503Error("Anthropic service overloaded (503)")
        return MockMessageResponse()

    with patch("anthropic.AsyncAnthropic.messages", new_callable=AsyncMock) as mock_messages:
        mock_messages.create = AsyncMock(side_effect=mock_messages_create)
        with patch.object(settings, "ANTHROPIC_API_KEY", "sk-ant-test-key"):
            res_retry = asyncio.run(
                generate(
                    query="what is photosynthesis",
                    context_chunks=dummy_chunks,
                    provider="anthropic",
                    mock_mode=False,
                )
            )
            test_assert(attempt_count == 3, "retried 3 times on 503", f"attempts={attempt_count}")
            test_assert(res_retry.answer == "Recovered answer", "successfully recovered")

    print("\n" + "=" * 65)
    print(f"  PASS  All {passed}/{total} generation tests passed successfully!")
    print("=" * 65 + "\n")


def run_pipeline(
    query: str,
    strategy: str | None = None,
    lang: str | None = None,
    top_k_retrieve: int = 10,
    top_k_final: int = 3,
    rerank_mode: str = "bm25_rrf",
    provider: str | None = None,
    model: str | None = None,
    mock_mode: bool = False,
    persist_dir: str | None = None,
):
    print("\n" + "=" * 70)
    print("  VOICE-RAG END-TO-END PIPELINE: Question -> Retrieval -> LLM Answer")
    print("=" * 70)
    print(f"  Query:            {query!r}")
    print(f"  Strategy filter:  {strategy or 'all'}")
    print(f"  Language filter:  {lang or 'all'}")
    print(f"  Rerank mode:      {rerank_mode} (top {top_k_retrieve} -> {top_k_final})")
    print(f"  LLM Provider:     {provider or settings.LLM_PROVIDER}")
    print(f"  LLM Model:        {model or settings.LLM_MODEL}")
    print("=" * 70)

    # ── [1/4] Warm Up ──────────────────────────────────────────────────────────
    t_start = time.perf_counter()
    print("\n[1/4] Warming up embedding model & ChromaDB collection...")
    t0 = time.perf_counter()
    warm_up(persist_dir=persist_dir)
    warm_ms = (time.perf_counter() - t0) * 1000
    print(f"      Ready in {warm_ms:.0f}ms")

    # ── [2/4] Retrieval ────────────────────────────────────────────────────────
    print(f"\n[2/4] Retrieving top-{top_k_retrieve} candidates from vector index...")
    candidates, retrieve_ms = retrieve(
        query=query,
        top_k=top_k_retrieve,
        strategy_filter=strategy,
        lang_filter=lang,
    )
    print(f"      Found {len(candidates)} candidates in {retrieve_ms:.1f}ms")

    if not candidates:
        print("\n  [WARN] No candidates retrieved. Run ingestion first:")
        print("    python -m ingestion.run_ingestion --strategy sentence --max-docs 5000")
        return

    # ── [3/4] Reranking ────────────────────────────────────────────────────────
    print(f"\n[3/4] Reranking to top-{top_k_final} ({rerank_mode})...")
    reranked_chunks, rerank_ms = rerank(
        query=query,
        candidates=candidates,
        top_k=top_k_final,
        mode=rerank_mode,
    )
    search_pipeline_ms = retrieve_ms + rerank_ms
    print(f"      Reranked in {rerank_ms:.1f}ms | Search Pipeline: {search_pipeline_ms:.1f}ms (target <200ms)")

    # ── [4/4] Generation ───────────────────────────────────────────────────────
    print(f"\n[4/4] Generating grounded answer with LLM...")
    try:
        gen_result = generate_sync(
            query=query,
            context_chunks=reranked_chunks,
            model=model,
            provider=provider,
            mock_mode=mock_mode,
        )
    except Exception as e:
        print(f"\n  [WARN] LLM generation failed: {e}")
        print("    Falling back to mock grounded generator...")
        gen_result = generate_sync(
            query=query,
            context_chunks=reranked_chunks,
            mock_mode=True,
        )

    total_pipeline_ms = search_pipeline_ms + gen_result.latency_ms

    # ── Final Answer Output ────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  GROUNDED ANSWER")
    print("=" * 70)
    print(f"\n  {gen_result.answer}\n")

    # Grounding signals
    status_icon = "[PASS]" if gen_result.supported else "[FAIL]"
    print("-" * 70)
    print(f"  Grounded in Context: {status_icon} {'YES' if gen_result.supported else 'NO (Insufficient Context)'}")
    print(f"  Confidence:          {gen_result.confidence * 100:.1f}%")
    print(f"  Model Used:          {gen_result.model} {'(Mock Mode)' if gen_result.mock else ''}")
    if gen_result.tokens_used:
        print(f"  Tokens Used:         {gen_result.tokens_used}")

    # Latency breakdown
    print("-" * 70)
    print(f"  LATENCY BREAKDOWN:")
    print(f"    - Vector Retrieval:    {retrieve_ms:6.1f} ms")
    print(f"    - BM25+RRF Reranking:  {rerank_ms:6.1f} ms")
    print(f"    ------------------------------------")
    budget_pass = "[PASS] < 200ms" if search_pipeline_ms <= 200 else "[WARN] > 200ms"
    print(f"    - Retrieval Pipeline:  {search_pipeline_ms:6.1f} ms   {budget_pass}")
    print(f"    - LLM Generation:      {gen_result.latency_ms:6.1f} ms")
    print(f"    ------------------------------------")
    print(f"    - Total End-to-End:    {total_pipeline_ms:6.1f} ms")

    # Sources & Citations
    print("-" * 70)
    print(f"  SOURCES & CITATIONS ({len(gen_result.citations)} cited from {len(reranked_chunks)} context chunks):")
    print("-" * 70)

    for c in gen_result.citations:
        print(f"\n  [Source {c.chunk_index}] doc_id: {c.doc_id}  |  chunk_id: {c.chunk_id[:12]}...  |  lang: {c.lang}  |  rel_score: {c.score:.4f}")
        print(f"    Snippet: \"{c.snippet}\"")

    print("\n" + "=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="End-to-End Voice-RAG Query & LLM Generation Test (Step 5)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("query", nargs="?", default="what is photosynthesis", help="Query to run")
    parser.add_argument("--strategy", choices=["fixed", "sentence", "metadata"], default="sentence", help="Chunking strategy filter")
    parser.add_argument("--lang", default=None, help="Language filter (e.g. 'en', 'hi')")
    parser.add_argument("--top-k-retrieve", type=int, default=10, help="Initial retrieval candidates")
    parser.add_argument("--top-k-final", type=int, default=3, help="Reranked chunks sent to LLM")
    parser.add_argument("--mode", default="bm25_rrf", choices=["bm25_rrf", "cross_encoder"], help="Reranking algorithm")
    parser.add_argument("--provider", default=None, choices=["anthropic", "claude", "groq", "openai", "mock"], help="LLM Provider")
    parser.add_argument("--model", default=None, help="Override LLM model name")
    parser.add_argument("--mock", action="store_true", help="Force offline mock generation")
    parser.add_argument("--persist-dir", default=None, help="Override ChromaDB persist directory")
    parser.add_argument("--unit-tests", action="store_true", help="Run LLM unit tests")

    args = parser.parse_args()

    if args.unit_tests:
        run_unit_tests()
    else:
        run_pipeline(
            query=args.query,
            strategy=args.strategy,
            lang=args.lang,
            top_k_retrieve=args.top_k_retrieve,
            top_k_final=args.top_k_final,
            rerank_mode=args.mode,
            provider=args.provider,
            model=args.model,
            mock_mode=args.mock,
            persist_dir=args.persist_dir,
        )


if __name__ == "__main__":
    main()
