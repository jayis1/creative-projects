# Circuit Simulator

A fully-featured digital circuit simulator with propagation delays, sequential logic, composite circuit builders, an oscilloscope with ASCII waveform rendering and VCD export, a Circuit Description Language (CDL) for declarative circuit construction, truth table generation, circuit analysis, and preset circuit libraries.

## Features

- **Signal types**: `LOW`, `HIGH`, `UNDEFINED`, `HIGH_IMPEDANCE` (for tri-state buffers)
- **Combinational gates**: AND, OR, NOT, XOR, NAND, NOR, XNOR, Buffer, Tri-State Buffer, Multi-input variants
- **Sequential elements**: SR Latch, D Latch, D Flip-Flop (with async reset), JK Flip-Flop, T Flip-Flop
- **Clock generator**: Configurable period and duty cycle
- **Composite builders**: Half Adder, Full Adder, Ripple-Carry Adder, 2-to-1 MUX, 2-to-4 Decoder
- **Preset circuits**: SR Latch, Counter, 1-bit ALU, Register, Ring Oscillator, Priority Encoder
- **Bus support**: Multi-bit bus with integer read/write (LSB-first)
- **Propagation delays**: Every gate has configurable delay in nanoseconds
- **Event-driven simulator**: With breakpoints, tracing, stimulus, and probe capabilities
- **Stimulus API**: Programmatic stimulus generation with timed events, pulses, and clock trains
- **Truth table generator**: Automatically enumerate all input combinations and record outputs
- **Circuit analyzer**: Gate count, depth, fan-out statistics
- **Oscilloscope**: ASCII waveform rendering and VCD file export (GTKWave compatible)
- **CDL parser**: Declarative circuit description language

## How It Works

### Core Architecture

The simulator uses an **event-driven** architecture:

1. **Signals** are represented as a 4-valued enum (`LOW`, `HIGH`, `UNDEFINED`, `HIGH_IMPEDANCE`)
2. **Wires** carry signals between components, with optional listeners and history recording
3. **Gates** evaluate their inputs and schedule output changes after a propagation delay
4. **The Simulator** advances time in discrete nanosecond steps, processing clocks, sequential elements, and combinational logic in order

### Simulation Loop (per time step)

```
1. Record traced wire values
2. Advance clocks (generate clock edges)
3. Evaluate sequential elements (detect edges, update state)
4. Evaluate combinational logic (iterate until stable)
5. Apply stimulus events (if using run_with_stimulus)
```

### Propagation Delay Model

Each gate has a `delay_ns` parameter. When a gate evaluates, it doesn't immediately change its output — it schedules the change in a propagation queue. The simulator processes these delays as time advances, creating realistic ripple-carry behavior.

### CDL (Circuit Description Language)

A simple declarative language for defining circuits:

```
circuit my_adder;
wire a initial=LOW;
wire b initial=LOW;
wire sum;
wire carry;
half_adder ha1 a b -> sum carry;
```

## Installation

```bash
pip install -e .
```

## Usage

### Basic Gate Simulation

```python
from circuit_sim.core import Signal
from circuit_sim.circuit import Circuit
from circuit_sim.simulator import Simulator

circ = Circuit("demo")
a = circ.add_wire("a", Signal.LOW)
b = circ.add_wire("b", Signal.LOW)
out = circ.add_wire("out")
circ.add_and("and1", a, b, out)

sim = Simulator(circ)
sim.trace("a", "b", "out")

a.signal = Signal.HIGH
b.signal = Signal.HIGH
sim.run(10)
print(sim.probe("out"))  # Signal.HIGH
```

### Ripple-Carry Adder

```python
from circuit_sim.core import Signal
from circuit_sim.circuit import Circuit
from circuit_sim.simulator import Simulator

circ = Circuit("4bit_adder")
a = circ.add_bus("a", 4)
b = circ.add_bus("b", 4)
s = circ.add_bus("s", 4)
circ.build_ripple_carry_adder("rca", a, b, s)

a.write_int(7)
b.write_int(3)
sim = Simulator(circ)
sim.run(20)
print(s.read_int())  # 10
```

### D Flip-Flop with Clock

```python
from circuit_sim.core import Signal
from circuit_sim.circuit import Circuit
from circuit_sim.simulator import Simulator
from circuit_sim.scope import Oscilloscope

circ = Circuit("flipflop_demo")
d = circ.add_wire("d", Signal.HIGH)
clk = circ.add_wire("clk", Signal.LOW)
q = circ.add_wire("q", Signal.LOW)
qbar = circ.add_wire("qbar", Signal.HIGH)

circ.add_d_flipflop("dff", d, clk, q, qbar)
circ.add_clock("clk1", clk, period_ns=10)

sim = Simulator(circ)
sim.trace("clk", "d", "q")
sim.run(100)

scope = Oscilloscope()
for name in ["clk", "d", "q"]:
    scope.add_trace(name, sim.get_trace(name))
print(scope.render_ascii())
```

### Stimulus-Driven Simulation

