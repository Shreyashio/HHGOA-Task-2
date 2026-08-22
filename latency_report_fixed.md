# Voice-RAG Latency Benchmark Report

> **Benchmark Configuration**: `N = 30 queries` | Strategy: `fixed` | Target: `< 200ms` for Search Pipeline.

## 1. Search Pipeline Performance (Sub-200ms Requirement)

This covers local vector retrieval (ChromaDB + `all-MiniLM-L6-v2`) and BM25+RRF reranking — the core pipeline compute required to run under 200ms.

| Pipeline Stage | Min | P50 (Median) | P70 | P90 | P100 (Max) | Mean | Sub-200ms Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Vector Retrieval (ChromaDB) | 14.7 ms | 16.0 ms | 16.2 ms | 19.0 ms | 46.6 ms | 17.7 ms | — |
| BM25+RRF Reranking | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | — |
| **Search Pipeline Total** | 14.7 ms | 16.0 ms | 16.2 ms | 19.0 ms | 46.6 ms | 17.7 ms | **PASSED (< 200ms)** |

## 2. Complete End-to-End Pipeline & Guardrails

Includes external API calls (Sarvam AI STT and Claude LLM generation) reported separately from pipeline compute.

| Stage | P50 (ms) | P70 (ms) | P90 (ms) | P100 (ms) | Mean (ms) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Input Guardrails | 0.0 ms | 0.1 ms | 0.1 ms | 1.5 ms | 0.1 ms | Safety & Prompt Injection filter |
| Speech-to-Text | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | Sarvam AI (saaras:v3) / Network API |
| Search Pipeline | 16.0 ms | 16.2 ms | 19.0 ms | 46.6 ms | 17.7 ms | Retrieval + BM25 Rerank |
| Context Validation | 0.0 ms | 0.0 ms | 0.0 ms | 0.1 ms | 0.0 ms | Pre-LLM Relevance Check |
| LLM Generation | 27.4 ms | 28.2 ms | 29.4 ms | 30.9 ms | 24.4 ms | Claude / Anthropic API |
| Grounding Check | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | Post-Gen Hallucination Verifier |
| **Total End-to-End** | 44.6 ms | 45.6 ms | 47.6 ms | 73.9 ms | 43.3 ms | **Complete user experience** |

---
*Report generated automatically on 2026-08-22 13:11:20 by `evaluation.benchmark`.*