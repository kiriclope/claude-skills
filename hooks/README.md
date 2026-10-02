# Hooks — the rules that must never be skipped

Skills are advice; hooks are enforced by the harness. `guard_bash.py` (PreToolUse on Bash):

| Command | Decision |
|---|---|
| `git push` | **ask** the user every time |
| `git commit -m …` without a `Co-Authored-By:` trailer | **deny** |
| `python sweep.py` / `rerun_dual.py` not inside `screen -dmS` | **deny** |

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
