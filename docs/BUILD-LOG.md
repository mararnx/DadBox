# Build Log

Newest entry at the top. One entry per session at the bench.

## 2026-10-06 (night) — App and server catch up with the box

**Did:** No bench work; the iOS app and the server caught up with today's
box changes. App (TestFlight build 12): reads the box's `doorbell` and says
how soon a message reaches the box (at once with the doorbell, within 15 s
just after use, at the next check-in when locked); a locked box shows "next
check-in in 28 min"; a new setting for the plugged-in backstop interval
(`backstop_minutes`, 5–30); the light guide rewritten for ADR 0024 as
revised today (blue–cyan ready flow, Play's colours at power-on, cyan-white
lock flashes); a `409` seq conflict renumbers above `max_seq` and retries
(ADR 0025); `late: null` before a first check-in no longer breaks the status;
the mute toggle removed. Server: mute dropped from the settings rules and,
by migration `20261006200000_no_mute`, from the live settings row; `PATCH
/settings` answers 403 to anything but poll, quiet hours, light and volume,
as PROTOCOL.md says. Checked live: settings hold no mute, a mute PATCH gets
403, the box reports its doorbell joined.
**Learned:** The app had silently kept a mute toggle the box had ignored
since ADR 0020 — a contract change needs a sweep of all three streams, not
only the one that prompted it.
**Next:** Look at the Box screen in build 12 on the phone. The
doorbell bench measurements (ADR 0021), and the new loudness on more takes.
Answered from the evening entry: the firmware stage of power-on (all three
of Play's colours on, which looks red at 3.3 V) is fine as it is.

## 2026-10-06 (evening) — Lights, sounds and loudness tuned by eye and ear

**Did:** With the box closed and on mains, tuned what a child sees and hears,
each step deployed and judged live. Faster answers: 15 s check-ins for 5 min
after use (ADR 0015 revised). Power-on: Play blue from the firmware
(`config.txt gpio=25`, later all three: `gpio=23,24,25`), a rainbow from ~10.6 s (`dadbox-bootlight.service`,
system Python + lgpio, installed through `overlayroot-chroot`), handed to
the service through `/run/dadbox/bootlight-stop`, until first ready (ADR
0024 §7). A white point tuned live through a file-fed PWM holder: red 25 %,
green 63 %, blue 100 %. Ready became a blue–cyan flow on Record, 4 s,
constant brightness; Play dark; Record dark while a message waits (§8).
Sounds chosen from five synthesized styles each, numbered by green blinks on
Record: a two-note "bee-boo" before and after recording (the start tone
played to the end before the mic gets power), a marimba pair for a new
message that repeats once after 10 s, a low marimba pair for lock on/off.
Lock: two cyan-white flashes on both buttons, one on unlock, three on a
press while locked (§9). Messages normalized with `loudnorm` (EBU R128,
−16 LUFS). User walked through power-on, recording, receiving and lock:
all as intended.
**Learned:** gpiozero's `PWMLED` truncates duty to whole percent — at a dim
16 % that is a dozen visible steps; lgpio's `tx_pwm` takes a fraction. A
smooth fade needs constant brightness, not more frames: crossfade straight
in duty between colours that look equally bright (green 25 % ≈ blue 100 %
on these buttons). The built-in resistors are sized for 5 V, so at 3.3 V red
outshines green outshines blue and on/off mixes look red. Record can never
show white: its red is the mic. lgpio software PWM costs ~0.85 % of a core
per 100 Hz per two pins. A fixed capture gain cannot cover the ~20 dB between
takes; `loudnorm` took a quiet one from −39 to −21 dB mean at ~16 s extra
encode for 3 minutes. A `dadboxctl record` test take is uploaded if it holds
1.3 s of "speech" — one went to the parent's archive (cannot be deleted).
**Next:** Is the first ~10 s (steady blue, the firmware stage) good enough,
or try a pull-up on red for a rough white. Judge the new loudness on more
takes from across the room.

## 2026-10-06 — New amp: loud scratch at any level, until it was rewired to the scheme

**Did:** Fitted a new amp, the same "MAX98367" clone module as U5 (silkscreen
"I2S 3W Class D Amplifier Module V1.0"). Digital silence still scratched,
lower than before and audible at 1 m. Ruled out one by one: Wi-Fi traffic,
the modem (USB unplugged), the supply (power bank), the in-box wire length
(short jumpers), the frame format (`hifiberry-dac` with 16-bit frames for
one boot, then the voicehat overlay restored). The telling test: one note
three times, each 10× (later 20 dB) quieter — heard **equally loud, or
louder**, and a left-only and a right-only note both played. Powering the
mic (GPIO 17 high) made it cleaner; taking the mic's clocks off, cleaner
still, but no quieter. Then an I2S loopback, a jumper from header pin N to
pin 38 (PCM_DIN) with the mic's data wire off: DIN on 40 came back
bit-exact (9.2 M bits, 0 errors) with the amp as load; LRC on 35 gave
`0x00000001 / 0xFFFFFFFE` in every frame; BCLK on 12 read constant with no
glitch. With the Pi cleared, the amp was reconnected to `WIRING.md`: a
falling test went very quiet and clean, and five notes at about −18 dBFS
"sound great". GAIN left unconnected (9 dB). Then the mic, clocks back on,
service stopped, powered by GPIO 17 (red light on) and recorded raw: left
channel only (L/R to GND), speech at 30 cm −28 to −39 dBFS rms, peaks
−8 dBFS, right channel digital zero. Played back through the amp: "clear
and natural".
**Learned:** Loudness that does not follow the level means the amp is
reading the wrong bits — no gain or volume setting touches it, so stop
turning things down and check the wiring. The loopback is a free, exact
test of the Pi's audio pins: a jumper to pin 38, `arecord` while `aplay`
sends a known pattern, then compare words; check with `pinctrl lev 20`
that pin 38 actually toggles, or a loose jumper reads as a clean zero. Which
wire was wrong before the rewire was not identified. GPIO 16 drives SD at
3.3 V, yet the amp plays both channels: this clone does not select a channel
the way a MAX98357A does (harmless, the stream is mono). The mic's output
drifts after power-up: a silent take swings its DC by ±0.18 of full scale
(−15 to −30 dBFS rms, louder than speech) and settles only after ~1.5 s,
far past the 100 ms the capture drops. But it is subsonic: the box's own
encode (Opus 16 kbit/s, `-application voip`, which high-passes) takes the
same take to −71 to −77 dBFS throughout, leaving one 50 ms click at
power-on at −51 dBFS. That was true of the encode, not of the box:
the first real recordings through the service went wrong twice. (1) A
normal release came out as `capture failed: arecord ended` (fault CAPTURE,
nothing queued): `stop()` terminates arecord while the pump waits in
`read()`, which returns `b""` before the loop re-checks the stop flag.
Fixed in `hw/pi.py`, with a regression test. The capture stayed on `/data`
as designed and was sent by the boot recovery. (2) Both recordings reached
the server as exactly **2.0 s** (one was 5.4 s): `trim` counted the drift as
speech (a silent take through the service's path: 1.9 s "speech") and real
speech at 50 cm, −52 to −66 dBFS in that path, as silence against
`SPEECH_RMS` −38 dBFS. The plaintext is deleted once queued, so both
messages are cut for good — and a softly spoken message would have been
discarded whole as under 1 s of speech. Fixed: `dsp.level` takes each 2 ms
slice's mean and slope out before measuring (drift to the noise floor;
−7 dB at 300 Hz, flat above 1 kHz; 1.1 s per minute of audio on the Zero),
used for trim and the silence stop; `SPEECH_LEVEL` −70 dBFS from a bench
take, set low on purpose. Deployed. GAIN on VIN made no
audible difference while the bits were wrong. The box was rewired twice
with power on today.
**Next:** the modem is still missing from `lsusb` after being unplugged —
reseat its USB lead; play a real message with `dadboxctl play` at 70 % and
the chime; a real recording through the service (Record button →
outbox → the phone) whose length matches what was said; re-measure
`SPEECH_LEVEL` with the mic behind its hole, and with a child; the capture
path may lose level (S32 → S16, stereo probably averaged to mono with an empty right
channel, 48 → 16 kHz in the ALSA plug) — take the left channel and add gain;
correct the amp in the BOM and `WIRING.md` (still open from 10-02).

## 2026-10-02 — All wires on: buttons pass, the amp scratches even on silence

**Did:** First boot on header power (5 V on pins 4/6, ADR 0026): no
undervoltage (`throttled=0x0`). With the service stopped, each button-light
channel lit on its own via `pinctrl`, and both switches read clean presses
and releases. The box still ran the old pin map (power key on GPIO 26), so
GPIO 4 floated high with the HAT's P4 on it; deployed the current code, which
holds it low. Then the speaker: a tone, a voice message, and pure digital
silence all came out as loud scratch. Remote checks from the Pi found no
bridge between BCLK, LRC and DIN and none to ground; the mic's clock wires
were unsoldered, and the modem's radio was switched off (`AT+CFUN=0`), with no
change. The photo showed the amp's ground wire on **GAIN**; moved to GND, the
tone's pitch came right, but it still scratched.
**Learned:** The amp is the generic MAX98357 module (U5, the spare; the shop
calls it MAX98367), not the Adafruit board: two rows, VCC/GND on both, a JST
speaker plug. It played clearly on 2026-09-25. A loud scratch on **digital
silence** means the noise starts in the amp, not in the signal: most likely
damaged while it ran without ground. White on Record is never needed
(only Play's lock blink is white); red swamps green and blue at 3.3 V. The
modem's USB hub dropped twice ("disabled by hub (EMI?)", self-recovered in
about 1 s), both near a button press, cause open. `dadboxctl modem off`
did not switch the modem off: the power key on GPIO 4 is still unproven
(DIP 3, the pin 7 joint). The mic was never tested: its clocks are
disconnected.
**Next:** test the speaker alone (3–4 Ω on a meter; a clean click from an
AA cell), then a new amp; reconnect the mic's clocks and test it; DIP 3 and
the power key; `gpio=4=op,dl` in `config.txt`; correct the amp in the BOM and
`WIRING.md`.

## 2026-09-30 (evening) — A 3-minute note over LTE: refused, and the box went offline

**Did:** Queued 3 min of synthetic voice through the box's own pipeline
(trim, ffmpeg Opus 16 kbps, seal, fsync to the outbox). There's no mic yet.
Container 339,493 bytes (0.34 MB) for 180,000 ms; the nominal size at
16 kbps is 0.36 MB. LTE itself was fine: `usb0` default route, ping 49–71 ms.
**Learned:** The re-flash left no `/data/seq`, so the note got seq 1, which
the server already had: `409 seq already used by another message`. The link
round stopped at that upload and never checked in, so from 18:00 to 18:10 the
box was `link=DOWN`. Moving the (synthetic) note out of the outbox brought it
straight back. Fixed in ADR 0025: `max_seq` on check-in and on the 409, the
box renumbers and retries, and a 4xx on one message no longer stops the
check-in. Deployed both; the first check-in raised `/data/seq` from 1 to 10.
Re-run: the same 3-minute note (seq 11, 339,493 bytes, 11 chunks) went from
queued to `complete` in **8.5 s**, 8.2 s of it uploading: ~41 KB/s (~330 kbit/s)
of payload, 400,593 bytes on `usb0` including TLS, HTTP and the SSH session.
**Next:** time it on the real antenna in the child's room; add `/data/seq`
to the `/data` backup.

## 2026-09-30 — USB-C panel coupler: powers the box one way up only

**Did:** Tried the Exsys EX-49195 (USB-C socket to socket, panel mount) as the
5 V inlet with a USB-C → micro-USB lead inside. The Pi boots with the plug
one way up and stays dark the other way. Exsys's own datasheet says so:
"the connections are not reversible due to the technical specifications of
USB-C".
**Learned:** A USB-C supply only switches 5 V on after it sees the sink's CC
resistor, and a plug carries one CC wire while a socket has two — a
socket-to-socket coupler joins each CC pin straight through, so the wire
meets its partner in only half the orientations. Power pins were never the
problem. A socket with a cable tail passes both CC lines, and the resistor
then has to be in whatever sits on the tail: test the socket-to-micro-USB
adapter straight on the USB-C supply before drilling.
**Next:** order the Exsys EX-49222 (same 22.3 mm hole, 30 cm tail) and a
Delock 65927 adapter; the socket moves to the back-left corner and the
antenna to its right (`hardware/LAYOUT.md`), because the new flange is
~30 mm, not 16.

## 2026-09-30 (evening) — Power-cut test on the read-only root

**Did:** Four pulls of the plug: one while idle, three more at different
times after power-on, the early ones before `/data` was even mounted. After
each: Wi-Fi back at once, LTE and Tailscale up, the service running, `/data`
mounted `ext4 rw` and marked clean, a check-in ok, and all ten files on
`/data` (config, key, `seq`, the two inbox messages) checksum-identical to a
fingerprint taken on the Mac beforehand. Also a clean image of the card after
`zerofree`: 1.45 GB, in `~/DadBox-backups/2026-09-30-clean/` with restore notes.
**Learned:** A pull during a recording cannot be tested without a mic: the
firmware stops a recording after 20 s of silence and drops one with under
1 s of speech — the rescued capture after a pull included — so a silent test
recording is gone before the plug is. `/data/tmp` is emptied at boot; keep
test fingerprints off the box. Every boot starts with the clock where the
root image last left it (17:23 today) until NTP — seconds on Wi-Fi.
**Next:** the pull mid-recording, speaking into the mic, once it is soldered.

## 2026-09-30 (afternoon) — Re-flashed: read-only root, /data partition, Tailscale, signal in the app

**Did:** Re-flashed the card so root could go read-only (the old root filled
the card, and ext4 cannot shrink while mounted). Before first boot, on the
Mac: `resize` out of `cmdline.txt`, `growpart` off in `user-data`. Root then
grown to 8 GB and `/data` made in the other 20.6 GB (`sfdisk`, no `parted`
on the image); the old `/data` restored with its 2 inbox messages. Setup
redone from `box/setup/README.md`. Then the overlay (`overlayroot`),
boot partition read-only, journal in RAM, zram-only swap, cloud-init off.
Tailscale with its state on `/data`: `ssh dadbox` is the Tailscale name,
reachable over LTE; `ssh dadbox-lan` the home network. The box now sends
`rssi` from `AT+CSQ` (−75 dBm on the server) and the app shows it, or says
there is no reading. From the HAT schematic: its PWR line is header pin 7
(P4) via DIP switch 3; the wire from Zero pin 37 is on, DIP 3 not yet, so
the power key is untested. The box runs the repo's current code
(`4c3ae52`, status LEDs gone). Clean image of the boot and root partitions,
plus `/data`, in `~/DadBox-backups/2026-09-30-clean/` on the Mac.
**Learned:** `overlayroot=tmpfs` alone overlays **every** fstab mount under
`/` in RAM, `/data` included: a recording would have vanished at the next
power cut. `overlayroot=tmpfs:recurse=0`, and `findmnt /data` must say
`ext4 rw`. `usb0` wins the default route (metric 100): the first `apt`
pulled 115 MB over LTE and took 20 minutes; Wi-Fi was several times
faster. The SIM is unlimited, so LTE stays first, as in the field. macOS
`openrsync` ignores `--chmod` and the Mac's files are mode 600: the service
could not read its own code — `box/deploy.sh` fixes modes on the Pi.
`setup/modem_check.py` made setuptools see a second package; `pyproject`
names `dadbox*` now.
**Next:** the power-cut test — pulls while idle, mid-boot and mid-recording,
checking Wi-Fi, `/data` against a checksum list and a check-in each time;
DIP 3 on and the power key, then the firmware presses it when the modem
stops answering; soldering the buttons and the mic.

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
