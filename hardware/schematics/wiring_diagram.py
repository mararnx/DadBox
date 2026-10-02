"""Draw the wiring map: every header pin, every wire, every part.

    python3 hardware/schematics/wiring_diagram.py

writes hardware/schematics/wiring-diagram.html. The data below is copied
from WIRING.md, which stays the authority: change that file first, then
this one, then box/dadbox/hw/pi.py.
"""
from __future__ import annotations

import html
import itertools
import random
from pathlib import Path

OUT = Path(__file__).with_name("wiring-diagram.html")

# ---- the header ------------------------------------------------------------

PIN_NAME = {
    1: "3V3", 2: "5V", 3: "GPIO 2 · SDA", 4: "5V", 5: "GPIO 3 · SCL", 6: "GND",
    7: "GPIO 4", 8: "GPIO 14 · TXD", 9: "GND", 10: "GPIO 15 · RXD", 11: "GPIO 17",
    12: "GPIO 18 · BCLK", 13: "GPIO 27", 14: "GND", 15: "GPIO 22", 16: "GPIO 23",
    17: "3V3", 18: "GPIO 24", 19: "GPIO 10", 20: "GND", 21: "GPIO 9", 22: "GPIO 25",
    23: "GPIO 11", 24: "GPIO 8", 25: "GND", 26: "GPIO 7", 27: "ID_SD", 28: "ID_SC",
    29: "GPIO 5", 30: "GND", 31: "GPIO 6", 32: "GPIO 12", 33: "GPIO 13", 34: "GND",
    35: "GPIO 19 · LRCLK", 36: "GPIO 16", 37: "GPIO 26", 38: "GPIO 20 · DIN",
    39: "GND", 40: "GPIO 21 · DOUT",
}

X_ODD, X_EVEN = 900, 940          # the two pin columns; odd = inner row
ROW0, PITCH = 240, 40             # pin 1/2 row, row pitch
BOARD = (780, 170, 1060, 1080)    # x0, y0, x1, y1
L_EDGE, R_EDGE = 470, 1400        # where left parts' pads / right parts' pads sit
L_CH, R_CH = (522, 750), (1086, 1368)   # channel bands for the routed wires




def pin_xy(p: int) -> tuple[int, int]:
    r = (p - 1) // 2
    return (X_ODD if p % 2 else X_EVEN), ROW0 + r * PITCH


# ---- the parts -------------------------------------------------------------
# pads: (key, name, note). A part's pads sit on the edge facing the header.

PARTS = {
    "mic": dict(side="L", y0=130, title="I²S MEMS microphone", sub="DFRobot · MSM261S4030H0 · 3.3 V",
                pads=[("SCK", "SCK", "chained from amp BCLK"), ("WS", "WS", "chained from amp LRC"),
                      ("SD", "SD", "pin 38 · GPIO 20"), ("GND", "GND", "pin 9"),
                      ("LR", "L/R", "jumper to GND · left"), ("VDD", "VDD", "from record R tab")]),
    "record": dict(side="L", y0=400, title="Record button", sub="16 mm RGB ring · common cathode",
                   pads=[("R", "R", "pin 11 · GPIO 17"), ("G", "G", "pin 13 · GPIO 27"),
                         ("B", "B", "pin 15 · GPIO 22"), ("NO", "gold", "pin 29 · GPIO 5"),
                         ("C", "gold", "pin 30 · GND"), ("K", "C−", "link to gold")]),
    "modem": dict(side="L", y0=674, h=236, title="Modem HAT", sub="Waveshare SIM7670G · under the Zero (ADR 0023)",
                  pads=[("USB", "USB-C", "data → Zero USB"), ("HDR", "2×20", "pin for pin, under the Zero")]),
    "psu": dict(side="L", y0=950, h=96, title="5 V 2.5 A supply", sub="mains · the off switch is the plug",
                pads=[("OUT", "plug", "micro-USB → PWR IN")]),
    "amp": dict(side="R", y0=130, w=300, title="Amplifier", sub="Adafruit MAX98357A · 5 V",
                pads=[("BCLK", "BCLK", "pin 12 · GPIO 18"), ("LRC", "LRC", "pin 35 · GPIO 19"),
                      ("DIN", "DIN", "pin 40 · GPIO 21"), ("SD", "SD", "pin 36 · GPIO 16"),
                      ("GAIN", "GAIN", "open · 9 dB"), ("GND", "GND", "pin 39"),
                      ("VIN", "Vin", "pin 2 · 5 V")]),
    "debug": dict(side="R", y0=410, title="Debug probe", sub="USB-UART · bench only · 115 200 baud",
                  pads=[("TX", "TX", "orange → pin 10"), ("RX", "RX", "yellow ← pin 8"),
                        ("GND", "GND", "black → pin 14")]),
    "play": dict(side="R", y0=580, title="Play button", sub="16 mm RGB ring · common cathode",
                 pads=[("R", "R", "pin 16 · GPIO 23"), ("G", "G", "pin 18 · GPIO 24"),
                       ("B", "B", "pin 22 · GPIO 25"), ("NO", "gold", "pin 31 · GPIO 6"),
                       ("C", "gold", "pin 20 · GND"), ("K", "C−", "link to gold")]),
}
PAD_DY, PAD_TOP = 26, 60
W_DEFAULT = 360


