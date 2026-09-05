"""PyInstaller entry point.

Kept separate from `scribedrop/__main__.py` because PyInstaller needs a
plain top-level script, not a package module.
"""

import sys

from scribedrop.app import main

if __name__ == "__main__":
    sys.exit(main())
