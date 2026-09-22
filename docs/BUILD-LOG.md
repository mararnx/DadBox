# Build Log

Newest entry at the top. One entry per session at the bench.

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
