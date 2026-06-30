"""Allow running as ``python3 -m reed_solomon``."""
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())