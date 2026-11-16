# Exam Timetabler

A dependency-free Python tool that converts shared-student constraints into an exam conflict graph and assigns exams to time slots using DSATUR graph coloring.

## How it works

Each exam is a vertex; two vertices share an edge when their student sets intersect. The scheduler repeatedly colors the unassigned exam with greatest saturation degree, then graph degree, then name (deterministic tie-break). It chooses the first available slot. This is a fast heuristic, not a proof of minimum coloring. A slot limit fails clearly if the greedy coloring cannot proceed within that limit.

## Usage

Run the included demonstration:

    python3 main.py

Schedule JSON input:

    python3 main.py exams.json --slots 4

For a detailed slot-by-slot breakdown, use:

    python3 main.py exams.json --slots 4 --report

Input shape: `{"exams":[{"name":"Algorithms","students":["s1","s2"]}]}`. The default output is JSON mapping exam names to zero-based slot numbers and a slot count. `--report` instead emits `exam_count`, the number of used slots, and a sorted mapping from slot numbers to exam names. Run `python3 -m unittest -v` from this directory. The CLI uses a deterministic DSATUR heuristic rather than an optimal-coloring search, so it may use more slots than mathematically necessary. It expects UTF-8 JSON and holds the complete input and conflict graph in memory.

## Known Issues (Resolved)

- The schedule checker previously accepted negative and fractional slot identifiers as valid. It now reports invalid slot values; regression tests reproduce both cases.
