# Tools

Scripts and rigs.

## `serial_capture.py` — read the board without a human at the keyboard

Captures the Pi's UART console (GPIO 14/15 via a USB-serial adapter) for N
seconds or until a regex — boot logs before Tailscale is up, or when Wi-Fi is
off. Once SSH works, `ssh dadbox` replaces it.
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
