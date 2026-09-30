#!/usr/bin/env python3
"""Bring-up check for the SIM7670G HAT: USB, AT port, SIM, APN, registration, data.

Stdlib only, so it runs before the venv exists. Run as root (the tty and the
routes need it):

    sudo python3 box/setup/modem_check.py                  # report only
    sudo python3 box/setup/modem_check.py --apn internet   # also set the APN
    sudo python3 box/setup/modem_check.py --at 'AT+CPSI?'  # one command

Changes nothing except the APN in PDP context 1, and only with --apn.
"""
from __future__ import annotations

import argparse
import glob
import os
import select
import subprocess
import sys
import termios
import time

# SIMCom's own ID, or the Qualcomm composite ID the SIM7670G HAT reports (05c6:9330)
MODEM_IDS = ("1e0e:", "05c6:9330")


def sh(cmd: str) -> str:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return (r.stdout + r.stderr).strip()


class AtPort:
    def __init__(self, path: str):
        self.path = path
        self.fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        attrs = termios.tcgetattr(self.fd)
        attrs[0] = 0                                   # iflag: raw
        attrs[1] = 0                                   # oflag
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[3] = 0                                   # lflag: no echo, no canon
        attrs[4] = attrs[5] = termios.B115200
        termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        termios.tcflush(self.fd, termios.TCIOFLUSH)

    def cmd(self, line: str, timeout: float = 3.0) -> str:
        os.write(self.fd, (line + "\r").encode())
        buf, end = b"", time.monotonic() + timeout
        while time.monotonic() < end:
            r, _, _ = select.select([self.fd], [], [], 0.2)
            if r:
                try:
                    buf += os.read(self.fd, 4096)
                except BlockingIOError:
                    pass
                text = buf.decode(errors="replace")
                if text.rstrip().endswith(("OK", "ERROR")) or "+CME ERROR" in text:
                    break
        return "\n".join(l for l in buf.decode(errors="replace").splitlines()
                         if l.strip() and l.strip() != line)

    def close(self) -> None:
        os.close(self.fd)


def find_at_port() -> AtPort | None:
    for path in sorted(glob.glob("/dev/ttyUSB*")) + sorted(glob.glob("/dev/ttyACM*")):
        try:
            port = AtPort(path)
        except OSError:
            continue
        if port.cmd("AT", 1.0).endswith("OK"):
            return port
        port.close()
    return None


def section(title: str) -> None:
    print(f"\n== {title}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apn", help="write this APN into PDP context 1")
    ap.add_argument("--at", action="append", default=[], help="extra AT command(s) to run")
    args = ap.parse_args()

    section("USB")
    usb = sh("lsusb")
    print(usb)
    if not any(i in usb for i in MODEM_IDS):
        print(f"!! no modem ({', '.join(MODEM_IDS)}) — OTG cable in the Zero's USB port? HAT powered?")
        return 1
    print(sh("ls -l /dev/ttyUSB* /dev/ttyACM* 2>&1"))
    print(sh("for d in /sys/bus/usb/devices/*:*; do "
             "[ -e $d/driver ] && echo \"$(basename $d) $(basename $(readlink $d/driver))\"; done"))

    section("Network interfaces")
    print(sh("ip -br addr"))
    print(sh("ip route"))

    port = find_at_port()
    section("AT port")
    if port is None:
        print("!! no port answered AT")
        return 1
    print(port.path)

    queries = ["ATI", "AT+CGMR", "AT+CPIN?", "AT+CICCID", "AT+CSQ", "AT+CREG?", "AT+CEREG?",
               "AT+COPS?", "AT+CPSI?", "AT+CGDCONT?", "AT+CGACT?", "AT+CGPADDR",
               "AT+CUSBCFG?", "AT+DIALMODE?"]
    if args.apn:
        section(f"Set APN {args.apn!r}")
        print(port.cmd(f'AT+CGDCONT=1,"IP","{args.apn}"'))
    section("Modem")
    for q in queries + args.at:
        print(f"> {q}\n{port.cmd(q, 10.0 if q.startswith('AT+COPS') else 3.0)}")
    port.close()

    section("Data over the modem (not Wi-Fi)")
    wlan = {"wlan0"}
    ifaces = [l.split()[0] for l in sh("ip -br link").splitlines()
              if l.split()[0] not in wlan | {"lo"} and not l.startswith("tailscale")]
    for ifc in ifaces:
        addr = sh(f"ip -4 -br addr show {ifc}")
        print(addr or f"{ifc}: no IPv4")
        if "." in addr:
            print(f"  curl via {ifc}:", sh(f"curl -s -m 20 --interface {ifc} https://ifconfig.me; echo"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
