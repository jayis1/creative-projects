from pathlib import Path

import pytest

from neural_net_lab.data import load_dataset, train_test_split


def test_csv_loader_uses_named_target(tmp_path: Path):
    path = tmp_path / "samples.csv"
    path.write_text("x1,x2,label\n1,2,0\n3,4,1\n", encoding="utf8")
    assert load_dataset(path, "label") == ([[1.0, 2.0], [3.0, 4.0]], [[0.0], [1.0]])


def test_jsonl_loader_supports_vector_targets(tmp_path: Path):
    path = tmp_path / "samples.jsonl"
    path.write_text('{"features": [1, 2], "target": [1, 0]}\n', encoding="utf8")
    assert load_dataset(path) == ([[1.0, 2.0]], [[1.0, 0.0]])


def test_split_is_aligned_and_reproducible():
    xs = [[float(i)] for i in range(10)]
    ys = [[float(i % 2)] for i in range(10)]
    first = train_test_split(xs, ys, test_size=0.3, seed=8)
    assert first == train_test_split(xs, ys, test_size=0.3, seed=8)
    assert len(first[0][0]) == len(first[0][1])
    assert len(first[1][0]) == len(first[1][1])
    assert len(first[0][0]) + len(first[1][0]) == 10


def test_loader_rejects_bad_target(tmp_path: Path):
    path = tmp_path / "samples.csv"
    path.write_text("x,label\nnot-a-number,1\n", encoding="utf8")
    with pytest.raises(ValueError, match="numeric"):
        load_dataset(path)
