"""Extended drum patterns library — additional styles beyond the core set.

Provides more drum patterns: jungle, garage, techno, trap, funk, and more.
"""

from __future__ import annotations

from sequencer.patterns import Pattern, Step

# GM Drum Map (MIDI note numbers)
BD = 36    # Bass Drum (Kick)
SN = 38    # Snare
CHH = 42   # Closed Hi-Hat
OHH = 46   # Open Hi-Hat
CRASH = 49 # Crash Cymbal
RIDE = 51  # Ride Cymbal
TOM_H = 50 # High Tom
TOM_M = 47 # Mid Tom
TOM_L = 45 # Low Tom
CLAP = 39  # Hand Clap
RIM = 37   # Rimshot
COWBELL = 56 # Cowbell


EXTENDED_DRUM_STYLES = {
    "jungle": {
        "description": "Fast jungle/DnB breakbeat (160+ BPM)",
        "pattern": [0, 3, 6, 10, 12],  # kick positions
        "snare": [4, 12],
        "hh": "even_16th",
    },
    "garage": {
        "description": "2-step garage pattern",
        "pattern": [0, 10],
        "snare": [4, 12],
        "hh": "even_16th",
    },
    "techno": {
        "description": "4/4 techno with offbeat hats",
        "pattern": [0, 4, 8, 12],
        "snare": [],
        "hh": "offbeat",
    },
    "trap": {
        "description": "Trap beat with rapid hats",
        "pattern": [0, 5, 10],
        "snare": [4, 12],
        "hh": "rapid_32nd",
    },
    "funk": {
        "description": "Funky drummers pattern",
        "pattern": [0, 6, 10],
        "snare": [4, 12],
        "hh": "even_16th",
    },
    "reggaeton": {
        "description": "Reggaeton dembow rhythm",
        "pattern": [0, 4, 7, 11],
        "snare": [3, 7, 11, 15],
        "hh": "even_8th",
    },
    "dub": {
        "description": "Dub/reggae with heavy offbeats",
        "pattern": [0, 8],
        "snare": [4, 12],
        "hh": "offbeat_heavy",
    },
    "samba": {
        "description": "Samba rhythm pattern",
        "pattern": [0, 6, 10, 12],
        "snare": [4, 12],
        "hh": "samba",
    },
}


def extended_drum_pattern(style: str, length: int = 16) -> Pattern:
    """Generate an extended drum pattern style.

    Args:
        style: Style name from EXTENDED_DRUM_STYLES or a custom style
        length: Pattern length in 16th notes

    Returns:
        A Pattern with the drum pattern
    """
    if style not in EXTENDED_DRUM_STYLES:
        # Fall back to the standard drum_pattern
        from sequencer.generators import drum_pattern
        return drum_pattern(style, length)

    style_def = EXTENDED_DRUM_STYLES[style]
    steps = [Step() for _ in range(length)]

    kick_positions = style_def.get("pattern", [])
    snare_positions = style_def.get("snare", [])
    hh_style = style_def.get("hh", "even_16th")

    for i in range(length):
        if i in kick_positions:
            steps[i].notes.append(BD)
        if i in snare_positions:
            steps[i].notes.append(SN)

        # Hi-hat patterns
        if hh_style == "even_16th":
            steps[i].notes.append(CHH)
        elif hh_style == "even_8th":
            if i % 2 == 0:
                steps[i].notes.append(CHH)
        elif hh_style == "offbeat":
            if i % 2 == 1:
                steps[i].notes.append(CHH)
        elif hh_style == "offbeat_heavy":
            if i % 2 == 1:
                steps[i].notes.append(OHH)
            elif i % 4 == 0:
                steps[i].notes.append(CHH)
        elif hh_style == "rapid_32nd":
            # Every step gets a hat, but with velocity variation
            steps[i].notes.append(CHH)
        elif hh_style == "samba":
            if i % 2 == 0 or i in [1, 5, 9, 13]:
                steps[i].notes.append(CHH)

        steps[i].velocity = 100

    return Pattern(name=f"drums_{style}", steps=steps, length=length)


def list_extended_styles() -> dict[str, str]:
    """List all extended drum styles with descriptions.

    Returns:
        Dict mapping style name to description
    """
    return {name: info["description"] for name, info in EXTENDED_DRUM_STYLES.items()}