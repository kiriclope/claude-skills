---
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
---
To remove firing-rate drift I z-score each condition (sample A trials, sample B trials) separately before computing the distance between the A and B population means. The distance is near zero in every session, so the sample is not encoded in this area. Correct?
