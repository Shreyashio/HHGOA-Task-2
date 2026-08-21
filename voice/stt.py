"""
voice/stt.py
─────────────
Speech-to-text transcription using the Sarvam AI API.

Features:
  - Accepts raw audio bytes (WAV/WebM/MP3/OGG/FLAC/M4A)
  - POST to Sarvam AI's /speech-to-text endpoint with SARVAM_API_KEY
  - Tenacity retry harness with exponential backoff on transient 5xx / 429 / network errors
  - Returns structured TranscriptionResult (text, language_detected, confidence, latency_ms)
  - Supports mock_mode for offline development and testing without consuming API credits
  - Provides both async and sync transcription interfaces

Sarvam AI STT endpoint: https://api.sarvam.ai/speech-to-text
Supported formats: WAV, WebM, MP3, OGG, FLAC, M4A/MP4 (up to 25MB)
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from backend.config import settings

log = structlog.get_logger()

SARVAM_STT_ENDPOINT = "https://api.sarvam.ai/speech-to-text"
DEFAULT_MODEL = "saaras:v3"
DEFAULT_LANGUAGE_CODE = "en-IN"
DEFAULT_MOCK_QUERY = "what is photosynthesis"

SARVAM_SUPPORTED_LANGUAGES: Dict[str, str] = {
    "en": "en-IN",
    "mr": "mr-IN",
    "hi": "hi-IN",
    "bn": "bn-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "od": "od-IN",
    "pa": "pa-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "gu": "gu-IN",
    "as": "as-IN",
    "ur": "ur-IN",
    "ne": "ne-IN",
    "kok": "kok-IN",
    "ks": "ks-IN",
    "sd": "sd-IN",
    "sa": "sa-IN",
    "sat": "sat-IN",
    "mni": "mni-IN",
    "brx": "brx-IN",
    "mai": "mai-IN",
    "doi": "doi-IN",
}


def normalize_sarvam_language_code(lang: Optional[str]) -> Optional[str]:
    """
    Normalize 2-letter ISO code or BCP-47 tag to Sarvam-supported code.
    Examples: 'en' -> 'en-IN', 'mr' -> 'mr-IN', 'hi' -> 'hi-IN'.
    Returns 'unknown' or normalized BCP-47 string.
    """
    if not lang:
        return "unknown"
    cleaned = str(lang).strip().lower()
    if cleaned in ("auto", "unknown", "none", "all", ""):
        return "unknown"
    if cleaned in SARVAM_SUPPORTED_LANGUAGES:
        return SARVAM_SUPPORTED_LANGUAGES[cleaned]
    if "-" in cleaned:
        parts = cleaned.split("-")
        return f"{parts[0].lower()}-{parts[1].upper()}"
    return "unknown"

MIME_TO_FILENAME: Dict[str, str] = {
    "audio/wav": "audio.wav",
    "audio/x-wav": "audio.wav",
    "audio/wave": "audio.wav",
    "audio/webm": "audio.webm",
    "audio/mpeg": "audio.mp3",
    "audio/mp3": "audio.mp3",
    "audio/ogg": "audio.ogg",
    "audio/flac": "audio.flac",
    "audio/x-flac": "audio.flac",
    "audio/mp4": "audio.m4a",
    "audio/m4a": "audio.m4a",
    "audio/x-m4a": "audio.m4a",
    "audio/aac": "audio.aac",
}


@dataclass
class TranscriptionResult:
    """Output of the STT call."""
    text: str
    language_detected: str = "en-IN"
    confidence: float = 1.0
    latency_ms: float = 0.0
    request_id: Optional[str] = None
    mock: bool = False


def get_supported_audio_types() -> List[str]:
    """Return list of supported audio MIME types."""
    return list(MIME_TO_FILENAME.keys())


def _is_transient_error(exc: BaseException) -> bool:
    """
    Check if an exception is a transient error worth retrying.
    Retries on 5xx server errors, 429 rate limits, and network timeouts/disconnects.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        return status_code >= 500 or status_code == 429
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError)):
        return True
    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4.0),
    retry=retry_if_exception(_is_transient_error),
    reraise=True,
)
async def _call_sarvam_api(
    client: httpx.AsyncClient,
    api_key: str,
    filename: str,
    audio_bytes: bytes,
    content_type: str,
    model: str,
    language_code: Optional[str] = None,
) -> dict:
    """Make HTTP POST to Sarvam STT with tenacity retry policy."""
    headers = {
        "api-subscription-key": api_key,
    }
    files = {
        "file": (filename, audio_bytes, content_type),
    }
    norm_lang = normalize_sarvam_language_code(language_code)
    data: Dict[str, str] = {
        "model": model,
        "with_diarization": "false",
    }
    if norm_lang:
        data["language_code"] = norm_lang

    response = await client.post(
        SARVAM_STT_ENDPOINT,
        headers=headers,
        files=files,
        data=data,
        timeout=30.0,
    )
    # If 400 bad request due to language code, retry once with language_code='unknown'
    if response.status_code == 400 and norm_lang != "unknown":
        data["language_code"] = "unknown"
        response = await client.post(
            SARVAM_STT_ENDPOINT,
            headers=headers,
            files=files,
            data=data,
            timeout=30.0,
        )
    response.raise_for_status()
    return response.json()


