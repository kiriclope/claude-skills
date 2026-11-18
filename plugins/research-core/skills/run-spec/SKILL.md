---
name: run-spec
description: Work a research spec's tickets in a loop with agents — read the ticket graph, run every unblocked ticket in a fresh agent (build, analysis and writing in parallel; experiments through the /run-ticket procedure, launching only what the user approved), merge onto one integration branch, stop and report at every failed or refuted ticket, and end with a QA plan for the user. The research version of Matt Pocock's implement-spec.
disable-model-invocation: true
---

# Run spec

The goal: every ticket of the spec closed with its verdict, the code on one **integration branch**, and a QA plan the
user works through. The tickets are a **task graph** (blocking edges), so there is always a **frontier** of tickets
ready to take. The tracker and the research meanings: `docs/agents/issue-tracker.md`, `docs/agents/research.md`.

This session is the orchestrator: it holds the user's approvals, starts agents, merges, and gates. It does no ticket
work itself. Every agent starts with a fresh context and gets **pointers, not copies**: the ticket, the spec, the
files to read.

## 1. Read the graph and get the approvals (the only wait at the start)

Read the spec and all its tickets; show the graph as a table (ticket, kind, blocked by, status, approval). Then ask,
in one round:
- **Experiments**: every experiment ticket's parameter table and GPU plan, approved once for the whole run. Record
  each approval on its ticket (a comment "Parameters approved by the user, <date>"); a ticket without one is not
  launched, and its dependents wait.
- **Limits**: at most 2 experiment tickets running at once (GPUs) and 4 agents in all, the project's GPU schedule
  (day / night, which devices; from CLAUDE.md or project.yaml), unless the user says otherwise.

## 2. The integration branch

`git worktree add ../<repo>_<spec> -b spec/<spec>` from the project's branch; results go where the project keeps them
(a symlink to its `results/`, never a second copy). Every ticket agent works in its own worktree off `spec/<spec>`,
and experiments launch from the integration worktree, so they run the merged code they depend on.

## 3. Work the frontier

For each frontier ticket, claim it (assign it) and start one background agent:
- **build / analysis / writing**: the agent reads `run-ticket/SKILL.md` (this plugin) and follows it, in its own
  worktree; a build adds a check that goes red without the change.
- **experiment**: the agent follows the same procedure through the launch, with the profile's routing
  (advising-research: the sweep-runner launches, the checker audits fresh). A sweep of hours ends the agent at the
  launch; this session watches the runs (Monitor, or a wakeup timed to the run) and starts a fresh agent for the
  audit when they finish.

When an agent reports done, a **merger agent** merges its branch into `spec/<spec>` and runs the project's tests;
a red test sends the ticket back, never a forced merge. Each close changes the frontier: start the newly unblocked
tickets at once.

## 4. Gates (the loop never passes these alone)

- **Failed or refuted ticket**: it closes with its verdict; every ticket waiting on it gets `paused` with the premise
  that changed. Notify the user (push notification) and keep working the independent branches.
- **An interpretation that changes the next ticket** goes to a fresh critical-reviewer before the dependents start.
- **Anything not on a ticket** (an extra arm, a changed default, a new analysis): propose it as a ticket; never run it.
- **Never**: launch without a recorded approval, merge into the project's branch, push, close the parent spec issue,
  or mark a review.

## 5. The end: code review, then the QA plan

When the frontier is empty (all closed or paused): reviewing-code-readability on `spec/<spec>` (both axes: the
conventions, and the code against its tickets), fixes in one fresh agent. Then post the **QA plan** on the parent
issue and in chat:

```
QA PLAN · <spec> · <closed> closed, <paused> paused, <open> open
Check first (one-way doors, and the tickets the most rides on):
  #<n> <title> — <verdict in one line> — figure: <path> — check: <the one thing to look at> — <one-/two-way door>
Then:
  …
Paused: #<n> — <the premise that changed> — <cancel / change / resume?>
Writing: <sections drafted> → reviewing-manuscript before they are shared
To merge: spec/<spec> → <project branch>, after the checks above (the user's call)
```

Order by consequence: what a later ticket or a claim in the paper rests on comes first. Clean up the ticket
worktrees; keep `spec/<spec>` until the user merges it.
