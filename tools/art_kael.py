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
    """Hands are offsets from their shoulder; feet are absolute (x shifted by ox)."""
    def __init__(self, **kw):
        self.ox = 0; self.oy = 0; self.crouch = 0; self.lean = 2
        self.f_foot = (55, GROUND); self.b_foot = (38, GROUND)
        self.f_hand = (8, 17); self.b_hand = (-2, 20)
        self.head_dx = 0; self.head_dy = 0
        self.eyes = 'open'; self.blade = 30; self.blade_front = True
        self.breath = 0; self.wind = 0.0; self.embers = 0
        self.smear = None; self.aura = 0; self.back_hand_on_hilt = False; self.no_blade = False
        self.__dict__.update(kw)


# Human landmarks (~5.3 heads): crown 20, chin 33, shoulders 35, elbow ~49 (waist),
# hip joint 56, wrist ~57 (crotch), knee ~71, ankle 85, ground 88.
HIP_Y, TORSO, THIGH, SHIN, UPPER, FORE = 56, 21, 16, 15, 13, 11


def skel(p):
    hip = (46 + p.ox, HIP_Y + p.oy + p.crouch)
    sh = (hip[0] + p.lean, hip[1] - TORSO + p.breath)
    head = (sh[0] + 2 + p.head_dx, sh[1] - 9 + p.head_dy)
    fsh, bsh = (sh[0] + 3, sh[1] + 1), (sh[0] - 4, sh[1] + 1)
    fh = (fsh[0] + p.f_hand[0], fsh[1] + p.f_hand[1])
    bh = (bsh[0] + p.b_hand[0], bsh[1] + p.b_hand[1])
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


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def leg(cv, hip, foot, back):
    ankle = (foot[0] - 1, foot[1] - 3)
    knee = ik(hip, ankle, THIGH, SHIN, bend=-1)
    bias = -0.3 if back else 0.0
    cv.part(limb(cv, hip, knee, 7, 5.5), TROUSER, 'cloth', 'cyl_v', bias=bias)          # thigh tapers to the knee
    cv.part(limb(cv, knee, ankle, 5.5, 4), TROUSER, 'cloth', 'cyl_v', bias=bias)        # calf
    top = lerp(knee, ankle, 0.35)                                                         # boots reach mid-calf
    boot = limb(cv, top, ankle, 5.5, 5)
    boot.poly([(ankle[0] - 3, ankle[1] - 1), (ankle[0] + 2, ankle[1] - 2), (foot[0] + 6, foot[1] - 2),
               (foot[0] + 6, foot[1]), (ankle[0] - 3, foot[1])])
    cv.part(boot, LEATHER, 'leather', bias=bias - 0.1)
    if not back:   # black steel greave on the front shin
        cv.part(limb(cv, lerp(knee, ankle, 0.12), lerp(knee, ankle, 0.6), 4, 3.5), STEEL, 'metal', 'cyl_v', cast=False)
        cv.part(cv.mask().ellipse(knee[0] + 0.5, knee[1], 2.2, 2), STEEL, 'metal', cast=False)   # knee cop
    return knee


def torso(cv, s, p):
    (hx, hy), (sx, sy) = s['hip'], s['sh']
    body = [(sx - 7, sy - 1), (sx + 5, sy - 1), (sx + 7, sy + 5), (hx + 5, hy - 9), (hx + 6, hy),
            (hx + 5, hy + 3), (hx - 6, hy + 3), (hx - 6, hy), (hx - 5, hy - 9), (sx - 8, sy + 6)]
    cv.part(cv.mask().poly(body), TUNIC, 'cloth', 'cyl_v')
    # leather jerkin, open over the chest
    cv.part(cv.mask().poly([(sx - 8, sy), (sx + 2, sy), (hx + 1, hy - 4), (hx - 6, hy - 4), (hx - 5, hy - 9), (sx - 8, sy + 6)]),
            LEATHER, 'leather', 'cyl_v')
    cv.part(cv.mask().poly([(sx + 5, sy + 1), (sx + 7, sy + 5), (hx + 5, hy - 5), (hx + 3, hy - 4)]), LEATHER, 'leather', 'cyl_v')
    # harness strap across the chest
    cv.part(limb(cv, (sx - 6, sy + 1), (hx + 4, hy - 5), 2.5, 2.5), LEATHER, 'leather', 'flat', normal=(0, -0.2, 1), bias=0.25)
    cv.part(cv.mask().ellipse((sx + hx) / 2 - 1, (sy + hy) / 2 - 2, 1.3, 1.3), GOLD, 'metal', cast=False)
    # belt, buckle, short tabard (ends above the knee)
    cv.part(cv.mask().poly([(hx - 6, hy - 5), (hx + 6, hy - 6), (hx + 6, hy - 3), (hx - 6, hy - 2)]), LEATHER, 'leather', 'cyl_v')
    cv.part(cv.mask().rect(hx + 2, hy - 6, hx + 4, hy - 3), GOLD, 'metal', 'flat', normal=(-0.3, -0.4, 1))
    cv.part(cv.mask().poly([(hx - 6, hy - 2), (hx - 1, hy - 2), (hx - 5, hy + 6)]), TUNIC, 'cloth', bias=-0.25)
    cv.part(cv.mask().poly([(hx - 1, hy - 3), (hx + 6, hy - 3), (hx + 6, hy + 5), (hx + 3, hy + 9), (hx, hy + 5)]), TUNIC, 'cloth')


