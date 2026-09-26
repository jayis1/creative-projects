# de Bruijn Assembler

A from-scratch DNA read assembler that turns short sequencing reads into contigs using a de Bruijn graph. It is intentionally dependency-free and focuses on making the graph algorithm inspectable.

## How it works

1. Each read is split into overlapping k-mers.
2. Every k-mer becomes a directed edge from its `(k-1)`-base prefix to suffix.
3. Maximal non-branching paths are walked to produce contigs.
4. The CLI emits contigs as FASTA plus a summary line.

## Usage

```bash
python3 -m debruijn_assembler.cli reads.txt --k 21
```

Input may be newline-delimited sequences, FASTA, or FASTQ. Bases are normalized to uppercase and k-mers containing unsupported symbols are skipped.

## Development

```bash
python3 -m pytest -q
```
