"""Tests for the CLI interface."""

import os
import subprocess
import sys
import pytest

from mcengine.cli import main, build_parser
from tests.conftest import temp_file, cleanup


class TestCLIParser:
    def test_build_parser(self):
        parser = build_parser()
        assert parser.prog == "mcengine"

    def test_no_command_prints_help(self, capsys):
        with pytest.raises(SystemExit):
            main([])
        captured = capsys.readouterr()
        assert "mcengine" in captured.out


class TestRenderCommand:
    def test_render_sphere(self, capsys):
        path = temp_file(".obj")
        try:
            main(["render", "-s", "sphere", "--res", "8", "-o", path])
            assert os.path.exists(path)
            captured = capsys.readouterr()
            assert "Running MC" in captured.out
            assert "Exported" in captured.out
        finally:
            cleanup(path)

    def test_render_torus(self, capsys):
        path = temp_file(".stl")
        try:
            main(["render", "-s", "torus", "--res", "12", "-o", path, "-f", "stl-binary"])
            assert os.path.exists(path)
        finally:
            cleanup(path)

    def test_render_with_preview(self, capsys):
        path = temp_file(".obj")
        try:
            main(["render", "-s", "sphere", "--res", "8", "-o", path, "--preview"])
            captured = capsys.readouterr()
            assert "ASCII preview" in captured.out
        finally:
            cleanup(path)

    def test_render_dc_algorithm(self, capsys):
        path = temp_file(".obj")
        try:
            main(["render", "-a", "dc", "-s", "octahedron", "--res", "8", "-o", path])
            assert os.path.exists(path)
        finally:
            cleanup(path)

    def test_render_with_simplify(self, capsys):
        path = temp_file(".obj")
        try:
            main(["render", "-s", "sphere", "--res", "16", "-o", path, "--simplify", "50"])
            captured = capsys.readouterr()
            assert "Simplifying" in captured.out
        finally:
            cleanup(path)

    def test_render_unknown_sampler(self, capsys):
        path = temp_file(".obj")
        try:
            with pytest.raises(SystemExit):
                main(["render", "-s", "nonexistent", "--res", "8", "-o", path])
        finally:
            cleanup(path)


class TestInfoCommand:
    def test_info_on_obj(self, capsys):
        # First create a file
        path = temp_file(".obj")
        try:
            main(["render", "-s", "sphere", "--res", "8", "-o", path])
            capsys.readouterr()  # clear
            main(["info", "-i", path])
            captured = capsys.readouterr()
            assert "Vertices:" in captured.out
            assert "Faces:" in captured.out
        finally:
            cleanup(path)


class TestListCommands:
    def test_list_samplers(self, capsys):
        main(["list-samplers"])
        captured = capsys.readouterr()
        assert "sphere" in captured.out
        assert "torus" in captured.out

    def test_list_presets(self, capsys):
        main(["list-presets"])
        captured = capsys.readouterr()
        assert "sphere" in captured.out


class TestCompareCommand:
    def test_compare_sphere(self, capsys):
        main(["compare", "-s", "sphere", "--res", "8"])
        captured = capsys.readouterr()
        assert "MarchingCubes" in captured.out
        assert "DualContouring" in captured.out


class TestPresetCommand:
    def test_preset_render(self, capsys):
        path = temp_file(".obj")
        try:
            main(["preset", "sphere", "-o", path])
            assert os.path.exists(path)
        finally:
            cleanup(path)


class TestConvertCommand:
    def test_convert_obj_to_stl(self, capsys):
        obj_path = temp_file(".obj")
        stl_path = temp_file(".stl")
        try:
            main(["render", "-s", "sphere", "--res", "8", "-o", obj_path])
            capsys.readouterr()
            main(["convert", "-i", obj_path, "-o", stl_path])
            assert os.path.exists(stl_path)
        finally:
            cleanup(obj_path)
            cleanup(stl_path)


class TestTransformCommand:
    def test_transform_translate(self, capsys):
        in_path = temp_file(".obj")
        out_path = temp_file(".obj")
        try:
            main(["render", "-s", "sphere", "--res", "8", "-o", in_path])
            capsys.readouterr()
            main(["transform", "-i", in_path, "-o", out_path, "-t", "5,0,0"])
            assert os.path.exists(out_path)
        finally:
            cleanup(in_path)
            cleanup(out_path)


class TestSubdivideCommand:
    def test_subdivide(self, capsys):
        in_path = temp_file(".obj")
        out_path = temp_file(".obj")
        try:
            main(["render", "-s", "sphere", "--res", "8", "-o", in_path])
            capsys.readouterr()
            main(["subdivide", "-i", in_path, "-o", out_path, "-n", "1"])
            captured = capsys.readouterr()
            assert "subdivision" in captured.out
        finally:
            cleanup(in_path)
            cleanup(out_path)


class TestSimplifyCommand:
    def test_simplify(self, capsys):
        in_path = temp_file(".obj")
        out_path = temp_file(".obj")
        try:
            main(["render", "-s", "sphere", "--res", "16", "-o", in_path])
            capsys.readouterr()
            main(["simplify", "-i", in_path, "-o", out_path, "-t", "50"])
            captured = capsys.readouterr()
            assert "Simplified" in captured.out
        finally:
            cleanup(in_path)
            cleanup(out_path)


class TestBatchCommand:
    def test_batch_render(self, capsys):
        config_path = temp_file(".json")
        out_path = temp_file(".obj")
        config = {
            "jobs": [
                {
                    "name": "test_batch",
                    "algorithm": "mc",
                    "sampler": "sphere",
                    "resolution": 8,
                    "bounds": [-1.5, 1.5],
                    "output": out_path,
                }
            ]
        }
        import json
        with open(config_path, "w") as f:
            json.dump(config, f)
        try:
            main(["batch", "-c", config_path])
            captured = capsys.readouterr()
            assert "Completed" in captured.out
            assert "test_batch" in captured.out
            assert os.path.exists(out_path)
        finally:
            cleanup(config_path)
            cleanup(out_path)