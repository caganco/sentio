---
id: DEC-012
title: Git History Scrub — Remove Personal Portfolio Data from config.yaml History
date: 2026-05-19
area: Security / Release
status: decided
priority: CRITICAL
affects:
  - config.yaml (all historical blobs in commits a16ffa7, b4ba95d, b190c1a, ab1b519)
  - All downstream commit SHAs (rewrite side-effect)
rationale: "config.yaml committed real lot sizes, average costs, and fund values across 4 commits. Working tree was cleaned in 2e2392e (G-2). History must be scrubbed before public release via git-filter-repo blob callback. Irreversible — timing: immediately before `git push --set-upstream` to public remote."
implementation_status: 0%
test_coverage: manual verification step (git log | grep avg_cost must return empty)
---

# DEC-012: Git History Scrub — Remove Personal Portfolio Data

**Decision Date:** 19 May 2026  
**Decided By:** the maintainer  
**Status:** ✅ DECIDED — pending execution

---

## CONTEXT

`config.yaml` contained real portfolio positions (lot sizes, average costs) and
fund values across 4 commits. Commit `2e2392e` (`fix(G-2)`) moved this data to
a git-ignored `positions.yaml`, cleaning the working tree. However, the
financial data remains accessible in git history:

```
git show ab1b519:config.yaml   # → AKSEN: { lots: 591, avg_cost: 87.59 } + funds
git show b190c1a:config.yaml   # → same dict format, same values
git show b4ba95d:config.yaml   # → AKSEN.IS: { quantity: 591, avg_cost: 87.59 }
git show a16ffa7:config.yaml   # → list format, same positions
```

**Exposed data per affected commit:**

| Field | Values in history |
|-------|------------------|
| Positions | AKSEN 591 lots @87.59, TTKOM 329 @60.65, TAVHL 68 @286.50, KCHOL 81 @188.83, ENERY 1543 @9.07 |
| Funds | DVT ₺41,688 (+36.52%), DFI ₺47,672 (+5.93%), PHE ₺20,673 (+3.38%) |

**Data format varies by commit** — the blob callback must handle both:
- `a16ffa7`, `b4ba95d`: YAML list format (`- ticker: AKSEN.IS\n  quantity: 591`)
- `b190c1a`, `ab1b519`: YAML dict format (`AKSEN: { lots: 591, avg_cost: 87.59 }`)

**Current state:** Repo is private. Risk is zero today. Risk becomes critical the
moment the repo is made public — any person can run `git log --all` and
`git show <sha>:config.yaml` to recover the financial data.

---

## DECISION

Execute `git-filter-repo` with a Python blob callback immediately before
making the repository public. The callback surgically removes only the
`positions:` and `funds:` blocks from all historical `config.yaml` blobs,
replacing them with empty mappings and a reference comment. All other
`config.yaml` content (portfolio universe, scanner parameters, macro weights,
agent config, scheduler) is preserved intact.

This operation rewrites all commit SHAs from `a16ffa7` forward. Existing
directive references (D-xxx commit hashes in OS_STATE.md and doc files) become
stale pointers — acceptable because the referenced content (code, not positions
data) is unchanged.

---

## IMPLEMENTATION STEPS

**Pre-conditions (verify before starting):**
- [ ] Repo is still private on GitHub
- [ ] No open PRs or branches referencing old SHAs
- [ ] Local working tree is clean (`git status` = clean)
- [ ] `positions.yaml` is confirmed git-ignored and data is safe there

---

### Step 1 — Install git-filter-repo

```bash
pip install git-filter-repo
# Verify:
git filter-repo --version
```

Minimum required: `git-filter-repo 2.38+`. Do not use `git-filter-branch` —
it is deprecated, slower, and produces unreliable results on complex rewrites.

---

### Step 2 — Backup (mandatory — this operation is irreversible)

```bash
# Create a full backup of the repo
cd ..
cp -r bist-trading-system bist-trading-system.backup-pre-scrub
# Verify backup exists
ls -la bist-trading-system.backup-pre-scrub/
```

---

### Step 3 — Create the blob callback script

Create `scrub_positions.py` outside the repo directory (e.g., `~/scrub_positions.py`):

```python
import re

def callback(blob, metadata):
    """Remove positions: and funds: blocks from all config.yaml blobs."""
    # Only process config.yaml
    if not any(
        p.endswith(b"config.yaml")
        for p in metadata.get("filename_callback", [b"config.yaml"])
    ):
        return

    try:
        content = blob.data.decode("utf-8")
    except UnicodeDecodeError:
        return  # binary blob, skip

    # Format A (dict): AKSEN: { lots: 591, avg_cost: 87.59 }
    # Matches indented positions: block up to next top-level or same-level key
    content = re.sub(
        r"([ \t]*positions:)[ \t]*\{[^}]*\}|"
        r"([ \t]*positions:)\s*\n(?:[ \t]+\S[^\n]*\n)*",
        r"\1{} # moved to positions.yaml (git-scrub DEC-012)\n",
        content,
    )

    # Format B (list): - ticker: AKSEN.IS\n  quantity: 591\n  avg_cost: 87.59
    content = re.sub(
        r"([ \t]*positions:)\s*\n(?:[ \t]*-[ \t]+\S[^\n]*\n(?:[ \t]+\S[^\n]*\n)*)*",
        r"\1 []  # moved to positions.yaml (git-scrub DEC-012)\n",
        content,
    )

    # Format A (dict): funds: { DVT: {...}, DFI: {...} }
    # Format B (block): funds:\n  DVT: { value: 41688, ... }
    content = re.sub(
        r"([ \t]*funds:)[ \t]*\{[^}]*(?:\{[^}]*\}[^}]*)*\}|"
        r"([ \t]*funds:)\s*\n(?:[ \t]+\S[^\n]*\n)*",
        r"\1{}  # moved to positions.yaml (git-scrub DEC-012)\n",
        content,
    )

    blob.data = content.encode("utf-8")
```

