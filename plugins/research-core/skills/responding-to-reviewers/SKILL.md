---
name: responding-to-reviewers
description: Draft a point-by-point response to peer reviewers (or editor, or internal pre-submission review) and plan the revision — full coverage of every comment, no fabricated results, no promises the revision does not keep, each answer tied to a concrete change and its location in the manuscript. Use when the user shares reviews or decision letters, asks to draft a rebuttal or response letter, to triage reviewer comments, or to plan revision analyses.
---

# Responding to reviewers

A response letter is checked line by line against the revised manuscript. The three ways it
fails: a comment silently skipped, a result claimed that was not run, a change promised that
is not in the manuscript. This skill prevents all three.

## Step 1 — split and number every comment

Copy the reviews verbatim into `docs/revision/comments.md` and split them into atomic points:
`R1.1, R1.2, … R2.1 …, E.1` (editor). A paragraph with three requests is three points.
Nothing is paraphrased away.

## Step 2 — triage table

| ID | Point (short) | Type | Our position | Action | Evidence needed | Status |
|---|---|---|---|---|---|---|
| R1.3 | movement confound on choice axis | analysis | agree, partly addressed | new control analysis | regression of movement | planned |

Types: misunderstanding (clarify text) · missing control/analysis · requested experiment ·
interpretation dispute · presentation · minor/typo. Positions: agree · partly · disagree
(with the reason and evidence).

New analyses and experiments go through **planning-research** (prediction, control, success
criterion written before running). Comments shared by several reviewers are answered once and
cross-referenced.

## Step 3 — write each response

```
R1.3  > quoted comment
We thank the reviewer … [one sentence acknowledging the point, no flattery]
[What we did: the analysis/change, with the result and its number, from the actual output]
[Where: "Results, section 3, paragraph 2; new Extended Data Fig. 5c; Methods, 'Movement controls'"]
[Quoted new or changed manuscript text, if short]
```

Rules:
- **No fabrication.** Every result in the letter comes from an analysis that has been run in
  this revision, with its output on disk. If it has not been run, the status is `planned`
  and the response is not finalized.
- **No overpromising.** Never write "we will" in a final letter; the change is made or it is
  declined with a reason.
- **Every response points to a location** in the revised manuscript, and that location
  contains the change (check it).
- **Disagree with evidence**, respectfully: what the reviewer proposes, why it does not apply
  or what the data show, and what we changed to prevent the misreading.
- Tone: direct, grateful once, never defensive or sarcastic; no "as clearly stated".

## Step 4 — consistency pass (before sending)

- Every ID in `comments.md` has a response (count them).
- Every number in the letter matches the manuscript and the numbers log (**auditing-paper-numbers**).
- Every location cited exists in the revised file; new figures/panels are cited in the text
  and captioned (**making-figures**).
- New references verified (**verifying-citations**).
- A short summary of major changes heads the letter.
- A fresh agent (**thinking-critically**, steps 3–4) reads each comment next to its response and
  the location it cites, without your notes: does the response answer the comment, and is every
  factual statement in it true of the revised manuscript?

## Checklist (copy and tick)

- [ ] all comments split, numbered, none paraphrased away
- [ ] triage table complete; analyses planned before run
- [ ] each response: action + result + location; no "we will"; nothing unrun claimed
- [ ] coverage count matches; numbers, locations, references cross-checked
- [ ] responses reviewed by a fresh agent against the comments and the revised manuscript
