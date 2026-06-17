# ⚡ Circuit Simulator

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-158%20passing-green.svg)](./tests)

A fully-featured **digital circuit simulator** with propagation delays, sequential logic, composite circuit builders, an oscilloscope with ASCII waveform rendering and VCD export, a Circuit Description Language (CDL), truth table generation, circuit analysis, JSON/DOT export, and a CLI tool.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [CLI Usage](#cli-usage)
- [Architecture](#architecture)
- [API Reference](#api-reference)
  - [Signals & Wires](#signals--wires)
  - [Logic Gates](#logic-gates)
  - [Sequential Elements](#sequential-elements)
  - [Circuit Builder](#circuit-builder)
  - [Simulator](#simulator)
  - [CDL Parser](#cdl-parser)
  - [Oscilloscope](#oscilloscope)
  - [Truth Table & Analysis](#truth-table--analysis)
  - [Export & Visualization](#export--visualization)
  - [Waveform Analysis](#waveform-analysis)
  - [Configuration](#configuration)
  - [Preset Circuits](#preset-circuits)
- [Examples](#examples)
- [Testing](#testing)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [Changelog](#changelog)
- [License](#license)

## Features

- **Signal types**: `LOW`, `HIGH`, `UNDEFINED`, `HIGH_IMPEDANCE` (for tri-state buffers)
- **Combinational gates**: AND, OR, NOT, XOR, NAND, NOR, XNOR, Buffer, Tri-State Buffer, Multi-input variants
- **Sequential elements**: SR Latch, D Latch, D Flip-Flop (with async reset), JK Flip-Flop, T Flip-Flop
- **Clock generator**: Configurable period and duty cycle with proper edge detection
- **Composite builders**: Half Adder, Full Adder, Ripple-Carry Adder, 2-to-1 MUX, 2-to-4 Decoder
- **Preset circuits**: SR Latch, Counter, 1-bit ALU, Register, Ring Oscillator, Priority Encoder
- **Bus support**: Multi-bit bus with integer read/write (LSB-first)
- **Propagation delays**: Every gate has configurable delay in nanoseconds
- **Event-driven simulator**: With breakpoints, tracing, stimulus, and probe capabilities
- **Stimulus API**: Programmatic stimulus generation with timed events, pulses, and clock trains
- **Truth table generator**: Automatically enumerate all input combinations and record outputs
- **Circuit analyzer**: Gate count, depth, and fan-out statistics
- **Oscilloscope**: ASCII waveform rendering and VCD file export (GTKWave compatible)
- **CDL parser**: Declarative circuit description language for rapid prototyping
- **CLI tool**: `circuit-sim` command for running simulations, truth tables, stats, and export
- **JSON export/import**: Serialize and deserialize circuits as JSON
- **Graphviz DOT export**: Generate circuit diagrams for visualization
- **ASCII schematics**: Text-based circuit diagrams
- **Waveform analysis**: Transition counting, duty cycle, frequency measurement, trace comparison
- **Configuration system**: TOML/JSON configuration for simulation parameters

## Installation

```bash
# Clone and install in development mode
git clone https://github.com/jayis1/creative-projects.git
cd creative-projects/circuit-simulator

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with development dependencies
pip install -e ".[dev]"
```

The `circuit-sim` CLI command will be available after installation.

## Quick Start

### Python API

```python
from circuit_sim.core import Signal
from circuit_sim.circuit import Circuit
from circuit_sim.simulator import Simulator
from circuit_sim.scope import Oscilloscope
from circuit_sim.analyze import TruthTable

# Build a circuit
circ = Circuit("demo")
a = circ.add_wire("a", Signal.LOW)
b = circ.add_wire("b", Signal.LOW)
out = circ.add_wire("out")
circ.add_and("and1", a, b, out)

# Simulate
sim = Simulator(circ)
sim.trace("a", "b", "out")

a.signal = Signal.HIGH
b.signal = Signal.HIGH
sim.run(10)

print(f"Output: {out.signal}")  # Signal.HIGH

# View waveforms
scope = Oscilloscope()
scope.add_trace("out", sim.get_trace("out"))
print(scope.render_ascii())
```

### CLI

```bash
# Run a simulation from a CDL file
circuit-sim run examples/mux2.cdl --trace a,b,sel,out --duration 100 --waveform

# Generate truth table
circuit-sim truth-table examples/mux2.cdl --inputs a,b --outputs out

# Show circuit info
circuit-sim info examples/mux2.cdl

# Print statistics
circuit-sim stats examples/mux2.cdl

# Export as DOT graph
circuit-sim export-dot examples/mux2.cdl --output mux.dot

# Export as JSON
circuit-sim export-json examples/mux2.cdl --output mux.json

# Run demo
circuit-sim demo
```

## Architecture

The simulator uses an **event-driven** architecture:

```
┌─────────────────────────────────────────────────────────┐
│                     Circuit                             │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────────────┐   │
│  │ Wire │──│ Gate │──│ Wire │──│ Sequential Element │   │
│  └──────┘  └──────┘  └──────┘  └──────────────────┘   │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────────────────┐   │
│  │ Wire │──│ Gate │──│ Wire │──│      Clock         │   │
│  └──────┘  └──────┘  └──────┘  └──────────────────┘   │
│       │            │            │          │             │
└───────┼────────────┼────────────┼──────────┼─────────────┘
        │            │            │          │
        └────────────┴────────────┴──────────┘
                     │
              ┌──────┴──────┐
              │  Simulator   │
              │  (event      │
              │   loop)      │
              └──────┬──────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
  ┌─────┴─────┐ ┌───┴───┐ ┌──────┴──────┐
  │Oscilloscope│ │ CDL   │ │   Export    │
  │  (traces)  │ │Parser │ │ (JSON/DOT) │
  └────────────┘ └───────┘ └─────────────┘
```

### Simulation Loop (per time step)

1. **Record traced wire values** — for oscilloscope capture
2. **Advance clocks** — generate clock edges
3. **Evaluate sequential elements** — detect edges, update state
4. **Evaluate combinational logic** — iterate until stable
5. **Apply stimulus events** — if using `run_with_stimulus()`

### Propagation Delay Model

Each gate has a `delay_ns` parameter. When a gate evaluates, it doesn't immediately change its output — it schedules the change in a propagation queue. The simulator processes these delays as time advances, creating realistic ripple-carry behavior.

## API Reference

### Signals & Wires

```python
from circuit_sim.core import Signal, Wire, Bus

# 4-valued signal enum
s = Signal.HIGH       # Logic 1
s = Signal.LOW        # Logic 0
s = Signal.UNDEFINED  # Unknown/X
s = Signal.HIGH_IMPEDANCE  # Z (tri-state)

# Signal operations
~Signal.HIGH          # NOT → Signal.LOW
Signal.HIGH & Signal.LOW  # AND → Signal.LOW
Signal.HIGH | Signal.LOW  # OR  → Signal.HIGH
Signal.HIGH ^ Signal.LOW  # XOR → Signal.HIGH

# Wire creation and monitoring
wire = Wire("clk", initial=Signal.LOW)
wire.signal = Signal.HIGH
wire.connect(lambda sig, name: print(f"{name} → {sig}"))

# Multi-bit bus
bus = Bus("data", width=8, initial=Signal.LOW)
bus.write_int(0xAB)
value = bus.read_int()  # 0xAB = 171
```

### Logic Gates

```python
from circuit_sim.gates import (
    AndGate, OrGate, NotGate, XorGate,
    NandGate, NorGate, XnorGate,
    BufferGate, TriStateBuffer, MultiInputGate,
)
```

| Gate | Inputs | Output | Description |
|------|--------|--------|-------------|
| AND | 2 | 1 | Logical AND |
| OR | 2 | 1 | Logical OR |
| NOT | 1 | 1 | Inverter |
| XOR | 2 | 1 | Exclusive OR |
| NAND | 2 | 1 | NOT AND |
| NOR | 2 | 1 | NOT OR |
| XNOR | 2 | 1 | NOT XOR |
| Buffer | 1 | 1 | Identity with delay |
| Tri-State | 2 (data, enable) | 1 | HIGH_IMPEDANCE when disabled |
| Multi-Input | N | 1 | AND/OR/NAND/NOR with N inputs |

### Sequential Elements

```python
from circuit_sim.sequential import (
    SRLatch, DLatch, DFlipFlop, JKFlipFlop, TFlipFlop, Clock,
)
```

| Element | Inputs | Outputs | Description |
|---------|--------|---------|-------------|
| SR Latch | S, R | Q, Q̄ | Set-Reset latch |
| D Latch | D, EN | Q, Q̄ | Transparent latch |
| D Flip-Flop | D, CLK, [RST] | Q, Q̄ | Rising-edge triggered |
| JK Flip-Flop | J, K, CLK | Q, Q̄ | Rising-edge, with toggle mode |
| T Flip-Flop | T, CLK | Q, Q̄ | Rising-edge, toggles on T=1 |
| Clock | — | 1 | Configurable period and duty cycle |

### Circuit Builder

```python
from circuit_sim.circuit import Circuit

circ = Circuit("my_circuit")

# Add wires
a = circ.add_wire("a", Signal.LOW)
b = circ.add_wire("b", Signal.LOW)
out = circ.add_wire("out")

# Add buses
data = circ.add_bus("data", width=8)

# Add gates
circ.add_and("and1", a, b, out)
circ.add_xor("xor1", a, b, out, delay_ns=2)

# Add sequential elements
circ.add_d_flipflop("dff", d, clk, q, qbar, reset=rst)

# Add clocks
circ.add_clock("sysclk", clk, period_ns=20, duty_cycle=0.5)

# Composite builders
circ.build_half_adder("ha", a, b, sum_out, carry_out)
circ.build_full_adder("fa", a, b, cin, sum_out, cout)
circ.build_ripple_carry_adder("rca", bus_a, bus_b, sum_bus)
circ.build_mux2("mux", a, b, sel, out)
circ.build_decoder_2to4("dec", a, b, y0, y1, y2, y3)
```

### Simulator

```python
from circuit_sim.simulator import Simulator, Stimulus, BreakpointHit

sim = Simulator(circ, step_ns=1)

# Trace wires for oscilloscope
sim.trace("a", "b", "out")
sim.trace_all()

# Add breakpoints
sim.add_breakpoint(lambda t: t >= 100)

# Run simulation
sim.step()              # Advance by one time step
sim.run(100)            # Run for 100 nanoseconds
sim.run_until(lambda: circ.wire("done").signal == Signal.HIGH)

# Stimulus-driven simulation
stim = Stimulus()
stim.set_wire(5, "a", Signal.HIGH)
stim.set_wire(10, "b", Signal.HIGH)
stim.pulse_wire(20, 40, "clk")
stim.clock_pulse(20, "clk", num_cycles=5)
sim.run_with_stimulus(stim, 100)

# Probe values
signal = sim.probe("out")
bus_val = sim.probe_bus("data")

# Get traces
trace = sim.get_trace("clk")

# Reset
sim.reset()
```

### CDL Parser

The Circuit Description Language provides a declarative way to define circuits:

```
circuit my_adder;
wire a initial=LOW;
wire b initial=LOW;
wire sum;
wire carry;
half_adder ha1 a b -> sum carry;

# With stimulus
set a HIGH at 5;
set b HIGH at 10;
```

```python
from circuit_sim.cdl import parse_cdl

source = open("my_adder.cdl").read()
circ = parse_cdl(source)
```

### Oscilloscope

```python
from circuit_sim.scope import Oscilloscope

scope = Oscilloscope()
scope.add_trace("clk", sim.get_trace("clk"))
scope.add_trace("data", sim.get_trace("data"))

# ASCII waveform
print(scope.render_ascii(width=80))

# VCD export (for GTKWave)
scope.export_vcd("output.vcd")

# Dictionary export
data = scope.to_dict()
```

### Truth Table & Analysis

```python
from circuit_sim.analyze import TruthTable, CircuitStats

# Truth table
tt = TruthTable(circ, ["a", "b"], ["sum", "carry"])
rows = tt.generate()
print(tt.to_ascii())  # ASCII table
print(tt.to_csv())    # CSV format

# Circuit statistics
stats = CircuitStats(circ)
print(stats.summary())
print(f"Gate count: {stats.gate_count()}")
print(f"Wire count: {stats.wire_count()}")
print(f"Depth: {stats.compute_depth()}")
```

### Export & Visualization

```python
from circuit_sim.export import (
    circuit_to_json, circuit_from_json,
    circuit_to_dot, circuit_to_ascii,
)

# JSON export/import
json_str = circuit_to_json(circ)
circuit_to_json(circ, "circuit.json")  # Write to file
loaded = circuit_from_json("circuit.json")

# Graphviz DOT export
dot = circuit_to_dot(circ)
# Render with: dot -Tpng circuit.dot -o circuit.png

# ASCII schematic
ascii_art = circuit_to_ascii(circ)
print(ascii_art)
```

### Waveform Analysis

```python
from circuit_sim.waveform import analyze_trace, compare_traces, format_trace_analysis

# Analyze a trace
trace = sim.get_trace("clk")
analysis = analyze_trace(trace, "clk")
print(f"Transitions: {analysis['transitions']}")
print(f"Duty cycle: {analysis['duty_cycle']:.1%}")
print(f"Frequency: {analysis['frequency_mhz']:.4f} MHz")

# Compare two traces
result = compare_traces(trace_a, trace_b)
print(f"Match: {result['match']}")

# Format analysis
print(format_trace_analysis(analysis))
```

### Configuration

```python
from circuit_sim.config import SimConfig

config = SimConfig(
    step_ns=1,
    default_gate_delay_ns=1,
    log_level="INFO",
)

# Load from JSON file
config = SimConfig.from_json("sim_config.json")

# Load from TOML file (Python 3.11+)
config = SimConfig.from_toml("sim_config.toml")
```

### Preset Circuits

```python
from circuit_sim.presets import (
    build_sr_latch_circuit,
    build_d_flipflop_counter,
    build_alu_1bit,
    build_register,
    build_ring_oscillator,
    build_priority_encoder,
)

# 1-bit ALU (AND, OR, XOR, ADD)
circ = build_alu_1bit()

# N-bit register
reg = build_register(width=4)

# 4-bit counter
counter = build_d_flipflop_counter(width=4)

# Ring oscillator
osc = build_ring_oscillator(num_stages=5)

# Priority encoder
enc = build_priority_encoder()
```

## Examples

See the `examples/` directory for complete examples:

| File | Description |
|------|-------------|
| `mux2.cdl` | 2-to-1 MUX in CDL format |
| `ripple_adder_4bit.cdl` | 4-bit ripple-carry adder in CDL |
| `d_flipflop.cdl` | D flip-flop with clock in CDL |
| `sr_latch.cdl` | SR latch in CDL |
| `adder_example.py` | Python API: 4-bit adder simulation |
| `truth_table_example.py` | Python API: Truth table generation |
| `export_example.py` | Python API: JSON/DOT/ASCII export |

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=circuit_sim --cov-report=html

# Run specific test file
pytest tests/test_circuit_sim.py -v

# Run new feature tests
pytest tests/test_new_features.py -v
```

The test suite includes **158 tests** covering:
- Signal and Wire operations
- All gate types (AND, OR, NOT, XOR, NAND, NOR, XNOR, Buffer, Tri-State, Multi-Input)
- Sequential elements (SR Latch, D Latch, D/JK/T Flip-Flops, Clock)
- Circuit builders (Half Adder, Full Adder, RCA, MUX, Decoder)
- Simulator (stepping, tracing, breakpoints, reset, stimulus)
- CDL parser (wires, buses, gates, sequential, clocks, builders, stimulus)
- Oscilloscope (ASCII rendering, VCD export)
- Truth table generation
- Circuit statistics
- Preset circuits
- Bug fixes and regression tests
- JSON export/import round-trip
- DOT export
- ASCII schematic export
- Waveform analysis
- Configuration system
- CLI commands

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for development guidelines.

## Roadmap

- [ ] **Wire delay support**: Use `Wire.delay_ns` in simulation for wire propagation delays
- [ ] **Negative-edge triggering**: Support falling-edge flip-flops in addition to rising-edge
- [ ] **Multi-bit bus operations**: Bus arithmetic (add, subtract, shift) directly on Bus objects
- [ ] **Circuit flattening**: Flatten composite circuits into primitive gates
- [ ] **Interactive REPL**: Live interactive simulation with step-by-step debugging
- [ ] **SVG waveform export**: Generate SVG waveforms alongside ASCII and VCD
- [ ] **Monte Carlo simulation**: Statistical analysis with random input distributions
- [ ] **Hazard/glitch detection**: Automatically detect and report combinational hazards
- [ ] **Critical path analysis**: Identify the longest delay path in a circuit
- [ ] **RTL-level CDL**: Extend CDL with register-transfer-level constructs
- [ ] **GUI waveform viewer**: Interactive waveform display using curses or web interface

## Changelog

### v2.0.0 — Major Enhancement Release

**New Features:**
- CLI tool (`circuit-sim`) with subcommands: `run`, `truth-table`, `stats`, `info`, `export-dot`, `export-json`, `demo`
- JSON circuit serialization/deserialization (`circuit_to_json` / `circuit_from_json`)
- Graphviz DOT export for circuit visualization (`circuit_to_dot`)
- ASCII schematic diagram generation (`circuit_to_ascii`)
- Waveform analysis module with trace comparison, frequency/duty-cycle measurement
- Simulation configuration system (`SimConfig`) with JSON/TOML support
- Comprehensive examples directory with CDL files and Python scripts

**Improvements:**
- Package now installable via `pip install -e .` with proper entry points
- Added `pyproject.toml` with full metadata and dependencies
- Added GitHub Actions CI configuration
- Added LICENSE (MIT) and CONTRIBUTING.md
- Expanded test suite from 127 to 158 tests
- Added type hints throughout new modules

### v1.1.0 — Bug Fix Release

**Bug Fixes:**
- Clock degenerate duty cycle: clamped `_high_ns` and `_low_ns` to minimum 1
- `Simulator.reset()` now restores initial wire values instead of setting all to UNDEFINED
- CDL `ripple_adder` command implemented
- `TruthTable.generate()` resets circuit state between iterations
- `Stimulus.pulse_wire()` validates `start_ns < end_ns`
- Convergence limit increased to `max(50, 2 * num_gates)`
- `Wire.delay_ns` documented as unused by simulator

### v1.0.0 — Initial Release

Core features: Signal/Wire/Bus, 10 gate types, 5 sequential elements, Clock, Circuit builder, Simulator, CDL parser, Oscilloscope, Truth tables, Circuit statistics, 6 preset circuits.

## License

[MIT License](./LICENSE)