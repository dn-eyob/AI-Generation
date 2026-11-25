# EXPERIMENTS

Each entry: hypothesis → change (one variable, seed fixed where possible) → result, with evidence in `runs.jsonl`.

| # | Date | Stage | Hypothesis | Change | Result | Evidence | Decision |
|---|---|---|---|---|---|---|---|
| E-01 | 2026-11-25 | keyframes (smoke) | FLUX.2 klein 4B (newer) will look better than FLUX.1 schnell for the same prompt. | Same prompt ("clay jebena on a woven mat, warm morning light, painterly"), model swapped. Not a fair test yet: schnell 4 steps at default size vs. klein 512×512, seed 42. | **I preferred FLUX.1 schnell.** Schnell was also ~5× faster (2.36 s vs. 12.42 s). Trade-off: schnell has **no seed parameter** on Cloudflare, so it is less reproducible. | `runs.jsonl` smoke_test `flux1_schnell`, `flux2_klein_4b`; `outputs/smoke/` | Preliminary (n=1 viewer, 1 prompt). Re-test at equal resolution on the real reference sheet in Phase 2 before locking the model. |
| E-02 | 2026-11-25 | narration (smoke) | Gemini 3.8 Flash TTS will handle Amharic well enough to narrate the film. | Same voice (Kore) and style ("warm, calm, unhurried"); English line vs. Amharic line. | Amharic: **clear and natural, but slightly robotic** (native-speaker judgement, me). English 4.5 s audio in 9.31 s; Amharic 3.7 s audio in 4.91 s. | `runs.jsonl` smoke_test `tts_english`, `tts_amharic` | Amharic is viable. Next: test whether a stronger style instruction or a different voice reduces the robotic quality (Phase 1). |
