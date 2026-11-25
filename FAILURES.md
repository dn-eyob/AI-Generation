# FAILURES

What broke, what I tried, and what fixed it (or how I worked around it).

---

### F-01 — `gemini-3.8-flash` returned 503 "high demand" during the smoke test
- **Date / stage:** 2026-11-25, smoke test (Phase 0, step 0.7)
- **Symptom:** every text call to `gemini-3.8-flash` failed with
  `503 UNAVAILABLE — This model is currently experiencing high demand.`
  Gemini TTS and both Cloudflare image models worked in the same run.
- **Cause:** provider-side overload on the free tier (not a key or code problem: the same key worked for TTS and for `gemini-3.5-flash`).
- **What I tried:**
  1. Default retry (wait 2 s) → failed again. A 2 s retry just hits the same overload.
  2. Changed the retry policy in `pipeline/common.py` so 503 / "unavailable" / "high demand" are treated like rate limits (wait 30 s) → still 503.
  3. Called the next-newest Flash model, `gemini-3.5-flash` → **succeeded in 1.72 s**.
- **Resolution / workaround:** the text stage will use a fallback chain
  (`gemini-3.8-flash` → `gemini-3.5-flash`) and log which model actually answered.
- **Evidence:** `runs.jsonl`, stage `smoke_test`, shot `gemini_text` (status `retry`/`error`, 4 lines) and `gemini_text_fallback` (status `ok`).

### F-02 — The model line-up differs from the challenge brief ("when a tool has moved, find what replaced it")
- **Date / stage:** 2026-11-25, smoke test
- **Findings (from `client.models.list()` and Cloudflare `/ai/models/search` with my own keys):**
  - **There is no `gemini-3.8-flash-lite`.** The newest Lite model available to my key is `gemini-3.5-flash-lite` (also `gemini-3.1-flash-lite`). Bulk/cheap calls will use `gemini-3.5-flash-lite`.
  - **Gemini TTS is not returned by `models.list()`**, yet `gemini-3.8-flash-tts` works when called directly. A model list is not a complete source of truth.
  - **The TTS docs moved** from `ai.google.dev/gemini-api/docs/speech-generation` (301 redirect) to `aistudio.google.com/docs/speech-generation`, and the documented call is now the **Interactions API** (`client.interactions.create`), not `generate_content`. Unary responses are WAV, 24 kHz, mono, 16-bit.
  - **FLUX.2 klein 4B's request fields are undocumented** on its Cloudflare model page (schema shows only an opaque `multipart` object). I tried the standard FLUX field names (`prompt`, `width`, `height`, `seed`) as multipart/form-data and it **worked** (12.4 s, 512×512). FLUX.1 schnell uses JSON (`prompt`, `steps` ≤ 8) and has **no seed parameter**, which matters for reproducibility.
- **Resolution:** model IDs are pinned in code with the date and source they were verified against.
