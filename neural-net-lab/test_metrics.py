import json
from pathlib import Path

import pytest

from neural_net_lab import MLP
from neural_net_lab.cli import main


def test_binary_classification_report_has_confusion_matrix():
    net = MLP([1, 1], ["sigmoid"], seed=1)
    net.layers[0].w = [[10.0]]
    net.layers[0].b = [-5.0]
    report = net.classification_report([[0.0], [1.0], [0.0], [1.0]], [[0.0], [1.0], [0.0], [1.0]])
    assert report["confusion_matrix"] == [[2, 0], [0, 2]]
    assert report["macro_f1"] == pytest.approx(1.0)


def test_cli_report_is_json(tmp_path: Path, capsys):
    model = MLP([1, 1], ["sigmoid"], seed=1)
    model.layers[0].w = [[10.0]]
    model.layers[0].b = [-5.0]
    model_path = tmp_path / "model.json"
    model.save(model_path)
    data_path = tmp_path / "data.csv"
    data_path.write_text("x,label\n0,0\n1,1\n", encoding="utf8")
    assert main(["--load", str(model_path), "--evaluate", str(data_path), "--report"]) == 0
    lines = capsys.readouterr().out.splitlines()
    report = json.loads(lines[-1])
    assert report["confusion_matrix"] == [[1, 0], [0, 1]]


def test_report_rejects_wrong_target_width():
    net = MLP([1, 2], ["softmax"], seed=1)
    with pytest.raises(ValueError, match="target width"):
        net.classification_report([[0.0]], [[1.0]])
