# Security & privacy

**Role.** A child's voice, recorded in a home that isn't yours, sent across a
public network. Handle it like it matters.

## Current design

TLS in transit, encrypted at rest, short retention, no speech services, no
third-party analytics.

## Checked

- **Transit encryption isn't enough if a third party terminates it.** With a
  Notecard, Notehub sees the bytes. With a hosted server, the host sees the
  disk. The fix in both cases is the same: **encrypt the audio on the box and
  in the app, with a key the server never has.** AES-256-GCM, a family key
  provisioned once into the box's NVS and the phone's Keychain. The server
  stores ciphertext and can't play it. Cheap to build now, impossible to
  retrofit honestly later.
- With on-device encryption, hosting becomes a pure availability question,
  and the "Pi vs VPS" argument mostly evaporates.
- Key provisioning is a one-time ceremony for one family: generate on the
  phone, show a QR, the box… has no camera. Options: bake it at flash time
  from a `.env` (fine for a one-off), or a short-lived pairing over USB.
- Device auth to the server: a per-device bearer token, separate from the
  family key. Losing the token lets someone *send*; it must not let them
  *listen*.
- Physical: the box is in another home. Anyone with a USB cable can read
  flash unless it's encrypted. The ESP32 supports flash encryption and secure
  boot; both are a one-way door. For a one-off, flash encryption on, secure
  boot off, is a reasonable line.
- Consent: the co-parent is on board, but "on board" should include knowing
  the box records only while the lid is open / button held, and that they can
  see the mute state. Write that down for them — one page.

## Questions

1. **On-device encryption in v1?** Suggest yes; it's a few hundred lines and
   changes the trust model from "trust the server" to "trust the box and the
   phone", which is the right shape for this data.
2. **Key ceremony** — bake at flash time, or pair over USB? For one box, bake.
3. **Flash encryption on the ESP32?** One-way; makes reflashing a chore.
   Suggest: on, from M3 — not during development.
4. **Who can trigger an OTA?** The server, authenticated. Signed images? For
   one family, a hash pinned in the manifest is proportionate.
5. **What does the co-parent get to see?** Mute state, quiet hours, that it's
   alive. Not the messages. Is that the right line?
6. **Legal** — recording consent rules vary by country and by who else is in
   the room. This project's answer is design (hard gating, visible state, the
   co-parent's knowledge) rather than lawyering, but is there anything in the
   custody arrangement that says how the child communicates? Worth a glance.
