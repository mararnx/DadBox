"""Draws the site's pictures from the real box dimensions and splices them into index.html.

Positions come from hardware/LAYOUT.md and hardware/cad/layout.json (outside
coordinates, mm: x from the left edge, y from the front edge, z up).
Run: python3 site/drawings.py
"""
import math
import pathlib
import re

L, W, H = 188, 119, 37.5          # outside; the box stands on a long edge, the lid is its face
# Face coordinates, measured from the build photos (±3 mm): u from the left, v down from the top edge.
PLAY, REC = (36, 43), (36, 83)    # 16 mm holes, Ø21.8 flange; the lower one is Record ("R" scratched on the lid)
GRILLE = (91, 62)                 # 19 holes, hex
MIC = (91, 101)
SCREWS = [(7, 7), (L - 7, 7), (7, W - 7), (L - 7, W - 7), (L / 2, 6), (L / 2, W - 6)]
USB_U, ANT_U = 25, 48             # on the top edge, centred in its depth
INK = "#1d1b3a"


def grille_pts(c, pitch=5.4, rings=2):
    pts = [(0.0, 0.0)]
    for ring in range(1, rings + 1):
        for k in range(6):
            a0, a1 = math.radians(60 * k + 30), math.radians(60 * (k + 1) + 30)
            for s in range(ring):
                t = s / ring
                pts.append((ring * pitch * ((1 - t) * math.cos(a0) + t * math.cos(a1)),
                            ring * pitch * ((1 - t) * math.sin(a0) + t * math.sin(a1))))
    return [(c[0] + x, c[1] + y) for x, y in pts]


# ---------------------------------------------------------------- hero: the box standing, 3/4 view
EU, EV, ED = (2.0, 0.10), (0.0, 2.0), (0.82, -0.56)
OX, OY = 34, 268


def P(u, v, d):
    return (OX + u * EU[0] + v * EV[0] + d * ED[0], OY + u * EU[1] + v * EV[1] + d * ED[1])


def poly(pts, **attr):
    a = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attr.items())
    return f'<path d="M{" L".join(f"{x:.1f} {y:.1f}" for x, y in pts)} Z" {a}/>'


def face(d=0.0):
    ox, oy = P(0, 0, d)
    return f'matrix({EU[0]} {EU[1]} {EV[0]} {EV[1]} {ox:.2f} {oy:.2f})'


def topplane(h=0.0):
    ox, oy = P(0, 0, 0)
    return f'matrix({EU[0]} {EU[1]} {ED[0]} {ED[1]} {ox:.2f} {oy - h * EV[1]:.2f})'


NS = 'vector-effect="non-scaling-stroke"'


def button(c, ring, glow, cls):
    x, y = c
    return (f'<g transform="{face()}">'
            f'<circle class="{cls}" cx="{x}" cy="{y}" r="19" fill="url(#{glow})"/>'
            f'<circle cx="{x}" cy="{y}" r="10.9" fill="#e7e5e0" stroke="{INK}" stroke-width="1.4" {NS}/>'
            f'<circle cx="{x}" cy="{y}" r="9.4" fill="none" stroke="#a5a196" stroke-width="1" {NS}/></g>'
            f'<g transform="{face(-2.3)}">'
            f'<circle class="{cls}" cx="{x}" cy="{y}" r="7.7" fill="none" stroke="{ring}" stroke-width="3.4" {NS}/>'
            f'<circle cx="{x}" cy="{y}" r="6" fill="url(#steel)" stroke="{INK}" stroke-width="1.2" {NS}/>'
            f'<ellipse cx="{x - 1.6}" cy="{y - 1.8}" rx="2.8" ry="1.5" fill="#fff" opacity=".85"/></g>')


def cylinder(u, d, r, h, side, top, edge=INK):
    out = []
    for i in range(int(h * 2) + 1):
        out.append(f'<g transform="{topplane(i / 2)}"><circle cx="{u}" cy="{d}" r="{r}" fill="{side}"/></g>')
    out.append(f'<g transform="{topplane(h)}"><circle cx="{u}" cy="{d}" r="{r}" fill="{top}" stroke="{edge}" stroke-width="1.4" {NS}/></g>')
    return "".join(out)


