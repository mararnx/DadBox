#!/usr/bin/env python3
"""Capture the board's serial output for a while, then exit.

`idf.py monitor` is interactive and never returns, which is useless from a
script. This opens the port, optionally resets the board, and captures for
N seconds or until a regex matches — to stdout and a file.

    tools/serial_capture.py                       # auto-detect port, 20 s
    tools/serial_capture.py -s 60 -o boot.log
    tools/serial_capture.py --until "READY|Guru Meditation" -s 90
    tools/serial_capture.py --reset               # toggle DTR/RTS first
    tools/serial_capture.py --send "state"        # send a console line, then capture

Needs pyserial:  python3 -m pip install --user pyserial
"""
import argparse, glob, re, sys, time

try:
    import serial
except ImportError:
    sys.exit("pyserial missing: python3 -m pip install --user pyserial")


def find_port():
    for pat in ("/dev/cu.usbserial*", "/dev/cu.wchusbserial*", "/dev/cu.SLAB*", "/dev/cu.usbmodem*"):
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[0]
    sys.exit("no board found on /dev/cu.* — is it plugged in?")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-p", "--port", help="serial port (default: auto-detect)")
    ap.add_argument("-b", "--baud", type=int, default=115200)
    ap.add_argument("-s", "--seconds", type=float, default=20, help="capture duration (default 20)")
    ap.add_argument("-o", "--out", help="also write to this file")
    ap.add_argument("--until", help="stop early when this regex matches a line")
    ap.add_argument("--reset", action="store_true", help="pulse DTR/RTS to reset the board first")
    ap.add_argument("--send", help="send this line (plus CR LF) after opening, e.g. a console command")
    a = ap.parse_args()

    port = a.port or find_port()
    stop = re.compile(a.until) if a.until else None
    out = open(a.out, "w") if a.out else None

    with serial.Serial(port, a.baud, timeout=0.2) as ser:
        if a.reset:
            # Classic ESP32 auto-reset via the USB-UART bridge: EN follows RTS, IO0 follows DTR.
            ser.dtr = False; ser.rts = True; time.sleep(0.1)
            ser.rts = False; time.sleep(0.1)
        if a.send:
            time.sleep(0.3)
            ser.write((a.send + "\r\n").encode())
        print(f"# {port} @ {a.baud}, {a.seconds}s" + (f", until /{a.until}/" if a.until else ""), file=sys.stderr)
        t0 = time.time()
        buf = b""
        while time.time() - t0 < a.seconds:
            chunk = ser.read(4096)
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                text = line.decode("utf-8", "replace").rstrip("\r")
                print(text)
                if out:
                    out.write(text + "\n"); out.flush()
                if stop and stop.search(text):
                    print(f"# matched /{a.until}/ after {time.time()-t0:.1f}s", file=sys.stderr)
                    return
        print(f"# {a.seconds}s elapsed", file=sys.stderr)


if __name__ == "__main__":
    main()
