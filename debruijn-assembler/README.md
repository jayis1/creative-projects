# de Bruijn Assembler

A from-scratch DNA read assembler that turns short sequencing reads into contigs using a de Bruijn graph. It is intentionally dependency-free and focuses on making the graph algorithm inspectable.

## How it works

1. Each read is split into overlapping k-mers.
2. Every k-mer becomes a weighted directed edge from its `(k-1)`-base prefix to suffix.
3. Optional abundance filtering removes sequencing-error k-mers below `--min-count`.
4. Maximal non-branching paths are walked to produce contigs.
5. N50, total bases, node counts, and k-mer counts make runs easy to compare.

## Usage

```bash
python3 -m debruijn_assembler.cli reads.txt --k 21 --min-count 2 --stats
```

Input may be newline-delimited sequences, multiline FASTA, or four-line FASTQ. Bases are normalized to uppercase and k-mers containing unsupported symbols are skipped. Malformed FASTQ records fail with a useful error instead of being silently assembled.

## Python API

```python
from debruijn_assembler import assemble, parse_reads
result = assemble(parse_reads("reads.fastq"), k=31, min_count=2)
print(result.contigs, result.n50)
```

## Development

```bash
python3 -m pytest -q
```
