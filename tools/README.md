# Tools

Scripts and rigs.

## `serial_capture.py` — read the board without a human at the keyboard

Captures the Pi's UART console (GPIO 14/15 via a USB-serial adapter) for N
seconds or until a regex — boot logs before Tailscale is up, or when Wi-Fi is
off. Once SSH works, `ssh dadbox` replaces it.
See [docs/DEV-PROCESS.md](../docs/DEV-PROCESS.md). Needs `pyserial`.

## `fakebox/fakebox.py` — the box, without the box

Impersonates the box against the server — and, with `--as parent-a`, the app —
so a message can make the full round trip before any hardware or Xcode exists.
Uses the box's own `dadbox.container`, so what it sends is byte-for-byte what
the real box will send.

```bash
~/.venvs/dadbox/bin/python tools/fakebox/fakebox.py send --seconds 60 --drop-after 1   # the link drops…
~/.venvs/dadbox/bin/python tools/fakebox/fakebox.py resume                             # …and the upload resumes
~/.venvs/dadbox/bin/python tools/fakebox/fakebox.py --as parent-a send                 # the app answers
~/.venvs/dadbox/bin/python tools/fakebox/fakebox.py inbox --halves --play              # Range download, decrypt, played
~/.venvs/dadbox/bin/python tools/fakebox/fakebox.py --as parent-a list
```

Also: `checkin --fault storage`, `--no-mains --battery 15`, `--locked`,
`send --shuffle --repeat` (out-of-order and repeated chunks), `run`. Config in
`tools/fakebox/.env` (gitignored; see `.env.example`). The venv lives outside
the repo: `python3 -m venv ~/.venvs/dadbox && ~/.venvs/dadbox/bin/pip install cryptography requests pytest`.

## `mint_token.py` — bearer tokens

Prints a 256-bit token once, and the SQL that stores only its SHA-256.

## Later

- Flashing / provisioning helper
- Audio quality bench: record through the real mic and enclosure, compare
  codecs and gain settings on something other than vibes