def hero():
    s = ['<svg class="boxart" viewBox="0 0 500 540" role="img" aria-label="The DadBox as built: a die-cast aluminium box standing on its long edge, '
         'two stainless buttons with lit rings stacked on the left of the face (Play glowing green above, Record red below), a round speaker grille in the middle, '
         'a mic pinhole below it, six screws, and on the top edge a round USB-C socket and a black swivel LTE antenna">']
    s.append('<defs>'
             '<radialGradient id="hgG"><stop offset="0" stop-color="#8dffb0" stop-opacity="1"/><stop offset=".5" stop-color="#2fd16b" stop-opacity=".45"/><stop offset="1" stop-color="#2fd16b" stop-opacity="0"/></radialGradient>'
             '<radialGradient id="hgB"><stop offset="0" stop-color="#8fb0ff" stop-opacity=".45"/><stop offset=".5" stop-color="#3a6fc4" stop-opacity=".18"/><stop offset="1" stop-color="#3a6fc4" stop-opacity="0"/></radialGradient>'
             '<radialGradient id="steel" cx=".35" cy=".35"><stop offset="0" stop-color="#ffffff"/><stop offset=".6" stop-color="#d2d0ca"/><stop offset="1" stop-color="#8e8a82"/></radialGradient>'
             '<linearGradient id="faceG" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f1f0ec"/><stop offset=".45" stop-color="#d9d7d1"/><stop offset="1" stop-color="#bcb9b1"/></linearGradient>'
             '<linearGradient id="topG" x1="0" y1="1" x2="1" y2="0"><stop offset="0" stop-color="#e9e7e2"/><stop offset="1" stop-color="#c9c6be"/></linearGradient>'
             '<linearGradient id="sideG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#a9a59c"/><stop offset="1" stop-color="#85817a"/></linearGradient>'
             '<linearGradient id="antG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3b3a48"/><stop offset=".5" stop-color="#15141c"/><stop offset="1" stop-color="#2a2935"/></linearGradient>'
             '<filter id="soft" x="-20%" y="-20%" width="140%" height="160%"><feGaussianBlur stdDeviation="9"/></filter>'
             '</defs>')
    # floor shadow
    a, b = P(0, W, 0), P(L, W, H)
    s.append(f'<ellipse cx="{(a[0] + b[0]) / 2 + 10:.1f}" cy="{a[1] + 16:.1f}" rx="{(b[0] - a[0]) / 2 + 20:.1f}" ry="16" fill="#1d1b3a" opacity=".22" filter="url(#soft)"/>')
    # body
    s.append(poly([P(0, 0, 0), P(L, 0, 0), P(L, 0, H), P(0, 0, H)], fill="url(#topG)", stroke=INK, stroke_width=2.5, stroke_linejoin="round"))
    s.append(poly([P(L, 0, 0), P(L, W, 0), P(L, W, H), P(L, 0, H)], fill="url(#sideG)", stroke=INK, stroke_width=2.5, stroke_linejoin="round"))
    for p0, p1 in ((P(0, 0, 3), P(L, 0, 3)), (P(L, 0, 3), P(L, W, 3))):
        s.append(f'<path d="M{p0[0]:.1f} {p0[1]:.1f} L{p1[0]:.1f} {p1[1]:.1f}" stroke="{INK}" stroke-width="1" opacity=".45"/>')
    s.append(f'<g transform="{face()}"><rect x="0" y="0" width="{L}" height="{W}" rx="4" fill="url(#faceG)" stroke="{INK}" stroke-width="2.5" {NS}/>')
    for x, y in SCREWS:
        s.append(f'<circle cx="{x}" cy="{y}" r="2.5" fill="#f4f3ef" stroke="{INK}" stroke-width="1" {NS}/>'
                 f'<path d="M{x - 1.3} {y} L{x + 1.3} {y} M{x} {y - 1.3} L{x} {y + 1.3}" stroke="{INK}" stroke-width=".8" {NS}/>')
    for x, y in grille_pts(GRILLE):
        s.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="1.7" fill="#24222c"/>')
    s.append(f'<circle cx="{MIC[0]}" cy="{MIC[1]}" r="1.1" fill="#15141c"/></g>')
    s.append(button(PLAY, "#3cf07a", "hgG", "breathe"))
    s.append(button(REC, "#6f93d8", "hgB", ""))   # ready: steady dim blue
    # USB-C socket on the top edge
    s.append(cylinder(USB_U, H / 2, 12, 9, "#a6a39b", "#e2e0da"))
    s.append(f'<g transform="{topplane(9)}"><circle cx="{USB_U}" cy="{H / 2}" r="8" fill="#cfccc5" stroke="{INK}" stroke-width="1" {NS}/>'
             f'<rect x="{USB_U - 4.3}" y="{H / 2 - 1.6}" width="8.6" height="3.2" rx="1.6" fill="#15141c"/></g>')
    # antenna: knuckle, then the whip tilted to the right
    s.append(cylinder(ANT_U, H / 2, 5.5, 4, "#b8902f", "#d9b04a"))
    s.append(cylinder(ANT_U, H / 2 + 0.01, 4.6, 14, "#22212b", "#3a3946"))
    bx, by = P(ANT_U, 0, H / 2); by -= 14 * 2.0
    ang = math.radians(38); ln = 112 * 2.0
    tx, ty = bx + math.sin(ang) * ln, by - math.cos(ang) * ln
    nx, ny = math.cos(ang), math.sin(ang)
    w0, w1 = 6.5, 3.5
    s.append(f'<path class="whip" d="M{bx - nx * w0:.1f} {by - ny * w0:.1f} L{tx - nx * w1:.1f} {ty - ny * w1:.1f} '
             f'A{w1} {w1} 0 0 1 {tx + nx * w1:.1f} {ty + ny * w1:.1f} L{bx + nx * w0:.1f} {by + ny * w0:.1f} Z" fill="url(#antG)" stroke="{INK}" stroke-width="1.5"/>')
    s.append(f'<circle cx="{bx:.1f}" cy="{by:.1f}" r="7" fill="#2b2a35" stroke="{INK}" stroke-width="1.5"/>')
    s.append('</svg>')
    return "".join(s)


