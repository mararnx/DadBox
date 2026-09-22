"""The link worker against the fake server: resume, never give up, download, report."""
import queue

from dadbox import container as dbx
from dadbox import core as c
from dadbox.clock import FakeClock
from dadbox.link import LinkWorker, Client
from dadbox.sim.hal import FakeModem
from dadbox.sim.parent import Parent
from dadbox.sim.server import FakeServer
from dadbox.store import Store
from dadbox.state import CHUNK_BYTES

KEY = bytes(range(32))


def setup(tmp_path):
    clock = FakeClock(wall=1_800_000_000.0)
    srv = FakeServer(clock)
    store = Store(tmp_path)
    store.put_key(1, KEY)
    events = queue.Queue()
    transport = srv.transport("box")
    worker = LinkWorker(client=Client(transport), store=store, modem=FakeModem(), clock=clock, post=events.put,
                        telemetry=lambda: {"next_checkin_s": 60, "fault": None, "mains": True, "battery_pct": None})
    return clock, srv, store, events, transport, worker


def enqueue(store, mid, n=100_000):
    cont = dbx.seal(b"OggS" + bytes(n), message_id=mid, key=KEY, key_id=1, codec=2, duration_ms=2000)
    store.enqueue(mid, cont, {"seq": store.next_seq(), "to": "parent-a", "created_at": "2026-09-22T10:00:00Z",
                              "time_ok": True, "duration_ms": 2000, "codec": 2, "key_id": 1, "bytes": len(cont)})
    return cont


def drain(events):
    out = []
    while not events.empty():
        out.append(events.get())
    return out


def test_a_round_uploads_oldest_first_then_checks_in(tmp_path):
    clock, srv, store, events, transport, worker = setup(tmp_path)
    enqueue(store, "01JAYZ3K7QW9E8RVX2M4N6P8TD")
    enqueue(store, "01JAYZ3K7QW9E8RVX2M4N6P8TA")   # later seq, earlier ULID: seq wins
    assert worker._round() is True
    ev = drain(events)
    done = [e.message_id for e in ev if isinstance(e, c.UploadDone)]
    assert done == ["01JAYZ3K7QW9E8RVX2M4N6P8TD", "01JAYZ3K7QW9E8RVX2M4N6P8TA"]
    assert store.outbox_ids() == [] and len(srv.blobs) == 2
    assert [e for e in ev if isinstance(e, c.Checkin)][-1].ok


def test_a_dropped_link_keeps_the_outbox_and_the_next_round_resumes(tmp_path):
    clock, srv, store, events, transport, worker = setup(tmp_path)
    cont = enqueue(store, "01JAYZ3K7QW9E8RVX2M4N6P8TD", n=200_000)
    total = -(-len(cont) // CHUNK_BYTES)
    transport.drop_after = 4                        # metadata, upload-state, two chunks — then the link dies
    assert worker._round() is False
    assert store.outbox_ids() == ["01JAYZ3K7QW9E8RVX2M4N6P8TD"]
    assert store.outbox_meta("01JAYZ3K7QW9E8RVX2M4N6P8TD")["state"] == "uploading"
    assert not [e for e in drain(events) if isinstance(e, c.UploadDone)]
    transport.drop_after = None
    before = transport.count
    assert worker._round() is True
    assert store.outbox_ids() == [] and srv.blobs["01JAYZ3K7QW9E8RVX2M4N6P8TD"] == cont
    assert transport.count - before < total + 4     # resumed: fewer chunk requests than a fresh upload


def test_inbox_is_downloaded_crc_checked_and_played_is_reported(tmp_path):
    clock, srv, store, events, transport, worker = setup(tmp_path)
    parent = Parent(srv, KEY)
    mid = parent.send(3.0, audio=b"RIFF" + bytes(50_000))
    assert worker._round() is True
    assert [e.message_id for e in drain(events) if isinstance(e, c.Downloaded)] == [mid]
    assert store.inbox_unheard() == [mid] and dbx.crc_ok(store.inbox_container(mid))
    store.inbox_mark(mid, played=True, played_at=1.0)
    assert worker._round() is True
    assert srv.messages[mid]["state"] == "played"
    assert [e.message_id for e in drain(events) if isinstance(e, c.PlayedReported)] == [mid]
    assert store.inbox_count() == 1 and store.inbox_last_played() == mid     # kept: Play repeats it (ADR 0020)
    mid2 = parent.send(3.0, audio=b"RIFF" + bytes(50_000))
    worker._round()
    store.inbox_mark(mid2, played=True, played_at=2.0)
    worker._round()
    assert store.inbox_count() == 1 and store.inbox_last_played() == mid2    # only the newest stays


def test_no_coverage_is_a_modem_fault_and_never_a_give_up(tmp_path):
    clock, srv, store, events, transport, worker = setup(tmp_path)
    worker.modem.coverage = False
    import threading
    threading.Thread(target=lambda: (clock.sleep(0.2), clock.skip(100)), daemon=True).start()
    assert worker._round() is False
    ev = drain(events)
    assert any(isinstance(e, c.FaultEvent) and e.fault.name == "MODEM" and e.active for e in ev)
    worker.modem.coverage = True
    assert worker._round() is True


def test_request_checkin_reports_a_round_begun_after_the_request(tmp_path):
    """A round already in flight started before the caller's change; its result must not be reported."""
    import threading
    clock, srv, store, events, transport, worker = setup(tmp_path)
    gate = threading.Event()
    real_round = worker._round
    calls = []

    def slow_round():
        calls.append(1)
        if len(calls) == 1:
            gate.wait(5)                           # the first round is in flight when the request arrives
            return True
        return False                               # the round after the request fails
    worker._round = slow_round
    worker.start()
    try:
        while not calls:
            clock.sleep(0.01)
        result = {}
        t = threading.Thread(target=lambda: result.setdefault("ok", worker.request_checkin(30)))
        t.start()
        clock.sleep(0.2)
        gate.set()                                 # the old round finishes "ok"…
        t.join(10)
        assert result["ok"] is False               # …but the answer is the round that began afterwards
    finally:
        worker.stop()
        worker._round = real_round
