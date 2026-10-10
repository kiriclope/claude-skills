---
name: validating-networks
description: Validate trained low-rank RNNs before their accuracies, flows, wells or trajectories are interpreted — with net_check.py at the project root, per run: did it learn DPA, does dual_dpa hide damage that after_gng/dpa shows, do the logged accuracies reproduce from the checkpoints with the run's own config, did frozen parameters stay frozen, does the net work only at its trained input noise or delay, do the trials end on the wells of the field the verdict scores, and is there a slow or continuous set where isolated-well verdicts fail. Use when a sweep has finished, before flow-verdict, traj-verdict or any figure; before pooling seeds; before any claim about noise, delays, retention or wells; when the user asks "do these nets really work", "is this run trustworthy", "can I compare these arms". Not for scoring the wells against the goal → flow-verdict; for κ(t) behavior → traj-verdict.
---

# Validating networks

A trained network can look right on its own task at its own noise level while it fails
everything else, and an analysis can describe a different object than the one that was
trained. Each check below is a past error that reached a figure or a conclusion.

## Run it first

```bash
$ENV_PREFIX python net_check.py --sweep_dir results/dual/<sweep> [--run_ids …] [--device cuda:0] [--quick]
$ENV_PREFIX python net_check.py --demo    # self-test: analytic slow sets; MISMATCH, FROZEN DRIFT on a perturbed copy
```
`$ENV_PREFIX` = `env_prefix` from `.claude/project.yaml` (an `LD_PRELOAD` libstdc++ shim on some machines;
empty otherwise).
About 40 s per run on a free GPU (`--quick` skips the noise ×2, delay and slow-set probes). Ask
before running it on a whole large sweep while training jobs share the GPUs.

## What each line means and what to do

| Line | Kind | Past failure | What it changes |
|---|---|---|---|
| MISMATCH | FAIL | figures drawn with a 0.5 s cue for a run trained with 1 s; accuracy read at the last step | fix the config or the analysis code until the logged accuracies reproduce; nothing else is read until then |
| FROZEN DRIFT | FAIL | Dual "inputs frozen" left `wi.bias` training (2026-09-21; every sweep before the `_bfix` reruns) | conclusions about the Dual stage of such runs include the drifting bias; rerun or say so |
| NOT LEARNED | FLAG | two seeds that never learned DPA, pooled into Fig. 5, made "the trained wells sit at the optimum" | analyze learners only (after-DPA DPA ≥ 0.95); report the others apart, with their count |
| HIDDEN DAMAGE | FLAG | arms ranked best on dual_dpa ≈ 1 were the worst on after_gng/dpa: Dual retrains rank 0 | lead with after_gng/dpa; dual_dpa never stands alone for retention |
| NOISE-TUNED | FLAG | nets at ×0 or ×1.5 of the trained noise fail DPA (2026-10-01; untied ring8 nets 2026-10-08) | a claim at another noise level needs nets retrained there; measure geometry at the trained noise |
| DELAY-TUNED | FLAG | — (generalization claim) | "holds a memory" means at the trained delay only |
| FIELD≠TRIALS | FLAG | the deterministic and the noise-averaged fields disagree on "all down" (5/8 vs 8/8); wells exist but trials do not sit there | read the wells as the landscape; occupancy comes from trials (traj-verdict) |
| SLOW SET | FLAG | flow_verdict scored 0/4 on an arm holding \|κ₀\| = 1.05 for 5 s: a continuous attractor has no isolated wells | map the slow set, report τ_slow against the delay; isolated-well verdicts do not apply |

Each `·` line gives the numbers behind the verdicts: accuracy at each noise multiple, the delay
probe, the distance of each sample class's end-of-delay state to the nearest well (in trial
s.d.) for the averaged and the deterministic fields, and the length of the slowest region.

## Rules

- **net_check before flow-verdict and traj-verdict**: a FAIL makes their output meaningless; a
  FLAG limits what their output can claim.
- **Seed by seed.** The SUMMARY gives k/N per verdict; never an arm mean that hides a seed.
- **Evaluation-time changes are counterfactuals.** Changing the noise, the delay or a
  parameter of a trained net shows how that net breaks, not what training under those
  conditions would give. Say which one a claim is about.
- **The accuracy calls mirror `sweep.run_single`.** When its `_eval` or `_dual_accuracy` changes,
  update `net_check.py` with it; MISMATCH on a run that used to pass is the signal. What each stage
  froze is read from the run's `train.log` (the config only when the log lacks the stage); a
  `DISAGREE` line means the config rules in `net_check.py` no longer match what training did.
- Record the verdicts as controls in the claims ledger (validating-claims): NOISE-TUNED and
  DELAY-TUNED are `held-out` controls; HIDDEN DAMAGE is a `metric` control.

## Checklist (in the reply: "✓ checklist" or the items that failed)
- [ ] net_check run on every run the claim uses; no FAIL
- [ ] learners only (or the non-learners reported apart)
- [ ] after_gng/dpa next to every dual_dpa
- [ ] noise and delay claims limited to the trained values, or nets retrained there
- [ ] wells read as landscape unless the trials sit on them; slow sets checked before any well count
