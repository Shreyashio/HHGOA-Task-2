"""
test_retrieval.py
──────────────────
CLI test script for the full retrieval pipeline:
  query → embed → ChromaDB search (top-10) → BM25+RRF rerank (top-3) → print

Usage:
  python test_retrieval.py "what is photosynthesis"
  python test_retrieval.py "who was the first president of India" --strategy sentence
  python test_retrieval.py "capital of France" --strategy metadata --lang en
  python test_retrieval.py "what is diabetes" --mode cross_encoder  # slow but high quality
"""

import sys
import os
import argparse
import time

sys.path.insert(0, os.path.dirname(__file__))

# ── Load .env ──────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

import structlog
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(30),  # WARNING only
)

from retrieval.retriever import warm_up, retrieve
from retrieval.reranker import rerank


def main():
    parser = argparse.ArgumentParser(
        description="Test retrieval pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("query", help="Query string to retrieve for")
    parser.add_argument(
        "--strategy", default=None,
        choices=["fixed", "sentence", "metadata"],
        help="Restrict to a specific chunking strategy index. "
             "None = query across all strategies.",
    )
    parser.add_argument(
        "--lang", default=None,
        help="Restrict to a language ('en', 'hi', 'ta', ...). None = all.",
    )
    parser.add_argument(
        "--top-k-retrieve", type=int, default=10,
        help="Number of candidates from vector search.",
    )
    parser.add_argument(
        "--top-k-final", type=int, default=3,
        help="Number of chunks after reranking.",
    )
    parser.add_argument(
        "--mode", default="bm25_rrf",
        choices=["bm25_rrf", "cross_encoder"],
        help="Reranking mode. cross_encoder is ~50-150ms slower.",
    )
    parser.add_argument(
        "--persist-dir", default=None,
        help="Override CHROMA_PERSIST_DIR.",
    )
    args = parser.parse_args()

    # ── Warm up (load model + open collection) ─────────────────────────────────
    print("\n" + "=" * 65)
    print(f"  Query: {args.query!r}")
    print(f"  Strategy filter: {args.strategy or 'all'}")
    print(f"  Language filter: {args.lang or 'all'}")
    print(f"  Rerank mode: {args.mode}  (top {args.top_k_retrieve} → {args.top_k_final})")
    print("=" * 65)

    print("\n[1/3] Warming up embedding model + ChromaDB...")
    t_warm = time.perf_counter()
    warm_up(persist_dir=args.persist_dir)
    print(f"      Done in {(time.perf_counter()-t_warm)*1000:.0f}ms  (cached on 2nd run)")

    # ── Retrieve ───────────────────────────────────────────────────────────────
    print(f"\n[2/3] Retrieving top {args.top_k_retrieve} candidates...")
    candidates, retrieve_ms = retrieve(
        query=args.query,
        top_k=args.top_k_retrieve,
        strategy_filter=args.strategy,
        lang_filter=args.lang,
    )
    print(f"      Got {len(candidates)} candidates in {retrieve_ms:.1f}ms")

    if not candidates:
        print("\n  ⚠  No results returned. Is the ChromaDB index built?")
        print("     Run: python -m ingestion.run_ingestion --strategy sentence --max-docs 5000")
        return

    # ── Rerank ─────────────────────────────────────────────────────────────────
    print(f"\n[3/3] Reranking to top {args.top_k_final} ({args.mode})...")
    if args.mode == "cross_encoder":
        print("      ⚠  Cross-encoder mode: expect +50-150ms latency")
    top_chunks, rerank_ms = rerank(
        query=args.query,
        candidates=candidates,
        top_k=args.top_k_final,
        mode=args.mode,
    )
    print(f"      Done in {rerank_ms:.1f}ms")

    # ── Results ────────────────────────────────────────────────────────────────
    total_ms = retrieve_ms + rerank_ms
    budget_pct = (total_ms / 200.0) * 100

    print("\n" + "=" * 65)
    print(f"  TOP {len(top_chunks)} RESULTS")
    print(f"  Retrieval: {retrieve_ms:.1f}ms | Rerank: {rerank_ms:.1f}ms")
    print(f"  Total: {total_ms:.1f}ms  ({budget_pct:.0f}% of 200ms budget)")
    print("=" * 65)

    for i, chunk in enumerate(top_chunks, 1):
        print(f"\n  [{i}] Score: {chunk.score:.4f}  |  Strategy: {chunk.strategy}"
              f"  |  Lang: {chunk.lang}  |  is_selected: {chunk.is_selected}")
        print(f"      QueryType: {chunk.query_type}  |  doc_id: {chunk.doc_id}")
        if chunk.metadata.get("eng_query"):
            print(f"      OrigQuery: {chunk.metadata['eng_query'][:80]}")
        # Print chunk text, wrapped at 75 chars
        words = chunk.text.split()
        line, lines = [], []
        for w in words:
            line.append(w)
            if len(" ".join(line)) > 75:
                lines.append(" ".join(line[:-1]))
                line = [w]
        if line:
            lines.append(" ".join(line))
        for j, l in enumerate(lines[:5]):  # max 5 lines of text
            prefix = "      Text: " if j == 0 else "            "
            print(f"{prefix}{l}")
        if len(lines) > 5:
            print(f"            ... ({len(words)} words total)")

    print("\n" + "=" * 65)
    if total_ms <= 200:
        print(f"  ✓ Within 200ms budget ({total_ms:.1f}ms)")
    else:
        print(f"  ✗ Over budget by {total_ms - 200:.1f}ms — consider bm25_rrf mode")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
