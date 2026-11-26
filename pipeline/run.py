"""One command: storyboard.json -> finished film (9:16 + 16:9).

    python pipeline/run.py                 run every stage (cached stages are skipped)
    python pipeline/run.py --shot s04      regenerate only shot s04's narration, keyframe
                                           and clips, then re-assemble the film
    python pipeline/run.py --force         ignore every cache (regenerates everything)

Stage order (each reads storyboard.json and writes to outputs/):
  0. validate   schema/storyboard.schema.json + timing/consistency rules
  1. script     Gemini drafts the storyboard from DESIGN.md (never overwrites your edits)
  2. narration  Gemini TTS, one WAV per shot, measured timings
  3. keyframes  Cloudflare FLUX.1 schnell, one still per shot
  4. shots      Wan clip from Kaggle if present, else Ken Burns (FFmpeg), 9:16 + 16:9
  5. music      score composed in code; uses the chosen candidate (outputs/music/score.wav)
  5b. sfx       ceremony sounds synthesised in code from each shot's "sfx" list
  6. assemble   mix, duck, two-pass loudness, subtitles, end card, both exports

Every model call is logged to runs.jsonl. Because each output is cached by a hash
of its inputs, a re-run only calls a model for what actually changed: an unchanged
storyboard needs no API keys at all.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:          # allow `python pipeline/run.py` as well as `-m`
    sys.path.insert(0, str(ROOT))

from pipeline import assemble, keyframes, music, narration, script, sfx, shots, storyboard  # noqa: E402
from pipeline.common import StageError, runs_log_path  # noqa: E402


def log_position() -> int:
    path = runs_log_path()
    return len(path.read_text(encoding="utf-8").splitlines()) if path.exists() else 0


def summarise(start_line: int) -> None:
    lines = runs_log_path().read_text(encoding="utf-8").splitlines()[start_line:]
    recs = [json.loads(l) for l in lines if l.strip()]
    by_status: dict[str, int] = {}
    for r in recs:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    model_calls = [r for r in recs if r["status"] in ("ok", "retry", "error")
                   and r["provider"] in ("google", "cloudflare", "kaggle")]
    print("\n=== run summary (from runs.jsonl) ===")
    print(f"log lines this run: {len(recs)}  {by_status}")
    print(f"new external model calls: {len(model_calls)}")
    for r in model_calls:
        print(f"  {r['stage']:<10} {str(r['shot_id']):<12} {r['model']:<40} {r['status']:<6} {r['latency_sec']}s")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shot", help="regenerate only this shot id (e.g. s04), then re-assemble")
    ap.add_argument("--force", action="store_true", help="ignore all caches")
    a = ap.parse_args()

    start, t0 = log_position(), time.perf_counter()
    try:
        print("[0/6] validate");  sb = storyboard.load(); print("      " + storyboard.summary(sb))
        if a.shot and a.shot not in {s["id"] for s in sb["shots"]}:
            raise StageError(f"unknown shot id {a.shot}")
        print("[1/6] script");    script.run(force=a.force)
        print("[2/6] narration"); narration.run(only=a.shot, force=a.force)
        print("[3/6] keyframes"); keyframes.run(only=a.shot, force=a.force)
        print("[4/6] shots");     shots.run(only=a.shot, force=a.force)
        print("[5/6] music");     music.run(force=a.force)
        if not music.SCORE.exists():
            print("      no score chosen yet -> assembling a rough cut with the placeholder drone "
                  "(choose with: python -m pipeline.music --choose B)")
        print("[5b]  sfx");       sfx.run(force=a.force)
        print("[6/6] assemble");  outs = assemble.run(force=a.force)
    except (StageError, storyboard.StoryboardError) as exc:
        print(f"\nPIPELINE STOPPED: {exc}")
        summarise(start)
        return 1
    summarise(start)
    print(f"\ndone in {time.perf_counter() - t0:.0f}s:")
    for o in outs:
        print(f"  {o.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
