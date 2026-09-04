#!/usr/bin/env sh
set -eu

python3 -m particle_life_sim snapshot \
  --preset aurora \
  --steps 40 \
  --dt 0.1 \
  --output examples/out/aurora-snapshot.json

python3 -m particle_life_sim resume \
  examples/out/aurora-snapshot.json \
  --steps 30 \
  --dt 0.1 \
  --save-snapshot examples/out/aurora-resumed.json

python3 -m particle_life_sim analyze \
  --config examples/aurora-variant.yaml \
  --steps 80 \
  --dt 0.1 \
  --output examples/out/aurora-analysis.json
