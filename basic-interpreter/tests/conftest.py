"""Test configuration and shared fixtures for the BASIC interpreter test suite."""

import io
import sys
import os
import tempfile

import pytest

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from basic_interpreter.interpreter import Interpreter
from basic_interpreter.errors import BasicError, BasicSyntaxError, BasicRuntimeError, BasicStopException


@pytest.fixture
def interp():
    """Create a fresh Interpreter with StringIO for stdout."""
    return Interpreter(stdout=io.StringIO())


@pytest.fixture
def interp_stdin():
    """Create a fresh Interpreter with both stdin and stdout as StringIO."""
    def _make(input_str=""):
        return Interpreter(
            stdin=io.StringIO(input_str),
            stdout=io.StringIO()
        )
    return _make


def run_basic(source: str, stdin_data: str = "") -> str:
    """Helper: run a BASIC program and return the output."""
    interp = Interpreter(
        stdin=io.StringIO(stdin_data),
        stdout=io.StringIO()
    )
    interp.load(source)
    interp.run()
    return interp.stdout.getvalue()


def run_basic_file(source: str, stdin_data: str = "") -> str:
    """Helper: run a BASIC program and return the output (alias for run_basic)."""
    return run_basic(source, stdin_data)