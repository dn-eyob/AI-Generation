# COSTS

All numbers are measured from `runs.jsonl`; the per-stage table is **generated** by `python -m pipeline.costs`, not typed.
**Paid: $0.** List-price equivalents use the providers' published paid-tier prices, checked 2026-11-26 (sources and formulas in the docstring of `pipeline/costs.py`):
Gemini 3.8 Flash $0.75 / $3.75 per 1M input/output tokens; Gemini 3.8 Flash TTS $9.00 per 1M audio tokens at 25 tokens/s;
FLUX.1 schnell $0.0000528 per 512×512 tile + $0.0001056 per step; FLUX.2 klein 4B $0.000287 per output tile.
`gemini-3.5-flash` is not on the pricing page, so its calls are counted as "unpriced", not guessed.

### Headline numbers
- **Most expensive stage by list price:** keyframes and narration (each about $0.015 for the whole film). The whole film's AI calls would cost **about 5 US cents** on paid tiers.
- **The real cost is time, not money:** most wall-clock time is local FFmpeg encoding (Ken Burns + two 83 s exports), not model calls. A single-shot regeneration is dominated by re-encoding the two final videos (about 2–3 min each).
- **Reliability is the hidden cost:** 9 retries and 6 errors, nearly all `503 high demand` from Gemini text models (FAILURES F-01, F-03, F-08). The one slow success took 343 s.

## Smoke test — first real call per provider (2026-11-25)
| Provider | Model | Result | Latency (s) | Output |
|---|---|---|---|---|
| Google AI Studio | `gemini-3.8-flash` | ❌ 503 high demand (see FAILURES F-01) | — | — |
| Google AI Studio | `gemini-3.5-flash` (fallback) | ✅ | 1.72 | 98 tokens |
| Google AI Studio | `gemini-3.8-flash-tts` (English) | ✅ | 9.31 | 4.5 s of audio |
| Google AI Studio | `gemini-3.8-flash-tts` (Amharic) | ✅ | 4.91 | 3.7 s of audio |
| Cloudflare Workers AI | `@cf/black-forest-labs/flux-1-schnell` (4 steps) | ✅ | 2.36 | 1 image |
| Cloudflare Workers AI | `@cf/black-forest-labs/flux-2-klein-4b` (512×512) | ✅ | 12.42 | 1 image |
| Kaggle | GPU notebook (2× T4) | ✅ session started (manual check) | — | 30 h/week quota shown |

## Free-tier limits actually observed
| Provider | Limit observed | Date checked |
|---|---|---|
| Google AI Studio | Free tier for Gemini 3.8 Flash, 3.5 Flash-Lite and 3.8 Flash TTS ("Free of charge" on the pricing page). No numeric limit hit; the practical limit was **503 "high demand"** overloads at peak times, not quota errors | 2026-11-26 |
| Cloudflare Workers AI | **10,000 neurons/day** free (pricing page). FLUX.1 schnell 1024×1024 at 8 steps = 4×4.8 + 8×9.6 = **96 neurons/image → about 104 images/day**. This project used 19 schnell images + 3 klein images in total | 2026-11-26 |
| Kaggle | 30 GPU hours/week (shown in notebook session options, GPU T4 ×2) | 2026-11-25 |

## Per-stage measurements
<!-- BEGIN GENERATED: python -m pipeline.costs -->
Generated from `runs.jsonl` (299 log lines). Latency = wall-clock seconds spent in calls (successful + failed attempts). Cached re-uses cost nothing and take ~0 s.

| Stage | Model(s) | OK | Cached | Retry | Error | Latency (s) | GPU min | List-price equiv. (USD) | Basis |
|---|---|---|---|---|---|---|---|---|---|
| smoke_test | @cf/black-forest-labs/flux-1-schnell, @cf/black-forest-labs/flux-2-klein-4b, gemini-3.5-flash, gemini-3.8-flash, gemini-3.8-flash-tts | 5 | 0 | 2 | 2 | 41.4 | 0.0 | 0.0028 (+1 unpriced) | 1 output tiles; 4 tiles + 4 steps; audio seconds x 25 tok/s; price not listed |
| script | gemini-3.8-flash | 1 | 4 | 1 | 0 | 350.5 | 0.0 | 0.0097 | exact tokens |
| narration | gemini-3.8-flash-tts | 11 | 61 | 0 | 0 | 129.7 | 0.0 | 0.0152 | audio seconds x 25 tok/s |
| radio_cut | ffmpeg | 2 | 1 | 0 | 0 | 69.9 | 0.0 | 0.0000 | local |
| reference | @cf/black-forest-labs/flux-1-schnell, @cf/black-forest-labs/flux-2-klein-4b | 4 | 0 | 0 | 0 | 34.3 | 0.0 | 0.0044 | 4 output tiles; 4 tiles + 8 steps |
| keyframes | @cf/black-forest-labs/flux-1-schnell | 15 | 37 | 0 | 0 | 62.9 | 0.0 | 0.0158 | 4 tiles + 8 steps |
| shots | ffmpeg-kenburns | 40 | 60 | 0 | 0 | 803.2 | 0.0 | 0.0000 | local |
| assemble_audio | ffmpeg | 4 | 2 | 0 | 0 | 141.3 | 0.0 | 0.0000 | local |
| assemble_video | ffmpeg | 10 | 2 | 0 | 0 | 1852.6 | 0.0 | 0.0000 | local |
| assemble_check | ffmpeg-ebur128 | 6 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0000 | local |
| music | numpy-tizita-synth-v1 | 3 | 9 | 0 | 0 | 108.8 | 0.0 | 0.0000 | local |
| music_choice | numpy-tizita-synth-v1 | 1 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0000 | local |
| sfx | numpy-sfx-synth-v1 | 1 | 1 | 0 | 0 | 1.9 | 0.0 | 0.0000 | local |
| ceiling_translate | gemini-3.8-flash | 1 | 1 | 1 | 0 | 32.4 | 0.0 | 0.0013 | exact tokens |
| ceiling_asr | gemini-3.5-flash, gemini-3.7-flash, gemini-3.8-flash | 1 | 1 | 5 | 4 | 141.4 | 0.0 | 0.0000 (+1 unpriced) | price not listed |
| **Total** | | **105** | **179** | **9** | **6** | **3770.1** | **0.0** | **0.0492** (+2 unpriced) | |

**Actually paid: $0.00** (free tiers only).
<!-- END GENERATED -->

## Frontier comparison
**Not done: no access.** The frontier image, video and music models named in the brief (Nano Banana, Omni Flash, Lyria 3.5) need paid billing, and I did not have an organisation key for them. The closest comparison I could make was **within** the free tier: FLUX.2 klein 4B (newer) vs FLUX.1 schnell (E-05), and Gemini 3.8 Flash vs the 3.5 / 3.6 / 3.7 fallbacks under load (F-01, F-08).

## GPU minutes
**0 GPU minutes used.** Kaggle's Wan 2.2 (F-07) was not run and ACE-Step (F-06) failed without returning logs, so every moving shot is Ken Burns and the score is composed on CPU. The 30 h/week Kaggle quota is untouched.

## Total cost paid: $0
