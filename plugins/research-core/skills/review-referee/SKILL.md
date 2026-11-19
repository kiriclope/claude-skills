---
name: review-referee
description: Mock external referee reports — one fresh agent per referee persona (from the latest editor review or project.yaml), each seeing only the submission package the journal would send, each writing a journal-form report with a recommendation; then merged as an editor would. The command entry to reviewing-manuscript, referee style.
disable-model-invocation: true
---

Run the reviewing-manuscript skill in the **referee** style on the scope the user names (default: the whole draft):
materials from `materials.py --style referee` (`--share-code` only when the user says the journal sends code),
`reviewing-manuscript/references/referee_brief.md`, one agent per persona. Without an editor review or `referees` in project.yaml, propose
running `/review-editor` first, or ask the user for the three personas.
