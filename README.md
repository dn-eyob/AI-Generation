# The King Who Built a Wonder in Stone (በድንጋይ ድንቅ የሠራው ንጉሥ): a heritage short, made by a pipeline

An 84.5-second illustrated film about **Lalibela**: King Lalibela's dream of a new Jerusalem, the craftsmen who carved eleven churches out of solid rock, and **Bete Giyorgis**, the cross carved into the earth. Amharic narration, English subtitles, an original score, quiet sound effects and a "Made with AI" end card, in **9:16 and 16:9**.

The film is generated from one file, [`storyboard.json`](storyboard.json), by a reproducible multi-model pipeline that runs at **$0** on free tiers.

| | |
|---|---|
| 🎬 Film (9:16, main) | https://youtube.com/shorts/8m-pmgWALgE (verified playing signed-out, 2026-11-26) |
| 🎬 Film (16:9) | https://youtu.be/MtDooMUs4Bs (verified public via YouTube oEmbed, 2026-11-26) |
| 🎥 Walkthrough (≤ 5 min) | https://youtu.be/h_rw17cinuY (includes a live single-shot regeneration of s07) |
| 📣 Public post | https://lnkd.in/p/e7d-yhsE |
| Local files | `outputs/final/wonder_in_stone_vertical.mp4`, `outputs/final/wonder_in_stone_horizontal.mp4` |

> **Development history:** the pipeline was built and first user-tested on an earlier development storyboard (v1–v7). That work is kept as evidence in [DESIGN.md](DESIGN.md) §1–5, [EXPERIMENTS.md](EXPERIMENTS.md) and [FAILURES.md](FAILURES.md); the film is storyboard v8+ ([DESIGN.md §6](DESIGN.md)).

## Run it

```bash
git clone https://github.com/dn-eyob/AI-Generation.git
cd AI-Generation
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in your keys (only needed to regenerate changed shots)

python pipeline/run.py      # the whole film (or: make film)
```

**Requirements:** Python 3.11+ (tested on 3.15.2), [FFmpeg](https://ffmpeg.org/) on your PATH (tested on 9.1), and free API keys in `.env`:

| Key | Where to get it | Used for |
|---|---|---|
| `GEMINI_API_KEY` | Google AI Studio → Get API key | script, narration (TTS) |
| `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN` | Cloudflare dashboard → Workers AI → Use REST API | keyframes |

Generated outputs are committed and every stage is cached, so **an unchanged storyboard rebuilds without any API keys** (verified: 0 model calls, 11 s). Keys are only needed when you change something.

### Change one shot, regenerate only that shot

```bash
# 1. edit one shot in storyboard.json, e.g. s04's "narration" or "image_prompt"
# 2. then:
python pipeline/run.py --shot s04          # or: make shot ID=s04
```

The run summary (computed from `runs.jsonl`) shows exactly which model calls were new; every other shot reports `cached`.

### Other commands

| Command | What it does |
|---|---|
| `python -m pipeline.storyboard` | validate `storyboard.json` against the schema and the timing and subtitle-layout rules |
| `python pipeline/run.py --draft` | also run the Gemini script stage (drafts a storyboard from DESIGN.md; never overwrites yours) |
| `python -m pipeline.common --selftest` | prove logging, caching and retries work (no keys needed) |
| `python -m pipeline.radio_cut` | narration + placeholder music on black (the User Test #1 prototype) |
| `python -m pipeline.music [--choose B]` | compose 3 score candidates with previews under the narration; choose one |
| `python -m pipeline.costs` | regenerate the cost/latency table in COSTS.md from `runs.jsonl` |
| `python -m pipeline.check_secrets` | scan every file Git would upload for secret values |
| `python -m pipeline.kaggle_io bundle` / `import <zip>` | move work to and from the Kaggle GPU notebooks |
| `python -m experiments.tts_roundtrip` | Phase 4: Amharic / Tigrinya / Afaan Oromo / Somali TTS round-trip test |

## How it works

```
DESIGN.md beats ─► script ─► storyboard.json ◄── schema (validated first, every run)
                                   │
       ┌──────────────┬────────────┼──────────────┬──────────────┐
   narration       keyframes     music           sfx       (Wan on Kaggle, optional)
 Gemini 3.8 TTS   FLUX.1 schnell  Tizita, code   code              │
       │              │            │              │                │
       │            shots (Ken Burns / Wan, 9:16 + 16:9) ◄─────────┘
       └──────────────┴──────► assemble (FFmpeg) ◄┘
                    duck · two-pass −14 LUFS · subtitles · AI end card
                                   │
                    wonder_in_stone_{vertical,horizontal}.mp4
         every call ─► runs.jsonl (model, params, seed, latency, cost, status)
```

Details: **[ARCHITECTURE.md](ARCHITECTURE.md)** (contracts, caching, failure handling).

| Stage | Model / tool | Licence |
|---|---|---|
| Script, translation | Gemini 3.8 Flash (fallback 3.5 Flash), Google AI Studio free tier | Gemini API terms |
| Narration (Amharic) | Gemini 3.8 Flash TTS, prebuilt voice "Kore" | Gemini API terms |
| Keyframes | FLUX.1 [schnell] on Cloudflare Workers AI | Apache 2.0 |
| Moving shots | FFmpeg Ken Burns (Wan 2.2 TI2V-5B notebook ready, not used: F-07) | GPL build / Apache 2.0 |
| Score + sound effects | composed in code with numpy (ACE-Step 1.5 attempted, failed: F-06) | original |
| Assembly | FFmpeg 9.1 | GPL build |

## What it cost

**$0 paid.** At paid-tier list prices the AI calls for the whole project (development + final film + experiments) come to **about $0.08**; most time is spent encoding video locally, not waiting on models. Generated table: [COSTS.md](COSTS.md).

## Project documents

| File | Contents |
|---|---|
| [DESIGN.md](DESIGN.md) | audience, intent, User Test #1 (3 people) and what changed because of it, the story change to Lalibela (§6), revision logs |
| [EXPERIMENTS.md](EXPERIMENTS.md) | 13+ experiments: hypothesis → change → result |
| [FAILURES.md](FAILURES.md) | what broke (503 overloads, a hung TTS call, identity drift, ACE-Step on Kaggle…) and what fixed it |
| [COSTS.md](COSTS.md) | measured latency per stage, free-tier limits observed, list-price equivalent |
| [ETHICS.md](ETHICS.md) | consent (no real person shown or voiced), licences, AI labelling plan |
| [ARCHITECTURE.md](ARCHITECTURE.md) | how the pipeline works |

## Repository layout

| Path | Purpose |
|---|---|
| `storyboard.json` | the contract: shots, durations, prompts, references, narration, music cues, sound effects |
| `schema/` | JSON Schema for the storyboard |
| `pipeline/` | one script per stage + `common.py` (logging, caching, retries) + `run.py` |
| `kaggle/` | GPU notebooks (Wan 2.2, ACE-Step 1.5) |
| `experiments/` | Phase 4 ceiling experiment and its results |
| `outputs/` | every generated file, with `.meta.json` fingerprints, kept so a run can be inspected |
| `runs.jsonl` | one line per model call |

## AI disclosure

Every image, the narrator's voice, the score and the sound effects in this film are generated. King Lalibela is a historical figure with no surviving likeness; he, the priests and the pilgrims are imagined, generic illustrations, and the images of the churches are artistic impressions, not documentation. No living person's face, likeness or voice appears. The film ends with a "Made with AI" card naming every model, and the platform AI label is switched on when posting.
