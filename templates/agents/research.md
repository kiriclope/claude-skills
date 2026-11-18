# Research meanings of the spec and ticket skills

`/to-spec` and `/to-tickets` are Matt Pocock's, unchanged, written for software. In this research project their terms
mean the following. Where this file and the skill disagree, this file wins.

## The grilling (`/grill-research`)

- The **design tree** is the destination's decisions: the claim and its wording, which result carries it, the
  measures that decide, the figures, what is out of scope. Facts (what a card measured, what a run used) are looked
  up in the verdict log, the conclusions doc and the code, never asked.
- Run it before `/to-spec`, in the same context window; for a project already underway, after reading its state.
- **ADRs** (`docs/adr/`) only for a decision that is hard to undo, surprising without context and a real trade-off
  (a scoring rule, an optimizer, a convention every run depends on); a result is never an ADR, it is a verdict card.

## The spec (`/to-spec`)

- **Problem Statement**: the research question, and why it matters now.
- **Solution**: the destination: what will exist when the spec is done (e.g. a paper's figures, one line each with its
  status: exists / assemble / pending).
- **User Stories**: reader stories. "As a reviewer, I want <a test or a number>, so that <the claim it lets me
  believe>". Actors: reviewer, reader, the user, a colleague who reruns the code.
- **Implementation Decisions**: decisions already taken (task, model, recipe, scoring, what is fixed), each citing the
  verdict card or the date it comes from. Sources that disagree become a question to the user, never a line.
- **Testing Decisions**: the measures that decide, each with its criterion and the card or date it comes from. His
  "seams" step: agree with the user which measure answers each story before writing the tickets.
- **Out of Scope**: the levers and questions not pursued under this spec.
- **Further Notes**: anything undecided is marked **GAP**.
- Publishing: create the spec's label first (`gh label create spec:<name>`), put it on the parent issue and on every
  ticket.
- The parent spec issue gets **no `ready-for-agent` label** (an agent polling for it would try to run the whole spec).

## Tickets (`/to-tickets`)

- A **tracer bullet** is the smallest run that gives one verdict end to end: one arm, or one analysis, or one figure,
  or one section of text. Kinds: experiment / build / analysis / writing.
- **What to build**: for an experiment, the question, the arms, and the parameter table with its GPU plan (one approval
  covers every launch of the spec); for the others, the deliverable.
- **Acceptance criteria**: the criterion of the pre-run card, written before the run. Every ticket names the user stories
  it answers.
- **Blocked by**: a ticket waits on another's *result* or *code*, never on a guess about the result.
- **HITL / AFK**: an approval, a choice of figure or a verdict that changes the next run is HITL (`ready-for-human`); a
  build, an analysis on approved runs, or an approved launch is AFK (`ready-for-agent`).

## Working the tickets

- A session claims a ticket (assign it) before its first write, then writes its pre-run card naming the ticket.
- **A ticket closes with its verdict, refuted or not.** The closing comment links the verdict card. A refuted ticket is
  a result, never reopened.
- **A failed or refuted ticket pauses its dependents**: label each `paused` with a comment saying which premise changed,
  and bring them to the user, who cancels, changes or resumes them.
- A lever that answers no user story is drift: propose a ticket for it, or drop it.
- A new destination is a new spec, not more tickets on the old one.
- The results stay in the repo (verdict cards, docs/conclusions); the tracker holds only where the work stands.

## Labels

- His four triage labels (`triage-labels.md`), plus `spec:<name>` on every issue of a spec and `paused`.
