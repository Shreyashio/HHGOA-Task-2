"""
evaluation/latency.py
──────────────────────
Fine-grained latency instrumentation for each stage of the pipeline.

What this will do (Step 6):
  - Provide a `LatencyTracker` context manager that wraps any pipeline stage
    and records wall-clock time with sub-millisecond precision (time.perf_counter)
  - Accumulate timings across multiple queries into a `LatencyReport`
  - Compute P50 / P70 / P100 (and optionally P95, P99) for each stage:
      stt, retrieval, reranking, generation, total_pipeline
  - Separate reporting for:
      a) retrieval-only path (chunking + embed + Chroma query + rerank)
      b) full end-to-end path (adds STT + LLM network latency)
  - Export to JSON and pretty-print a table to stdout

The sub-200ms target is for (a); (b) is reported separately as it depends
on external API latency that we don't control.

Usage:
  tracker = LatencyTracker()
  with tracker.measure("retrieval"):
      chunks = retrieve(query)
  report = tracker.report()
  print(report.summary_table())
"""

from __future__ import annotations
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List
import time
import numpy as np


@dataclass
class LatencyReport:
    """Percentile breakdown for each pipeline stage."""
    stages: Dict[str, List[float]] = field(default_factory=dict)

    def percentile(self, stage: str, p: int) -> float:
        """Return the p-th percentile latency (ms) for a stage."""
        samples = self.stages.get(stage, [])
        if not samples:
            return 0.0
        return float(np.percentile(samples, p))

    def summary_table(self) -> str:
        """Pretty-print a table of P50 / P70 / P100 for all stages."""
        lines = [f"{'Stage':<20} {'P50':>8} {'P70':>8} {'P100':>8}"]
        lines.append("-" * 46)
        for stage in self.stages:
            p50 = self.percentile(stage, 50)
            p70 = self.percentile(stage, 70)
            p100 = self.percentile(stage, 100)
            lines.append(f"{stage:<20} {p50:>7.1f}ms {p70:>7.1f}ms {p100:>7.1f}ms")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        result = {}
        for stage in self.stages:
            result[stage] = {
                "p50_ms": self.percentile(stage, 50),
                "p70_ms": self.percentile(stage, 70),
                "p100_ms": self.percentile(stage, 100),
                "n_samples": len(self.stages[stage]),
            }
        return result


class LatencyTracker:
    """Accumulates latency measurements across pipeline stages."""

    def __init__(self):
        self._report = LatencyReport()

    @contextmanager
    def measure(self, stage: str):
        """Context manager — records wall-clock time for `stage`."""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._report.stages.setdefault(stage, []).append(elapsed_ms)

    def record(self, stage: str, latency_ms: float) -> None:
        """Manually record a pre-measured latency (e.g., from an API response header)."""
        self._report.stages.setdefault(stage, []).append(latency_ms)

    def report(self) -> LatencyReport:
        return self._report

    def reset(self) -> None:
        self._report = LatencyReport()
