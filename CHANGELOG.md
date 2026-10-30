# Changelog

## 2026-10-30 — research-core 0.20.0 (reviewing-manuscript)
- **Pre-checks before the lenses**: `materials.py` prints the numbers audit, claims-ledger and reference checks with
  their paths filled in (only those whose inputs exist); their outputs go to the reviewers. Lens 2 computes small-n
  floors with `stats_floor.py --n / --counts`. **Why:** a reviewer agent misread a band a script gets right (2026-10-29).
- **Claim status (Step 2b)**, after the blind lenses: each Abstract/Results claim mapped to its verdict card or
  conclusion; text stronger than its status (open, exploring-only, a screen read as mechanism) is must-fix, a claim
  with no record is should-fix.
- **Review file** `<reviews_dir>/<date>_<scope>.md` (template `reviews_dir: docs/reviews`): numbered findings; the next
  review's triage marks each old one fixed / back / not checked. Lenses never see it.
- **Recall trial** on the dual paper's 2026-08-30 snapshot (~/tmp/review_trial/REPORT.md; lenses 1, 2, 4, 5 on Opus):
  3 of 5 known must-fix found, 1 partly, 1 inverted (pass mark 4: partial). Fixed from it: variant renders listed
  for lens 2 (the knob-dependent star sat in a variant the canonical-only rule withheld); a value read by running
  code counts only with the figure script's own arguments, and code-vs-doc findings are re-checked at the call site.

## 2026-10-29 — research-core 0.19.0 (concluding-research)
- **New skill concluding-research**: one question across all its verdict cards → pooling check (scoring, criterion,
  metric, code, seeds), a hypothesis ledger with calibrated status (established = confirmed on fresh seeds; an
  undecidable test is open, not "not supported"), discards with how decisive they were, contradictions and corrections
  (listed, cards not edited), a plain answer with a status-by-shape figure, 2–3 next experiments ranked by how much they
  would change the answer as draft pre-run cards, a fresh review, and the question's section rewritten in place in
  `docs/conclusions.md`. Script `collect_cards.py` lists the cards and flags after-data / open / corrected ones.
- Tested on rnn's Dual-curriculum question (21 cards; ~/.claude/jobs/f1653fb5/tmp/conclude_test/): the fresh review
  caught a silently skipped failing run and a card appended mid-session. Fixed in the skill: a run account per
  hypothesis (no quiet exclusions), re-collect before writing, uncarded runs listed, "N cannot decide" written as open
  even when every replicate agrees, replicates (seeds) counted rather than runs, re-tallied as a pooling option, "what
  would overturn it" instead of a post-hoc falsifier, the reviewer's plan = the cards' own criteria, a defined ledger
  figure (per-card shapes: supports / against / no effect / cannot decide; x = card order), answer up to 8 lines.
  `collect_cards.py`: headings by default (`--body` opt-in), more correction words, Question / Claim tested as Plan.
  **Why:** answers spread over ~10 cards per question; titles outlived their corrected evidence; a discard was logged on a
  count no outcome could reverse.
- Wired: profile skill table, project.yaml template (`conclusions_doc`), planning-research Step 3, README.

## 2026-10-29 — research-core 0.18.0 (a plan before every arm)
- **planning-research** Step 1, the pre-run card: every arm, even a quick "try X", gets six lines (WHY, PREDICTS, CRITERION
  with its cost side, FLOOR, RIVALS, N) opened at the top of the verdict log before the run, status RUNNING; the verdict
  fills in below it. **Why:** none of 25 verdict cards in one project quoted a plan; two set their criterion after the run.
- **Can N decide it?** Run stats_floor.py before the launch; a design whose every outcome misses the criterion is changed
  or labeled a pilot. The full plan: rivals each with their control (or "at best open"), the noise floor planned as an arm,
  independent units (runs sharing a parent stage count once). After results: the verdict words of auditing-results §0
  (supported / not supported / refuted / open), not "confirmed / inconclusive".
- **choosing-statistics** `stats_floor.py --counts N`: for two arms of N solved/not-solved units, the counts Fisher's exact
  test can separate from each baseline (better or worse), and the discordant pairs McNemar needs for twins; self-tests
  added. At N = 6 a 5/6 baseline leaves no count that shows an arm helps.
