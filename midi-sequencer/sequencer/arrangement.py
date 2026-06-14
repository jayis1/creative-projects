"""Song arrangement: chain patterns into multi-section songs."""

from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from sequencer.patterns import Song, Track, Pattern, Step
from sequencer.export import song_to_midi


@dataclass
class Section:
    """A section of a song, referencing tracks with specific patterns.

    Attributes:
        name: Section name (e.g. 'verse', 'chorus')
        tracks: Dict mapping track name to (pattern, channel, program) tuples
        repeats: Number of times this section repeats
        bpm: Override BPM for this section (None = use song BPM)
    """
    name: str
    tracks: Dict[str, Tuple[Pattern, int, int]]  # track_name -> (pattern, channel, program)
    repeats: int = 1
    bpm: Optional[int] = None


class Arrangement:
    """Arrange multiple sections into a complete song.

    Sections are played in sequence, each can have its own BPM and pattern
    assignments for each track.
    """

    def __init__(self, name: str = "untitled", bpm: int = 120, ppqn: int = 480):
        self.name = name
        self.bpm = bpm
        self.ppqn = ppqn
        self.sections: List[Section] = []

    def add_section(self, section: Section) -> "Arrangement":
        """Add a section to the arrangement."""
        self.sections.append(section)
        return self

    def render_to_song(self) -> Song:
        """Render the arrangement into a single Song object.

        Concatenates all sections' patterns into continuous tracks.
        """
        all_tracks: Dict[str, List[Step]] = {}
        track_channels: Dict[str, int] = {}
        track_programs: Dict[str, int] = {}

        for section in self.sections:
            for repeat in range(section.repeats):
                for track_name, (pattern, channel, program) in section.tracks.items():
                    if track_name not in all_tracks:
                        all_tracks[track_name] = []
                        track_channels[track_name] = channel
                        track_programs[track_name] = program
                    for step in pattern.steps:
                        all_tracks[track_name].append(Step(
                            notes=list(step.notes),
                            velocity=step.velocity,
                            gate=step.gate,
                            probability=step.probability,
                            tie=step.tie,
                        ))

        tracks = []
        for track_name, steps in all_tracks.items():
            tracks.append(Track(
                name=track_name,
                pattern=Pattern(name=track_name, steps=steps, length=len(steps)),
                channel=track_channels[track_name],
                program=track_programs[track_name],
            ))

        return Song(
            name=self.name,
            tracks=tracks,
            bpm=self.bpm,
            ppqn=self.ppqn,
        )

    def export_midi(self, filename: str) -> str:
        """Export the arrangement directly to a MIDI file."""
        song = self.render_to_song()
        return song_to_midi(song, filename)


def verse_chorus_verse(
    verse_pattern: Pattern,
    chorus_pattern: Pattern,
    bass_verse: Pattern,
    bass_chorus: Pattern,
    drums_verse: Pattern,
    drums_chorus: Pattern,
    key: str = "C",
    bpm: int = 120,
) -> Arrangement:
    """Create a verse-chorus-verse arrangement.

    A common song structure: Verse -> Chorus -> Verse with different patterns for each section.
    """
    arr = Arrangement(name=f"VCV in {key}", bpm=bpm)

    verse = Section(
        name="Verse",
        tracks={
            "Lead": (verse_pattern, 0, 81),
            "Bass": (bass_verse, 1, 34),
            "Drums": (drums_verse, 9, 0),
        },
        repeats=2,
    )

    chorus = Section(
        name="Chorus",
        tracks={
            "Lead": (chorus_pattern, 0, 81),
            "Bass": (bass_chorus, 1, 34),
            "Drums": (drums_chorus, 9, 0),
        },
        repeats=2,
    )

    arr.add_section(verse).add_section(chorus).add_section(verse)
    return arr