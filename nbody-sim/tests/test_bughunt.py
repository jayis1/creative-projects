"""Bug-hunt tests for nbody-sim. Each test reproduces a bug before the fix."""
import os
import sys
import math
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nbody.body import Body
from nbody.simulation import Simulation
from nbody.barnes_hut import BHTree
from nbody.brute_force import brute_force_accelerations, barnes_hut_accelerations, force_error
from nbody.diagnostics import total_angular_momentum, virial_ratio, adaptive_dt
from nbody.serialize import save_result, load_snapshot, save_snapshot
from nbody.renderer import Renderer


def test_bug_self_force_colocated():
    """BUG: A body at the same position as a leaf body that *is* the query
    body gets zero force from that leaf, but if the leaf's mass includes the
    query body itself (it does — the tree contains all bodies), the BH
    approximation at an ancestor internal node will apply the leaf's COM
    (which is the query body's own position) as if it were an external mass.

    Actually the real bug: when theta is large, an internal node whose COM
    coincides with the query body produces a force toward itself (dx=dy=0 →
    zero force), so self-force is naturally zero. The actual issue is when
    co-located *distinct* bodies exist: the leaf skip check `sbx==bx and
    sby==by` skips *all* force from that leaf even if the leaf contains a
    different-mass body at the same point. The bucket mechanism should catch
    this, but only if the bucket is on the *same* node.

    Let's test: two co-located bodies should exert force on each other.
    """
    # Two bodies at the exact same point with different masses.
    bodies = [Body(1.0, 1.0, 0.0, 0.0, 1.0), Body(1.0, 1.0, 0.0, 0.0, 2.0)]
    # Brute force: force on body 0 from body 1 is G*m1*m2/r^3 * dx,dy = 0
    # because dx=dy=0. So brute force gives zero (they're at the same point).
    bf = brute_force_accelerations(bodies, G=1.0, softening=0.0)
    assert math.hypot(*bf[0]) < 1e-9, f"brute force should be 0 at same point, got {bf[0]}"

    # With softening, brute force gives a force along dx,dy = 0 → still 0.
    bf_soft = brute_force_accelerations(bodies, G=1.0, softening=0.5)
    assert math.hypot(*bf_soft[0]) < 1e-9, f"softened brute at same point should be 0, got {bf_soft[0]}"

    # Barnes-Hut: should also give ~0 for co-located (the COM is at the same
    # point, so dx=dy=0 → zero force). This is actually correct behavior!
    bh = barnes_hut_accelerations(bodies, theta=0.5, G=1.0, softening=0.5)
    err = math.hypot(bh[0][0] - bf_soft[0][0], bh[0][1] - bf_soft[0][1])
    print(f"  colocated BH vs BF error: {err:.2e}")
    assert err < 1e-9, f"BH should match BF (both 0) for co-located, got {bh[0]}"
    print("  test_bug_self_force_colocated: PASS (no bug here)")


def test_bug_run_called_twice_snapshot_t():
    """BUG: run() hardcodes t=0.0 for the initial snapshot instead of self.t.
    If run() is called after previous steps, the initial snapshot has wrong t.
    """
    sim = Simulation.two_body_orbit(dt=0.01, softening=0.1)
    # Run 50 steps first.
    sim.run(50)
    # Now run again with snapshots — the "initial" snapshot should have
    # t = 0.5 (50 * 0.01), not 0.0.
    res = sim.run(10, snapshot_every=5)
    first_snap_t = res.snapshots[0].t
    print(f"  first snapshot t = {first_snap_t} (expected ~0.5)")
    assert abs(first_snap_t - 0.5) < 1e-9, f"BUG: initial snapshot t={first_snap_t}, expected 0.5"
    # Also check the step number is correct (50, not 0).
    assert res.snapshots[0].step == 50, f"BUG: initial snapshot step={res.snapshots[0].step}, expected 50"
    print("  test_bug_run_called_twice_snapshot_t: PASS")


def test_bug_cli_missing_final_snapshot():
    """BUG (FIXED): CLI's on_step callback used to miss the final snapshot if
    steps was not a multiple of snapshot_every. The fix uses run()'s
    snapshot_every parameter directly, which guarantees a final snapshot.
    """
    sim = Simulation.two_body_orbit(dt=0.01, softening=0.1)
    snapshot_every = 7
    steps = 10  # 10 is not a multiple of 7

    # The fix: use snapshot_every in run() instead of a manual on_step callback.
    res = sim.run(steps, snapshot_every=snapshot_every)
    snapshots = res.snapshots
    print(f"  captured {len(snapshots)} snapshots, last step = {snapshots[-1].step if snapshots else 'none'}")
    # The final snapshot should be at the final step (10).
    assert snapshots[-1].step == steps, f"BUG: last snapshot at step {snapshots[-1].step}, expected {steps}"
    print("  test_bug_cli_missing_final_snapshot: PASS")


