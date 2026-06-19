"""Example: Colored Petri nets — modeling data-dependent concurrency."""

from petri.colored import (
    ColoredPetriNet, ColoredPlace, ColoredTransition,
    ColorSet, ArcInscription, INT, STRING,
)

# Model a simple data processing pipeline:
# Input: integers → double → filter even → output

cpn = ColoredPetriNet("data_pipeline")
cpn.add_place(ColoredPlace("input", color_set=INT, initial=[1, 2, 3, 4, 5]))
cpn.add_place(ColoredPlace("doubled", color_set=INT))
cpn.add_place(ColoredPlace("even_only", color_set=INT))
cpn.add_place(ColoredPlace("output", color_set=INT))

cpn.add_transition(ColoredTransition("double"))
cpn.add_transition(ColoredTransition("filter_even", guard=lambda b: b.get("x", 0) % 2 == 0))

# double: input -> doubled (transform x → 2x)
cpn.add_arc("input", "double", ArcInscription.identity("x"), direction="in")
cpn.add_arc("doubled", "double", ArcInscription.transform(lambda x: x * 2, "x"), direction="out")

# filter_even: doubled -> even_only (only pass even numbers)
cpn.add_arc("doubled", "filter_even", ArcInscription.identity("x"), direction="in")
cpn.add_arc("even_only", "filter_even", ArcInscription.identity("x"), direction="out")

print("=== Colored Petri Net: Data Pipeline ===")
print(cpn)
print()

marking = cpn.initial_marking()
print(f"Initial marking: {marking}")
print()

# Fire "double" repeatedly
step = 0
while cpn.is_enabled("double", marking):
    marking = cpn.fire("double", marking)
    step += 1
    print(f"  After double #{step}: input={marking.get('input', [])}, doubled={marking.get('doubled', [])}")

print()
print(f"Marking after doubling: {marking}")
print()

# Fire "filter_even" repeatedly
step = 0
while cpn.is_enabled("filter_even", marking):
    marking = cpn.fire("filter_even", marking)
    step += 1
    print(f"  After filter #{step}: doubled={marking.get('doubled', [])}, even_only={marking.get('even_only', [])}")

print()
print(f"Final marking: {marking}")
print(f"Even results: {marking.get('even_only', [])}")