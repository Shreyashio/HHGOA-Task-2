# Voice-RAG — HH Goa 2026, Task 2

> **Voice-enabled Retrieval-Augmented Generation** over the MSMARCO-XI multilingual
> dataset. User speaks a question → Sarvam AI STT → ChromaDB vector retrieval →
> BM25 reranking → Groq LLM → grounded answer, all under 200ms pipeline latency.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- A free [Groq](https://console.groq.com) API key (fast + free tier)
- A [Sarvam AI](https://www.sarvam.ai) API key (STT)

---

### 1 — Clone & set up Python environment

```bash
cd voice-rag

# Create virtualenv
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Activate (Mac / Linux)
source .venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

### 2 — Configure environment variables

```bash
# Copy template
cp backend/.env.example backend/.env

# Edit backend/.env and fill in:
#   SARVAM_API_KEY=...
#   GROQ_API_KEY=...
```

### 3 — Run the backend

```bash
# From the voice-rag/ root
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: http://localhost:8000/health  
API docs: http://localhost:8000/docs

### 4 — Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

---

## Project Structure

```
voice-rag/
├── backend/            FastAPI app (main.py, config.py)
├── frontend/           React + Vite + Tailwind UI
├── ingestion/
│   ├── loader.py       HuggingFace MSMARCO-XI dataset loader
│   ├── chunking.py     Fixed / Sentence / Metadata-aware chunking strategies
│   └── indexing.py     Embed + upsert chunks into ChromaDB
├── retrieval/
│   ├── retriever.py    Vector similarity search (ChromaDB + SentenceTransformers)
│   └── reranker.py     BM25 + Reciprocal Rank Fusion hybrid reranking
├── voice/
│   └── stt.py          Sarvam AI speech-to-text
├── generation/
│   ├── llm.py          Groq LLM call with structured JSON output
│   └── guardrails.py   Off-topic / unsafe / hallucination checks
├── evaluation/
│   ├── benchmark.py    IR metrics (MRR, Recall, nDCG) + latency benchmark
│   └── latency.py      P50 / P70 / P100 per-stage latency tracker
├── api/
│   └── server.py       FastAPI router — /query/voice, /query/text, /stats
└── README.md
```

---

## Ingestion Pipeline (Step 2)

```bash
# Index the MSMARCO-XI dataset with a chosen chunking strategy
python -m ingestion.indexing --strategy sentence --max-docs 5000
```

## Benchmark (Step 6)

```bash
python -m evaluation.benchmark --queries data/test_queries.tsv --n 100 --strategy sentence
```

---

## Chunking Strategies

| Strategy | Description | Use case |
|----------|-------------|----------|
| `fixed` | Token-window with overlap | Baseline, fastest to index |
| `sentence` | NLTK sentence boundaries | Better semantic coherence |
| `metadata` | MSMARCO-XI aware, prefixes lang/query | Filtered retrieval |

Switch at runtime via the `strategy` field on any `/query/*` request.

---

## Latency Targets

| Stage | Target |
|-------|--------|
| Retrieval pipeline (embed + Chroma + rerank) | **< 200ms** |
| STT (Sarvam AI network) | reported separately |
| LLM generation (Groq network) | reported separately |
| Total end-to-end | reported combined |

---

## Guardrails

The pipeline will refuse to answer if:
- Query is off-topic (cosine similarity below threshold)
- Query contains unsafe / inappropriate content
- LLM cannot find support in the retrieved context
- Answer fails grounding verification against retrieved chunks

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| STT | Sarvam AI |
| Vector DB | ChromaDB (local, persistent) |
| Embeddings | `all-MiniLM-L6-v2` (SentenceTransformers) |
| Reranking | BM25 + Reciprocal Rank Fusion |
| LLM | Groq (`llama-3.1-8b-instant`) |
| Backend | FastAPI + Uvicorn |
| Frontend | React + Vite + Tailwind CSS |
| Orchestration | Tenacity (retries + structured I/O) |
