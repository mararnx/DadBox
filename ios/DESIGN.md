# iOS app — design

**Status:** draft, 2026-09-21. Nothing built. Written against
[ADR 0017](../docs/decisions/0017-managed-hosting-e2ee.md) (E2EE, iOS the only
client), [ADR 0018](../docs/decisions/0018-archive-forever.md) (archive
forever) and [SERVER-CONCEPT.md](../docs/SERVER-CONCEPT.md). PROTOCOL.md v0.3
is the contract; where this document needs something v0.3 does not list yet,
it says so in [§ Needed from v0.3](#needed-from-protocol-v03) instead of
inventing it.

**Role.** Be loud and on time. Be honest about the box. Keep the conversation.

## Decided (Marco, 2026-09-21)

| Question | Decision |
| --- | --- |
| Layout | **One conversation.** A single timeline, both directions; recorder at the bottom; a box-status chip at the top that opens the Box screen. Replaces the three tabs. |
| Archive | Both directions, forever, end-to-end encrypted (ADR 0017/0018). The phone keeps its own copy. |
| Key backup | iCloud Keychain. (The key is shown as a QR during setup anyway, so ADR 0018's paper copy costs nothing.) |
| Recording | **Tap, tap, review, send.** Never sent without being listened to or explicitly sent. |
| Parent cap | 5 minutes, same as the box. A quiet marker at 2:00; no stop. |
| From a push | Opens scrolled to the message, audio ready. **No autoplay.** Raise to ear → earpiece. |
| Pushes | New message, box late, battery < 20 %, own message unplayed after 48 h, box fault. Mute changes are shown in the app, not pushed. |
| Quick record (widget, Control Center, Action Button) | **Never.** The app is the only way in. |
| Language | English only. |
| Apple Developer account | Paid membership exists — APNs from the first build. |

## Screens

There are two, plus a setup that runs once. It should be hard to add a third.

### 1. Conversation

```
┌──────────────────────────┐
│ ● Box  82% · 4G · 2m ago │  status chip → Box screen
├──────────────────────────┤
│ ── Box was offline 14 h ─│  from offline_s / outbox_oldest_s
│  ▶ ▁▅▃▁  0:08            │
│    recorded while offline│  time_ok = false: no invented time
│  ▶ ▁▃▅▂▁▃  0:14   ●      │  ● = not yet heard
│    18:04                 │
│          0:42  ▁▂▅▃▁ ▶   │  from you
│        played 19:12      │
├──────────────────────────┤
│          ( ● )           │  recorder
└──────────────────────────┘
```

- **Order:** within a sender by `seq`; between senders by the server's
  `uploaded_at`. Never by `created_at` — the box may not know the time.
- **The chip** is the Box screen in one line and one colour: green *fine*,
  amber *late / low battery / muted / quiet hours*, red *silent or fault*.
  "Late" is `now > last_checkin + 2 × next_checkin_s`, as the protocol defines
  it — never a fixed interval.
- **A message from you** carries the whole feedback loop on its bubble:

  | State | Bubble says |
  | --- | --- |
  | `queued` / `uploading` | Sending… (progress) |
  | `uploaded` | Sent · box checks in ~19:30 *(from `next_checkin_s`)* — or *box is late* |
  | `delivered` | On the box · glowing *(or: quiet hours, glow only / muted by household B)* |
  | `played` | **Played 19:12** |
  | unplayed > 48 h | On the box for 2 days |

- **The archive** is the same timeline, scrolled up: date headers, paged from
  `GET /messages`, audio fetched on demand and kept. No search, no stars, no
  export in v1.
- Waveforms are computed on the phone after decryption and cached; the server
  never sees one.

### 2. Recorder (bottom of the conversation, grows into a sheet)

`idle → recording → review → sending`

- Tap to start, tap to stop. Review: play, re-record, send. One draft at a
  time; it survives the app being killed.
- Written to disk while recording. A phone call or Siri stops the recording
  into review — never into send.
- At 5:00 it stops into review. At 2:00 the timer changes colour, nothing else.
- Under 1 s: discarded, same rule as the box.
- Review shows what the box will do with it: *"Quiet hours until 07:00 — it
  will glow, not chime"*, *"Muted by household B since 18:30 — it will glow"*,
  *"Box is late — it will arrive when the box is back"*. Sending is never
  blocked; quiet hours are the device's job.
- Send: mint ULID and `seq`, encrypt, hand to the background upload session,
  bubble appears at once. The draft is deleted only when the encrypted
  container is on disk.

### 3. Box

Words first, numbers second. Every `fault` and both status LEDs are explained
in a sentence, because the adult in the other house will ask what the blinking
means.

| Section | From |
| --- | --- |
| **Status** — Fine / Late since 14:10 / Silent for 9 h; last and next check-in | `last_checkin_at`, `next_checkin_s`, `offline_s` |
| **Power** — 82 %, on mains, charging | `battery_pct`, `mains`, `charging` |
| **Link** — signal in words and dBm | `rssi` |
| **Queue** — "2 recordings waiting to send, oldest 3 h" · inbox count · storage | `outbox`, `outbox_oldest_s`, `inbox`, `storage_pct` |
| **Fault** — what it is, what to do, what the LEDs are showing | `fault` |
| **Settings** — quiet hours + tz, volume, LED brightness, idle check-in (5–60 min) | `settings`, each with who set it and when |
| **Mute** — mine: a switch. The other household's: read-only, who and when | `settings.mute` |
| **Key** — key id, show as QR / 43 characters for the paper copy (Face ID first) | Keychain |
| **About** — firmware, app version, server host | `fw` |

### Setup (once)

1. Scan the QR printed by the server's token script: server URL, identity,
   bearer token.
2. The app generates the 32-byte key, stores it, and shows it — QR and 43
   base64url characters — to be baked into the box's `.env` and printed for
   the drawer (SERVER-CONCEPT § Encryption).
3. Ask for notification permission, register the APNs token.

On a new phone iCloud Keychain brings token and key; setup is skipped.
Recovery without iCloud: scan the paper copy.

## Notifications

| Kind | Level | Text | Tap |
| --- | --- | --- | --- |
| `message` | active, **own sound** | "New message" *(title rewritten on the phone with the child's name — the server never learns it)* | conversation, at the message |
| `box_late` | active, default sound | "The box has been silent for 3 h" | Box |
| `fault` | active, default sound | "The box reports a problem: storage" | Box |
| `battery_low` | passive, once per discharge | "Box battery at 18 %" | Box |
| `unplayed_48h` | passive, once per message | "Your message from Tuesday hasn't been played" | conversation |
| `played` | background, no alert | — updates the bubble | — |

- Payloads carry a kind and ids, never content (ADR 0017).
- A notification service extension downloads the container and checks its
  GCM tag before the alert shows, so tapping it never waits on a network. It
  shares the Keychain group and app-group container with the app.
- Background pushes are best-effort by Apple's design. The truth is
  re-fetched whenever the app comes to the front; `played` pushes only make
  it feel live.
- No Critical Alerts, no Time Sensitive. A voice message must not beat a
  Sleep focus.

## Audio

- **From the box:** Ogg Opus (`codec = 2`), decrypted in memory, played with
  `AVAudioPlayer(data:)`. **Checked 2026-09-21 on macOS 26.4:** AudioToolbox
  lists `Oggf` as a file type, and `AVAudioPlayer` / `AVAudioFile` opened a
  standard Ogg Opus file (hand-muxed from Opus packets; 2.03 s in, 2.03 s
  out). iOS shares the framework — **confirm on a device**. Fallback if not:
  ~150 lines of Ogg page parsing feeding `AVAudioConverter`
  (`kAudioFormatOpus`); no third-party library either way.
- **To the box:** `AVAudioRecorder`, AAC-LC, 16 kHz mono, 24 kbps, `.m4a`
  (`codec = 3`). About 180 KB/min; five minutes ≈ 900 KB ≈ 28 chunks. Checked
  the same day: CoreAudio encodes exactly that format.
- `POST …/played` when playback first reaches the end; the unheard dot clears
  then too. Replays are local and silent.
- Speaker by default; proximity sensor switches to the earpiece.
  Session is `.playAndRecord` only while recording.

## Keys and storage

- Envelope exactly as SERVER-CONCEPT § Encryption: `key_id ‖ nonce ‖
  ciphertext ‖ tag`, AAD = header ‖ message id. CryptoKit `AES.GCM`.
- Keychain: one item per `key_id` plus the bearer token — synchronizable,
  `AfterFirstUnlock` (the notification extension runs while locked), shared
  access group. Old keys are never deleted; they read the archive.
- **On disk: ciphertext only** — `Archive/<id>.dbx`, the container as
  received, included in the phone's backup (ADR 0018 counts on it). Plaintext
  exists in memory during playback, and as the one recording draft until it
  is sent.
- Index: SwiftData in the app-group container — the protocol's message object
  plus local fields (heard, waveform peaks, cached). Rebuildable from
  `GET /messages` at any time; the server is the index of record.
- One set of encryption test vectors in the repo, run by the box's Python
  tests and the Swift tests alike.

## Network

- One `APIClient`, bearer token, `/v1`. No third-party SDKs of any kind.
- **Upload** through a background `URLSession`: metadata → 32 KB chunk files →
  `upload-state` → `complete`. Every step is idempotent by design, so the app
  retries blindly. A message recorded in a lift goes when the phone next has a
  link, app running or not.
- **Sync** on foreground and on every push: `GET /device/status`,
  `GET /messages` after the stored cursor, and `GET /messages/{id}` for own
  messages not yet `played` (there are never many).
- `seq` is persisted with the index; after a reinstall it is re-seeded from the
  server's highest `seq` for this identity.

## Code layout

```
ios/
  DadBoxKit/        Swift package, no UIKit — container, envelope, ULID, models,
                    APIClient, upload planner, late/played logic.
                    `swift test` on the Mac; needs no Xcode and no hardware.
  DadBox/           app target — SwiftUI views, recorder, player, store, push
  DadBoxNotify/     notification service extension
```

Minimum iOS 26: one family, one current phone, and native Ogg Opus. A second
parent (ADR 0008) is a second provisioning QR and a second `key_id` — same
build.

## Build order

1. **DadBoxKit** with the shared test vectors — unblocked today.
2. Xcode project; setup; conversation, read-only, against `tools/fakebox` and
   the local server. *(Needs Xcode — this Mac has only the Command Line Tools.)*
3. Push + notification extension + box-late alert → **M1**.
4. Recorder + background upload + bubble states → **M2**.
5. Box screen settings, mute, quiet hours, fault texts → **M3**.

## Needed from PROTOCOL v0.3

Not in SERVER-CONCEPT's v0.3 list, and the app cannot work without them:

1. **`PUT /push-token`** — `{ apns, environment }`. The `push_devices` table
   exists; no endpoint fills it.
2. **`PATCH /settings`** (parents) — which fields each identity may set
   (`mute.a` only by parent-a), returning who-set-what.
3. **Timestamps on the message object** — `uploaded_at`, `delivered_at`,
   `played_at`. "Played 19:12" is the feedback loop; `state` alone can't say it.
4. **`GET /messages/{id}`** — refresh one message's state.
5. **`GET /messages` ordering** — by server `uploaded_at`, opaque cursor,
   tombstones included, and a way to learn the caller's highest `seq`.
6. **Push payloads** — the six kinds above, ids only; `mutable-content` on
   `message`, `content-available` on `played`.
7. **Telemetry `locked`** — travel lock engaged (ADR 0016). Otherwise a locked
   box in a bag looks like a child who stopped talking.
8. The example message object still says `"codec": 1`.

## Open

- ~~Per-message delete~~ — **no delete in v1** (Marco, 2026-09-21; ADR 0018
  revised). No control in the app, no endpoint; tombstones drop out of
  § Needed item 5 until it returns.
- ~~iOS version~~ — the iPhone runs the latest iOS; minimum iOS 26 stands.
- Ogg Opus through `AVAudioPlayer` on an actual iPhone (above).
- ~28 background upload tasks per long message: measure time-to-`complete`
  with the app suspended.
- What `played` means on the box side (start or end of playback) — should
  match the app's "reached the end".
