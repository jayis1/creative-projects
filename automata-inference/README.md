# Automata Inference

A compact, dependency-free DFA learner for developers who want to turn a small labeled corpus of strings into an inspectable recognizer. Supply positive and negative examples; in seconds it emits a deterministic finite automaton as JSON.

## How it works

The learner constructs an augmented prefix-tree acceptor, then runs the RPNI red/blue state-merging strategy. Candidate merges are propagated through matching transitions and rejected if they collapse a positive example with a negative one. The output is a hypothesis consistent with the supplied examples, not a promise of recovering the unknown language: finite samples cannot uniquely determine every regular language.

Strings are sequences of Unicode code points. Missing transitions reject. Conflicting positive/negative labels and non-string samples are errors. The library has no runtime dependencies.

## Usage

From this directory, run:

```sh
python3 cli.py examples/even-free.json
```

Example output (the transition state IDs are deterministic):

```json
{
  "accepting": [1, 2],
  "start": 0,
  "transitions": {
    "0": {"a": 1, "b": 2},
    "1": {"a": 1, "b": 0},
    "2": {"a": 0, "b": 2}
  }
}
```

Run `python3 cli.py --help` for options. Add `--minimize` to compact equivalent states. The library also supports ordered batch classification with `accepts_many` and shortest distinguishing-word checks between two hypotheses with `distinguishing_word`; equivalent machines return `None`. Input JSON must contain `positive` and `negative` arrays of strings; malformed schemas fail with a concise error and exit status 2. The learner rejects contradictory labels and non-string samples. The library has no runtime dependencies.

```python
from automata_inference import infer
machine = infer(["cat", "cats"], ["car", "dog"])
print(machine.accepts("cat"))  # True
```

## Tests

Run `python3 -m unittest discover -s automata-inference -p 'test_*.py'` from the repository root.

## Known Issues (Resolved)

- The CLI previously treated a JSON string in place of a sample array as a collection of one-character words and exited successfully. A regression test reproduced the false success before the fix; the CLI now validates the JSON object and array fields and returns status 2 with a clear diagnostic. The test suite covers this red-to-green case.
