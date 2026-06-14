"""Generative algorithms for pattern creation."""

from __future__ import annotations
from typing import List, Optional, Tuple, Dict
from sequencer.scales import scale_notes, SCALE_INTERVALS, chord_notes
from sequencer.patterns import Pattern, Step
import random
import math


def euclidean_rhythm(beats: int, length: int, rotation: int = 0) -> List[bool]:
    """Generate a Euclidean rhythm using Björklund's algorithm.

    Distributes `beats` pulses as evenly as possible across `length` steps.

    Args:
        beats: Number of on-steps (pulses)
        length: Total number of steps
        rotation: Rotate the result by this many positions

    Returns:
        List of booleans where True = pulse
    """
    if beats <= 0:
        return [False] * length
    if beats >= length:
        return [True] * length

    # Björklund's algorithm
    groups = [[True] for _ in range(beats)] + [[False] for _ in range(length - beats)]
    while True:
        remaining = len(groups) - 1
        min_len = min(len(g) for g in groups)
        # Find how many groups have min_len
        short_count = sum(1 for g in groups if len(g) == min_len)
        if short_count >= remaining or min_len >= 2:
            break
        # Distribute short groups into longer ones
        new_groups = []
        i = 0
        while i < len(groups) and len(groups[i]) != min_len:
            new_groups.append(groups[i])
            i += 1
        j = len(groups) - 1
        while i < j and len(groups[j]) == min_len:
            new_groups.append(groups[i] + groups[j])
            i += 1
            j -= 1
        while i <= j:
            new_groups.append(groups[i])
            i += 1
        groups = new_groups

    result = []
    for g in groups:
        result.extend(g)

    # Rotate
    if rotation:
        rotation = rotation % length
        result = result[-rotation:] + result[:-rotation] if rotation else result

    # Pad or trim to exact length
    result = (result * ((length // len(result)) + 1))[:length]
    return result


def euclidean_pattern(
    beats: int,
    length: int,
    root: str = "C",
    scale: str = "pentatonic_minor",
    octave: int = 4,
    rotation: int = 0,
    velocity: int = 100,
    gate: float = 0.8,
) -> Pattern:
    """Create a pattern from a Euclidean rhythm with melodic content from a scale.

    Args:
        beats: Number of active steps
        length: Total pattern length
        root: Root note of the scale
        scale: Scale name
        octave: Starting octave
        rotation: Rotation offset for the rhythm
        velocity: Default velocity for active steps
        gate: Default gate length for active steps
    """
    rhythm = euclidean_rhythm(beats, length, rotation)
    notes = scale_notes(root, scale, 2, octave)
    steps = []
    note_idx = 0
    for active in rhythm:
        if active:
            s = Step(
                notes=[notes[note_idx % len(notes)]],
                velocity=velocity,
                gate=gate,
            )
            note_idx += 1
            steps.append(s)
        else:
            steps.append(Step())
    return Pattern(name=f"euc_{beats}_{length}", steps=steps, length=length)


def random_pattern(
    length: int = 16,
    density: float = 0.5,
    root: str = "C",
    scale: str = "pentatonic_minor",
    octave: int = 4,
    velocity_range: Tuple[int, int] = (70, 120),
    probability: float = 1.0,
) -> Pattern:
    """Generate a random pattern with given density.

    Args:
        length: Number of steps
        density: 0.0 = empty, 1.0 = every step filled
        root: Root note of scale
        scale: Scale name
        octave: Starting octave
        velocity_range: (min, max) for random velocities
        probability: Step trigger probability
    """
    notes = scale_notes(root, scale, 2, octave)
    steps = []
    for i in range(length):
        if random.random() < density:
            note = random.choice(notes)
            vel = random.randint(velocity_range[0], velocity_range[1])
            steps.append(Step(
                notes=[note],
                velocity=vel,
                gate=random.choice([0.5, 0.75, 0.8, 1.0]),
                probability=probability,
            ))
        else:
            steps.append(Step())
    return Pattern(name="random", steps=steps, length=length)


def markov_pattern(
    length: int = 16,
    root: str = "C",
    scale: str = "major",
    octave: int = 4,
    transition_matrix: Optional[Dict[int, Dict[int, float]]] = None,
    initial_note: Optional[int] = None,
    velocity: int = 100,
) -> Pattern:
    """Generate a melodic pattern using a Markov chain over scale degrees.

    Args:
        length: Number of steps
        root: Root note
        scale: Scale name
        octave: Starting octave
        transition_matrix: Dict mapping degree -> {next_degree: probability}.
                           If None, a simple stepwise motion preference is used.
        initial_note: Starting MIDI note. If None, uses scale root.
        velocity: Note velocity
    """
    notes = scale_notes(root, scale, 2, octave)

    if transition_matrix is None:
        # Default: prefer stepwise motion with occasional jumps
        n = len(notes)
        transition_matrix = {}
        for i in range(n):
            probs = {}
            total_weight = 0.0
            for j in range(n):
                distance = abs(i - j)
                if distance == 0:
                    weight = 2.0
                elif distance == 1:
                    weight = 5.0
                elif distance == 2:
                    weight = 2.0
                elif distance <= 4:
                    weight = 1.0
                else:
                    weight = 0.3
                probs[j] = weight
                total_weight += weight
            # Normalize
            transition_matrix[i] = {k: v / total_weight for k, v in probs.items()}

    current = initial_note if initial_note is not None else notes[0]
    # Find closest scale note
    current_idx = min(range(len(notes)), key=lambda i: abs(notes[i] - current))
    if initial_note is None:
        current_idx = 0

    steps = []
    for i in range(length):
        # Pick next note from transition matrix
        transitions = transition_matrix.get(current_idx, {})
        if not transitions:
            current_idx = random.randint(0, len(notes) - 1)
        else:
            choices = list(transitions.keys())
            weights = [transitions[c] for c in choices]
            total = sum(weights)
            weights = [w / total for w in weights]
            r = random.random()
            cumulative = 0.0
            current_idx = choices[0]
            for c, w in zip(choices, weights):
                cumulative += w
                if r <= cumulative:
                    current_idx = c
                    break

        steps.append(Step(notes=[notes[current_idx]], velocity=velocity))
        # Some steps are rests
        if random.random() < 0.2:
            steps[-1] = Step()  # empty step = rest

    return Pattern(name="markov", steps=steps, length=length)


def chord_pattern(
    chords: List[Tuple[str, str]],
    length_per_chord: int = 16,
    root: str = "C",
    scale: str = "major",
    octave: int = 3,
    arpeggiate: bool = False,
    velocity: int = 80,
) -> Pattern:
    """Generate a pattern from a chord progression.

    Args:
        chords: List of (root, quality) tuples, e.g. [("C", "maj7"), ("Am", "min7")]
        length_per_chord: Steps per chord
        root: Key root for context
        scale: Scale for context
        octave: Octave for chords
        arpeggiate: If True, arpeggiate chords instead of playing simultaneously
        velocity: Note velocity
    """
    all_steps = []
    for chord_root, quality in chords:
        cn = chord_notes(chord_root, quality, octave)
        if arpeggiate:
            for i in range(length_per_chord):
                note = cn[i % len(cn)]
                all_steps.append(Step(notes=[note], velocity=velocity, gate=0.8))
        else:
            # Hit on first step, sustain for length_per_chord
            all_steps.append(Step(notes=cn, velocity=velocity, gate=float(length_per_chord), tie=True))
            for i in range(length_per_chord - 1):
                all_steps.append(Step(tie=True))

    return Pattern(name="chords", steps=all_steps, length=len(all_steps))


def bassline_from_chords(
    chords: List[Tuple[str, str]],
    length_per_chord: int = 16,
    octave: int = 2,
    pattern_type: str = "steady",
) -> Pattern:
    """Generate a bassline pattern from a chord progression.

    Args:
        chords: List of (root, quality) tuples
        length_per_chord: Steps per chord
        octave: Bass octave
        pattern_type: "steady" = root on every beat, "walking" = walking bass
    """
    from sequencer.scales import note_to_midi
    all_steps = []

    for chord_root, quality in chords:
        root_note = note_to_midi(f"{chord_root}{octave}")
        cn = chord_notes(chord_root, quality, octave)

        if pattern_type == "steady":
            for i in range(length_per_chord):
                if i % 4 == 0:  # On each beat
                    all_steps.append(Step(notes=[root_note], velocity=100, gate=0.9))
                else:
                    all_steps.append(Step())
        elif pattern_type == "walking":
            for i in range(length_per_chord):
                note = cn[i % len(cn)]
                all_steps.append(Step(notes=[note], velocity=90 + random.randint(-10, 10), gate=0.8))
        else:
            for i in range(length_per_chord):
                all_steps.append(Step(notes=[root_note], velocity=100, gate=0.8))

    return Pattern(name="bass", steps=all_steps, length=len(all_steps))


def drum_pattern(
    style: str = "four_on_floor",
    length: int = 16,
) -> Pattern:
    """Generate a drum pattern with GM drum mapping.

    Uses GM drum notes: 36=Bass Drum, 38=Snare, 42=Closed HH, 46=Open HH,
    49=Crash, 51=Ride

    Args:
        style: Predefined drum pattern style
        length: Pattern length in 16th notes
    """
    BD = 36
    SN = 38
    CHH = 42
    OHH = 46

    steps = [Step() for _ in range(length)]

    if style == "four_on_floor":
        # Kick on beats 1, 5, 9, 13; Snare on 5, 13; HH on every even step
        for i in range(length):
            if i % 4 == 0:
                steps[i].notes.append(BD)
            if i % 8 == 4:
                steps[i].notes.append(SN)
            if i % 2 == 0:
                steps[i].notes.append(CHH)
            steps[i].velocity = 100

    elif style == "breakbeat":
        for i in range(length):
            if i in (0, 6, 10, 12):
                steps[i].notes.append(BD)
            if i in (4, 12):
                steps[i].notes.append(SN)
            if i % 2 == 0:
                steps[i].notes.append(CHH)
            steps[i].velocity = 100

    elif style == "hiphop":
        for i in range(length):
            if i in (0, 5, 10):
                steps[i].notes.append(BD)
            if i in (4, 12):
                steps[i].notes.append(SN)
            if i % 2 == 0:
                steps[i].notes.append(CHH)
            steps[i].velocity = 90 if CHH in steps[i].notes else 100

    elif style == "bossa":
        # Bossa nova pattern
        kick_pattern = [0, 3, 6, 10, 12]
        snare_pattern = [4, 8, 12, 14]
        for i in range(length):
            if i in kick_pattern:
                steps[i].notes.append(BD)
            if i in snare_pattern:
                steps[i].notes.append(SN)
            if i % 4 == 0 or i % 4 == 2:
                steps[i].notes.append(CHH)
            steps[i].velocity = 80

    elif style == "waltz":
        # 3/4 time feel
        for i in range(length):
            if i % 6 == 0:
                steps[i].notes.append(BD)
            if i % 6 == 3:
                steps[i].notes.append(SN)
            if i % 2 == 0:
                steps[i].notes.append(CHH)
            steps[i].velocity = 100

    else:
        # Default: simple kick + snare
        for i in range(length):
            if i % 8 == 0:
                steps[i].notes.append(BD)
            if i % 8 == 4:
                steps[i].notes.append(SN)
            steps[i].velocity = 100

    return Pattern(name=f"drums_{style}", steps=steps, length=length)


def morph_pattern(a: Pattern, b: Pattern, position: float) -> Pattern:
    """Morph between two patterns.

    Args:
        a: First pattern
        b: Second pattern
        position: 0.0 = pattern A, 1.0 = pattern B

    Returns:
        A new pattern blending the two
    """
    length = max(a.length, b.length)
    steps = []
    for i in range(length):
        step_a = a.get_step(i)
        step_b = b.get_step(i)
        if random.random() > position:
            # Use pattern A's step
            step = Step(
                notes=list(step_a.notes),
                velocity=step_a.velocity,
                gate=step_a.gate,
                probability=step_a.probability,
                tie=step_a.tie,
            )
        else:
            step = Step(
                notes=list(step_b.notes),
                velocity=step_b.velocity,
                gate=step_b.gate,
                probability=step_b.probability,
                tie=step_b.tie,
            )
        steps.append(step)

    return Pattern(name=f"morph_{a.name}_{b.name}", steps=steps, length=length)