- **The scientific-method rules of the card** (planning-research Step 1): premises cite a checked source (a test card's
  WHY rested on an overstated line of an uncorrected card); WHY "none: a screen" supports no mechanism; STAGE exploring /
  confirming: an exploring pass stays "open" until fresh seeds repeat it with the criterion unchanged (forking paths), with
  the number of arms tried for the question; a quantitative prediction from theory when there is one (severity).
- **launching-experiments** `record_provenance.py --card <verdict log> --card_heading "<heading>"`: freezes the card
  into each run directory as precard.md + sha256 in provenance.json (missing or ambiguous heading → error); the verdict
  quotes that copy and explains any later edit of the log's card (auditing-results).
- **launching-experiments** (launch table, checklist), **advising-research** (the planner returns a card per arm) and
  **auditing-results** (the entry is written under its open card; Plan slot) point to the card.

## 2026-10-29 — research-core 0.17.0, personal 0.2.1 (scientific method in the verdict; model routing)
- **auditing-results §0**: hypotheses marked as planned or after the data; rivals per test (strong inference); the noise
  floor beside every effect; calibrated words (supported / not supported / refuted / open); exact intervals and Fisher's
  test for counts; a Next line. In the chat the evidence figure comes first and the whole entry right below it. "Who runs
  it": the profile's audit agent when one is assigned.
- **making-figures, Evidence figures**: the noise floor drawn next to the effect, or the panel says none was measured.
- **planning-research**: save the plan, dated, before the run, so the verdict can quote it.
- **thinking-critically** step 3: the fresh review runs on the profile's critical-review agent.
- **personal agents**: `effort: medium` on research-planner, sweep-runner and result-checker; new `critical-reviewer`
  (read-only, on the model the profile assigns). Profile: model routing for auditing-results and thinking-critically.
- Re-tested on the delay-pin verdict (~/tmp/verdict_format_trial/, v2): it ends open, not discarded; its notes on the
  rules (no word for a large effect without a floor, Fisher vs twins, shared parent stages) are open items.
- Figures stay on the main session: Sonnet vs Opus on one evidence figure, scored blind, failed the fixed criterion
  (worse figure 7 vs 6 defects, a wrong noise band); ~/tmp/figure_model_trial/REPORT.md.

## 2026-10-29 — research-core 0.16.0 (a verdict is an argument: hypotheses → tests → panels → conclusions)
- **auditing-results §0**: the verdict card (claim / criterion / figure / look at / verdict) becomes a verdict entry
  organized by hypothesis: each test names what it compares, its criterion (fixed before / exploratory / shown only), its
  panel ("Fig. A": what to look at) and its result, and ends with what it means for the hypothesis; a conclusion per
  hypothesis, then the verdict (kept / discarded / superseded / open). Written for a reader who missed the session, short,
  independent units only. A clarity check: a fresh agent restates the entry from the text and the PNG alone (≤ 2 rounds).
- **making-figures, Evidence figures**: laid out by the argument (one row per hypothesis, panels A, B, … in the text's
  order), panel title = test + result, one encoding for the whole figure, paired criteria as slope lines or differences,
  main title = the verdict in one line, ≤ 6 panels.
- **cbstyle**: `evidence_figure(rows, verdict)` builds that layout and returns the panels by letter; `PASS` / `FAIL` marker
  styles. Profile and project.yaml template: "verdict entry".
- Tested on the rnn delay-pin verdict (a 3 × 3 figure by arm, no letters): the rewrite reads hypothesis by hypothesis; the
  clarity check found 5 text/figure mismatches in round 1, none in round 2. Its 14 notes on the instructions became the
  sizes in the helper, the open verdict, the shown-only criterion, independent units, paired criteria and the stopping
  rule. Files: ~/tmp/verdict_format_trial/.

## 2026-10-26 — research-core 0.15.1 (pages archive)
- **publishing-drafts** Step 4: when the profile names a pages archive (a private git repo), every published page
  is copied to `<archive>/<project key>/<page>/<page>.html`, its README row updated and committed there. Why: the
  built pages were untracked everywhere (no recoverable version), and the code repos shared with colleagues must
  not carry them. Profile leon.md: the archive is `~/claude-artefacts`.

## 2026-10-20 — research-core 0.15.0 (evidence figure behind every verdict)
- **auditing-results** §0 (new, top): no verdict without its evidence figure, whether kept or discarded and
  including exploratory dead ends. A verdict card (claim · criterion · figure · look at · verdict) goes in the
  reply and is appended to the project's verdict log. Why: in auto mode, results were solved or dropped in one
  line of text, so a wrong discard could not be caught.
