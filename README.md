# Creative Projects

A monorepo of AI-generated creative coding projects. Each project lives in its own subfolder with its own README.md.

## Projects

| Project | Description |
|---------|-------------|
| [lattice-boltzmann-fluid-sim](./lattice-boltzmann-fluid-sim) | 2D fluid dynamics via Lattice Boltzmann Method |
| [lsystem-renderer](./lsystem-renderer) | L-System fractal and plant renderer |
| [sdf-raymarcher](./sdf-raymarcher) | Pure-Python SDF ray marcher with PBR lighting |
| [wfc-generator](./wfc-generator) | Wave Function Collapse procedural generation |
| [cdcl-sat-solver](./cdcl-sat-solver) | Full-featured CDCL SAT solver with VSIDS, 2-watched-literal BCP, preprocessing, incremental solving, CLI, and 77 tests |
| [constraint-solver](./constraint-solver) | Comprehensive CSP solver: AC-3, backtracking+MRV/LCV, MAC, forward checking, config system, visualization, serialization, 141 tests |
| [reaction-diffusion-sim](./reaction-diffusion-sim) | Turing pattern simulator: 5 models (Gray-Scott, FHN, GM, Brusselator, Schnakenberg), RK4 solver, YAML/TOML config, parameter sweeps, custom model registration, 23 presets, 114 tests, pip-installable |
| [midi-sequencer](./midi-sequencer) | Generative MIDI step sequencer: Euclidean/Markov/L-System generation, 15 scales, 11 chords, 10 progressions, 13 drum styles, groove templates, velocity curves, arrangement, serialization, CLI, config, validation, analysis, batch composition, 124 tests, pip-installable |
| [regex-engine](./regex-engine) | Regex engine from scratch: Thompson NFA construction, O(nm) guarantee, recursive-descent parser, char classes, quantifiers, alternation, capture groups, findall/sub/split, backreferences in sub, CLI, 146 tests, pip-installable |
| [cryptanalysis-toolkit](./cryptanalysis-toolkit) | Classical cipher toolkit: 12 ciphers (Caesar, substitution, Vigenère, affine, Playfair, rail fence, columnar transposition, autokey, Beaufort, Porta, XOR, Enigma), frequency analysis, IC, Friedman test, Kasiski examination, pattern matching, n-gram scoring, automatic breaking (Caesar/affine/Vigenère/substitution/XOR), hill climbing, CLI, 115 tests |
| [basic-interpreter](./basic-interpreter) | Full-featured BASIC language interpreter: modular package (lexer, parser, AST, interpreter, config, CLI, REPL), 40+ built-in functions, FOR/NEXT/WHILE/WEND/DO/LOOP/SELECT CASE/ON ERROR, arrays, file I/O, PRINT USING, argparse CLI, TOML config, comprehensive pytest suite, pip-installable, 75+ tests |
| [compression-engine](./compression-engine) | From-scratch data compression engine: 8 codecs (Huffman, LZ77, BWT, DEFLATE, RLE, Delta, LZW, Arithmetic), codec pipelines, analysis tools, benchmarking, CRC32 integrity, config system, CLI, abstract base class, 203 tests, pip-installable |
| [chip8-emulator](./chip8-emulator) | CHIP-8 VM emulator: 35 opcodes, SUPER-CHIP extensions, built-in assembler, execution profiler, trace recorder, step-through debugger, ROM validator, config files (YAML/JSON/TOML), CLI, 293 tests, pip-installable |
|| [prolog-engine](./prolog-engine) | Mini-Prolog logic programming engine v2.0: Robinson's unification w/ occurs-check, backtracking, 60+ built-ins (string/atom ops, list aggregation), config files (YAML/JSON/TOML), colorized REPL, structured exceptions, logging, engine statistics, 195 tests, pip-installable |
|| [riscv-emu](./riscv-emu) | RISC-V RV32I CPU emulator: full instruction set, Zicsr CSRs, two-pass assembler (pseudo-instructions, directives, labels), ELF32/raw loader, interactive debugger (breakpoints, watchpoints, step, inspect), execution profiler, trace recorder, 81 tests, pip-installable |

---