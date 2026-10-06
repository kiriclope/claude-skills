"""Review checkpoints: measure what changed since the user last reviewed the project, and record reviews.

A project opts in with `review_checkpoint:` in .claude/project.yaml:

    review_checkpoint:
      max_lines: 300                 # changed lines (added + removed) since the last review
      max_commits: 3                 # commits since the last review
      include: [py, md, yaml, yml, toml, sh, tex, html]   # extensions that count (code, docs, config)
      exclude: [results/, scratchpad/]                     # path prefixes / components that never count

The reviewed state is a snapshot of the working tree (tracked + untracked text files of the included
extensions, .gitignore respected) kept as the per-worktree ref refs/worktree/review/last. Taking a
snapshot never touches the working tree or the index (a temporary index is used). "Since the last
review" = that snapshot vs a fresh snapshot of now, so uncommitted and new files count too.
The first run in a project sets a baseline: past work does not trigger a review.

Usage:
    python review_status.py                      # facts for the digest: files, lines, commits, due?
    python review_status.py --mark --note "..."  # record a review — ONLY after the user approved it
    python review_status.py --defer              # the user said "not now": next checkpoint one step later
    python review_status.py --off | --on         # switch checkpoints off / on in this project (local, not committed)
    python review_status.py --off --global       # … or everywhere (~/.claude/review_checkpoints.json)
    python review_status.py --reset              # new baseline; the log says earlier changes were not reviewed
    python review_status.py --hook stop          # Stop hook: block the end of the turn when a review is due
    python review_status.py --demo               # self-test in a throwaway repository
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile

REF = "refs/worktree/review/last"
LOG = os.path.join(".claude", "review_log.md")
DEFAULTS = dict(max_lines=300, max_commits=3, include=["py", "md", "yaml", "yml", "toml", "sh", "tex", "html"],
                exclude=["results/", "scratchpad/"])
SNAPSHOT_ID = {"GIT_AUTHOR_NAME": "review-checkpoint", "GIT_AUTHOR_EMAIL": "review@localhost",
               "GIT_COMMITTER_NAME": "review-checkpoint", "GIT_COMMITTER_EMAIL": "review@localhost"}
GLOBAL_SWITCH = os.environ.get("REVIEW_CHECKPOINTS_GLOBAL", os.path.expanduser("~/.claude/review_checkpoints.json"))
READABILITY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "reviewing-code-readability",
                           "scripts", "readability_check.py")


# ── git plumbing ────────────────────────────────────────────────────────────────────────────────

def _git(root, *args, env=None, check=True):
    r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True,
                       env={**os.environ, **(env or {})})
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip()


def repo_root(path):
    r = subprocess.run(["git", "-C", path, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def load_cfg(root):
    """The project's review_checkpoint settings, or None when the project has not opted in."""
    p = os.path.join(root, ".claude", "project.yaml")
    if not os.path.exists(p):
        return None
    try:
        import yaml
        rc = (yaml.safe_load(open(p)) or {}).get("review_checkpoint")
    except Exception as e:                                      # a broken yaml must not block every turn
        print(f"review_status: cannot read {p}: {e}", file=sys.stderr)
        return None
    return None if rc is None else {**DEFAULTS, **(rc or {})}


def _pathspecs(cfg):
    keep = [f":(glob)**/*.{ext}" for ext in cfg["include"]]
    drop = [f":(exclude,glob)**/{p.rstrip('/')}" + ("/**" if p.endswith("/") else "") for p in cfg["exclude"]]
    return keep + drop


def counts(cfg, path):
    if path == LOG or any(path.startswith(p) or f"/{p}" in f"/{path}" for p in cfg["exclude"]):
        return False
    return path.rsplit(".", 1)[-1] in cfg["include"]


def snapshot(root, cfg):
    """Commit object holding the current working tree (included files), without touching index or files."""
    gitdir = os.path.abspath(os.path.join(root, _git(root, "rev-parse", "--git-dir")))
    idx = os.path.join(gitdir, "review_snapshot.index")
    env = {"GIT_INDEX_FILE": idx, **SNAPSHOT_ID}
    head = _git(root, "rev-parse", "--verify", "-q", "HEAD", check=False)
    try:
        _git(root, "read-tree", *(["HEAD"] if head else ["--empty"]), env=env)
        # list first: `git add` aborts entirely when one pattern matches nothing; ls-files never does
        files = subprocess.run(["git", "-C", root, "ls-files", "-z", "--cached", "--others", "--exclude-standard",
                                "--", *_pathspecs(cfg)], capture_output=True, env={**os.environ, **env}).stdout
        if files:
            subprocess.run(["git", "-C", root, "add", "-A", "--pathspec-from-file=-", "--pathspec-file-nul"],
                           input=files, capture_output=True, check=True, env={**os.environ, **env})
        tree = _git(root, "write-tree", env=env)
        return _git(root, "commit-tree", tree, *(["-p", head] if head else []), "-m", "review snapshot", env=env)
    finally:
        if os.path.exists(idx):
            os.remove(idx)


