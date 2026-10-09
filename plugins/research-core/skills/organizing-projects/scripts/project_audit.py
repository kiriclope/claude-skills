"""Audit how a research repository is organized and propose a tidy plan. It never moves or deletes anything.

Reports, for the git project around --repo:
  * untracked source files — code, docs, configs, hand-made vector art that git does not version
  * ignored source files — an ignore rule hides a source (e.g. `*.svg` hiding a hand-drawn scheme)
  * version-suffixed copies (_v2, _v1259, _old, _final, _copy, _bak, dated) and exploratory leftovers (preview)
  * large tracked files
  * scratch folders: size, file count, files older than the age limit (promote or delete)
  * docs missing from the doc index (CLAUDE.md, README.md, any README.md or index.md under docs/)
  * CLAUDE.md size and dated history lines; whether the project has a README
then a numbered tidy plan. Changes happen only after the user approves them — `git add`, `git mv`,
a .gitignore exception — each group committed on its own.

--staged checks only the commit the index would make (before each commit; the Bash guard runs it on
`git commit` in projects with .claude/project.yaml). Exit 1 when something blocks.
  ✗ blocks (clear mess): a path under `never_stage`; a force-added ignored file; editor/OS junk
    (`file~`, `.#file`, `.pyc`, `.DS_Store`); a file over large_file_mb (new, or grown past it);
    a version-suffixed copy of code (`fig_v2.py`, `fig_old.py` next to `fig.py`).
  ?  proposes: a new file under an output folder; a staged scratch file; a new doc missing from the
    doc index; a README that misses a new top-level folder or script, or a file in a folder whose
    README lists its files; an index or README that still names a file the commit removes; an
    untracked file that staged code refers to; a dated or versioned doc name; no README at all.

Settings (`organize:` in .claude/project.yaml, all optional):
  output_dirs [results/, figures/]   scratch_dirs [scratchpad/]   large_file_mb 5
  scratch_max_age_days 30            claude_md_max_lines 250      commit_check true
plus the top-level `never_stage:` list (path, folder/ or glob; entries with spaces are notes, skipped).

Usage:
    python project_audit.py [--repo PATH] [--limit 12]
    python project_audit.py --staged [--all] [--repo PATH]     # --all: as `git commit -a` would commit
    python project_audit.py --demo
"""
import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

DEFAULTS = {"output_dirs": ["results/", "figures/"], "scratch_dirs": ["scratchpad/"], "large_file_mb": 5,
            "scratch_max_age_days": 30, "claude_md_max_lines": 250, "commit_check": True, "never_stage": []}
SOURCE_EXT = {"py", "ipynb", "md", "tex", "bib", "yaml", "yml", "toml", "sh", "r", "jl", "m", "c", "cpp", "h",
              "org", "svg", "cfg", "ini"}
JUNK = ("__pycache__/", ".ipynb_checkpoints/", ".egg-info/", "node_modules/", ".venv/", ".git/")
# strong suffixes mark a copy on their own; weak ones (make_comment_copy.py) only when the base file exists
STRONG = re.compile(r"(_v\d+[a-z]?|_\d{4}-\d{2}-\d{2}|_\d{8}| \(\d+\)| copy)$", re.I)
WEAK = re.compile(r"(_old|_new|_final|_copy|_bak|_backup|_orig|_tmp)$", re.I)
DATE = re.compile(r"\b20\d\d-\d\d-\d\d\b")
DATED = re.compile(r"_(\d{4}-\d{2}-\d{2}|\d{8})$")
DOC_EXT = {"md", "org", "tex", "bib"}           # a dated or _v2 doc is often a deliberate record: proposed, not blocked
JUNK_NAME = re.compile(r"(^\.#|^#.*#$|~$|\.py[co]$|^\.DS_Store$|^Thumbs\.db$)")
INDEX_FILES = ("CLAUDE.md", "README.md", "docs/README.md", "docs/index.md")
SCRIPT_EXT = {"py", "sh", "r", "jl", "m"}
NOT_ENTRY = {"__init__.py", "setup.py", "conftest.py"}


def _git(root, *args, env=None, inp=None):
    r = subprocess.run(["git", "-C", root, *args], capture_output=True, env=env, input=inp)
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
        y = yaml.safe_load(open(p)) or {}
        return {**DEFAULTS, **(y.get("organize") or {}), "never_stage": y.get("never_stage") or []}
    except yaml.YAMLError as e:
        print(f"note: cannot parse {p}: {e} — using default settings", file=sys.stderr)
        return dict(DEFAULTS)


