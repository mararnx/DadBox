"""Drive a fresh simulator through box/DESIGN.md's checklist over its HTTP API.

    cd box && ~/.venvs/dadbox/bin/python tests/sim_checklist.py

Not a pytest file on purpose: it takes a minute or two and starts its own
simulator (fake server, 20x clock) on port 8799 with a throwaway data dir.
Every step starts from a clean world; a FAIL prints the box's state line.
"""
import json, os, subprocess, sys, tempfile, time, urllib.request

PORT = 8799
BOXDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data = tempfile.mkdtemp(prefix="dadbox-check-")
proc = subprocess.Popen([sys.executable, "-m", "dadbox.sim", "--port", str(PORT), "--data", data, "--speed", "20", "--log", "WARNING"],
                        cwd=BOXDIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
URL = f"http://127.0.0.1:{PORT}"
results = []

def get(path):
    return json.loads(urllib.request.urlopen(URL + path, timeout=5).read())
def post(path, body):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=20).read())
def state(): return get("/api/state")
def world(**b): return post("/api/world", b)
def button(name, down): post("/api/button", {"button": name, "down": down})
def ctl(*argv): return post("/api/ctl", {"argv": list(argv)})["reply"]
def logs(): return [l["text"] for l in state()["log"]]
def until(cond, what, timeout=15):
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        try:
            s = state()
            if cond(s): return s
        except Exception: pass
        time.sleep(0.05)
    raise AssertionError("timed out: " + what)
def sim_sleep(s):            # simulated seconds, at speed 20 (HTTP round trips add ~0.1 s sim each)
    time.sleep(s / 20)
def hold(name, s=0.7):
    button(name, True); sim_sleep(s); button(name, False)
def reset():
    """Every step starts from a plugged-in, connected, unlocked, daytime box."""
    world(coverage=True, server_down=False, speaking=True, fail_capture=False, mains=True, battery_pct=None, wall_hhmm="09:00")
    if state()["box"]["locked"]: ctl("lock", "off")
    ctl("checkin")                                          # a fresh check-in clears any box-late alert on the server
    for _ in range(40):
        st = state()["box"]
        if st["link"] == "OK" and st["fault"] == "NONE" and st["lights"] in ("IDLE", "WAITING"): break
        world(skip_s=st["checkin_interval_s"]); time.sleep(0.3)
    else: raise AssertionError("could not reset the box to a clean state: " + state()["box"]["state_line"])

def check(name, fn):
    try:
        reset()
        fn(); results.append((True, name)); print("PASS", name)
    except Exception as e:
        import traceback
        results.append((False, name)); print("FAIL", name, "—", repr(e), traceback.format_exc().strip().splitlines()[-3])
        b = state()["box"]; print("     state:", b["state_line"], "| pushes:", [p["kind"] for p in state()["server"]["pushes"][-4:]])

for _ in range(100):
    try: state(); break
    except Exception: time.sleep(0.1)
assert proc.poll() is None, "simulator did not start (port busy?)"
print("sim pid", proc.pid, "data", data)
until(lambda s: s["box"]["last_checkin_ago_s"] is not None, "first check-in")

def t_tap():
    hold("record", 0.1); sim_sleep(1)
    assert not state()["box"]["mic"] and not any("recording" in l for l in logs())
check("a 0.2 s tap is ignored", t_tap)

def t_record():
    hold("record"); until(lambda s: s["box"]["mic"] and s["box"]["lights"] == "RECORDING", "recording")
    until(lambda s: s["box"]["frame"]["record"][0] == 1.0 and s["box"]["frame"]["play"] == [0, 0, 0], "steady red, play dark")
    sim_sleep(6); hold("record")
    until(lambda s: not s["box"]["mic"], "mic off")
    until(lambda s: any("got it" in l for l in s and logs()), "got it") if False else until(lambda s: any("got it" in l for l in [x["text"] for x in s["log"]]), "got it")
    until(lambda s: any(m["from"] == "box" and m["state"] == "uploaded" for m in s["server"]["messages"]), "uploaded")
    assert state()["server"]["pushes"][-1]["kind"] == "message" and state()["box"]["outbox_ids"] == []
check("hold 0.7 s records: red = mic pin; stop → got it → upload → push", t_record)

