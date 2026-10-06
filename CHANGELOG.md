# Changelog

## 2026-10-06 — research-core 0.7.0
- New `running-review-checkpoints`: human review checkpoints against unreviewed AI code, unreadable
  human code and drift. `review_status.py` measures changed lines and commits since the user's last
  review, from a snapshot of the working tree kept in the per-worktree ref refs/worktree/review/last
  (uncommitted and new files count; index and files untouched); first run sets a baseline;
  `--mark` records an approved review in .claude/review_log.md; `--defer` postpones one step.
  Enforced by a Stop hook (`--hook stop`) and a commit gate in hooks/guard_bash.py. Digest: intent,
  changes with their why, decisions to approve, drift, the hunks to read, readability.
- readability_check.py: `--since REV` compares against any commit (used by the checkpoint).
- Opted in: rnn, rnn_symmetry, dual, neuron_symmetry (300 lines / 3 commits).
- On/off: `--off` / `--on` per project (local state in the git dir, not committed) or `--global`
  (~/.claude/review_checkpoints.json); hooks and commit gate are silent while off; `--reset` starts a
  fresh baseline and logs the skipped changes as NOT reviewed.

## 2026-10-06 — research-core 0.6.0
- New `clarifying-requests`: the reflection partner for vague requests — look in the context first,
  mirror the request (and the deeper question behind it), ask at most four concrete questions with
  options (AskUserQuestion), problem-level before detail-level, then a five-line task spec (GOAL,
  DELIVERABLE, SCOPE, DONE WHEN, DEFAULTS) that feeds thinking-critically. references/question_bank.md:
  nine dimensions and worked examples. profiles/leon.md: use it whenever a request is vague.
  Tested with a fresh agent: "plot the nocue sweep" → resolved from memory and docs, no questions;
  "the figures need to be better" → mirror plus three concrete questions with options. Its feedback
  added the rule that defaults never stretch approval to costly extras.

## 2026-10-06 — research-core 0.5.0, lowrank-rnn 0.2.0
- The fresh independent review of `thinking-critically` (steps 3–4) is wired into every skill that
  draws a conclusion: auditing-results (§7, before a verdict is reported), planning-research
  (before a verdict is logged or acted on), writing-paper (Step 3b, claims before a draft is
  shared), reviewing-literature (novelty and "they show" claims), responding-to-reviewers (each
  response against its comment and the revised manuscript), flow-verdict and traj-verdict
  (interpretation beyond the tool's score). Only for conclusions that are reported or acted on.

## 2026-10-06 — 0.4.0
- New `thinking-critically`: plan with a pre-stated criterion → act with a claims ledger
  (observed / derived / recalled / assumed) → review by a FRESH general-purpose agent (never a fork;
  never shown the author's reasoning; optional second model via codex) that re-checks each claim
  against primary evidence and the literature → triage and revise with a calibrated confidence.
  references/reviewer_brief.md (the reviewer's prompt), references/failure_modes.md (17 failure modes
  from real projects + 5 test cases). Tested on a planted case: the fresh reviewer caught both planted
  errors and one imprecise claim the tester had believed true; its citations checked out.

## 2026-10-06 — 0.3.0
- New `reviewing-code-readability`: a colleague-test rubric plus `readability_check.py`, which flags
  hard-coded derived constants (caught the historical `alpha=0.075` bug), comments that swallowed code,
  silent excepts, opaque names, missing docstring/Usage, hex colors, deep nesting and long lines — by
  default only on lines changed since HEAD. `references/examples.md`: before/after pairs from real fixes.
- `writing-research-code` hands off to it and reads project `code_rules`; American English in comments only.
- templates/project.yaml: `code_rules` and `code_check` (max_line, derived_names, derived_callees,
  config_files, style_modules).
- templates/project.yaml: `CLAUDE.md` is no longer in `never_stage` — it is committed like any doc
  (log-and-ship still shows edits it did not make before staging them).

## 2026-10-02 — 0.2.0
- New research-core skills: auditing-results, auditing-paper-numbers, verifying-citations, reviewing-literature,
  writing-paper, responding-to-reviewers, checking-derivations, launching-experiments, debugging-training —
  each with a script + passing `--demo` where the step is mechanical.
- making-figures: colorblind-safe standard (`cb_style.py`: Okabe-Ito, blue/vermillion pair, fixed points coded by
  shape), `check_figure` flags colors confusable under deuteranopia/protanopia.
- hooks/guard_bash.py: ask on git push, deny commits without trailer, deny foreground sweeps (install by hand).
- templates/project.yaml: figure_*, paper_dir, numbers_log, style_guide, launch, verdict_scripts keys.
- `.claude/settings.json` disables the watermark-scrubbing plugin inside this repo (its fix deletes descriptions).

## 2026-10-02 — 0.1.0
- Repo created as a plugin marketplace: `research-core` (shareable), `lowrank-rnn` (domain), `personal`.
- Migrated `log-and-ship` (now generic: reads `.claude/project.yaml`, trailer from the session, no stale model name),
  `flow-verdict`, `traj-verdict`, `bifurcation-probe` (from ~/rnn, the newest copies; `$ENV_PREFIX` instead of a
  home path), `figure-gallery` (personal).
- New: `making-figures` (+ `paper.mplstyle`, `check_figure.py`, caption reference), `writing-research-code`,
  `planning-research`, `maintaining-skills` (+ `lint_skills.py`).
- `profiles/leon.md` linked as `~/.claude/CLAUDE.md`.