def neck(cv, s):
    (hx, hy), (sx, sy) = s['head'], s['sh']
    cv.part(limb(cv, (hx - 1, hy + 4), (sx + 1, sy), 4, 4.5), SKIN, 'skin', 'cyl_v', bias=-0.25)


def head(cv, s, p):
    hx, hy = s['head']
    back = cv.mask().ellipse(hx - 1.5, hy - 2.5, 6.5, 6)          # back hair mass + swept spikes
    back.poly([(hx - 5, hy - 5), (hx - 13, hy - 8), (hx - 6, hy - 1)])
    back.poly([(hx - 5, hy - 1), (hx - 12, hy + 1), (hx - 5, hy + 3)])
    back.poly([(hx - 3, hy - 6), (hx - 8, hy - 12), (hx, hy - 7)])
    cv.part(back, HAIR, 'hair')
    face = cv.mask().ellipse(hx + 0.5, hy, 5.5, 6.5)               # oval skull, taller than wide
    face.poly([(hx - 3, hy + 3), (hx + 5, hy + 1), (hx + 6.5, hy + 1), (hx + 6, hy + 2.5), (hx + 5, hy + 5),
               (hx + 2, hy + 7), (hx - 2, hy + 6)])                 # nose bump + jaw pointing forward-down
    cv.part(face, SKIN, 'skin')
    cv.part(cv.mask().ellipse(hx - 2.5, hy + 1, 1.2, 1.8), SKIN, 'skin', bias=-0.35)   # ear
    for pts in ([(hx - 3, hy - 6), (hx + 5, hy - 6), (hx + 7, hy - 2), (hx + 3, hy - 3)],
                [(hx - 1, hy - 6), (hx + 3, hy - 11), (hx + 4, hy - 6)],
                [(hx + 2, hy - 6), (hx + 8, hy - 9), (hx + 6, hy - 4)],
                [(hx - 5, hy - 5), (hx - 1, hy - 11), (hx + 1, hy - 6)],
                [(hx - 3, hy - 4), (hx - 1, hy - 5), (hx - 2, hy + 2)]):
        cv.part(cv.mask().poly(pts), HAIR, 'hair', 'flat', normal=(-0.2, -0.6, 1))
    cv.part(cv.mask().poly([(hx - 5, hy - 4), (hx + 5, hy - 5), (hx + 5, hy - 3), (hx - 5, hy - 2)]), SCARF, 'cloth', 'cyl_v', cast=False)
    ex, ey = hx + 3, hy
    e = p.eyes
    if e in ('open', 'fierce'):
        cv.pixels([(ex, ey), (ex, ey + 1), (ex + 1, ey + 1)], EYE)
        cv.dot(ex + 1, ey, EYE_HI)
        cv.pixels([(ex - 1, ey - 2), (ex, ey - 2), (ex + 1, ey - 2) if e == 'open' else (ex + 1, ey - 1)], HAIR[1])
    elif e == 'closed':
        cv.pixels([(ex, ey + 1), (ex + 1, ey + 1)], EYE)
    elif e == 'hurt':
        cv.pixels([(ex, ey), (ex + 1, ey + 1)], EYE)
        cv.pixels([(ex - 1, ey - 1), (ex, ey - 2)], HAIR[1])
    elif e == 'ko':
        cv.pixels([(ex, ey), (ex + 1, ey + 1), (ex + 1, ey)], EYE)
    cv.pixels([(hx + 3, hy + 4), (hx + 4, hy + 4)] if e != 'hurt' else [(hx + 3, hy + 4), (hx + 4, hy + 5)], SKIN[0])


