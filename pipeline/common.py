"""Shared helpers used by every pipeline stage.

Three jobs live here so every stage gets them for free:

1. LOGGING  - every model call appends one JSON line to runs.jsonl
              (timestamp, stage, shot, model, parameters, seed, latency,
              GPU minutes, estimated list cost, status, error).
2. CACHING  - the inputs of a call (model + parameters + seed + prompt +
              upstream files) are hashed into a short fingerprint. If the
              output already exists with the same fingerprint, the call is
              skipped and logged as "cached". Change one shot -> only that
              shot's fingerprint changes -> only that shot regenerates.
3. RETRIES  - a failing call is retried (default 3 attempts) with an
              increasing wait; rate-limit errors wait longer. Every attempt
              is logged, so failures are visible evidence, not silent.

Self-test (no API keys needed):  python -m pipeline.common --selftest
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv

# --------------------------------------------------------------------------
# Paths and configuration
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "outputs"

load_dotenv(ROOT / ".env")

# Names of environment variables whose values must never appear in logs.
SECRET_ENV_NAMES = ("GEMINI_API_KEY", "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")


def runs_log_path() -> Path:
    """Where log lines go. RUNS_LOG can redirect it (used by the self-test)."""
    return Path(os.environ.get("RUNS_LOG", str(ROOT / "runs.jsonl")))


def require_env(name: str) -> str:
    """Read a required setting from .env, with a clear message if missing."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Missing {name}. Copy .env.example to .env and fill it in."
        )
    return value


def redact(text: str) -> str:
    """Replace any secret value that leaked into an error message with ***."""
    for name in SECRET_ENV_NAMES:
        secret = os.environ.get(name, "").strip()
        if secret:
            text = text.replace(secret, "***")
    return text


# --------------------------------------------------------------------------
# Hashing (the "fingerprint" of a call's inputs)
# --------------------------------------------------------------------------
def canonical_json(obj: Any) -> str:
    """Stable JSON text: same data always gives the exact same string."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=str)


def input_hash(obj: Any) -> str:
    """Short SHA-256 fingerprint of any JSON-like data."""
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()[:16]


def file_hash(path: Path | str) -> str:
    """Fingerprint of a file's bytes, so a changed upstream file (e.g. a new
    keyframe) automatically invalidates everything built from it."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
LOG_FIELDS = (
    "timestamp", "run_id", "stage", "shot_id", "provider", "model", "status",
    "attempt", "seed", "parameters", "input_hash", "latency_sec",
    "gpu_minutes", "est_list_cost_usd", "output", "error", "notes",
)


