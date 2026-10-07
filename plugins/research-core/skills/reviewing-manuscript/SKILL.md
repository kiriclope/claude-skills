---
name: reviewing-manuscript
description: Run a mock referee review of a manuscript, a section or a figure set before it is shared or submitted — one fresh independent agent per lens (claims vs evidence, statistics and methods, novelty, clarity, reproducibility), each given only the text, the rendered figures and the numbers log, never the authors' reasoning; findings sorted into must-fix / should-fix / judgment call, each checked before it is applied. Use when the user says "act as a reviewer", "review the paper / draft / figures", "what would a reviewer ask", "is it ready to submit". Not for answering real reviews → use responding-to-reviewers.
---

# Reviewing a manuscript (mock referee)

Authors — and the agent that helped write — read what they meant; a referee reads what is there.
Past internal reviews of real papers found, among others: a significance star drawn from a variant
of the analysis that was not significant in the canonical build; a reliability correction without a
floor that turned noise into the headline points; a "transfer" claim clearing a 100-draw null by
0.011; a Methods window that the code never used; 95% CIs computed with 1.96 at n = 9; a null line
drawn for one group with another group's points; a Methods sentence ("one decoder across figures")
that no script implemented. Each was invisible from inside the writing.

## Step 0 — scope and materials

```
QUESTION     what the review must decide (submission-ready? one section? one figure?)
CRITERION    e.g. "no open must-fix; every claim has a panel that shows it"
```
Build the materials list — the only things reviewers see:
```bash
python <this skill>/scripts/materials.py                       # from project.yaml (paper_dir, figure_code, numbers_*)
python <this skill>/scripts/materials.py --paper <draft> --figures '<glob of the CANONICAL rendered figures>'
```
Give the canonical build only (not `_old`, `_all`, preview or variant renders). Fix what it flags
first: a missing figure, a figure older than its script (re-render), an absent numbers log.

## Step 1 — the lens reviewers, in parallel

One **fresh general-purpose agent per lens** (Agent tool, never a fork: a fork inherits the authors'
reasoning). Prompts: `references/lens_briefs.md` — the common header plus one lens:

1. **Claims ↔ evidence** — does each claim follow from the panel it cites?
2. **Statistics and methods** — design, units, nesting, floors, nulls, stars (choosing-statistics,
   auditing-results).
3. **Novelty and positioning** — what is known, who a referee will cite against it (reviewing-literature,
   verifying-citations).
4. **Clarity and presentation** — argument, panel citations, vocabulary, captions, legibility
   (writing-paper, making-figures).
5. **Reproducibility** — Methods vs code, text numbers vs the numbers log (auditing-paper-numbers).

For one figure, run lenses 1, 2, 4 and 5 on that figure. For a submission, also send lens 2 to a
second model (`codex:codex-rescue`) when it is installed: its errors are less correlated.

## Step 2 — triage (the reviewers can be wrong)

Merge duplicates. Check every finding before accepting it — read the line, rerun the number, open the
panel — and mark it **verified**, **rejected** (one line why) or **needs data**. This is
thinking-critically's step 4; do not re-describe it, do it.

## Step 3 — report

```
VERDICT: ready / needs fixes / blocked by <must-fix>
| severity | where (figure:panel, section:line) | finding | evidence | fix | verified |
REFEREE QUESTIONS TO EXPECT: the 5–10 most likely, each with where the answer is (or that it is missing)
PLAN: ordered actions — analyses → planning-research · text → writing-paper · figures → making-figures
```
When real reviews arrive, the plan feeds **responding-to-reviewers**.

## Step 4 — apply (what the user approves)

Must-fix first. Re-render the affected figures, rerun the numbers (auditing-paper-numbers), and log the
review and its outcome (log-and-ship), so the next review starts from it rather than repeating it.

## Never

- Give a lens reviewer the chat, the authors' notes or an earlier verdict — it anchors the review.
- Apply a finding unchecked, or downgrade a verified must-fix to finish sooner.
- Pad a lens: a clean lens is one line, "no findings".

Checklist (report as one line: "✓ review" or the failed items): materials list from the canonical
build · one fresh agent per lens · every finding verified or rejected · referee questions listed ·
plan routed to the right skills.
