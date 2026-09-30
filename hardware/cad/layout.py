"""Enclosure layout: clearance check, 1:1 drill templates, and data for the HTML view.

    python3 hardware/cad/layout.py            # report + templates + sync HTML
    python3 hardware/cad/layout.py 181 113 30 # the same with measured L W H (mm)

Everything comes from layout.json. Print the SVG templates at 100 % / actual size
and check the 50 mm bar with a ruler before you centre-punch anything.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
DATA = json.loads((HERE / "layout.json").read_text())


def ev(v, H):
    return float(eval(str(v), {"__builtins__": {}}, {"H": H})) if isinstance(v, str) else float(v)


def resolve(data, L, W, H, with_battery=False):
    parts, out = list(data["parts"]), {}
    if with_battery:
        parts.append(data["battery"])
    for p in sorted(parts, key=lambda p: "rel" in p):
        q = dict(p)
        q["z0"], q["z1"] = ev(p["z0"], H), ev(p["z1"], H)
        if "rel" in p:
            b = out[p["rel"]]
            q["x0"], q["y0"] = b["x0"] + p["dx"], b["y0"] + p["dy"]
            q["x1"], q["y1"] = q["x0"] + p["w"], q["y0"] + p["d"]
        elif p["shape"] == "cyl":
            r = p["dia"] / 2
            q["cx"] = p["x"] if p["ax"] == "left" else L - p["x"]
            q["cy"] = p["y"] if p["ay"] == "front" else W - p["y"]
            q["x0"], q["x1"], q["y0"], q["y1"] = q["cx"] - r, q["cx"] + r, q["cy"] - r, q["cy"] + r
        else:
            q["x0"] = p["x"] if p["ax"] == "left" else L - p["x"] - p["w"]
            q["y0"] = p["y"] if p["ay"] == "front" else W - p["y"] - p["d"]
            q["x1"], q["y1"] = q["x0"] + p["w"], q["y0"] + p["d"]
        if "cx" not in q:
            q["cx"], q["cy"] = (q["x0"] + q["x1"]) / 2, (q["y0"] + q["y1"]) / 2
        out[p["id"]] = q
    bd = data["bosses"]["dia"]
    for i, (hx, ox, hy, oy) in enumerate(data["bosses"]["at"]):
        cx = {"left": ox, "right": L - ox, "mid": L / 2}[hx]
        cy = oy if hy == "front" else W - oy
        out[f"boss{i}"] = {"id": f"boss{i}", "label": "boss", "shape": "cyl", "group": "boss", "dia": bd,
                           "cx": cx, "cy": cy, "x0": cx - bd / 2, "x1": cx + bd / 2,
                           "y0": cy - bd / 2, "y1": cy + bd / 2, "z0": 0, "z1": H}
    return out


def xy_gap(a, b):
    """Horizontal clearance between two footprints; negative means they overlap."""
    if a["shape"] == "cyl" and b["shape"] == "cyl":
        return math.dist((a["cx"], a["cy"]), (b["cx"], b["cy"])) - a["dia"] / 2 - b["dia"] / 2
    if a["shape"] == "cyl" or b["shape"] == "cyl":
        c, r = (a, b) if a["shape"] == "cyl" else (b, a)
        dx = max(r["x0"] - c["cx"], 0, c["cx"] - r["x1"])
        dy = max(r["y0"] - c["cy"], 0, c["cy"] - r["y1"])
        inside = dx == 0 and dy == 0
        return -c["dia"] / 2 if inside else math.hypot(dx, dy) - c["dia"] / 2
    dx = max(b["x0"] - a["x1"], a["x0"] - b["x1"])
    dy = max(b["y0"] - a["y1"], a["y0"] - b["y1"])
    if dx > 0 and dy > 0:
        return math.hypot(dx, dy)
    return max(dx, dy)


def related(a, b):
    if a.get("asm") and a.get("asm") == b.get("asm"):
        return True
    ids = {a["id"], b["id"]}
    for p in (a, b):
        if p.get("part_of") in ids or p.get("rel") in ids:
            return True
    return a["group"] == "boss" and b["group"] == "boss"


def check(parts, L, W, H):
    items, issues, gaps = list(parts.values()), [], []
    for i, a in enumerate(items):
        if a["group"] != "boss" and (a["x0"] < -0.01 or a["y0"] < -0.01 or a["x1"] > L + 0.01 or a["y1"] > W + 0.01):
            issues.append(f"{a['id']} pokes through a wall")
        for b in items[i + 1:]:
            if related(a, b):
                continue
            dz = min(a["z1"], b["z1"]) - max(a["z0"], b["z0"])
            if dz <= 0.01:
                continue
            g = xy_gap(a, b)
            if g < -0.01:
                issues.append(f"{a['id']} collides with {b['id']} ({-g:.1f} mm)")
            else:
                gaps.append((g, a["id"], b["id"]))
    gaps.sort()
    stack_top = max(p["z1"] for p in parts.values() if p.get("asm") == "stack")
    return issues, gaps, {"above the stack": H - stack_top,
                          "under the buttons": parts["rec"]["z0"],
                          "foam block": parts["foam"]["z1"] - parts["foam"]["z0"]}


def grille(c, hole):
    pts, p = [(0.0, 0.0)], hole["pitch"]
    for ring in range(1, hole["rings"] + 1):
        for k in range(6):
            a0, a1 = math.radians(60 * k), math.radians(60 * (k + 1))
            for s in range(ring):
                t = s / ring
                x = ring * p * ((1 - t) * math.cos(a0) + t * math.cos(a1))
                y = ring * p * ((1 - t) * math.sin(a0) + t * math.sin(a1))
                pts.append((x, y))
    return [(c[0] + x, c[1] + y) for x, y in pts]


def holes(parts, data, L, W, H):
    OL, OW, _ = data["box"]["outer"]
    ox, oy = (OL - L) / 2, (OW - W) / 2
    out = []
    for p in parts.values():
        h = p.get("hole")
        if not h:
            continue
        X, Y = p["cx"] + ox, p["cy"] + oy
        if h["face"] == "top":
            out.append({"part": p["id"], "label": p["label"], "face": "top", "X": X, "Y": Y, **h,
                        "points": grille((X, Y), h) if h["kind"] == "grille" else [(X, Y)]})
        else:
            u, v = OL - X, H - (p["z0"] + p["z1"]) / 2  # down from the rim
            out.append({"part": p["id"], "label": p["label"], "face": "back", "U": u, "V": v, **h})
    return out


def svg_page(title, w_face, h_face, body, note):
    pad_x, pad_top, pad_bot = 12, 22, 30
    W_, H_ = w_face + 2 * pad_x, h_face + pad_top + pad_bot
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W_}mm" height="{H_}mm" viewBox="0 0 {W_} {H_}" '
            f'font-family="Helvetica, Arial, sans-serif">\n'
            f'<rect x="0" y="0" width="{W_}" height="{H_}" fill="white"/>\n'
            f'<text x="{pad_x}" y="8" font-size="4.2" font-weight="bold">{title}</text>\n'
            f'<text x="{pad_x}" y="13.5" font-size="2.8">{note}</text>\n'
            f'<g transform="translate({pad_x},{pad_top})">{body}</g>\n'
            f'<g transform="translate({pad_x},{H_ - 12})"><rect x="0" y="0" width="50" height="3" fill="black"/>'
            f'<text x="0" y="8" font-size="2.8">50 mm - print at 100 % (actual size) and measure this bar first</text></g>\n'
            f'</svg>\n')


def cross(x, y, r, label=None, sub=None):
    s = (f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="none" stroke="black" stroke-width="0.25"/>'
         f'<line x1="{x - r - 3:.2f}" y1="{y:.2f}" x2="{x + r + 3:.2f}" y2="{y:.2f}" stroke="black" stroke-width="0.15"/>'
         f'<line x1="{x:.2f}" y1="{y - r - 3:.2f}" x2="{x:.2f}" y2="{y + r + 3:.2f}" stroke="black" stroke-width="0.15"/>')
    if label:
        s += f'<text x="{x + r + 1.5:.2f}" y="{y - r - 0.5:.2f}" font-size="2.6" font-weight="bold">{label}</text>'
    if sub:
        s += f'<text x="{x + r + 1.5:.2f}" y="{y - r + 2.8:.2f}" font-size="2.2">{sub}</text>'
    return s


def templates(parts, hs, data, L, W, H):
    OL, OW, _ = data["box"]["outer"]
    TH = data["box"]["tub_h"]
    ox, oy = (OL - L) / 2, (OW - W) / 2
    # Top face, seen from above, front edge at the bottom.
    b = f'<rect x="0" y="0" width="{OL}" height="{OW}" rx="4" fill="none" stroke="black" stroke-width="0.35"/>'
    b += f'<text x="{OL / 2}" y="{OW + 5}" font-size="3" text-anchor="middle">FRONT - the child\'s side</text>'
    b += f'<text x="{OL / 2}" y="-2" font-size="3" text-anchor="middle">back</text>'
    for h in (h for h in hs if h["face"] == "top"):
        if h["kind"] == "grille":
            for x, y in h["points"]:
                b += cross(x, OW - y, h["dia"] / 2)
            X, Y = h["X"], OW - h["Y"]
            b += (f'<text x="{X + 20:.1f}" y="{Y - 16:.1f}" font-size="2.6" font-weight="bold">Speaker grille</text>'
                  f'<text x="{X + 20:.1f}" y="{Y - 12.8:.1f}" font-size="2.2">{len(h["points"])} x Ø{h["dia"]:g}, pitch {h["pitch"]:g}</text>'
                  f'<text x="{X + 20:.1f}" y="{Y - 9.8:.1f}" font-size="2.2">centre X {h["X"]:.1f} Y {h["Y"]:.1f}</text>')
        else:
            b += cross(h["X"], OW - h["Y"], h["dia"] / 2, f'{h["label"]} Ø{h["dia"]:g}', f'X {h["X"]:.1f}  Y {h["Y"]:.1f}')
    top = svg_page("DadBox - top face (the lid), outside view, 1:1", OL, OW, b,
                   "X from the LEFT edge, Y from the FRONT edge, both outside. Centre-punch, pilot 2 mm, then open up.")
    # Back wall, seen from behind: its left end is the box's right end.
    b = f'<rect x="0" y="0" width="{OL}" height="{TH}" rx="2" fill="none" stroke="black" stroke-width="0.35"/>'
    b += f'<text x="{OL / 2}" y="-2" font-size="3" text-anchor="middle">top edge = rim, the lid sits on it</text>'
    for h in (h for h in hs if h["face"] == "back"):
        r = (h["dia"] or 14) / 2
        b += cross(h["U"], h["V"], r, h["label"] + (f' Ø{h["dia"]:g}' if h["dia"] else " - per socket"),
                   f'{h["U"]:.1f} from left end, {h["V"]:.1f} down')
    back = svg_page("DadBox - back wall, seen from behind, 1:1", OL, TH, b,
                    "Measured from the LEFT end as you look at the back, and down from the rim.")
    # Tub floor, seen from above through the open top.
    b = f'<rect x="0" y="0" width="{OL}" height="{OW}" rx="4" fill="none" stroke="black" stroke-width="0.35"/>'
    b += f'<rect x="{ox}" y="{oy}" width="{L}" height="{W}" fill="none" stroke="black" stroke-width="0.15" stroke-dasharray="1.5 1"/>'
    b += f'<text x="{OL / 2}" y="{OW + 5}" font-size="3" text-anchor="middle">FRONT</text>'
    for pid, txt in (("hat", "Modem HAT - mark its 4 holes through the board, drill 2.7 mm"),
                     ("amp", "Amp - foam tape"), ("foam", "Foam block")):
        p = parts[pid]
        x, y, w, d = p["x0"] + ox, OW - (p["y1"] + oy), p["x1"] - p["x0"], p["y1"] - p["y0"]
        b += (f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{d:.2f}" fill="none" stroke="black" stroke-width="0.3"/>'
              f'<text x="{x + 2:.2f}" y="{y + 4:.2f}" font-size="2.4">{txt}</text>')
    for fx, fy in ((12, 12), (OL - 12, 12), (12, OW - 12), (OL - 12, OW - 12)):
        b += f'<circle cx="{fx}" cy="{fy}" r="5" fill="none" stroke="black" stroke-width="0.2" stroke-dasharray="1 1"/>'
    b += f'<text x="12" y="{OW - 19}" font-size="2.2">rubber feet go underneath, at the corners</text>'
    base = svg_page("DadBox - tub floor, seen from above, 1:1", OL, OW, b,
                    "Dashed = inside walls. Trim to the dashed line, lay it in the tub, place the parts, mark, then drill from inside.")
    return {"template-top-face.svg": top, "template-back-wall.svg": back, "template-tub-floor.svg": base}


def main():
    L, W, H = (float(a) for a in sys.argv[1:4]) if len(sys.argv) >= 4 else DATA["box"]["inner"]
    parts = resolve(DATA, L, W, H)
    issues, gaps, clear = check(parts, L, W, H)
    print(f"Inside {L:g} x {W:g} x {H:g} mm")
    for k, v in clear.items():
        print(f"  {k:<18} {v:5.1f} mm")
    print("  collisions:       ", "none" if not issues else "")
    for s in issues:
        print("    -", s)
    print("  tightest gaps:")
    for g, a, b in gaps[:5]:
        print(f"    {g:5.1f} mm  {a} / {b}")
    bat_issues, _, _ = check(resolve(DATA, L, W, H, with_battery=True), L, W, H)
    print(f"  with the deferred UPS module: {len(bat_issues) - len(issues)} more collisions")
    hs = holes(parts, DATA, L, W, H)
    for name, svg in templates(parts, hs, DATA, L, W, H).items():
        (HERE / name).write_text(svg)
    html = HERE / "enclosure-layout.html"
    if html.exists():
        t = html.read_text()
        t2 = re.sub(r'(<script id="layout-data" type="application/json">)(.*?)(</script>)',
                    lambda m: m.group(1) + json.dumps(DATA, separators=(",", ":")) + m.group(3), t, flags=re.S)
        html.write_text(t2)
    print("wrote", ", ".join(templates(parts, hs, DATA, L, W, H)))
    for h in hs:
        if h["face"] == "top":
            n = len(h["points"])
            print(f"  top   {h['label']:<8} X {h['X']:6.1f}  Y {h['Y']:6.1f}  Ø{h['dia']:g}{' x ' + str(n) if n > 1 else ''}  {h['drill']}")
        else:
            print(f"  back  {h['label']:<8} U {h['U']:6.1f}  down {h['V']:5.1f}  Ø{h['dia'] or '?'}  {h['drill']}")


if __name__ == "__main__":
    main()
