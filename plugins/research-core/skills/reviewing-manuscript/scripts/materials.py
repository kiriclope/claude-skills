"""Assemble the materials list a mock referee review works from, and flag what is missing or stale.

Reads `.claude/project.yaml` (paper_dir, review_texts, figures_root, review_figures, figure_code, numbers_script,
numbers_log, style_guide) unless paths are given, finds the manuscript files, extracts every figure the text
references — Markdown ![..](path), LaTeX \\includegraphics{path}, HTML <img src>, {{FIG:name}}
placeholders — and resolves each to a file. Flags:
  missing   a referenced figure with no file
  stale     a figure file older than the newest script in figure_code (it may not show the current analysis)
  absent    a numbers log, style guide or figure script named in project.yaml that does not exist
  notes     a file in paper_dir that looks like author notes (README, notes, style guide, todo), when project.yaml
            has no review_texts (globs of the reader-facing text): a reviewer must never see it
It also prints the PRE-CHECKS to run before the lenses (numbers vs the numbers log, the claims ledger, the
references), with their paths filled in; their outputs go to the reviewers with the materials.

The printed list is what every reviewer receives — the evidence, never the authors' reasoning. --style sets what
each kind of reviewer sees, as at a journal:
  editor    the main text, the main figures and the cover letter; supplementary material listed as skimmed only
  referee   the submission package: main text, supplementary text and figures, references; no cover letter, no
            figure code, numbers log or pre-checks (--share-code adds the figure code, for journals that send it)
  internal  everything, with the pre-checks (default)
Supplementary = a path containing supp, extended, appendix, _si / si_ or ED_Fig / edfig; cover letter = a path containing "cover".

Usage:
    python materials.py                          # from the project root (uses .claude/project.yaml)
    python materials.py --paper docs/paper/results_draft.md --figures 'figures/**/png/*main*.png'
    python materials.py --style referee            # what an external referee receives
    python materials.py --demo
"""
import argparse
import glob
import os
import re
import sys
import tempfile

TEXT_EXT = (".md", ".tex", ".html", ".txt", ".rst")
FIG_EXT = (".png", ".pdf", ".svg", ".jpg", ".jpeg")
REFS = [re.compile(r"!\[[^\]]*\]\(([^)\s]+)"), re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}"),
        re.compile(r"<img[^>]+src=[\"']([^\"']+)"), re.compile(r"\{\{FIG:([\w\-.]+)\}\}")]


def load_cfg(root):
    p = os.path.join(root, ".claude", "project.yaml")
    if not os.path.exists(p):
        return {}
    try:
        import yaml
        return yaml.safe_load(open(p)) or {}
    except ImportError:
        print("note: PyYAML not installed — pass --paper/--figures explicitly", file=sys.stderr)
        return {}


def manuscript_files(paper):
    if paper and os.path.isfile(paper):
        return [paper]
    if paper and os.path.isdir(paper):
        return sorted(f for f in glob.glob(os.path.join(paper, "**", "*"), recursive=True) if f.endswith(TEXT_EXT))
    return []


def resolve(ref, text_file, fig_roots):
    """File for a figure reference, or None."""
    for base in [os.path.dirname(text_file)] + fig_roots:
        p = os.path.normpath(os.path.join(base, ref))
        if os.path.isfile(p):
            return p
    name = os.path.splitext(os.path.basename(ref))[0]                 # {{FIG:name}} or an extension-less ref
    for root in fig_roots:
        hits = [f for f in glob.glob(os.path.join(root, "**", name + ".*"), recursive=True) if f.endswith(FIG_EXT)]
        if hits:
            return sorted(hits, key=os.path.getmtime)[-1]
    return None


