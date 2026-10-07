---
name: choosing-statistics
description: Choose the statistical test from the design before any result is seen — unit of replication, pairing, nesting (mixed model or GEE with the random effects the claim needs), exact small-n tests and the smallest p they can reach, sidedness and multiple-comparison correction declared up front — then report that test whatever it gives. Use when a comparison, p-value or significance star is about to be computed, or the user asks "which test", "is it significant", "a less conservative test", "can we get a star", or two tests disagree. Not for auditing a finished result → use auditing-results.
---

# Choosing statistics

The test is part of the question, not of the answer. Choosing it after seeing p — switching to
"a less conservative test", a one-sided test, a trial-level model, the variant that gives a star —
turns a p-value into a search result. Three failures this prevents:

- **Test shopping.** "Change the panel to a t-test — that will boost the stats." The pre-chosen test
  is reported; anything else is a labeled secondary.
- **Pseudoreplication.** A trial-level mixed model with only a random intercept gave p = .004 for a
  within-animal effect; with the random slope the claim needs, p = .17.
- **Small-n floors.** At n = 9 the signed-rank test cannot go below p = .0039, and three small
  differences of the other sign put it at .055 whatever the effect size; a sign test at n = 6 needs
  6 of 6 units; a 100-draw permutation null cannot resolve a margin of 0.01.

## Step 1 — the design card (before computing anything)

```
QUESTION     the comparison in one sentence: what differs from what, in which units
UNIT         the unit of replication = the unit the claim is about (animal, session, network seed); n counts these
PAIRING      paired (same units in both conditions) or independent
NESTING      e.g. trials within sessions within animals → which random effects (intercept AND the slope of the tested effect)
TEST         the primary test (Step 2); two-sided unless the direction was predicted in writing before the data
FAMILY       how many tests answer this question, and the correction (Holm by default)
CRITERION    α after correction; effect size and 95% CI reported whatever p is
FLOOR        python scripts/stats_floor.py --n <n> (or --n1/--n2, --perm) — if the floor is above α, the design cannot answer; say so now
```

Write the card where the analysis is recorded (docs, notebook, commit message) before running it.

## Step 2 — pick the test

| design | primary test | report |
|---|---|---|
| two conditions, same units, differences roughly normal, n ≳ 15 | paired t | mean Δ, 95% CI with the t quantile (t₈ = 2.31 at n = 9, not 1.96), dz |
| same, small n or skewed differences | Wilcoxon signed-rank, or exact sign-flip permutation of the mean Δ | median Δ, CI, the floor |
| only the direction is meaningful | sign test | k/n units in the predicted direction |
| two independent groups | Welch t, or Mann-Whitney / exact label permutation at small n | difference, CI, Hedges g or rank-biserial r |
| trials nested in animals, effect within animal | mixed model with random intercept **and random slope** for the effect, or per-animal summaries + a paired test | fixed effect, CI, n animals and n observations |
| binary trial outcomes nested in animals | GEE (exchangeable) or a logistic mixed model with random slopes | odds ratio, CI |
| animals treated as fixed (within-animal claim) | permutation with labels shuffled within each animal | disclose the across-animal test beside it |
| association across units | Pearson / Spearman on per-unit values, n = units | r, CI |
| "a change predicts a change" | partial correlation / regression on the baseline | the baseline-adjusted estimate (change scores regress to the mean) |
| many cells, panels or windows | one omnibus model, or the family corrected | corrected p for every cell, not only the starred ones |

Permutation nulls: ≥ 1000 draws when a p near α matters, with a fixed seed recorded.

## Step 3 — report the pre-chosen test

- Report the primary test whatever it gives: statistic, df or n (with its unit), p, effect size, CI.
- A secondary test only if the design card named it and why (robustness, a check of assumptions),
  always labeled secondary and shown next to the primary — never instead of it.
- If two tests disagree, report the pre-chosen one and explain the disagreement (floor, a few sign
  flips, an outlier, a ceiling). Do not swap.
- Stars follow the primary test of the canonical analysis only — never a variant, a knob setting,
  or a single favorable window.
- When the request is to make a result significant ("less conservative", "boost the stats"), say
  plainly that this is test shopping, report the pre-chosen test, and offer what would legitimately
  add power (more units, a pre-registered direction, a better-matched design).

When the result will be reported or acted on, hand the design card and the result to
**thinking-critically** (steps 3–4): the fresh reviewer checks the card against what was run.

## Never

- Choose or switch the test, the sidedness, the unit or the correction after seeing p.
- Count trials when the claim is about animals.
- Drop the correction because the analysis is "exploratory" without saying so in the text.
- Report only the variant that reached significance.

Checklist (report as one line: "✓ stats" or the failed items): card written before running · unit =
claim's unit · random slopes where nested · floor checked · family corrected · primary reported first ·
effect size + CI · stars from the primary test only.
