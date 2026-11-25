"""Pre-push safety check: make sure no secret value is about to be committed.

Run before every push:  python -m pipeline.check_secrets

It reads the real values from .env and searches every file Git would upload
(tracked + new, respecting .gitignore) for them, plus common key patterns.
It never prints a secret, only the file name and which key matched.
"""

from __future__ import annotations

import re
import subprocess
import sys

from pipeline.common import ROOT, SECRET_ENV_NAMES
import os

PATTERNS = {
    "Google API key pattern": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "Private key block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}


def files_git_would_upload() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [line for line in out.splitlines() if line.strip()]


def main() -> int:
    secrets = {name: os.environ.get(name, "").strip() for name in SECRET_ENV_NAMES}
    secrets = {k: v for k, v in secrets.items() if len(v) >= 8}
    files = files_git_would_upload()

    if ".env" in files:
        print("DANGER: .env would be uploaded! Check .gitignore.")
        return 1

    problems = []
    for rel in files:
        try:
            text = (ROOT / rel).read_bytes().decode("utf-8", errors="ignore")
        except OSError:
            continue
        for name, value in secrets.items():
            if value in text:
                problems.append(f"{rel}: contains the value of {name}")
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                problems.append(f"{rel}: matches {label}")

    print(f"Scanned {len(files)} files for {len(secrets)} secret values + {len(PATTERNS)} patterns.")
    if problems:
        print("SECRETS FOUND - do NOT push:")
        for p in problems:
            print("  " + p)
        return 1
    print("CLEAN: no secrets found. Safe to push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
