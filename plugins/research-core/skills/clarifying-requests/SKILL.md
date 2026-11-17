---
name: clarifying-requests
description: Act as the user's reflection partner when a request is vague, underspecified or open to several materially different readings — look in the context first, mirror back what the user seems to be after (including the deeper question they may not have stated), ask a few sharp questions with concrete options, then write a short task spec before acting. Use when a task or message has no clear goal, deliverable, scope or success criterion ("make it better", "look at this", "fix the figures", "what about X?"), when the user asks "help me think this through", "ask me questions first", "I'm not sure what I want", or says "clarify". Not when the context already answers it or the request is precise.
---

# Clarifying requests

The user's own words: be my reflection. A vague request is often a problem not yet thought
through; good questions help the user see what they actually want — the way a colleague's
"which cat, for whom, why?" turns "draw a cat" into a task. The goal is a sharper problem,
not a longer conversation: every question must change what will be done, or show the user
something about their problem they had not considered.

## Step 0 — look before asking

Search the conversation, the project docs, `CLAUDE.md`, the memory and the code first. Never
ask what they answer (which sweep is "the baseline", where figures go, which script plots
flows). If what remains has a sensible default and a wrong guess is cheap to undo, state the
default and proceed — no questions. The action the user asked for is approved by the asking;
extras you add on top (re-runs, renames, publishing, anything long, costly or outward-facing)
still follow the project's approval rules — end with one yes/no question for those.

## Step 1 — mirror

One or two sentences: "Here is what I think you are after: … The open point is …". When the
request hides a bigger question, name it: "It sounds like the real question is whether X —
is that right?". This is the reflection the user asked for; often it resolves half the vagueness.

## Step 2 — ask, one round at a time

Ask in **rounds**, written in the reply as numbered text the user reads at their own pace:

```
**Q1 · <decision, a few words>.** <the question with its options, as much context as it needs>
➡️ Recommended: <your answer, and why in one line>
```

- Word each question so that **"yes" accepts the recommendation**; the user answers "yes",
  "yes except Q2: …", or per question.
- A round holds the **frontier**: every question whose prerequisites are settled. A question that
  depends on an answer still open waits for the next round.
- **Facts are your job, decisions the user's.** A question the code, docs or a quick search can
  answer is not asked: look it up (a subagent for anything long) and ask only the decisions.
- Each question is **concrete** ("Which figure: 5 (flows) or 6 (depth vs accuracy)?") and the
  rounds go **by impact**, the question that changes the most first.
- The AskUserQuestion pop-up only for one or two quick choices, or to compare layouts side by
  side with `preview`. **Why:** the pop-up covers the text above it; questions in it were hard to
  follow without their context (2026-11-04), and a numbered round with recommendations is read and
  answered in one line (Pocock's `grilling`, 2026-11-17).

Pick the questions from the dimensions in `references/question_bank.md` (goal, deliverable,
scope, success criterion, constraints, audience, prior knowledge, interpretation, trade-off).
Problem-level questions (why, what decision it serves, what a good outcome looks like) come
before detail-level ones (color, size, file name) — the detail may stop mattering once the
goal is clear.

## Step 3 — the task spec

When the answers are in, write it in five lines and act on it (confirm first only if the task
is long, costly or irreversible):

```
GOAL         what the user wants to know or have, and why
DELIVERABLE  what comes back (figure, table, number, code, text) and where it goes
SCOPE        which data / runs / files / panels — and what is out of scope
CRITERION    done when … (the success criterion)
DEFAULTS     what was not asked, and the default taken for it
```

For a scientific question, the spec feeds the plan of the **thinking-critically** skill
(GOAL → QUESTION; CRITERION carries over).

## Step 4 — another round, or stop

Ask a second round only if an answer opened a new fork that changes the work. Stop when every
open point has a cheap-to-change default. Two rounds is the usual maximum; a third needs a
reason the user would agree with.

## Never

- Ask what the context answers, or what the user already answered in this session.
- Ask a question whose answer would not change the work ("which color?" for a throwaway plot).
- Ask open-ended "anything else?" questions, or a question whose answer is a fact you can look up.
- Interrogate a precise request — this skill is for vague ones.
- Ask, then ignore the answer: the spec must show where each answer went.
