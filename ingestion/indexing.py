"""
ingestion/indexing.py
──────────────────────
Embeds chunks with SentenceTransformers and upserts into ChromaDB.

Design decisions
────────────────
Vector DB: ChromaDB (persistent HNSW)
  - Chosen over FAISS because: Chroma supports metadata WHERE filters natively,
    which is required to A/B compare chunking strategies at retrieval time
    (e.g. `.where({"strategy": "sentence"})`) and to filter by language.
  - HNSW index on 50K vectors → ~5–15ms query latency on CPU (well within
    the 200ms retrieval budget).
  - Zero infra: single-process, file-backed, no Docker required.

Embedding model: sentence-transformers/all-MiniLM-L6-v2
  - 384-dimensional dense vectors
  - ~80MB download, runs on CPU at ~2–5ms/sentence after warm-up
  - Strong performance on MS MARCO-style passage retrieval tasks
  - Same model used at both index time and query time (critical for alignment)

Batch strategy: 512 chunks per Chroma upsert call (Chroma sweet spot).
  Embedding is batched at 64 by sentence-transformers (GPU/CPU auto-detected).
"""

from __future__ import annotations

import time
import hashlib
from typing import Iterable, List, Optional
import structlog

log = structlog.get_logger()

# ── Module-level singletons (loaded once at warm_up / first use) ────────────────
_embedding_model = None
_chroma_client = None
_chroma_collection = None


# ─── Embedding model ────────────────────────────────────────────────────────────

def _get_embedding_model(model_name: str = "all-MiniLM-L6-v2"):
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        log.info("indexing", msg=f"Loading embedding model: {model_name}")
        t0 = time.perf_counter()
        _embedding_model = SentenceTransformer(model_name)
        log.info("indexing", msg=f"Model loaded in {(time.perf_counter()-t0)*1000:.0f}ms")
    return _embedding_model


def embed_texts(texts: List[str], batch_size: int = 64) -> List[List[float]]:
    """
    Embed a list of texts using the singleton SentenceTransformer.

    Args:
        texts:      list of strings to embed
        batch_size: number of texts per encoding batch

    Returns:
        List of embedding vectors (list of float).
    """
    model = _get_embedding_model()
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=True,      # cosine similarity via dot product
    )
    return vectors.tolist()


# ─── ChromaDB collection ────────────────────────────────────────────────────────

def get_collection(
    persist_dir: Optional[str] = None,
    collection_name: Optional[str] = None,
):
    """
    Open (or create) the ChromaDB persistent collection.

    Uses module-level singleton — safe to call multiple times.
    The collection uses cosine distance (matching normalised embeddings).

    Returns:
        chromadb.Collection instance.
    """
    global _chroma_client, _chroma_collection

    if _chroma_collection is not None:
        return _chroma_collection

    import chromadb
    from backend.config import settings

    _persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
    _collection_name = collection_name or settings.CHROMA_COLLECTION_NAME

    log.info("indexing", msg=f"Opening ChromaDB at {_persist_dir!r}")
    _chroma_client = chromadb.PersistentClient(path=_persist_dir)

    _chroma_collection = _chroma_client.get_or_create_collection(
        name=_collection_name,
        metadata={"hnsw:space": "cosine"},   # cosine distance
    )
    count = _chroma_collection.count()
    log.info("indexing", msg=f"Collection '{_collection_name}' opened. "
             f"Existing vectors: {count:,}")
    return _chroma_collection


def get_vector_count(persist_dir=None, collection_name=None) -> int:
    """Return total number of vectors currently in the collection."""
    col = get_collection(persist_dir, collection_name)
    return col.count()


# ─── Core indexing function ─────────────────────────────────────────────────────

