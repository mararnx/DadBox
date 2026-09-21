# Development process — and what Claude can do directly

Short version: **the box is a Linux machine, and Claude has a shell on it.**
On the bench over UART or home Wi-Fi; in the other house over Tailscale.
Every step is a command; what Claude cannot do is hear, see, touch or
measure — so the service makes all of that visible as text.

## The loop on the Pi Zero 2 W

```
 edit on the Mac → rsync to the box → systemctl restart dadbox → journalctl → edit
                   ▲ same Python runs on the Mac: unit tests first, in milliseconds
```

- **Deploy**: `rsync -a box/ dadbox:/opt/dadbox/ && ssh dadbox sudo systemctl restart dadbox`.
  Seconds. (`/opt` is on `/data`, the writable partition; the root is read-only.)
- **Logs**: `ssh dadbox journalctl -u dadbox -n 200 --no-pager`, or `-f` with a
  timeout. Python tracebacks are already file:line.
- **Poke it**: `ssh dadbox dadboxctl state` — or a Python REPL on the box.
- **Audio**: `arecord`/`aplay` for raw tests; the dump comes back with `scp`.
- **Modem**: `ip a`, `nmcli`, `curl -s ifconfig.me`. The HAT is an Ethernet
  interface for traffic; `/dev/ttyUSB2` is an AT port for diagnostics only
  (`AT+CSQ`, `AT+CREG?`, `AT+CPSI?`).
- **Remote**: identical, over Tailscale, from anywhere. The box in the other
  house is one `ssh dadbox` away. **Updates are `git pull`.**

## What Claude can do without asking you

| Thing | How |
| --- | --- |
| Deploy, restart, read logs, tracebacks, REPL, `gdb`/`strace` if it ever comes to that | SSH |
| Drive the box's state machine | `dadboxctl` — `lid open`, `lid close`, `play`, `state`, `checkin`, `ring test`, `sim link down` |
| Unit-test every bit of logic | the same Python on the Mac — no board needed |
| Test the whole protocol end-to-end | `tools/fakebox` against `server/`, or the real box over Tailscale |
| Run and click through the iOS app | the iOS Simulator (once Xcode is installed); push via `xcrun simctl push` |
| Analyse a recording | `scp` the WAV; RMS, clipping, noise floor, spectrum in Python |
| Check the link | from the box: signal via `AT+CSQ` / `AT+CPSI?` on `/dev/ttyUSB2`, throughput with `curl` |
| Power tuning | edit `config.txt`/`cmdline`, disable cores, read the MAX17048 gauge over I²C — then ask you for the meter |

## What Claude needs you for

| Thing | Why | Cheapest way |
| --- | --- | --- |
| **Listening** | no ears | "tinny / muffled / fine"; Claude reads the spectrum alongside |
| **Seeing the ring / LEDs** | no eyes | `state` prints what the ring *should* show; confirm once, or a photo |
| **Physical gestures** | no hands | `dadboxctl` fakes them; you do the real lid a few times per milestone |
| **Currents** | no meter | USB power meter inline; the gauge gives the rest |
| **First boot** | needs hands and a card reader | Raspberry Pi Imager: hostname `dadbox`, your SSH key, home Wi-Fi for the first boot. After that Claude does the rest over SSH |
| **Cellular** | needs the SIM and the room | plug in; Claude checks `ip a` |

## `dadboxctl` — the console, now a CLI over a Unix socket

```
dadboxctl state          ring=WAITING(2) link=OK power=OK fault=NONE lid=closed vbat=3.91 soc=68%
dadboxctl lid open       → mic on, ring LISTENING, capture started
dadboxctl lid close      → trimmed 4.2 s, opus 31 KB, queued 01JAY…, GOT_IT pulse
dadboxctl play           → playing 01JAX… (12.1 s)
dadboxctl inbox|outbox   list with seq, size, age
dadboxctl checkin        force one now, print the response
dadboxctl modem on|off   PWRKEY (or the 5 V feed switch)
dadboxctl ring test      sweep every ring state for 2 s each — you watch once
dadboxctl sim link down  no link: queue must fill, LINK LED must double-blink
```

Build it in M0, before the audio: it is how the audio gets debugged.

## Debug ladder

1. `journalctl -u dadbox` — structured logging at INFO; DEBUG per module when hunting.
2. `dadboxctl state` — is the state machine where you think it is?
3. Tracebacks — Python gives file:line for free.
4. Unit test the suspect module with the failing input, on the Mac.
5. `strace -p`, `py-spy dump` if something hangs.
6. For the link: `ip a`, `ping`, `curl`, `AT+CSQ` on the modem's AT port.

## Reliability rules that make this safe to run unattended

- **Read-only root overlay** (`raspi-config` → Overlay FS, or `overlayroot`).
  All writes go to `/data`. A power pull cannot corrupt the OS.
- `/data` is ext4; every message is `write → fsync → rename`.
- `systemd` restarts the service on failure; a hardware watchdog
  (`dtparam=watchdog=on`, `RuntimeWatchdogSec=`) reboots a hung Pi.
- Wi-Fi is off in the field (power); Tailscale over LTE is the door in.
- A second imaged SD card lives in a drawer.

## Setting up this Mac (checked 2026-09-20)

Nothing embedded is needed any more. Node is installed. For the iOS stream:
**Xcode from the App Store** (Command Line Tools alone can't build apps or run
the Simulator), then `sudo xcode-select -s /Applications/Xcode.app` — needs
your password. Tailscale is already on this Mac.

```bash
python3 -m pip install --user pyserial
```
(for the bench UART console via `tools/serial_capture.py`; a CP2102 USB-serial
adapter on GPIO 14/15, 115200 baud.)

## Setting up the box (first time; Claude does everything after step 2)

1. Raspberry Pi Imager → Raspberry Pi OS **Lite 64-bit** → hostname `dadbox`,
   SSH with your key, home Wi-Fi. Boot it.
2. `ssh dadbox` from the Mac works → hand over.
3. Claude: `apt` (ffmpeg, alsa-utils, python3-venv), Tailscale, `config.txt`
   (`dtoverlay=googlevoicehat-soundcard`, `dtparam=audio=off`,
   `dtparam=spi=on` for the ring, `dtparam=watchdog=on`, HDMI off), `/data`
   partition, the overlay, the service, `dadboxctl`. Then Wi-Fi off, modem on.

## Milestone by milestone

- **M0** — `dadboxctl` first, then `arecord` → WAV → `ffmpeg` → Opus → `aplay`.
  You listen in the cardboard box; Claude reads the spectrum.
- **M1** — modem on, `/data` outbox, resumable upload to `server/`, Tailscale
  up. From here on Claude works on the box directly.
- **M2** — inbound: check-in, download, ring WAITING. `state` verifies it; you
  confirm the glow once.
- **M3** — power: meter in, Claude tunes cores/clocks and the modem gate,
  reads the gauge, and turns your readings into the cell count.
