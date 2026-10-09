# Hooks — the rules that must never be skipped, and the session board

Skills are advice; hooks are enforced by the harness. `guard_bash.py` (PreToolUse on Bash):

| Command | Decision |
|---|---|
| `git push` | **ask** the user every time |
| `git commit -m …` without a `Co-Authored-By:` trailer | **deny** |
| the project's training launcher in the foreground (not in `screen -dmS`, `tmux -d`, `sbatch`/`qsub`, `nohup … &`, or `--per_run_screen`) | **deny** |
| `git commit` while a review checkpoint is due (projects with `review_checkpoint:`) | **deny** until the checkpoint |
| `git commit` that would commit clear mess (projects with `.claude/project.yaml`): a `never_stage` path, a force-added ignored file, editor junk, a file over `large_file_mb`, a `_v2` / `_old` copy of code | **deny**: unstage or fix; `TIDY_OK=1` prefix only for files the user named |
| `git commit` that includes a file another Claude Code session changed in the last hour and has not committed (the session board, below) | **ask** the user, naming that session |

The push and trailer rules apply in every session. Launchers are read from the project's
`.claude/project.yaml` (`launch.entrypoints`, or `launch.entrypoint`), else the `GUARD_LAUNCHERS`
env var (comma-separated names), else `sweep.py` and `rerun_dual.py`. Only commands are matched:
commit messages and heredoc bodies are removed first, and a launcher counts only where a command
starts. The tidy check is `project_audit.py --staged` (organizing-projects): it sees `git add …`
earlier in the same command and `git commit -a` by replaying them on a throwaway copy of the index,
blocks only the clear-mess items, and leaves its proposals (README lines, unindexed docs, scratch
files) to log-and-ship. Off per project with `organize: {commit_check: false}`.

## Review checkpoints (Stop hook)

`plugins/research-core/skills/running-review-checkpoints/scripts/review_status.py --hook stop` blocks
the end of a turn when a human review is due in the session's project (≥ `max_lines` changed lines or
≥ `max_commits` commits since the last review, set per project under `review_checkpoint:` in
`.claude/project.yaml`), so Claude runs the checkpoint. It never blocks twice in a row, stays silent
in projects that have not opted in, and the user can say "not now" (`--defer`). Switch it off per
project (`review_status.py --off`, local) or everywhere (`--off --global`); `--on` resumes. Its
`Stop` entry is in the install block below.

## Session board (parallel sessions)

Several sessions often work at once (a background job per paper, an interactive one, a sweep monitor),
sometimes in the same repository. `session_board.py` keeps `~/.claude/active_sessions.json` (private,
mode 600) up to date, so each session knows the others:

- **SessionStart**: the session registers (its name from the background-job list, the one `SendMessage`
  takes, else its first prompt; folder, repository, branch) and is told which other sessions are live
  (seen in the last day), those in its repository first, with the files they changed and have not committed.
- **PostToolUse**: the files each Edit / Write / NotebookEdit changed are recorded, and for a Bash command
  the pending files of the repositories it ran in that changed after it started (PreToolUse notes the
  start; read-only commands are skipped). When another session changed the same file in the last hour and
  has not committed it since, the session is told who, once per file.
- **The guard** asks the user before a commit that includes such a file, naming the session.
- **resume_brief.py** (resuming-work) lists the live sessions in its SESSIONS section.

`python ~/claude-skills/hooks/session_board.py --list` shows the board, `--who <file>` who changed a file.
A Bash attribution is a guess from modification times, said so in the messages. Nothing is blocked
by the board itself: only the commit guard asks. Self-test: `python session_board.py --demo` (10 checks,
including twelve concurrent hooks).

Self-test of the guard: `python guard_bash.py --demo` (32 cases, including the false positives fixed in
0.8, the tidy check and the session board).

## Install (user-level, all projects) — add to `~/.claude/settings.json`

```json
{
  "hooks": {
    "SessionStart":     [ { "hooks": [ { "type": "command", "timeout": 10, "command": "python3 ~/claude-skills/hooks/session_board.py" } ] } ],
    "UserPromptSubmit": [ { "hooks": [ { "type": "command", "timeout": 10, "command": "python3 ~/claude-skills/hooks/session_board.py" } ] } ],
    "PreToolUse": [
      { "matcher": "Bash",
        "hooks": [ { "type": "command", "timeout": 10, "command": "python3 ~/claude-skills/hooks/guard_bash.py" },
                   { "type": "command", "timeout": 10, "command": "python3 ~/claude-skills/hooks/session_board.py" } ] }
    ],
    "PostToolUse": [
      { "matcher": "Bash|Edit|Write|MultiEdit|NotebookEdit",
        "hooks": [ { "type": "command", "timeout": 10, "command": "python3 ~/claude-skills/hooks/session_board.py" } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "timeout": 30,
          "command": "python3 ~/claude-skills/plugins/research-core/skills/running-review-checkpoints/scripts/review_status.py --hook stop" } ] }
    ],
    "SessionEnd":       [ { "hooks": [ { "type": "command", "timeout": 10, "command": "python3 ~/claude-skills/hooks/session_board.py" } ] } ]
  }
}
```
The guard alone is the PreToolUse `guard_bash.py` entry; the session board is every `session_board.py`
entry. Merge with any existing `hooks` block rather than replacing it. Run `/hooks` in Claude Code to confirm it loaded.
