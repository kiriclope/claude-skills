"""Audit how a research repository is organized and propose a tidy plan. It never moves or deletes anything.

Reports, for the git project around --repo:
  * untracked source files — code, docs, configs, hand-made vector art that git does not version
  * ignored source files — an ignore rule hides a source (e.g. `*.svg` hiding a hand-drawn scheme)
  * version-suffixed copies (_v2, _v1259, _old, _final, _copy, _bak, dated) and exploratory leftovers (preview)
  * large tracked files
  * scratch folders: size, file count, files older than the age limit (promote or delete)
  * docs missing from the doc index (CLAUDE.md, README.md, docs/README.md or docs/index.md)
  * CLAUDE.md size and dated history lines; whether the project has a README
then a numbered tidy plan. Changes happen only after the user approves them — `git add`, `git mv`,
a .gitignore exception — each group committed on its own.

Settings (`organize:` in .claude/project.yaml, all optional):
  output_dirs [results/, figures/]   scratch_dirs [scratchpad/]   large_file_mb 5
  scratch_max_age_days 30            claude_md_max_lines 250

Usage:
    python project_audit.py [--repo PATH] [--limit 12]
    python project_audit.py --demo
"""
import argparse
import datetime as dt
import os
import re
import subprocess
import sys
import tempfile
import time

DEFAULTS = {"output_dirs": ["results/", "figures/"], "scratch_dirs": ["scratchpad/"], "large_file_mb": 5,
            "scratch_max_age_days": 30, "claude_md_max_lines": 250}
SOURCE_EXT = {"py", "ipynb", "md", "tex", "bib", "yaml", "yml", "toml", "sh", "r", "jl", "m", "c", "cpp", "h",
              "org", "svg", "cfg", "ini"}
JUNK = ("__pycache__/", ".ipynb_checkpoints/", ".egg-info/", "node_modules/", ".venv/", ".git/")
# strong suffixes mark a copy on their own; weak ones (make_comment_copy.py) only when the base file exists
STRONG = re.compile(r"(_v\d+[a-z]?|_\d{4}-\d{2}-\d{2}|_\d{8}| \(\d+\)| copy)$", re.I)
WEAK = re.compile(r"(_old|_new|_final|_copy|_bak|_backup|_orig|_tmp)$", re.I)
DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")


def _git(root, *args):
    r = subprocess.run(["git", "-C", root, *args], capture_output=True)
    return r.stdout.decode(errors="ignore") if r.returncode == 0 else ""


def _z(out):
    return [p for p in out.split("\0") if p]


def load_cfg(root):
    p = os.path.join(root, ".claude", "project.yaml")
    if not os.path.exists(p):
        return dict(DEFAULTS)
    try:
        import yaml
    except ImportError:
        print("note: PyYAML not installed — using default settings", file=sys.stderr)
        return dict(DEFAULTS)
    try:
        return {**DEFAULTS, **((yaml.safe_load(open(p)) or {}).get("organize") or {})}
    except yaml.YAMLError as e:
        print(f"note: cannot parse {p}: {e} — using default settings", file=sys.stderr)
        return dict(DEFAULTS)


def _under(path, prefixes):
    return any(path.startswith(p) or f"/{p}" in f"/{path}" for p in prefixes)


def _is_source(path):
    return "." in os.path.basename(path) and path.rsplit(".", 1)[-1].lower() in SOURCE_EXT and not _under(path, JUNK)


