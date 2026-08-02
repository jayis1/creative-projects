"""Command-line interface for the matrix_decomp package."""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from . import __version__
from .matrix import Matrix


def _parse_matrix(text: str) -> Matrix:
    """Parse a matrix from a JSON array or newline/semicolon-separated rows."""
    text = text.strip()
    if text.startswith("["):
        data = json.loads(text)
        return Matrix(data)
    # Allow semicolon or newline row separators, comma/space cell separators.
    rows = []
    for chunk in text.replace(";", "\n").split("\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        # Split on commas if present, otherwise whitespace.
        cells = [c.strip() for c in chunk.split(",")] if "," in chunk else chunk.split()
        rows.append([float(c) for c in cells])
    return Matrix(rows)


def _format_matrix(m: Matrix) -> str:
    return str(m)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="matrix-decomp",
        description="Matrix decomposition & linear algebra toolkit (pure Python).",
    )
    parser.add_argument("--version", action="version", version=f"matrix-decomp {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    # LU
    p_lu = sub.add_parser("lu", help="LU decomposition with partial pivoting")
    p_lu.add_argument("matrix", help="Input matrix (JSON array or rows)")
    p_lu.add_argument("--solve", help="Optional RHS vector (JSON array) to solve Ax=b")

    # Cholesky
    p_chol = sub.add_parser("cholesky", help="Cholesky factorization of an SPD matrix")
    p_chol.add_argument("matrix", help="Input matrix (JSON array or rows)")

    # QR
    p_qr = sub.add_parser("qr", help="QR decomposition via Householder reflections")
    p_qr.add_argument("matrix", help="Input matrix (JSON array or rows)")

    # SVD
    p_svd = sub.add_parser("svd", help="Singular Value Decomposition")
    p_svd.add_argument("matrix", help="Input matrix (JSON array or rows)")

    # Eigenvalues
    p_eig = sub.add_parser("eigen", help="Eigenvalues via QR algorithm")
    p_eig.add_argument("matrix", help="Input matrix (JSON array or rows)")
    p_eig.add_argument("--vectors", action="store_true", help="Also compute eigenvectors (symmetric matrices)")

    # Determinant
    p_det = sub.add_parser("det", help="Determinant of a square matrix")
    p_det.add_argument("matrix", help="Input matrix (JSON array or rows)")

    # Inverse
    p_inv = sub.add_parser("inv", help="Inverse of a square matrix")
    p_inv.add_argument("matrix", help="Input matrix (JSON array or rows)")

    # Rank
    p_rank = sub.add_parser("rank", help="Numerical rank of a matrix")
    p_rank.add_argument("matrix", help="Input matrix (JSON array or rows)")

    # Solve
    p_solve = sub.add_parser("solve", help="Solve A x = b")
    p_solve.add_argument("matrix", help="Input matrix (JSON array or rows)")
    p_solve.add_argument("rhs", help="RHS vector (JSON array)")

    # Power
    p_pow = sub.add_parser("power", help="Integer matrix power A^p")
    p_pow.add_argument("matrix", help="Input matrix (JSON array or rows)")
    p_pow.add_argument("exp", type=int, help="Non-negative integer exponent")

    # Polyfit
    p_poly = sub.add_parser("polyfit", help="Polynomial least-squares fit")
    p_poly.add_argument("xs", help="x values (JSON array)")
    p_poly.add_argument("ys", help="y values (JSON array)")
    p_poly.add_argument("degree", type=int, help="Polynomial degree")

    # Condition number
    p_cond = sub.add_parser("cond", help="Condition number of a matrix")
    p_cond.add_argument("matrix", help="Input matrix (JSON array or rows)")

    args = parser.parse_args(argv)

    # Commands that take a matrix argument parse it here; polyfit does not.
    A = None
    if hasattr(args, "matrix"):
        A = _parse_matrix(args.matrix)

    from .lu import lu_decompose, lu_solve, lu_inverse, determinant
    from .cholesky import cholesky
    from .qr import qr_householder
    from .svd import svd, rank as svd_rank, condition_number as cond_num
    from .eigen import qr_algorithm, jacobi_eigen
    from .matrix import matrix_power
    from .least_squares import polynomial_fit

    if args.command == "lu":
        L, U, perm, sign = lu_decompose(A)
        print("L ="); print(_format_matrix(L))
        print("U ="); print(_format_matrix(U))
        print("perm =", perm, "sign =", sign)
        if args.solve:
            b = json.loads(args.solve)
            x = lu_solve(A, b)
            print("x =", x)
    elif args.command == "cholesky":
        L = cholesky(A)
        print("L ="); print(_format_matrix(L))
    elif args.command == "qr":
        Q, R = qr_householder(A)
        print("Q ="); print(_format_matrix(Q))
        print("R ="); print(_format_matrix(R))
    elif args.command == "svd":
        U, S, Vt = svd(A)
        print("U ="); print(_format_matrix(U))
        print("S =", [round(s, 8) for s in S])
        print("Vt ="); print(_format_matrix(Vt))
    elif args.command == "eigen":
        if args.vectors:
            vals, V = jacobi_eigen(A)
            print("eigenvalues =", [round(v, 8) for v in vals])
            print("eigenvectors (columns) ="); print(_format_matrix(V))
        else:
            vals = qr_algorithm(A)
            print("eigenvalues =", [round(v, 8) for v in vals])
    elif args.command == "det":
        print(determinant(A))
    elif args.command == "inv":
        print(_format_matrix(lu_inverse(A)))
    elif args.command == "rank":
        print(svd_rank(A))
    elif args.command == "solve":
        b = json.loads(args.rhs)
        print(lu_solve(A, b))
    elif args.command == "power":
        print(_format_matrix(matrix_power(A, args.exp)))
    elif args.command == "polyfit":
        xs = json.loads(args.xs)
        ys = json.loads(args.ys)
        coeffs = polynomial_fit(xs, ys, args.degree)
        print([round(c, 8) for c in coeffs])
    elif args.command == "cond":
        print(cond_num(A))
    return 0


if __name__ == "__main__":
    sys.exit(main())