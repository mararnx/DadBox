# Architecture

```
  ┌──────────────────┐         cellular          ┌──────────┐        ┌─────────────┐
  │   DadBox         │  ───── Notecard ─────►    │ Notehub  │ ─────► │  Backend    │
  │  (child's home)  │  ◄──── sync ─────────     │          │ ◄───── │  + storage  │
  │ ESP32-S3         │                           └──────────┘        └─────────────┘
  │ mic·speaker·LEDs │                                                      ▲
  │ record · play    │                                                      │ HTTPS
  └──────────────────┘                                              ┌───────────────┐
                                                                    │ Parent's PWA  │
                                                                    │ (phone)       │
                                                                    └───────────────┘
```

## Audio

Record 16 kHz mono PCM straight into PSRAM while the button is held. **Encode
after the button is released, not during.** There is no real-time constraint on
a voice message, which removes the only hard CPU problem in the firmware and
makes the codec choice free.

- 60 s of 16 kHz 16-bit PCM = ~1.9 MB — comfortable in 8 MB PSRAM.
- Opus at 16 kbps = ~2 KB/s, so a 60 s message is ~120 KB on the wire.
- Against a 500 MB bundled data allowance that is several thousand messages —
  years of use. Data cost is not a design constraint.

Hard cap at 60 seconds, ended by a gentle chime rather than a cut-off.

## Message flow

**Child → parent**
1. Hold record. Ring fills as the time runs out.
2. Release. Encode, write to a queue in flash, return to idle immediately.
3. Upload when there is a link. If there isn't, it waits. The child is never
   told about a network.

**Parent → child**
1. Parent records in the PWA, uploads to the backend.
2. Backend queues it; the box picks it up on its next sync.
3. Ring breathes warm, one lit segment per waiting message. Optional single
   chime — suppressed during quiet hours.
4. Child presses play. Messages play oldest first.

## Device states

| State | What the child sees |
| --- | --- |
| Idle, nothing waiting | Ring dark |
| Messages waiting | Slow warm breathing, N segments lit |
| Recording | Ring fills over 60 s |
| Just sent | One pulse, then idle |
| Playing | Segment-by-segment progress |
| No connection | **Nothing.** Queue and retry with backoff |
| Battery low | Slow amber fade at the base — a grown-up's signal, not a child's |

There is no error state. Anything that goes wrong is a grown-up's problem and
surfaces in the parent's app, never on the box.

## Retention and privacy

A child's recorded voice is the most sensitive thing in this system.

- Messages are deleted a fixed, short time after being played.
- No third-party analytics, no cloud transcription, no speech services.
- Storage encrypted at rest; TLS in transit.
- The box holds only what is queued, and wipes on successful send.

## To verify before building

- **Cellular coverage at the destination address.** Everything depends on it.
- Notecard binary payload limits — a ~120 KB message will likely need chunking.
- Notecard current draw during transmit against the chosen LiPo and regulator.
- Whether the ESP-IDF Opus encoder component is worth it over ADPCM (4:1, near
  zero CPU) — ADPCM's ~480 KB per minute is still affordable and much simpler.
