# Build Log

Newest entry at the top. One entry per session at the bench.

## 2026-09-30 — Modem HAT: a real check-in over LTE

**Did:** Fitted the SIM7670G HAT (header plus OTG USB) with a Sunrise SIM.
It came up as a Qualcomm composite device, `05c6:9330`: RNDIS `usb0` and
four `ttyACM` ports. SIM7670G-MNGV, firmware V1.9.05; registered on Sunrise
228-02, LTE band 3 first, band 20 later, `CSQ 20`, RSRP −97 to −104 dBm on
the bench antenna. APN `internet`. `AT+DIALMODE=0` and `AT+CRESET` gave
data: ping 1.1.1.1 in 16–66 ms and public address 194.230.144.156 through
`usb0` only. It survives a power cycle with nothing re-applied. Then
`dadboxctl checkin` over LTE: ok, 2 messages in the inbox, ~1.1 KB each way
on `usb0`. `throttled=0x0` throughout: no under-voltage from the modem on
the bench supply. New `box/setup/modem_check.py` (stdlib only) does the whole
check in one command.
**Learned:** At `DIALMODE 1`, as it shipped, the modem registers, has a carrier
address and answers on 192.168.0.1, yet forwards nothing — easy to misread
as a coverage or APN problem. The AT ports are `ttyACM*`, not `ttyUSB*`.
`usb0` wins the default route over Wi-Fi (metric 100 vs 600), so on the
bench every byte is SIM data. **The Wi-Fi profile had vanished before the
modem went on:** the Imager's netplan files in `/etc/netplan/` were 0 bytes,
dated 25 Sep 16:41 — a power pull right after a write, with the overlay not
yet on. Recovered over the serial console with `nmcli`. It had also left
the SD card unseated once today (solid LED, no boot). Shut down before
pulling the plug until the read-only overlay is on.
**Next:** the PWRKEY wiring (GPIO 26 in `hw/pi.py` is still a guess — the
modem powers on by itself from USB); `rssi` from `AT+CSQ` on `ttyACM0` for
the app; which antenna connector the HAT uses (the wiki lists IPEX1 and
SMA), then order the antennas; turn the overlay on.

## 2026-09-25 — Amp and speaker: the first real message played

**Did:** Wired the MAX98357A (VCC to pin 2, GND, BCLK 12, LRC 35, DIN 40, SD
36) and the speaker. A test tone through the voicehat card, then five of the
seven messages waiting for the box, played with `dadboxctl play`: downloaded,
decrypted, the phone's AAC decoded by ffmpeg, played, reported. The server
shows `played_at` for all five, and the amp was on for each message's length
(10.5 s → 10.6 s, 60.9 s → 61.1 s) and off in between.
**Learned:** Jumper pins pushed through unsoldered holes on the amp board
gave total silence while every software check passed — the driver raised SD,
the I2S pins were in PCM mode. Solder the headers. The kernel logs "Enabling
/ Disabling audio amp" around each stream: a free check that playback
happened. `dadbox.local` drops out for minutes after a reboot on this
network; the Zero's address works.
**Heard:** "it sounds amazing" — clear at the default volume (70 %), on the
bench, in the open (not yet inside the aluminium box).
**Next:** the two buttons and their lights (`dadboxctl led test`); then the
mic; listen again once the speaker sits behind the grille.

## 2026-09-24 — First boot of the real Pi Zero 2 W (software only)

**Did:** Raspberry Pi OS Lite 64-bit (Debian 13, Python 3.13) via Imager,
`ssh dadbox` over home Wi-Fi. Setup from `box/setup/README.md`: ffmpeg (with
libopus), ALSA, lgpio, the `googlevoicehat-soundcard` overlay, serial console
on GPIO 14/15, I²C, hardware watchdog armed by systemd, the `dadbox` service
user, `/data` (a directory for now), the service and `dadboxctl`. The test
key and box token from `tools/fakebox/.env`. Full suite on the Zero: 94 tests
in 29 s. The service runs, checks in with the live server over Wi-Fi, and
downloaded the 7 messages waiting for the box. **Nothing is wired yet** — no
buttons, mic, amp or modem.
**Learned:** Raspberry Pi OS on Debian 13 no longer gives the first user
passwordless sudo (the user added it). The first boot grows the root
partition to fill the card, so a separate `/data` partition means
re-flashing. `config.txt` has no end-of-line comments. The voicehat driver
**owns GPIO 16** (amp SD_MODE) and raises it only while audio plays, so the
firmware must not claim it — "GPIO busy". lgpio writes its notification
pipes into the working directory: `LG_WD=/run/dadbox`, and
`GPIOZERO_PIN_FACTORY=lgpio` so gpiozero cannot fall back to sysfs. A backlog
of arrivals chimed seven times at once and the sound card refused the
overlapping opens: now one chime per burst, never overlapping.
**Next:** wire the buttons and LEDs and walk the pin map with `dadboxctl led
test`; then mic and amp (`arecord`/`aplay` on the voicehat card); then the
modem HAT. Tailscale before the box leaves the bench.

