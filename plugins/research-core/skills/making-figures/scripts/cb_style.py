"""Shim: the colorblind-safe standard lives in the `cbstyle` package (~/claude-skills/python).

Install once per environment:   pip install -e ~/claude-skills/python
Then in project code:           from cbstyle import OKABE_ITO, PAIR, FP, plot_fixed_points, plot_manifold
Demo:                           python cb_style.py --demo out.png
"""
import os
import sys

try:
    from cbstyle import *            # noqa: F401,F403
    from cbstyle import _demo, __doc__ as _pkg_doc
except ImportError:                  # not installed: use the copy in the repo
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "..", "python"))
    from cbstyle import *            # noqa: F401,F403
    from cbstyle import _demo, __doc__ as _pkg_doc

if __name__ == "__main__":
    if "--demo" in sys.argv:
        _demo(sys.argv[sys.argv.index("--demo") + 1] if len(sys.argv) > sys.argv.index("--demo") + 1 else None)
    else:
        print(_pkg_doc)
