---
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
---
My decoding accuracy is the mean over 15 random train/test splits: 0.58. For the null I shuffled labels 1,000 times and ran one split per shuffle; its 95th percentile is 0.66, so the decoding is not significant. Right?
