# Event Ledger

A small, auditable event-sourced account ledger for developers testing replayable financial workflows. It stores integer minor units (for example, cents), replays immutable transaction events, and detects snapshot corruption. No floating point or third-party dependencies.

## How it works

Each event has a unique ID, account, and signed integer amount. Replay applies events in order to derive balances. A transfer writes a debit and credit pair only after validating amount and available funds. Snapshots include a SHA-256 checksum and are checked against a fresh replay when loaded. The checksum detects accidental corruption; it is not an authenticity signature.

## Usage

From this directory:

```sh
python3 ledger.py --demo
python3 -m unittest discover -s tests -v
```

Load a JSON event list or snapshot with `python3 ledger.py ledger.json`. Python 3.10+; standard library only.

## Features and options

- `--demo`: run a deterministic in-memory transfer example.
- `file`: read an event list or checksummed snapshot and print verified balances.
- `Ledger.append`: validate and replay unique integer-minor-unit events.
- `Ledger.transfer`: atomic debit/credit transfer with insufficient-funds and ID-collision checks.
- `Ledger.save` / `Ledger.load`: persist snapshots and verify checksums plus replayed balances.

## Testing

Run `python3 -m unittest discover -s tests -v` (6 tests) and `python3 ledger.py --demo`.

## Known Issues (Resolved)

- Transfer could partially debit an account if its generated credit event ID already existed. Regression test `test_transfer_id_collision_is_atomic` verifies the failure leaves events and balances unchanged.