# Failure modes a reviewer looks for

Each one has produced a wrong conclusion in real projects. Hint → what to check.

## Evidence

1. **The aggregate hides the unit.** An arm mean "fails" while one seed is a perfect success (or the
   reverse). → Re-read the per-unit table (seed / subject / session); count k/N against the criterion.
2. **Only the occupied state was examined.** Reporting the attractor the network sits in, not all of
   them. → Enumerate every fixed point / outcome / cluster, not the visited one.
3. **Selection.** Shown seeds, sessions, cells or conditions are the good ones. → Ask for all of them
   and the rule that selected these.
4. **Read, not run.** A claim about what code or a preprocessing step does, inferred from reading it.
   → Run it on real data and print the shape, values or counts.
5. **Eyeballed figure.** A geometric or visual claim not scored by the project's verdict tool. →
   Run the tool; the figure may show a different field, window or condition than the claim uses.

## Comparisons

6. **Sample-size and normalization artifacts.** A statistic that grows with n (participation ratio,
   decoding accuracy, variance explained) compared across sets of different size; a per-set
   z-score that makes the measured quantity constant (a flat column in a table is the tell). →
   Subsample to matched n; check what the normalization fixes.
7. **Mismatched comparison.** Different time windows, fields (deterministic vs noise-averaged),
   conditions, stages or boundaries across the two sides. → Line the definitions up side by side.
8. **Missing null or control.** An effect without its shuffle, its baseline, or the matched
   control arm. → Name the null that would produce the same number.
9. **Effect without its size in noise units.** "Below the line" by 0.01 when trial-to-trial σ is 0.2.
   → Express it in σ or against the null distribution.

## Inference

10. **Moved criterion.** The conclusion uses a rule that is not the one written in the plan. →
    Apply the original rule; report both if the change is justified.
11. **Confirmation.** The result matches the hypothesis exactly and was audited least. → Audit
    the confirming results as hard as the disconfirming ones.
12. **Circularity.** The quantity tested was trained, selected or fitted on the same data. →
    Held-out data, or a prediction made before the fit.
13. **Overgeneralization.** One seed, one task, one parameter value, one dataset → "networks do X".
    → State the tested range; what was not tested.
14. **Numerical trust.** A solver root, eigenvalue, fit or optimum used without its residual or
    convergence check. → Report the residual.
15. **Stale knowledge.** A fact from memory, notes or an old run that no longer holds. → Re-read
    the current source; dated facts older than the last code change are suspect.

## Literature

16. **Hallucinated or misattributed citation.** The paper does not exist, or does not say that,
    or says it under conditions that do not apply. → Find it, quote the passage, check conditions.
17. **Uncited contradiction.** A known result disagrees and is not mentioned. → Search for it
    explicitly ("X contradicts", "fails to replicate", competing models).

## Test cases (for evaluating this skill)

- **A. Hidden success.** Conclusion "the memory wells do not go below the line in arm X: mean
  occupied-attractor κ₁ = +0.088 over 4 seeds", with a per-seed table in which seed 0 has both
  memory wells at κ₁ ≈ −1.5 and −1.25. Expected: CONTRADICTED (failure modes 1, 2, 10).
- **B. Misattributed citation.** "Consistent with Mastrogiuseppe & Ostojic (2018, Neuron), who
  showed that rank-2 networks cannot hold two independent memories." Expected: UNSUPPORTED or
  CONTRADICTED by the source (16).
- **C. Size artifact.** "Dimensionality grows from DPA to dual (participation ratio 37 → 49,
  p = .004)" where dual sets hold about twice the trials. Expected: WEAKER THAN STATED until
  matched-n subsampling (6).
- **D. Read, not run.** "The preprocessing subtracts a per-trial baseline", stated from reading
  the code. Expected: UNVERIFIABLE until run (4).
- **E. Plausible but imprecise.** "Low-rank RNN dynamics reduce to a latent system whose dimension
  equals the rank." Expected: WEAKER THAN STATED: with inputs it is R + N_in (Dubreuil et al. 2022),
  and a two-filter model doubles it. (A reviewer caught this in the first test run although the
  test's author had written it as a true control claim.)

First test run (2026-10-06, cases A + B + E plus two control claims): the fresh reviewer
contradicted A, found B unsupported with the source quoted, caught E, and confirmed both controls.
Spot-check of its citations: sources real, the key quote verbatim, two full-text quotes unverifiable.