def face_plan():
    k = 2.6
    s = [f'<svg viewBox="-60 -40 {L * k + 150:.0f} {W * k + 100:.0f}" role="img" aria-label="Front face, 188 by 119 mm, as built (measured from photos, about plus or minus 3 mm): '
         f'Play button 36 mm from the left and 43 mm down, Record 36 mm from the left and 83 mm down, both 16 mm holes; speaker grille of 19 holes centred at 91, 62; '
         f'mic pinhole at 91, 101; six screws">', MARK]
    def X(u): return u * k
    def Y(v): return v * k
    s.append(f'<rect x="0" y="0" width="{L * k}" height="{W * k}" rx="10" {LINE} stroke-width="2.5" style="fill:var(--card)"/>')
    for x, y in SCREWS:
        s.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="6.5" {LINE} stroke-width="1.5"/><path d="M{X(x) - 4} {Y(y)} L{X(x) + 4} {Y(y)} M{X(x)} {Y(y) - 4} L{X(x)} {Y(y) + 4}" {LINE}/>')
    for (x, y), name, col in ((PLAY, "PLAY", "var(--led-green)"), (REC, "RECORD", "var(--led-red)")):
        s.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="{10.9 * k:.1f}" {LINE} stroke-dasharray="4 3" stroke-width="1"/>'
                 f'<circle cx="{X(x)}" cy="{Y(y)}" r="{8 * k:.1f}" stroke="{col}" stroke-width="3.5" fill="none"/>'
                 f'<path d="M{X(x) - 34} {Y(y)} L{X(x) + 34} {Y(y)} M{X(x)} {Y(y) - 34} L{X(x)} {Y(y) + 34}" {LINE} stroke-width=".8" stroke-dasharray="6 2 1 2"/>'
                 f'<text x="{X(x) + 36}" y="{Y(y) + 4}" font-size="12" font-weight="700" {T}>{name} Ø16</text>')
    for x, y in grille_pts(GRILLE):
        s.append(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="{1.7 * k:.1f}" style="fill:var(--ink)"/>')
    s.append(f'<text x="{X(GRILLE[0])}" y="{Y(GRILLE[1]) + 44}" text-anchor="middle" font-size="11" {T}>SPEAKER · 19 holes</text>')
    s.append(f'<circle cx="{X(MIC[0])}" cy="{Y(MIC[1])}" r="3.2" style="fill:var(--ink)"/>'
             f'<text x="{X(MIC[0]) + 10}" y="{Y(MIC[1]) + 4}" font-size="11" {T}>MIC Ø2</text>')
    s.append(dim_h(0, L, -18, "188", k))
    s.append(dim_v(-34, 0, W, "119", k))
    yb = W * k + 24
    s.append(dim_h(0, PLAY[0], yb, "≈36", k) + dim_h(PLAY[0], GRILLE[0], yb, "≈55", k))
    xr = L * k + 22
    for v0, v1, lab in ((0, PLAY[1], "≈43"), (PLAY[1], REC[1], "≈40")):
        s.append(f'<path d="M{xr} {Y(v0)} L{xr} {Y(v1)}" {DIM} marker-start="url(#da)" marker-end="url(#da)"/>'
                 f'<text x="{xr + 5}" y="{(Y(v0) + Y(v1)) / 2 + 4:.1f}" font-size="11" {T}>{lab}</text>')
    s.append(f'<text x="{L * k / 2}" y="{W * k + 54}" text-anchor="middle" font-size="12" font-weight="700" {T}>FRONT FACE (the lid) · as built, ±3 mm from photos</text>')
    s.append('</svg>')
    return "".join(s)


def top_edge():
    k = 2.6
    s = [f'<svg viewBox="-60 -50 {L * k + 120:.0f} {H * k + 120:.0f}" role="img" aria-label="Top edge seen from above, 188 by 37.5 mm: the USB-C power socket about 25 mm from the left '
         f'and the LTE antenna about 48 mm from the left, both centred in the depth">', MARK]
    s.append(f'<rect x="0" y="0" width="{L * k}" height="{H * k}" rx="6" {LINE} stroke-width="2.5" style="fill:var(--card)"/>')
    s.append(f'<path d="M0 {H * k - 3 * k} L{L * k} {H * k - 3 * k}" {LINE} stroke-width="1" stroke-dasharray="5 3"/>'
             f'<text x="{L * k - 6}" y="{H * k - 3 * k - 5}" text-anchor="end" font-size="10" {T} opacity=".7">lid (front)</text>')
    cy = H * k / 2
    s.append(f'<circle cx="{USB_U * k}" cy="{cy}" r="{12 * k}" stroke="var(--ink)" stroke-width="2" style="fill:var(--paper-2)"/>'
             f'<rect x="{USB_U * k - 4.3 * k:.1f}" y="{cy - 1.6 * k:.1f}" width="{8.6 * k:.1f}" height="{3.2 * k:.1f}" rx="{1.6 * k:.1f}" style="fill:var(--ink)"/>')
    hexpts = " ".join(f"{ANT_U * k + 5.5 * k * math.cos(math.radians(60 * i)):.1f},{cy + 5.5 * k * math.sin(math.radians(60 * i)):.1f}" for i in range(6))
    s.append(f'<polygon points="{hexpts}" stroke="var(--ink)" stroke-width="1.5" style="fill:var(--mustard)"/>'
             f'<circle cx="{ANT_U * k}" cy="{cy}" r="{4.4 * k:.1f}" stroke="var(--ink)" stroke-width="1.5" style="fill:#2b2a35"/>')
    s.append(f'<text x="{USB_U * k}" y="{H * k + 24}" text-anchor="middle" font-size="11" font-weight="700" {T}>5 V USB-C</text>'
             f'<text x="{ANT_U * k + 46}" y="{H * k + 24}" text-anchor="middle" font-size="11" font-weight="700" {T}>LTE ANTENNA (SMA)</text>')
    s.append(dim_h(0, USB_U, -14, "≈25", k) + dim_h(0, ANT_U, -32, "≈48", k))
    s.append(dim_v(-22, 0, H, "37.5", k))
    s.append(f'<text x="{L * k / 2 + 80}" y="{H * k + 54}" text-anchor="middle" font-size="12" font-weight="700" {T}>TOP EDGE · seen from above</text>')
    s.append('</svg>')
    return "".join(s)


# ---------------------------------------------------------------- technical drawings (theme-aware)
DIM = 'stroke="var(--rust)" stroke-width="1.2"'
LINE = 'stroke="var(--ink)" fill="none"'
T = 'font-family="JetBrains Mono, monospace" fill="var(--ink)"'


def dim_h(x1, x2, y, label, k):
    a, b = x1 * k, x2 * k
    return (f'<path d="M{a:.1f} {y} L{b:.1f} {y}" {DIM} marker-start="url(#da)" marker-end="url(#da)"/>'
            f'<text x="{(a + b) / 2:.1f}" y="{y - 5}" text-anchor="middle" font-size="11" {T}>{label}</text>')


def dim_v(x, y1, y2, label, k):
    a, b = y1 * k, y2 * k
    return (f'<path d="M{x} {a:.1f} L{x} {b:.1f}" {DIM} marker-start="url(#da)" marker-end="url(#da)"/>'
            f'<text x="{x - 6}" y="{(a + b) / 2 + 4:.1f}" text-anchor="end" font-size="11" {T}>{label}</text>')


MARK = ('<defs><marker id="da" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0 1 L9 5 L0 9" fill="none" stroke="var(--rust)" stroke-width="1.5"/></marker>'
        '<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        '<path d="M0 0 L0 6" stroke="var(--ink-soft)" stroke-width="1" opacity=".5"/></pattern></defs>')


def inside():
    k = 2.6
    o = 4   # wall: interior 180 × 112 sits 4 mm in
    Li, Wi = 180, 112
    s = [f'<svg viewBox="-20 -60 {L * k + 40:.0f} {W * k + 110:.0f}" role="img" aria-label="Inside the box, lid off, seen from the front, bottom edge at the bottom: '
         f'the Pi Zero 2 W stacked on the LTE modem HAT at the right, the speaker in the middle on a foam block, the amplifier in the lower left corner, '
         f'the two buttons and the mic hanging from the lid, the USB-C socket and antenna on the top edge">', MARK]
    def X(x): return (x + o) * k
    def Y(y): return (W - (y + o)) * k
    def box(x, y, w, d, fill, label, sub="", dash=False, tc="var(--ink)"):
        x0, y0 = X(x), Y(y + d)
        da = ' stroke-dasharray="6 4"' if dash else ""
        t = (f'<text x="{x0 + w * k / 2:.1f}" y="{y0 + d * k / 2:.1f}" text-anchor="middle" font-size="12" font-weight="600" {T} style="fill:{tc}">{label}</text>')
        if sub:
            t += f'<text x="{x0 + w * k / 2:.1f}" y="{y0 + d * k / 2 + 15:.1f}" text-anchor="middle" font-size="10" {T} style="fill:{tc}" opacity=".8">{sub}</text>'
        return f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w * k:.1f}" height="{d * k:.1f}" rx="3" stroke="var(--ink)" stroke-width="2"{da} style="fill:{fill}"/>' + t
    s.append(f'<rect x="0" y="0" width="{L * k}" height="{W * k}" rx="12" stroke="var(--ink)" stroke-width="2.5" style="fill:url(#hatch)"/>')
    s.append(f'<rect x="{o * k}" y="{o * k}" width="{Li * k}" height="{Wi * k}" rx="6" stroke="var(--ink)" stroke-width="1.5" style="fill:var(--paper)"/>')
    for bx, by in ((5, 5), (Li - 5, 5), (5, Wi - 5), (Li - 5, Wi - 5), (Li / 2, 4), (Li / 2, Wi - 4)):
        s.append(f'<circle cx="{X(bx)}" cy="{Y(by)}" r="{5 * k}" stroke="var(--ink)" stroke-width="1.2" style="fill:var(--paper-2)"/>')
    # HAT then Pi on top
    s.append(box(110, 22, 56.7, 85, "#2b6cb0", "", ""))
    s.append(f'<text x="{X(110) + 8:.1f}" y="{Y(22) - 8:.1f}" font-size="10" {T} style="fill:#f3e8cf">LTE HAT 85 × 57</text>')
    s.append(box(134, 32, 30, 65, "#2f9e5b", "Pi", "Zero 2 W", tc="#fff"))
    # header row along the Pi's edge
    for i in range(20):
        yy = Y(32 + 7 + i * 2.54)
        s.append(f'<rect x="{X(134 + 30 - 3.5):.1f}" y="{yy - 2:.1f}" width="4" height="4" fill="#d8b04a"/>')
    # the speaker sits under the grille, the buttons and mic hang from the lid (dashed); positions as built
    s.append(box(64.5 + 5, 28 + 5, 35, 40, "var(--paper-2)", "", "", dash=True))
    s.append(box(64.5, 28, 45, 50, "var(--mustard)", "SPEAKER", "on foam", tc="#1d1b3a"))
    s.append(f'<circle cx="{X(87)}" cy="{Y(53)}" r="{17 * k}" stroke="#1d1b3a" stroke-width="1.5" fill="none" opacity=".5"/>')
    s.append(box(8, 4, 18, 19, "var(--orange)", "AMP", "", tc="#1d1b3a"))
    for (x, y), name, col in (((32, 72), "PLAY", "var(--led-green)"), ((32, 32), "REC", "var(--led-red)")):
        s.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="{11 * k}" stroke="var(--ink)" stroke-width="2" stroke-dasharray="6 4" style="fill:var(--card)"/>'
                 f'<circle cx="{X(x)}" cy="{Y(y)}" r="{8 * k}" stroke="{col}" stroke-width="3" fill="none"/>'
                 f'<text x="{X(x)}" y="{Y(y) + 4}" text-anchor="middle" font-size="11" font-weight="700" {T}>{name}</text>')
    s.append(f'<circle cx="{X(87)}" cy="{Y(14)}" r="{7 * k}" stroke="var(--ink)" stroke-width="2" stroke-dasharray="6 4" style="fill:var(--card)"/>'
             f'<text x="{X(87)}" y="{Y(14) + 4}" text-anchor="middle" font-size="10" font-weight="700" {T}>MIC</text>')
    # top edge (the back wall when lying down): USB-C socket and antenna
    s.append(box(USB_U - 4 - 12, Wi - 14, 24, 14, "var(--card)", "5 V", ""))
    s.append(box(ANT_U - 4 - 5, Wi - 13, 10, 13, "var(--mustard)", "", ""))
    s.append(f'<text x="{X(ANT_U - 4)}" y="{Y(Wi) - 10}" text-anchor="middle" font-size="10" {T}>ANT</text>')
    hx = X(134 + 30 - 1.5)
    for (sx, sy), col in (((X(32) + 26, Y(72)), "#ff8a3d"), ((X(32) + 26, Y(32)), "#ff8a3d"),
                          ((X(87) + 16, Y(14)), "#8b5a3c"), ((X(26), Y(14)), "#8a5cf6"), ((X(USB_U + 6), Y(Wi - 14)), "#ff4a3d")):
        s.append(f'<path class="wire" d="M{sx:.1f} {sy:.1f} C{(sx + hx) / 2:.1f} {sy - 30:.1f} {hx - 30:.1f} {Y(60):.1f} {hx:.1f} {Y(64):.1f}" stroke="{col}" stroke-width="2.4" fill="none" opacity=".9"/>')
    s.append(f'<text x="{L * k / 2}" y="{W * k + 30}" text-anchor="middle" font-size="12" font-weight="700" {T}>▼ BOTTOM EDGE (it stands here) · dashed = hangs from the lid</text>')
    s.append(f'<text x="0" y="-36" font-size="12" font-weight="600" {T}>INSIDE · lid off, seen from the front · 180 × 112 × ~31 mm</text>')
    s.append('</svg>')
    return "".join(s)


