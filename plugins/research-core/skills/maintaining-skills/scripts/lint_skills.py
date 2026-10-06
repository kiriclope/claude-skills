"""Lint the shared skills repo and the projects that use it.

Checks per skill (SKILL.md):
  * frontmatter: name = dir name, ≤64 chars, [a-z0-9-], no "claude"/"anthropic";
    description present, ≤1024 chars, says when to use it ("Use when/whenever/BEFORE …")
  * body ≤500 lines; reference files >100 lines should start with a contents list
  * relative links / backticked paths to references/ and scripts/ exist; references one level deep
  * shareable plugins (research-core, lowrank-rnn): no personal names, home paths or machine facts
    (patterns listed in <repo>/personal_patterns.txt — each contributor adds their own)
  * stale markers: hard-coded model names (Claude Fable/Opus/Sonnet N), "TODO", dates older than --stale_days
  * scripts/*.py compile
Checks per project (--projects): skills that are real copies instead of symlinks into the repo
(drift risk), copies that differ from the repo version, dangling symlinks.

Usage:
    python lint_skills.py                                  # repo only
    python lint_skills.py --projects ~/project_a ~/project_b
    python lint_skills.py --demo
"""
import argparse
import datetime as dt
import os
import py_compile
import re
import sys

REPO = os.path.expanduser("~/claude-skills")
SHAREABLE = {"research-core", "lowrank-rnn"}          # must stay colleague-safe
PATTERNS_FILE = "personal_patterns.txt"     # repo root: one regex per line (names, home paths, machine facts)
MODEL_NAME = re.compile(r"Claude (Fable|Opus|Sonnet|Haiku) \d")
DATE = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")
NAME_OK = re.compile(r"^[a-z0-9-]{1,64}$")


def frontmatter(text):
    if not text.startswith("---"):
        return {}, text
    end = text.index("\n---", 3)
    fm = {}
    for line in text[3:end].strip().splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1); fm[k.strip()] = v.strip()
    return fm, text[end + 4:]


def load_personal(repo):
    p = os.path.join(repo, PATTERNS_FILE)
    pats = [l.strip() for l in open(p)] if os.path.exists(p) else []
    pats = [l for l in pats if l and not l.startswith("#")]
    return re.compile("|".join(pats)) if pats else None


def lint_skill(plugin, skill_dir, stale_days, personal):
    issues = []
    name = os.path.basename(skill_dir)
    path = os.path.join(skill_dir, "SKILL.md")
    if not os.path.exists(path):
        return [("error", "no SKILL.md")]
    text = open(path).read()
    fm, body = frontmatter(text)

    n = fm.get("name", "")
    if n != name: issues.append(("error", f"name '{n}' ≠ directory '{name}'"))
    if not NAME_OK.match(n): issues.append(("error", "name must be ≤64 chars of [a-z0-9-]"))
    if re.search("claude|anthropic", n): issues.append(("error", "name must not contain claude/anthropic"))
    d = fm.get("description", "")
    if not d: issues.append(("error", "missing description"))
    elif len(d) > 1024: issues.append(("error", f"description {len(d)} chars > 1024"))
    elif not re.search(r"\b(Use (when|whenever|for|BEFORE|before)|use when)\b", d):
        issues.append(("warn", "description does not say when to use the skill ('Use when …')"))

    n_lines = body.count("\n")
    if n_lines > 500: issues.append(("warn", f"body {n_lines} lines > 500 — move detail to references/"))

    # links and referenced bundled files
    for ref in set(re.findall(r"\(((?:references|scripts)/[^)\s#]+)\)|`((?:references|scripts)/[^`\s]+)`", body)):
        ref = ref[0] or ref[1]
        if any(c in ref for c in "*<{"):
            continue                                    # a pattern, not a file
        if not os.path.exists(os.path.join(skill_dir, ref)):
            issues.append(("error", f"referenced file missing: {ref}"))
    for sub in ("references",):
        sd = os.path.join(skill_dir, sub)
        if os.path.isdir(sd):
            for f in os.listdir(sd):
                fp = os.path.join(sd, f)
                if os.path.isdir(fp):
                    issues.append(("warn", f"{sub}/{f}/ nested — keep references one level deep"))
                elif f.endswith(".md"):
                    t = open(fp).read()
                    if t.count("\n") > 100 and not re.search(r"(?i)^#+ *(contents|toc)", t, re.M):
                        issues.append(("warn", f"{sub}/{f} >100 lines without a contents list"))

    # every text file of the skill
    files = [path] + [os.path.join(r, f) for r, _, fs in os.walk(skill_dir) for f in fs
                      if f.endswith((".md", ".py", ".yaml", ".mplstyle")) and os.path.join(r, f) != path]
    today = dt.date.today()
    for fp in files:
        rel = os.path.relpath(fp, skill_dir)
        t = open(fp).read()
        if plugin in SHAREABLE and personal is not None:
            for m in sorted(set(personal.findall(t))):
                issues.append(("warn", f"{rel}: personal/machine fact '{m}' in a shareable plugin"))
        for m in sorted(set(MODEL_NAME.findall(t))):
            issues.append(("warn", f"{rel}: hard-coded model name 'Claude {m} …' (goes stale)"))
        old = [m for m in DATE.findall(t) if (today - dt.date(*map(int, m))).days > stale_days]
        if old:
            issues.append(("info", f"{rel}: {len(old)} date(s) older than {stale_days} d — re-verify the facts they date"))
        if fp.endswith(".py"):
            try:
                py_compile.compile(fp, doraise=True)
            except py_compile.PyCompileError as e:
                issues.append(("error", f"{rel}: does not compile: {e.msg.splitlines()[0]}"))
    return issues


