import sys
from . import _demo, __doc__
if "--demo" in sys.argv:
    _demo(sys.argv[sys.argv.index("--demo") + 1])
else:
    print(__doc__)
