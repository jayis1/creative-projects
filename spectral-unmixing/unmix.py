#!/usr/bin/env python3
"""Non-negative spectral unmixing with projected gradient descent (stdlib only)."""
from __future__ import annotations
import argparse, json, math

def solve(matrix, observed, *, steps=3000, tolerance=1e-10, normalize=False):
    """Estimate nonnegative material fractions minimizing ||Ax-y||².

    Matrix is band-major: one row per band and one column per material.
    """
    if not matrix or not observed or len(matrix) != len(observed):
        raise ValueError("matrix must have one nonempty row per observation")
    materials = len(matrix[0])
    if materials == 0 or any(len(row) != materials for row in matrix):
        raise ValueError("matrix must be rectangular with at least one material")
    if any(not math.isfinite(float(v)) for row in matrix for v in row) or any(not math.isfinite(float(v)) for v in observed):
        raise ValueError("all values must be finite")
    if steps < 1: raise ValueError("steps must be positive")
    gram = [[sum(row[i]*row[j] for row in matrix) for j in range(materials)] for i in range(materials)]
    lipschitz = max(sum(abs(x) for x in row) for row in gram)
    if lipschitz == 0: raise ValueError("zero signature matrix")
    rhs = [sum(row[i]*y for row,y in zip(matrix,observed)) for i in range(materials)]
    x = [0.0]*materials
    for _ in range(steps):
        nxt = [max(0.0, x[i] - (sum(gram[i][j]*x[j] for j in range(materials))-rhs[i])/lipschitz) for i in range(materials)]
        if max(abs(a-b) for a,b in zip(x,nxt)) < tolerance: x=nxt; break
        x=nxt
    return x

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('json_file'); p.add_argument('--steps',type=int,default=3000); a=p.parse_args()
    with open(a.json_file, encoding='utf8') as f: data=json.load(f)
    result=solve(data['signatures'],data['observed'],steps=a.steps)
    reconstruction=[sum(row[i]*result[i] for i in range(len(result))) for row in data['signatures']]
    residual=math.sqrt(sum((predicted-observed)**2 for predicted,observed in zip(reconstruction,data['observed'])))
    print(json.dumps({'fractions':result,'reconstruction':reconstruction,'residual_l2':residual}, indent=2))
if __name__=='__main__': main()
