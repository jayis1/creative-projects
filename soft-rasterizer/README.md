# soft-rasterizer

A from-scratch software 3D rasterizer in pure Python — no OpenGL, no NumPy, no external graphics libraries. Implements the complete fixed-function rendering pipeline from vertex transformation to per-pixel shading.

## Features

- **Complete rendering pipeline**: vertex shader → near-plane clipping → perspective divide → viewport transform → scanline rasterization → z-buffer test → fragment shader
- **Z-buffer (depth buffer)**: per-pixel depth testing for correct visibility
- **Perspective-correct interpolation**: all vertex attributes (normals, UVs, colours) are interpolated with proper perspective correction via `1/w` weighting
- **Near-plane clipping**: Sutherland-Hodgman polygon clipping against the near plane to prevent division-by-zero artifacts
- **Backface culling**: screen-space winding-order test to skip triangles facing away from the camera
- **7 shading models**:
  - **Flat** — one colour per triangle (lighting at face centroid)
  - **Gouraud** — per-vertex lighting, colour interpolated across the triangle
  - **Phong** — per-pixel lighting with interpolated normals (most accurate)
  - **Wireframe** — edge-only rendering
  - **Normal** — visualise normals as RGB colours (debugging)
  - **Depth** — greyscale depth visualisation
- **Texture mapping**: nearest-neighbour and bilinear sampling with clamp-to-edge wrapping
- **Procedural checkerboard texture**
- **Phong illumination model**: ambient + diffuse (Lambertian) + specular (Phong) with support for multiple point and directional lights, distance attenuation
- **7 primitive mesh generators**: cube, sphere, plane, cylinder, torus, tetrahedron, octahedron
- **OBJ file loading**: Wavefront OBJ parser with `v`/`vt`/`vn`/`f` support and fan triangulation
- **PPM image output**: binary P6 PPM format (viewable in any image viewer)
- **ASCII preview**: render to terminal as ASCII art for quick debugging
- **Scene graph**: objects with position/rotation/scale transforms, cameras, lights
- **CLI tool**: render from the command line with configurable primitives, shaders, textures, camera angles

## How It Works

### Rendering Pipeline

```
Vertices → Vertex Shader → Clip Space → Near-Plane Clipping → Perspective Divide (÷w)
         → NDC → Viewport Transform → Screen Space → Rasterization (scanline fill)
         → Z-Buffer Test → Fragment Shader → Framebuffer
```

1. **Vertex Shader**: Each vertex is transformed from model space → world space (model matrix) → view space (view matrix) → clip space (projection matrix). Normals are transformed by the inverse-transpose of the model matrix.

2. **Near-Plane Clipping**: Triangles straddling the near plane are clipped using the Sutherland-Hodgman algorithm. The clip condition is `w + z ≥ 0` (i.e., the vertex is in front of the near plane). Clipped polygons are fan-triangulated.

3. **Perspective Divide**: Clip-space coordinates `(x, y, z, w)` are divided by `w` to produce Normalized Device Coordinates (NDC) in `[-1, 1]³`.

4. **Viewport Transform**: NDC coordinates are mapped to screen pixels: `x_screen = (ndc.x + 1) × width/2`, `y_screen = (1 - ndc.y) × height/2` (Y is flipped).

5. **Rasterization**: For each triangle, a bounding box is computed and each pixel within it is tested using edge functions. Pixels inside all three edges are shaded.

6. **Perspective-Correct Interpolation**: Vertex attributes are interpolated using `1/w` weighting:
   ```
   attr = (Σ bᵢ × attrᵢ / wᵢ) / (Σ bᵢ / wᵢ)
   ```
   This prevents warping of textures and normals under perspective projection.

7. **Z-Buffer Test**: Each fragment's NDC z-value is compared against the z-buffer. Closer fragments (lower z) overwrite farther ones.

8. **Fragment Shader**: Per-pixel lighting (Phong) or interpolated colour (Gouraud) is computed and written to the framebuffer.

### Shading Models

| Shader | Lighting | Per-Vertex | Per-Pixel | Normals |
|--------|----------|------------|-----------|---------|
| Flat | At face centroid | ✗ | Same for all fragments | Face normal |
| Gouraud | At each vertex | ✓ | Colour interpolated | Vertex normals |
| Phong | At each pixel | ✗ | ✓ | Interpolated normals |

