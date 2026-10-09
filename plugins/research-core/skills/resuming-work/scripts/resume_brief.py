"""Resume a project: what changed since a date, what is running, what is open — and find past sessions.

Prints, for the git project around --repo:
  * git: branch, ahead/behind, uncommitted files, commits since --since
  * running work: detached screens, this user's python processes inside the project, recent queue files
  * review checkpoint: due / not due (running-review-checkpoints), when the project has a baseline
  * other Claude Code sessions live on this machine and the files they changed and have not committed
    (the session board, hooks/session_board.py in the skills repo, when its hooks are installed)
  * memory: the newest dated entries of the state file (project.yaml memory_dir + memory_state_file)
  * docs changed since --since, and open items (TODO, FIXME, NEXT:, unchecked boxes)
  * memory hygiene: oversized memory files, duplicate memory folders for this project, rules copied
    across projects (identical → one copy in the profile; different → one copy is stale). Proposals only.

--find "keywords" lists the past Claude Code sessions of this project whose user messages match.
Nothing is changed: the script only reads.

Settings (`resume:` in .claude/project.yaml, optional): since_days (3), memory_cap_kb (40).

Usage:
    python resume_brief.py [--repo PATH] [--since 2026-10-01 | --days 3]
    python resume_brief.py --find "figure 5 flows" [--all_projects]
    python resume_brief.py --memory                 # the memory-hygiene section in detail
    python resume_brief.py --demo
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

CLAUDE_ROOT = os.environ.get("CLAUDE_PROJECTS_ROOT", os.path.expanduser("~/.claude/projects"))
REVIEW = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "running-review-checkpoints",
                      "scripts", "review_status.py")
BOARD = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), *[".."] * 5, "hooks",
                                      "session_board.py"))
DEFAULTS = {"since_days": 3, "memory_cap_kb": 40}
DATE = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")
OPEN_ITEM = re.compile(r"\b(TODO|FIXME|NEXT:|OPEN:)|^\s*[-*] \[ \]")
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".ipynb_checkpoints"}
TOOLING = {"pyright-langserver", "pylsp", "jedi-language-server", "ruff", "black"}   # editors, not work
ORPHAN_HOURS = 7 * 24


# ── helpers ─────────────────────────────────────────────────────────────────────────────────────

def sh(args, cwd=None):
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def repo_root(path):
    return sh(["git", "-C", path, "rev-parse", "--show-toplevel"]) or None


def load_cfg(root):
    p = os.path.join(root, ".claude", "project.yaml")
    if not os.path.exists(p):
        return {}
    try:
        import yaml
    except ImportError:
        print("note: PyYAML not installed — project.yaml ignored", file=sys.stderr)
        return {}
    try:
        return yaml.safe_load(open(p)) or {}
    except yaml.YAMLError as e:
        print(f"note: cannot parse {p}: {e}", file=sys.stderr)
        return {}


def _norm(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def project_dirs(root, claude_root):
    """Claude Code folders of this project (its path with / → -; '_' and '-' variants both match)."""
    want = _norm(root)
    return sorted(d for d in glob.glob(os.path.join(claude_root, "*"))
                  if os.path.isdir(d) and _norm(os.path.basename(d)) == want)


def memory_dir(cfg, dirs):
    if cfg.get("memory_dir"):
        return os.path.expanduser(cfg["memory_dir"])
    for d in dirs:
        if os.path.isdir(os.path.join(d, "memory")):
            return os.path.join(d, "memory")
    return None


def _since(args, cfg):
    if args.since:
        return args.since
    days = args.days if args.days is not None else (cfg.get("resume") or {}).get("since_days", DEFAULTS["since_days"])
    return (dt.date.today() - dt.timedelta(days=days)).isoformat()


def _ts(date_str):
    return dt.datetime.fromisoformat(date_str).timestamp()


def _clip(s, n=110):
    s = " ".join(s.split())
    return s if len(s) <= n else s[:n - 1] + "…"


# ── sections ────────────────────────────────────────────────────────────────────────────────────

def git_section(root, since):
    head = sh(["git", "-C", root, "status", "-sb"]).splitlines()
    status = head[1:]
    modified = [l[3:] for l in status if not l.startswith("??")]
    untracked = [l[3:] for l in status if l.startswith("??")]
    commits = sh(["git", "-C", root, "log", f"--since={since}", "--format=%h %ad %s",
                  "--date=format:%m-%d %H:%M"]).splitlines()
    out = [f"{head[0].lstrip('# ') if head else '?'} · {len(modified)} modified · {len(untracked)} untracked · "
           f"{len(commits)} commits since {since}"]
    out += [f"  {_clip(c)}" for c in commits[:8]] + ([f"  … {len(commits) - 8} more"] if len(commits) > 8 else [])
    if modified:
        out.append("  modified: " + _clip(", ".join(modified[:8]), 150) + (" …" if len(modified) > 8 else ""))
    return out, {"commits": len(commits), "modified": len(modified), "untracked": len(untracked)}


def _processes(root):
    procs = []
    if not os.path.isdir("/proc"):
        return procs
    try:
        uptime = float(open("/proc/uptime").read().split()[0]); tick = os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError):
        uptime, tick = None, None
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or int(pid) == os.getpid():
            continue
        try:
            if os.stat(f"/proc/{pid}").st_uid != os.getuid():
                continue
            cwd = os.readlink(f"/proc/{pid}/cwd")
            argv = [a for a in open(f"/proc/{pid}/cmdline").read().split("\0") if a]
            start = int(open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[19])
        except (OSError, ValueError, IndexError):
            continue                                    # the process ended while we looked
        if not argv or not re.match(r"^python[\d.]*$", os.path.basename(argv[0])):
            continue                                    # only python interpreters, not tools living in a python env
        tool = os.path.basename(argv[1]) if len(argv) > 1 else ""
        if tool in TOOLING or tool == "node" or tool.endswith("langserver"):
            continue                                    # editors and language servers, not the user's work
        args = " ".join(argv)
        inside = cwd == root or cwd.startswith(root + os.sep) or (root + os.sep) in args
        if inside and "resume_brief" not in args:
            hours = (uptime - start / tick) / 3600 if uptime else float("nan")
            procs.append((pid, hours, " ".join(os.path.basename(a) if i == 0 else a for i, a in enumerate(argv))))
    return sorted(procs, key=lambda p: -p[1])


def _group(procs):
    """Group processes by what they run (first two arguments): (count, oldest hours, signature, a pid)."""
    groups = {}
    for pid, hours, args in procs:
        sig = " ".join(args.split()[1:3])[:90] or args[:90]
        n, h, _ = groups.get(sig, (0, 0.0, pid))
        groups[sig] = (n + 1, max(h, hours), pid)
    return sorted(((n, h, sig, pid) for sig, (n, h, pid) in groups.items()), key=lambda g: (-g[0], -g[1]))


def _queue_files(root, since_ts, max_depth=3):
    found = []
    for d, subdirs, files in os.walk(root):
        depth = d[len(root):].count(os.sep)
        subdirs[:] = [s for s in subdirs if s not in SKIP_DIRS and depth < max_depth]
        for f in files:
            if re.match(r"^queue.*\.(sh|log|txt)$", f):
                p = os.path.join(d, f)
                if os.path.getmtime(p) >= since_ts:
                    found.append(p)
    return sorted(found, key=os.path.getmtime, reverse=True)


def running_section(root, cfg, since):
    out = []
    names = re.findall(r"^\s*\d+\.(\S+)\s+\(", sh(["screen", "-ls"]) or "", re.M)
    prefix = (cfg.get("launch") or {}).get("screen_prefix") or ""
    mine = [n for n in names if prefix and n.startswith(prefix)]
    out.append(f"screens: {len(names)} detached" + (f", {len(mine)} named {prefix}*" if prefix else "")
               + (": " + _clip(", ".join(names[:12]), 140) if names else ""))
    procs = _processes(root)
    groups = _group(procs)
    out.append(f"python processes inside the project: {len(procs)}" + (f" in {len(groups)} group(s)" if procs else ""))
    for n, h, sig, pid in groups[:6]:
        stale = " — possibly orphaned, check before anything else" if h > ORPHAN_HOURS else ""
        out.append(f"  {n}× {_clip(sig, 80)} · oldest {h:.0f} h (pid {pid}){stale}")
    queues = _queue_files(root, _ts(since))
    for q in queues[:6]:
        tail = ""
        if q.endswith((".log", ".txt")):
            lines = [l for l in open(q, errors="ignore").read().splitlines() if l.strip()]
            tail = f" — last: {_clip(lines[-1], 70)}" if lines else ""
        out.append(f"queue file {os.path.relpath(q, root)} "
                   f"({dt.datetime.fromtimestamp(os.path.getmtime(q)):%m-%d %H:%M}){tail}")
    return out, {"screens": len(names), "processes": len(procs), "groups": len(groups), "queues": len(queues)}


def checkpoint_section(root, cfg):
    if not os.path.exists(REVIEW):
        return ["review checkpoint: skill not installed"], {}
    if "review_checkpoint" not in cfg:
        return ["review checkpoint: off (no review_checkpoint: in project.yaml)"], {"state": "off"}
    if not sh(["git", "-C", root, "rev-parse", "--verify", "-q", "refs/worktree/review/last"]):
        return ["review checkpoint: no baseline yet (review_status.py sets one)"], {"state": "no baseline"}
    lines = sh([sys.executable, REVIEW, "--repo", root]).splitlines()   # writes only loose git objects
    off = [l for l in lines if l.startswith("review checkpoints are")]
    size = next((l for l in lines if "changed lines in" in l), "")
    summary = next((l for l in lines if l.startswith("SUMMARY")), "SUMMARY: ?")
    return [f"review checkpoint: {summary[9:]}" + (f" · {size}" if size else "")] + off, \
           {"state": "due" if "DUE" in summary else "not due"}


def sessions_section(root):
    """Other Claude Code sessions live on this machine (the session board, when its hooks are installed)."""
    if not os.path.exists(BOARD):
        return ["session board: not installed (hooks/session_board.py in the skills repo)"], {"live": None}
    lines = sh([sys.executable, BOARD, "--list", "--repo", root]).splitlines()
    head = lines[0] if lines else ""
    n = int(m.group(1)) if (m := re.search(r"(\d+) live session", head)) else 0
    if not n:
        return ["no other session on the board (live = seen in the last day)"], {"live": 0}
    rule = "another session's uncommitted file: ask its owner (SendMessage to its name) before editing or committing it"
    return [l.strip() if l.startswith("  •") else l[2:] for l in lines[1:]] + [rule], {"live": n}


def memory_entries(path, n=5):
    """The n newest dated headings / bullets of a markdown memory file: (date, line, next line)."""
    lines = open(path, errors="ignore").read().splitlines()
    entries = []
    for i, l in enumerate(lines):
        if l.startswith("#") or l.lstrip().startswith(("- ", "* ")):
            m = DATE.search(l)
            if m:
                nxt = next((x for x in lines[i + 1:i + 4] if x.strip() and not x.startswith("#")), "")
                entries.append((m.group(0), -int(l.startswith("#")), i, l.strip(), nxt.strip()))
    entries.sort(key=lambda e: (e[0], -e[1], -e[2]), reverse=True)
    return [(e[0], e[3], e[4]) for e in entries[:n]]


def memory_section(cfg, mem, since):
    state = cfg.get("memory_state_file")
    if not mem or not os.path.isdir(mem):
        return ["memory: no memory folder found (project.yaml memory_dir)"], []
    if not state or not os.path.exists(os.path.join(mem, state)):
        recent = sorted((p for p in glob.glob(os.path.join(mem, "*.md")) if not p.endswith("MEMORY.md")),
                        key=os.path.getmtime, reverse=True)[:4]
        out = ["memory: no single state file — most recently changed memory files:"]
        for p in recent:
            top = memory_entries(p, n=1)
            out.append(f"  {dt.datetime.fromtimestamp(os.path.getmtime(p)):%m-%d}  {os.path.basename(p)}"
                       + (f" — {_clip(top[0][1], 90)}" if top else ""))
        return out, []
    entries = memory_entries(os.path.join(mem, state))
    out = [f"memory {state} — newest dated entries:"]
    if entries and entries[0][0] < since:
        out.append(f"  ⚠ newest entry is {entries[0][0]}, older than {since}: the state file lags the work")
    for date, line, nxt in entries:
        out.append(f"  {_clip(line, 120)}")
        if nxt:
            out.append(f"      {_clip(nxt, 110)}")
    return out, entries


def docs_section(root, cfg, mem, since):
    since_ts = _ts(since)
    candidates = [os.path.join(root, f) for f in os.listdir(root) if f.endswith(".md")]
    for d, subdirs, files in os.walk(os.path.join(root, "docs")):
        subdirs[:] = [s for s in subdirs if s not in SKIP_DIRS]
        candidates += [os.path.join(d, f) for f in files if f.endswith(".md")]
    changed = sorted((p for p in candidates if os.path.getmtime(p) >= since_ts), key=os.path.getmtime, reverse=True)
    out = [f"docs changed since {since}: {len(changed)}"]
    out += [f"  {dt.datetime.fromtimestamp(os.path.getmtime(p)):%m-%d %H:%M}  {os.path.relpath(p, root)}"
            for p in changed[:8]]
    scan = changed[:10]
    state = cfg.get("memory_state_file")
    if mem and state and os.path.exists(os.path.join(mem, state)):
        scan.append(os.path.join(mem, state))
    items = []
    for p in scan:
        for i, l in enumerate(open(p, errors="ignore").read().splitlines(), 1):
            if OPEN_ITEM.search(l):
                items.append((p, i, l.strip()))
    out.append(f"open items (TODO / FIXME / NEXT: / [ ]) in recent docs and memory: {len(items)}")
    for p, i, l in items[:10]:
        name = os.path.basename(p) if not p.startswith(root) else os.path.relpath(p, root)
        out.append(f"  {name}:{i}  {_clip(l, 100)}")
    return out, {"changed": [os.path.relpath(p, root) for p in changed], "open": len(items)}


def hygiene_section(root, cfg, claude_root, detail=False):
    cap = (cfg.get("resume") or {}).get("memory_cap_kb", DEFAULTS["memory_cap_kb"])
    dirs = project_dirs(root, claude_root)
    mem = memory_dir(cfg, dirs)
    out, found = [], {"oversized": [], "duplicate_dirs": [], "shared_same": [], "shared_diff": []}
    distinct = {}
    for d in dirs:                                   # a symlinked folder is the same folder, not a duplicate
        distinct.setdefault(os.path.realpath(d), d)
    dirs = list(distinct.values())
    if len(dirs) > 1:
        newest = max(dirs, key=lambda d: max([os.path.getmtime(p) for p in glob.glob(os.path.join(d, "**"), recursive=True)] or [0]))
        found["duplicate_dirs"] = [os.path.basename(d) for d in dirs]
        out.append(f"duplicate memory folders for this project: {', '.join(found['duplicate_dirs'])} "
                   f"(newest: {os.path.basename(newest)}) — propose merging into one")
    if mem and os.path.isdir(mem):
        for p in sorted(glob.glob(os.path.join(mem, "*.md"))):
            kb = os.path.getsize(p) / 1024
            if kb > cap:
                found["oversized"].append(os.path.basename(p))
                old = [d for d, _, _ in memory_entries(p, n=10 ** 6)
                       if (dt.date.today() - dt.date.fromisoformat(d)).days > 30]
                out.append(f"{os.path.basename(p)}: {kb:.0f} KB > {cap} KB"
                           + (f" — {len(old)} dated entries older than 30 days could move to docs" if old else "")
                           + " (proposal; never applied)")
        own = {os.path.realpath(d) for d in dirs} | {os.path.realpath(os.path.dirname(mem))}
        seen, others = set(own), []
        for d in sorted(glob.glob(os.path.join(claude_root, "*"))):   # one entry per real folder (symlinks are aliases)
            if os.path.realpath(d) not in seen and os.path.isdir(os.path.join(d, "memory")):
                seen.add(os.path.realpath(d)); others.append(os.path.join(d, "memory"))
        for p in sorted(glob.glob(os.path.join(mem, "*.md"))):
            name = os.path.basename(p)
            if name == "MEMORY.md" or name.startswith("project_"):
                continue
            copies = [o for o in others if os.path.exists(os.path.join(o, name))]
            if not copies:
                continue
            text = open(p, errors="ignore").read()
            differ = [o for o in copies if open(os.path.join(o, name), errors="ignore").read() != text]
            (found["shared_diff"] if differ else found["shared_same"]).append(name)
            if detail or differ:
                where = ", ".join(os.path.basename(os.path.dirname(o)) for o in (differ or copies))
                out.append(f"{name}: also in {len(copies)} other project(s); "
                           + (f"copies DIFFER ({where}) — one is stale" if differ
                              else "identical — one canonical copy belongs in the profile"))
        if found["shared_same"] and not detail:
            out.append(f"{len(found['shared_same'])} rule(s) copied identically into other projects — "
                       "candidates for the profile (--memory lists them)")
    if not out:
        out.append("memory hygiene: nothing to flag")
    return out, found


# ── past sessions ───────────────────────────────────────────────────────────────────────────────

def _user_text(d):
    if d.get("type") != "user":
        return ""
    c = (d.get("message") or {}).get("content")
    if isinstance(c, list):
        if any(isinstance(x, dict) and x.get("type") == "tool_result" for x in c):
            return ""
        c = " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    if not isinstance(c, str) or c.lstrip().startswith("<") or c.startswith("[Request interrupted"):
        return ""
    return c.strip()


def find_sessions(root, query, claude_root, all_projects=False, top=5):
    words = [w.lower() for w in query.split() if w.strip()]
    dirs = glob.glob(os.path.join(claude_root, "*")) if all_projects else project_dirs(root, claude_root)
    seen, results = set(), []
    for d in dirs:
        for path in glob.glob(os.path.join(d, "*.jsonl")):
            sid = os.path.basename(path)[:-6]
            if sid in seen:
                continue
            seen.add(sid)
            first, hits, best = None, 0, (0, "")
            with open(path, errors="ignore") as f:
                for n, line in enumerate(f):
                    if first is None and n < 400 and '"user"' in line:
                        try:
                            first = _user_text(json.loads(line)) or None
                        except ValueError:
                            pass
                    low = line.lower()
                    if '"user"' not in line or not any(w in low for w in words):
                        continue
                    try:
                        text = _user_text(json.loads(line))
                    except ValueError:
                        continue
                    k = sum(w in text.lower() for w in words)
                    if k:
                        hits += 1
                        if k > best[0]:
                            best = (k, text)
            if hits:
                results.append((best[0], hits, os.path.getmtime(path), sid, os.path.basename(d), first or "", best[1]))
    results.sort(key=lambda r: (r[0], r[1], r[2]), reverse=True)
    return results[:top], len(words)


# ── CLI ─────────────────────────────────────────────────────────────────────────────────────────

def brief(root, args, claude_root):
    cfg = load_cfg(root)
    since = _since(args, cfg)
    dirs = project_dirs(root, claude_root)
    mem = memory_dir(cfg, dirs)
    sections = [("GIT", git_section(root, since)), ("RUNNING", running_section(root, cfg, since)),
                ("REVIEW", checkpoint_section(root, cfg)), ("SESSIONS", sessions_section(root)),
                ("MEMORY", memory_section(cfg, mem, since)),
                ("DOCS", docs_section(root, cfg, mem, since)), ("HYGIENE", hygiene_section(root, cfg, claude_root))]
    print(f"RESUME BRIEF · {os.path.basename(root)} · since {since}")
    for title, (lines, _) in sections:
        print(f"── {title}")
        for l in lines:
            print(f"  {l}")
    return {t: data for t, (_, data) in sections}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="any path inside the project's repository")
    ap.add_argument("--since", help="ISO date (YYYY-MM-DD); default: today − resume.since_days")
    ap.add_argument("--days", type=int, help="look back this many days instead of --since")
    ap.add_argument("--find", help="keywords: list past sessions whose user messages match")
    ap.add_argument("--all_projects", action="store_true", help="with --find: search every project's sessions")
    ap.add_argument("--memory", action="store_true", help="only the memory-hygiene section, in detail")
    ap.add_argument("--claude_root", default=CLAUDE_ROOT, help="Claude Code projects folder (sessions + memory)")
    ap.add_argument("--demo", action="store_true", help="self-test in a throwaway project")
    a = ap.parse_args(argv)
    if a.demo:
        return _demo()
    root = repo_root(a.repo)
    if not root:
        print("not inside a git repository"); return 1
    if a.find:
        res, n = find_sessions(root, a.find, a.claude_root, a.all_projects)
        print(f"SESSIONS matching '{a.find}' ({'all projects' if a.all_projects else os.path.basename(root)}): {len(res)}")
        for k, hits, mtime, sid, proj, first, best in res:
            print(f"  {dt.datetime.fromtimestamp(mtime):%Y-%m-%d %H:%M}  {sid}  [{proj}]  {hits} matching messages, "
                  f"best {k}/{n} words")
            print(f"      first: {_clip(first, 100)}")
            print(f"      match: {_clip(best, 100)}")
            print(f"      resume (from the project folder): claude --resume {sid}")
        return 0
    if a.memory:
        lines, _ = hygiene_section(root, load_cfg(root), a.claude_root, detail=True)
        print(f"MEMORY HYGIENE · {os.path.basename(root)} (proposals only — nothing is changed)")
        for l in lines:
            print(f"  {l}")
        return 0
    brief(root, a, a.claude_root)
    return 0


def _demo():
    checks = []
    with tempfile.TemporaryDirectory() as t:
        root = os.path.join(t, "my_proj")
        claude = os.path.join(t, "projects")
        enc = "-" + "-".join(p for p in root.split(os.sep) if p)            # Claude Code's folder name
        mem = os.path.join(claude, enc, "memory")
        os.makedirs(mem); os.makedirs(os.path.join(claude, enc.replace("my_proj", "my-proj"), "memory"))
        other = os.path.join(claude, "-elsewhere-other", "memory"); os.makedirs(other)
        os.makedirs(os.path.join(root, "docs")); os.makedirs(os.path.join(root, ".claude"))
        open(os.path.join(root, ".claude", "project.yaml"), "w").write(
            f"memory_dir: {mem}\nmemory_state_file: project_state.md\nresume:\n  memory_cap_kb: 1\n")
        open(os.path.join(mem, "project_state.md"), "w").write(
            "# State\n\n## 2026-09-01 — old result\nwells above the line\n\n## 2026-10-05 — new result\n"
            "wells below the line in s0\n- NEXT: rerun seeds 4-7\n" + "filler\n" * 200)
        open(os.path.join(mem, "feedback_rule.md"), "w").write("Never launch more than 8 runs.\n")
        open(os.path.join(other, "feedback_rule.md"), "w").write("More than 8 runs allowed since 2026-10-05.\n")
        open(os.path.join(root, "docs", "log.md"), "w").write("# Log\n- TODO: plot the new sweep\n")
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@t"}
        for cmd in (["git", "init", "-q"], ["git", "add", "-A"], ["git", "commit", "-qm", "first analysis"]):
            subprocess.run(cmd, cwd=root, env=env, check=True, capture_output=True)
        for sid, msgs in (("aaa", ["plot the dual task figures", "make figure 5 flows colorblind"]),
                          ("bbb", ["fix the loss", "what loss are we using"])):
            with open(os.path.join(claude, enc, f"{sid}.jsonl"), "w") as f:
                for m in msgs:
                    f.write(json.dumps({"type": "user", "message": {"role": "user", "content": m}}) + "\n")
                f.write(json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "content": "figure 5"}]}}) + "\n")

        class A:                                                            # the CLI defaults
            since, days = "2000-01-01", None
        import contextlib, io
        import time
        board = os.path.join(t, "board.json")                              # another session, live in this project
        with open(os.path.join(root, "notes.py"), "w") as f:
            f.write("x = 1\n")
        json.dump({"sessions": {"cccc1111": {"name": "Figure five", "repo": os.path.realpath(root),
                                             "last_seen": time.time()}},
                   "touches": {os.path.realpath(os.path.join(root, "notes.py")): {"cccc1111": [time.time(), "edit"]}}},
                  open(board, "w"))
        os.environ["SESSION_BOARD"] = board
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            data = brief(root, A, claude)
        out = buf.getvalue()
        del os.environ["SESSION_BOARD"]
        os.remove(os.path.join(root, "notes.py"))
        checks.append(("sessions: another live session and its uncommitted file are listed",
                       not os.path.exists(BOARD) or (data["SESSIONS"]["live"] == 1 and "'Figure five'" in out
                                                     and "notes.py" in out)))
        checks.append(("git: the commit is listed", data["GIT"]["commits"] == 1 and "first analysis" in out))
        checks.append(("memory: newest dated entry first", data["MEMORY"] and data["MEMORY"][0][0] == "2026-10-05"))
        checks.append(("docs: changed doc listed", "docs/log.md" in data["DOCS"]["changed"]))
        checks.append(("open items: TODO and NEXT found", data["DOCS"]["open"] >= 2))
        checks.append(("review: off without review_checkpoint", data["REVIEW"].get("state") == "off"))
        h = data["HYGIENE"]
        checks.append(("hygiene: oversized state file flagged", "project_state.md" in h["oversized"]))
        checks.append(("hygiene: duplicate memory folders flagged", len(h["duplicate_dirs"]) == 2))
        checks.append(("hygiene: diverging copies of a rule flagged", "feedback_rule.md" in h["shared_diff"]))
        class B:
            since, days = "2026-10-06", None
        with contextlib.redirect_stdout(io.StringIO()) as b2:
            brief(root, B, claude)
        checks.append(("memory: a state file older than --since is flagged", "lags the work" in b2.getvalue()))
        res, _ = find_sessions(root, "figure 5 flows", claude)
        # session aaa: two typed messages match ("figures", "figure 5 flows"); its tool result must not count
        checks.append(("find: the right session first; tool results ignored", bool(res) and res[0][3] == "aaa" and res[0][1] == 2))
        before = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True).stdout
        checks.append(("nothing changed in the project", before.strip() == ""))
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'} ({sum(bool(c) for _, c in checks)}/{len(checks)})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
