# Architecture

```
  ┌────────────────────┐    LTE Cat-1 / PPP     ┌─────────────┐   HTTPS   ┌────────────┐
  │   DadBox           │ ───── HTTPS ─────────► │   Server    │ ◄──────── │  Parent's  │
  │  (travels with     │ ◄──── check-in ──────  │  blobs ·    │ ── APNs ► │  iPhone    │
  │   the child)       │                        │  telemetry  │           └────────────┘
  │ ESP32 · A7670G     │                        └─────────────┘
  │ lid · play · ring  │
  └────────────────────┘
```

Nobody but our server is in the path. See [PROTOCOL.md](PROTOCOL.md) for the
wire contract and [decisions/](decisions/) for why each piece is what it is.

## Audio

- Lid open → mic powered via a load switch → I2S at 16 kHz → **IMA-ADPCM as
  it goes** → PSRAM. 5 minutes is 2.4 MB; PSRAM is 8 MB.
- Lid closed → trim silence → container + CRC → **TF-card outbox** (4 MB
  flash holds only OTA and a one-message fallback) → upload.
- v1 sends ADPCM on the wire (~480 KB/min). Data is unlimited
  ([ADR 0013](decisions/0013-cat1-not-catm.md)), so Opus is only about upload
  time — ~40 s vs ~4 s for a 5-minute message on a 0.5 Mbps uplink. An M3
  nicety; the container header carries the codec id either way.
- The rule: **no real-time-constrained codec in the capture path.** ADPCM is a
  few integer ops per sample and doesn't count.

## Message flow

**Child → parent**
1. Open the lid. Ring lights "listening". No timer shown.
2. Talk. Up to five minutes.
3. Close the lid. Trim, encode, queue. One pulse. Box is idle again.
4. Upload when there's a link — resumable in 32 KB chunks. If there's no link,
   it waits. The child is never told about a network.
5. Server sees `complete`, pushes to the parent's phone.

**Parent → child**
1. Parent records in the app, uploads.
2. Box learns of it at its next check-in (poll interval, app-set, default
   10 min), downloads it, stores it in the inbox.
3. Ring breathes warm, one lit segment per waiting message. One gentle chime —
   suppressed during quiet hours and by mute.
4. Child presses play. Oldest first, one per press.

## Indication

Two vocabularies, deliberately separate ([ADR 0009](decisions/0009-two-led-vocabularies.md)):

- **The ring** is the child's. It says three things — *something is waiting*,
  *I'm listening*, *I'm playing* — plus one pulse for *got it*. It never shows
  link, battery or faults.
- **Two small status LEDs** — LINK and POWER, low on the box beside the USB-C
  port — are the adults'. Off means fine. Anyone in either house can glance at
  them; the child never needs to.

### Ring — priority order, highest wins

| # | State | Ring | Notes |
| --- | --- | --- | --- |
| 1 | Listening (lid open) | Steady, bright, warm. Never animated. | The mic-is-on signal for everyone in the room. Quiet hours dim it to a floor, never off. |
| 2 | Playing | Progress sweep around the ring | Then falls through to 4 or 5 |
| 3 | Got it (lid just closed) | One pulse, ~600 ms | Only after the message is on flash. Identical online or offline — the pulse means *safe*, not *delivered*. |
| 4 | Waiting (inbox > 0) | Slow warm breathing, N segments lit (fill ≥ 8) | After 2 h without interaction → *resting*: one breath every ~10 s. Quiet hours: brightness floor. |
| 5 | Idle | Dark; ring rail off | |
| — | Boot | One sweep | Then whichever applies |

The ring has no error state. Nothing on it ever needs interpreting beyond the
four words above.

### Status LEDs — the adults' channel

| LED | Pattern | Meaning |
| --- | --- | --- |
| LINK | off | Checked in within 2 × poll interval — nothing to see |
| LINK | 1 short blink / 3 s | No connection; nothing queued |
| LINK | 2 short blinks / 3 s | No connection **and messages waiting to go** — safe on flash |
| LINK | brief on | A check-in or upload just succeeded (useful when placing the box) |
| POWER | off | On battery above 20 %, or plugged in and full |
| POWER | steady | Charging |
| POWER | 1 blink / 3 s | Below 20 %, on battery |
| POWER | off, box asleep | Below 5 %: box sleeps, lid does nothing; LINK still blinks so an adult can tell |
| both | alternating | **Fault** — an adult must act: outbox ≥ 80 %, storage error, modem unresponsive, capture failed |

