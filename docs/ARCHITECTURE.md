# Architecture

```
  ┌──────────────────────┐   LTE (Cat-1 modem)    ┌─────────────┐   HTTPS   ┌────────────┐
  │   DadBox             │ ───── HTTPS ─────────► │   Server    │ ◄──────── │  Parent's  │
  │  (travels with       │ ◄──── check-in ──────  │  blobs ·    │ ── APNs ► │  iPhone    │
  │   the child)         │ ◄──── Tailscale SSH ── │  telemetry  │           └────────────┘
  │ Pi Zero 2 W · Linux  │        (from the Mac)  └─────────────┘
  │ lid · play · ring    │
  └──────────────────────┘
```

Nobody but our server is in the path. See [PROTOCOL.md](PROTOCOL.md) for the
wire contract and [decisions/](decisions/) for why each piece is what it is.
The box is a Linux machine ([ADR 0014](decisions/0014-raspberry-pi-zero-2w.md));
the [dev process](DEV-PROCESS.md) is SSH.

## Audio

- Lid open → mic powered via a load switch → ALSA capture (I2S,
  `googlevoicehat-soundcard` overlay) at 16 kHz mono → **written to `/data` as
  it happens**. A power loss mid-story loses only the last buffer.
- Lid closed → trim silence → `ffmpeg` → **Opus 16 kbps** (~120 KB/min) →
  container + CRC → outbox. Opus from day one; there is no ADPCM stage and
  no "encode later" rule any more — a Cortex-A53 encodes Opus faster than
  real time without noticing.
- 5 minutes is ~600 KB on the wire: ~10 s on Digital Republic Flat 1.

## Message flow

**Child → parent**
1. Open the lid. Ring lights "listening". No timer shown.
2. Talk. Up to five minutes.
3. Close the lid. Trim, encode to Opus, queue. One pulse. Box is idle again.
4. Upload when there's a link — resumable in 32 KB chunks. If there's no link,
   it waits. The child is never told about a network.
5. Server sees `complete`, pushes to the parent's phone.

**Parent → child**
1. Parent records in the app, uploads.
2. Box learns of it at its next check-in — within a minute when plugged in
   or just used, otherwise `idle_minutes` (default 30;
   [ADR 0015](decisions/0015-adaptive-polling.md)) — downloads it, stores it
   in the inbox.
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
| LINK | off | Checked in within 2 × the current poll interval — nothing to see |
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
2. The capture is written to disk **as it happens**. A power loss mid-story
   costs the last buffer, not the story.
3. The **outbox is never evicted**. The inbox may be — the server still has
   those. Both live on the `/data` partition of the SD card, beside a
   read-only root.
4. Out of the outbox only after `complete` returns 2xx; 2xx only after the
   server's durable write and CRC match.
5. Retries back off forever. On boot, interrupted uploads resume from
   `upload-state`.
6. Ordering is a monotonic `seq` from NVS, not the clock — the box has no RTC
   battery and does not know the time after a cold start until it connects.
7. On reconnect, telemetry says how long the box was offline and what queued.

Capacity is the SD card — gigabytes, years of Opus. The failure to design
for is not a full card but a corrupt one: hence the read-only root overlay,
`fsync`-then-rename on `/data`, a name-brand card, and a spare imaged card
in a drawer ([components/storage-queue.md](components/storage-queue.md)).

## Power

Target: **a weekend (60 h) unplugged** ([ADR 0005](decisions/0005-battery-required.md)).
A Pi cannot sleep, so the budget is about what stays on:

| Consumer | Gated by | Cost |
| --- | --- | --- |
| Pi Zero 2 W, tuned (Wi-Fi/BT/HDMI off, cores/clock reduced) | — | ~100 mA, always (a 3A+: ~200 mA — mains only) |
| A7670E Cat-1 modem HAT | **PWRKEY** (or a high-side switch on its 5 V feed). On battery: on for check-ins, uploads and the 90-min conversation window only. On mains: stays on ([ADR 0015](decisions/0015-adaptive-polling.md)) | ~150 mA on; ~3–10 mA averaged on battery |
| Mic | load switch on the lid | 0 |
| LED ring (16 × WS2812B) | FET — ~1 mA each even dark | 0 when off; ~15 mA breathing; ~1.5 mA *resting* |
| Amp | MAX98357A SD pin | µA |
| Boost converter losses | — | ~10 % on top |

Roughly **~117 mA average → four cells (13 Ah) ≈ 60 h** on a Zero 2 W. The
levers, in order: keep the modem off between idle check-ins, drop to one core
at idle, dim the ring. **Measure before choosing the cell count.** Charging
13 Ah at ~1 A is overnight and then some — the box is plugged in most of the
time, which is the point of the mains cadence.

## Retention and privacy

A child's recorded voice is the most sensitive thing in this system.

- Deleted 24 h after being played. Unplayed messages are surfaced, not reaped.
- No third-party analytics, no cloud transcription, no speech services.
- TLS in transit to our server only. Encrypted at rest.
- On-device encryption with a key the server never holds: recommended, open.
- The box holds only what is queued, and wipes on successful send or play.
- The root filesystem is a read-only overlay; `/data` is the only writable
  partition, and every message write is `fsync` then `rename`.

## To verify before building

- **Sunrise 4G in both bedrooms** (Digital Republic rides Sunrise).
- Real current of the tuned Pi, the modem on and PWRKEY-off, and the ring, on the
  bench with a USB meter — **before buying the cells**.
- That the modem HAT stays in ECM (Ethernet) mode across reboots and PWRKEY
  cycles, and which antenna connector it has.
- That the short Delock 90694 stub holds signal in both bedrooms (`AT+CSQ`),
  against the 115 mm 90682.
- That the read-only overlay + `/data` survives a power pull mid-write.
- That a reed contact + magnet register reliably through the lid gap.
