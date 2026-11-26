"""Subtitle timing and SRT writing, shared by the radio cut and final assembly.

Timing comes from the MEASURED narration (outputs/narration/timings.json),
not from guesses: each line appears when its narration starts and stays
until it ends. Lines are wrapped to at most 2 lines of ~42 characters.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from pipeline.common import OUTPUTS

TIMINGS_PATH = OUTPUTS / "narration" / "timings.json"
NARRATION_OFFSET_SEC = 0.3   # narration starts this long after the cut
MAX_LINE_CHARS = 42


def shot_starts(sb: dict) -> dict[str, float]:
    """Start time of every shot on the timeline (cumulative durations)."""
    t, starts = 0.0, {}
    for s in sb["shots"]:
        starts[s["id"]] = t
        t += float(s["duration_sec"])
    return starts


def wrap(text: str, width: int = MAX_LINE_CHARS) -> str:
    lines = textwrap.wrap(text, width=width)
    if len(lines) > 2:   # rebalance into two lines rather than three
        half = len(text) // 2
        split = text.rfind(" ", 0, half + 10)
        lines = [text[:split].strip(), text[split:].strip()]
    return "\n".join(lines)


def cues(sb: dict, timings_path: Path = TIMINGS_PATH,
         width: int = MAX_LINE_CHARS) -> list[tuple[float, float, str]]:
    timings = {r["shot_id"]: r for r in json.loads(timings_path.read_text(encoding="utf-8"))["shots"]}
    starts = shot_starts(sb)
    out = []
    for s in sb["shots"]:
        spoken = timings.get(s["id"], {}).get("narration_sec", 0.0)
        if not s["subtitle"] or not spoken:
            continue
        start = starts[s["id"]] + NARRATION_OFFSET_SEC
        end = min(start + spoken + 0.2, starts[s["id"]] + float(s["duration_sec"]))
        out.append((start, end, wrap(s["subtitle"], width)))
    return out


def _ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(path: Path, items: list[tuple[float, float, str]]) -> Path:
    blocks = [f"{i}\n{_ts(a)} --> {_ts(b)}\n{text}\n" for i, (a, b, text) in enumerate(items, 1)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(blocks), encoding="utf-8")
    return path
