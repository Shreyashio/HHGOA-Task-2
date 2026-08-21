"""
evaluation/benchmark.py
────────────────────────
Runs a set of test queries through the full RAG pipeline (excluding STT and
live LLM generation) to measure retrieval quality and system performance.

What this will do (Step 6):
  - Load a test query set (TSV / JSONL with expected passage IDs)
  - For each query, run: retrieve → rerank → (mock LLM) and record:
      { query_id, retrieved_ids, relevant_ids, latency_ms }
  - Compute standard IR metrics:
      - MRR@10  (Mean Reciprocal Rank)
      - Recall@K (K = TOP_K_FINAL)
      - nDCG@10
  - Compute latency percentiles (P50, P70, P100) for the retrieval pipeline
  - Output a JSON report: evaluation/results/benchmark_<timestamp>.json

Usage (CLI):
  python -m evaluation.benchmark --queries data/test_queries.tsv --n 100
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List


@dataclass
class BenchmarkResult:
    """Aggregate output of a benchmark run."""
    n_queries: int
    mrr_at_10: float
    recall_at_k: float
    ndcg_at_10: float
    latency_p50_ms: float
    latency_p70_ms: float
    latency_p100_ms: float
    per_query: List[dict] = field(default_factory=list)


def run_benchmark(
    queries_path: str,
    n: int = 100,
    strategy: str = "sentence",
) -> BenchmarkResult:
    """
    Run the full benchmark suite.

    Args:
        queries_path: path to TSV/JSONL file of (query_id, query, relevant_ids)
        n:            number of queries to evaluate
        strategy:     chunking strategy to evaluate ("fixed"|"sentence"|"metadata")

    Returns:
        BenchmarkResult with IR metrics and latency percentiles.
    """
    raise NotImplementedError("Implemented in Step 6")


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", required=True)
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--strategy", default="sentence")
    args = parser.parse_args()
    result = run_benchmark(args.queries, args.n, args.strategy)
    print(json.dumps(result.__dict__, indent=2))
