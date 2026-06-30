#!/usr/bin/env python3
"""Backward-compatibility CLI shim — delegates to reed_solomon.cli.

For the full CLI with config support, logging, and all subcommands, use:
    python3 -m reed_solomon.cli <command> [options]
or install the package and use the ``rsc`` entry point.
"""
import sys
from reed_solomon.cli import main

if __name__ == "__main__":
    sys.exit(main())