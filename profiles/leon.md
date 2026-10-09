# Personal profile — Leon (loaded in every project via ~/.claude/CLAUDE.md → this file)

Colleagues: copy this file to `profiles/<you>.md`, edit it, and symlink it as your own
`~/.claude/CLAUDE.md`. The shared skills read their defaults from here and from each
project's `.claude/project.yaml`; nothing personal belongs inside a shared skill.

## Who
Computational neuroscientist: low-rank / EI RNNs (PyTorch), dynamical-systems analysis,
mouse electrophysiology, paper drafting (Neuron, Nature Neuroscience). Emacs + Org-mode, Linux, screen,
2× A30. Package manager: **mamba** (`/home/leon/mambaforge`), never conda.

## How to work with me
- Concise answers, no padding. Explain the math/science, not just the commands.
- **When my request is vague** (no clear goal, deliverable, scope or success criterion, or several
  readings), use the `clarifying-requests` skill before acting: look in the context first, then ask
  me a few sharp questions with concrete options — be my reflection, not an interrogation.
- **Review checkpoints** are on in my projects (`running-review-checkpoints`): when one is due, run it
  before ending the turn; never record a review I did not approve.
- Honest assessment over a pleasing story: say "this did not work, here is why"; separate
  data finding / imposed assumption / model limitation.
- **American English** everywhere (docs, figures, comments, commits, chat): realize, initialization, behavior,
  labeled, modeling, canceled, center, analyze, gray — not -ise / -our / -lled / -tre.
- When I start fixing the code myself, stop and let me — don't wait for me to explain.
- **I am colorblind.** Every figure must be colorblind-safe (`making-figures` → `cb_style.py`):
  never red vs green, never hue alone; describe colors by name + shape when discussing a figure.
- Ask before launching anything long-running or outward-facing; commit only when asked, push only on "push it".

## Which skill when (load it before starting — these never trigger on their own often enough)

| When | Skill |
|---|---|
| my request is vague | `clarifying-requests` |
| starting a session, "where were we" | `resuming-work` |
| planning an experiment, "what next" | `planning-research` |
| launching or monitoring a sweep / long job; "what did we train" | `launching-experiments`; `run-card` |
| training misbehaves | `debugging-training` |
| numbers just came out, before any conclusion | `auditing-results` |
| choosing a test, a p-value, a star | `choosing-statistics` |
| a conclusion that matters, "think critically" | `thinking-critically` |
| deriving or checking math | `checking-derivations` |
| low-rank RNN flows, trajectories, g·λ | `flow-verdict`, `traj-verdict`, `bifurcation-probe` |
| **any** figure or plotting code (never `dataviz`) | `making-figures` |
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
- `ask-kimi` / `extract-chat` / `kimi-write` were removed (2026-10-02; they never worked):
  do not delegate doc writing or reading to a cheap-worker CLI.
- Figures are viewed through the gallery at localhost:8000 (`figure-gallery` skill).