def audit(root, cfg):
    tracked = _z(_git(root, "ls-files", "-z"))
    untracked = _z(_git(root, "ls-files", "-z", "--others", "--exclude-standard"))
    ignored = _z(_git(root, "ls-files", "-z", "--others", "--ignored", "--exclude-standard"))
    outputs, scratch = cfg["output_dirs"], cfg["scratch_dirs"]
    r = {}
    r["untracked_sources"] = sorted((p for p in untracked if _is_source(p) and not _under(p, outputs + scratch)),
                                    key=lambda p: -os.path.getmtime(os.path.join(root, p)))
    hidden = [p for p in ignored if _is_source(p) and not _under(p, outputs + scratch)]
    r["ignored_sources"] = []
    for p in sorted(hidden)[:200]:
        rule = _git(root, "check-ignore", "-v", "--", p).strip().split("\t")[0]
        r["ignored_sources"].append((p, rule))
    everything = tracked + untracked
    stems = {os.path.splitext(p)[0]: p for p in everything}
    r["versioned_copies"] = []
    for p in everything:
        stem, ext = os.path.splitext(p)
        m = STRONG.search(stem) or WEAK.search(stem)
        if m and _is_source(p):
            base = stems.get(stem[:m.start()])
            if base or STRONG.search(stem):
                r["versioned_copies"].append((p, base))
    r["previews"] = [p for p in everything if _is_source(p) and re.search(r"preview", os.path.basename(p), re.I)]
    big = cfg["large_file_mb"] * 2 ** 20
    sizes = [(p, os.path.getsize(os.path.join(root, p))) for p in tracked if os.path.isfile(os.path.join(root, p))]
    r["large_tracked"] = sorted(((p, s) for p, s in sizes if s > big), key=lambda x: -x[1])
    r["scratch"] = []
    now = time.time()
    for sdir in scratch:
        base = os.path.join(root, sdir)
        if not os.path.isdir(base):
            continue
        files = [os.path.join(d, f) for d, _, fs in os.walk(base) for f in fs if "__pycache__" not in d]
        old = sorted((f for f in files if now - os.path.getmtime(f) > cfg["scratch_max_age_days"] * 86400),
                     key=os.path.getmtime)
        r["scratch"].append({"dir": sdir, "files": len(files), "mb": sum(map(os.path.getsize, files)) / 2 ** 20,
                             "old": [os.path.relpath(f, root) for f in old],
                             "tracked": sum(1 for p in tracked if p.startswith(sdir))})
    index_files = [os.path.join(root, f) for f in ("CLAUDE.md", "README.md", "docs/README.md", "docs/index.md")]
    index = "".join(open(f, errors="ignore").read() for f in index_files if os.path.exists(f))
    docs = [p for p in tracked + untracked if p.startswith("docs/") and p.endswith(".md")
            and p not in ("docs/README.md", "docs/index.md")]
    r["unindexed_docs"] = sorted(p for p in docs if p not in index and os.path.basename(p) not in index)
    cm = os.path.join(root, "CLAUDE.md")
    if os.path.exists(cm):
        text = open(cm, errors="ignore").read()
        r["claude_md"] = {"lines": text.count("\n") + 1, "kb": len(text.encode()) / 1024,
                          "dated_lines": sum(1 for l in text.splitlines() if DATE.search(l))}
    else:
        r["claude_md"] = None
    r["readme"] = os.path.exists(os.path.join(root, "README.md"))
    return r


def plan(r, cfg):
    steps = []
    if r["untracked_sources"]:
        dirs = sorted({os.path.dirname(p) or "." for p in r["untracked_sources"]})
        steps.append(f"Version {len(r['untracked_sources'])} untracked source file(s) — `git add` them (or delete the "
                     f"dead ones) in: {', '.join(dirs[:8])}{' …' if len(dirs) > 8 else ''}")
    if r["ignored_sources"]:
        rules = sorted({rule for _, rule in r["ignored_sources"] if rule})
        steps.append(f"Un-hide {len(r['ignored_sources'])} ignored source file(s): narrow the rule(s) {', '.join(rules[:4])} "
                     "to output folders, or add `!path` exceptions")
    if r["versioned_copies"]:
        steps.append(f"Resolve {len(r['versioned_copies'])} version-suffixed copies: diff each against its base "
                     "(`git diff --no-index base copy`), keep one file, delete the copy — git keeps the history")
    if r["previews"]:
        steps.append(f"Decide on {len(r['previews'])} exploratory 'preview' scripts: promote the ones still used, delete the rest")
    if r["large_tracked"]:
        steps.append(f"Move {len(r['large_tracked'])} large tracked file(s) out of git (outputs belong in ignored output "
                     "folders); rewriting history is a separate decision")
    for s in r["scratch"]:
        if s["old"]:
            steps.append(f"{s['dir']}: {len(s['old'])} of {s['files']} files older than {cfg['scratch_max_age_days']} days — "
                         "promote what is still used (`git mv` into scripts/ with a docstring), delete the rest")
    if r["unindexed_docs"]:
        steps.append(f"Add {len(r['unindexed_docs'])} doc(s) to the doc index (CLAUDE.md table or docs/README.md)")
    cm = r["claude_md"]
    if cm and cm["lines"] > cfg["claude_md_max_lines"]:
        steps.append(f"Slim CLAUDE.md ({cm['lines']} lines, {cm['dated_lines']} dated): keep rules and the doc map, "
                     "move dated history into docs")
    if not r["readme"]:
        steps.append("Write a README.md: what the project is, how to run it, where results and docs live")
    return steps


