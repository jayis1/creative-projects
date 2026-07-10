"""Tests for extended functions (date/time, financial, information)."""

import math
import pytest
from spreadsheet import Engine
from spreadsheet.cell import CellError, ErrorType


class TestDateFunctions:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_today(self):
        self.engine.set("S", "A1", "=TODAY()")
        self.engine.recalculate()
        val = self.engine.get("S", "A1")
        assert isinstance(val, float)
        assert val > 40000  # should be a reasonable serial date

    def test_now(self):
        self.engine.set("S", "A1", "=NOW()")
        self.engine.recalculate()
        val = self.engine.get("S", "A1")
        assert isinstance(val, float)

    def test_date(self):
        self.engine.set("S", "A1", "=DATE(2024, 1, 1)")
        self.engine.recalculate()
        val = self.engine.get("S", "A1")
        # 2024-01-01 since epoch 1899-12-30 = 45292 days
        assert val == 45292.0

    def test_year(self):
        self.engine.set("S", "A1", "=YEAR(DATE(2024, 6, 15))")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 2024.0

    def test_month(self):
        self.engine.set("S", "A1", "=MONTH(DATE(2024, 6, 15))")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 6.0

    def test_day(self):
        self.engine.set("S", "A1", "=DAY(DATE(2024, 6, 15))")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 15.0

    def test_weekday_default(self):
        # 2024-01-01 is a Monday
        # return_type=1: Sunday=1..Saturday=7, so Monday=2
        self.engine.set("S", "A1", "=WEEKDAY(DATE(2024,1,1), 1)")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 2.0

    def test_weekday_type2(self):
        # return_type=2: Monday=1..Sunday=7
        self.engine.set("S", "A1", "=WEEKDAY(DATE(2024,1,1), 2)")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 1.0

    def test_hour_minute_second(self):
        # Serial 0.5 = noon
        self.engine.set("S", "A1", "=HOUR(0.5)")
        self.engine.set("S", "A2", "=MINUTE(0.5)")
        self.engine.set("S", "A3", "=SECOND(0.5)")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 12.0
        assert self.engine.get("S", "A2") == 0.0
        assert self.engine.get("S", "A3") == 0.0

    def test_date_month_overflow(self):
        self.engine.set("S", "A1", "=DATE(2024, 13, 1)")
        self.engine.recalculate()
        val = self.engine.get("S", "A1")
        assert isinstance(val, float)
        # month=13 -> January 2025


class TestFinancialFunctions:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_pmt(self):
        # $100k loan, 6% annual, 30 years, 360 payments
        # Monthly rate = 0.005, PMT should be ~-599.55
        self.engine.set("S", "A1", "=PMT(0.005, 360, 100000)")
        self.engine.recalculate()
        val = self.engine.get("S", "A1")
        assert val is not None
        assert abs(val - (-599.55)) < 1.0

    def test_pv(self):
        # PV of $1000/month for 12 months at 1%/month
        self.engine.set("S", "A1", "=PV(0.01, 12, -1000)")
        self.engine.recalculate()
        val = self.engine.get("S", "A1")
        assert val is not None
        assert abs(val - 11255.08) < 5.0

    def test_fv(self):
        # FV of $1000/month for 12 months at 1%/month
        self.engine.set("S", "A1", "=FV(0.01, 12, -1000)")
        self.engine.recalculate()
        val = self.engine.get("S", "A1")
        assert val is not None
        assert abs(val - 12682.50) < 5.0

    def test_npv(self):
        self.engine.set("S", "A1", "0")
        self.engine.set("S", "A2", "=NPV(0.1, 100, 200, 300)")
        self.engine.recalculate()
        val = self.engine.get("S", "A2")
        assert val is not None
        # NPV = 100/1.1 + 200/1.21 + 300/1.331
        expected = 100/1.1 + 200/1.21 + 300/1.331
        assert abs(val - expected) < 0.01

    def test_irr(self):
        self.engine.set("S", "A1", "0")
        self.engine.set("S", "A2", "=IRR(-100, 50, 60)")
        self.engine.recalculate()
        val = self.engine.get("S", "A2")
        assert val is not None
        assert not isinstance(val, CellError), f"IRR returned error: {val}"
        # IRR should be around 13%
        assert -1 < val < 2

    def test_sln(self):
        self.engine.set("S", "A1", "=SLN(10000, 1000, 5)")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 1800.0

    def test_syd(self):
        self.engine.set("S", "A1", "=SYD(10000, 1000, 5, 1)")
        self.engine.recalculate()
        # SYD = (10000-1000) * 5 / (5*6/2) = 9000 * 5/15 = 3000
        assert self.engine.get("S", "A1") == 3000.0

    def test_rate(self):
        self.engine.set("S", "A1", "=RATE(360, -599.55, 100000)")
        self.engine.recalculate()
        val = self.engine.get("S", "A1")
        assert val is not None
        assert abs(val - 0.005) < 0.001


