"""Tests for the CLI interface."""
from __future__ import annotations
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matrix_decomp.cli import main


def _run(argv):
    """Run CLI with argv, returning the exit code (captured stdout)."""
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(argv)
    return code, buf.getvalue()


def test_cli_det():
    code, out = _run(["det", "[[6,1,1],[4,-2,5],[2,8,7]]"])
    assert code == 0
    assert "-306" in out


def test_cli_lu():
    code, out = _run(["lu", "[[4,3],[6,3]]", "--solve", "[10,12]"])
    assert code == 0
    assert "L =" in out
    assert "U =" in out
    assert "x = [1.0, 2.0]" in out or "x = [1.0, 2.0]" in out


def test_cli_qr():
    code, out = _run(["qr", "[[1,1],[1,0],[0,1]]"])
    assert code == 0
    assert "Q =" in out
    assert "R =" in out


def test_cli_qr_givens():
    code, out = _run(["qr", "[[1,2],[3,4]]", "--method", "givens"])
    assert code == 0
    assert "Q =" in out


def test_cli_svd():
    code, out = _run(["svd", "[[3,0],[0,2]]"])
    assert code == 0
    assert "S = [3.0, 2.0]" in out


def test_cli_svd_truncate():
    code, out = _run(["svd", "[[1,0,0],[0,2,0],[0,0,3]]", "--truncate", "2"])
    assert code == 0
    assert "truncated" in out


def test_cli_eigen():
    code, out = _run(["eigen", "[[2,1],[1,2]]"])
    assert code == 0
    assert "eigenvalues" in out
    assert "3.0" in out


def test_cli_eigen_vectors():
    code, out = _run(["eigen", "[[2,1],[1,2]]", "--vectors"])
    assert code == 0
    assert "eigenvectors" in out


def test_cli_eigen_power():
    code, out = _run(["eigen", "[[3,0],[0,1]]", "--method", "power"])
    assert code == 0
    assert "dominant eigenvalue" in out
    assert "3" in out


def test_cli_inv():
    code, out = _run(["inv", "[[4,7],[2,6]]"])
    assert code == 0
    assert "0.6" in out  # inv[0][0] = 6/10


def test_cli_rank():
    code, out = _run(["rank", "[[1,2],[2,4]]"])
    assert code == 0
    assert "1" in out


def test_cli_solve():
    code, out = _run(["solve", "[[2,1],[1,3]]", "[5,10]"])
    assert code == 0
    assert "[1.0, 3.0]" in out


def test_cli_solve_cg():
    code, out = _run(["solve", "[[4,1],[1,3]]", "[1,2]", "--method", "cg"])
    assert code == 0
    assert "0.09" in out


def test_cli_power():
    code, out = _run(["power", "[[1,1],[0,1]]", "3"])
    assert code == 0
    assert "3" in out


def test_cli_polyfit():
    code, out = _run(["polyfit", "[0,1,2,3]", "[1,3,5,7]", "1"])
    assert code == 0
    assert "1.0" in out and "2.0" in out


def test_cli_cond():
    code, out = _run(["cond", "[[1,0],[0,1e6]]"])
    assert code == 0
    assert "1000000" in out or "1e+06" in out


def test_cli_jacobi():
    code, out = _run(["jacobi", "[[10,1],[1,10]]", "[11,11]", "--tol", "1e-12"])
    assert code == 0
    assert "1.0" in out


def test_cli_gs():
    code, out = _run(["gs", "[[10,1],[1,10]]", "[11,11]", "--tol", "1e-12"])
    assert code == 0
    assert "converged" in out


def test_cli_sor():
    code, out = _run(["sor", "[[10,1],[1,10]]", "[11,11]", "--omega", "1.5", "--tol", "1e-12"])
    assert code == 0
    assert "converged" in out


def test_cli_cg():
    code, out = _run(["cg", "[[4,1],[1,3]]", "[1,2]", "--tol", "1e-12"])
    assert code == 0
    assert "converged" in out


def test_cli_pca():
    code, out = _run(["pca", "[[0,0],[1,0],[2,0],[3,0]]", "--no-standardize", "--k", "2"])
    assert code == 0
    assert "Components" in out


def test_cli_cov():
    code, out = _run(["cov", "[[1,2],[3,4],[5,6]]"])
    assert code == 0
    assert "4" in out  # var of col 0


def test_cli_corr():
    code, out = _run(["corr", "[[1,2],[3,5],[4,1],[2,3]]"])
    assert code == 0
    assert "1" in out  # diagonal


def test_cli_schur():
    code, out = _run(["schur", "[[4,1],[1,4]]"])
    assert code == 0
    assert "Q =" in out
    assert "T =" in out


def test_cli_polar():
    code, out = _run(["polar", "[[3,1],[1,2]]"])
    assert code == 0
    assert "Q (orthogonal)" in out
    assert "P (SPD)" in out


def test_cli_version():
    try:
        _run(["--version"])
        assert False
    except SystemExit as e:
        assert e.code == 0


def test_cli_convert(tmp_path=None):
    import tempfile
    import json
    csv_path = tempfile.mktemp(suffix=".csv")
    json_path = tempfile.mktemp(suffix=".json")
    try:
        with open(csv_path, "w") as f:
            f.write("1,2\n3,4\n")
        code, _ = _run(["convert", csv_path, json_path])
        assert code == 0
        with open(json_path) as f:
            obj = json.load(f)
        assert obj["matrix"] == [[1.0, 2.0], [3.0, 4.0]]
    finally:
        for p in (csv_path, json_path):
            if os.path.exists(p):
                os.unlink(p)


def test_cli_bench():
    code, out = _run(["bench", "4", "--seed", "42"])
    assert code == 0
    assert "LU" in out
    assert "ms" in out


def test_cli_cholesky():
    code, out = _run(["cholesky", "[[4,2],[2,3]]"])
    assert code == 0
    assert "L =" in out