- **making-figures**: "Evidence figures" spec: every unit shown, the criterion drawn, pass/fail by shape + fill,
  the figure's main title is the VERDICT line, one panel per reason in VERDICT (a cost, such as lost accuracy,
  gets its own panel), no abbreviation without a key, and every check_figure overlap fixed.
- Tested on the rnn design2 wells discard (fresh agent, auto mode, no mention of figures): the card, the log and
  a per-seed figure came unprompted, and w4 s0/s1 were not written off. The figure lacked the GNG accuracy
  panel behind the w4 discard → the panel-per-reason rule.
- `templates/project.yaml`: `verdict_log:` (default `docs/verdicts.md`). Profile: "Show me, don't tell me" line.

## 2026-10-14 — research-core 0.14.0, personal 0.2.0 (advising-research: route each phase to its model)
- **advising-research** (new): the main session is the advisor. It keeps the user's decisions and writes the
  code, and hands planning, sweep launching and result checking to the agents the profile's **Model routing**
  table assigns, with self-contained PLAN / SWEEP / CHECK handoffs. Approvals stay with the user, the sweep-runner
  launches only the approved table, and the checker gets the evidence, not the author's reasoning. No model
  names in the skill.
- **personal/agents** (new): research-planner (fable), sweep-runner (sonnet), result-checker (opus), linked into
  `~/.claude/agents/`. The sweep-runner model was chosen by a dry test (16 runs + 4 reruns, $11): Sonnet matched
  Opus 4.8 on clean launch, a `--run_filter` that selects 16 runs instead of 4 (both stopped), check-on and finish,
  once the failed-run rule was made unambiguous (it had stopped Sonnet before the figures).
- Profile: Model routing table; advising-research row in "Which skill when". README: the skill and the agents.

## 2026-10-12 — research-core 0.13.0, lowrank-rnn 0.4.1 (bugs found by a fresh-agent review)
Two fresh agents reviewed the validation scripts (ponytail's review procedure: every finding needs a concrete
failing input). Each fixed bug is now a `--demo` case that fails on the previous version.
- **decoder_check.py**: a nan score printed PASS (now NON-FINITE SCORE); CONFOUNDED compared the matched trials'
  score with the full set's null, so a label-only decoder whose licks follow the label was called confounded (11
  of 36 simulated runs; now 1 of 36): the matched score is judged against shuffled labels on the matched trials,
  with unmatched subsets of the same size as the power control, and the nuisance must itself decode; crash when
  the first class had more than 3× the trials of the second; adapters could not import project code (the
  current folder is now on the module path); the time estimate counts every call.
- **recovery_check.py**: nan estimates printed PASS or crashed (NON-FINITE ESTIMATE); a correct measure that
  falls with the planted effect failed NOT MONOTONE (now ordered by truth()); DETECTABLE reports the smallest
  effect in size; the ci must be a 95% interval (documented).
- **claims_ledger.py**: a bare `type: null` read as no type; paths now resolve from the project root; a claim
  sentence right under a heading was skipped; a control without `falsifies_if` is UNCONTROLLED, and one without
  an output or a source is STALE (was CONTROLLED); `source` documented as the data file, not the numbers log.
- **pin_numbers.py**: re-pinning prints the changes it accepts and keeps `<snapshot>.prev`.
- **reviewing-code-readability**: new Step 3, a fresh-agent bug hunt for every new or verdict-printing script,
  each finding with a concrete failing case, each fixed bug added to the demo. (Ponytail itself is not part of
  these plugins. A later test on four real tasks, 16 headless runs, found that its lite mode halved the code with
  the same correctness and controls, and it still asked on a vague request; it is now enabled per project.)
