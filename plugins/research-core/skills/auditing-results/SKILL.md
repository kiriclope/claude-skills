---
name: auditing-results
description: Audit an analysis result BEFORE reporting or interpreting it — unit-by-unit (seed / subject / session) instead of means, all outcomes enumerated not only the occupied one, effect sizes in noise units, nulls and shuffles, matched trial counts and normalizations, pseudoreplication, the right between- vs within-subject estimator, decoder leakage, solver residuals, and an honest finding / assumption / limitation split. Use whenever a sweep, analysis or statistic has just produced numbers, before writing a conclusion ("it works", "it fails", "X increases"), before comparing arms, stages or conditions, or when a result looks too clean or exactly as hypothesized.
---

# Auditing results

A result is reported only after it survives this audit. The two most expensive past errors
were opposite: a working configuration written off because a mean hid it, and an effect that
matched the hypothesis but was produced by trial count or normalization. **The effect that
matches the hypothesis is the one least likely to be audited — audit it hardest.**

Helpers: `scripts/audit_table.py` (`per_unit_table`, `flat_columns`, `matched_n`,
`participation_ratio`; `python audit_table.py --demo` shows each failure mode).

## 1. Unit by unit, never a mean alone

- Print one row per unit (seed, subject, session) with `per_unit_table`, then
  `SUMMARY: k/N pass` against the success criterion written **before** looking (see
  planning-research). The mean is an aside under the table, never the finding.
- In a search (does ANY configuration produce the target?), one unit that works is the
  result; the next question is what distinguishes it from its siblings.
- Representative examples: name the unit shown and say whether it is typical.

## 2. Enumerate all outcomes, not just the observed one

- "Where the attractors/solutions ARE" (landscape) and "where the state SITS" (occupancy) are
  different claims needing different measurements. List every fixed point / cluster / mode,
  then say which are used. A good solution may exist but not be reached — that is a
  transport/basin problem with different levers.
- Select the feature nearest to the observed state, print the distance, flag far matches;
  never select by an extreme (largest, deepest) without checking it is the one used.
- **Check for continuous solutions** (rings, lines, slow manifolds) before trusting a finder
  that looks for isolated points: "no fixed point found" on a continuous attractor is a tool
  failure, not a result. Map the slow set (|F| small on a grid) and look at its shape.
- **Verify every solver output**: residual of each fixed point / root, convergence of each fit.

## 3. Scale effects by the noise

Express positions and differences in units of the relevant noise σ (state noise, across-trial
s.d., across-unit s.d.), and report the fraction of time/trials on each side of a boundary.
An effect of 0.2σ is not a separation, whatever its sign.

## 4. Controls that most often change the answer

| Check | Failure it catches | How |
|---|---|---|
| **Matched n** | statistics that grow with sample size (participation ratio, dimensionality, decoder accuracy, max/min) | `matched_n`: subsample every set to the smallest n, many draws |
| **Normalization** | per-set z-scoring / per-set scaling that fixes the quantity you measure | `flat_columns` on the results table: a near-constant column must be explained |
| **Null / chance** | "above chance" without a null | label shuffle or permutation null, cross-validated; state the chance level and the CI |
| **Leakage** | decoders trained and tested on overlapping trials (resampled from one pool) | disjoint train/test folds; suspicious diagonal ⇒ suspect leakage first |
| **Pseudoreplication** | trials treated as independent when the claim is about subjects | aggregate per subject, or a mixed model with the right random effects |
| **Estimator vs claim** | a random intercept absorbs exactly the between-subject variance a between-subject claim needs | between-subject claim ⇒ per-subject statistics; within-subject claim ⇒ paired/differenced |
| **Metric dependence** | significant under one normalization/metric only | report the result under the 2–3 reasonable metrics; say if it flips |
| **Confounds between arms** | arms differing in more than the lever (RNG stream, early stopping, noise level, checkpoint) | list everything that differs besides the variable; match or name it |
| **Circular readouts** | a readout that is the trained target by construction | compare conditions at a fixed stage, not stages that train the readout |
| **Counterfactual vs retraining** | a fixed-weights ablation read as what learning would do | say which one the claim is about |

Before comparing sets, write the list "what differs between these sets besides the variable of
interest" (counts, conditions, units, scaling, preprocessing) and neutralize each item, or add a
design-matched control set.

## 5. Make sure the analysis describes the right object

- Every option that changes the task or the dynamics must reach the analysis/plotting code; load
  configs with the same defaults as training. Spot-check one unit end to end (re-simulate, compare
  to the logged accuracy).
- Gauge/scale choices: do not normalize away a quantity the loss or the data anchor.

## 6. Write the verdict honestly

For each claim, label it:
- **data finding** — survives the controls above;
- **imposed assumption** — follows from a modeling or analysis choice (say which);
- **limitation** — the method cannot answer it (say what would).

Say plainly when something did not work and why. If the result contradicts an earlier
conclusion in the docs, mark the old one superseded there.

## Checklist (copy into the reply and tick)

- [ ] per-unit table + `SUMMARY: k/N`, criterion fixed in advance
- [ ] all outcomes enumerated (not only the occupied one); continuous sets checked; residuals verified
- [ ] effects in noise units
- [ ] null/chance level stated; no train/test leakage
- [ ] matched n and normalization checked (`matched_n`, `flat_columns`)
- [ ] unit of replication = unit of the claim; estimator matches between/within claim
- [ ] arm confounds listed and matched
- [ ] each claim labeled finding / assumption / limitation
