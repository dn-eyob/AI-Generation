"""Stage - narration: one Gemini TTS audio file per shot, plus measured timings.

Input:   storyboard.json (shots[].narration, defaults.tts_model/voice/style)
Output:  outputs/narration/<shot_id>.wav   (cached per shot by input hash)
         outputs/narration/timings.json    (measured seconds per line)

Run:  python -m pipeline.narration                 all shots
      python -m pipeline.narration --shot s03      one shot only
      python -m pipeline.narration --force         ignore the cache

Changing one shot's narration text changes only that shot's hash, so only
that line is regenerated. Shots with empty narration are skipped.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pipeline import gemini, storyboard
from pipeline.common import OUTPUTS, StageError, cached_call, models_in_cache_order

NARRATION_DIR = OUTPUTS / "narration"
TIMINGS_PATH = NARRATION_DIR / "timings.json"
PAD_SEC = 0.8   # breathing room the shot needs beyond its spoken line

# Documented on aistudio.google.com/docs/speech-generation (2026-11-25);
# used only if the main TTS model fails. Not yet verified by a real call.
TTS_FALLBACK = "gemini-3.8-flash-lite-tts"


def synthesize_shot(shot: dict, defaults: dict, force: bool = False) -> dict:
    sid = shot["id"]
    out = NARRATION_DIR / f"{sid}.wav"
    voice, style = defaults["tts_voice"], defaults["tts_style"]
    models = models_in_cache_order([defaults["tts_model"], TTS_FALLBACK], out)
    last_exc: Exception | None = None

    for model in models:
        def generate(path: Path, model=model) -> dict:
            wav = gemini.tts_wav(model, shot["narration"], voice, style)
            path.write_bytes(wav)
            secs = gemini.wav_seconds(wav)
            words = len(shot["narration"].split())
            return {"notes": f"audio_seconds={secs} words={words} "
                             f"words_per_sec={words / secs if secs else 0:.2f}"}
        try:
            r = cached_call(stage="narration", shot_id=sid, provider="google", model=model,
                            parameters={"voice": voice, "style": style}, seed=None,
                            inputs={"text": shot["narration"]}, output=out,
                            fn=generate, max_attempts=3, force=force)
            return {"status": r.status, "model": model}
        except StageError as exc:
            last_exc = exc
            print(f"  {sid}: {model} failed, trying fallback if any")
    raise StageError(f"narration {sid} failed on all TTS models: {last_exc}")


def measure(sb: dict) -> dict:
    """Read every narration file's real length and compare with the plan."""
    rows, spoken_total = [], 0.0
    for shot in sb["shots"]:
        path = NARRATION_DIR / f"{shot['id']}.wav"
        secs = gemini.wav_seconds(path.read_bytes()) if shot["narration"] and path.exists() else 0.0
        spoken_total += secs
        needed = round(secs + PAD_SEC, 2) if secs else 0.0
        rows.append({
            "shot_id": shot["id"],
            "planned_sec": shot["duration_sec"],
            "narration_sec": secs,
            "needed_sec": needed,
            "fits": needed <= shot["duration_sec"],
            "words": len(shot["narration"].split()),
        })
    planned_total = sum(s["duration_sec"] for s in sb["shots"])
    return {"shots": rows, "narration_total_sec": round(spoken_total, 2),
            "planned_total_sec": planned_total,
            "narration_share": round(spoken_total / planned_total, 2) if planned_total else 0}


def run(only: str | None = None, force: bool = False) -> dict:
    sb = storyboard.load()                      # validates first
    for shot in sb["shots"]:
        if only and shot["id"] != only:
            continue
        if not shot["narration"]:
            print(f"  {shot['id']}: no narration (music only), skipped")
            continue
        res = synthesize_shot(shot, sb["defaults"], force=force)
        print(f"  {shot['id']}: {res['status']} ({res['model']})")

    timings = measure(sb)
    TIMINGS_PATH.write_text(json.dumps(timings, indent=2), encoding="utf-8")

    print("\nshot  planned  spoken  needed  fits")
    for r in timings["shots"]:
        print(f"{r['shot_id']:<5} {r['planned_sec']:>6.1f}s {r['narration_sec']:>6.2f}s "
              f"{r['needed_sec']:>6.2f}s  {'yes' if r['fits'] else 'NO - lengthen shot'}")
    print(f"\nspoken total {timings['narration_total_sec']}s of {timings['planned_total_sec']}s "
          f"planned ({timings['narration_share']:.0%} of the film has voice)")
    return timings


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shot", help="regenerate only this shot id, e.g. s03")
    ap.add_argument("--force", action="store_true", help="ignore the cache")
    args = ap.parse_args()
    try:
        run(only=args.shot, force=args.force)
    except StageError as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)
