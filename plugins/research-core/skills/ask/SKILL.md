---
name: ask
description: Ask which skill or flow fits your situation — a router over the research skills, from Matt Pocock's ask-matt.
disable-model-invocation: true
---

# Ask

Before saying what a skill does or recommending a step be skipped, read that skill's SKILL.md: the lines here orient,
they do not replace it. Answer with the one flow that fits and its first command; name the alternative only when the
situation is ambiguous.

## The main flow: question → verdict → conclusion

1. **Sharpen the question.** A vague request → clarifying-requests (questions in rounds, each with a recommendation).
2. **Can one session hold it?**
   - **Yes** → planning-research writes the pre-run card (or the full plan), then the work runs (launching-experiments
     for a sweep), then auditing-results gives the verdict card.
   - **No** (a paper, a figure to replace, a mechanism question over weeks) → **`/grill-research`** on the
     destination (Pocock's relentless interview with the research rules: conclusions cited with their strength,
     falsifiers, rivals and reviewer objections; `GLOSSARY.md` updated as terms settle), then **`/to-spec`** (synthesis, no new interview), then **`/to-tickets`** (the breakdown is
     approved before anything is posted), then one **`/run-ticket`** per session from the frontier; **`/run-spec`**
     runs the frontier in parallel once built. For a project already underway, read its state first (conclusions doc,
     plans, latest verdict cards), then grill.
   - **Not sure the mechanism works at all** → **`/toy-model`** first; its answer decides whether to plan.
3. **After several verdicts on one question** → **`/conclude`** (status per hypothesis, the spec's stories answered or
   not, the next tickets).
4. **A session went wrong** → **`/retro`** before clearing it.

Keep the grilling, the spec and the tickets in one context window until `/to-tickets` has run, so the spec and tickets build on the same thinking;
each `/run-ticket` then starts fresh from its ticket.

## On-ramps

- **Training misbehaves** → debugging-training (one command that fails first, ranked hypotheses).
- **Referee reports arrived** → responding-to-reviewers.
- **Starting a session, "where were we"** → resuming-work.
- **A review is due, "catch me up"** → running-review-checkpoints.

`/grill-with-docs` and `/grill-me` are Pocock's originals, for a plan that is not research (code, tooling). The grilling skill also loads on its own
when you say "grill me"; clarifying-requests stays for a vague request (one or two rounds, then act).

## Checks that run under the flow

auditing-results (every number), validating-networks / validating-pipelines / validating-decoders (before a result is
believed), choosing-statistics (before a p-value), thinking-critically (a conclusion that matters), checking-derivations
(math), validating-claims (a result becomes a claim).

## Writing and shipping

writing-paper, auditing-paper-numbers, verifying-citations, reviewing-literature, reviewing-manuscript,
making-figures → showing-figures / figure-gallery, publishing-drafts, log-and-ship (commit).

## Upkeep

organizing-projects (the repo), maintaining-memory (the memory), maintaining-skills (the skills),
reviewing-code-readability (before a commit), domain-modeling (the glossary; an ADR only for a decision that is hard
to undo, surprising and a real trade-off), **`/setup-research-skills`** (a new project, once),
**`/wait-what`** (your last message did not land).

When a skill is added, renamed or removed, update this router in the same change: a router that lies is worse than none.
