"""Cost & latency report computed from runs.jsonl (nothing typed by hand).

Run:  python -m pipeline.costs        prints the table and rewrites the generated
                                       section of COSTS.md between the markers.

What was actually paid: $0 (free tiers only). The "list-price equivalent" is what the
same calls would cost on the paid tier, using prices published on the dates below.
Prices (checked 2026-11-26):
  Gemini  https://aistudio.google.com/docs/pricing  (paid tier, through 2026-12-31)
    gemini-3.8-flash        $0.75 / 1M input tokens, $3.75 / 1M output tokens
    gemini-3.8-flash-tts    $9.00 / 1M output audio tokens, 25 audio tokens per second
                            (+ $0.50 / 1M input text tokens; input counts not logged -> excluded, negligible)
    gemini-3.5-flash        not listed on the pricing page -> no estimate
  Cloudflare  https://developers.cloudflare.com/workers-ai/platform/pricing/ (dateModified 2026-11-18)
    flux-1-schnell          $0.0000528 per 512x512 tile + $0.0001056 per step
    flux-2-klein-4b         $0.000287 per output 512x512 tile
    free allocation         10,000 neurons/day (schnell 1024x1024, 8 steps = 96 neurons)
"""

from __future__ import annotations

import ast
import json
import re
from collections import defaultdict

from pipeline.common import ROOT, runs_log_path

COSTS_MD = ROOT / "COSTS.md"
BEGIN, END = "<!-- BEGIN GENERATED: python -m pipeline.costs -->", "<!-- END GENERATED -->"

GEMINI_TEXT = {"gemini-3.8-flash": (0.75, 3.75)}           # $ per 1M (input, output)
TTS_OUT_PER_M, TTS_TOKENS_PER_SEC = 9.00, 25
SCHNELL_TILE, SCHNELL_STEP, KLEIN_OUT_TILE = 0.0000528, 0.0001056, 0.000287


def tokens(notes: str) -> dict:
    m = re.search(r"tokens=(\{.*?\}|\d+)", notes or "")
    if not m:
        return {}
    raw = m.group(1)
    return {"total_tokens": int(raw)} if raw.isdigit() else ast.literal_eval(raw)


def list_price(r: dict) -> tuple[float | None, str]:
    """(usd, basis) for one successful call, or (None, reason)."""
    model, notes, params = r.get("model") or "", r.get("notes") or "", r.get("parameters") or {}
    if r["provider"] == "local":
        return 0.0, "local"
    if model in GEMINI_TEXT:
        t = tokens(notes)
        pin, pout = GEMINI_TEXT[model]
        if "prompt_tokens" in t and t.get("output_tokens") is not None:
            return (t["prompt_tokens"] * pin + t["output_tokens"] * pout) / 1e6, "exact tokens"
        if "total_tokens" in t and t["total_tokens"]:
            return t["total_tokens"] * pout / 1e6, "upper bound (total tokens at output price)"
        return None, "tokens not logged"
    if model.endswith("-tts"):
        m = re.search(r"audio_seconds=([\d.]+)", notes)
        if m:
            return float(m.group(1)) * TTS_TOKENS_PER_SEC * TTS_OUT_PER_M / 1e6, "audio seconds x 25 tok/s"
        return None, "audio length not logged"
    if model.endswith("flux-1-schnell"):
        steps = params.get("steps", 4)
        return 4 * SCHNELL_TILE + steps * SCHNELL_STEP, f"4 tiles + {steps} steps"
    if model.endswith("flux-2-klein-4b"):
        w, h = params.get("width", 1024), params.get("height", 1024)
        tiles = -(-w // 512) * -(-h // 512)
        return tiles * KLEIN_OUT_TILE, f"{tiles} output tiles"
    return None, "price not listed"


def report() -> str:
    recs = [json.loads(l) for l in runs_log_path().read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = defaultdict(lambda: {"ok": 0, "cached": 0, "retry": 0, "error": 0, "latency": 0.0,
                                "gpu": 0.0, "usd": 0.0, "unpriced": 0, "models": set(), "basis": set()})
    for r in recs:
        if r["status"] not in ("ok", "cached", "retry", "error"):
            continue
        row = rows[r["stage"]]
        row[r["status"]] += 1
        row["models"].add(r.get("model") or "?")
        if r["status"] in ("ok", "retry", "error"):
            row["latency"] += float(r.get("latency_sec") or 0)
            row["gpu"] += float(r.get("gpu_minutes") or 0)
        if r["status"] == "ok":
            usd, basis = list_price(r)
            row["basis"].add(basis)
            if usd is None:
                row["unpriced"] += 1
            else:
                row["usd"] += usd

    lines = [f"Generated from `runs.jsonl` ({len(recs)} log lines). Latency = wall-clock seconds spent "
             "in calls (successful + failed attempts). Cached re-uses cost nothing and take ~0 s.", "",
             "| Stage | Model(s) | OK | Cached | Retry | Error | Latency (s) | GPU min | List-price equiv. (USD) | Basis |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    tot = {"ok": 0, "cached": 0, "retry": 0, "error": 0, "latency": 0.0, "gpu": 0.0, "usd": 0.0, "unpriced": 0}
    for stage, r in rows.items():
        usd = f"{r['usd']:.4f}" + (f" (+{r['unpriced']} unpriced)" if r["unpriced"] else "")
        lines.append(f"| {stage} | {', '.join(sorted(r['models']))} | {r['ok']} | {r['cached']} | {r['retry']} | "
                     f"{r['error']} | {r['latency']:.1f} | {r['gpu']:.1f} | {usd} | {'; '.join(sorted(r['basis']))} |")
        for k in tot:
            tot[k] += r[k]
    lines.append(f"| **Total** | | **{tot['ok']}** | **{tot['cached']}** | **{tot['retry']}** | **{tot['error']}** | "
                 f"**{tot['latency']:.1f}** | **{tot['gpu']:.1f}** | **{tot['usd']:.4f}**"
                 + (f" (+{tot['unpriced']} unpriced)" if tot["unpriced"] else "") + " | |")
    lines += ["", "**Actually paid: $0.00** (free tiers only)."]
    return "\n".join(lines)


def main() -> None:
    table = report()
    print(table)
    text = COSTS_MD.read_text(encoding="utf-8")
    block = f"{BEGIN}\n{table}\n{END}"
    if BEGIN in text:
        text = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    else:
        text = text.replace("## Per-stage measurements", "## Per-stage measurements\n" + block, 1)
    COSTS_MD.write_text(text, encoding="utf-8")
    print(f"\nupdated {COSTS_MD.name}")


if __name__ == "__main__":
    main()
