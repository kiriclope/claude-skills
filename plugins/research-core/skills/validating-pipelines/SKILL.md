---
name: validating-pipelines
description: Check that an analysis pipeline recovers ground truth before its result on real data is believed — plant an effect of known size (and none) in synthetic data shaped like the real data, run the real pipeline, and score offset (the measure's zero is elsewhere), shrinkage or inflation (a normalization removes the effect), sign, false positives (pseudoreplication, leakage), interval coverage and the smallest detectable effect with recovery_check.py; pin a paper's numbers and flag those that moved after a code change with pin_numbers.py. Use when a new measure or pipeline is about to give its first result, when its zero, sign or scale is assumed, before claiming that something does not change, after editing analysis code that feeds the paper, or when the user asks "does this analysis actually work", "sanity-check the pipeline", "did the numbers change". Not for decoder leakage → validating-decoders; for auditing a result → auditing-results.
---

# Validating pipelines

A pipeline that has never been shown a known answer cannot be trusted with an unknown one.
Every measure has a zero, a sign and a scale. Usually they are assumed, and the assumption
fails silently: a distance between noisy means is positive with no effect at all, z-scoring
each condition removes the difference you measure, and pooled trials make every null
"significant".

## Rules

- **Run the real pipeline code, not a re-implementation.** The adapter calls the same functions
  that make the figure.
- **Shape the synthetic data like the real data**: the same number of units, trials, sessions and
  time bins; the same noise level and the same nuisance structure (licks, sessions, drift), taken
  from the data. Plant the effect where the hypothesis puts it, and nowhere else.
- **Always include effect 0.** The null run checks the zero (OFFSET) and the false-positive rate.
- **A FAIL is fixed in the pipeline, or the claim is restricted**: say which. Never tune the
  synthetic data until the pipeline passes.
- **A null-result claim needs the detectable effect**: "no change" means "no change larger than
  the smallest effect this pipeline detects with power 0.8" (the DETECTABLE line). Record it as
  the claim's `positive` control in the claims ledger (validating-claims).
- Re-run after any edit to the pipeline, and pin the paper's numbers (below) so a silent change
  shows up.

## Workflow

1. **Write the adapter** next to the analysis (e.g. `analysis/recovery_<measure>.py`):
   ```python
   import numpy as np
   from analysis.measures import score              # the real pipeline function
   EFFECTS = [0, 0.05, 0.1, 0.2]                   # planted sizes, in the measure's units
   def truth(effect): return effect                # what the measure should read (omit if unknown;
   # NULL_VALUE = 0.5                              #  then give the no-effect value, e.g. chance accuracy)
   def simulate(effect, rng):                      # n neurons, trials, bins, noise as in the real data
       ...
       return data
   def estimate(data):
       return {"value": score(data), "p": ..., "ci": (lo, hi)}   # p and a 95% ci optional
   ```
2. **Run it from the project root**, so the adapter can import the project's code:
   ```bash
   python <this skill>/scripts/recovery_check.py --adapter analysis/recovery_<measure>.py --reps 50
   ```
   One row per planted effect (mean, bias, s.d., detection rate, coverage), then the verdicts:
   OFFSET, SHRINKAGE, INFLATION, SIGN FLIP, NOT MONOTONE, FALSE POSITIVES, UNDERCOVERAGE, and the
   DETECTABLE line. `--demo` shows one sound pipeline and three classic flaws.
3. **Act on each verdict**:

   | Verdict | Usual cause | Fix |
   |---|---|---|
   | OFFSET | the measure is biased at zero (norms, max over units, a baseline shared by conditions) | subtract the null estimate (shuffle or split-half), or compare against the null distribution |
   | SHRINKAGE / INFLATION | per-condition normalization, regularization, a ratio of noisy terms | normalize across conditions jointly; report the recovered fraction |
   | SIGN FLIP | an axis or a difference taken the wrong way round | fix the convention, then re-check every figure that uses it |
   | FALSE POSITIVES | trials or bins treated as independent; train/test overlap | test at the unit of the claim (choosing-statistics); disjoint folds |
   | UNDERCOVERAGE | the CI ignores a variance component, or is not a 95% interval (mean ± s.e.m. is 68%) | bootstrap over the unit of replication |
   | NON-FINITE ESTIMATE | a fit failed and returned nan or inf | fix the pipeline; nothing else is judged until every run returns a number |

4. **Pin the paper's numbers** once they have been reviewed, and check them after every code change:
   ```bash
   python <this skill>/scripts/pin_numbers.py --pin   --log <numbers_log> --snapshot <numbers_log>.pinned.json
   python <this skill>/scripts/pin_numbers.py --check --log <numbers_log> --snapshot <numbers_log>.pinned.json
   ```
   CHANGED or GONE numbers are explained before the text is touched (auditing-paper-numbers), and
   re-pinned only after the user accepts them.
5. **Report** the recovery table and verdicts, what was fixed or which claim was restricted, and
   the detectable effect for any null result.

## Checklist (in the reply: "✓ checklist" or the items that failed)
- [ ] the adapter runs the real pipeline on data shaped like the real data
- [ ] effect 0 included: no OFFSET, no FALSE POSITIVES
- [ ] slope ≈ 1 where the truth is known; no SIGN FLIP
- [ ] the detectable effect stated for every null-result claim
- [ ] the paper's numbers pinned; `--check` clean or each change accepted by the user
