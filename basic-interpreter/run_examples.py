#!/usr/bin/env python3
"""Run example programs."""
import sys, io
sys.path.insert(0, '/root/projects/creative-projects/basic-interpreter')
from basic import Interpreter

def run_example(path):
    with open(path) as f:
        source = f.read()
    interp = Interpreter(stdout=sys.stdout)
    interp.load(source)
    interp.run()
    print()

for p in sys.argv[1:]:
    print(f"=== {p} ===")
    run_example(p)
    print()