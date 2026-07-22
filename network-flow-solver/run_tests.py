#!/usr/bin/env python3
"""Run tests for network-flow-solver."""
import sys, os, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
loader = unittest.TestLoader()
suite = loader.discover(os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests"), pattern="test_*.py")
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)
sys.exit(0 if result.wasSuccessful() else 1)