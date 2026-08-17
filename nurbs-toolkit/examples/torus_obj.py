"""Example: create a torus and export it as OBJ."""
from nurbs import make_torus, tessellate_surface, export_obj

torus = make_torus(R=3.0, r=1.0, u_segments=4, v_segments=4)
print(f"Torus: {torus}")

verts, faces = tessellate_surface(torus, samples_u=40, samples_v=40)
obj = export_obj(verts, faces)
with open("torus.obj", "w") as f:
    f.write(obj)
print(f"Wrote torus.obj ({len(verts)} vertices, {len(faces)} faces)")