"""Tests for the logging utilities."""
import os, sys, logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from delaunay_voronoi.logging_utils import get_logger, configure_logging


class TestLogging:
    def test_get_logger(self):
        logger = get_logger("test")
        assert logger.name == "delaunay_voronoi.test"

    def test_get_root_logger(self):
        logger = get_logger()
        assert logger.name == "delaunay_voronoi"

    def test_configure_logging(self):
        logger = configure_logging("DEBUG")
        assert logger.level == logging.DEBUG

    def test_configure_logging_warning(self):
        logger = configure_logging("WARNING")
        assert logger.level == logging.WARNING