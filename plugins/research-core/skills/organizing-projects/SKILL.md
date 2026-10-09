---
name: organizing-projects
description: Keep a research repository organized — a clear layout, every source under version control (including hand-made vector art and figure builders), outputs out of git, no _v2/_old/_final copies, scratch scripts promoted or deleted, docs indexed, a lean CLAUDE.md and a README. project_audit.py reports what is off and proposes a tidy plan; nothing moves until the user approves. Its --staged mode checks each commit (the Bash guard refuses clear mess; log-and-ship proposes the rest, README lines included). Use when the user asks to "organize", "tidy", "clean up" or "structure" a project or repo, when files seem lost or duplicated, when a README is missing or stale, or before sharing a repo. Not for code style → use reviewing-code-readability.
---

# Organizing projects

A research repo decays in predictable ways: a source hidden by an ignore rule (`*.svg` swallowing
a hand-drawn scheme), page builders left in a temporary folder that disappears, `fig_x_v1259.py`
next to `fig_x.py` with nobody sure which is current, hundreds of scratch scripts of which a few
quietly became the analysis, a CLAUDE.md that grew into a history log, docs nobody can find.
The fix is a short audit, a plan the user approves, and small reversible moves — and then a check
at every commit, so the mess does not come back.

## Every commit — the tidy check (this commit only)

```bash
python <this skill>/scripts/project_audit.py --staged [--all]    # --all = as `git commit -a`
```
- **✗ blocks** only clear mess: a `never_stage` path, a force-added ignored file, editor/OS junk
  (`file~`, `.#file`, `.pyc`), a file over `large_file_mb`, a `_v2` / `_old` copy of code. The Bash
  guard refuses such a commit in any project with `.claude/project.yaml` (it replays `git add …` in
  the same command on a copy of the index). `TIDY_OK=1 git commit …` only when the user named the file.
- **? proposes**: README and doc-index lines for the files the commit adds, renames or removes (new
  top-level folder or script, a folder README that lists its files, a doc missing from the index, an
  index still naming a removed file); a scratch file staged; an untracked file staged code imports;
  a new file in an output folder; a dated or versioned doc name; no README at all.
- log-and-ship writes the README/index lines into the same commit (they document it) and lists the
  other proposals in its report; they happen on the user's yes. Off: `organize: {commit_check: false}`.

## Step 1 — audit (read-only)

```bash
python <this skill>/scripts/project_audit.py --repo <project>
```
It reports untracked source files, ignored source files (with the rule that hides them),
version-suffixed copies (paired with their base), exploratory "preview" scripts, large tracked
files, scratch folders (size, age), docs missing from the index, CLAUDE.md size and dated lines,
a missing README — then a numbered tidy plan. Settings: `organize:` in `.claude/project.yaml`.

## Step 2 — the plan, for approval

Present the plan as groups, each with its concrete commands and what it touches; ask which
groups to run (AskUserQuestion, multiSelect). Typical groups:

| Group | Action |
|---|---|
| version sources | `git add` the sources worth keeping; delete the dead ones (named by the user) |
| un-hide sources | narrow an over-broad ignore rule to the output folders, or add `!path` exceptions |
| resolve copies | diff each `_v2`/`_old` copy against its base; keep one file; git keeps the history |
| scratch | promote scripts still in use (`git mv` into `scripts/`, add a docstring); delete the rest |
| docs | add missing docs to the index; move dated history out of CLAUDE.md into docs |
| README | write one, or fix a stale one: what the project is, how to run it (entry points), the top-level folders, where results and docs live; one line per item, links not copies (`references/layout.md`) |

The target layout, what git tracks vs ignores, and naming rules: `references/layout.md`.

## Step 3 — execute what was approved

- Moves with `git mv`; then grep for every reference to the old path (imports, docs, CLAUDE.md,
  project.yaml) and update it; run each moved script's `--help` to prove it still imports.
- Deletions only of files the user approved; never `rm -rf` a folder.
- Never rewrite git history (large files already committed stay; only new ones are kept out).
- One commit per group (log-and-ship), so each is easy to revert.
- Re-run the audit and show the before/after counts.
- A README written or fixed here: every command in it is run (or `--help`ed) before the commit, and
  every path in it exists — a README that lies is worse than none.

## Never

- Move, rename or delete anything before the user approves that group.
- Reorganize code other projects import without updating them.
- Mass-reformat or "clean" code while organizing — that is a different review.

Checklist, reported as one line: audit run · plan approved by group · references updated · scripts still run · audit re-run · README paths and commands checked.
