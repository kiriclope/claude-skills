---
name: thinking-critically
description: A critical scientific loop for any question or task whose conclusion matters — state a falsifiable plan, act (after approval in plan/manual mode, directly in auto mode), keep a ledger of every claim tagged observed / derived / recalled / assumed, then have a FRESH independent reviewer agent re-check each claim against the primary evidence and the literature, and revise the conclusion with a calibrated confidence. Use when asked to think about or reason through a scientific problem, propose a mechanism or hypothesis, interpret results or figures, draw a conclusion from an analysis, relate findings to the literature, or when the user says "think critically", "be critical", "double-check", "are you sure", "review this freshly". Not for mechanical tasks (renames, commits, formatting).
---

# Thinking critically

What this prevents: a confident conclusion built on a recalled-but-unchecked fact, an
aggregate that hides the one unit that matters, a citation that does not say what it is cited
for, or a criterion quietly moved after seeing the data. The author of a conclusion is the
worst person to check it — anchored on their own plan and reasoning — so the check is done by a
fresh agent that never sees the author's justification, only the evidence and the claims.

## 1 — Plan (before acting)

Write it in 5–8 lines — the short form of planning-research's plan block, same field names (research
tasks: use the full block):

```
QUESTION     one sentence
APPROACH     the steps and tools
EVIDENCE     what will decide it (which output, figure, table, source)
CRITERION    the decision rule, written now — e.g. "≥ 6/8 seeds show …", "the paper states X"
FALSIFIER    the result that would show the opposite
RISKS        confounds or artifacts that could fake the answer
```

- **Plan mode:** present it with ExitPlanMode. **Default (manual) mode:** show it and wait for
  approval when the actions are costly, long or irreversible. **Auto mode:** state it in 2–3
  lines and proceed.
- The criterion is never moved afterwards without saying so explicitly.

## 2 — Act, and keep a claims ledger

Every statement that will appear in the conclusion goes in a numbered ledger with a tag:

| tag | meaning | requirement |
|---|---|---|
| `observed` | read directly from a tool output, file or figure in this session | keep the pointer: command, `file:line`, figure path |
| `derived` | computed or inferred from observed items | state the step |
| `recalled` | from your own knowledge: facts, literature, typical values | unchecked — verify or label it |
| `assumed` | a premise or a choice | say why it is reasonable |

- Numbers come only from this session's outputs, never from memory of earlier runs (re-read them).
- Literature enters a conclusion only after `verifying-citations` (exists, says that, quote).
- Keep "I checked" and "I believe" apart in the wording.

## 3 — Fresh critical review

Spawn a **new** agent — Agent tool, `subagent_type: general-purpose`. **Not a fork**: a fork
inherits your context, your reasoning and your blind spots. Fill `references/reviewer_brief.md`
with ONLY: the question, the plan and its pre-stated criterion, pointers to the evidence, and the
numbered claims with their tags. **Do not include your justification or your confidence.**

For high-stakes conclusions — a claim going into a paper, a decision that commits days of
compute — also send the same brief to a different model (`codex:codex-rescue`), whose errors are
less correlated with yours.

`references/failure_modes.md` lists what the reviewer looks for (the brief points to it).

## 4 — Triage and revise

- **The reviewer can be wrong too.** For each objection, run the check it proposes or read the
  source before accepting or rejecting it — one line each, with the result.
- **Must-fix** items are fixed. Auto mode: cheap checks and quick re-analyses run immediately;
  anything long-running, costly or outward-facing waits for approval. Manual mode: propose.
- **Revise the conclusion:** drop or soften every claim that is weaker than stated; give a
  confidence (low / medium / high) and the result that would change it.
- At most two review rounds; stop when a round finds no must-fix.

## Output (end of the answer)

```
## Critical review
Reviewed by: fresh agent [+ codex] · N claims — a supported, b weaker than stated, c unsupported, d contradicted
| # | claim | tag | status | evidence / check | revision |
Must-fix: done … / pending (needs approval) …
Revised conclusion (confidence: …): …
Would change it: …
```

## Never

- Present `recalled` as `observed`; cite a paper that was not verified; report a number that
  does not appear in this session's outputs.
- Give the reviewer your reasoning (it anchors the review), or skip the review because you feel sure.
- Manufacture criticism: if the review finds nothing, write "no must-fix" in one line.