def _state_path(root):
    return os.path.join(os.path.abspath(os.path.join(root, _git(root, "rev-parse", "--git-dir"))),
                        "review_state.json")


def _state(root):
    try:
        return json.load(open(_state_path(root)))
    except (OSError, ValueError):
        return {"deferrals": 0}


def _save_state(root, st):
    json.dump(st, open(_state_path(root), "w"))


def switched_on(root):
    """(on, why): the global switch wins, then this project's local switch. Both default to on."""
    try:
        if json.load(open(GLOBAL_SWITCH)).get("enabled") is False:
            return False, "off everywhere (global switch)"
    except (OSError, ValueError):
        pass
    if _state(root).get("enabled") is False:
        return False, "off in this project (local switch)"
    return True, ""


def set_switch(root, on, everywhere=False):
    if everywhere:
        os.makedirs(os.path.dirname(GLOBAL_SWITCH), exist_ok=True)
        json.dump({"enabled": on}, open(GLOBAL_SWITCH, "w"))
    else:
        st = _state(root); st["enabled"] = on; _save_state(root, st)


def checkpoint_due(root):
    """status() when this project has opted in and checkpoints are switched on, else None (hooks use this)."""
    cfg = load_cfg(root)
    if cfg is None or not switched_on(root)[0]:
        return None
    return status(root, cfg)


# ── status ──────────────────────────────────────────────────────────────────────────────────────

def status(root, cfg=None):
    """Dict with lines, files, commits, due, … since the last review. Sets a baseline on first use."""
    cfg = cfg or load_cfg(root)
    if cfg is None:
        return None
    last = _git(root, "rev-parse", "--verify", "-q", REF, check=False)
    if not last:
        _git(root, "update-ref", REF, snapshot(root, cfg))
        _save_state(root, {"deferrals": 0, "baseline": dt.datetime.now().isoformat(timespec="minutes")})
        return {"baseline": True, "due": False, "lines": 0, "files": [], "commits": [], "cfg": cfg}
    now = snapshot(root, cfg)
    files = []
    for line in _git(root, "diff", "--numstat", "--no-renames", last, now).splitlines():
        a, d, path = line.split("\t", 2)
        if counts(cfg, path) and a != "-":
            files.append((int(a), int(d), path))
    files.sort(key=lambda f: -(f[0] + f[1]))
    parent = _git(root, "rev-parse", "--verify", "-q", f"{last}^", check=False)
    log = _git(root, "log", "--format=%h %s", f"{parent}..HEAD" if parent else "HEAD", check=False)
    commits = [c for c in log.splitlines() if c]
    st = _state(root)
    step = 1 + st.get("deferrals", 0)
    lines = sum(a + d for a, d, _ in files)
    due_lines, due_commits = lines >= cfg["max_lines"] * step, len(commits) >= cfg["max_commits"] * step
    when = _git(root, "log", "-1", "--format=%cd", "--date=format:%Y-%m-%d %H:%M", last, check=False)
    return {"baseline": False, "due": due_lines or due_commits, "due_lines": due_lines, "due_commits": due_commits,
            "lines": lines, "files": files, "commits": commits, "deferrals": st.get("deferrals", 0),
            "since": when, "last": last, "cfg": cfg}


def mark(root, cfg, note):
    s = status(root, cfg)
    assert s is not None                                          # cfg is given, so status() is defined
    os.makedirs(os.path.join(root, ".claude"), exist_ok=True)
    head = _git(root, "rev-parse", "--short", "HEAD", check=False) or "(no commit)"
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    new = not os.path.exists(os.path.join(root, LOG))
    with open(os.path.join(root, LOG), "a") as f:
        if new:
            f.write("# Review log\n\nHuman review checkpoints (running-review-checkpoints skill). Newest last.\n")
        f.write(f"\n## {stamp} — checkpoint at {head}\n"
                f"- reviewed since {s.get('since') or 'baseline'}: {s['lines']} lines in {len(s['files'])} files, "
                f"{len(s['commits'])} commits\n- approved by the user in the checkpoint\n- note: {note}\n")
    _git(root, "update-ref", REF, snapshot(root, cfg))
    _save_state(root, {**_state(root), "deferrals": 0})
    return s


