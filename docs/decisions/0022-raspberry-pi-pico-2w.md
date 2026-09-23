# ADR 0022 — Raspberry Pi Pico 2 W instead of the Pi Zero 2 W

**Date:** 2026-09-23
**Status:** proposed — the board is the user's decision (2026-09-23); the
four choices under *Decisions needed* are open. When accepted it supersedes
the compute board of [ADR 0014](0014-raspberry-pi-zero-2w.md) and revises
[ADR 0019](0019-mains-first-battery-deferred.md) and
[ADR 0021](0021-doorbell.md).

## Context

The user has switched the box's computer to a **Raspberry Pi Pico 2 W**: an
RP2350 microcontroller (two Cortex-M33 cores at 150 MHz, 520 KB SRAM, 4 MB
flash, PIO), with a CYW43439 for 2.4 GHz Wi-Fi and Bluetooth. It runs no
operating system.

Everything above the drivers was built for Linux (box/DESIGN.md): a Python
service under `systemd`, `arecord`/`ffmpeg`/`aplay`, an ext4 `/data` with
fsync-then-rename, SSH over Tailscale, `dadboxctl` on a Unix socket. None of
that exists on a Pico. What carries over is the *design*: the pure core
(events in, actions out), the gestures, the two light vocabularies, the
store's durability rules, the link round, the protocol, the server, the app,
and the simulator as the executable specification.

## What the Pico gives

- **It can sleep.** A Pi Zero idles at ~100 mA and cannot; an RP2350 in
  dormant draws well under a milliamp. With the modem off between check-ins,
  the weekend on battery that [ADR 0005](0005-battery-required.md) wanted and
  ADR 0019 gave up on is back within reach.
- **Instant on.** No 25 s boot after a power cut.
- **No SD-card OS to corrupt**, no overlay, no apt, no updates to a root
  filesystem over years.
- Cheaper and smaller.

## What it takes away

- **No SSH, no Tailscale, no journal.** On the bench: the Debug Probe
  already ordered (SWD for flashing and `gdb`, UART for a console). In the
  field: only what the box reports to the server. DEV-PROCESS.md's "Claude
  debugs a box in the other house live" ends.
- **No `ffmpeg`.** Encoding and decoding are firmware, and the parent's
  AAC (codec 3) cannot reasonably be decoded on the box.
- **4 MB of flash** holds the firmware; it cannot hold five minutes of
  audio (16 kHz × 16 bit × 300 s = 9.6 MB of PCM) plus an offline outbox.
- **No USB Ethernet modem.** The SIM7670G must be driven over its UART
  (AT commands, PPP) instead of appearing as a network interface.
- **Updates** need an OTA mechanism of our own (RP2350 A/B partitions),
  not `git pull`.

## Decisions needed

### 1. Firmware language — recommend **C with the Pico SDK**

| | C / C++ (Pico SDK) | MicroPython |
| --- | --- | --- |
| I2S in/out | PIO, DMA — standard | `machine.I2S` — works |
| ADPCM / Opus at 16 kHz | trivially fast | too slow in pure Python; needs native code |
| AES-256-GCM | mbedTLS (in the SDK) | not in `cryptolib` (no GCM) — needs native code |
| TLS, lwIP, PPP | SDK + lwIP | built in, less control |
| Porting the Python core | rewrite, ~1–2 k lines | nearly a copy (no `dataclasses`/`enum`) |
| Debugging | `gdb` over SWD | REPL over USB/UART |

MicroPython would keep the core almost as written, but every hot path —
audio, codec, GCM — would need native modules anyway. C with the SDK keeps
one language on the box. The Python core and simulator stay as the
reference: the C core is tested against the same scenarios and the shared
container vectors.

### 2. Connectivity — recommend **keep cellular** (ADR 0002 stands)

