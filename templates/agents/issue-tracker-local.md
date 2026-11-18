# Issue tracker: Local Markdown

Specs and tickets for this repo live as markdown files in `.scratch/` (this repo has no GitHub remote). Adapted from
mattpocock/skills (setup-matt-pocock-skills/issue-tracker-local.md, 5863806, MIT); the research conventions are in
`docs/agents/research.md`.

## Conventions

- One spec per directory: `.scratch/<spec-slug>/`
- The spec is `.scratch/<spec-slug>/spec.md`
- Tickets are one file per ticket at `.scratch/<spec-slug>/issues/<NN>-<slug>.md`, numbered from `01` in dependency order, never a single combined tickets file
- Near the top of each ticket: a `Status:` line (a label from `triage-labels.md`, or `claimed`, `paused`, `closed`) and a `Blocked by: NN, NN` line
- Comments and conversation history append to the bottom of the file under a `## Comments` heading

## Frontier

Files under `.scratch/<spec-slug>/issues/` that are not `claimed`, `paused` or `closed`, and whose every `Blocked by`
ticket is `closed`; first by number wins.

- **Claim**: set `Status: claimed` and save before any work.
- **Close**: append the outcome under `## Comments` (the verdict card's heading and where it is), then set `Status: closed`.

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/<spec-slug>/` (creating the directory if needed).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the ticket number directly.
