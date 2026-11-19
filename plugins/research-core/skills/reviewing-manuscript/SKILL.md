---
name: reviewing-manuscript
description: Run a mock review of a manuscript, a section or a figure set before it is shared or submitted, in one of three styles — the journal's editor (desk decision, fit, format against the fetched guide, the referees to invite), external referees (the submission package only, one fresh agent per referee persona, a journal-form report with a recommendation), or an internal reviewer (text, figures, code, numbers log and pre-checks; one fresh agent per lens) — never given the authors' reasoning; findings sorted into must-fix / should-fix / judgment call, each checked before it is applied. Use when the user says "act as a reviewer / editor / referee", "review the paper / draft / figures", "would the editor send it out", "what would a reviewer ask", "is it ready to submit", or types /review-editor, /review-referee, /review-internal. Not for answering real reviews → use responding-to-reviewers.
---

# Reviewing a manuscript (mock editor, referee or internal review)

Authors — and the agent that helped write — read what they meant; a referee reads what is there.
Past internal reviews of real papers found, among others: a significance star drawn from a variant
of the analysis that was not significant in the canonical build; a reliability correction without a
floor that turned noise into the headline points; a "transfer" claim clearing a 100-draw null by
0.011; a Methods window that the code never used; 95% CIs computed with 1.96 at n = 9; a null line
drawn for one group with another group's points; a Methods sentence ("one decoder across figures")
that no script implemented. Each was invisible from inside the writing.

## The three styles (each sees what its real counterpart sees)

| Style (command) | Sees (`materials.py --style …`) | Decides | Agents and brief |
|---|---|---|---|
| **editor** (`/review-editor`) | main text, main figures, cover letter; supplementary skimmed | send out or desk-reject (with a probability); fit and significance for the journal; novelty; format against the journal's guide, fetched; the 3 referees to invite | 1 fresh agent, `references/editor_brief.md`; a second on another model for a submission |
| **referee** (`/review-referee`) | the submission package: main and supplementary text and figures, references; no cover letter, code, numbers log or pre-checks (`--share-code` when the journal sends code) | a journal-form report: summary, significance, major concerns with what resolves each, minor points, requested analyses, recommendation, confidential comments | 1 fresh agent per referee persona, `references/referee_brief.md`; a second model per referee for a submission |
| **internal** (`/review-internal`) | everything: text, all figures and their variants, figure code, numbers log, pre-check outputs | errors: Methods vs code, numbers vs the log, statistics, stale figures, claims stronger than their cards | 1 fresh agent per lens, `references/lens_briefs.md` |

For a submission, run them in this order: **internal** (fix your own errors first) → **editor** (its referee table
becomes the referee personas) → **referees**. Without a style named, ask which, with that order as the recommendation.

## Step 0 — scope and materials

```
QUESTION     what the review must decide (submission-ready? one section? one figure?)
CRITERION    e.g. "no open must-fix; every claim has a panel that shows it"
```
Build the materials list for the style — the only things its reviewers see:
```bash
python <this skill>/scripts/materials.py --style editor|referee|internal   # from project.yaml
python <this skill>/scripts/materials.py --style … --paper <draft> --figures '<glob of the CANONICAL rendered figures>'
```
The reader-facing text comes from `project.yaml` → `review_texts` (globs: main, supplementary, cover letter). A
`[notes]` flag means author notes sit in `paper_dir` and would reach the reviewers: set `review_texts` first. **Why:**
`paper_dir` mixes the draft with its README, method notes and style guide; the 2026-11-13 editor read had them
stripped by hand.
Give the canonical build as the figures (not `_old`, `_all` or preview renders). List each figure's
variant renders (`_pca20`, `_robust`, …) separately as VARIANTS, for lens 2 only: a star that flips
between variants is visible only there (2026-10-30 trial: the knob-dependent Fig. 3 star was in the
`_pca20` render, which a canonical-only list hid). Fix what it flags
first: a missing figure, a figure older than its script (re-render), an absent numbers log.

**Pre-checks before the lenses (internal only).** Run the PRE-CHECKS `materials.py` prints (numbers vs the numbers log,
the claims ledger, every `.bib`) and add their outputs to the materials. **Why:** what a script can
decide should not cost a reviewer's attention, and an agent misreads a number a script would not (a
reviewer agent once drew a ±0.021 band from a mismatched pair; the true value was ±0.011, 2026-10-29).
A figure script that calls `check_figure` gets its report added the same way.

## Step 1 — the reviewers (fresh agents; never a fork: a fork inherits the authors' reasoning)

