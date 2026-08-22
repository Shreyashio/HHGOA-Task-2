# Voice-RAG Latency Benchmark Report

> **Benchmark Configuration**: `N = 30 queries` | Strategy: `sentence` | Target: `< 200ms` for Search Pipeline.

## 1. Search Pipeline Performance (Sub-200ms Requirement)

This covers local vector retrieval (ChromaDB + `all-MiniLM-L6-v2`) and BM25+RRF reranking — the core pipeline compute required to run under 200ms.

| Pipeline Stage | Min | P50 (Median) | P70 | P90 | P100 (Max) | Mean | Sub-200ms Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Vector Retrieval (ChromaDB) | 23.1 ms | 25.7 ms | 26.5 ms | 34.4 ms | 68.5 ms | 29.9 ms | — |
| BM25+RRF Reranking | 0.5 ms | 0.6 ms | 0.7 ms | 0.7 ms | 0.9 ms | 0.6 ms | — |
| **Search Pipeline Total** | 23.8 ms | 26.2 ms | 27.1 ms | 35.1 ms | 69.2 ms | 30.5 ms | **PASSED (< 200ms)** |

## 2. Complete End-to-End Pipeline & Guardrails

Includes external API calls (Sarvam AI STT and Claude LLM generation) reported separately from pipeline compute.

| Stage | P50 (ms) | P70 (ms) | P90 (ms) | P100 (ms) | Mean (ms) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Input Guardrails | 0.0 ms | 0.1 ms | 0.1 ms | 1.6 ms | 0.1 ms | Safety & Prompt Injection filter |
| Speech-to-Text | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | Sarvam AI (saaras:v3) / Network API |
| Search Pipeline | 26.2 ms | 27.1 ms | 35.1 ms | 69.2 ms | 30.5 ms | Retrieval + BM25 Rerank |
| Context Validation | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | Pre-LLM Relevance Check |
| LLM Generation | 18.3 ms | 19.4 ms | 24.8 ms | 30.0 ms | 19.6 ms | Claude / Anthropic API |
| Grounding Check | 0.1 ms | 0.1 ms | 0.2 ms | 0.2 ms | 0.1 ms | Post-Gen Hallucination Verifier |
| **Total End-to-End** | 45.5 ms | 45.7 ms | 64.7 ms | 93.4 ms | 51.7 ms | **Complete user experience** |

---
*Report generated automatically on 2026-08-22 13:09:07 by `evaluation.benchmark`.*