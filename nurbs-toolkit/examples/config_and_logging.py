"""Example: configuration and logging."""
from nurbs import NURBSConfig, get_logger

# Create a custom configuration.
cfg = NURBSConfig()
cfg.tessellation.curve_samples = 500
cfg.tessellation.surface_samples_u = 100
cfg.tessellation.surface_samples_v = 100
cfg.export.format = "stl_binary"
cfg.export.precision = 8
cfg.fitting.degree = 5
cfg.fitting.num_control_points = 10
cfg.logging.level = "DEBUG"

# Save to JSON.
cfg.save("nurbs_config.json")
print("Saved config to nurbs_config.json")

# Print as JSON.
print("\n=== Configuration ===")
print(cfg.to_json(indent=2))

# Load from file.
cfg2 = NURBSConfig.from_file("nurbs_config.json")
assert cfg2.tessellation.curve_samples == 500
assert cfg2.export.format == "stl_binary"
print(f"\nLoaded: tessellation.curve_samples = {cfg2.tessellation.curve_samples}")
print(f"Loaded: export.format = {cfg2.export.format}")

# Set up logging.
log = get_logger("nurbs.example", level="DEBUG")
log.info("This is an info message")
log.debug("This is a debug message")
log.warning("This is a warning")