"""Every World control of the simulator page, over the page's own API: the
button must flip and the box must react.

    cd box && ~/.venvs/dadbox/bin/python tests/sim_world_controls.py 8797 fake
    cd box && ~/.venvs/dadbox/bin/python tests/sim_world_controls.py 8797 live   # the real server, tools/fakebox/.env

Live mode checks in with the Supabase project but records nothing.
"""
import json, os, subprocess, sys, tempfile, time, urllib.request
PORT, MODE = int(sys.argv[1]), sys.argv[2]            # "live" or "fake"
data = tempfile.mkdtemp(prefix="dadbox-world-")
args = [sys.executable, "-m", "dadbox.sim", "--port", str(PORT), "--data", data, "--log", "WARNING"] + (["--real-server"] if MODE == "live" else [])
proc = subprocess.Popen(args, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
URL = f"http://127.0.0.1:{PORT}"
def get(p): return json.loads(urllib.request.urlopen(URL + p, timeout=10).read())
def post(p, b):
    r = urllib.request.Request(URL + p, data=json.dumps(b).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=40).read())
S = lambda: get("/api/state")
W = lambda **b: post("/api/world", b)
ctl = lambda *a: post("/api/ctl", {"argv": list(a)})["reply"]
def until(c, what, t=15):
    t0 = time.monotonic()
    while time.monotonic() - t0 < t:
        try:
            if c(S()): return
        except Exception: pass
        time.sleep(0.1)
    raise AssertionError("timed out: " + what)
res = []
def down(): r = ctl("checkin"); assert r.startswith(("check-in failed", "check-in timed out")), r
def up():
    for _ in range(4):
        r = ctl("checkin")
        if r.startswith("check-in ok"): return
    raise AssertionError(r)
def check(name, fn):
    try: fn(); res.append(True); print("PASS", name)
    except Exception as e: res.append(False); print("FAIL", name, "—", e, "|", S()["box"]["state_line"])
for _ in range(150):
    try: S(); break
    except Exception: time.sleep(0.1)
until(lambda s: s["box"]["last_checkin_ago_s"] is not None, "first check-in", 30)

def coverage():
    W(coverage=False); assert S()["world"]["coverage"] is False
    down()
    W(coverage=True); assert S()["world"]["coverage"] is True
    up()
check("coverage: yes ⇄ NONE — check-in fails without coverage, works again after", coverage)

def server():
    W(server_down=True); assert S()["world"]["server_down"] is True
    down()
    W(server_down=False); assert S()["world"]["server_down"] is False
    up()
check("server: reachable ⇄ DOWN — check-in fails while down, works again after", server)

def simlink():
    ctl("sim", "link", "down"); assert S()["box"]["link_worker"]["simulated_down"]
    down()
    ctl("sim", "link", "up"); assert not S()["box"]["link_worker"]["simulated_down"]
    up()
check("sim link: up ⇄ DOWN", simlink)

def doorbell():
    ctl("sim", "doorbell", "silent"); assert S()["box"]["doorbell_worker"]["silent"]
    ctl("sim", "doorbell", "up"); assert not S()["box"]["doorbell_worker"]["silent"]
check("doorbell: normal ⇄ HALF-OPEN (flag flips)", doorbell)

def usb():
    W(mains=False); until(lambda s: not s["world"]["mains"] and s["box"]["power"] == "OK", "unplugged")
    W(mains=True); until(lambda s: s["world"]["mains"] and s["box"]["power"] == "MAINS", "plugged in")
check("USB power: present ⇄ ABSENT", usb)

def battery():
    W(battery_pct=80); until(lambda s: s["world"]["battery_pct"] == 80 and s["box"]["telemetry"]["battery_pct"] == 80, "fitted at 80")
    W(battery_pct=15, mains=False); until(lambda s: s["box"]["power"] == "LOW", "slider → LOW")
    W(charging=True, mains=True); until(lambda s: s["world"]["charging"] and s["box"]["power"] == "CHARGING", "charging")
    W(charging=False); until(lambda s: s["box"]["power"] == "MAINS", "not charging")
    W(battery_pct=None); until(lambda s: s["world"]["battery_pct"] is None and s["box"]["telemetry"]["battery_pct"] is None, "removed")
check("battery fitted ⇄ none, the % slider, charging yes ⇄ no", battery)

def child():
    W(speaking=False); assert S()["world"]["speaking"] is False
    W(speaking=True); assert S()["world"]["speaking"] is True
    W(fail_capture=True); assert S()["world"]["fail_capture"] is True
    ctl("record", "start"); until(lambda s: s["box"]["fault"] == "CAPTURE", "capture fault")
    W(fail_capture=False); assert S()["world"]["fail_capture"] is False
check("child talking ⇄ SILENT; mic works ⇄ BROKEN (fault shown)", child)

def speed():
    for v in (5, 20, 60, 1):
        W(speed=v); assert S()["sim"]["speed"] == v
check("speed 1× / 5× / 20× / 60×", speed)

def skips():
    for s_ in (60, 1800, 7200, 172800):
        t0 = S()["sim"]["now"]; W(skip_s=s_); assert S()["sim"]["now"] - t0 >= s_
check("+1 min / +30 min / +2 h / +48 h", skips)

def clock():
    W(wall_hhmm="21:00"); until(lambda s: s["box"]["quiet"], "quiet at 21:00")
    W(wall_hhmm="09:00"); until(lambda s: not s["box"]["quiet"], "not quiet at 09:00")
check("clock → 21:00 (quiet) / 09:00", clock)

def plug():
    r = W(power_cut=True); assert "power cut" in r.get("note", "")
    for _ in range(50):
        if proc.poll() is not None: break
        time.sleep(0.1)
    assert proc.poll() == 3, proc.poll()
check("pull the plug — the simulator exits (restart shows recovery)", plug)
if proc.poll() is None: proc.terminate()
print(f"{sum(res)}/{len(res)} {MODE}")
sys.exit(0 if all(res) else 1)
