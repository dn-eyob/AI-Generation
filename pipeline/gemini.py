"""Thin wrappers around the Gemini API (text + TTS), shared by stages.

Model IDs verified 2026-11-25 (see FAILURES.md F-02):
  text: gemini-3.8-flash, falling back to gemini-3.5-flash on overload (F-01)
  tts:  gemini-3.8-flash-tts via the Interactions API, returns WAV 24 kHz mono 16-bit
"""

from __future__ import annotations

import base64
import io
import json
import re
import wave
from functools import lru_cache

from pipeline.common import require_env


# Hard per-request limit. Without it a stalled server response hangs forever and
# the retry logic never runs (FAILURES.md F-04: s05 narration hung >10 min).
REQUEST_TIMEOUT_MS = 120_000


@lru_cache(maxsize=1)
def client():
    from google import genai
    return genai.Client(api_key=require_env("GEMINI_API_KEY"),
                        http_options={"api_version": "v1beta", "timeout": REQUEST_TIMEOUT_MS})


def text_json(model: str, prompt: str, temperature: float = 0.8) -> tuple[dict, dict]:
    """Ask a text model for JSON. Returns (parsed_json, usage_info)."""
    from google.genai import types
    resp = client().models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=temperature,
        ),
    )
    raw = (resp.text or "").strip()
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)  # tolerate fenced output
    usage = getattr(resp, "usage_metadata", None)
    info = {
        "prompt_tokens": getattr(usage, "prompt_token_count", None),
        "output_tokens": getattr(usage, "candidates_token_count", None),
        "total_tokens": getattr(usage, "total_token_count", None),
    }
    return json.loads(raw), info


def transcribe_json(model: str, wav: bytes, instruction: str) -> tuple[dict, dict]:
    """Send audio + an instruction to a text model; expect JSON back."""
    from google.genai import types
    resp = client().models.generate_content(
        model=model,
        contents=[types.Part.from_bytes(data=wav, mime_type="audio/wav"), instruction],
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0),
    )
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", (resp.text or "").strip())
    usage = getattr(resp, "usage_metadata", None)
    return json.loads(raw), {"total_tokens": getattr(usage, "total_token_count", None)}


def tts_wav(model: str, text: str, voice: str, style: str) -> bytes:
    """Synthesize one line of speech. Returns WAV bytes."""
    interaction = client().interactions.create(
        model=model,
        input=[{
            "type": "user_input",
            "content": [{
                "type": "text",
                "text": text,
                "annotations": [{"type": "speech_metadata", "style": style}],
            }],
        }],
        response_format={"type": "audio"},
        generation_config={"speech_config": [{"voice": voice}]},
    )
    return base64.b64decode(interaction.output_audio.data)


def wav_seconds(wav_bytes: bytes) -> float:
    with wave.open(io.BytesIO(wav_bytes)) as w:
        return round(w.getnframes() / w.getframerate(), 3)
