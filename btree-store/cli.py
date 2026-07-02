#!/usr/bin/env python3
"""
Backward-compatibility shim for the original cli.py module.

Re-exports the CLI from btreestore_cli.py so existing usage
(`python cli.py --db FILE ...`) continues to work.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from btreestore_cli import main

if __name__ == "__main__":
    main()