"""
evaluation/latency.py
──────────────────────
Fine-grained latency instrumentation and statistical benchmarking for Voice-RAG.

Stages Tracked:
  - STT Transcription (Sarvam AI API / Mock)
  - Input Guardrail (Safety & Prompt Injection)
  - Vector Retrieval (ChromaDB + all-MiniLM-L6-v2)
  - BM25 Reranking (BM25 + Reciprocal Rank Fusion)
  - Search Pipeline Compute (Vector Retrieval + BM25 Reranking — Sub-200ms Target)
  - Context Validation (Pre-LLM Relevance Check)
  - Grounded LLM Generation (Claude / Anthropic / Groq)
  - Grounding Verification (Post-LLM Hallucination Check)
  - Total End-to-End Pipeline

Provides:
  - LatencyTracker: Context manager & manual recorder with sub-millisecond precision
  - LatencyReport: Computes P50, P70, P90, P95, P99, P100, Min, Mean, StdDev
  - Export utilities: Pretty CLI Table, Markdown Report (latency_report.md), JSON Report
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np


@dataclass
class StageStats:
    """Statistical summary for a single pipeline stage."""
    stage_name: str
    n_samples: int
    min_ms: float
    p50_ms: float
    p70_ms: float
    p90_ms: float
    p95_ms: float
    p100_ms: float
    mean_ms: float
    std_ms: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "n_samples": self.n_samples,
            "min_ms": round(self.min_ms, 2),
            "p50_ms": round(self.p50_ms, 2),
            "p70_ms": round(self.p70_ms, 2),
            "p90_ms": round(self.p90_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p100_ms": round(self.p100_ms, 2),
            "mean_ms": round(self.mean_ms, 2),
            "std_ms": round(self.std_ms, 2),
        }


@dataclass
class LatencyReport:
    """Multi-stage latency benchmark report with percentiles."""
    stages: Dict[str, List[float]] = field(default_factory=dict)
    n_queries: int = 0
    strategy: str = "sentence"
    target_search_budget_ms: float = 200.0

    def add_sample(self, stage: str, latency_ms: float) -> None:
        """Add a single latency sample for a stage."""
        self.stages.setdefault(stage, []).append(latency_ms)

    def percentile(self, stage: str, p: float) -> float:
        """Return the p-th percentile latency (ms) for a stage."""
        samples = self.stages.get(stage, [])
        if not samples:
            return 0.0
        return float(np.percentile(samples, p))

    def get_stats(self, stage: str) -> Optional[StageStats]:
        """Compute full statistical summary for a stage."""
        samples = self.stages.get(stage, [])
        if not samples:
            return None
        arr = np.array(samples)
        return StageStats(
            stage_name=stage,
            n_samples=len(arr),
            min_ms=float(np.min(arr)),
            p50_ms=float(np.percentile(arr, 50)),
            p70_ms=float(np.percentile(arr, 70)),
            p90_ms=float(np.percentile(arr, 90)),
            p95_ms=float(np.percentile(arr, 95)),
            p100_ms=float(np.max(arr)),
            mean_ms=float(np.mean(arr)),
            std_ms=float(np.std(arr)),
        )

    def summary_table(self) -> str:
        """Generate a formatted ASCII summary table."""
        lines = []
        lines.append("=" * 82)
        lines.append(f"  VOICE-RAG LATENCY BENCHMARK REPORT (N = {self.n_queries} queries, strategy = {self.strategy})")
        lines.append("=" * 82)
        header = f"{'Stage':<26} {'P50':>8} {'P70':>8} {'P90':>8} {'P100 (Max)':>12} {'Mean':>8} {'Target':>10}"
        lines.append(header)
        lines.append("-" * 82)

        stage_order = [
            ("input_guardrail", "Input Guardrails", None),
            ("retrieval", "Vector Retrieval", None),
            ("reranking", "BM25 Reranking", None),
            ("search_pipeline", "Search Pipeline (Total)", f"< {self.target_search_budget_ms:.0f}ms"),
            ("context_validation", "Context Validation", None),
            ("stt", "STT (Sarvam AI)", "External"),
            ("generation", "LLM Generation", "External"),
            ("grounding_check", "Grounding Check", None),
            ("total_end_to_end", "Total End-to-End", "E2E"),
        ]

        for stage_key, display_name, target in stage_order:
            stats = self.get_stats(stage_key)
            if not stats:
                continue

            target_str = target or "—"
            if stage_key == "search_pipeline":
                p100 = stats.p100_ms
                status = " [PASS]" if p100 <= self.target_search_budget_ms else " [WARN]"
                target_str = f"< 200ms{status}"

            lines.append(
                f"{display_name:<26} "
                f"{stats.p50_ms:>7.1f}ms "
                f"{stats.p70_ms:>7.1f}ms "
                f"{stats.p90_ms:>7.1f}ms "
                f"{stats.p100_ms:>11.1f}ms "
                f"{stats.mean_ms:>7.1f}ms "
                f"{target_str:>10}"
            )

        lines.append("=" * 82)
        search_stats = self.get_stats("search_pipeline")
        if search_stats:
            if search_stats.p100_ms <= self.target_search_budget_ms:
                lines.append(f"  ✓ Sub-200ms Search Target MET: P50={search_stats.p50_ms:.1f}ms, P70={search_stats.p70_ms:.1f}ms, P100={search_stats.p100_ms:.1f}ms")
            else:
                lines.append(f"  ⚠ Search Target Warning: P100={search_stats.p100_ms:.1f}ms exceeds {self.target_search_budget_ms:.0f}ms budget.")
        lines.append("=" * 82)
        return "\n".join(lines)

    def to_markdown(self) -> str:
        """Generate a GitHub-flavored Markdown report suitable for README/submission."""
        md = []
        md.append(f"# Voice-RAG Latency Benchmark Report")
        md.append("")
        md.append(f"> **Benchmark Configuration**: `N = {self.n_queries} queries` | Strategy: `{self.strategy}` | Target: `< {self.target_search_budget_ms:.0f}ms` for Search Pipeline.")
        md.append("")
        md.append("## 1. Search Pipeline Performance (Sub-200ms Requirement)")
        md.append("")
        md.append("This covers local vector retrieval (ChromaDB + `all-MiniLM-L6-v2`) and BM25+RRF reranking — the core pipeline compute required to run under 200ms.")
        md.append("")
        md.append("| Pipeline Stage | Min | P50 (Median) | P70 | P90 | P100 (Max) | Mean | Sub-200ms Status |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

        for key, name in [
            ("retrieval", "Vector Retrieval (ChromaDB)"),
            ("reranking", "BM25+RRF Reranking"),
            ("search_pipeline", "**Search Pipeline Total**"),
        ]:
            st = self.get_stats(key)
            if st:
                status = "**PASSED (< 200ms)**" if (key == "search_pipeline" and st.p100_ms <= 200) else ("—" if key != "search_pipeline" else "**OVER BUDGET**")
                md.append(
                    f"| {name} | {st.min_ms:.1f} ms | {st.p50_ms:.1f} ms | {st.p70_ms:.1f} ms | {st.p90_ms:.1f} ms | {st.p100_ms:.1f} ms | {st.mean_ms:.1f} ms | {status} |"
                )

        md.append("")
        md.append("## 2. Complete End-to-End Pipeline & Guardrails")
        md.append("")
        md.append("Includes external API calls (Sarvam AI STT and Claude LLM generation) reported separately from pipeline compute.")
        md.append("")
        md.append("| Stage | P50 (ms) | P70 (ms) | P90 (ms) | P100 (ms) | Mean (ms) | Notes |")
        md.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")

        for key, name, note in [
            ("input_guardrail", "Input Guardrails", "Safety & Prompt Injection filter"),
            ("stt", "Speech-to-Text", "Sarvam AI (saaras:v3) / Network API"),
            ("search_pipeline", "Search Pipeline", "Retrieval + BM25 Rerank"),
            ("context_validation", "Context Validation", "Pre-LLM Relevance Check"),
            ("generation", "LLM Generation", "Claude / Anthropic API"),
            ("grounding_check", "Grounding Check", "Post-Gen Hallucination Verifier"),
            ("total_end_to_end", "**Total End-to-End**", "**Complete user experience**"),
        ]:
            st = self.get_stats(key)
            if st:
                md.append(f"| {name} | {st.p50_ms:.1f} ms | {st.p70_ms:.1f} ms | {st.p90_ms:.1f} ms | {st.p100_ms:.1f} ms | {st.mean_ms:.1f} ms | {note} |")

        md.append("")
        md.append("---")
        md.append(f"*Report generated automatically on {time.strftime('%Y-%m-%d %H:%M:%S')} by `evaluation.benchmark`.*")
        return "\n".join(md)

    def to_dict(self) -> Dict[str, Any]:
        """Convert entire report into structured JSON dictionary."""
        result = {
            "n_queries": self.n_queries,
            "strategy": self.strategy,
            "target_search_budget_ms": self.target_search_budget_ms,
            "timestamp": time.time(),
            "stages": {},
        }
        for stage in self.stages:
            st = self.get_stats(stage)
            if st:
                result["stages"][stage] = st.to_dict()
        return result


class LatencyTracker:
    """Accumulates latency measurements across pipeline stages."""

    def __init__(self, strategy: str = "sentence"):
        self._report = LatencyReport(strategy=strategy)

    @contextmanager
    def measure(self, stage: str):
        """Context manager — records wall-clock time for stage."""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self._report.add_sample(stage, elapsed_ms)

    def record(self, stage: str, latency_ms: float) -> None:
        """Manually record a pre-measured latency in ms."""
        self._report.add_sample(stage, latency_ms)

    def increment_queries(self, count: int = 1) -> None:
        self._report.n_queries += count

    def report(self) -> LatencyReport:
        return self._report

    def reset(self) -> None:
        self._report = LatencyReport(strategy=self._report.strategy)