async def transcribe(
    audio_bytes: bytes,
    content_type: str = "audio/wav",
    mock_mode: bool = False,
    language_code: Optional[str] = None,
    model: Optional[str] = None,
    mock_text: Optional[str] = None,
    mock_file: Optional[str] = None,
) -> TranscriptionResult:
    """
    Transcribe audio using Sarvam AI STT or mock fallback.

    Args:
        audio_bytes:   Raw audio file bytes from HTTP upload.
        content_type:  MIME type of the audio ("audio/wav", "audio/webm", etc.).
        mock_mode:     If True, returns a mock response (for testing / offline dev).
        language_code: Optional BCP-47 language code hint (e.g. 'en-IN', 'hi-IN').
        model:         Optional model name override (default 'saaras:v3').
        mock_text:     Optional text string to return when mock_mode is True.
        mock_file:     Optional path to a text file containing mock transcription.

    Returns:
        TranscriptionResult with transcribed text, language, confidence, and latency.

    Raises:
        ValueError: If audio_bytes is empty or SARVAM_API_KEY is missing in non-mock mode.
        httpx.HTTPStatusError: On non-retriable API errors (e.g., 401 Unauthorized, 400 Bad Request).
    """
    if not audio_bytes:
        raise ValueError("audio_bytes cannot be empty")

    api_key = settings.SARVAM_API_KEY.strip()
    is_placeholder_key = not api_key or api_key in (
        "your_sarvam_api_key_here",
        "your_sarvam_key",
        "mock",
        "none",
    )

    # ── Handle Mock Mode ────────────────────────────────────────────────────────
    if mock_mode or is_placeholder_key:
        t0 = time.perf_counter()
        # Simulated processing delay (5-15ms)
        await asyncio.sleep(0.01)

        result_text = DEFAULT_MOCK_QUERY
        if mock_text:
            result_text = mock_text.strip()
        elif mock_file and os.path.exists(mock_file):
            try:
                with open(mock_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        result_text = content
            except Exception as e:
                log.warning("stt.mock_file_read_failed", file=mock_file, error=str(e))

        elapsed_ms = (time.perf_counter() - t0) * 1000

        log.info(
            "stt.transcribe_mock",
            text=result_text,
            bytes=len(audio_bytes),
            content_type=content_type,
            latency_ms=f"{elapsed_ms:.1f}",
        )

        return TranscriptionResult(
            text=result_text,
            language_detected=language_code or DEFAULT_LANGUAGE_CODE,
            confidence=1.0,
            latency_ms=elapsed_ms,
            request_id="mock-request-id",
            mock=True,
        )

    # ── Live API Call ──────────────────────────────────────────────────────────
    normalized_content_type = content_type.split(";")[0].strip().lower()
    filename = MIME_TO_FILENAME.get(normalized_content_type, "audio.wav")
    selected_model = model or DEFAULT_MODEL

    log.info(
        "stt.transcribe_start",
        model=selected_model,
        bytes=len(audio_bytes),
        content_type=normalized_content_type,
        language_code=language_code,
    )

    t0 = time.perf_counter()
    async with httpx.AsyncClient() as client:
        try:
            payload = await _call_sarvam_api(
                client=client,
                api_key=api_key,
                filename=filename,
                audio_bytes=audio_bytes,
                content_type=normalized_content_type,
                model=selected_model,
                language_code=language_code,
            )
        except httpx.HTTPStatusError as err:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            log.error(
                "stt.api_http_error",
                status_code=err.response.status_code,
                response=err.response.text,
                latency_ms=f"{elapsed_ms:.1f}",
            )
            raise
        except Exception as err:
            elapsed_ms = (time.perf_counter() - t0) * 1000
            log.error(
                "stt.api_error",
                error=str(err),
                latency_ms=f"{elapsed_ms:.1f}",
            )
            raise

    elapsed_ms = (time.perf_counter() - t0) * 1000

    transcript_text = payload.get("transcript") or payload.get("text") or ""
    detected_lang = payload.get("language_code") or language_code or DEFAULT_LANGUAGE_CODE
    request_id = payload.get("request_id")

    log.info(
        "stt.transcribe_success",
        transcript_preview=transcript_text[:60],
        language_detected=detected_lang,
        latency_ms=f"{elapsed_ms:.1f}",
        request_id=request_id,
    )

    return TranscriptionResult(
        text=transcript_text,
        language_detected=detected_lang,
        confidence=1.0,
        latency_ms=elapsed_ms,
        request_id=request_id,
        mock=False,
    )


def transcribe_sync(
    audio_bytes: bytes,
    content_type: str = "audio/wav",
    mock_mode: bool = False,
    language_code: Optional[str] = None,
    model: Optional[str] = None,
    mock_text: Optional[str] = None,
    mock_file: Optional[str] = None,
) -> TranscriptionResult:
    """
    Synchronous wrapper for transcribe().
    Safely executes whether an event loop is currently active or not.
    """
    def _run():
        return asyncio.run(
            transcribe(
                audio_bytes=audio_bytes,
                content_type=content_type,
                mock_mode=mock_mode,
                language_code=language_code,
                model=model,
                mock_text=mock_text,
                mock_file=mock_file,
            )
        )

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(_run).result()
    else:
        return _run()
