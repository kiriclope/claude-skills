---
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
---
I keep the 50 neurons with the largest sample selectivity (t-test on all trials), then decode the sample with 10-fold cross-validation: 0.91 accuracy. Shuffled labels give 0.50. Good result?
