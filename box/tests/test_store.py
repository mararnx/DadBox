from dadbox.store import Store


def test_outbox_orders_by_seq_and_is_atomic(tmp_path):
    st = Store(tmp_path)
    st.enqueue("01JAYZ3K7QW9E8RVX2M4N6P8TD", b"b", {"seq": 2})
    st.enqueue("01JAYZ3K7QW9E8RVX2M4N6P8TA", b"a", {"seq": 1})
    assert st.outbox_ids() == ["01JAYZ3K7QW9E8RVX2M4N6P8TA", "01JAYZ3K7QW9E8RVX2M4N6P8TD"]
    assert not list(tmp_path.glob("**/*.tmp"))
    st.outbox_set_state("01JAYZ3K7QW9E8RVX2M4N6P8TA", "uploading")
    assert st.outbox_meta("01JAYZ3K7QW9E8RVX2M4N6P8TA")["state"] == "uploading"
    st.outbox_remove("01JAYZ3K7QW9E8RVX2M4N6P8TA")
    assert st.outbox_ids() == ["01JAYZ3K7QW9E8RVX2M4N6P8TD"]


def test_seq_is_monotonic_across_instances(tmp_path):
    assert Store(tmp_path).next_seq() == 1
    assert Store(tmp_path).next_seq() == 2


def test_travel_lock_survives_a_reboot(tmp_path):
    Store(tmp_path).set_locked(True)
    assert Store(tmp_path).locked()
    Store(tmp_path).set_locked(False)
    assert not Store(tmp_path).locked()


def test_an_interrupted_capture_is_found_at_boot(tmp_path):
    st = Store(tmp_path)
    p = st.begin_capture("01JAYZ3K7QW9E8RVX2M4N6P8TD", {"created_at": "x", "time_ok": False})
    p.write_bytes(b"\x00" * 3200)
    assert Store(tmp_path).pending_captures() == ["01JAYZ3K7QW9E8RVX2M4N6P8TD"]
    st.remove_capture("01JAYZ3K7QW9E8RVX2M4N6P8TD")
    assert st.pending_captures() == []


def test_inbox_flags(tmp_path):
    st = Store(tmp_path)
    st.inbox_put("01JAYZ3K7QW9E8RVX2M4N6P8TD", b"x")
    st.inbox_put("01JAYZ3K7QW9E8RVX2M4N6P8TA", b"y")
    assert st.inbox_unheard() == ["01JAYZ3K7QW9E8RVX2M4N6P8TA", "01JAYZ3K7QW9E8RVX2M4N6P8TD"]
    st.inbox_mark("01JAYZ3K7QW9E8RVX2M4N6P8TA", played=True)
    assert st.inbox_unheard() == ["01JAYZ3K7QW9E8RVX2M4N6P8TD"]
    assert st.inbox_to_report() == ["01JAYZ3K7QW9E8RVX2M4N6P8TA"]
    st.inbox_mark("01JAYZ3K7QW9E8RVX2M4N6P8TA", reported=True)
    assert st.inbox_to_report() == []
    st.inbox_mark("01JAYZ3K7QW9E8RVX2M4N6P8TD", broken=True)
    assert st.inbox_unheard() == [] and st.inbox_broken() == ["01JAYZ3K7QW9E8RVX2M4N6P8TD"]
    assert st.keys() == {}
    st.put_key(1, bytes(32))
    assert st.keys() == {1: bytes(32)}
