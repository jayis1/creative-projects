#!/usr/bin/env python3
"""Example: Iterative solvers (Jacobi, Gauss-Seidel, SOR, Conjugate Gradient).

Demonstrates solving the same linear system with four iterative methods
and comparing convergence speed.
"""

from matrix_decomp import Matrix, lu_solve
from matrix_decomp.iterative import jacobi_solve, gauss_seidel_solve, sor_solve, conjugate_gradient


def main() -> None:
    # A strictly diagonally dominant, symmetric positive-definite matrix.
    A = Matrix([
        [10.0, -1.0, 2.0, 0.0],
        [-1.0, 11.0, -1.0, 3.0],
        [2.0, -1.0, 10.0, -1.0],
        [0.0, 3.0, -1.0, 8.0],
    ])
    b = [6.0, 25.0, -11.0, 15.0]

    # Ground-truth via direct (LU) solve.
    x_exact = lu_solve(A, b)
    print("Direct (LU) solution:", [round(v, 6) for v in x_exact])
    print()

    for name, solver in [
        ("Jacobi", jacobi_solve),
        ("Gauss-Seidel", gauss_seidel_solve),
        ("SOR (omega=1.5)", lambda A, b, **kw: sor_solve(A, b, omega=1.5, **kw)),
        ("Conjugate Gradient", conjugate_gradient),
    ]:
        result = solver(A, b, tol=1e-14, max_iter=2000)
        match = all(abs(a - b) < 1e-8 for a, b in zip(result.x, x_exact))
        print(f"{name:25s}  iters={result.iterations:4d}  "
              f"residual={result.residual:.2e}  "
              f"converged={'yes' if result.converged else 'NO'}  "
              f"correct={match}")

    # Convergence history plot (ASCII).
    print("\nConvergence history (Jacobi vs CG, first 20 iterations):")
    r_j = jacobi_solve(A, b, tol=1e-14, max_iter=20)
    r_cg = conjugate_gradient(A, b, tol=1e-14, max_iter=20)
    max_res = max(max(r_j.history), max(r_cg.history))
    for i in range(min(20, len(r_j.history), len(r_cg.history))):
        bar_j = "#" * int(40 * r_j.history[i] / max_res)
        bar_cg = "#" * int(40 * r_cg.history[i] / max_res)
        print(f"  iter {i:2d}  Jacobi {bar_j:40s} {r_j.history[i]:.2e}")
        print(f"           CG     {bar_cg:40s} {r_cg.history[i]:.2e}")


if __name__ == "__main__":
    main()