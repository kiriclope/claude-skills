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
  * every --flag the SKILL.md passes to one of its own scripts/*.py is defined in that script's argparse
Checks per agent (plugins/*/agents/*.md): name = file name, description, tools, a model alias
(haiku/sonnet/opus/fable/inherit or a full claude-* id), personal facts in a shareable plugin; an agent
redefined in another plugin (a personal override) may differ only in model/effort.
Checks the marketplace: personal facts in its metadata and plugin descriptions; every plugin dir listed.
Checks per project (--projects): skills that are real copies instead of symlinks into the repo
(drift risk), copies that differ from the repo version, dangling symlinks; template keys missing from
the project's .claude/project.yaml (info); verdict_scripts that do not exist in the project.

Usage:
    python lint_skills.py                                  # repo only (default: the repo this script lives in)
    python lint_skills.py --projects ~/project_a ~/project_b
    python lint_skills.py --demo
"""
import argparse
import datetime as dt
import json
import os
import py_compile
import re
import sys


def _find_repo():
    """The repo this script lives in (has .claude-plugin/marketplace.json); else ~/claude-skills."""
    d = os.path.dirname(os.path.abspath(__file__))
    while d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, ".claude-plugin", "marketplace.json")):
            return d
        d = os.path.dirname(d)
    return os.path.expanduser("~/claude-skills")


REPO = _find_repo()
MODEL_ALIASES = {"haiku", "sonnet", "opus", "fable", "inherit"}
ARG_FLAG = re.compile(r"add_argument\(\s*[\"'](--[\w-]+)[\"']")
CMD_FLAG = re.compile(r"(?<![\w-])(--[a-z][\w-]*)")
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
    issues += check_script_flags(skill_dir, text)
    return issues


def script_flags(py_path):
    """--flags a script defines with argparse (read from source: no import, so no torch needed)."""
    return set(ARG_FLAG.findall(open(py_path).read())) | {"--help"}


def check_script_flags(skill_dir, text):
    """Every --flag written on a command line that runs one of this skill's scripts must exist there."""
    sd = os.path.join(skill_dir, "scripts")
    if not os.path.isdir(sd):
        return []
    known = {f: script_flags(os.path.join(sd, f)) for f in os.listdir(sd) if f.endswith(".py")}
    issues, lines = [], text.splitlines()
    for i, line in enumerate(lines):
        cmd = line
        while cmd.rstrip().endswith("\\") and i + 1 < len(lines):      # shell continuation lines
            i += 1; cmd = cmd.rstrip()[:-1] + " " + lines[i]
        for script in re.findall(r"([\w-]+\.py)\b", cmd):
            if script not in known or len(known[script]) == 1:      # not ours, or no argparse
                continue
            tail = cmd.split(script, 1)[1].split("#", 1)[0]         # flags after the script name, not comments
            for f in sorted(set(CMD_FLAG.findall(tail)) - known[script]):
                issues.append(("warn", f"SKILL.md passes {f} to scripts/{script}, which does not define it"))
    return sorted(set(issues))


def lint_agent(plugin, path, personal):
    issues = []
    fm, _ = frontmatter(open(path).read())
    stem = os.path.splitext(os.path.basename(path))[0]
    if fm.get("name") != stem: issues.append(("error", f"name '{fm.get('name', '')}' ≠ file name '{stem}'"))
    if not fm.get("description"): issues.append(("error", "missing description"))
    if not fm.get("tools"): issues.append(("warn", "no tools list — the agent inherits every tool"))
    m = fm.get("model", "")
    if m and m not in MODEL_ALIASES and not m.startswith("claude-"):
        issues.append(("error", f"model '{m}' is neither an alias ({'/'.join(sorted(MODEL_ALIASES))}) nor a claude-* id"))
    if plugin in SHAREABLE and personal is not None:
        for hit in sorted(set(personal.findall(open(path).read()))):
            issues.append(("warn", f"personal/machine fact '{hit}' in a shareable plugin"))
    return issues


def _agent_core(path):
    """An agent file without its model/effort lines: what an override must keep identical."""
    return [l for l in open(path).read().splitlines() if not re.match(r"(model|effort):", l)]


def lint_overrides(paths_by_name):
    """An agent defined in two plugins (a personal override of a shared agent, e.g. another model)
    must differ only in model/effort; anything else is drift from the shared version."""
    issues = []
    for name, paths in sorted(paths_by_name.items()):
        real = sorted({os.path.realpath(p) for p in paths})
        for other in real[1:]:
            if _agent_core(real[0]) != _agent_core(other):
                issues.append(("warn", f"agent '{name}': {os.path.relpath(other)} differs from "
                               f"{os.path.relpath(real[0])} beyond model/effort — re-copy the override"))
    return issues


def lint_marketplace(repo, personal):
    p = os.path.join(repo, ".claude-plugin", "marketplace.json")
    if not os.path.exists(p):
        return [("error", "no .claude-plugin/marketplace.json")]
    mk, issues = json.load(open(p)), []
    texts = [json.dumps(mk.get("metadata", {}))] + [pl.get("description", "") for pl in mk.get("plugins", [])
                                                     if pl.get("name") in SHAREABLE]
    if personal is not None:                                    # the owner field may name the owner
        for hit in sorted({h for t in texts for h in personal.findall(t)}):
            issues.append(("warn", f"personal/machine fact '{hit}' in marketplace metadata or a shareable plugin's description"))
    listed = {pl.get("name") for pl in mk.get("plugins", [])}
    for d in sorted(os.listdir(os.path.join(repo, "plugins"))):
        if d not in listed:
            issues.append(("info", f"plugins/{d} is not listed in marketplace.json (fine only if it is install-by-hand)"))
    return issues


def top_keys(yaml_path):
    return set(re.findall(r"^([A-Za-z_][\w-]*):", open(yaml_path).read(), re.M))


def lint_project_config(proj, repo):
    """Template keys the project lacks (info) and verdict_scripts missing from the project (warn)."""
    proj = os.path.expanduser(proj)
    py, tpl = os.path.join(proj, ".claude", "project.yaml"), os.path.join(repo, "templates", "project.yaml")
    if not os.path.exists(py):
        return [("warn", f"{proj}: no .claude/project.yaml — copy templates/project.yaml and fill it in")]
    issues = []
    if os.path.exists(tpl):
        missing = sorted(top_keys(tpl) - top_keys(py))
        if missing:
            issues.append(("info", f"{proj}: project.yaml lacks template keys (skills fall back to defaults): {', '.join(missing)}"))
    m = re.search(r"^verdict_scripts:\s*\[([^\]]*)\]", open(py).read(), re.M)
    for s in [x.strip().strip("'\"") for x in m.group(1).split(",")] if m else []:
        if s and not os.path.exists(os.path.join(proj, s)):
            issues.append(("warn", f"{proj}: verdict_scripts names {s}, which is not in the project"))
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
        # a skill whose SKILL.md passes a flag its script does not define
        fl = os.path.join(sk, "flags"); os.makedirs(os.path.join(fl, "scripts"))
        open(os.path.join(fl, "scripts", "tool.py"), "w").write("import argparse\nap=argparse.ArgumentParser()\nap.add_argument('--n')\n")
        open(os.path.join(fl, "SKILL.md"), "w").write("---\nname: flags\ndescription: Z. Use when Z.\n---\n"
                                                       "python scripts/tool.py --n 3 \\\n    --gone 1   # --comment\n")
        res["flags"] = lint_skill("research-core", fl, 90, personal)
        ag = os.path.join(d, "agent.md")
        open(ag, "w").write("---\nname: other\ndescription: A.\nmodel: gpt-4\n---\nbody\n")
        res["agent"] = lint_agent("research-core", ag, personal)
        base = "---\nname: a\ndescription: A.\nmodel: opus\n---\nbody\n"
        for f, t in (("o_ok.md", base.replace("opus", "fable")), ("o_bad.md", base + "extra\n"), ("o_base.md", base)):
            open(os.path.join(d, f), "w").write(t)
        res["ov_ok"] = lint_overrides({"a": [os.path.join(d, "o_base.md"), os.path.join(d, "o_ok.md")]})
        res["ov_bad"] = lint_overrides({"a": [os.path.join(d, "o_base.md"), os.path.join(d, "o_bad.md")]})
    flag_msgs = [m for _, m in res["flags"]]
    checks = [("a valid skill passes", not [k for k, _ in res["good-skill"] if k in ("error", "warn")]),
              ("a name mismatch and missing description are errors", sum(k == "error" for k, _ in res["bad"]) >= 2),
              ("personal facts in a shared plugin are flagged", any("personal" in m for _, m in res["leaky"])),
              ("an undefined script flag is flagged (continuation line), a defined one and a comment are not",
               any("--gone" in m for m in flag_msgs) and not any("--n " in m or "--comment" in m for m in flag_msgs)),
              ("an agent with a wrong name and unknown model is an error", sum(k == "error" for k, _ in res["agent"]) == 2),
              ("an override differing only in model passes; one with a changed body warns",
               not res["ov_ok"] and len(res["ov_bad"]) == 1)]
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

    n_agents, by_name = 0, {}
    for plugin in sorted(os.listdir(pdir)):
        adir = os.path.join(pdir, plugin, "agents")
        for a in sorted(os.listdir(adir)) if os.path.isdir(adir) else []:
            if not a.endswith(".md"):
                continue
            by_name.setdefault(a[:-3], []).append(os.path.join(adir, a))
            if os.path.islink(os.path.join(adir, a)):
                continue                                # a link to a shared agent, linted there
            n_agents += 1
            issues = lint_agent(plugin, os.path.join(adir, a), personal)
            print(f"{plugin}/agents/{a} {'' if any(k in ('error', 'warn') for k, _ in issues) else '✓'}")
            for k, m in issues:
                print(f"    [{k}] {m}")
            n_err += sum(k == "error" for k, _ in issues); n_warn += sum(k == "warn" for k, _ in issues)

    for k, m in lint_overrides(by_name):
        print(f"    [{k}] {m}")
        n_warn += k == "warn"

    print("marketplace:")
    for k, m in lint_marketplace(args.repo, personal):
        print(f"    [{k}] {m}")
        n_err += k == "error"; n_warn += k == "warn"

    if args.projects:
        print("projects:")
        proj_issues = lint_projects(args.projects, repo_skills)
        for p in args.projects:
            proj_issues += lint_project_config(p, args.repo)
        for k, m in proj_issues:
            print(f"    [{k}] {m}")
            n_err += k == "error"; n_warn += k == "warn"
    print(f"SUMMARY: {len(repo_skills)} skills, {n_agents} agents, {n_err} error(s), {n_warn} warning(s)")
    sys.exit(1 if n_err else 0)


if __name__ == "__main__":
    main()
