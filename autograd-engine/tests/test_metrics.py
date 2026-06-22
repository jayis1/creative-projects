"""Tests for the metrics module."""

import pytest
from autograd_engine.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report,
    mean_squared_error, root_mean_squared_error,
    mean_absolute_error, r2_score,
)


class TestAccuracy:
    def test_perfect(self):
        assert accuracy_score([1, 0, 1], [1, 0, 1]) == 1.0

    def test_partial(self):
        assert accuracy_score([1, 0, 1, 1], [1, 0, 0, 1]) == 0.75

    def test_empty(self):
        assert accuracy_score([], []) == 0.0

    def test_length_mismatch(self):
        with pytest.raises(ValueError):
            accuracy_score([1], [1, 0])


class TestPrecision:
    def test_perfect(self):
        assert precision_score([1, 1, 0], [1, 1, 0]) == 1.0

    def test_no_true_positives(self):
        assert precision_score([0, 0], [1, 1]) == 0.0


class TestRecall:
    def test_perfect(self):
        assert recall_score([1, 1, 0], [1, 1, 0]) == 1.0

    def test_no_positives(self):
        assert recall_score([0, 0], [0, 0]) == 0.0


class TestF1:
    def test_perfect(self):
        assert f1_score([1, 1, 0], [1, 1, 0]) == 1.0

    def test_no_predictions(self):
        assert f1_score([0, 0], [0, 0]) == 0.0


class TestConfusionMatrix:
    def test_basic(self):
        cm = confusion_matrix([0, 1, 0, 1], [0, 1, 1, 1], n_classes=2)
        assert cm[0][0] == 1  # true 0, pred 0
        assert cm[0][1] == 1  # true 0, pred 1
        assert cm[1][0] == 0  # true 1, pred 0
        assert cm[1][1] == 2  # true 1, pred 1


class TestClassificationReport:
    def test_runs(self):
        report = classification_report([0, 1, 0, 1], [0, 1, 1, 1])
        assert "Precision" in report
        assert "Accuracy" in report


class TestRegressionMetrics:
    def test_mse(self):
        assert abs(mean_squared_error([1, 2, 3], [1, 2, 3]) - 0.0) < 1e-9
        assert abs(mean_squared_error([1, 2], [2, 3]) - 1.0) < 1e-9

    def test_rmse(self):
        assert abs(root_mean_squared_error([1, 2], [2, 3]) - 1.0) < 1e-9

    def test_mae(self):
        assert abs(mean_absolute_error([1, 2], [2, 3]) - 1.0) < 1e-9

    def test_r2_perfect(self):
        assert abs(r2_score([1, 2, 3], [1, 2, 3]) - 1.0) < 1e-9

    def test_r2_negative(self):
        # Bad predictions can give negative R²
        r2 = r2_score([1, 2, 3], [3, 2, 1])
        assert r2 < 0

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            mean_squared_error([], [])