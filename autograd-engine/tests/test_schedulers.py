"""Tests for learning-rate schedulers."""

import math
import pytest
from autograd_engine.schedulers import (
    StepLR, ExponentialLR, CosineAnnealingLR, LinearLR,
    WarmupLR, ReduceOnPlateauLR, get_scheduler,
)


class TestStepLR:
    def test_basic(self):
        s = StepLR(0.1, step_size=10, gamma=0.5)
        assert s.get_lr(0) == 0.1
        assert s.get_lr(9) == 0.1
        assert s.get_lr(10) == 0.05
        assert s.get_lr(20) == 0.025

    def test_invalid_step_size(self):
        with pytest.raises(ValueError):
            StepLR(0.1, step_size=0)


class TestExponentialLR:
    def test_basic(self):
        s = ExponentialLR(0.1, gamma=0.99)
        assert abs(s.get_lr(0) - 0.1) < 1e-9
        assert abs(s.get_lr(1) - 0.099) < 1e-6
        assert abs(s.get_lr(10) - 0.1 * 0.99 ** 10) < 1e-9


class TestCosineAnnealingLR:
    def test_start(self):
        s = CosineAnnealingLR(0.1, T_max=100, eta_min=0.001)
        assert abs(s.get_lr(0) - 0.1) < 1e-6

    def test_midpoint(self):
        s = CosineAnnealingLR(0.1, T_max=100, eta_min=0.001)
        mid = s.get_lr(50)
        # At midpoint, should be roughly (0.1 + 0.001) / 2
        assert abs(mid - (0.1 + 0.001) / 2) < 1e-4

    def test_end(self):
        s = CosineAnnealingLR(0.1, T_max=100, eta_min=0.001)
        assert abs(s.get_lr(100) - 0.001) < 1e-9

    def test_beyond_T_max(self):
        s = CosineAnnealingLR(0.1, T_max=100, eta_min=0.001)
        assert s.get_lr(200) == 0.001


class TestLinearLR:
    def test_start(self):
        s = LinearLR(0.1, 0.01, total_epochs=100)
        assert abs(s.get_lr(0) - 0.1) < 1e-9

    def test_end(self):
        s = LinearLR(0.1, 0.01, total_epochs=100)
        assert abs(s.get_lr(100) - 0.01) < 1e-9

    def test_midpoint(self):
        s = LinearLR(0.1, 0.01, total_epochs=100)
        mid = s.get_lr(50)
        assert abs(mid - 0.055) < 1e-6


class TestWarmupLR:
    def test_warmup_phase(self):
        base = CosineAnnealingLR(0.1, 100)
        s = WarmupLR(base, warmup_epochs=5, warmup_start_lr=0.0)
        # epoch 0: warmup_start + (base_lr - start) * 1/5
        lr0 = s.get_lr(0)
        assert lr0 > 0.0
        assert lr0 < 0.1
        # epoch 5: should be base scheduler at epoch 0
        assert abs(s.get_lr(5) - base.get_lr(0)) < 1e-9


class TestReduceOnPlateauLR:
    def test_reduces_when_not_improving(self):
        s = ReduceOnPlateauLR(0.1, factor=0.5, patience=3, mode="min")
        s.step_metric(1.0)
        s.step_metric(1.0)
        s.step_metric(1.0)
        s.step_metric(1.0)  # patience exceeded
        assert s.get_lr(0) == 0.05

    def test_no_reduce_when_improving(self):
        s = ReduceOnPlateauLR(0.1, factor=0.5, patience=3, mode="min")
        for v in [1.0, 0.9, 0.8, 0.7]:
            s.step_metric(v)
        assert s.get_lr(0) == 0.1

    def test_min_lr_floor(self):
        s = ReduceOnPlateauLR(0.01, factor=0.1, patience=1, min_lr=0.005, mode="min")
        s.step_metric(1.0)
        s.step_metric(1.0)
        assert s.get_lr(0) == 0.005  # floored at min_lr


class TestGetScheduler:
    def test_step(self):
        s = get_scheduler("step", base_lr=0.1, step_size=10, gamma=0.5)
        assert isinstance(s, StepLR)
        assert s.get_lr(0) == 0.1

    def test_cosine(self):
        s = get_scheduler("cosine", base_lr=0.1, T_max=100)
        assert isinstance(s, CosineAnnealingLR)

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown scheduler"):
            get_scheduler("bogus")