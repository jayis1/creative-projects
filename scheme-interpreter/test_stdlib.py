from scheme_interpreter.interpreter import Interpreter
from scheme_interpreter.primitives import set_global_interpreter

interp = Interpreter()
set_global_interpreter(interp)

# Check if cons-stream is defined
try:
    val = interp.global_env.lookup("cons-stream")
    print(f"cons-stream is: {val}")
except NameError:
    print("cons-stream is NOT defined")

# Check if map is defined from stdlib
try:
    val = interp.global_env.lookup("square")
    print(f"square is: {val}")
except NameError:
    print("square is NOT defined")