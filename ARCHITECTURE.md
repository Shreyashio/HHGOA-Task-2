# 🏗️ Voice-RAG (MATRUBHASHA) — System Architecture

> **HH Goa 2026 · Task 2** — Voice-enabled Retrieval-Augmented Generation for Indic languages.

---

## Table of Contents

1. [High-Level Overview](#1-high-level-overview)
2. [Layer-by-Layer Breakdown](#2-layer-by-layer-breakdown)
3. [Request Flow Diagrams](#3-request-flow-diagrams)
4. [Data Flow: Ingestion Pipeline](#4-data-flow-ingestion-pipeline)
5. [Component Reference](#5-component-reference)
6. [Configuration and Environment](#6-configuration-and-environment)
7. [Latency Budget](#7-latency-budget)
8. [Tech Stack Summary](#8-tech-stack-summary)

---

## 1. High-Level Overview

`
+-------------------------------------------------------------------------+
|                    CLIENT  (Browser / curl)                             |
|         React + Vite SPA  -  localhost:5173 / Vercel                   |
+---------------------------+-----------------------------+---------------+
                            |  POST /ask-voice           |  POST /ask-text
                            v                            v
+-------------------------------------------------------------------------+
|                  BACKEND  —  FastAPI  (port 8000)                       |
|  backend/main.py  -  CORS  -  Lifespan startup  -  SPA static serving  |
|                                                                         |
|  +------------------------------------------------------------------+   |
|  |               api/server.py  (APIRouter)                         |   |
|  |  /ask-voice  /ask-text  /chunking/strategies  /stats  /health   |   |
|  +----------------------------------+-------------------------------+   |
+-------------------------------------+-----------------------------------+
                                      | calls
                                      v
+-------------------------------------------------------------------------+
|          PIPELINE ORCHESTRATOR  —  generation/harness.py               |
|                                                                         |
|  Stage 1 -> Input Validation     (audio/text sanity check)             |
|  Stage 2 -> STT                  (voice/stt.py -> Sarvam AI saaras:v3) |
|  Stage 3 -> Input Guardrail      (generation/guardrails.py)            |
|  Stage 4 -> Vector Retrieval     (retrieval/retriever.py -> ChromaDB)  |
|  Stage 5 -> BM25 + RRF Rerank   (retrieval/reranker.py)               |
|  Stage 6 -> Context Validation   (generation/guardrails.py)            |
|  Stage 7 -> LLM Generation       (generation/llm.py -> Groq / Claude)  |
|  Stage 8 -> Grounding Check      (generation/guardrails.py)            |
|                                                                         |
|  Returns: PipelineResult (answer, sources, latency breakdown, status)  |
+-------------------------------------------------------------------------+
         |                           |
         v                           v
 +---------------+         +----------------------+
 |  ChromaDB     |         |  External APIs       |
 |  (local disk) |         |  ----------------   |
 |  chroma_db/   |         |  Sarvam AI (STT)    |
 |  HNSW index   |         |  Groq / Anthropic   |
 |  ~50K vectors |         |  (LLM Generation)   |
 +---------------+         +----------------------+
`

---

## 2. Layer-by-Layer Breakdown

### Frontend — rontend/

| Item | Detail |
|:-----|:--------|
| Framework | React + Vite |
| Styling | Tailwind CSS |
| Build output | rontend/dist/ (served by FastAPI as SPA) |
| Dev server | localhost:5173 |
| Prod deploy | Vercel |

The SPA is mounted directly into the FastAPI server via StaticFiles.
Any unknown route falls back to index.html (client-side routing).

---

### API Layer — pi/server.py

Thin routing layer. No business logic — delegates everything to the orchestrator.

| Endpoint | Method | Purpose |
|:---------|:-------|:--------|
| /ask-voice | POST | Upload audio -> full voice RAG pipeline |
| /ask-text | POST | JSON query -> text RAG pipeline |
| /chunking/strategies | GET | Available chunking modes |
| /stats | GET | Config + latency targets |
| /health | GET | Liveness probe |

All endpoints are aliased: /ask-voice == /query/voice == /api/v1/query/voice.

---

### Backend Config — ackend/config.py

Single Settings class (Pydantic BaseSettings) loads everything from .env.

Key settings:
`
EMBEDDING_MODEL     = all-MiniLM-L6-v2
LLM_PROVIDER        = groq
LLM_MODEL           = llama-3.1-8b-instant
TOP_K_RETRIEVE      = 10
TOP_K_FINAL         = 3
CHUNKING_STRATEGY   = sentence
CHROMA_COLLECTION   = msmarco_xi
`

---

### Pipeline Orchestrator — generation/harness.py

The heart of the system. Implements PipelineOrchestrator with:

- **execute_voice()** — for audio input (bytes + content type)
- **execute_text()** — for text input (string)

Both methods run the same 8-stage async pipeline. Blocking I/O (ChromaDB,
reranking) is offloaded via syncio.to_thread().

**PipelineResult** — the unified output model:
`python
status: str              # "success" | "refusal" | "error"
transcript: str          # original or transcribed query
language_detected: str   # e.g. "en-IN"
answer: str              # LLM-generated answer
grounded: bool           # passed grounding check?
confidence: float        # 0.0 to 1.0
guardrail_passed: bool
sources: List[SourceChunk]
latency: StageLatency    # ms breakdown per stage
`

**StageLatency** tracks 10 timing fields:
`
input_validation_ms  stt_ms  input_guardrail_ms  retrieval_ms
reranking_ms  context_validation_ms  generation_ms
grounding_check_ms  search_pipeline_ms  total_ms
`

---

### Guardrails — generation/guardrails.py

Three checkpoints wrap the pipeline:

| Check | When | What it does |
|:------|:-----|:-------------|
| check_input() | After STT | Rejects off-topic / unsafe / prompt-injection queries |
| check_context() | After retrieval | Short-circuits if context similarity is too low |
| check_output() | After generation | Lexical grounding: answer tokens must appear in context |

Returns GuardrailResult(passed, reason, confidence).

---

### Retrieval Layer — etrieval/

#### etriever.py
- Loads ll-MiniLM-L6-v2 (sentence-transformers) as a **singleton** at startup
- Embeds query -> cosine similarity search in ChromaDB HNSW index
- Supports strategy_filter (sentence / fixed / metadata) and lang_filter
- Returns List[RetrievedChunk] + latency in ms
- **Target latency**: < 100ms (actual P50 ~15ms)

#### eranker.py
- **BM25 + RRF** (Reciprocal Rank Fusion) hybrid reranking
- Takes 	op_k=10 candidates -> returns 	op_k=3 final chunks
- Pure CPU, no network calls -> P50 ~0ms (negligible)

---

### Voice Layer — oice/stt.py

- HTTP POST to **Sarvam AI** saaras:v3 endpoint
- Supports: WAV, WebM, MP3, OGG, FLAC, M4A (up to 25MB)
- Tenacity retry: exponential backoff on 5xx / 429 / network errors
- Returns TranscriptionResult(text, language_detected, confidence, latency_ms)
- mock_mode=True -> returns a canned response for offline dev

---

### LLM Generation — generation/llm.py

- Supports multiple providers: **Groq** (primary), **Anthropic / Claude**, **OpenAI**
- Constructs grounded RAG prompt from retrieved chunks + citations
- Returns GenerationResult(answer, citations, model, latency_ms)
- P50 generation latency ~28ms (mock/cached) or ~1-5s (live API)

---

### Ingestion Pipeline — ingestion/

One-time (or re-run) pipeline to build the vector store.

| Module | Role |
|:-------|:-----|
| loader.py | Load raw documents (JSONL / CSV / plain text) from data/ |
| chunking.py | Chunk documents: sentence, ixed, or metadata strategies |
| indexing.py | Embed chunks -> upsert into ChromaDB |
| un_ingestion.py | CLI entrypoint: python -m ingestion.run_ingestion |

---

### Evaluation — evaluation/

| Module | Role |
|:-------|:-----|
| enchmark.py | Runs N=30 queries, collects per-stage latency, saves latency_report.json |
| latency.py | Computes P50/P70/P90/P95/P100 percentiles, generates markdown reports |

---

## 3. Request Flow Diagrams

### Voice Query (POST /ask-voice)

`
Browser
  |
  +--- multipart audio file ---> FastAPI /ask-voice
  |                                     |
  |                              [1] Input Validation
  |                              (empty / corrupt check)
  |                                     |
  |                              [2] STT - Sarvam AI
  |                              audio bytes -> text transcript
  |                                     |
  |                              [3] Input Guardrail
  |                              off-topic? unsafe? -> REFUSAL
  |                                     |
  |                              [4] Vector Retrieval (async thread)
  |                              embed query -> ChromaDB -> top-10 chunks
  |                                     |
  |                              [5] BM25+RRF Reranking (async thread)
  |                              10 chunks -> top-3 ranked chunks
  |                                     |
  |                              [6] Context Validation
  |                              low similarity? -> REFUSAL
  |                                     |
  |                              [7] LLM Generation
  |                              prompt + context -> answer
  |                                     |
  |                              [8] Grounding Check
  |                              hallucination? -> flag answer
  |                                     |
  +<-- PipelineResponse JSON -----------+
       (answer, sources, latency, status)
`

### Text Query (POST /ask-text)

Same flow, **Stage 2 (STT) is skipped** — query text is used directly.

---

## 4. Data Flow: Ingestion Pipeline

`
data/ (JSONL / CSV)
       |
       v
  ingestion/loader.py
  (load raw documents)
       |
       v
  ingestion/chunking.py
  +----------------------------------+
  |  Strategy: sentence              |  -> NLTK sentence-level chunks
  |  Strategy: fixed                 |  -> Fixed-length token windows
  |  Strategy: metadata              |  -> Metadata-aware splits
  +----------------------------------+
       |
       v
  ingestion/indexing.py
  (embed via all-MiniLM-L6-v2)
       |
       v
  ChromaDB  <->  chroma_db/
  (HNSW cosine index, persisted to disk)
`

---

## 5. Component Reference

| File | Lines | Role |
|:-----|------:|:-----|
| ackend/main.py | 138 | FastAPI app, CORS, lifespan, SPA serving |
| ackend/config.py | 71 | Centralised settings (Pydantic BaseSettings) |
| pi/server.py | 234 | FastAPI router, all HTTP endpoints |
| generation/harness.py | 458 | Pipeline orchestrator, 8-stage execution |
| generation/guardrails.py | ~290 | Input/context/output safety checks |
| generation/llm.py | ~450 | Multi-provider LLM client (Groq/Claude/OpenAI) |
| etrieval/retriever.py | 233 | ChromaDB vector search + embedding |
| etrieval/reranker.py | ~200 | BM25 + RRF hybrid reranker |
| oice/stt.py | 366 | Sarvam AI STT with retry + mock |
| ingestion/loader.py | ~215 | Raw document loader |
| ingestion/chunking.py | ~380 | 3-strategy text chunker |
| ingestion/indexing.py | ~240 | ChromaDB upsertion |
| evaluation/benchmark.py | ~310 | Latency benchmarking harness |
| evaluation/latency.py | ~250 | Percentile stats + report generator |

---

## 6. Configuration and Environment

All config lives in ackend/.env. Key variables:

`ash
# STT
SARVAM_API_KEY=...

# LLM (choose one provider)
ANTHROPIC_API_KEY=...
GROQ_API_KEY=...
LLM_PROVIDER=groq                      # groq | anthropic | openai
LLM_MODEL=llama-3.1-8b-instant

# Vector DB
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=msmarco_xi
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Retrieval
TOP_K_RETRIEVE=10                      # candidates fetched from ChromaDB
TOP_K_FINAL=3                          # after BM25+RRF reranking

# Chunking
CHUNKING_STRATEGY=sentence             # sentence | fixed | metadata

# Server
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:5173,...  # comma-separated allowed origins
`

---

## 7. Latency Budget

The core **Search Pipeline** must complete in **< 200ms**.

| Stage | Target | Actual P50 | Actual P90 |
|:------|:------:|:----------:|:----------:|
| Vector Retrieval | < 100ms | **15.4ms** PASS | 17.7ms PASS |
| BM25+RRF Reranking | < 100ms | **0.0ms** PASS | 0.0ms PASS |
| **Search Pipeline Total** | **< 200ms** | **15.4ms PASS** | **17.7ms PASS** |
| LLM Generation | network | 28.2ms | 29.9ms |
| **Total End-to-End** | — | **44.8ms** | **46.5ms** |

> STT latency (Sarvam AI) is network-bound and excluded from the 200ms local compute target.

---

## 8. Tech Stack Summary

| Category | Technology |
|:---------|:-----------|
| Web Framework | FastAPI (Python 3.11+) |
| Async runtime | asyncio + 	o_thread for blocking I/O |
| Embeddings | sentence-transformers - ll-MiniLM-L6-v2 |
| Vector DB | ChromaDB (persistent HNSW, cosine similarity) |
| Reranking | BM25 + RRF (Reciprocal Rank Fusion) |
| STT | Sarvam AI saaras:v3 (Indic language support) |
| LLM | Groq llama-3.1-8b-instant / Anthropic Claude |
| Guardrails | Custom lexical + semantic checks (3 stages) |
| Frontend | React + Vite + Tailwind CSS |
| Deployment | Render (backend) + Vercel (frontend) |
| Containerisation | Docker (Dockerfile at project root) |
| Logging | structlog (structured JSON logs) |
| Config | Pydantic BaseSettings + .env |
| Retry | 	enacity (exponential backoff) |

---

*Generated: 2026-08-22 - Voice-RAG MATRUBHASHA - HH Goa 2026 Task 2*
