
## Phase 2 enhancements

Add slash-bass chords such as `C/E` and optional `--stats` for total semitone travel. Slash bass is honored exactly in each candidate voicing. The search still performs a global minimum-movement optimization.

```sh
python3 chord_voicer.py --stats C/E F G
```

The first note in the C/E voicing is E (MIDI note 52); the summary reports whole-progression travel.
