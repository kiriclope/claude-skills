---
name: auditing-paper-numbers
description: Check that every number and claim in a manuscript (results text, captions, abstract, reviewer response; .md/.tex/.html) is traceable to the current output of a numbers script, and that each claim sentence points to the panel and statistic that support it. Use before sharing or submitting a draft, after re-running analyses or sweeps that feed the paper, when editing results paragraphs or captions, or when asked "are the numbers right / up to date", "check the draft", "audit the paper". Not for the wording of the text → writing-paper.
---

# Auditing paper numbers

A number in a paper is correct only if a script printed it from the current data. Numbers drift
when analyses are re-run, seeds are added, or text is edited by hand. This skill finds every
number in the text and classifies it against the numbers log.

## Rules

- **Never type a number into the manuscript by hand without a source.** If no script prints
  it, add it to the numbers script first.
- **Fix the cause, not the symptom**: a MISMATCH means either the text is stale (update the text
  from the log) or the script changed definition (decide which is right, then fix one of them).
- Rounding follows the text: "0.81" matches 0.8134; a percentage matches a fraction ("97.3%" ↔ 0.973).

## Workflow

1. **Regenerate the numbers log** with the project's numbers script (path in
   `.claude/project.yaml` → `numbers_script` = the script, `numbers_log` = the file it writes, or
   ask; the audit refuses a `.py` passed as the log). The log is JSON (any
   nesting; key paths become sources) and/or the script's printed report saved as text.
   Check that it ran on the intended data (sweep, seed set, sessions) — print its header.
2. **Run the audit:**
   ```bash
   python <this skill dir>/scripts/audit_numbers.py --text <manuscript> --log <numbers.json> [<report.txt>] \
       --only MISMATCH UNSOURCED
   ```
   `MATCH` (a log value rounds to it), `MISMATCH` (a log value is within 10 %: stale or
   mis-rounded), `UNSOURCED` (nothing near it). Figure/section/equation references, years,
   dates, citation brackets and small integers are skipped (`--strict` checks everything).
   A MATCH found only by coincidence (common values like 0.5) is possible: for key claims,
   confirm the source path printed next to the number is the right quantity.
3. **Resolve every MISMATCH and UNSOURCED**: update the text, extend the numbers script, or
   mark the number as a definition/parameter (not a result). Re-run until clean.
4. **Claim audit** (manual, per results paragraph and caption):
   - each claim sentence → the panel that shows it ("(Fig. 3b)") → the statistic in the log;
   - the statistic's n is in the right unit (subjects vs trials vs seeds) and the test is named;
   - every panel of every figure is cited at least once (inventory from the rendered figure);
   - wording matches the strength of the evidence (no "shows" for an n.s. trend; caveats kept);
   - the same quantity has the same value everywhere it appears (abstract, results, caption).
5. Report: counts per class before → after, the list of changed sentences, and any number
   that remains a deliberate exception.

## Checklist (check before reporting; in the reply, one line: "✓ checklist" or the items that failed)
- [ ] numbers log regenerated from the current data (header checked)
- [ ] `audit_numbers.py` clean: 0 MISMATCH, 0 UNSOURCED (or each exception justified)
- [ ] key MATCHes point to the right source quantity
- [ ] every claim ↔ panel ↔ statistic; n in the unit of the claim
- [ ] every panel cited; values identical across abstract, text and captions