# ---------------------------------------------------------------- the button's light states
STATES = [   # in the order a child meets them, then the two that say "not now"
    ("Ready", "steady dim blue", "Record", "#3a6fc4", "dim"),
    ("Recording", "red · mic on", "Record", "#e0442c", "on"),
    ("Got it", "one green pulse", "Record", "#58d47c", "pulse"),
    ("Message waits", "breathing green", "Play", "#58d47c", "breathe"),
    ("Playing", "steady green", "Play", "#58d47c", "on"),
    ("Not ready", "slow blue blink", "Record", "#3a6fc4", "blink"),
    ("Travel lock", "white blink", "Play", "#f4f1ea", "blink"),
]


def light_states():
    out = []
    for i, (name, sub, which, col, mode) in enumerate(STATES):
        out.append(
            f'<figure class="lstate{" aside" if i == 5 else ""}"><svg viewBox="0 0 120 120" aria-hidden="true">'
            f'<defs><radialGradient id="ls{i}"><stop offset="0" stop-color="{col}" stop-opacity=".9"/><stop offset="1" stop-color="{col}" stop-opacity="0"/></radialGradient></defs>'
            f'<circle cx="60" cy="60" r="56" fill="#cfcbc2" stroke="{INK}" stroke-width="2.5"/>'
            f'<g class="l-{mode}"><circle cx="60" cy="60" r="54" fill="url(#ls{i})"/>'
            f'<circle cx="60" cy="60" r="36" fill="none" stroke="{col}" stroke-width="9"/></g>'
            f'<circle cx="60" cy="60" r="30" fill="url(#steel2)" stroke="{INK}" stroke-width="2"/>'
            f'<ellipse cx="52" cy="50" rx="11" ry="6" fill="#fff" opacity=".7"/>'
            f'</svg><figcaption><b>{name}</b><span>{which} · {sub}</span></figcaption></figure>')
    return ('<svg width="0" height="0" style="position:absolute"><defs><radialGradient id="steel2" cx=".35" cy=".35">'
            '<stop offset="0" stop-color="#fff"/><stop offset=".6" stop-color="#cfccc5"/><stop offset="1" stop-color="#8e8a82"/></radialGradient></defs></svg>'
            + "".join(out))


