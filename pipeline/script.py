"""Stage 1 - script: turn the story beats into a draft storyboard.json.

Input:   DESIGN.md section 2 (story beats) + the fixed decisions below.
Output:  outputs/script/storyboard_draft.json (cached by input hash)
         storyboard.json (only if it doesn't exist yet, or with --overwrite,
         so your hand edits are never silently replaced)

Run:  python -m pipeline.script [--overwrite] [--force]

Gemini only writes the creative per-shot fields (prompts, narration,
subtitles, reasons, music cues). Style, character, models, voice and seeds
are fixed here, so they are identical across every shot.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

from pipeline import gemini
from pipeline.common import OUTPUTS, ROOT, StageError, cached_call, models_in_cache_order
from pipeline.storyboard import STORYBOARD_PATH, END_CARD_SEC, summary, validate

DRAFT_PATH = OUTPUTS / "script" / "storyboard_draft.json"

# ---------------------------------------------------------------- fixed decisions
STYLE_BLOCK = ("warm hand-painted gouache illustration, earthy browns, coffee-bean reds "
               "and soft golds, golden afternoon light through a window, gentle film grain, "
               "simple shapes, calm and intimate")

CHARACTERS = [{
    "id": "mother",
    "description": ("a generic Ethiopian woman in her fifties with a kind face, hair wrapped "
                    "in a white cotton netela shawl with a thin woven border, wearing a white "
                    "habesha dress with a woven tibeb trim"),
}]

DEFAULTS = {
    "text_model": "gemini-3.8-flash",
    "text_fallback_model": "gemini-3.5-flash",
    "tts_model": "gemini-3.8-flash-tts",
    "tts_voice": "Kore",
    "tts_style": "warm, calm, unhurried, like an elder telling a family story",
    "image_model": "@cf/black-forest-labs/flux-1-schnell",
    "video_model": "Wan2.2-TI2V-5B",
    "fps": 24,
}

TEXT_MODELS = [DEFAULTS["text_model"], DEFAULTS["text_fallback_model"]]
SEED_BASE = 1000


def read_beats() -> str:
    """Section 2 of DESIGN.md. Only this section feeds the hash, so editing
    user-test notes elsewhere in DESIGN.md does not trigger a regeneration."""
    # Normalise line endings: a Windows clone with autocrlf would otherwise change the
    # hash and trigger a needless (key-requiring) Gemini call on an unchanged storyboard.
    text = (ROOT / "DESIGN.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    m = re.search(r"## 2\..*?(?=\n## 3\.)", text, flags=re.S)
    if not m:
        raise StageError("DESIGN.md has no '## 2.' story-beats section")
    return m.group(0).strip()


def build_prompt(beats: str) -> str:
    return f"""You are a film director and screenwriter making a 60-90 second vertical heritage short.

