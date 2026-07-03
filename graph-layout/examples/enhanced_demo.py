import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from graph_layout import (
    petersen_graph, hypercube_graph, erdos_renyi, barabasi_albert,
    watts_strogatz, FruchtermanReingold, SVGRenderer, LayoutMetrics,
    scale_to_fit, AnimatedSVGRenderer,
)

# Test generators
print("Petersen:", petersen_graph())
print("Hypercube Q3:", hypercube_graph(3))
print("Erdos-Renyi(20, 0.2):", erdos_renyi(20, 0.2, seed=42))
print("Barabasi-Albert(20, 3):", barabasi_albert(20, 3, seed=42))
print("Watts-Strogatz(20, 4, 0.3):", watts_strogatz(20, 4, 0.3, seed=42))

# Test frame capture
g = petersen_graph()
algo = FruchtermanReingold(seed=42, iterations=100, capture_frames=True, frame_interval=10)
algo.layout(g)
print(f"\nCaptured {len(algo.frames)} frames for animation")

# Test animated SVG
AnimatedSVGRenderer().save(algo.frames, g, os.path.join(os.path.dirname(__file__), "petersen_animated.svg"))
print("Saved petersen_animated.svg")

# Test scale_to_fit
g2 = erdos_renyi(15, 0.3, seed=42)
FruchtermanReingold(seed=42).layout(g2)
scale_to_fit(g2, 800, 600)
print(f"\nScaled ER graph to fit 800x600, metrics:")
m = LayoutMetrics.all_metrics(g2)
for k, v in m.items():
    print(f"  {k}: {v:.4f}")