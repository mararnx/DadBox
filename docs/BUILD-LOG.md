# Build Log

Newest entry at the top. One entry per session at the bench.

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
