#!/usr/bin/env python3
"""Quick test script for the enhanced boids simulation."""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from boids.simulation import BoidSimulation
from boids.config import SimulationConfig, get_preset, list_presets, save_config, load_config
from boids.renderer import SVGRenderer, TrailSVGRenderer, PPMRenderer, ASCIIRenderer

# Test presets
print("Presets:", list_presets())

# Test default config
cfg = SimulationConfig(num_boids=50, trail_length=10)
sim = BoidSimulation(cfg)
sim.add_obstacle(400, 300, 40)
sim.add_predator(100, 100)
sim.set_goal(600, 400)

for _ in range(20):
    sim.step()

stats = sim.stats()
print(f"Stats: alignment={stats['alignment']:.3f}, spread={stats['spread']:.1f}, centroid={stats['centroid']}")

# Test preset
cfg2 = get_preset("fast-murmuration")
print(f"Preset config: num_boids={cfg2.num_boids}, max_speed={cfg2.max_speed}, wrap={cfg2.use_wrap}")
sim2 = BoidSimulation(cfg2)
for _ in range(10):
    sim2.step()
print(f"Preset sim alignment: {sim2.stats()['alignment']:.3f}")

# Test save/load
sim.save("/tmp/test_save.json")
sim3 = BoidSimulation.load("/tmp/test_save.json")
print(f"Loaded: {len(sim3.boids)} boids, {len(sim3.predators)} predators, {len(sim3.obstacles)} obstacles, tick={sim3.tick}")

# Test config save/load
save_config(cfg, "/tmp/test_config.json")
cfg_loaded = load_config("/tmp/test_config.json")
print(f"Config loaded: num_boids={cfg_loaded.num_boids}, trail_length={cfg_loaded.trail_length}")

# Test renderers
os.makedirs("/tmp/boids_out", exist_ok=True)
SVGRenderer().render(sim, "/tmp/boids_out/frame.svg")
TrailSVGRenderer().render(sim, "/tmp/boids_out/trail.svg")
PPMRenderer().render(sim, "/tmp/boids_out/frame.ppm", scale=0.5)
ascii_out = ASCIIRenderer(cols=60, rows=20).render(sim)
print("ASCII render length:", len(ascii_out))
print("All tests passed!")