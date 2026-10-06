---
name: running-review-checkpoints
description: Hold regular human review checkpoints while working on a project, so its code, docs and proposals stay understood and owned by the user — no unreviewed AI-generated code, no unreadable human code, no silent drift from the goal. When a checkpoint is due (review_status.py measures changed lines and commits since the user's last review; a Stop hook and a commit gate enforce it in projects that opt in), present a one-screen digest — intent, what changed and why, the decisions taken for the user to approve or change, drift, the 1–3 hunks most worth reading, readability — and record the review only after the user approves. Use when a hook or the commit gate says a review is due, when a task's DONE WHEN is reached, before a push, or when the user asks "where are we", "what changed", "catch me up", "review checkpoint"; also to switch checkpoints on or off ("turn review checkpoints off here / everywhere", "/running-review-checkpoints off").
---

# Running review checkpoints

Three ways a project slips out of its owner's hands: code written faster than it is read (nobody
on the project understands it), code no colleague can read (whoever wrote it), and drift — many
small reasonable steps away from the goal, each invisible from inside one turn. A checkpoint is
where the user re-reads what changed, decides what was decided for them, and takes it back.

## On / off (if invoked with `on`, `off`, `on global`, `off global` or `reset`: do only this)

```bash
python <this skill>/scripts/review_status.py --off            # this project (local switch, not committed)
python <this skill>/scripts/review_status.py --off --global   # every project
python <this skill>/scripts/review_status.py --on [--global]  # back on; unreviewed work since the last review still counts
python <this skill>/scripts/review_status.py --reset          # fresh baseline; logged as NOT reviewed — only on request
```
While off, the Stop hook and the commit gate stay silent. Say what you switched and how to undo
it. `--reset` is the user's call, never yours: it writes that the earlier changes went unreviewed.

## When

- `review_status.py` says DUE — in projects with `review_checkpoint:` in `.claude/project.yaml`
  the Stop hook makes you run the checkpoint at the end of the turn, and the commit gate refuses
  commits until it is done;
- a task's DONE WHEN is reached (the spec of clarifying-requests or planning-research), even if not due;
- before any push;
- when the user asks.

## Step 1 — the facts

```bash
python <this skill>/scripts/review_status.py          # files +/−, commits, readability since the last review
```

## Step 2 — the digest (one screen)

```
REVIEW CHECKPOINT · <project> · <N> lines, <F> files, <C> commits since <last review>
Intent: <the goal being worked on, in the user's words, and when it was asked>

Changed (grouped by purpose; every file gets its why)
  <file>                 +a −d   <why, one line>

Decisions I took for you                                 approve / change
  1. <a default, assumption, threshold, name, structure or trade-off the user did not choose>

Drift (not traceable to a request)
  <scope creep, refactors nobody asked for, changes that contradict the docs or the plan>

Read these (most consequential, least obvious)
  ▸ <file:lines> — <what it decides, why it matters>       (the hunk inline, ≤ 25 lines each)

Readability (changed lines): <checker SUMMARY>
Docs / memory in sync: <yes, or which doc is now stale>
```

- Every file gets its why — never "various improvements".
- **Decisions** lists real choices only; this is where drift hides. Do not bury them in "Changed".
- **Drift** includes changes the user may well like — they still have to hear about them.
- Changes by the user or by other sessions get the same eye (readability, conventions) as yours.
- Choose the hunks after reading the diff: the ones that change a number, a criterion, a default
  or an interface, and the ones whose effect is least obvious.

## Step 3 — the user decides (AskUserQuestion)

- One question per consequential decision (at most four; minor ones batched in one multiSelect
  "approve these"), with options **Approve**, **Change** (Other says how), **Explain first**.
- If the work may be drifting, a last question: "Still the right direction?" with the next
  planned step as the recommended option.
- "Not now" is a valid answer: run `review_status.py --defer` (the next checkpoint comes one
  threshold step later) and carry on.

## Step 4 — act, then record

1. Apply what the user changed; revert what they rejected, and show the diff.
2. Record it: `review_status.py --mark --note "<approved 1, 3; changed 2 → …>"`. The note says what
   the user decided. **Never mark a review the user did not explicitly approve in this checkpoint**
   — not in auto mode, not because the changes look small.
3. `.claude/review_log.md` goes into the project's next commit (log-and-ship).

## Setup (once per project; hooks once per user)

```yaml
# .claude/project.yaml
review_checkpoint:
  max_lines: 300                 # changed lines since the last review
  max_commits: 3                 # commits since the last review
  include: [py, md, yaml, yml, toml, sh, tex, html]
  exclude: [results/, scratchpad/]
```
The first `review_status.py` run sets a baseline: past work does not trigger a review. The Stop
hook and the commit gate are installed once per user (`hooks/README.md` in the skills repo).

## Never

- Record a review the user did not approve, or approve on the user's behalf.
- Skip a due checkpoint because the changes "are small" or "were requested" — the threshold decides.
- Paste the whole diff: a walk-through is a different, slower review the user can ask for.
