"""Keep memory notes short: find oversized notes, guard them, check trimmed drafts, then archive and apply.

The judgment (what is current, which rules still hold) is made by a fresh agent per note following
references/trim_brief.md. This script does the mechanical steps around it:

  scan      notes above the cap (project.yaml `resume.memory_cap_kb`, default 40 KB) and MEMORY.md
            indexes near Claude Code's load limit (first 200 lines / 25 KB)
  snapshot  sha1 of each note into <work>/snapshot.sha1, so other sessions' later edits are caught
  check     each draft <work>/<note>.md: front matter identical, archive pointer present, size, numbers
            absent from the original (each must be a marked addition), and how-to coverage — scripts and
            --flags the original names that nothing describes after the trim
  apply     refuse a note changed since the snapshot; write memory/archive/<note>.md (the original under a
            "superseded history" header, appended if an archive exists); install the draft

Usage:
    python memory_trim.py scan [--repo PATH | --all] [--cap_kb 40]
    python memory_trim.py snapshot --work DIR NOTE [NOTE ...]
    python memory_trim.py check --work DIR [--roots PROJECT_DIR ...]
    python memory_trim.py apply --work DIR NOTE [NOTE ...]
    python memory_trim.py --demo
"""
import argparse
import datetime as dt
import glob
import hashlib
import os
import re
import subprocess
import sys
import tempfile

CLAUDE_ROOT = os.environ.get("CLAUDE_PROJECTS_ROOT", os.path.expanduser("~/.claude/projects"))
CAP_KB = 40
INDEX_LINES, INDEX_KB = 200, 25                # Claude Code loads only this much of MEMORY.md
TARGET_LINES, TARGET_KB = 180, 18              # a trimmed note above this is flagged, not refused
NUM = re.compile(r"(?<![\w.])[-−+]?\d+(?:[.,]\d+)?(?:e[-−]?\d+)?")
SCRIPT = re.compile(r"\b[\w/]*?([a-z][a-z0-9_]+\.py)\b")
FLAG = re.compile(r"(?<![\w-])(--[a-z][a-z0-9_]+)")
SKIP = ("/.git/", "/results/", "/data/", "/worktrees/", "/node_modules/", "/__pycache__/")


def front_matter(text):
    return text.split("\n---", 1)[0] if text.startswith("---\n") else ""


def body(text):
    return text.split("\n---\n", 1)[1].lstrip("\n") if text.startswith("---\n") and "\n---\n" in text else text


def sha1(path):
    return hashlib.sha1(open(path, "rb").read()).hexdigest()


def load_cap(repo):
    p = os.path.join(repo, ".claude", "project.yaml") if repo else ""
    if p and os.path.exists(p):
        try:
            import yaml
            return ((yaml.safe_load(open(p)) or {}).get("resume") or {}).get("memory_cap_kb", CAP_KB)
        except Exception as e:                    # a broken project.yaml must not stop the scan
            print(f"note: {p} not read ({e}); cap {CAP_KB} KB", file=sys.stderr)
    return CAP_KB


def memory_dirs(repo, everything):
    if everything or not repo:
        return [d for d in sorted(glob.glob(os.path.join(CLAUDE_ROOT, "*", "memory")))
                if not os.path.islink(os.path.dirname(d))]        # a symlinked project folder is the same folder
    want = re.sub(r"[^a-z0-9]+", "-", os.path.abspath(repo).lower()).strip("-")
    return [d for d in sorted(glob.glob(os.path.join(CLAUDE_ROOT, "*", "memory")))
            if re.sub(r"[^a-z0-9]+", "-", os.path.basename(os.path.dirname(d)).lower()).strip("-") == want
            and not os.path.islink(os.path.dirname(d))]


# ── scan ────────────────────────────────────────────────────────────────────────────────────────

