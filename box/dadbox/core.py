"""The box's brain: one pure state machine. See box/DESIGN.md.

Events in, actions out. No I/O, no threads, no sleeping; the only time it
knows is the `Clock` it was handed. Every fact a driver or worker learns
arrives as an event; everything the box should do leaves as an action. The
service (`service.py`) is the one place where the two meet, and the same
core runs unchanged on the Pi, in the simulator and in the tests.

Rules it enforces, by construction:

- The button lights have no error state (`state.lights_state`).
- The mic pin is raised only by `StartRecording` and dropped before anything
  else happens on stop; the mic and the amp are never on together.
- The got-it cue fires only on `Queued`, which the audio worker posts after
  the container is fsynced (ADR 0010).
- Presses under 0.5 s and the travel lock are `gestures.py`'s job; the core
  sees presses, never contacts.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from . import state as rules
from .clock import Clock
from .gestures import Button, Gestures, LockGesture, Press
from .ids import ulid
from .lights import Cue, LightsPlan, StatusPlan, cue_active
from .settings import Settings, in_quiet_hours
from .state import Fault, Lights, Link, Power

FW_VERSION = "0.2.0"
FLASH_LINK_FOR_S = 3600          # LINK "brief on" per check-in, only in the first hour after boot
REBOOT_CHECKIN_WINDOW_S = 0      # placeholder for a future "check in at once after boot"


class Mode(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PLAYING = "playing"


# --- Events (in) ------------------------------------------------------------------------

class Event:
    pass


@dataclass(frozen=True)
class Boot(Event):
    outbox: Dict[str, int]                   # id → bytes
    inbox: Sequence[str]                     # unheard, oldest first
    locked: bool
    settings: Settings
    pending_captures: Sequence[str] = ()
    mains: bool = True
    battery_pct: Optional[int] = None
    charging: bool = False
    last_checkin_wall: Optional[float] = None   # for offline_s on the first check-in


@dataclass(frozen=True)
class Contact(Event):
    """Raw button contact, from GPIO or the simulator's mouse."""
    button: Button
    down: bool


@dataclass(frozen=True)
class Tick(Event):
    pass


@dataclass(frozen=True)
class CaptureLevel(Event):
    message_id: str
    elapsed_s: float
    silence_s: float


@dataclass(frozen=True)
class CaptureEnded(Event):
    message_id: str
    ok: bool
    reason: str = ""


@dataclass(frozen=True)
class Queued(Event):
    """The container is on /data and fsynced. The pulse may follow."""
    message_id: str
    bytes: int
    duration_ms: int


@dataclass(frozen=True)
class Discarded(Event):
    message_id: str
    reason: str


@dataclass(frozen=True)
class UploadDone(Event):
    message_id: str


@dataclass(frozen=True)
class Checkin(Event):
    ok: bool
    settings: Optional[Settings] = None
    inbox: Sequence[str] = ()
    rssi: Optional[int] = None
    error: str = ""


@dataclass(frozen=True)
class Downloaded(Event):
    message_id: str


@dataclass(frozen=True)
class PlaybackEnded(Event):
    message_id: str
    ok: bool = True


@dataclass(frozen=True)
class PlayedReported(Event):
    message_id: str


@dataclass(frozen=True)
class LinkState(Event):
    up: bool


@dataclass(frozen=True)
class PowerState(Event):
    mains: bool
    battery_pct: Optional[int] = None
    charging: bool = False


@dataclass(frozen=True)
class FaultEvent(Event):
    fault: Fault
    active: bool


@dataclass(frozen=True)
class Command(Event):
    """From `dadboxctl`. The service answers with a `Reply` action."""
    name: str
    args: Tuple[str, ...] = ()
    token: int = 0


# --- Actions (out) ----------------------------------------------------------------------

class Action:
    pass


@dataclass(frozen=True)
class MicPower(Action):
    """The one pin that is both the mic's supply and the record button's red light."""
    on: bool


@dataclass(frozen=True)
class SetLights(Action):
    plan: LightsPlan


@dataclass(frozen=True)
class SetStatus(Action):
    plan: StatusPlan


@dataclass(frozen=True)
class StartCapture(Action):
    message_id: str
    created_at_wall: float
    time_ok: bool


@dataclass(frozen=True)
class StopCapture(Action):
    message_id: str


