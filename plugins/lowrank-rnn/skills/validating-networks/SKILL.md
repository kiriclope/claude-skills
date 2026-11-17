---
name: validating-networks
description: Validate trained low-rank RNNs before their performance, flows, wells or trajectories are interpreted — with net_check.py at the project root, per run: do the logged P reproduce from the checkpoints with the run's own config, did frozen parameters stay frozen, did each task get learned and stay learned through the later stages, does the net work only at its trained input noise or delay, do the trials end on the wells of the field the flows draw, and is there a slow or continuous set where isolated-well verdicts fail. Use when a sweep has finished, before any flow, trajectory, well count or figure; before pooling seeds; before any claim about noise, delays, retention or wells; when the user asks "do these nets really work", "is this run trustworthy", "can I compare these arms". Not for the numbers a claim quotes → the project's state table (~/rnn: analysis/state_table.py, docs/claims.md).
---

# Validating networks

A trained network can look right on its own task at its own noise level while it fails
everything else, and an analysis can describe a different object than the one that was
trained. Each check below is a past error that reached a figure or a conclusion.

## Run it first

```bash
$ENV_PREFIX $PYTHON net_check.py --sweep_dir results/runs/<sweep> [--run_ids …] [--device cuda:0] [--quick]
```
`$PYTHON`, `$ENV_PREFIX` = `python`, `env_prefix` in `.claude/project.yaml` (`uv run python` in `~/rnn`).
`--quick` skips the noise, delay and slow-set probes; exit 1 on any FAIL. Each line's exact rule and its
thresholds (TOL, DROP, FAR, SLOW_DRIFT, …) are in `net_check.py`'s docstring and constants: quote them from
there. Ask before running it on a whole large sweep while training jobs share the GPUs.

## What each line means and what to do

| Line | Kind | Past failure | What it changes |
|---|---|---|---|
| MISMATCH | FAIL | figures drawn with a 0.5 s cue for a run trained with 1 s; accuracy read at the last step | fix the config or the analysis code until the logged P reproduce; nothing else is read until then |
| FROZEN DRIFT | FAIL | Dual "inputs frozen" left the input bias training (2026-09-21) | conclusions about that stage include the drifting parameter; rerun or say so |
| NOT LEARNED | FLAG | two seeds that never learned DPA, pooled into Fig. 5, made "the trained wells sit at the optimum" | analyze learners only; report the others apart, with their count. Dual is judged on its lowest part (DPA or go/no-go) |
| FORGOTTEN | FLAG | Dual's DPA part ≈ 1 hid a DPA the GNG stage had lost (Dual retrained the SAMPLE rank) | name the stage that lost it; a final P never stands alone for retention |
| NOISE-TUNED | FLAG | nets failed DPA away from their trained noise (2026-10-01; untied ring8 nets 2026-10-08) | a claim at another noise needs nets retrained there; measure geometry at the trained noise |
| DELAY-TUNED | FLAG | — (generalization claim) | "holds a memory" means at the trained delay only |
| FIELD≠TRIALS | FLAG | the deterministic and the noise-averaged fields disagreed on "all down" (5/8 vs 8/8); wells existed but the trials did not sit there | read the wells as the landscape; where the trials sit comes from the trials |
| SLOW SET | FLAG | an arm holding \|κ₀\| = 1.05 for 5 s scored 0/4 on isolated wells: a continuous attractor has none; after GNG, rank-3 SAMPLE wells survive as saddles that hold the sample for seconds | map the slow set, report τ_slow against the delay; no well ≠ no memory |
| UNRECORDED | FLAG | — | no ok record in `results.jsonl`: MISMATCH was not checked; find the run's record before reading anything else |
| UNFINISHED | FLAG | — | a stage has no checkpoint yet: only the stages before it were checked |

Above its FAIL and FLAG lines each run prints the numbers behind them: P of every task after each
stage (with the logged value), P at each noise multiple and at the longer delay, each trial class's
distance to the nearest attractor (in trial s.d.), and the length of the slowest region.

## Rules

- **net_check before any flow, trajectory, well count or figure**: a FAIL makes them meaningless; a
  FLAG limits what they can claim.
- **Seed by seed.** The last line counts the runs with a FAIL; count each FLAG over the runs yourself
  (k/N); never an arm mean that hides a seed.
- **Evaluation-time changes are counterfactuals.** Changing the noise, the delay or a
  parameter of a trained net shows how that net breaks, not what training under those
  conditions would give. Say which one a claim is about.
- **The rescoring is the training's own** (`src.run.score_tasks`, the same trials; each stage's
  freezing from `config.json`). A MISMATCH on a run that used to pass means the scoring or the task
  code changed: find that change before reading anything else.
- Record the verdicts as controls in the claims ledger (validating-claims): NOISE-TUNED and
  DELAY-TUNED are `held-out` controls; FORGOTTEN is a `metric` control.

## Checklist (in the reply: "✓ checklist" or the items that failed)
- [ ] net_check run on every run the claim uses; no FAIL
- [ ] learners only (or the non-learners reported apart)
- [ ] retention read stage by stage (FORGOTTEN), not from the final P alone
- [ ] noise and delay claims limited to the trained values, or nets retrained there
- [ ] wells read as landscape unless the trials sit on them; slow sets checked before any well count
