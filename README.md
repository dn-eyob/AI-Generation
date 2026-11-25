# The Heritage Short — an AI film pipeline

A 60–90 second heritage film generated from one file, `storyboard.json`, by a reproducible multi-model pipeline.

> Status: **work in progress** (Phase 0 — setup).

## What it does
TODO — filled in Phase 5.

## Run it (one command)
TODO — filled in Phase 3 (`python pipeline/run.py`).

## Requirements
- Python 3.11+
- FFmpeg on your PATH
- Free API keys: copy `.env.example` to `.env` and fill it in.

## Repository layout
| Path | Purpose |
|---|---|
| `storyboard.json` | The contract: shots, durations, prompts, references, narration, music cues |
| `schema/` | JSON Schema for the storyboard, validated before every run |
| `pipeline/` | One script per stage: script, keyframes, shots, music, narration, assemble |
| `kaggle/` | GPU notebooks (Wan 2.2 video, ACE-Step music) run on Kaggle |
| `runs.jsonl` | One log line per model call |
| `outputs/` | Generated images, audio and video, kept so a run can be inspected |
| `DESIGN.md` | Audience, intent, user tests and what changed because of them |
| `ARCHITECTURE.md` | Stages, contracts, caching, failure handling |
| `EXPERIMENTS.md` | Hypothesis → change → result |
| `FAILURES.md` | What broke, what was tried, what fixed it |
| `COSTS.md` | Measured latency and GPU minutes per stage, list-price equivalent |
| `ETHICS.md` | Consent record, licences, labelling plan |

## Cost
TODO — summarised from `runs.jsonl` in Phase 5.
