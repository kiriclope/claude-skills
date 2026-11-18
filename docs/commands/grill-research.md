# /grill-research

## What it does

Runs Matt Pocock's grilling (a relentless interview in rounds, each question with its recommended answer, until no
decision is left assumed) and domain-modeling (the glossary updated as terms settle), with five research rules:
a card's conclusion is cited with its strength and asked when weak; every recommendation carries its evidence; every
claim grows four branches (falsifier, rivals, reviewer objection, imposed or found); questions stand alone in plain
words, at most four a round; one-way doors first. It ends with what was decided, what is assumed rather than found,
and what is out of scope.

## When to reach for it

Before `/to-spec`, in the same session, on a destination that spans sessions: a paper, a figure to replace, a
mechanism question. For a project underway it reads the conclusions and the latest cards first.

## Common questions

**Why not edit Pocock's grilling?**
So his file stays unchanged and his fixes keep applying; this command adds the research rules on top, as his
grill-with-docs adds domain-modeling.

**Won't the four branches make it endless?**
They are asked only once their claim is settled, at most four questions a round. If it still runs long, say "enough
on rivals for now": that branch goes to the closing list as assumed.

## It's working if

No recommendation lacks a source, no weak card is treated as settled, and the "assumed, not found" list is what the
spec's GAP lines and first tickets are made of.

Skill: [`plugins/research-core/skills/grill-research/SKILL.md`](../../plugins/research-core/skills/grill-research/SKILL.md)
