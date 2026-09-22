# Architecture

```
  ┌──────────────────────┐   LTE (Cat-1 modem)    ┌─────────────┐   HTTPS   ┌────────────┐
  │   DadBox             │ ───── HTTPS ─────────► │   Server    │ ◄──────── │  Parent's  │
  │  (travels with       │ ◄──── check-in ──────  │  blobs ·    │ ── APNs ► │  iPhone    │
  │   the child)         │ ◄──── Tailscale SSH ── │  telemetry  │           └────────────┘
  │ Pi Zero 2 W · Linux  │        (from the Mac)  └─────────────┘
  │ two lit buttons      │
  └──────────────────────┘
```

The audio is end-to-end encrypted between the box and the phone: nobody in the
path — our own host included — can hear it
([ADR 0017](decisions/0017-managed-hosting-e2ee.md)). See
[PROTOCOL.md](PROTOCOL.md) for the wire contract and [decisions/](decisions/)
for why each piece is what it is. The box is a Linux machine
([ADR 0014](decisions/0014-raspberry-pi-zero-2w.md)); the
[dev process](DEV-PROCESS.md) is SSH.

## Audio

- Record pressed → one GPIO lights the button red **and powers the mic** →
  ALSA capture (I2S, `googlevoicehat-soundcard` overlay) at 16 kHz mono →
  **written to `/data` as it happens**. A power loss mid-story loses only the
  last buffer.
- Record pressed again — or the 5-minute cap, or ~20 s of continuous silence —
  → trim silence → `ffmpeg` → **Opus 16 kbps** in Ogg (~120 KB/min) → encrypt
  → container + CRC → outbox. A Cortex-A53 encodes Opus faster than real time
  without noticing. Under 1 s of speech is discarded silently.
- 5 minutes is ~600 KB on the wire: ~10 s on Digital Republic Flat 1.
- Playback: inbox → decrypt → `ffmpeg` → ALSA → MAX98357A, whose SD pin is
  held low whenever nothing is playing. The box plays whatever the phone
  records; the server never transcodes.

## Message flow

**Child → parent**
1. Press Record. The button turns steady red. No timer shown.
2. Talk. Up to five minutes.
3. Press Record again. Trim, encode to Opus, queue. One green pulse. Box is
   idle again.
4. Upload when there's a link — resumable in 32 KB chunks. If there's no link,
   it waits. The child is never told about a network.
5. Server sees `complete`, pushes to the parent's phone.

**Parent → child**
1. Parent records in the app, uploads.
2. Box learns of it at its next check-in — within a minute when plugged in
   or just used, otherwise `idle_minutes` (default 30;
   [ADR 0015](decisions/0015-adaptive-polling.md)) — downloads it, stores it
   in the inbox.
3. The Play button breathes warm. One gentle chime — suppressed during quiet
   hours.
4. Child presses Play. Oldest first, one per press. With nothing new waiting,
   Play repeats the last message heard ([ADR 0020](decisions/0020-no-mute-replay-green-link.md)).

## Link

Adaptive polling, no SMS wake ([ADR 0015](decisions/0015-adaptive-polling.md)).
**On mains** the modem stays on and the box checks in every `active_minutes`
(1). **On battery** it does the same for `active_window_minutes` (90) after an
upload completes or the child plays a message — a message merely arriving does
not count — and otherwise checks in every `idle_minutes` (30; app-set 5–60)
with the modem off in between. Mains versus battery comes from the sign of the
battery current on the UPS module's INA219. Telemetry carries `mains`,
`next_checkin_s` and `recording`, so the app knows when the box is *late*
rather than guessing.

## Indication

Two vocabularies, deliberately separate ([ADR 0009](decisions/0009-two-led-vocabularies.md),
[ADR 0016](decisions/0016-two-buttons-no-lid.md)):

- **The two buttons' lights** are the child's. They say three things —
  *something is waiting*, *I'm listening*, *I'm playing* — plus one pulse for
  *got it*. They never show link, battery or faults. The count of waiting
  messages is not shown on the box; the app has it.
- **Two small green status LEDs** — POWER and LINK, in that order, low on
  the box beside the charge port — are the adults'. Steady means fine,
  blinking means trouble ([ADR 0020](decisions/0020-no-mute-replay-green-link.md)).
  Anyone in either house can glance at them; the child never needs to.

### Button lights — priority order, highest wins

