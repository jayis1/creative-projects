"""Educational de Bruijn graph genome assembler."""

from .core import AssemblyResult, assemble, build_graph, parse_reads

__all__ = ["AssemblyResult", "assemble", "build_graph", "parse_reads"]
__version__ = "0.3.0"
