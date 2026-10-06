# Hooks — the rules that must never be skipped

Skills are advice; hooks are enforced by the harness. `guard_bash.py` (PreToolUse on Bash):

| Command | Decision |
|---|---|
| `git push` | **ask** the user every time |
| `git commit -m …` without a `Co-Authored-By:` trailer | **deny** |
| `python sweep.py` / `rerun_dual.py` not inside `screen -dmS` | **deny** |
| `git commit` while a review checkpoint is due (projects with `review_checkpoint:`) | **deny** until the checkpoint |

## Review checkpoints (Stop hook)

`plugins/research-core/skills/running-review-checkpoints/scripts/review_status.py --hook stop` blocks
the end of a turn when a human review is due in the session's project (≥ `max_lines` changed lines or
≥ `max_commits` commits since the last review, set per project under `review_checkpoint:` in
`.claude/project.yaml`), so Claude runs the checkpoint. It never blocks twice in a row, stays silent
in projects that have not opted in, and the user can say "not now" (`--defer`). Switch it off per
project (`review_status.py --off`, local) or everywhere (`--off --global`); `--on` resumes. Add to
`~/.claude/settings.json`, next to the PreToolUse entry:

```json
"Stop": [
  { "hooks": [ { "type": "command", "timeout": 30,
      "command": "python3 ~/claude-skills/plugins/research-core/skills/running-review-checkpoints/scripts/review_status.py --hook stop" } ] }
]
```

Launcher names: env `GUARD_LAUNCHERS` (comma-separated regexes). Self-test: `python guard_bash.py --demo`.

## Install (user-level, all projects) — add to `~/.claude/settings.json`

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "python3 ~/claude-skills/hooks/guard_bash.py", "timeout": 10 }
        ]
      }
    ]
  }
}
```
Merge with any existing `hooks` block rather than replacing it. Run `/hooks` in Claude Code to confirm it loaded.