@dataclass(frozen=True)
class Encode(Action):
    message_id: str
    recovered: bool = False


@dataclass(frozen=True)
class Play(Action):
    message_id: str
    volume: int


@dataclass(frozen=True)
class StopPlay(Action):
    pass


@dataclass(frozen=True)
class Chime(Action):
    volume: int


@dataclass(frozen=True)
class PersistLock(Action):
    locked: bool


@dataclass(frozen=True)
class MarkPlayed(Action):
    message_id: str
    ok: bool = True


@dataclass(frozen=True)
class LinkPlan(Action):
    """When to check in next and whether the modem stays on until then (ADR 0015)."""
    interval_s: int
    modem_on: bool
    wake: bool = False       # check in now (after an upload, on boot, on request)


@dataclass(frozen=True)
class Reply(Action):
    token: int
    text: str


@dataclass(frozen=True)
class Log(Action):
    message: str
    level: str = "info"


@dataclass(frozen=True)
class Shutdown(Action):
    reason: str


@dataclass(frozen=True)
class LedTest(Action):
    pass


@dataclass(frozen=True)
class ModemPower(Action):
    on: bool


# --- State ------------------------------------------------------------------------------

@dataclass
class BoxState:
    mode: Mode = Mode.IDLE
    locked: bool = False
    settings: Settings = field(default_factory=Settings)
    outbox: Dict[str, int] = field(default_factory=dict)
    inbox: List[str] = field(default_factory=list)          # unheard, oldest first
    recording_id: Optional[str] = None
    recording_since: float = 0.0
    silence_s: float = 0.0
    playing_id: Optional[str] = None
    cue: Optional[Cue] = None
    cue_at: float = 0.0
    boot_at: float = 0.0
    last_checkin_ok_at: Optional[float] = None
    last_checkin_wall: Optional[float] = None
    checkin_interval_s: int = 60
    modem_on: bool = True
    last_activity_at: Optional[float] = None                # upload done / played: opens the window
    last_interaction_at: float = 0.0                        # any press: resets *resting*
    waiting_since: Optional[float] = None
    mains: bool = True
    battery_pct: Optional[int] = None
    charging: bool = False
    faults: Set[Fault] = field(default_factory=set)
    link_up: bool = False
    rssi: Optional[int] = None
    time_ok: bool = False                                   # clock trusted once a check-in has succeeded
    flash_at: Optional[float] = None
    shutting_down: bool = False


