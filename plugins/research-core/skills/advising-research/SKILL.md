---
name: advising-research
description: Act as the advisor of a research task — keep the user's decisions and the code in the main session, and hand each other phase to the agent the user's profile assigns it (plan → planner agent, sweep launch and monitoring → sweep-runner agent, result check → a fresh checker agent), with self-contained written handoffs and every approval kept with the user. Use when a phase boundary comes up — a plan is needed ("what next", "how do we test X", designing a sweep or analysis), a sweep is about to be launched, resumed, checked on or finished, or results came in and need checking before any conclusion — or when the user types /advising-research. Not for a vague request → clarifying-requests first; the rules of each phase stay in planning-research, launching-experiments, auditing-results and validating-networks.
---

# Advising research

Two reasons to split a research task by phase. Models differ in what they are best or cheapest at,
so each phase runs on the model the user chose for it. And the author of a plan or a piece of code
is the worst person to check its results, so the check runs in a fresh context that never saw the
author's reasoning (as in thinking-critically). The main session is the advisor: it holds the
conversation, the user's corrections and every approval, writes the code itself, and routes the
other phases.

## Step 0 — the routing table

Read the **Model routing** table in the user's profile (`~/.claude/CLAUDE.md`): the agent for each
phase. A phase without an agent, or an agent that does not load, runs in the main session; say so.
The model names live in that table and in the agent files, never in this skill.

## Step 1 — route

| Phase | Who | Gets (the handoff) | Returns |
|---|---|---|---|
| plan | planner agent | the PLAN handoff below | the plan block of planning-research, filled |
| code | main session | the approved plan | the diff, its checks (writing-research-code) |
| sweep | sweep-runner agent | the SWEEP handoff below | per-seed launch / status / finish report |
| check | checker agent, fresh | the CHECK handoff below | per-unit table, verdict vs the CRITERION, objections |

Route a phase when it is real work (minutes, not seconds). Each agent rebuilds its context
(tens of thousands of tokens), so a one-line fix, a single number or a quick question stays in
the main session.

## Rules (each prevents a failure)

1. **Approvals stay with the user, in the main session.** Agents cannot ask the user anything.
   Show the planner's plan and wait for approval before any code; show the launch table
   (launching-experiments Step 1) and wait for a go *before* dispatching the sweep-runner.
2. **A handoff is self-contained.** An agent sees none of the conversation: give paths, numbers,
   the user's constraints in their own words, and what was already run. A missing fact becomes
   a guess.
3. **The sweep-runner launches exactly what was approved and edits no code.** The config and launch
   command are written in the code phase. If anything differs from the approved table, or the pilot
   fails, it stops and reports. Debugging goes back to the main session (debugging-training).
4. **The checker gets the evidence, not the reasoning:** the plan with its CRITERION and FALSIFIER,
   written before the run, the run directories and the scoring tools. It does not get the coder's
   expectations or the main session's reading of the numbers. Its report goes to the user with the
   main session's triage of each objection (thinking-critically Step 4), never silently filtered.
5. **The main session does not redo a routed phase.** It relays, decides with the user, and
   says which agent did what.

## Handoffs (copy, fill every line)

```
PLAN
QUESTION      the user's words, and when they asked
STATE         what is settled and open; the docs and memory notes to read (paths)
ALREADY RUN   sweeps and analyses that bear on it (paths), so nothing is re-proposed
CONSTRAINTS   the user's rules that apply (seeds policy, budget, no engineered constraints, …)
RETURN        the plan block of planning-research; cost; what you read
```

```
SWEEP
JOB           launch | check-on | finish
APPROVED      the launch table the user approved, verbatim, and when
COMMANDS      pilot command, launch command (absolute paths); the run directories to expect
RETURN        launch: pilot result, screens and logs per seed · check-on: per seed running / done /
              failed with the log tail · finish: every planned run accounted for, figures made (paths)
```

```
CHECK
PLAN          QUESTION, CRITERION, FALSIFIER, as approved before the run
EVIDENCE      run directories, result files, figure paths; the project's scoring and validation
              tools (e.g. validating-networks, the verdict scripts)
RETURN        per-unit table; verdict vs the CRITERION: confirmed / refuted / inconclusive (why);
              objections ranked, each with the evidence that would settle it
```

## The loop

plan (planner) → user approves → code (main) → user approves the launch table → sweep launch
(sweep-runner) → the main session arms a monitor on completion *and* failure → sweep finish
(sweep-runner) → check (checker) → the main session triages the objections with the user → log
(log-and-ship) → re-plan (planner, with the verdict in STATE).
