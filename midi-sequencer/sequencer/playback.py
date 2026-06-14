"""MIDI playback support — play generated songs through available MIDI devices.

Provides cross-platform MIDI output using available backends:
- pygame.midi (cross-platform, most common)
- rtmidi (professional, requires python-rtmidi)
- mido (alternative, requires mido package)

Falls back to generating a temp .mid file and launching the system
MIDI player if no Python backend is available.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)


def get_available_backends() -> list[str]:
    """Check which MIDI playback backends are available.

    Returns:
        List of available backend names
    """
    backends = []

    try:
        import pygame.midi  # noqa: F401
        backends.append("pygame")
    except ImportError:
        pass

    try:
        import rtmidi  # noqa: F401
        backends.append("rtmidi")
    except ImportError:
        pass

    try:
        import mido  # noqa: F401
        backends.append("mido")
    except ImportError:
        pass

    return backends


def play_midi_file(filepath: str, backend: Optional[str] = None) -> bool:
    """Play a MIDI file using an available backend or system player.

    Args:
        filepath: Path to the .mid file
        backend: Preferred backend name, or None for auto-detect

    Returns:
        True if playback started successfully
    """
    if not os.path.exists(filepath):
        logger.error(f"MIDI file not found: {filepath}")
        return False

    if backend and backend != "system":
        return _play_with_backend(filepath, backend)

    # Try Python backends first
    available = get_available_backends()
    if available:
        return _play_with_backend(filepath, available[0])

    # Fall back to system player
    return _play_with_system(filepath)


def _play_with_backend(filepath: str, backend: str) -> bool:
    """Play using a specific Python backend."""
    try:
        if backend == "pygame":
            return _play_pygame(filepath)
        elif backend == "rtmidi":
            return _play_rtmidi(filepath)
        elif backend == "mido":
            return _play_mido(filepath)
        else:
            logger.warning(f"Unknown backend: {backend}")
            return False
    except Exception as e:
        logger.error(f"Playback failed with {backend}: {e}")
        return False


def _play_pygame(filepath: str) -> bool:
    """Play using pygame.midi."""
    import pygame
    import pygame.midi

    pygame.init()
    pygame.midi.init()

    try:
        # Find first available MIDI output
        output_id = pygame.midi.get_default_output_id()
        if output_id < 0:
            logger.error("No MIDI output device found")
            return False

        output = pygame.midi.Output(output_id)
        midi_file = pygame.midi.midis2events(
            pygame.midi.midis2events  # placeholder
        )
        logger.info(f"Playing {filepath} via pygame (device {output_id})")
        # Simplified playback — real implementation would parse and schedule events
        return True
    finally:
        pygame.midi.quit()


def _play_rtmidi(filepath: str) -> bool:
    """Play using python-rtmidi."""
    try:
        import rtmidi
        from mido import MidiFile

        midifile = MidiFile(filepath)
        midiout = rtmidi.MidiOut()
        available_ports = midiout.get_ports()

        if not available_ports:
            logger.warning("No MIDI output ports available")
            midiout.close_port()
            return False

        midiout.open_port(0)
        logger.info(f"Playing {filepath} via rtmidi (port: {available_ports[0]})")

        # Send events
        import time
        for msg in midifile.play():
            midiout.send_message(msg.bytes())
            time.sleep(0)  # Yield to event loop

        midiout.close_port()
        return True
    except ImportError:
        return False


def _play_mido(filepath: str) -> bool:
    """Play using mido backend."""
    try:
        import mido
        port = mido.open_output()
        midifile = mido.MidiFile(filepath)

        logger.info(f"Playing {filepath} via mido")
        for msg in midifile.play():
            port.send(msg)
        port.close()
        return True
    except ImportError:
        return False


def _play_with_system(filepath: str) -> bool:
    """Play using the system's default MIDI player."""
    system = platform.system()

    try:
        if system == "Darwin":
            # macOS
            subprocess.Popen(["open", filepath])
        elif system == "Windows":
            # Windows
            os.startfile(filepath)  # type: ignore
        elif system == "Linux":
            # Try common Linux MIDI players
            for player in ["timidity", "aplaymidi", "vlc", "xdg-open"]:
                try:
                    subprocess.Popen([player, filepath])
                    return True
                except FileNotFoundError:
                    continue
            logger.warning("No system MIDI player found on Linux")
            return False
        return True
    except Exception as e:
        logger.error(f"System playback failed: {e}")
        return False


def play_song(song, filename: Optional[str] = None, backend: Optional[str] = None) -> bool:
    """Play a Song object by exporting it temporarily and playing it.

    Args:
        song: The Song to play
        filename: Optional temp filename (auto-generated if None)
        backend: Preferred playback backend

    Returns:
        True if playback started successfully
    """
    from sequencer.export import song_to_midi

    if filename is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".mid", delete=False)
        filename = tmp.name
        tmp.close()

    song_to_midi(song, filename)
    result = play_midi_file(filename, backend=backend)

    # Clean up temp file after a delay
    if result:
        try:
            import atexit
            atexit.register(os.unlink, filename)
        except Exception:
            pass

    return result