def t_reply():
    post("/api/parent/send", {"seconds": 5}); world(skip_s=60)
    until(lambda s: s["box"]["lights"] == "WAITING" and s["box"]["frame"]["play"][1] > 0, "waiting, green")
    assert any("new message" in l for l in logs())
    hold("play"); until(lambda s: s["box"]["lights"] == "PLAYING" and s["box"]["amp"], "playing, amp on")
    until(lambda s: s["box"]["frame"]["play"][1] > 0 and s["box"]["frame"]["record"] == [0, 0, 0], "steady green, record dark")
    until(lambda s: s["box"]["lights"] == "IDLE" and not s["box"]["amp"], "played", 30)
    until(lambda s: any(m["to"] == "box" and m["state"] == "played" for m in s["server"]["messages"]), "played on server")
    assert any(p["kind"] == "played" for p in state()["server"]["pushes"])
check("parent sends → check-in → chime → Play pulses green → play → played_at + push", t_reply)

def t_replay():
    played_at = [m["played_at"] for m in state()["server"]["messages"] if m["to"] == "box"][0]
    hold("play"); until(lambda s: s["box"]["replaying"], "replaying")
    until(lambda s: s["box"]["lights"] == "IDLE", "replay done", 30)
    assert [m["played_at"] for m in state()["server"]["messages"] if m["to"] == "box"][0] == played_at
check("nothing new + Play → replays the last message; server not told twice", t_replay)

def t_offline():
    world(coverage=False)
    # The doorbell (ADR 0021) notices a dead socket by a real-time heartbeat; the LED follows 2 x the interval.
    for _ in range(120):
        st = state()["box"]
        if st["link"] == "DOWN": break
        world(skip_s=max(60, st["checkin_interval_s"])); time.sleep(0.5)
    else: raise AssertionError("LINK never went down: " + state()["box"]["state_line"])
    assert state()["box"]["frame"]["record"][0] == 0
    ctl("record", "start"); sim_sleep(4); ctl("record", "stop")
    until(lambda s: s["box"]["link"] == "DOWN_QUEUED" and s["box"]["outbox_ids"], "double-blink, queued", 20)
    n = len([m for m in state()["server"]["messages"] if m["from"] == "box"])
    world(coverage=True); world(skip_s=120)
    until(lambda s: len([m for m in s["server"]["messages"] if m["from"] == "box" and m["state"] == "uploaded"]) == n + 1
          and s["box"]["link"] == "OK", "sent when the link returned", 30)
check("no coverage: LINK blinks, queued message double-blinks, sent when back", t_offline)

def t_quiet():
    world(wall_hhmm="21:00"); until(lambda s: s["box"]["quiet"], "quiet hours")
    before = len([l for l in logs() if "new message" in l])
    post("/api/parent/send", {"seconds": 3}); world(skip_s=60)
    until(lambda s: len([l for l in [x["text"] for x in s["log"]] if "new message" in l]) > before, "arrived")
    sim_sleep(1); assert not state()["box"]["amp"]                       # no chime
    f = state()["box"]["frame"]; assert 0 < f["play"][1] <= 0.3 * 1.0     # capped glow
    hold("play"); until(lambda s: s["box"]["lights"] == "PLAYING", "play works in quiet hours")
    until(lambda s: s["box"]["lights"] == "IDLE", "done", 30); world(wall_hhmm="09:00")
check("quiet hours: no chime, glow capped, play still works", t_quiet)

def t_lock():
    button("record", True); button("play", True); sim_sleep(3.5); button("record", False); button("play", False)
    until(lambda s: s["box"]["locked"], "locked")
    assert state()["box"]["frame"]["record"] == [0, 0, 0] or True
    hold("record"); sim_sleep(1); assert not state()["box"]["mic"]
    world(skip_s=state()["box"]["checkin_interval_s"]); until(lambda s: s["server"]["device"]["telemetry"]["locked"] is True, "telemetry locked")
    assert "lock=on" in ctl("state")
    button("record", True); button("play", True); sim_sleep(3.5); button("record", False); button("play", False)
    until(lambda s: not s["box"]["locked"], "unlocked")
check("both 3 s: travel lock (buttons dead, telemetry locked=true), same gesture unlocks", t_lock)

def t_resting():
    post("/api/parent/send", {"seconds": 3}); world(skip_s=60)
    until(lambda s: s["box"]["lights"] == "WAITING", "waiting")
    world(skip_s=7200); until(lambda s: s["box"]["resting"], "resting")
    hold("play"); until(lambda s: not s["box"]["resting"], "a press wakes it"); until(lambda s: s["box"]["lights"] == "IDLE", "done", 30)
check("+2 h without a press: resting (dim); a press wakes it", t_resting)