def collect(root, paper=None, figures=None):
    """figures: a folder, or glob patterns of rendered figure files (e.g. 'figs/**/png/*main*.png')."""
    cfg = load_cfg(root)
    j = lambda p: None if p is None else (p if os.path.isabs(p) else os.path.join(root, p))
    paper_given = paper is not None
    paper = j(paper or cfg.get("paper_dir"))
    issues_pre = []
    figures = figures or cfg.get("review_figures")                 # project.yaml: globs of the canonical renders
    patterns = [f for f in (figures or []) if any(ch in f for ch in "*?[") or os.path.isfile(j(f))]  # globs and files
    folders = [f for f in (figures or []) if f not in patterns] or [cfg.get("figures_root")]
    fig_roots = [r for r in [j(f) for f in folders] + [j(cfg.get("paper_dir"))] if r and os.path.isdir(r)]
    code = [j(c) for c in (cfg.get("figure_code") or [])]
    rt = cfg.get("review_texts")                                    # globs of the reader-facing text files
    if rt and not paper_given:
        texts = sorted({f for g in rt for f in glob.glob(j(g), recursive=True) if f.endswith(TEXT_EXT + (".bib",))})
    else:
        texts = manuscript_files(paper)
        if not paper_given:
            for t in texts:
                if NOTES.search(os.path.basename(t)):
                    issues_pre.append(("notes", f"{os.path.relpath(t, root)} looks like author notes — set review_texts "
                                                f"in project.yaml to the reader-facing files"))
    figs, issues = [], issues_pre
    newest_code = max([os.path.getmtime(c) for c in code if os.path.exists(c)], default=None)
    for t in texts:
        body = open(t, errors="ignore").read()
        for rx in REFS:
            for ref in rx.findall(body):
                f = resolve(ref, t, fig_roots)
                if f is None:
                    issues.append(("missing", f"{os.path.relpath(t, root)} references '{ref}' — no file found"))
                elif f not in figs:
                    figs.append(f)
                    if newest_code and os.path.getmtime(f) < newest_code:
                        issues.append(("stale", f"{os.path.relpath(f, root)} is older than the newest figure script"))
    for pat in patterns:                                              # figures cited by name, given explicitly
        for f in sorted(glob.glob(j(pat), recursive=True)):
            if f.endswith(FIG_EXT) and f not in figs:
                figs.append(f)
                if newest_code and os.path.getmtime(f) < newest_code:       # given by glob: same stale check
                    issues.append(("stale", f"{os.path.relpath(f, root)} is older than the newest figure script"))
    if texts and not figs:
        issues.append(("unlinked", "the text links no figure files (figures cited by name?) — pass "
                                   "--figures '<glob of the rendered main figures>' so reviewers see them"))
    extras = {k: j(cfg.get(k)) for k in ("numbers_script", "numbers_log", "style_guide") if cfg.get(k)}
    for k, p in list(extras.items()) + [("figure_code", c) for c in code]:
        if p and not os.path.exists(p):
            issues.append(("absent", f"{k}: {os.path.relpath(p, root)} does not exist"))
    return texts, figs, extras, code, issues


NOTES = re.compile(r"readme|notes?\b|notes_|style_guide|todo|scratch", re.I)
SUPP = re.compile(r"supp|extended|appendix|(^|[_/\-])si([_/.\-]|$)|(^|[_/\-])ed_?fig", re.I)
COVER = re.compile(r"cover", re.I)


def for_style(style, texts, figs, extras, code, share_code=False):
    """Cut the materials to what this kind of reviewer sees: (texts, figures, skimmed, extras, code)."""
    if style == "internal":
        return texts, figs, [], extras, code
    supp = lambda f: bool(SUPP.search(f))
    if style == "editor":
        keep = [t for t in texts if not supp(t) and not t.endswith(".bib")]
        return keep, [f for f in figs if not supp(f)], [f for f in texts + figs if supp(f)], {}, []
    keep = [t for t in texts if not COVER.search(os.path.basename(t))]   # referee: no cover letter
    return keep, figs, [], {}, (code if share_code else [])


SKILLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def prechecks(root, texts):
    """The mechanical checks to run before the lenses, as commands (only those whose inputs exist)."""
    cfg = load_cfg(root)
    j = lambda p: p if os.path.isabs(p) else os.path.join(root, p)
    rel = lambda p: os.path.relpath(p, root)
    tx = " ".join(rel(t) for t in texts if not t.endswith(".bib"))
    cmds = []
    if cfg.get("numbers_log") and os.path.exists(j(cfg["numbers_log"])) and tx:
        cmds.append(f"python {SKILLS}/auditing-paper-numbers/scripts/audit_numbers.py --text {tx} --log {cfg['numbers_log']}")
    claims = (cfg.get("validation") or {}).get("claims_file")
    if claims and os.path.exists(j(claims)):
        cmds.append(f"python {SKILLS}/validating-claims/scripts/claims_ledger.py --ledger {claims}")
    paper = cfg.get("paper_dir")
    bibs = sorted(glob.glob(os.path.join(j(paper), "**", "*.bib"), recursive=True)) if paper else []
    cmds += [f"python {SKILLS}/verifying-citations/scripts/verify_refs.py {rel(b)}" for b in bibs]
    return cmds


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".", help="project root (where .claude/project.yaml is)")
    ap.add_argument("--paper", help="manuscript file or folder (default: project.yaml paper_dir)")
    ap.add_argument("--figures", nargs="*", help="folder(s) or glob pattern(s) of rendered figures "
                    "(default: project.yaml figures_root)")
    ap.add_argument("--style", choices=["editor", "referee", "internal"], default="internal",
                    help="what this kind of reviewer sees (default internal: everything)")
    ap.add_argument("--share-code", action="store_true", help="referee: add the figure code (the journal sends it)")
    ap.add_argument("--demo", action="store_true", help="run the built-in self-test")
    a = ap.parse_args(argv)
    if a.demo:
        return _demo()
    root = os.path.abspath(a.root)
    texts, figs, extras, code, issues = collect(root, a.paper, a.figures)
    all_texts = texts
    texts, figs, skimmed, extras, code = for_style(a.style, texts, figs, extras, code, a.share_code)
    rel = lambda p: os.path.relpath(p, root)
    print(f"MATERIALS for the {a.style} review (give these, and only these, to every reviewer of this style)")
    print("manuscript:\n" + ("\n".join(f"  {rel(t)}" for t in texts) or "  (none found — pass --paper)"))
    print("figures referenced:\n" + ("\n".join(f"  {rel(f)}" for f in figs) or "  (none)"))
    for k, p in extras.items():
        print(f"{k}: {rel(p)}")
    if skimmed:
        print("supplementary (an editor skims these only):\n" + "\n".join(f"  {rel(f)}" for f in skimmed))
    if code:
        print("figure code:\n" + "\n".join(f"  {rel(c)}" for c in code))
    for kind, msg in issues:
        print(f"[{kind}] {msg}")
    if a.style != "internal":
        print(f"SUMMARY: {len(texts)} text file(s), {len(figs)} figure(s), {len(issues)} issue(s); no pre-checks "
              f"for the {a.style} review")
        return 0
    cmds = prechecks(root, all_texts)
    print("PRE-CHECKS (run now; give their output with the materials):\n" + ("\n".join(f"  {c}" for c in cmds)
          or "  (none: no numbers_log, validation.claims_file or .bib in project.yaml's paths)"))
    print(f"SUMMARY: {len(texts)} text file(s), {len(figs)} figure(s), {len(issues)} issue(s)")
    return 0


