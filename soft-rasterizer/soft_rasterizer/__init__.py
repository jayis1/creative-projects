"""
soft-rasterizer: A from-scratch software 3D rasterizer.

Pure-Python software rendering pipeline with vertex transformation,
near-plane clipping, perspective-correct interpolation, z-buffering,
texture mapping, Phong/Gouraud/Toon/Crosshatch shading, scene
configuration via JSON, multi-format image output (PPM/BMP),
post-processing effects, and turntable animation.

    >>> from soft_rasterizer import Renderer, Scene, Mesh, Camera, Light
"""

from .math3d import Vec2, Vec3, Vec4, Mat4
from .texture import Texture, CheckerTexture, MipTexture
from .mesh import Mesh, Triangle, Vertex, OBJLoader
from .rasterizer import (Renderer, Framebuffer, DISCARD,
                         post_grayscale, post_edge_detect, post_vignette)
from .shaders import (
    FlatShader,
    GouraudShader,
    PhongShader,
    PhongMaterial,
    WireframeShader,
    NormalShader,
    DepthShader,
    ToonShader,
    FogShader,
    CrosshatchShader,
    MatcapShader,
)
from .scene import Scene, Camera, Light, Object3D
from .config import SceneConfig
from .animation import AnimationBuilder

__version__ = "2.0.0"

__all__ = [
    "Vec2", "Vec3", "Vec4", "Mat4",
    "Texture", "CheckerTexture", "MipTexture",
    "Mesh", "Triangle", "Vertex", "OBJLoader",
    "Renderer", "Framebuffer", "DISCARD",
    "post_grayscale", "post_edge_detect", "post_vignette",
    "FlatShader", "GouraudShader", "PhongShader", "PhongMaterial",
    "WireframeShader", "NormalShader", "DepthShader",
    "ToonShader", "FogShader", "CrosshatchShader", "MatcapShader",
    "Scene", "Camera", "Light", "Object3D",
    "SceneConfig", "AnimationBuilder",
]