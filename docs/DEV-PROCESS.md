# Development process — and what Claude can do directly

Short version: **yes, Claude can drive the build–flash–log loop itself** from
this Mac, because the board plugs into this Mac and every step is a shell
command. What Claude cannot do is hear, see, touch or measure — so the
firmware is designed to make all of that visible as text.

## The loop on the T-A7670G R2

```
 edit → idf.py build → idf.py flash → capture serial 20 s → read → edit
        ▲ compiler errors            ▲ ESP_LOG, panics, backtraces
        │                            │  (decoded automatically)
        └── Claude ──────────────────┘
```

- **Build**: `idf.py build`. Claude reads compiler output and fixes it.
- **Flash**: `idf.py -p /dev/cu.usbserial-XXXX flash`. The R2 has a USB-UART
  bridge with auto-reset — no button dance. ~30–60 s at 921600 baud.
- **Logs**: `idf.py monitor` is interactive, so Claude uses
  [`tools/serial_capture.py`](../tools/serial_capture.py) — capture for
  N seconds or until a pattern, to a file, then read it. Panics come with
  backtraces that `idf.py monitor` decodes to file:line; the capture tool
  keeps the raw addresses and Claude runs `addr2line` when needed.
- **Iterate**. A full cycle is about a minute.

## What Claude can do without asking you

| Thing | How |
| --- | --- |
| Compile, flash, read logs, decode crashes | Bash on this Mac |
| Drive the box's state machine | the **serial console** (below) — `lid open`, `play`, `state` |
| Test the codec, container, CRC, queue logic | **host builds** — plain C compiled on the Mac, no board needed |
| Test the whole protocol end-to-end | `tools/fakebox` against `server/` — no hardware at all |
| Run and click through the iOS app | the iOS Simulator (once Xcode is installed) — build, launch, tap, screenshot; push via `xcrun simctl push` |
| Analyse a recording | pull the ADPCM/WAV off the SD card or over a debug upload; Python computes RMS, clipping, noise floor, spectrum |
| Reason about power | from your meter readings and the datasheets |

## What Claude needs you for

| Thing | Why | Cheapest way |
| --- | --- | --- |
| **Listening** | no ears | you say "tinny / muffled / fine"; Claude reads the spectrum alongside |
| **Seeing the ring / LEDs** | no eyes | `state` on the console prints what the ring *should* show; you confirm once, or send a photo |
| **Physical gestures** | no hands | the console fakes them; you do the real lid a few times per milestone |
| **Voltages, currents** | no meter | USB power meter inline; you read, Claude budgets |
| **Cellular** | needs the SIM and the room | Claude drives the modem over the console (`at AT+CSQ`, `at AT+CPSI?`) and reads the answers |

## The serial console — the thing that makes this work

ESP-IDF's `console` component gives a line-oriented shell over the same UART
as the logs. Every gesture and every state becomes text:

```
> state                 ring=WAITING(2) link=OK power=OK fault=NONE lid=closed vbat=3.91
> lid open              → mic on, ring LISTENING
> lid close             → trimmed 4.2 s, queued 01JAY…, GOT_IT pulse
> play                  → playing 01JAX… (12.1 s)
> inbox / outbox        list queued messages with seq, size, age
> rec 3 / dump last     record 3 s from the real mic; dump the buffer as hex/WAV over serial
| checkin               force a check-in now, print the response
> at AT+CSQ             pass an AT command to the modem, print the reply
> ring test             sweep every ring state for 2 s each — you watch once
> sleep 60              enter light sleep for 60 s (for the meter)
> sim link down         simulate no link — queue must fill, LINK LED must double-blink
```

With that, Claude can reproduce "the message didn't send after the lid closed
while offline" without anyone touching the box, and the ring's logic is
verifiable from `state` output alone. Build the console in M0, before the
audio, because it is how the audio gets debugged.

## Debug ladder — when it breaks

1. **Logs.** `ESP_LOGx` at INFO in normal use, DEBUG per module when hunting.
2. **`state`** on the console — is the state machine where you think it is?
3. **Assertions + panic backtrace** — decoded to file:line automatically.
4. **Core dump to flash** (`CONFIG_ESP_COREDUMP_ENABLE_TO_FLASH`), read back
   with `idf.py coredump-info` — the crash you didn't catch live.
5. **Host build** of the suspect module with the failing input — fastest
   iteration, no flash cycle.
6. **AT passthrough** for anything cellular: registration, signal, APN, PPP.

**No JTAG.** The classic ESP32's JTAG pins are GPIO 12–15 — exactly where the
R2's TF card lives. Live breakpoints would mean an ESP-Prog *and* no SD card
during that session. The S3 board would have had USB-JTAG built in; that is
the one debugging cost of ADR 0013. In practice log-driven debugging plus
host tests covers it.

## Structure the firmware so most of it runs on the Mac

| Host-testable (pure C, no ESP APIs) | Board-only |
| --- | --- |
| ADPCM encode/decode | I2S driver setup |
| container header + CRC32 | SD/FATFS mount |
| queue state machine, resume logic | `esp_modem` PPP, HTTPS |
| ring priority + resting timer | LED/WS2812 driver |
| chunking, `upload-state` reconciliation | sleep and gating |
| silence trim | button/lid debounce |

Aim for the left column being ~70 % of the logic. Claude tests it in
milliseconds with `cc` and a tiny test runner; the right column is thin
glue verified on the board.

## Setting up this Mac (nothing is installed yet — checked 2026-09-20)

```bash
brew install cmake ninja dfu-util
```
```bash
mkdir -p ~/esp && cd ~/esp && git clone -b v5.3 --recursive https://github.com/espressif/esp-idf.git
```
```bash
cd ~/esp/esp-idf && ./install.sh esp32
```
Then, per shell (or add an alias): `. ~/esp/esp-idf/export.sh`. Claude will
run it at the start of each firmware Bash command.

```bash
python3 -m pip install --user pyserial
```

For the iOS stream: **Xcode from the App Store** (the Command Line Tools
alone can't build apps or run the Simulator), then `sudo xcode-select -s
/Applications/Xcode.app` — that step needs your password, so it's yours.

Plug the board in and `ls /dev/cu.*` — the R2 shows up as
`/dev/cu.usbserial-…` or `/dev/cu.wchusbserial…`. Claude will find it.

## Modem specifics to expect

- `esp_modem` has no A7670 profile by name; the A76xx family speaks the
  SIM7600 AT set, so start with the **SIM7600 device profile** and adjust.
- Digital Republic rides Sunrise: APN is expected to be `internet`
  (**verify** on their support site once the SIM arrives). No username or
  password.
- PPP dial is `AT+CGDCONT=1,"IP","internet"` then `ATD*99#`. If registration
  fails, `AT+CPSI?` tells you the band and cell; `AT+CSQ` the signal.
- Cat-1 wakes from DTR sleep in well under a second — no PWRKEY cycling
  between check-ins.

## Milestone by milestone

- **M0** — console first, then I2S in, ADPCM, I2S out. Claude builds and
  flashes; you listen to `rec 3` + `play` in the cardboard box and say what
  you hear; Claude reads the spectrum of the dump.
- **M1** — SD outbox, container, `fakebox` already proved the server, then
  the modem: Claude drives AT commands over the console until PPP is up,
  then the first real upload. You supply the SIM and the room.
- **M2** — inbound: check-in, download, ring WAITING. Claude verifies with
  `state`; you confirm the glow once.
- **M3** — power: you clip the meter in, Claude runs `sleep`, `checkin`,
  `ring test` and turns your readings into the weekend budget.
