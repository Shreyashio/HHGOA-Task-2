"""
test_api.py
───────────
FastAPI integration test suite for Voice-RAG endpoints (Step 6).

Tests:
  - GET /health
  - GET /chunking/strategies
  - GET /stats
  - POST /ask-text
  - POST /ask-voice (multipart audio upload)
  - Error handling (empty payload, missing file, bad input)

Usage:
  python test_api.py
"""

import io
import os
import struct
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

import structlog
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(30),  # WARNING only for tests
)

from fastapi.testclient import TestClient
from backend.main import app


def _synthetic_wav_bytes(duration_sec: float = 0.5) -> bytes:
    """Generate minimal valid PCM WAV header + silence bytes for testing."""
    sample_rate = 16000
    num_samples = int(sample_rate * duration_sec)
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
    block_align = num_channels * (bits_per_sample // 8)
    data_size = num_samples * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,             # Subchunk1Size (16 for PCM)
        1,              # AudioFormat (1 for PCM)
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header + (b"\x00" * data_size)


def run_tests():
    print("\n" + "=" * 65)
    print("  FastAPI Server Endpoints Integration Tests (Step 6)")
    print("=" * 65)

    client = TestClient(app)
    passed = 0
    total = 0

    def test_assert(condition: bool, name: str, details: str = ""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"  [PASS] {name}" + (f" ({details})" if details else ""))
        else:
            print(f"  [FAIL] {name}" + (f" ({details})" if details else ""))
            raise AssertionError(f"Test failed: {name} - {details}")

    # ── Test 1: GET /health ───────────────────────────────────────────────────
    print("\n[1] Health Check Probe")
    resp = client.get("/health")
    test_assert(resp.status_code == 200, "GET /health returns 200")
    test_assert(resp.json().get("status") == "ok", "health status is 'ok'")

    # ── Test 2: GET /chunking/strategies ──────────────────────────────────────
    print("\n[2] Chunking Strategies Config")
    resp = client.get("/chunking/strategies")
    test_assert(resp.status_code == 200, "GET /chunking/strategies returns 200")
    data = resp.json()
    test_assert("available" in data and len(data["available"]) >= 3, "returns available strategies")

    # ── Test 3: GET /stats ────────────────────────────────────────────────────
    print("\n[3] Pipeline Stats Endpoint")
    resp = client.get("/stats")
    test_assert(resp.status_code == 200, "GET /stats returns 200")
    test_assert("pipeline_target_latency_ms" in resp.json(), "contains target latency metrics")

    # ── Test 4: POST /ask-text (Valid Question) ───────────────────────────────
    print("\n[4] Text Query Endpoint (POST /ask-text)")
    resp = client.post(
        "/ask-text",
        json={"query": "what is photosynthesis", "mock": True},
    )
    test_assert(resp.status_code == 200, "POST /ask-text returns 200")
    data = resp.json()
    test_assert("answer" in data, "contains answer field")
    test_assert("latency" in data, "contains latency breakdown")
    test_assert(data["latency"]["total_ms"] >= 0, "total latency measured")

    # ── Test 5: POST /ask-text (Empty Query) ──────────────────────────────────
    print("\n[5] Text Query Validation (Empty Query)")
    resp = client.post("/ask-text", json={"query": "   "})
    test_assert(resp.status_code == 400, "POST /ask-text with whitespace returns 400")

    # ── Test 6: POST /ask-voice (Valid Audio Upload) ──────────────────────────
    print("\n[6] Voice Query Endpoint (POST /ask-voice)")
    wav_data = _synthetic_wav_bytes(0.3)
    files = {"audio": ("test_recording.wav", io.BytesIO(wav_data), "audio/wav")}
    data = {"mock": "true", "strategy": "sentence"}
    resp = client.post("/ask-voice", files=files, data=data)
    test_assert(resp.status_code == 200, "POST /ask-voice returns 200")
    result = resp.json()
    test_assert("transcript" in result, "contains transcribed text", result.get("transcript"))
    test_assert("answer" in result, "contains generated answer")
    test_assert(result["latency"]["stt_ms"] > 0, "STT latency recorded", f"{result['latency']['stt_ms']:.1f}ms")
    test_assert("sources" in result, "sources field present")

    # ── Test 7: POST /ask-voice (Empty Audio File) ────────────────────────────
    print("\n[7] Voice Query Validation (Empty Audio)")
    empty_files = {"audio": ("empty.wav", io.BytesIO(b""), "audio/wav")}
    resp = client.post("/ask-voice", files=empty_files)
    test_assert(resp.status_code == 400, "POST /ask-voice with empty audio returns 400")

    # ── Test 8: POST /ask-voice (Missing File Field) ───────────────────────────
    print("\n[8] Voice Query Validation (Missing File Field)")
    resp = client.post("/ask-voice", data={"strategy": "sentence"})
    test_assert(resp.status_code == 400, "POST /ask-voice without file returns 400")

    print("\n" + "=" * 65)
    print(f"  PASS  All {passed}/{total} FastAPI integration tests passed!")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    run_tests()
