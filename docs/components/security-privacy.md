# Security & privacy

**Role.** A child's voice, recorded in a home that isn't yours, sent across a
public network. Handle it like it matters.

## Current design

- **No red light, no mic.** The mic's 3.3 V supply and the record button's
  red LED are driven by the **same GPIO pin**
  ([ADR 0016](../decisions/0016-two-buttons-no-lid.md)). If the light is off
  the microphone has no power — a wiring fact, not a firmware promise. The
  box lives in rooms with other people in them.
- **The audio is end-to-end encrypted in v1** ([ADR 0017](../decisions/0017-managed-hosting-e2ee.md)):
  AES-256-GCM, container flag bit0, keys on the box and in the iPhone
  Keychain. TLS in transit; the managed host stores and moves ciphertext and
  cannot play it.
- **Messages are archived forever** ([ADR 0018](../decisions/0018-archive-forever.md)) —
  as ciphertext on the server and in the app's own copy. Deleting is a
  deliberate act in the app. The box is not an archive.
- Three bearer tokens, one per identity ([PROTOCOL.md](../PROTOCOL.md)). The
  box's token can fetch **only its own inbox**, never history.
- The host still sees that messages exist, when, how long, between whom, and
  the box's telemetry. Pushes carry "New message" and an id — never content.
- No transcription, no speech services, no third-party analytics, ever.

## Checked

- **Transit encryption isn't enough if a third party terminates it.** A
  managed host holds the disk and terminates TLS. The fix: **encrypt the
  audio on the box and in the app, with a key the server never has.** Cheap
  to build now, impossible to retrofit honestly later — hence v1. Hosting
  then becomes a question of availability and durability, not of who can
  listen.
- **The key now guards everything ever said**, not the last day's messages.
  It syncs through iCloud Keychain and a paper copy goes in a drawer. Lose
  every copy and the archive is noise.
- Device auth to the server: a per-device bearer token, separate from the
  family key. Losing the token lets someone *send*; it must not let them
  *listen*.
- Physical: the box is in another home. Anyone can pull the SD card and read
  it. LUKS on `/data` would need its key on the same card, unless a key is
  typed at boot (nobody will). The honest position: message encryption (the
  family key in a file only root reads) makes the queued *audio* unreadable
  to a casual card-puller; the OS itself is not secret. A key that does leak
  from the card opens the archive only to someone who *also* has a parent
  token — which is why the box's token is inbox-only and re-keying must be
  possible (`key_id` in the envelope).
- Consent: the co-parent is on board, but "on board" should include knowing
  that the box records only while the record button is red — a smaller
  signal than an open lid was, so it has to be explained — that the mic has
  no power otherwise, that messages are kept, encrypted, and by whom they can
  be heard, and that quiet hours are theirs to set too. Write that down for them —
  one page.

## Questions

1. **What does the co-parent get to see?** Quiet hours, that it's
   alive. Not the messages. Is that the right line?
2. **Key ceremony** — generate on the phone; then bake it into the box at
   setup from a `.env` (the box has no camera), or pair over USB? For one box,
   bake. Plus the iCloud Keychain sync and the paper copy.
3. **Re-keying** — when and how: new key going forward, old one kept on the
   phone for the archive. What triggers it — a lost box?
4. **The raw capture on the card** is plaintext until it is encoded and
   encrypted. How long does it live, and how is it removed? See
   [storage-queue.md](storage-queue.md) Q5.
5. **Who can get into the box?** Updates are SSH over Tailscale, so the
   Tailscale account is a way into a box in another home — the mic still
   cannot run without its red light. Key-only SSH, a tight ACL, and who holds
   that account.
6. **Legal** — recording consent rules vary by country and by who else is in
   the room. This project's answer is design (the mic wired to its light,
   visible state, the co-parent's knowledge) rather than lawyering, but is
   there anything in the custody arrangement that says how the child
   communicates? Worth a glance.
