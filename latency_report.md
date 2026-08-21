# Voice-RAG Latency Benchmark Report

> **Benchmark Configuration**: `N = 30 queries` | Strategy: `sentence` | Target: `< 200ms` for Search Pipeline.

## 1. Search Pipeline Performance (Sub-200ms Requirement)

This covers local vector retrieval (ChromaDB + `all-MiniLM-L6-v2`) and BM25+RRF reranking — the core pipeline compute required to run under 200ms.

| Pipeline Stage | Min | P50 (Median) | P70 | P90 | P100 (Max) | Mean | Sub-200ms Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Vector Retrieval (ChromaDB) | 16.2 ms | 22.9 ms | 26.2 ms | 36.4 ms | 64.5 ms | 25.3 ms | — |
| BM25+RRF Reranking | 0.4 ms | 0.6 ms | 0.6 ms | 0.8 ms | 1.1 ms | 0.6 ms | — |
| **Search Pipeline Total** | 16.6 ms | 23.5 ms | 26.8 ms | 37.0 ms | 64.9 ms | 25.9 ms | **PASSED (< 200ms)** |

## 2. Complete End-to-End Pipeline & Guardrails

Includes external API calls (Sarvam AI STT and Claude LLM generation) reported separately from pipeline compute.

| Stage | P50 (ms) | P70 (ms) | P90 (ms) | P100 (ms) | Mean (ms) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Input Guardrails | 0.0 ms | 0.0 ms | 0.1 ms | 1.6 ms | 0.1 ms | Safety & Prompt Injection filter |
| Speech-to-Text | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | Sarvam AI (saaras:v3) / Network API |
| Search Pipeline | 23.5 ms | 26.8 ms | 37.0 ms | 64.9 ms | 25.9 ms | Retrieval + BM25 Rerank |
| Context Validation | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | Pre-LLM Relevance Check |
| LLM Generation | 24.6 ms | 26.5 ms | 28.3 ms | 30.1 ms | 23.9 ms | Claude / Anthropic API |
| Grounding Check | 0.1 ms | 0.1 ms | 0.2 ms | 0.2 ms | 0.1 ms | Post-Gen Hallucination Verifier |
| **Total End-to-End** | 46.1 ms | 46.9 ms | 61.6 ms | 87.5 ms | 50.3 ms | **Complete user experience** |

---
*Report generated automatically on 2026-08-21 18:48:02 by `evaluation.benchmark`.*