def _under(path, prefixes):
    return any(path.startswith(p) or f"/{p}" in f"/{path}" for p in prefixes)


def _is_source(path):
    return "." in os.path.basename(path) and path.rsplit(".", 1)[-1].lower() in SOURCE_EXT and not _under(path, JUNK)


def _index_text(root, paths):
    """Text of every doc index: CLAUDE.md, README.md, and each README.md / index.md under docs/."""
    subs = [p for p in paths if p.startswith("docs/") and os.path.basename(p) in ("README.md", "index.md")]
    return "".join(_read(root, f) for f in dict.fromkeys(list(INDEX_FILES) + subs))


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
    index = _index_text(root, tracked + untracked)
    docs = [p for p in tracked + untracked if p.startswith("docs/") and p.endswith(".md")
            and os.path.basename(p) not in ("README.md", "index.md")]
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
        steps.append(f"Add {len(r['unindexed_docs'])} doc(s) to the doc index "
                     "(CLAUDE.md table, docs/README.md or the folder's README.md)")
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


# ---- staged mode: this commit only --------------------------------------------------------------

def _changes(root, env):
    """(status, path, old_path) for each change in the index; old_path only for a rename or copy."""
    toks, out, i = _z(_git(root, "diff", "--cached", "--name-status", "-z", "-M", env=env)), [], 0
    while i < len(toks):
        st = toks[i][0]
        if st in "RC":
            out.append((st, toks[i + 2], toks[i + 1])); i += 3
        else:
            out.append((st, toks[i + 1], None)); i += 2
    return out


def _blob_sizes(root, env, specs):
    """{spec: bytes} for specs like ':path' (the index) and 'HEAD:path'; missing objects are left out."""
    if not specs:
        return {}
    out = _git(root, "cat-file", "--batch-check=%(objectsize)", env=env, inp="\n".join(specs).encode() + b"\n")
    return {sp: int(line) for sp, line in zip(specs, out.splitlines()) if line.isdigit()}


def _never_stage_rule(path, rules):
    for rule in rules:
        rule = str(rule).strip()
        if not rule or " " in rule:                       # a prose note, not a path
            continue
        if any(ch in rule for ch in "*?["):
            import fnmatch
            if fnmatch.fnmatch(path, rule) or fnmatch.fnmatch(os.path.basename(path), rule):
                return rule
        elif path == rule.rstrip("/") or path.startswith(rule.rstrip("/") + "/"):
            return rule
    return None


def _read(root, rel):
    p = os.path.join(root, rel)
    try:
        return open(p, errors="ignore").read() if os.path.isfile(p) and os.path.getsize(p) < 2 ** 21 else ""
    except OSError:
        return ""


def _names(text, name):
    """`name` appears in text as a whole name (not inside a longer file or folder name)."""
    return re.search(rf"(?<![\w.-]){re.escape(name)}(?![\w-])", text) is not None


def _blocking(root, cfg, env, kept, tracked):
    """({path: why} for the clear-mess files, [(path, why)] for dated or versioned doc names)."""
    new = [p for st, p in kept if st in "ACR"]
    sizes = _blob_sizes(root, env, [f":{p}" for _, p in kept] + [f"HEAD:{p}" for st, p in kept if st == "M"])
    ignored = set(_z(_git(root, "check-ignore", "--no-index", "-z", "--stdin", env=env,
                          inp="\0".join(new).encode() + b"\0"))) if new else set()
    stems = {os.path.splitext(p)[0]: p for p in tracked}
    big = cfg["large_file_mb"] * 2 ** 20
    block, prop = {}, []
    for st, p in kept:
        is_new, size = st in "ACR", sizes.get(f":{p}", 0)
        why = []
        rule = _never_stage_rule(p, cfg["never_stage"])
        if rule:
            why.append(f"matches never_stage `{rule}` (.claude/project.yaml)")
        if is_new and p in ignored:
            why.append("ignored by .gitignore, so it was force-added: "
                       "add a `!path` exception if it is a source, else leave it out")
        if is_new and (JUNK_NAME.search(os.path.basename(p)) or _under(p, JUNK)):
            why.append("editor/OS/build junk")
        if size > big and (is_new or sizes.get(f"HEAD:{p}", 0) <= big):
            why.append(f"{size / 2 ** 20:.1f} MB (> {cfg['large_file_mb']} MB): data and outputs stay out of git")
        stem = os.path.splitext(p)[0]
        m = STRONG.search(stem) or WEAK.search(stem)
        base = stems.get(stem[:m.start()]) if m else None
        if is_new and m and _is_source(p) and not why and (base or STRONG.search(stem)):
            if os.path.splitext(p)[1][1:].lower() in DOC_EXT or (DATED.search(stem) and not base):
                prop.append((p, "dated or versioned name" + (f" next to {base}" if base else "")
                             + ": keep one current file, unless this is a dated record"))
            else:
                why.append(f"version-suffixed copy{f' of {base}' if base else ''}: edit "
                           f"{base or 'the original'} instead (git keeps the history)")
        if why:
            block[p] = "; ".join(why)
    return block, prop


