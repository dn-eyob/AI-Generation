"""Move work between this repo and Kaggle (where the free GPUs are).

  python -m pipeline.kaggle_io bundle
      -> outputs/tmp/kaggle_bundle.zip  (storyboard.json + keyframes + the two
         Kaggle scripts). Upload it to Kaggle as a Dataset named "heritage-bundle".

  python -m pipeline.kaggle_io import <folder-or-zip downloaded from Kaggle output>
      -> copies wan/*.mp4 to outputs/wan/, music/*.wav to outputs/music/candidates/,
         and appends the notebook's *_runs.jsonl lines to runs.jsonl (no duplicates),
         so GPU minutes measured on Kaggle land in the same log as everything else.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

from pipeline.common import OUTPUTS, ROOT, runs_log_path

BUNDLE = OUTPUTS / "tmp" / "kaggle_bundle.zip"


def bundle() -> Path:
    BUNDLE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(BUNDLE, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(ROOT / "storyboard.json", "storyboard.json")
        for p in sorted((OUTPUTS / "keyframes").glob("s*.png")):
            z.write(p, f"keyframes/{p.name}")
        for p in sorted((ROOT / "kaggle").glob("*.py")):
            z.write(p, f"kaggle/{p.name}")
    print(f"bundle: {BUNDLE.relative_to(ROOT)} ({BUNDLE.stat().st_size / 1e6:.1f} MB)")
    return BUNDLE


def import_results(src: Path) -> None:
    tmp = None
    if src.suffix == ".zip":
        tmp = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(src) as z:
            z.extractall(tmp)
        src = tmp
    copied = 0
    for clip in src.rglob("wan/s*.mp4"):
        dest = OUTPUTS / "wan" / clip.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(clip, dest); copied += 1
    for wav in src.rglob("music/*.wav"):
        dest = OUTPUTS / "music" / "candidates" / wav.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(wav, dest); copied += 1

    log = runs_log_path()
    existing = {json.loads(l)["run_id"] for l in log.read_text(encoding="utf-8").splitlines() if l.strip()}
    added = 0
    with open(log, "a", encoding="utf-8") as f:
        for jl in src.rglob("*_runs.jsonl"):
            for line in jl.read_text(encoding="utf-8").splitlines():
                if line.strip() and json.loads(line).get("run_id") not in existing:
                    f.write(line.strip() + "\n"); added += 1
    print(f"imported {copied} media files, appended {added} log lines to {log.name}")
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "bundle":
        bundle()
    elif len(sys.argv) >= 3 and sys.argv[1] == "import":
        import_results(Path(sys.argv[2]))
    else:
        print(__doc__)
        sys.exit(1)