def report(root, r, cfg, limit):
    print(f"PROJECT AUDIT · {os.path.basename(root)} (read-only — nothing is changed)")
    print(f"untracked source files: {len(r['untracked_sources'])}")
    for p in r["untracked_sources"][:limit]:
        print(f"  {dt.datetime.fromtimestamp(os.path.getmtime(os.path.join(root, p))):%Y-%m-%d}  {p}")
    print(f"ignored source files: {len(r['ignored_sources'])}")
    for p, rule in r["ignored_sources"][:limit]:
        print(f"  {p}   ← {rule}")
    print(f"version-suffixed copies: {len(r['versioned_copies'])}")
    for p, base in r["versioned_copies"][:limit]:
        print(f"  {p}" + (f"   (copy of {base})" if base else ""))
    print(f"exploratory 'preview' scripts: {len(r['previews'])}")
    print(f"large tracked files (> {cfg['large_file_mb']} MB): {len(r['large_tracked'])}")
    for p, s in r["large_tracked"][:limit]:
        print(f"  {s / 2 ** 20:7.1f} MB  {p}")
    for s in r["scratch"]:
        print(f"scratch {s['dir']}: {s['files']} files, {s['mb']:.1f} MB, {s['tracked']} tracked, "
              f"{len(s['old'])} older than {cfg['scratch_max_age_days']} days")
    print(f"docs missing from the index: {len(r['unindexed_docs'])}")
    for p in r["unindexed_docs"][:limit]:
        print(f"  {p}")
    cm = r["claude_md"]
    print("CLAUDE.md: " + (f"{cm['lines']} lines, {cm['kb']:.0f} KB, {cm['dated_lines']} dated lines" if cm else "none")
          + f" · README.md: {'yes' if r['readme'] else 'MISSING'}")
    steps = plan(r, cfg)
    print("TIDY PLAN (proposal — run nothing until the user approves):")
    for i, s in enumerate(steps, 1):
        print(f"  {i}. {s}")
    print(f"SUMMARY: {len(steps)} proposed step(s)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="any path inside the project's repository")
    ap.add_argument("--limit", type=int, default=12, help="rows shown per finding")
    ap.add_argument("--demo", action="store_true", help="self-test in a throwaway repository")
    a = ap.parse_args(argv)
    if a.demo:
        return _demo()
    root = _git(a.repo, "rev-parse", "--show-toplevel").strip()
    if not root:
        print("not inside a git repository"); return 1
    cfg = load_cfg(root)
    report(root, audit(root, cfg), cfg, a.limit)
    return 0


def _demo():
    with tempfile.TemporaryDirectory() as root:
        def w(path, text="x = 1\n", age_days=0):
            p = os.path.join(root, path); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(text)
            if age_days:
                t = time.time() - age_days * 86400; os.utime(p, (t, t))
        w(".claude/project.yaml", "organize:\n  large_file_mb: 0.001\n  claude_md_max_lines: 5\n")
        w(".gitignore", "*.svg\nresults/\n")
        w("src/model.py"); w("fig_main.py"); w("fig_main_v2.py"); w("make_comment_copy.py")
        w("docs/a.md", "# A\n"); w("docs/b.md", "# B\n")
        w("CLAUDE.md", "# Project\nSee docs/a.md\n" + "".join(f"- 2026-09-{d:02d}: note\n" for d in range(1, 10)))
        w("data.bin", "0" * 5000)
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@t"}
        for cmd in (["git", "init", "-q"], ["git", "add", "-A"], ["git", "commit", "-qm", "init"]):
            subprocess.run(cmd, cwd=root, env=env, check=True, capture_output=True)
        w("scheme.svg", "<svg/>"); w("results/plot.svg", "<svg/>"); w("fig_new.py")
        w("scratchpad/old_try.py", age_days=60); w("scratchpad/today.py")
        before = _git(root, "status", "--porcelain")
        r = audit(root, load_cfg(root)); steps = plan(r, load_cfg(root))
        after = _git(root, "status", "--porcelain")
    checks = [("untracked source found (fig_new.py)", r["untracked_sources"] == ["fig_new.py"]),
              ("hand-made SVG hidden by *.svg found; output SVG not", [p for p, _ in r["ignored_sources"]] == ["scheme.svg"]),
              ("the ignore rule is named", "*.svg" in r["ignored_sources"][0][1]),
              ("version copy paired with its base; make_comment_copy.py not flagged",
               r["versioned_copies"] == [("fig_main_v2.py", "fig_main.py")]),
              ("large tracked file found", [p for p, _ in r["large_tracked"]] == ["data.bin"]),
              ("old scratch file found", r["scratch"] and r["scratch"][0]["old"] == ["scratchpad/old_try.py"]),
              ("doc missing from the index found", r["unindexed_docs"] == ["docs/b.md"]),
              ("long CLAUDE.md and missing README flagged", any("CLAUDE.md" in s for s in steps) and not r["readme"]),
              ("the audit changed nothing", before == after)]
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'} ({sum(bool(c) for _, c in checks)}/{len(checks)})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
