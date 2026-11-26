"""Stage - music: an original instrumental score composed in code (fallback for ACE-Step).

Why this exists: ACE-Step 1.5 on Kaggle failed (FAILURES.md F-06). The score is
required, so this stage composes one deterministically with numpy, no GPU:
  - a krar-like plucked melody (additive synthesis with decaying harmonics)
  - in the Tizita qenet, the Ethiopian pentatonic mode of nostalgia and longing
  - over a soft E drone, with a warm pad in the resolve section, plus a simple reverb
  - shaped by the storyboard's music cues (m01 sparse -> m02 builds -> m03 resolves)
Same inputs + same seed -> identical WAV, every time.

Run:
  python -m pipeline.music                 make 3 candidates + previews under the narration
  python -m pipeline.music --choose B      copy candidate B to outputs/music/score.wav
Outputs:
  outputs/music/candidates/{A,B,C}.wav     48 kHz stereo
  outputs/music/preview_{A,B,C}.mp3        candidate ducked under the narration, for listening
  outputs/music/score.wav                  the chosen score (read by assemble.py)
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

from pipeline import storyboard, subtitles
from pipeline.common import OUTPUTS, ROOT, StageError, cached_call, log_run

SR = 48_000
MUSIC_DIR = OUTPUTS / "music"
CAND_DIR = MUSIC_DIR / "candidates"
SCORE = MUSIC_DIR / "score.wav"
E3 = 164.81  # root: E (storyboard key E minor)

# Tizita qenet: pentatonic. Intervals in semitones from the root.
SCALES = {"tizita_minor": [0, 2, 3, 7, 8], "tizita_major": [0, 2, 4, 7, 9]}

CANDIDATES = {
    "A": {"scale": "tizita_minor", "bpm": 66, "density": (0.22, 0.40, 0.30), "drone": 0.55,
          "desc": "Tizita minor, 66 bpm, sparse and intimate"},
    "B": {"scale": "tizita_major", "bpm": 72, "density": (0.25, 0.45, 0.35), "drone": 0.45,
          "desc": "Tizita major, 72 bpm, warmer and brighter"},
    "C": {"scale": "tizita_minor", "bpm": 80, "density": (0.30, 0.55, 0.40), "drone": 0.70,
          "desc": "Tizita minor, 80 bpm, fuller drone and busier krar"},
}
VERSION = "tizita-synth-v1"


# ------------------------------------------------------------------ synthesis
def hz(semitones_from_root: int, octave: int = 0) -> float:
    return E3 * 2 ** ((semitones_from_root + 12 * octave) / 12)


def pluck(freq: float, dur: float, vel: float, rng: np.random.Generator) -> np.ndarray:
    """Krar-like pluck: bright attack, upper harmonics die fast, slight inharmonicity."""
    t = np.arange(int(dur * SR)) / SR
    out = np.zeros_like(t)
    for h in range(1, 9):
        f = freq * h * (1 + 0.0005 * h * h)
        if f > SR / 2.2:
            break
        out += (vel / h ** 1.15) * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi)) \
            * np.exp(-(1.0 + 1.6 * h) * t)
    n = min(len(t), int(0.008 * SR))                       # string "pick" noise
    out[:n] += rng.normal(0, 0.12 * vel, n) * np.linspace(1, 0, n)
    a = min(len(t), int(0.002 * SR))
    out[:a] *= np.linspace(0, 1, a)                         # no click
    return out


def sine_layer(freqs: list[float], total: float, lfo_hz: float, rng: np.random.Generator) -> np.ndarray:
    t = np.arange(int(total * SR)) / SR
    out = np.zeros_like(t)
    for f in freqs:
        out += np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi)) \
            + 0.3 * np.sin(2 * np.pi * 2 * f * t) + 0.1 * np.sin(2 * np.pi * 3 * f * t)
    return out * (0.7 + 0.3 * np.sin(2 * np.pi * lfo_hz * t)) / max(len(freqs), 1)


def envelope(total: float, points: list[tuple[float, float]]) -> np.ndarray:
    t = np.arange(int(total * SR)) / SR
    xs, ys = zip(*points)
    return np.interp(t, xs, ys)


def reverb(x: np.ndarray, seconds: float, mix: float, rng: np.random.Generator) -> np.ndarray:
    n = int(seconds * SR)
    ir = rng.normal(0, 1, n) * np.exp(-np.arange(n) / SR * (6.9 / seconds))
    ir /= np.sqrt(np.sum(ir ** 2))
    size = 1 << int(np.ceil(np.log2(len(x) + n)))
    wet = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[:len(x)]
    return (1 - mix) * x + mix * wet


def section_bounds(sb: dict) -> list[tuple[float, float, str]]:
    """Map music cues (from_shot..to_shot) to times. The last cue runs through the end card."""
    starts = subtitles.shot_starts(sb)
    total = sum(s["duration_sec"] for s in sb["shots"]) + storyboard.END_CARD_SEC
    ends = {s["id"]: starts[s["id"]] + s["duration_sec"] for s in sb["shots"]}
    cues = sb["music"]["cues"]
    out = []
    for i, c in enumerate(cues):
        end = total if i == len(cues) - 1 else ends[c["to_shot"]]
        out.append((starts[c["from_shot"]], end, c["id"]))
    return out


def compose(sb: dict, cfg: dict, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    total = sum(s["duration_sec"] for s in sb["shots"]) + storyboard.END_CARD_SEC
    n = int(total * SR)
    left, right = np.zeros(n), np.zeros(n)
    scale = SCALES[cfg["scale"]]
    step = 60 / cfg["bpm"] / 2                               # eighth notes
    sections = section_bounds(sb)

    # melody: random walk over the scale, density per section, phrases breathe
    degree = 5                                               # index into 2-octave scale
    ladder = [(iv, o) for o in (0, 1) for iv in scale] + [(scale[0], 2)]
    for si, (a, b, _) in enumerate(sections):
        dens = cfg["density"][min(si, len(cfg["density"]) - 1)]
        t = a + 0.5
        last_section = si == len(sections) - 1
        while t < b - (2.5 if last_section else 0.3):
            if rng.random() < dens:
                degree = int(np.clip(degree + rng.choice([-2, -1, -1, 0, 1, 1, 2]), 0, len(ladder) - 1))
                iv, octv = ladder[degree]
                note = pluck(hz(iv, octv), 2.2, 0.55 + 0.2 * rng.random(), rng)
                i0 = int(t * SR); i1 = min(n, i0 + len(note))
                pan = 0.5 + 0.25 * np.sin(t * 0.7)
                left[i0:i1] += note[: i1 - i0] * (1 - pan)
                right[i0:i1] += note[: i1 - i0] * pan
            t += step * (2 if rng.random() < 0.25 else 1)
    # final resolving root, rung like a last pluck over the end card
    for iv, octv, d in ((0, 0, 0.0), (7, 0, 0.12), (0, 1, 0.24)):
        note = pluck(hz(iv, octv), 3.5, 0.6, rng)
        i0 = int((total - 3.2 + d) * SR); i1 = min(n, i0 + len(note))
        left[i0:i1] += note[: i1 - i0] * 0.5; right[i0:i1] += note[: i1 - i0] * 0.5

    # drone (E + B), swelling with the cue structure
    m01_end, m02_end = sections[0][1], sections[1][1] if len(sections) > 1 else total
    drone = sine_layer([hz(0, -1), hz(7, -1)], total, 0.07, rng) * cfg["drone"] * 0.35
    drone *= envelope(total, [(0, 0), (3, 0.5), (m01_end, 0.6), (m02_end, 1.0),
                              (total - 4, 0.9), (total, 0)])
    # warm pad only in the resolve section
    pad = sine_layer([hz(scale[0], 0), hz(scale[3], 0), hz(scale[0], 1)], total, 0.11, rng) * 0.12
    pad *= envelope(total, [(0, 0), (m02_end - 2, 0), (m02_end + 3, 1), (total - 3, 1), (total, 0)])

    left += drone + pad
    right += drone * 0.95 + pad
    left = reverb(left, 2.4, 0.28, rng)
    right = reverb(right, 2.4, 0.28, np.random.default_rng(seed + 99))
    stereo = np.stack([left, right], axis=1)
    fade = int(0.05 * SR)
    stereo[:fade] *= np.linspace(0, 1, fade)[:, None]
    stereo *= 0.707 / max(np.max(np.abs(stereo)), 1e-9)      # peak -3 dBFS
    return stereo


def write_wav(path: Path, stereo: np.ndarray) -> None:
    data = (np.clip(stereo, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(data.tobytes())


# ------------------------------------------------------------------ previews / choice
def preview(sb: dict, wav: Path, out: Path) -> None:
    """Candidate ducked under the real narration, so it is judged where it will live."""
    from pipeline.assemble import mix_graph
    inputs, graph = mix_graph(sb, ["-i", str(wav)])
    proc = subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *inputs,
                           "-filter_complex", graph + ";[mix]loudnorm=I=-14:TP=-1[out]",
                           "-map", "[out]", "-c:a", "libmp3lame", "-q:a", "3", str(out)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise StageError(f"preview ffmpeg: {proc.stderr[-500:]}")


def run(force: bool = False) -> None:
    sb = storyboard.load()
    CAND_DIR.mkdir(parents=True, exist_ok=True)
    base_seed = int(sb["music"].get("seed", 4242))
    timing = [(s["id"], s["duration_sec"]) for s in sb["shots"]]
    for i, (name, cfg) in enumerate(CANDIDATES.items()):
        seed = base_seed + i
        out = CAND_DIR / f"{name}.wav"
        params = {k: cfg[k] for k in ("scale", "bpm", "density", "drone")} | {"version": VERSION}
        r = cached_call(stage="music", shot_id=name, provider="local", model=f"numpy-{VERSION}",
                        parameters=params, seed=seed,
                        inputs={"timing": timing, "cues": sb["music"]["cues"]}, output=out,
                        fn=lambda p, cfg=cfg, seed=seed: (write_wav(p, compose(sb, cfg, seed)),
                                                          {"notes": cfg["desc"]})[1],
                        max_attempts=1, force=force)
        prev = MUSIC_DIR / f"preview_{name}.mp3"
        if force or r.status == "ok" or not prev.exists():
            preview(sb, out, prev)
        print(f"  {name}: {r.status} {r.latency_sec:.1f}s  {cfg['desc']}  -> {prev.relative_to(ROOT)}")


def choose(name: str) -> None:
    src = CAND_DIR / f"{name}.wav"
    if not src.exists():
        raise StageError(f"candidate {name} not found; run python -m pipeline.music first")
    shutil.copyfile(src, SCORE)
    meta = json.loads((src.with_name(src.name + ".meta.json")).read_text(encoding="utf-8"))
    log_run(stage="music_choice", shot_id=name, provider="local", model=meta["model"],
            status="ok", seed=meta["seed"], parameters=meta["parameters"],
            output="outputs/music/score.wav", notes=CANDIDATES[name]["desc"])
    print(f"score.wav <- candidate {name} ({CANDIDATES[name]['desc']})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--choose", choices=list(CANDIDATES))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    try:
        choose(a.choose) if a.choose else run(force=a.force)
    except StageError as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)
