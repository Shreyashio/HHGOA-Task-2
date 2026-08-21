"""
evaluation/benchmark.py
────────────────────────
Comprehensive latency benchmarking suite for Voice-RAG (Step 8).

Runs a batch of realistic test queries against the MSMARCO-XI dataset index,
computes P50 / P70 / P90 / P100 latency for the search pipeline and the full
end-to-end pipeline, and generates clean `latency_report.md` and `latency_report.json`
artifacts ready for submission.

Usage:
  python -m evaluation.benchmark                         # Run default 30 queries
  python -m evaluation.benchmark --strategy sentence     # Specify chunking strategy
  python -m evaluation.benchmark --n 25 --mock           # Offline test mode
  python -m evaluation.benchmark --output-md latency_report.md
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Allow running as standalone script or module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

import structlog
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(30),  # WARNING only during benchmark
)

from evaluation.latency import LatencyReport, LatencyTracker
from generation.harness import PipelineResult, default_orchestrator
from retrieval.retriever import warm_up

# ── 30 Realistic Benchmark Test Queries ─────────────────────────────────────────
BENCHMARK_QUERIES: List[str] = [
    "what is photosynthesis",
    "what is the function of phloem in plants",
    "causes of diabetes and how to prevent it",
    "who was the first president of India",
    "capital of France and famous monuments",
    "how does the human circulatory system work",
    "what is machine learning and neural networks",
    "what is the difference between RAM and ROM",
    "history and significance of the Taj Mahal",
    "what is the law of conservation of energy",
    "how do solar panels generate electricity",
    "symptoms and treatment of malaria",
    "what is the theory of general relativity",
    "who invented the World Wide Web",
    "what causes tides in the oceans",
    "what is DNA and how does it replicate",
    "what is the greenhouse effect and global warming",
    "how do airplanes generate lift",
    "what is the role of mitochondria in a cell",
    "what are the primary colors of light",
    "what is the speed of light in vacuum",
    "how does a transformer work in electrical circuits",
    "what is the capital of Japan",
    "who wrote the play Romeo and Juliet",
    "what is inflation in economics",
    "how does vaccination provide immunity",
    "what is an earthquake and what causes it",
    "what is the process of water purification",
    "who was Mahatma Gandhi and what was his role in independence",
    "what are the benefits of renewable energy",
]


@dataclass
class BenchmarkResult:
    """Aggregate result of a benchmark execution."""
    n_queries: int
    strategy: str
    search_p50_ms: float
    search_p70_ms: float
    search_p90_ms: float
    search_p100_ms: float
    search_mean_ms: float
    total_p50_ms: float
    total_p70_ms: float
    total_p90_ms: float
    total_p100_ms: float
    total_mean_ms: float
    sub_200ms_compliant: bool
    per_query: List[Dict[str, Any]] = field(default_factory=list)
    report_dict: Dict[str, Any] = field(default_factory=dict)


def load_custom_queries(path: str) -> List[str]:
    """Load query strings from a TSV, JSONL, or TXT file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Queries file not found: {path}")

    queries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if path.endswith(".jsonl"):
                try:
                    data = json.loads(line)
                    q = data.get("query") or data.get("text") or ""
                    if q:
                        queries.append(q)
                except Exception:
                    pass
            elif "\t" in line:
                # TSV (query_id \t query)
                parts = line.split("\t")
                queries.append(parts[1] if len(parts) > 1 else parts[0])
            else:
                queries.append(line)
    return queries


