"""Entry point for ``python -m gc_sim``."""
from .cli import main

if __name__ == "__main__":
    import sys
    sys.exit(main())