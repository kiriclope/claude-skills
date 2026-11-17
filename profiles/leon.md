# Personal profile — Leon (loaded in every project via ~/.claude/CLAUDE.md → this file)

Colleagues: copy this file to `profiles/<you>.md`, edit it, and symlink it as your own
`~/.claude/CLAUDE.md`. The shared skills read their defaults from here and from each
project's `.claude/project.yaml`; nothing personal belongs inside a shared skill.

## Who
Computational neuroscientist: low-rank / EI RNNs (PyTorch), dynamical-systems analysis,
mouse electrophysiology, paper drafting (Neuron, Nature Neuroscience). Emacs + Org-mode, Linux, screen,
2× A30. Package manager: **uv** (`uv run python`; one `pyproject.toml` + `uv.lock` per project, as in ~/rnn and
~/balance_llm; no `LD_PRELOAD` shim). Moving off mamba (2026-10-30): a project without a uv env yet keeps its mamba
env (`/home/leon/mambaforge`) until it gets one; never conda.

## How to work with me
- Concise answers, no padding. Explain the math/science, not just the commands.
- **When my request is vague** (no clear goal, deliverable, scope or success criterion, or several
  readings), use the `clarifying-requests` skill before acting: look in the context first, then ask
  me a few sharp questions with concrete options — be my reflection, not an interrogation.
- **Review checkpoints** are on in my projects (`running-review-checkpoints`): when one is due, hold it
  when I accept a plan or a next step, or ask to commit or push (never pop it up over a plan I have not
  read), each question understood on its own; never record a review I did not approve.
- **Every claim carries its measurement, chat included** (`auditing-results`, 2026-11-03 review of seven wrong reports):
  run and stage, trials, window, metric, k/N; numbers computed this session, never by eye or from a summary; a finder,
  a loss or a log field is a proxy; "gone / lost" only after the direct test; when I read a figure differently,
  measure first; an interpretation that changes the next run goes to a fresh critical-reviewer before you send it.
- Honest assessment over a pleasing story: say "this did not work, here is why"; separate
  data finding / imposed assumption / model limitation.
- **Show me, don't tell me — especially in auto mode.** Every verdict (solved, works, fails,
  discarded) comes as its figure, the verdict right below it, the per-unit table, then the argument
  hypothesis by hypothesis (prediction → each test with its numbers → calibrated conclusion), clear
  to someone who missed the session, also appended to the project's verdict log (`auditing-results` §0).
  The figure shows the effect itself, designed for the problem, not the test tally: from your knowledge,
  the literature, my propositions and our own views (`making-figures`, figure brief; 2026-11-04).
  Discards most of all: I can't catch a wrong discard I never saw.
- **American English** everywhere (docs, figures, comments, commits, chat): realize, initialization, behavior,
  labeled, modeling, canceled, center, analyze, gray — not -ise / -our / -lled / -tre.
- When I start fixing the code myself, stop and let me — don't wait for me to explain.
- **I am colorblind.** Every figure must be colorblind-safe (`making-figures` → `cb_style.py`):
  never red vs green, never hue alone; describe colors by name + shape when discussing a figure.
- Ask before launching anything long-running or outward-facing; commit only when asked, push only on "push it".

## Model routing (`advising-research`; agents in `~/.claude/agents/` → `plugins/personal/agents/`, all at effort medium)

| Phase | Who | Model |
|---|---|---|
| plan | `research-planner` | Fable (alias `fable`) |
| code | main session | Opus 5.5 (the session model) |
| sweep launch / check-on / finish | `sweep-runner` | Sonnet (alias `sonnet`): matched Opus on a dry test, 2026-10-14 (`~/tmp/sweeprunner_trial/REPORT.md`); to move it back, set `model: opus` in the agent |
| check results; `auditing-results` | `result-checker` (fresh context) | Opus 5.5 (alias `opus`) |
| fresh review of `thinking-critically` | `critical-reviewer` | Fable (alias `fable`) |

## Which skill when (load it before starting — these never trigger on their own often enough)

| When | Skill |
|---|---|
| my request is vague | `clarifying-requests` |
| starting a session, "where were we" | `resuming-work` |
| planning an experiment, "what next" | `planning-research` |
| a phase boundary: a plan is needed, a sweep launches or finishes, results come in | `advising-research` (routes it) |
| launching or monitoring a sweep / long job; "what did we train" | `launching-experiments`; `run-card` (not in `~/rnn`: there the run's `config.json` lists its stages) |
| training misbehaves | `debugging-training` |
| numbers just came out, before any conclusion | `auditing-results` |
| several verdicts on one question; "what do we know about X", "conclude" | `concluding-research` |
| choosing a test, a p-value, a star | `choosing-statistics` |
| a new measure or pipeline, its first result; "did the numbers change" | `validating-pipelines` |
| a decoder / CCGP / axis result; "is it above chance", "is it just licks" | `validating-decoders` |
| a finished sweep, before any flow, trajectory or figure; "do these nets really work" | `validating-networks` |
| a result becomes a claim in a draft; "what would falsify this" | `validating-claims` |
| a conclusion that matters, "think critically" | `thinking-critically` |
| deriving or checking math | `checking-derivations` |
| low-rank RNN flows, wells, trajectories | `validating-networks`, then the project's state table (`~/rnn`: `analysis/state_table.py`); `flow-verdict`, `traj-verdict`, `bifurcation-probe` are the old `~/rnn_dual` tools, not used in `~/rnn` |
| **any** figure or plotting code (never `dataviz`) | `making-figures` |
| showing a figure to me ("show me", a verdict's figure) | `showing-figures` |
| writing code; before committing it | `writing-research-code`; `reviewing-code-readability` |
| paper text; its numbers; its references | `writing-paper`; `auditing-paper-numbers`; `verifying-citations` |
| related work, novelty | `reviewing-literature` |
| "act as a reviewer", before submitting | `reviewing-manuscript` |
| referee reports arrived | `responding-to-reviewers` |
| publishing a page, artifact comments | `publishing-drafts` |
| tidying the repo, lost or duplicated files | `organizing-projects` |
| a review checkpoint is due, "catch me up" | `running-review-checkpoints` |
| "log", "commit" | `log-and-ship` |
| memory too long or contradicting the docs; "trim / archive the memory" | `maintaining-memory` |
| changing the skills themselves | `maintaining-skills` |
| your last message did not land (I type `/wait-what`) | `wait-what` (user-only) |
| a session went wrong, "retro" | `maintaining-skills` → Retro |

## Compact instructions
Long sessions compact, often several times, so the summary must carry what a fresh reader needs.
Keep, in this order:
- the goal and the spec or plan in force (GOAL / CRITERION), in my words, and when I asked;
- decisions I made, and questions still open — a pending question is never an approval;
- my corrections ("don't do X") and the rules they set;
- files created or changed (paths), commits (hashes), pushes, running jobs (screen names, run dirs);
- key numbers with their source (file, run, script), each marked verified or assumed;
- what failed and why, so it is not retried; the next step.
Drop: tool outputs and file contents that can be re-read, images, superseded attempts.

## Machine facts
- **Pages archive:** `~/claude-artefacts` (private git, laid out like claude-memory): `publishing-drafts`
  copies every published page there and commits.
- Do not delegate doc writing or reading to a cheap-worker CLI: the ones tried did not work.
- Figures are viewed through the gallery at localhost:8000 (`figure-gallery` skill).
