#!/usr/bin/env python3
"""Session board: which Claude Code session is working on what, so that parallel sessions know about each other.

Hooks keep a board file up to date (install: hooks/README.md):
  SessionStart       register the session (name, folder, repository, branch); tell it which other sessions
                     are live, those in its own repository first, with the files they changed and have not committed
  UserPromptSubmit   first and last prompt, last-seen time, branch
  PreToolUse  Bash   note when the command started
  PostToolUse        record the files an Edit / Write / MultiEdit / NotebookEdit changed, and the files a Bash
                     command changed (pending files in the repositories it ran in, modified after it started);
                     when another session changed the same file in the last hour and has not committed it since,
                     tell this session who it was (once per file and session)
  SessionEnd         mark the session ended (dropped from the board an hour later)
Readers: the commit guard (guard_bash.py) asks the user before a commit that includes such a file;
resume_brief.py (resuming-work) lists the live sessions.

A session's name is the one the background-job list (~/.claude/jobs/*/state.json) gives it, the name
SendMessage takes; interactive sessions without one show their first prompt. Bash attribution is a best
guess (modification times): another session's file changed during the command counts as this one's
unless that session recorded it with an Edit first. Deleted files are not attributed.

Usage:
  python session_board.py --list [--repo PATH]     live sessions, newest first, and their uncommitted files
  python session_board.py --who PATH [PATH ...]    which sessions changed these files, and when
  python session_board.py --demo                   self-test on a throwaway board and repository
  python session_board.py < payload.json           the hook (what settings.json runs)
Board file: $SESSION_BOARD, else ~/.claude/active_sessions.json (private, mode 600). The hook never blocks
anything and always exits 0.
"""
import contextlib
import fcntl
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import time

RECENT_S = 3600             # a change counts as someone's work in progress for an hour
LIVE_S = 24 * 3600          # a session unseen for a day is dropped, with its changes
ENDED_S = 3600              # an ended session stays on the board for an hour
MAX_BASH_FILES = 100        # a Bash command that changed more files records the newest only
MAX_SHOWN = 6               # sessions listed at SessionStart
MTIME_SLACK = 0.05          # file times use the kernel's coarse clock, a few ms behind time.time()
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
READ_ONLY = re.compile(r"\s*(?:cd|ls|cat|head|tail|less|wc|grep|rg|find|echo|printf|pwd|which|file|stat|du|df|tree"
                       r"|diff|ps|date|nvidia-smi|screen\s+-ls|sed\s+-n|git\s+(?:-C\s+\S+\s+)?(?:status|log|diff|show"
                       r"|branch|remote|rev-parse|ls-files|blame|grep|fetch))\b")
WRITES = re.compile(r"(?<![\d&])>(?!&|\s*/dev/null)|\s-delete\b|\s-exec\b|\btee\b")


def board_path():
    return os.environ.get("SESSION_BOARD") or os.path.expanduser("~/.claude/active_sessions.json")


def jobs_dir():
    return os.environ.get("SESSION_BOARD_JOBS") or os.path.expanduser("~/.claude/jobs")


def load(path=None):
    try:
        with open(path or board_path()) as f:
            b = json.load(f)
    except (OSError, ValueError):
        b = {}
    b.setdefault("sessions", {})
    b.setdefault("touches", {})        # {absolute path: {session id: [time, "edit" | "bash"]}}
    return b


def _prune(b, now):
    for sid, s in list(b["sessions"].items()):
        if now - s.get("last_seen", 0) > LIVE_S or (s.get("ended") and now - s["ended"] > ENDED_S):
            del b["sessions"][sid]
    for p, who in list(b["touches"].items()):
        for sid in [k for k, (ts, _) in who.items() if k not in b["sessions"] or now - ts > LIVE_S]:
            del who[sid]
        if not who:
            del b["touches"][p]


@contextlib.contextmanager
def _edit(now):
    """The board, locked for a read-modify-write, then pruned and written back atomically."""
    path = board_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        b = load(path)
        yield b
        _prune(b, now)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".session_board")
        with os.fdopen(fd, "w") as f:
            json.dump(b, f, indent=1)
        os.replace(tmp, path)


# ── git and names ───────────────────────────────────────────────────────────────────────────────