def part_box(k):
    p = PARTS[k]
    w = p.get("w", W_DEFAULT)
    h = p.get("h", PAD_TOP + len(p["pads"]) * PAD_DY + 4)
    x0 = L_EDGE - w if p["side"] == "L" else R_EDGE
    return x0, p["y0"], w, h


def pad_xy(k, key):
    p = PARTS[k]
    i = [q[0] for q in p["pads"]].index(key)
    return (L_EDGE if p["side"] == "L" else R_EDGE), p["y0"] + PAD_TOP + i * PAD_DY


# ---- the wires -------------------------------------------------------------
# (pin, part, pad, wire colour, what it is). The colours are the ten in the ribbon
# cable in hand (photo, 2026-09-30): red = 5 V, black = ground everywhere; both
# buttons are wired alike (R orange, G green, B blue, switch white, ground black);
# the I²S clocks keep their colour through the chain to the mic.

WIRES = [
    (9, "mic", "GND", "black", "GND"),
    (38, "mic", "SD", "brown", "I²S data in (mic → Pi)"),
    (11, "record", "R", "orange", "GPIO 17 · red ring, mic power"),
    (13, "record", "G", "green", "green ring"),
    (15, "record", "B", "blue", "blue ring"),
    (29, "record", "NO", "white", "switch · pull-up, pressed = low"),
    (30, "record", "C", "black", "GND · switch C and LED −"),
    (2, "amp", "VIN", "red", "5 V"),
    (12, "amp", "BCLK", "yellow", "I²S bit clock"),
    (35, "amp", "LRC", "purple", "I²S word clock"),
    (40, "amp", "DIN", "green", "I²S data out (Pi → amp)"),
    (36, "amp", "SD", "grey", "amp enable · owned by the sound driver"),
    (39, "amp", "GND", "black", "GND"),
    (8, "debug", "RX", "yellow", "Pi TXD → probe RX"),
    (10, "debug", "TX", "orange", "probe TX → Pi RXD"),
    (14, "debug", "GND", "black", "GND"),
    (16, "play", "R", "orange", "red ring"),
    (18, "play", "G", "green", "green ring"),
    (22, "play", "B", "blue", "blue ring"),
    (31, "play", "NO", "white", "switch · pull-up, pressed = low"),
    (20, "play", "C", "black", "GND · switch C and LED −"),
]
# wires that must cross the header to reach their side, and the gap they use
GAP = {30: +1, 38: +1, 31: +1, 33: +1, 35: +1, 39: +1}


# The modem HAT sits under the Zero, joined pin for pin by a 2×20 header (ADR 0023).
# From its schematic it uses only these; every other pin ends at the header on the HAT.
HAT_PINS = {2: "5 V", 4: "5 V", 6: "GND", 7: "P4 · power key"}


def start_of(pin):
    """Where the wire leaves the header on its own side: (x, y, lead-in points)."""
    x, y = pin_xy(pin)
    if pin in GAP:
        gy = y + GAP[pin] * PITCH // 2
        return [(x, y), (x, gy)], gy
    return [(x, y)], y