---

### Step 4 — Run the scrub

```bash
cd bist-trading-system

git filter-repo \
  --path config.yaml \
  --blob-callback "$(cat ~/scrub_positions.py)"
```

**If `--blob-callback` with a file is not supported by your git-filter-repo version,
use this alternative (inline, single-command):**

```bash
git filter-repo --path config.yaml --blob-callback '
import re

try:
    content = blob.data.decode("utf-8")
except UnicodeDecodeError:
    pass
else:
    # Remove dict-format positions block
    content = re.sub(
        r"([ \t]*positions:)\s*\n(?:[ \t]+\S[^\n]*\n)*",
        "  positions: {}  # moved to positions.yaml (DEC-012)\n",
        content,
    )
    # Remove list-format positions block
    content = re.sub(
        r"([ \t]*positions:)\s*\n(?:[ \t]*-[ \t]+\S[^\n]*\n(?:[ \t]+\S[^\n]*\n)*)*",
        "  positions: []  # moved to positions.yaml (DEC-012)\n",
        content,
    )
    # Remove funds block (dict or block format)
    content = re.sub(
        r"([ \t]*funds:)\s*\n(?:[ \t]+\S[^\n]*\n)*",
        "  funds: {}  # moved to positions.yaml (DEC-012)\n",
        content,
    )
    blob.data = content.encode("utf-8")
'
```

---

### Step 5 — Verify the scrub

```bash
# Must return empty — if any line appears, scrub failed
git log --all --format="%H" -- config.yaml \
  | xargs -I{} git show {}:config.yaml 2>/dev/null \
  | grep -iE "avg_cost|lots:|quantity:|return_pct|value: [0-9]"

# Expected output: (empty)

# Spot-check a specific previously-dirty commit (SHA will have changed):
git log --oneline | grep "Signal engine refactor"
# Note the new SHA, then:
git show <new-sha>:config.yaml | grep -A5 "positions:"
# Expected: positions: {}  # moved to positions.yaml (DEC-012)
```

---

### Step 6 — Force push

```bash
# Re-add the remote if git-filter-repo removed it (it does by default)
git remote add origin https://github.com/<user>/bist-trading-system.git

git push --force origin master
```

---

### Step 7 — GitHub cache purge

GitHub caches pack objects. After force push:

1. Go to `Settings → Danger Zone → Delete all caches`  
   *Or:* Contact GitHub Support if cached objects remain accessible via the API.

2. Wait 24 hours for CDN propagation before confirming public release.

---

### Step 8 — Update OS_STATE.md commit hash references

After the rewrite, any commit hash referenced in documentation is stale.
Run:

```bash
git log --oneline | head -10
```

Update `OS_STATE.md` (root) and any directive files that reference the old
`9c9bbcb` (D-052) or other hashes that were rewritten. The code is identical;
only SHAs changed.

---

## CONSTRAINTS

- **Irreversible.** The backup from Step 2 is the only recovery path.
- **`positions.yaml`** (created by G-2, git-ignored) is unaffected — it exists
  only on disk and is never touched by this operation.
- **Force push invalidates any cached clone.** If other machines have cloned
  the repo, they must delete and re-clone after the force push.
- **Do not run this on a repo with open PRs** — all PR base SHAs will be
  invalidated.

---

## CONSEQUENCES

**If executed:**
- All 4 dirty commits are rewritten; financial data is unrecoverable from git
  history without the backup
- Every commit SHA from `a16ffa7` forward changes
- Existing D-xxx directive references to commit hashes become stale pointers
  (cosmetic issue only — code is unchanged)
- Repo is safe to make public

**If not executed before public release:**
- Any visitor can recover exact lot sizes, average costs, and fund performance
  via `git log --all` + `git show`
- Even after making the repo private again, GitHub may retain cached objects

---

## ALTERNATIVES REJECTED

1. **BFG Repo Cleaner.** Simpler CLI, but cannot perform partial-file
   surgery (positions block only). BFG operates on whole-file replacement or
   text substitution — it would require replacing the entire `config.yaml`
   at each dirty commit, losing historical context for scanner/macro parameters.
   `git-filter-repo` blob callback is more precise.

2. **Delete config.yaml from history entirely** (`--invert-paths`).
   Rejected: loses legitimate scanner, macro, and agent configuration history,
   which has forensic value for understanding parameter evolution.

3. **Leave history dirty, keep repo private forever.**
   Accepted as a temporary state only. Not viable for the BIST BT application
   use case, which requires a public GitHub link.

---

## RELATED DECISIONS

- **D-061 G-2** — Working tree cleanup (positions moved to `positions.yaml`,
  `2e2392e`)
- **DEC-010** — Strategist advisory boundary (separate privacy concern)

---

**Status:** ✅ DECIDED — execution blocked until immediately before public release  
**Approved By:** the maintainer  
**Execution Owner:** the maintainer (manual — irreversible operation, human must confirm each step)  
**Implementation Owner:** the maintainer (not delegatable to Builder — git history rewrite requires human sign-off)
