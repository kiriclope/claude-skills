#!/usr/bin/env python3
"""PreToolUse hook for Bash — the rules that must never be skipped (skills are only advice).

Every session:
  * `git push`                    → ask the user every time (push only on an explicit "push it")
  * `git commit` whose message lacks a `Co-Authored-By:` trailer
                                  → deny: add the trailer from the session's attribution reminder
Per project:
  * a training launcher run in the foreground → deny: run it detached (screen -dmS, tmux -d, a
    scheduler such as sbatch/qsub, nohup … &, or the launcher's own --per_run_screen mode).
    Launchers = `launch.entrypoints` (or `launch.entrypoint`) in .claude/project.yaml, else the
    GUARD_LAUNCHERS env var (comma-separated names), else sweep.py and rerun_dual.py.
  * `git commit` while a human review checkpoint is due in that repository (projects that opted in
    with `review_checkpoint:`) → deny: run the running-review-checkpoints skill first.

Only commands are matched, never text: commit messages and heredoc bodies are removed first, and a
launcher counts only where a command starts (after ;, &&, ||, |, (, a newline or `bash -c '`).
Install: see hooks/README.md. Test: python guard_bash.py --demo
"""
import json
import os
import re
import sys
import tempfile

DEFAULT_LAUNCHERS = ["sweep.py", "rerun_dual.py"]
REVIEW_STATUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "plugins", "research-core", "skills",
                             "running-review-checkpoints", "scripts")

HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?\n[ \t]*\2\b", re.S)          # body of a heredoc
MESSAGE = re.compile(r"(?:\s-m|--message)(?:=|\s+)(\"(?:[^\"\\]|\\.)*\"|'[^']*'|\S+)", re.S)  # a commit message
CMD_START = r"(?:^|[;&|(\n]|\$\(|\bdo\b|\bthen\b|\belse\b)\s*"
BASH_C = r"\b(?:bash|sh|zsh)\s+(?:-\w+\s+)*-c\s+[\"']\s*"
PREFIXES = r"(?:\w+=(?:\"[^\"]*\"|'[^']*'|\S+)\s+|(?:time|nice|env|exec|stdbuf)\s+)*"
DETACHED = re.compile(r"\bscreen\s+-d?m|\btmux\s+new(?:-session)?\b[^;&|\n]*\s-d\b|\b(?:sbatch|qsub|bsub)\b|\bsetsid\b"
                      r"|--per_run_screen\b")


def _strip_text(cmd):
    """The command with heredoc bodies and commit messages removed: what is left is code, not prose."""
    return MESSAGE.sub(" ", HEREDOC.sub("<<HEREDOC", cmd))


def _at_command(code, word_re):
    return re.search(rf"(?:{CMD_START}|{BASH_C}){PREFIXES}{word_re}", code, re.M)


def _project_cfg(cwd):
    d = os.path.abspath(cwd) if cwd else None
    while d:
        p = os.path.join(d, ".claude", "project.yaml")
        if os.path.exists(p):
            try:
                import yaml
                return yaml.safe_load(open(p)) or {}
            except Exception:
                return {}
        if os.path.dirname(d) == d:
            return {}
        d = os.path.dirname(d)
    return {}


def launchers_for(cwd):
    env = os.environ.get("GUARD_LAUNCHERS")
    if env:
        return [s.strip() for s in env.split(",") if s.strip()]
    launch = _project_cfg(cwd).get("launch") or {}
    names = launch.get("entrypoints") or ([launch["entrypoint"]] if launch.get("entrypoint") else [])
    return names or DEFAULT_LAUNCHERS


def _commit_dir(c, cwd):
    """Directory the commit runs in: `git -C <dir> commit`, `cd <dir> && … git commit`, else the session cwd."""
    m = re.search(r"git\s+-C\s+(\S+)\s+commit\b", c) or re.search(r"\bcd\s+(\S+)\s*(&&|;)[^;&]*git\s+commit\b", c)
    d = os.path.expanduser(m.group(1).strip("'\"")) if m else cwd
    return d if d and os.path.isabs(d) else (os.path.join(cwd, d) if cwd and d else cwd)


def review_due(c, cwd):
    """(due, message) for the repository of a `git commit`, or (False, "") when checkpoints are off there."""
    if not cwd or not os.path.isdir(REVIEW_STATUS):
        return False, ""
    sys.path.insert(0, REVIEW_STATUS)
    try:
        import review_status as rs
        root = rs.repo_root(_commit_dir(c, cwd) or cwd)
        s = rs.checkpoint_due(root) if root else None      # None when off (local or global) or not opted in
    except Exception:                                   # never let the gate crash the hook
        return False, ""
    if not s or not s["due"]:
        return False, ""
    return True, (f"Review checkpoint due in {os.path.basename(root)} ({s['lines']} changed lines, "
                  f"{len(s['commits'])} commits since the user's last review): run the running-review-checkpoints "
                  "skill before committing — or review_status.py --defer if the user says not now.")