def _doc_proposals(root, cfg, new, gone, tracked):
    """README and doc-index lines the commit needs: new folders, scripts and docs; files it removes."""
    outputs, scratch = cfg["output_dirs"], cfg["scratch_dirs"]
    prop = []
    index = _index_text(root, tracked)
    for p in new:
        if p.startswith("docs/") and p.endswith(".md") and os.path.basename(p) not in ("README.md", "index.md") \
                and p not in index and os.path.basename(p) not in index:
            prop.append((p, "new doc missing from the doc index: add a line to the CLAUDE.md doc table "
                            "or the folder's README.md"))
    readme = _read(root, "README.md")
    if not os.path.isfile(os.path.join(root, "README.md")):
        prop.append(("README.md", "missing: write one (what the project is, how to run it, "
                                  "where results and docs live)"))
    else:
        top = set(_z(_git(root, "ls-tree", "-z", "--name-only", "HEAD")))
        for d in sorted({p.split("/")[0] for p in new if "/" in p} - top):
            if not d.startswith(".") and not _under(d + "/", outputs + scratch) and not _names(readme, d):
                prop.append((d + "/", "new top-level folder not in README.md: add a line on what it holds"))
        for p in new:
            if "/" not in p and os.path.splitext(p)[1][1:].lower() in SCRIPT_EXT and p not in NOT_ENTRY \
                    and not p.startswith("test_") and not _names(readme, p):
                prop.append((p, "new top-level script not in README.md: add a line (what it does, how to run it)"))
    for p in new:
        d = os.path.dirname(p)
        rd = f"{d}/README.md" if d else None
        if not rd or p == rd or not os.path.isfile(os.path.join(root, rd)):
            continue
        text = _read(root, rd)
        siblings = [os.path.basename(t) for t in tracked if os.path.dirname(t) == d and t not in (p, rd)]
        if any(_names(text, x) for x in siblings) and not _names(text, os.path.basename(p)):
            prop.append((p, f"{rd} lists the files of {d}/ but not this one: add a line"))
    after = {os.path.basename(t) for t in tracked}
    for old, now in gone:
        b, d = os.path.basename(old), os.path.dirname(old)
        if b in after or b in ("README.md", "__init__.py") or _under(old, outputs + scratch + list(JUNK)):
            continue
        for f in dict.fromkeys(list(INDEX_FILES) + ([f"{d}/README.md"] if d else [])):
            text = _read(root, f)
            if text and (old in text or _names(text, b)):
                prop.append((f, f"still names {old}, which this commit "
                                f"{'renames to ' + now if now else 'removes'}: update or drop the line"))
    return prop


IMPORT = re.compile(r"^[ \t]*(?:from[ \t]+([\w.]+)[ \t]+import[ \t]+(\([^)]*\)|[\w \t,]+)"   # from a.b import c, (d, e)
                    r"|import[ \t]+([\w. \t,]+))", re.M)                                     # import a.b as x, y


def _imported_modules(text):
    """Dotted names a Python file imports: `from a.b import c` gives a.b and a.b.c; `import a.b as x` gives a.b."""
    mods = set()
    for frm, names, plain in IMPORT.findall(text):
        if frm:
            mods.add(frm)
            names = names.strip("()").split(",")
            mods.update(f"{frm}.{n.split()[0]}" for n in names if n.strip())
        else:
            mods.update(n.split()[0] for n in plain.split(",") if n.strip())
    return mods


