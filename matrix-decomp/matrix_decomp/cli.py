"""Command-line interface for the matrix_decomp package.

Subcommands
-----------

``lu``         LU decomposition with partial pivoting (PA = LU)
``lu-cp``      LU with complete pivoting (PAQ = LU)
``cholesky``   Cholesky factorization of an SPD matrix
``qr``         QR decomposition via Householder reflections
``svd``        Singular Value Decomposition
``eigen``      Eigenvalues via QR algorithm / Jacobi
``det``        Determinant of a square matrix
``inv``        Inverse of a square matrix
``rank``       Numerical rank of a matrix
``solve``      Solve A x = b (LU for square, QR for over-determined)
``power``      Integer matrix power A^p
``polyfit``    Polynomial least-squares fit
``cond``       Condition number of a matrix
``jacobi``     Iterative Jacobi solve
``gs``         Iterative Gauss-Seidel solve
``sor``        Iterative SOR solve
``cg``         Conjugate Gradient solve (SPD)
``pca``        Principal Component Analysis on a data matrix
``cov``        Sample covariance matrix
``corr``       Pearson correlation matrix
``schur``      Schur decomposition (symmetric matrices)
``polar``      Polar decomposition A = Q P
``convert``    Convert a matrix file between CSV and JSON
``bench``      Benchmark all decompositions on a random matrix

Matrices can be passed as JSON arrays (``"[[1,2],[3,4]]"``), as
semicolon/newline-separated rows with comma- or space-separated values,
or loaded from a file via ``--file PATH``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import List

from . import __version__
from .matrix import Matrix
from .logging_config import get_logger
from .file_io import load_csv, load_json, parse_matrix_string

log = get_logger("cli")


def _load_matrix(text: str, file_path: str | None = None) -> Matrix:
    """Load a matrix from a file path, a JSON/semicolom string, or stdin."""
    if file_path is not None:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".json":
            return load_json(file_path)
        return load_csv(file_path)
    if text == "-" or text is None:
        # Read from stdin
        data = sys.stdin.read().strip()
        return parse_matrix_string(data)
    return parse_matrix_string(text)


def _parse_vector(text: str) -> list:
    """Parse a vector from JSON or comma/space separated values."""
    text = text.strip()
    if text.startswith("["):
        return json.loads(text)
    if "," in text:
        return [float(c.strip()) for c in text.split(",") if c.strip()]
    return [float(c) for c in text.split() if c]


def _format_matrix(m: Matrix) -> str:
    return str(m)


def _add_matrix_arg(p, help_text="Input matrix (JSON array, rows, or --file PATH)"):
    p.add_argument("matrix", nargs="?", default=None, help=help_text)
    p.add_argument("--file", "-f", default=None, help="Load matrix from a CSV/JSON file")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="matrix-decomp",
        description="Matrix decomposition & linear algebra toolkit (pure Python, no NumPy).",
    )
    parser.add_argument("--version", action="version", version=f"matrix-decomp {__version__}")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable INFO logging")
    parser.add_argument("--debug", action="store_true", help="Enable DEBUG logging")
    sub = parser.add_subparsers(dest="command", required=True)

    # ---- LU ----
    p_lu = sub.add_parser("lu", help="LU decomposition with partial pivoting")
    _add_matrix_arg(p_lu)
    p_lu.add_argument("--solve", default=None, help="RHS vector (JSON array)")

    # ---- LU complete pivoting ----
    p_lcp = sub.add_parser("lu-cp", help="LU with complete pivoting (PAQ = LU)")
    _add_matrix_arg(p_lcp)

    # ---- Cholesky ----
    p_chol = sub.add_parser("cholesky", help="Cholesky factorization of an SPD matrix")
    _add_matrix_arg(p_chol)

    # ---- QR ----
    p_qr = sub.add_parser("qr", help="QR decomposition via Householder reflections")
    _add_matrix_arg(p_qr)
    p_qr.add_argument("--method", choices=["householder", "givens", "mgs"], default="householder")

    # ---- SVD ----
    p_svd = sub.add_parser("svd", help="Singular Value Decomposition")
    _add_matrix_arg(p_svd)
    p_svd.add_argument("--truncate", type=int, default=None, help="Keep only top-k singular values")

    # ---- Eigenvalues ----
    p_eig = sub.add_parser("eigen", help="Eigenvalues via QR algorithm")
    _add_matrix_arg(p_eig)
    p_eig.add_argument("--vectors", action="store_true", help="Also compute eigenvectors (symmetric)")
    p_eig.add_argument("--method", choices=["qr", "jacobi", "power"], default="qr")

    # ---- Determinant ----
    p_det = sub.add_parser("det", help="Determinant of a square matrix")
    _add_matrix_arg(p_det)

    # ---- Inverse ----
    p_inv = sub.add_parser("inv", help="Inverse of a square matrix")
    _add_matrix_arg(p_inv)

    # ---- Rank ----
    p_rank = sub.add_parser("rank", help="Numerical rank of a matrix")
    _add_matrix_arg(p_rank)

    # ---- Solve ----
    p_solve = sub.add_parser("solve", help="Solve A x = b")
    _add_matrix_arg(p_solve)
    p_solve.add_argument("rhs", help="RHS vector (JSON array)")
    p_solve.add_argument("--method", choices=["lu", "qr", "cg"], default="lu")

    # ---- Power ----
    p_pow = sub.add_parser("power", help="Integer matrix power A^p")
    _add_matrix_arg(p_pow)
    p_pow.add_argument("exp", type=int, help="Non-negative integer exponent")

    # ---- Polyfit ----
    p_poly = sub.add_parser("polyfit", help="Polynomial least-squares fit")
    p_poly.add_argument("xs", help="x values (JSON array)")
    p_poly.add_argument("ys", help="y values (JSON array)")
    p_poly.add_argument("degree", type=int, help="Polynomial degree")

    # ---- Condition number ----
    p_cond = sub.add_parser("cond", help="Condition number of a matrix")
    _add_matrix_arg(p_cond)

    # ---- Iterative: Jacobi ----
    p_jac = sub.add_parser("jacobi", help="Iterative Jacobi solve")
    _add_matrix_arg(p_jac)
    p_jac.add_argument("rhs", help="RHS vector (JSON array)")
    p_jac.add_argument("--max-iter", type=int, default=1000)
    p_jac.add_argument("--tol", type=float, default=1e-10)

    # ---- Iterative: Gauss-Seidel ----
    p_gs = sub.add_parser("gs", help="Iterative Gauss-Seidel solve")
    _add_matrix_arg(p_gs)
    p_gs.add_argument("rhs", help="RHS vector (JSON array)")
    p_gs.add_argument("--max-iter", type=int, default=1000)
    p_gs.add_argument("--tol", type=float, default=1e-10)

    # ---- Iterative: SOR ----
    p_sor = sub.add_parser("sor", help="Iterative SOR solve")
    _add_matrix_arg(p_sor)
    p_sor.add_argument("rhs", help="RHS vector (JSON array)")
    p_sor.add_argument("--omega", type=float, default=1.0)
    p_sor.add_argument("--max-iter", type=int, default=1000)
    p_sor.add_argument("--tol", type=float, default=1e-10)

    # ---- Iterative: CG ----
    p_cg = sub.add_parser("cg", help="Conjugate Gradient solve (SPD)")
    _add_matrix_arg(p_cg)
    p_cg.add_argument("rhs", help="RHS vector (JSON array)")
    p_cg.add_argument("--max-iter", type=int, default=1000)
    p_cg.add_argument("--tol", type=float, default=1e-10)

    # ---- PCA ----
    p_pca = sub.add_parser("pca", help="Principal Component Analysis")
    _add_matrix_arg(p_pca)
    p_pca.add_argument("--k", type=int, default=None, help="Number of components")
    p_pca.add_argument("--no-standardize", action="store_true")

    # ---- Covariance ----
    p_cov = sub.add_parser("cov", help="Sample covariance matrix")
    _add_matrix_arg(p_cov)

    # ---- Correlation ----
    p_corr = sub.add_parser("corr", help="Pearson correlation matrix")
    _add_matrix_arg(p_corr)

    # ---- Schur ----
    p_schur = sub.add_parser("schur", help="Schur decomposition (symmetric)")
    _add_matrix_arg(p_schur)

    # ---- Polar ----
    p_polar = sub.add_parser("polar", help="Polar decomposition A = Q P")
    _add_matrix_arg(p_polar)

    # ---- Convert ----
    p_conv = sub.add_parser("convert", help="Convert a matrix file between CSV and JSON")
    p_conv.add_argument("input", help="Input file path")
    p_conv.add_argument("output", help="Output file path")

    # ---- Benchmark ----
    p_bench = sub.add_parser("bench", help="Benchmark all decompositions on a random n x n matrix")
    p_bench.add_argument("n", type=int, help="Matrix dimension")
    p_bench.add_argument("--seed", type=int, default=42)

    args = parser.parse_args(argv)

    if args.verbose:
        from .logging_config import set_level
        set_level("INFO")
    if args.debug:
        from .logging_config import set_level
        set_level("DEBUG")

    # Lazy imports
    from .lu import lu_decompose, lu_solve, lu_inverse, determinant
    from .lu import SingularMatrixError
    from .cholesky import cholesky
    from .qr import qr_householder, qr_givens, modified_gram_schmidt
    from .svd import svd, rank as svd_rank, condition_number as cond_num, truncated_svd
    from .eigen import qr_algorithm, jacobi_eigen, power_iteration
    from .matrix import matrix_power
    from .least_squares import polynomial_fit
    from .iterative import jacobi_solve, gauss_seidel_solve, sor_solve, conjugate_gradient
    from .stats import pca as pca_func, covariance_matrix, correlation_matrix
    from .decompositions import schur_decomposition, polar_decomposition, lu_complete_pivot
    from .file_io import save_csv, save_json, load_csv, load_json

    # Load matrix for commands that need it
    A = None
    if hasattr(args, "matrix") or hasattr(args, "file"):
        mat_text = getattr(args, "matrix", None)
        file_arg = getattr(args, "file", None)
        A = _load_matrix(mat_text, file_arg)

    if args.command == "lu":
        L, U, perm, sign = lu_decompose(A)
        print("L ="); print(_format_matrix(L))
        print("U ="); print(_format_matrix(U))
        print("perm =", perm, "sign =", sign)
        if args.solve:
            b = _parse_vector(args.solve)
            x = lu_solve(A, b)
            print("x =", x)
    elif args.command == "lu-cp":
        L, U, rp, cp, sign = lu_complete_pivot(A)
        print("L ="); print(_format_matrix(L))
        print("U ="); print(_format_matrix(U))
        print("row_perm =", rp, "col_perm =", cp, "sign =", sign)
    elif args.command == "cholesky":
        L = cholesky(A)
        print("L ="); print(_format_matrix(L))
    elif args.command == "qr":
        if args.method == "householder":
            Q, R = qr_householder(A)
        elif args.method == "givens":
            Q, R = qr_givens(A)
        else:
            Q, R = modified_gram_schmidt(A)
        print("Q ="); print(_format_matrix(Q))
        print("R ="); print(_format_matrix(R))
    elif args.command == "svd":
        if args.truncate is not None:
            Uk, Sk, Vtk = truncated_svd(A, k=args.truncate)
            print("U (truncated) ="); print(_format_matrix(Uk))
            print("S (truncated) =", [round(s, 8) for s in Sk])
            print("Vt (truncated) ="); print(_format_matrix(Vtk))
        else:
            U, S, Vt = svd(A)
            print("U ="); print(_format_matrix(U))
            print("S =", [round(s, 8) for s in S])
            print("Vt ="); print(_format_matrix(Vt))
    elif args.command == "eigen":
        if args.method == "jacobi" or (args.vectors and args.method != "power"):
            vals, V = jacobi_eigen(A)
            print("eigenvalues =", [round(v, 8) for v in vals])
            if args.vectors:
                print("eigenvectors (columns) ="); print(_format_matrix(V))
        elif args.method == "power":
            val, vec = power_iteration(A)
            print(f"dominant eigenvalue = {val:.8f}")
            print("eigenvector =", [round(v, 8) for v in vec])
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
        b = _parse_vector(args.rhs)
        if args.method == "qr":
            from .qr import qr_solve
            x = qr_solve(A, b)
        elif args.method == "cg":
            result = conjugate_gradient(A, b, tol=1e-12)
            x = result.x
            log.info("CG converged in %d iterations, residual=%.2e", result.iterations, result.residual)
        else:
            x = lu_solve(A, b)
        print(x)
    elif args.command == "power":
        print(_format_matrix(matrix_power(A, args.exp)))
    elif args.command == "polyfit":
        xs = _parse_vector(args.xs)
        ys = _parse_vector(args.ys)
        coeffs = polynomial_fit(xs, ys, args.degree)
        print([round(c, 8) for c in coeffs])
    elif args.command == "cond":
        print(cond_num(A))
    elif args.command == "jacobi":
        b = _parse_vector(args.rhs)
        result = jacobi_solve(A, b, max_iter=args.max_iter, tol=args.tol)
        print(f"x = {result.x}")
        print(f"# {result}")
    elif args.command == "gs":
        b = _parse_vector(args.rhs)
        result = gauss_seidel_solve(A, b, max_iter=args.max_iter, tol=args.tol)
        print(f"x = {result.x}")
        print(f"# {result}")
    elif args.command == "sor":
        b = _parse_vector(args.rhs)
        result = sor_solve(A, b, omega=args.omega, max_iter=args.max_iter, tol=args.tol)
        print(f"x = {result.x}")
        print(f"# {result}")
    elif args.command == "cg":
        b = _parse_vector(args.rhs)
        result = conjugate_gradient(A, b, max_iter=args.max_iter, tol=args.tol)
        print(f"x = {result.x}")
        print(f"# {result}")
    elif args.command == "pca":
        k = args.k
        comps, var, ratios = pca_func(A, k=k, standardize_first=not args.no_standardize)
        print("Components (columns) ="); print(_format_matrix(comps))
        print("Explained variance =", [round(v, 8) for v in var])
        print("Explained variance ratio =", [round(r, 8) for r in ratios])
    elif args.command == "cov":
        print(_format_matrix(covariance_matrix(A)))
    elif args.command == "corr":
        print(_format_matrix(correlation_matrix(A)))
    elif args.command == "schur":
        Q, T = schur_decomposition(A)
        print("Q ="); print(_format_matrix(Q))
        print("T ="); print(_format_matrix(T))
    elif args.command == "polar":
        Q, P = polar_decomposition(A)
        print("Q (orthogonal) ="); print(_format_matrix(Q))
        print("P (SPD) ="); print(_format_matrix(P))
    elif args.command == "convert":
        ext_in = os.path.splitext(args.input)[1].lower()
        if ext_in == ".json":
            M = load_json(args.input)
        else:
            M = load_csv(args.input)
        ext_out = os.path.splitext(args.output)[1].lower()
        if ext_out == ".json":
            save_json(M, args.output, wrapper=True)
        else:
            save_csv(M, args.output)
        log.info("Converted %s -> %s", args.input, args.output)
    elif args.command == "bench":
        import random
        random.seed(args.seed)
        n = args.n
        data = [[random.gauss(0, 1) for _ in range(n)] for _ in range(n)]
        M = Matrix(data)
        print(f"Benchmarking on a {n}x{n} random matrix (seed={args.seed}):\n")
        for name, fn in [
            ("LU", lambda: lu_decompose(M)),
            ("QR (Householder)", lambda: qr_householder(M)),
            ("Cholesky*", lambda: cholesky(_make_spd(M))),
            ("SVD", lambda: svd(M)),
            ("Eigen (Jacobi)", lambda: jacobi_eigen(M)),
            ("QR algorithm", lambda: qr_algorithm(M)),
        ]:
            t0 = time.perf_counter()
            try:
                fn()
                dt = time.perf_counter() - t0
                print(f"  {name:20s} {dt*1000:10.2f} ms")
            except Exception as e:
                print(f"  {name:20s} FAILED ({e})")
        print("\n* Cholesky benchmarked on A^T A (guaranteed SPD)")
    return 0


def _make_spd(M):
    """Make an SPD matrix from M by computing M^T M."""
    from .matrix import matmul, transpose
    return matmul(transpose(M), M)


if __name__ == "__main__":
    sys.exit(main())