| # | State | Record button | Play button | Notes |
| --- | --- | --- | --- | --- |
| 1 | Recording | **Steady red.** Never animated, never dimmed. | dark | The mic-is-on signal for everyone in the room. The red LED and the mic's 3.3 V supply are the same GPIO pin: no red light, no mic — so the pin is on or off, not PWM. |
| 2 | Playing | dark | **Steady green** | The mic cannot be used now, so Record shows nothing. Then falls through to 4 or 5 |
| 3 | Got it | One green pulse, ~600 ms | — | Only after the message is fsynced to the outbox. Identical online or offline — the pulse means *safe*, not *delivered*. |
| 4 | Waiting (inbox > 0) | dim ready pulse | **Pulsing green** | After 2 h without interaction → *resting*: dim. Quiet hours: capped. |
| 5 | Idle | **Dim, slow blue pulse** — *ready to record* | dark | No red in the ready pulse: that channel is the mic pin. Dark when the travel lock is on. |

Colours revised 2026-09-22 ([ADR 0020](decisions/0020-no-mute-replay-green-link.md)):
Play is green (pulsing = new, steady = playing); Record is red only while
recording, otherwise a dim blue pulse that says *press me*.

The child's lights have no error state, ever. Nothing on them needs
interpreting beyond the four words above.

### Buttons and the bag

Buttons on the outside of a box in a school bag can be pressed by the bag
([ADR 0016](decisions/0016-two-buttons-no-lid.md)). A press must last ≥ 0.5 s
to count; a recording with under 1 s of speech is discarded. **Travel lock:**
hold both buttons for 3 s — both blink twice and the buttons are dead until the
same gesture again; it persists across a reboot. Device-enforced quiet hours
still apply to the chime.

### Status LEDs — the adults' channel

| LED | Pattern | Meaning |
| --- | --- | --- |
| LINK | steady green | Connected and the server answered: checked in within 2 × the current poll interval |
| LINK | off | Not yet checked in since boot — and never seen after the first minute unless something is wrong |
| LINK | 1 short blink / 3 s | No connection; nothing queued |
| LINK | 2 short blinks / 3 s | No connection **and messages waiting to go** — safe on disk |
| POWER | steady | External power present on the USB port — with or without a battery, charging or full |
| POWER | off | Unplugged: on battery above 20 % |
| POWER | 1 blink / 3 s | Below 20 %, on battery |
| POWER | off, box shut down | Below 5 %: the box shuts down cleanly and the buttons do nothing; the app has the last battery reading |
| both | alternating | **Fault** — an adult must act: outbox ≥ 80 %, storage error, modem unresponsive, capture failed |

Patterns carry the meaning; colour is redundant, for anyone colour-blind in
either house. Blinks are ~50 ms at low brightness; the steady LEDs are dim
enough for a bedroom (to judge with the parts in hand).

### Validation notes

- *Recording* outranks everything because it is the safety signal. It is the
  only red the child's lights ever show and it is never animated, so a
  bystander can tell "mic on" from "message waiting" without knowing the
  vocabulary. A lit button is a small sign; the wiring keeps it honest.
- *Got it* is identical online and offline on purpose. The child is promised
  *safe*; delivery is the adults' business (LINK, and the app).
- *Waiting* is one button LED driven from a GPIO pin — cheap, but a message
  can wait all weekend in a dark bedroom. Hence *resting* after 2 h: the glow
  survives, dimmer.
- Link is not the child's concern. Both households can still tell a quiet box
  from a dead one: that is what LINK is for.

## Nothing is lost

[ADR 0010](decisions/0010-nothing-is-lost.md). A recording that got its pulse
is on disk and stays until the server has confirmed it.

1. Record stops → trim → Opus → encrypt → container + CRC → outbox on `/data`
   → fsync → **then** the pulse.
2. The capture is written to disk **as it happens**. A power loss mid-story
   costs the last buffer, not the story.
3. The **outbox is never evicted**. The inbox may be — the server still has
   those. Both live on the `/data` partition of the SD card, beside a
   read-only root.
4. Out of the outbox only after `complete` returns 2xx; 2xx only after the
   server's durable write and CRC match.
5. Retries back off forever. On boot, interrupted uploads resume from
   `upload-state`.
6. Ordering is a monotonic `seq` kept on `/data`, not the clock — the box has
   no RTC battery and does not know the time after a cold start until it
   connects.
7. On reconnect, telemetry says how long the box was offline and what queued.

Capacity is the SD card — gigabytes, years of Opus. The failure to design
for is not a full card but a corrupt one: hence the read-only root overlay,
`fsync`-then-rename on `/data`, an endurance-grade card before the box leaves
home, and the bench card kept as a spare image in a drawer
([components/storage-queue.md](components/storage-queue.md)).

## Power

Target: **a weekend (60 h) unplugged** ([ADR 0005](decisions/0005-battery-required.md)).
A Pi cannot sleep, so the budget is about what stays on:

| Consumer | Gated by | Cost |
| --- | --- | --- |
| Pi Zero 2 W, tuned (Wi-Fi/BT/HDMI off, cores/clock reduced) | — | ~100 mA at 5 V, always |
| SIM7670G Cat-1 modem HAT | Its power key from a GPIO (wiring to verify; a high-side switch on its 5 V feed if the measured standby says so). On battery: on for check-ins, uploads and the 90-min conversation window only. On mains: stays on ([ADR 0015](decisions/0015-adaptive-polling.md)) | ~150 mA on; ~3–10 mA averaged on battery |
| Mic (~1 mA at 3.3 V) | the Record button's red-LED pin — one GPIO for both | 0 unless recording |
| Button LEDs (2 × RGB, 3.3 V from GPIO, software PWM) | GPIO; dark when idle | 0 when idle; breathing and *resting* — to measure |
| Status LEDs | ~10 ms blinks | negligible |
| Amp | MAX98357A SD pin | µA |
| UPS module's converter losses | — | ~10 % on top |

**The first box has no battery** ([ADR 0019](decisions/0019-mains-first-battery-deferred.md)): a 5 V micro-USB supply,
on only while plugged in, `mains: true` and `battery_pct: null` in telemetry,
one-minute check-ins always. Pulling the plug is the normal way it turns off,
so the power-pull test below is not optional. The rest of this section is the
battery as designed, for when it is fitted.

Supply: **Waveshare UPS Module 3S** — three protected 18650s in series
(~36 Wh), 5 V 5 A out, charges while powering, INA219 over I²C for battery %,
current and mains-versus-battery — charged from its own **12.6 V 2 A
barrel-jack supply, not USB**, through a panel-mount DC jack; a second charger
lives in house B ([ADR 0014](decisions/0014-raspberry-pi-zero-2w.md)). Not a
power bank: no gauge, an output blip on plug and unplug, auto-off.

Roughly **0.6 W → ~36 Wh ≈ 50–55 h** — two days, not quite 60 h. The levers,
in order: keep the modem off between idle check-ins, drop to one core at idle,
dim the button lights. **Measure before buying the cells.** Charging the pack
takes ~5 h — the box is plugged in most of the time, which is the point of the
mains cadence. Until the battery phase the box runs from a 5 V micro-USB
supply.

## Retention and privacy

A child's recorded voice is the most sensitive thing in this system.

- **End-to-end encrypted** (AES-256-GCM): keys live on the box and in the
  iPhone Keychain; the host stores and moves ciphertext it cannot play
  ([ADR 0017](decisions/0017-managed-hosting-e2ee.md)). TLS in transit on top.
  The host still sees that messages exist, when, how long, and the box's
  telemetry.
- **Archived forever**: the server never deletes a completed message and the
  app keeps its own copy; deleting is a deliberate act in the app, per message
  ([ADR 0018](decisions/0018-archive-forever.md)). Unplayed messages are
  surfaced, not reaped.
- No third-party analytics, no cloud transcription, no speech services.
- One managed host; the iOS app is the only human-facing client. No
  server-side transcode — the server cannot read the audio.
- The box is not an archive: the outbox copy goes on the server's
  confirmation, the inbox copy after play.
- The root filesystem is a read-only overlay; `/data` is the only writable
  partition, and every message write is `fsync` then `rename`.

## To verify before building

- **Sunrise 4G in both bedrooms** (Digital Republic rides Sunrise) — `AT+CSQ`
  and `AT+CPSI?` over SSH with the HAT in hand.
- That the short Delock 90694 stub holds signal in both bedrooms, against the
  115 mm 90682 — its datasheet range misses the band 20 downlink.
- With the SIM7670G HAT in hand: how its power key is wired, that it stays in
  USB Ethernet (RNDIS/ECM) mode across reboots and power-key cycles, and which
  antenna connector it has (before ordering the pigtail).
- Real current of the tuned Pi, the modem on and powered off, and the button
  lights, on the bench — **before buying the cells**.
- That the button LEDs are bright enough at 3.3 V straight from GPIO; two
  74AHCT125s only if not.
- That the mic captures cleanly from the GPIO pin it shares with the red LED.
- The inside of the enclosure (a 1590DD-size clone: length, width, depth,
  corner bosses) **before any layout or drilling** — and with it, whether the
  buttons (~20 mm behind the panel) go in a wall or in the top plate.
- The UPS Module 3S with the part in hand: that its holders take 69.5 mm
  protected cells, its height against the box's inner depth, its own quiescent
  draw, and no output blip when the charger is plugged or pulled.
- That the read-only overlay + `/data` survives a power pull mid-write.