def _untracked_refs(root, cfg, env, kept, tracked):
    """Untracked source files that a staged file imports or names by path: the commit will not stand on its own.
    A bare file name counts only next to the staged file, or when no tracked file has that name."""
    untracked = [u for u in _z(_git(root, "ls-files", "-z", "--others", "--exclude-standard", env=env))
                 if _is_source(u) and not _under(u, cfg["output_dirs"] + cfg["scratch_dirs"])][:3000]
    if not untracked:
        return []
    names = {}
    for t in tracked:
        names.setdefault(os.path.basename(t), set()).add(t)
    prop, seen = [], set()
    for _, p in kept:
        if os.path.splitext(p)[1][1:].lower() not in {"py", "sh", "md", "tex", "yaml", "yml", "ipynb"}:
            continue
        text = _read(root, p)
        mods = _imported_modules(text) if p.endswith(".py") else set()
        here = os.path.dirname(p)
        for u in untracked:
            if u in seen:
                continue
            b, d = os.path.basename(u), os.path.dirname(u)
            dotted = os.path.splitext(u)[0].replace("/", ".")
            stem = os.path.splitext(b)[0]
            hit = u in text \
                or (_names(text, b) and (d == here or b not in names)) \
                or (u.endswith(".py") and (dotted in mods or (d == here and stem in mods)))
            if hit:
                seen.add(u)
                consequence = "the doc points to a file git does not have" if p.endswith(".md") \
                    else "a fresh clone will not run"
                prop.append((u, f"untracked, but {p} (staged) refers to it: stage it too, or {consequence}"))
    return prop


def staged_check(root, cfg, env=None):
    """Tidy check of the commit the index would make.
    Returns {"block": [(path, why)], "propose": [(path, why)], "staged": number of staged changes}."""
    changes = _changes(root, env)
    tracked = _z(_git(root, "ls-files", "-z", env=env))
    kept = [(st, p) for st, p, _ in changes if st != "D"]
    gone = [(old or p, p if old else None) for st, p, old in changes if st in "DR"]
    block, prop = _blocking(root, cfg, env, kept, tracked)
    new = [p for st, p in kept if st in "ACR" and p not in block]
    for p in new:
        if any(p.startswith(o) for o in cfg["output_dirs"]):
            prop.append((p, "new file under an output folder: commit it only if it is a deliverable "
                            "(a paper figure), else leave it out or ignore the folder"))
        elif _under(p, cfg["scratch_dirs"]):
            prop.append((p, "scratch file: promote it (`git mv` into scripts/, add a docstring) or leave it out"))
    prop += _doc_proposals(root, cfg, new, gone, tracked)
    prop += _untracked_refs(root, cfg, env, [(st, p) for st, p in kept if p not in block], tracked)
    return {"block": sorted(block.items()), "propose": prop, "staged": len(changes)}


def check_commit(root, cfg, adds=(), commit_all=False):
    """staged_check of the commit that follows `git add <args>` (each (cwd, args) in adds) and, with commit_all,
    `git commit -a`. The adds run against a throwaway copy of the index; the real index is never touched."""
    if not adds and not commit_all:
        return {**staged_check(root, cfg), "notes": []}
    idx = _git(root, "rev-parse", "--git-path", "index").strip()
    idx = idx if os.path.isabs(idx) else os.path.join(root, idx)
    notes = []
    with tempfile.TemporaryDirectory() as d:
        tmp = os.path.join(d, "index")
        if os.path.exists(idx):
            shutil.copy2(idx, tmp)
        env = {**os.environ, "GIT_INDEX_FILE": tmp}
        for cwd, args in list(adds) + ([(root, ["-u"])] if commit_all else []):
            try:
                r = subprocess.run(["git", "add", *args], cwd=cwd, env=env, capture_output=True,
                                   stdin=subprocess.DEVNULL, timeout=5)
            except subprocess.TimeoutExpired:
                notes.append(f"`git add {' '.join(args)}` timed out in the simulation"); continue
            if r.returncode:
                notes.append(f"`git add {' '.join(args)}` would fail: {r.stderr.decode(errors='ignore').strip()[:200]}")
        return {**staged_check(root, cfg, env), "notes": notes}