def _launcher_issue(code, cwd):
    for name in launchers_for(cwd):
        pat = name if "\\" in name else re.escape(name)
        for m in re.finditer(rf"(?:{CMD_START}|{BASH_C}){PREFIXES}(?:\S*/)?python3?\s+(?:-\S+\s+)*(?:\S*/)?{pat}\b",
                             code, re.M):
            rest = code[m.end():]
            end = re.search(r";|\n|&&|\|\|", rest)
            segment = rest[:end.start()] if end else rest
            if re.search(r"\s(-h|--help)\b", segment):
                continue
            background = re.search(r"(?<![&>])&(?![&>\d])", segment)
            if DETACHED.search(code) or background:
                continue
            return (f"{name} must run detached: screen -dmS <name> bash -c \"… 2>&1 | tee <run_dir>/train.log\", "
                    "a scheduler (sbatch, qsub), nohup … &, or the launcher's --per_run_screen mode. "
                    "Never in the foreground.")
    return None


def decide(cmd, cwd=None):
    """Return (decision, reason) or None. decision ∈ {"ask", "deny"}."""
    code = _strip_text(cmd)
    if _at_command(code, r"git\s+(?:-C\s+\S+\s+)?push\b"):
        return "ask", "git push: confirm the user explicitly asked to push."
    is_commit = _at_command(code, r"git\s+(?:-C\s+\S+\s+)?commit\b")
    c = " ".join(cmd.split())
    if is_commit and re.search(r"\s(-m|--message|-F|--file)\b|<<", c) \
            and "--amend --no-edit" not in c and "Co-Authored-By:" not in c:
        return "deny", "git commit: the message must end with the Co-Authored-By trailer from the attribution reminder."
    if is_commit:
        due, why = review_due(c, cwd)
        if due:
            return "deny", why
    why = _launcher_issue(code, cwd)
    if why:
        return "deny", why
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    verdict = decide(payload.get("tool_input", {}).get("command", ""), payload.get("cwd"))
    if verdict:
        decision, reason = verdict
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": decision,
                                                 "permissionDecisionReason": reason}}))
    return 0


def _demo():
    trailer = "\n\nCo-Authored-By: X <noreply@anthropic.com>"
    cases = [
        ("git push origin main", None, "ask"),
        ("cd ~/rnn && git push", None, "ask"),
        ("git status && git log --oneline -3", None, None),
        ("git commit -m 'fix'", None, "deny"),
        ("git commit -m \"$(cat <<'EOF'\nfix" + trailer + "\nEOF\n)\"", None, None),
        ("python sweep.py --out_dir results/dual/x --n_gpus 2", None, "deny"),
        ("screen -dmS sweep_x bash -c \"python sweep.py --out_dir r --per_run_screen 2>&1 | tee r/launch.log\"", None, None),
        ("python sweep.py --help", None, None),
        ("python plot_sweep.py --sweep_dir results/dual/x", None, None),
        ("echo 'git pushing is fine in a string?'", None, None),
        # false positives found in review: text is not a command
        ("git commit -m \"Fix: python sweep.py now resumes; git push later" + trailer + "\"", None, None),
        ("cat <<'EOF' | wc -l\npython sweep.py --out_dir r\nEOF", None, None),
        ("grep -n \"python sweep.py\" CLAUDE.md", None, None),
        # detached forms are allowed; real foreground launches are still caught
        ("sbatch --wrap \"python sweep.py --out_dir r\"", None, None),
        ("nohup python sweep.py --out_dir r > r/log 2>&1 &", None, None),
        ("python sweep.py --out_dir r --n_gpus 2 --per_run_screen", None, None),
        ("LD_PRELOAD=/x/libstdc++.so.6 python sweep.py --out_dir r", None, "deny"),
        ("cd ~/rnn\npython -u rerun_dual.py --sweep_dir x", None, "deny"),
        ("python sweep.py --out_dir r 2>&1 | tee r/log", None, "deny"),
    ]
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, ".claude"))
        open(os.path.join(d, ".claude", "project.yaml"), "w").write("launch:\n  entrypoint: train.py\n")
        cases += [("python train.py --seed 0", d, "deny"),                       # the project's own launcher
                  ("python sweep.py --out_dir r", d, None)]                      # not a launcher in that project
        bad = 0
        for cmd, cwd, want in cases:
            got = decide(cmd, cwd); got = got[0] if got else None
            ok = got == want; bad += not ok
            print(f"{'✓' if ok else '✗'} {want!s:5} {got!s:5} {cmd.splitlines()[0][:70]}")
    print(f"SUMMARY: {len(cases) - bad}/{len(cases)} cases correct")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(_demo() if "--demo" in sys.argv else main())
