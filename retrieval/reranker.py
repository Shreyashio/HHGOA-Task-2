"""
retrieval/reranker.py
──────────────────────
Reranks the top-K vector search candidates down to top-N final chunks.

Reranking approach: BM25 + Reciprocal Rank Fusion (RRF)
─────────────────────────────────────────────────────────

Why NOT cross-encoder (e.g. ms-marco-MiniLM-L-6-v2):
  A cross-encoder scores each (query, chunk) pair by running a full
  transformer forward pass. With 10 candidates, that's 10 forward passes
  = 50–150ms on CPU. Combined with 20–35ms retrieval, that's 70–185ms
  just for retrieval+rerank — dangerously close to (or over) the 200ms
  budget with no headroom for generation setup.

  Cross-encoder is available as opt-in "quality mode" (set RERANK_MODE=cross
  in .env), but is NOT the default.

Why BM25 + RRF:
  - BM25 (Okapi BM25): classic lexical scoring, <2ms on 10 candidates
  - RRF (Reciprocal Rank Fusion): combines vector rank + BM25 rank with
    no tuning parameters: score = 1/(k+r_vector) + 1/(k+r_bm25)  where k=60
  - Total reranking cost: ~2–5ms
  - Works well for conversational/voice queries where exact keyword matches
    matter (BM25 catches what dense retrieval misses)
  - Parameter-free — no hypertuning needed for a hackathon timeline

Latency budget for this file
─────────────────────────────
Target: <20ms (retriever uses ~15-35ms, leaving 145ms for generation)
BM25+RRF actual: ~2-5ms  ✓
Cross-encoder:   ~50-150ms  ⚠ (documented opt-in)
"""

from __future__ import annotations

import time
from typing import List, Optional

import structlog

log = structlog.get_logger()


# ─── RRF constant ──────────────────────────────────────────────────────────────
# k=60 is the standard value from the original RRF paper (Cormack et al. 2009).
# Higher k → less aggressive fusion; lower k → top ranks dominate more.
_RRF_K = 60


# ─── BM25 + RRF reranker ────────────────────────────────────────────────────────

def rerank(
    query: str,
    candidates: list,                   # List[RetrievedChunk]
    top_k: Optional[int] = None,
    mode: str = "bm25_rrf",            # "bm25_rrf" | "cross_encoder"
) -> tuple[list, float]:
    """
    Rerank candidates using BM25 + Reciprocal Rank Fusion (default) or
    cross-encoder (opt-in quality mode, ~50-150ms extra latency).

    Args:
        query:      the user's query string
        candidates: List[RetrievedChunk] from retrieve() — typically top-10
        top_k:      how many to return (default: TOP_K_FINAL from settings)
        mode:       "bm25_rrf" (default, ~2-5ms) | "cross_encoder" (~50-150ms)

    Returns:
        (reranked_chunks, rerank_latency_ms)
        reranked_chunks is sorted best-first, length = min(top_k, len(candidates))
    """
    from backend.config import settings

    _top_k = top_k or settings.TOP_K_FINAL

    if not candidates:
        return [], 0.0

    if len(candidates) <= _top_k:
        # Nothing to rerank — just return sorted by vector score
        return sorted(candidates, key=lambda c: c.score, reverse=True), 0.0

    if mode == "cross_encoder":
        return _rerank_cross_encoder(query, candidates, _top_k)
    else:
        return _rerank_bm25_rrf(query, candidates, _top_k)


# ─── BM25 + RRF (default) ──────────────────────────────────────────────────────

def _rerank_bm25_rrf(
    query: str,
    candidates: list,
    top_k: int,
) -> tuple[list, float]:
    """
    Combine vector similarity rank + BM25 lexical rank via Reciprocal Rank Fusion.

    Steps:
    1. Vector rank: already sorted by Chroma score (best = rank 0)
    2. BM25 rank: tokenise query + candidates, score with BM25Okapi
    3. RRF: rrf_score[i] = 1/(k + vector_rank[i]) + 1/(k + bm25_rank[i])
    4. Sort by rrf_score descending, return top_k
    """
    from rank_bm25 import BM25Okapi

    t0 = time.perf_counter()

    # ── Tokenise ─────────────────────────────────────────────────────────────
    # Simple whitespace tokenisation — fast and good enough for BM25
    tokenised_corpus = [c.text.lower().split() for c in candidates]
    tokenised_query  = query.lower().split()

    # ── BM25 scores ──────────────────────────────────────────────────────────
    bm25 = BM25Okapi(tokenised_corpus)
    bm25_scores = bm25.get_scores(tokenised_query)  # numpy array, higher = better

    # ── BM25 ranks (0 = highest score) ───────────────────────────────────────
    bm25_order = sorted(range(len(bm25_scores)), key=lambda i: -bm25_scores[i])
    bm25_rank  = {idx: rank for rank, idx in enumerate(bm25_order)}

    # ── Vector ranks (already ordered by Chroma: index 0 = best) ─────────────
    vector_rank = {i: i for i in range(len(candidates))}

    # ── RRF fusion ────────────────────────────────────────────────────────────
    rrf_scores = []
    for i, chunk in enumerate(candidates):
        vr = vector_rank[i]
        br = bm25_rank[i]
        rrf = 1.0 / (_RRF_K + vr) + 1.0 / (_RRF_K + br)
        rrf_scores.append((rrf, chunk))

    rrf_scores.sort(key=lambda x: -x[0])

    reranked = []
    for rrf_score, chunk in rrf_scores[:top_k]:
        # Attach the fused score back onto the chunk object
        chunk.score = rrf_score
        reranked.append(chunk)

    latency_ms = (time.perf_counter() - t0) * 1000

    log.info("reranker.bm25_rrf",
             n_candidates=len(candidates),
             top_k=top_k,
             latency_ms=f"{latency_ms:.1f}")

    return reranked, latency_ms


# ─── Cross-encoder (opt-in quality mode) ────────────────────────────────────────

_cross_encoder_model = None

def _rerank_cross_encoder(
    query: str,
    candidates: list,
    top_k: int,
) -> tuple[list, float]:
    """
    Cross-encoder reranking using ms-marco-MiniLM-L-6-v2.

    ⚠ LATENCY WARNING: ~50-150ms on CPU for 10 candidates.
    Exceeds the 200ms budget when combined with retrieval (~35ms) and
    generation setup. Use only when latency is not the primary concern
    (e.g. for a benchmark run to measure quality vs. speed tradeoff).

    To enable: set RERANK_MODE=cross_encoder in backend/.env
    """
    global _cross_encoder_model

    from sentence_transformers import CrossEncoder

    t0 = time.perf_counter()

    if _cross_encoder_model is None:
        log.info("reranker.cross_encoder", msg="Loading cross-encoder model...")
        _cross_encoder_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

    pairs = [(query, c.text) for c in candidates]
    scores = _cross_encoder_model.predict(pairs)

    ranked = sorted(zip(scores, candidates), key=lambda x: -x[0])
    reranked = []
    for score, chunk in ranked[:top_k]:
        chunk.score = float(score)
        reranked.append(chunk)

    latency_ms = (time.perf_counter() - t0) * 1000
    log.info("reranker.cross_encoder",
             n_candidates=len(candidates),
             top_k=top_k,
             latency_ms=f"{latency_ms:.1f}")

    return reranked, latency_ms