def staged_report(root, res):
    print(f"TIDY CHECK · {os.path.basename(root)} · this commit only ({res['staged']} staged change(s))")
    for note in res.get("notes", []):
        print(f"  note: {note}")
    for p, why in res["block"]:
        print(f"  ✗ {p} — {why}")
    for p, why in res["propose"]:
        print(f"  ? {p} — {why}")
    if res["block"]:
        print("✗ = clear mess, blocks the commit: unstage (`git restore --staged <path>`), move or delete it; "
              "commit it anyway only if the user named that file.")
    if res["propose"]:
        print("? = proposals: README / index lines for this commit's own files go in with it; "
              "moves need the user's yes.")
    print(f"SUMMARY: {len(res['block'])} blocking, {len(res['propose'])} proposal(s)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="any path inside the project's repository")
    ap.add_argument("--limit", type=int, default=12, help="rows shown per finding")
    ap.add_argument("--staged", action="store_true", help="check only what the next commit would contain")
    ap.add_argument("--all", action="store_true",
                    help="with --staged: as `git commit -a` would commit (adds modified tracked files)")
    ap.add_argument("--demo", action="store_true", help="self-test in a throwaway repository")
    a = ap.parse_args(argv)
    if a.demo:
        return _demo()
    root = _git(a.repo, "rev-parse", "--show-toplevel").strip()
    if not root:
        print("not inside a git repository"); return 1
    cfg = load_cfg(root)
    if a.staged:
        if cfg.get("commit_check") is False:
            print("TIDY CHECK off (organize.commit_check: false)"); return 0
        res = check_commit(root, cfg, commit_all=a.all)
        staged_report(root, res)
        return 1 if res["block"] else 0
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
        w("docs/a.md", "# A\n"); w("docs/b.md", "# B\n"); w("docs/sub/README.md", "- c.md\n"); w("docs/sub/c.md")
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
    checks += _demo_staged()
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'} ({sum(bool(c) for _, c in checks)}/{len(checks)})")
    return 0 if ok else 1



def _demo_staged():
    """One staged change per --staged rule, in a throwaway repository."""
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t"}
    with tempfile.TemporaryDirectory() as root:
        def w(path, text="x = 1\n"):
            p = os.path.join(root, path); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(text)

        def git(*args):
            subprocess.run(["git", *args], cwd=root, env=env, check=True, capture_output=True)
        w(".claude/project.yaml", "never_stage: [notes/private.md]\norganize:\n  large_file_mb: 0.001\n")
        w(".gitignore", "*.log\n")
        w("README.md", "# P\nsrc/ holds the model; run sweep.py. old.py is legacy.\n")
        w("CLAUDE.md", "| [docs/a.md](docs/a.md) | A |\n")
        w("scripts/README.md", "- a.py: does A\n")
        for f in ("src/model.py", "src/plot_utils.py", "sweep.py", "docs/a.md", "scripts/a.py", "fig.py"):
            w(f)
        w("old.py", "legacy = True\n")                   # unique content, so its removal is not seen as a rename
        git("init", "-q"); git("add", "-A"); git("commit", "-qm", "init")
        cfg = load_cfg(root)
        w("run2.log")
        sim = check_commit(root, cfg, adds=[(root, ["-f", "run2.log"])])
        sim_ok = [p for p, _ in sim["block"]] == ["run2.log"] and _git(root, "diff", "--cached", "--name-only") == ""
        for f in ("results/plot.png", "fig_v2.py", "fig.py~", "notes/private.md", "run.log", "scratchpad/try.py",
                  "docs/b.md", "newtool.py", "analysis/x.py", "scripts/b.py", "docs/review_2026-10-09.md"):
            w(f)
        w("big.bin", "0" * 5000); w("src/model.py", "from src import helper\nfrom src import plot_utils\n")
        w("src/helper.py"); w("utils/plot_utils.py")      # untracked copy named like the tracked src/plot_utils.py
        git("add", "-f", "results/plot.png", "big.bin", "fig_v2.py", "fig.py~", "notes/private.md", "run.log",
            "scratchpad/try.py", "docs/b.md", "newtool.py", "analysis/x.py", "scripts/b.py",
            "docs/review_2026-10-09.md", "src/model.py")
        git("rm", "-q", "old.py")
        r = staged_check(root, cfg)
    blocked = {p for p, _ in r["block"]}
    proposed = {(p, why.split(":")[0]) for p, why in r["propose"]}
    has = lambda p, words: any(q == p and words in why for q, why in proposed)
    return [("staged: a simulated `git add -f` is checked; the real index is untouched", sim_ok),
            ("staged blocks never_stage, force-added ignored, junk, large and _v2 copy (only those)",
             blocked == {"notes/private.md", "run.log", "fig.py~", "big.bin", "fig_v2.py"}),
            ("staged proposes output, scratch, unindexed doc and dated doc",
             has("results/plot.png", "output folder") and has("scratchpad/try.py", "scratch")
             and has("docs/b.md", "doc index") and has("docs/review_2026-10-09.md", "dated")),
            ("staged proposes README lines: new script, new folder, folder listing, removed file",
             has("newtool.py", "top-level script") and has("analysis/", "top-level folder")
             and has("scripts/b.py", "scripts/README.md")
             and has("README.md", "still names old.py, which this commit removes")),
            ("staged finds the untracked module staged code imports, not a same-named copy; nothing else",
             has("src/helper.py", "untracked") and len(r["propose"]) == 10)]


if __name__ == "__main__":
    sys.exit(main())
