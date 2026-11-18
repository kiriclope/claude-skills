# Issue tracker: GitHub

Specs and tickets for this repo live as GitHub issues (repo: {owner}/{repo}, private). Use the `gh` CLI (≥ 2.94) for all
operations. Adapted from mattpocock/skills (setup-matt-pocock-skills/issue-tracker-github.md, 5863806, MIT); the research
conventions are in `docs/agents/research.md`.

## Conventions

- **Create an issue**: `gh issue create --title "..." --body "..." --label "spec:{name}"`. Use a heredoc for multi-line bodies.
  Every issue of a spec carries its `spec:{name}` label (several projects may share one repo).
- **Read an issue**: `gh issue view <number> --json number,title,body,labels,comments,assignees`.
- **List a spec's issues**: `gh issue list --label "spec:{name}" --state open --json number,title,labels,assignees`.
- **Make an issue a sub-issue of a parent**: `gh issue create --parent <parent> ...`, or `gh issue edit <parent> --add-sub-issue <child>`.
- **Blocking**: GitHub's native issue dependencies. `gh issue create --blocked-by <n>,<n> ...` or
  `gh issue edit <child> --add-blocked-by <blocker>`. A ticket is unblocked when every blocker is closed.
- **Count open blockers**: `gh issue view <n> --json blockedBy --jq '[.blockedBy.nodes[] | select(.state == "OPEN")] | length'` (0: startable).
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Claim**: `gh issue edit <n> --add-assignee @me`, the session's first write on the ticket.
- **Close**: post the explanation with `gh issue comment <number> --body "..."`, then `gh issue close <number>`.

Infer the repo from `git remote -v`. Before the first `gh issue create` of a session, check the target with
`gh repo view --json nameWithOwner,visibility` and stop if it is not this project's private repo.

## Frontier

The spec's open tickets (`--label "spec:{name}"`), minus any with an open blocker, an assignee, or the `paused` label;
first by number wins.

## When a skill says "publish to the issue tracker"

Create a GitHub issue, after the user approved the content in this session.

## When a skill says "fetch the relevant ticket"

Read it as in **Read an issue** above.