def route(side, pts_start, ys, cx, tx, ty):
    pts = list(pts_start)
    if ys == ty:
        pts.append((tx, ty))
    else:
        pts += [(cx, ys), (cx, ty), (tx, ty)]
    return pts


def crossings(ws, chans, side):
    """Count crossings of orthogonal wires (start y, terminal y) given channel x's."""
    n = 0
    far = (lambda a, b: a < b) if side == "L" else (lambda a, b: a > b)  # a is further from the header
    for i, j in itertools.permutations(range(len(ws)), 2):
        (ysa, yta), (ysb, ytb) = ws[i], ws[j]
        ca, cb = chans[i], chans[j]
        lo, hi = sorted((ysa, yta))
        if lo == hi:
            continue
        # A's vertical vs B's start run (header → cb): crosses if cb is further out than ca
        if far(cb, ca) and lo < ysb < hi:
            n += 1
        # A's vertical vs B's end run (cb → part): crosses if cb is nearer the header than ca
        if far(ca, cb) and lo < ytb < hi:
            n += 1
    return n


def assign_channels(side):
    ws = [w for w in WIRES if PARTS[w[1]]["side"] == side]
    spans = []
    for pin, part, pad, *_ in ws:
        _, ys = start_of(pin)
        spans.append((ys, pad_xy(part, pad)[1]))
    a, b = L_CH if side == "L" else R_CH
    slots = [round(a + (b - a) * i / (len(ws) - 1)) for i in range(len(ws))]
    rng = random.Random(7)
    best, best_n = None, 10**9
    for _ in range(60):
        order = slots[:]
        rng.shuffle(order)
        n = crossings(spans, order, side)
        improved = True
        while improved:
            improved = False
            for i, j in itertools.combinations(range(len(order)), 2):
                order[i], order[j] = order[j], order[i]
                m = crossings(spans, order, side)
                if m < n:
                    n, improved = m, True
                else:
                    order[i], order[j] = order[j], order[i]
        if n < best_n:
            best, best_n = order[:], n
    return {w[0]: c for w, c in zip(ws, best)}, best_n


# ---- SVG helpers -----------------------------------------------------------

