# COSTS

All numbers are measured from `runs.jsonl`. Anything not yet measured is marked `TODO_RUN`.
List-price equivalents will be added from each provider's published pricing page (with the date checked); until then `TODO_RUN`.

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
| Google AI Studio | TODO_RUN (record from the AI Studio rate-limit page) | |
| Cloudflare Workers AI | TODO_RUN (daily neuron allowance from the dashboard) | |
| Kaggle | 30 GPU hours/week (shown in notebook session options, GPU T4 ×2) | 2026-11-25 |

## Per-stage measurements
| Stage | Model | Calls | Total latency (s) | GPU minutes | List-price equivalent (USD) |
|---|---|---|---|---|---|

## Total cost paid: $0
