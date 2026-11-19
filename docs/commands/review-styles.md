# /review-editor · /review-referee · /review-internal

## What it does

A mock review in one of three styles, each seeing what its real counterpart sees (`materials.py --style`):
the journal's **editor** (main text, main figures, cover letter: send out or not, with a probability; format against
the journal's guide fetched at review time; the three referees it would invite), **external referees** (the
submission package only, one agent per persona, a journal-form report with a recommendation), and an **internal**
colleague (text, every figure, code, numbers log and pre-checks: the five lenses). Every finding is verified by us
before it counts, and the review file goes to `docs/reviews/<date>_<style>_<scope>.md`.

## When to reach for it

Before a submission, in order: `/review-internal` (your errors first), `/review-editor` (its referee table becomes
the personas), `/review-referee`. One figure or section: `/review-internal` on it.

## Common questions

**Why can't the referees see the code?**
Most journals do not send it; a referee who reads the code finds what a real one never would. `--share-code` when
your journal sends it.

**Where do the referee personas come from?**
The latest editor review's referee table, plus `referees` in project.yaml (personas always included).

**The reviewers saw my notes?**
Set `review_texts` in project.yaml to the reader-facing files; `materials.py` flags author notes in `paper_dir`.

## It's working if

The editor's decision and the referees' major concerns are ones you would recognize from a real round, and the
internal review finds the errors before they do.

Skill: [`plugins/research-core/skills/reviewing-manuscript/SKILL.md`](../../plugins/research-core/skills/reviewing-manuscript/SKILL.md)
