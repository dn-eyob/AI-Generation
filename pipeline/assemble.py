"""Stage - assembly: the finished film in 9:16 and 16:9, all in FFmpeg, all from the storyboard.

Audio (built once, shared by both aspect ratios):
  1. narration lines placed at each shot's start (+0.3 s), padded to shot length
  2. stems pre-balanced: voice -> about -16 LUFS, music -> about -26 LUFS
  3. music ducked under the voice with sidechaincompress
  4. TWO-PASS loudnorm to -14 LUFS / -1 dBTP (pass 1 measures, pass 2 applies; see E-04)
Picture (per aspect): concat of outputs/shots/<aspect>/*.mp4 + 3 s end card,
  English subtitles + "Made with AI" end-card text burned in via libass, inside the safe area.

Music: outputs/music/score.wav if a score has been chosen; otherwise the
placeholder drone, and the output is named rough_cut_* instead of three_rounds_*.

Output: outputs/final/<name>_vertical.mp4, outputs/final/<name>_horizontal.mp4
Run:    python -m pipeline.assemble [--force]
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from pipeline import storyboard, subtitles
from pipeline.common import OUTPUTS, StageError, cached_call, file_hash, log_run
from pipeline.radio_cut import DRONE

FINAL_DIR = OUTPUTS / "final"
WORK_DIR = OUTPUTS / "assembly"
SHOT_DIR = OUTPUTS / "shots"
NARRATION_DIR = OUTPUTS / "narration"
SCORE = OUTPUTS / "music" / "score.wav"
END_CARD_SEC = storyboard.END_CARD_SEC
FPS = 24

DUCK = {"threshold": 0.02, "ratio": 6, "attack": 300, "release": 1500}
TARGET = {"I": -14.0, "TP": -1.0, "LRA": 11.0}
VOICE_LUFS, MUSIC_LUFS = -16, -26
SFX = OUTPUTS / "sfx" / "sfx.wav"
SFX_GAIN = 1.0   # sfx.wav measures about -29 LUFS: ~13 dB under the voice, not ducked (E-10)

# libass styles for SRT (script units are relative to a 384x288 canvas)
SUB_STYLE = {
    # vertical: lifted above the bottom ~25% that phone apps cover with buttons/captions;
    # narrow frame -> wrap at 33 chars so lines stay at 2 (rough cut showed 3 at 42 chars)
    "vertical": {"size": (720, 1280), "wrap": 33,
                 "style": "FontName=Arial,FontSize=9,MarginV=70,MarginL=12,MarginR=12"},
    "horizontal": {"size": (1280, 720), "wrap": 42,
                   "style": "FontName=Arial,FontSize=15,MarginV=18"},
}
COMMON_STYLE = ("PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,"
                "BorderStyle=1,Outline=1.2,Shadow=0,Alignment=2")

END_CARD_TEXT = {
    "vertical": ("{\\an5}{\\fs14}Made with AI\\N\\N{\\fs9}"
                 "Images: FLUX.1 schnell\\NVoice: Gemini 3.8 Flash TTS\\N"
                 "Music: composed in code (Tizita)\\NEdit: FFmpeg\\N\\N"
                 "Illustrated characters,\\Nnot real people"),
    "horizontal": ("{\\an5}{\\fs24}Made with AI\\N\\N{\\fs13}"
                   "Images: FLUX.1 schnell  ·  Voice: Gemini 3.8 Flash TTS\\N"
                   "Music: composed in code (Tizita scale)  ·  Edit: FFmpeg\\N"
                   "Illustrated characters, not real people"),
}


def ffmpeg(args: list[str], cwd: Path | None = None) -> str:
    proc = subprocess.run(["ffmpeg", "-y", "-hide_banner", *args], cwd=cwd,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise StageError(f"ffmpeg: {proc.stderr.strip()[-900:]}")
    return proc.stderr


def total_seconds(sb: dict) -> float:
    return sum(float(s["duration_sec"]) for s in sb["shots"]) + END_CARD_SEC


# ------------------------------------------------------------------ audio
def mix_graph(sb: dict, music_input: list[str], sfx: Path | None = None) -> tuple[list[str], str]:
    """Inputs + filter graph producing [mix] (before final loudness).
    If `sfx` is given, the ceremony sounds join the music bed, so they duck under the voice too."""
    inputs, parts, segs = [], [], []
    for s in sb["shots"]:
        dur, wav, label = float(s["duration_sec"]), NARRATION_DIR / f"{s['id']}.wav", f"v{s['id']}"
        if s["narration"] and wav.exists():
            idx = len(inputs) // 2
            inputs += ["-i", str(wav)]
            parts.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=mono,"
                         f"adelay={int(subtitles.NARRATION_OFFSET_SEC * 1000)},"
                         f"apad=whole_dur={dur},atrim=duration={dur}[{label}]")
        else:
            parts.append(f"anullsrc=r=48000:cl=mono,atrim=duration={dur}[{label}]")
        segs.append(f"[{label}]")
    parts.append(f"anullsrc=r=48000:cl=mono,atrim=duration={END_CARD_SEC}[vend]")
    segs.append("[vend]")
    total = total_seconds(sb)
    music_idx = len(inputs) // 2
    inputs += music_input
    parts += [
        f"{''.join(segs)}concat=n={len(segs)}:v=0:a=1,loudnorm=I={VOICE_LUFS}:TP=-2,"
        "aresample=48000,aformat=channel_layouts=stereo[voice]",
        "[voice]asplit=2[voice_mix][voice_key]",
        f"[{music_idx}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=duration={total},"
        f"loudnorm=I={MUSIC_LUFS}:TP=-6,aresample=48000,"
        f"afade=t=in:d=2,afade=t=out:st={total - 4}:d=4[music]",
        f"[music][voice_key]sidechaincompress=threshold={DUCK['threshold']}:ratio={DUCK['ratio']}:"
        f"attack={DUCK['attack']}:release={DUCK['release']}[ducked]",
    ]
    if sfx:
        # Effects sit beside the voice, NOT in the ducked bed: inside the bed they were
        # ducked on top of being quiet and became inaudible (E-10).
        sfx_idx = music_idx + 1
        inputs += ["-i", str(sfx)]
        parts += [
            f"[{sfx_idx}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=duration={total},"
            f"volume={SFX_GAIN}[sfx]",
            "[voice_mix][ducked][sfx]amix=inputs=3:duration=first:normalize=0[mix]",
        ]
    else:
        parts.append("[voice_mix][ducked]amix=inputs=2:duration=first:normalize=0[mix]")
    return inputs, ";".join(parts)


def build_audio(sb: dict, music_input: list[str], out: Path, sfx: Path | None = None) -> dict:
    """Pre-mix, then two-pass loudnorm to TARGET. Writes a 48 kHz stereo WAV."""
    premix = out.with_name("premix.wav")
    inputs, graph = mix_graph(sb, music_input, sfx)
    ffmpeg([*inputs, "-filter_complex", graph, "-map", "[mix]", "-t", str(total_seconds(sb)),
            "-c:a", "pcm_s16le", str(premix)])
    # pass 1: measure
    log = ffmpeg(["-i", str(premix), "-af",
                  f"loudnorm=I={TARGET['I']}:TP={TARGET['TP']}:LRA={TARGET['LRA']}:print_format=json",
                  "-f", "null", "-"])
    m = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", log, re.S).group(0))
    # pass 2: apply with measured values (linear mode = no pumping)
    ffmpeg(["-i", str(premix), "-af",
            f"loudnorm=I={TARGET['I']}:TP={TARGET['TP']}:LRA={TARGET['LRA']}:"
            f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
            f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
            "aresample=48000", "-c:a", "pcm_s16le", str(out)])
    measured = measure_loudness(out)
    premix.unlink(missing_ok=True)
    return {"notes": f"pass1 input_i={m['input_i']} -> final I={measured['I']} LUFS, "
                     f"TP={measured['TP']} dBTP, LRA={measured['LRA']}"}


def measure_loudness(path: Path) -> dict:
    log = ffmpeg(["-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"])
    summary = log[log.rfind("Summary:"):]
    get = lambda key: float(re.search(rf"{key}:\s+(-?[\d.]+)", summary).group(1))
    return {"I": get("I"), "LRA": get("LRA"), "TP": get("Peak")}


# ------------------------------------------------------------------ picture
def end_card_text(sb: dict, aspect: str) -> str:
    """Optional closing title (storyboard `end_card_title`) above the AI disclosure."""
    title = sb.get("end_card_title", "").strip()
    if not title:
        return END_CARD_TEXT[aspect]
    size = 13 if aspect == "vertical" else 22
    body = END_CARD_TEXT[aspect].replace("{\\an5}", "", 1)
    return f"{{\\an5}}{{\\fs{size}}}{{\\b1}}{title}{{\\b0}}\\N\\N{body}"


def write_srt_with_end_card(sb: dict, aspect: str, path: Path) -> None:
    items = subtitles.cues(sb, width=SUB_STYLE[aspect]["wrap"])
    total = total_seconds(sb)
    items.append((total - END_CARD_SEC + 0.2, total - 0.1, end_card_text(sb, aspect)))
    subtitles.write_srt(path, items)


def build_video(sb: dict, aspect: str, audio: Path, srt: Path, out: Path) -> dict:
    w, h = SUB_STYLE[aspect]["size"]
    inputs, labels = [], []
    for i, s in enumerate(sb["shots"]):
        inputs += ["-i", str(SHOT_DIR / aspect / f"{s['id']}.mp4")]
        labels.append(f"[{i}:v]")
    n = len(sb["shots"])
    inputs += ["-f", "lavfi", "-i", f"color=c=0x140d08:s={w}x{h}:r={FPS}:d={END_CARD_SEC}"]
    inputs += ["-i", str(audio)]
    norm = "".join(f"{lab}fps={FPS},setsar=1,format=yuv420p[n{i}];" for i, lab in enumerate(labels))
    graph = (f"{norm}[{n}:v]setsar=1,format=yuv420p[nend];"
             f"{''.join(f'[n{i}]' for i in range(n))}[nend]concat=n={n + 1}:v=1:a=0[cat];"
             f"[cat]subtitles={srt.name}:force_style='{SUB_STYLE[aspect]['style']},{COMMON_STYLE}'[vout]")
    ffmpeg([*inputs, "-filter_complex", graph, "-map", "[vout]", "-map", f"{n + 1}:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-b:a", "192k", "-t", str(total_seconds(sb)), "-movflags", "+faststart",
            out.name], cwd=out.parent)
    return {"notes": f"{aspect} {w}x{h}, {n} shots + end card"}


# ------------------------------------------------------------------ run
def run(force: bool = False) -> list[Path]:
    sb = storyboard.load()
    have_score = SCORE.exists()
    slug = sb.get("slug", "film")
    name = slug if have_score else f"{slug}_rough_cut"
    music_input = (["-i", str(SCORE)] if have_score
                   else ["-f", "lavfi", "-i", f"aevalsrc='{DRONE}':s=48000:d={total_seconds(sb)}"])
    music_id = file_hash(SCORE) if have_score else "placeholder-drone"

    WORK_DIR.mkdir(parents=True, exist_ok=True)
    narration = {p.stem: file_hash(p) for p in sorted(NARRATION_DIR.glob("s*.wav"))}
    timing = [{k: s[k] for k in ("id", "duration_sec", "narration", "subtitle")} for s in sb["shots"]]

    sfx = SFX if (SFX.exists() and any(s.get("sfx") for s in sb["shots"])) else None
    audio = WORK_DIR / f"{name}_audio.wav"
    ra = cached_call(stage="assemble_audio", shot_id=None, provider="local", model="ffmpeg",
                     parameters={"duck": DUCK, "target": TARGET, "voice_lufs": VOICE_LUFS,
                                 "music_lufs": MUSIC_LUFS, "sfx_gain": SFX_GAIN if sfx else None},
                     seed=None, inputs={"narration": narration, "timing": timing, "music": music_id,
                                        "sfx": file_hash(sfx) if sfx else None},
                     output=audio, fn=lambda o: build_audio(sb, music_input, o, sfx),
                     max_attempts=1, force=force)
    print(f"audio: {ra.status} {ra.latency_sec:.1f}s  {ra.record.get('notes') or ''}")

    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    outs = []
    for aspect in ("vertical", "horizontal"):
        srt = FINAL_DIR / f"{name}_{aspect}.srt"
        write_srt_with_end_card(sb, aspect, srt)
        out = FINAL_DIR / f"{name}_{aspect}.mp4"
        shots = {s["id"]: file_hash(SHOT_DIR / aspect / f"{s['id']}.mp4") for s in sb["shots"]}
        rv = cached_call(stage="assemble_video", shot_id=aspect, provider="local", model="ffmpeg",
                         parameters={"style": SUB_STYLE[aspect], "fps": FPS, "crf": 20},
                         seed=None, inputs={"shots": shots, "audio": file_hash(audio),
                                            "srt": srt.read_text(encoding="utf-8")},
                         output=out, fn=lambda o, a=aspect, srt=srt: build_video(sb, a, audio, srt, o),
                         max_attempts=1, force=force)
        print(f"{aspect}: {rv.status} {rv.latency_sec:.1f}s -> {out.relative_to(OUTPUTS.parent)}")
        outs.append(out)

    final = measure_loudness(outs[0])
    log_run(stage="assemble_check", shot_id=None, provider="local", model="ffmpeg-ebur128",
            status="ok", parameters={"file": outs[0].name}, notes=f"measured {final}")
    print(f"measured loudness of {outs[0].name}: {final}  (target I={TARGET['I']}, TP<={TARGET['TP']})")
    return outs


if __name__ == "__main__":
    try:
        run(force="--force" in sys.argv)
    except StageError as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)
