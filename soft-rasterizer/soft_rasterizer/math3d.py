"""3D math primitives: vectors, matrices, and geometric helpers.

All operations are pure-Python (no NumPy) for educational clarity.
Matrices are row-major and use the convention ``M @ v`` where ``v`` is a
column vector (stored as a :class:`Vec4`).
"""

from __future__ import annotations

import math
from typing import Iterable

__all__ = ["Vec2", "Vec3", "Vec4", "Mat4"]


class Vec2:
    """A 2-component vector."""

    __slots__ = ("x", "y")

    def __init__(self, x: float = 0.0, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)

    # --- arithmetic -------------------------------------------------
    def __add__(self, o: "Vec2") -> "Vec2":
        return Vec2(self.x + o.x, self.y + o.y)

    def __sub__(self, o: "Vec2") -> "Vec2":
        return Vec2(self.x - o.x, self.y - o.y)

    def __mul__(self, s: float) -> "Vec2":
        return Vec2(self.x * s, self.y * s)

    __rmul__ = __mul__

    def __truediv__(self, s: float) -> "Vec2":
        inv = 1.0 / s
        return Vec2(self.x * inv, self.y * inv)

    def __neg__(self) -> "Vec2":
        return Vec2(-self.x, -self.y)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Vec2):
            return NotImplemented
        return self.x == o.x and self.y == o.y

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def dot(self, o: "Vec2") -> float:
        return self.x * o.x + self.y * o.y

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y)

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y

    def normalized(self) -> "Vec2":
        ln = self.length()
        if ln == 0.0:
            return Vec2(0.0, 0.0)
        return self / ln

    def lerp(self, o: "Vec2", t: float) -> "Vec2":
        return Vec2(self.x + (o.x - self.x) * t, self.y + (o.y - self.y) * t)

    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)

    def __iter__(self):
        yield self.x
        yield self.y

    def __repr__(self) -> str:
        return f"Vec2({self.x:.4f}, {self.y:.4f})"


class Vec3:
    """A 3-component vector."""

    __slots__ = ("x", "y", "z")

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    # --- arithmetic -------------------------------------------------
    def __add__(self, o: "Vec3") -> "Vec3":
        return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)

    def __sub__(self, o: "Vec3") -> "Vec3":
        return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)

    def __mul__(self, s: float) -> "Vec3":
        return Vec3(self.x * s, self.y * s, self.z * s)

    __rmul__ = __mul__

    def __truediv__(self, s: float) -> "Vec3":
        inv = 1.0 / s
        return Vec3(self.x * inv, self.y * inv, self.z * inv)

    def __neg__(self) -> "Vec3":
        return Vec3(-self.x, -self.y, -self.z)

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Vec3):
            return NotImplemented
        return self.x == o.x and self.y == o.y and self.z == o.z

    def __hash__(self) -> int:
        return hash((self.x, self.y, self.z))

    def dot(self, o: "Vec3") -> float:
        return self.x * o.x + self.y * o.y + self.z * o.z

    def cross(self, o: "Vec3") -> "Vec3":
        return Vec3(
            self.y * o.z - self.z * o.y,
            self.z * o.x - self.x * o.z,
            self.x * o.y - self.y * o.x,
        )

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y + self.z * self.z

    def normalized(self) -> "Vec3":
        ln = self.length()
        if ln == 0.0:
            return Vec3(0.0, 0.0, 0.0)
        return self / ln

    def lerp(self, o: "Vec3", t: float) -> "Vec3":
        return Vec3(
            self.x + (o.x - self.x) * t,
            self.y + (o.y - self.y) * t,
            self.z + (o.z - self.z) * t,
        )

    def reflect(self, n: "Vec3") -> "Vec3":
        """Reflect ``self`` about a surface with normal ``n``."""
        d = self.dot(n)
        return self - n * (2.0 * d)

    def component_mul(self, o: "Vec3") -> "Vec3":
        """Hadamard (component-wise) product — useful for colour mixing."""
        return Vec3(self.x * o.x, self.y * o.y, self.z * o.z)

    def clamp(self, lo: float = 0.0, hi: float = 1.0) -> "Vec3":
        return Vec3(
            max(lo, min(hi, self.x)),
            max(lo, min(hi, self.y)),
            max(lo, min(hi, self.z)),
        )

    def to_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z

    def __repr__(self) -> str:
        return f"Vec3({self.x:.4f}, {self.y:.4f}, {self.z:.4f})"


