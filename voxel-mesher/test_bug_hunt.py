from mesher import VoxelModel


def test_obj_quad_winding_points_outward_on_all_axes():
    model = VoxelModel([(0, 0, 0)])
    vertices = []
    faces = []
    for line in model.to_obj().splitlines():
        if line.startswith("v "):
            vertices.append(tuple(map(float, line.split()[1:])))
        elif line.startswith("f "):
            faces.append([int(index) - 1 for index in line.split()[1:]])
    for indices in faces:
        a, b, c = (vertices[index] for index in indices[:3])
        ab = tuple(b[i] - a[i] for i in range(3))
        ac = tuple(c[i] - a[i] for i in range(3))
        normal = (ab[1] * ac[2] - ab[2] * ac[1],
                  ab[2] * ac[0] - ab[0] * ac[2],
                  ab[0] * ac[1] - ab[1] * ac[0])
        assert sum(normal[i] * (a[i] - 0.5) for i in range(3)) > 0
