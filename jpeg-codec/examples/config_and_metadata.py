"""Example: Using config files and metadata inspection.

Demonstrates loading encoding settings from a JSON config file
and inspecting JPEG metadata after encoding.
"""

import json
import tempfile
import os
import numpy as np
from jpeg_codec import encode, decode, get_info
from jpeg_codec.config import EncodingConfig, save_config, load_config


def main():
    # Create a test image
    img = np.random.RandomState(42).randint(
        0, 256, (64, 64, 3), dtype=np.uint8
    )

    # Create a config file
    config_path = os.path.join(tempfile.gettempdir(), "jpeg_config.json")
    cfg = EncodingConfig(
        quality=92,
        sampling="4:4:4",
        comment="Config file demo",
        dpi=(300, 300),
    )
    save_config(cfg, config_path)
    print(f"Config saved to: {config_path}")
    print(f"Config contents:")
    with open(config_path) as f:
        print(f"  {json.dumps(json.load(f), indent=2)}")

    # Load and use the config
    loaded_cfg = load_config(config_path)
    kwargs = {k: v for k, v in loaded_cfg.to_dict().items()
              if k != "optimize_huffman"}
    jpeg = encode(img, **kwargs)

    # Inspect the resulting JPEG
    info = get_info(jpeg)
    print(f"\nJPEG metadata:")
    print(f"  Dimensions: {info.width}x{info.height}")
    print(f"  Components: {info.num_components}")
    print(f"  Sampling:   {info.sampling_string}")
    print(f"  Process:    {info.encoding_process}")
    print(f"  Comment:    {info.comment}")
    print(f"  DPI:        {info.x_density}x{info.y_density}")
    print(f"  Markers:    {len(info.markers)}")
    for name, offset in info.markers:
        print(f"    {name:12s} at offset {offset}")

    # Clean up
    os.unlink(config_path)


if __name__ == "__main__":
    main()