```python
from circuit_sim.core import Signal
from circuit_sim.circuit import Circuit
from circuit_sim.simulator import Simulator, Stimulus

circ = Circuit("stim_demo")
a = circ.add_wire("a", Signal.LOW)
b = circ.add_wire("b", Signal.LOW)
out = circ.add_wire("out")
circ.add_xor("xor1", a, b, out)

stim = Stimulus()
stim.set_wire(5, "a", Signal.HIGH)
stim.pulse_wire(10, 20, "b")

sim = Simulator(circ)
sim.run_with_stimulus(stim, 30)
```

### Truth Table Generation

```python
from circuit_sim.core import Signal
from circuit_sim.circuit import Circuit
from circuit_sim.analyze import TruthTable

circ = Circuit("xor_tt")
a = circ.add_wire("a", Signal.LOW)
b = circ.add_wire("b", Signal.LOW)
out = circ.add_wire("out")
circ.add_xor("xor1", a, b, out)

tt = TruthTable(circ, ["a", "b"], ["out"])
rows = tt.generate()
print(tt.to_ascii())
```

### CDL (Circuit Description Language)

```python
from circuit_sim.cdl import parse_cdl
from circuit_sim.simulator import Simulator

source = """
circuit half_adder;
wire a initial=LOW;
wire b initial=LOW;
wire sum;
wire carry;
half_adder ha1 a b -> sum carry;
"""
circ = parse_cdl(source)
sim = Simulator(circ)
```

### Preset Circuits

```python
from circuit_sim.presets import build_alu_1bit, build_register, build_priority_encoder
from circuit_sim.simulator import Simulator
from circuit_sim.core import Signal

# 1-bit ALU
circ = build_alu_1bit()
circ.wire("a").signal = Signal.HIGH
circ.wire("b").signal = Signal.LOW
circ.wire("op0").signal = Signal.LOW  # AND
circ.wire("op1").signal = Signal.LOW
sim = Simulator(circ)
sim.run(20)
print(circ.wire("result").signal)  # Signal.LOW (0 AND 1 = 0)

# 4-bit Register
reg = build_register(width=4)
sim = Simulator(reg)
sim.run(100)
```

### VCD Export (for GTKWave)

```python
from circuit_sim.scope import Oscilloscope

scope = Oscilloscope()
scope.add_trace("clk", sim.get_trace("clk"))
scope.add_trace("q", sim.get_trace("q"))
scope.export_vcd("output.vcd")
# Open in GTKWave: gtkwave output.vcd
```

## Project Structure

```
circuit-simulator/
├── circuit_sim/
│   ├── __init__.py          # Package exports
│   ├── core.py              # Signal, Wire, Bus
│   ├── gates.py             # Combinational gate implementations
│   ├── sequential.py        # Latches, flip-flops, clock
│   ├── circuit.py           # Circuit container and composite builders
│   ├── simulator.py         # Event-driven simulation engine, Stimulus
│   ├── cdl.py               # Circuit Description Language parser
│   ├── scope.py             # Oscilloscope and VCD export
│   ├── analyze.py           # Truth table generator, circuit statistics
│   └── presets.py           # Pre-built circuit templates
├── tests/
│   └── test_circuit_sim.py  # Comprehensive test suite (93 tests)
├── demo.py                  # Interactive demo script
├── README.md
└── pyproject.toml
```

## Supported Gates

| Gate | Inputs | Output | Description |
|------|--------|--------|-------------|
| AND  | 2      | 1      | Logical AND |
| OR   | 2      | 1      | Logical OR |
| NOT  | 1      | 1      | Inverter |
| XOR  | 2      | 1      | Exclusive OR |
| NAND | 2      | 1      | NOT AND |
| NOR  | 2      | 1      | NOT OR |
| XNOR | 2      | 1      | NOT XOR |
| Buffer | 1    | 1      | Identity with delay |
| Tri-State | 2 (data, enable) | 1 | HIGH_IMPEDANCE when disabled |
| Multi-Input | N | 1 | AND/OR/NAND/NOR with N inputs |

## Supported Sequential Elements

| Element | Inputs | Outputs | Description |
|---------|--------|---------|-------------|
| SR Latch | S, R | Q, Q̄ | Set-Reset latch |
| D Latch | D, EN | Q, Q̄ | Transparent latch |
| D Flip-Flop | D, CLK, [RST] | Q, Q̄ | Rising-edge triggered |
| JK Flip-Flop | J, K, CLK | Q, Q̄ | Rising-edge, with toggle mode |
| T Flip-Flop | T, CLK | Q, Q̄ | Rising-edge, toggles on T=1 |
| Clock | — | 1 | Configurable period and duty cycle |

## Preset Circuits

| Preset | Description |
|--------|-------------|
| `build_sr_latch_circuit` | Basic SR latch with test inputs |
| `build_d_flipflop_counter` | N-bit ripple counter using T flip-flops |
| `build_alu_1bit` | 1-bit ALU (AND, OR, XOR, ADD operations) |
| `build_register` | N-bit register with load enable and reset |
| `build_ring_oscillator` | N-stage ring oscillator (odd number of inverters) |
| `build_priority_encoder` | 4-bit priority encoder with valid output |

## License

MIT