class TestInfoFunctions:
    def setup_method(self):
        self.engine = Engine()
        self.engine.add_sheet("S")

    def test_isna(self):
        self.engine.set("S", "A1", "=NA()")
        self.engine.set("S", "B1", "=ISNA(A1)")
        self.engine.recalculate()
        assert self.engine.get("S", "B1") is True

    def test_islogical(self):
        self.engine.set("S", "A1", "TRUE")
        self.engine.set("S", "B1", "=ISLOGICAL(A1)")
        self.engine.recalculate()
        assert self.engine.get("S", "B1") is True

    def test_iserr(self):
        self.engine.set("S", "A1", "=1/0")
        self.engine.set("S", "B1", "=ISERR(A1)")
        self.engine.recalculate()
        assert self.engine.get("S", "B1") is True

    def test_iserr_na(self):
        self.engine.set("S", "A1", "=NA()")
        self.engine.set("S", "B1", "=ISERR(A1)")
        self.engine.recalculate()
        # ISERR should be False for #N/A (only ISNA catches it)
        assert self.engine.get("S", "B1") is False

    def test_isodd(self):
        self.engine.set("S", "A1", "=ISODD(3)")
        self.engine.set("S", "A2", "=ISODD(4)")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") is True
        assert self.engine.get("S", "A2") is False

    def test_iseven(self):
        self.engine.set("S", "A1", "=ISEVEN(3)")
        self.engine.set("S", "A2", "=ISEVEN(4)")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") is False
        assert self.engine.get("S", "A2") is True

    def test_type(self):
        self.engine.set("S", "A1", "=TYPE(42)")
        self.engine.set("S", "A2", "=TYPE(\"hello\")")
        self.engine.set("S", "A3", "=TYPE(TRUE)")
        self.engine.recalculate()
        assert self.engine.get("S", "A1") == 1.0
        assert self.engine.get("S", "A2") == 2.0
        assert self.engine.get("S", "A3") == 4.0


class TestConfig:
    def setup_method(self):
        self.engine = Engine()

    def test_load_yaml_config(self):
        import tempfile
        import os

        yaml_text = """
sheets:
  - name: Test
    cells:
      A1: "10"
      A2: "=A1*2"
named_ranges:
  MyCell: "Test!A1"
options:
  auto_recalc: true
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_text)
            f.flush()
            path = f.name

        try:
            from spreadsheet.config import load_config
            engine = load_config(path)
            assert engine.get("Test", "A1") == 10.0
            assert engine.get("Test", "A2") == 20.0
            assert engine.get_name("MyCell") is not None
        finally:
            os.unlink(path)

    def test_load_json_config(self):
        import tempfile
        import os
        import json

        data = {
            "sheets": [{"name": "J", "cells": {"A1": "42", "A2": "=A1+1"}}],
            "options": {"auto_recalc": True}
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            path = f.name

        try:
            from spreadsheet.config import load_config
            engine = load_config(path)
            assert engine.get("J", "A1") == 42.0
            assert engine.get("J", "A2") == 43.0
        finally:
            os.unlink(path)

    def test_save_config(self):
        import tempfile
        import os

        engine = Engine()
        engine.add_sheet("S")
        engine.set("S", "A1", "42")
        engine.set("S", "A2", "=A1+1")
        engine.define_name("MyVal", "S", "A1")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name

        try:
            from spreadsheet.config import save_config, load_config
            save_config(engine, path)
            engine2 = load_config(path)
            assert engine2.get("S", "A1") == 42.0
        finally:
            os.unlink(path)

    def test_config_error_missing_file(self):
        from spreadsheet.config import load_config, ConfigError
        with pytest.raises(ConfigError):
            load_config("/nonexistent/file.yaml")


class TestCachedEngine:
    def setup_method(self):
        from spreadsheet.optimizer import CachedEngine
        self.engine = CachedEngine()
        self.engine.add_sheet("S")

    def test_cached_basic(self):
        self.engine.set("S", "A1", "10")
        self.engine.set("S", "A2", "=A1*2")
        self.engine.recalculate()
        assert self.engine.get("S", "A2") == 20.0

    def test_cached_invalidation(self):
        self.engine.set("S", "A1", "10")
        self.engine.set("S", "A2", "=A1*2")
        self.engine.recalculate()
        assert self.engine.get("S", "A2") == 20.0

        self.engine.set("S", "A1", "20")
        self.engine.recalculate()
        assert self.engine.get("S", "A2") == 40.0

    def test_cached_complex(self):
        for i in range(10):
            self.engine.set("S", f"A{i+1}", str(i + 1))
        self.engine.set("S", "B1", "=SUM(A1:A10)")
        self.engine.set("S", "B2", "=AVERAGE(A1:A10)")
        self.engine.set("S", "B3", "=MAX(A1:A10)")
        self.engine.recalculate()
        assert self.engine.get("S", "B1") == 55.0
        assert self.engine.get("S", "B2") == 5.5
        assert self.engine.get("S", "B3") == 10.0


class TestOptimizer:
    def test_batch_set(self):
        from spreadsheet.optimizer import batch_set
        engine = Engine()
        batch_set(engine, "S", [["1", "2", "3"], ["4", "5", "=A1+A2"]])
        engine.recalculate()
        assert engine.get("S", "A1") == 1.0
        # B2 = A1 + A2 = 1 + 4 = 5
        assert engine.get("S", "B2") == 5.0

    def test_load_matrix(self):
        from spreadsheet.optimizer import load_matrix
        engine = Engine()
        load_matrix(engine, "S", [[1, 2, 3], [4, 5, 6]])
        engine.recalculate()
        assert engine.get("S", "A1") == 1.0
        assert engine.get("S", "C2") == 6.0

    def test_lru_cache(self):
        from spreadsheet.optimizer import LRUCache
        c = LRUCache(capacity=3)
        c.put(("S", 0, 0), 42)
        assert c.get(("S", 0, 0)) == 42
        assert c.get(("S", 0, 1)) is not None  # _MISS sentinel, not actual
        assert ("S", 0, 0) in c
        c.invalidate(("S", 0, 0))
        assert ("S", 0, 0) not in c
        assert len(c) == 0


class TestLogging:
    def test_logger(self):
        from spreadsheet.logging_utils import get_logger, set_level
        import logging
        logger = get_logger()
        assert logger.name == "spreadsheet"
        set_level(logging.DEBUG)
        assert logger.level == logging.DEBUG

    def test_configure(self):
        from spreadsheet.logging_utils import configure
        configure(verbose=True)
        configure(quiet=True)
        configure()