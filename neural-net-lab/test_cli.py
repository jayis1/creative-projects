from pathlib import Path

import pytest

from neural_net_lab import MLP
from neural_net_lab.cli import main


def test_evaluate_loaded_model_on_dataset(tmp_path: Path, capsys):
    model = MLP([2, 1], ["linear"], seed=2)
    model.save(tmp_path / "model.json")
    dataset = tmp_path / "samples.csv"
    dataset.write_text("x1,x2,label\n0,0,0\n1,1,1\n", encoding="utf8")

    assert main([
        "--load", str(tmp_path / "model.json"),
        "--evaluate", str(dataset),
        "--target-column", "label",
    ]) == 0
    assert "samples: 2" in capsys.readouterr().out


def test_load_rejects_non_xor_inspection(tmp_path: Path):
    model_path = tmp_path / "model.json"
    MLP([3, 1], ["sigmoid"], seed=2).save(model_path)
    with pytest.raises(ValueError, match="two input features"):
        main(["--load", str(model_path)])


def test_evaluate_rejects_dataset_width_mismatch(tmp_path: Path):
    model_path = tmp_path / "model.json"
    MLP([2, 1], ["sigmoid"], seed=2).save(model_path)
    dataset = tmp_path / "samples.csv"
    dataset.write_text("x,label\n1,1\n", encoding="utf8")
    with pytest.raises(ValueError, match="widths"):
        main(["--load", str(model_path), "--evaluate", str(dataset)])
