"""Tests for texture sampling: nearest, bilinear, mipmap, checkerboard."""

import pytest
from soft_rasterizer.math3d import Vec3, Vec2
from soft_rasterizer.texture import Texture, CheckerTexture, MipTexture


class TestTexture:
    def test_construction(self):
        t = Texture(4, 4)
        assert t.width == 4 and t.height == 4
        assert len(t.pixels) == 16

    def test_invalid_dims(self):
        with pytest.raises(ValueError):
            Texture(0, 4)
        with pytest.raises(ValueError):
            Texture(4, -1)

    def test_pixel_mismatch(self):
        with pytest.raises(ValueError):
            Texture(4, 4, [Vec3(1, 1, 1)] * 10)

    def test_sample_nearest(self):
        t = Texture(2, 2, [Vec3(1, 0, 0), Vec3(0, 1, 0),
                           Vec3(0, 0, 1), Vec3(1, 1, 1)])
        c = t.sample_nearest(0.0, 0.0)
        assert c.x == 1.0  # top-left

    def test_sample_bilinear(self):
        t = Texture(2, 2, [Vec3(0, 0, 0), Vec3(1, 0, 0),
                           Vec3(0, 0, 0), Vec3(1, 0, 0)])
        c = t.sample_bilinear(0.5, 0.5)
        # Should be average of all 4 pixels
        assert abs(c.x - 0.5) < 0.1

    def test_clamp_coord(self):
        t = Texture(4, 4)
        # Sampling outside should clamp to edge
        c = t.sample_nearest(-1, -1)
        assert c == t.pixels[0]

    def test_sample_bilinear_clamp(self):
        t = Texture(2, 2, [Vec3(1, 1, 1)] * 4)
        c = t.sample_bilinear(10, 10)
        assert c == Vec3(1, 1, 1)

    def test_downsample(self):
        t = Texture(4, 4, [Vec3(1, 1, 1)] * 16)
        d = t.downsample()
        assert d.width == 2 and d.height == 2

    def test_downsample_1x1(self):
        t = Texture(1, 1, [Vec3(0.5, 0.5, 0.5)])
        d = t.downsample()
        assert d.width == 1 and d.height == 1


class TestCheckerTexture:
    def test_construction(self):
        t = CheckerTexture(squares=4)
        assert t.width > 0 and t.height > 0

    def test_invalid_squares(self):
        with pytest.raises(ValueError):
            CheckerTexture(squares=0)

    def test_custom_colors(self):
        t = CheckerTexture(squares=2, color_a=Vec3(1, 0, 0),
                           color_b=Vec3(0, 0, 1))
        # Sample in the middle of a square
        c = t.sample_nearest(0.1, 0.1)
        assert c.x == 1.0 or c.z == 1.0  # one of the two colours


class TestMipTexture:
    def test_construction(self):
        t = MipTexture(8, 8, [Vec3(0.5, 0.5, 0.5)] * 64)
        assert len(t.levels) >= 4  # 8→4→2→1

    def test_sample_lod0(self):
        t = MipTexture(4, 4, [Vec3(1, 0, 0)] * 16)
        c = t.sample(0.5, 0.5, lod=0)
        assert c.x == 1.0

    def test_sample_high_lod(self):
        t = MipTexture(8, 8, [Vec3(1, 0, 0)] * 64)
        c = t.sample(0.5, 0.5, lod=100)
        # Should use the smallest mipmap level
        assert c.x == 1.0  # all pixels are the same colour