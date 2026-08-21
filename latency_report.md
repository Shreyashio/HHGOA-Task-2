# Voice-RAG Latency Benchmark Report

> **Benchmark Configuration**: `N = 30 queries` | Strategy: `sentence` | Target: `< 200ms` for Search Pipeline.

## 1. Search Pipeline Performance (Sub-200ms Requirement)

This covers local vector retrieval (ChromaDB + `all-MiniLM-L6-v2`) and BM25+RRF reranking — the core pipeline compute required to run under 200ms.

| Pipeline Stage | Min | P50 (Median) | P70 | P90 | P100 (Max) | Mean | Sub-200ms Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Vector Retrieval (ChromaDB) | 15.8 ms | 17.8 ms | 18.6 ms | 22.0 ms | 54.8 ms | 19.5 ms | — |
| BM25+RRF Reranking | 0.3 ms | 0.5 ms | 0.6 ms | 0.6 ms | 0.8 ms | 0.5 ms | — |
| **Search Pipeline Total** | 16.3 ms | 18.3 ms | 19.2 ms | 22.5 ms | 55.1 ms | 20.0 ms | **PASSED (< 200ms)** |

## 2. Complete End-to-End Pipeline & Guardrails

Includes external API calls (Sarvam AI STT and Claude LLM generation) reported separately from pipeline compute.

| Stage | P50 (ms) | P70 (ms) | P90 (ms) | P100 (ms) | Mean (ms) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Input Guardrails | 0.0 ms | 0.0 ms | 0.0 ms | 1.7 ms | 0.1 ms | Safety & Prompt Injection filter |
| Speech-to-Text | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | Sarvam AI (saaras:v3) / Network API |
| Search Pipeline | 18.3 ms | 19.2 ms | 22.5 ms | 55.1 ms | 20.0 ms | Retrieval + BM25 Rerank |
| Context Validation | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | Pre-LLM Relevance Check |
| LLM Generation | 27.2 ms | 27.8 ms | 28.5 ms | 31.5 ms | 25.8 ms | Claude / Anthropic API |
| Grounding Check | 0.1 ms | 0.1 ms | 0.1 ms | 0.2 ms | 0.1 ms | Post-Gen Hallucination Verifier |
| **Total End-to-End** | 46.1 ms | 46.6 ms | 49.1 ms | 81.9 ms | 46.2 ms | **Complete user experience** |

---
*Report generated automatically on 2026-08-21 19:26:24 by `evaluation.benchmark`.*