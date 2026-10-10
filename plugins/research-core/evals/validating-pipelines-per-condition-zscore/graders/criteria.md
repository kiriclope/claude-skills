---
type: llm
weight: 1
---

The response points out that z-scoring each condition separately subtracts each condition's own mean, which removes exactly the A vs B difference being measured, so a near-zero distance is built in. It proposes planting a known A-B difference in synthetic data and running the real pipeline to show the shrinkage, normalizing across conditions jointly instead, and stating the smallest detectable effect before any "not encoded" claim.
