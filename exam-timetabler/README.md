# Exam Timetabler

A dependency-free Python tool that converts shared-student constraints into an exam conflict graph and assigns exams to time slots using DSATUR graph coloring.

## How it works

Each exam is a vertex; two vertices share an edge when their student sets intersect. The scheduler repeatedly colors the unassigned exam with greatest saturation degree, then graph degree, then name (deterministic tie-break). It chooses the first available slot. This is a fast heuristic, not a proof of minimum coloring. A slot limit fails clearly if the greedy coloring cannot proceed within that limit.

## Usage

Run the included demonstration:

    python3 main.py

Schedule JSON input:

    python3 main.py exams.json --slots 4

Input shape: `{"exams":[{"name":"Algorithms","students":["s1","s2"]}]}`. Output is JSON mapping exam names to zero-based slot numbers. Run tests with `python3 -m unittest -v` from this directory. Requires Python 3.10+; no third-party packages.
