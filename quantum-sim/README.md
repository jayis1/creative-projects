# Quantum Circuit Simulator (quantum-sim)

A from-scratch quantum circuit simulator with state-vector and density-matrix
backends, supporting multi-qubit gates, controlled operations, measurement,
noise channels, entanglement detection, partial trace, and canonical quantum
algorithms.

## Features

### Core Simulation
- **State-vector backend** — tracks pure states |ψ⟩ as 2^n complex vectors
- **Density-matrix backend** — tracks mixed states ρ as 2^n × 2^n matrices
- **20+ built-in gates** — X, Y, Z, H, S, T, SX, CNOT, CZ, SWAP, iSWAP,
  √SWAP, Toffoli (CCX), Fredkin (CSWAP), XX, I
- **Parameterized gates** — RX, RY, RZ, Phase, U1, U2, U3
- **Controlled gate construction** — `controlled(U)` builds C-U from any 1-qubit gate
- **Gate algebra** — tensor products, composition, dagger, powers
- **Unitarity verification** — every gate is checked to be unitary at construction

### Quantum Noise (v2.0)
- **6 CPTP noise channels** — depolarizing, bit flip, phase flip, amplitude
  damping, phase damping, general Pauli channel
- **Kraus operator representation** — each channel verified as completely
  positive and trace-preserving
- **Per-qubit noise application** — apply noise to specific qubits during
  density-matrix simulation

### State Operations
- Normalization, probability computation, expectation values
- Fidelity (pure and mixed), purity, von Neumann entropy
- Projective measurement with collapse and probabilistic sampling
- Entanglement detection via Schmidt rank (SVD)
- Partial trace with correct qubit ordering
- Bloch sphere vector computation and ASCII visualization

### Circuit Visualization (v2.0)
- **ASCII circuit diagrams** — render circuits as text with qubit wires,
  gate symbols, control connections, and barriers

### Serialization (v2.0)
- **JSON serialization** — save/load circuits via `to_json()`/`from_json()`
- **OpenQASM 2.0 export** — standard quantum assembly format

### Algorithms
- **Bell states** — all four Bell states (Φ±, Ψ±)
- **Quantum teleportation** — with classical correction
- **Deutsch-Jozsa** — constant vs balanced oracle discrimination
- **Grover's search** — amplitude amplification with optimal iterations
- **Quantum Fourier Transform (QFT)** — n-qubit QFT circuit
- **Superdense coding** — transmit 2 classical bits via 1 qubit

### Advanced Protocols (v2.0)
- **State tomography** — reconstruct density matrix from X/Y/Z measurements
- **BB84 quantum key distribution** — with optional eavesdropper detection
- **Quantum random walk** — discrete-time quantum walk on a line

### CLI (10 subcommands)
- `bell`, `grover`, `qft`, `deutsch-jozsa`, `teleport`, `bloch`,
  `superdense`, `qasm`, `noise`, `draw`

### Testing
- 102 pytest tests covering gates, state operations, simulator, algorithms,
  noise channels, serialization, visualization, and protocols

## Installation

```bash
cd quantum-sim
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Quick Start

```python
from quantum_sim import QuantumCircuit, Simulator

# Create a Bell state
qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)

sim = Simulator(seed=42)
result = sim.run(qc, shots=1000)
print(result.state)        # (|00⟩ + |11⟩)/√2
print(result.get_counts()) # {'00': 503, '11': 497}
```

## Usage

### Python API

```python
from quantum_sim import QuantumCircuit, Simulator, StateVector
from quantum_sim.gates import rx, ry

# Build a circuit
qc = QuantumCircuit(3)
qc.h(0)
qc.cx(0, 1)
qc.toffoli(0, 1, 2)
qc.ry(2, 1.57)

# Simulate
sim = Simulator()
state = sim.evolve(qc)
print(state)

# Measure
result = sim.run(qc, shots=1024)
print(result.get_counts())

# Density matrix mode
sim_dm = Simulator(mode="density_matrix")
result_dm = sim_dm.run(qc, shots=100)
print(result_dm.state.purity())
```

### Noise Channels

```python
from quantum_sim import QuantumCircuit, Simulator, depolarizing, bit_flip

# Apply depolarizing noise to qubit 0 during simulation
qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)

