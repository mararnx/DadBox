# Box firmware — design

**Status:** implemented on the Mac (2026-09-22), untested on a Pi. Everything
that is not a driver runs and is tested here; the drivers in `dadbox/hw/pi.py`
are written against the proposed pin map and wait for the parts.

The box is a Linux service ([ADR 0014](../docs/decisions/0014-raspberry-pi-zero-2w.md)),
so "firmware" means one Python package under `systemd`. Its job, in one line:
turn two buttons into messages that are never lost, and never show a child an
error ([BRIEF](../docs/BRIEF.md), [ARCHITECTURE](../docs/ARCHITECTURE.md)).

## Shape: a pure core, an effectful shell

```
         GPIO / mouse            ALSA / synth              modem / fake server
              │                       │                            │
   ┌──────────▼──────────┐  ┌─────────▼──────────┐  ┌──────────────▼────────────┐
   │ Buttons (driver)    │  │ AudioWorker        │  │ LinkWorker (own thread)   │
   │ contacts → events   │  │ capture·trim·Opus· │  │ upload·played·check-in·   │
   └──────────┬──────────┘  │ seal·fsync·play    │  │ download; never gives up  │
              │             └─────────▲──┬───────┘  └──────────────▲──┬─────────┘
              │ events                │  │ events                  │  │ events
              │                actions│  │                  actions│  │
   ┌──────────▼───────────────────────┴──▼──────────────────────────┴──▼─────────┐
   │  Service — one thread: event queue → Core.handle(event) → dispatch(actions) │
   └──────────┬──────────────────────────────────────┬──────────────────────────┘
              │ LightsPlan / StatusPlan               │ MicPower · PersistLock · Reply · Log
   ┌──────────▼──────────┐                 ┌─────────▼─────────┐
   │ LightsDriver 30 Hz  │                 │ Store (/data)     │
   │ render() → PWM/UI   │                 │ fsync-then-rename │
   └─────────────────────┘                 └───────────────────┘
```

**`core.py` is the only place that decides anything**, and it is pure:
events in, actions out, no I/O, no threads, time only through the `Clock` it
was handed. Drivers and workers do what an action says and post what they
learn as an event. The service is the one thread that steps the core.

This is what makes the simulator cheap and honest: the same core, the same
workers, the same store and the same link code run on the Mac with fake
drivers and a fake clock. Only the `hal.py` interfaces have two
implementations.

### Threads

| Thread | Owns | Talks to the core via |
| --- | --- | --- |
| `core` | the `Core`, the event queue, the action dispatch | — |
| `lights` | rendering both channels at 30 Hz from the last plans | reads plans only |
| `link` | the modem and the server; one round at a time | events |
| `encode-*` | one trim → Opus → seal → fsync per recording | `Queued` / `Discarded` |
| capture pump | `arecord` → `/data/capture/<id>.pcm`, fsync each second | `CaptureLevel` / `CaptureEnded` |
| `power` | the gauge, polled every 2 s | `PowerState` |
| `ctl` | the Unix socket for `dadboxctl` | `Command` → `Reply` |

## Modules

| Module | Job | Pure? |
| --- | --- | --- |
| `core.py` | the state machine: modes, presses, lock, replay, quiet hours, cadence, lights plan, status plan, telemetry | yes |
| `gestures.py` | contacts → presses: ≥ 0.5 s to count, both held 3 s = travel lock, fumbles fire nothing | yes |
| `lights.py` | `LightsPlan` + time → RGB levels; **only recording renders full red, asserted** | yes |
| `settings.py` | the server's `settings` object, tolerant parse, quiet-hours test in the settings' time zone | yes |
| `dsp.py` | RMS per 100 ms block, trim, WAV wrapper, chime, a synthetic voice | yes |
| `state.py` | the rules that pre-date this design: light priority, poll plan, constants | yes |
| `container.py` | DBX1 + AES-256-GCM (shared vectors) | yes |
| `store.py` | the `/data` layout, fsync-then-rename, seq, lock, keys, capture recovery | disk |
| `link.py` | `Client` (PROTOCOL.md on any `Transport`) and `LinkWorker` (the round, backoff, modem gating) | network |
| `audio.py` | `AudioWorker`: the capture/encode/seal/queue policy and the amp gate around playback | disk, backend |
| `service.py` | the loop, `LightsDriver`, `dadboxctl` command handling | threads |
| `ctl.py` | `dadboxctl` client and socket server | socket |
| `hal.py` | the interfaces and the proposed pin map | — |
| `hw/pi.py` | gpiozero, `arecord`/`ffmpeg`/`aplay`, `ip addr` for the modem | Pi only |
| `sim/` | fake drivers, synthetic audio, in-process server, web UI, `python3 -m dadbox.sim` | Mac |

