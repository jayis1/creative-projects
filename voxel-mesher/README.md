# Voxel Mesher

A dependency-free Python toolkit for extracting the exposed boundary of a voxel solid and reducing it to coplanar, material-aware quads. It includes deterministic Wavefront OBJ output. This is useful for inspecting block models, preparing low-poly meshes, and teaching surface-net concepts without pulling in a graphics stack.

## How it works

Each occupied integer cell contributes at most six outward faces. Faces adjacent to another occupied cell are suppressed. The greedy pass groups faces by axis, direction, grid plane, and material, then covers each group's 2D unit-cell mask with deterministic rectangles. Materials remain separate so a merged polygon never crosses a material boundary. OBJ export deduplicates shared corner positions and emits indexed quads.

The mesher is intentionally sparse: storage is proportional to occupied cells, not the volume of the bounding box. Face extraction is O(V log V) due to deterministic input sorting; greedy rectangle covering is practical for compact masks, but is not guaranteed globally minimum.

## Usage

```python
from mesher import VoxelModel

model = VoxelModel([
    (0, 0, 0),
    (1, 0, 0, 2),  # optional positive material ID
    (1, 1, 0),
])
print(f"unit faces: {len(model.faces())}")
print(f"merged quads: {len(model.greedy_faces())}")
with open("model.obj", "w", encoding="utf-8") as output:
    output.write(model.to_obj())
```

Coordinates must be integers, material IDs positive integers, and duplicate coordinates are rejected. Run tests with `pytest -q` from this directory (pytest is the only development dependency; production code uses the standard library).

## Phase 1 implementation

Supports exposed-face extraction, deterministic greedy rectangle merging, per-voxel material IDs, and OBJ mesh serialization.

## Phase 2 enhancements

A JSON-to-OBJ CLI accepts a document shaped as `{"voxels": [[x, y, z], [x, y, z, material]]}`. It can write the mesh to a file or stdout and optionally report voxel, exposed-face, and merged-quad counts to stderr. Malformed JSON, unsupported shapes, invalid voxels, and file errors produce a concise diagnostic and exit code 2.

```sh
python3 cli.py model.json --output model.obj --stats
```

## Phase 3 enhancements

The CLI also exports ASCII STL for 3D-printing and CAD workflows. Each greedily merged quad is triangulated into two facets with outward axis-aligned normals. The STL solid name is taken from the input filename stem; use `--output` to save it.

```sh
python3 cli.py model.json --format stl --output model.stl --stats
```

Tests (including CLI behavior) run with `pytest -q`.

## Known Issues (Resolved)

- OBJ quads on the Y axis had inward-facing winding because the chosen `(x, z)` face basis is left-handed relative to +Y. A single-voxel regression test calculated each triangle normal and failed before the fix; winding now accounts for the basis orientation, and all six normals point outward.
