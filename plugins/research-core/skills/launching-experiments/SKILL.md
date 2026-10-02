---
name: launching-experiments
description: Launch, monitor and finish training sweeps and long-running experiments safely — parameter confirmation, pilot run, one detached screen and one log per seed, concurrency caps, readable run names, provenance (git hash, config, seed) in every run directory, resume-safe relaunch, and the post-run verdicts and figures. Use when asked to launch/run/start/resume a sweep, a grid, seeds, or any multi-hour job; when editing a sweep config before launch; when checking on running jobs; or when runs finish and results need reporting.
---

# Launching experiments

A launch is cheap to start and expensive to get wrong: a wrong parameter costs hours of GPU
time and, worse, results that look valid. The rules below come from repeated real failures
(wrong config launched, 16 runs at once slowing everything, unreadable run names, results
reported without figures).

## Step 0 — project facts

`cat .claude/project.yaml` → `launch:` (sweep entrypoint, results root, max concurrent runs,
GPUs, workers per GPU, screen prefix), `env_prefix`, `python`. Read the project's running doc
(`docs/running.md` or as `CLAUDE.md` says). Project rules override the defaults here.

## Step 1 — the plan, shown and confirmed (never skip)

Before launching, show the user a table and **wait for an explicit go**:

```
sweep name     <short_lowercase_tokens>       e.g. lif_sub_cue_nolick_nogo
arms           arm → the ONE lever it changes vs the baseline arm
seeds          exploring: 4 · definitive: 8   (say which mode)
fixed params   everything else, with values (diff vs the baseline config, not the full dump)
runs           n_arms × n_seeds = N  → batches of ≤ max_concurrent
cost           est. wall clock per batch, GPUs used
success        what result counts as success (see planning-research)
outputs        verdict scripts + figures that will be produced
```

Names: short, lowercase, underscore-separated, tokens that say what the arm adds, readable
run ids (`s3_cue_nolick`, not `s3_k1zcnl`). The name is how results are found in a gallery of
dozens of folders.

## Step 2 — pilot

Run **one seed for a few steps through the whole pipeline** (train → save → verdict script →
one figure) before the grid. Most failed sweeps fail at loading/analysis, not at training.
Check: loss decreases, checkpoint written, provenance written, analysis script reads it.

## Step 3 — launch (detached, one screen + one log per seed)

- Never run a sweep in the foreground or as a harness background task (killed on memory
  pressure); use detached `screen` (or the project's scheduler).
- **One screen per seed/run**, named `<prefix>_<run_id>`, round-robin over GPUs; each tees to its
  **own** `<run_dir>/train.log` with an **absolute** path (inner commands may `cd`):
  ```bash
  screen -dmS sweep_<run_id> bash -c "cd <repo> && <env_prefix> python <entry> <args> \
      2>&1 | tee /abs/path/<run_dir>/train.log"
  ```
- **Cap concurrency** (`launch.max_concurrent`; small models are often launch-bound and gain
  nothing past ~8 processes). Bigger grids go in batches: launch, wait, launch the next.
- Every run directory gets the full config, the seed and **provenance** at start:
  ```python
  sys.path.insert(0, "<this skill dir>/scripts")
  from record_provenance import record_provenance
  record_provenance(run_dir, repo=".", config=asdict(cfg), seed=cfg.seed)   # git hash, dirty diff, env
  ```
  (`python scripts/record_provenance.py --demo` to see it.) If the tree is dirty, the diff is
  saved next to it — say so to the user, or commit first.
- Relaunch must be a **resume**: skip runs whose final checkpoint exists.

## Step 4 — monitor

`screen -ls` · `tail -f <run_dir>/train.log` · `screen -r <name>` · kill one:
`screen -S <name> -X quit`. When waiting, arm a monitor on *both* completion and failure
(`Traceback`, `Killed`, `nan`, screen vanished with no checkpoint) — silence must not read as
success. Report failures immediately with the log tail.

## Step 5 — finish (a sweep is not done until this is done)

1. Check every run finished (count checkpoints vs planned runs; list missing/failed ones).
2. Run the project's **verdict/scoring scripts**, unit by unit (per seed), against the success
   line written in Step 1.
3. **Make the figures** (project plotting entrypoint, detached if slow) and show/publish them.
   Never report numbers without the figures.
4. Log it (log-and-ship): config, result per seed, verdict, next step.

## Checklist (copy into the reply)

- [ ] plan table shown; user said go
- [ ] pilot passed end to end
- [ ] one screen + one absolute-path log per seed; ≤ max concurrent
- [ ] config + seed + provenance in every run dir
- [ ] monitor armed for completion and failure
- [ ] all runs accounted for; verdicts run per seed
- [ ] figures made and shown; logged