## Events and actions

Events (in): `Boot`, `Contact(button, down)`, `Tick`, `CaptureLevel`,
`CaptureEnded`, `Queued`, `Discarded`, `UploadDone`, `Checkin`,
`Downloaded`, `PlaybackEnded`, `PlayedReported`, `LinkState`, `PowerState`,
`FaultEvent`, `Command`.

Actions (out): `MicPower`, `SetLights`, `StartCapture`,
`StopCapture`, `Encode`, `Play`, `StopPlay`, `Chime`, `PersistLock`,
`MarkPlayed`, `LinkPlan`, `ModemPower`, `LedTest`, `Shutdown`, `Reply`, `Log`.

`SetLights`, `SetStatus` and `LinkPlan` are *derived* after every event and
emitted only when they change, so the drivers see a plan, not a stream.

## The child's side

Three modes: `IDLE`, `RECORDING`, `PLAYING`. Everything else is overlay
(inbox, cue, lock).

| Press | Idle | Recording | Playing |
| --- | --- | --- | --- |
| Record | start tone, played **to the end** (amp off), then mic on, capture starts, steady red | stop: **mic off first**, then `StopCapture`, then the "done" tone | ignored — mic and amp are never on together |
| Play | oldest unheard plays; with nothing new, the last one again | ignored | ignored (no restart, no skip) |
| Both, 3 s | travel lock toggles; Play blinks white twice | stops the recording, then locks | stops playback (not counted as heard), then locks |

- A press fires **at 0.5 s of hold**, not on release: the red light answers
  while the finger is still down (a hold released after 0.5 s but before the
  next tick still counts — never tick-dependent). Under 0.5 s nothing happens
  ([ADR 0016](../docs/decisions/0016-two-buttons-no-lid.md)).
- Recording stops itself at the 5-minute cap or after 20 s of continuous
  silence (`dsp.SPEECH_RMS`, per 100 ms block — tune on real recordings).
  Under 1 s of speech after trimming is discarded: no pulse, no file.
- **The got-it pulse comes only on `Queued`**, which the audio worker posts
  after the sealed container is fsynced into the outbox
  ([ADR 0010](../docs/decisions/0010-nothing-is-lost.md)). Online and offline
  are identical.
- **Quiet hours**: no chime, play still works, the glow is capped at 30 %.
  Enforced from the settings on `/data`, so they work after a reboot with no
  link. There is no mute ([ADR 0020](../docs/decisions/0020-no-mute-replay-green-link.md)).
- **Replay**: the last played message stays on disk; Play with nothing new
  repeats it, lights `PLAYING`, opens the window, and is not reported again.
- **Waiting → resting** after 2 h without any press: dim, not off. Any press
  resets it.
- A locked box still shows *waiting* — the glow is information for the
  child, the lock is for the bag.
- **Interrupts, decided here** (open in `components/audio-playback.md` Q4):
  Play during playback and Record during playback are ignored; Record
  during recording stops. Simplest, and it keeps the mic and the amp apart.

### Lights: plan, then render

The core emits a `LightsPlan` — which of the five states, an optional cue
(got-it pulse, lock blink), brightness, resting, quiet, ready. `lights.render()`
turns it into levels at 30 Hz. Two rules live there and are tested against
every combination of inputs:

1. **The record button's red channel is 0 or 1, never in between.** That
   pin is the mic's supply. It is 1 only in `RECORDING`, and `led_brightness`,
   quiet hours and cues never touch it. Ready / not ready is blue, the got-it
   pulse green and the lock blink white on Play for that reason. On the Pi
   the driver ignores the frame's red for Record entirely: the pin belongs
   to `MicPower`.

   Colours (ADR 0020, ADR 0024): Play green — pulsing when a message waits,
   steady while playing, dark otherwise (a replay is unannounced); Record —
   steady red while recording (GPIO 17, the mic pin), otherwise steady dim
   blue when ready and a slow blue blink when not, dark while playing or
   locked; got-it — one green pulse on Record; lock — two white blinks on
   Play.