class Core:
    def __init__(self, clock: Clock, *, has_battery: bool = False):
        self.clock = clock
        self.has_battery = has_battery
        self.s = BoxState()
        self.gestures = Gestures()
        self._lights: Optional[LightsPlan] = None
        self._status: Optional[StatusPlan] = None
        self._link_plan: Optional[Tuple[int, bool]] = None

    # --- entry point ----------------------------------------------------------------

    def handle(self, event: Event) -> List[Action]:
        now = self.clock.now()
        out: List[Action] = []
        h = getattr(self, "_on_" + type(event).__name__, None)
        if h is None:
            return [Log(f"unhandled event {event!r}", "warning")]
        h(event, now, out)
        out.extend(self._derive(now))
        return out

    # --- derived outputs, emitted only on change --------------------------------------

    def lights(self, now: float) -> Lights:
        return rules.lights_state(recording=self.s.mode is Mode.RECORDING,
                                  playing=self.s.mode is Mode.PLAYING,
                                  got_it_pulse=self.s.cue is Cue.GOT_IT and cue_active(self._plan_probe(), now),
                                  inbox=len(self.s.inbox))

    def _plan_probe(self) -> LightsPlan:
        return LightsPlan(cue=self.s.cue, cue_at=self.s.cue_at)

    def quiet(self) -> bool:
        return in_quiet_hours(self.s.settings.quiet_hours, self.clock.wall())

    def resting(self, now: float) -> bool:
        if not self.s.inbox or self.s.waiting_since is None:
            return False
        since = max(self.s.waiting_since, self.s.last_interaction_at)
        return now - since >= rules.RESTING_AFTER_S

    def link(self, now: float) -> Link:
        ok_at = self.s.last_checkin_ok_at
        if ok_at is not None and now - ok_at <= 2 * self.s.checkin_interval_s:
            return Link.OK
        return Link.DOWN_QUEUED if self.s.outbox else Link.DOWN

    def power(self) -> Power:
        if self.s.battery_pct is None:
            return Power.OK                     # no battery fitted: nothing to say (ADR 0019)
        if self.s.battery_pct < rules.SLEEP_PCT and not self.s.mains:
            return Power.ASLEEP
        if self.s.charging:
            return Power.CHARGING
        if self.s.battery_pct < rules.LOW_PCT and not self.s.mains:
            return Power.LOW
        return Power.OK

    def fault(self) -> Fault:
        for f in (Fault.STORAGE, Fault.CAPTURE, Fault.MODEM, Fault.CHARGER):
            if f in self.s.faults:
                return f
        return Fault.NONE

    def _derive(self, now: float) -> List[Action]:
        out: List[Action] = []
        cue = self.s.cue if self.s.cue is not None and cue_active(self._plan_probe(), now) else None
        if cue is None:
            self.s.cue = None
        plan = LightsPlan(lights=self.lights(now), cue=cue, cue_at=self.s.cue_at,
                          brightness=self.s.settings.led_brightness,
                          resting=self.resting(now), quiet=self.quiet())
        if plan != self._lights:
            self._lights = plan
            out.append(SetLights(plan))
        flash = self.s.flash_at if self.s.flash_at is not None and now - self.s.flash_at < 1.0 else None
        status = StatusPlan(link=self.link(now), power=self.power(), fault=self.fault(), flash_at=flash)
        if status != self._status:
            self._status = status
            out.append(SetStatus(status))
        interval, modem_on = self.plan(now)
        if (interval, modem_on) != self._link_plan:
            self._link_plan = (interval, modem_on)
            self.s.checkin_interval_s, self.s.modem_on = interval, modem_on
            out.append(LinkPlan(interval, modem_on))
        return out

    def plan(self, now: float) -> Tuple[int, bool]:
        since = None if self.s.last_activity_at is None else now - self.s.last_activity_at
        return rules.poll_plan(self.s.settings.poll, mains=self.s.mains, since_activity_s=since)

    # --- event handlers -----------------------------------------------------------------

    def _on_Boot(self, e: Boot, now: float, out: List[Action]) -> None:
        s = self.s
        s.boot_at = now
        s.last_interaction_at = now
        s.outbox = dict(e.outbox)
        s.inbox = list(e.inbox)
        s.waiting_since = now if s.inbox else None
        s.locked = e.locked
        s.settings = e.settings
        s.mains, s.battery_pct, s.charging = e.mains, e.battery_pct, e.charging
        s.last_checkin_wall = e.last_checkin_wall
        out.append(MicPower(False))                     # the wiring fact, restated at every boot
        out.append(Log(f"boot: outbox {len(s.outbox)}, inbox {len(s.inbox)}, "
                       f"{'locked' if s.locked else 'unlocked'}, {'mains' if s.mains else 'battery'}"))
        for mid in e.pending_captures:                  # a power cut mid-story: finish the job (ADR 0019)
            out.append(Log(f"recovering interrupted recording {mid}"))
            out.append(Encode(mid, recovered=True))
        self._link_plan = None                          # force a LinkPlan…
        interval, modem_on = self.plan(now)
        self._link_plan = (interval, modem_on)
        s.checkin_interval_s, s.modem_on = interval, modem_on
        out.append(LinkPlan(interval, modem_on, wake=True))   # …and check in at once

    def _on_Contact(self, e: Contact, now: float, out: List[Action]) -> None:
        for g in self.gestures.contact(e.button, e.down, now):
            self._gesture(g, now, out)

    def _on_Tick(self, e: Tick, now: float, out: List[Action]) -> None:
        for g in self.gestures.tick(now):
            self._gesture(g, now, out)
        if self.s.mode is Mode.RECORDING and self.s.recording_id:
            elapsed = now - self.s.recording_since
            if rules.should_stop_recording(elapsed_s=elapsed, silence_s=self.s.silence_s):
                why = "cap" if elapsed >= rules.MAX_MESSAGE_S else "silence"
                out.append(Log(f"recording {self.s.recording_id} stopped by {why}"))
                self._stop_recording(now, out)
        if (self.s.battery_pct is not None and not self.s.mains
                and self.s.battery_pct < rules.SLEEP_PCT and not self.s.shutting_down):
            self.s.shutting_down = True
            out.append(Shutdown(f"battery {self.s.battery_pct}% on battery"))

    def _gesture(self, g: Any, now: float, out: List[Action]) -> None:
        self.s.last_interaction_at = now
        if isinstance(g, LockGesture):
            self._set_lock(not self.s.locked, now, out)
            return
        if self.s.locked:
            out.append(Log(f"{g.button.value} press ignored: travel lock"))
            return
        if g.button is Button.RECORD:
            self._record_press(now, out)
        else:
            self._play_press(now, out)

    def _set_lock(self, locked: bool, now: float, out: List[Action]) -> None:
        if self.s.mode is Mode.RECORDING:
            self._stop_recording(now, out)
        if self.s.mode is Mode.PLAYING:
            out.append(StopPlay())
            self._playback_over(now, out, heard=False)
        self.s.locked = locked
        self.s.cue, self.s.cue_at = Cue.LOCK, now
        out.append(PersistLock(locked))
        out.append(Log("travel lock " + ("on" if locked else "off")))

    def _record_press(self, now: float, out: List[Action]) -> None:
        s = self.s
        if s.mode is Mode.RECORDING:
            self._stop_recording(now, out)
        elif s.mode is Mode.PLAYING:
            out.append(Log("record press ignored: playing (mic and amp are never on together)"))
        else:
            s.mode = Mode.RECORDING
            s.recording_id = ulid(self.clock.wall())
            s.recording_since = now
            s.silence_s = 0.0
            out.append(MicPower(True))                  # red light and mic supply: one pin, first
            out.append(StartCapture(s.recording_id, self.clock.wall(), s.time_ok))
            out.append(Log(f"recording {s.recording_id}"))

    def _stop_recording(self, now: float, out: List[Action]) -> None:
        s = self.s
        mid = s.recording_id
        out.append(MicPower(False))                     # mic dead before anything else
        if mid:
            out.append(StopCapture(mid))
        s.mode = Mode.IDLE
        s.recording_id = None

    def _play_press(self, now: float, out: List[Action]) -> None:
        s = self.s
        if s.mode is not Mode.IDLE:
            out.append(Log("play press ignored: busy"))
            return
        if not s.inbox:
            out.append(Log("play press: nothing waiting"))
            return
        if s.settings.muted:
            out.append(Log("play press ignored: muted"))
            return
        s.mode = Mode.PLAYING
        s.playing_id = s.inbox[0]
        out.append(Play(s.playing_id, s.settings.volume))
        out.append(Log(f"playing {s.playing_id}"))

    def _playback_over(self, now: float, out: List[Action], *, heard: bool) -> None:
        s = self.s
        mid = s.playing_id
        s.mode = Mode.IDLE
        s.playing_id = None
        if mid and heard:
            if mid in s.inbox:
                s.inbox.remove(mid)
            s.waiting_since = now if s.inbox else None
            s.last_activity_at = now                    # the child used the box: window opens (ADR 0015)
            out.append(MarkPlayed(mid))

    def _on_CaptureLevel(self, e: CaptureLevel, now: float, out: List[Action]) -> None:
        if e.message_id == self.s.recording_id:
            self.s.silence_s = e.silence_s

    def _on_CaptureEnded(self, e: CaptureEnded, now: float, out: List[Action]) -> None:
        if self.s.recording_id == e.message_id:         # the worker died under us
            self._stop_recording(now, out)
        if e.ok:
            out.append(Encode(e.message_id))
        else:
            self.s.faults.add(Fault.CAPTURE)
            out.append(Log(f"capture {e.message_id} failed: {e.reason}", "error"))

    def _on_Queued(self, e: Queued, now: float, out: List[Action]) -> None:
        self.s.faults.discard(Fault.CAPTURE)
        self.s.outbox[e.message_id] = e.bytes
        self.s.cue, self.s.cue_at = Cue.GOT_IT, now
        out.append(Log(f"queued {e.message_id}: {e.duration_ms} ms, {e.bytes} bytes — got it"))
        out.append(LinkPlan(*self.plan(now), wake=True))

    def _on_Discarded(self, e: Discarded, now: float, out: List[Action]) -> None:
        self.s.faults.discard(Fault.CAPTURE)
        out.append(Log(f"discarded {e.message_id}: {e.reason}"))

    def _on_UploadDone(self, e: UploadDone, now: float, out: List[Action]) -> None:
        self.s.outbox.pop(e.message_id, None)
        self.s.last_activity_at = now
        out.append(Log(f"uploaded {e.message_id}"))

    def _on_Checkin(self, e: Checkin, now: float, out: List[Action]) -> None:
        s = self.s
        if not e.ok:
            out.append(Log(f"check-in failed: {e.error}", "warning"))
            return
        s.last_checkin_ok_at = now
        s.last_checkin_wall = self.clock.wall()
        s.time_ok = True
        s.rssi = e.rssi
        s.faults.discard(Fault.MODEM)
        if now - s.boot_at < FLASH_LINK_FOR_S:
            s.flash_at = now
        if e.settings is not None and e.settings != s.settings:
            out.append(Log("settings changed: " + str(e.settings.to_json())))
            s.settings = e.settings

    def _on_Downloaded(self, e: Downloaded, now: float, out: List[Action]) -> None:
        s = self.s
        if e.message_id in s.inbox:
            return
        s.inbox.append(e.message_id)
        s.inbox.sort()
        if s.waiting_since is None:
            s.waiting_since = now
        if s.mode is Mode.IDLE and not s.settings.muted and not self.quiet():
            out.append(Chime(s.settings.volume))
        out.append(Log(f"new message {e.message_id} waiting ({len(s.inbox)})"))

    def _on_PlaybackEnded(self, e: PlaybackEnded, now: float, out: List[Action]) -> None:
        if self.s.playing_id != e.message_id:
            return
        if not e.ok:
            out.append(Log(f"could not play {e.message_id}", "error"))
            self.s.mode, self.s.playing_id = Mode.IDLE, None
            if e.message_id in self.s.inbox:
                self.s.inbox.remove(e.message_id)
            out.append(MarkPlayed(e.message_id, ok=False))
            return
        self._playback_over(now, out, heard=True)

    def _on_PlayedReported(self, e: PlayedReported, now: float, out: List[Action]) -> None:
        pass

    def _on_LinkState(self, e: LinkState, now: float, out: List[Action]) -> None:
        if e.up != self.s.link_up:
            self.s.link_up = e.up
            out.append(Log("link " + ("up" if e.up else "down")))

    def _on_PowerState(self, e: PowerState, now: float, out: List[Action]) -> None:
        s = self.s
        changed = (e.mains, e.battery_pct, e.charging) != (s.mains, s.battery_pct, s.charging)
        s.mains, s.battery_pct, s.charging = e.mains, e.battery_pct, e.charging
        if changed:
            out.append(Log(f"power: {'mains' if e.mains else 'battery'} {e.battery_pct}%"))

    def _on_FaultEvent(self, e: FaultEvent, now: float, out: List[Action]) -> None:
        if e.active:
            self.s.faults.add(e.fault)
        else:
            self.s.faults.discard(e.fault)

    def _on_Command(self, e: Command, now: float, out: List[Action]) -> None:
        name, args = e.name, e.args
        if name == "state":
            out.append(Reply(e.token, self.state_line(now)))
        elif name == "record" and args[:1] == ("start",):
            if self.s.mode is Mode.RECORDING:
                out.append(Reply(e.token, "already recording"))
            else:
                self.s.last_interaction_at = now
                self._record_press(now, out)
                out.append(Reply(e.token, f"recording {self.s.recording_id}" if self.s.recording_id else "not started"))
        elif name == "record" and args[:1] == ("stop",):
            if self.s.mode is not Mode.RECORDING:
                out.append(Reply(e.token, "not recording"))
            else:
                mid = self.s.recording_id
                self._stop_recording(now, out)
                out.append(Reply(e.token, f"stopped {mid}; encoding"))
        elif name == "play":
            before = self.s.mode
            self.s.last_interaction_at = now
            self._play_press(now, out)
            out.append(Reply(e.token, f"playing {self.s.playing_id}" if self.s.mode is Mode.PLAYING and before is not Mode.PLAYING
                             else "nothing to play" if not self.s.inbox else "not idle or muted"))
        elif name == "lock":
            want = args[:1] == ("on",)
            if want != self.s.locked:
                self._set_lock(want, now, out)
            out.append(Reply(e.token, "lock " + ("on" if self.s.locked else "off")))
        elif name == "led" and args[:1] == ("test",):
            out.append(LedTest())
            out.append(Reply(e.token, "sweeping every button-light state, 2 s each"))
        elif name == "modem":
            out.append(ModemPower(args[:1] == ("on",)))
            out.append(Reply(e.token, "modem " + ("on" if args[:1] == ("on",) else "off")))
        elif name == "checkin":
            out.append(LinkPlan(*self.plan(now), wake=True))
            out.append(Reply(e.token, "check-in requested"))
        else:
            out.append(Reply(e.token, f"unknown command: {name} {' '.join(args)}"))

    # --- what the outside asks of the core -------------------------------------------------

    def telemetry(self, *, outbox_bytes: int, outbox_oldest_s: int, storage_pct: int, inbox_on_disk: int) -> Dict[str, Any]:
        now = self.clock.now()
        s = self.s
        offline = 0
        if s.last_checkin_ok_at is None and s.last_checkin_wall is not None:
            offline = max(0, int(self.clock.wall() - s.last_checkin_wall))
        elif s.last_checkin_ok_at is not None and now - s.last_checkin_ok_at > 2 * s.checkin_interval_s:
            offline = int(now - s.last_checkin_ok_at)
        fault = self.fault()
        return {
            "battery_pct": s.battery_pct, "charging": s.charging if s.battery_pct is not None else None,
            "mains": s.mains, "rssi": s.rssi, "fw": FW_VERSION,
            "outbox": len(s.outbox), "outbox_bytes": outbox_bytes, "outbox_oldest_s": outbox_oldest_s,
            "storage_pct": storage_pct, "inbox": inbox_on_disk, "uptime_s": int(now - s.boot_at),
            "offline_s": offline, "next_checkin_s": s.checkin_interval_s,
            "recording": s.mode is Mode.RECORDING, "locked": s.locked, "house": "unknown",
            "fault": None if fault is Fault.NONE else fault.name.lower(),
        }

    def state_line(self, now: Optional[float] = None) -> str:
        now = self.clock.now() if now is None else now
        s = self.s
        soc = "n/a" if s.battery_pct is None else f"{s.battery_pct}%"
        return (f"lights={self.lights(now).name} link={self.link(now).name} power={self.power().name} "
                f"fault={self.fault().name} recording={'yes' if s.mode is Mode.RECORDING else 'no'} "
                f"playing={'yes' if s.mode is Mode.PLAYING else 'no'} lock={'on' if s.locked else 'off'} "
                f"mains={'yes' if s.mains else 'no'} soc={soc} inbox={len(s.inbox)} outbox={len(s.outbox)} "
                f"quiet={'yes' if self.quiet() else 'no'} muted={'yes' if s.settings.muted else 'no'} "
                f"next_checkin={s.checkin_interval_s}s modem={'on' if s.modem_on else 'off'}")

    def snapshot(self) -> Dict[str, Any]:
        now = self.clock.now()
        s = self.s
        return {
            "mode": s.mode.value, "lights": self.lights(now).name, "link": self.link(now).name,
            "power": self.power().name, "fault": self.fault().name, "locked": s.locked,
            "inbox": list(s.inbox), "outbox": dict(s.outbox), "recording_id": s.recording_id,
            "recording_s": (now - s.recording_since) if s.mode is Mode.RECORDING else 0.0,
            "silence_s": s.silence_s if s.mode is Mode.RECORDING else 0.0,
            "playing_id": s.playing_id, "mains": s.mains, "battery_pct": s.battery_pct,
            "charging": s.charging, "quiet": self.quiet(), "resting": self.resting(now),
            "muted": s.settings.muted, "settings": s.settings.to_json(),
            "checkin_interval_s": s.checkin_interval_s, "modem_on": s.modem_on,
            "last_checkin_ago_s": None if s.last_checkin_ok_at is None else now - s.last_checkin_ok_at,
            "link_up": s.link_up, "uptime_s": now - s.boot_at, "time_ok": s.time_ok,
            "window_open": s.last_activity_at is not None
            and now - s.last_activity_at < s.settings.poll.active_window_minutes * 60,
        }
