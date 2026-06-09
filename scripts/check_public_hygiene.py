#!/usr/bin/env python3
"""Public-hygiene leak guard.

Blocks generic PII / machine-specific leakage from entering tracked files and
commit messages of this PUBLIC repo. By default it is DIFF-SCOPED: it inspects
only the lines ADDED in the staged change (pre-commit) or in a PR range (CI). It
does NOT trip on pre-existing debt -- it only prevents NEW leaks.

Stdlib-only, ASCII-only, Windows + Linux safe.

The COMMITTED rules here are deliberately GENERIC (machine paths, personal-provider
email, AI-attribution trailers) so this public file names no one and reveals no
project-internal vocabulary. Project-specific patterns (personal name, internal
process terms, clone ids) are NOT hardcoded here; they are loaded at runtime from
an OPTIONAL, git-ignored local file so they are enforced locally without being
published. See LOCAL_PATTERNS_FILE below.

Modes:
  (default)            scan lines added in `git diff --cached` (pre-commit hook)
  --ci-range A...B     scan lines added in a PR range (CI)
  --all                scan every tracked text file (post-cleanup full sweep)
  --commit-msg FILE    scan a commit message file ('-' = stdin) for AI attribution

Exit 0 = clean, 1 = leak found (prints file:line + reason), 2 = usage error.

Escape hatch: a line containing the marker  hygiene-allow  is skipped (use only
for a verified false positive, e.g. a doc that legitimately discusses the rule).
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ALLOW_MARK = "hygiene-allow"

# Files where the personal name is legitimate: the copyright/author files (LICENSE,
# NOTICE, pyproject metadata) and the identity map (.mailmap), whose explicit purpose
# is to declare the canonical author name for the contributor view.
NAME_ALLOW_FILES = {"LICENSE", "LICENSE.md", "LICENSE.txt", ".mailmap", "NOTICE", "pyproject.toml"}

# This guard would otherwise be scanned like any other file; skip it.
SELF_FILES = {"scripts/check_public_hygiene.py"}

# Optional git-ignored file with project-specific patterns (name / process terms /
# clone ids). Kept out of the public tree on purpose. One rule per line:
#     <regex><TAB><reason>[<TAB>name]
# A 3rd column "name" marks a rule that is skipped inside NAME_ALLOW_FILES.
# Lines that are blank or start with '#' are ignored. Patterns are case-insensitive.
LOCAL_PATTERNS_FILE = os.environ.get(
    "HYGIENE_LOCAL_PATTERNS",
    str(Path(__file__).resolve().parent.parent / ".hygiene-local-patterns.txt"),
)

# Binary / non-text extensions we never scan.
SKIP_EXT = {
    ".parquet", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip",
    ".gz", ".xlsx", ".xls", ".pyc", ".so", ".dll", ".woff", ".woff2", ".ttf",
}

# (compiled pattern, human reason, name_rule?)
# name_rule=True patterns are skipped inside NAME_ALLOW_FILES.
# Only GENERIC detectors live here; project-specific patterns load from
# LOCAL_PATTERNS_FILE (see _load_local_rules).
CONTENT_RULES = [
    (re.compile(r"<local-path>", re.IGNORECASE), "machine-specific home path (<local-path>)", False),
    (re.compile(r"/home/[A-Za-z0-9._-]+/"), "machine-specific home path (/home/<user>/)", False),
    # Personal-provider email (maintainer should use no-reply/service addresses).
    # Generic on purpose: avoids embedding a real address in this public file.
    (re.compile(r"[A-Za-z0-9._%+-]+@(?:gmail|hotmail|yahoo|outlook|icloud|protonmail|proton)\.(?:com|net|me)",
     re.IGNORECASE), "personal email address (use a no-reply/service address)", False),
]

COMMIT_MSG_RULES = [
    (re.compile(r"Co-Authored-By:\s*Claude", re.IGNORECASE), "AI attribution trailer (Co-Authored-By: Claude)"),
    (re.compile(r"Generated with .*Claude Code", re.IGNORECASE), "AI attribution (Generated with Claude Code)"),
    (re.compile(r"noreply@anthropic\.com", re.IGNORECASE), "AI attribution email"),
]


def _load_local_rules() -> None:
    """Append project-specific rules from the optional git-ignored local file.

    Absent file (e.g. a fresh CI checkout) -> generic rules only; never an error.
    """
    path = Path(LOCAL_PATTERNS_FILE)
    if not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        pat = parts[0]
        reason = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "internal/project-specific pattern"
        is_name = len(parts) > 2 and parts[2].strip().lower() == "name"
        try:
            CONTENT_RULES.append((re.compile(pat, re.IGNORECASE), reason, is_name))
        except re.error:
            sys.stderr.write(f"warning: bad regex in {path.name}: {pat}\n")


def _git(args: list[str]) -> str:
    out = subprocess.run(["git", *args], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    if out.returncode != 0:
        sys.stderr.write(out.stderr)
        sys.exit(2)
    return out.stdout


def _check_line(path: str, lineno: int, text: str, hits: list[str]) -> None:
    if ALLOW_MARK in text:
        return
    base = Path(path).name
    for pat, reason, is_name in CONTENT_RULES:
        if is_name and base in NAME_ALLOW_FILES:
            continue
        if pat.search(text):
            hits.append(f"{path}:{lineno}: {reason}\n    {text.strip()[:160]}")


def _iter_added(diff_text: str):
    """Yield (path, lineno_in_new_file, added_line) from a unified=0 diff."""
    path = None
    newline = 0
    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            p = raw[4:].strip()
            path = None if p == "/dev/null" else p[2:] if p[:2] in ("a/", "b/") else p
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            newline = int(m.group(1)) if m else 0
        elif raw.startswith("+") and not raw.startswith("+++"):
            if path is not None:
                yield path, newline, raw[1:]
            newline += 1
        elif not raw.startswith("-") and not raw.startswith("\\"):
            newline += 1
    return


def scan_diff(diff_text: str) -> list[str]:
    hits: list[str] = []
    for path, lineno, text in _iter_added(diff_text):
        norm = path.replace("\\", "/")
        if norm in SELF_FILES or Path(path).suffix.lower() in SKIP_EXT:
            continue
        _check_line(path, lineno, text, hits)
    return hits


def scan_all() -> list[str]:
    hits: list[str] = []
    for path in _git(["ls-files"]).splitlines():
        norm = path.replace("\\", "/")
        if not path or norm in SELF_FILES or Path(path).suffix.lower() in SKIP_EXT:
            continue
        fp = Path(path)
        if not fp.is_file():
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), start=1):
            _check_line(path, i, line, hits)
    return hits


def scan_commit_msg(source: str) -> list[str]:
    text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8", errors="replace")
    hits: list[str] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARK in line:
            continue
        for pat, reason in COMMIT_MSG_RULES:
            if pat.search(line):
                hits.append(f"commit-msg:{i}: {reason}\n    {line.strip()[:160]}")
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description="Public-hygiene leak guard")
    ap.add_argument("--all", action="store_true", help="scan every tracked text file (post-cleanup)")
    ap.add_argument("--ci-range", metavar="A...B", help="scan lines added in a git range (CI)")
    ap.add_argument("--commit-msg", metavar="FILE", help="scan a commit message file ('-' = stdin)")
    args = ap.parse_args()

    if args.commit_msg:
        hits = scan_commit_msg(args.commit_msg)
    else:
        _load_local_rules()
        if args.all:
            hits = scan_all()
        elif args.ci_range:
            hits = scan_diff(_git(["diff", "--unified=0", "--no-color", args.ci_range]))
        else:
            hits = scan_diff(_git(["diff", "--cached", "--unified=0", "--no-color"]))

    if hits:
        sys.stderr.write("PUBLIC-HYGIENE GUARD: blocked %d leak(s)\n\n" % len(hits))
        for h in hits:
            sys.stderr.write(h + "\n")
        sys.stderr.write(
            "\nFix the line(s) above. If a hit is a verified false positive, add the\n"
            "marker 'hygiene-allow' to that line.\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