**Editor.** One fresh general-purpose agent with `references/editor_brief.md`, filled with the journal, the field,
the editor materials and `project.yaml` → `referees`. For a submission, a second agent on another model with the same
brief, blind to the first (as on 2026-11-13).

**Referees.** The personas: the REFEREES table of the latest editor review in the reviews folder, plus
`project.yaml` → `referees`; with neither, run the editor first, or ask the user for the three. One fresh agent per
referee, in parallel, with `references/referee_brief.md`; for a submission each persona also on a second model. Then
merge as an editor would: concerns raised by two or more referees first, disagreements between referees shown, the
recommendations side by side.

**Internal.** One fresh general-purpose agent per lens, with `references/lens_briefs.md` — the common header plus one lens:

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

Merge duplicates. A finding that says a doc, comment or Methods value is wrong because the code says
otherwise is re-checked at the figure script's call site (2026-10-30 trial: a lens ran a function
with its default and "corrected" the right window to the wrong one). Check every finding before accepting it — read the line, rerun the number, open the
panel — and mark it **verified**, **rejected** (one line why) or **needs data**. This is
thinking-critically's step 4; do not re-describe it, do it.

**The previous review.** If the reviews folder (`project.yaml` → `reviews_dir`, default `docs/reviews/`)
holds an earlier review, read it now — never before, and never give it to a lens. Mark each of its
findings **fixed**, **back** (found again: it was not fixed, or the fix did not hold) or **not checked**
(out of this scope). A must-fix that is back stays must-fix.

## Step 2b — claim status (after the reviewers, every style; the reviewers stay blind)

Map each claim in the Abstract and the Results to its evidence record: the verdict card
(`project.yaml` → `verdict_log`, with `concluding-research/scripts/collect_cards.py --match`) or the
question's section in `conclusions_doc`, and the claims ledger (validating-claims) when there is one.
- The text states it more strongly than its status (the text "X causes Y", the status "open: N cannot
  decide", "supported" from exploring runs only, or a screen read as a mechanism) → **must-fix**: the
  wording comes down to the status, or the confirming run goes into the plan.
- No card, conclusion or ledger entry → **should-fix**: audit the result (auditing-results) or drop the claim.
- A card corrected or superseded since the text was written → the text follows the correction.
**Why:** the reviewers see only the paper, so they cannot know that a confident sentence rests on a
one-seed series or on a card's title that its own numbers contradict (2026-10-29).

## Step 3 — report

Editor: the DECISION with its probability, the letter, the findings, the referee table. Referees: each referee's
recommendation, then the merged concerns. Internal, and the common part of all three:
```
VERDICT: ready / needs fixes / blocked by <must-fix>
| severity | where (figure:panel, section:line) | finding | evidence | fix | verified |
REFEREE QUESTIONS TO EXPECT: the 5–10 most likely, each with where the answer is (or that it is missing)
PLAN: ordered actions — analyses → planning-research · text → writing-paper · figures → making-figures
      (a "needs data" finding goes to planning-research as a draft pre-run card; advising-research routes it to the planner)
```
A revision larger than a few direct fixes goes through the flow: `/grill-research` on the findings (accept, reject,
rephrase the claim), then `/to-spec` (the accepted objections as user stories, the declined ones in Out of Scope
with why) and `/to-tickets`. When real reviews arrive, the plan feeds **responding-to-reviewers**.

Write the report to `<reviews_dir>/<date>_<style>_<scope>.md` (default `docs/reviews/`), the findings numbered
F1, F2, … with their triage mark, and a line for each finding of the previous review (fixed / back /
not checked). It is the one place the next review's triage starts from.

## Step 4 — apply (what the user approves)

Must-fix first. Re-render the affected figures, rerun the numbers (auditing-paper-numbers), mark each
applied finding in the review file (fixed in <commit>), and commit it with the fixes (log-and-ship).

## Never

- Give a reviewer the chat, the authors' notes, an earlier verdict, the verdict log or a previous review — it
  anchors the review. The pre-check outputs are evidence for the internal lenses only.
- Give an editor or a referee more than its style's materials (code, numbers log, pre-checks, another referee's
  report): the review is only worth what its real counterpart would see.
- Apply a finding unchecked, or downgrade a verified must-fix to finish sooner.
- Pad a lens: a clean lens is one line, "no findings".

Checklist (report as one line: "✓ review" or the failed items): style chosen · materials list for that style from
the canonical build, no author notes · internal: pre-checks run, outputs in the materials · one fresh agent per lens
or persona · every finding verified or
rejected · previous review's findings marked · claim status checked against the verdict cards ·
referee questions listed · plan routed to the right skills · review file written.
