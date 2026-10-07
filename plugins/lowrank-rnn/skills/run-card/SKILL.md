---
name: run-card
description: Answer "what exactly did we train?" for a low-rank RNN sweep — per stage (DPA, GNG, Dual-paired, Dual) the loss terms with weights and thresholds, the trial targets and windows, epochs, optimizer, lr, clip, scheduler, stop loss, freezing and symmetry, read from the code that trains them; other runs shown as differences grouped into arms. Use when asked "what loss are we using", "what did we train", "what differs between the arms", "which settings does this sweep use", before interpreting or comparing a sweep, or when writing Methods. Not for scoring the results → use flow-verdict / traj-verdict.
---

# Run card

Before interpreting a sweep, know what it trained. `run_card.py` reads each run's `config.json` and
maps every field to the stage it feeds by **parsing `run_single` in the repo's `sweep.py`** — the
trial generator, the `UnifiedLoss` and the `Optimization` call of each stage — so the card follows the
code instead of a hand-written table that drifts.

## Run it

```bash
python <this skill>/scripts/run_card.py --sweep_dir results/dual/<sweep>            # full card + arms
python <this skill>/scripts/run_card.py --sweep_dir results/dual/<sweep> --diff_only  # arms only
python <this skill>/scripts/run_card.py --sweep_dir … --run_ids s0_a s0_b --baseline s0_a
```
Plain Python, no torch: it reads files, it never trains or imports the model.

## Read it

- **Header:** the `sweep.py` commit the map comes from. A **WARNING** line means the run's
  `config.json` predates fields of today's `RunConfig`: those values are today's defaults and may not
  be what the run used — say so whenever you quote them.
- **SHARED:** fields read outside the stage sites (model, dynamics, init) and the derived dt, α, α_rec
  (from the repo's own `run_dt_alpha`).
- **Per stage:** `header` (epochs, freezing), `trials` (targets, windows, trial types), `loss`
  (every term and weight, e.g. `pair_weight ← dpa_weight`), `train` (optimizer, lr, clip, scheduler,
  stop loss, regularizers, symmetry). "runs only when" lists the switches that skip the stage
  (a checkpoint given, `dual_paired_stage`).
- **NOT PLACED:** functions that receive the whole `config` and could not be read. Their fields may
  belong to any stage — do not assign one.
- **NOT READ by run_single:** inert or legacy fields. A difference in one of them changes nothing.
- **DIFFERENCES:** runs grouped into arms by identical differences from the baseline; each difference
  is tagged with the stages it feeds.

## Use it

1. Run the card before any interpretation or comparison of arms; quote the differences that matter
   ("arm B differs only in `nolick_weight` 1 → 0, Dual loss").
2. When two arms differ in something **NOT READ**, they trained identically — the difference in results
   is seed noise or code change, not the setting.
3. When writing Methods or a reviewer answer, take the values from the card, not from memory or old docs.
4. If the card and a doc disagree, the card (the code) wins; correct the doc.

One line in the reply: the arms and what separates them, or "all runs identical except seed".
