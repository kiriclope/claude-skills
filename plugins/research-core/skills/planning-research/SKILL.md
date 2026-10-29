---
name: planning-research
description: Plan a piece of research before running it — turn a question into a falsifiable hypothesis, predictions, the decisive experiment/analysis, controls, success criteria and a staged run plan; and re-plan after results. Use when the user asks "what should we try next", "how do we test X", "design a sweep/experiment/analysis", "what would convince a reviewer", proposes a new direction, or when results came back and the next step is unclear. Also use before launching any arm — even a quick "try X" (the 6-line pre-run card) — and before anything expensive (sweeps, long training, large analyses). Not for a vague request → clarifying-requests first; for checking a finished conclusion → thinking-critically.
---

# Planning research

The expensive mistakes in modeling projects are not bugs — they are running the wrong
experiment, reading a result the experiment could not have refuted, and moving the goalposts
after the fact. A plan written **before** running fixes all three.

## Step 0 — load the state

Read the project's overview doc, the current-thread log, and the live-status memory (paths in
`.claude/project.yaml` / `CLAUDE.md`). State in two lines what is settled and what is open.
Do not re-propose experiments that the logs already ran — search them first.

## Step 1 — the pre-run card (every arm, even a quick "try X")

Most arms start from a one-line request mid-session, and the full plan below never gets written: none
of 25 verdict cards in one project quoted a plan, two set their criterion after the run, and none had
planned its noise floor, so hypotheses could only be "after the data" (2026-10-29). Before launching **any** arm, open its card
at the top of the project's verdict log (`project.yaml` → `verdict_log`, default `docs/verdicts.md`),
dated, status `running`; the verdict (auditing-results §0) fills the bottom half after the run.

```
## <date> · <what is tested> — RUNNING (card opened <date>, before the run)
WHY         why this lever should work: the mechanism, in one or two sentences, each fact it rests on with
            its checked source; or "none: a screen" (see below)
PREDICTS    if it works → <observable A>; if not → <observable B>; a number from theory when there is one
STAGE       exploring (a pass is "open" until confirmed) / confirming <the exploring card it repeats>
CRITERION   the decision rule on independent units, incl. the COST side (what must not get worse)
FLOOR       what a change caused by nothing looks like, and the arm or rescoring that measures it
RIVALS      each other cause of A → the control that excludes it, or "not excluded → at best open"
N           independent units per arm, and what they can decide (stats_floor.py, below)
```
Show it with the launch table; the user approves both together. Write the full plan (Step 2) instead
when the question is new, the run is expensive, or several arms answer one question.

**Can N decide it?** Before the launch, run `choosing-statistics/scripts/stats_floor.py` on the design:
`--counts N` for solved / not-solved arms (Fisher; twins: McNemar), `--n N` for paired values,
`--n1 --n2` for independent groups. If no outcome the arm can produce meets the CRITERION, change
the design (more seeds, a graded readout, a harder baseline) or write down that the run is a pilot
that cannot decide. **Why:** with 6 runs per arm and a 5/6 baseline, no count can show an arm
helps; the delay-pin run (4/6 vs 5/6) was undecidable before it started.

**The rules that keep the card scientific:**
- **Premises checked.** Every fact WHY rests on cites a checked source: a verdict entry re-scored, a
  script's output, a run directory, never an old card's wording alone. **Why:** a test card's WHY said
  the pin "held κ₁ near 0", an overstated line from an uncorrected card; a plan on a wrong premise tests
  the wrong thing (2026-10-29).
- **No mechanism, no mechanistic conclusion.** WHY "none: a screen" is allowed, but its verdict can only
  say what the lever changed ("the pin lowers κ₁ over the delay"), never that a mechanism is supported.
- **Exploring, then confirming.** Trying lever after lever on few seeds until one passes will find a
  pass by chance (the garden of forking paths). An exploring arm that passes is "open"; it becomes
  "supported" only when a confirming card repeats it on fresh seeds with the same CRITERION, unchanged.
  Say on the exploring card how many arms were tried for the same question.
- **Frozen at launch.** The card is copied into every run directory at launch
  (`record_provenance.py --card <verdict log> --card_heading "<its heading>"` → `precard.md` + its
  sha256 in `provenance.json`). The verdict quotes that copy; any later edit of the card in the log
  is visible as a mismatch and must be explained in the entry.
- **Severity.** A quantitative prediction from theory or a reduced model ("κ₁ RMS ≈ 0.03 at weight
  0.2") is a stronger test than a direction; give one when the theory allows it.

**Independent units:** count the units that were trained apart. Runs that share a parent stage
(three GNG versions continuing one DPA stage) are one unit for anything the parent fixes; say so in N.

## Step 2 — the full plan (template; fill every line)

This is the canonical plan block. Other skills use short forms with the same field names:
thinking-critically (QUESTION, APPROACH, EVIDENCE, CRITERION, FALSIFIER, RISKS) and
clarifying-requests (GOAL, DELIVERABLE, SCOPE, CRITERION, DEFAULTS).

```
QUESTION     one sentence, in the field's terms
HYPOTHESIS   the mechanism you believe, stated so it can be wrong
PREDICTIONS  if true → we will see A; if false → we will see B   (A and B must differ observably)
ALTERNATIVES the 1–3 other explanations that also predict A, each with the control that excludes it
               (or "not excluded" — then the conclusion can be at best open)
EXPERIMENT   the smallest decisive manipulation/analysis (what changes, what is held fixed)
CONTROLS     baseline arm, null/shuffle, matched sample size and normalization, sanity case
               with a known answer; the NOISE FLOOR (seed spread, sham arm, same network rescored
               on fresh trials) planned as an arm, not hoped for after the data
METRIC       the primary readout, computed per unit (seed / subject); the decision threshold
CRITERION    the decision rule, written now: "≥k of N seeds show …", incl. the cost side (what must
               not get worse) — never adjusted after seeing the data
SCALE        independent units per arm and what they can decide (stats_floor.py); exploring:
               few seeds/small grid; definitive: more seeds; cost (GPU-h, time)
STAGES       pilot (1–2 runs, check the pipeline end to end) → exploration → confirmation on fresh
               seeds with the criterion unchanged (only a confirmed result is "supported")
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
- Save the plan, dated, before the run, as the open card at the top of the verdict log (Step 1):
  the verdict entry (auditing-results §0) quotes its HYPOTHESIS, PREDICTIONS and CRITERION to show
  what was fixed before the data.

## Step 3 — after results: re-plan honestly

1. Score the results with the project's verdict tools / scripts, unit by unit, against the
   CRITERION written before. Report hits and misses; a mean alone hides the one unit that
   worked and the one that failed.
2. Conclude in the verdict words of auditing-results §0: **supported / not supported / refuted /
   open** (and why: noise, confound, pipeline, a rival not excluded). Separate data finding,
   imposed assumption, and model limitation.
3. If refuted, say so plainly and update the docs where the hypothesis was stated — do not
   reinterpret the success criterion.
4. **Before the verdict is logged or acted on**, run the fresh review of **thinking-critically**
   (steps 3–4): the reviewer gets the plan with its CRITERION, the per-unit scores and the
   verdict — not your reasoning — and you triage its objections.
5. Next step = the single most informative experiment given what changed; write a new plan. When
   the question has several verdict cards, conclude it first (concluding-research): its ranked
   next steps are draft cards for this step.
6. Log it (log-and-ship): plan, result, verdict, next step, with dates.

## Planning a paper or figure set

Lead with the claims (propositions/results), then for each claim the minimal evidence that
makes it undeniable, then the figure panels that show that evidence. Supplement material and
polish come after the main claims stop moving.
