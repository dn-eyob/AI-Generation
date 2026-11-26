"""Load and validate storyboard.json, the contract every stage reads.

Two layers of checks:
1. JSON Schema (schema/storyboard.schema.json): fields, types, allowed values.
2. Rules a schema can't express: total length 60-90 s, unique shot ids,
   music cues pointing at real shots, characters defined, subtitle length.

Run:  python -m pipeline.storyboard            (validates storyboard.json)
      python -m pipeline.storyboard other.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

from pipeline.common import ROOT

SCHEMA_PATH = ROOT / "schema" / "storyboard.schema.json"
STORYBOARD_PATH = ROOT / "storyboard.json"

MIN_TOTAL_SEC, MAX_TOTAL_SEC = 60, 90
END_CARD_SEC = 3            # added by assembly; counts toward the total
MAX_SUBTITLE_CHARS = 84     # about 2 lines x 42 characters
VERTICAL_WRAP = 33          # wrap width used for 9:16 subtitles (assemble.SUB_STYLE)
MAX_VERTICAL_LINE = 41      # longest line that fits the 9:16 frame at that font (measured, E-14)


class StoryboardError(ValueError):
    """The storyboard breaks the contract. Message lists every problem."""


def schema_errors(data: dict) -> list[str]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in err.path) or "(top level)"
        errors.append(f"{where}: {err.message}")
    return errors


def rule_errors(data: dict) -> list[str]:
    errors = []
    shots = data.get("shots", [])
    ids = [s.get("id") for s in shots]

    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        errors.append(f"duplicate shot ids: {dupes}")

    total = sum(float(s.get("duration_sec", 0)) for s in shots) + END_CARD_SEC
    if not MIN_TOTAL_SEC <= total <= MAX_TOTAL_SEC:
        errors.append(f"total length {total:.1f}s (shots + {END_CARD_SEC}s end card) "
                      f"must be {MIN_TOTAL_SEC}-{MAX_TOTAL_SEC}s")

    known_chars = {c.get("id") for c in data.get("style", {}).get("characters", [])}
    for s in shots:
        sid = s.get("id", "?")
        for c in s.get("characters", []):
            if c not in known_chars:
                errors.append(f"{sid}: character '{c}' is not defined in style.characters")
        narration, subtitle = s.get("narration", "").strip(), s.get("subtitle", "").strip()
        if narration and not subtitle:
            errors.append(f"{sid}: has narration but no English subtitle")
        if len(subtitle) > MAX_SUBTITLE_CHARS:
            errors.append(f"{sid}: subtitle is {len(subtitle)} chars (max {MAX_SUBTITLE_CHARS}); "
                          f"split the line or shorten it")
        elif subtitle:
            from pipeline.subtitles import wrap   # local import: subtitles is a leaf module
            longest = max(len(line) for line in wrap(subtitle, VERTICAL_WRAP).split("\n"))
            if longest > MAX_VERTICAL_LINE:
                errors.append(f"{sid}: subtitle needs a {longest}-char line on the 9:16 frame "
                              f"(max {MAX_VERTICAL_LINE}, or the player wraps it to 3 lines); shorten it")

    for cue in data.get("music", {}).get("cues", []):
        for key in ("from_shot", "to_shot"):
            if cue.get(key) not in ids:
                errors.append(f"music cue {cue.get('id')}: {key} '{cue.get(key)}' is not a shot id")
        if cue.get("from_shot") in ids and cue.get("to_shot") in ids and \
                ids.index(cue["from_shot"]) > ids.index(cue["to_shot"]):
            errors.append(f"music cue {cue.get('id')}: from_shot comes after to_shot")
    return errors


def validate(data: dict) -> None:
    """Raise StoryboardError listing every problem, or return quietly if valid."""
    problems = schema_errors(data)
    if not problems:               # rule checks assume the basic shape is right
        problems = rule_errors(data)
    if problems:
        raise StoryboardError("storyboard is invalid:\n  - " + "\n  - ".join(problems))


def load(path: Path = STORYBOARD_PATH) -> dict:
    """Read and validate. Every stage calls this first, so a broken storyboard
    stops the pipeline before any model is called."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate(data)
    return data


def summary(data: dict) -> str:
    shots = data["shots"]
    total = sum(s["duration_sec"] for s in shots) + END_CARD_SEC
    words = sum(len(s["narration"].split()) for s in shots)
    return (f"'{data['title']}' v{data['version']}: {len(shots)} shots, "
            f"{total:.1f}s incl. end card, {words} narration words ({data['language']['narration']})")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else STORYBOARD_PATH
    try:
        data = load(path)
    except FileNotFoundError:
        print(f"Not found: {path}")
        return 1
    except (json.JSONDecodeError, StoryboardError) as exc:
        print(f"INVALID: {path.name}\n{exc}")
        return 1
    print(f"VALID: {summary(data)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
