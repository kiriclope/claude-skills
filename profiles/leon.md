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
- **Review happens in the flow**, not on a line count: I approve the spec, the tickets and the experiments, then check
  each verdict card and `/run-spec`'s QA plan (review checkpoints removed 2026-11-19).
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

## Which skill when

Skills load from their descriptions; this table holds only what the descriptions cannot say. Lost? `/ask`.

| When | Do |
|---|---|
| an effort over several sessions (a paper, a figure to replace) | Pocock's skills + `research-flow` (fork `~/pocock-skills`): I type `/grill-research`, `/to-spec`, `/to-tickets` (one session), then `/run-spec` (I approve the experiments once and check the QA plan) or `/run-ticket` |
| **one ticket, one session** | each ticket starts fresh from the board; past two compactions or ~150k tokens, finish or pause the ticket, write its state on it, propose `/clear` |
| where things stand | the board (the spec's tickets) and the conclusions doc; memory only for what is in neither (`resuming-work`) |
| "does this mechanism work at all" | suggest `/toy-model` |
| a phase boundary (plan, sweep, results) | `advising-research` routes it to the agents above |
| a p-value or star; a decoder / axis result; a result becomes a claim; training misbehaves | `choosing-statistics`; `validating-decoders`; `validating-claims`; `debugging-training` (none loaded on its own in the 30 days to 2026-11-19: load them) |
| low-rank RNN flows, wells, trajectories | `validating-networks`, then `~/rnn`'s `analysis/state_table.py`; `flow-verdict`, `traj-verdict`, `bifurcation-probe` are old `~/rnn_dual` tools; `run-card` not in `~/rnn` (the run's `config.json`) |
| **any** figure | `making-figures`, never `dataviz` |
| before a submission | `/review-internal` → `/review-editor` → `/review-referee`; literature and real referee reports are commands I type (`/reviewing-literature`, `/responding-to-reviewers`) |

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
