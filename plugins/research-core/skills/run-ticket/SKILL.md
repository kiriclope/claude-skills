---
name: run-ticket
description: Work one ticket of a research spec end to end in one session — fetch and claim it, write its pre-run card, get the user's OK on the parameters, run it (experiment, build, analysis or writing), audit the result, append the verdict card and close the ticket with the card, refuted or not. The research version of Matt Pocock's implement.
disable-model-invocation: true
---

# Run ticket

One ticket, one session. The tracker and the research meanings are in `docs/agents/issue-tracker.md` and
`docs/agents/research.md`.

1. **Fetch.** With a ticket reference, read it with its comments and state its title, kind (experiment / build /
   analysis / writing) and acceptance criteria. Without one, read the spec's frontier and propose its first ticket.
   If it has an open blocker, an assignee or the `paused` label, stop and say so.
2. **Claim** it (assign it, or `Status: claimed`) before any other write.
3. **Pre-run card** (planning-research Step 1) in the verdict log, naming the ticket; its criterion is the ticket's
   acceptance criteria, copied, never rewritten after the run.
4. **The user's OK** on what will run. For an experiment, the parameter table: if the user already approved it on the
   ticket (one approval per spec), say so and go; otherwise show it and wait. Anything the ticket does not name (an
   extra arm, a changed default) is asked, never added.
5. **Run it** with the skills of its kind:
   - experiment → launching-experiments (pilot, one screen and one log per seed), then validating-networks or
     validating-pipelines on the finished runs;
   - build → writing-research-code, a small check that goes red without the change, reviewing-code-readability;
   - analysis → validating-pipelines when the measure is new; making-figures for its figure;
   - writing → writing-paper, auditing-paper-numbers.
6. **Audit and verdict** (auditing-results): figure, verdict, per-unit table, the argument; an interpretation that
   changes the next ticket goes to a fresh critical-reviewer first. Append the card.
7. **Close** the ticket with a comment linking the card (auditing-results), refuted or not. Tickets whose premise the
   result changed get `paused` and go to the user.
8. **Report** in chat: the figure, the verdict, the ticket closed, what the frontier is now. Commit only when asked
   (log-and-ship).

A long run (a sweep of hours) ends this session at step 5 with the ticket still claimed; the session that picks the
results up (`/run-ticket <same ticket>`) resumes at step 6.