def rounded(pts, r=7):
    pts = [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]
    d = f"M{pts[0][0]},{pts[0][1]}"
    for i in range(1, len(pts) - 1):
        (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[i + 1]
        l1 = max(abs(x1 - x0), abs(y1 - y0))
        l2 = max(abs(x2 - x1), abs(y2 - y1))
        rr = min(r, l1 / 2, l2 / 2)
        sx = (x1 - x0) / l1 if l1 else 0
        sy = (y1 - y0) / l1 if l1 else 0
        ex = (x2 - x1) / l2 if l2 else 0
        ey = (y2 - y1) / l2 if l2 else 0
        d += f" L{x1 - sx * rr:g},{y1 - sy * rr:g} Q{x1},{y1} {x1 + ex * rr:g},{y1 + ey * rr:g}"
    d += f" L{pts[-1][0]},{pts[-1][1]}"
    return d


def esc(s):
    return html.escape(str(s), quote=True)


def wire(d, color, parts, title, cls="", width=3.2):
    return (f'<g class="w {cls}" data-p="{" ".join(parts)}"><title>{esc(title)}</title>'
            f'<path class="halo" d="{d}"/>'
            f'<path class="edge" d="{d}" style="stroke-width:{width + 2}"/>'
            f'<path class="core" d="{d}" style="stroke:var(--w-{color});stroke-width:{width}"/></g>')


def text(x, y, s, cls="", anchor="start", extra=""):
    return f'<text x="{x}" y="{y}" class="{cls}" text-anchor="{anchor}" {extra}>{esc(s)}</text>'


# ---- build ----------------------------------------------------------------

def build_svg():
    W, H = 1860, 1110
    wires_svg, parts_svg, header_svg, labels_svg, notes = [], [], [], [], []
    chans = {}
    report = {}
    for side in "LR":
        c, n = assign_channels(side)
        chans.update(c)
        report[side] = n

    used = {w[0]: w for w in WIRES}

    # -- cables that aren't header wires (drawn first, under everything) --
    bx0, by0, bx1, by1 = BOARD
    usb_y = pad_xy("modem", "USB")[1]
    pwr_y = usb_y + 40
    psu_y = pad_xy("psu", "OUT")[1]
    wires_svg.append(wire(rounded([(L_EDGE, usb_y), (bx0 - 12, usb_y)]), "cable", ["modem"],
                          "USB data: Zero inner micro-USB → HAT USB-C, short lead", "cable", 7))
    wires_svg.append(wire(rounded([(L_EDGE, psu_y), (bx0 - 22, psu_y), (bx0 - 22, pwr_y), (bx0 - 12, pwr_y)]),
                          "cable", ["psu"], "5 V supply → Zero outer micro-USB, PWR IN", "cable", 7))
    notes.append(text(L_EDGE + 70, usb_y - 9, "micro-USB → USB-C lead", "cap"))
    hdr_y = pad_xy("modem", "HDR")[1]
    wires_svg.append(f'<g class="w stack" data-p="modem"><title>Stacked 2×20 header: Zero pin N on HAT pin N, all 40</title>'
                     f'<path class="stackline" d="M{L_EDGE},{hdr_y} H{bx0}"/></g>')
    notes.append(text(L_EDGE + 70, hdr_y + 16, "stacked header: pin N ↔ HAT pin N", "cap"))
    notes.append(text(L_EDGE + 70, psu_y - 9, "micro-USB plug", "cap"))

    # -- the header wires --
    for pin, part, pad, color, what in WIRES:
        side = PARTS[part]["side"]
        lead, ys = start_of(pin)
        tx, ty = pad_xy(part, pad)
        pts = route(side, lead, ys, chans[pin], tx, ty)
        cls = "bench" if part == "debug" else ""
        title = f"{color} wire · pin {pin} · {PIN_NAME[pin]} → {PARTS[part]['title']} {pad}: {what}"
        wires_svg.append(wire(rounded(pts), color, [part], title, cls))

    # -- chains at the parts --
    rx, ry = pad_xy("record", "R")
    vx, vy = pad_xy("mic", "VDD")
    wires_svg.append(wire(rounded([(rx, ry), (rx + 16, ry), (rx + 16, vy), (vx, vy)]), "orange",
                          ["mic", "record"], "Chain: record R tab → mic VDD (GPIO 17 through the red LED's tab)", "chain"))
    for key, mkey, color, top, xr, xl in (("BCLK", "SCK", "yellow", 100, 1394, 488),
                                          ("LRC", "WS", "purple", 114, 1386, 498)):
        ax, ay = pad_xy("amp", key)
        mx, my = pad_xy("mic", mkey)
        pts = [(ax, ay), (xr, ay), (xr, top), (xl, top), (xl, my), (mx, my)]
        wires_svg.append(wire(rounded(pts), color, ["mic", "amp"],
                              f"Chain: amp {key} → mic {mkey}", "chain"))
    # jumpers at the parts
    for part in ("record", "play"):
        x, y1 = pad_xy(part, "C")
        _, y2 = pad_xy(part, "K")
        dx = 12 if PARTS[part]["side"] == "L" else -12
        wires_svg.append(wire(rounded([(x, y1), (x + dx, y1), (x + dx, y2), (x, y2)], 4), "black", [part],
                              f"{PARTS[part]['title']}: C− linked to a gold switch tab at the button", "jumper", 2.4))
    x, y1 = pad_xy("mic", "GND")
    _, y2 = pad_xy("mic", "LR")
    wires_svg.append(wire(rounded([(x, y1), (x + 12, y1), (x + 12, y2), (x, y2)], 4), "black", ["mic"],
                          "Mic: L/R tied to GND at the mic (left channel)", "jumper", 2.4))

    # -- the board and header --
    header_svg.append(f'<rect class="pcb" x="{bx0}" y="{by0}" width="{bx1 - bx0}" height="{by1 - by0}" rx="14"/>')
    for hx, hy in ((bx0 + 16, by0 + 16), (bx1 - 16, by0 + 16), (bx0 + 16, by1 - 16), (bx1 - 16, by1 - 16)):
        header_svg.append(f'<circle class="hole" cx="{hx}" cy="{hy}" r="7"/>')
    header_svg.append(f'<rect class="sd" x="{(bx0 + bx1) / 2 - 36}" y="{by0 - 8}" width="72" height="22" rx="3"/>')
    header_svg.append(text((bx0 + bx1) / 2, by0 + 34, "SD card end · pin 1 here", "silk", "middle"))
    header_svg.append(text((bx0 + bx1) / 2, by1 - 36, "Raspberry Pi Zero 2 W", "silk strong", "middle"))
    header_svg.append(text((bx0 + bx1) / 2, by1 - 20, "header drawn enlarged", "silk", "middle"))
    for y, lab in ((usb_y, "USB"), (pwr_y, "PWR IN")):
        header_svg.append(f'<rect class="port" x="{bx0 - 12}" y="{y - 9}" width="22" height="18" rx="2"/>')
        labels_svg.append(text(bx0 + 16, y + 4, lab, "silk lab"))
    header_svg.append(f'<rect class="housing" x="{X_ODD - 18}" y="{ROW0 - 20}" width="{X_EVEN - X_ODD + 36}" '
                      f'height="{19 * PITCH + 40}" rx="4"/>')
    for p in range(1, 41):
        x, y = pin_xy(p)
        u = p in used or p in HAT_PINS
        cls = "pin used" if u else "pin"
        if p in HAT_PINS:
            cls += " hat"
        owners = ([used[p][1]] if p in used else []) + (["modem"] if p in HAT_PINS else [])
        dp = f'data-p="{" ".join(owners)}"' if u else ""
        shape = (f'<rect x="{x - 9}" y="{y - 9}" width="18" height="18" rx="2"/>' if p == 1
                 else f'<circle cx="{x}" cy="{y}" r="9.5"/>')
        ring = f'<circle class="hatring" cx="{x}" cy="{y}" r="13.5"/>' if p in HAT_PINS else ""
        header_svg.append(f'<g class="{cls}" {dp}>{ring}{shape}{text(x, y + 3.5, p, "pnum", "middle")}</g>')
        lx = X_ODD - 22 if p % 2 else X_EVEN + 22
        labels_svg.append(text(lx, y - 6, PIN_NAME[p], "plab" + (" on" if u else ""),
                               "end" if p % 2 else "start", dp))

    # -- parts --
    for k, p in PARTS.items():
        x0, y0, w, h = part_box(k)
        left = p["side"] == "L"
        g = [f'<g class="part" data-p="{k}">',
             f'<rect class="box{" bench" if k == "debug" else ""}" x="{x0}" y="{y0}" width="{w}" height="{h}" rx="6"/>']
        tx = x0 + 16 if left else x0 + w - 16
        anchor = "start" if left else "end"
        g.append(text(tx if left else x0 + 16, y0 + 24, p["title"], "ptitle", "start"))
        g.append(text(tx if left else x0 + 16, y0 + 42, p["sub"], "psub", "start"))
        for key, name, note in p["pads"]:
            px, py = pad_xy(k, key)
            colour = PAD_COLOUR.get((k, key))
            if colour:
                note = f"{colour} · {note}"
            open_ = key == "GAIN"
            g.append(f'<circle class="pad{" open" if open_ else ""}" cx="{px}" cy="{py}" r="5.5"/>')
            if left:
                g.append(text(px - 14, py + 4, name, "padname", "end"))
                g.append(text(px - 70, py + 4, note, "padnote", "end"))
            else:
                g.append(text(px + 14, py + 4, name, "padname"))
                g.append(text(px + 70, py + 4, note, "padnote"))
        g.append("</g>")
        parts_svg.append("\n".join(g))

    parts_svg.append(illustrations())
    notes += labels_svg
    return W, H, "\n".join(wires_svg), "\n".join(parts_svg), "\n".join(header_svg), "\n".join(notes), report


def ring(cx, cy, r=26):
    """A 16 mm RGB-ring button seen from the front: three arcs, one per LED colour."""
    out = [f'<circle class="alu" cx="{cx}" cy="{cy}" r="{r + 7}"/>']
    import math
    for i, c in enumerate(("red", "green", "blue")):
        a0, a1 = math.radians(-90 + i * 120 + 6), math.radians(-90 + (i + 1) * 120 - 6)
        x0, y0 = cx + r * math.cos(a0), cy + r * math.sin(a0)
        x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
        out.append(f'<path d="M{x0:.1f},{y0:.1f} A{r},{r} 0 0 1 {x1:.1f},{y1:.1f}" '
                   f'style="stroke:var(--c-{c});stroke-width:5;fill:none;stroke-linecap:round"/>')
    out.append(f'<circle class="cap" cx="{cx}" cy="{cy}" r="{r - 7}"/>')
    return "".join(out)


def illustrations():
    g = []
    # buttons
    x0, y0, w, h = part_box("record")
    g.append(f'<g class="part" data-p="record">{ring(x0 + 52, y0 + 130)}'
             f'{text(x0 + 52, y0 + 186, "Ø16 mm", "cap", "middle")}</g>')
    x0, y0, w, h = part_box("play")
    g.append(f'<g class="part" data-p="play">{ring(x0 + w - 52, y0 + 130)}'
             f'{text(x0 + w - 52, y0 + 186, "Ø16 mm", "cap", "middle")}</g>')
    # mic: module with its port hole
    x0, y0, w, h = part_box("mic")
    g.append(f'<g class="part" data-p="mic"><rect class="alu" x="{x0 + 22}" y="{y0 + 74}" width="54" height="54" rx="4"/>'
             f'<circle class="cap" cx="{x0 + 49}" cy="{y0 + 101}" r="7"/>'
             f'{text(x0 + 49, y0 + 146, "powered only", "cap", "middle")}'
             f'{text(x0 + 49, y0 + 160, "while red is lit", "cap", "middle")}</g>')
    # amp → speaker
    x0, y0, w, h = part_box("amp")
    sx, sy = x0 + w + 80, y0 + 150
    g.append(f'<g class="part" data-p="amp">'
             f'<rect class="alu" x="{x0 + w - 30}" y="{y0 + 118}" width="22" height="40" rx="2"/>'
             f'{text(x0 + w - 36, y0 + 108, "screw terminal", "cap", "end")}'
             f'<path class="spk" d="M{sx - 28},{sy - 18} h16 l24,-22 v80 l-24,-22 h-16 z"/>'
             f'{text(sx, sy + 58, "Seeed 4 Ω", "cap", "middle")}{text(sx, sy + 72, "speaker", "cap", "middle")}</g>')
    for dy, lab, col in ((-8, "+", "red"), (8, "−", "black")):
        g.append(wire(rounded([(x0 + w - 8, y0 + 138 + dy), (sx - 28, y0 + 138 + dy)]), col, ["amp"],
                      f"Speaker {lab}", "", 2.6))
    # modem: antenna, DIP switches, SIM
    x0, y0, w, h = part_box("modem")
    ay = y0 + 200
    g.append(f'<g class="part" data-p="modem">'
             f'<path class="sym" d="M{x0},{ay} H{x0 - 44} V{ay - 44} M{x0 - 44},{ay - 44} l-10,-16 M{x0 - 44},{ay - 44} l10,-16 M{x0 - 44},{ay - 44} v-18"/>'
             f'{text(x0 - 44, ay + 20, "LTE", "cap", "middle")}'
             f'{text(x0 + 16, ay + 4, "IPEX1 → SMA through the wall", "cap")}</g>')
    dip = [("1", "TXD", False), ("2", "RXD", False), ("3", "PWR", True), ("4", "BOOT", False)]
    dx0, dy0 = x0 + 16, y0 + 172
    s = [f'<g class="part" data-p="modem">{text(dx0, dy0 - 8, "DIP switches", "cap")}']
    for i, (n, lab, on) in enumerate(dip):
        xx = dx0 + i * 44
        s.append(f'<rect class="dip" x="{xx}" y="{dy0}" width="14" height="22" rx="2"/>'
                 f'<rect class="dipk{" on" if on else ""}" x="{xx + 2}" y="{dy0 + (2 if on else 11)}" width="10" height="9" rx="1"/>'
                 f'{text(xx + 18, dy0 + 10, lab, "cap")}{text(xx + 18, dy0 + 21, "on" if on else "off", "cap" + (" hot" if on else ""))}')
    s.append("</g>")
    g.append("".join(s))
    # psu plug icon
    x0, y0, w, h = part_box("psu")
    g.append(f'<g class="part" data-p="psu"><rect class="alu" x="{x0 + 250}" y="{y0 + 58}" width="36" height="26" rx="4"/>'
             f'<path class="sym" d="M{x0 + 258},{y0 + 58} v-10 M{x0 + 278},{y0 + 58} v-10"/></g>')
    return "\n".join(g)


COLOURS = ["black", "brown", "red", "orange", "yellow", "green", "blue", "purple", "grey", "white"]
USES = {
    "black": "ground: mic, both buttons, amp; also the short jumpers at the parts",
    "brown": "mic data → pin 38",
    "red": "5 V → amp (the modem gets it through the stacked header)",
    "orange": "button red rings; record R tab → mic VDD",
    "yellow": "I²S bit clock: pin 12 → amp BCLK → mic SCK",
    "green": "button green rings; amp DIN",
    "blue": "button blue rings",
    "purple": "I²S word clock: pin 35 → amp LRC → mic WS",
    "grey": "amp SD",
    "white": "button switches",
}


# the colour arriving at each pad, for the pad labels
PAD_COLOUR = {(part, pad): colour for pin, part, pad, colour, what in WIRES}
PAD_COLOUR.update({("mic", "VDD"): "orange", ("mic", "SCK"): "yellow", ("mic", "WS"): "purple",
                   ("record", "K"): "black", ("play", "K"): "black", ("mic", "LR"): "black"})


def colour_counts():
    """Wires to cut per colour: header wires plus the chains (not jumpers, not the probe's own cable)."""
    n = {c: 0 for c in COLOURS}
    for pin, part, pad, colour, what in WIRES:
        if part != "debug":
            n[colour] += 1
    for c in ("orange", "yellow", "purple"):     # the three chains to the mic
        n[c] += 1
    return n


FILTERS = [("all", "Everything"), ("record", "Record button"), ("mic", "Microphone"),
           ("play", "Play button"), ("amp", "Amp + speaker"),
           ("modem", "Modem HAT"), ("psu", "Power"), ("debug", "Debug probe")]

CARDS = [
    ("record", "Record button", "16 mm, RGB ring, common cathode, resistors built in.",
     [("gold", "29 · GPIO 5", "switch; either gold tab. Input, internal pull-up; pressed = low"), ("other gold", "30 · GND", "one ground wire, linked to C− at the button"),
      ("R", "11 · GPIO 17", "<b>first</b> stop of GPIO 17; a second wire from this tab goes to the mic's VDD"),
      ("G", "13 · GPIO 27", ""), ("B", "15 · GPIO 22", ""), ("C−", "other gold", "LED common cathode, not the switch")]),
    ("mic", "Microphone", "DFRobot I²S MEMS (MSM261S4030H0). Labels vary: SCK/BCLK, WS/LRCL, SD/DATA, L/R/SEL.",
     [("VDD", "record R tab", "GPIO 17 through the red LED's tab. Never the 3.3 V pin, never straight to pin 11"),
      ("GND", "9", ""), ("SCK", "amp BCLK", "chained, not to the header"), ("WS", "amp LRC", "chained, not to the header"),
      ("SD", "38 · GPIO 20", "data out of the mic"), ("L/R", "GND", "jumper at the mic; left channel")]),
    ("play", "Play button", "Same part as the record button.",
     [("gold", "31 · GPIO 6", "switch; either gold tab. Pull-up; pressed = low"), ("other gold", "20 · GND", "linked to C− at the button"),
      ("R", "16 · GPIO 23", ""), ("G", "18 · GPIO 24", ""), ("B", "22 · GPIO 25", ""), ("C−", "other gold", "LED common cathode, not the switch")]),
    ("amp", "Amplifier and speaker", "Adafruit MAX98357A; Seeed 4 Ω speaker on the screw terminal.",
     [("Vin", "2 · 5 V", ""), ("GND", "39", ""), ("BCLK", "12 · GPIO 18", "and on to the mic's SCK"),
      ("LRC", "35 · GPIO 19", "and on to the mic's WS"), ("DIN", "40 · GPIO 21", "data into the amp"),
      ("SD", "36 · GPIO 16", "the sound driver raises it while audio plays; firmware never touches it"),
      ("GAIN", "—", "unconnected: 9 dB"), ("+ / −", "speaker", "screw terminal")]),
    ("modem", "Modem HAT", "Waveshare SIM7670G, under the Zero (ADR 0023). A straight 2×20 header soldered in from below joins pin N to pin N, all 40; no modem wires.",
     [("USB-C", "Zero inner micro-USB", "short micro-USB → USB-C lead; shows up as a network interface"),
      ("pins 2, 4 · 5 V", "same pins", "through the header"), ("GND", "every ground pin", "through the header"),
      ("pin 7 · P4", "pin 7 · GPIO 4", "power key: high turns on a transistor that pulls PWRKEY low. <code>gpio=4=op,dl</code> in config.txt holds it low through boot"),
      ("pins 8, 10", "TXD, RXD", "reach the HAT only through DIP 1 and 2, which stay off"),
      ("DIP", "", "1 TXD off · 2 RXD off · 3 PWR on · 4 BOOT off"),
      ("LTE", "antenna", "IPEX1 pigtail → SMA through the wall. Never transmit without it"),
      ("SIM", "", "insert before power; no hot-swap")]),
    ("psu", "Power", "Mains only for the first box; pulling the plug is how it turns off (ADR 0019).",
     [("5 V 2.5 A", "Zero outer micro-USB", "“PWR IN”"), ("5 V rail", "pins 2 and 4", "feeds the amp and the modem HAT"),
      ("later", "pins 3 and 5", "the UPS module's INA219 on I²C")]),
    ("debug", "Debug probe", "Bench only. Receive meets transmit. 115 200 baud, full UART, kernel console.",
     [("orange · TX", "10 · RXD", ""), ("yellow · RX", "8 · TXD", ""), ("black · GND", "14", "")]),
]


def cards_html():
    out = []
    for k, title, lede, rows in CARDS:
        trs = "".join(f"<tr><th>{esc(a)}</th><td class=\"mono\">{esc(b)}</td><td>{c}</td></tr>" for a, b, c in rows)
        out.append(f'<section class="card" data-p="{k}"><header><h3>{esc(title)}</h3>'
                   f'<button type="button" class="show" data-f="{k}">Show on map</button></header>'
                   f'<p class="lede">{esc(lede)}</p>'
                   f'<div class="tw"><table><thead><tr><th>Terminal</th><th>Goes to</th><th>Note</th></tr></thead>'
                   f'<tbody>{trs}</tbody></table></div></section>')
    return "\n".join(out)


def main():
    W, H, wires, parts, header, notes, report = build_svg()
    focus_css = "\n".join(
        f'#map[data-focus="{k}"] .w:not([data-p~="{k}"]),#map[data-focus="{k}"] .part:not([data-p~="{k}"]),'
        f'#map[data-focus="{k}"] .pin.used:not([data-p~="{k}"]),#map[data-focus="{k}"] .plab.on:not([data-p~="{k}"])'
        f'{{opacity:.1}}' for k, _ in FILTERS[1:])
    n = colour_counts()
    legend = "".join(f'<li><span class="sw" style="background:var(--w-{c})"></span><b>{c}</b> <span class="n">× {n[c]}</span>'
                     f'<span class="use">{esc(USES[c])}</span></li>' for c in COLOURS)
    filters = "".join(f'<button type="button" class="f{" on" if k == "all" else ""}" data-f="{k}" id="f-{k}">{esc(t)}</button>'
                      for k, t in FILTERS)
    page = TEMPLATE
    for key, val in dict(W=W, H=H, WIRES=wires, PARTS=parts, HEADER=header, NOTES=notes, FOCUS=focus_css,
                         LEGEND=legend, FILTERS=filters, CARDS=cards_html()).items():
        page = page.replace(f"%%{key}%%", str(val))
    OUT.write_text(page)
    print(f"wrote {OUT.name}; crossings left {report['L']}, right {report['R']}")


TEMPLATE = open(Path(__file__).with_name("wiring_template.html")).read()

if __name__ == "__main__":
    main()
