# /grill-with-docs (and /grill-me)

For a research plan use [/grill-research](grill-research.md), which runs this interview with the research rules.

## What it does

Matt Pocock's, unchanged: a relentless interview on a plan. The decisions form a tree; each round asks every question
whose prerequisites are settled, numbered, each with its recommended answer, worded so "yes" accepts it. Facts are
looked up by a sub-agent, never asked. It ends when no branch is left and you confirm a shared understanding.
`/grill-with-docs` also updates `GLOSSARY.md` as terms settle, and offers an ADR for a decision that is hard to undo,
surprising and a real trade-off (`domain-modeling`). `/grill-me` is the interview alone.

## When to reach for it

Before `/to-spec`, in the same session: a destination over several sessions (a paper, a figure to replace). For a
project already underway, have the session read its state first (conclusions doc, plans, latest verdict cards).

## Common questions

**How is it different from clarifying-requests?**
clarifying-requests turns a vague request into a task in one or two rounds, then acts. Grilling keeps going until
every decision of the plan is yours, and acts on nothing until you confirm.

**What counts as a decision in research?**
The claim and its wording, which result carries it, the measures that decide, the figures, what is out of scope
(`docs/agents/research.md`). What a card measured is a fact: looked up, not asked.

## It's working if

Every question is one only you could answer, and `/to-spec` afterwards has no line you never said.

Skill: [`plugins/research-core/skills/grill-with-docs/SKILL.md`](../../plugins/research-core/skills/grill-with-docs/SKILL.md)
