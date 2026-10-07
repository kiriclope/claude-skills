"""Check the ledger of published pages (`pages:` in .claude/project.yaml) before anything is republished.

Each page entry:
    pages:
      - name: Draft                        # unique — the page title readers see
        url: https://claude.ai/code/artifact/<id>
        source: paper/build/draft.html     # the built page (may be gitignored; never in a temp or job folder)
        builder: build_draft.py            # tracked script that rebuilds the source from repo files
        inputs: [docs/paper/*.md]          # optional: what the page is built from (staleness check)
        shared: private                    # private | link  (link-holders may see a pinned older version)

Flags, by severity:
  error  source or builder inside a temp / job / scratch folder (lost when the session ends)
         builder missing; two pages with the same name or the same url
  warn   builder not tracked by git; source missing (rebuild, or recover it with an Artifact read)
         source older than its builder or one of its inputs (rebuild before republishing)
         source above 12 MB (the artifact limit is 16 MB, embedded data: URIs included)
  info   shared by link: readers keep a pinned version until the pin is advanced from the share menu

Usage:
    python pages_check.py [--project_yaml .claude/project.yaml]
    python pages_check.py --demo
"""
import argparse
import glob
import os
import re
import subprocess
import sys
import tempfile

VOLATILE = re.compile(r"(^|/)(tmp|temp|scratchpad|scratch)(/|$)|\.claude/jobs/|CLAUDE_JOB_DIR|^/tmp/")
URL = re.compile(r"^https://(claude\.ai/(code/)?artifact/|docs\.google\.com/)")
SIZE_WARN = 12 * 2 ** 20


def find_project_yaml(start="."):
    d = os.path.abspath(start)
    while True:
        p = os.path.join(d, ".claude", "project.yaml")
        if os.path.exists(p):
            return p
        if os.path.dirname(d) == d:
            return None
        d = os.path.dirname(d)


def tracked(root, path):
    r = subprocess.run(["git", "-C", root, "ls-files", "--error-unmatch", path], capture_output=True)
    return r.returncode == 0