# ---------------------------------------------------------------- the 40-pin header, as wired (must match box/dadbox/hw/pi.py)
# pin: (label, wire colour); a None colour means a bench-only probe lead
PINS = {
    2: ("Amp 5 V", "#d9412f"), 4: ("5 V in", "#d9412f"), 6: ("GND in", "#1b1a17"), 7: ("Modem key", "#9a958b"),
    8: ("UART TX", None), 10: ("UART RX", None), 14: ("UART GND", None),
    9: ("Mic GND", "#1b1a17"), 11: ("Rec red + mic", "#e8862a"), 12: ("BCLK", "#e9c03a"),
    13: ("Rec green", "#2f9e5b"), 15: ("Rec blue", "#3a6fc4"), 16: ("Play red", "#e8862a"),
    18: ("Play green", "#2f9e5b"), 20: ("Play GND", "#1b1a17"), 22: ("Play blue", "#3a6fc4"),
    29: ("Rec switch", "#ffffff"), 30: ("Rec GND", "#1b1a17"), 31: ("Play switch", "#ffffff"),
    35: ("LRCLK", "#8a5cf6"), 36: ("Amp SD", "#9a958b"), 38: ("Mic data", "#8b5a3c"),
    39: ("Amp GND", "#1b1a17"), 40: ("Amp DIN", "#2f9e5b"),
}