The box still travels between two homes; that argument is untouched by the
board. The SIM7670G HAT connects by jumper wires: 5 V, GND, UART TX/RX,
PWRKEY. Recommended: **PPP over the UART into lwIP**, so TLS and HTTP run
on the Pico and the modem only carries bytes — the same shape as today.
The modem's own AT HTTPS stack is the fallback if PPP fights. UART at
921 600 baud moves a 2.4 MB message in under a minute.

The Pico's Wi-Fi is used on the bench (home network, no SIM needed) and is
free to become a fallback later. Not a second link in v1.

### 3. Storage — recommend **a microSD breakout on SPI, with littlefs**

"The capture is on disk while the child is still talking" and "the outbox
is never evicted" need more than 4 MB of NOR flash. A microSD card on SPI
gives gigabytes. **littlefs** instead of FAT: it is designed to survive a
power cut mid-write, which FAT is not — and pulling the plug is how the
first box turns off. The same file layout as `/data` today (outbox, inbox,
capture, seq, lock, settings, keys, config). One new part, a few francs.

### 4. Codec — recommend **IMA-ADPCM (codec 1) both ways in v1**

PROTOCOL.md already reserves codec 1 "so an ESP32 box could still speak
the protocol". Four bits a sample: 64 kbit/s, 2.4 MB for five minutes —
under the server's 4 MB message limit, and Flat 1 is unlimited. Encoding
and decoding are a few integer operations per sample, so the box can
encode *while* recording, straight to the card.

- **Box → parent:** ADPCM in a WAV container. iOS plays IMA-ADPCM WAV
  natively.
- **Parent → box:** the app must stop sending AAC to the box and send
  ADPCM WAV instead. That is a protocol change for the iOS stream.
- The server allows codec 1 (today it accepts only 2 and 3).
- Opus on the RP2350 is possible later; it is an optimisation, not v1.

## Other consequences, if accepted

- **Pins** fit: 26 GPIOs; needed ≈ 24 — six button-LED channels, two
  switches, two status LEDs, amp enable, I2S (shared BCLK/LRCLK, data in,
  data out), modem UART + PWRKEY, SD on SPI, I²C kept for a gauge. The mic's
  supply stays on the record button's red LED pin: the wiring rule survives.
- **ADR 0021 (doorbell)** was built on a Linux WebSocket client. On the
  Pico it is possible over lwIP + mbedTLS but not v1; the box polls every
  minute on mains as [ADR 0015](0015-adaptive-polling.md) first said.
- **ADR 0019** can be revisited: the battery becomes cheap to run. The
  UPS Module 3S is oversized for a sleeping Pico; a single cell with a
  charger board may do. Measure first.
- **`dadboxctl`** becomes a line console on the UART (same commands), and
  the simulator stays the way to drive the whole box on the Mac.
- **Field diagnostics** move into telemetry: a small ring buffer of recent
  log lines sent with the check-in when a fault is set.
- **Toolchain on the Mac:** the Arm GNU toolchain (Arm's own macOS
  installer), `cmake` and `ninja` from pip, the Pico SDK from git; flashing
  by UF2 drag-and-drop or through the Debug Probe. Homebrew is not needed.
- **BOM:** Pico 2 W and a microSD breakout in; the Pi Zero 2 W kit
  becomes a spare. Update `hardware/bom/bom.csv` on acceptance.
- **Docs to revise on acceptance:** CLAUDE.md (hardware line, working on
  the box), BRIEF, ARCHITECTURE, DEV-PROCESS, PROTOCOL (codec 1), box/
  README and DESIGN, setup/.

## Alternatives considered

- **Keep the Pi Zero 2 W** — the firmware for it is written and tested on
  the Mac; the cost is power (no sleep) and a Linux image to maintain. The
  user chose the Pico.
- **ESP32-S3** ([ADR 0012](0012-lilygo-t-sim7080g-s3.md), superseded) —
  PSRAM would help audio buffering, but the Pico is the user's choice and
  its PIO makes I2S and the LED PWM easy.
