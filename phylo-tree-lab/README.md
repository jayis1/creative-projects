# Phylo Tree Lab

A dependency-free Python toolkit for scoring aligned DNA/protein characters on rooted phylogenetic trees using Fitch's minimum-parsimony algorithm.

## How it works

At each site, each leaf begins with its observed state. Internal nodes combine child state sets: use their intersection when nonempty; otherwise use the union and add one substitution. This is the classic bottom-up Fitch pass for unordered characters. Multifurcations are handled by folding all child sets.

The parser accepts a deliberately small Newick subset: internal groups and leaves written `name:SEQUENCE`, followed by `;`. Branch lengths, quoted names, and ambiguity codes are not currently supported.

## Usage

```python
from parsimony import fitch_score, parse_newick

tree = parse_newick("((human:ACGT,chimp:ACGA),gorilla:TCGA);")
print(fitch_score(tree))
```

Run tests with `python3 -m unittest -v` from this directory. No third-party packages are required.

## Command line

Pipe a tree or provide a UTF-8 file; the CLI prints the total parsimony score and reports invalid input on stderr with exit status 2:

```sh
printf '((human:ACGT,chimp:ACGA),gorilla:TCGA);' | python3 cli.py
python3 cli.py tree.nwk
```

Internal labels are ignored. Input is a single tree using the documented `name:SEQUENCE` leaf notation.

## Known Issues (Resolved)

Phase 3 reviewed the parser, Fitch recurrence, and CLI. No production defect was reproducibly demonstrated, so no bug fix is claimed. Expanded regression coverage includes hand-calculated constant/single-change/multifurcation scores, ignored internal labels, malformed and misaligned input rejection, and CLI success/error behavior. Unsupported Newick features (quoted names, branch lengths, ambiguity sets) remain intentional limitations.