KEYSTYLE = ' style="fill:var(--rec)"'


def pin_header():
    pitch, x0, ye, yo = 40, 92, 112, 152          # even pins on the board's edge (top row), odd below
    s = ['<svg viewBox="0 0 900 300" role="img" aria-label="The Pi\'s 40-pin header as wired: 24 of 40 pins used. '
         + "; ".join(f"pin {n}: {l}" for n, (l, _) in sorted(PINS.items())) + '">']
    s.append(f'<rect x="{x0 - 26}" y="{ye - 22}" width="{19 * pitch + 52}" height="{yo - ye + 44}" rx="8" stroke="var(--ink)" stroke-width="2" style="fill:var(--card)"/>')
    s.append(f'<text x="{x0 - 34}" y="{(ye + yo) / 2 + 4}" text-anchor="end" font-size="12" {T} opacity=".7">SD end</text>')
    for col in range(20):
        for row, y in ((0, ye), (1, yo)):
            n = col * 2 + (2 if row == 0 else 1)
            x = x0 + col * pitch
            if n not in PINS:
                s.append(f'<rect x="{x - 4}" y="{y - 4}" width="8" height="8" rx="1" stroke="var(--ink-soft)" stroke-width="1" fill="none" opacity=".55"/>')
                continue
            label, c = PINS[n]
            key = n == 11
            if c is None:
                s.append(f'<circle cx="{x}" cy="{y}" r="8" stroke="var(--ink)" stroke-width="1.5" stroke-dasharray="3 2" fill="none"/>')
            else:
                s.append(f'<circle cx="{x}" cy="{y}" r="9" stroke="var(--ink)" stroke-width="{3 if key else 1.5}" fill="{c}"/>')
            if key:
                s.append(f'<circle cx="{x}" cy="{y}" r="15" stroke="var(--rec)" stroke-width="1.5" fill="none"/>')
            ly, anchor, rot = (y - 20, "start", -55) if row == 0 else (y + 26, "end", -55)
            s.append(f'<text transform="translate({x + 3} {ly}) rotate({rot})" text-anchor="{anchor}" font-size="13" '
                     f'font-weight="{700 if key else 500}" {T}{KEYSTYLE if key else ""}>{label}</text>')
    for n, x, y in ((1, x0, yo), (2, x0, ye), (39, x0 + 19 * pitch, yo), (40, x0 + 19 * pitch, ye)):
        s.append(f'<text x="{x + (-16 if n in (1, 2) else 16)}" y="{y + 4}" text-anchor="middle" font-size="10" {T} opacity=".6">{n}</text>')
    s.append(f'<text x="{x0 - 26}" y="292" font-size="12" {T} opacity=".75">Dashed: bench-only debug probe · hollow squares: unused · ring: the privacy wire</text>')
    s.append('</svg>')
    return "".join(s)


