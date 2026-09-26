"""Command-line interface for the assembler."""
import argparse
import sys
from pathlib import Path
from .core import assemble, parse_reads


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assemble DNA reads with a de Bruijn graph")
    parser.add_argument("reads", type=Path, help="newline-delimited, FASTA, or FASTQ file")
    parser.add_argument("-k", type=int, default=21, help="k-mer size (default: 21)")
    parser.add_argument("--min-count", type=int, default=1, help="discard k-mers below this count")
    parser.add_argument("--stats", action="store_true", help="print graph statistics")
    args = parser.parse_args(argv)
    try:
        reads = parse_reads(args.reads)
        result = assemble(reads, args.k, min_count=args.min_count)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    for index, contig in enumerate(result.contigs, 1):
        print(f">contig_{index} length={len(contig)}")
        print(contig)
    print(f"# reads={result.reads} kmers={result.kmers} contigs={len(result.contigs)} k={result.k} n50={result.n50}")
    if args.stats:
        print(f"# nodes={result.graph_nodes} total_bases={result.total_bases}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
