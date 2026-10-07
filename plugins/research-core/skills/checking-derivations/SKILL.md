---
name: checking-derivations
description: Derive and verify math for models and theory — Jacobians, fixed-point conditions, stability/bifurcation criteria, mean-field reductions, closed-form predictions, proofs in a theory note. Use when deriving or editing an equation, writing a derivation into docs or a paper, claiming "analytically, X = …", when a formula and a simulation disagree, or BEFORE building figures or arguments on a formula. Derive symbolically (sympy), state assumptions, then check numerically against the real model code with scripts/check_jacobian.py. Not for statistics → choosing-statistics.
---

# Checking derivations

A derivation is trusted only after it has been **checked against the code that runs the model**.
Hand algebra fails quietly: a lost chain-rule factor (a gain, a time step), a transpose, a
1/N, a sign. The model code is the ground truth because the figures come from it.

## Workflow

1. **State the object and the assumptions** before deriving: variables and shapes, which
   parameters are fixed, limits taken (N → ∞, small noise, slow input), what is neglected.
   Write them at the top of the derivation in the doc.
2. **Read the model code** that implements the dynamics (update rule, scalings, where gains,
   time constants and normalizations enter). Derive from *that*, not from memory of the
   paper equation — they often differ by a scale or a discretization.
3. **Derive symbolically** with sympy where possible (`sympy.diff`, `simplify`, `solve`,
   `series`), and print the result; keep the script next to the doc
   (`scripts/derive_<topic>.py` in the project) so it can be re-run.
4. **Check numerically against the real model**:
   ```python
   sys.path.insert(0, "<this skill dir>/scripts")
   from check_jacobian import compare_jacobian, finite_diff_check
   compare_jacobian(F, x0, J_analytic(x0))      # autograd of the code's own function
   finite_diff_check(F, x0, J_analytic(x0))     # independent of autograd
   ```
   `F` must call the project's model code (or a one-line wrapper around it), in float64, at
   **several** points: the origin, a generic point, and the regime the claim is about.
   `python scripts/check_jacobian.py --demo` shows the pattern on a low-rank tanh RNN.
5. **Check the prediction, not only the formula**: simulate the model and compare the
   predicted quantity (fixed point location, eigenvalue, bifurcation point, decay time) with
   the measured one, with residuals. Fixed points: report ‖F(x*)‖.
6. Write the derivation up only after steps 4–5 pass; quote the check (max rel. error,
   simulated vs predicted) in the doc.

## Sanity checks for any result (and for proofs)

- **Dimensions / units**: every term in a sum has the same units; rates vs times; per-step vs
  per-second (dt, α = dt/τ).
- **Limiting cases**: gain → 0, N → 1 or ∞, zero input, linear regime (tanh x ≈ x), rank 1;
  the result must reduce to the known answer.
- **Symmetries**: if the model is invariant under a transformation (sign flip, permutation,
  rotation), the result must be too; an odd function gives a fixed point at 0, etc.
- **Special values**: plug in numbers where the answer is obvious.
- **Small-N simulation**: for population / mean-field results, simulate finite N and check the
  error shrinks as N grows (∝ 1/√N for random-connectivity averages).
- **Proof steps**: name the theorem used at each nontrivial step and check its hypotheses hold
  (smoothness, compactness, genericity, invertibility). A step that "clearly" follows is the one
  to check. Try to break the claim with a counterexample before asserting it.
- **Disagreement between formula and simulation is a finding**: locate it (which term, which
  regime) instead of tuning the comparison until it matches.

## Checklist (check before reporting; in the reply, one line: "✓ checklist" or the items that failed)
- [ ] assumptions and shapes written down
- [ ] derived from the model code's actual update rule
- [ ] sympy derivation saved as a script
- [ ] `compare_jacobian` + `finite_diff_check` pass at ≥3 points (float64)
- [ ] prediction vs simulation compared, residuals reported
- [ ] units, limiting cases and symmetries checked
