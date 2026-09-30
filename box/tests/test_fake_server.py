"""The simulator's server must behave like server/ — these are the rules the
box relies on."""
import json
import os

from dadbox import container as dbx
from dadbox.link import Client, LinkError
from dadbox.sim.parent import Parent
from dadbox.sim.server import FakeServer
from dadbox.state import CHUNK_BYTES

import pytest

KEY = bytes(range(32))
MID = "01JAYZ3K7QW9E8RVX2M4N6P8TD"


def sealed(n_bytes=70000, mid=MID):
    audio = b"OggS" + os.urandom(n_bytes)
    return dbx.seal(audio, message_id=mid, key=KEY, key_id=1, codec=2, duration_ms=3000)


def meta(container, seq=1):
    return {"seq": seq, "to": "parent-a", "created_at": "2026-09-22T10:00:00Z", "time_ok": True,
            "duration_ms": 3000, "codec": 2, "key_id": 1, "bytes": len(container)}


def test_upload_resumes_repeats_and_completes_once():
    srv = FakeServer()
    t = srv.transport("box")
    c = Client(t)
    cont = sealed()
    total = -(-len(cont) // CHUNK_BYTES)
    t.request("PUT", f"/messages/{MID}", headers={"Content-Type": "application/json"}, body=json.dumps(meta(cont)).encode())
    for i in (2, 0, 2):                                       # out of order and repeated
        t.request("PUT", f"/messages/{MID}/chunks/{i}", headers={"X-Chunk-Total": str(total)},
                  body=cont[i * CHUNK_BYTES:(i + 1) * CHUNK_BYTES])
    status, _, body = t.request("POST", f"/messages/{MID}/complete")
    assert status == 409 and json.loads(body)["missing"] == [1]
    assert c.upload(MID, cont, meta(cont))                    # resumes from upload-state: sends chunk 1 only
    assert srv.messages[MID]["state"] == "uploaded" and srv.blobs[MID] == cont
    assert c.upload(MID, cont, meta(cont))                    # a retry after success is harmless
    assert srv.pushes[-1]["kind"] == "message"


def test_same_id_different_metadata_is_409_and_bad_crc_is_422():
    srv = FakeServer()
    c = Client(srv.transport("box"))
    cont = sealed()
    c.upload(MID, cont, meta(cont))
    with pytest.raises(LinkError, match="409"):
        c.upload(MID, cont, dict(meta(cont), duration_ms=1))
    bad = bytearray(sealed(mid="01JAYZ3K7QW9E8RVX2M4N6P8TA")); bad[-1] ^= 0xFF
    with pytest.raises(LinkError, match="422"):
        c.upload("01JAYZ3K7QW9E8RVX2M4N6P8TA", bytes(bad), meta(bytes(bad), seq=2))


def test_the_box_token_never_lists_and_parents_see_their_thread():
    srv = FakeServer()
    status, _, _ = srv.transport("box").request("GET", "/messages")
    assert status == 403
    p = Parent(srv, KEY)
    mid = p.send(2.0, audio=b"RIFF" + bytes(100))
    assert [m["id"] for m in p.thread()] == [mid]
    settings, inbox, _, _ = Client(srv.transport("box")).checkin({"next_checkin_s": 60})
    assert inbox == [mid] and settings.poll.active_minutes == 1


def test_range_download_delivered_played_and_scope():
    srv = FakeServer()
    p = Parent(srv, KEY)
    mid = p.send(2.0, audio=b"RIFF" + bytes(100))
    box = Client(srv.transport("box"))
    head = srv.transport("box").request("GET", f"/messages/{mid}/audio", headers={"Range": "bytes=0-99"})
    assert head[0] == 206 and srv.messages[mid]["state"] == "uploaded"
    full = box.download(mid, head[2])
    assert dbx.crc_ok(full) and srv.messages[mid]["state"] == "delivered"
    box.played(mid)
    assert srv.messages[mid]["state"] == "played" and srv.messages[mid]["played_at"]
    assert srv.transport("box").request("GET", f"/messages/{mid}/audio")[0] == 404   # inbox only, never history
    assert srv.transport("parent-a").request("GET", f"/messages/{mid}/audio")[0] == 200


def test_settings_record_who_and_there_is_no_mute():
    srv = FakeServer()
    a = Parent(srv, KEY, who="parent-a")
    r = a.settings({"volume": 55, "quiet_hours": {"start": "19:00"}})
    assert r["settings"]["volume"] == 55 and r["settings_meta"]["volume"]["by"] == "parent-a"
    assert "mute" not in r["settings"]
    status, _, _ = srv.transport("parent-a").request("PATCH", "/settings", body=json.dumps({"mute": {"a": True}}).encode())
    assert status == 403


def test_box_late_alert_once_per_outage():
    from dadbox.clock import FakeClock
    clock = FakeClock(wall=1_800_000_000.0)
    srv = FakeServer(clock)
    Client(srv.transport("box")).checkin({"next_checkin_s": 60})
    srv.tick()
    assert not [p for p in srv.pushes if p["kind"] == "box_late"]
    clock.skip(130)
    srv.tick(); srv.tick()
    assert len([p for p in srv.pushes if p["kind"] == "box_late"]) == 1
