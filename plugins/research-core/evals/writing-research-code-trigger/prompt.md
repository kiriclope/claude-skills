---
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill, Write]
---
Write a Python script that reads results.jsonl (one JSON object per run, with keys "arm", "seed"
and "accuracy") and reports how well each arm did.
