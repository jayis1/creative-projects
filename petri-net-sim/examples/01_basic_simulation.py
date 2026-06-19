"""Example: Basic simulation and analysis of a workflow net."""

from petri import PetriNet, Place, Transition, Simulator, ascii_marking
from petri import reachability_graph, compute_t_invariants, compute_p_invariants
from petri import is_reachable, is_reversible, analyze_boundedness, analyze_liveness

# Build a workflow net
net = PetriNet("workflow")
net.add_place(Place("start", initial=1))
net.add_place(Place("submitted", initial=0))
net.add_place(Place("reviewed", initial=0))
net.add_place(Place("end", initial=0))

net.add_transition(Transition("submit"))
net.add_transition(Transition("review"))
net.add_transition(Transition("approve"))
net.add_transition(Transition("reject"))

net.add_arc("start", "submit")
net.add_arc("submit", "submitted")
net.add_arc("submitted", "review")
net.add_arc("review", "reviewed")
net.add_arc("reviewed", "approve")
net.add_arc("reviewed", "reject")
net.add_arc("approve", "end")
net.add_arc("reject", "submitted")

print("=== Workflow Net ===")
print(f"Places: {list(net.places)}")
print(f"Transitions: {list(net.transitions)}")
print(f"Initial marking: {ascii_marking(net.initial_marking(), net)}")
print()

# Simulate
sim = Simulator(net, seed=42)
result = sim.random_walk(max_steps=20)
print(f"=== Simulation ===")
print(f"Steps fired: {result.steps_fired}")
print(f"Deadlocked: {result.deadlocked}")
print(f"Final marking: {ascii_marking(result.final_marking, net)}")
print()

# Reachability
rg = reachability_graph(net)
print(f"=== Reachability ===")
print(f"States: {rg.num_states}, Edges: {rg.num_edges}")
print(f"Deadlocks: {len(rg.deadlocks)}")
print()

# Invariants
print(f"=== Invariants ===")
t_invs = compute_t_invariants(net)
print(f"T-invariants: {t_invs}")
p_invs = compute_p_invariants(net)
print(f"P-invariants: {p_invs}")
print()

# Boundedness
b = analyze_boundedness(net)
print(f"=== Boundedness ===")
print(f"  {b}")
print()

# Liveness
l = analyze_liveness(net)
print(f"=== Liveness ===")
print(l)
print()

# Reversibility
rev = is_reversible(net)
print(f"=== Reversibility ===")
print(f"  Reversible: {rev}")
print()

# Reachability checking
print(f"=== Reachability Check ===")
print(f"  Can reach end=1: {is_reachable(net, {'end': 1})}")
print(f"  Can reach start=2: {is_reachable(net, {'start': 2})}")