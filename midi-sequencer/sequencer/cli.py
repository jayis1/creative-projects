"""Command-line interface for the MIDI Step Sequencer.

Provides commands for generating patterns, composing songs, analyzing
output, batch processing, and managing configuration.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Optional

from sequencer.scales import SCALE_INTERVALS, CHORD_INTERVALS, scale_notes, chord_notes, note_to_midi
from sequencer.patterns import Song, Track, Pattern, Step
from sequencer.generators import (
    euclidean_pattern, random_pattern, markov_pattern, chord_pattern,
    bassline_from_chords, drum_pattern, morph_pattern, euclidean_rhythm,
)
from sequencer.presets import PRESETS
from sequencer.export import song_to_midi, pattern_to_midi
from sequencer.grooves import GROOVE_TEMPLATES, VELOCITY_CURVES, apply_groove, apply_velocity_curve
from sequencer.progressions import PROGRESSIONS, build_progression, list_progressions
from sequencer.lsystem import lsystem_pattern, PRESETS as LS_PRESETS
from sequencer.serialization import save_song, load_song, save_pattern, load_pattern
from sequencer.analysis import (
    pattern_stats, track_stats, song_stats as analyze_song_stats,
    song_summary, visualize_pattern, note_distribution, interval_distribution,
)
from sequencer.batch import (
    CompositionRecipe, parameter_sweep, euclidean_variations,
    scale_exploration, progression_album,
)
from sequencer.extended_drums import extended_drum_pattern, list_extended_styles, EXTENDED_DRUM_STYLES
from sequencer.config import SequencerConfig, generate_default_config
from sequencer.logging_setup import setup_logging

logger = logging.getLogger(__name__)


def cmd_generate(args):
    """Generate a pattern using one of the generative algorithms."""
    if args.algorithm == "euclidean":
        pattern = euclidean_pattern(
            beats=args.beats or 5,
            length=args.length,
            root=args.root,
            scale=args.scale,
            octave=args.octave,
            rotation=args.rotation or 0,
        )
    elif args.algorithm == "random":
        pattern = random_pattern(
            length=args.length,
            density=args.density or 0.5,
            root=args.root,
            scale=args.scale,
            octave=args.octave,
        )
    elif args.algorithm == "markov":
        pattern = markov_pattern(
            length=args.length,
            root=args.root,
            scale=args.scale,
            octave=args.octave,
        )
    elif args.algorithm == "drums":
        # Try extended drums first, then standard
        style = args.drum_style or "four_on_floor"
        if style in EXTENDED_DRUM_STYLES:
            pattern = extended_drum_pattern(style=style, length=args.length)
        else:
            pattern = drum_pattern(style=style, length=args.length)
    elif args.algorithm == "chords":
        chords = []
        if args.chords:
            for c in args.chords:
                parts = c.split(":")
                root = parts[0]
                quality = parts[1] if len(parts) > 1 else "maj"
                chords.append((root, quality))
        else:
            chords = [(args.root, "maj7")]
        pattern = chord_pattern(
            chords=chords,
            length_per_chord=args.length,
            octave=args.octave,
            arpeggiate=args.arpeggiate,
        )
    elif args.algorithm == "lsystem":
        pattern = lsystem_pattern(
            preset=args.lsystem_preset or "cantor",
            iterations=args.lsystem_iterations or 3,
            root=args.root,
            scale=args.scale,
            octave=args.octave,
            velocity=args.velocity or 100,
        )
    elif args.algorithm == "progression":
        prog_name = args.progression or "pop_I_V_vi_IV"
        chords = build_progression(prog_name, key=args.root, scale=args.scale)
        pattern = chord_pattern(
            chords=chords,
            length_per_chord=args.length,
            octave=args.octave,
            arpeggiate=args.arpeggiate,
        )
    else:
        print(f"Unknown algorithm: {args.algorithm}", file=sys.stderr)
        sys.exit(1)

    # Apply groove if specified
    if args.groove:
        pattern = apply_groove(pattern, args.groove, intensity=args.groove_intensity or 1.0)

    # Apply velocity curve if specified
    if args.velocity_curve:
        pattern = apply_velocity_curve(pattern, args.velocity_curve)

    if args.output:
        song = Song(
            name=f"{args.algorithm}_{args.root}_{args.scale}",
            tracks=[Track(
                name=args.algorithm,
                pattern=pattern,
                channel=args.channel,
                program=args.program,
            )],
            bpm=args.bpm,
        )
        filename = song_to_midi(song, args.output)
        print(f"Exported to {filename}")
    else:
        # Print pattern visualization
        style = "piano" if args.visualize == "piano" else "block"
        print(visualize_pattern(pattern, style=style))

    # Save pattern as JSON if requested
    if args.save_pattern:
        save_pattern(pattern, args.save_pattern)
        print(f"Pattern saved to {args.save_pattern}")


def cmd_preset(args):
    """Generate a song from a preset template."""
    if args.preset not in PRESETS:
        print(f"Unknown preset: {args.preset}", file=sys.stderr)
        print(f"Available: {list(PRESETS.keys())}", file=sys.stderr)
        sys.exit(1)

    song = PRESETS[args.preset](key=args.key, bpm=args.bpm)
    filename = song_to_midi(song, args.output)
    print(f"Exported preset '{args.preset}' to {filename}")
    print(f"  Tracks: {len(song.tracks)}, BPM: {song.bpm}")

    if args.save_json:
        save_song(song, args.save_json)
        print(f"  Song JSON saved to {args.save_json}")

    if args.summary:
        print(song_summary(song))


def cmd_info(args):
    """Display information about scales, chords, progressions, and available options."""
    if args.type == "scales":
        print("Available scales:")
        for name, intervals in SCALE_INTERVALS.items():
            semitones = " ".join(str(i) for i in intervals)
            print(f"  {name:20s} [{semitones}]")
    elif args.type == "chords":
        print("Available chord qualities:")
        for name, intervals in CHORD_INTERVALS.items():
            semitones = " ".join(str(i) for i in intervals)
            print(f"  {name:8s} [{semitones}]")
    elif args.type == "notes":
        if args.root and args.scale:
            notes = scale_notes(args.root, args.scale, 2, 4)
            print(f"Scale: {args.root} {args.scale}")
            print(f"Notes: {notes}")
            print(f"Names: {' '.join(str(n) for n in notes)}")
        else:
            print("Provide --root and --scale to see note numbers")
    elif args.type == "rhythm":
        beats = args.beats or 5
        length = args.length or 16
        rhythm = euclidean_rhythm(beats, length, rotation=args.rotation or 0)
        vis = "".join("█" if r else "·" for r in rhythm)
        print(f"Euclidean ({beats}, {length}): {vis}")
    elif args.type == "progressions":
        print("Available chord progressions:")
        for name, prog in PROGRESSIONS.items():
            degrees = " ".join(f"{d}:{q}" for d, q in prog)
            print(f"  {name:25s} [{degrees}]")
    elif args.type == "grooves":
        print("Available groove templates:")
        for name in GROOVE_TEMPLATES:
            print(f"  {name}")
    elif args.type == "lsystems":
        print("Available L-System presets:")
        for name, preset in LS_PRESETS.items():
            print(f"  {name:20s} axiom={preset['axiom']} rules={preset['rules']}")
    elif args.type == "drums":
        print("Standard drum styles: four_on_floor, breakbeat, hiphop, bossa, waltz")
        print("\nExtended drum styles:")
        for name, desc in list_extended_styles().items():
            print(f"  {name:15s} — {desc}")


def cmd_compose(args):
    """Compose a multi-track song from command-line specifications."""
    tracks = []

    for spec in args.tracks:
        parts = spec.split(":")
        track_type = parts[0].lower()

        if track_type == "drums":
            style = parts[1] if len(parts) > 1 else "four_on_floor"
            if style in EXTENDED_DRUM_STYLES:
                pattern = extended_drum_pattern(style=style, length=args.length)
            else:
                pattern = drum_pattern(style=style, length=args.length)
            tracks.append(Track(name=f"Drums ({style})", pattern=pattern, channel=9))

        elif track_type == "euclidean":
            beats = int(parts[1]) if len(parts) > 1 else 5
            length = int(parts[2]) if len(parts) > 2 else args.length
            root = parts[3] if len(parts) > 3 else args.root
            scale = parts[4] if len(parts) > 4 else args.scale
            octave = int(parts[5]) if len(parts) > 5 else args.octave
            ch = len(tracks)
            pattern = euclidean_pattern(beats, length, root=root, scale=scale, octave=octave)
            tracks.append(Track(name=f"Euc {beats}:{length}", pattern=pattern, channel=min(ch, 15)))

        elif track_type == "random":
            density = float(parts[1]) if len(parts) > 1 else 0.5
            root = parts[2] if len(parts) > 2 else args.root
            scale = parts[3] if len(parts) > 3 else args.scale
            octave = int(parts[4]) if len(parts) > 4 else args.octave
            ch = len(tracks)
            pattern = random_pattern(args.length, density=density, root=root, scale=scale, octave=octave)
            tracks.append(Track(name="Random", pattern=pattern, channel=min(ch, 15)))

        elif track_type == "markov":
            root = parts[1] if len(parts) > 1 else args.root
            scale = parts[2] if len(parts) > 2 else args.scale
            octave = int(parts[3]) if len(parts) > 3 else args.octave
            ch = len(tracks)
            pattern = markov_pattern(args.length, root=root, scale=scale, octave=octave)
            tracks.append(Track(name="Markov", pattern=pattern, channel=min(ch, 15)))

        elif track_type == "bass":
            root = parts[1] if len(parts) > 1 else args.root
            quality = parts[2] if len(parts) > 2 else "min"
            octave = int(parts[3]) if len(parts) > 3 else 2
            style = parts[4] if len(parts) > 4 else "steady"
            pattern = bassline_from_chords([(root, quality)], args.length, octave=octave, pattern_type=style)
            tracks.append(Track(name="Bass", pattern=pattern, channel=min(len(tracks), 15), program=34))

        elif track_type == "chords":
            chords = []
            for cp in parts[1:]:
                cq = cp.split(",")
                for c in cq:
                    crq = c.split("-")
                    root = crq[0]
                    quality = crq[1] if len(crq) > 1 else "maj7"
                    chords.append((root, quality))
            if not chords:
                chords = [(args.root, "maj7")]
            pattern = chord_pattern(chords, length_per_chord=args.length, octave=3, arpeggiate=True)
            tracks.append(Track(name="Chords", pattern=pattern, channel=min(len(tracks), 15), program=4))

        elif track_type == "lsystem":
            preset = parts[1] if len(parts) > 1 else "cantor"
            iterations = int(parts[2]) if len(parts) > 2 else 3
            root = parts[3] if len(parts) > 3 else args.root
            scale = parts[4] if len(parts) > 4 else args.scale
            octave = int(parts[5]) if len(parts) > 5 else args.octave
            ch = len(tracks)
            pattern = lsystem_pattern(preset=preset, iterations=iterations, root=root, scale=scale, octave=octave)
            tracks.append(Track(name=f"LS-{preset}", pattern=pattern, channel=min(ch, 15)))

        elif track_type == "progression":
            prog_name = parts[1] if len(parts) > 1 else "pop_I_V_vi_IV"
            octave = int(parts[2]) if len(parts) > 2 else 3
            chords = build_progression(prog_name, key=args.root, scale=args.scale)
            pattern = chord_pattern(chords, length_per_chord=args.length, octave=octave, arpeggiate=True)
            tracks.append(Track(name=f"Prog-{prog_name}", pattern=pattern, channel=min(len(tracks), 15), program=4))

        else:
            print(f"Unknown track type: {track_type}", file=sys.stderr)
            sys.exit(1)

    if not tracks:
        print("No tracks specified!", file=sys.stderr)
        sys.exit(1)

    song = Song(name=args.name or "composition", tracks=tracks, bpm=args.bpm)
    filename = song_to_midi(song, args.output)
    print(f"Composed '{song.name}' with {len(tracks)} tracks at {song.bpm} BPM")
    print(f"Exported to {filename}")
    for t in tracks:
        print(f"  - {t.name}: {t.pattern.length} steps, ch={t.channel}, prog={t.program}")

    if args.save_json:
        save_song(song, args.save_json)
        print(f"  Song JSON saved to {args.save_json}")

    if args.summary:
        print()
        print(song_summary(song))


def cmd_analyze(args):
    """Analyze a song or pattern from a JSON file."""
    if args.input:
        if args.input.endswith(".json"):
            song = load_song(args.input)
        else:
            print(f"Can only analyze JSON files, got: {args.input}", file=sys.stderr)
            sys.exit(1)
    else:
        print("No input file specified. Use --input to provide a JSON song file.", file=sys.stderr)
        sys.exit(1)

    if args.summary:
        print(song_summary(song))

    if args.stats:
        stats = analyze_song_stats(song)
        print("\nSong Statistics:")
        for key, value in stats.items():
            if key != "tracks":
                print(f"  {key}: {value}")
        if args.verbose:
            print("\nPer-Track Statistics:")
            for track_stats_data in stats.get("tracks", []):
                print(f"\n  Track: {track_stats_data.get('track_name', 'unknown')}")
                for k, v in track_stats_data.items():
                    if k != "track_name":
                        print(f"    {k}: {v}")


def cmd_batch(args):
    """Run batch composition tasks."""
    output_dir = args.output_dir or "batch_output"

    if args.task == "euclidean":
        files = euclidean_variations(
            root=args.root,
            scale=args.scale,
            bpm=args.bpm,
            beat_range=(args.min_beats, args.max_beats),
            length=args.length,
            output_dir=output_dir,
        )
    elif args.task == "scales":
        files = scale_exploration(
            root=args.root,
            bpm=args.bpm,
            length=args.length,
            output_dir=output_dir,
        )
    elif args.task == "progressions":
        files = progression_album(
            key=args.root,
            bpm=args.bpm,
            length_per_chord=args.length,
            output_dir=output_dir,
        )
    elif args.task == "sweep":
        recipe = CompositionRecipe(
            name="sweep",
            bpm=args.bpm,
            root=args.root,
            scale=args.scale,
            tracks=[
                {"type": "euclidean", "beats": 5, "length": args.length, "channel": 0, "program": 81},
                {"type": "drums", "style": "four_on_floor", "length": args.length, "channel": 9},
            ],
        )
        param = args.parameter or "bpm"
        values = _parse_sweep_values(args.values, param)
        files = parameter_sweep(
            base_recipe=recipe,
            parameter=param,
            values=values,
            output_dir=output_dir,
        )
    else:
        print(f"Unknown batch task: {args.task}", file=sys.stderr)
        sys.exit(1)

    print(f"Generated {len(files)} files in {output_dir}/")


def _parse_sweep_values(values_str: Optional[str], param: str) -> list:
    """Parse sweep values from a comma-separated string."""
    if not values_str:
        if param == "bpm":
            return [80, 100, 120, 140, 160]
        elif param == "root":
            return ["C", "D", "E", "F", "G", "A", "Bb"]
        elif param == "scale":
            return ["major", "minor", "dorian", "pentatonic_minor"]
        return [120]

    items = values_str.split(",")
    result = []
    for item in items:
        item = item.strip()
        try:
            result.append(int(item))
        except ValueError:
            try:
                result.append(float(item))
            except ValueError:
                result.append(item)
    return result


def cmd_config(args):
    """Manage configuration files."""
    if args.action == "show":
        config = SequencerConfig.load(args.config_file)
        print("Current configuration:")
        for key, value in config.to_dict().items():
            print(f"  {key}: {value}")
    elif args.action == "init":
        fmt = args.format or "yaml"
        output = args.output or f"midi-sequencer.{fmt}"
        generate_default_config(output, fmt)
        print(f"Created default config file: {output}")
    elif args.action == "validate":
        try:
            config = SequencerConfig.load(args.config_file)
            print(f"Configuration is valid: {args.config_file or '(defaults)'}")
        except Exception as e:
            print(f"Configuration error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Unknown config action: {args.action}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="MIDI Step Sequencer — Generative music composition and MIDI export",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s generate euclidean --beats 5 --length 16 -o output.mid
  %(prog)s generate drums --drum-style hiphop -o drums.mid
  %(prog)s generate lsystem --lsystem-preset fibonacci_melody -o lsystem.mid
  %(prog)s generate progression --progression pop_I_V_vi_IV --root G -o prog.mid
  %(prog)s compose --tracks "drums:four_on_floor" "euclidean:5:16:C:pentatonic_minor:4" -o song.mid
  %(prog)s preset four_on_floor --key Am -o dance.mid
  %(prog)s info scales
  %(prog)s info progressions
  %(prog)s info drums
  %(prog)s batch euclidean --root A --min-beats 3 --max-beats 9 -o batch/
  %(prog)s batch scales --root C -o scales/
  %(prog)s analyze --input song.json --summary
  %(prog)s config init --format yaml
  %(prog)s config show
        """,
    )
    parser.add_argument("--config", help="Configuration file path", dest="config_file")
    parser.add_argument("--log-level", default="WARNING",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                       help="Set logging level")
    subparsers = parser.add_subparsers(dest="command", help="Sub-command")

    # Generate subcommand
    gen_parser = subparsers.add_parser("generate", help="Generate a pattern")
    gen_parser.add_argument("algorithm",
                            choices=["euclidean", "random", "markov", "drums", "chords", "lsystem", "progression"],
                            help="Generation algorithm")
    gen_parser.add_argument("--beats", type=int, help="Number of beats (for Euclidean)")
    gen_parser.add_argument("--length", type=int, default=16, help="Pattern length in steps")
    gen_parser.add_argument("--root", default="C", help="Root note (e.g. C, F#, Bb)")
    gen_parser.add_argument("--scale", default="pentatonic_minor", help="Scale name")
    gen_parser.add_argument("--octave", type=int, default=4, help="Starting octave")
    gen_parser.add_argument("--rotation", type=int, help="Rotation offset (for Euclidean)")
    gen_parser.add_argument("--density", type=float, help="Note density 0-1 (for random)")
    gen_parser.add_argument("--velocity", type=int, help="Note velocity")
    gen_parser.add_argument("--drum-style", default="four_on_floor", help="Drum pattern style")
    gen_parser.add_argument("--chords", nargs="+", help="Chord specs ROOT:QUALITY")
    gen_parser.add_argument("--arpeggiate", action="store_true", help="Arpeggiate chords")
    gen_parser.add_argument("--lsystem-preset", help="L-System preset name")
    gen_parser.add_argument("--lsystem-iterations", type=int, help="L-System iterations")
    gen_parser.add_argument("--progression", help="Named chord progression")
    gen_parser.add_argument("--groove", help="Apply groove template")
    gen_parser.add_argument("--groove-intensity", type=float, help="Groove intensity 0.0-1.0")
    gen_parser.add_argument("--velocity-curve", help="Apply velocity curve")
    gen_parser.add_argument("-o", "--output", help="Output MIDI filename")
    gen_parser.add_argument("--bpm", type=int, default=120, help="Tempo in BPM")
    gen_parser.add_argument("--channel", type=int, default=0, help="MIDI channel")
    gen_parser.add_argument("--program", type=int, default=0, help="MIDI program number")
    gen_parser.add_argument("--save-pattern", help="Save pattern to JSON file")
    gen_parser.add_argument("--visualize", choices=["block", "piano", "dot"],
                           default="block", help="Visualization style")

    # Preset subcommand
    preset_parser = subparsers.add_parser("preset", help="Generate from a preset template")
    preset_parser.add_argument("preset", choices=list(PRESETS.keys()), help="Preset name")
    preset_parser.add_argument("--key", default="C", help="Root key")
    preset_parser.add_argument("--bpm", type=int, default=120, help="Tempo")
    preset_parser.add_argument("-o", "--output", default="preset_output.mid", help="Output filename")
    preset_parser.add_argument("--save-json", help="Save song structure to JSON")
    preset_parser.add_argument("--summary", action="store_true", help="Show song summary")

    # Compose subcommand
    comp_parser = subparsers.add_parser("compose", help="Compose a multi-track song")
    comp_parser.add_argument("--tracks", nargs="+", required=True, help="Track specifications")
    comp_parser.add_argument("--bpm", type=int, default=120, help="Tempo")
    comp_parser.add_argument("--length", type=int, default=16, help="Pattern length")
    comp_parser.add_argument("--root", default="C", help="Default root note")
    comp_parser.add_argument("--scale", default="pentatonic_minor", help="Default scale")
    comp_parser.add_argument("--octave", type=int, default=4, help="Default octave")
    comp_parser.add_argument("--name", help="Song name")
    comp_parser.add_argument("-o", "--output", default="composition.mid", help="Output filename")
    comp_parser.add_argument("--save-json", help="Save song structure to JSON")
    comp_parser.add_argument("--summary", action="store_true", help="Show song summary")

    # Info subcommand
    info_parser = subparsers.add_parser("info", help="Display information")
    info_parser.add_argument("type",
                             choices=["scales", "chords", "notes", "rhythm", "progressions",
                                      "grooves", "lsystems", "drums"],
                             help="What to display")
    info_parser.add_argument("--root", default="C", help="Root note for note display")
    info_parser.add_argument("--scale", default="major", help="Scale name for note display")
    info_parser.add_argument("--beats", type=int, help="Beats for rhythm display")
    info_parser.add_argument("--length", type=int, default=16, help="Length for rhythm display")
    info_parser.add_argument("--rotation", type=int, help="Rotation for rhythm display")

    # Analyze subcommand
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a song or pattern")
    analyze_parser.add_argument("--input", "-i", help="Input JSON song file")
    analyze_parser.add_argument("--summary", action="store_true", help="Show song summary")
    analyze_parser.add_argument("--stats", action="store_true", help="Show detailed statistics")
    analyze_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    # Batch subcommand
    batch_parser = subparsers.add_parser("batch", help="Batch composition tasks")
    batch_parser.add_argument("task",
                              choices=["euclidean", "scales", "progressions", "sweep"],
                              help="Batch task type")
    batch_parser.add_argument("--root", default="C", help="Root note")
    batch_parser.add_argument("--scale", default="pentatonic_minor", help="Scale name")
    batch_parser.add_argument("--bpm", type=int, default=120, help="Tempo")
    batch_parser.add_argument("--length", type=int, default=16, help="Pattern length")
    batch_parser.add_argument("-o", "--output-dir", default="batch_output", help="Output directory")
    # Euclidean-specific
    batch_parser.add_argument("--min-beats", type=int, default=3, help="Min beats for euclidean range")
    batch_parser.add_argument("--max-beats", type=int, default=9, help="Max beats for euclidean range")
    # Sweep-specific
    batch_parser.add_argument("--parameter", help="Parameter to sweep (bpm, root, scale)")
    batch_parser.add_argument("--values", help="Comma-separated values for sweep")

    # Config subcommand
    config_parser = subparsers.add_parser("config", help="Manage configuration")
    config_parser.add_argument("action",
                               choices=["show", "init", "validate"],
                               help="Config action")
    config_parser.add_argument("--config-file", help="Config file path")
    config_parser.add_argument("--format", choices=["yaml", "toml", "json"], help="Config format")
    config_parser.add_argument("-o", "--output", help="Output file for init")

    args = parser.parse_args()

    # Set up logging
    setup_logging(args.log_level or "WARNING")

    # Load config if specified
    if hasattr(args, 'config_file') and args.config_file:
        try:
            config = SequencerConfig.load(args.config_file)
            logger.info(f"Loaded config from {args.config_file}")
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "preset":
        cmd_preset(args)
    elif args.command == "compose":
        cmd_compose(args)
    elif args.command == "info":
        cmd_info(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "batch":
        cmd_batch(args)
    elif args.command == "config":
        cmd_config(args)


if __name__ == "__main__":
    main()