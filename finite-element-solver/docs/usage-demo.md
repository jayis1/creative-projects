# Usage demo

```bash
python3 -m finite_element_solver validate examples/roof-truss.yaml
python3 -m finite_element_solver summary examples/roof-truss.yaml
python3 -m finite_element_solver solve examples/roof-truss.yaml --combination ultimate-down
python3 -m finite_element_solver envelope examples/roof-truss.yaml --json
```

Example envelope excerpt:

```json
{
  "result_count": 5,
  "global_max_displacement": {
    "node": "D",
    "magnitude": 0.000012,
    "source": "ultimate-down"
  }
}
```
