from mesher import Face, VoxelModel


def test_single_voxel_has_six_faces_and_obj():
    model = VoxelModel([(0, 0, 0)])
    assert len(model.faces()) == 6
    assert len(model.greedy_faces()) == 6
    obj = model.to_obj()
    assert obj.count("\nv ") == 8
    assert obj.count("\nf ") == 6


def test_adjacent_voxels_remove_internal_faces_and_merge_sides():
    model = VoxelModel([(0, 0, 0), (1, 0, 0)])
    assert len(model.faces()) == 10
    assert len(model.greedy_faces()) == 6


def test_material_boundaries_are_not_merged():
    model = VoxelModel([(0, 0, 0, 1), (1, 0, 0, 2)])
    assert len(model.greedy_faces()) == 10


def test_ascii_stl_triangulates_each_quad_with_outward_normals():
    model = VoxelModel([(0, 0, 0)])
    stl = model.to_stl(name="cube")
    assert stl.startswith("solid cube\n") and stl.endswith("endsolid cube\n")
    assert stl.count("facet normal") == 12
    assert stl.count("      vertex ") == 36
    for line in stl.splitlines():
        if line.startswith("  facet normal"):
            normal = tuple(map(int, line.split()[-3:]))
            assert sum(value != 0 for value in normal) == 1


def test_stl_rejects_newline_in_solid_name():
    import pytest
    with pytest.raises(ValueError, match="no newlines"):
        VoxelModel([]).to_stl(name="bad\\nsolid")


def test_validation():
    for voxels in [[(0, 0)], [(0.5, 0, 0)], [(0, 0, 0, 0)], [(0, 0, 0), (0, 0, 0)]]:
        try:
            VoxelModel(voxels)
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted invalid voxel input: {voxels}")