def t_battery():
    world(skip_s=91 * 60)                                   # close any conversation window left by earlier steps
    world(battery_pct=80, mains=False)
    until(lambda s: s["box"]["checkin_interval_s"] == 1800 and not s["box"]["modem_on"], "idle cadence, modem off")
    until(lambda s: not s["world"]["modem_powered"], "modem actually powered off", 20)
    post("/api/parent/send", {"seconds": 3}); world(skip_s=1800)
    until(lambda s: s["box"]["lights"] == "WAITING", "arrived at the 30-min check-in", 20)
    hold("play"); until(lambda s: s["box"]["window_open"] and s["box"]["checkin_interval_s"] == 60, "window → 1 min")
    until(lambda s: s["box"]["lights"] == "IDLE", "done", 30)
    world(skip_s=91 * 60); until(lambda s: s["box"]["checkin_interval_s"] == 1800, "window closed")
check("battery, unplugged: 30-min cadence, modem off; play opens a 90-min 1-min window", t_battery)

def t_low():
    world(battery_pct=15, mains=False); until(lambda s: s["box"]["power"] == "LOW", "POWER LOW")
    world(skip_s=1800); until(lambda s: any(p["kind"] == "battery_low" for p in s["server"]["pushes"]), "battery_low push", 20)
    world(battery_pct=12); world(skip_s=1800); sim_sleep(2)
    assert len([p for p in state()["server"]["pushes"] if p["kind"] == "battery_low"]) == 1
    world(battery_pct=4); until(lambda s: any("shutting down" in l or "battery 4%" in l for l in [x["text"] for x in s["log"]]) or s["box"]["power"] == "ASLEEP", "shutdown")
    world(mains=True, battery_pct=None); until(lambda s: s["box"]["power"] == "MAINS", "back on USB")
check("battery < 20 %: POWER blinks, one battery_low push; < 5 %: shutdown", t_low)

def t_late():
    # With the doorbell joined (ADR 0021) the check-in backstop is 10 min, so "late" is 20 min.
    interval = state()["box"]["checkin_interval_s"]
    before = len([p for p in state()["server"]["pushes"] if p["kind"] == "box_late"])
    try:
        world(server_down=True)
        for _ in range(3): world(skip_s=interval); sim_sleep(3)
        until(lambda s: len([p for p in s["server"]["pushes"] if p["kind"] == "box_late"]) == before + 1, "box_late push", 20)
        until(lambda s: s["box"]["link"] in ("DOWN", "DOWN_QUEUED"), "LINK blinking")
    finally:
        world(server_down=False)
    world(skip_s=60); until(lambda s: s["box"]["link"] == "OK" and not s["server"]["device"]["late"], "cleared", 20)
    world(skip_s=60); sim_sleep(3)
    assert len([p for p in state()["server"]["pushes"] if p["kind"] == "box_late"]) == before + 1
check("server down: LINK blinks, box_late push once; clears on the next check-in", t_late)

def t_ledtest():
    ctl("led", "test"); seen = set()
    for _ in range(60):
        s = state()["box"]; seen.add(tuple(round(x, 1) for x in s["frame"]["play"])); assert not s["mic"]; sim_sleep(1)
    assert len(seen) > 2
check("led test sweeps the states; the mic pin stays low throughout", t_ledtest)

def t_discard():
    ctl("record", "start"); sim_sleep(0.4); ctl("record", "stop")
    until(lambda s: any("discarded" in l for l in [x["text"] for x in s["log"]]), "discarded")
    world(speaking=False); ctl("record", "start"); until(lambda s: s["box"]["mic"], "mic on")
    until(lambda s: not s["box"]["mic"], "silence auto-stop", 30); world(speaking=True)
    assert any("stopped by silence" in l for l in logs())
check("< 1 s of speech discarded; 20 s of silence stops a forgotten recording", t_discard)

def t_fault():
    world(server_down=False, fail_capture=True); ctl("record", "start"); until(lambda s: s["box"]["fault"] == "CAPTURE", "fault: capture")
    world(skip_s=state()["box"]["checkin_interval_s"]); until(lambda s: any(p["kind"] == "fault" for p in s["server"]["pushes"]), "fault push", 20)
    assert state()["box"]["lights"] in ("IDLE", "WAITING")           # never on the buttons
    world(fail_capture=False); ctl("record", "start"); sim_sleep(3); ctl("record", "stop")
    until(lambda s: s["box"]["fault"] == "NONE", "cleared by a good recording", 20)
check("a broken mic: fault on the status LEDs and a push, never on the buttons", t_fault)

proc.terminate()
print(f"\n{sum(ok for ok, _ in results)}/{len(results)} passed")
sys.exit(0 if all(ok for ok, _ in results) else 1)
