#!/usr/bin/env python3
"""Example: Using the typeinfer Python API.

This script demonstrates the key features of the typeinfer library:
  - Basic type inference
  - Let-polymorphism
  - Type annotations
  - Pattern matching
  - Data declarations
  - Inference trace
"""

from typeinfer import (
    infer, infer_with_trace, type_to_string, scheme_to_string,
    INT, BOOL, STRING, TCon, TFun,
)


def main() -> None:
    print("=" * 60)
    print("typeinfer API Examples")
    print("=" * 60)

    # 1. Identity function
    print("\n1. Identity function: \\x. x")
    t = infer(r"\x. x")
    print(f"   Type: {type_to_string(t)}")
    # Expected: a -> a

    # 2. Let-polymorphism
    print("\n2. Let-polymorphism:")
    print("   let id = \\x. x in (id 1, id true)")
    t = infer(r"let id = \x. x in (id 1, id true)")
    print(f"   Type: {type_to_string(t)}")
    # Expected: Tuple<Int, Bool>

    # 3. With built-in primitives
    print("\n3. Arithmetic with builtins:")
    print("   \\x. x + 1")
    t = infer(r"\x. x + 1", use_builtins=True)
    print(f"   Type: {type_to_string(t)}")
    # Expected: Int -> Int

    # 4. Type annotations
    print("\n4. Type annotations:")
    print(r"   \x: Int -> Int. x 5")
    t = infer(r"\x: Int -> Int. x 5", use_builtins=True)
    print(f"   Type: {type_to_string(t)}")
    # Expected: (Int -> Int) -> Int

    # 5. Pattern matching
    print("\n5. Pattern matching:")
    print("   match Just 5 with | Nothing -> 0 | Just n -> n")
    t = infer(
        r"match Just 5 with | Nothing -> 0 | Just n -> n",
        use_builtins=True,
    )
    print(f"   Type: {type_to_string(t)}")
    # Expected: Int

    # 6. Data declarations
    print("\n6. Data type declarations:")
    print("   data Tree = Leaf | Node Tree Tree in Node Leaf Leaf")
    t = infer(
        "data Tree = Leaf | Node Tree Tree in Node Leaf Leaf",
        use_builtins=True,
    )
    print(f"   Type: {type_to_string(t)}")
    # Expected: Tree

    # 7. List literals
    print("\n7. List literals:")
    print("   [1, 2, 3]")
    t = infer("[1, 2, 3]", use_builtins=True)
    print(f"   Type: {type_to_string(t)}")
    # Expected: List<Int>

    # 8. String literals
    print("\n8. String literals:")
    print('   "hello"')
    t = infer('"hello"', use_builtins=True)
    print(f"   Type: {type_to_string(t)}")
    # Expected: String

    # 9. Higher-order map function
    print("\n9. Higher-order map function:")
    print("   let map = \\f. \\xs. match xs with ...")
    t = infer(
        r"let map = \f. \xs. match xs with | Nil -> Nil | Cons x rest -> Cons (f x) rest "
        r"in map (\n. n + 1) (Cons 1 Nil)",
        use_builtins=True,
    )
    print(f"   Type: {type_to_string(t)}")
    # Expected: List<Int>

    # 10. Inference trace
    print("\n10. Inference trace:")
    print("    let id = \\x. x in id 42")
    t, steps = infer_with_trace(r"let id = \x. x in id 42")
    for step in steps:
        print(f"    {step}")
    print(f"    => {type_to_string(t)}")

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()