def scan(dirs, cap_kb):
    flagged = []
    for d in dirs:
        proj = os.path.basename(os.path.dirname(d))
        idx = os.path.join(d, "MEMORY.md")
        if os.path.exists(idx):
            t = open(idx, errors="ignore").read()
            if t.count("\n") > 0.8 * INDEX_LINES or len(t) > 0.8 * INDEX_KB * 1000:
                print(f"  {proj}: MEMORY.md {t.count(chr(10))} lines / {len(t)/1000:.1f} KB — near the load limit "
                      f"({INDEX_LINES} lines / {INDEX_KB} KB); lines past it are never loaded")
        for p in sorted(glob.glob(os.path.join(d, "*.md"))):
            if os.path.islink(p) or os.path.basename(p) == "MEMORY.md":
                continue
            kb = os.path.getsize(p) / 1000
            if kb > cap_kb:
                t = open(p, errors="ignore").read()
                dates = re.findall(r"\b20\d\d-\d\d-\d\d\b", t)
                flagged.append(p)
                print(f"  {proj}: {os.path.basename(p)}  {kb:.0f} KB, {t.count(chr(10))} lines, "
                      f"dates {min(dates) if dates else '-'} … {max(dates) if dates else '-'}")
    print(f"SUMMARY: {len(flagged)} notes over {cap_kb} KB in {len(dirs)} memory folders")
    return flagged


# ── snapshot / apply ───────────────────────────────────────────────────────────────────────────

def snapshot(work, notes):
    os.makedirs(work, exist_ok=True)
    with open(os.path.join(work, "snapshot.sha1"), "a") as f:
        for n in notes:
            f.write(f"{sha1(n)}  {os.path.abspath(n)}\n")
    print(f"SUMMARY: {len(notes)} notes snapshotted in {work}/snapshot.sha1")


def read_snapshot(work):
    p = os.path.join(work, "snapshot.sha1")
    if not os.path.exists(p):
        sys.exit(f"no snapshot in {work}: run `snapshot` before drafting")
    return {line.split("  ", 1)[1].strip(): line.split()[0] for line in open(p) if line.strip()}


def apply(work, notes, today=None):
    snap, done = read_snapshot(work), 0
    today = today or dt.date.today().isoformat()
    for n in map(os.path.abspath, notes):
        stem = os.path.basename(n)[:-3]
        draft_p = os.path.join(work, stem + ".md")
        if n not in snap or not os.path.exists(draft_p):
            print(f"  skipped {stem}: no snapshot or no draft"); continue
        if sha1(n) != snap[n]:
            print(f"  REFUSED {stem}: changed since the snapshot — another session wrote it; redraft or merge first")
            continue
        orig, draft = open(n).read(), open(draft_p).read()
        if front_matter(draft) != front_matter(orig):
            print(f"  REFUSED {stem}: the draft changed the front matter"); continue
        m = re.search(r"^name:\s*[\"']?([^\"'\n]+)", orig, re.M)
        name = m.group(1).strip() if m else stem
        arch_dir = os.path.join(os.path.dirname(n), "archive")
        os.makedirs(arch_dir, exist_ok=True)
        arch = os.path.join(arch_dir, stem + ".md")
        if os.path.exists(arch):
            block = f"\n\n---\n\n## Archived {today}\n\n" + body(orig)
        else:
            block = (f"# ARCHIVE — {stem}.md, superseded history (archived {today})\n\n"
                     f"> The current note is `../{stem}.md` ([[{name}]]); it and the project docs win over anything\n"
                     f"> here. Kept so old analyses, scripts and decisions stay findable by search. Not in the index.\n\n"
                     + body(orig))
        with open(arch, "a") as f:
            f.write(block)
        open(n, "w").write(draft)
        done += 1
        print(f"  applied {stem}: {len(orig)/1000:.0f} KB → {len(draft)/1000:.0f} KB; original in archive/{stem}.md")
    print(f"SUMMARY: {done} of {len(notes)} notes trimmed")
    return done


