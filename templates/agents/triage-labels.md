<!-- From mattpocock/skills (setup-matt-pocock-skills/triage-labels.md, 5863806, MIT), with the research additions at the end. -->
# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

Edit the "Label in our tracker" column to match whatever vocabulary you actually use.

## Research additions (docs/agents/research.md)

| Label | Meaning |
| --- | --- |
| `spec:<name>` | Every issue of one spec (several projects may share one repo) |
| `paused` | Waits on a ticket that failed or was refuted; the user decides whether to cancel, change or resume it |
