---
name: running-review-checkpoints
description: Hold regular human review checkpoints so a project's code, docs and proposals stay understood and owned by the user — no unreviewed AI code, no unreadable human code, no silent drift. When review_status.py says a checkpoint is due (a prompt hook says so with each message, a commit gate refuses commits, in opted-in projects), hold it at the next plan boundary — when the user accepts a plan or a next step, or asks to commit or push — never over a plan or result the user has not read: a one-screen digest (intent, changes and why, decisions to approve, drift, hunks to read), then questions each understood on its own, and record the review only after the user approves. Use when a review is due and the user just accepted a plan or a next step, when the commit gate refuses a commit, when a task's CRITERION is met, before a push, for "where are we", "what changed", "catch me up", or to switch checkpoints on/off. Not for reviewing one file's code → reviewing-code-readability.
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
While off, the prompt hook and the commit gate stay silent. Say what you switched and how to undo
it. `--reset` is the user's call, never yours: it writes that the earlier changes went unreviewed.

## When: at a plan boundary, never over something the user has not read

The questions come in a pop-up that covers the text above it. So hold the checkpoint where the user
has just read and decided, and never at the end of a turn that shows a plan, a verdict or a figure.
**Why:** set off by a line count at the end of any turn, it popped up over plans the user had not
read yet (2026-11-04).

When `review_status.py` says DUE (in projects with `review_checkpoint:` in `.claude/project.yaml`,
the prompt hook adds this to each message of the user), hold it at the first of:
- **the user accepts a plan or a proposed next step** ("go", "yes", "do 1 and 3"): run the checkpoint
  first, then start the accepted work, with the answers applied;
- **the user asks to commit or push** (the commit gate refuses commits while it is due);
- the user asks ("review", "what changed", "catch me up").

Otherwise carry on and do not mention it. A task whose CRITERION is met (the spec of
clarifying-requests or the plan of planning-research) gets its checkpoint at the next of these
moments, even if not due.

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

The pop-up hides the digest, so each question must be understood alone, by a reader who sees only
it. **Why:** questions like "The models.py speedup (last-digit changes in wi's gradient)?" and options
like "My config choices" could not be answered without asking back (2026-11-04).

- One question per consequential decision, at most four per round (a second round if more). The
  question, in 2–4 plain sentences: what was decided and where (file, function); what it changes for
  the user (which numbers, runs, figures or behavior, or "nothing reruns"); why it was chosen; what
  the alternative was. Full names: restate what a label or code means (M1, H2, an arm code).
- The `header` chip names the decision ("Noise scale"), never "Decision 1".
- The options are the concrete choices, each description saying what happens next: **Approve**
  (what stays), the alternative by name ("Use 0.05 instead: config.py:41 changes, 3 figures
  rebuild"), **Explain first** (you walk the user through it before they decide).
- The hunk (≤ 25 lines) goes in the Approve option's `preview`, so the code sits beside the question.
- Minor decisions may share one multiSelect question. Each option there still says what it is and
  what approving it means: no catch-all options ("my config choices").
- Ask "Still the right direction?" only when the Drift list is not empty, naming the drift. At a plan
  boundary the user has just chosen the next step.
- "Not now" is a valid answer: run `review_status.py --defer` (the next checkpoint comes one
  threshold step later) and carry on.

## Step 4 — act, then record

1. Apply what the user changed; revert what they rejected, and show the diff.
2. Record it: `review_status.py --mark --note "<approved 1, 3; changed 2 → …>"`, in its own command
   before the commit (the commit gate checks before a command runs). The note says what the user decided. **Never mark a review the user did not explicitly approve in this checkpoint**
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
The first `review_status.py` run sets a baseline: past work does not trigger a review. The prompt
hook and the commit gate are installed once per user (`hooks/README.md` in the skills repo).

## Never

- Record a review the user did not approve, or approve on the user's behalf.
- Skip a due checkpoint because the changes "are small" or "were requested" — the threshold decides.
- Pop up questions in the turn that shows a plan, a verdict or a figure: the user has not read it yet.
- Paste the whole diff: a walk-through is a different, slower review the user can ask for.
