"""
retrieval/retriever.py
───────────────────────
Embeds an incoming query and retrieves the top-K most similar chunks
from ChromaDB, with optional strategy and language filters.

Design
──────
- Singleton embedding model (loaded once at warm_up(), reused every request)
- ChromaDB query with cosine distance (HNSW index, sub-20ms on 50K vectors)
- Strategy-aware: pass strategy="sentence" to query only that strategy's index
- Language-aware: pass lang_filter="hi" to restrict to a language subset
- Returns RetrievedChunk objects with text, score, metadata, and per-call latency

Latency budget for this file
─────────────────────────────
Target: <100ms (leaving 100ms for reranking + generation prep within the 200ms window)
Breakdown:
  - embed_query  : ~5-15ms (warmed all-MiniLM-L6-v2 on CPU)
  - chroma query : ~5-20ms (HNSW on 50K vectors)
  Total          : ~10-35ms  ✓
"""

import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import structlog

log = structlog.get_logger()

# ── Module-level singletons ─────────────────────────────────────────────────────
_embedding_model = None
_chroma_collection = None


# ─── Data model ────────────────────────────────────────────────────────────────

@dataclass
class RetrievedChunk:
    """A chunk returned by vector search, with relevance score and metadata."""
    chunk_id: str
    doc_id: str
    text: str
    score: float                        # cosine similarity (0–1, higher = better)
    strategy: str = "sentence"
    lang: str = "en"
    query_id: int = 0
    query_type: str = ""
    is_selected: int = 0               # ground-truth label (for evaluation)
    metadata: dict = field(default_factory=dict)
    embed_latency_ms: float = 0.0
    query_latency_ms: float = 0.0

    @property
    def total_latency_ms(self) -> float:
        return self.embed_latency_ms + self.query_latency_ms


# ─── Warm-up ────────────────────────────────────────────────────────────────────

def warm_up(
    model_name: Optional[str] = None,
    persist_dir: Optional[str] = None,
    collection_name: Optional[str] = None,
) -> None:
    """
    Pre-load the embedding model and open the ChromaDB collection.
    Called once at FastAPI startup (backend/main.py lifespan).
    Subsequent calls are no-ops.
    """
    global _embedding_model, _chroma_collection

    from backend.config import settings
    from sentence_transformers import SentenceTransformer
    import chromadb

    _model_name = model_name or settings.EMBEDDING_MODEL
    _persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
    _col_name = collection_name or settings.CHROMA_COLLECTION_NAME

    if _embedding_model is None:
        log.info("retriever.warm_up", model=_model_name)
        t0 = time.perf_counter()
        _embedding_model = SentenceTransformer(_model_name)
        # Warm up with a dummy query so the first real request isn't slow
        _embedding_model.encode(["warm up"], normalize_embeddings=True)
        log.info("retriever.warm_up",
                 model_loaded_ms=f"{(time.perf_counter()-t0)*1000:.0f}")

    if _chroma_collection is None:
        client = chromadb.PersistentClient(path=_persist_dir)
        _chroma_collection = client.get_or_create_collection(
            name=_col_name,
            metadata={"hnsw:space": "cosine"},
        )
        log.info("retriever.warm_up",
                 collection=_col_name,
                 vectors=_chroma_collection.count())


def _ensure_warmed() -> None:
    """Auto-warm if not yet loaded (for use outside FastAPI context)."""
    if _embedding_model is None or _chroma_collection is None:
        warm_up()


# ─── Query embedding ────────────────────────────────────────────────────────────

def embed_query(query: str) -> tuple[List[float], float]:
    """
    Embed a single query string.

    Returns:
        (embedding_vector, latency_ms)
    """
    _ensure_warmed()
    t0 = time.perf_counter()
    vec = _embedding_model.encode(
        [query],
        normalize_embeddings=True,
        show_progress_bar=False,
    )[0].tolist()
    latency_ms = (time.perf_counter() - t0) * 1000
    return vec, latency_ms


# ─── Core retrieval ─────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    top_k: Optional[int] = None,
    strategy_filter: Optional[str] = None,
    lang_filter: Optional[str] = None,
) -> tuple[List[RetrievedChunk], float]:
    """
    Embed `query` and retrieve top-K chunks from ChromaDB.

    Args:
        query:           natural-language query string (from STT or text input)
        top_k:           number of candidates to return (default: TOP_K_RETRIEVE env var)
        strategy_filter: restrict to a specific chunking strategy
                         "fixed" | "sentence" | "metadata" | None (all strategies)
        lang_filter:     restrict to a specific language ("en", "hi", etc.) | None

    Returns:
        (chunks, total_retrieval_ms) where total_retrieval_ms covers embed + Chroma query.

    Raises:
        ValueError: if the collection is empty (run ingestion first).
    """
    from backend.config import settings
    _ensure_warmed()

    _top_k = top_k or settings.TOP_K_RETRIEVE

    # ── Build ChromaDB WHERE filter ──────────────────────────────────────────
    where_clause: Optional[dict] = None
    conditions = []

    if strategy_filter:
        conditions.append({"strategy": {"$eq": strategy_filter}})
    if lang_filter:
        conditions.append({"lang": {"$eq": lang_filter}})

    if len(conditions) == 1:
        where_clause = conditions[0]
    elif len(conditions) > 1:
        where_clause = {"$and": conditions}

    # ── Embed query ──────────────────────────────────────────────────────────
    vec, embed_ms = embed_query(query)

    # ── ChromaDB HNSW search ─────────────────────────────────────────────────
    t_query = time.perf_counter()

    query_kwargs: dict = {
        "query_embeddings": [vec],
        "n_results": min(_top_k, _chroma_collection.count() or _top_k),
        "include": ["documents", "metadatas", "distances"],
    }
    if where_clause:
        query_kwargs["where"] = where_clause

    results = _chroma_collection.query(**query_kwargs)
    query_ms = (time.perf_counter() - t_query) * 1000
    total_ms = embed_ms + query_ms

    # ── Parse results ────────────────────────────────────────────────────────
    chunks: List[RetrievedChunk] = []
    ids       = results["ids"][0]
    docs      = results["documents"][0]
    metas     = results["metadatas"][0]
    distances = results["distances"][0]   # cosine distance (0=identical, 2=opposite)

    for chunk_id, text, meta, dist in zip(ids, docs, metas, distances):
        # Convert cosine distance → similarity score (0–1)
        score = 1.0 - (dist / 2.0)

        chunks.append(RetrievedChunk(
            chunk_id=chunk_id,
            doc_id=meta.get("doc_id", ""),
            text=text,
            score=score,
            strategy=meta.get("strategy", ""),
            lang=meta.get("lang", ""),
            query_id=int(meta.get("query_id", 0)),
            query_type=meta.get("query_type", ""),
            is_selected=int(meta.get("is_selected", 0)),
            metadata=meta,
            embed_latency_ms=embed_ms,
            query_latency_ms=query_ms,
        ))

    log.info("retriever.retrieve",
             query_preview=query[:60],
             top_k=_top_k,
             strategy=strategy_filter,
             returned=len(chunks),
             embed_ms=f"{embed_ms:.1f}",
             query_ms=f"{query_ms:.1f}",
             total_ms=f"{total_ms:.1f}")

    return chunks, total_ms
