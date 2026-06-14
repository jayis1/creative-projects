"""Command-line interface for the MIDI Step Sequencer."""

from __future__ import annotations
import argparse
import sys
import json
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
        pattern = drum_pattern(
            style=args.drum_style or "four_on_floor",
            length=args.length,
        )
    elif args.algorithm == "chords":
        # Parse chord progression
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
        print(f"Pattern: {pattern.name} ({pattern.length} steps)")
        print("-" * (pattern.length + 2))
        for i, step in enumerate(pattern.steps):
            if step.notes:
                notes_str = " ".join(str(n) for n in step.notes)
                marker = "▓" if step.velocity > 80 else "▒" if step.velocity > 0 else "░"
                print(f"  Step {i:2d}: {marker} vel={step.velocity:3d} notes=[{notes_str}]")
            else:
                print(f"  Step {i:2d}: ░ (rest)")

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


def cmd_compose(args):
    """Compose a multi-track song from command-line specifications."""
    tracks = []

    # Parse track specs: "drums:four_on_floor", "euclidean:5:8:C:pentatonic_minor:4",
    # "bass:steady:C:min7:2", "chords:C:maj7:D:min7:3"
    for spec in args.tracks:
        parts = spec.split(":")
        track_type = parts[0].lower()

        if track_type == "drums":
            style = parts[1] if len(parts) > 1 else "four_on_floor"
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


def main():
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
  %(prog)s info grooves
        """,
    )
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
    gen_parser.add_argument("--lsystem-preset", help="L-System preset name (cantor, fibonacci_melody, tree_rhythm, koch_snowflake, serpinski_melody)")
    gen_parser.add_argument("--lsystem-iterations", type=int, help="L-System iterations")
    gen_parser.add_argument("--progression", help="Named chord progression (e.g. pop_I_V_vi_IV, jazz_ii_V_I)")
    gen_parser.add_argument("--groove", help="Apply groove template (straight, swing_16th, shuffle, dilla, bossa, reggae)")
    gen_parser.add_argument("--groove-intensity", type=float, help="Groove intensity 0.0-1.0")
    gen_parser.add_argument("--velocity-curve", help="Apply velocity curve (crescendo, diminuendo, swell, heartbeat, random)")
    gen_parser.add_argument("-o", "--output", help="Output MIDI filename")
    gen_parser.add_argument("--bpm", type=int, default=120, help="Tempo in BPM")
    gen_parser.add_argument("--channel", type=int, default=0, help="MIDI channel")
    gen_parser.add_argument("--program", type=int, default=0, help="MIDI program number")
    gen_parser.add_argument("--save-pattern", help="Save pattern to JSON file")

    # Preset subcommand
    preset_parser = subparsers.add_parser("preset", help="Generate from a preset template")
    preset_parser.add_argument("preset", choices=list(PRESETS.keys()), help="Preset name")
    preset_parser.add_argument("--key", default="C", help="Root key")
    preset_parser.add_argument("--bpm", type=int, default=120, help="Tempo")
    preset_parser.add_argument("-o", "--output", default="preset_output.mid", help="Output filename")
    preset_parser.add_argument("--save-json", help="Save song structure to JSON")

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

    # Info subcommand
    info_parser = subparsers.add_parser("info", help="Display information")
    info_parser.add_argument("type",
                             choices=["scales", "chords", "notes", "rhythm", "progressions", "grooves", "lsystems"],
                             help="What to display")
    info_parser.add_argument("--root", default="C", help="Root note for note display")
    info_parser.add_argument("--scale", default="major", help="Scale name for note display")
    info_parser.add_argument("--beats", type=int, help="Beats for rhythm display")
    info_parser.add_argument("--length", type=int, default=16, help="Length for rhythm display")
    info_parser.add_argument("--rotation", type=int, help="Rotation for rhythm display")

    args = parser.parse_args()

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


if __name__ == "__main__":
    main()