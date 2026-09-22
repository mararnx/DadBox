#!/usr/bin/env python3
"""fakebox — impersonate the box (or a parent) against the server. PROTOCOL.md v0.3.

Unblocks the server and iOS streams before any hardware exists, and stays on as
the rig for everything the real firmware must get right: resumable uploads over
a link that drops, idempotent retries, the check-in, Range downloads.

    fakebox.py checkin [--battery 68 [--no-mains]] [--fault storage] [--locked]   no --battery: mains only, as built
    fakebox.py send [--seconds 14] [--file a.ogg] [--drop-after 3] [--shuffle] [--repeat]
    fakebox.py resume                      finish every interrupted upload, as the box does on boot
    fakebox.py inbox [--play] [--halves]   check in, download what waits, decrypt, optionally mark played
    fakebox.py --as parent-a send          be the app: AAC (codec 3) to the box
    fakebox.py --as parent-a list | status | mute on|off
    fakebox.py --as parent-a setup-code    what the iOS app's setup screen wants: the code, then the key
    fakebox.py run [--every 60]            check in forever; download and play what arrives

Config comes from the environment or tools/fakebox/.env (gitignored):
    DADBOX_URL=https://<ref>.supabase.co/functions/v1/api
    DADBOX_TOKEN_BOX=…            DADBOX_TOKEN_PARENT_A=…
    DADBOX_KEY_1=<64 hex>         the parent-a ↔ box key. A TEST key: the real one
                                  is born on the phone and never comes near this file.
State (seq counter, outbox, downloads) lives in ~/.dadbox-fake/<identity>/.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import warnings

warnings.filterwarnings("ignore")          # urllib3's LibreSSL note on the stock Mac Python
import requests  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "box"))
from dadbox.container import CODEC_AAC_M4A, CODEC_OGG_OPUS, open_, seal  # noqa: E402
from dadbox.state import CHUNK_BYTES  # noqa: E402

B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid() -> str:
    n = (int(time.time() * 1000) << 80) | int.from_bytes(os.urandom(10), "big")
    return "".join(B32[(n >> (5 * i)) & 31] for i in reversed(range(26)))


def load_env() -> None:
    f = Path(__file__).with_name(".env")
    if f.exists():
        for line in f.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


class Client:
    def __init__(self, who: str):
        self.who = who
        self.url = os.environ["DADBOX_URL"].rstrip("/")
        token = os.environ["DADBOX_TOKEN_" + who.upper().replace("-", "_")]
        self.http = requests.Session()              # one TLS session, as the box keeps
        self.http.headers["Authorization"] = f"Bearer {token}"
        self.keys = {int(k[11:]): bytes.fromhex(v) for k, v in os.environ.items()
                     if k.startswith("DADBOX_KEY_")}
        self.dir = Path.home() / ".dadbox-fake" / who
        (self.dir / "outbox").mkdir(parents=True, exist_ok=True)
        (self.dir / "inbox").mkdir(exist_ok=True)

    def call(self, method: str, path: str, **kw) -> requests.Response:
        r = self.http.request(method, self.url + path, timeout=30, **kw)
        if r.status_code >= 400:
            sys.exit(f"{method} {path} → {r.status_code} {r.text}")
        return r

    def next_seq(self) -> int:
        f = self.dir / "seq"                        # the box keeps this beside the outbox
        n = int(f.read_text()) + 1 if f.exists() else 1
        f.write_text(str(n))
        return n


# --- sending --------------------------------------------------------------------

def cmd_send(c: Client, a) -> None:
    if a.file:
        audio = Path(a.file).read_bytes()
    else:                                           # noise of a plausible size: 16 kbps
        audio = b"OggS" + os.urandom(max(1, a.seconds * 2000 - 4))
    parent = c.who != "box"
    mid, key_id = ulid(), min(c.keys)
    container = seal(audio, message_id=mid, key=c.keys[key_id], key_id=key_id,
                     codec=CODEC_AAC_M4A if parent else CODEC_OGG_OPUS,
                     duration_ms=a.seconds * 1000)
    meta = {"seq": c.next_seq(), "to": "box" if parent else "parent-a",
            "created_at": datetime.now(timezone.utc).isoformat(), "time_ok": not a.no_clock,
            "duration_ms": a.seconds * 1000, "codec": CODEC_AAC_M4A if parent else CODEC_OGG_OPUS,
            "key_id": key_id, "bytes": len(container)}
    # Disk first, network second: what the real box does before its got-it pulse.
    (c.dir / "outbox" / f"{mid}.dbx").write_bytes(container)
    (c.dir / "outbox" / f"{mid}.json").write_text(json.dumps(meta))
    print(f"{mid}  seq {meta['seq']}  {len(container)} bytes  queued")
    upload(c, mid, drop_after=a.drop_after, shuffle=a.shuffle, repeat=a.repeat)


def upload(c: Client, mid: str, drop_after=None, shuffle=False, repeat=False) -> None:
    container = (c.dir / "outbox" / f"{mid}.dbx").read_bytes()
    meta = json.loads((c.dir / "outbox" / f"{mid}.json").read_text())
    c.call("PUT", f"/messages/{mid}", json=meta)
    have = set(c.call("GET", f"/messages/{mid}/upload-state").json()["received"])
    total = -(-len(container) // CHUNK_BYTES)
    todo = [i for i in range(total) if i not in have]
    if shuffle:
        random.shuffle(todo)
    if repeat and todo:
        todo = todo + todo[:1]                      # a retry the server must treat as the same chunk
    print(f"  {len(have)}/{total} already there; sending {len(todo)}")
    for n, i in enumerate(todo):
        if drop_after is not None and n >= drop_after:
            print(f"  link dropped after {n} chunks — run `resume`")
            return
        c.call("PUT", f"/messages/{mid}/chunks/{i}", data=container[i * CHUNK_BYTES:(i + 1) * CHUNK_BYTES],
               headers={"X-Chunk-Total": str(total), "Content-Type": "application/octet-stream"})
    state = c.call("POST", f"/messages/{mid}/complete").json()["state"]
    # Only now — on the server's 2xx — does the copy leave the outbox (ADR 0010).
    (c.dir / "outbox" / f"{mid}.dbx").unlink()
    (c.dir / "outbox" / f"{mid}.json").unlink()
    print(f"  complete → {state}; removed from outbox")


def cmd_resume(c: Client, a) -> None:
    waiting = sorted(p.stem for p in (c.dir / "outbox").glob("*.dbx"))
    print(f"{len(waiting)} in the outbox")
    for mid in waiting:
        print(mid)
        upload(c, mid)


# --- the box's loop ---------------------------------------------------------------

def telemetry(c: Client, a) -> dict:
    outbox = list((c.dir / "outbox").glob("*.dbx"))
    no_battery = a.no_battery or a.battery is None   # the first box: mains only (ADR 0019)
    return {"battery_pct": None if no_battery else a.battery, "charging": False,
            "mains": True if no_battery else not a.no_mains, "rssi": -91,
            "fw": "fakebox", "outbox": len(outbox), "outbox_bytes": sum(p.stat().st_size for p in outbox),
            "outbox_oldest_s": int(time.time() - min((p.stat().st_mtime for p in outbox), default=time.time())),
            "storage_pct": 1, "inbox": len(list((c.dir / "inbox").glob("*.dbx"))), "uptime_s": 1,
            "offline_s": a.offline, "next_checkin_s": a.every, "recording": False,
            "locked": a.locked, "house": "unknown", "fault": a.fault}


def cmd_checkin(c: Client, a) -> dict:
    r = c.call("POST", "/device/checkin", json=telemetry(c, a)).json()
    print(f"checked in; inbox {r['inbox']}; poll {r['settings']['poll']}; mute {r['settings']['mute']}")
    return r


def cmd_inbox(c: Client, a) -> None:
    for mid in cmd_checkin(c, a)["inbox"]:
        path = f"/messages/{mid}/audio"
        if a.halves:                                # a link that drops: two Range requests
            head = c.call("GET", path, headers={"Range": "bytes=0-99"}).content
            container = head + c.call("GET", path, headers={"Range": f"bytes={len(head)}-"}).content
        else:
            container = c.call("GET", path).content
        header, audio = open_(container, message_id=mid, keys=c.keys)
        out = c.dir / "inbox" / f"{mid}.{'m4a' if header.codec == CODEC_AAC_M4A else 'ogg'}"
        out.write_bytes(audio)
        print(f"{mid}  {header.duration_ms} ms  codec {header.codec}  decrypted → {out}")
        if a.play:
            print(f"  played → {c.call('POST', f'/messages/{mid}/played').json()['played_at']}")


def cmd_run(c: Client, a) -> None:
    a.play, a.halves = True, False
    while True:
        cmd_inbox(c, a)
        time.sleep(a.every)


# --- the app's side ------------------------------------------------------------------

def cmd_list(c: Client, a) -> None:
    cursor = None
    while True:
        r = c.call("GET", "/messages", params={"cursor": cursor} if cursor else None).json()
        for m in r["messages"]:
            print(f"{m['id']}  {m['from']:>8} → {m['to']:<8}  {m['duration_ms']:>6} ms  {m['state']:<9}"
                  f"  played {m['played_at'] or '—'}")
        cursor = r["cursor"]
        if not r["more"]:
            print(f"max_seq {r['max_seq']}")
            return


def cmd_status(c: Client, a) -> None:
    print(json.dumps(c.call("GET", "/device/status").json(), indent=2))


def cmd_mute(c: Client, a) -> None:
    mine = "a" if c.who == "parent-a" else "b"
    r = c.call("PATCH", "/settings", json={"mute": {mine: a.state == "on"}}).json()
    print(r["settings"]["mute"], r["settings_meta"].get(f"mute.{mine}"))


def cmd_setup_code(c: Client, a) -> None:
    """The two things the app's setup screen asks for (ios/DESIGN.md § Setup)."""
    import base64
    code = {"v": 1, "url": c.url, "identity": c.who, "token": c.http.headers["Authorization"][7:]}
    key_id = 2 if c.who == "parent-b" else 1
    key = base64.urlsafe_b64encode(c.keys[key_id]).decode().rstrip("=")
    try:
        import qrcode                               # optional: pip install qrcode
    except ImportError:
        qrcode = None
    for n, (what, text) in enumerate([("setup code — scan or paste into the app", json.dumps(code, separators=(",", ":"))),
                                      ("the key, 43 characters — scan or type (a TEST key; the real one is born on the phone)", key)], 1):
        print(f"{n} · {what}:\n\n  {text}\n")
        if qrcode and a.qr:
            q = qrcode.QRCode(border=2); q.add_data(text); q.print_ascii(invert=True); print()


