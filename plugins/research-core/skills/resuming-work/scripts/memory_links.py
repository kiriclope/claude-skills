"""Make Claude Code memory notes browsable as an Obsidian vault: aliases for [[links]], and a link report.

Claude Code writes links as [[name]] (the note's `name:` slug, e.g. [[user-colorblind]]) while the file is
user_colorblind.md; Obsidian resolves [[…]] by file name or by `aliases:`. This adds one `aliases:` line to
each note's front matter — the name slug and the kebab-case file name (with and without its type prefix) —
by inserting text, never re-serializing the YAML, so the rest of the header is untouched. Idempotent.

Usage:
    python memory_links.py                              # report: links, resolving, dangling (all memory folders)
    python memory_links.py --add-aliases                # write the aliases, then report
    python memory_links.py --root ~/.claude/projects --add-aliases --quiet   # what the vault's pre-commit hook runs
    python memory_links.py --demo
"""
import argparse
import glob
import os
import re
import sys
import tempfile

PREFIXES = ("feedback_", "project_", "reference_", "user_")
LINK = re.compile(r"\[\[([^\]|#\n]+)")


def wanted_aliases(path, text):
    stem = os.path.basename(path)[:-3]
    out = []
    m = re.search(r"^name:\s*[\"']?([^\"'\n]+)", text, re.M)
    if m:
        out.append(m.group(1).strip())
    out.append(stem.replace("_", "-"))
    for p in PREFIXES:
        if stem.startswith(p):
            out.append(stem[len(p):].replace("_", "-"))
    return [a for i, a in enumerate(out) if a and a not in out[:i] and a != stem]


def add_aliases(path):
    """Insert or refresh the `aliases:` line in the front matter. Returns True when the file changed."""
    text = open(path, encoding="utf-8").read()
    if not text.startswith("---\n") or "\n---" not in text[4:]:
        return False
    end = text.index("\n---", 4)
    head, body = text[4:end], text[end:]
    aliases = wanted_aliases(path, text)
    if not aliases:
        return False
    line = "aliases: [" + ", ".join(f'"{a}"' for a in aliases) + "]"
    if re.search(r"^aliases:.*$", head, re.M):
        new_head = re.sub(r"^aliases:.*$", line, head, count=1, flags=re.M)
    else:
        lines = head.split("\n")
        i = next((k + 1 for k, l in enumerate(lines) if l.startswith("name:")), 0)
        new_head = "\n".join(lines[:i] + [line] + lines[i:])
    if new_head == head:
        return False
    open(path, "w", encoding="utf-8").write("---\n" + new_head + body)
    return True


def report(notes):
    stems, aliases = set(), set()
    for p in notes:
        stems.add(os.path.basename(p)[:-3])
        aliases.update(wanted_aliases(p, open(p, encoding="utf-8", errors="ignore").read()))
    links, dangling = 0, {}
    for p in notes:
        for target in LINK.findall(open(p, encoding="utf-8", errors="ignore").read()):
            t = target.strip()
            if not re.search(r"[A-Za-z]", t):                 # e.g. [[1,-1.5]] — not a link
                continue
            links += 1
            if t not in stems and t not in aliases:
                dangling.setdefault(t, os.path.relpath(p))
    return links, dangling


def notes_under(root):
    return sorted(glob.glob(os.path.join(os.path.expanduser(root), "*", "memory", "*.md")))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default="~/.claude/projects", help="folder holding the <project>/memory folders")
    ap.add_argument("--add-aliases", action="store_true", help="write the aliases line into every note")
    ap.add_argument("--quiet", action="store_true", help="print only the summary line")
    ap.add_argument("--demo", action="store_true", help="self-test in a temp folder")
    a = ap.parse_args(argv)
    if a.demo:
        return _demo()
    notes = [p for p in notes_under(a.root) if os.path.basename(p) != "MEMORY.md"]
    changed = sum(add_aliases(p) for p in notes) if a.add_aliases else 0
    links, dangling = report(notes)
    if not a.quiet:
        for t, where in sorted(dangling.items()):
            print(f"  dangling [[{t}]]  (first in {where})")
    print(f"SUMMARY: {len(notes)} notes, {changed} updated, {links} links, {len(dangling)} distinct dangling targets")
    return 0


def _demo():
    with tempfile.TemporaryDirectory() as d:
        m = os.path.join(d, "-home-x-proj", "memory"); os.makedirs(m)
        open(os.path.join(m, "user_colorblind.md"), "w").write(
            '---\nname: user-colorblind\ndescription: "x"\nmetadata:\n  type: user\n---\n\nSee [[feedback-plots]].\n')
        open(os.path.join(m, "feedback_plots.md"), "w").write(
            "---\nname: plots-rule\ndescription: y\n---\n\nSee [[user-colorblind]] and [[nowhere]].\n")
        before = report(notes_under(d))
        changed = sum(add_aliases(p) for p in notes_under(d))
        again = sum(add_aliases(p) for p in notes_under(d))
        links, dangling = report(notes_under(d))
        head = open(os.path.join(m, "user_colorblind.md")).read().split("\n---")[0]
    checks = [("aliases written once, then idempotent", changed == 2 and again == 0),
              ("slug and kebab file name become aliases", '"user-colorblind"' in head),
              ("rest of the header untouched", 'description: "x"' in head and "  type: user" in head),
              ("only the truly missing note dangles", list(dangling) == ["nowhere"] and links == 3)]
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
