---
name: grill-research
description: A relentless interview on a research plan (a paper, a figure to replace, a mechanism question) until no decision is left assumed, run on Matt Pocock's grilling and domain-modeling with the research rules added — conclusions cited with their strength, recommendations backed by evidence, falsifiers, rivals and reviewer objections as standing branches, plain standalone questions, and a closing list of what is assumed rather than found. Comes before /to-spec.
disable-model-invocation: true
---

# Grill research

Call the Skill tool twice, for "grilling" and "domain-modeling". Run them with the rules below; where they differ
from grilling, these win.

## Before the first round

Read the project's `docs/agents/research.md`, `GLOSSARY.md`, the conclusions doc's section on this question, the plan
or figure plan it names, and the verdict cards since that section's date. State the destination in one line and ask
the user to confirm it: the whole tree hangs off it.

## The rules added for research

1. **A measurement is a fact; what it means is not.** Look up what a card or run measured, never ask it. A branch that
   rests on a card's *conclusion* cites it with its strength ("supported, 7/8 seeds, card 2026-11-12"), and a
   conclusion that is single-card, exploring, contradicted or older than a code change that touches it is asked as a
   decision, not used as settled.
2. **Every recommended answer carries its evidence**: the card, run, figure, paper or derivation it comes from, or
   "judgment" when it has none. Never a number from memory or a summary.
3. **Every claim in the tree grows four branches**, asked once its claim is settled:
   - **falsifier**: which result would make the user drop or weaken it;
   - **rivals**: the other explanations, and the control or measure that rules out each;
   - **reviewer**: the first objection a referee in the target journal raises, and what answers it;
   - **imposed or found**: what the model, task or training sets by construction versus what the nets discovered.
4. **Questions stand alone**: what is decided and where, what it changes (which runs, figures, claims), why the
   recommendation, the alternative. Full names, never a bare code (an arm id, M1, H2); plain words, the science
   explained, not only the choice. At most four questions per round; the frontier waits for the next one.
5. **Doors**: say whether a decision is a one-way door (a relaunch, a claim in a submitted text, data dropped) or a
   two-way door, one-way doors first.

## The end

When the frontier is empty, before the user confirms, list:
- **Decided**: one line per decision, with its evidence.
- **Assumed, not found**: what the plan takes for granted without a measurement (these become the spec's GAP lines or
  its first tickets).
- **Out of scope**: what was set aside, and why.

Then the user runs `/to-spec` in this session.
