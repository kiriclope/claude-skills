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
- Honest assessment over a pleasing story: say "this did not work, here is why"; separate
  data finding / imposed assumption / model limitation.
- **American English** everywhere (docs, figures, comments, commits).
- **I am colorblind.** Every figure must be colorblind-safe (`making-figures` → `cb_style.py`):
  never red vs green, never hue alone; describe colors by name + shape when discussing a figure.
- Ask before launching anything long-running or outward-facing; commit only when asked, push only on "push it".

## Machine facts
- `ask-kimi` / `extract-chat` / `kimi-write` were removed (2026-10-02; they never worked):
  do not delegate doc writing or reading to a cheap-worker CLI.
- Figures are viewed through the gallery at localhost:8000 (`figure-gallery` skill).
