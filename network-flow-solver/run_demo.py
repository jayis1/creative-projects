#!/usr/bin/env python3
"""Quick test runner for network-flow-solver."""
import sys
sys.path.insert(0, ".")
sys.argv = ["networkflow", "demo"]
from networkflow.cli import main
sys.exit(main())