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

### F-03 — Storyboard draft: 503 again, then a 343-second response
- **Date / stage:** 2026-11-26, script stage (`python -m pipeline.script`)
- **Symptom:** first attempt on `gemini-3.8-flash` → 503 high demand; after the 30 s overload wait, attempt 2 succeeded but took **342.9 s** for one JSON storyboard (the smoke-test reply took ~2 s on 3.5 Flash).
- **Cause:** provider load on the free tier, plus a long structured output (10 shots, Amharic + English).
- **What worked:** the retry policy from F-01 (30 s wait on 503) recovered without needing the fallback model. The fallback chain (`3.8-flash` → `3.5-flash`) stays in place.
- **Lesson:** the text stage is cached by input hash, so this slow call is paid **once**; re-runs with an unchanged DESIGN.md beats section are instant cache hits.
- **Evidence:** `runs.jsonl`, stage `script` (one `retry`, one `ok` with `latency_sec` ≈ 342.9).

### F-04 — A TTS call hung for more than 10 minutes, and the retries never fired
- **Date / stage:** 2026-11-26, narration re-run for storyboard v3 (after User Test #1)
- **Symptom:** s01 cached, s02 regenerated in 12.6 s, s03–s04 cached, then **s05 produced no log line for over 10 minutes**. No error was raised, so the retry/backoff logic in `common.cached_call` never ran.
- **Cause (my bug):** the Gemini client had **no request timeout**. A stalled server response leaves the HTTP call waiting forever; retries only help if the call *fails*.
- **Fix:** set `http_options={"timeout": 120000}` (2 min, in milliseconds; confirmed as a real `HttpOptions` field in google-genai 3.6.1) in `pipeline/gemini.py`. A stall now becomes an exception, which is logged as `retry` and retried with the overload wait.
- **Lesson:** retries without timeouts are not resilience. Every network call needs both.

### F-05 — Character consistency: identity drift, wrong ethnicity, and text inside images
- **Date / stage:** 2026-11-26, reference sheet + keyframes
- **Symptoms:**
  1. FLUX.2 klein 4B drew the "Ethiopian woman" as a non-Ethiopian woman in both reference candidates (E-05).
  2. With FLUX.1 schnell, **3 of 8 shots that show the mother drifted**: a young woman's face in a hands-only shot (s02), clear faces of family members who should be silhouettes (s08), and a different young woman in the emotional hero shot (s09).
  3. Garbled text and signature-like marks in 4 of 10 frames, despite "No text, no letters, no watermark" in every prompt.
  4. No model drew a real jebena (teapots and jugs instead).
- **Cause:** FLUX.1 schnell on Cloudflare takes no seed and no reference image, so every image is an independent sample conditioned only on text. Generic words ("Ethiopian woman", "jebena") are under-specified; negative instructions ("no text") are weak in distilled models.
- **What I tried / what worked:**
  - Picked the model that held identity (schnell over klein) using a fair side-by-side comparison → E-05.
  - **Object glossary** for the jebena → fixed (E-06).
  - **Shot-level physical specificity** (age markers, "only hands, no face", "seen from behind") → fixed 3/3 drifted shots (E-07).
  - Re-rolled frames with text: the large text went away; small corner marks remain but fall **outside the centre crops** for 9:16 and 16:9.
- **Not solved:** wardrobe drift in s06 (pink shawl). Accepted: it reads as the same scene, and another re-roll risks losing a good pour.
- **Evidence:** `runs.jsonl` stage `reference` and `keyframes`; `EXPERIMENTS.md` E-05 to E-07.
- **Evidence:** `runs.jsonl` stage `narration` (s02 `ok` at 22:57:15 UTC, then a gap, then the re-run); process stopped manually.
