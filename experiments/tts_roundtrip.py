"""Ceiling experiment: does Gemini TTS really speak Ethiopian / Horn of Africa languages?

Question (from the challenge brief): "We could not confirm that every model handles
[Afaan Oromo, Tigrinya, Somali] well; find out, and document exactly where they fail."

Method (round trip, no human raters needed for the first pass):
  1. Take 3 Amharic narration lines (results/source_lines.json, from development storyboard v7)
       and their Amharic audio (results/audio/am_*.wav).
       Tigrinya (ti), Afaan Oromo (om), Somali (so) = Gemini translation of the English subtitle.
  2. Speak each line with gemini-3.8-flash-tts (same voice and style as the film).
  3. A separate Gemini model transcribes the audio *blind* (not told the language or the text)
     and names the language it hears.
  4. Score: character error rate (CER) between the text sent to TTS and the transcript,
     language-ID correctness, and speaking rate.

Caveat, recorded with the results: this is machine judging machine. A high CER can mean
the TTS mispronounced OR the transcriber is weak in that language. Native-speaker
listening is the ground truth (Amharic: me).

Run:  python -m experiments.tts_roundtrip
Out:  experiments/results/tts_roundtrip.json, experiments/results/tts_roundtrip.md,
      experiments/results/audio/<lang>_<shot>.wav ; every call logged to runs.jsonl
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

from pipeline import gemini, storyboard
from pipeline.common import ROOT, OUTPUTS, StageError, cached_call, models_in_cache_order

RES = ROOT / "experiments" / "results"
AUDIO = RES / "audio"
SHOTS = ["s03", "s07", "s10"]
LANGS = {"am": "Amharic", "ti": "Tigrinya", "om": "Afaan Oromo", "so": "Somali"}
# Long fallback chain: on 2026-11-26 both 3.8 and 3.5 Flash returned 503 "high demand"
# mid-experiment (FAILURES F-08). Which model transcribed each clip is recorded per row.
TEXT_MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash",
               "gemini-3.5-flash", "gemini-3.5-flash-lite"]

TRANSCRIBE_INSTRUCTION = (
    "Transcribe this speech exactly as spoken, in the language and writing system it is spoken in "
    "(use Ge'ez/Ethiopic script for Amharic and Tigrinya, Latin script for Afaan Oromo and Somali). "
    "Do not translate. Then identify the spoken language. "
    'Return JSON: {"language_code": "<ISO 639-1>", "language_name": "...", "transcript": "..."}'
)


def text_call(stage: str, shot_id: str, out: Path, prompt_inputs: dict, make) -> dict:
    """Run a Gemini text call through the cache, falling back across models."""
    last = None
    for model in models_in_cache_order(TEXT_MODELS, out):
        try:
            cached_call(stage=stage, shot_id=shot_id, provider="google", model=model,
                        parameters={"temperature": 0.0}, seed=None, inputs=prompt_inputs,
                        output=out, fn=lambda p, m=model: make(p, m), max_attempts=2)
            return json.loads(out.read_text(encoding="utf-8"))
        except StageError as exc:
            last = exc
    raise StageError(f"{stage}/{shot_id}: all text models failed: {last}")


def translate(source: dict) -> dict:
    lines = {sid: source[sid]["subtitle"] for sid in SHOTS}
    prompt = ("Translate each English line into Tigrinya (ti, Ge'ez script), Afaan Oromo (om, Latin "
              "script, Qubee) and Somali (so, Latin script). Keep them natural, short and spoken. "
              f"Lines: {json.dumps(lines, ensure_ascii=False)}\n"
              'Return JSON: {"<shot_id>": {"ti": "...", "om": "...", "so": "..."}, ...}')
    out = RES / "translations.json"

    def make(p: Path, model: str) -> dict:
        data, usage = gemini.text_json(model, prompt, temperature=0.0)
        missing = [(sid, lg) for sid in SHOTS for lg in ("ti", "om", "so") if not data.get(sid, {}).get(lg)]
        if missing:
            raise ValueError(f"translation missing {missing}")
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"notes": f"tokens={usage}"}

    return text_call("ceiling_translate", None, out, {"prompt": prompt}, make)


def speak(lang: str, sid: str, text: str, sb: dict) -> Path:
    if lang == "am":   # the coffee film's own narration, archived when the story changed
        return AUDIO / f"am_{sid}.wav"
    d = sb["defaults"]
    out = AUDIO / f"{lang}_{sid}.wav"

    def make(p: Path) -> dict:
        wav = gemini.tts_wav(d["tts_model"], text, d["tts_voice"], d["tts_style"])
        p.write_bytes(wav)
        return {"notes": f"lang={lang} audio_seconds={gemini.wav_seconds(wav)}"}

    cached_call(stage="ceiling_tts", shot_id=f"{lang}_{sid}", provider="google", model=d["tts_model"],
                parameters={"voice": d["tts_voice"], "style": d["tts_style"], "lang": lang}, seed=None,
                inputs={"text": text}, output=out, fn=make, max_attempts=3)
    return out


def transcribe(lang: str, sid: str, wav: Path) -> dict:
    out = RES / "transcripts" / f"{lang}_{sid}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    from pipeline.common import file_hash

    def make(p: Path, model: str) -> dict:
        data, usage = gemini.transcribe_json(model, wav.read_bytes(), TRANSCRIBE_INSTRUCTION)
        if "transcript" not in data:
            raise ValueError(f"no transcript in {data}")
        p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"notes": f"heard={data.get('language_code')} tokens={usage}"}

    data = text_call("ceiling_asr", f"{lang}_{sid}", out,
                     {"audio": file_hash(wav), "instruction": TRANSCRIBE_INSTRUCTION}, make)
    meta = json.loads(out.with_name(out.name + ".meta.json").read_text(encoding="utf-8"))
    return {**data, "_asr_model": meta.get("model")}


# ------------------------------------------------------------------ scoring
# The transcriber sometimes answers with ISO 639-2/3 codes (e.g. "amh" for Amharic);
# map them to the 639-1 codes used here so language-ID isn't marked wrong for formatting.
ISO_ALIASES = {"amh": "am", "tir": "ti", "orm": "om", "gaz": "om", "hae": "om", "som": "so"}


def lang_code(code: str | None) -> str | None:
    c = (code or "").strip().lower().split("-")[0]
    return ISO_ALIASES.get(c, c) or None

def normalise(s: str) -> str:
    s = unicodedata.normalize("NFC", s).lower()
    s = re.sub(r"[፡-፨]", " ", s)          # Ethiopic punctuation (፡ ። ፣ ፤ ...)
    s = re.sub(r"[^\w\s]", " ", s)                   # other punctuation
    return re.sub(r"\s+", " ", s).strip()


def cer(ref: str, hyp: str) -> float:
    r, h = normalise(ref), normalise(hyp)
    prev = list(range(len(h) + 1))
    for i, rc in enumerate(r, 1):
        cur = [i]
        for j, hc in enumerate(h, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rc != hc)))
        prev = cur
    return round(prev[-1] / max(len(r), 1), 3)


# The experiment's source text is pinned in its own folder (3 Amharic lines from the
# development storyboard v7), so it doesn't change when the film's storyboard does.
SOURCE_LINES = RES / "source_lines.json"


def cached_transcript(lang: str, sid: str) -> dict | None:
    out = RES / "transcripts" / f"{lang}_{sid}.json"
    meta = out.with_name(out.name + ".meta.json")
    if not (out.exists() and meta.exists()):
        return None
    data = json.loads(out.read_text(encoding="utf-8"))
    return {**data, "_asr_model": json.loads(meta.read_text(encoding="utf-8")).get("model")}


def run(partial: bool = False) -> None:
    """partial=True: no API calls; report only clips whose audio + transcript are already cached."""
    sb = storyboard.load()                      # only for the TTS voice/style defaults
    RES.mkdir(parents=True, exist_ok=True); AUDIO.mkdir(parents=True, exist_ok=True)
    shots = json.loads(SOURCE_LINES.read_text(encoding="utf-8"))["lines"]
    tr = (json.loads((RES / "translations.json").read_text(encoding="utf-8")) if partial else translate(shots))
    rows, missing = [], []
    for lang in LANGS:
        for sid in SHOTS:
            text = shots[sid]["narration"] if lang == "am" else tr[sid][lang]
            if partial:
                wav = AUDIO / f"{lang}_{sid}.wav"
                heard = cached_transcript(lang, sid)
                if heard is None or not wav.exists():
                    missing.append(f"{lang}_{sid}")
                    continue
            else:
                wav = speak(lang, sid, text, sb)
                heard = transcribe(lang, sid, wav)
            secs = gemini.wav_seconds(wav.read_bytes())
            rows.append({
                "lang": lang, "shot": sid, "text": text, "transcript": heard.get("transcript", ""),
                "heard_lang": heard.get("language_code"),
                "lang_id_ok": lang_code(heard.get("language_code")) == lang,
                "cer": cer(text, heard.get("transcript", "")), "audio_sec": secs,
                "asr_model": heard.get("_asr_model"),
                "chars_per_sec": round(len(normalise(text)) / secs, 1) if secs else None,
            })
            print(f"  {lang} {sid}: CER={rows[-1]['cer']:.3f} heard={rows[-1]['heard_lang']} {secs:.1f}s")

    summary = {}
    for lang, name in LANGS.items():
        rs = [r for r in rows if r["lang"] == lang]
        if not rs:
            summary[lang] = {"language": name, "mean_cer": None, "lang_id_correct": "0/0",
                             "mean_chars_per_sec": None, "clips": 0}
            continue
        summary[lang] = {"language": name, "clips": len(rs),
                         "mean_cer": round(sum(r["cer"] for r in rs) / len(rs), 3),
                         "lang_id_correct": f"{sum(r['lang_id_ok'] for r in rs)}/{len(rs)}",
                         "mean_chars_per_sec": round(sum(r["chars_per_sec"] or 0 for r in rs) / len(rs), 1)}
    (RES / "tts_roundtrip.json").write_text(json.dumps({"summary": summary, "rows": rows, "partial": partial,
                                                        "missing": missing}, indent=2, ensure_ascii=False),
                                            encoding="utf-8")
    md = ["# TTS round-trip results (gemini-3.8-flash-tts -> blind Gemini transcription)", ""]
    if missing:
        md += [f"**PARTIAL RESULT:** {len(rows)}/{len(rows) + len(missing)} clips completed. Not completed "
               f"(Gemini free-tier 429 quota / 503 overload, FAILURES F-08): {', '.join(missing)}.", ""]
    md += ["| Language | Clips | Mean CER | Language ID correct | Chars/s |", "|---|---|---|---|---|"]
    md += [f"| {v['language']} ({k}) | {v['clips']} | "
           f"{'n/a' if v['mean_cer'] is None else format(v['mean_cer'], '.3f')} | {v['lang_id_correct']} | "
           f"{v['mean_chars_per_sec'] if v['mean_chars_per_sec'] is not None else 'n/a'} |"
           for k, v in summary.items()]
    md += ["", "| Lang | Shot | Sent to TTS | Transcribed back | Heard as | CER | Transcriber |",
           "|---|---|---|---|---|---|---|"]
    md += [f"| {r['lang']} | {r['shot']} | {r['text']} | {r['transcript']} | {r['heard_lang']} | "
           f"{r['cer']:.3f} | {r['asr_model']} |" for r in rows]
    (RES / "tts_roundtrip.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\nSUMMARY" + (f" (PARTIAL: missing {missing})" if missing else ""))
    for k, v in summary.items():
        cer_txt = "n/a" if v["mean_cer"] is None else f"{v['mean_cer']:.3f}"
        print(f"  {v['language']:<12} clips {v['clips']}  mean CER {cer_txt}  lang-ID {v['lang_id_correct']}  "
              f"{v['mean_chars_per_sec']} chars/s")


if __name__ == "__main__":
    try:
        run(partial="--partial" in sys.argv)
    except StageError as exc:
        print(f"FAILED: {exc}")
        sys.exit(1)
