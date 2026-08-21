"""
voice/stt.py
─────────────
Speech-to-text transcription using the Sarvam AI API.

What this will do (Step 4):
  - Accept raw audio bytes (WAV/WebM/MP3) from the frontend upload
  - POST to Sarvam AI's /speech-to-text endpoint with SARVAM_API_KEY
  - Handle retries (tenacity) on transient 5xx errors
  - Return a TranscriptionResult with:
      { text, language_detected, confidence, latency_ms }
  - Support a `mock_mode` flag (reads a text file instead of calling the API)
    for offline testing without burning API credits

Sarvam AI STT endpoint: https://api.sarvam.ai/speech-to-text
Supported formats: WAV, MP3, OGG, FLAC (up to 25MB)
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class TranscriptionResult:
    """Output of the STT call."""
    text: str
    language_detected: str = "en-IN"
    confidence: float = 1.0
    latency_ms: float = 0.0


async def transcribe(
    audio_bytes: bytes,
    content_type: str = "audio/wav",
    mock_mode: bool = False,
) -> TranscriptionResult:
    """
    Transcribe audio using Sarvam AI STT.

    Args:
        audio_bytes:  raw audio file bytes from the HTTP upload
        content_type: MIME type of the audio ("audio/wav", "audio/webm", etc.)
        mock_mode:    if True, returns a canned response (for CI / offline dev)

    Returns:
        TranscriptionResult with the transcribed text and metadata.

    Raises:
        httpx.HTTPStatusError: on non-retriable API errors
        ValueError: if audio_bytes is empty
    """
    raise NotImplementedError("Implemented in Step 4")
