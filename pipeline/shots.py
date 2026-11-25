"""Stage - moving shots: one clip per shot per aspect ratio.

For each shot:
  - video_mode "wan" AND outputs/wan/<id>.mp4 exists (made on Kaggle) -> use that clip,
    cropped to the aspect and fitted to the shot length (gentle slow-down up to 1.6x,
    then hold the last frame)
  - otherwise -> Ken Burns: slow pan/zoom over the keyframe with FFmpeg zoompan,
    direction taken from the shot's `camera` field. Deterministic, no GPU.
This is also the automatic FALLBACK when a Wan clip is missing or failed.

Input:   storyboard.json, outputs/keyframes/<id>.png, optional outputs/wan/<id>.mp4
Output:  outputs/shots/vertical/<id>.mp4   (720x1280)
         outputs/shots/horizontal/<id>.mp4 (1280x720)

Run:  python -m pipeline.shots [--shot s04] [--force]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from pipeline import storyboard
from pipeline.common import OUTPUTS, StageError, cached_call, file_hash
from pipeline.keyframes import keyframe_path

SHOT_DIR = OUTPUTS / "shots"
WAN_DIR = OUTPUTS / "wan"
FPS = 24
ASPECTS = {
    "vertical": {"crop": "ih*9/16:ih", "work": "1440:2560", "out": (720, 1280)},
    "horizontal": {"crop": "iw:iw*9/16", "work": "2560:1440", "out": (1280, 720)},
}
MAX_SLOWDOWN = 1.6
ZOOM = 0.12   # 12% zoom range: slow, gentle


def kenburns_expr(camera: str, frames: int) -> tuple[str, str, str]:
    """zoompan z/x/y expressions for a camera move. `on` = output frame number."""
    p = f"(on/{max(frames - 1, 1)})"            # progress 0 -> 1
    cx, cy = "(iw/2-(iw/zoom/2))", "(ih/2-(ih/zoom/2))"
    if camera == "push_in":
        return f"1+{ZOOM}*{p}", cx, cy
    if camera == "pull_out":
        return f"1+{ZOOM}*(1-{p})", cx, cy
    if camera == "pan_right":
        return f"1+{ZOOM}", f"(iw-iw/zoom)*{p}", cy
    if camera == "pan_left":
        return f"1+{ZOOM}", f"(iw-iw/zoom)*(1-{p})", cy
    if camera == "tilt_up":
        return f"1+{ZOOM}", cx, f"(ih-ih/zoom)*(1-{p})"
    if camera == "tilt_down":
        return f"1+{ZOOM}", cx, f"(ih-ih/zoom)*{p}"
    return f"1+0.03*{p}", cx, cy                 # static: barely-there breathing


def kenburns_cmd(img: Path, out: Path, camera: str, dur: float, aspect: str) -> list[str]:
    a = ASPECTS[aspect]
    frames = int(round(dur * FPS))
    z, x, y = kenburns_expr(camera, frames)
    w, h = a["out"]
    vf = (f"crop={a['crop']},scale={a['work']}:flags=lanczos,"
          f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={w}x{h}:fps={FPS},"
          f"format=yuv420p")
    return ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(img),
            "-vf", vf, "-frames:v", str(frames), "-r", str(FPS),
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(out)]


def probe_seconds(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def wan_cmd(clip: Path, out: Path, dur: float, aspect: str) -> list[str]:
    a = ASPECTS[aspect]
    w, h = a["out"]
    clip_sec = probe_seconds(clip)
    slow = min(MAX_SLOWDOWN, max(1.0, dur / clip_sec))
    hold = max(0.0, dur - clip_sec * slow)
    crop = "ih*9/16:ih" if aspect == "vertical" else "iw:iw*9/16"
    vf = (f"crop='min(iw,{crop.split(':')[0]})':'min(ih,{crop.split(':')[1]})',"
          f"scale={w}:{h}:flags=lanczos,setpts={slow:.3f}*PTS,fps={FPS},"
          f"tpad=stop_mode=clone:stop_duration={hold:.3f},trim=duration={dur},format=yuv420p")
    return ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(clip), "-an",
            "-vf", vf, "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(out)]


def run(only: str | None = None, force: bool = False) -> None:
    sb = storyboard.load()
    for shot in sb["shots"]:
        sid = shot["id"]
        if only and sid != only:
            continue
        img = keyframe_path(sid)
        if not img.exists():
            raise StageError(f"{sid}: keyframe missing ({img}); run pipeline.keyframes first")
        wan_clip = WAN_DIR / f"{sid}.mp4"
        use_wan = shot.get("video_mode") == "wan" and wan_clip.exists()
        dur = float(shot["duration_sec"])

        for aspect in ASPECTS:
            out = SHOT_DIR / aspect / f"{sid}.mp4"
            if use_wan:
                mode, src_hash = "wan", file_hash(wan_clip)
                build = lambda o, aspect=aspect: wan_cmd(wan_clip, o, dur, aspect)
            else:
                mode, src_hash = "kenburns", file_hash(img)
                build = lambda o, aspect=aspect: kenburns_cmd(img, o, shot["camera"], dur, aspect)

            def make(path: Path, build=build, mode=mode) -> dict:
                proc = subprocess.run(build(path), capture_output=True, text=True)
                if proc.returncode != 0:
                    raise StageError(f"ffmpeg: {proc.stderr.strip()[-600:]}")
                return {"notes": f"mode={mode}"}

            r = cached_call(stage="shots", shot_id=f"{sid}/{aspect}", provider="local",
                            model=f"ffmpeg-{mode}",
                            parameters={"camera": shot["camera"], "duration_sec": dur,
                                        "aspect": aspect, "zoom": ZOOM, "fps": FPS},
                            seed=None, inputs={"source": src_hash, "mode": mode},
                            output=out, fn=make, max_attempts=1, force=force)
            fell_back = shot.get("video_mode") == "wan" and not use_wan
            print(f"  {sid} {aspect:<10} {mode:<8} {r.status}"
                  + ("  (Wan clip missing -> Ken Burns fallback)" if fell_back else ""))


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
