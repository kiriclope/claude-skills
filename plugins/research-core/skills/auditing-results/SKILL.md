---
name: auditing-results
description: Audit an analysis result BEFORE reporting or interpreting it — unit-by-unit (seed / subject / session) instead of means, all outcomes enumerated not only the occupied one, effect sizes in noise units, nulls and shuffles, matched trial counts and normalizations, pseudoreplication, the right between- vs within-subject estimator, decoder leakage, solver residuals, and an honest finding / assumption / limitation split. Use whenever a sweep, analysis or statistic has just produced numbers, before writing a conclusion ("it works", "it fails", "X increases") or answering a question about a result in chat ("is it gone", "did it learn"), before comparing arms, stages or conditions, or when a result looks too clean or exactly as hypothesized. Not for choosing the test → choosing-statistics; for an independent check of a conclusion → thinking-critically.
---

# Auditing results

A result is reported only after it survives this audit. The two most expensive past errors
were opposite: a working configuration written off because a mean hid it, and an effect that
matched the hypothesis but was produced by trial count or normalization. **The effect that
matches the hypothesis is the one least likely to be audited — audit it hardest.**

**Who runs it:** the audit agent (`result-checker`) when one is assigned — give it the question, the
criterion and the evidence (advising-research, CHECK handoff); otherwise the main session.
- **When you are the checker** (read-only, no agents): run §1–§6 and return the per-unit table, the
  verdict in the §0 words with why, and the objections ranked. Do not write the card, save files, make
  the figure or run the clarity check — you cannot.
- **The main session** then writes the card (§0), makes the figure, saves the table, runs the clarity
  check and §7, and reports.

## Every claim carries its measurement — chat replies too

Most wrong reports come from quick answers in chat, not from the verdict entries a fresh agent
checks. Every statement about a result, in an entry, a doc or a one-line reply, follows these rules:
- **Conditions:** name the unit (run, seed, subject) and its state (stage, checkpoint), the trials
  (task, condition, trial kind), the time window and the metric. Use the window and metric the task
  itself scores, not the end of the trial or a feature of a figure.
- **Denominator:** k/N with the units named. A statement about the units that did X is not a
  statement about the model.
- **Numbers come from a computation in this session** (a script's printed output, or the project's
  claims table: `project.yaml` → `claims_doc` names the measurement and trap for each claim). Never
  read a number by eye off a figure, and never take one from a compaction summary or a memory note
  without re-measuring. Anything else is labeled "unchecked".
- **Name a proxy as a proxy.** A finder's "no isolated fixed point" is not "no memory" (§2,
  continuous and slow sets). A loss is not a performance. A logged field is whatever its code
  computes: read the code before relaying the field.
- **A negative ("gone", "lost", "doesn't exist") needs the direct test**, or a search of every place
  the thing could be. Otherwise write "not found in <where>".
- **When the user reads a figure differently, measure first**, then answer.
- **An interpretation that would change the next run** (a lever chosen or dropped, a mechanism)
  goes through the fresh review of §7 before it is sent. A reply that only describes results does not.

**Why:** in one project session (2026-11-03), seven wrong reports, six of them in chat:
- wells called "gone" while the memory sat on a slow set;
- a latent read off a figure at the trial end instead of the scored window;
- the units that learned one task stated as the model;
- a loss read as a stage failing;
- a logged score that held only one part of the task;
- a claim with no network named;
- a file called "missing" after a search of two of five worktrees.

## 0. No verdict without its figure and its table — kept OR discarded

Every verdict (solved, works, fails, discarded, superseded, "not worth pursuing") ships with
a verdict entry, the figure that shows the effect, and the per-unit table of the tests. This applies to quick exploratory dead ends
too, where one hypothesis and one small figure are enough, and above all in auto mode.
**Why:** in auto mode, results were solved or dropped in one line of text. The user could
not see why, and could not catch a wrong discard (see §1: a working seed written off by a
mean). A discard without a figure cannot be reviewed. And a card whose numbers sat in one
paragraph and whose figure was laid out by arm, not by argument, left the user to connect
them (2026-10-29). Figures drawn as the test tally (one derived number per unit, pass/fail markers,
count-sentence titles) were cryptic to the user in every project (2026-11-03).

**Write the entry from `references/verdict_card.md`** (template and rules; read it every time you
write or check a card). In short:
- **An argument, one hypothesis at a time**, under the run's pre-run card when there is one (planning-research
  Step 1: replace RUNNING with the verdict, leave the card's lines unchanged). Each hypothesis: what it
  predicts if true and if false; each test with its criterion, noise floor, k/N [95% interval] and rivals;
  a conclusion in the calibrated words **supported / not supported / refuted / open**.
- **In the chat: the figure first, then the whole entry.** The figure shows the effect (designed from the
  making-figures brief), the per-unit table (`<figure>_table.md`) holds the tests; every count comes from it.
- **≤ 40 lines**, for a reader who did not follow the session; independent units only.
- **Clarity check** by a fresh agent (PNG, entry, table only) before reporting; then the entry goes into
  the verdict log **at the top, newest first**. A correction is a new card; at 5+ cards since the question's
  conclusions section, run concluding-research next.
- No figure possible (a crash, a missing file)? Say so in the figure slot, with the log line.

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

When a check needs more than a table, run the validation script built for it:

| Concern | Skill · script |
|---|---|
| a decoder's null, leakage, class balance, nuisance, held-out sessions | validating-decoders · `decoder_check.py` |
| a measure's zero, sign, scale, false-positive rate; the detectable effect behind a null result | validating-pipelines · `recovery_check.py` |
| trained low-rank RNNs: accuracies reproduce, frozen stayed frozen, trained noise and delay only | validating-networks · `net_check.py` |
| the controls a claim still lacks before it goes into a draft | validating-claims · `claims_ledger.py` |

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
conclusion in the docs, mark the old one superseded there (one line, §0).

## 7. Independent review before the verdict is reported

When the verdict will be reported, written into a doc or the paper, or acted on (a new sweep, a
decision), invoke the **thinking-critically** skill and run its steps 3–4: a fresh agent — not a
fork — gets the question, the criterion fixed in advance, the per-unit table and the numbered
claims with their labels, never your reasoning; check each of its objections before accepting
it. Skip it for exploratory looks (a review costs ~5–10 min).

## Checklist (check before reporting; in the reply, one line: "✓ checklist" or the items that failed)
- [ ] verdict entry (plan → predictions → tests with noise floor and rivals → calibrated conclusions → next) + its designed figure (the effect) + the per-unit table, clarity-checked, in the reply and the verdict log (discards included)
- [ ] per-unit table + `SUMMARY: k/N`, criterion fixed in advance
- [ ] all outcomes enumerated (not only the occupied one); continuous sets checked; residuals verified
- [ ] effects in noise units
- [ ] null/chance level stated; no train/test leakage
- [ ] matched n and normalization checked (`matched_n`, `flat_columns`)
- [ ] unit of replication = unit of the claim; estimator matches between/within claim
- [ ] arm confounds listed and matched
- [ ] each claim labeled finding / assumption / limitation
- [ ] every claim in the reply, chat included: unit and state, trials, window, metric, k/N; numbers computed this session; proxies named; negatives directly tested
- [ ] a verdict that will be reported was reviewed by a fresh agent (thinking-critically), objections triaged