def index_chunks(
    chunks: Iterable,
    batch_size: int = 512,
    embed_batch_size: int = 64,
    persist_dir: Optional[str] = None,
    collection_name: Optional[str] = None,
) -> int:
    """
    Embed and upsert an iterable of Chunk objects into ChromaDB.

    This function is idempotent: Chunk IDs are deterministic (MD5 of
    strategy::doc_id::chunk_index), so re-running does an upsert, not a duplicate.

    Args:
        chunks:          iterable of ingestion.chunking.Chunk objects
        batch_size:      chunks per Chroma upsert call (512 is Chroma's sweet spot)
        embed_batch_size: texts per SentenceTransformer encode call
        persist_dir:     override CHROMA_PERSIST_DIR
        collection_name: override CHROMA_COLLECTION_NAME

    Returns:
        Total number of chunks indexed in this call.
    """
    collection = get_collection(persist_dir, collection_name)

    ids_batch:      List[str]       = []
    texts_batch:    List[str]       = []
    metadata_batch: List[dict]      = []
    total_indexed = 0
    t_start = time.perf_counter()

    def _flush():
        nonlocal total_indexed
        if not ids_batch:
            return
        embeddings = embed_texts(texts_batch, batch_size=embed_batch_size)
        collection.upsert(
            ids=ids_batch,
            embeddings=embeddings,
            documents=texts_batch,
            metadatas=metadata_batch,
        )
        total_indexed += len(ids_batch)
        elapsed = (time.perf_counter() - t_start)
        rate = total_indexed / elapsed if elapsed > 0 else 0
        log.info("indexing",
                 indexed=total_indexed,
                 rate_per_sec=f"{rate:.0f}",
                 elapsed_s=f"{elapsed:.1f}")
        ids_batch.clear()
        texts_batch.clear()
        metadata_batch.clear()

    for chunk in chunks:
        chunk_id, text, meta = chunk.to_chroma()

        # Skip empty or whitespace-only chunks
        if not text or not text.strip():
            continue

        # Chroma requires string metadata values; coerce integers
        safe_meta = {}
        for k, v in meta.items():
            if isinstance(v, bool):
                safe_meta[k] = int(v)
            elif isinstance(v, (str, int, float)):
                safe_meta[k] = v
            else:
                safe_meta[k] = str(v)

        ids_batch.append(chunk_id)
        texts_batch.append(text)
        metadata_batch.append(safe_meta)

        if len(ids_batch) >= batch_size:
            _flush()

    _flush()  # remainder

    log.info("indexing", msg="Done.", total_indexed=total_indexed,
             total_s=f"{time.perf_counter()-t_start:.1f}")
    return total_indexed


# ─── Full pipeline helper (loader → chunker → index) ────────────────────────────

def run_ingestion_pipeline(
    strategy: str = "sentence",
    max_docs: int = 5000,
    split: str = "train",
    lang: str = "all",
    batch_size: int = 512,
    persist_dir: Optional[str] = None,
    collection_name: Optional[str] = None,
    chunker_kwargs: Optional[dict] = None,
) -> dict:
    """
    End-to-end ingestion: load → chunk → embed → index.

    Args:
        strategy:     chunking strategy ("fixed" | "sentence" | "metadata")
        max_docs:     number of MSMARCO-XI rows to process
        split:        dataset split ("train" | "validation")
        lang:         language filter ("all" | "en" | "hi" | ...)
        batch_size:   Chroma upsert batch size
        persist_dir:  ChromaDB persist directory
        collection_name: ChromaDB collection name
        chunker_kwargs: extra kwargs forwarded to the chunker constructor

    Returns:
        Summary dict with counts and timing.
    """
    from ingestion.loader import load_dataset
    from ingestion.chunking import get_chunker

    t0 = time.perf_counter()
    log.info("pipeline", strategy=strategy, max_docs=max_docs,
             split=split, lang=lang)

    chunker = get_chunker(strategy, **(chunker_kwargs or {}))

    def _chunk_stream():
        doc_count = 0
        chunk_count = 0
        for doc in load_dataset(split=split, lang=lang,
                                 max_docs=max_docs, streaming=True):
            doc_chunks = chunker.chunk(doc)
            for c in doc_chunks:
                yield c
                chunk_count += 1
            doc_count += 1
            if doc_count % 500 == 0:
                log.info("pipeline", docs_processed=doc_count,
                         chunks_so_far=chunk_count)

    total = index_chunks(
        _chunk_stream(),
        batch_size=batch_size,
        persist_dir=persist_dir,
        collection_name=collection_name,
    )

    elapsed = time.perf_counter() - t0
    final_count = get_vector_count(persist_dir, collection_name)

    summary = {
        "strategy":       strategy,
        "max_docs":       max_docs,
        "chunks_indexed": total,
        "total_vectors":  final_count,
        "elapsed_s":      round(elapsed, 1),
        "chunks_per_sec": round(total / elapsed, 1) if elapsed > 0 else 0,
    }
    log.info("pipeline", **summary)
    return summary
