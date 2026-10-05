# Changelog

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
