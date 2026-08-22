# Voice-RAG Latency Benchmark Report

> **Benchmark Configuration**: `N = 30 queries` | Strategy: `metadata` | Target: `< 200ms` for Search Pipeline.

## 1. Search Pipeline Performance (Sub-200ms Requirement)

This covers local vector retrieval (ChromaDB + `all-MiniLM-L6-v2`) and BM25+RRF reranking — the core pipeline compute required to run under 200ms.

| Pipeline Stage | Min | P50 (Median) | P70 | P90 | P100 (Max) | Mean | Sub-200ms Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Vector Retrieval (ChromaDB) | 13.7 ms | 15.4 ms | 15.7 ms | 17.7 ms | 58.3 ms | 18.3 ms | — |
| BM25+RRF Reranking | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | — |
| **Search Pipeline Total** | 13.7 ms | 15.4 ms | 15.7 ms | 17.7 ms | 58.3 ms | 18.3 ms | **PASSED (< 200ms)** |

## 2. Complete End-to-End Pipeline & Guardrails

Includes external API calls (Sarvam AI STT and Claude LLM generation) reported separately from pipeline compute.

| Stage | P50 (ms) | P70 (ms) | P90 (ms) | P100 (ms) | Mean (ms) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Input Guardrails | 0.0 ms | 0.1 ms | 0.1 ms | 2.0 ms | 0.1 ms | Safety & Prompt Injection filter |
| Speech-to-Text | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | Sarvam AI (saaras:v3) / Network API |
| Search Pipeline | 15.4 ms | 15.7 ms | 17.7 ms | 58.3 ms | 18.3 ms | Retrieval + BM25 Rerank |
| Context Validation | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | Pre-LLM Relevance Check |
| LLM Generation | 28.2 ms | 29.0 ms | 29.9 ms | 30.5 ms | 25.8 ms | Claude / Anthropic API |
| Grounding Check | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | Post-Gen Hallucination Verifier |
| **Total End-to-End** | 44.8 ms | 45.5 ms | 46.5 ms | 77.3 ms | 45.1 ms | **Complete user experience** |

---
*Report generated automatically on 2026-08-22 13:11:36 by `evaluation.benchmark`.*