import json
from cli import main


def test_cli_writes_obj_and_reports_stats(tmp_path, capsys):
    source = tmp_path / "voxels.json"
    target = tmp_path / "mesh.obj"
    source.write_text(json.dumps({"voxels": [[0, 0, 0]]}), encoding="utf-8")
    assert main([str(source), "--output", str(target), "--stats"]) == 0
    assert target.read_text(encoding="utf-8").count("\nf ") == 6
    assert "voxels=1" in capsys.readouterr().err


def test_cli_rejects_wrong_document_shape(tmp_path, capsys):
    source = tmp_path / "bad.json"
    source.write_text("[]", encoding="utf-8")
    assert main([str(source)]) == 2
    assert "voxels" in capsys.readouterr().err
