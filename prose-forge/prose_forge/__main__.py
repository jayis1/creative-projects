"""Allow running as `python -m prose_forge`."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())