"""
Kael Emberclaw (3*) - Phase 6 redesign. Design sheet: docs/art/characters/kael.md
Native 96x96 battle frames (feet on row 88, faces RIGHT; the game flips players),
96x96 portrait. Run: python3 tools/art_kael.py  (writes into Content/assets/characters/kael_emberclaw/)
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image
from px6 import Canvas, Ramp, colours
from rig import ik

FW = FH = 96
GROUND = 88
OUT = os.path.join(os.path.dirname(__file__), '..', 'Content', 'assets', 'characters', 'kael_emberclaw')

# ------------------------------------------------------------------ palette (dark -> light, hue shifted)
SKIN = Ramp('#4a2426', '#9c5a48', '#d98e6c', '#f2b68c', '#ffd9b4')
HAIR = Ramp('#1e0f14', '#3e1a1a', '#66281f', '#8e3a26', '#b8583a')
TUNIC = Ramp('#2a0a14', '#5a1420', '#8e1f26', '#c43a2e', '#e8653e')
SCARF = Ramp('#2e0a12', '#6e1a1e', '#b02a24', '#e04a2c', '#ff7a40')
LEATHER = Ramp('#1a0f12', '#3a2220', '#5a3628', '#7a4e36', '#9a6a48')
STEEL = Ramp('#0e0e16', '#262634', '#3e3e52', '#62647a', '#9aa0b8', '#e6ecf5')
GOLD = Ramp('#2a1608', '#6a3e10', '#a86a1a', '#e0a232', '#ffe07a')
TROUSER = Ramp('#120c16', '#241a2a', '#3a2c40', '#524258', '#6a5a70')
EMBER = ['#ff5a1e', '#ffa02a', '#ffe070']
EYE, EYE_HI = '#241016', '#fff4e8'
SMEAR = [(255, 122, 48, 255), (255, 200, 90, 255), (255, 246, 200, 255)]


class Pose:
    def __init__(self, **kw):
        self.ox = 0; self.oy = 0; self.crouch = 0; self.lean = 3
        self.f_foot = (56, GROUND); self.b_foot = (35, GROUND)
        self.f_hand = None; self.b_hand = None
        self.head_dx = 0; self.head_dy = 0
        self.eyes = 'open'; self.blade = 25; self.blade_front = True
        self.breath = 0; self.wind = 0.0; self.embers = 0
        self.smear = None; self.aura = 0; self.back_hand_on_hilt = False; self.no_blade = False
        self.__dict__.update(kw)


def skel(p):
    hip = (44 + p.ox, 63 + p.oy + p.crouch)
    sh = (hip[0] + p.lean, hip[1] - 17 + p.breath)
    head = (sh[0] + 3 + p.head_dx, sh[1] - 11 + p.head_dy)
    fsh, bsh = (sh[0] + 3, sh[1] + 2), (sh[0] - 5, sh[1] + 1)
    fh = p.f_hand or (fsh[0] + 9, fsh[1] + 12)
    bh = p.b_hand or (bsh[0] - 2, bsh[1] + 15)
    ff = (p.f_foot[0] + p.ox, min(GROUND, p.f_foot[1] + p.oy))
    bf = (p.b_foot[0] + p.ox, min(GROUND, p.b_foot[1] + p.oy))
    return dict(hip=hip, sh=sh, head=head, fsh=fsh, bsh=bsh, fh=fh, bh=bh, ff=ff, bf=bf)


# ------------------------------------------------------------------ parts
def limb(cv, a, b, w0, w1):
    """Tapered capsule from a to b (widths in px)."""
    m = cv.mask()
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    px, py = -math.sin(ang), math.cos(ang)
    m.poly([(a[0] + px * w0 / 2, a[1] + py * w0 / 2), (b[0] + px * w1 / 2, b[1] + py * w1 / 2),
            (b[0] - px * w1 / 2, b[1] - py * w1 / 2), (a[0] - px * w0 / 2, a[1] - py * w0 / 2)])
    m.ellipse(a[0], a[1], w0 / 2 - 0.2, w0 / 2 - 0.2).ellipse(b[0], b[1], w1 / 2 - 0.2, w1 / 2 - 0.2)
    return m


def leg(cv, hip, foot, back):
    knee = ik(hip, (foot[0], foot[1] - 3), 12.5, 12, bend=-1)
    bias = -0.25 if back else 0.0
    cv.part(limb(cv, hip, knee, 8, 7), TROUSER, 'cloth', 'cyl_v', bias=bias)
    ankle = (foot[0], foot[1] - 3)
    cv.part(limb(cv, knee, ankle, 7, 6), TROUSER, 'cloth', 'cyl_v', bias=bias)
    # boot: leather shaft + toe pointing right
    boot = cv.mask().poly([(ankle[0] - 3, ankle[1] - 6), (ankle[0] + 3, ankle[1] - 6), (foot[0] + 3, foot[1] - 3),
                           (foot[0] + 7, foot[1] - 2), (foot[0] + 7, foot[1]), (foot[0] - 4, foot[1]), (foot[0] - 4, foot[1] - 3)])
    cv.part(boot, LEATHER, 'leather', bias=bias - 0.1)
    # black steel greave over the shin (front leg only: reads as armour, keeps back leg quiet)
    if not back:
        g = limb(cv, (knee[0] + 1, knee[1] + 1), (ankle[0] + 1, ankle[1] - 5), 5, 5)
        cv.part(g, STEEL, 'metal', 'cyl_v', cast=False)
        cv.part(cv.mask().rect(ankle[0] - 3, ankle[1] - 7, ankle[0] + 3, ankle[1] - 6), SCARF, 'cloth', 'flat', cast=False)
    return knee


def torso(cv, s, p):
    hip, sh = s['hip'], s['sh']
    # crimson tunic
    t = cv.mask().poly([(sh[0] - 8, sh[1] - 1), (sh[0] + 7, sh[1] - 1), (hip[0] + 6, hip[1] + 1),
                        (hip[0] + 8, hip[1] + 7), (hip[0] - 7, hip[1] + 7), (hip[0] - 6, hip[1] + 1)])
    cv.part(t, TUNIC, 'cloth', 'cyl_v')
    # leather jerkin, open at the front to show the tunic
    j = cv.mask().poly([(sh[0] - 8, sh[1]), (sh[0] + 2, sh[1]), (hip[0] + 1, hip[1] - 1), (hip[0] - 6, hip[1]), (hip[0] - 7, hip[1] - 6)])
    cv.part(j, LEATHER, 'leather', 'cyl_v')
    j2 = cv.mask().poly([(sh[0] + 5, sh[1]), (sh[0] + 7, sh[1]), (hip[0] + 6, hip[1] - 1), (hip[0] + 4, hip[1] - 1)])
    cv.part(j2, LEATHER, 'leather', 'cyl_v')
    # belt + gold buckle + tassets (triangles: Kael's shape language)
    cv.part(cv.mask().poly([(hip[0] - 7, hip[1] - 2), (hip[0] + 7, hip[1] - 3), (hip[0] + 7, hip[1] + 1), (hip[0] - 7, hip[1] + 2)]),
            LEATHER, 'leather', 'cyl_v')
    cv.part(cv.mask().rect(hip[0] + 2, hip[1] - 3, hip[0] + 5, hip[1] + 1), GOLD, 'metal', 'flat', normal=(-0.3, -0.4, 1))
    cv.part(cv.mask().poly([(hip[0] - 7, hip[1] + 2), (hip[0] - 1, hip[1] + 2), (hip[0] - 6, hip[1] + 9)]), TUNIC, 'cloth', bias=-0.2)
    cv.part(cv.mask().poly([(hip[0] - 1, hip[1] + 1), (hip[0] + 8, hip[1]), (hip[0] + 7, hip[1] + 8), (hip[0] + 3, hip[1] + 12), (hip[0], hip[1] + 8)]),
            TUNIC, 'cloth')
    # diagonal chest strap with a gold ring (scabbard harness)
    cv.part(limb(cv, (sh[0] - 7, sh[1] + 1), (hip[0] + 4, hip[1] - 4), 3, 3), LEATHER, 'leather', 'flat', normal=(0, -0.2, 1), bias=0.25)
    cv.part(cv.mask().ellipse((sh[0] + hip[0]) / 2 - 1, (sh[1] + hip[1]) / 2 - 2, 1.6, 1.6), GOLD, 'metal', cast=False)


def head(cv, s, p):
    hx, hy = s['head']
    # back hair mass + swept spikes (large shapes first)
    back = cv.mask().ellipse(hx - 2, hy - 2, 9, 8.5)
    back.poly([(hx - 7, hy - 6), (hx - 17, hy - 9), (hx - 9, hy - 1)])
    back.poly([(hx - 8, hy + 1), (hx - 16, hy + 2), (hx - 8, hy + 5)])
    back.poly([(hx - 4, hy - 9), (hx - 11, hy - 17), (hx, hy - 10)])
    cv.part(back, HAIR, 'hair')
    # face (3/4 right): round skull + short jaw pointing forward
    face = cv.mask().ellipse(hx + 1, hy + 1, 7.5, 7.5)
    face.poly([(hx - 3, hy + 5), (hx + 8, hy + 3), (hx + 5, hy + 9), (hx - 1, hy + 9)])
    cv.part(face, SKIN, 'skin')
    cv.part(cv.mask().ellipse(hx - 3, hy + 2, 1.6, 2.2), SKIN, 'skin', bias=-0.3)   # ear
    # front hair: three triangular locks over the forehead + crown spikes
    for pts in ([(hx - 4, hy - 7), (hx + 7, hy - 7), (hx + 9, hy - 1), (hx + 4, hy - 4)],
                [(hx - 1, hy - 8), (hx + 4, hy - 16), (hx + 5, hy - 7)],
                [(hx + 3, hy - 8), (hx + 11, hy - 12), (hx + 8, hy - 5)],
                [(hx - 6, hy - 6), (hx - 1, hy - 14), (hx + 1, hy - 7)],
                [(hx - 5, hy - 5), (hx - 2, hy - 6), (hx - 3, hy + 1)]):
        cv.part(cv.mask().poly(pts), HAIR, 'hair', 'flat', normal=(-0.2, -0.6, 1))
    # headband (tails live in back_cloth)
    hb = cv.mask().poly([(hx - 7, hy - 5), (hx + 6, hy - 7), (hx + 6, hy - 5), (hx - 7, hy - 3)])
    cv.part(hb, SCARF, 'cloth', 'cyl_v', cast=False)
    # face features: 2x3 eye, determined brow, small mouth
    ex, ey = hx + 4, hy + 1
    e = p.eyes
    if e in ('open', 'fierce'):
        cv.pixels([(ex, ey - 1), (ex + 1, ey - 1), (ex, ey), (ex + 1, ey), (ex + 1, ey + 1)], EYE)
        cv.dot(ex, ey - 1, EYE_HI)
        cv.pixels([(ex - 1, ey - 3), (ex, ey - 3), (ex + 1, ey - 2), (ex + 2, ey - 2)], HAIR[1])
        if e == 'fierce':
            cv.pixels([(ex - 1, ey - 2), (ex + 2, ey - 1)], HAIR[1])
    elif e == 'closed':
        cv.pixels([(ex, ey), (ex + 1, ey), (ex + 2, ey - 1)], EYE)
    elif e == 'hurt':
        cv.pixels([(ex, ey - 1), (ex + 1, ey), (ex, ey + 1)], EYE)
        cv.pixels([(ex - 1, ey - 3), (ex, ey - 2), (ex + 1, ey - 2)], HAIR[1])
    elif e == 'ko':
        cv.pixels([(ex, ey - 1), (ex + 1, ey), (ex + 2, ey + 1), (ex + 2, ey - 1), (ex, ey + 1)], EYE)
    mouth = [(hx + 6, hy + 6), (hx + 7, hy + 6)] if e != 'hurt' else [(hx + 6, hy + 6), (hx + 7, hy + 5), (hx + 7, hy + 7)]
    cv.pixels(mouth, SKIN[0])


def back_cloth(cv, s, p):
    """Scarf tail + headband tails, blown back; `wind` animates them."""
    hx, hy = s['head']
    sx, sy = s['sh']
    w = p.wind
    tail = cv.mask().poly([(sx - 3, sy - 3), (sx - 1, sy + 1), (sx - 13 - w, sy + 6 + w * 0.5), (sx - 20 - w * 1.5, sy + 4 + w),
                           (sx - 15 - w, sy + 1)])
    cv.part(tail, SCARF, 'cloth', 'flat', normal=(-0.1, -0.3, 1))
    band = cv.mask().poly([(hx - 7, hy - 5), (hx - 16 - w, hy - 3 + w * 0.4), (hx - 19 - w * 1.2, hy + 1 + w * 0.3), (hx - 8, hy - 2)])
    cv.part(band, SCARF, 'cloth', 'flat', normal=(0, -0.2, 1), bias=-0.2)


def scarf_wrap(cv, s):
    sx, sy = s['sh']
    m = cv.mask().ellipse(sx + 1, sy - 1, 7, 3.2)
    m.poly([(sx - 5, sy), (sx + 5, sy - 1), (sx + 1, sy + 7), (sx - 3, sy + 6)])
    cv.part(m, SCARF, 'cloth', 'cyl_v')


def arm(cv, shoulder, hand, front, bend):
    elbow = ik(shoulder, hand, 9, 9, bend=bend)
    bias = 0.0 if front else -0.3
    cv.part(limb(cv, shoulder, elbow, 6, 5), TUNIC, 'cloth', 'cyl_v', bias=bias)
    fore = limb(cv, elbow, hand, 5, 5)
    cv.part(fore, LEATHER if front else TUNIC, 'leather', 'cyl_v', bias=bias)
    fist = cv.mask().ellipse(hand[0], hand[1], 2.6, 2.6)
    cv.part(fist, STEEL if front else SKIN, 'metal' if front else 'skin', bias=bias)
    return elbow


def pauldron(cv, fsh):
    x, y = fsh
    m = cv.mask().poly([(x - 5, y - 2), (x + 1, y - 5), (x + 6, y - 2), (x + 5, y + 3), (x - 3, y + 4)])
    cv.part(m, STEEL, 'metal')
    cv.part(cv.mask().poly([(x - 4, y + 3), (x + 5, y + 2), (x + 5, y + 4), (x - 3, y + 5)]), GOLD, 'metal', 'flat', normal=(0, 0.3, 1), cast=False)


def sword(cv, hand, ang, embers=0):
    """Oversized single-edged flame blade: black steel, bright cutting edge, ember cracks on the spine."""
    a = math.radians(ang)
    ux, uy = math.cos(a), math.sin(a)
    px, py = -uy, ux                      # +p = spine side (ang 0 -> spine faces down), -p = edge
    hx, hy = hand

    def at(t, o):
        return (hx + ux * t + px * o, hy + uy * t + py * o)
    cv.part(limb(cv, at(-6, 0), at(1, 0), 3, 3), LEATHER, 'leather', 'cyl_h', cast=False)        # grip
    cv.part(cv.mask().ellipse(*at(-7, 0), 1.8, 1.8), GOLD, 'metal', cast=False)                  # pommel
    cv.part(limb(cv, at(3, -5), at(3, 5), 3, 3), GOLD, 'metal', cast=False)                      # guard
    L = 34
    blade = cv.mask().poly([at(4, -3), at(L - 8, -3.6), at(L, 1.5), at(L - 4, 3.6), at(4, 3.6)])
    cv.part(blade, STEEL, 'metal', 'flat', normal=(-0.2, -0.5, 1), cast=False, bias=-0.55)
    edge = cv.mask()
    for t in range(5, L - 7):
        edge.set(*at(t, -2.6))
    for k in range(8):
        edge.set(*at(L - 8 + k, -2.8 + k * 0.55))
    cv.part(edge, STEEL, 'metal', 'flat', normal=(-0.6, -0.8, 0.5), sep=False, cast=False, bias=0.2)
    # ember cracks: three 2-3px glowing notches along the spine, brightness steps with `embers`
    for i, t in enumerate((10, 17, 24)):
        c = EMBER[(i + embers) % 3]
        for (tt, oo) in ((t, 1.2), (t, 2.2), (t + 1, 1.7), (t + 1, 2.7), (t + 2, 2.2)):
            cv.dot(*at(tt, oo), c)
    return at(L, 0)


def smear(cv, centre, r0, r1, a0, a1, thick=4):
    """Hand-shaped slash smear: a filled crescent, thickest mid-swing, 3 tones (hot edge outside)."""
    cx, cy = centre
    n = max(6, int(abs(a1 - a0) / 6))
    outer, inner = [], []
    for i in range(n + 1):
        t = i / n
        a = math.radians(a0 + (a1 - a0) * t)
        w = thick * math.sin(math.pi * t) ** 0.7 + 0.6
        outer.append((cx + math.cos(a) * r1, cy + math.sin(a) * r1))
        inner.append((cx + math.cos(a) * (r1 - w), cy + math.sin(a) * (r1 - w)))
    m = cv.mask().poly(outer + inner[::-1]).m
    for y, x in zip(*m.nonzero()):
        d = r1 - math.hypot(x - cx, y - cy)
        cv.dot(x, y, SMEAR[2] if d < 1.2 else (SMEAR[1] if d < thick * 0.55 else SMEAR[0]))


def flames(cv, base_x, base_y, n, h, phase):
    """Controlled flame tongues (Kael's aura) - shapes, not particle soup."""
    for i in range(n):
        x = base_x + (i - n / 2) * 7 + (3 if (i + phase) % 2 else 0)
        hh = h * (0.6 + 0.4 * ((i * 7 + phase * 3) % 5) / 4)
        m = cv.mask().poly([(x - 3, base_y), (x + 3, base_y), (x + 1, base_y - hh * 0.6), (x + 2, base_y - hh), (x - 2, base_y - hh * 0.5)])
        cv.part(m, Ramp('#8a1a0e', '#e0521c', '#ff8a2a', '#ffc15a', '#ffef9a'), 'flat', 'round', cast=False, sep=False)


# ------------------------------------------------------------------ frame
def frame(p):
    cv = Canvas(FW, FH)
    s = skel(p)
    if p.aura:
        flames(cv, s['hip'][0], GROUND, 5, 10 + p.aura * 6, p.embers)
    back_cloth(cv, s, p)
    bh = s['bh'] if not p.back_hand_on_hilt else (s['fh'][0] - 4, s['fh'][1] + 1)
    arm(cv, s['bsh'], bh, False, bend=1)
    leg(cv, s['hip'], s['bf'], True)
    leg(cv, s['hip'], s['ff'], False)
    torso(cv, s, p)
    if not p.blade_front and not p.no_blade:
        sword(cv, s['fh'], p.blade, p.embers)
    head(cv, s, p)
    scarf_wrap(cv, s)
    arm(cv, s['fsh'], s['fh'], True, bend=-1)
    pauldron(cv, s['fsh'])
    if p.blade_front and not p.no_blade:
        sword(cv, s['fh'], p.blade, p.embers)
        # fist over the grip
        cv.part(cv.mask().ellipse(s['fh'][0], s['fh'][1], 2.6, 2.6), STEEL, 'metal', cast=False)
    if p.smear:
        smear(cv, *p.smear)
    cv.cleanup().outline()
    return cv.image()


# ------------------------------------------------------------------ animations (counts/hit frames match data/skills)
def idle():
    out = []
    for i in range(6):
        k = math.sin(i / 6 * math.tau)
        out.append(frame(Pose(breath=1 if k > 0.3 else 0, wind=1.5 + k * 1.5, embers=i % 3,
                              f_hand=(62, 61 + (1 if k > 0.3 else 0)), blade=28)))
    return out


def attack():
    P = Pose
    return [frame(P(crouch=2, lean=1, f_hand=(50, 52), blade=-150, blade_front=False, wind=2, b_hand=(36, 58))),
            frame(P(crouch=3, lean=-1, f_hand=(44, 50), blade=-165, blade_front=False, wind=3, eyes='fierce', b_hand=(34, 56))),
            frame(P(ox=10, crouch=2, lean=6, f_hand=(75, 56), blade=8, wind=5, eyes='fierce', b_foot=(40, GROUND), f_foot=(64, GROUND),
                    smear=((58, 50), 22, 30, -110, 20, 5))),
            frame(P(ox=10, crouch=4, lean=7, f_hand=(72, 66), blade=55, wind=6, eyes='fierce', b_foot=(40, GROUND), f_foot=(64, GROUND))),
            frame(P(ox=10, crouch=1, lean=5, f_hand=(72, 44), blade=-60, wind=6, eyes='fierce', b_foot=(40, GROUND), f_foot=(64, GROUND),
                    smear=((60, 58), 20, 28, 70, -70, 5))),
            frame(P(ox=5, crouch=1, lean=4, f_hand=(66, 55), blade=-10, wind=4)),
            frame(P(f_hand=(62, 60), blade=25, wind=2))]


def hit():
    return [frame(Pose(ox=-3, lean=-2, head_dx=-2, eyes='hurt', f_hand=(57, 60), blade=40, wind=4)),
            frame(Pose(ox=-5, lean=-4, head_dx=-3, head_dy=1, eyes='hurt', f_hand=(54, 62), blade=55, wind=5)),
            frame(Pose(ox=-2, lean=0, eyes='open', f_hand=(60, 61), blade=32, wind=3))]


def guard():
    g = dict(crouch=4, lean=1, f_hand=(60, 52), blade=-95, back_hand_on_hilt=True, eyes='fierce')
    return [frame(Pose(crouch=2, lean=2, f_hand=(61, 55), blade=-60, wind=2)),
            frame(Pose(wind=2, **g)),
            frame(Pose(wind=3, breath=1, **g))]


def victory():
    return [frame(Pose(f_hand=(60, 44), blade=-120, wind=2, eyes='closed')),
            frame(Pose(f_hand=(58, 38), blade=-60, wind=3, smear=((56, 34), 14, 20, -200, -40, 3))),
            frame(Pose(f_hand=(57, 34), blade=-80, wind=4, embers=1, eyes='fierce')),
            frame(Pose(f_hand=(57, 34), blade=-82, wind=2, embers=2, eyes='fierce', breath=1))]


def ko():
    kneel = frame(Pose(crouch=9, lean=6, head_dx=2, head_dy=3, eyes='hurt', f_hand=(64, 80), blade=80,
                       f_foot=(58, GROUND), b_foot=(36, GROUND), wind=0))
    down = frame(Pose(eyes='ko', f_hand=(60, 62), no_blade=True, wind=0)).rotate(90, expand=False)
    bb = down.getbbox()
    gs = Canvas(FW, FH)
    sword(gs, (16, GROUND - 2), -4)
    gs.cleanup().outline()
    lying = gs.image()
    if bb:
        c = down.crop(bb)
        lying.paste(c, (FW // 2 - c.width // 2, GROUND + 1 - c.height), c)
    return [kneel, lying]


def burst():
    P = Pose
    f = []
    f.append(frame(P(crouch=4, lean=0, f_hand=(48, 54), blade=-160, blade_front=False, aura=1, embers=0, eyes='fierce', wind=3)))
    f.append(frame(P(crouch=5, lean=-1, f_hand=(46, 52), blade=-170, blade_front=False, aura=2, embers=1, eyes='fierce', wind=4)))
    f.append(frame(P(ox=12, crouch=3, lean=8, f_hand=(70, 58), blade=-20, aura=1, embers=2, eyes='fierce', wind=7, b_foot=(40, GROUND))))
    f.append(frame(P(ox=12, crouch=2, lean=7, f_hand=(76, 56), blade=10, embers=0, eyes='fierce', wind=7, b_foot=(40, GROUND),
                     smear=((60, 50), 22, 31, -110, 25, 5))))
    f.append(frame(P(ox=12, crouch=3, lean=6, f_hand=(72, 66), blade=60, embers=1, eyes='fierce', wind=6, b_foot=(40, GROUND))))
    f.append(frame(P(ox=12, crouch=1, lean=5, f_hand=(73, 44), blade=-55, embers=2, eyes='fierce', wind=7, b_foot=(40, GROUND),
                     smear=((62, 58), 20, 29, 70, -75, 5))))
    f.append(frame(P(ox=12, crouch=3, lean=4, f_hand=(62, 50), blade=-150, blade_front=False, embers=0, eyes='fierce', wind=6, b_foot=(40, GROUND))))
    f.append(frame(P(ox=12, crouch=2, lean=8, f_hand=(76, 58), blade=18, embers=1, eyes='fierce', wind=8, b_foot=(40, GROUND),
                     smear=((60, 52), 22, 31, -120, 30, 6))))
    f.append(frame(P(ox=10, oy=-12, lean=3, f_hand=(58, 26), blade=-95, embers=2, eyes='fierce', wind=8, aura=1,
                     f_foot=(58, GROUND - 4), b_foot=(38, GROUND - 2))))
    f.append(frame(P(ox=12, crouch=6, lean=9, f_hand=(76, 70), blade=75, embers=0, eyes='fierce', wind=9, aura=3, b_foot=(40, GROUND),
                     smear=((64, 44), 22, 33, -95, 80, 7))))
    f.append(frame(P(ox=6, crouch=2, lean=4, f_hand=(66, 58), blade=20, embers=1, wind=4, aura=1)))
    return f


ANIMS = [('idle', idle, 6, True), ('attack', attack, 14, False), ('hit', hit, 10, False), ('victory', victory, 6, True),
         ('ko', ko, 6, False), ('burst', burst, 12, False), ('guard', guard, 6, False)]


# ------------------------------------------------------------------ portrait (96x96 bust, same ramps as the sprite)
def portrait():
    cv = Canvas(96, 96)
    hx, hy = 50, 40
    # sword hilt rising behind the back shoulder (identity: the blade)
    cv.part(limb(cv, (13, 38), (26, 58), 5, 5), LEATHER, 'leather', 'cyl_h', cast=False)
    cv.part(cv.mask().ellipse(12, 36, 3, 3), GOLD, 'metal')
    cv.part(limb(cv, (18, 64), (34, 54), 5, 5), GOLD, 'metal', cast=False)
    # shoulders / torso
    cv.part(cv.mask().poly([(14, 96), (20, 72), (38, 64), (64, 64), (82, 72), (88, 96)]), TUNIC, 'cloth', 'cyl_v', bias=-0.25)
    cv.part(cv.mask().poly([(18, 96), (24, 74), (40, 68), (46, 96)]), LEATHER, 'leather', 'cyl_v')
    cv.part(cv.mask().poly([(60, 68), (78, 74), (84, 96), (64, 96)]), LEATHER, 'leather', 'cyl_v')
    # back hair
    back = cv.mask().ellipse(hx - 4, hy - 6, 20, 19)
    back.poly([(hx - 14, hy - 14), (hx - 36, hy - 20), (hx - 18, hy)])
    back.poly([(hx - 16, hy), (hx - 34, hy + 4), (hx - 16, hy + 12)])
    back.poly([(hx - 8, hy - 20), (hx - 22, hy - 38), (hx + 2, hy - 22)])
    cv.part(back, HAIR, 'hair')
    # neck + face
    cv.part(limb(cv, (hx - 2, hy + 14), (hx - 1, hy + 26), 12, 12), SKIN, 'skin', 'cyl_v', bias=-0.2)
    face = cv.mask().ellipse(hx + 2, hy + 2, 16, 16)
    face.poly([(hx - 8, hy + 10), (hx + 17, hy + 6), (hx + 12, hy + 20), (hx - 2, hy + 21)])
    cv.part(face, SKIN, 'skin')
    cv.part(cv.mask().ellipse(hx - 8, hy + 5, 3.5, 5), SKIN, 'skin', bias=-0.3)
    for pts in ([(hx - 9, hy - 14), (hx + 15, hy - 14), (hx + 20, hy - 2), (hx + 9, hy - 8)],
                [(hx - 2, hy - 16), (hx + 8, hy - 34), (hx + 11, hy - 14)],
                [(hx + 6, hy - 16), (hx + 24, hy - 26), (hx + 17, hy - 9)],
                [(hx - 13, hy - 12), (hx - 3, hy - 30), (hx + 2, hy - 15)],
                [(hx - 11, hy - 10), (hx - 4, hy - 12), (hx - 6, hy + 3)],
                [(hx + 12, hy - 10), (hx + 19, hy - 6), (hx + 18, hy + 4)]):
        cv.part(cv.mask().poly(pts), HAIR, 'hair', 'flat', normal=(-0.2, -0.6, 1))
    cv.part(cv.mask().poly([(hx - 15, hy - 10), (hx + 14, hy - 14), (hx + 14, hy - 10), (hx - 15, hy - 6)]), SCARF, 'cloth', 'cyl_v', cast=False)
    # eyes: 3/4 view, near eye larger. Determined: flat brow, iris with 1px highlight
    def eye(x, y, w):
        for yy in range(y, y + 5):
            for xx in range(x, x + w):
                cv.dot(xx, yy, EYE)
        for xx in range(x + 1, x + w - 1):
            cv.dot(xx, y + 2, '#8e2a1e')
            cv.dot(xx, y + 3, '#c4471e')
        cv.dot(x + 1, y + 1, EYE_HI)
        for xx in range(x - 1, x + w + 1):
            cv.dot(xx, y - 2, HAIR[1])
        cv.dot(x + w, y - 1, HAIR[1])
    eye(hx + 6, hy + 2, 5)
    eye(hx - 4, hy + 3, 4)
    cv.pixels([(hx + 5, hy + 10), (hx + 5, hy + 11)], SKIN[1])                # nose shade
    cv.pixels([(hx + 3, hy + 15), (hx + 4, hy + 15), (hx + 5, hy + 15), (hx + 6, hy + 14)], SKIN[0])   # set mouth
    # scarf wrap + pauldron in front
    cv.part(limb(cv, (30, 70), (62, 96), 6, 6), LEATHER, 'leather', 'flat', normal=(0, -0.2, 1), bias=0.2)       # chest strap
    cv.part(cv.mask().ellipse(46, 83, 2.5, 2.5), GOLD, 'metal', cast=False)
    cv.part(cv.mask().ellipse(hx - 1, hy + 28, 22, 7).poly([(hx - 14, hy + 30), (hx + 8, hy + 30), (hx - 6, hy + 46)]), SCARF, 'cloth', 'cyl_v')
    for a, b in (((hx - 16, hy + 27), (hx - 4, hy + 33)), ((hx + 2, hy + 25), (hx + 12, hy + 30)), ((hx - 8, hy + 34), (hx - 5, hy + 42))):
        cv.part(cv.mask().line(*a, *b, 1), SCARF, 'cloth', 'flat', bias=-0.9, sep=False, cast=False)   # scarf folds
    p = cv.mask().poly([(58, 76), (76, 66), (92, 74), (92, 90), (66, 92)])
    cv.part(p, STEEL, 'metal')
    cv.part(cv.mask().poly([(62, 90), (92, 88), (92, 93), (64, 95)]), GOLD, 'metal', 'flat', normal=(0, 0.2, 1), cast=False)
    cv.cleanup().outline()
    return cv.image()


# ------------------------------------------------------------------ export
def main():
    os.makedirs(OUT, exist_ok=True)
    rows = [(n, fn(), fps, loop) for n, fn, fps, loop in ANIMS]
    cols = max(len(r[1]) for r in rows)
    sheet = Image.new('RGBA', (cols * FW, len(rows) * FH), (0, 0, 0, 0))
    meta = {'frame_size': [FW, FH], 'pivot': [FW // 2, GROUND], 'animations': {}}
    for ri, (name, frames, fps, loop) in enumerate(rows):
        for ci, im in enumerate(frames):
            sheet.paste(im, (ci * FW, ri * FH), im)
        meta['animations'][name] = {'row': ri, 'frames': len(frames), 'fps': fps, 'loop': loop}
    sheet.save(os.path.join(OUT, 'kael_emberclaw_sheet.png'))
    with open(os.path.join(OUT, 'kael_emberclaw_sheet.json'), 'w') as f:
        json.dump(meta, f, indent=1)
    pr = portrait()
    pr.save(os.path.join(OUT, 'kael_emberclaw_portrait.png'))
    print('kael: sheet', sheet.size, 'colours', colours(sheet), '| portrait colours', colours(pr))


if __name__ == '__main__':
    main()
