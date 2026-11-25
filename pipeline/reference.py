"""Reference sheet: candidate images of the main character + style, made BEFORE keyframes.

Generates 2 candidates with each image model from the same prompt (a fair
model comparison at equal 1024x1024 size, see EXPERIMENTS.md), so you can:
  1. pick the golden reference (the look every keyframe is checked against)
  2. pick the image model for all keyframes

Output: outputs/reference/<model>_<n>.png (cached)
Run:    python -m pipeline.reference [--force]
After choosing, set style.characters[0].reference_image and defaults.image_model
in storyboard.json, and log the choice in EXPERIMENTS.md.
"""

from __future__ import annotations

import sys

from pipeline import cloudflare, storyboard
from pipeline.common import OUTPUTS, StageError, cached_call

REF_DIR = OUTPUTS / "reference"
CANDIDATES_PER_MODEL = 2
SEEDS = [7001, 7002]

REFERENCE_PROMPT = ("Character reference portrait: the mother kneeling on a floor covered with "
                    "fresh green grass, centred, full upper body, facing three-quarters toward "
                    "the viewer, gentle smile, beside a clay jebena coffee pot and a small "
                    "incense burner with a thin plume of smoke, plain warm wall behind her.")


def run(force: bool = False) -> list:
    sb = storyboard.load()
    prompt = cloudflare.build_prompt(REFERENCE_PROMPT, sb, ["mother"])
    results = []
    for model, tag in ((cloudflare.SCHNELL, "schnell"), (cloudflare.KLEIN_4B, "klein4b")):
        for n, seed in enumerate(SEEDS[:CANDIDATES_PER_MODEL], start=1):
            params, used_seed = cloudflare.model_parameters(model, seed)
            out = REF_DIR / f"{tag}_{n}.png"

            def gen(path, model=model, used_seed=used_seed):
                cloudflare.save_png(cloudflare.generate(model, prompt, used_seed), path)

            # schnell has no seed: candidate number keeps its two calls distinct in the hash
            r = cached_call(stage="reference", shot_id=f"{tag}_{n}", provider="cloudflare",
                            model=model, parameters=params, seed=used_seed,
                            inputs={"prompt": prompt, "candidate": n}, output=out,
                            fn=gen, max_attempts=3, force=force)
            print(f"  {out.name}: {r.status} {r.latency_sec:.1f}s")
            results.append(r)
    return results


if __name__ == "__main__":
    try:
        run(force="--force" in sys.argv)
    except StageError as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)