### Coordinate System

- Right-handed (OpenGL convention)
- Camera looks down -Z
- NDC: x∈[-1,1] right, y∈[-1,1] up, z∈[-1,1] (near=-1, far=+1)
- Screen: x∈[0,width] right, y∈[0,height] down (Y flipped)

## Installation

```bash
cd soft-rasterizer
pip install -e .
```

## Usage

### Python API

```python
from soft_rasterizer import (Renderer, Scene, Camera, Light, Object3D,
                              Vec3, PhongShader, PhongMaterial, CheckerTexture)
from soft_rasterizer.primitives import make_cube

# Create a scene with lights
scene = Scene()
scene.lights.append(Light.directional(Vec3(-0.5, -1, -0.3), Vec3(1, 1, 0.9), 0.8))
scene.lights.append(Light.point(Vec3(5, 5, 5), Vec3(0.4, 0.4, 0.6), 0.5))

# Camera
camera = Camera(position=Vec3(3, 2, 4), target=Vec3(0, 0, 0), fov=60)

# Create a textured cube
cube = make_cube(size=2.0)
cube.texture = CheckerTexture(squares=4)
material = PhongMaterial(
    diffuse=Vec3(0.9, 0.7, 0.5),
    specular=Vec3(0.9, 0.9, 0.9),
    shininess=64,
    ambient=Vec3(0.2, 0.2, 0.2),
)
obj = Object3D(cube, shader=PhongShader(material=material),
               rotation=Vec3(0.3, 0.8, 0))
scene.add(obj)

# Render and save
renderer = Renderer(640, 480)
renderer.render(scene, camera)
renderer.save_ppm("output.ppm")
```

### Loading OBJ Files

```python
from soft_rasterizer import OBJLoader

mesh = OBJLoader.load("model.obj")
mesh.compute_smooth_normals()  # if normals aren't in the file
obj = Object3D(mesh, shader=PhongShader())
```

### CLI

```bash
# Render a Phong-shaded sphere
soft-rasterizer render -o sphere.ppm -p sphere -s phong --width 640 --height 480

# Render a textured cube from a specific angle
soft-rasterizer render -o cube.ppm -p cube -s phong --texture checker \
    --angle 0.8 --distance 5 --height 2 --rotation 0.5

# Render an OBJ file
soft-rasterizer render -o model.ppm --obj model.obj -s gouraud

# Normal visualization (debugging)
soft-rasterizer render -o normals.ppm -p torus -s normal

# ASCII preview
soft-rasterizer render -o /dev/null -p cube -s phong --ascii

# List available primitives and shaders
soft-rasterizer list
```

### Available Primitives

| Primitive | Description |
|-----------|-------------|
| `cube` | Unit cube with per-face normals |
| `sphere` | UV sphere (configurable segments/rings) |
| `plane` | Flat plane on Y=0 (configurable divisions) |
| `cylinder` | Cylinder along Y axis with caps |
| `torus` | Torus (donut) with configurable major/minor radii |
| `tetrahedron` | Regular tetrahedron |
| `octahedron` | Regular octahedron |

## Project Structure

```
soft-rasterizer/
├── soft_rasterizer/
│   ├── __init__.py       # Package exports
│   ├── math3d.py         # Vec2, Vec3, Vec4, Mat4, barycentric
│   ├── texture.py        # Texture, CheckerTexture (nearest + bilinear)
│   ├── mesh.py           # Vertex, Triangle, Mesh, OBJLoader
│   ├── rasterizer.py     # Renderer, Framebuffer, clipping, z-buffer
│   ├── shaders.py        # Flat, Gouraud, Phong, Wireframe, Normal, Depth
│   ├── scene.py          # Scene, Camera, Light, Object3D
│   ├── primitives.py     # Cube, sphere, plane, cylinder, torus, etc.
│   └── cli.py            # Command-line interface
├── tests/
│   └── test_rasterizer.py
├── pyproject.toml
└── README.md
```

## Technical Details

- **Pure Python**: No dependencies beyond the standard library
- **Performance**: Optimized inner loop with edge function precomputation; a 320×240 render of a sphere takes ~1-2 seconds
- **Numerical stability**: Degenerate triangles (zero area) are detected and skipped; `1/w = 0` cases are handled gracefully
- **Right-handed coordinates**: Standard OpenGL convention throughout

## License

MIT