2. The five states of `state.Lights`, plus `LightsPlan.ready` =
   `Core.ready()`: link OK and no fault. There are no status LEDs (ADR 0024);
   link, power and faults are otherwise telemetry and the app's.

## Storage and durability

```
/data/outbox/<id>.dbx + .json    sealed container + metadata; never evicted
/data/inbox/<id>.dbx + .json     downloaded, crc-checked; flags played/reported/broken
/data/capture/<id>.pcm + .json   the live recording; recovered at boot
/data/seq · lock · settings.json · keys/<n>.key · config.env
```

The life of a recording:

1. press → `MicPower(on)` → `/data/capture/<id>.pcm` grows, fsynced every second
2. press → `MicPower(off)` → `arecord` ends → `Encode(id)`
3. trim → `ffmpeg` → Opus → `seal()` → `outbox/<id>.dbx` (write, fsync, rename, fsync dir) → `.json` → **`Queued` → pulse**
4. the raw `.pcm` is unlinked only now (the plaintext leaves the card)
5. link round: `PUT` metadata → `upload-state` → missing chunks → `complete`
6. `2xx` → `outbox_remove` → `UploadDone` (opens the conversation window)

Every file write is temp → fsync → rename → fsync(dir). A power pull leaves
each file whole or absent. **At boot** `store.pending_captures()` finds any
`.pcm` a power cut interrupted and the core issues `Encode(recovered=True)`:
it is trimmed, sealed and queued as if stop had been pressed
([ADR 0019](../docs/decisions/0019-mains-first-battery-deferred.md)).

Inbox: a message is flagged `played` (with `played_at`) when heard, then
`reported` once the server has acknowledged it; after that every played
message but the newest is removed (`inbox_prune_played`). The newest stays
for replay and is passed to the core at boot as `last_played`. A container
that will not open is flagged `broken` and never re-downloaded.

## The link

One round, in this order, on the `link` thread:

1. modem on if the plan turned it off; wait for the interface (90 s, then `fault: modem`)
2. outbox, **oldest `seq` first**, each resumed from `upload-state`
3. `played` for everything the child heard; then all but the newest leave the inbox
4. `POST /device/checkin` with the core's telemetry; settings saved to `/data`
5. download every inbox id not on disk; crc before it is accepted; Range-resume of a partial body
6. modem off if the plan says so; sleep until the next round or a wake

The core sets the plan (`LinkPlan(interval_s, modem_on, wake)`) from
`state.poll_plan` ([ADR 0015](../docs/decisions/0015-adaptive-polling.md)):
60 s with the modem on when on mains or inside a conversation window, else
`idle_minutes` with the modem off between rounds. Wakes: boot, every
`Queued`, every `MarkPlayed`, `dadboxctl checkin`. Any failure ends the
round; the next try is at min(5 s · 2ⁿ, 5 min, interval). The worker never
gives up and never decides.

### The doorbell

A second thread, `doorbell`, holds the Supabase Realtime channel the server
names in its check-in answer ([ADR 0021](../docs/decisions/0021-doorbell.md),
`dadbox/doorbell.py`). It only posts two events: `DoorbellState(joined)` and
`Ring()`. The core does the rest:

- `DoorbellPlan(url, topic)` opens it only on mains (`state.doorbell_wanted`);
  unplugging closes it at once, and the core counts a joined doorbell on
  battery as closed.
- Joined: the timer stretches to `backstop_minutes` (10). Not joined: 60 s,
  exactly as before. Every join is a `LinkPlan(wake=True)`.
- A ring wakes the link at most every `RING_MIN_GAP_S` (5 s); rings inside
  the gap set `ring_pending` and are answered on the next tick after it. They
  are never dropped.
- Heartbeat every 25 s; a join or heartbeat unanswered for 10 s means dead,
  then reconnect at 5 s · 2ⁿ, at most 5 min. Real time, not the sim clock.