def run_benchmark(
    queries: Optional[List[str]] = None,
    queries_path: Optional[str] = None,
    n: int = 30,
    strategy: str = "sentence",
    mock_mode: bool = True,
    output_md: Optional[str] = "latency_report.md",
    output_json: Optional[str] = "latency_report.json",
    persist_dir: Optional[str] = None,
) -> BenchmarkResult:
    """
    Run full latency benchmark across a batch of test queries.

    Args:
        queries: Optional explicit list of query strings.
        queries_path: Optional file path to load queries from.
        n: Number of queries to run.
        strategy: Chunking strategy ('sentence', 'fixed', 'metadata').
        mock_mode: If True, uses mock LLM/STT generation to measure pure compute without API cost.
        output_md: Path to save Markdown latency report.
        output_json: Path to save JSON latency report.
        persist_dir: Optional ChromaDB path override.

    Returns:
        BenchmarkResult containing latency percentiles and report data.
    """
    # ── 1. Prepare Query Set ───────────────────────────────────────────────────
    if queries_path:
        query_set = load_custom_queries(queries_path)
    elif queries:
        query_set = queries
    else:
        query_set = BENCHMARK_QUERIES

    selected_queries = query_set[:n]
    if len(selected_queries) < n:
        # Loop queries if requested n exceeds available set
        while len(selected_queries) < n:
            selected_queries.extend(query_set[: n - len(selected_queries)])

    print("\n" + "=" * 82)
    print(f"  STARTING VOICE-RAG LATENCY BENCHMARK")
    print(f"  Total Queries: {len(selected_queries)} | Strategy: '{strategy}' | Mock Mode: {mock_mode}")
    print("=" * 82)

    # ── 2. Warm Up Embedding Model & ChromaDB ──────────────────────────────────
    print("\n[1/2] Warming up retriever model & ChromaDB index...")
    t0 = time.perf_counter()
    warm_up(persist_dir=persist_dir)
    print(f"      Retriever warmed in {(time.perf_counter() - t0) * 1000:.0f} ms")

    # ── 3. Execute Queries & Collect Timings ────────────────────────────────────
    print(f"\n[2/2] Running {len(selected_queries)} queries through the full pipeline...")
    tracker = LatencyTracker(strategy=strategy)
    per_query_results: List[Dict[str, Any]] = []

    for i, q in enumerate(selected_queries, 1):
        # Run through orchestrator
        res: PipelineResult = default_orchestrator.execute_text_sync(
            query=q,
            strategy=strategy,
            mock_mode=mock_mode,
        )

        lat = res.latency
        # Record timings
        tracker.record("input_validation", lat.input_validation_ms)
        tracker.record("input_guardrail", lat.input_guardrail_ms)
        tracker.record("retrieval", lat.retrieval_ms)
        tracker.record("reranking", lat.reranking_ms)
        tracker.record("search_pipeline", lat.search_pipeline_ms)
        tracker.record("context_validation", lat.context_validation_ms)
        tracker.record("stt", lat.stt_ms)
        tracker.record("generation", lat.generation_ms)
        tracker.record("grounding_check", lat.grounding_check_ms)
        tracker.record("total_end_to_end", lat.total_ms)
        tracker.increment_queries(1)

        per_query_results.append({
            "index": i,
            "query": q,
            "status": res.status,
            "guardrail_passed": res.guardrail_passed,
            "search_pipeline_ms": lat.search_pipeline_ms,
            "total_ms": lat.total_ms,
            "sources_count": len(res.sources),
        })

        # Progress log
        if i % 5 == 0 or i == len(selected_queries):
            print(f"      Processed {i:2d}/{len(selected_queries)} queries | Last search: {lat.search_pipeline_ms:.1f}ms | Total: {lat.total_ms:.1f}ms")

    report: LatencyReport = tracker.report()
    report.n_queries = len(selected_queries)

    # ── 4. Print Summary Table ─────────────────────────────────────────────────
    print("\n" + report.summary_table() + "\n")

    search_stats = report.get_stats("search_pipeline")
    total_stats = report.get_stats("total_end_to_end")

    search_p50 = search_stats.p50_ms if search_stats else 0.0
    search_p70 = search_stats.p70_ms if search_stats else 0.0
    search_p90 = search_stats.p90_ms if search_stats else 0.0
    search_p100 = search_stats.p100_ms if search_stats else 0.0
    search_mean = search_stats.mean_ms if search_stats else 0.0

    total_p50 = total_stats.p50_ms if total_stats else 0.0
    total_p70 = total_stats.p70_ms if total_stats else 0.0
    total_p90 = total_stats.p90_ms if total_stats else 0.0
    total_p100 = total_stats.p100_ms if total_stats else 0.0
    total_mean = total_stats.mean_ms if total_stats else 0.0

    compliant = search_p100 <= 200.0

    benchmark_res = BenchmarkResult(
        n_queries=len(selected_queries),
        strategy=strategy,
        search_p50_ms=search_p50,
        search_p70_ms=search_p70,
        search_p90_ms=search_p90,
        search_p100_ms=search_p100,
        search_mean_ms=search_mean,
        total_p50_ms=total_p50,
        total_p70_ms=total_p70,
        total_p90_ms=total_p90,
        total_p100_ms=total_p100,
        total_mean_ms=total_mean,
        sub_200ms_compliant=compliant,
        per_query=per_query_results,
        report_dict=report.to_dict(),
    )

    # ── 5. Save Output Artifacts ───────────────────────────────────────────────
    if output_md:
        md_content = report.to_markdown()
        with open(output_md, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"  [SAVED] Markdown Report: {output_md}")

    if output_json:
        json_content = report.to_dict()
        json_content["per_query_results"] = per_query_results
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(json_content, f, indent=2)
        print(f"  [SAVED] JSON Report:     {output_json}")

    return benchmark_res


def main():
    parser = argparse.ArgumentParser(
        description="Run Voice-RAG Latency Benchmark Suite (Step 8)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--queries", default=None, help="Path to custom test queries file (TSV/JSONL/TXT)")
    parser.add_argument("--n", type=int, default=30, help="Number of benchmark queries to run")
    parser.add_argument("--strategy", choices=["sentence", "fixed", "metadata"], default="sentence", help="Chunking strategy")
    parser.add_argument("--live", action="store_true", help="Use live external LLM/STT APIs (default is mock mode for pure latency testing)")
    parser.add_argument("--output-md", default="latency_report.md", help="Output path for Markdown report")
    parser.add_argument("--output-json", default="latency_report.json", help="Output path for JSON report")
    parser.add_argument("--persist-dir", default=None, help="Override ChromaDB persist directory")
    args = parser.parse_args()

    run_benchmark(
        queries_path=args.queries,
        n=args.n,
        strategy=args.strategy,
        mock_mode=not args.live,
        output_md=args.output_md,
        output_json=args.output_json,
        persist_dir=args.persist_dir,
    )


if __name__ == "__main__":
    main()
