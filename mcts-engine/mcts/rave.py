"""
RAVE selection policy module.

Re-exports RAVEPolicy for convenience. The actual implementation lives
in uct.py since RAVEPolicy shares the SelectionPolicy base class.
"""

from .uct import RAVEPolicy

__all__ = ["RAVEPolicy"]