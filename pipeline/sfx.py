"""Stage - sound effects: quiet coffee-ceremony sounds, synthesised in code.

Added after User Test #1 (P2: "the familiar sounds of the ceremony, such as coffee
beans roasting, coffee being poured, and cups touching"). No recordings, samples
or licences: every sound is generated with numpy, deterministically (fixed seed).

Each shot lists its effects in storyboard.json, e.g. "sfx": ["roast"]:
  wash   water swishing in a bowl        roast  beans crackling and popping in the pan
  grind  wooden pestle thuds in a mortar  pour   a thin stream of coffee into small cups
  clink  small ceramic cups touching

Output: outputs/sfx/sfx.wav (48 kHz stereo, whole-film length, peak -12 dBFS),
mixed by assemble.py into the music bed, so it also ducks under the voice.
Run:    python -m pipeline.sfx [--force]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from pipeline import storyboard, subtitles
from pipeline.common import OUTPUTS, StageError, cached_call
from pipeline.music import SR, write_wav

SFX_DIR = OUTPUTS / "sfx"
SFX_WAV = SFX_DIR / "sfx.wav"
VERSION = "sfx-synth-v2"   # v2: + chisel, wind
SEED = 9090


def band(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    """Band-pass by zeroing FFT bins outside [lo, hi] Hz."""
    spec = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    spec[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(spec, len(x))


def fades(x: np.ndarray, sec: float = 0.4) -> np.ndarray:
    n = min(len(x) // 2, int(sec * SR))
    env = np.ones(len(x))
    env[:n] = np.linspace(0, 1, n)
    env[-n:] = np.linspace(1, 0, n)
    return x * env


def wash(dur: float, rng) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    swirl = 0.5 + 0.5 * np.sin(2 * np.pi * 0.6 * t) * np.sin(2 * np.pi * 0.17 * t + 1)
    return fades(band(rng.normal(0, 1, len(t)), 300, 2500) * swirl ** 2, 0.8)


def roast(dur: float, rng) -> np.ndarray:
    n = int(dur * SR)
    out = band(rng.normal(0, 0.15, n), 2000, 7000)                  # sizzle bed
    for _ in range(int(dur * 9)):                                    # crackles / pops
        i = rng.integers(0, n - 2000)
        k = rng.integers(200, 1200)
        out[i:i + k] += rng.normal(0, 1, k) * np.exp(-np.arange(k) / (k / 5)) * rng.uniform(0.4, 1.0)
    return fades(band(out, 800, 9000), 0.6)


def grind(dur: float, rng) -> np.ndarray:
    n = int(dur * SR)
    out = np.zeros(n)
    t = 0.4
    while t < dur - 0.4:
        k = int(0.18 * SR)
        tt = np.arange(k) / SR
        thud = np.sin(2 * np.pi * (95 + 40 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 22)
        thud += band(rng.normal(0, 0.4, k), 200, 1500) * np.exp(-tt * 40)
        i = int(t * SR)
        out[i:i + k] += thud * rng.uniform(0.7, 1.0)
        t += 0.75 + rng.uniform(-0.08, 0.08)                         # steady pounding
    return fades(out, 0.2)


def pour(dur: float, rng) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    wobble = band(rng.normal(0, 1, n), 4, 30)
    bubble = 1 + 0.5 * wobble / (np.std(wobble) or 1.0)               # irregular gurgle
    stream = band(rng.normal(0, 1, n), 600, 3200) * np.clip(bubble, 0, None)
    stream *= 0.6 + 0.4 * np.clip(np.sin(2 * np.pi * t / max(dur, 1) * 3), 0, 1)  # cup to cup
    return fades(stream, 0.5)


def clink(dur: float, rng) -> np.ndarray:
    n = int(dur * SR)
    out = np.zeros(n)
    for start in (0.6, 0.6 + rng.uniform(1.2, 2.0)):
        if start > dur - 0.6:
            break
        k = int(0.6 * SR)
        tt = np.arange(k) / SR
        tone = sum(a * np.sin(2 * np.pi * f * tt) * np.exp(-tt * d)
                   for f, a, d in ((2350, 1.0, 9), (3810, 0.6, 12), (5620, 0.35, 16)))
        i = int(start * SR)
        out[i:i + k] += tone
    return out


def chisel(dur: float, rng) -> np.ndarray:
    """Iron chisel on volcanic stone: a bright metallic tap plus a short gritty impact."""
    n = int(dur * SR)
    out = np.zeros(n)
    t = 0.5
    while t < dur - 0.5:
        k = int(0.25 * SR)
        tt = np.arange(k) / SR
        ring = sum(a * np.sin(2 * np.pi * f * tt) * np.exp(-tt * d)
                   for f, a, d in ((1870, 0.5, 30), (3150, 0.35, 40), (4420, 0.2, 55)))
        grit = band(rng.normal(0, 1, k), 1500, 6000) * np.exp(-tt * 60)
        i = int(t * SR)
        out[i:i + k] += (ring + grit) * rng.uniform(0.6, 1.0)
        t += rng.uniform(0.45, 0.9)                                  # several workers, irregular
    return fades(out, 0.2)


def wind(dur: float, rng) -> np.ndarray:
    """Highland wind: low band-passed noise with slow gusts."""
    t = np.arange(int(dur * SR)) / SR
    gust = 0.55 + 0.45 * np.sin(2 * np.pi * 0.13 * t + 0.7) * np.sin(2 * np.pi * 0.05 * t)
    return fades(band(rng.normal(0, 1, len(t)), 120, 900) * gust, 1.5)


EFFECTS = {"wash": wash, "roast": roast, "grind": grind, "pour": pour, "clink": clink,
           "chisel": chisel, "wind": wind}


def build(sb: dict, out: Path) -> dict:
    rng = np.random.default_rng(SEED)
    total = sum(s["duration_sec"] for s in sb["shots"]) + storyboard.END_CARD_SEC
    track = np.zeros((int(total * SR), 2))
    starts = subtitles.shot_starts(sb)
    used = []
    for s in sb["shots"]:
        for name in s.get("sfx", []):
            mono = EFFECTS[name](float(s["duration_sec"]), rng)
            peak = np.max(np.abs(mono)) or 1.0
            mono = mono / peak
            i0 = int(starts[s["id"]] * SR)
            i1 = min(len(track), i0 + len(mono))
            pan = rng.uniform(0.35, 0.65)
            track[i0:i1, 0] += mono[: i1 - i0] * (1 - pan)
            track[i0:i1, 1] += mono[: i1 - i0] * pan
            used.append(f"{s['id']}:{name}")
    if not used:
        raise StageError("no shot has an 'sfx' entry")
    track *= 0.25 / max(np.max(np.abs(track)), 1e-9)                   # peak -12 dBFS
    write_wav(out, track)
    return {"notes": "effects " + ", ".join(used)}


def run(force: bool = False) -> Path | None:
    sb = storyboard.load()
    if not any(s.get("sfx") for s in sb["shots"]):
        print("  no sfx in storyboard, skipped")
        return None
    plan = [(s["id"], s["duration_sec"], s.get("sfx", [])) for s in sb["shots"]]
    r = cached_call(stage="sfx", shot_id=None, provider="local", model=f"numpy-{VERSION}",
                    parameters={"effects": sorted(EFFECTS)}, seed=SEED, inputs={"plan": plan},
                    output=SFX_WAV, fn=lambda o: build(sb, o), max_attempts=1, force=force)
    print(f"  sfx: {r.status} {r.latency_sec:.1f}s  {r.record.get('notes') or ''}")
    return SFX_WAV


if __name__ == "__main__":
    try:
        run(force="--force" in sys.argv)
    except StageError as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)
