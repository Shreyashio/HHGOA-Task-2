# Voice-RAG Latency Benchmark Report

> **Benchmark Configuration**: `N = 30 queries` | Strategy: `sentence` | Target: `< 200ms` for Search Pipeline.

## 1. Search Pipeline Performance (Sub-200ms Requirement)

This covers local vector retrieval (ChromaDB + `all-MiniLM-L6-v2`) and BM25+RRF reranking — the core pipeline compute required to run under 200ms.

| Pipeline Stage | Min | P50 (Median) | P70 | P90 | P100 (Max) | Mean | Sub-200ms Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Vector Retrieval (ChromaDB) | 18.0 ms | 24.3 ms | 25.4 ms | 32.2 ms | 65.7 ms | 26.1 ms | — |
| BM25+RRF Reranking | 0.3 ms | 0.5 ms | 0.5 ms | 0.6 ms | 0.8 ms | 0.5 ms | — |
| **Search Pipeline Total** | 18.3 ms | 24.7 ms | 25.8 ms | 32.7 ms | 66.2 ms | 26.6 ms | **PASSED (< 200ms)** |

## 2. Complete End-to-End Pipeline & Guardrails

Includes external API calls (Sarvam AI STT and Claude LLM generation) reported separately from pipeline compute.

| Stage | P50 (ms) | P70 (ms) | P90 (ms) | P100 (ms) | Mean (ms) | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Input Guardrails | 0.0 ms | 0.0 ms | 0.1 ms | 1.5 ms | 0.1 ms | Safety & Prompt Injection filter |
| Speech-to-Text | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | Sarvam AI (saaras:v3) / Network API |
| Search Pipeline | 24.7 ms | 25.8 ms | 32.7 ms | 66.2 ms | 26.6 ms | Retrieval + BM25 Rerank |
| Context Validation | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | 0.0 ms | Pre-LLM Relevance Check |
| LLM Generation | 1761.9 ms | 1772.0 ms | 1846.6 ms | 2472.7 ms | 1415.2 ms | Claude / Anthropic API |
| Grounding Check | 0.1 ms | 0.1 ms | 0.2 ms | 0.3 ms | 0.1 ms | Post-Gen Hallucination Verifier |
| **Total End-to-End** | 1809.5 ms | 1823.1 ms | 1907.1 ms | 2494.9 ms | 1454.8 ms | **Complete user experience** |

---
*Report generated automatically on 2026-08-22 13:10:49 by `evaluation.benchmark`.*