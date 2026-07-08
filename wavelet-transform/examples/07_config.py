"""Example: Configuration files for reproducible pipelines.

Shows how to create, save, load, and validate configuration files
in JSON, YAML, and TOML formats.
"""
import sys, os, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from wavelet import WaveletConfig, load_config, save_config, DenoiseConfig, CompressConfig


def main():
    # Create a custom configuration
    config = WaveletConfig(
        wavelet="sym4",
        level=4,
        transform="dwt",
        signal="doppler",
        signal_length=512,
        noise=0.3,
        denoise=DenoiseConfig(method="bayes", threshold_func="soft",
                              cycle_spinning=True, n_shifts=16),
        compress=CompressConfig(keep_ratio=0.1),
    )

    print("Configuration:")
    print(f"  Wavelet: {config.wavelet}")
    print(f"  Level: {config.level}")
    print(f"  Transform: {config.transform}")
    print(f"  Signal: {config.signal}")
    print(f"  Denoise: method={config.denoise.method}, "
          f"func={config.denoise.threshold_func}, "
          f"cycle_spin={config.denoise.cycle_spinning}")
    print(f"  Compress: keep_ratio={config.compress.keep_ratio}")

    # Validate
    errors = config.validate()
    if errors:
        print(f"\nValidation errors: {errors}")
    else:
        print("\nValidation: PASSED")

    # Save in different formats
    with tempfile.TemporaryDirectory() as tmpdir:
        for ext in [".json", ".toml"]:
            path = os.path.join(tmpdir, f"config{ext}")
            save_config(config, path)
            print(f"\nSaved to {path}")

            loaded = load_config(path)
            print(f"Loaded: wavelet={loaded.wavelet}, level={loaded.level}")
            print(f"  denoise.method={loaded.denoise.method}")
            print(f"  compress.keep_ratio={loaded.compress.keep_ratio}")
            assert loaded.wavelet == config.wavelet
            assert loaded.level == config.level

    # Example YAML config (requires PyYAML)
    print("\n  YAML support requires: pip install pyyaml")


if __name__ == "__main__":
    main()