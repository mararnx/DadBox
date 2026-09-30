# Enclosure layout

The to-scale plan: an [interactive page](cad/enclosure-layout.html) (exploded
view, plan, sections, holes, fixings, wiring). The decision behind it is
[ADR 0023](../docs/decisions/0023-enclosure-layout.md). One source,
[cad/layout.json](cad/layout.json); `python3 hardware/cad/layout.py L W H`
re-checks it with your measured inside dimensions and rewrites the 1:1
templates (`cad/template-*.svg` — print at 100 %, check the 50 mm bar).

## Inside dimensions

| | Length | Width | Depth |
| --- | --- | --- | --- |
| Outside (listing) | 188 | 120 | 37.5 |
| Planning value | **180** | **112** | **31** |
| Measured | — | — | — |

Walls ~3 mm at the rim plus ~1 mm casting draft toward the tub floor; tub floor
and lid ~3 mm each. Six lid screws: four corners and two mid-way along the long
walls (seen on the clone). **Measure before drilling** and use the smaller of
rim and floor.

## Where everything goes

The tub stands the right way up and the flat lid is the top face
([ADR 0023](../docs/decisions/0023-enclosure-layout.md), revised 2026-09-29,
from the parts laid in the box). Interior coordinates: x from the left wall
(as the child faces the front), y from the front wall, z up from the tub
floor; the lid's inside face is at z = 31. Positions come from a photo of the
mock-up: ±5 mm until the parts are marked for real.

| Part | Mounted on | Position (mm) | Height |
| --- | --- | --- | --- |
| Pi Zero 2 W on the SIM7670G HAT | tub floor, 4 × M2.5 nylon standoffs, USB-A ports to the front | x 110–167, y 22–107 | 5–23 with soldered leads |
| Amp (MAX98357A) | tub floor, foam tape | x 10–28, y 62–81 | 2–11 |
| Foam block | tub floor, glued | under the speaker | 0–8, fills the gap |
| Speaker (Seeed 5 W) | pressed against the lid by the foam block, foam ring as seal | x 61–106, y 37–87 | 8–31 |
| Record button | lid, own nut | centre x 16, y 24 | hangs 26 |
| Play button | lid, own nut | centre x 46, y 24 | hangs 26 |
| Mic | lid, foam gasket, foam column below | centre x 110, y 20 | hangs 14 |
| Antenna SMA bulkhead | back wall, nut + lock washer | centre x 53, mid-height | 13 inward |
| 5 V USB-C socket (Exsys EX-49222, ~30 mm flange — measure it) | back wall, own nut | centre x 27, mid-height | 25 inward, then a 30 cm tail |

Clearances at the planning values: 8 mm above the stack, 5 mm under the
buttons (leads only), 8 mm foam block; nothing collides; tightest gaps 2 mm
(the 5 V socket to a screw boss) and 3.3 mm (the HAT to a screw boss). No
status LEDs: Record says ready or not
([ADR 0024](../docs/decisions/0024-no-status-leds-record-says-ready.md)).

## Holes

Lid (top face), measured on the outside from the **left** and **front** edges:

| For | X | Y | Ø | How |
| --- | --- | --- | --- | --- |
| Record | 20 | 28 | 16 | step drill 15, file to 16 |
| Play | 50 | 28 | 16 | step drill 15, file to 16 |
| Mic | 114 | 24 | 2 | twist drill |
| Speaker grille | 87.5 | 66 | 19 × 5 | hex pattern, 7 mm pitch |

Back wall, seen from behind, from its **left end** and **down from the rim**:
5 V socket 157 / 15.5 (Ø 22.3 for the EX-49222), antenna 131 / 15.5 (Ø 6.5).
The socket sits at the
corner because its flange is the widest thing on that wall: 2 mm from the
screw boss, 6 mm to the antenna nut. Tub floor: 4 × 2.7 mm,
marked through the HAT's own holes.

**Mark before you drill.** Put the parts where the table says, close the lid
and check each mark over its part: the grille over the cone (trace the foam
ring's hole), the mic hole over the sound port, each button over 22 mm × 26 mm
of empty space. Move a mark rather than a part, and tell Claude the measured
centres so `layout.json` stays true.

## Fixing kit

M2.5 nylon standoff assortment; six matching stainless lid screws (they are on show); 3M VHB or 2 mm foam tape; 10 mm closed-cell
EVA foam; adhesive cable-tie mounts and small ties; 26 AWG silicone wire;
heat-shrink; medium threadlocker; Kapton tape or a plastic sheet; 2 and 2.7 mm
twist drills, centre punch, deburring tool; a half-round file; a round
USB-C panel socket with a cable tail (Exsys EX-49222, not a socket-to-socket coupler: those power the box one way up only), a USB-C-socket-to-micro-USB adapter on its tail for the Pi's PWR IN, and a short micro-USB → USB-C lead (Pi OTG → HAT).
About CHF 100 in all, mostly tools. Rows in [bom/bom.csv](bom/bom.csv), phase 4.

## Measure first

1. Inside length and width at the rim and at the floor; depth; lid thickness.
2. The screw bosses: how many, where, how thick.
3. The Pi-on-HAT stack height, bottom of the HAT to the top of the Pi.
4. The HAT's LTE antenna connector, and whether its pigtail reaches the back
   wall at x ≈ 31 (in the mock-up it goes through the back-left).
5. Where the mic's sound hole is.
