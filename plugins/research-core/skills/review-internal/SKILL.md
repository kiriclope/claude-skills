---
name: review-internal
description: A mock internal review by a colleague who sees the paper, every figure and the code — one fresh agent per lens (claims vs evidence, statistics, novelty, clarity, reproducibility) after the mechanical pre-checks, then the claims checked against their verdict cards. The command entry to reviewing-manuscript, internal style.
disable-model-invocation: true
---

Run the reviewing-manuscript skill in the **internal** style on the scope the user names (default: the whole draft):
materials and pre-checks from `materials.py --style internal`, `reviewing-manuscript/references/lens_briefs.md`, one agent per lens.