def _git(d, *args):
    try:
        r = subprocess.run(["git", "-C", d, *args], capture_output=True, text=True, timeout=5,
                           stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return r.stdout if r.returncode == 0 else ""


def _toplevel(d):
    top = _git(d, "rev-parse", "--show-toplevel").strip() if d and os.path.isdir(d) else ""
    return os.path.realpath(top) if top else ""


def _pending_files(root):
    """Absolute paths of the files `git status` shows as changed or untracked (a rename's old path left out)."""
    toks, out, i = _git(root, "status", "--porcelain", "-z", "--untracked-files=all").split("\0"), [], 0
    while i < len(toks):
        t = toks[i]
        i += 1 + (len(t) > 3 and t[0] in "RC")          # a rename's old path follows it
        if len(t) > 3:
            out.append(os.path.join(root, t[3:]))
    return out


def _job_name(sid):
    for p in glob.glob(os.path.join(jobs_dir(), "*", "state.json")):
        try:
            with open(p) as f:
                d = json.load(f)
        except (OSError, ValueError):
            continue
        if d.get("sessionId") == sid:
            return d.get("name") or ""
    return ""


def _clip(s, n=70):
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[:n - 1] + "…"


def label(sid, s):
    name = s.get("name") or _clip(s.get("first_prompt") or "", 40)
    return f"'{name}' ({sid[:8]})" if name else f"session {sid[:8]}"


def _ago(ts, now):
    m = max(0, now - ts) / 60
    return f"{m:.0f} min ago" if m < 90 else f"{m / 60:.0f} h ago"


class _Pending:
    """Pending (uncommitted) files per repository, one `git status` each, and last-commit times per file."""

    def __init__(self):
        self.dirty = {}

    def settled(self, path, ts):
        """True when that change is no longer pending: the file is clean, or was committed after ts."""
        root = _toplevel(os.path.dirname(path))
        if not root:
            return False                                 # outside git: nothing to compare against
        if root not in self.dirty:
            self.dirty[root] = set(_pending_files(root))
        if path not in self.dirty[root]:
            return True
        ct = _git(root, "log", "-1", "--format=%ct", "--", os.path.relpath(path, root)).strip()
        return ct.isdigit() and int(ct) > ts


# ── what a tool call changed ────────────────────────────────────────────────────────────────────

def _read_only(cmd):
    if WRITES.search(cmd):
        return False
    parts = [p for p in re.split(r"&&|\|\||[;|\n]", cmd) if p.strip()]
    return bool(parts) and all(READ_ONLY.match(p) for p in parts)


def _bash_repos(cmd, cwd):
    """Repositories a command may have written in: the cwd, `cd` / `git -C` targets, absolute paths it names."""
    cands = [cwd] + re.findall(r"(?:\bcd|\bgit\s+-C)\s+([^\s;&|)'\"]+)", cmd) \
        + re.findall(r"(?<![\w.~/-])(~?/[\w.~/-]+)", cmd)
    roots, seen = [], set()
    for c in cands:
        c = os.path.expanduser(c or "")
        c = os.path.join(cwd, c) if cwd and not os.path.isabs(c) else c
        d = c if os.path.isdir(c) else os.path.dirname(c)
        if not d or d in seen:
            continue
        seen.add(d)
        r = _toplevel(d)
        if r and r not in roots:
            roots.append(r)
        if len(roots) >= 4 or len(seen) >= 12:
            break
    return roots


def _changed_since(roots, since):
    found = []
    for p in (q for r in roots for q in _pending_files(r)):
        try:
            m = os.lstat(p).st_mtime
        except OSError:
            continue
        if m >= since and not os.path.isdir(p):
            found.append((m, p))
    return [p for _, p in sorted(found, reverse=True)[:MAX_BASH_FILES]]


def _touched(p, s, now):
    tool, ti = p.get("tool_name"), p.get("tool_input") or {}
    if tool in EDIT_TOOLS:
        f = ti.get("file_path") or ti.get("notebook_path")
        return ([os.path.realpath(f)] if f else []), "edit"
    if tool == "Bash" and not _read_only(ti.get("command", "")):
        start = (s.get("bash_started") or {}).get(p.get("tool_use_id") or "-") or s.get("last_seen") or now
        return _changed_since(_bash_repos(ti.get("command", ""), p.get("cwd")), start - MTIME_SLACK), "bash"
    return [], ""


def foreign_touches(paths, sid, board=None, window=RECENT_S, now=None):
    """[(path, session id, session, time, via)] for each path another session changed within window and has not
    committed or reverted since (ended sessions included: their work is still someone else's). Absolute paths."""
    b, now, pend, hits = board or load(), now or time.time(), _Pending(), []
    for p in map(os.path.realpath, paths):
        for o, (ts, via) in (b["touches"].get(p) or {}).items():
            s = b["sessions"].get(o)
            if o != sid and s and now - ts <= window and not pend.settled(p, ts):
                hits.append((p, o, s, ts, via))
    return hits


def describe(hits, now, base=None):
    """One clause per hit: `x.py — 'name' (abcd1234), 12 min ago (live)`."""
    out = []
    for p, o, s, ts, via in hits:
        state = "ended" if s.get("ended") else "live"
        guess = ", by a Bash command" if via == "bash" else ""
        out.append(f"{os.path.relpath(p, base) if base else p} — {label(o, s)}, {_ago(ts, now)} ({state}{guess})")
    return out


# ── listing ─────────────────────────────────────────────────────────────────────────────────────

def session_lines(b, now, exclude=None, repo=None, limit=None):
    """Live sessions (not `exclude`), those in `repo` first, each with its pending changed files."""
    live = [(sid, s) for sid, s in b["sessions"].items() if sid != exclude and not s.get("ended")]
    live.sort(key=lambda x: (x[1].get("repo") != repo, -x[1].get("last_seen", 0)))
    pend, lines = _Pending(), []
    for sid, s in live[:limit]:
        where = os.path.basename(s.get("repo") or s.get("cwd") or "?")
        where += f" @ {s['branch']}" if s.get("branch") else ""
        prompt = f' · last prompt: "{_clip(s["last_prompt"], 60)}"' if s.get("last_prompt") else ""
        me = " (this session)" if sid == os.environ.get("CLAUDE_CODE_SESSION_ID") else ""
        lines.append(f"• {label(sid, s)}{me} · {where} · seen {_ago(s.get('last_seen', now), now)}{prompt}")
        mine = sorted(((ts, p) for p, who in b["touches"].items() for o, (ts, _) in who.items() if o == sid),
                      reverse=True)
        files = [os.path.relpath(p, s["repo"]) if s.get("repo") and p.startswith(s["repo"] + os.sep) else p
                 for ts, p in mine[:30] if not pend.settled(p, ts)]
        if files:
            more = f" … +{len(files) - 6}" if len(files) > 6 else ""
            lines.append(f"    changed, not committed: {', '.join(files[:6])}{more}")
    return lines, len(live)


def start_context(b, sid, repo, now):
    lines, n = session_lines(b, now, exclude=sid, repo=repo, limit=MAX_SHOWN)
    if not lines:
        return None
    more = f"\n  … and {n - MAX_SHOWN} more" if n > MAX_SHOWN else ""
    return ("Session board: other Claude Code sessions live on this machine\n  " + "\n  ".join(lines) + more +
            "\nBefore editing or committing a file another session changed and has not committed, ask its owner "
            "(SendMessage to its name) or the user. Full board: python " + os.path.abspath(__file__) + " --list")


# ── the hook ────────────────────────────────────────────────────────────────────────────────────

def on_event(p, now=None):
    """Update the board for one hook payload; return the additionalContext to give the session, or None."""
    ev, sid, now = p.get("hook_event_name"), p.get("session_id"), now or time.time()
    if not sid:
        return None
    snap = load()
    s0 = snap["sessions"].get(sid, {})
    paths, via = _touched(p, s0, now) if ev == "PostToolUse" else ([], "")
    if via == "bash":                          # a file another session recorded exactly, during the command, is theirs
        start = (s0.get("bash_started") or {}).get(p.get("tool_use_id") or "-", now)
        paths = [q for q in paths if not any(o != sid and v == "edit" and ts >= start
                                             for o, (ts, v) in (snap["touches"].get(q) or {}).items())]
    hits = [h for h in foreign_touches(paths, sid, snap, now=now) if f"{h[0]}|{h[1]}" not in s0.get("warned", [])]
    cwd = p.get("cwd") or s0.get("cwd") or ""
    fresh = ev in ("SessionStart", "UserPromptSubmit") or cwd != s0.get("cwd")
    root = _toplevel(cwd) if fresh else s0.get("repo", "")
    branch = _git(root, "branch", "--show-current").strip() if fresh and root else s0.get("branch", "")
    name = s0.get("name") or _job_name(sid)
    with _edit(now) as b:
        s = b["sessions"].setdefault(sid, {"started": now})
        s.update(cwd=cwd, repo=root, branch=branch, name=name, last_seen=now)
        if p.get("transcript_path"):
            s["transcript"] = p["transcript_path"]
        if ev == "SessionEnd":
            s["ended"] = now
        else:
            s.pop("ended", None)
        if ev == "UserPromptSubmit" and p.get("prompt"):
            s.setdefault("first_prompt", _clip(p["prompt"], 120))
            s["last_prompt"] = _clip(p["prompt"], 120)
        starts = s.setdefault("bash_started", {})
        if ev == "PreToolUse" and p.get("tool_name") == "Bash":
            starts[p.get("tool_use_id") or "-"] = now
        if ev == "PostToolUse":
            starts.pop(p.get("tool_use_id") or "-", None)
        for k in [k for k, t in starts.items() if now - t > LIVE_S]:
            del starts[k]
        for q in paths:
            b["touches"].setdefault(q, {})[sid] = [now, via]
        s["warned"] = (s.get("warned", []) + [f"{h[0]}|{h[1]}" for h in hits])[-200:]
        board = json.loads(json.dumps(b)) if ev == "SessionStart" else None
    if ev == "SessionStart":
        return start_context(board, sid, root, now)
    if hits:
        return ("Session board: " + "; ".join(describe(hits, now, root or None)) + ". That change is not committed: "
                "it is another session's work in progress. Tell the user, or ask that session (SendMessage to its "
                "name) before editing further or committing this file.")
    return None


def main_hook():
    try:
        p = json.load(sys.stdin)
        ctx = on_event(p)
    except Exception:                                    # never break a session over the board
        return 0
    if ctx:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": p["hook_event_name"], "additionalContext": ctx}}))
    return 0


def main_cli(argv):
    now, b = time.time(), load()
    if "--who" in argv:
        pend = _Pending()
        for path in map(os.path.realpath, argv[argv.index("--who") + 1:]):
            who = b["touches"].get(path) or {}
            print(f"{path}: " + ("no session changed it in the last day" if not who else ""))
            for o, (ts, via) in sorted(who.items(), key=lambda x: -x[1][0]):
                s = b["sessions"].get(o, {})
                state = "committed or reverted since" if pend.settled(path, ts) else "pending"
                print(f"  {label(o, s)} · {_ago(ts, now)} · {via} · {state}"
                      + (" · session ended" if s.get("ended") else ""))
        return 0
    repo = _toplevel(argv[argv.index("--repo") + 1]) if "--repo" in argv else None
    lines, n = session_lines(b, now, repo=repo)
    first = f", {os.path.basename(repo)} first" if repo else ""
    print(f"SESSION BOARD · {board_path()} · {n} live session(s){first}")
    for l in lines:
        print(f"  {l}")
    return 0


def _demo():
    checks = []
    with tempfile.TemporaryDirectory() as t:
        os.environ["SESSION_BOARD"] = os.path.join(t, "board.json")
        os.environ["SESSION_BOARD_JOBS"] = os.path.join(t, "jobs")
        os.makedirs(os.path.join(t, "jobs", "aaaa"))
        A, B = "aaaa0000-1111", "bbbb0000-2222"
        with open(os.path.join(t, "jobs", "aaaa", "state.json"), "w") as f:
            json.dump({"sessionId": A, "name": "Figure five"}, f)
        repo = os.path.realpath(os.path.join(t, "repo"))
        os.makedirs(repo)
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@t"}
        for f in ("x.py", "y.py", "z.py"):
            with open(os.path.join(repo, f), "w") as fh:
                fh.write("a = 1\n")
        for cmd in ("git init -q", "git add -A", "git commit -qm init"):
            subprocess.run(cmd.split(), cwd=repo, env=env, check=True, capture_output=True)
        ev = lambda sid, e, **kw: on_event({"session_id": sid, "hook_event_name": e, "cwd": repo, **kw})
        x, y, z = (os.path.join(repo, f) for f in ("x.py", "y.py", "z.py"))

        ev(A, "SessionStart")
        ev(A, "UserPromptSubmit", prompt="make figure 5 colorblind")
        open(x, "a").write("b = 2\n")
        ev(A, "PostToolUse", tool_name="Edit", tool_input={"file_path": x})
        ctx = ev(B, "SessionStart") or ""
        checks.append(("start: a new session is told who else is live, by name, with pending files",
                       "'Figure five'" in ctx and "x.py" in ctx and "make figure 5" in ctx))
        open(x, "a").write("c = 3\n")
        w1 = ev(B, "PostToolUse", tool_name="Edit", tool_input={"file_path": x}) or ""
        w2 = ev(B, "PostToolUse", tool_name="Edit", tool_input={"file_path": x})
        checks.append(("edit: warned once that another session changed the file", "'Figure five'" in w1 and w2 is None))
        open(z, "a").write("before\n")                                      # changed before B's command started
        time.sleep(0.3)
        ev(B, "PreToolUse", tool_name="Bash", tool_use_id="t1", tool_input={"command": "python gen.py"})
        open(y, "a").write("generated\n")
        ev(B, "PostToolUse", tool_name="Bash", tool_use_id="t1", tool_input={"command": "python gen.py"})
        who = load()["touches"]
        checks.append(("bash: the file the command changed is attributed, an older change is not",
                       B in who.get(y, {}) and z not in who))
        ev(B, "PreToolUse", tool_name="Bash", tool_use_id="t2", tool_input={"command": "git status && ls -la"})
        checks.append(("bash: read-only commands are not scanned", _read_only("git status && ls -la | wc -l")
                       and not _read_only("python x.py > out.txt") and not _read_only("sed -i s/a/b/ x.py")))
        sees = lambda me: [h[1] for h in foreign_touches([x], me)]
        checks.append(("guard view: B sees A's pending change to x.py, A sees B's", sees(B) == [A] and sees(A) == [B]))
        checks.append(("a change older than an hour does not count",
                       foreign_touches([x], B, now=time.time() + RECENT_S + 60) == []))
        subprocess.run(["git", "commit", "-qam", "ship"], cwd=repo, env=env, check=True, capture_output=True)
        checks.append(("a committed change no longer counts", foreign_touches([x, y], B) == []))
        procs = [subprocess.Popen([sys.executable, __file__], stdin=subprocess.PIPE, env=os.environ)
                 for _ in range(12)]
        for i, pr in enumerate(procs):                                       # all twelve wait on stdin: release at once
            assert pr.stdin is not None
            pr.stdin.write(json.dumps({"session_id": f"c{i:02d}", "hook_event_name": "PostToolUse", "cwd": repo,
                                       "tool_name": "Write", "tool_input": {"file_path": f"{repo}/n{i}.py"}}).encode())
        for pr in procs:
            assert pr.stdin is not None
            pr.stdin.close()
        for pr in procs:
            pr.wait()
        b = load()
        checks.append(("12 concurrent hooks: no update lost", all(f"c{i:02d}" in b["sessions"] for i in range(12))
                       and len([p for p in b["touches"] if "/n" in p]) == 12))
        ev(A, "SessionEnd")
        with _edit(time.time() + ENDED_S + 60):
            pass
        checks.append(("an ended session leaves the board after an hour, with its changes",
                       A not in load()["sessions"] and all(A not in w for w in load()["touches"].values())))
        checks.append(("the board is private (mode 600)", oct(os.stat(board_path()).st_mode)[-3:] == "600"))
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'} ({sum(bool(c) for _, c in checks)}/{len(checks)})")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--demo" in sys.argv:
        sys.exit(_demo())
    if "--list" in sys.argv or "--who" in sys.argv:
        sys.exit(main_cli(sys.argv))
    sys.exit(main_hook())
