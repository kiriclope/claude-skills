---
name: validating-decoders
description: Validate a decoding or classification pipeline on neural data before its accuracy is believed — run the real pipeline on shuffled labels (the null, built exactly like the score), on pure-noise data (must sit at chance, else labels leak through preprocessing, feature selection, tuning or resampled pseudo-trials), on imbalanced noise (a metric that rewards the majority class), on nuisance-matched trials (licks, running, session: is the decoder reading the nuisance?), at fewer trials, and across held-out sessions or animals, with decoder_check.py. Use when a decoder, cross-temporal generalization matrix, axis projection, dPCA or CCGP result is about to be reported or plotted, when accuracy looks too high or appears before the variable exists, when the user asks "is this above chance", "is there leakage", "is it just licks", "does it generalize across sessions". Not for statistics across animals → choosing-statistics; for any other analysis's ground truth → validating-pipelines.
---

# Validating decoders

Decoders fail in a few ways, and every one of them makes the score look better: train and test
trials that overlap; preprocessing, feature selection or the regularization strength chosen on
all trials; a null built differently from the score; a metric that rewards the majority class; a
label that equals a nuisance on the selected trials. None of this shows on the plot. Each one
shows on inputs whose answer is known.

## Rules

- **Probe the real pipeline**: the adapter's `evaluate()` calls the same code that makes the
  figure, including its cross-validation, averaging over splits and trial selection.
- **The null goes through the identical pipeline**: same folds, same averaging, same trial set.
  A null of single-split accuracies against a bar that averages 15 splits puts chance far too high.
- **Pure noise must decode at chance.** If it does not, the leak is in the pipeline, whatever
  the real score.
- **Nothing fitted on a trial may score that trial**: axes, weights, PCA or dPCA bases, scalers
  and selected features are fitted on training folds only. Projecting trials onto an axis
  trained on them, or onto fold-averaged weights, is self-inclusion.
- **Resampling respects the unit.** Pseudo-trials are drawn within folds, never before the
  split. A bootstrap over animals or sessions refits the decoder on every draw.
- **Trial selection can create the label.** On correct trials, lick ≡ match: a "choice"
  decoder there may read the trial type. Decode on all trials, or match the nuisance.
- **The variable cannot be decoded before it exists.** Bins before the stimulus are a free
  negative control: decoding there must sit at chance.
- **Pooled pseudo-populations score higher than single animals.** Pair every pooled claim
  with its per-animal value.

## Workflow

1. **Write the adapter** next to the analysis (e.g. `analysis/decoder_adapter_<variable>.py`):
   ```python
   import numpy as np
   from analysis.decode import decode_score, fit_decoder, score_decoder   # the real pipeline
   CHANCE = 0.5                                     # for this metric
   def load():                                      # one animal × stage, or the pooled set the claim uses
       X, y, session, licks = ...                   # X: trials × neurons [× time bins]
       return {"X": X, "y": y, "groups": session, "nuisance": {"lick": licks}}
   def evaluate(X, y, groups, rng):                 # the figure's score, its own cross-validation inside
       return decode_score(X, y, groups, rng=rng)
   def evaluate_across(X_train, y_train, X_test, y_test):   # optional: held-out sessions / animals
       return score_decoder(fit_decoder(X_train, y_train), X_test, y_test)
   ```
2. **Run it** (each probe calls `evaluate()`; the first line tells how long one call takes):
   ```bash
   python <this skill>/scripts/decoder_check.py --adapter analysis/decoder_adapter_<variable>.py --perms 50
   ```
3. **Read the verdicts**:

   | Verdict | Meaning | Fix |
   |---|---|---|
   | LEAKAGE | noise decodes above chance | move every fitted step inside the folds; resample within folds; no self-projection |
   | CHANCE MISPLACED | the shuffle null is not where you think chance is | if LEAKAGE, fix that first; else the metric or the class balance: state the null's value as chance |
   | METRIC UNBALANCED | imbalanced classes score above chance on noise | balanced accuracy or AUC, or subsample to equal classes |
   | CONFOUNDED | after matching the nuisance across classes the score falls into the null | the claim is about the nuisance; restrict the trial set or add the nuisance as a covariate |
   | NOT ABOVE NULL | no evidence of decoding | report it as such; check the detectable effect (validating-pipelines) before calling it absent |
   | N-DEPENDENCE | the score changes with trial count | compare conditions, stages or animals at matched n |
   | HELD-OUT GROUPS | generalization to unseen sessions or animals | what a "generalizes" claim needs (validating-claims) |

4. **Record** each probe as a control of the claim it supports in the claims ledger
   (validating-claims): shuffle → `null`, nuisance matching → `confound`, held-out groups →
   `held-out`, pre-stimulus bins → `null`.
5. **Report** the real score against the null (mean, 95th percentile, p), each verdict, and what
   changed in the pipeline.

## Checklist (in the reply: "✓ checklist" or the items that failed)
- [ ] null built by the identical pipeline (folds, averaging, trial set)
- [ ] pure noise at chance: no LEAKAGE
- [ ] class balance: no METRIC UNBALANCED
- [ ] each plausible nuisance matched: not CONFOUNDED
- [ ] comparisons at matched n; pooled claims paired with per-animal values
- [ ] pre-stimulus bins at chance for a time-resolved decoder
