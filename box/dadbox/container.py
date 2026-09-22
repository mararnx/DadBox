"""The DBX1 container and its end-to-end encryption. Pure Python — runs on the Mac.

PROTOCOL.md § Container and § Encryption are the contract; the byte-exact
examples are docs/testvectors/container-v1.json and this module must produce
and accept every one of them.

    header (16)  "DBX1" · version · codec · channels · flags · sample_rate · duration_ms
    payload      key_id (1) ‖ nonce (12) ‖ AES-256-GCM ciphertext ‖ tag (16)
    trailer (4)  crc32 of header + payload, u32 LE

The AAD is the 16 header bytes followed by the 26 ASCII bytes of the message
id, so a server cannot swap the audio of two messages or alter a duration
without the tag failing. The crc32 covers ciphertext: the server checks
integrity without ever holding a key (ADR 0017).
"""
from __future__ import annotations

import os
import struct
import zlib
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"DBX1"
VERSION = 1
FLAG_ENCRYPTED = 0x01

CODEC_ADPCM = 1      # reserved; unused on the Pi
CODEC_OGG_OPUS = 2   # box → parent
CODEC_AAC_M4A = 3    # parent → box; ffmpeg decodes it

HEADER_LEN = 16
NONCE_LEN = 12
TAG_LEN = 16
KEY_LEN = 32
ID_LEN = 26          # ULID

_HEADER = struct.Struct("<4sBBBBII")


class ContainerError(ValueError):
    """The bytes are not a valid DBX1 container, or do not decrypt."""


@dataclass(frozen=True)
class Header:
    codec: int
    sample_rate: int
    duration_ms: int
    channels: int = 1
    flags: int = FLAG_ENCRYPTED
    version: int = VERSION

    def pack(self) -> bytes:
        return _HEADER.pack(MAGIC, self.version, self.codec, self.channels,
                            self.flags, self.sample_rate, self.duration_ms)


def parse_header(container: bytes) -> Header:
    if len(container) < HEADER_LEN:
        raise ContainerError("shorter than a header")
    magic, version, codec, channels, flags, sample_rate, duration_ms = \
        _HEADER.unpack_from(container)
    if magic != MAGIC:
        raise ContainerError("bad magic")
    if version != VERSION:
        raise ContainerError(f"unknown version {version}")
    return Header(codec=codec, sample_rate=sample_rate, duration_ms=duration_ms,
                  channels=channels, flags=flags, version=version)


def crc_ok(container: bytes) -> bool:
    """What the server checks on `complete` — no key needed."""
    if len(container) < HEADER_LEN + 4:
        return False
    (want,) = struct.unpack_from("<I", container, len(container) - 4)
    return zlib.crc32(container[:-4]) & 0xFFFFFFFF == want


def _aad(header: bytes, message_id: str) -> bytes:
    mid = message_id.encode("ascii")
    if len(mid) != ID_LEN:
        raise ContainerError("message id is not a 26-character ULID")
    return header + mid


def seal(audio: bytes, *, message_id: str, key: bytes, key_id: int, codec: int,
         duration_ms: int, sample_rate: int = 16000, nonce: bytes | None = None) -> bytes:
    """Encrypt an encoded audio file into a container.

    `nonce` exists for the test vectors only. Leave it None: a fresh random
    nonce per message is what makes GCM safe.
    """
    if len(key) != KEY_LEN:
        raise ContainerError("key must be 32 bytes")
    if not 1 <= key_id <= 255:
        raise ContainerError("key_id must be 1..255")
    nonce = os.urandom(NONCE_LEN) if nonce is None else nonce
    if len(nonce) != NONCE_LEN:
        raise ContainerError("nonce must be 12 bytes")
    header = Header(codec=codec, sample_rate=sample_rate, duration_ms=duration_ms).pack()
    sealed = AESGCM(key).encrypt(nonce, audio, _aad(header, message_id))  # ciphertext ‖ tag
    body = header + bytes([key_id]) + nonce + sealed
    return body + struct.pack("<I", zlib.crc32(body) & 0xFFFFFFFF)


def key_id_of(container: bytes) -> int:
    """Which key a container needs — read before choosing one from the keyring."""
    parse_header(container)
    if len(container) < HEADER_LEN + 1 + NONCE_LEN + TAG_LEN + 4:
        raise ContainerError("shorter than an empty message")
    return container[HEADER_LEN]


def open_(container: bytes, *, message_id: str, keys: dict[int, bytes]) -> tuple[Header, bytes]:
    """Verify and decrypt. `keys` maps key_id → key; old keys stay in it forever
    so old messages stay readable (ADR 0018)."""
    header = parse_header(container)
    if not header.flags & FLAG_ENCRYPTED:
        raise ContainerError("not encrypted — refused")
    if not crc_ok(container):
        raise ContainerError("crc mismatch")
    key_id = key_id_of(container)
    key = keys.get(key_id)
    if key is None:
        raise ContainerError(f"no key with id {key_id}")
    nonce_at = HEADER_LEN + 1
    nonce = container[nonce_at:nonce_at + NONCE_LEN]
    sealed = container[nonce_at + NONCE_LEN:-4]
    try:
        audio = AESGCM(key).decrypt(nonce, sealed, _aad(container[:HEADER_LEN], message_id))
    except InvalidTag:
        raise ContainerError("does not decrypt: wrong key, wrong id, or altered") from None
    return header, audio
