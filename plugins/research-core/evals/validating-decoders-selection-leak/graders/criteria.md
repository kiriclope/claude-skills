---
type: llm
weight: 1
---

The response points out that selecting neurons on all trials, before the split, uses the labels of the test trials, so the score is inflated (leakage), and that a shuffle null that does not repeat the selection on the shuffled labels cannot reveal this. It asks to move the selection inside each training fold and to check that pure noise run through the full pipeline decodes at chance.
