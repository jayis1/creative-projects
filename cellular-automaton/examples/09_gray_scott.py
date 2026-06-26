"""Gray-Scott reaction-diffusion — spots preset.

Demonstrates continuous cellular automata with the Gray-Scott model.
The spots preset (F=0.025, k=0.060) produces stable circular spots.
"""

from cellular_automaton import GrayScott, render_continuous_ascii

gs = GrayScott.from_preset("spots", width=50, height=25)
gs.seed_square(25, 12, radius=6)
gs.step(500)

print(f"Gray-Scott 'spots' preset after {gs.step_count} steps:")
print(render_continuous_ascii(gs.states[1], chars=" .:-=+*#%@"))