#!/usr/bin/env python3
"""Quick test of examples."""
import io, sys
sys.path.insert(0, '.')
from basic import Interpreter

interp = Interpreter(stdout=io.StringIO())
interp.load(open('examples/hello.bas').read())
interp.run()
print('hello:', repr(interp.stdout.getvalue()))

interp2 = Interpreter(stdout=io.StringIO())
interp2.load(open('examples/fibonacci.bas').read())
interp2.run()
print('fib:', repr(interp2.stdout.getvalue()))