# Contributing

Thanks for improving Stitch Planner. Keep changes focused on raster-to-stitch planning and preserve the dependency-free runtime.

1. Use Python 3.10 or newer.
2. Create an isolated environment and install the project: `python3 -m venv .venv`, `. .venv/bin/activate`, then `python3 -m pip install -e . pytest`.
3. Run `python3 -m pytest` and exercise the CLI example in the README.
4. Add regression tests for behavior changes and update the README when commands or limitations change.
5. Keep generated SVGs and virtual environments out of commits.

Please include a concise explanation of the use case and test results in pull requests.