def back_cloth(cv, s, p):
    """Scarf tail + headband tails, blown back; `wind` animates them."""
    hx, hy = s['head']
    sx, sy = s['sh']
    w = p.wind
    cv.part(cv.mask().poly([(sx - 3, sy - 2), (sx - 1, sy + 1), (sx - 10 - w, sy + 5 + w * 0.4), (sx - 16 - w * 1.3, sy + 3 + w),
                            (sx - 12 - w, sy)]), SCARF, 'cloth', 'flat', normal=(-0.1, -0.3, 1))
    cv.part(cv.mask().poly([(hx - 5, hy - 4), (hx - 12 - w, hy - 2 + w * 0.4), (hx - 15 - w * 1.2, hy + 1 + w * 0.3), (hx - 6, hy - 2)]),
            SCARF, 'cloth', 'flat', normal=(0, -0.2, 1), bias=-0.2)


def scarf_wrap(cv, s):
    sx, sy = s['sh']
    m = cv.mask().ellipse(sx + 1, sy - 1, 5, 2.4)
    m.poly([(sx - 3, sy), (sx + 4, sy - 1), (sx + 1, sy + 5), (sx - 2, sy + 4)])
    cv.part(m, SCARF, 'cloth', 'cyl_v')


def arm(cv, shoulder, hand, front, bend):
    elbow = ik(shoulder, hand, UPPER, FORE, bend=bend)
    bias = 0.0 if front else -0.35
    cv.part(cv.mask().ellipse(shoulder[0], shoulder[1] + 1, 2.8, 3), TUNIC, 'cloth', bias=bias)       # deltoid
    cv.part(limb(cv, shoulder, elbow, 5, 4), TUNIC, 'cloth', 'cyl_v', bias=bias)
    cv.part(limb(cv, elbow, hand, 4.5, 3.5), LEATHER, 'leather', 'cyl_v', bias=bias)               # bracer
    cv.part(cv.mask().ellipse(hand[0], hand[1], 2, 2), STEEL if front else SKIN, 'metal' if front else 'skin', bias=bias)
    return elbow


def pauldron(cv, fsh):
    x, y = fsh
    cv.part(cv.mask().poly([(x - 4, y - 2), (x + 1, y - 4), (x + 5, y - 1), (x + 4, y + 3), (x - 2, y + 4)]), STEEL, 'metal')
    cv.part(cv.mask().poly([(x - 2, y + 3), (x + 4, y + 2), (x + 4, y + 4), (x - 2, y + 5)]), GOLD, 'metal', 'flat', normal=(0, 0.3, 1), cast=False)


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
    L = 30
    blade = cv.mask().poly([at(4, -3), at(L - 8, -3.6), at(L, 1.5), at(L - 4, 3.6), at(4, 3.6)])
    cv.part(blade, STEEL, 'metal', 'flat', normal=(-0.2, -0.5, 1), cast=False, bias=-0.55)
    edge = cv.mask()
    for t in range(5, L - 7):
        edge.set(*at(t, -2.6))
    for k in range(8):
        edge.set(*at(L - 8 + k, -2.8 + k * 0.55))
    cv.part(edge, STEEL, 'metal', 'flat', normal=(-0.6, -0.8, 0.5), sep=False, cast=False, bias=0.2)
    # ember cracks: three 2-3px glowing notches along the spine, brightness steps with `embers`
    for i, t in enumerate((9, 15, 21)):
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
    bh = s['bh'] if not p.back_hand_on_hilt else (s['fh'][0] - 3, s['fh'][1] + 2)
    arm(cv, s['bsh'], bh, False, bend=1)
    leg(cv, s['hip'], s['bf'], True)
    leg(cv, s['hip'], s['ff'], False)
    torso(cv, s, p)
    neck(cv, s)
    if not p.blade_front and not p.no_blade:
        sword(cv, s['fh'], p.blade, p.embers)
    head(cv, s, p)
    scarf_wrap(cv, s)
    arm(cv, s['fsh'], s['fh'], True, bend=-1)
    pauldron(cv, s['fsh'])
    if p.blade_front and not p.no_blade:
        sword(cv, s['fh'], p.blade, p.embers)
        # fist over the grip
        cv.part(cv.mask().ellipse(s['fh'][0], s['fh'][1], 2, 2), STEEL, 'metal', cast=False)
    if p.smear:   # (dx, dy) from the front shoulder, r0, r1, a0, a1, thick
        dx, dy, *rest = p.smear
        smear(cv, (s['fsh'][0] + dx, s['fsh'][1] + dy), *rest)
    cv.cleanup().outline()
    return cv.image()


