"""
Command-line interface for the Waveform Synthesizer.

Usage:
    waveform-synth generate --waveform sine --frequency 440 --duration 2 --output out.wav
    waveform-synth fm --carrier 440 --modulator 880 --index 2.0 --duration 2 --output out.wav
    waveform-synth scale --root C --scale major --waveform triangle --duration 4 --output out.wav
    waveform-synth visualize --input input.wav
"""

import argparse
import math
import sys
import os

from .core import Oscillator, Waveform, normalize, mix
from .envelope import ADSR
from .fm import FMSynth, FMPreset
from .effects import EffectsChain, Effect, EffectType
from .export import WavWriter
from .visualize import ascii_waveform
from .notes import generate_scale, generate_chord, SCALES, CHORDS
from .composition import Track, Composition


def main():
    parser = argparse.ArgumentParser(
        prog="waveform-synth",
        description="Digital audio synthesizer — generate, process, and export waveforms",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- generate subcommand ---
    gen_parser = subparsers.add_parser("generate", help="Generate a single waveform")
    gen_parser.add_argument("--waveform", "-w", choices=[w.value for w in Waveform],
                           default="sine", help="Waveform type (default: sine)")
    gen_parser.add_argument("--frequency", "-f", type=float, default=440.0,
                           help="Frequency in Hz (default: 440)")
    gen_parser.add_argument("--amplitude", "-a", type=float, default=0.8,
                           help="Amplitude 0-1 (default: 0.8)")
    gen_parser.add_argument("--duration", "-d", type=float, default=2.0,
                           help="Duration in seconds (default: 2)")
    gen_parser.add_argument("--sample-rate", "-r", type=int, default=44100,
                           help="Sample rate (default: 44100)")
    gen_parser.add_argument("--harmonics", type=str, default=None,
                           help="Harmonics as ratio:amp pairs, e.g. '2:0.5,3:0.3'")
    gen_parser.add_argument("--envelope", "-e", type=str, default=None,
                           help="ADSR as attack,decay,sustain,release (e.g. '0.01,0.1,0.7,0.3')")
    gen_parser.add_argument("--effects", type=str, default=None,
                           help="Effects chain: gain:1.5,delay:0.3:0.3:0.5,distortion:2")
    gen_parser.add_argument("--output", "-o", type=str, default=None,
                           help="Output WAV file path")
    gen_parser.add_argument("--visualize", "-v", action="store_true",
                           help="Show ASCII waveform visualization")

    # --- fm subcommand ---
    fm_parser = subparsers.add_parser("fm", help="FM synthesis")
    fm_parser.add_argument("--carrier", "-c", type=float, default=440.0,
                          help="Carrier frequency in Hz (default: 440)")
    fm_parser.add_argument("--modulator", "-m", type=float, default=440.0,
                          help="Modulator frequency in Hz (default: 440)")
    fm_parser.add_argument("--index", "-i", type=float, default=2.0,
                          help="Modulation index (default: 2.0)")
    fm_parser.add_argument("--carrier-waveform", choices=[w.value for w in Waveform],
                          default="sine", help="Carrier waveform (default: sine)")
    fm_parser.add_argument("--modulator-waveform", choices=[w.value for w in Waveform],
                          default="sine", help="Modulator waveform (default: sine)")
    fm_parser.add_argument("--amplitude", "-a", type=float, default=0.8,
                          help="Amplitude (default: 0.8)")
    fm_parser.add_argument("--duration", "-d", type=float, default=2.0,
                          help="Duration in seconds (default: 2)")
    fm_parser.add_argument("--preset", "-p", type=str, default=None,
                          choices=["bellish", "brassish", "woodwind", "bass", "e_piano"],
                          help="Use a preset (overrides other options)")
    fm_parser.add_argument("--sample-rate", "-r", type=int, default=44100,
                          help="Sample rate (default: 44100)")
    fm_parser.add_argument("--envelope", "-e", type=str, default=None,
                          help="ADSR as attack,decay,sustain,release")
    fm_parser.add_argument("--output", "-o", type=str, default=None,
                          help="Output WAV file path")
    fm_parser.add_argument("--visualize", "-v", action="store_true",
                          help="Show ASCII waveform visualization")

    # --- scale subcommand ---
    scale_parser = subparsers.add_parser("scale", help="Generate a musical scale")
    scale_parser.add_argument("--root", type=str, default="C",
                            help="Root note (default: C)")
    scale_parser.add_argument("--scale", type=str, default="major",
                            choices=list(SCALES.keys()),
                            help="Scale type (default: major)")
    scale_parser.add_argument("--octave", type=int, default=4,
                            help="Starting octave (default: 4)")
    scale_parser.add_argument("--waveform", "-w", choices=[w.value for w in Waveform],
                            default="sine", help="Waveform type (default: sine)")
    scale_parser.add_argument("--note-duration", type=float, default=0.4,
                            help="Duration per note in seconds (default: 0.4)")
    scale_parser.add_argument("--sample-rate", "-r", type=int, default=44100,
                            help="Sample rate (default: 44100)")
    scale_parser.add_argument("--output", "-o", type=str, default=None,
                            help="Output WAV file path")
    scale_parser.add_argument("--visualize", "-v", action="store_true",
                            help="Show ASCII waveform visualization")

    # --- visualize subcommand ---
    viz_parser = subparsers.add_parser("visualize", help="Visualize a WAV file")
    viz_parser.add_argument("--input", "-i", type=str, required=True,
                          help="Input WAV file path")
    viz_parser.add_argument("--width", type=int, default=80,
                          help="Display width (default: 80)")
    viz_parser.add_argument("--height", type=int, default=20,
                          help="Display height (default: 20)")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "generate":
        _cmd_generate(args)
    elif args.command == "fm":
        _cmd_fm(args)
    elif args.command == "scale":
        _cmd_scale(args)
    elif args.command == "visualize":
        _cmd_visualize(args)


def _parse_envelope(envelope_str: str, sample_rate: int) -> ADSR:
    """Parse an ADSR envelope string like '0.01,0.1,0.7,0.3'."""
    parts = [float(x) for x in envelope_str.split(",")]
    if len(parts) != 4:
        raise ValueError(f"ADSR must have 4 values (a,d,s,r), got {len(parts)}")
    return ADSR(attack=parts[0], decay=parts[1], sustain=parts[2], release=parts[3],
                sample_rate=sample_rate)


def _parse_effects(effects_str: str) -> EffectsChain:
    """Parse an effects chain string."""
    chain = EffectsChain()
    for effect_def in effects_str.split(","):
        parts = effect_def.split(":")
        effect_name = parts[0]
        if effect_name == "gain":
            amount = float(parts[1]) if len(parts) > 1 else 1.0
            chain.add(Effect(EffectType.GAIN, amount=amount))
        elif effect_name == "delay":
            time = float(parts[1]) if len(parts) > 1 else 0.3
            feedback = float(parts[2]) if len(parts) > 2 else 0.3
            mix = float(parts[3]) if len(parts) > 3 else 0.5
            chain.add(Effect(EffectType.DELAY, time=time, feedback=feedback, mix=mix))
        elif effect_name == "distortion":
            drive = float(parts[1]) if len(parts) > 1 else 2.0
            chain.add(Effect(EffectType.DISTORTION, drive=drive))
        elif effect_name == "lowpass":
            cutoff = float(parts[1]) if len(parts) > 1 else 1000.0
            chain.add(Effect(EffectType.LOWPASS, cutoff=cutoff))
        elif effect_name == "highpass":
            cutoff = float(parts[1]) if len(parts) > 1 else 200.0
            chain.add(Effect(EffectType.HIGHPASS, cutoff=cutoff))
        elif effect_name == "tremolo":
            rate = float(parts[1]) if len(parts) > 1 else 5.0
            depth = float(parts[2]) if len(parts) > 2 else 0.5
            chain.add(Effect(EffectType.TREMOLO, rate=rate, depth=depth))
        elif effect_name == "flanger":
            rate = float(parts[1]) if len(parts) > 1 else 0.5
            depth = float(parts[2]) if len(parts) > 2 else 0.002
            chain.add(Effect(EffectType.FLANGER, rate=rate, depth=depth))
    return chain


def _cmd_generate(args):
    """Handle the 'generate' subcommand."""
    waveform = Waveform(args.waveform)

    # Parse harmonics
    harmonics = None
    if args.harmonics:
        harmonics = []
        for pair in args.harmonics.split(","):
            ratio, amp = pair.split(":")
            harmonics.append((float(ratio), float(amp)))

    osc = Oscillator(
        waveform=waveform,
        frequency=args.frequency,
        amplitude=args.amplitude,
        sample_rate=args.sample_rate,
        harmonics=harmonics,
    )

    samples = osc.generate(args.duration)

    # Apply envelope
    if args.envelope:
        env = _parse_envelope(args.envelope, args.sample_rate)
        samples = env.apply(samples, note_duration=args.duration)

    # Normalize
    samples = normalize(samples)

    # Apply effects
    if args.effects:
        chain = _parse_effects(args.effects)
        samples = chain.process(samples, args.sample_rate)
        samples = normalize(samples)

    # Visualize
    if args.visualize:
        print(ascii_waveform(samples, title=f"{waveform.value} @ {args.frequency}Hz"))

    # Export
    if args.output:
        writer = WavWriter(sample_rate=args.sample_rate)
        writer.write(args.output, samples)
        print(f"WAV written to {args.output} ({len(samples)} samples, {args.duration:.2f}s)")
    elif not args.visualize:
        print(f"Generated {len(samples)} samples ({args.duration:.2f}s)")
        print("Use --output to save as WAV or --visualize to display")


def _cmd_fm(args):
    """Handle the 'fm' subcommand."""
    carrier_wf = Waveform(args.carrier_waveform)
    modulator_wf = Waveform(args.modulator_waveform)

    if args.preset:
        presets = {
            "bellish": FMPreset.bellish,
            "brassish": FMPreset.brassish,
            "woodwind": FMPreset.woodwind,
            "bass": FMPreset.bass,
            "e_piano": FMPreset.e_piano,
        }
        synth = presets[args.preset](carrier_freq=args.carrier, sample_rate=args.sample_rate)
    else:
        synth = FMSynth(
            carrier_freq=args.carrier,
            modulator_freq=args.modulator,
            modulation_index=args.index,
            carrier_waveform=carrier_wf,
            modulator_waveform=modulator_wf,
            amplitude=args.amplitude,
            sample_rate=args.sample_rate,
        )

    samples = synth.generate(args.duration)

    # Apply envelope
    if args.envelope:
        env = _parse_envelope(args.envelope, args.sample_rate)
        samples = env.apply(samples, note_duration=args.duration)

    samples = normalize(samples)

    # Visualize
    if args.visualize:
        print(ascii_waveform(samples, title=f"FM: {args.carrier}Hz carrier, {args.modulator}Hz modulator"))

    # Export
    if args.output:
        writer = WavWriter(sample_rate=args.sample_rate)
        writer.write(args.output, samples)
        print(f"WAV written to {args.output} ({len(samples)} samples, {args.duration:.2f}s)")
    elif not args.visualize:
        print(f"Generated {len(samples)} samples ({args.duration:.2f}s)")
        print("Use --output to save as WAV or --visualize to display")


def _cmd_scale(args):
    """Handle the 'scale' subcommand."""
    waveform = Waveform(args.waveform)
    freqs = generate_scale(args.root, args.scale, args.octave)

    comp = Composition(sample_rate=args.sample_rate, title=f"{args.root} {args.scale} scale")
    track = Track(waveform=waveform, sample_rate=args.sample_rate)

    for freq in freqs:
        osc = Oscillator(waveform=waveform, frequency=freq, amplitude=0.7, sample_rate=args.sample_rate)
        note_samples = osc.generate(args.note_duration)
        note_samples = normalize(note_samples)
        track.add_note(freq_to_nearest_note(freq), args.note_duration)

    # Actually, let's just render the scale directly
    samples = []
    for freq in freqs:
        osc = Oscillator(waveform=waveform, frequency=freq, amplitude=0.7, sample_rate=args.sample_rate)
        note_samples = osc.generate(args.note_duration)
        note_samples = normalize(note_samples, target_peak=0.7)
        samples.extend(note_samples)

    # Small gap between notes
    gap = [0.0] * int(0.02 * args.sample_rate)
    final_samples = []
    for i, note_samples in enumerate(
        [normalize(Oscillator(waveform=waveform, frequency=f, amplitude=0.7,
                              sample_rate=args.sample_rate).generate(args.note_duration),
                      target_peak=0.7)
         for f in freqs]):
        final_samples.extend(note_samples)
        if i < len(freqs) - 1:
            final_samples.extend(gap)

    final_samples = normalize(final_samples)

    # Visualize
    if args.visualize:
        print(ascii_waveform(final_samples, title=f"{args.root} {args.scale} scale"))

    # Export
    if args.output:
        writer = WavWriter(sample_rate=args.sample_rate)
        writer.write(args.output, final_samples)
        print(f"WAV written to {args.output} ({len(final_samples)} samples)")
    elif not args.visualize:
        print(f"Generated {args.root} {args.scale} scale ({len(freqs)} notes)")
        print("Use --output to save as WAV or --visualize to display")


def freq_to_nearest_note(freq: float) -> str:
    """Convert a frequency to the nearest note name (approximate)."""
    from .notes import NOTE_NAMES, A4_MIDI, A4_FREQ
    if freq <= 0:
        return "C4"
    midi = int(round(12 * math.log2(freq / A4_FREQ) + A4_MIDI))
    octave = (midi // 12) - 1
    note_idx = midi % 12
    return f"{NOTE_NAMES[note_idx]}{octave}"


def _cmd_visualize(args):
    """Handle the 'visualize' subcommand."""
    samples, sample_rate, num_channels, bits_per_sample = WavWriter.samples_from_wav(args.input)
    print(ascii_waveform(samples[:min(len(samples), 44100 * 10)],  # Limit to 10 seconds
                        width=args.width, height=args.height,
                        title=args.input))
    print(f"\nSample rate: {sample_rate} Hz, Channels: {num_channels}, Bits: {bits_per_sample}")
    print(f"Duration: {len(samples) / sample_rate:.2f}s, Samples: {len(samples)}")


if __name__ == "__main__":
    main()