"""Knot vector generation and validation utilities.

A *knot vector* is a non-decreasing sequence of real numbers
``U = [u_0, u_1, ..., u_m]``.  For a B-spline of degree ``p`` with ``n+1``
control points the relationship ``m = n + p + 1`` holds.
"""

from __future__ import annotations

from typing import Sequence, List


def generate_uniform_knot_vector(n: int, p: int) -> List[float]:
    """Generate an *unclamped* uniform knot vector.

    Parameters
    ----------
    n : int
        Number of control points minus one (i.e. ``n+1`` control points).
    p : int
        Spline degree.

    Returns
    -------
    list[float]
        A knot vector of length ``n + p + 2`` (= ``m + 1`` where
        ``m = n + p + 1``) with values evenly spaced from 0 to ``n + p``.
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    if p < 0:
        raise ValueError("p must be >= 0")
    # m = n + p + 1; knot vector has m + 1 = n + p + 2 elements.
    return [float(i) for i in range(n + p + 2)]


def generate_clamped_uniform_knot_vector(n: int, p: int) -> List[float]:
    """Generate a *clamped* (open) uniform knot vector.

    The first and last knots have multiplicity ``p + 1`` so the curve
    interpolates the end control points.

    Parameters
    ----------
    n : int
        Number of control points minus one.
    p : int
        Spline degree.

    Returns
    -------
    list[float]
        A knot vector of length ``n + p + 2`` with the parameter range
        ``[0, n - p + 1]`` and evenly-spaced unit interior knots.
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    if p < 0:
        raise ValueError("p must be >= 0")
    if n < p:
        raise ValueError("n must be >= p for a clamped knot vector")
    # m = n + p + 1; knot vector length = m + 1 = n + p + 2.
    end = n - p + 1  # parameter range upper bound
    knots: List[float] = [0.0] * (p + 1)
    for i in range(1, n - p + 1):  # interior knots: 1, 2, ..., n-p
        knots.append(float(i))
    knots.extend([float(end)] * (p + 1))
    return knots


def validate_knot_vector(knots: Sequence[float], n: int, p: int) -> None:
    """Validate that *knots* is a legal knot vector for ``n+1`` control
    points and degree ``p``.

    The knot vector must have ``m + 1 = n + p + 2`` elements (where
    ``m = n + p + 1`` is the highest knot index).

    Raises
    ------
    ValueError
        If any constraint is violated.
    """
    expected = n + p + 2
    if len(knots) != expected:
        raise ValueError(
            f"Knot vector length {len(knots)} != n + p + 2 = {expected}"
        )
    prev = knots[0]
    for i, u in enumerate(knots):
        if u < prev:
            raise ValueError(
                f"Knot vector must be non-decreasing; u[{i}]={u} < u[{i-1}]={prev}"
            )
        prev = u
    # For clamped vectors the end multiplicity should not exceed p+1.
    # We do not enforce clamped-ness, but multiplicity anywhere must be <= p+1.
    i = 0
    m = len(knots)
    while i < m:
        j = i
        while j < m and knots[j] == knots[i]:
            j += 1
        mult = j - i
        if mult > p + 1:
            raise ValueError(
                f"Knot {knots[i]} has multiplicity {mult} > p+1={p+1}"
            )
        i = j