# ------------------------------------------------------------------ animations (counts/hit frames match data/skills)
G = GROUND


def idle():
    out = []
    for i in range(6):
        k = math.sin(i / 6 * math.tau)
        up = 1 if k > 0.3 else 0
        out.append(frame(Pose(breath=up, wind=1.5 + k * 1.5, embers=i % 3, f_hand=(8, 17 - up))))
    return out


LUNGE = dict(ox=10, f_foot=(60, G), b_foot=(34, G), eyes='fierce')


def attack():
    P = Pose
    return [frame(P(crouch=2, lean=1, f_hand=(-8, 8), blade=-150, blade_front=False, wind=2, b_hand=(-4, 16))),
            frame(P(crouch=3, lean=-1, f_hand=(-10, 4), blade=-165, blade_front=False, wind=3, eyes='fierce', b_hand=(-5, 14))),
            frame(P(crouch=2, lean=6, f_hand=(18, 12), blade=8, wind=5, smear=(-4, 6, 16, 26, -110, 20, 5), **LUNGE)),
            frame(P(crouch=4, lean=7, f_hand=(14, 20), blade=55, wind=6, **LUNGE)),
            frame(P(crouch=1, lean=5, f_hand=(15, 2), blade=-60, wind=6, smear=(-2, 12, 15, 24, 70, -70, 5), **LUNGE)),
            frame(P(ox=5, crouch=1, lean=4, f_hand=(12, 14), blade=-10, wind=4)),
            frame(P(wind=2))]


def hit():
    return [frame(Pose(ox=-3, lean=-3, head_dx=-2, eyes='hurt', f_hand=(6, 18), blade=45, wind=4)),
            frame(Pose(ox=-5, lean=-5, head_dx=-2, head_dy=1, eyes='hurt', f_hand=(4, 19), blade=60, wind=5)),
            frame(Pose(ox=-2, lean=0, f_hand=(7, 17), blade=35, wind=3))]


def guard():
    g = dict(crouch=4, lean=1, f_hand=(8, 8), blade=-95, back_hand_on_hilt=True, eyes='fierce')
    return [frame(Pose(crouch=2, lean=2, f_hand=(9, 12), blade=-60, wind=2)),
            frame(Pose(wind=2, **g)),
            frame(Pose(wind=3, breath=1, **g))]


def victory():
    return [frame(Pose(f_hand=(6, 6), blade=-120, wind=2, eyes='closed')),
            frame(Pose(f_hand=(4, -4), blade=-60, wind=3, smear=(0, -6, 12, 17, -200, -40, 3))),
            frame(Pose(f_hand=(3, -10), blade=-80, wind=4, embers=1, eyes='fierce')),
            frame(Pose(f_hand=(3, -10), blade=-82, wind=2, embers=2, eyes='fierce', breath=1))]