The WebSocket client is RFC 6455 on `socket` + `ssl`, about a hundred lines,
so the Pi needs no new package. The address is kept in `/data/doorbell.json`.
In the simulator the fake server hands out `sim://doorbell` and answers like
Realtime; its socket follows the fake modem's coverage, and
`dadboxctl sim doorbell silent` makes it half-open.

`Transport` is one method — `request(method, path, headers, body)` — so the
real `requests` session and the simulator's in-process server are
interchangeable, and `link.Client` is exercised against the fake in tests
with dropped links, shuffled chunks and repeated retries.

## Audio

| Step | Pi | Simulator |
| --- | --- | --- |
| capture | `arecord -f S16_LE -r 16000 -c 1 -t raw` → pump thread → file, RMS per block, first 100 ms dropped (mic click) | a voice-shaped synthetic signal at the box's rate; `speaking=False` for room tone |
| trim / discard | `dsp.trim` | same |
| encode | `ffmpeg … -c:a libopus -b:a 16k -application voip -f ogg` | same if ffmpeg is on the Mac, else a WAV labelled codec 2 (sim only, flagged in the UI) |
| play | decrypt → `ffmpeg -af volume=` → `aplay`; amp SD pin high only around it | waits the message's length on the fake clock; the browser plays the real file |
| chime | two soft notes from `dsp.chime_pcm()` via `aplay` | 0.5 s |

Volume is the app's `volume` applied as a gain (the MAX98357A's gain is a
pin). No normalisation yet (audio-capture Q6).

## Boot

`Service.start()`: mic pin low → temp dir wiped → lights → buttons →
`Boot` event (outbox sizes, unheard inbox, lock, saved settings, saved
doorbell address, pending captures, power) → link thread → doorbell thread →
power poll → core thread. The core's first
actions are `MicPower(False)`, an `Encode` per recovered capture, and a
`LinkPlan(wake=True)` — the box checks in at once, with `offline_s` from
the last saved check-in.

## Telemetry

Everything in PROTOCOL.md § Telemetry, composed by `Core.telemetry()` from
its own state plus what only the store knows (`outbox_bytes`,
`outbox_oldest_s`, `storage_pct`, inbox on disk). `rssi` is `None` until
the AT port is read; `house` is `unknown`; `battery_pct`/`charging` are
`null` without a battery.

## `dadboxctl`

JSON lines over `/run/dadbox/ctl.sock` (`$DADBOX_CTL`). `state`, `record
start|stop`, `play`, `lock on|off`, `led test`, `modem on|off` go through
the core as `Command` events and come back as `Reply`; `inbox`, `outbox`,
`checkin`, `sim link down|up`, `sim doorbell silent|up` are answered by the service. `checkin` blocks
for the next round and prints its result. Works identically against the
simulator.

## Pin map (proposed — confirm with the parts in hand)

Every wire — per header pin and per part, grounds and 5 V included — is in
[hardware/schematics/WIRING.md](../hardware/schematics/WIRING.md).

| BCM | Function |
| --- | --- |
| 17 | **Record button red ring and the mic's 3.3 V** — one pin, `DigitalOutputDevice`, never PWM |
| 27, 22 | Record button green, blue (software PWM) |
| 23, 24, 25 | Play button red, green, blue (software PWM) |
| 5, 6 | Record, Play switches to GND; internal pull-ups; 20 ms debounce in gpiozero |
| 16 | MAX98357A SD_MODE (the overlay's `sdmode` pin) |
| 4 | Modem PWRKEY: pin 7, joined to the HAT's pin 7 (P4) by one pin from below (ADR 0026), DIP 3 on; high presses the key (schematic). Held low from boot by `gpio=4=op,dl` |
| 18, 19, 20, 21 | I2S (`googlevoicehat-soundcard`) |
| 2, 3 | I²C — INA219 on the UPS module, later |
| 14, 15 | UART console |

Only `hw/pi.py` knows a pin number.

## The simulator

```bash
cd box && ~/.venvs/dadbox/bin/python -m dadbox.sim           # http://127.0.0.1:8765
DADBOX_CTL=~/.dadbox-sim/ctl.sock ~/.venvs/dadbox/bin/python -m dadbox.ctl state
```

What is real: the core, gestures, lights rendering, the store on
`~/.dadbox-sim` (fsyncs and all), the audio worker, the link worker and
`link.Client`, the container crypto, `dadboxctl`. What is fake: GPIO (the
mouse), the mic and speaker (synthesis; the browser plays real files), the
modem (a "coverage" switch and a power state), the gauge, the clock
(runs at 1–60× and can be skipped), and the server (an in-process
implementation of PROTOCOL v0.3 with the same rules as `server/`, minus
APNs — it records the pushes it would send). `--real-server` replaces the
last one with the live Supabase project from `tools/fakebox/.env`; the
parent is then the iPhone app.

The web page: the box (hold a button; the record ring's red is drawn from
the mic pin, not from the lights plan), what is inside it, `dadboxctl`,
the world (coverage, server up/down, mains/battery, the child talking or
silent, a broken mic, time speed and skips, the clock at 21:00 for quiet
hours, "pull the plug"), the parent's phone (send, a dropped upload,
quiet hours, volume, brightness, idle poll, the thread with `played_at`,
the pushes), and the log.