# ── check ──────────────────────────────────────────────────────────────────────────────────────

def files_under(roots, ext):
    out = []
    for r in roots:
        out += [p for p in glob.glob(os.path.join(os.path.expanduser(r), "**", "*." + ext), recursive=True)
                if not any(s in p for s in SKIP)]
    return out


def check(work, roots):
    snap = read_snapshot(work)
    docs = "".join(open(p, errors="ignore").read() for p in files_under(roots, "md"))
    py = files_under(roots, "py")
    code, names = "".join(open(p, errors="ignore").read() for p in py), {os.path.basename(p) for p in py}
    drafts = {os.path.basename(n)[:-3]: n for n in snap if os.path.exists(os.path.join(work, os.path.basename(n)))}
    problems = 0
    for stem, n in sorted(drafts.items()):
        orig, draft = open(n).read(), open(os.path.join(work, stem + ".md")).read()
        others = ""                                           # the rest of that memory folder, after the trim
        for p in glob.glob(os.path.join(os.path.dirname(n), "*.md")):
            s = os.path.basename(p)[:-3]
            if s != stem:
                others += open(os.path.join(work, s + ".md")).read() if s in drafts else open(p, errors="ignore").read()
        onum = {x.lstrip("-−+") for x in NUM.findall(orig)}
        new_nums = sorted({x for x in NUM.findall(draft) if x.lstrip("-−+") not in onum})
        lines, kb = draft.count("\n"), len(draft) / 1000
        print(f"{stem}: {orig.count(chr(10))} → {lines} lines, {len(orig)/1000:.0f} → {kb:.1f} KB")
        issues = []
        if front_matter(draft) != front_matter(orig):
            issues.append("front matter changed")
        if f"archive/{stem}.md" not in draft:
            issues.append(f"no pointer to memory/archive/{stem}.md")
        if lines > TARGET_LINES or kb > TARGET_KB:
            issues.append(f"over the target ({TARGET_LINES} lines / {TARGET_KB} KB)")
        if sha1(n) != snap[n]:
            issues.append("the note changed since the snapshot")
        for i in issues:
            print(f"  ✗ {i}")
        problems += len(issues)
        if new_nums:
            print(f"  ? numbers not in the original (each must be a marked addition): {new_nums[:12]}")

        def where(x, kind):
            if x in draft: return "kept"
            if x in others: return "other notes"
            if x in docs: return "docs"
            if kind == "script" and x in names: return "file only"
            if kind == "flag" and x in code: return "code only"
            return "gone"
        for kind, rx in (("script", SCRIPT), ("flag", FLAG)):
            found = {}
            for x in set(rx.findall(orig)):
                found.setdefault(where(x, kind), []).append(x)
            if found:
                print(f"  {kind}s {sum(map(len, found.values()))}: "
                      + " · ".join(f"{k} {len(v)}" for k, v in sorted(found.items(), key=lambda kv: -len(kv[1]))))
            for k in ("file only", "code only"):
                if found.get(k):
                    print(f"    described nowhere after the trim ({k}): {sorted(found[k])[:10]}")
    print(f"SUMMARY: {len(drafts)} drafts checked, {problems} blocking issues")
    return problems


# ── demo ───────────────────────────────────────────────────────────────────────────────────────