class Vec4:
    """A 4-component vector (homogeneous coordinates)."""

    __slots__ = ("x", "y", "z", "w")

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0, w: float = 1.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)
        self.w = float(w)

    def __add__(self, o: "Vec4") -> "Vec4":
        return Vec4(self.x + o.x, self.y + o.y, self.z + o.z, self.w + o.w)

    def __sub__(self, o: "Vec4") -> "Vec4":
        return Vec4(self.x - o.x, self.y - o.y, self.z - o.z, self.w - o.w)

    def __mul__(self, s: float) -> "Vec4":
        return Vec4(self.x * s, self.y * s, self.z * s, self.w * s)

    __rmul__ = __mul__

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Vec4):
            return NotImplemented
        return (self.x == o.x and self.y == o.y
                and self.z == o.z and self.w == o.w)

    def to_vec3(self) -> Vec3:
        """Perspective divide — return the Vec3 after dividing by w."""
        if self.w == 0.0 or self.w == 1.0:
            return Vec3(self.x, self.y, self.z)
        inv = 1.0 / self.w
        return Vec3(self.x * inv, self.y * inv, self.z * inv)

    def xyz(self) -> Vec3:
        """Return xyz as a Vec3 (ignoring w, no divide)."""
        return Vec3(self.x, self.y, self.z)

    def __repr__(self) -> str:
        return f"Vec4({self.x:.4f}, {self.y:.4f}, {self.z:.4f}, {self.w:.4f})"