def log_run(**fields: Any) -> dict:
    """Append one record to runs.jsonl and return it."""
    record = {k: None for k in LOG_FIELDS}
    record["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record["run_id"] = uuid.uuid4().hex[:12]
    record.update(fields)
    if isinstance(record.get("error"), str):
        record["error"] = redact(record["error"])[:500]
    path = runs_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return record


# --------------------------------------------------------------------------
# Cached call with retries
# --------------------------------------------------------------------------
class StageError(RuntimeError):
    """A stage call failed after all retry attempts."""


@dataclass
class CallResult:
    output: Path
    status: str          # "ok" (freshly generated) or "cached" (reused)
    input_hash: str
    latency_sec: float
    record: dict


def _meta_path(output: Path) -> Path:
    """Sidecar file that remembers which fingerprint produced an output."""
    return output.with_name(output.name + ".meta.json")


def is_cached(output: Path, fingerprint: str) -> bool:
    meta = _meta_path(output)
    if not (output.exists() and output.stat().st_size > 0 and meta.exists()):
        return False
    try:
        return json.loads(meta.read_text(encoding="utf-8")).get("input_hash") == fingerprint
    except (OSError, json.JSONDecodeError):
        return False


def _is_rate_limit(message: str) -> bool:
    """Quota / overload errors: retrying after 2s just hits the same wall,
    so these get the longer `rate_limit_delay` wait.
    (503 'high demand' added after the 2026-11-25 smoke test - see FAILURES.md F-01.)"""
    m = message.lower()
    return any(s in m for s in ("429", "rate limit", "resource_exhausted", "quota",
                                "503", "unavailable", "high demand", "overloaded"))


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def cached_call(
    *,
    stage: str,
    shot_id: str | None,
    provider: str,
    model: str,
    parameters: dict,
    seed: int | None,
    inputs: dict,
    output: Path,
    fn: Callable[[Path], dict | None],
    max_attempts: int = 3,
    force: bool = False,
    base_delay: float = 2.0,
    rate_limit_delay: float = 30.0,
) -> CallResult:
    """Run `fn(output)` unless an identical earlier run already produced `output`.

    `fn` must write its result to `output`. It may return a dict with extra
    measurements to log: gpu_minutes, est_list_cost_usd, notes.
    """
    fingerprint = input_hash({
        "stage": stage, "provider": provider, "model": model,
        "parameters": parameters, "seed": seed, "inputs": inputs,
    })
    common = dict(stage=stage, shot_id=shot_id, provider=provider, model=model,
                  seed=seed, parameters=parameters, input_hash=fingerprint,
                  output=_rel(output))

    # 1. Cache hit: nothing changed, reuse the existing output.
    if not force and is_cached(output, fingerprint):
        rec = log_run(**common, status="cached", attempt=0, latency_sec=0.0)
        return CallResult(output, "cached", fingerprint, 0.0, rec)

    # 2. Cache miss: generate, with retries.
    output.parent.mkdir(parents=True, exist_ok=True)
    last_error = ""
    for attempt in range(1, max_attempts + 1):
        start = time.perf_counter()
        try:
            extra = fn(output) or {}
            latency = round(time.perf_counter() - start, 3)
            if not output.exists() or output.stat().st_size == 0:
                raise StageError("stage function finished but wrote no output")
            _meta_path(output).write_text(json.dumps({
                "input_hash": fingerprint, "stage": stage, "shot_id": shot_id,
                "provider": provider, "model": model, "seed": seed,
                "parameters": parameters,
                "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }, indent=2, ensure_ascii=False), encoding="utf-8")
            rec = log_run(**common, status="ok", attempt=attempt, latency_sec=latency,
                          gpu_minutes=extra.get("gpu_minutes"),
                          est_list_cost_usd=extra.get("est_list_cost_usd"),
                          notes=extra.get("notes"))
            return CallResult(output, "ok", fingerprint, latency, rec)
        except Exception as exc:  # noqa: BLE001 - we log every failure type
            latency = round(time.perf_counter() - start, 3)
            last_error = redact(f"{type(exc).__name__}: {exc}")
            final = attempt == max_attempts
            log_run(**common, status="error" if final else "retry", attempt=attempt,
                    latency_sec=latency, error=last_error)
            if final:
                break
            wait = base_delay * (2 ** (attempt - 1))
            if _is_rate_limit(last_error):
                wait = max(wait, rate_limit_delay)
            print(f"  [{stage}/{shot_id}] attempt {attempt} failed, retrying in {wait:.0f}s: {last_error[:120]}")
            time.sleep(wait)

    raise StageError(f"{stage}/{shot_id} failed after {max_attempts} attempts: {last_error}")


# --------------------------------------------------------------------------
# Self-test: proves logging, caching and retries work, without any API.
# --------------------------------------------------------------------------
def _selftest() -> int:
    import shutil

    tmp = OUTPUTS / "tmp" / "selftest"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    os.environ["RUNS_LOG"] = str(tmp / "selftest_runs.jsonl")
    out = tmp / "shot01.txt"

    def fake_model(path: Path) -> dict:
        path.write_text("pretend this is an image", encoding="utf-8")
        return {"notes": "fake model"}

    def call(params: dict, fn=fake_model, **kw) -> CallResult:
        return cached_call(stage="selftest", shot_id="s01", provider="local",
                           model="fake-v1", parameters=params, seed=42,
                           inputs={"prompt": "a market in Dessie"}, output=out,
                           fn=fn, base_delay=0.05, **kw)

    checks = []
    r1 = call({"steps": 4})
    checks.append(("first run generates", r1.status == "ok"))
    r2 = call({"steps": 4})
    checks.append(("identical re-run is cached", r2.status == "cached"))
    r3 = call({"steps": 8})
    checks.append(("changed parameter regenerates", r3.status == "ok"))

    flaky = {"n": 0}
    def flaky_model(path: Path) -> dict:
        flaky["n"] += 1
        if flaky["n"] == 1:
            raise ConnectionError("simulated network blip")
        return fake_model(path)
    r4 = call({"steps": 16}, fn=flaky_model)
    checks.append(("retry recovers from one failure", r4.status == "ok" and flaky["n"] == 2))

    def broken_model(path: Path) -> dict:
        raise RuntimeError("simulated permanent failure")
    try:
        call({"steps": 32}, fn=broken_model)
        checks.append(("permanent failure raises after 3 attempts", False))
    except StageError:
        checks.append(("permanent failure raises after 3 attempts", True))

    lines = [json.loads(l) for l in Path(os.environ["RUNS_LOG"]).read_text(encoding="utf-8").splitlines()]
    print("Log lines written:")
    for rec in lines:
        print(f"  status={rec['status']:<7} attempt={rec['attempt']} "
              f"params={canonical_json(rec['parameters']):<14} hash={rec['input_hash']} "
              f"latency={rec['latency_sec']}s" + (f"  error={rec['error']}" if rec['error'] else ""))
    print("\nChecks:")
    ok = True
    for name, passed in checks:
        ok &= passed
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    shutil.rmtree(tmp, ignore_errors=True)
    print("\nALL PASSED" if ok else "\nSOME CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print(__doc__)