def _demo():
    global CLAUDE_ROOT
    checks = []
    with tempfile.TemporaryDirectory() as d:
        CLAUDE_ROOT = os.path.join(d, "projects")
        mem = os.path.join(CLAUDE_ROOT, "-x-proj", "memory"); os.makedirs(mem)
        repo = os.path.join(d, "proj"); os.makedirs(os.path.join(repo, "docs"))
        open(os.path.join(repo, "docs", "log.md"), "w").write("plot_a.py makes Fig 1 (--fast).\n")
        open(os.path.join(repo, "plot_b.py"), "w").write("p.add_argument('--slow')\n")
        fm = "---\nname: state\ndescription: x\n---\n\n"
        hist = "".join(f"## 2026-0{m}-01 entry\nresult 0.{m}5 with plot_a.py and plot_b.py --slow\n\n" for m in range(1, 9))
        note = os.path.join(mem, "project_state.md")
        open(note, "w").write(fm + "# State\n" + hist * 40)
        open(os.path.join(mem, "MEMORY.md"), "w").write("- [State](project_state.md)\n")
        open(os.path.join(mem, "small.md"), "w").write(fm + "short\n")
        flagged = scan(memory_dirs(None, True), cap_kb=5)
        checks.append(("scan flags the oversized note only", flagged == [note]))
        work = os.path.join(d, "work")
        snapshot(work, [note])
        open(os.path.join(work, "project_state.md"), "w").write(
            fm + "# State\n## Current\n- 2026-08-01 result 0.85 (and an invented 0.99)\n## History\n"
            "- `memory/archive/project_state.md`\n")
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            problems = check(work, [repo])
        out = buf.getvalue()
        checks.append(("check: no blocking issue in a good draft", problems == 0))
        checks.append(("check: an invented number is reported", "0.99" in out and "0.85" not in out.split("numbers")[-1]))
        checks.append(("check: plot_b.py is described nowhere after the trim", "file only): ['plot_b.py']" in out))
        checks.append(("check: plot_a.py survives in the docs", "plot_a.py" not in out))
        with open(note, "a") as f:
            f.write("a concurrent edit\n")
        checks.append(("apply refuses a note changed since the snapshot", apply(work, [note]) == 0))
        open(os.path.join(work, "snapshot.sha1"), "w").write("")
        snapshot(work, [note])
        before = open(note).read()
        checks.append(("apply installs the draft", apply(work, [note], today="2026-10-09") == 1
                       and open(note).read() == open(os.path.join(work, "project_state.md")).read()))
        arch = open(os.path.join(mem, "archive", "project_state.md")).read()
        checks.append(("archive = header + the full original body", arch.startswith("# ARCHIVE")
                       and body(before) in arch and "name: state" not in arch))
        open(os.path.join(work, "snapshot.sha1"), "w").write("")
        snapshot(work, [note]); apply(work, [note], today="2026-11-01")
        checks.append(("a second trim appends to the archive", "## Archived 2026-11-01" in
                       open(os.path.join(mem, "archive", "project_state.md")).read()))
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'} ({sum(c for _, c in checks)}/{len(checks)})")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", choices=["scan", "snapshot", "check", "apply"])
    ap.add_argument("notes", nargs="*", help="memory note paths (snapshot, apply)")
    ap.add_argument("--repo", default=None, help="project whose memory to scan (default: every project)")
    ap.add_argument("--all", action="store_true", help="scan every project's memory")
    ap.add_argument("--cap_kb", type=float, default=None, help="size above which a note is flagged")
    ap.add_argument("--work", help="scratch folder holding the snapshot, drafts and reports")
    ap.add_argument("--roots", nargs="*", default=None, help="project folders whose docs and code count as coverage")
    ap.add_argument("--demo", action="store_true", help="self-test in a temp folder")
    a = ap.parse_args(argv)
    if a.demo:
        return _demo()
    if a.command == "scan":
        repo = subprocess.run(["git", "-C", a.repo, "rev-parse", "--show-toplevel"], capture_output=True,
                              text=True).stdout.strip() if a.repo else None
        scan(memory_dirs(repo, a.all), a.cap_kb or load_cap(repo))
        return 0
    if not a.work:
        ap.error(f"{a.command} needs --work")
    if a.command == "snapshot":
        snapshot(a.work, a.notes)
    elif a.command == "check":
        return 1 if check(a.work, a.roots or [os.getcwd()]) else 0
    elif a.command == "apply":
        apply(a.work, a.notes)
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