class Mat4:
    """A 4×4 matrix stored row-major as a flat 16-element list."""

    __slots__ = ("m",)

    def __init__(self, values: Iterable[float] | None = None):
        if values is None:
            self.m = [0.0] * 16
        else:
            vals = list(values)
            if len(vals) != 16:
                raise ValueError(f"Mat4 needs exactly 16 values, got {len(vals)}")
            self.m = [float(v) for v in vals]

    # --- helpers ----------------------------------------------------
    @staticmethod
    def identity() -> "Mat4":
        return Mat4([
            1, 0, 0, 0,
            0, 1, 0, 0,
            0, 0, 1, 0,
            0, 0, 0, 1,
        ])

    @staticmethod
    def translation(x: float, y: float, z: float) -> "Mat4":
        return Mat4([
            1, 0, 0, x,
            0, 1, 0, y,
            0, 0, 1, z,
            0, 0, 0, 1,
        ])

    @staticmethod
    def scaling(x: float, y: float, z: float) -> "Mat4":
        return Mat4([
            x, 0, 0, 0,
            0, y, 0, 0,
            0, 0, z, 0,
            0, 0, 0, 1,
        ])

    @staticmethod
    def rotation_x(angle: float) -> "Mat4":
        c, s = math.cos(angle), math.sin(angle)
        return Mat4([
            1, 0,  0, 0,
            0, c, -s, 0,
            0, s,  c, 0,
            0, 0,  0, 1,
        ])

    @staticmethod
    def rotation_y(angle: float) -> "Mat4":
        c, s = math.cos(angle), math.sin(angle)
        return Mat4([
             c, 0, s, 0,
             0, 1, 0, 0,
            -s, 0, c, 0,
             0, 0, 0, 1,
        ])

    @staticmethod
    def rotation_z(angle: float) -> "Mat4":
        c, s = math.cos(angle), math.sin(angle)
        return Mat4([
            c, -s, 0, 0,
            s,  c, 0, 0,
            0,  0, 1, 0,
            0,  0, 0, 1,
        ])

    @staticmethod
    def perspective(fovy: float, aspect: float, near: float, far: float) -> "Mat4":
        """Right-handed perspective projection matrix (OpenGL convention).

        Maps the view frustum to the clip-space cube [-1, 1]³.  After the
        perspective divide, visible geometry has xyz in [-1, 1] and
        ``z = -1`` at the near plane, ``z = 1`` at the far plane.
        """
        if near <= 0 or far <= 0 or near >= far:
            raise ValueError(
                f"Invalid near/far: near={near}, far={far} "
                "(need 0 < near < far)")
        if aspect == 0:
            raise ValueError("aspect must be non-zero")
        f = 1.0 / math.tan(fovy / 2.0)
        return Mat4([
            f / aspect, 0, 0, 0,
            0, f, 0, 0,
            0, 0, (far + near) / (near - far), (2 * far * near) / (near - far),
            0, 0, -1, 0,
        ])

    @staticmethod
    def look_at(eye: Vec3, target: Vec3, up: Vec3) -> "Mat4":
        """Right-handed look-at (view) matrix.

        ``eye`` is the camera position, ``target`` is the point being
        looked at, and ``up`` is the world up direction (typically
        ``(0, 1, 0)``).
        """
        f = (target - eye).normalized()    # forward
        s = f.cross(up).normalized()        # right
        u = s.cross(f)                      # true up
        return Mat4([
            s.x,  s.y,  s.z, -s.dot(eye),
            u.x,  u.y,  u.z, -u.dot(eye),
           -f.x, -f.y, -f.z,  f.dot(eye),
            0,    0,    0,    1,
        ])

    # --- operators --------------------------------------------------
    def __matmul__(self, o: "Mat4") -> "Mat4":
        return self.__mul__(o)

    def __mul__(self, o: "Mat4") -> "Mat4":
        a, b = self.m, o.m
        return Mat4([
            a[0]*b[0]+a[1]*b[4]+a[2]*b[8]+a[3]*b[12],
            a[0]*b[1]+a[1]*b[5]+a[2]*b[9]+a[3]*b[13],
            a[0]*b[2]+a[1]*b[6]+a[2]*b[10]+a[3]*b[14],
            a[0]*b[3]+a[1]*b[7]+a[2]*b[11]+a[3]*b[15],
            a[4]*b[0]+a[5]*b[4]+a[6]*b[8]+a[7]*b[12],
            a[4]*b[1]+a[5]*b[5]+a[6]*b[9]+a[7]*b[13],
            a[4]*b[2]+a[5]*b[6]+a[6]*b[10]+a[7]*b[14],
            a[4]*b[3]+a[5]*b[7]+a[6]*b[11]+a[7]*b[15],
            a[8]*b[0]+a[9]*b[4]+a[10]*b[8]+a[11]*b[12],
            a[8]*b[1]+a[9]*b[5]+a[10]*b[9]+a[11]*b[13],
            a[8]*b[2]+a[9]*b[6]+a[10]*b[10]+a[11]*b[14],
            a[8]*b[3]+a[9]*b[7]+a[10]*b[11]+a[11]*b[15],
            a[12]*b[0]+a[13]*b[4]+a[14]*b[8]+a[15]*b[12],
            a[12]*b[1]+a[13]*b[5]+a[14]*b[9]+a[15]*b[13],
            a[12]*b[2]+a[13]*b[6]+a[14]*b[10]+a[15]*b[14],
            a[12]*b[3]+a[13]*b[7]+a[14]*b[11]+a[15]*b[15],
        ])

    def transform(self, v: Vec4) -> Vec4:
        """Multiply this matrix by a column vector ``v``."""
        a = self.m
        return Vec4(
            a[0]*v.x + a[1]*v.y + a[2]*v.z + a[3]*v.w,
            a[4]*v.x + a[5]*v.y + a[6]*v.z + a[7]*v.w,
            a[8]*v.x + a[9]*v.y + a[10]*v.z + a[11]*v.w,
            a[12]*v.x + a[13]*v.y + a[14]*v.z + a[15]*v.w,
        )

    def transform_point(self, p: Vec3) -> Vec3:
        """Transform a point (w=1) and return the Vec3 after perspective divide."""
        v = self.transform(Vec4(p.x, p.y, p.z, 1.0))
        return v.to_vec3()

    def transform_direction(self, d: Vec3) -> Vec3:
        """Transform a direction (w=0) — no translation, no divide."""
        a = self.m
        return Vec3(
            a[0]*d.x + a[1]*d.y + a[2]*d.z,
            a[4]*d.x + a[5]*d.y + a[6]*d.z,
            a[8]*d.x + a[9]*d.y + a[10]*d.z,
        )

    def transposed(self) -> "Mat4":
        return Mat4([
            self.m[0], self.m[4], self.m[8],  self.m[12],
            self.m[1], self.m[5], self.m[9],  self.m[13],
            self.m[2], self.m[6], self.m[10], self.m[14],
            self.m[3], self.m[7], self.m[11], self.m[15],
        ])

    def inverse(self) -> "Mat4":
        """General 4×4 inverse via cofactor expansion (Gauss-Jordan)."""
        a = list(self.m)
        # Augment with identity
        inv = [0.0] * 16
        for i in range(4):
            inv[i * 4 + i] = 1.0

        # Forward elimination with partial pivoting
        for col in range(4):
            # Find pivot
            pivot_row = col
            max_val = abs(a[col * 4 + col])
            for row in range(col + 1, 4):
                val = abs(a[row * 4 + col])
                if val > max_val:
                    max_val = val
                    pivot_row = row
            if max_val < 1e-12:
                raise ValueError("Matrix is singular (non-invertible)")

            # Swap rows in both a and inv
            if pivot_row != col:
                for k in range(4):
                    a[col * 4 + k], a[pivot_row * 4 + k] = a[pivot_row * 4 + k], a[col * 4 + k]
                    inv[col * 4 + k], inv[pivot_row * 4 + k] = inv[pivot_row * 4 + k], inv[col * 4 + k]

            # Normalize pivot row
            pivot = a[col * 4 + col]
            inv_p = 1.0 / pivot
            for k in range(4):
                a[col * 4 + k] *= inv_p
                inv[col * 4 + k] *= inv_p

            # Eliminate column in other rows
            for row in range(4):
                if row == col:
                    continue
                factor = a[row * 4 + col]
                if factor == 0.0:
                    continue
                for k in range(4):
                    a[row * 4 + k] -= factor * a[col * 4 + k]
                    inv[row * 4 + k] -= factor * inv[col * 4 + k]

        return Mat4(inv)

    def normal_matrix(self) -> "Mat4":
        """Return the upper-3×3 inverse-transpose as a Mat4 (for normals)."""
        return self.inverse().transposed()

    def __getitem__(self, idx: int) -> float:
        return self.m[idx]

    def __eq__(self, o: object) -> bool:
        if not isinstance(o, Mat4):
            return NotImplemented
        return self.m == o.m

    def __repr__(self) -> str:
        rows = [self.m[i*4:i*4+4] for i in range(4)]
        return "Mat4(\n  " + "\n  ".join("  ".join(f"{v:8.3f}" for v in r) for r in rows) + "\n)"


# ---------------------------------------------------------------------------
# Geometric helpers
# ---------------------------------------------------------------------------

def barycentric(px: float, py: float,
                ax: float, ay: float,
                bx: float, by: float,
                cx: float, cy: float) -> tuple[float, float, float]:
    """Compute barycentric coordinates of point (px, py) in triangle ABC.

    Returns (u, v, w) where u + v + w = 1 and the point = u*A + v*B + w*C.
    Returns (0, 0, 0) for degenerate triangles.
    """
    denom = (by - cy) * (ax - cx) + (cy - ay) * (bx - cx)
    if abs(denom) < 1e-12:
        return (0.0, 0.0, 0.0)
    inv_denom = 1.0 / denom
    u = ((by - cy) * (px - cx) + (cy - ay) * (py - cy)) * inv_denom
    v = ((cy - ay) * (px - cx) + (ay - by) * (py - cy)) * inv_denom
    w = 1.0 - u - v
    return (u, v, w)