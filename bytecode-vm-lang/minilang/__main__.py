"""Entry point for ``python -m minilang``."""
import sys
from .cli import main

sys.exit(main())