def reset(root, cfg):
    """New baseline without a review; the log records that the changes before it were not reviewed."""
    s = status(root, cfg)
    assert s is not None
    os.makedirs(os.path.join(root, ".claude"), exist_ok=True)
    with open(os.path.join(root, LOG), "a") as f:
        f.write(f"\n## {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} — baseline reset by the user\n"
                f"- NOT reviewed: {s['lines']} lines in {len(s['files'])} files, {len(s['commits'])} commits "
                f"since {s.get('since') or 'the previous baseline'}\n")
    _git(root, "update-ref", REF, snapshot(root, cfg))
    _save_state(root, {**_state(root), "deferrals": 0})
    return s


def defer(root):
    st = _state(root)
    st["deferrals"] = st.get("deferrals", 0) + 1
    _save_state(root, st)
    return st["deferrals"]


def readability_summary(root, s):
    py = [os.path.join(root, p) for _, _, p in s["files"] if p.endswith(".py") and os.path.exists(os.path.join(root, p))]
    if not py or not os.path.exists(READABILITY):
        return None
    r = subprocess.run([sys.executable, READABILITY, "--since", s["last"], *py[:40]], capture_output=True, text=True)
    lines = r.stdout.strip().splitlines()
    errors = [l.strip() for l in lines if " error " in l]
    return (lines[-1] if lines else "readability check: no output"), errors[:8]


# ── CLI ─────────────────────────────────────────────────────────────────────────────────────────

def report(root, s):
    cfg = s["cfg"]
    if s["baseline"]:
        print(f"review checkpoint: baseline set for {root} — changes from now on count toward the next review")
        return
    step = 1 + s["deferrals"]
    print(f"REVIEW STATUS · {os.path.basename(root)} · since {s['since']}  "
          f"(due at {cfg['max_lines'] * step} lines or {cfg['max_commits'] * step} commits"
          + (f"; deferred {s['deferrals']}×" if s["deferrals"] else "") + ")")
    print(f"{s['lines']} changed lines in {len(s['files'])} files · {len(s['commits'])} commits")
    for a, d, p in s["files"][:30]:
        print(f"  {p:60s} +{a:<5d} −{d}")
    if len(s["files"]) > 30:
        print(f"  … {len(s['files']) - 30} more files")
    for c in s["commits"][:15]:
        print(f"  commit {c}")
    rs = readability_summary(root, s)
    if rs:
        print(f"readability (changed lines): {rs[0]}")
        for e in rs[1]:
            print(f"    {e}")
    print("SUMMARY: review " + ("DUE" if s["due"] else "not due"))


def hook_stop(payload):
    if payload.get("stop_hook_active"):
        return 0                                                  # already continuing because of us
    root = repo_root(payload.get("cwd") or os.getcwd())
    if not root:
        return 0
    s = checkpoint_due(root)
    if not s or not s["due"]:
        return 0
    why = (f"{s['lines']} changed lines" if s["due_lines"] else "") + \
          (" and " if s["due_lines"] and s["due_commits"] else "") + \
          (f"{len(s['commits'])} commits" if s["due_commits"] else "")
    print(json.dumps({"decision": "block", "reason":
        f"Review checkpoint due in {os.path.basename(root)}: {why} since the user's last review ({s['since']}). "
        "Run the running-review-checkpoints skill now: digest, decisions for the user to approve, then "
        "review_status.py --mark (only after approval) or --defer if the user says not now."}))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="any path inside the project's repository")
    ap.add_argument("--mark", action="store_true", help="record a review (only after the user approved it)")
    ap.add_argument("--note", default="", help="what was approved or changed, for the review log")
    ap.add_argument("--defer", action="store_true", help="postpone the checkpoint by one threshold step")
    ap.add_argument("--off", action="store_true", help="switch checkpoints off in this project (or everywhere with --global)")
    ap.add_argument("--on", action="store_true", help="switch checkpoints back on (counting resumes from the last review)")
    ap.add_argument("--global", dest="everywhere", action="store_true", help="with --on/--off: all projects")
    ap.add_argument("--reset", action="store_true", help="new baseline now; logged as NOT reviewed")
    ap.add_argument("--hook", choices=["stop"], help="run as a Claude Code hook (reads the JSON payload on stdin)")
    ap.add_argument("--demo", action="store_true", help="self-test in a throwaway repository")
    a = ap.parse_args(argv)
    if a.demo:
        return _demo()
    if a.hook:
        try:
            payload = json.loads(sys.stdin.read() or "{}")
        except ValueError:
            payload = {}
        return hook_stop(payload)
    root = repo_root(a.repo)
    if (a.on or a.off) and a.everywhere:
        set_switch(root, a.on, everywhere=True)
        print(f"review checkpoints switched {'ON' if a.on else 'OFF'} everywhere ({GLOBAL_SWITCH})"); return 0
    if not root:
        print("not inside a git repository"); return 1
    if a.on or a.off:
        set_switch(root, a.on)
        msg = f"review checkpoints switched {'ON' if a.on else 'OFF'} in {os.path.basename(root)} (local, not committed)"
        if a.on:
            msg += " — counting resumes from the last review; --reset starts fresh instead"
        print(msg); return 0
    cfg = load_cfg(root)
    if cfg is None:
        print(f"{root}: no `review_checkpoint:` in .claude/project.yaml — checkpoints are off here"); return 0
    if a.defer:
        n = defer(root); print(f"deferred: next checkpoint at {(1 + n) * cfg['max_lines']} lines or "
                               f"{(1 + n) * cfg['max_commits']} commits since the last review"); return 0
    if a.reset:
        s = reset(root, cfg)
        print(f"baseline reset; logged as NOT reviewed: {s['lines']} lines, {len(s['files'])} files"); return 0
    if a.mark:
        s = mark(root, cfg, a.note or "(no note)")
        print(f"review recorded in {LOG}: {s['lines']} lines, {len(s['files'])} files, {len(s['commits'])} commits")
        return 0
    on, why = switched_on(root)
    if not on:
        print(f"review checkpoints are {why} — hooks stay silent; --on to resume")
    s = status(root, cfg)
    assert s is not None
    report(root, s)
    return 0