def main() -> None:
    load_env()
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--as", dest="who", default="box", choices=["box", "parent-a", "parent-b"])
    sub = p.add_subparsers(dest="cmd", required=True)

    def box_flags(s):
        s.add_argument("--battery", type=int, default=None, help="battery_pct; omitted = no battery fitted (the first box)")
        s.add_argument("--no-battery", action="store_true")
        s.add_argument("--no-mains", action="store_true")
        s.add_argument("--fault", choices=["storage", "modem", "capture", "charger"])
        s.add_argument("--locked", action="store_true")
        s.add_argument("--offline", type=int, default=0, help="offline_s to report")
        s.add_argument("--every", type=int, default=60, help="next_checkin_s")

    s = sub.add_parser("send")
    s.add_argument("--seconds", type=int, default=14)
    s.add_argument("--file")
    s.add_argument("--drop-after", type=int)
    s.add_argument("--shuffle", action="store_true")
    s.add_argument("--repeat", action="store_true")
    s.add_argument("--no-clock", action="store_true", help="time_ok: false — recorded before the clock was set")
    s.set_defaults(fn=cmd_send)
    sub.add_parser("resume").set_defaults(fn=cmd_resume)
    s = sub.add_parser("checkin"); box_flags(s); s.set_defaults(fn=cmd_checkin)
    s = sub.add_parser("inbox"); box_flags(s)
    s.add_argument("--play", action="store_true")
    s.add_argument("--halves", action="store_true")
    s.set_defaults(fn=cmd_inbox)
    s = sub.add_parser("run"); box_flags(s); s.set_defaults(fn=cmd_run)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    s = sub.add_parser("mute"); s.add_argument("state", choices=["on", "off"]); s.set_defaults(fn=cmd_mute)
    s = sub.add_parser("setup-code"); s.add_argument("--qr", action="store_true", help="also as QR codes to scan"); s.set_defaults(fn=cmd_setup_code)

    a = p.parse_args()
    a.fn(Client(a.who), a)


if __name__ == "__main__":
    main()