STORY AND BEATS (from the director's design document):
{beats}

AUDIENCE: young Ethiopians, cousins living abroad, families, people interested in Ethiopian culture.
They watch on a phone, often with the sound low. Intended feeling at the end: PRIDE and WARMTH.

FIXED LOOK (added automatically to every image; do NOT repeat it in image_prompt):
{STYLE_BLOCK}

MAIN CHARACTER id "mother" (described automatically; in image_prompt just say "the mother"):
{CHARACTERS[0]['description']}
Other family members appear only as hands, silhouettes, backs or out of focus, never as clear faces.

WRITE 9 or 10 SHOTS covering beats 1-5 in order. Rules:
- duration_sec per shot between 5 and 9; the sum of all shots must be between 68 and 80.
- Vary shot_size (wide to establish, medium for action, close_up / insert for feeling and detail).
- image_prompt: subject, action, setting, composition, light. Subject centred so it crops to both 9:16 and 16:9. No text, signs or letters in the image. Mention real ceremony objects where natural: fresh grass on the floor, incense burner with smoke, small handle-less cups (sini) on a tray, clay jebena coffee pot, roasting pan, wooden mortar, popcorn.
- motion_prompt: ONLY gentle motion and camera (e.g. "smoke curls upward, camera pushes in slowly"). One movement per shot.
- camera: one of static, push_in, pull_out, pan_left, pan_right, tilt_up, tilt_down. Vary it between consecutive shots.
- narration: AMHARIC, written in Ge'ez script, warm, simple, short spoken sentences, written for the ear. About 6-12 Amharic words per shot, fewer for close-ups. One or two shots may have empty narration ("") to let the music breathe.
- subtitle: faithful natural ENGLISH translation of that narration, at most 80 characters. Empty only if narration is empty.
- reason: one sentence saying why the shot exists for the audience.
- The final shot is Bereka (the blessing) and must land pride and warmth; its line should speak to family far from home.
- The rising smoke is a recurring motif: show it in beat 1, beat 2 and the final shot.

ALSO WRITE:
- title_native: the film title "Three Rounds" in Amharic.
- logline: one English sentence.
- music: caption describing an instrumental score (style, mood, instruments such as krar, masenqo, soft strings, texture; no tempo or key in the caption), tempo_bpm (integer), key (e.g. "D minor"), and 2-3 cues, each with id (m01...), from_shot, to_shot, intent (what the music does: starts, builds, drops, resolves).

Return ONLY JSON in exactly this shape:
{{
  "title_native": "...",
  "logline": "...",
  "music": {{"caption": "...", "tempo_bpm": 72, "key": "...", "cues": [{{"id": "m01", "from_shot": "s01", "to_shot": "s04", "intent": "..."}}]}},
  "shots": [
    {{"id": "s01", "beat": 1, "reason": "...", "shot_size": "wide", "duration_sec": 7,
      "characters": ["mother"], "image_prompt": "...", "motion_prompt": "...", "camera": "push_in",
      "narration": "...", "subtitle": "..."}}
  ]
}}"""


def assemble_storyboard(draft: dict) -> dict:
    """Merge Gemini's creative fields with the fixed decisions, then validate."""
    shots = []
    for i, s in enumerate(draft["shots"], start=1):
        shots.append({
            "id": f"s{i:02d}",
            "beat": int(s["beat"]),
            "reason": s["reason"].strip(),
            "shot_size": s["shot_size"],
            "duration_sec": float(s["duration_sec"]),
            "characters": [c for c in s.get("characters", []) if c == "mother"],
            "image_prompt": s["image_prompt"].strip(),
            "motion_prompt": s["motion_prompt"].strip(),
            "camera": s["camera"],
            "video_mode": "kenburns",
            "seed": SEED_BASE + i,
            "narration": s.get("narration", "").strip(),
            "subtitle": s.get("subtitle", "").strip(),
        })
    music = draft["music"]
    storyboard = {
        "title": "Three Rounds",
        "title_native": draft.get("title_native", "").strip(),
        "version": 1,
        "logline": draft.get("logline", "").strip(),
        "language": {"narration": "am", "subtitles": "en"},
        "style": {"style_block": STYLE_BLOCK, "characters": CHARACTERS},
        "defaults": DEFAULTS,
        "music": {
            "caption": music["caption"].strip(),
            "tempo_bpm": int(music["tempo_bpm"]),
            "key": music.get("key", ""),
            "instrumental": True,
            "seed": 4242,
            "cues": music["cues"],
        },
        "shots": shots,
    }
    validate(storyboard)
    return storyboard


def run(overwrite: bool = False, force: bool = False) -> Path:
    beats = read_beats()
    prompt = build_prompt(beats)
    last_exc: Exception | None = None

    for model in models_in_cache_order(TEXT_MODELS, DRAFT_PATH):
        def generate(out: Path, model=model) -> dict:
            draft, usage = gemini.text_json(model, prompt)
            storyboard = assemble_storyboard(draft)   # invalid draft -> exception -> retry
            out.write_text(json.dumps(storyboard, indent=2, ensure_ascii=False), encoding="utf-8")
            return {"notes": f"tokens={usage}"}

        try:
            result = cached_call(stage="script", shot_id=None, provider="google", model=model,
                                 parameters={"temperature": 0.8, "response_mime_type": "application/json"},
                                 seed=None, inputs={"prompt": prompt}, output=DRAFT_PATH,
                                 fn=generate, max_attempts=2, force=force)
            print(f"draft: {result.status} via {model} in {result.latency_sec:.1f}s -> {DRAFT_PATH.relative_to(ROOT)}")
            break
        except StageError as exc:
            last_exc = exc
            print(f"{model} failed; trying next model if any.")
    else:
        raise StageError(f"all text models failed: {last_exc}")

    if STORYBOARD_PATH.exists() and not overwrite:
        print("storyboard.json already exists - NOT overwritten (use --overwrite to replace it).")
    else:
        shutil.copyfile(DRAFT_PATH, STORYBOARD_PATH)
        print("wrote storyboard.json")
    data = json.loads(DRAFT_PATH.read_text(encoding="utf-8"))
    print("draft:", summary(data), f"(end card {END_CARD_SEC}s)")
    return DRAFT_PATH


if __name__ == "__main__":
    try:
        run(overwrite="--overwrite" in sys.argv, force="--force" in sys.argv)
    except StageError as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)
