"""
ingestion/run_ingestion.py
───────────────────────────
CLI entry point for the ingestion pipeline.

Usage examples:
  # Index 5000 rows with sentence chunking (recommended for dev):
  python -m ingestion.run_ingestion --strategy sentence --max-docs 5000

  # Index with all three strategies (for benchmark comparison):
  python -m ingestion.run_ingestion --strategy fixed    --max-docs 5000
  python -m ingestion.run_ingestion --strategy sentence --max-docs 5000
  python -m ingestion.run_ingestion --strategy metadata --max-docs 5000

  # Print current vector count without indexing:
  python -m ingestion.run_ingestion --count-only

  # Reset the collection and re-index:
  python -m ingestion.run_ingestion --reset --strategy sentence --max-docs 5000
"""

import argparse
import json
import sys
import os

# Allow import from voice-rag root when run as module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import structlog
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
)
log = structlog.get_logger()


def main():
    parser = argparse.ArgumentParser(
        description="Ingest MSMARCO-XI into ChromaDB",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--strategy", default="sentence",
        choices=["fixed", "sentence", "metadata", "all"],
        help="Chunking strategy. Use 'all' to index with all three strategies.",
    )
    parser.add_argument(
        "--max-docs", type=int, default=5000,
        help="Number of MSMARCO-XI rows to process.",
    )
    parser.add_argument(
        "--split", default="train", choices=["train", "validation"],
        help="Dataset split to use.",
    )
    parser.add_argument(
        "--lang", default="all",
        help="Language filter ('all' | 'en' | 'hi' | 'ta' | ...).",
    )
    parser.add_argument(
        "--batch-size", type=int, default=512,
        help="Chroma upsert batch size.",
    )
    parser.add_argument(
        "--count-only", action="store_true",
        help="Just print the current vector count and exit.",
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Delete and recreate the collection before indexing.",
    )
    parser.add_argument(
        "--persist-dir", default=None,
        help="Override CHROMA_PERSIST_DIR from .env.",
    )
    parser.add_argument(
        "--collection", default=None,
        help="Override CHROMA_COLLECTION_NAME from .env.",
    )
    args = parser.parse_args()

    # ── Load .env ──────────────────────────────────────────────────────────────
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

    from ingestion.indexing import get_collection, get_vector_count, run_ingestion_pipeline
    import chromadb

    # ── Count only ─────────────────────────────────────────────────────────────
    if args.count_only:
        count = get_vector_count(args.persist_dir, args.collection)
        print(f"\n  ChromaDB vector count: {count:,}\n")
        return

    # ── Optional reset ──────────────────────────────────────────────────────────
    if args.reset:
        from backend.config import settings
        _persist = args.persist_dir or settings.CHROMA_PERSIST_DIR
        _col     = args.collection  or settings.CHROMA_COLLECTION_NAME
        client = chromadb.PersistentClient(path=_persist)
        try:
            client.delete_collection(_col)
            log.info("reset", msg=f"Deleted collection '{_col}'")
        except Exception:
            log.info("reset", msg="Collection didn't exist — nothing to delete")

    # ── Run pipeline ────────────────────────────────────────────────────────────
    strategies = (
        ["fixed", "sentence", "metadata"]
        if args.strategy == "all"
        else [args.strategy]
    )

    results = []
    for strat in strategies:
        print(f"\n{'='*60}")
        print(f"  Indexing with strategy: {strat!r}")
        print(f"  max_docs={args.max_docs}  split={args.split}  lang={args.lang}")
        print(f"{'='*60}")
        summary = run_ingestion_pipeline(
            strategy=strat,
            max_docs=args.max_docs,
            split=args.split,
            lang=args.lang,
            batch_size=args.batch_size,
            persist_dir=args.persist_dir,
            collection_name=args.collection,
        )
        results.append(summary)

    # ── Summary table ──────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("  INGESTION SUMMARY")
    print("="*60)
    for r in results:
        print(f"\n  Strategy : {r['strategy']}")
        print(f"  Docs     : {r['max_docs']:,}")
        print(f"  Chunks   : {r['chunks_indexed']:,}")
        print(f"  Time     : {r['elapsed_s']}s  ({r['chunks_per_sec']} chunks/s)")

    total_vectors = get_vector_count(args.persist_dir, args.collection)
    print(f"\n  Total vectors in ChromaDB: {total_vectors:,}")
    print("="*60)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
