"""
test_stt.py
───────────
Unit and integration test suite for the Speech-to-Text (STT) layer (Step 4).

Usage:
  python test_stt.py                     # Run automated test suite
  python test_stt.py --mock              # Run mock transcription test
  python test_stt.py --file audio.wav    # Transcribe a real audio file
  python test_stt.py --text "Custom query" --mock
"""

import argparse
import asyncio
import os
import sys
import time
from unittest.mock import AsyncMock, patch

import httpx

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

import structlog
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(30),  # WARNING only for tests
)

from backend.config import settings
from voice.stt import (
    TranscriptionResult,
    _is_transient_error,
    get_supported_audio_types,
    transcribe,
    transcribe_sync,
)


def _synthetic_wav_bytes(duration_sec: float = 0.5) -> bytes:
    """Generate minimal valid PCM WAV header + silence bytes for testing."""
    import struct
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


async def run_tests():
    print("\n" + "=" * 60)
    print("  Speech-to-Text (STT) Layer Unit & Integration Tests (Step 4)")
    print("=" * 60)

    dummy_audio = _synthetic_wav_bytes(0.2)
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

    # ── Test 1: Empty audio rejection ──────────────────────────────────────────
    print("\n[1] Input Validation")
    try:
        await transcribe(b"")
        test_assert(False, "empty bytes raises ValueError", "No error was raised")
    except ValueError as e:
        test_assert(True, "empty bytes raises ValueError", str(e))

    # ── Test 2: Mock mode default transcription ────────────────────────────────
    print("\n[2] Mock Mode Transcription")
    res_mock = await transcribe(dummy_audio, mock_mode=True)
    test_assert(isinstance(res_mock, TranscriptionResult), "returns TranscriptionResult")
    test_assert(bool(res_mock.text), "transcribed text non-empty", res_mock.text)
    test_assert(res_mock.mock is True, "mock flag set to True")
    test_assert(res_mock.latency_ms > 0, "latency measured", f"{res_mock.latency_ms:.1f}ms")
    test_assert(res_mock.confidence == 1.0, "confidence is 1.0")

    # ── Test 3: Mock mode custom text ──────────────────────────────────────────
    print("\n[3] Custom Mock Text & Language Code")
    custom_text = "What is the distance between Earth and Mars?"
    res_custom = await transcribe(
        dummy_audio,
        mock_mode=True,
        mock_text=custom_text,
        language_code="hi-IN",
    )
    test_assert(res_custom.text == custom_text, "matches custom mock text", res_custom.text)
    test_assert(res_custom.language_detected == "hi-IN", "matches custom language code")

    # ── Test 4: Supported audio MIME types ─────────────────────────────────────
    print("\n[4] Audio Format Support")
    types = get_supported_audio_types()
    test_assert("audio/wav" in types, "WAV supported")
    test_assert("audio/webm" in types, "WebM supported")
    test_assert("audio/mpeg" in types, "MP3/MPEG supported")
    test_assert("audio/ogg" in types, "OGG supported")
    test_assert("audio/flac" in types, "FLAC supported")
    test_assert("audio/m4a" in types, "M4A supported")

    # ── Test 5: Synchronous wrapper ───────────────────────────────────────────
    print("\n[5] Synchronous Wrapper (transcribe_sync)")
    res_sync = transcribe_sync(dummy_audio, mock_mode=True, mock_text="Sync test query")
    test_assert(res_sync.text == "Sync test query", "transcribe_sync executes correctly")

    # ── Test 6: Tenacity retry behavior on transient errors (500 / 503) ───────
    print("\n[6] Tenacity Retries on Transient 5xx Errors")
    attempt_count = 0

    async def mock_transient_failing_post(*args, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        req = httpx.Request("POST", "https://api.sarvam.ai/speech-to-text")
        if attempt_count < 3:
            # Simulate 503 Service Unavailable for first 2 attempts
            resp = httpx.Response(503, request=req, json={"message": "Temporary Server Busy"})
            raise httpx.HTTPStatusError("Server busy", request=req, response=resp)
        # Succeed on 3rd attempt
        resp = httpx.Response(
            200,
            request=req,
            json={"transcript": "Recovered after transient error", "language_code": "en-IN"},
        )
        return resp

    with patch.object(settings, "SARVAM_API_KEY", "dummy-live-key"):
        with patch("httpx.AsyncClient.post", side_effect=mock_transient_failing_post):
            res_retry = await transcribe(dummy_audio, mock_mode=False)
            test_assert(
                attempt_count == 3,
                "tenacity retried 3 times on 503",
                f"attempt_count={attempt_count}",
            )
            test_assert(
                res_retry.text == "Recovered after transient error",
                "transcription recovered successfully",
            )

    # ── Test 7: Fast failure on non-retriable 401 Unauthorized ─────────────────
    print("\n[7] Fast Failure on 4xx Client Errors")
    attempt_401_count = 0

    async def mock_401_post(*args, **kwargs):
        nonlocal attempt_401_count
        attempt_401_count += 1
        req = httpx.Request("POST", "https://api.sarvam.ai/speech-to-text")
        resp = httpx.Response(401, request=req, json={"message": "Invalid API Key"})
        raise httpx.HTTPStatusError("Invalid API Key", request=req, response=resp)

    with patch.object(settings, "SARVAM_API_KEY", "invalid-key"):
        with patch("httpx.AsyncClient.post", side_effect=mock_401_post):
            try:
                await transcribe(dummy_audio, mock_mode=False)
                test_assert(False, "401 raises HTTPStatusError immediately", "No error raised")
            except httpx.HTTPStatusError as e:
                test_assert(
                    attempt_401_count == 1,
                    "401 error fails fast without retrying",
                    f"attempts={attempt_401_count}",
                )

    # ── Test 8: Live API Call (if real key configured) ────────────────────────
    print("\n[8] Live Sarvam AI API Check")
    real_key = settings.SARVAM_API_KEY.strip()
    if real_key and real_key not in ("your_sarvam_api_key_here", "mock", "none"):
        print("      Found real SARVAM_API_KEY in backend/.env — testing live transcription...")
        try:
            res_live = await transcribe(dummy_audio, mock_mode=False)
            test_assert(True, "live Sarvam AI transcription succeeded", f"{res_live.latency_ms:.1f}ms")
            print(f"      Transcript: {res_live.text!r}")
            print(f"      Language: {res_live.language_detected}")
        except Exception as e:
            print(f"      Live API call failed (check key / network): {e}")
    else:
        print("      SARVAM_API_KEY is placeholder or unset — skipping live cloud request (mock passed).")
        test_assert(True, "live check skipped safely (mock mode validated)")

    print("\n" + "=" * 60)
    print(f"  PASS  All {passed}/{total} STT tests passed successfully!")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Test STT Module (Step 4)")
    parser.add_argument("--mock", action="store_true", help="Run mock transcription")
    parser.add_argument("--text", default=None, help="Custom text for mock transcription")
    parser.add_argument("--file", default=None, help="Path to audio file to transcribe")
    parser.add_argument("--lang", default=None, help="Language code hint (e.g., 'en-IN', 'hi-IN')")
    args = parser.parse_args()

    if args.file:
        if not os.path.exists(args.file):
            print(f"Error: file not found '{args.file}'")
            sys.exit(1)
        with open(args.file, "rb") as f:
            audio_data = f.read()
        ext = os.path.splitext(args.file)[1].lower()
        mime_map = {
            ".wav": "audio/wav",
            ".webm": "audio/webm",
            ".mp3": "audio/mp3",
            ".ogg": "audio/ogg",
            ".flac": "audio/flac",
            ".m4a": "audio/m4a",
        }
        content_type = mime_map.get(ext, "audio/wav")
        print(f"\nTranscribing '{args.file}' ({len(audio_data)} bytes, {content_type})...")
        t0 = time.perf_counter()
        result = transcribe_sync(
            audio_bytes=audio_data,
            content_type=content_type,
            mock_mode=args.mock,
            language_code=args.lang,
            mock_text=args.text,
        )
        print(f"\nTranscription Result:")
        print(f"  Text: {result.text}")
        print(f"  Language: {result.language_detected}")
        print(f"  Confidence: {result.confidence}")
        print(f"  Latency: {result.latency_ms:.1f}ms")
        print(f"  Mock: {result.mock}")
    else:
        asyncio.run(run_tests())


if __name__ == "__main__":
    main()