def check(yaml_path):
    import yaml
    root = os.path.dirname(os.path.dirname(os.path.abspath(yaml_path)))
    pages = (yaml.safe_load(open(yaml_path)) or {}).get("pages") or []
    out = []                                                   # (severity, page, message)
    names, urls = {}, {}
    for p in pages:
        name = p.get("name") or "(unnamed)"
        names.setdefault(name, 0); names[name] += 1
        if p.get("url"):
            urls.setdefault(p["url"], []).append(name)
            if not URL.match(p["url"]):
                out.append(("info", name, f"url does not look like an artifact or Google Doc link: {p['url']}"))
        else:
            out.append(("warn", name, "no url recorded — publish, then record the url here"))
        src, bld = p.get("source"), p.get("builder")
        for kind, path in (("source", src), ("builder", bld)):
            if path and VOLATILE.search(os.path.expandvars(path)):
                out.append(("error", name, f"{kind} lives in a temporary folder ({path}): it disappears with the "
                                           "session — move it into the repo"))
        src_abs = os.path.join(root, src) if src else None
        bld_abs = os.path.join(root, bld) if bld else None
        if not bld:
            out.append(("error", name, "no builder recorded — the page cannot be rebuilt from the repo"))
        elif not os.path.exists(bld_abs):
            out.append(("error", name, f"builder missing: {bld}"))
        elif not tracked(root, bld):
            out.append(("warn", name, f"builder not tracked by git: {bld}"))
        if src and not os.path.exists(src_abs):
            out.append(("warn", name, f"source missing ({src}): rebuild it, or recover the live page with an "
                                      "Artifact read and save it there"))
        elif src:
            mt = os.path.getmtime(src_abs)
            if bld and os.path.exists(bld_abs) and os.path.getmtime(bld_abs) > mt:
                out.append(("warn", name, "builder changed after the source was built — rebuild before republishing"))
            newer = [f for g in (p.get("inputs") or []) for f in glob.glob(os.path.join(root, g))
                     if os.path.getmtime(f) > mt]
            if newer:
                out.append(("warn", name, f"{len(newer)} input(s) newer than the source (e.g. "
                                          f"{os.path.relpath(newer[0], root)}) — rebuild before republishing"))
            if os.path.getsize(src_abs) > SIZE_WARN:
                out.append(("warn", name, f"source is {os.path.getsize(src_abs) / 2 ** 20:.1f} MB — the artifact "
                                          "limit is 16 MB including embedded images"))
        if str(p.get("shared", "")).lower() == "link":
            out.append(("info", name, "shared by link: readers may see a pinned older version until the pin is "
                                      "advanced from the page's share menu (no tool can do it)"))
    for n, k in names.items():
        if k > 1:
            out.append(("error", n, f"{k} pages share this name — readers will share the wrong one; retitle the "
                                    "retired page"))
    for u, ns in urls.items():
        if len(ns) > 1:
            out.append(("error", ", ".join(ns), f"same url recorded for {len(ns)} pages"))
    return pages, out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project_yaml", default=None, help="default: the nearest .claude/project.yaml")
    ap.add_argument("--demo", action="store_true", help="self-test on a throwaway project")
    a = ap.parse_args(argv)
    if a.demo:
        return _demo()
    y = a.project_yaml or find_project_yaml()
    if not y:
        print("no .claude/project.yaml found"); return 1
    pages, out = check(y)
    print(f"PAGES · {len(pages)} recorded in {y}")
    order = {"error": 0, "warn": 1, "info": 2}
    for sev, name, msg in sorted(out, key=lambda r: order[r[0]]):
        print(f"  {sev:5s}  {name:24s} {msg}")
    n_err = sum(r[0] == "error" for r in out)
    print(f"SUMMARY: {n_err} error, {sum(r[0] == 'warn' for r in out)} warn" + ("  ✓" if not n_err else ""))
    return 1 if n_err else 0


def _demo():
    import time
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["git", "init", "-q"], cwd=d, check=True)
        os.makedirs(os.path.join(d, ".claude")); os.makedirs(os.path.join(d, "build")); os.makedirs(os.path.join(d, "docs"))
        open(os.path.join(d, "build_draft.py"), "w").write("print('build')\n")
        subprocess.run(["git", "add", "build_draft.py"], cwd=d, check=True)
        open(os.path.join(d, "build", "draft.html"), "w").write("<p>draft</p>")
        time.sleep(0.05)
        open(os.path.join(d, "docs", "results.md"), "w").write("new text")       # input newer than the source
        open(os.path.join(d, ".claude", "project.yaml"), "w").write(
            "pages:\n"
            "  - {name: Draft, url: 'https://claude.ai/code/artifact/aaa', source: build/draft.html,"
            " builder: build_draft.py, inputs: [docs/*.md], shared: link}\n"
            "  - {name: Figures, url: 'https://claude.ai/code/artifact/bbb', source: /tmp/figs.html,"
            " builder: scratchpad/build_figs.py}\n"
            "  - {name: Figures, url: 'https://claude.ai/code/artifact/ccc', source: build/old.html, builder: build_draft.py}\n")
        _, out = check(os.path.join(d, ".claude", "project.yaml"))
    msgs = [f"{s} {n} {m}" for s, n, m in out]
    checks = [("source in a temp folder is an error", any(s == "error" and "temporary folder" in m for s, _, m in out)),
              ("missing builder is an error", any("builder missing" in m for _, _, m in out)),
              ("input newer than source is flagged", any("newer than the source" in m for _, _, m in out)),
              ("duplicate page names are an error", any("share this name" in m for _, _, m in out)),
              ("link sharing gets the pinned-version note", any("pinned older version" in m for _, _, m in out)),
              ("a tracked builder raises no git warning", not any("not tracked" in m and "Draft" in m for m in msgs))]
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'} ({sum(c for _, c in checks)}/{len(checks)})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
