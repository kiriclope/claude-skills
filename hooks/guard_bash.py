#!/usr/bin/env python3
"""PreToolUse hook for Bash — the rules that must never be skipped (skills are only advice).

  * `git push`                    → ask the user every time (push only on an explicit "push it")
  * a sweep/training launcher run in the foreground (not inside `screen -dmS`)
                                  → deny: one detached screen per seed, tee'd log
  * `git commit` whose message lacks a `Co-Authored-By:` trailer
                                  → deny: add the trailer from the session's attribution reminder

Launcher names come from GUARD_LAUNCHERS (comma-separated regexes), default "sweep.py,rerun_dual.py".
Install: see hooks/README.md. Test: python guard_bash.py --demo
"""
import json
import os
import re
import sys

LAUNCHERS = [s.strip() for s in os.environ.get("GUARD_LAUNCHERS", r"sweep\.py,rerun_dual\.py").split(",") if s.strip()]


def decide(cmd):
    """Return (decision, reason) or None. decision ∈ {"ask", "deny"}."""
    c = " ".join(cmd.split())
    if re.search(r"(^|[;&|(]\s*|\s)git\s+push\b", c):
        return "ask", "git push: confirm the user explicitly asked to push."
    if re.search(r"(^|[;&|(]\s*|\s)git\s+commit\b", c) and re.search(r"\s(-m|--message|-F|--file)\b|<<", c) \
            and "--amend --no-edit" not in c and "Co-Authored-By:" not in c:
        return "deny", "git commit: the message must end with the Co-Authored-By trailer from the attribution reminder."
    for pat in LAUNCHERS:
        if re.search(rf"\bpython3?\s+(\S*/)?{pat}", c) and not re.search(r"\s(-h|--help)\b", c):
            if "screen -dmS" not in c:
                return "deny", (f"{pat.replace(chr(92), '')} must run detached: "
                                "screen -dmS <name> bash -c \"... 2>&1 | tee <run_dir>/train.log\" "
                                "(or the launcher's --per_run_screen mode). Never in the foreground.")
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if payload.get("tool_name") != "Bash":
        return 0
    verdict = decide(payload.get("tool_input", {}).get("command", ""))
    if verdict:
        decision, reason = verdict
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "permissionDecision": decision,
                                                 "permissionDecisionReason": reason}}))
    return 0


def _demo():
    cases = [
        ("git push origin main", "ask"),
        ("cd ~/rnn && git push", "ask"),
        ("git status && git log --oneline -3", None),
        ("git commit -m 'fix'", "deny"),
        ("git commit -m \"$(cat <<'EOF'\nfix\n\nCo-Authored-By: X <noreply@anthropic.com>\nEOF\n)\"", None),
        ("python sweep.py --out_dir results/dual/x --n_gpus 2", "deny"),
        ("screen -dmS sweep_x bash -c \"python sweep.py --out_dir r --per_run_screen 2>&1 | tee r/launch.log\"", None),
        ("python sweep.py --help", None),
        ("python plot_sweep.py --sweep_dir results/dual/x", None),
        ("echo 'git pushing is fine in a string?'", None),
    ]
    bad = 0
    for cmd, want in cases:
        got = decide(cmd); got = got[0] if got else None
        ok = got == want; bad += not ok
        print(f"{'✓' if ok else '✗'} {want!s:5} {got!s:5} {cmd.splitlines()[0][:70]}")
    print(f"SUMMARY: {len(cases) - bad}/{len(cases)} cases correct")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(_demo() if "--demo" in sys.argv else main())
