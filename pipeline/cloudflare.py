"""Cloudflare Workers AI image calls (FLUX), shared by reference.py and keyframes.py.

Verified 2026-11-25 (FAILURES.md F-02):
  flux-1-schnell: JSON {prompt (<=2048 chars), steps (<=8)}; NO seed, NO size (returns 1024x1024)
  flux-2-klein-4b: multipart/form-data {prompt, width, height, seed} (fields undocumented,
                   standard FLUX names confirmed working by the smoke test)
Both return JSON {"result": {"image": <base64>}}.
Every image is normalised to PNG with FFmpeg so file names and formats are stable.
"""

from __future__ import annotations

import base64
import subprocess
from pathlib import Path

import requests

from pipeline.common import require_env

SCHNELL = "@cf/black-forest-labs/flux-1-schnell"
KLEIN_4B = "@cf/black-forest-labs/flux-2-klein-4b"
SIZE = 1024   # square: subject centred, so it crops to both 9:16 and 16:9


def _url(model: str) -> str:
    return (f"https://api.cloudflare.com/client/v4/accounts/"
            f"{require_env('CLOUDFLARE_ACCOUNT_ID')}/ai/run/{model}")


def _headers() -> dict:
    return {"Authorization": f"Bearer {require_env('CLOUDFLARE_API_TOKEN')}"}


def _decode(resp: requests.Response) -> bytes:
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    if resp.headers.get("content-type", "").startswith("image/"):
        return resp.content
    data = resp.json()
    result = data.get("result", data)
    if not isinstance(result, dict) or "image" not in result:
        raise RuntimeError(f"no image in response: {str(data)[:300]}")
    return base64.b64decode(result["image"])


def model_parameters(model: str, seed: int | None) -> tuple[dict, int | None]:
    """The parameters actually sent (for logging/hashing). Schnell ignores seed."""
    if model == SCHNELL:
        return {"steps": 8}, None
    if model == KLEIN_4B:
        return {"width": SIZE, "height": SIZE}, seed
    raise ValueError(f"unsupported image model {model}")


def generate(model: str, prompt: str, seed: int | None) -> bytes:
    if model == SCHNELL:
        resp = requests.post(_url(model), headers=_headers(),
                             json={"prompt": prompt[:2048], "steps": 8}, timeout=180)
    elif model == KLEIN_4B:
        form = {"prompt": prompt, "width": str(SIZE), "height": str(SIZE)}
        if seed is not None:
            form["seed"] = str(seed)
        resp = requests.post(_url(model), headers=_headers(),
                             files={k: (None, v) for k, v in form.items()}, timeout=180)
    else:
        raise ValueError(f"unsupported image model {model}")
    return _decode(resp)


def save_png(image_bytes: bytes, out: Path) -> None:
    """Normalise whatever the API returned (JPEG/PNG) to PNG at `out`."""
    proc = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
                           "-i", "pipe:0", "-frames:v", "1", str(out)],
                          input=image_bytes, capture_output=True)
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError(f"could not decode image: {proc.stderr.decode(errors='ignore')[-300:]}")


def build_prompt(image_prompt: str, sb: dict, characters: list[str]) -> str:
    """Shot prompt + fixed character description(s) + fixed style block.
    The same wording every time is what prevents identity and style drift."""
    parts = [image_prompt.strip()]
    for c in sb["style"]["characters"]:
        if c["id"] in characters:
            parts.append(f"The {c['id']} is {c['description']}.")
    parts.append(f"Style: {sb['style']['style_block']}.")
    parts.append("No text, no letters, no watermark.")
    return " ".join(parts)
