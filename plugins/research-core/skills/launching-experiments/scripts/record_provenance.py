"""Write provenance.json into a run directory: everything needed to know what produced a result.

Records: git commit, branch, dirty flag + `git diff --stat` (and the full diff to
provenance.diff when dirty), argv, timestamp, host, user-visible GPU(s), Python / torch / numpy
versions, optional config dict and seed.

Importable (call at the start of each run, before training):
    sys.path.insert(0, "<skill_dir>/scripts")
    from record_provenance import record_provenance
    record_provenance(run_dir, config=asdict(cfg), seed=cfg.seed)

CLI:
    python record_provenance.py --run_dir results/my_sweep/s0_arm --repo .
    python record_provenance.py --demo
"""
import argparse
import datetime as dt
import json
import os
import platform
import re
import socket
import subprocess
import sys
import tempfile


def _git(repo, *args):
    try:
        return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return ""


def _commit(repo):
    h = _git(repo, "rev-parse", "--verify", "-q", "HEAD")
    return h if re.fullmatch(r"[0-9a-f]{40}", h) else None      # None: not a repo or no commits yet


def _versions():
    out = {"python": platform.python_version()}
    for mod in ("torch", "numpy", "scipy", "jax"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception:
            pass
    return out


def _gpus():
    try:
        import torch
        if torch.cuda.is_available():
            return [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
    except Exception:
        pass
    return []


def record_provenance(run_dir, repo=".", config=None, seed=None, extra=None):
    """Write <run_dir>/provenance.json (+ provenance.diff when the tree is dirty). Returns the dict."""
    os.makedirs(run_dir, exist_ok=True)
    repo = os.path.abspath(repo)
    status = _git(repo, "status", "--porcelain", "--untracked-files=no")
    prov = {
        "timestamp": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "argv": sys.argv,
        "cwd": os.getcwd(),
        "git": {
            "repo": repo,
            "commit": _commit(repo),
            "branch": _git(repo, "rev-parse", "--abbrev-ref", "HEAD") or None,
            "dirty": bool(status),
            "diff_stat": _git(repo, "diff", "--stat", "HEAD") if status else "",
        },
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "gpus": _gpus(),
        "versions": _versions(),
        "seed": seed,
        "config": config,
    }
    if extra:
        prov.update(extra)
    if status:
        with open(os.path.join(run_dir, "provenance.diff"), "w") as f:
            f.write(_git(repo, "diff", "HEAD"))
    with open(os.path.join(run_dir, "provenance.json"), "w") as f:
        json.dump(prov, f, indent=2, default=str)
    return prov


def _demo():
    with tempfile.TemporaryDirectory() as d:
        p = record_provenance(d, repo=os.path.dirname(os.path.abspath(__file__)),
                              config={"lr": 0.01, "n_epochs": 10}, seed=0)
        back = json.load(open(os.path.join(d, "provenance.json")))
        assert back["seed"] == 0 and back["config"]["lr"] == 0.01 and "python" in back["versions"]
        print(f"commit {p['git']['commit']}  dirty={p['git']['dirty']}  host={p['host']}  "
              f"gpus={p['gpus'] or 'none'}  versions={p['versions']}")
        print("SUMMARY: demo OK — provenance.json written and read back")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run_dir", help="run directory to write provenance.json into")
    ap.add_argument("--repo", default=".", help="git repository of the code that runs")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--demo", action="store_true", help="write and read back a provenance file in a temp dir")
    args = ap.parse_args()
    if args.demo:
        _demo()
    elif args.run_dir:
        p = record_provenance(args.run_dir, repo=args.repo, seed=args.seed)
        print(f"wrote {os.path.join(args.run_dir, 'provenance.json')}  commit {p['git']['commit']}  dirty={p['git']['dirty']}")
    else:
        ap.print_help()