def _demo():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, ".claude")); os.makedirs(os.path.join(d, "paper")); os.makedirs(os.path.join(d, "figs"))
        open(os.path.join(d, ".claude", "project.yaml"), "w").write(
            "paper_dir: paper\nfigures_root: figs\nfigure_code: [make_figs.py]\nnumbers_log: numbers.json\n")
        open(os.path.join(d, "figs", "fig1.png"), "wb").write(b"png")
        open(os.path.join(d, "figs", "fig2.png"), "wb").write(b"png")
        os.utime(os.path.join(d, "figs", "fig2.png"), (1, 1))            # rendered before the script changed
        open(os.path.join(d, "make_figs.py"), "w").write("# draws the figures\n")
        os.utime(os.path.join(d, "make_figs.py"), (1000, 1000))         # explicit times: the test must not
        os.utime(os.path.join(d, "figs", "fig1.png"), (2000, 2000))     # depend on write order or clock resolution
        open(os.path.join(d, "paper", "draft.md"), "w").write(
            "Result one ![](../figs/fig1.png). Result two {{FIG:fig2}}. Result three ![](../figs/fig3.png).\n")
        texts, figs, extras, code, issues = collect(d)
        open(os.path.join(d, "paper", "draft.md"), "w").write("As Fig. 1 shows, ...\n")
        _, figs_none, _, _, iss_none = collect(d)
        _, figs_glob, _, _, iss_glob = collect(d, figures=["figs/*.png"])   # fig2.png is older than the script
        with open(os.path.join(d, ".claude", "project.yaml"), "a") as f:
            f.write("review_figures: ['figs/fig1.png']\n")
        _, figs_cfg, _, _, _ = collect(d)
        open(os.path.join(d, "paper", "methods_notes.md"), "w").write("author notes\n")
        t_notes, _, _, _, iss_notes = collect(d)
        with open(os.path.join(d, ".claude", "project.yaml"), "a") as f:
            f.write("review_texts: ['paper/draft.md']\n")
        t_rt, _, _, _, iss_rt = collect(d)
        os.remove(os.path.join(d, "paper", "methods_notes.md"))
        cmds_none = prechecks(d, texts)
        open(os.path.join(d, "numbers.json"), "w").write("{}")
        open(os.path.join(d, "paper", "refs.bib"), "w").write("")
        cmds = prechecks(d, texts)
        st = (["p/main.md", "p/cover_letter.md", "p/supplementary.md", "p/refs.bib"],
              ["f/fig1.png", "f/extended_data_fig1.png", "f/ED_Fig2.png"], {"numbers_log": "n.json"}, ["make_figs.py"])
        ed, rf, rfc, it = (for_style("editor", *st), for_style("referee", *st), for_style("referee", *st, share_code=True),
                           for_style("internal", *st))
    kinds = [k for k, _ in issues]
    checks = [("manuscript found", len(texts) == 1),
              ("two referenced figures resolved (path and {{FIG:name}})", len(figs) == 2),
              ("missing figure flagged", kinds.count("missing") == 1),
              ("figure older than its script flagged as stale", kinds.count("stale") == 1),
              ("absent numbers log flagged", kinds.count("absent") == 1),
              ("figures cited only by name → flagged as unlinked", any(k == "unlinked" for k, _ in iss_none) and not figs_none),
              ("--figures glob adds the rendered figures", len(figs_glob) == 2 and not any(k == "unlinked" for k, _ in iss_glob)),
              ("a globbed figure older than its script is flagged stale", [k for k, _ in iss_glob].count("stale") == 1),
              ("review_figures in project.yaml is used", [os.path.basename(f) for f in figs_cfg] == ["fig1.png"]),
              ("author notes in paper_dir flagged", any(k == "notes" for k, _ in iss_notes)),
              ("review_texts keeps only the reader-facing text", [os.path.basename(t) for t in t_rt] == ["draft.md"]
               and not any(k == "notes" for k, _ in iss_rt)),
              ("no pre-check without its inputs", cmds_none == []),
              ("numbers audit and reference check once their files exist",
               len(cmds) == 2 and "audit_numbers.py" in cmds[0] and cmds[1].endswith("paper/refs.bib")),
              ("editor: main text, cover letter and main figures; supplementary skimmed; no code or numbers",
               ed[0] == ["p/main.md", "p/cover_letter.md"] and ed[1] == ["f/fig1.png"]
               and ed[2] == ["p/supplementary.md", "f/extended_data_fig1.png", "f/ED_Fig2.png"] and not ed[3] and not ed[4]),
              ("referee: the package without the cover letter; no code unless shared",
               rf[0] == ["p/main.md", "p/supplementary.md", "p/refs.bib"] and len(rf[1]) == 3 and not rf[3]
               and not rf[4] and rfc[4] == ["make_figs.py"]),
              ("internal: everything", it[0] == st[0] and it[3] == st[2] and it[4] == st[3])]
    for name, ok in checks:
        print(f"  {'✓' if ok else '✗'} {name}")
    ok = all(c for _, c in checks)
    print(f"SUMMARY: demo {'OK' if ok else 'FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