def _demo():
    global GLOBAL_SWITCH
    def hook(d, extra=None):
        return subprocess.run([sys.executable, __file__, "--hook", "stop"], input=json.dumps({"cwd": d, **(extra or {})}),
                              capture_output=True, text=True, env={**os.environ, "REVIEW_CHECKPOINTS_GLOBAL": GLOBAL_SWITCH}).stdout
    def sh(*args):
        subprocess.run(args, cwd=d, check=True, capture_output=True, env={**os.environ, **SNAPSHOT_ID})
    with tempfile.TemporaryDirectory() as d:
        GLOBAL_SWITCH = os.path.join(d, "global_switch.json")      # never touch the user's real switch
        sh("git", "init", "-q"); os.makedirs(os.path.join(d, ".claude"))
        open(os.path.join(d, ".claude", "project.yaml"), "w").write(
            "review_checkpoint:\n  max_lines: 20\n  max_commits: 2\n  exclude: [results/]\n")
        open(os.path.join(d, "a.py"), "w").write("x = 1\n")
        sh("git", "add", "-A"); sh("git", "commit", "-qm", "init")
        checks = []
        s = status(d); checks.append(("first run sets a baseline", s["baseline"] and not s["due"]))
        open(os.path.join(d, "b.py"), "w").write("".join(f"y{i} = {i}\n" for i in range(25)))   # untracked, 25 lines
        os.makedirs(os.path.join(d, "results")); open(os.path.join(d, "results", "r.md"), "w").write("z\n" * 500)
        s = status(d); checks.append(("25 new lines (untracked) → due; results/ ignored", s["due"] and s["lines"] == 25))
        staged = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=d, capture_output=True, text=True).stdout
        checks.append(("snapshots leave the index untouched (nothing staged)", staged.strip() == ""))
        checks.append(("Stop hook blocks when due", '"decision": "block"' in hook(d)))
        checks.append(("Stop hook never blocks twice in a row", hook(d, {"stop_hook_active": True}).strip() == ""))
        set_switch(d, False); checks.append(("local --off silences the hook", hook(d).strip() == ""))
        set_switch(d, True); checks.append(("--on: blocks again (unreviewed work still counts)", '"decision"' in hook(d)))
        set_switch(d, False, everywhere=True); checks.append(("global --off silences the hook", hook(d).strip() == ""))
        set_switch(d, True, everywhere=True)
        defer(d); s = status(d); checks.append(("deferral doubles the threshold", not s["due"]))
        mark(d, load_cfg(d), "demo"); s = status(d)
        checks.append(("--mark resets: not due, 0 lines", not s["due"] and s["lines"] == 0))
        checks.append(("review log written", "approved by the user" in open(os.path.join(d, LOG)).read()))
        sh("git", "add", "-A"); sh("git", "commit", "-qm", "c1"); sh("git", "commit", "-q", "--allow-empty", "-m", "c2")
        s = status(d); checks.append(("2 commits → due by commits", s["due"] and s["due_commits"]))
        reset(d, load_cfg(d)); s = status(d)
        checks.append(("--reset: not due, logged as NOT reviewed", not s["due"] and "NOT reviewed" in open(os.path.join(d, LOG)).read()))
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'} ({sum(c for _, c in checks)}/{len(checks)})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
