# /to-spec

## What it does

Matt Pocock's skill, unchanged: it turns the planning conversation into a spec with no new interview (problem, solution, a long list of user stories, decisions, testing decisions, out of scope) and posts it as the parent issue. In research, `docs/agents/research.md` gives his headings their meaning: user stories are reader stories, testing decisions are the measures that decide, the solution is the destination.

## When to reach for it

A planning conversation has settled a destination that will take several sessions: a paper, a figure to replace, a mechanism question.

## Common questions

**Why no ready-for-agent label on the spec?**
His FAQ: agents polling for that label try to build the whole spec at once. Ours leave it off the parent issue.

**Why unchanged?**
So his fixes and docs keep applying. Research meanings live in the project's docs/agents/research.md, never in his file.

## It's working if

Every line comes from something already decided; the two sections to read closely are the measures that decide and out of scope; nothing is posted before you have read it.

Skill: [`plugins/research-core/skills/to-spec/SKILL.md`](../../plugins/research-core/skills/to-spec/SKILL.md)
