"""Command-line interface for the assembler."""
import argparse
from pathlib import Path
from .core import assemble, parse_reads


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assemble DNA reads with a de Bruijn graph")
    parser.add_argument("reads", type=Path, help="newline-delimited, FASTA, or FASTQ file")
    parser.add_argument("-k", type=int, default=21, help="k-mer size (default: 21)")
    args = parser.parse_args(argv)
    reads = parse_reads(args.reads)
    result = assemble(reads, args.k)
    for index, contig in enumerate(result.contigs, 1):
        print(f">contig_{index} length={len(contig)}")
        print(contig)
    print(f"# reads={result.reads} kmers={result.kmers} contigs={len(result.contigs)} k={result.k}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
