"""Additional feature coverage for softmax classification and configuration."""
import json
from pathlib import Path
from neural_net_lab import MLP, Adam
from neural_net_lab.config import load_config

def test_softmax_cross_entropy_learns_or_logic():
    x = [[1, 0], [0, 1], [2, 0], [0, 2]]; y = [[1, 0], [0, 1], [1, 0], [0, 1]]
    net = MLP([2, 4, 2], ["tanh", "softmax"], seed=4)
    before = net.loss(x, y, "cross_entropy")
    net.train(x, y, epochs=350, lr=.08, batch_size=4, optimizer=Adam(), loss_name="cross_entropy")
    assert net.loss(x, y, "cross_entropy") < before
    assert net.accuracy(x, y) == 1.0
    assert abs(sum(net.predict([1, 0])) - 1) < 1e-9

def test_toml_configuration(tmp_path: Path):
    p = tmp_path / "experiment.toml"
    p.write_text('sizes=[2,2,1]\noptimizer="sgd"\n', encoding="utf8")
    c = load_config(p)
    assert c["sizes"] == [2, 2, 1] and c["optimizer"] == "sgd" and c["epochs"] == 2000

def test_load_reports_bad_json(tmp_path: Path):
    p = tmp_path / "bad.json"; p.write_text("not json", encoding="utf8")
    try: MLP.load(p)
    except ValueError as e: assert "cannot read model" in str(e)
    else: raise AssertionError("malformed JSON accepted")


def test_gradient_check_validates_backpropagation():
    x = [[0.2, -0.4], [0.7, 0.1]]
    y = [[1.0], [0.0]]
    net = MLP([2, 3, 1], ["tanh", "sigmoid"], seed=9)
    assert net.gradient_check(x[0], y[0], loss_name="bce") < 1e-5
    assert net.gradient_check(x[0], y[0], loss_name="mse") < 1e-5
