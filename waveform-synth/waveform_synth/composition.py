"""
Composition engine for creating multi-track musical pieces.

Provides a Track class for holding notes with timing, and a Composition
class for mixing multiple tracks together with effects and export.
"""

import math
from typing import List, Optional, Dict, Tuple

from .core import Oscillator, Waveform, normalize, fade_in_out
from .envelope import ADSR
from .fm import FMSynth
from .effects import EffectsChain, Effect, EffectType
from .export import WavWriter
from .visualize import ascii_waveform
from .notes import note_to_freq, midi_to_freq


class Note:
    """
    A single musical note with pitch, duration, and velocity.

    Args:
        note: Note name (e.g. 'C4', 'A#3') or None for a rest.
        duration: Duration in seconds (must be > 0).
        velocity: Volume in [0.0, 1.0].
        delay: Time offset from note start in seconds (for chords).
    """

    def __init__(self, note: Optional[str] = None, duration: float = 0.5,
                 velocity: float = 1.0, delay: float = 0.0):
        self.note = note
        self.duration = duration
        self.velocity = velocity
        self.delay = delay

    @property
    def frequency(self) -> Optional[float]:
        """Return the frequency in Hz, or None for rests."""
        if self.note is None:
            return None
        return note_to_freq(self.note)

    def __repr__(self):
        return f"Note({self.note!r}, dur={self.duration}, vel={self.velocity:.2f}, delay={self.delay:.2f})"


class Track:
    """
    A single track of music containing a sequence of notes.

    Args:
        waveform: Waveform type for the oscillator.
        instrument: Optional FMSynth instance for FM synthesis.
        envelope: ADSR envelope to shape each note.
        effects: Effects chain to apply to the whole track.
        sample_rate: Samples per second.
    """

    def __init__(
        self,
        waveform: Waveform = Waveform.SINE,
        instrument: Optional[FMSynth] = None,
        envelope: Optional[ADSR] = None,
        effects: Optional[EffectsChain] = None,
        sample_rate: int = 44100,
    ):
        self.waveform = waveform
        self.instrument = instrument
        self.envelope = envelope or ADSR(attack=0.01, decay=0.1, sustain=0.7, release=0.3, sample_rate=sample_rate)
        self.effects = effects or EffectsChain()
        self.sample_rate = sample_rate
        self.notes: List[Note] = []

    def add_note(self, note: str, duration: float = 0.5, velocity: float = 1.0, delay: float = 0.0):
        """Add a note to the track."""
        self.notes.append(Note(note=note, duration=duration, velocity=velocity, delay=delay))
        return self

    def add_rest(self, duration: float = 0.5):
        """Add a rest to the track."""
        self.notes.append(Note(note=None, duration=duration))
        return self

    def add_notes(self, notes: List[Tuple[str, float]]):
        """
        Add multiple notes. Each tuple is (note_name, duration).

        Args:
            notes: List of (note_name, duration) tuples.
        """
        for note_name, duration in notes:
            self.add_note(note_name, duration)
        return self

    def render(self) -> List[float]:
        """
        Render the track to audio samples.

        Returns:
            List of float samples.
        """
        if not self.notes:
            return []

        # Calculate total duration
        total_time = 0.0
        for n in self.notes:
            note_end = total_time + n.duration + n.delay
            total_time += n.duration

        # Add release time to total
        total_duration = total_time + self.envelope.release

        # Create output buffer
        total_samples = int(total_duration * self.sample_rate) + self.sample_rate  # extra buffer
        output = [0.0] * total_samples

        current_time = 0.0
        for n in self.notes:
            start_time = current_time + n.delay
            note_freq = n.frequency

            if note_freq is not None:
                # Generate oscillator samples for this note
                if self.instrument is not None:
                    # Use FM synth
                    synth = FMSynth(
                        carrier_freq=note_freq,
                        modulator_freq=self.instrument.modulator_freq * (note_freq / self.instrument.carrier_freq),
                        modulation_index=self.instrument.modulation_index,
                        carrier_waveform=self.instrument.carrier_waveform,
                        modulator_waveform=self.instrument.modulator_waveform,
                        amplitude=n.velocity,
                        sample_rate=self.sample_rate,
                    )
                    raw = synth.generate(n.duration)
                else:
                    # Use simple oscillator
                    osc = Oscillator(
                        waveform=self.waveform,
                        frequency=note_freq,
                        amplitude=n.velocity,
                        sample_rate=self.sample_rate,
                    )
                    raw = osc.generate(n.duration)

                # Apply envelope
                enveloped = self.envelope.apply(raw, note_duration=n.duration)

                # Mix into output buffer
                start_sample = int(start_time * self.sample_rate)
                for i, s in enumerate(enveloped):
                    idx = start_sample + i
                    if idx < len(output):
                        output[idx] += s

            current_time += n.duration

        # Trim to actual content length
        # Find last non-zero sample
        last_nonzero = len(output) - 1
        while last_nonzero > 0 and abs(output[last_nonzero]) < 1e-10:
            last_nonzero -= 1

        output = output[:last_nonzero + 1]

        # Apply effects chain
        if self.effects.effects:
            output = self.effects.process(output, self.sample_rate)

        return output


class Composition:
    """
    A multi-track composition.

    Args:
        sample_rate: Samples per second.
        title: Optional title.
    """

    def __init__(self, sample_rate: int = 44100, title: str = "Untitled"):
        self.sample_rate = sample_rate
        self.title = title
        self.tracks: List[Track] = []

    def add_track(self, track: Track) -> 'Composition':
        """Add a track to the composition."""
        if track.sample_rate != self.sample_rate:
            raise ValueError(f"Track sample rate {track.sample_rate} doesn't match composition rate {self.sample_rate}")
        self.tracks.append(track)
        return self

    def render(self, normalize_output: bool = True) -> List[float]:
        """
        Render all tracks and mix them together.

        Args:
            normalize_output: Whether to normalize the final output.

        Returns:
            Mixed audio samples.
        """
        rendered_tracks = []
        for track in self.tracks:
            rendered_tracks.append(track.render())

        if not rendered_tracks:
            return []

        # Find the longest track
        max_len = max(len(t) for t in rendered_tracks)

        # Mix all tracks
        mixed = [0.0] * max_len
        for track_samples in rendered_tracks:
            for i in range(len(track_samples)):
                mixed[i] += track_samples[i]

        if normalize_output:
            mixed = normalize(mixed)

        # Apply fade in/out
        fade_samples = min(int(0.01 * self.sample_rate), len(mixed) // 4)
        if fade_samples > 0:
            mixed = fade_in_out(mixed, fade_samples)

        return mixed

    def export_wav(self, filepath: str, normalize_output: bool = True):
        """
        Render and export the composition as a WAV file.

        Args:
            filepath: Output file path.
            normalize_output: Whether to normalize before export.
        """
        samples = self.render(normalize_output=normalize_output)
        writer = WavWriter(sample_rate=self.sample_rate)
        writer.write(filepath, samples)

    def visualize(self, width: int = 80, height: int = 20) -> str:
        """
        Render an ASCII waveform visualization of the composition.

        Args:
            width: Display width in characters.
            height: Display height in lines.

        Returns:
            ASCII art string.
        """
        samples = self.render()
        return ascii_waveform(samples, width=width, height=height, title=self.title)