---
name: conclude
description: Conclude one research question across its verdict cards, and check the spec's user stories against them. The command entry to the concluding-research skill.
disable-model-invocation: true
---

Run the concluding-research skill on the question the user names (or, without one, the question with the most cards
since its last conclusion: `collect_cards.py --since`). When the question has a spec, end with its user stories
answered / open / failed and the open ones proposed as the next tickets (`/to-tickets`), not posted.
