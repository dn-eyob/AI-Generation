"""Smoke test: one tiny real call per provider, each logged to runs.jsonl.

Run all:   python -m pipeline.smoke_test
Run some:  python -m pipeline.smoke_test gemini_text gemini_text_fallback

It always calls the providers (force=True, no cache) because its job is to
prove keys, model names and request formats work *today*. Outputs go to
outputs/smoke/. Each test is independent: one failure does not stop the rest.
"""

from __future__ import annotations

import base64
import io
import sys
import wave
from pathlib import Path

import requests

from pipeline.common import OUTPUTS, StageError, cached_call, require_env

SMOKE_DIR = OUTPUTS / "smoke"

# Model IDs verified on 2026-11-25:
#   Gemini text  -> listed by client.models.list() for this key
#   Gemini TTS   -> https://aistudio.google.com/docs/speech-generation
#   Cloudflare   -> /ai/models/search for this account
GEMINI_TEXT_MODEL = "gemini-3.8-flash"
GEMINI_TEXT_FALLBACK = "gemini-3.5-flash"   # used when 3.8 is overloaded (503)
GEMINI_TTS_MODEL = "gemini-3.8-flash-tts"
CF_SCHNELL = "@cf/black-forest-labs/flux-1-schnell"
CF_KLEIN_4B = "@cf/black-forest-labs/flux-2-klein-4b"

TEST_PROMPT_IMAGE = ("A small clay coffee pot (jebena) on a woven mat, warm morning "
                     "light, painterly illustration")


def _gemini_client():
    from google import genai
    return genai.Client(api_key=require_env("GEMINI_API_KEY"),
                        http_options={"api_version": "v1beta"})


def _cf_url(model: str) -> str:
    return (f"https://api.cloudflare.com/client/v4/accounts/"
            f"{require_env('CLOUDFLARE_ACCOUNT_ID')}/ai/run/{model}")


def _cf_headers() -> dict:
    return {"Authorization": f"Bearer {require_env('CLOUDFLARE_API_TOKEN')}"}


def _cf_image_from_response(resp: requests.Response) -> bytes:
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    if resp.headers.get("content-type", "").startswith("image/"):
        return resp.content
    data = resp.json()
    result = data.get("result", data)
    if not isinstance(result, dict) or "image" not in result:
        raise RuntimeError(f"no image in response: {str(data)[:300]}")
    return base64.b64decode(result["image"])


def _wav_seconds(wav_bytes: bytes) -> float:
    with wave.open(io.BytesIO(wav_bytes)) as w:
        return round(w.getnframes() / w.getframerate(), 2)


# ---------------------------------------------------------------- tests
def _gemini_text(out: Path, model: str) -> dict:
    client = _gemini_client()
    resp = client.models.generate_content(
        model=model,
        contents="Reply with exactly the two letters: ok",
    )
    text = (resp.text or "").strip()
    out.write_text(text, encoding="utf-8")
    usage = getattr(resp, "usage_metadata", None)
    return {"notes": f"reply={text!r} tokens={getattr(usage, 'total_token_count', None)}"}


def test_gemini_text(out: Path) -> dict:
    return _gemini_text(out, GEMINI_TEXT_MODEL)


def test_gemini_text_fallback(out: Path) -> dict:
    return _gemini_text(out, GEMINI_TEXT_FALLBACK)


def _tts(out: Path, text: str, style: str, voice: str) -> dict:
    client = _gemini_client()
    interaction = client.interactions.create(
        model=GEMINI_TTS_MODEL,
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
    audio = base64.b64decode(interaction.output_audio.data)
    out.write_bytes(audio)
    return {"notes": f"audio_seconds={_wav_seconds(audio)} bytes={len(audio)}"}


def test_gemini_tts_english(out: Path) -> dict:
    return _tts(out, "Hello. This is a connection test for the heritage film.",
                "warm, calm, unhurried", "Kore")


def test_gemini_tts_amharic(out: Path) -> dict:
    # "Hello, this is a test voice." in Amharic.
    return _tts(out, "ሰላም፣ ይህ የሙከራ ድምፅ ነው።", "warm, calm, unhurried", "Kore")


def test_cf_schnell(out: Path) -> dict:
    resp = requests.post(_cf_url(CF_SCHNELL), headers=_cf_headers(),
                         json={"prompt": TEST_PROMPT_IMAGE, "steps": 4}, timeout=120)
    out.write_bytes(_cf_image_from_response(resp))
    return {"notes": f"bytes={out.stat().st_size}"}


def test_cf_klein_4b(out: Path) -> dict:
    # Form field names are NOT documented on the model page (checked 2026-11-25);
    # this tries the standard FLUX names. Result is recorded either way.
    form = {"prompt": TEST_PROMPT_IMAGE, "width": "512", "height": "512", "seed": "42"}
    files = {k: (None, v) for k, v in form.items()}  # forces multipart/form-data
    resp = requests.post(_cf_url(CF_KLEIN_4B), headers=_cf_headers(), files=files, timeout=120)
    out.write_bytes(_cf_image_from_response(resp))
    return {"notes": f"bytes={out.stat().st_size} fields={sorted(form)}"}


TESTS = [
    # (name, provider, model, parameters, seed, output file, function)
    ("gemini_text", "google", GEMINI_TEXT_MODEL, {}, None, "gemini_text.txt", test_gemini_text),
    ("gemini_text_fallback", "google", GEMINI_TEXT_FALLBACK, {}, None, "gemini_text_fallback.txt",
     test_gemini_text_fallback),
    ("tts_english", "google", GEMINI_TTS_MODEL, {"voice": "Kore", "style": "warm, calm, unhurried"},
     None, "tts_english.wav", test_gemini_tts_english),
    ("tts_amharic", "google", GEMINI_TTS_MODEL, {"voice": "Kore", "style": "warm, calm, unhurried"},
     None, "tts_amharic.wav", test_gemini_tts_amharic),
    ("flux1_schnell", "cloudflare", CF_SCHNELL, {"steps": 4}, None, "flux1_schnell.jpg", test_cf_schnell),
    ("flux2_klein_4b", "cloudflare", CF_KLEIN_4B, {"width": 512, "height": 512}, 42,
     "flux2_klein_4b.png", test_cf_klein_4b),
]


def main() -> int:
    # Optional: run only some tests, e.g.  python -m pipeline.smoke_test gemini_text
    wanted = set(sys.argv[1:])
    results = []
    for name, provider, model, params, seed, filename, fn in TESTS:
        if wanted and name not in wanted:
            continue
        print(f"-> {name} ({model}) ...", flush=True)
        try:
            r = cached_call(stage="smoke_test", shot_id=name, provider=provider, model=model,
                            parameters=params, seed=seed, inputs={"test": name},
                            output=SMOKE_DIR / filename, fn=fn, max_attempts=2, force=True)
            results.append((name, model, "OK", f"{r.latency_sec:.2f}s", r.record.get("notes") or ""))
        except StageError as exc:
            results.append((name, model, "FAILED", "-", str(exc)[:160]))

    print("\nSMOKE TEST SUMMARY")
    for name, model, status, latency, info in results:
        print(f"  {status:<6} {name:<15} {latency:>8}  {model}\n         {info}")
    return 0 if all(r[2] == "OK" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
