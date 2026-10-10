---
type: llm
weight: 1
---

The response says that dual_dpa cannot show retention because the Dual stage retrains the memory (rank 0), so damage done by GNG is hidden; it asks for after_gng/dpa (DPA accuracy right after GNG) seed by seed for both arms before ranking them, and notes that arm C may well be the worst on that metric.
