# Tools

Scripts and rigs.

## `serial_capture.py` — read the board without a human at the keyboard

`idf.py monitor` never returns; this captures for N seconds or until a regex,
optionally resetting the board or sending a console command first. It is how
Claude reads logs, panics and console output during the build–flash loop.
See [docs/DEV-PROCESS.md](../docs/DEV-PROCESS.md). Needs `pyserial`.

## Wanted first — `fakebox`

A script that impersonates the box against the server: uploads a message,
polls for inbound, reports telemetry, and can pretend to be offline or flat.

This is the highest-value thing in the repo before the parts arrive. It unblocks
the server and iOS streams completely, and it doubles as the test rig for
everything the real firmware will later have to get right.

## Later

- Flashing / provisioning helper
- Audio quality bench: record through the real mic and enclosure, compare
  codecs and gain settings on something other than vibes
