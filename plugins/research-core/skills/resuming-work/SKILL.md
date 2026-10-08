---
name: resuming-work
description: Pick a project back up — what changed since a date, what is running (screens, processes, queue files), whether a review checkpoint is due, the newest state in memory, open items — and find the past session that worked on something. Also memory hygiene: oversized state files, rules copied across projects, duplicate memory folders (proposals only). Use when starting a session, when the user asks "where were we", "what's running", "catch me up on this project", "which session had X", or when memory looks bloated or contradictory. Not for reviewing the changed code itself → use running-review-checkpoints.
---

# Resuming work

A resumed session is only as good as its first five minutes: trust the disk, not the memory.
Memory says what was true when it was written; git, the process table and the logs say what is
true now. When they disagree, report the disagreement and fix the memory (with the user's OK).

## Step 1 — the brief (read-only)

```bash
python <this skill>/scripts/resume_brief.py --repo <project> [--days 3 | --since YYYY-MM-DD]
```
It prints: git (branch, ahead/behind, uncommitted files, commits since the date) · running work
(screens, python processes inside the project, queue files and their last log line) · the review
checkpoint (due / not due) · the newest dated entries of the memory state file · docs changed
since the date · open items (TODO, FIXME, NEXT:, unchecked boxes) · memory hygiene flags.

## Step 2 — tell the user, in ten lines or fewer

1. **Where things stand** — the last result or decision, with its date.
2. **What is running** — and whether it is still alive (a process, a growing log), not just listed in memory.
3. **What is due** — a review checkpoint, a finished run waiting for verdicts and figures.
4. **Open items** — the two or three that matter, not the whole list.
5. **Proposed next step**, as a question. If the user's answer is vague, use clarifying-requests.

Say explicitly when memory and disk disagree ("memory says the sweep is running; no process or
screen exists, last log line 2 days ago").

## "Which session had X?"

```bash
python <this skill>/scripts/resume_brief.py --repo <project> --find "figure 5 flows" [--all_projects]
```
Lists matching past sessions (typed user messages only, newest and best-matching first) with the
command to reopen one from the project folder: `claude --resume <session id>`.

## Memory hygiene (proposals only)

```bash
python <this skill>/scripts/resume_brief.py --repo <project> --memory
```
- **Oversized files** (over `resume.memory_cap_kb`): propose which dated sections move into the
  project's docs (the history belongs there; memory keeps the current state and pointers).
- **A rule copied into several projects**: one canonical copy belongs in the user's profile;
  copies that **differ** mean one is stale — show both and ask which holds.
- **Duplicate memory folders** for one project (a path spelled with `_` and with `-`): propose
  merging into the one Claude Code currently writes to. A folder that is a symlink to another is
  the same folder, not a duplicate.
- **Dangling `[[links]]`** and notes Obsidian cannot resolve: `scripts/memory_links.py` reports
  them; `--add-aliases` writes the `aliases:` line Obsidian needs (the memory vault's pre-commit
  hook runs it).

Apply nothing without the user's approval; then edit, and log it (log-and-ship).

## Never

- Kill, restart or relaunch anything while resuming — report it and ask.
- Present a memory fact as current without checking it against the disk.
- Rewrite, archive or merge memory files without approval.

Checklist, reported as one line: brief run · memory vs disk checked · running work verified · next step proposed.