### What to check with it, in this order

`tests/sim_checklist.py` drives a fresh simulator through this list over its
HTTP API in about two minutes (a 20× clock, every step from a clean world).

- [x] a tap is ignored; a 0.5 s hold records; the ring is red exactly while the mic pin is high
- [x] stop → got-it pulse → outbox → upload → the thread shows it → push `message`
- [x] parent sends → next check-in → chime → Play breathes → play → `played_at` → push `played` → inbox empty
- [x] coverage off: Record blinks blue, a message still records and queues; coverage back: it goes
- [ ] quiet hours (clock → 21:00): no chime, glow dimmed, play works
- [ ] nothing new + Play: the last message plays again, `played_at` on the server does not change
- [ ] both buttons 3 s: lock blink, buttons dead, `locked: true` in telemetry, survives restart
- [ ] +2 h: *resting*; a press wakes it
- [ ] battery fitted, unplug: 30-minute cadence, modem off between; play → window → 1 min
- [ ] battery < 20 %: push `battery_low` once; < 5 %: shutdown
- [ ] pull the plug mid-recording, restart: the recording is queued, `recovered: true`
- [ ] server down for 3 minutes: box-late push once, clears on the next check-in
- [ ] `led test` sweeps every state; the mic pin stays low throughout

## Decisions taken here (revisit when the box exists)

| Question | Decision |
| --- | --- |
| Press fires when | at 0.5 s of hold, not on release |
| Play during playback / Record during playback | ignored |
| Play with nothing new | repeats the last message (ADR 0020) |
| Inbox removal after play | on the server's `played` ack, except the newest played message |
| Quiet-hours glow | capped at 30 % of `led_brightness` |
| Message chime | a marimba pair (G5, C6), once on arrival and once more 10 s later if still unplayed, idle and no press since; never in quiet hours |
| Record tones | rising two-note "bee-boo" (660 → 990 Hz) before the mic, the same falling after; `volume`, half in quiet hours (they answer a press; the message chime stays silent then) |
| Ready (blue–cyan flow on Record, 4 s, Play dark; Record dark while a message waits) | the server answered within 2 × the interval and no fault (ADR 0024) |
| Silence threshold / auto-stop | RMS 400 per 100 ms block, 20 s — tune on real audio |
| Raw capture lifetime | unlinked right after the sealed container is fsynced |
| Lock blink | two white blinks on Play (ADR 0024); Record keeps its red for the mic |
| Record not ready | dim blue blink, 1 s on / 2 s off; dark while locked or playing (ADR 0024) |
| Powering on | Play runs through the colours, Record dark, until first ready (or 3 min, a press, a waiting message); before the service: `config.txt` + `dadbox-bootlight.service` (ADR 0024 §7) |

## Not built yet

INA219 gauge and `mains` from battery current; `AT+CSQ` for `rssi`; the
modem PWRKEY pulse (wired, not yet proven); loudness normalisation; OTA beyond `rsync`/`git pull`.

## Tests

`~/.venvs/dadbox/bin/python -m pytest -q` in `box/` — 70 tests, ~7 s:
gestures, rendering (every input combination for the red rule), settings,
store, core (each rule above, on a fake clock), the fake server against the
protocol, the link worker with dropped links, and `test_e2e.py`: the whole
service on fake hardware at 40× — record, upload, reply, glow, play,
played; offline queueing; discard and silence-stop; lock and `dadboxctl`;
boot recovery.
