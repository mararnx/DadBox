# Architecture review — 2026-09-20

A second pass over the design before any money is spent. Findings ranked by how
much they would cost if discovered after ordering.

## What holds

- One box + phone app, protocol written as if both ends were boxes (ADR 0003/0004).
- The device state machine and the absence of an error state.
- Capture-then-encode, with the constraint restated more precisely below.
- Retention and privacy rules.
- Buying in phases with kill-checkpoints between them.

## What doesn't

### 1. The recording gesture contradicts two other decisions

Hold-to-talk, a 5-minute cap, and "mic powered only while the button is
physically held" cannot all be true. No seven-year-old holds a button down for
three minutes of story. One of them gives:

| Option | Cap | Mic gating | Transport-safe |
| --- | --- | --- | --- |
| **A. Hold-to-talk** | ~90 s | physical, via the button | no |
| **B. Press to start / press to stop** | 5 min | firmware only | no |
| **C. Lid: open to talk, close to send** | 5 min | physical, via a lid switch | **yes** |

C is the interesting one. Opening a lid is an unmistakable "I am talking now"
for everyone in the room; closing it is a natural "send"; and a closed box has
nothing on the outside that a school bag can press. It also gives the box a
reason to be a box. See [components/controls-ui.md](components/controls-ui.md).

### 2. The PSRAM buffer math is wrong

5 min × 16 kHz × 16-bit = 9.6 MB. PSRAM is 8 MB, and the heap needs some of it.
`firmware/main/dadbox_config.h` currently asserts a buffer that cannot exist.

Resolved by finding 1: a 90 s cap is 2.9 MB and fits comfortably. A 5-minute cap
needs either streaming PCM to flash during capture, or IMA-ADPCM in the capture
path — 4:1, a handful of integer ops per sample, and nothing like a real-time
constraint. The rule should read: **no real-time-constrained codec in the
capture path**, not "no encoding during capture".

### 3. The Notecard is probably the wrong shape for audio

It is built for small JSON telemetry. Note payloads are base64 inside JSON with
a per-note limit of a few KB, so "chunk the audio into Notes" means on the
order of 150 notes per long message, all through Notecard flash and Notehub's
queue. That is not what the product was designed for, and it will show.

The intended large-object path is `card.binary` + `web.post` / `web.get`
through a Notehub proxy route. Buffer size is on the order of ~100 KB and
model-dependent (**unverified**), and the modem has to be up for the duration of
the transfer. Workable — but awkward — and Notehub sees the audio bytes unless
the firmware encrypts them first.

The alternative is a bare LTE-M modem (SIM7080G family) with ESP-IDF's
`esp_modem` component doing PPP: the ESP32 gets a real IP stack and talks plain
HTTPS to our own server. No third party in the path, no payload-shape
constraints, resumable chunked uploads are just HTTP. A flat-rate IoT SIM
(e.g. 1NCE: ~€10 one-off, 500 MB, 10 years, EU-wide) makes it roughly half the
Notecard's price. The cost is integration: modem bring-up, band selection,
antenna, power-save modes. Real work, but the kind a maker signed up for.

See [components/connectivity.md](components/connectivity.md). ADR 0002 stays
"cellular" either way; the module choice needs its own decision.

### 4. "Travels" got conflated with "operates unplugged"

ADR 0005 assumed that because the box rides in a bag it must run on battery.
But if it is *used* plugged in at both homes and only has to *survive* the ride,
the battery shrinks to a small backup — or vanishes, since state lives in
flash. If instead it spends a weekend at a grandparent's unplugged, the power
budget dominates every other decision. Nobody has said which. It is the largest
single swing in the BOM and the enclosure.

### 5. The bag

Two 60 mm arcade buttons in a school bag will record the inside of the bag,
upload it over cellular, and play messages aloud in a classroom. A transport
lock is not optional: a lid (finding 1, option C), recessed buttons, a
long-press to arm, or a motion inhibit from an accelerometer.

### 6. The LED ring eats the idle budget

WS2812B pixels draw roughly 1 mA each even when dark. Sixteen of them is
~16 mA, always — about a week of a 3000 mAh cell before the box has done
anything. Power-gate the ring with a FET. The amp has a shutdown pin. The mic
gets a load switch, which is also how finding 1's "physically gated" is
delivered in hardware rather than in software.

### 7. Nobody has set an acceptable latency

Parent → box requires the box to either poll or hold a connection. Polling every
5 minutes versus every 30 versus staying connected is a ~10× difference in
power, and it decides whether the modem can sleep. Child → parent is easier
(the box is awake anyway when it has something to send) but still needs a
number. "Minutes" and "seconds" lead to different hardware.

### 8. Two parents?

The child alternates homes. When they are with Dad, the box is in Dad's house.
Does the other parent get the app too, so the child can message whichever
parent they are away from? That changes auth (two identities), routing (send
to whom?), and the child-facing UI — unless the box can infer which house it is
in. Cellular cell ID would do it; so would a per-house charger with an ID
resistor in the plug. Either is more fun than a "who is this for" button.

### 9. Smaller

- The Opus encoder on ESP32-S3 is unverified. ESP-ADF ships one; if it fights,
  Speex or ADPCM is the fallback and the data budget still works.
- Quiet hours need local time: network time from the modem, plus a timezone
  the app sets.
- Notehub is a third party in the audio path. If it stays, encrypt on-device.
- Playback volume: a child will turn it up; the other household will want it
  down. Decide who controls it.
- Charging becomes a chore someone owns. The app should nag before it matters.

## What changes as a result

Nothing yet. Findings 1, 3, 4 and 8 are decisions, not fixes, and each revises
an ADR. The shopping list is unaffected — phase 1 is the audio path and is
correct under every option above. **Phase 2 is on hold until finding 3 is
decided.**