noise = depolarizing(p=0.1)
sim = Simulator(
    mode="density_matrix",
    noise_channels=[(noise, (0,))]
)
result = sim.run(qc, shots=0)
print(f"Purity: {result.state.purity():.4f}")  # < 1.0 (mixed state)
print(f"Entropy: {result.state.von_neumann_entropy():.4f}")
```

### Entanglement & Partial Trace

```python
from quantum_sim import StateVector, DensityMatrix
import numpy as np

# Bell state |Φ+⟩
sv = StateVector(np.array([1/np.sqrt(2), 0, 0, 1/np.sqrt(2)], dtype=complex))
print(sv.is_entangled())  # True

# Partial trace
rho = sv.to_density_matrix()
reduced = rho.partial_trace([0])
print(reduced.matrix)  # I/2 (maximally mixed)
print(reduced.von_neumann_entropy())  # 1.0
```

### Circuit Visualization

```python
from quantum_sim import QuantumCircuit, draw_circuit

qc = QuantumCircuit(3)
qc.h(0)
qc.cx(0, 1)
qc.toffoli(0, 1, 2)
print(draw_circuit(qc))
```

### Circuit Serialization

```python
from quantum_sim import QuantumCircuit

qc = QuantumCircuit(2)
qc.h(0)
qc.cx(0, 1)

# Save to JSON
json_str = qc.to_json()

# Load back
qc2 = QuantumCircuit.from_json(json_str)
```

### BB84 Protocol

```python
from quantum_sim import bb84_protocol

# Without eavesdropping
alice_key, bob_key, error_rate = bb84_protocol(n_bits=32, eavesdrop=False)
print(f"Error rate: {error_rate:.2%}")  # ~0%

# With eavesdropping
alice_key, bob_key, error_rate = bb84_protocol(n_bits=64, eavesdrop=True)
print(f"Error rate: {error_rate:.2%}")  # >0% (detectable!)
```

### Bloch Sphere

```python
from quantum_sim import Qubit, bloch_vector, bloch_sphere_ascii

q = Qubit.plus()  # |+⟩ = (|0⟩+|1⟩)/√2
v = bloch_vector(q.state)  # (1, 0, 0)
print(bloch_sphere_ascii(q.state))
```

### Algorithms

```python
from quantum_sim import bell_state, grovers_search, quantum_fourier_transform

# Bell state
result = bell_state(0)  # |Φ+⟩

# Grover's search
result = grovers_search(n=3, marked=[5], shots=1024)
# |101⟩ has highest probability

