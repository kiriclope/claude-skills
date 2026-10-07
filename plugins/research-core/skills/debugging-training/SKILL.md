---
name: debugging-training
description: Systematic diagnosis of neural-network training problems — loss not decreasing, NaN/inf, plateaus, sudden divergence, a stage that "forgets", frozen parameters that drift, results that changed after a code edit, or a model that trains but behaves wrong. Use when training misbehaves or results look implausible, before changing hyperparameters by guesswork, and after any change to the training loop, freezing logic, optimizer or loss. Includes scripts/freeze_check.py for frozen-parameter and gradient checks. Not for launching or monitoring runs → launching-experiments.
---

# Debugging training

Guessing hyperparameters on a broken pipeline wastes days. Reduce the problem to one seed and
one fact at a time, and verify each hypothesis with a measurement before changing anything.

## Step 1 — reproduce small

- One seed, the smallest config that shows the problem, fixed data seed, deterministic flags
  if needed. Record the exact command. If it does not reproduce on one seed, the problem is
  variance across seeds — look at all seeds individually, not the mean.
- Note the last configuration/commit where it worked.

## Step 2 — read the loss curve shape

| Shape | Usual causes |
|---|---|
| flat from step 0 | no gradient reaches the parameters (detached tensor, `requires_grad=False`, frozen by mistake), lr far too small, targets constant/masked out |
| decreases then NaN / spikes | lr too high, exploding recurrent dynamics (gain, spectral radius), log/divide of ~0, missing grad clipping |
| plateau at chance | the task is not learnable from the inputs as fed (timing/mask bug, target misaligned with inputs), loss weights zero for the term that matters |
| decreases, behavior wrong | loss measures something other than the task (wrong mask/window, wrong readout), or eval differs from training (noise, timing, mode) |
| good, then later stage forgets | freezing not effective, regularizer missing, lr too high in the later stage |
| changed after a code edit | regression: diff the configs/defaults, `git bisect` between last good and current |

## Step 3 — measure, don't assume

1. **Data and targets**: plot one batch — inputs, targets and the loss mask over time for each
   condition. Most "training" bugs are here (shifted windows, wrong sign, mask covering the
   wrong epoch).
2. **Gradients**: after `backward()`, per-parameter gradient norms:
   ```python
   sys.path.insert(0, "<this skill dir>/scripts")
   from freeze_check import snapshot, diff_report, grad_norm_table
   grad_norm_table(model)        # None = disconnected, 0 = masked, NON-FINITE = NaN source
   ```
3. **NaN/inf source**: `torch.autograd.set_detect_anomaly(True)` for one step, or forward
   hooks asserting `torch.isfinite` per module; check the input and state magnitude first.
4. **Frozen parameters**: snapshot before the optimizer step, diff after:
   ```python
   before = snapshot(model); opt.step()
   diff_report(model, before, frozen={"m": mask, "W_in": None})   # mask = frozen entries
   ```
   Zeroing gradients does **not** freeze a parameter under AdamW (decoupled weight decay and
   Adam moments still move it). Restore the frozen values after each step or exclude them
   from the optimizer. `python scripts/freeze_check.py --demo` shows the failure and the fix.
5. **Optimizer state**: actual lr per param group at the step (schedulers, warmup), weight
   decay per group, gradient clipping threshold vs typical grad norm, optimizer re-created
   (or not) between stages.
6. **Overfit one batch**: the model must drive the loss near zero on a single fixed batch. If
   it cannot, the bug is in the model/loss, not in optimization or data size.
7. **Regression**: compare the configs (including defaults) of the last good run and the
   current one; `git bisect run <script that exits 1 on failure>` between the two commits.

## Step 4 — fix one thing, re-measure

Change one thing, rerun the small reproduction, compare with the measurement that motivated
the change. Keep the diagnostic (assertion, hook, check) in the code if the bug could come
back. State what was verified and what was not; report per seed.

## Never

- Tune hyperparameters before the data/target plot and the gradient table look right.
- Add a loss term or constraint that forces the desired behavior to "fix" training — that
  hides the bug and invalidates the result.
- Declare it fixed from one lucky seed.

## Checklist (check before reporting; in the reply, one line: "✓ checklist" or the items that failed)
- [ ] reproduced on one seed with an exact command
- [ ] loss-curve shape classified
- [ ] one batch of inputs/targets/mask plotted and checked
- [ ] grad-norm table clean (no None/NaN where unexpected)
- [ ] frozen parameters verified with `diff_report`
- [ ] one-batch overfit passes
- [ ] fix verified on the small case, then on all seeds
