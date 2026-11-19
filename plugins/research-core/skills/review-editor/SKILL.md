---
name: review-editor
description: A mock desk read by the journal's handling editor — send out or desk-reject, fit, novelty, format against the journal's current guide, and the three referees the editor would invite. The command entry to reviewing-manuscript, editor style.
disable-model-invocation: true
---

Run the reviewing-manuscript skill in the **editor** style on the scope the user names (default: the whole draft):
materials from `materials.py --style editor`, `reviewing-manuscript/references/editor_brief.md`, a second model for a submission. The
review file keeps the editor's referee table: `/review-referee` takes its personas from there.