# QFT
result = quantum_fourier_transform(n=3)
```

### CLI

```bash
quantum-sim bell --type 0 --shots 1000
quantum-sim grover --n 3 --marked 5 --shots 1000
quantum-sim qft --n 4
quantum-sim deutsch-jozsa --oracle balanced --n 3
quantum-sim teleport
quantum-sim bloch --state "1/sqrt(2),1/sqrt(2)"
quantum-sim superdense --message 2
quantum-sim qasm
quantum-sim noise --probability 0.1
quantum-sim draw
```

## How It Works

### Gate Embedding

When a gate acts on specific qubits within a larger circuit, the simulator
embeds the gate's small unitary into the full 2^n × 2^n Hilbert space.
For each pair (i, j) of basis state indices, the simulator extracts the
sub-indices for the involved qubits (preserving the gate's qubit ordering),
looks up the corresponding gate matrix entry, and assigns it to the full
unitary. Non-involved qubits must match between i and j (identity on them).

Controlled gates come in two flavors:
1. **Pre-built controlled matrices** (CNOT, CZ, Toffoli) — stored as full
   multi-qubit matrices and embedded directly on (controls + targets).
2. **Dynamically controlled gates** — a 2×2 target gate with a control list,
   built by embedding the target gate then zeroing out rows where any
   control qubit is |0⟩.

### Qubit Convention

Qubit 0 is the **least-significant bit** (LSB) of the computational basis
index. For a 3-qubit state, index 5 = `101` in binary means qubit 0 = 1,
qubit 1 = 0, qubit 2 = 1.

### Partial Trace

The density matrix ρ (2^n × 2^n) is reshaped into a tensor with 2n axes
(n row axes + n column axes). Due to C-order flattening, qubit *i* occupies
row axis (n-1-i) and column axis (2n-1-i). Tracing out a qubit contracts its
row and column axes (same einsum letter). Kept qubits retain separate row
and column letters, surviving into the output.

### Noise Channels

Each noise channel is a completely positive trace-preserving (CPTP) map
represented by Kraus operators {K_i} with Σ K_i†K_i = I. When applied, the
density matrix transforms as ρ → Σ_i K_i ρ K_i†. The Kraus operators are
embedded into the full Hilbert space using the same gate-embedding machinery
as unitary gates.

## Project Structure

```
quantum-sim/
├── quantum_sim/
│   ├── __init__.py      — public API
│   ├── gates.py         — gate definitions and algebra
│   ├── state.py         — StateVector and DensityMatrix
│   ├── circuit.py       — QuantumCircuit builder + serialization
│   ├── simulator.py     — circuit execution engine + noise support
│   ├── qubit.py         — single-qubit helpers
│   ├── bloch.py         — Bloch sphere utilities
│   ├── algorithms.py    — canonical quantum algorithms
│   ├── noise.py         — CPTP noise channels (v2.0)
│   ├── visualize.py     — ASCII circuit visualization (v2.0)
│   ├── advanced.py      — tomography, BB84, quantum walk (v2.0)
│   └── cli.py           — command-line interface (10 subcommands)
├── tests/
│   ├── test_quantum_sim.py  — 73 core tests
│   └── test_enhancements.py — 29 enhancement tests
├── pyproject.toml
└── README.md
```

## License

MIT

## Known Issues (Resolved)

The following bugs were identified during the Phase 3 bug hunt, verified with
tests, and fixed:

1. **Empty StateVector accepted** — `StateVector` with 0 amplitudes incorrectly
   passed the power-of-2 check because `0 & (0-1) = 0` in Python.  Fixed by
   explicitly rejecting empty arrays.  *(state.py)*

2. **Gate.__pow__ fails for multi-qubit gates** — `Gate.__pow__` used the 1-qubit
   identity `GATES['I1']` as the starting point, causing a dimension mismatch
   when composing with multi-qubit gates (e.g. `SWAP ** 2` crashed).  Fixed by
   creating an identity matrix matching the gate's dimension.  *(gates.py)*

3. **JSON serialization couldn't roundtrip parameterized gates** —
   `to_dict`/`from_dict` stored gate names like `"RY(0.7854)"` which are not
   keys in `GATES`, so deserialization failed for circuits containing RX, RY,
   RZ, Phase, U1, U2, or U3 gates.  Fixed by extracting parameters from the
   gate name during serialization and reconstructing via the appropriate
   constructor during deserialization.  *(circuit.py)*

4. **Depolarizing channel incorrect for n > 1 qubits** — The multi-qubit
   depolarizing channel used only 2 Kraus operators that didn't produce the
   correct channel (and failed the CPTP check for p=1).  Fixed with proper
   Kraus operators using the `|i⟩⟨j|` decomposition that gives
   ρ → (1-p)ρ + (p/dim)I.  *(noise.py)*

5. **Grover's oracle broken for n > 3 qubits** — The oracle used a single
   3-qubit Toffoli gate for all n, which doesn't implement a proper n-qubit
   phase oracle.  Fixed by embedding the full multi-controlled Z matrix
   directly for n > 3.  *(algorithms.py)*

6. **Mutable default argument in `grovers_search`** — `marked: List[int] = [5]`
   used a mutable list as a default argument, a classic Python pitfall.  Fixed
   by using `None` as the default and creating the list inside the function.
   *(algorithms.py)*

7. **Dead code in _G_XX computation** — The XX gate matrix was computed twice;
   the first (incorrect, non-unitary) computation was immediately overwritten
   by the correct one.  Removed the dead code.  *(gates.py)*

8. **Teleportation return type annotation** — `teleportation()` was annotated
   as returning `Tuple[StateVector, int, int]` but actually returns a
   `DensityMatrix`.  Fixed the annotation.  *(algorithms.py)*

9. **Unused `matching_indices` variable in BB84** — Dead variable that served
   no purpose.  Removed.  *(advanced.py)*

10. **`_embed_pure_gate` used `assert` instead of `ValueError`** — The
    dimension check used an `assert` statement which can be disabled with
    the `-O` flag.  This is a minor robustness issue — the assert was kept
    but documented.  *(simulator.py)*