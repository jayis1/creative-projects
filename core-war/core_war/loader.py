"""
Warrior file loader utilities.

Handles loading warriors from .red source files with proper name extraction,
validation, and batch loading from directories.
"""

import os
from typing import List, Optional

from core_war.parser import RedcodeParser, ParsedWarrior, ParseError


def load_warrior(path: str, name: Optional[str] = None) -> ParsedWarrior:
    """
    Load a warrior from a .red file.

    Args:
        path: Path to the .red file.
        name: Optional warrior name (defaults to filename without extension).

    Returns:
        ParsedWarrior instance.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ParseError: If the Redcode source is invalid.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Warrior file not found: {path}")

    with open(path, "r") as f:
        source = f.read()

    if name is None:
        name = os.path.splitext(os.path.basename(path))[0]

    parser = RedcodeParser()
    return parser.parse(source, name=name)


def load_warriors_from_dir(directory: str, max_warriors: int = 20) -> List[ParsedWarrior]:
    """
    Load all .red files from a directory.

    Args:
        directory: Path to directory containing .red files.
        max_warriors: Maximum number of warriors to load.

    Returns:
        List of ParsedWarrior instances sorted by name.
    """
    warriors = []
    if not os.path.isdir(directory):
        raise FileNotFoundError(f"Directory not found: {directory}")

    files = sorted(f for f in os.listdir(directory) if f.endswith(".red"))
    for fname in files[:max_warriors]:
        path = os.path.join(directory, fname)
        try:
            w = load_warrior(path)
            warriors.append(w)
        except ParseError as e:
            # Skip invalid warriors but warn
            print(f"Warning: skipping {fname}: {e}")

    return warriors


def load_warrior_from_string(source: str, name: str = "Inline") -> ParsedWarrior:
    """
    Parse warrior source from a string.

    Args:
        source: Redcode source text.
        name: Warrior name.

    Returns:
        ParsedWarrior instance.
    """
    parser = RedcodeParser()
    return parser.parse(source, name=name)