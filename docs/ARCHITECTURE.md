# Architecture

```
  ┌────────────────────┐      LTE-M / PPP       ┌─────────────┐   HTTPS   ┌────────────┐
  │   DadBox           │ ───── HTTPS ─────────► │   Server    │ ◄──────── │  Parent's  │
  │  (travels with     │ ◄──── check-in ──────  │  blobs ·    │ ── APNs ► │  iPhone    │
  │   the child)       │                        │  telemetry  │           └────────────┘
  │ ESP32-S3 · SIM7080G│                        └─────────────┘
  │ lid · play · ring  │
  └────────────────────┘
```

Nobody but our server is in the path. See [PROTOCOL.md](PROTOCOL.md) for the
wire contract and [decisions/](decisions/) for why each piece is what it is.

## Audio

- Lid open → mic powered via a load switch → I2S at 16 kHz → **IMA-ADPCM as
  it goes** → PSRAM. 5 minutes is 2.4 MB; PSRAM is 8 MB.
- Lid closed → trim silence → container + CRC → flash outbox → upload.
- v1 sends ADPCM on the wire (~480 KB/min). Opus transcode after the lid
  closes is an M3 upgrade: ten times smaller, one more dependency, nothing
  else changes — the container header carries the codec id.
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

## Device states

| State | What the child sees |
| --- | --- |
| Idle, nothing waiting | Ring dark |
| Messages waiting | Slow warm breathing, N segments lit (fill above ~8) |
| Listening (lid open) | Steady "listening" light — no time pressure |
| Just sent (lid closed) | One pulse, then idle |
| Playing | Segment-by-segment progress |
| No connection | **Nothing.** Queue and retry with backoff |
| Sleeping (no link for a day) | Very slow, very dim pulse — different from broken |
| Battery low | Nothing below 20 %; the app nags the adults. Below 5 %: box sleeps, app says so |

There is no error state. Anything that goes wrong is a grown-up's problem and
surfaces in the parent's app, never on the box.

## Power

Target: **a weekend (60 h) unplugged** ([ADR 0005](decisions/0005-battery-required.md)).
That makes gating the design's centre of gravity:

| Consumer | Gated by | Idle cost |
| --- | --- | --- |
| Mic | load switch on the lid | 0 |
| LED ring (16 × WS2812B) | FET — they draw ~1 mA each even dark | 0 when off |
| Amp | MAX98357A SD pin | µA |
| Modem | PSM between check-ins | ~µA–1 mA |
| ESP32-S3 | light sleep; deep sleep between polls if wake sources prove reliable | ~1-2 mA |

Roughly 5 mA average, gated → ~3 weeks on 3000 mAh. Ungated ring alone would
be ~6 days. Transmit bursts to ~2 A: the cell, its PCM, the power-path
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

- **LTE-M coverage at both addresses** — Cat-M1 specifically, not NB-IoT.
- The SIM7080G breakout level-shifts its 1.8 V UART.
- Real idle current of each gated rail, on the bench, before choosing a cell.
- Opus encode time on the S3 for a 5-minute clip (M3, not blocking).
- That a lid switch / hall sensor is *reliable* — it is the mic gate.