def ko():
    kneel = frame(Pose(crouch=10, lean=7, head_dx=2, head_dy=3, eyes='hurt', f_hand=(6, 21), blade=80,
                       f_foot=(58, G), b_foot=(36, G), wind=0))
    down = frame(Pose(eyes='ko', f_hand=(6, 18), no_blade=True, wind=0)).rotate(90, expand=False)
    bb = down.getbbox()
    gs = Canvas(FW, FH)
    sword(gs, (16, G - 2), -4)
    gs.cleanup().outline()
    lying = gs.image()
    if bb:
        c = down.crop(bb)
        lying.paste(c, (FW // 2 - c.width // 2, G + 1 - c.height), c)
    return [kneel, lying]


def burst():
    P = Pose
    L = dict(ox=12, f_foot=(60, G), b_foot=(34, G), eyes='fierce')
    return [frame(P(crouch=4, lean=0, f_hand=(-10, 8), blade=-160, blade_front=False, aura=1, eyes='fierce', wind=3)),
            frame(P(crouch=5, lean=-1, f_hand=(-12, 5), blade=-170, blade_front=False, aura=2, embers=1, eyes='fierce', wind=4)),
            frame(P(crouch=3, lean=8, f_hand=(12, 14), blade=-20, aura=1, embers=2, wind=7, **L)),
            frame(P(crouch=2, lean=7, f_hand=(18, 12), blade=10, wind=7, smear=(-4, 6, 16, 26, -110, 25, 5), **L)),
            frame(P(crouch=3, lean=6, f_hand=(14, 20), blade=60, embers=1, wind=6, **L)),
            frame(P(crouch=1, lean=5, f_hand=(15, 2), blade=-55, embers=2, wind=7, smear=(-2, 12, 15, 24, 70, -75, 5), **L)),
            frame(P(crouch=3, lean=4, f_hand=(-6, 6), blade=-150, blade_front=False, wind=6, **L)),
            frame(P(crouch=2, lean=8, f_hand=(18, 14), blade=18, embers=1, wind=8, smear=(-4, 8, 16, 26, -120, 30, 6), **L)),
            frame(P(ox=10, oy=-12, lean=3, f_hand=(4, -14), blade=-95, embers=2, eyes='fierce', wind=8, aura=1,
                    f_foot=(57, G - 4), b_foot=(39, G - 2))),
            frame(P(crouch=6, lean=9, f_hand=(16, 22), blade=75, wind=9, aura=3, smear=(-2, 0, 18, 28, -95, 80, 7), **L)),
            frame(P(ox=6, crouch=2, lean=4, f_hand=(12, 16), blade=20, embers=1, wind=4, aura=1))]


ANIMS = [('idle', idle, 6, True), ('attack', attack, 14, False), ('hit', hit, 10, False), ('victory', victory, 6, True),
         ('ko', ko, 6, False), ('burst', burst, 12, False), ('guard', guard, 6, False)]


# ------------------------------------------------------------------ portrait (96x96 bust, same ramps as the sprite)
def portrait():
    """Head-and-shoulders bust with adult proportions: oval face, defined jaw, neck, broad shoulders."""
    cv = Canvas(96, 96)
    hx, hy = 52, 36                                     # face centre
    # sword hilt rising behind the back shoulder (identity: the blade)
    cv.part(limb(cv, (16, 34), (26, 54), 5, 5), LEATHER, 'leather', 'cyl_h', cast=False)
    cv.part(cv.mask().ellipse(15, 32, 3, 3), GOLD, 'metal')
    cv.part(limb(cv, (18, 60), (34, 50), 5, 5), GOLD, 'metal', cast=False)
    # shoulders / chest
    cv.part(cv.mask().poly([(2, 96), (8, 72), (30, 62), (70, 62), (90, 70), (96, 80), (96, 96)]), TUNIC, 'cloth', 'cyl_v', bias=-0.25)
    cv.part(cv.mask().poly([(4, 96), (10, 74), (32, 66), (46, 96)]), LEATHER, 'leather', 'cyl_v')
    cv.part(cv.mask().poly([(62, 66), (84, 72), (90, 96), (66, 96)]), LEATHER, 'leather', 'cyl_v')
    cv.part(limb(cv, (22, 70), (60, 96), 6, 6), LEATHER, 'leather', 'flat', normal=(0, -0.2, 1), bias=0.2)       # chest strap
    cv.part(cv.mask().ellipse(40, 82, 2.5, 2.5), GOLD, 'metal', cast=False)
    # back hair
    back = cv.mask().ellipse(hx - 5, hy - 7, 15, 14)
    back.poly([(hx - 12, hy - 12), (hx - 30, hy - 16), (hx - 16, hy - 2)])
    back.poly([(hx - 14, hy - 2), (hx - 28, hy + 2), (hx - 14, hy + 8)])
    back.poly([(hx - 8, hy - 17), (hx - 18, hy - 32), (hx, hy - 19)])
    cv.part(back, HAIR, 'hair')
    # neck (trapezius slopes into the shoulders)
    cv.part(cv.mask().poly([(hx - 9, hy + 10), (hx + 5, hy + 12), (hx + 7, hy + 26), (hx + 16, hy + 30), (hx - 20, hy + 30), (hx - 9, hy + 24)]),
            SKIN, 'skin', 'cyl_v', bias=-0.25)
    # face: oval skull, straight nose line, jaw angling to a firm chin
    face = cv.mask().ellipse(hx, hy - 2, 11, 13)
    face.poly([(hx - 10, hy + 2), (hx + 10, hy - 2), (hx + 13, hy + 2), (hx + 12, hy + 6), (hx + 10, hy + 13),
               (hx + 5, hy + 19), (hx - 1, hy + 18), (hx - 7, hy + 12)])
    cv.part(face, SKIN, 'skin')
    cv.part(cv.mask().ellipse(hx - 8, hy + 3, 2.5, 4), SKIN, 'skin', bias=-0.35)   # ear
    for pts in ([(hx - 8, hy - 12), (hx + 11, hy - 13), (hx + 15, hy - 4), (hx + 7, hy - 8)],
                [(hx - 2, hy - 14), (hx + 6, hy - 28), (hx + 9, hy - 13)],
                [(hx + 5, hy - 14), (hx + 20, hy - 22), (hx + 14, hy - 8)],
                [(hx - 11, hy - 11), (hx - 3, hy - 26), (hx + 1, hy - 13)],
                [(hx - 10, hy - 9), (hx - 4, hy - 10), (hx - 6, hy + 4)],
                [(hx + 9, hy - 9), (hx + 14, hy - 6), (hx + 13, hy + 1)]):
        cv.part(cv.mask().poly(pts), HAIR, 'hair', 'flat', normal=(-0.2, -0.6, 1))
    cv.part(cv.mask().poly([(hx - 12, hy - 9), (hx + 12, hy - 12), (hx + 12, hy - 9), (hx - 12, hy - 6)]), SCARF, 'cloth', 'cyl_v', cast=False)

    def eye(x, y, w):   # almond eye: lid line, iris, 1px catch-light, brow
        for xx in range(x, x + w):
            cv.dot(xx, y, EYE)
            cv.dot(xx, y + 1, '#8e2a1e' if 0 < xx - x < w - 1 else EYE)
            cv.dot(xx, y + 2, '#c4471e' if 0 < xx - x < w - 1 else SKIN[1])
        cv.dot(x + 1, y + 1, EYE_HI)
        for xx in range(x - 1, x + w + 1):
            cv.dot(xx, y - 3, HAIR[1])
        cv.dot(x + w, y - 2, HAIR[1])
    eye(hx + 4, hy + 1, 4)
    eye(hx - 5, hy + 2, 3)
    cv.pixels([(hx + 10, hy + 3), (hx + 11, hy + 5), (hx + 11, hy + 6), (hx + 10, hy + 8), (hx + 9, hy + 8)], SKIN[1])   # nose
    cv.pixels([(hx + 4, hy + 12), (hx + 5, hy + 12), (hx + 6, hy + 12), (hx + 7, hy + 11)], SKIN[0])                  # mouth
    cv.pixels([(hx - 6, hy + 10), (hx - 5, hy + 12), (hx - 3, hy + 14)], SKIN[1])                                     # jaw shade
    # scarf wrap + pauldron in front
    cv.part(cv.mask().ellipse(hx - 3, hy + 25, 19, 6).poly([(hx - 15, hy + 27), (hx + 6, hy + 27), (hx - 8, hy + 42)]), SCARF, 'cloth', 'cyl_v')
    for a, b in (((hx - 17, hy + 24), (hx - 5, hy + 30)), ((hx + 1, hy + 22), (hx + 11, hy + 27)), ((hx - 10, hy + 31), (hx - 7, hy + 39))):
        cv.part(cv.mask().line(*a, *b, 1), SCARF, 'cloth', 'flat', bias=-0.9, sep=False, cast=False)   # scarf folds
    cv.part(cv.mask().poly([(62, 74), (80, 64), (96, 70), (96, 88), (68, 90)]), STEEL, 'metal')
    cv.part(cv.mask().poly([(66, 88), (96, 86), (96, 91), (68, 93)]), GOLD, 'metal', 'flat', normal=(0, 0.2, 1), cast=False)
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
