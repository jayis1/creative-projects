#!/usr/bin/env python3
"""Verify the legacy kenken.py shim works."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import kenken
print("Shim import OK")
c = kenken.Cage([(0, 0)], "=", 3)
print(f"Cage created: {c}")
gen = kenken.KenKenGenerator(size=3, seed=1)
puzzle = gen.generate()
solver = kenken.KenKenSolver(puzzle)
grid = solver.solve_grid()
print(f"Solved 3x3: {grid}")
print("All shim functionality OK!")