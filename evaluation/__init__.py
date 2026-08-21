"""
evaluation/__init__.py
──────────────────────
Evaluation, benchmarking, and latency instrumentation module.
"""

from evaluation.benchmark import (
    BENCHMARK_QUERIES,
    BenchmarkResult,
    run_benchmark,
)
from evaluation.latency import (
    LatencyReport,
    LatencyTracker,
    StageStats,
)

__all__ = [
    "LatencyTracker",
    "LatencyReport",
    "StageStats",
    "run_benchmark",
    "BenchmarkResult",
    "BENCHMARK_QUERIES",
]