# ---------------------------------------------------------------- the privacy wire
def privacy_wire():
    s = ['<svg viewBox="0 0 760 300" role="img" aria-label="The privacy wire: header pin 11 (GPIO 17) goes first to the Record button\'s red LED tab; '
         'a short wire from that same tab powers the microphone. Any break leaves the mic unpowered, never powered with the light off.">']
    # header strip
    s.append(f'<rect x="20" y="60" width="90" height="180" rx="6" fill="#1f6f6b" stroke="{INK}" stroke-width="2.5"/>'
             f'<text x="65" y="50" text-anchor="middle" font-size="12" font-weight="600" {T}>Pi header</text>')
    for r in range(8):
        for c in range(2):
            y = 80 + r * 20
            hi = (r == 5 and c == 0)
            s.append(f'<rect x="{46 + c * 26}" y="{y}" width="12" height="12" fill="{"#f2b83b" if hi else "#d8b04a"}" stroke="{INK}" stroke-width="{2.5 if hi else 1}"/>')
    s.append(f'<text x="38" y="191" text-anchor="end" font-size="11" font-weight="600" {T}>11</text>')
    # button, rear view with tabs
    bx, by = 380, 150
    s.append(f'<circle cx="{bx}" cy="{by}" r="78" stroke="var(--ink)" stroke-width="2.5" style="fill:var(--card)"/>'
             f'<circle cx="{bx}" cy="{by}" r="60" stroke="var(--ink)" stroke-width="1" stroke-dasharray="4 3" fill="none"/>'
             f'<text x="{bx}" y="{by + 108}" text-anchor="middle" font-size="12" font-weight="600" {T}>Record button, from behind</text>')
    tabs = {"C−": (bx - 28, by - 36), "R": (bx + 28, by - 36), "B": (bx - 28, by + 36), "G": (bx + 28, by + 36)}
    for n, (x, y) in tabs.items():
        s.append(f'<rect x="{x - 9}" y="{y - 14}" width="18" height="28" rx="2" fill="#c8c5bd" stroke="{INK}" stroke-width="1.5"/>'
                 f'<text x="{x}" y="{y + 30 if y > by else y - 20}" text-anchor="middle" font-size="12" font-weight="600" {T}>{n}</text>')
    for x in (bx - 62, bx + 62):
        s.append(f'<rect x="{x - 9}" y="{by - 12}" width="18" height="24" rx="2" fill="#d8b04a" stroke="{INK}" stroke-width="1.5"/>')
    rx, ry = tabs["R"]
    # wire 1: pin 11 to R
    s.append(f'<path d="M58 186 C 200 186, 250 {ry - 60}, {rx} {ry - 4}" stroke="{INK}" stroke-width="8" fill="none" stroke-linecap="round"/>'
             f'<path d="M58 186 C 200 186, 250 {ry - 60}, {rx} {ry - 4}" stroke="#e8862a" stroke-width="5" fill="none" stroke-linecap="round"/>'
             f'<text x="170" y="150" font-size="11" {T}>① GPIO 17 → red LED first</text>')
    # mic
    mx, my = 640, 80
    s.append(f'<rect x="{mx - 50}" y="{my - 34}" width="100" height="68" rx="6" fill="#2a4f9a" stroke="{INK}" stroke-width="2.5"/>'
             f'<circle cx="{mx}" cy="{my - 4}" r="9" fill="#c9c6bf" stroke="{INK}" stroke-width="1.5"/><circle cx="{mx}" cy="{my - 4}" r="2" fill="{INK}"/>'
             f'<text x="{mx}" y="{my + 24}" text-anchor="middle" font-size="11" font-weight="600" fill="#fff" font-family="JetBrains Mono, monospace">MIC · VDD</text>')
    s.append(f'<path d="M{rx} {ry - 4} C {rx + 80} {ry - 40}, {mx - 120} {my + 10}, {mx - 50} {my}" stroke="{INK}" stroke-width="8" fill="none" stroke-linecap="round"/>'
             f'<path d="M{rx} {ry - 4} C {rx + 80} {ry - 40}, {mx - 120} {my + 10}, {mx - 50} {my}" stroke="#e8862a" stroke-width="5" fill="none" stroke-linecap="round"/>'
             f'<text x="{rx + 60}" y="{ry - 40}" font-size="11" {T}>② same tab → mic power</text>')
    s.append(f'<rect x="530" y="170" width="215" height="92" fill="var(--mustard)" stroke="{INK}" stroke-width="2"/>'
             f'<text x="542" y="194" font-size="12" font-weight="600" fill="{INK}" font-family="JetBrains Mono, monospace">NO RED LIGHT, NO MIC.</text>'
             f'<text x="542" y="214" font-size="11" fill="{INK}" font-family="JetBrains Mono, monospace">Break ① → both dark.</text>'
             f'<text x="542" y="232" font-size="11" fill="{INK}" font-family="JetBrains Mono, monospace">Break ② → light on, mic off.</text>'
             f'<text x="542" y="250" font-size="11" fill="{INK}" font-family="JetBrains Mono, monospace">Never: mic on, light off.</text>')
    s.append('</svg>')
    return "".join(s)


PICTURES = {"hero": hero, "face": face_plan, "top": top_edge, "inside": inside, "lights": light_states, "privacy": privacy_wire, "pins": pin_header}

if __name__ == "__main__":
    page = pathlib.Path(__file__).with_name("index.html")
    html = page.read_text()
    for name, fn in PICTURES.items():
        pat = re.compile(rf"(<!--pic:{name}-->).*?(<!--/pic:{name}-->)", re.S)
        if not pat.search(html):
            raise SystemExit(f"marker pic:{name} missing in index.html")
        html = pat.sub(lambda m: m.group(1) + fn() + m.group(2), html)
    page.write_text(html)
    print("drew", ", ".join(PICTURES))