- **validating-networks**: UNCHECKED (a run with no logged accuracy) and runs that loaded `gng_ckpt`.
- **writing-research-code** (two of ponytail's rules): end the reply with what was skipped or not checked; mark a
  deliberate shortcut `# shortcut: <the limit>, <when to upgrade>`.

## 2026-10-09 — research-core 0.12.0, lowrank-rnn 0.4.0 (validation skills: catch wrong results before a figure)
Four skills, each with a verdict script and a `--demo`; each check is a past error that reached a figure,
a conclusion or the paper. They run the real pipeline on inputs whose answer is known.
- **validating-pipelines** (new): `recovery_check.py` plants effects of known size (and none) through an
  adapter (`simulate`, `estimate`) and reports OFFSET, SHRINKAGE, INFLATION, SIGN FLIP, NOT MONOTONE,
  FALSE POSITIVES, UNDERCOVERAGE and the DETECTABLE effect (demo: a sound pipeline, an offset distance, a
  per-condition normalization, pseudoreplication). `pin_numbers.py` pins a reviewed numbers log and flags
  CHANGED, GONE and NEW numbers after a code change.
- **validating-decoders** (new): `decoder_check.py` runs the adapter's own `evaluate()` on shuffled labels,
  pure noise (LEAKAGE when it decodes above chance; judged against chance, since a leak inflates the null
  too), imbalanced noise (METRIC UNBALANCED), nuisance-matched trials (CONFOUNDED), fewer trials and held-out
  groups (demo: leaky feature selection, plain accuracy, pseudo-trials resampled before the split, a lick
  confound).
- **validating-networks** (lowrank-rnn, new): `net_check.py` at the project root, per run: NOT LEARNED,
  HIDDEN DAMAGE (dual_dpa against after_gng/dpa), MISMATCH (logged accuracies not reproduced from the
  checkpoints with the run's own config), FROZEN DRIFT (each stage's freezes read from its `train.log`), NOISE-TUNED, DELAY-TUNED, FIELD≠TRIALS, SLOW SET.
  On real runs it flags the 2026-10-01 log nets as noise-tuned, a non-learner whose dual_dpa hid damage,
  and `wi.bias` training during Dual in every sweep before the 2026-09-21 fix.
- **validating-claims** (new): `claims_ledger.py` checks a YAML ledger of claims, each with the controls its
  kind requires and the result that would falsify it, written before the control runs: CONTROLLED, FAILED,
  UNCONTROLLED, PENDING, STALE; with the draft, GONE and UNLEDGERED sentences. `--init` writes a skeleton
  from a draft. The ledger path comes from `validation.claims_file` in `project.yaml` (new `validation:`
  block: `claims_file`, `min_n`, `required`).
- **auditing-results** points to the four scripts for checks a table cannot do. 12 eval cases (3 per skill),
  each a past failure: a null result with no detectable effect, the participation ratio against n, pooled
  cross-validation called generalization; a distance with no zero, per-condition z-scoring, trial-level
  tests; correct-trial choice decoding, a single-split null, selection before the split; nets read off
  their trained noise, dual_dpa hiding GNG damage, a continuous attractor scored as no wells.

## 2026-10-09 — research-core 0.11.0 (session board: parallel sessions know each other)
- **hooks/session_board.py** (new): hooks on SessionStart, UserPromptSubmit, PreToolUse (Bash), PostToolUse
  (Bash and edits) and SessionEnd keep `~/.claude/active_sessions.json`: each session's name (the
  background-job name `SendMessage` takes, else its first prompt), folder, repository, branch, last
  prompt, and the files it changed. Bash commands are attributed from modification times after the
  command started, and labeled as a guess. A starting session is told which others are live and what
  they changed and have not committed; an edit to a file with another session's uncommitted change from the
  last hour gets a one-time note naming that session. `--list`, `--who <file>`; demo 10 checks
  (twelve concurrent hooks lose nothing).
- **Bash guard**: asks before a commit that includes another session's uncommitted change from the last
  hour, naming the session (any repository, once the board is installed). The tidy check and this check
  share one simulated index (`project_audit.simulated_index`, `staged_paths`). Demo 32 cases.
