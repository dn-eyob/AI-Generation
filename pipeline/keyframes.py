"""Stage - keyframes: one still image per shot (Cloudflare FLUX).

Input:   storyboard.json (shots[].image_prompt, characters, seed; style block;
         defaults.image_model)
Output:  outputs/keyframes/<shot_id>.png  (square 1024, subject centred)

Run:  python -m pipeline.keyframes                all shots
      python -m pipeline.keyframes --shot s04     one shot only
      python -m pipeline.keyframes --force        ignore cache

Every prompt = shot prompt + fixed character description + fixed style block,
so wording never drifts between shots. Cached per shot: editing one shot's
image_prompt regenerates only that keyframe (and, downstream, only that clip).
"""

from __future__ import annotations

import argparse
import sys

from pipeline import cloudflare, storyboard
from pipeline.common import OUTPUTS, StageError, cached_call

KEYFRAME_DIR = OUTPUTS / "keyframes"


def keyframe_path(shot_id: str):
    return KEYFRAME_DIR / f"{shot_id}.png"


def run(only: str | None = None, force: bool = False) -> None:
    sb = storyboard.load()
    model = sb["defaults"]["image_model"]
    failed = []
    for shot in sb["shots"]:
        if only and shot["id"] != only:
            continue
        prompt = cloudflare.build_prompt(shot["image_prompt"], sb, shot.get("characters", []))
        params, seed = cloudflare.model_parameters(model, shot["seed"])

        def gen(path, prompt=prompt, seed=seed):
            cloudflare.save_png(cloudflare.generate(model, prompt, seed), path)

        try:
            r = cached_call(stage="keyframes", shot_id=shot["id"], provider="cloudflare",
                            model=model, parameters=params, seed=seed,
                            inputs={"prompt": prompt, "shot_seed": shot["seed"]},
                            output=keyframe_path(shot["id"]), fn=gen, max_attempts=3, force=force)
            print(f"  {shot['id']}: {r.status} {r.latency_sec:.1f}s")
        except StageError as exc:
            failed.append(shot["id"])
            print(f"  {shot['id']}: FAILED {exc}")
    if failed:
        raise StageError(f"keyframes failed for {failed}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shot")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    try:
        run(only=a.shot, force=a.force)
    except StageError as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)