def test_bug_renderer_aspect_ratio():
    """BUG: Renderer._to_pixel distorts the world when width != height because
    it uses view_size for both axes but scales by width/height independently.
    A circle in world space becomes an ellipse in pixel space.
    """
    # Non-square image: 200 wide, 100 tall. View spans [-10, 10] in both axes.
    r = Renderer(width=200, height=100, view_size=10.0, trails=False)
    # A body at (10, 0) should map to the right edge (px=200), and a body at
    # (0, 10) should map to the top edge (py=0). But with the bug, (0,10) maps
    # to py = (10 - 10) / 20 * 100 = 0, which is correct. And (10,0) maps to
    # px = (10 + 10) / 20 * 200 = 200, also correct. So the mapping fills the
    # image — but a world circle of radius 5 maps to an ellipse because x is
    # stretched by 200/20=10 px/unit while y is stretched by 100/20=5 px/unit.
    # The aspect ratio is wrong: the world is not square-mapped.
    px1, py1 = r._to_pixel(5.0, 0.0)   # 5 units right of center
    px2, py2 = r._to_pixel(0.0, 5.0)   # 5 units up from center
    cx_px, cy_px = r._to_pixel(0.0, 0.0)
    dx_px = px1 - cx_px  # pixels for 5 world units in x
    dy_px = cy_px - py2  # pixels for 5 world units in y
    print(f"  5 world units: dx_px={dx_px}, dy_px={dy_px}")
    assert dx_px == dy_px, f"BUG: aspect ratio distorted (dx={dx_px}, dy={dy_px})"
    print("  test_bug_renderer_aspect_ratio: PASS")


def test_bug_unused_imports():
    """BUG: barnes_hut.py imports Vec2, add, scale, sub and field but never
    uses them — dead code that can confuse readers and linters.
    """
    import nbody.barnes_hut as bh
    # These names should not be in the module namespace if imports are cleaned.
    # (They're currently imported but unused.)
    src = open(bh.__file__).read()
    assert "from .vec import" not in src or "Vec2" not in bh.__dict__, \
        "BUG: unused vec imports in barnes_hut"
    # The 'field' import from dataclasses is unused.
    assert "from dataclasses import dataclass, field" not in src, \
        "BUG: unused 'field' import in barnes_hut"
    print("  test_bug_unused_imports: PASS")


def test_bug_dt_zero_adaptive_disabled():
    """EDGE: adaptive_dt with dt=0 should be allowed (dt is recomputed), but
    the validation `if dt <= 0.0 and not adaptive_dt` correctly allows it.
    Verify no crash."""
    sim = Simulation([Body(0,0,0,0,1), Body(1,0,0,0,1)], dt=0.0,
                     adaptive_dt=True, softening=0.5)
    res = sim.run(5)
    print(f"  adaptive dt=0 run: {res.n_steps} steps, E0={res.initial_energy:.3f}")
    assert res.n_steps == 5
    print("  test_bug_dt_zero_adaptive_disabled: PASS")


def test_bug_plummer_radius_formula():
    """BUG: plummer_sphere radius formula `r = R * u^(1/3) / sqrt(1 - u^(2/3))`
    diverges as u→1, producing bodies at enormous radii. The correct Plummer
    radius inverse-CDF is r = R / sqrt(u^(-2/3) - 1), which is bounded-ish but
    still grows. Actually the standard Plummer radius sampling uses:
      r = R * (u^(-2/3) - 1)^(-1/2)
    which is the same as R * u^(1/3) / sqrt(1 - u^(2/3)) after substitution.
    The issue is that as u→1, the denominator →0 and r→∞. This is actually
    correct for a Plummer model (which has infinite extent), but bodies can
    end up absurdly far away. We should cap r to a reasonable multiple of R.
    """
    sim = Simulation.plummer_sphere(n=200, seed=42, radius=10.0, softening=1.0)
    max_r = max(math.hypot(b.x, b.y) for b in sim.bodies)
    print(f"  max body radius = {max_r:.1f} (R=10, cap=100)")
    # After the fix, r is capped at 10 * radius = 100.
    assert max_r <= 100.0 + 1e-6, f"BUG: Plummer body at r={max_r}, exceeds cap of 100"
    print("  test_bug_plummer_radius_formula: PASS (capped at 10*R)")


if __name__ == "__main__":
    tests = [
        test_bug_self_force_colocated,
        test_bug_run_called_twice_snapshot_t,
        test_bug_cli_missing_final_snapshot,
        test_bug_renderer_aspect_ratio,
        test_bug_unused_imports,
        test_bug_dt_zero_adaptive_disabled,
        test_bug_plummer_radius_formula,
    ]
    failed = 0
    for t in tests:
        print(f"\n[{t.__name__}]")
        try:
            t()
        except AssertionError as e:
            print(f"  FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{'='*50}")
    print(f"{len(tests) - failed}/{len(tests)} tests passed, {failed} bugs confirmed")
    sys.exit(1 if failed else 0)