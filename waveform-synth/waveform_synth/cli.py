"""
Command-line interface for the Waveform Synthesizer.

Usage:
    waveform-synth generate --waveform sine --frequency 440 --duration 2 --output out.wav
    waveform-synth fm --carrier 440 --modulator 880 --index 2.0 --duration 2 --output out.wav
    waveform-synth scale --root C --scale major --waveform triangle --duration 4 --output out.wav
    waveform-synth chord --root C --chord major --waveform sine --duration 2 --output out.wav
    waveform-synth analyze --input input.wav
    waveform-synth visualize --input input.wav
    waveform-synth preset --name ambient_pad --output out.wav
    waveform-synth config --file config.json --output out.wav
"""

import argparse
import logging
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
from .analysis import rms, peak_level, compute_stats
from .stereo import mono_to_stereo
from .config import SynthConfig, PRESETS, get_preset

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Configure logging for the CLI."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S',
    )


def main():
    parser = argparse.ArgumentParser(
        prog="waveform-synth",
        description="Digital audio synthesizer — generate, process, and export waveforms",
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--version', action='version', version='waveform-synth 4.0.0')

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ─── generate subcommand ────────────────────────────────────────
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
    gen_parser.add_argument("--visualize", "-V", action="store_true",
                           help="Show ASCII waveform visualization")
    gen_parser.add_argument("--analyze", "-A", action="store_true",
                           help="Print audio analysis statistics")

    # ─── fm subcommand ───────────────────────────────────────────────
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
    fm_parser.add_argument("--visualize", "-V", action="store_true",
                          help="Show ASCII waveform visualization")
    fm_parser.add_argument("--analyze", "-A", action="store_true",
                          help="Print audio analysis statistics")

    # ─── scale subcommand ─────────────────────────────────────────────
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
    scale_parser.add_argument("--visualize", "-V", action="store_true",
                            help="Show ASCII waveform visualization")

    # ─── chord subcommand ─────────────────────────────────────────────
    chord_parser = subparsers.add_parser("chord", help="Generate a chord")
    chord_parser.add_argument("--root", type=str, default="C",
                             help="Root note (default: C)")
    chord_parser.add_argument("--chord", type=str, default="major",
                             choices=list(CHORDS.keys()),
                             help="Chord type (default: major)")
    chord_parser.add_argument("--octave", type=int, default=4,
                             help="Starting octave (default: 4)")
    chord_parser.add_argument("--waveform", "-w", choices=[w.value for w in Waveform],
                             default="sine", help="Waveform type (default: sine)")
    chord_parser.add_argument("--duration", "-d", type=float, default=2.0,
                             help="Duration in seconds (default: 2)")
    chord_parser.add_argument("--sample-rate", "-r", type=int, default=44100,
                             help="Sample rate (default: 44100)")
    chord_parser.add_argument("--output", "-o", type=str, default=None,
                             help="Output WAV file path")
    chord_parser.add_argument("--visualize", "-V", action="store_true",
                             help="Show ASCII waveform visualization")

    # ─── analyze subcommand ───────────────────────────────────────────
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a WAV file")
    analyze_parser.add_argument("--input", "-i", type=str, required=True,
                               help="Input WAV file path")
    analyze_parser.add_argument("--verbose-analysis", action="store_true",
                               help="Show detailed spectral analysis")

    # ─── visualize subcommand ────────────────────────────────────────
    viz_parser = subparsers.add_parser("visualize", help="Visualize a WAV file")
    viz_parser.add_argument("--input", "-i", type=str, required=True,
                          help="Input WAV file path")
    viz_parser.add_argument("--width", type=int, default=80,
                          help="Display width (default: 80)")
    viz_parser.add_argument("--height", type=int, default=20,
                          help="Display height (default: 20)")

    # ─── preset subcommand ────────────────────────────────────────────
    preset_parser = subparsers.add_parser("preset", help="Generate from a built-in preset")
    preset_parser.add_argument("--name", "-n", type=str, required=True,
                              choices=list(PRESETS.keys()) if isinstance(PRESETS, dict) else [],
                              help="Preset name")
    preset_parser.add_argument("--frequency", "-f", type=float, default=None,
                              help="Override frequency (Hz)")
    preset_parser.add_argument("--duration", "-d", type=float, default=None,
                              help="Override duration (seconds)")
    preset_parser.add_argument("--output", "-o", type=str, default=None,
                              help="Output WAV file path")
    preset_parser.add_argument("--visualize", "-V", action="store_true",
                              help="Show ASCII waveform visualization")

    # ─── config subcommand ────────────────────────────────────────────
    config_parser = subparsers.add_parser("config", help="Generate from a config file")
    config_parser.add_argument("--file", "-f", type=str, required=True,
                              help="Path to config file (.json or .toml)")
    config_parser.add_argument("--output", "-o", type=str, default=None,
                              help="Output WAV file path (overrides config file)")
    config_parser.add_argument("--visualize", "-V", action="store_true",
                              help="Show ASCII waveform visualization")

    # ─── wavetable subcommand ────────────────────────────────────────
    wt_parser = subparsers.add_parser("wavetable", help="Wavetable synthesis")
    wt_parser.add_argument("--table", "-t", type=str, default="sine_to_saw",
                          choices=["sine_to_saw", "classic_analog"],
                          help="Built-in wavetable (default: sine_to_saw)")
    wt_parser.add_argument("--frequency", "-f", type=float, default=440.0,
                          help="Frequency in Hz (default: 440)")
    wt_parser.add_argument("--duration", "-d", type=float, default=2.0,
                          help="Duration in seconds (default: 2)")
    wt_parser.add_argument("--position", "-p", type=float, default=0.0,
                          help="Wavetable position 0-1 (default: 0)")
    wt_parser.add_argument("--interpolation", "-i", type=str, default="linear",
                          choices=["linear", "cubic"],
                          help="Interpolation method (default: linear)")
    wt_parser.add_argument("--sample-rate", "-r", type=int, default=44100,
                          help="Sample rate (default: 44100)")
    wt_parser.add_argument("--output", "-o", type=str, default=None,
                          help="Output WAV file path")
    wt_parser.add_argument("--visualize", "-V", action="store_true",
                          help="Show ASCII waveform visualization")

    # ─── noise subcommand ─────────────────────────────────────────────
    noise_parser = subparsers.add_parser("noise", help="Generate colored noise")
    noise_parser.add_argument("--color", "-c", type=str, default="white",
                             choices=["white", "pink", "brown", "blue", "violet"],
                             help="Noise color (default: white)")
    noise_parser.add_argument("--duration", "-d", type=float, default=2.0,
                             help="Duration in seconds (default: 2)")
    noise_parser.add_argument("--amplitude", "-a", type=float, default=0.8,
                             help="Amplitude 0-1 (default: 0.8)")
    noise_parser.add_argument("--seed", "-s", type=int, default=None,
                             help="Random seed for reproducibility")
    noise_parser.add_argument("--sample-rate", "-r", type=int, default=44100,
                             help="Sample rate (default: 44100)")
    noise_parser.add_argument("--output", "-o", type=str, default=None,
                             help="Output WAV file path")
    noise_parser.add_argument("--visualize", "-V", action="store_true",
                             help="Show ASCII waveform visualization")

    # ─── ringmod subcommand ───────────────────────────────────────────
    ringmod_parser = subparsers.add_parser("ringmod", help="Ring modulation")
    ringmod_parser.add_argument("--input", "-i", type=str, required=True,
                               help="Input WAV file path")
    ringmod_parser.add_argument("--modulator-freq", "-m", type=float, default=30.0,
                               help="Modulator frequency in Hz (default: 30)")
    ringmod_parser.add_argument("--mix", type=float, default=1.0,
                               help="Dry/wet mix 0-1 (default: 1.0)")
    ringmod_parser.add_argument("--output", "-o", type=str, default=None,
                               help="Output WAV file path")
    ringmod_parser.add_argument("--visualize", "-V", action="store_true",
                               help="Show ASCII waveform visualization")

    # ─── pitchshift subcommand ────────────────────────────────────────
    pitch_parser = subparsers.add_parser("pitchshift", help="Pitch shift a WAV file")
    pitch_parser.add_argument("--input", "-i", type=str, required=True,
                             help="Input WAV file path")
    pitch_parser.add_argument("--semitones", "-s", type=float, required=True,
                             help="Semitones to shift (can be fractional)")
    pitch_parser.add_argument("--output", "-o", type=str, default=None,
                             help="Output WAV file path")

    # ─── timestretch subcommand ──────────────────────────────────────
    stretch_parser = subparsers.add_parser("timestretch", help="Time-stretch a WAV file")
    stretch_parser.add_argument("--input", "-i", type=str, required=True,
                               help="Input WAV file path")
    stretch_parser.add_argument("--factor", "-f", type=float, required=True,
                               help="Stretch factor (>1 = slower, <1 = faster)")
    stretch_parser.add_argument("--output", "-o", type=str, default=None,
                               help="Output WAV file path")

    # ─── granular subcommand ──────────────────────────────────────────
    granular_parser = subparsers.add_parser("granular", help="Granular synthesis")
    granular_parser.add_argument("--input", "-i", type=str, required=True,
                                help="Input WAV file (source buffer)")
    granular_parser.add_argument("--duration", "-d", type=float, default=3.0,
                                help="Output duration in seconds (default: 3)")
    granular_parser.add_argument("--grain-size", "-g", type=float, default=0.05,
                                help="Grain size in seconds (default: 0.05)")
    granular_parser.add_argument("--density", type=float, default=20.0,
                                help="Grains per second (default: 20)")
    granular_parser.add_argument("--pitch-spread", type=float, default=0.0,
                                help="Pitch randomization 0-2 (default: 0)")
    granular_parser.add_argument("--position-spread", type=float, default=0.5,
                                help="Position randomization 0-1 (default: 0.5)")
    granular_parser.add_argument("--seed", "-s", type=int, default=None,
                                help="Random seed for reproducibility")
    granular_parser.add_argument("--output", "-o", type=str, default=None,
                                help="Output WAV file path")
    granular_parser.add_argument("--visualize", "-V", action="store_true",
                                help="Show ASCII waveform visualization")

    # ─── midi-import subcommand ──────────────────────────────────────
    midi_import_parser = subparsers.add_parser("midi-import", help="Import and analyze a MIDI file")
    midi_import_parser.add_argument("--input", "-i", type=str, required=True,
                                    help="Input MIDI file path")
    midi_import_parser.add_argument("--output", "-o", type=str, default=None,
                                    help="Output WAV file path (render notes)")
    midi_import_parser.add_argument("--waveform", "-w", type=str, default="sine",
                                    choices=[w.value for w in Waveform],
                                    help="Waveform for rendering (default: sine)")
    midi_import_parser.add_argument("--visualize", "-V", action="store_true",
                                    help="Show ASCII waveform visualization")

    args = parser.parse_args()

    if args.verbose:
        setup_logging(True)
    else:
        setup_logging(False)

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "generate":
        _cmd_generate(args)
    elif args.command == "fm":
        _cmd_fm(args)
    elif args.command == "scale":
        _cmd_scale(args)
    elif args.command == "chord":
        _cmd_chord(args)
    elif args.command == "analyze":
        _cmd_analyze(args)
    elif args.command == "visualize":
        _cmd_visualize(args)
    elif args.command == "preset":
        _cmd_preset(args)
    elif args.command == "config":
        _cmd_config(args)
    elif args.command == "wavetable":
        _cmd_wavetable(args)
    elif args.command == "noise":
        _cmd_noise(args)
    elif args.command == "ringmod":
        _cmd_ringmod(args)
    elif args.command == "pitchshift":
        _cmd_pitchshift(args)
    elif args.command == "timestretch":
        _cmd_timestretch(args)
    elif args.command == "granular":
        _cmd_granular(args)
    elif args.command == "midi-import":
        _cmd_midi_import(args)


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
        elif effect_name == "reverb":
            room_size = float(parts[1]) if len(parts) > 1 else 0.7
            damping = float(parts[2]) if len(parts) > 2 else 0.5
            wet = float(parts[3]) if len(parts) > 3 else 0.3
            chain.add(Effect(EffectType.REVERB, room_size=room_size, damping=damping, wet=wet))
        elif effect_name == "compressor":
            threshold = float(parts[1]) if len(parts) > 1 else 0.5
            ratio = float(parts[2]) if len(parts) > 2 else 4.0
            chain.add(Effect(EffectType.COMPRESSOR, threshold=threshold, ratio=ratio))
        elif effect_name == "chorus":
            rate = float(parts[1]) if len(parts) > 1 else 0.5
            depth = float(parts[2]) if len(parts) > 2 else 0.003
            mix = float(parts[3]) if len(parts) > 3 else 0.5
            voices = int(float(parts[4])) if len(parts) > 4 else 2
            chain.add(Effect(EffectType.CHORUS, rate=rate, depth=depth, mix=mix, voices=voices))
        elif effect_name == "bitcrusher":
            bits = int(float(parts[1])) if len(parts) > 1 else 8
            downsample = int(float(parts[2])) if len(parts) > 2 else 1
            chain.add(Effect(EffectType.BITCRUSHER, bits=bits, downsample=downsample))
        elif effect_name == "echo":
            time = float(parts[1]) if len(parts) > 1 else 0.3
            feedback = float(parts[2]) if len(parts) > 2 else 0.4
            mix = float(parts[3]) if len(parts) > 3 else 0.5
            chain.add(Effect(EffectType.ECHO, time=time, feedback=feedback, mix=mix))
    return chain


def _print_analysis(samples, sample_rate: int = 44100):
    """Print audio analysis statistics."""
    stats = compute_stats(samples)
    print("── Audio Analysis ──")
    print(f"  Samples:      {stats['num_samples']}")
    print(f"  Duration:      {stats['num_samples'] / sample_rate:.3f}s")
    print(f"  RMS Level:     {stats['rms']:.6f}")
    print(f"  Peak Level:    {stats['peak']:.6f}")
    print(f"  Crest Factor:  {stats['crest_factor']:.3f}")
    print(f"  ZCR:           {stats['zero_crossing_rate']:.4f}")
    print(f"  Mean:          {stats['mean']:.6f}")
    print(f"  Variance:      {stats['variance']:.6f}")
    print(f"  Range:         [{stats['min']:.4f}, {stats['max']:.4f}]")


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
    logger.debug(f"Generated {len(samples)} raw samples")

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

    # Analyze
    if args.analyze:
        _print_analysis(samples, args.sample_rate)

    # Export
    if args.output:
        writer = WavWriter(sample_rate=args.sample_rate)
        writer.write(args.output, samples)
        print(f"WAV written to {args.output} ({len(samples)} samples, {args.duration:.2f}s)")
    elif not args.visualize and not args.analyze:
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

    # Analyze
    if args.analyze:
        _print_analysis(samples, args.sample_rate)

    # Export
    if args.output:
        writer = WavWriter(sample_rate=args.sample_rate)
        writer.write(args.output, samples)
        print(f"WAV written to {args.output} ({len(samples)} samples, {args.duration:.2f}s)")
    elif not args.visualize and not args.analyze:
        print(f"Generated {len(samples)} samples ({args.duration:.2f}s)")
        print("Use --output to save as WAV or --visualize to display")


def _cmd_scale(args):
    """Handle the 'scale' subcommand."""
    waveform = Waveform(args.waveform)
    freqs = generate_scale(args.root, args.scale, args.octave)

    final_samples = []
    gap = [0.0] * int(0.02 * args.sample_rate)

    for i, freq in enumerate(freqs):
        osc = Oscillator(waveform=waveform, frequency=freq, amplitude=0.7,
                         sample_rate=args.sample_rate)
        note_samples = osc.generate(args.note_duration)
        note_samples = normalize(note_samples, target_peak=0.7)
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


def _cmd_chord(args):
    """Handle the 'chord' subcommand."""
    waveform = Waveform(args.waveform)
    freqs = generate_chord(args.root, args.chord, args.octave)

    # Generate each note and mix them
    note_signals = []
    for freq in freqs:
        osc = Oscillator(waveform=waveform, frequency=freq, amplitude=0.5,
                         sample_rate=args.sample_rate)
        note_samples = osc.generate(args.duration)
        note_signals.append(note_samples)

    # Mix all notes together
    samples = mix(note_signals)
    samples = normalize(samples)

    # Visualize
    if args.visualize:
        print(ascii_waveform(samples, title=f"{args.root} {args.chord} chord"))

    # Export
    if args.output:
        writer = WavWriter(sample_rate=args.sample_rate)
        writer.write(args.output, samples)
        print(f"WAV written to {args.output} ({len(samples)} samples, {args.duration:.2f}s)")
    elif not args.visualize:
        print(f"Generated {args.root} {args.chord} chord ({len(freqs)} notes)")
        print("Use --output to save as WAV or --visualize to display")


def _cmd_analyze(args):
    """Handle the 'analyze' subcommand."""
    samples, sample_rate, num_channels, bits_per_sample = WavWriter.samples_from_wav(args.input)

    print(f"── File: {args.input} ──")
    print(f"  Sample Rate:    {sample_rate} Hz")
    print(f"  Channels:       {num_channels}")
    print(f"  Bit Depth:      {bits_per_sample}")
    print(f"  Duration:       {len(samples) / sample_rate:.3f}s")
    print(f"  Samples:        {len(samples)}")
    _print_analysis(samples, sample_rate)

    if args.verbose_analysis:
        from .analysis import fundamental_frequency, zero_crossing_rate, spectral_analysis
        freq = fundamental_frequency(samples[:min(len(samples), sample_rate * 2)], sample_rate)
        print(f"\n  Est. Frequency: {freq:.1f} Hz")
        print(f"  ZCR:           {zero_crossing_rate(samples):.4f}")

        spectrum = spectral_analysis(samples[:8192], sample_rate, num_bins=32)
        print(f"\n  Spectrum (top 10 bins):")
        # Sort by magnitude
        spectrum_sorted = sorted(spectrum, key=lambda x: x[1], reverse=True)[:10]
        for freq_bin, mag in spectrum_sorted:
            bar = "█" * int(mag * 200)
            print(f"    {freq_bin:8.1f} Hz  {mag:.6f}  {bar}")


def _cmd_visualize(args):
    """Handle the 'visualize' subcommand."""
    samples, sample_rate, num_channels, bits_per_sample = WavWriter.samples_from_wav(args.input)
    print(ascii_waveform(samples[:min(len(samples), 44100 * 10)],  # Limit to 10 seconds
                        width=args.width, height=args.height,
                        title=args.input))
    print(f"\nSample rate: {sample_rate} Hz, Channels: {num_channels}, Bits: {bits_per_sample}")
    print(f"Duration: {len(samples) / sample_rate:.2f}s, Samples: {len(samples)}")


def _cmd_preset(args):
    """Handle the 'preset' subcommand."""
    try:
        config = get_preset(args.name)
    except ValueError as e:
        print(f"Error: {e}")
        print(f"Available presets: {list(PRESETS.keys())}")
        sys.exit(1)

    # Override with command-line arguments
    freq = args.frequency if args.frequency is not None else config.frequency
    duration = args.duration if args.duration is not None else config.duration
    sample_rate = config.sample_rate

    # Generate based on config
    if config.fm_preset:
        # FM synthesis preset
        presets = {
            "bellish": FMPreset.bellish,
            "brassish": FMPreset.brassish,
            "woodwind": FMPreset.woodwind,
            "bass": FMPreset.bass,
            "e_piano": FMPreset.e_piano,
        }
        synth = presets[config.fm_preset](carrier_freq=freq, sample_rate=sample_rate)
        samples = synth.generate(duration)
    else:
        # Oscillator preset
        waveform = Waveform(config.waveform)
        osc = Oscillator(waveform=waveform, frequency=freq,
                         amplitude=config.amplitude, sample_rate=sample_rate)
        samples = osc.generate(duration)

    # Apply envelope
    env = ADSR(attack=config.attack, decay=config.decay, sustain=config.sustain,
                release=config.release, sample_rate=sample_rate,
                curve=config.envelope_curve)
    samples = env.apply(samples, note_duration=duration)

    # Apply effects
    if config.effects:
        chain = EffectsChain()
        for eff in config.effects:
            eff_type = EffectType(eff['type'])
            eff_params = {k: v for k, v in eff.items() if k != 'type'}
            chain.add(Effect(eff_type, **eff_params))
        samples = chain.process(samples, sample_rate)

    samples = normalize(samples)

    if args.visualize:
        print(ascii_waveform(samples, title=f"Preset: {args.name}"))

    output = args.output
    if output:
        writer = WavWriter(sample_rate=sample_rate)
        writer.write(output, samples)
        print(f"WAV written to {output} ({len(samples)} samples, {duration:.2f}s)")


def _cmd_config(args):
    """Handle the 'config' subcommand."""
    try:
        config = SynthConfig.from_file(args.file)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

    logger.info(f"Loaded config: {config}")

    # Generate based on config
    if config.fm_preset:
        presets = {
            "bellish": FMPreset.bellish,
            "brassish": FMPreset.brassish,
            "woodwind": FMPreset.woodwind,
            "bass": FMPreset.bass,
            "e_piano": FMPreset.e_piano,
        }
        synth = presets[config.fm_preset](carrier_freq=config.carrier_freq,
                                           sample_rate=config.sample_rate)
        samples = synth.generate(config.duration)
    else:
        waveform = Waveform(config.waveform)
        harmonics = [(h[0], h[1]) for h in config.harmonics] if config.harmonics else None
        osc = Oscillator(waveform=waveform, frequency=config.frequency,
                         amplitude=config.amplitude, sample_rate=config.sample_rate,
                         harmonics=harmonics)
        samples = osc.generate(config.duration)

    # Apply envelope
    env = ADSR(attack=config.attack, decay=config.decay, sustain=config.sustain,
                release=config.release, sample_rate=config.sample_rate,
                curve=config.envelope_curve)
    samples = env.apply(samples, note_duration=config.duration)

    # Apply effects
    if config.effects:
        chain = EffectsChain()
        for eff in config.effects:
            eff_type = EffectType(eff['type'])
            eff_params = {k: v for k, v in eff.items() if k != 'type'}
            chain.add(Effect(eff_type, **eff_params))
        samples = chain.process(samples, config.sample_rate)

    samples = normalize(samples)

    if args.visualize:
        print(ascii_waveform(samples, title=f"Config: {args.file}"))

    output = args.output or config.output
    if output:
        writer = WavWriter(sample_rate=config.sample_rate,
                           bits_per_sample=config.bits_per_sample)
        writer.write(output, samples)
        print(f"WAV written to {output} ({len(samples)} samples, {config.duration:.2f}s)")
    else:
        print(f"Generated {len(samples)} samples ({config.duration:.2f}s)")
        print("Use --output to save as WAV")


# ─── New feature command handlers ────────────────────────────────────────


def _cmd_wavetable(args):
    """Handle the 'wavetable' subcommand."""
    from .wavetable import Wavetable, WavetableOscillator

    if args.table == "sine_to_saw":
        wt = Wavetable.sine_to_saw(num_frames=8, frame_size=2048)
    elif args.table == "classic_analog":
        wt = Wavetable.classic_analog(frame_size=2048)
    else:
        wt = Wavetable.sine_to_saw(num_frames=8, frame_size=2048)

    osc = WavetableOscillator(
        wavetable=wt,
        frequency=args.frequency,
        amplitude=0.8,
        position=args.position,
        sample_rate=args.sample_rate,
        interpolation=args.interpolation,
    )
    samples = osc.generate(args.duration)
    samples = normalize(samples)

    if args.visualize:
        print(ascii_waveform(samples, title=f"Wavetable: {args.table} @ {args.frequency}Hz"))

    if args.output:
        writer = WavWriter(sample_rate=args.sample_rate)
        writer.write(args.output, samples)
        print(f"WAV written to {args.output} ({len(samples)} samples, {args.duration:.2f}s)")
    elif not args.visualize:
        print(f"Generated {len(samples)} samples ({args.duration:.2f}s)")
        print("Use --output to save as WAV or --visualize to display")


def _cmd_noise(args):
    """Handle the 'noise' subcommand."""
    from .noise import NoiseColor, NoiseGenerator

    color_map = {
        "white": NoiseColor.WHITE,
        "pink": NoiseColor.PINK,
        "brown": NoiseColor.BROWN,
        "blue": NoiseColor.BLUE,
        "violet": NoiseColor.VIOLET,
    }
    ng = NoiseGenerator(
        color=color_map[args.color],
        seed=args.seed,
        sample_rate=args.sample_rate,
    )
    samples = ng.generate(args.duration, amplitude=args.amplitude)
    samples = normalize(samples)

    if args.visualize:
        print(ascii_waveform(samples, title=f"{args.color.title()} noise"))

    if args.output:
        writer = WavWriter(sample_rate=args.sample_rate)
        writer.write(args.output, samples)
        print(f"WAV written to {args.output} ({len(samples)} samples, {args.duration:.2f}s)")
    elif not args.visualize:
        print(f"Generated {len(samples)} samples of {args.color} noise ({args.duration:.2f}s)")
        print("Use --output to save as WAV or --visualize to display")


def _cmd_ringmod(args):
    """Handle the 'ringmod' subcommand."""
    from .modulation import RingModulator

    samples, sample_rate, num_channels, bits_per_sample = WavWriter.samples_from_wav(args.input)
    rm = RingModulator(
        modulator_freq=args.modulator_freq,
        amplitude=1.0,
        sample_rate=sample_rate,
        mix=args.mix,
    )
    result = rm.process(samples)
    result = normalize(result)

    if args.visualize:
        print(ascii_waveform(result, title=f"Ring mod @ {args.modulator_freq}Hz"))

    if args.output:
        writer = WavWriter(sample_rate=sample_rate)
        writer.write(args.output, result)
        print(f"WAV written to {args.output} ({len(result)} samples)")
    elif not args.visualize:
        print(f"Ring-modulated {len(result)} samples")
        print("Use --output to save as WAV or --visualize to display")


def _cmd_pitchshift(args):
    """Handle the 'pitchshift' subcommand."""
    from .spectral import pitch_shift as ps

    samples, sample_rate, num_channels, bits_per_sample = WavWriter.samples_from_wav(args.input)
    # Use first 44100 samples for performance
    chunk_size = min(len(samples), 44100)
    shifted = ps(samples[:chunk_size], semitones=args.semitones, sample_rate=sample_rate)

    if args.output:
        writer = WavWriter(sample_rate=sample_rate)
        writer.write(args.output, shifted)
        print(f"WAV written to {args.output} (pitch-shifted {args.semitones} semitones)")
    else:
        print(f"Pitch-shifted {len(shifted)} samples by {args.semitones} semitones")
        print("Use --output to save as WAV")


def _cmd_timestretch(args):
    """Handle the 'timestretch' subcommand."""
    from .spectral import time_stretch as ts

    samples, sample_rate, num_channels, bits_per_sample = WavWriter.samples_from_wav(args.input)
    chunk_size = min(len(samples), 44100)
    stretched = ts(samples[:chunk_size], stretch_factor=args.factor, sample_rate=sample_rate)

    if args.output:
        writer = WavWriter(sample_rate=sample_rate)
        writer.write(args.output, stretched)
        print(f"WAV written to {args.output} (time-stretched by {args.factor}x)")
    else:
        print(f"Time-stretched {len(stretched)} samples by factor {args.factor}")
        print("Use --output to save as WAV")


def _cmd_granular(args):
    """Handle the 'granular' subcommand."""
    from .granular import GranularSynth

    samples, sample_rate, num_channels, bits_per_sample = WavWriter.samples_from_wav(args.input)
    gran = GranularSynth(
        source=samples,
        grain_size=args.grain_size,
        density=args.density,
        pitch_spread=args.pitch_spread,
        position_spread=args.position_spread,
        seed=args.seed,
        sample_rate=sample_rate,
    )
    result = gran.generate(args.duration)

    if args.visualize:
        print(ascii_waveform(result, title="Granular synthesis"))

    if args.output:
        writer = WavWriter(sample_rate=sample_rate)
        writer.write(args.output, result)
        print(f"WAV written to {args.output} ({len(result)} samples, {args.duration:.2f}s)")
    elif not args.visualize:
        print(f"Generated {len(result)} samples ({args.duration:.2f}s)")
        print("Use --output to save as WAV or --visualize to display")


def _cmd_midi_import(args):
    """Handle the 'midi-import' subcommand."""
    from .midi_reader import read_midi_file

    midi_file = read_midi_file(args.input)

    print(f"── MIDI File: {args.input} ──")
    print(f"  Format:    {midi_file.format}")
    print(f"  Tracks:    {midi_file.num_tracks}")
    print(f"  Division:  {midi_file.division} PPQ")
    print(f"  Duration:  {midi_file.duration:.2f}s")
    print(f"  Notes:     {len(midi_file.notes)}")

    if midi_file.tempo_events:
        print(f"  Tempo events: {len(midi_file.tempo_events)}")
        for te in midi_file.tempo_events[:5]:
            print(f"    {te.time:.2f}s -> {te.bpm:.1f} BPM")

    if midi_file.notes:
        print(f"\n  Note list (first 20):")
        for note in midi_file.notes[:20]:
            print(f"    {note}")

    if args.output and midi_file.notes:
        # Render notes to WAV
        waveform = Waveform(args.waveform)
        comp = Composition(title="MIDI Import", sample_rate=44100)
        track = Track(waveform=waveform, sample_rate=44100)

        for note in midi_file.notes:
            track.add_note(
                note=note.note_name,
                duration=note.duration,
                velocity=min(1.0, note.velocity / 127.0),
            )

        comp.add_track(track)
        comp.export_wav(args.output)
        print(f"\nWAV written to {args.output}")

    if args.visualize and midi_file.notes:
        # Quick visualization of first few notes rendered
        osc = Oscillator(Waveform.SINE, frequency=midi_file.notes[0].frequency)
        samples = osc.generate(0.5)
        print(ascii_waveform(samples, title="First note"))


if __name__ == "__main__":
    main()