def lint_projects(projects, repo_skills):
    issues = []
    for proj in projects:
        sd = os.path.join(os.path.expanduser(proj), ".claude", "skills")
        if not os.path.isdir(sd):
            continue
        for s in sorted(os.listdir(sd)):
            p = os.path.join(sd, s)
            if os.path.islink(p):
                if not os.path.exists(p):
                    issues.append(("error", f"{proj}: {s} is a dangling symlink"))
            elif s in repo_skills:
                same = open(os.path.join(p, "SKILL.md")).read() == open(os.path.join(repo_skills[s], "SKILL.md")).read()
                issues.append(("warn", f"{proj}: {s} is a COPY of the repo skill"
                               + ("" if same else " and has DRIFTED") + " — replace with a symlink"))
            else:
                issues.append(("info", f"{proj}: {s} is project-only (fine if it is truly project-specific)"))
    return issues


def _demo():
    """Lint a throwaway repo: a good skill passes, a broken one errors, a leaky one warns."""
    import tempfile
    good = "---\nname: good-skill\ndescription: Does X. Use when the user asks for X.\n---\n# Good\n"
    bad = "---\nname: wrong-name\n---\n# Bad\n"
    leaky = "---\nname: leaky\ndescription: Does Y. Use when Y.\n---\nAsk Alice, see /home/alice.\n"
    with tempfile.TemporaryDirectory() as d:
        for name, text in (("good-skill", good), ("bad", bad), ("leaky", leaky)):
            os.makedirs(os.path.join(d, "plugins", "research-core", "skills", name))
            open(os.path.join(d, "plugins", "research-core", "skills", name, "SKILL.md"), "w").write(text)
        open(os.path.join(d, PATTERNS_FILE), "w").write("\\bAlice\\b\n/home/alice\n")
        personal = load_personal(d)
        sk = os.path.join(d, "plugins", "research-core", "skills")
        res = {n: lint_skill("research-core", os.path.join(sk, n), 90, personal) for n in ("good-skill", "bad", "leaky")}
    checks = [("a valid skill passes", not [k for k, _ in res["good-skill"] if k in ("error", "warn")]),
              ("a name mismatch and missing description are errors", sum(k == "error" for k, _ in res["bad"]) >= 2),
              ("personal facts in a shared plugin are flagged", any("personal" in m for _, m in res["leaky"]))]
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--projects", nargs="*", default=[], help="project roots to check for copied/drifted skills")
    ap.add_argument("--stale_days", type=int, default=90)
    ap.add_argument("--demo", action="store_true", help="run the built-in self-test")
    args = ap.parse_args()
    if args.demo:
        sys.exit(_demo())

    repo_skills, n_err, n_warn = {}, 0, 0
    personal = load_personal(args.repo)
    pdir = os.path.join(args.repo, "plugins")
    for plugin in sorted(os.listdir(pdir)):
        sdir = os.path.join(pdir, plugin, "skills")
        if not os.path.isdir(sdir):
            continue
        for s in sorted(os.listdir(sdir)):
            repo_skills[s] = os.path.join(sdir, s)
            issues = lint_skill(plugin, repo_skills[s], args.stale_days, personal)
            flag = "✓" if not any(k in ("error", "warn") for k, _ in issues) else ""
            print(f"{plugin}/{s} {flag}")
            for k, m in issues:
                print(f"    [{k}] {m}")
            n_err += sum(k == "error" for k, _ in issues); n_warn += sum(k == "warn" for k, _ in issues)

    if args.projects:
        print("projects:")
        for k, m in lint_projects(args.projects, repo_skills):
            print(f"    [{k}] {m}")
            n_err += k == "error"; n_warn += k == "warn"
    print(f"SUMMARY: {len(repo_skills)} skills, {n_err} error(s), {n_warn} warning(s)")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