- **resuming-work**: the brief has a SESSIONS section (other live sessions, this project's first).
  **log-and-ship**: `--who` before committing changes you did not make; never answer the guard's ask yourself.

## 2026-10-09 — research-core 0.10.1 (from the first backlog cleanup, rnn and dual)
- **project_audit.py --staged**: an untracked file counts as imported only when the import resolves to
  its path; a bare file name counts only next to the staged file or when no tracked file shares it
  (dual's `from src.common import plot_utils` flagged an untracked `utils/plot_utils.py`). The import
  parser no longer runs across lines.
- **organizing-projects**: before proposing to version or clear a file, find what uses it (paper,
  resolved imports, figure inputs, docs, memory) and its size; clearing = commit once, then remove
  (recoverable by hash), a large file goes outside the repository; plan for the review checkpoint
  that large deletions trigger.
- **running-review-checkpoints**: `--mark` in its own command before the commit.

## 2026-10-09 — research-core 0.10.0 (tidy check at every commit)
- **organizing-projects**: `project_audit.py --staged [--all]` checks one commit. It blocks only clear
  mess (a `never_stage` path, a force-added ignored file, editor junk, a file over `large_file_mb`, a
  `_v2` / `_old` copy of code) and proposes the rest: README lines for a new top-level folder or
  script, for a file in a folder whose README lists its files, and for a file the commit removes;
  docs missing from the index; scratch files; untracked files that staged code imports; outputs;
  dated doc names; a missing README. New README section in `references/layout.md`. The audit now
  counts a README.md / index.md inside any docs/ subfolder as a doc index (dual's `docs/pca/README.md`).
- **Bash guard**: refuses a `git commit` that would commit the blocking items, in projects with a
  `project.yaml`. It replays `git add …` from the same command and `-a` on a throwaway copy of the
  index. Override `TIDY_OK=1` (only for a file the user named); off with
  `organize: {commit_check: false}`. Commit-directory detection now follows the last `cd` before the
  commit (`cd x && git add … && git commit` used the session's folder). Demo 29 cases.
- **log-and-ship**: runs the tidy check after staging; writes the README / index lines for this
  commit's own files into the same commit; lists other proposals in the report for the user's yes.

## 2026-10-09 — research-core 0.9.0 (maintaining-memory)
- **New skill maintaining-memory**: trims oversized memory notes to current state + rules that still hold
  + pointers, archives the full original in `memory/archive/` (never deletes), one user approval per note.
  `memory_trim.py` (scan · snapshot · check · apply, `--demo`) and a drafting brief for the fresh agents.
  Built from the first real trim (five notes, 438 KB → 75 KB): a check found that deleting instead of
  archiving would have lost the only description of 25 of the 253 scripts the notes named.
- resuming-work and log-and-ship hand oversized notes to it; log-and-ship: a state note is a state,
  not a diary (rewrite superseded entries when adding one). Profile: the skill in "Which skill when";
  compact instructions.

## 2026-10-09 — research-core 0.8.1 (memory vault)
- **resuming-work**: new `memory_links.py` — writes the Obsidian `aliases:` line into memory notes
  and reports dangling `[[links]]`; `resume_brief.py` no longer reports a symlinked memory folder as
  a duplicate, and lists each real folder once in the cross-project scan.
- **log-and-ship**: commits memory changes to the memory vault when `~/.claude/projects` is a git
  repository (push only on request).
- README: how to set up the private memory vault; profile: American English word list, "stop when I
  start fixing the code myself".

## 2026-10-07 — research-core 0.8.0, lowrank-rnn 0.3.0 (skills review)
Review: usage across 22 sessions (only 7 of 22 skills had ever loaded), two independent reviewers
(quality; gaps from ~1,080 user prompts), claims spot-checked before acting.
- **Loading**: every description says what the skill is not for (→ which one instead);
  making-figures takes precedence over generic charting skills; the profile maps tasks to skills.
- **Fixes**: bifurcation-probe no longer reports wells (flow-verdict owns them: noise-averaged field,
  verified fixed points); guard_bash matches commands not text (commit messages, heredocs), accepts
  tmux/sbatch/qsub/nohup &/--per_run_screen, reads launchers from `launch.entrypoints`; check_figure
  says when the colorblind check cannot run; cb_style resolves symlinks; record_provenance runs as a
  command with `--config` (no versioned import path) and has no silent excepts; audit_numbers refuses
  a script as its log (`numbers_script` vs `numbers_log`); log-and-ship handles the commit gate.
- **Structure**: one canonical plan block (planning-research; CRITERION, FALSIFIER everywhere);
  `evals/` with 11 cases (behavior + skill-fired graders), test cases removed from the reviewer's
  reference; dated project history and a dead path out of the lowrank-rnn skills; checklists are
  reported as one line.
- **New skills**: reviewing-manuscript, choosing-statistics, resuming-work, organizing-projects,
  publishing-drafts (research-core); run-card (lowrank-rnn). Template keys: review_figures, journal,
  field, stats, resume, organize, pages, numbers_script.

## 2026-10-06 — research-core 0.7.1
- README rewritten for newcomers: what it is, five-minute start, how skills work, all 22 skills by
  research stage, how they chain (diagram), installation, configuration and hook reference, scripts,
  maintaining, troubleshooting. All links checked.
- Every script now runs a plain `--demo`: lint_skills.py gains a self-test; cbstyle's demo path is optional.
- templates/project.yaml: no personal names or paths left.

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
