"""
soft-rasterizer: A from-scratch software 3D rasterizer.

Pure-Python software rendering pipeline with vertex transformation,
near-plane clipping, perspective-correct interpolation, z-buffering,
texture mapping, and Gouraud/Phong shading.

    >>> from soft_rasterizer import Renderer, Scene, Mesh, Camera, Light
"""

from .math3d import Vec2, Vec3, Vec4, Mat4
from .texture import Texture, CheckerTexture, MipTexture
from .mesh import Mesh, Triangle, OBJLoader
from .rasterizer import Renderer, Framebuffer
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
)
from .scene import Scene, Camera, Light, Object3D

__version__ = "1.0.0"

__all__ = [
    "Vec2", "Vec3", "Vec4", "Mat4",
    "Texture", "CheckerTexture", "MipTexture",
    "Mesh", "Triangle", "OBJLoader",
    "Renderer", "Framebuffer",
    "FlatShader", "GouraudShader", "PhongShader", "PhongMaterial",
    "WireframeShader", "NormalShader", "DepthShader",
    "ToonShader", "FogShader",
    "Scene", "Camera", "Light", "Object3D",
]