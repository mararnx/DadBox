#!/usr/bin/env python3
"""Wrap the Opus packets of a CAF file in a standard Ogg Opus stream.

macOS can encode Opus (`afconvert -f caff -d opus -b 16000 in.aiff out.caf`) but
cannot write Ogg, and the Mac has no ffmpeg. This makes `codec = 2` test audio
for the fake box and the iOS demo without installing anything:

    say -o hello.aiff "Hello"
    afconvert -f caff -d opus -b 16000 hello.aiff hello.caf
    tools/caf2ogg.py hello.caf hello.opus

The box itself uses ffmpeg; this is a bench tool only.
"""
import struct
import sys


def read_caf(path):
    d = open(path, "rb").read()
    assert d[:4] == b"caff", "not a CAF file"
    o, chunks = 8, {}
    while o < len(d):
        kind, n = d[o:o + 4], struct.unpack(">q", d[o + 4:o + 12])[0]
        if n < 0:
            n = len(d) - o - 12
        chunks[kind] = d[o + 12:o + 12 + n]
        o += 12 + n
    rate = struct.unpack(">d", chunks[b"desc"][:8])[0]
    frames_per_packet = struct.unpack(">I", chunks[b"desc"][20:24])[0]
    pakt = chunks[b"pakt"]
    count, _, priming, _ = struct.unpack(">qqii", pakt[:24])
    i, sizes = 24, []
    while len(sizes) < count:          # variable-length big-endian integers
        v = 0
        while True:
            b = pakt[i]
            i += 1
            v = (v << 7) | (b & 0x7F)
            if not b & 0x80:
                break
        sizes.append(v)
    data, o, packets = chunks[b"data"][4:], 0, []
    for s in sizes:
        packets.append(data[o:o + s])
        o += s
    scale = 48000 / rate               # Ogg Opus counts everything at 48 kHz
    return packets, int(priming * scale), int(frames_per_packet * scale), int(rate)


def crc(buf):
    c = 0
    for x in buf:
        c ^= x << 24
        for _ in range(8):
            c = ((c << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if c & 0x80000000 else (c << 1) & 0xFFFFFFFF
    return c


def page(packets, granule, seq, flags, serial=0x0DADB0C5):
    lacing = b"".join(b"\xff" * (len(p) // 255) + bytes([len(p) % 255]) for p in packets)
    head = b"OggS\0" + bytes([flags]) + struct.pack("<qIII", granule, serial, seq, 0) + bytes([len(lacing)]) + lacing
    body = b"".join(packets)
    return head[:22] + struct.pack("<I", crc(head + body)) + head[26:] + body


def main(src, dst):
    packets, pre_skip, step, rate = read_caf(src)
    out = page([b"OpusHead" + struct.pack("<BBHIhB", 1, 1, pre_skip, rate, 0, 0)], 0, 0, 2)
    out += page([b"OpusTags" + struct.pack("<I", 6) + b"dadbox" + struct.pack("<I", 0)], 0, 1, 0)
    granule, seq = 0, 2
    for k in range(0, len(packets), 40):
        group = packets[k:k + 40]
        granule += step * len(group)
        out += page(group, granule, seq, 4 if k + 40 >= len(packets) else 0)
        seq += 1
    open(dst, "wb").write(out)
    print(f"{dst}: {len(packets)} packets, {granule / 48000:.2f} s, {len(out)} bytes")


if __name__ == "__main__":
    main(*sys.argv[1:3])
