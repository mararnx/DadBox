import json
from pathlib import Path

import pytest

from dadbox.container import (ContainerError, crc_ok, key_id_of, open_, parse_header, seal)

VECTORS = json.loads(
    (Path(__file__).parents[2] / "docs/testvectors/container-v1.json").read_text())
IDS = [v["name"] for v in VECTORS]


def _h(v, field):
    return bytes.fromhex(v[field])


@pytest.mark.parametrize("v", VECTORS, ids=IDS)
def test_seal_produces_the_vector_byte_for_byte(v):
    made = seal(_h(v, "plaintext_hex"), message_id=v["id"], key=_h(v, "key_hex"),
                key_id=v["key_id"], codec=v["codec"], duration_ms=v["duration_ms"],
                sample_rate=v["sample_rate"], nonce=_h(v, "nonce_hex"))
    assert made.hex() == v["container_hex"]


@pytest.mark.parametrize("v", VECTORS, ids=IDS)
def test_open_accepts_the_vector(v):
    container = _h(v, "container_hex")
    assert crc_ok(container)
    assert key_id_of(container) == v["key_id"]
    header, audio = open_(container, message_id=v["id"], keys={v["key_id"]: _h(v, "key_hex")})
    assert audio == _h(v, "plaintext_hex")
    assert (header.codec, header.duration_ms, header.sample_rate) == \
        (v["codec"], v["duration_ms"], v["sample_rate"])


def test_a_random_nonce_is_used_when_none_is_given():
    args = dict(message_id="01JAYZ3K7QW9E8RVX2M4N6P8TD", key=bytes(32), key_id=1,
                codec=2, duration_ms=1000)
    assert seal(b"hello", **args) != seal(b"hello", **args)


def test_another_messages_id_does_not_open_it():
    v = VECTORS[0]
    with pytest.raises(ContainerError, match="does not decrypt"):
        open_(_h(v, "container_hex"), message_id=VECTORS[1]["id"],
              keys={v["key_id"]: _h(v, "key_hex")})


def test_an_altered_duration_is_caught_even_with_a_recomputed_crc():
    # What a server could try: change the header, fix the crc. The GCM tag still fails.
    import struct
    import zlib
    v = VECTORS[0]
    body = bytearray(_h(v, "container_hex")[:-4])
    struct.pack_into("<I", body, 12, 99999)
    forged = bytes(body) + struct.pack("<I", zlib.crc32(bytes(body)) & 0xFFFFFFFF)
    assert crc_ok(forged) and parse_header(forged).duration_ms == 99999
    with pytest.raises(ContainerError, match="does not decrypt"):
        open_(forged, message_id=v["id"], keys={v["key_id"]: _h(v, "key_hex")})


def test_a_flipped_bit_fails_the_crc():
    v = VECTORS[0]
    damaged = bytearray(_h(v, "container_hex"))
    damaged[30] ^= 0x01
    assert not crc_ok(bytes(damaged))
    with pytest.raises(ContainerError, match="crc"):
        open_(bytes(damaged), message_id=v["id"], keys={v["key_id"]: _h(v, "key_hex")})


def test_a_missing_key_is_named():
    v = VECTORS[2]
    with pytest.raises(ContainerError, match="no key with id 3"):
        open_(_h(v, "container_hex"), message_id=v["id"], keys={1: bytes(32)})


def test_unencrypted_containers_are_refused():
    v = VECTORS[0]
    body = bytearray(_h(v, "container_hex"))
    body[7] = 0
    with pytest.raises(ContainerError, match="not encrypted"):
        open_(bytes(body), message_id=v["id"], keys={v["key_id"]: _h(v, "key_hex")})
