---
name: log-and-ship
description: Persist a chunk of work into the project's second brain and version control — update the right docs/*.md and the cross-session memory, then commit (and push only if asked). Use when the user says "log", "log and commit", "log doc commit", "update the docs", "commit this", "push it", or otherwise wants the just-finished experiment/code change recorded and shipped. Works in every project; the per-project doc map, memory folder and never-stage list come from `.claude/project.yaml`. Not for catching up at session start → resuming-work.
---

# Log and ship

The project treats `docs/*.md` and the auto-memory as a **second brain** — lazy-loaded Markdown files
that carry context across sessions. A chunk of work isn't "done" until it's written there AND
committed. **Do the doc/memory update even when the user only says "commit"** — an undocumented
commit is a half-logged change.

## Step 0 — load the project's facts

```bash
cat .claude/project.yaml 2>/dev/null || echo "NO project.yaml"
```

It gives `docs_map` (which doc for which work), `memory_dir`, `memory_state_file`, and
`never_stage`. If it is missing, fall back to the doc table in `CLAUDE.md`, and offer to create
`.claude/project.yaml` from `~/claude-skills/templates/project.yaml`.

## Golden rules (do not skip)

- **Commit only when asked. Push ONLY when explicitly asked.** "log and commit" ≠ push.
- **Commit trailer = the one in this session's attribution system-reminder.** Never copy a
  trailer from an old commit, a doc, or this skill — model names change and stale trailers
  have shipped before. If no reminder gives one, ask.
- **Check delegation tools before trusting them.** If `CLAUDE.md` says to route doc writing
  through an external CLI, run it once; if it fails, write the `.md` yourself and tell the user
  the instruction is stale.
- **Verify git state before asserting "everything is committed"** — run `git status`/`git log`.
- **Don't commit others' in-flight edits blind.** If a file has changes you didn't make, or an
  artifact looks corrupted, flag it and ask before staging. `session_board.py --who <file>` (skills
  repo, `hooks/`) says which session changed it; with the session board installed the guard asks the
  user before such a commit — name that session in your question, never approve it yourself.

## Step 1 — update the right doc(s)

Pick the doc from `docs_map` (first match). Rules for the entry:
- **Date it** (absolute date; convert "today/last week").
- State config/levers, the result numbers, and status/next step.
- If it **supersedes or contradicts** an older entry, say so explicitly at the old spot — the
  next session will trust whatever it finds.

## Step 2 — update the cross-session memory

In `memory_dir`:
- **`memory_state_file`** (live status: current runs, what's built, open issues, latest result) —
  refresh the relevant section, keep it compact, point to the long-form doc, and rewrite or delete
  the entries your update supersedes (it is a state, not a diary). A note over the cap → propose
  maintaining-memory.
- **`MEMORY.md`** — add a one-line pointer ONLY for a *new* memory file; never content.
- If the memory root (`~/.claude/projects`) is a git repo — a memory vault — commit the memory
  changes there too: `git -C ~/.claude/projects add -- '*/memory/*.md'` then commit `memory: <what>`
  (its pre-commit hook refreshes the Obsidian aliases). Push only when asked, like any repo.
- If you notice a memory that contradicts a doc, `CLAUDE.md` or a skill, fix the wrong one or
  flag it — do not leave both.

Skip this step only for a trivial mechanical commit (typo, comment) that changes no state.

## Step 3 — stage, commit, (push)

Stage **named paths only** — source + the docs you edited. Never `git add -A` / `git add .`.
Never stage anything under `never_stage` unless the user names it. Memory files live outside the repo.
If the commit is refused because a **review checkpoint is due**, run the running-review-checkpoints
skill first (or `review_status.py --defer` if the user says not now); after a checkpoint, stage
`.claude/review_log.md` with the work.

```bash
git add <source files> <docs you edited>
git status --short                     # confirm nothing unintended is staged
python <organizing-projects skill>/scripts/project_audit.py --staged     # TIDY CHECK: this commit only
git commit -m "$(cat <<'EOF'
<subject: what changed, imperative, ~65 chars>

<body: the why, the key result/mechanism, any "not yet re-run" caveat>

<trailer from the attribution system-reminder>
EOF
)"
git log --oneline -1
```

**Tidy check** (keeps the repo clean one commit at a time; the Bash guard refuses the ✗ items anyway):
- **✗ blocking** (never_stage path, force-added ignored file, editor junk, large file, `_v2` copy of
  code): unstage or fix it before committing. Only if the user named that file for this commit, commit
  with a `TIDY_OK=1` prefix and say so in the report.
- **? README / doc-index lines** for files this commit adds, renames or removes: write them now and
  stage them with the work. They document this commit, like Step 1.
- **? everything else** (move a scratch file, stage an untracked file the code imports, an output file,
  a dated name, a missing README): list it under "Tidy" in the report with its one-line fix; act only
  on the user's yes.

Push (`git push`) only after an explicit "push it" — and run a review checkpoint first if one is due.

## Step 4 — report

Commit hash + subject, which docs/memory you updated, what is still dirty and why
("results/ left unstaged as usual"), the tidy proposals left open, and whether it was pushed or is
local-only.
