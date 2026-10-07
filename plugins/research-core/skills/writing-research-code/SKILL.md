---
name: writing-research-code
description: Conventions for writing and editing research code (Python, NumPy, PyTorch) — analysis scripts, models, training, probes, figure scripts — so it stays human-readable, consistent with the project, and numerically trustworthy. Use whenever writing a new script or function, editing model/training/analysis code, adding a config option or CLI flag, or refactoring. Covers naming, docstrings, CLI and config structure, single sources of truth, printed results, reproducibility, and the verify-by-running rule. Not for reviewing finished code → reviewing-code-readability; for correctness bugs → /code-review.
---

# Writing research code

Research code is read by the person who has to trust its numbers. Write it so that a
colleague can open the file, see what it decides, how to run it, and why each non-obvious
choice was made — and so that the numbers it prints cannot silently drift from the model.

## Before writing

1. **Read the file (all of it) and its neighbors before editing.** Look for an existing
   helper first — grep for the function you are about to write. Reuse beats re-implement:
   duplicated logic is where projects drift (a constant copied into a probe script stays
   wrong after the model changes).
2. Check `.claude/project.yaml` → `python`, `env_prefix` for how scripts must be run, and
   `code_rules` for the project's own rules (canonical helpers, constants that must be derived).

## Single source of truth (the most important rule)

- Every quantity is **defined once** and **derived** everywhere else. Never hard-code a value
  that the config or the model already determines (time steps, decay rates, noise levels,
  timings, sizes). Read it from the config/checkpoint with the same defaults the training
  code uses, e.g. `cfg.get("tau", 0.3)`, through one shared helper.
- When a probe/analysis script mirrors training-time logic, call the training code's function
  rather than re-writing it; if you cannot, leave a comment pointing to the original
  ("must match sweep.run_single").
- Never rename stored keys (cache, results, checkpoints) to fix a label — map to display names
  at draw time.

## Readability

- **Names follow the math and the paper**: `alpha`, `kappa` / `kap`, `W_rec`, `n_trials`.
  Readable tokens over initialisms (`pin_cue_nolick`, not `pcnl`). Functions are verbs in
  snake_case; private helpers start with `_`. Files by role: `fig_*.py`, `exp_*.py` (analyses),
  `*_verdict.py` (scorers), `plot_*.py`.
- **Module docstring** = what the script decides, its conventions, and a `Usage:` block with
  the exact command. Use it as the CLI help (`argparse.ArgumentParser(description=__doc__,
  formatter_class=argparse.RawDescriptionHelpFormatter)`).
- **Comments say why, not what**: the reason for a constant, a sign convention, a past bug
  ("# direct verification — never trust a finder unchecked"). Date decisions that came from a
  discussion ("Which field (2026-09-25): …"). Shape tags on tensors: `# (B, T, rank)`.
  Unicode math (κ₀, σ, λ) is welcome in comments and printed output.
- Section rules for long files: `# ── trials ─────────────`.
- Match the surrounding code's density and idiom; do not reformat code you did not change.
- Comments and docstrings in American English; existing identifiers keep their spelling
  (renaming `behaviour` → `behavior` in a name breaks every caller).

## Structure

- One `main()` under `if __name__ == "__main__":`. argparse flags with `help=` that explains
  the semantics; `nargs="*"` for id lists, `choices=[...]` for modes.
- Configs are dataclasses (`frozen=True` where possible) with commented fields and derived
  values as `@property`; variants via `dataclasses.replace`.
- **New options are keyword arguments with a default that reproduces old behavior**, so old
  checkpoints and configs still load. One list-valued option beats several booleans on the
  same axis (`freeze_stages=["gng", "dual"]`).
- Paths: absolute for logs and outputs; no build artifacts left in temp dirs.

## Numbers you can trust

- **Seed everything** per run (`torch.manual_seed`, `np.random.default_rng(seed)`,
  `torch.cuda.manual_seed_all`), and record the seed and the git hash with the results.
- Evaluation under `torch.no_grad()`; take the device from the model
  (`next(model.parameters()).device`); `.detach().cpu().numpy()` before NumPy.
- **Verify solvers**: check the residual of every fixed point, root or optimum you report.
- **Print results unit by unit** (one row per seed / subject / run), aligned, signed format
  (`+.2f`), then a `SUMMARY: k/N …` line. A mean alone hides the one run that worked.
- Use `flush=True` and a `[run_id]` prefix in long-running logs.

## After writing — verify by running

Run the code on a small real case and read the output before saying it works. For a fix,
reproduce the bug first, then show it gone. For a refactor, show identical output before and
after. Say plainly what was not run. Then review it with the `reviewing-code-readability` skill
(its checker on the changed lines + the colleague test) before calling it done.

## Never

- Engineered shortcuts that force the desired result (loss terms or constraints that encode
  the answer) unless the user asks for them explicitly.
- Silent fallbacks that hide a failure (bare `except:`, default values for missing data).
- Printing secrets or the contents of variables/files named `*KEY*`, `*TOKEN*`, `*SECRET*`.
