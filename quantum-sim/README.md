# Quantum Circuit Simulator (quantum-sim)

A from-scratch quantum circuit simulator with state-vector and density-matrix
backends, supporting multi-qubit gates, controlled operations, measurement,
entanglement detection, partial trace, and canonical quantum algorithms.

## Features

### Core
- **State-vector backend** — tracks pure states |ψ⟩ as 2^n complex vectors
- **Density-matrix backend** — tracks mixed states ρ as 2^n × 2^n matrices
- **20+ built-in gates** — X, Y, Z, H, S, T, SX, CNOT, CZ, SWAP, iSWAP,
  √SWAP, Toffoli (CCX), Fredkin (CSWAP), XX, I
- **Parameterized gates** — RX, RY, RZ, Phase, U1, U2, U3
- **Controlled gate construction** — `controlled(U)` builds C-U from any 1-qubit gate
- **Gate algebra** — tensor products, composition, dagger, powers
- **Unitarity verification** — every gate is checked to be unitary at construction

### State Operations
- Normalization, probability computation, expectation values
- Fidelity (pure and mixed), purity, von Neumann entropy
- Projective measurement with collapse and probabilistic sampling
- Entanglement detection via Schmidt rank (SVD)
- Partial trace with correct qubit ordering
- Bloch sphere vector computation and ASCII visualization

### Algorithms
- **Bell states** — all four Bell states (Φ±, Ψ±)
- **Quantum teleportation** — with classical correction
- **Deutsch-Jozsa** — constant vs balanced oracle discrimination
- **Grover's search** — amplitude amplification with optimal iterations
- **Quantum Fourier Transform (QFT)** — n-qubit QFT circuit
- **Superdense coding** — transmit 2 classical bits via 1 qubit

### Other
- OpenQASM 2.0 export
- CLI with subcommands (bell, grover, qft, deutsch-jozsa, teleport, bloch, superdense, qasm)
- 73 pytest tests

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
print(result.get_counts())  # {'00': 503, '11': 497}
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
(n row axes + n column axes). Qubit *i* occupies row axis (n-1-i) and
column axis (2n-1-i) due to C-order flattening. Tracing out a qubit
contracts its row and column axes (same einsum letter). Kept qubits
retain separate row and column letters, surviving into the output.

## Project Structure

```
quantum-sim/
├── quantum_sim/
│   ├── __init__.py      — public API
│   ├── gates.py         — gate definitions and algebra
│   ├── state.py         — StateVector and DensityMatrix
│   ├── circuit.py       — QuantumCircuit builder
│   ├── simulator.py     — circuit execution engine
│   ├── qubit.py         — single-qubit helpers
│   ├── bloch.py         — Bloch sphere utilities
│   ├── algorithms.py    — canonical quantum algorithms
│   └── cli.py           — command-line interface
├── tests/
│   └── test_quantum_sim.py  — 73 tests
├── pyproject.toml
└── README.md
```

## License

MIT