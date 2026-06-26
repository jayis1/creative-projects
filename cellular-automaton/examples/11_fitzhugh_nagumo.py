"""FitzHugh-Nagumo spiral waves.

The FitzHugh-Nagumo model is an excitable-medium CA that produces
spiral wave patterns, similar to those seen in Belousov-Zhabotinsky
reactions or cardiac tissue.
"""

from cellular_automaton import FitzHughNagumo, render_continuous_ascii

fhn = FitzHughNagumo(50, 25)
fhn.seed_spiral(25, 12)
fhn.step(300)

print(f"FitzHugh-Nagumo after {fhn.step_count} steps:")
print(render_continuous_ascii(fhn.states[0], chars=" .:-=+*#%@"))