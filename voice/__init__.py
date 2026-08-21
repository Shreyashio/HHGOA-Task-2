"""
voice/__init__.py
─────────────────
Voice input module for Voice-RAG pipeline.
"""

from voice.stt import (
    TranscriptionResult,
    get_supported_audio_types,
    transcribe,
    transcribe_sync,
)

__all__ = [
    "transcribe",
    "transcribe_sync",
    "TranscriptionResult",
    "get_supported_audio_types",
]