Patterns carry the meaning; colour is redundant, for anyone colour-blind in
either house. Blinks are ~10 ms at low brightness — invisible in a dark bedroom
and effectively free.

### Validation notes

- *Listening* outranks everything because it is the safety signal. It is the
  only ring state that is never animated, so a bystander can tell "mic on"
  from "message waiting" without knowing the vocabulary.
- *Got it* is identical online and offline on purpose. The child is promised
  *safe*; delivery is the adults' business (LINK, and the app).
- *Waiting* is the expensive state: 16 pixels breathing is ~15 mA, and a
  message that waits all weekend would eat ~30 % of the cell. Hence *resting*
  after 2 h — the glow survives, the budget survives.
- The old *sleeping* ring state is gone. Link is not the child's concern.
- The old *no connection → nothing* rule is gone. It protected the child but
  left both households unable to tell a quiet box from a dead one.

## Nothing is lost

[ADR 0010](decisions/0010-nothing-is-lost.md). A recording that got its pulse
is on flash and stays until the server has confirmed it.

1. Lid closes → trim → container + CRC → LittleFS outbox → fsync → **then**
   the pulse.
2. During capture the PSRAM buffer is checkpointed to flash every 30 s. A
   power loss mid-story costs at most 30 s.
3. The **outbox is never evicted**. The inbox may be — the server still has
   those. On the T-A7670G R2 the outbox is the TF card; internal flash
   mirrors the latest message so a missing card costs at most one.
4. Out of the outbox only after `complete` returns 2xx; 2xx only after the
   server's durable write and CRC match.
5. Retries back off forever. On boot, interrupted uploads resume from
   `upload-state`.
6. Ordering is a monotonic `seq` from NVS, not the clock — the box has no RTC
   battery and does not know the time after a cold start until it connects.
7. On reconnect, telemetry says how long the box was offline and what queued.

Capacity: ~10 MB of flash after the app and OTA slot → ~20 minutes of ADPCM,
~3 h once Opus lands. Full is the one case where *never lost* and *always
accept* collide; the fault pattern shows at 80 %, and whether *never* needs a
microSD is open in [components/storage-queue.md](components/storage-queue.md).

## Power

Target: **a weekend (60 h) unplugged** ([ADR 0005](decisions/0005-battery-required.md)).
That makes gating the design's centre of gravity:

| Consumer | Gated by | Idle cost |
| --- | --- | --- |
| Mic | load switch on the lid | 0 |
| LED ring (16 × WS2812B) | FET — they draw ~1 mA each even dark | 0 when off |
| Amp | MAX98357A SD pin | µA |
| Modem (A7670G, Cat-1) | DTR sleep between check-ins | ~2 mA — 120 mAh per weekend, fine |
| ESP32 | light sleep; deep sleep between polls if wake sources prove reliable | ~1-2 mA |
| Ring, *waiting* | — | ~15 mA breathing; ~1.5 mA *resting* after 2 h |
| Status LEDs | — | ~0 — 10 ms blinks |

Roughly 5 mA average, gated → ~3 weeks on 3000 mAh. Ungated ring alone would
be ~6 days; a message left *waiting* at full breathing all weekend would be
~30 % of the cell, which is why *waiting* drops to *resting* after 2 h. Transmit bursts to ~2 A: the cell, its PCM, the power-path
regulator and the trace to the modem all need to be rated for it, plus bulk
capacitance at the modem. This is the #1 cause of "my LTE project resets".

## Retention and privacy

A child's recorded voice is the most sensitive thing in this system.

- Deleted 24 h after being played. Unplayed messages are surfaced, not reaped.
- No third-party analytics, no cloud transcription, no speech services.
- TLS in transit to our server only. Encrypted at rest.
- On-device encryption with a key the server never holds: recommended, open.
- The box holds only what is queued, and wipes on successful send or play.

## To verify before building

- **Sunrise 4G coverage in both bedrooms** (Digital Republic rides Sunrise).
- That the T-A7670G R2 has its TF slot, and that the SD survives a power pull
  mid-write (sync-on-write).
- The Allnet pigtail's SMA is a bulkhead; the LILYGO's antenna connector is u.FL, not MHF4.
- Real idle current of each gated rail, on the bench, before choosing a cell.
- Opus encode time on the S3 for a 5-minute clip (M3, not blocking).
- That a lid switch / hall sensor is *reliable* — it is the mic gate.
