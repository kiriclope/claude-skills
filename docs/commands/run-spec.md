# /run-spec

## What it does

Agents work the spec's board in a loop (Pocock's implement-spec, for research). It shows the ticket graph, asks you
once to approve every experiment's parameters and the limits (at most 2 experiments and 4 agents at a time, the GPU
schedule), then runs each unblocked ticket in a fresh agent: build, analysis and writing in parallel; experiments
through the run-ticket procedure. Code lands on one integration branch, `spec/<name>`, with the tests green. It ends
with a code review and a QA plan for you.

## When to reach for it

After `/to-tickets`, once the breakdown is approved, when you want the work done without driving each ticket.

## Common questions

**What stops it?**
A failed or refuted ticket: its dependents are paused and you are notified; independent branches carry on. An
interpretation that would change the next ticket goes to a fresh reviewer first. Anything not on a ticket is
proposed, never run.

**What does it never do?**
Launch without a recorded approval, merge into your branch, push, close the spec, mark a review.

**What is the QA plan?**
The closed tickets ordered by how much rides on them, each with its verdict, figure, the one thing to check and
whether it is a one-way door; the paused ones with the premise that changed; the drafted sections for
reviewing-manuscript; then the merge, your call.

## It's working if

You spend your time on the approvals at the start, the paused tickets and the QA plan, and nowhere else.

Skill: [`plugins/research-core/skills/run-spec/SKILL.md`](../../plugins/research-core/skills/run-spec/SKILL.md)
