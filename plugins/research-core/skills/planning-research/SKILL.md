---
name: planning-research
description: Plan a piece of research before running it — turn a question into a falsifiable hypothesis, predictions, the decisive experiment/analysis, controls, success criteria and a staged run plan; and re-plan after results. Use when the user asks "what should we try next", "how do we test X", "design a sweep/experiment/analysis", "what would convince a reviewer", proposes a new direction, or when results came back and the next step is unclear. Also use before launching anything expensive (sweeps, long training, large analyses). Not for a vague request → clarifying-requests first; for checking a finished conclusion → thinking-critically.
---

# Planning research

The expensive mistakes in modeling projects are not bugs — they are running the wrong
experiment, reading a result the experiment could not have refuted, and moving the goalposts
after the fact. A plan written **before** running fixes all three.

## Step 0 — load the state

Read the project's overview doc, the current-thread log, and the live-status memory (paths in
`.claude/project.yaml` / `CLAUDE.md`). State in two lines what is settled and what is open.
Do not re-propose experiments that the logs already ran — search them first.

## Step 1 — write the plan (template; fill every line)

This is the canonical plan block. Other skills use short forms with the same field names:
thinking-critically (QUESTION, APPROACH, EVIDENCE, CRITERION, FALSIFIER, RISKS) and
clarifying-requests (GOAL, DELIVERABLE, SCOPE, CRITERION, DEFAULTS).

```
QUESTION     one sentence, in the field's terms
HYPOTHESIS   the mechanism you believe, stated so it can be wrong
PREDICTIONS  if true → we will see A; if false → we will see B   (A and B must differ observably)
ALTERNATIVES the 1–3 other explanations that also predict A, and what separates them
EXPERIMENT   the smallest decisive manipulation/analysis (what changes, what is held fixed)
CONTROLS     baseline arm, null/shuffle, matched sample size and normalization, sanity case
               with a known answer
METRIC       the primary readout, computed per unit (seed / subject); the decision threshold
CRITERION    the decision rule, written now: "≥k of N seeds show …" — never adjusted after seeing the data
SCALE        exploring: few seeds/small grid; definitive: more seeds; cost (GPU-h, time)
STAGES       pilot (1–2 runs, check the pipeline end to end) → exploration → confirmation
FALSIFIER    the result that refutes the hypothesis — if it appears, drop or change direction
OUTPUTS      the figures and tables this produces, and which claim each supports
```

Rules:
- **One lever per arm.** If two things change, the result is uninterpretable. Name the
  baseline every arm is compared with.
- **No engineered answers.** A loss term, constraint or pin that encodes the desired outcome
  makes the outcome uninformative; say so if one is proposed.
- **Theory before brute force.** If the result can be predicted analytically or from a cheap
  reduced model, do that first and use the experiment to test the prediction.
- **Pilot first.** One short run through the whole pipeline (train → analyze → figure) before
  the grid; most failed sweeps fail at analysis, not training.
- Show the plan and the exact configuration to the user and **wait for confirmation** before
  launching anything long or costly.

## Step 2 — after results: re-plan honestly

1. Score the results with the project's verdict tools / scripts, unit by unit, against the
   CRITERION written before. Report hits and misses; a mean alone hides the one unit that
   worked and the one that failed.
2. Classify: **confirmed / refuted / inconclusive (and why: noise, confound, pipeline)**.
   Separate data finding, imposed assumption, and model limitation.
3. If refuted, say so plainly and update the docs where the hypothesis was stated — do not
   reinterpret the success criterion.
4. **Before the verdict is logged or acted on**, run the fresh review of **thinking-critically**
   (steps 3–4): the reviewer gets the plan with its CRITERION, the per-unit scores and the
   verdict — not your reasoning — and you triage its objections.
5. Next step = the single most informative experiment given what changed; write a new plan.
6. Log it (log-and-ship): plan, result, verdict, next step, with dates.

## Planning a paper or figure set

Lead with the claims (propositions/results), then for each claim the minimal evidence that
makes it undeniable, then the figure panels that show that evidence. Supplement material and
polish come after the main claims stop moving.