## 2026-09-22 — Box firmware designed and built on the Mac; virtual box

**Did:** The box's service, end to end, on fake hardware (`box/DESIGN.md`):
a pure core (`core.py`, events in, actions out) with gestures, light
rendering, the `/data` store, the link worker and the audio worker around
it; `dadboxctl` over a Unix socket; Pi drivers written against a proposed
pin map. `python3 -m dadbox.sim` runs it all with a fake server speaking
PROTOCOL v0.3 and a web page: hold the buttons, be the parent, pull the
link or the plug, skip time. 70 tests, including the whole round trip at
40× and boot recovery of an interrupted recording. Driven in the browser:
tap ignored, record, upload, reply, glow, play, `played_at`.
**Learned:** Putting the "record red is the mic pin" rule as an assertion in
the renderer caught a real bug in the first hour — the lock blink was grey,
which would have chopped the mic's supply; it is teal now. A fake clock
that every wait goes through makes a 90-minute conversation window a
two-second test. No ffmpeg on this Mac: the simulator seals WAV as codec 2
until it is installed.
**Next:** the parts. Then `hw/pi.py` against real pins: confirm the pin
map, the PWRKEY wiring, `arecord` from the shared mic pin, and run the same
tests through `dadboxctl` on the box.

## 2026-09-22 — Server live; phone ↔ fake box round trip

**Did:** Supabase Pro project in Zurich; schema, Edge Function and `pg_cron`
clock deployed (`server/`). Box-side container + AES-GCM in Python
(`box/dadbox/container.py`) against the shared vectors. `tools/fakebox`
drove the live server: dropped-link resume, shuffled/repeated chunks, Range
download, mute with who-set-what, box-late alert raised once and cleared.
Then the real thing: the iPhone app connected, played a synthesised Opus
message from the fake box, recorded a reply, and the fake box decrypted it
to valid 16 kHz AAC. Every message on the server is ciphertext.
**Learned:** Homebrew here belongs to another account — Deno and the Supabase
CLI run via `npx`, Python from `~/.venvs/dadbox`. The CLI's login token
reaches the database without the password. `verify_jwt = false` in
`config.toml` is honoured on deploy, so our own bearer tokens pass the
gateway. A tick at :00 and a box due at :13 is easy to misread as a bug —
wait for two ticks before judging the late alert.
**Next:** APNs key → pushes; then the box's HTTP client on the Pi speaks the
same protocol the fake box does.

## 2026-09-21 — iOS app, first build (no hardware)

**Did:** Designed the app (`ios/DESIGN.md`), then built it: `ios/DadBoxKit`
(31 tests) and the SwiftUI app, run in the iOS 26.5 simulator against an
in-memory demo box. Play, record-review-send and the *On the box → Played*
loop all work there. Shared container/encryption vectors in
`docs/testvectors/`.
**Learned:** iOS 26 / macOS 26 read **Ogg Opus natively** — `AVAudioPlayer(data:)`
opens the box's format from memory, so the app needs no demuxer and no codec
library. macOS can *encode* Opus (`afconvert`) but not write Ogg;
`tools/caf2ogg.py` bridges that for test audio without ffmpeg. A reinstalled
app must not number a message before it has seen the server's `max_seq` — found
by running it, now enforced in the store. This Mac's `xcode-select` points at
the Command Line Tools; Xcode works via `DEVELOPER_DIR`.
**Next:** the server, so `LiveBackend` meets something real; the box's Python
container code against the same vectors; then the app on the actual iPhone.

## YYYY-MM-DD — (template)

**Did:**
**Learned:**
**Next:**
