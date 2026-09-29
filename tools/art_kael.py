"""
Kael - Phase 6 art for all three forms: 3* Emberclaw, 4* Blazeheart, 5* Cinderlord.
Design sheet: docs/art/characters/kael.md.  Run: python3 tools/art_kael.py

Battle sprite: 96x96 frames, feet on row 88, faces RIGHT (the game flips players to face the enemies).
Heroic chibi body (~3 heads incl. hair) with a real torso/limbs; the face is HAND-PIXELLED (both eyes,
3/4 toward the viewer) and stamped on top of shaded hair shapes.
Portrait: a separate front-facing bust (not the battle pose), same person/colours.
Evolution = story: 4* gets a breastplate, cape and an ember-edged blade; 5* dark plate, horned
pauldron, flame-hemmed cape, a burning blade and flame-lit hair.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image
from pixlib import hexc
from px6 import Canvas, Ramp, colours
from rig import ik

FW = FH = 96
GROUND = 88
ROOT = os.path.join(os.path.dirname(__file__), '..', 'Content', 'assets', 'characters')
FORMS = {3: 'kael_emberclaw', 4: 'kael_blazeheart', 5: 'kael_cinderlord'}
FORM = 3

# ------------------------------------------------------------------ palette (dark -> light, hue shifted)
SKIN = Ramp('#4a2426', '#9c5a48', '#d98e6c', '#f2b68c', '#ffd9b4')
HAIR = Ramp('#1e0f14', '#3e1a1a', '#66281f', '#8e3a26', '#b8583a')
FLAME = Ramp('#8a1a0e', '#e0521c', '#ff8a2a', '#ffc15a', '#ffef9a')
TUNIC = Ramp('#2a0a14', '#5a1420', '#8e1f26', '#c43a2e', '#e8653e')
SCARF = Ramp('#2e0a12', '#6e1a1e', '#b02a24', '#e04a2c', '#ff7a40')
CAPE = Ramp('#1e060c', '#4a0e16', '#7a1820', '#a82a26', '#d0482e')
LEATHER = Ramp('#1a0f12', '#3a2220', '#5a3628', '#7a4e36', '#9a6a48')
STEEL = Ramp('#0e0e16', '#262634', '#3e3e52', '#62647a', '#9aa0b8', '#e6ecf5')
DARK = Ramp('#08070c', '#1a1720', '#2c2834', '#46404f', '#6e6678', '#b8b0c4')
GOLD = Ramp('#2a1608', '#6a3e10', '#a86a1a', '#e0a232', '#ffe07a')
HORN = Ramp('#1a1216', '#3a2a2a', '#5e4640', '#86685a', '#b89480')
TROUSER = Ramp('#120c16', '#241a2a', '#3a2c40', '#524258', '#6a5a70')
EMBER = ['#ff5a1e', '#ffa02a', '#ffe070']
SMEAR = [(255, 122, 48, 255), (255, 200, 90, 255), (255, 246, 200, 255)]


def armour():
    return DARK if FORM == 5 else STEEL


# ------------------------------------------------------------------ hand-pixelled face (3/4 toward the viewer)
FACE = [   # headband + bangs + face; chin is row 16, col 12. Light from the upper left.
    ".ohhhHrrrrrrrrrrrrrrrrrro",
    "ohhhhrRRRRRRRRRRRRRRRRdo.",
    ".ohhhHdHHddHHdddHHdddHHo.",
    "ohhhHoHSHHoSHHoSSHHoSHHo.",
    ".ohhhosssHsssssHssssHsso.",     # the bangs cast a shadow across the forehead
    "..ohhKKSSSSSSSSSSSSSSSso.",
    "..ohsKbbbSSSSSSbbbbSSso..",     # brows
    "..oKsKeeeSSSSSSeeeeSSso..",     # eyes: same design; the near eye shows one more column of white
    "..oKsSwkeSSSSSSWwkeSso...",
    "..oSsSikiSSSSSSWikiSso...",
    "...osSsIsSSSSSSssIsSso...",
    "...osSSSSSSSSsSSSSSso....",     # nose shade
    "....osSSSSSSSSssSSSso....",
    ".....osSSSSSSmmmSSso.....",
    "......ossSSSSSSSSso......",
    "........ossssssso........",
    "..........ooooo..........",
]
EXPR = {   # replacement rows 6..10 (brows + eyes)
    'fierce': ["..ohsKbbSSSSSSSSbbbSSso..", "..oKsKeeeSSSSSSeeeeSSso..", "..oKsSwkeSSSSSSWwkeSso...",
               "..oSsSikiSSSSSSWikiSso...", "...osSsIsSSSSSSssIsSso..."],
    'closed': ["..ohsKbbbSSSSSSbbbbSSso..", "..oKsKSSSSSSSSSSSSSSSso..", "..oKsSeeeSSSSSSeeeeSso...",
               "..oSsSSSSSSSSSSSSSSSso...", "...osSsSsSSSSSSssSsSso..."],
    'hurt': ["..ohsKbSSSSSSSSSSSbbSso..", "..oKsKeSSSSSSSSSSSeSSso..", "..oKsSSeeSSSSSSSeeSSso...",
             "..oSsSeSSSSSSSSSSSeSso...", "...osSsSsSSSSSSssSsSso..."],
    'ko': ["..ohsKSSSSSSSSSSSSSSSso..", "..oKsKeSeSSSSSSSeSeSso...", "..oKsSSeSSSSSSSSSeSSso...",
           "..oSsSeSeSSSSSSSeSeSso...", "...osSsSsSSSSSSssSsSso..."],
}


def face_pal():
    band = GOLD if FORM == 5 else SCARF
    return {'o': HAIR[0], 'h': HAIR[1], 'H': HAIR[3], 'd': band[1], 'r': band[2], 'R': band[3],
            's': SKIN[2], 'S': SKIN[3], 'K': SKIN[4], 'b': HAIR[1], 'e': hexc('#241016'), 'k': hexc('#1a0a10'),
            'W': hexc('#f4ece4'), 'w': hexc('#ffffff'), 'i': hexc('#b0381c') if FORM < 5 else hexc('#e0601a'),
            'I': hexc('#ff8a4a') if FORM < 5 else hexc('#ffe07a'), 'm': SKIN[1]}


def face_img(expr):
    rows = list(FACE)
    if expr in EXPR:
        rows[6:11] = EXPR[expr]
    pal = face_pal()
    im = Image.new('RGBA', (25, len(rows)), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        for x, c in enumerate(r.ljust(25, '.')):
            if c in pal:
                im.putpixel((x, y), pal[c])
    return im


SPIKES = [((2, 26), (9, 20), (9, 27)), ((0, 16), (9, 14), (11, 21)), ((6, 2), (10, 15), (17, 11)),
          ((17, 0), (14, 12), (22, 11)), ((28, 3), (20, 12), (27, 14)), ((35, 11), (25, 13), (29, 18))]


def head_img(expr):
    """36x36: shaded hair shapes (+ flame tips on evolved forms) behind the hand-pixelled face."""
    cv = Canvas(36, 36)
    cv.part(cv.mask().ellipse(18, 17, 12, 8), HAIR, 'hair')
    tip = {3: 0.0, 4: 0.38, 5: 0.6}[FORM]
    for t, a, b in SPIKES:
        m = cv.mask().poly([t, a, b])
        cv.part(m, HAIR, 'hair', 'flat', normal=(-0.25, -0.6, 1))
        if tip:
            base_y = (a[1] + b[1]) / 2
            for y, x in zip(*m.m.nonzero()):
                r = (y - t[1]) / max(1.0, (base_y - t[1]) * tip)   # 0 at the tip -> 1 where the flame ends
                if r < 1:
                    cv.px[y, x] = FLAME[4 - min(3, int(r * 3.2 + (cv.band[y, x] < 2)))]
    cv.stamp(face_img(expr), 5, 17, HAIR)
    return cv.image()


# ------------------------------------------------------------------ skeleton
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


# heroic chibi on a human frame: chin 40, shoulders 41, hip 60, knee ~73, ankle 85
HIP_Y, TORSO, THIGH, SHIN, UPPER, FORE = 60, 19, 13, 13, 11, 9.5


def skel(p):
    hip = (46 + p.ox, HIP_Y + p.oy + p.crouch)
    sh = (hip[0] + p.lean, hip[1] - TORSO + p.breath)
    chin = (sh[0] + 2 + p.head_dx, sh[1] - 1 + p.head_dy)
    fsh, bsh = (sh[0] + 3, sh[1] + 1), (sh[0] - 4, sh[1] + 1)
    fh = (fsh[0] + p.f_hand[0], fsh[1] + p.f_hand[1])
    bh = (bsh[0] + p.b_hand[0], bsh[1] + p.b_hand[1])
    ff = (p.f_foot[0] + p.ox, min(GROUND, p.f_foot[1] + p.oy))
    bf = (p.b_foot[0] + p.ox, min(GROUND, p.b_foot[1] + p.oy))
    return dict(hip=hip, sh=sh, chin=chin, fsh=fsh, bsh=bsh, fh=fh, bh=bh, ff=ff, bf=bf)


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


# ------------------------------------------------------------------ body parts
def cape(cv, s, p):
    if FORM < 4:
        return
    sx, sy = s['sh']
    w = p.wind
    ln = 34 if FORM == 4 else 42
    pts = [(sx - 6, sy - 1), (sx + 2, sy - 1), (sx - 3 - w, sy + ln * 0.55), (sx - 8 - w * 1.4, sy + ln),
           (sx - 14 - w * 1.8, sy + ln - 3), (sx - 19 - w * 2, sy + ln - 1), (sx - 17 - w * 1.5, sy + ln * 0.5)]
    m = cv.mask().poly(pts)
    cv.part(m, CAPE, 'cloth', 'flat', normal=(-0.1, -0.2, 1))
    if FORM == 5:   # ember-lit tattered hem
        for i in range(4):
            x = sx - 6 - w * 1.4 - i * 4
            y = sy + ln - (i % 2) * 2
            cv.part(cv.mask().poly([(x - 2, y - 3), (x + 2, y - 3), (x, y + 3 + (i + p.embers) % 3)]), FLAME, 'flat', cast=False, sep=False)


def leg(cv, hip, foot, back):
    ankle = (foot[0] - 1, foot[1] - 3)
    knee = ik(hip, ankle, THIGH, SHIN, bend=-1)
    bias = -0.3 if back else 0.0
    cv.part(limb(cv, hip, knee, 7, 5.5), TROUSER, 'cloth', 'cyl_v', bias=bias)
    cv.part(limb(cv, knee, ankle, 5.5, 4.5), TROUSER, 'cloth', 'cyl_v', bias=bias)
    boot = limb(cv, lerp(knee, ankle, 0.3), ankle, 6, 5.5)
    boot.poly([(ankle[0] - 3, ankle[1] - 1), (ankle[0] + 2, ankle[1] - 2), (foot[0] + 6, foot[1] - 2),
               (foot[0] + 6, foot[1]), (ankle[0] - 3, foot[1])])
    cv.part(boot, LEATHER, 'leather', bias=bias - 0.1)
    if not back or FORM >= 4:
        cv.part(limb(cv, lerp(knee, ankle, 0.1), lerp(knee, ankle, 0.6), 4.5, 4), armour(), 'metal', 'cyl_v', cast=False, bias=bias)
        cv.part(cv.mask().ellipse(knee[0] + 0.5, knee[1], 2.4, 2.2), GOLD if FORM == 5 else armour(), 'metal', cast=False, bias=bias)
    return knee


def torso(cv, s, p):
    (hx, hy), (sx, sy) = s['hip'], s['sh']
    body = [(sx - 7, sy - 1), (sx + 5, sy - 1), (sx + 7, sy + 5), (hx + 5, hy - 8), (hx + 6, hy),
            (hx + 5, hy + 3), (hx - 6, hy + 3), (hx - 6, hy), (hx - 5, hy - 8), (sx - 8, sy + 6)]
    cv.part(cv.mask().poly(body), TUNIC, 'cloth', 'cyl_v')
    if FORM == 3:   # leather jerkin open over the chest + harness strap
        cv.part(cv.mask().poly([(sx - 8, sy), (sx + 2, sy), (hx + 1, hy - 4), (hx - 6, hy - 4), (hx - 5, hy - 8), (sx - 8, sy + 6)]),
                LEATHER, 'leather', 'cyl_v')
        cv.part(cv.mask().poly([(sx + 5, sy + 1), (sx + 7, sy + 5), (hx + 5, hy - 5), (hx + 3, hy - 4)]), LEATHER, 'leather', 'cyl_v')
        cv.part(limb(cv, (sx - 6, sy + 1), (hx + 4, hy - 5), 2.5, 2.5), LEATHER, 'leather', 'flat', normal=(0, -0.2, 1), bias=0.25)
        cv.part(cv.mask().ellipse((sx + hx) / 2 - 1, (sy + hy) / 2 - 2, 1.3, 1.3), GOLD, 'metal', cast=False)
    else:           # forged breastplate (5*: dark plate, gold trim, ember core)
        plate = cv.mask().poly([(sx - 7, sy), (sx + 5, sy - 1), (sx + 7, sy + 5), (hx + 5, hy - 6), (hx, hy - 4), (hx - 5, hy - 6), (sx - 8, sy + 6)])
        cv.part(plate, armour(), 'metal', 'cyl_v')
        cv.part(cv.mask().poly([(hx - 5, hy - 7), (hx, hy - 5), (hx + 5, hy - 7), (hx + 5, hy - 5), (hx, hy - 3), (hx - 5, hy - 5)]),
                GOLD, 'metal', 'flat', normal=(0, 0.2, 1), cast=False)
        if FORM == 5:
            cx, cy = (sx + hx) / 2 + 1, (sy + hy) / 2 - 2
            cv.part(cv.mask().ellipse(cx, cy, 2.2, 2.2), GOLD, 'metal', cast=False)
            cv.pixels([(cx, cy), (cx - 1, cy), (cx, cy - 1)], EMBER[1 + p.embers % 2])
    cv.part(cv.mask().poly([(hx - 6, hy - 4), (hx + 6, hy - 5), (hx + 6, hy - 2), (hx - 6, hy - 1)]), LEATHER, 'leather', 'cyl_v')
    cv.part(cv.mask().rect(hx + 2, hy - 5, hx + 4, hy - 2), GOLD, 'metal', 'flat', normal=(-0.3, -0.4, 1))
    cv.part(cv.mask().poly([(hx - 6, hy - 1), (hx - 1, hy - 1), (hx - 5, hy + 7)]), TUNIC, 'cloth', bias=-0.25)
    cv.part(cv.mask().poly([(hx - 1, hy - 2), (hx + 6, hy - 2), (hx + 6, hy + 6), (hx + 3, hy + 10), (hx, hy + 6)]), TUNIC, 'cloth')
    if FORM >= 4:   # armoured tassets over the tabard
        cv.part(cv.mask().poly([(hx - 1, hy - 1), (hx + 7, hy - 2), (hx + 7, hy + 3), (hx, hy + 4)]), armour(), 'metal', 'cyl_v', cast=False)


def neck(cv, s):
    (cx, cy), (sx, sy) = s['chin'], s['sh']
    cv.part(limb(cv, (cx - 2, cy - 1), (sx + 1, sy + 1), 4.5, 5), SKIN, 'skin', 'cyl_v', bias=-0.3)


def head(cv, s, p):
    cx, cy = s['chin']
    cv.stamp(head_img(p.eyes), int(round(cx)) - 17, int(round(cy)) - 33, HAIR)


def back_cloth(cv, s, p):
    """Scarf tail (3*) / headband tails, blown back; `wind` animates them."""
    cx, cy = s['chin']
    sx, sy = s['sh']
    w = p.wind
    if FORM == 3:
        cv.part(cv.mask().poly([(sx - 3, sy - 2), (sx - 1, sy + 1), (sx - 10 - w, sy + 5 + w * 0.4), (sx - 16 - w * 1.3, sy + 3 + w),
                                (sx - 12 - w, sy)]), SCARF, 'cloth', 'flat', normal=(-0.1, -0.3, 1))
    band = GOLD if FORM == 5 else SCARF
    hy = cy - 15
    cv.part(cv.mask().poly([(cx - 11, hy), (cx - 19 - w, hy + 2 + w * 0.4), (cx - 22 - w * 1.2, hy + 5 + w * 0.3), (cx - 12, hy + 2)]),
            SCARF if FORM < 5 else CAPE, 'cloth', 'flat', normal=(0, -0.2, 1), bias=-0.2)


def scarf_wrap(cv, s):
    sx, sy = s['sh']
    m = cv.mask().ellipse(sx + 1, sy - 1, 5, 2.4)
    if FORM == 3:
        m.poly([(sx - 3, sy), (sx + 4, sy - 1), (sx + 1, sy + 5), (sx - 2, sy + 4)])
    cv.part(m, SCARF if FORM < 5 else CAPE, 'cloth', 'cyl_v')


def arm(cv, shoulder, hand, front, bend):
    elbow = ik(shoulder, hand, UPPER, FORE, bend=bend)
    bias = 0.0 if front else -0.35
    cv.part(cv.mask().ellipse(shoulder[0], shoulder[1] + 1, 2.8, 3), TUNIC, 'cloth', bias=bias)
    cv.part(limb(cv, shoulder, elbow, 5, 4), TUNIC, 'cloth', 'cyl_v', bias=bias)
    cv.part(limb(cv, elbow, hand, 4.5, 3.5), LEATHER if FORM == 3 else armour(), 'leather' if FORM == 3 else 'metal', 'cyl_v', bias=bias)
    cv.part(cv.mask().ellipse(hand[0], hand[1], 2, 2), armour() if (front or FORM >= 4) else SKIN,
            'metal' if (front or FORM >= 4) else 'skin', bias=bias)
    return elbow


def pauldron(cv, sh, back=False):
    x, y = sh
    bias = -0.35 if back else 0.0
    cv.part(cv.mask().poly([(x - 4, y - 2), (x + 1, y - 4), (x + 5, y - 1), (x + 4, y + 3), (x - 2, y + 4)]), armour(), 'metal', bias=bias)
    if FORM == 4 and not back:
        cv.part(cv.mask().poly([(x - 1, y - 3), (x + 1, y - 9), (x + 3, y - 3)]), armour(), 'metal', 'flat', normal=(-0.3, -0.6, 1), cast=False)
    if FORM == 5 and not back:   # curved horn sweeping back
        cv.part(cv.mask().poly([(x - 1, y - 3), (x - 4, y - 8), (x - 9, y - 11), (x - 6, y - 7), (x + 3, y - 3)]), HORN, 'leather', cast=False)
    cv.part(cv.mask().poly([(x - 2, y + 3), (x + 4, y + 2), (x + 4, y + 4), (x - 2, y + 5)]), GOLD, 'metal', 'flat', normal=(0, 0.3, 1),
            cast=False, bias=bias)


def sword(cv, hand, ang, embers=0):
    """Oversized single-edged blade; grows and ignites with each form."""
    a = math.radians(ang)
    ux, uy = math.cos(a), math.sin(a)
    px, py = -uy, ux                      # +p = spine side, -p = cutting edge
    hx, hy = hand

    def at(t, o):
        return (hx + ux * t + px * o, hy + uy * t + py * o)
    L = {3: 30, 4: 34, 5: 36}[FORM]
    W = {3: 3.6, 4: 4.2, 5: 4.6}[FORM]
    if FORM == 5:   # controlled flame tongues along the edge (drawn behind the steel)
        for i, t in enumerate(range(8, L - 2, 6)):
            h = 5 + (i + embers) % 3 * 2
            cv.part(cv.mask().poly([at(t - 3, -W + 1), at(t + 3, -W + 1), at(t, -W - h * 0.55), at(t - 4, -W - h)]), FLAME, 'flat', cast=False, sep=False)
    cv.part(limb(cv, at(-6, 0), at(1, 0), 3, 3), LEATHER, 'leather', 'cyl_h', cast=False)
    cv.part(cv.mask().ellipse(*at(-7, 0), 1.8, 1.8), GOLD, 'metal', cast=False)
    g = 5 if FORM == 3 else 7
    cv.part(limb(cv, at(3, -g), at(3, g), 3, 3), GOLD, 'metal', cast=False)
    blade = cv.mask().poly([at(4, -W + 0.6), at(L - 8, -W), at(L, 1.5), at(L - 4, W), at(4, W)])
    cv.part(blade, DARK if FORM == 5 else STEEL, 'metal', 'flat', normal=(-0.2, -0.5, 1), cast=False, bias=-0.55)
    edge = cv.mask()
    for t in range(5, L - 7):
        edge.set(*at(t, -W + 1))
    for k in range(8):
        edge.set(*at(L - 8 + k, -W + 0.8 + k * 0.55))
    if FORM == 3:
        cv.part(edge, STEEL, 'metal', 'flat', normal=(-0.6, -0.8, 0.5), sep=False, cast=False, bias=0.2)
    else:           # ember-hot cutting edge
        cv.part(edge, FLAME, 'metal', 'flat', normal=(-0.6, -0.8, 0.5), sep=False, cast=False)
    for i, t in enumerate(range(9, L - 6, 6)):   # ember cracks along the spine
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
        cv.part(m, FLAME, 'flat', 'round', cast=False, sep=False)


# ------------------------------------------------------------------ frame
def frame(p):
    cv = Canvas(FW, FH)
    s = skel(p)
    if p.aura:
        flames(cv, s['hip'][0], GROUND, 5, 10 + p.aura * 6 + (FORM - 3) * 3, p.embers)
    cape(cv, s, p)
    back_cloth(cv, s, p)
    bh = s['bh'] if not p.back_hand_on_hilt else (s['fh'][0] - 3, s['fh'][1] + 2)
    arm(cv, s['bsh'], bh, False, bend=1)
    if FORM >= 4:
        pauldron(cv, s['bsh'], back=True)
    leg(cv, s['hip'], s['bf'], True)
    leg(cv, s['hip'], s['ff'], False)
    torso(cv, s, p)
    neck(cv, s)
    raised = -135 < p.blade < -45 and p.blade_front   # a blade held up passes behind the head
    if (not p.blade_front or raised) and not p.no_blade:
        sword(cv, s['fh'], p.blade, p.embers)
    scarf_wrap(cv, s)
    arm(cv, s['fsh'], s['fh'], True, bend=-1)
    pauldron(cv, (s['fsh'][0] + 2, s['fsh'][1] + 1))
    head(cv, s, p)
    if p.blade_front and not p.no_blade:
        if not raised:
            sword(cv, s['fh'], p.blade, p.embers)
        cv.part(cv.mask().ellipse(s['fh'][0], s['fh'][1], 2, 2), armour(), 'metal', cast=False)
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
    return [frame(Pose(f_hand=(10, 6), blade=-120, wind=2, eyes='closed')),
            frame(Pose(f_hand=(11, -4), blade=-60, wind=3, smear=(6, -6, 12, 17, -200, -40, 3))),
            frame(Pose(f_hand=(10, -12), blade=-78, wind=4, embers=1, eyes='fierce')),
            frame(Pose(f_hand=(10, -12), blade=-80, wind=2, embers=2, eyes='fierce', breath=1))]


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

# ------------------------------------------------------------------ portrait: separate front-facing bust
EYE_R = ["..eeeee", ".eeeeeee", "eWwiiie", "eWiikie", "eWiIkie", ".WiIIie", "..eeee."]


def portrait():
    cv = Canvas(96, 96)
    cx, cy = 48, 40                                  # face centre
    arm_ = armour()
    # blade resting behind the right shoulder (hilt up by the head)
    cv.part(limb(cv, (70, 30), (86, 8), 5, 5), LEATHER, 'leather', 'cyl_h', cast=False)
    cv.part(cv.mask().ellipse(88, 6, 3, 3), GOLD, 'metal')
    cv.part(limb(cv, (60, 40), (80, 30), 5, 5), GOLD, 'metal', cast=False)
    cv.part(cv.mask().poly([(66, 38), (74, 34), (20, 96), (6, 96)]), DARK if FORM == 5 else STEEL, 'metal', 'flat',
            normal=(-0.2, -0.5, 1), bias=-0.5, cast=False)
    if FORM >= 4:
        for i in range(5):
            y = 50 + i * 10
            x = 64 - i * 9
            if FORM == 5:
                cv.part(cv.mask().poly([(x, y - 4), (x + 5, y), (x + 10, y - 8)]), FLAME, 'flat', cast=False, sep=False)
        cv.part(cv.mask().line(68, 38, 14, 96, 1), FLAME, 'metal', 'flat', sep=False, cast=False)
    if FORM >= 4:   # cape collar behind the shoulders
        cv.part(cv.mask().poly([(10, 96), (14, 64), (34, 56), (62, 56), (82, 64), (88, 96)]), CAPE, 'cloth', 'cyl_v')
    # shoulders / chest
    cv.part(cv.mask().poly([(10, 96), (16, 72), (34, 64), (62, 64), (80, 72), (86, 96)]), TUNIC, 'cloth', 'cyl_v')
    if FORM >= 4:
        cv.part(cv.mask().poly([(20, 96), (24, 74), (38, 68), (58, 68), (72, 74), (76, 96)]), arm_, 'metal', 'cyl_v')
        cv.part(cv.mask().poly([(26, 84), (48, 80), (70, 84), (70, 87), (48, 83), (26, 87)]), GOLD, 'metal', 'flat', cast=False)
        if FORM == 5:
            cv.part(cv.mask().ellipse(48, 90, 4, 4), GOLD, 'metal', cast=False)
            cv.part(cv.mask().ellipse(48, 90, 2.4, 2.4), FLAME, 'flat', cast=False)
    # pauldrons both sides (front view): rounded plates at the shoulder tips
    for side in (-1, 1):
        x = cx + side * 30
        leather = FORM == 3 and side < 0
        cv.part(cv.mask().ellipse(x, 70, 10, 7).poly([(x - 10, 70), (x + 10, 70), (x + 8, 78), (x - 8, 78)]),
                LEATHER if leather else arm_, 'leather' if leather else 'metal')
        cv.part(cv.mask().poly([(x - 9, 76), (x + 9, 76), (x + 8, 79), (x - 8, 79)]), GOLD, 'metal', 'flat', cast=False)
        if FORM == 5:
            cv.part(cv.mask().poly([(x - side * 2, 64), (x + side * 8, 52), (x + side * 13, 48), (x + side * 9, 57), (x + side * 6, 65)]),
                    HORN, 'leather', cast=False)
    if FORM == 3:   # jerkin lapels framing a V of crimson tunic
        cv.part(cv.mask().poly([(34, 66), (46, 74), (40, 96), (28, 96)]), LEATHER, 'leather', 'cyl_v')
        cv.part(cv.mask().poly([(62, 66), (50, 74), (56, 96), (68, 96)]), LEATHER, 'leather', 'cyl_v')
        cv.part(limb(cv, (60, 70), (30, 96), 4, 4), LEATHER, 'leather', 'flat', normal=(0, -0.2, 1), bias=0.25)
    # neck, back hair
    cv.part(limb(cv, (cx, cy + 12), (cx, cy + 24), 11, 12), SKIN, 'skin', 'cyl_v', bias=-0.3)
    back = cv.mask().ellipse(cx, cy - 6, 19, 17)
    cv.part(back, HAIR, 'hair')
    # face (front): oval, cheeks narrowing to a soft chin; ears both sides
    face = cv.mask().ellipse(cx, cy, 14, 15)
    face.poly([(cx - 13, cy + 4), (cx + 13, cy + 4), (cx + 7, cy + 15), (cx, cy + 19), (cx - 7, cy + 15)])
    cv.part(cv.mask().ellipse(cx - 14, cy + 3, 2.5, 4), SKIN, 'skin', bias=-0.3)
    cv.part(cv.mask().ellipse(cx + 14, cy + 3, 2.5, 4), SKIN, 'skin', bias=-0.1)
    cv.part(face, SKIN, 'skin')
    # hair: spiky crown + bangs, flame tips on evolved forms
    tip = {3: 0.0, 4: 0.4, 5: 0.62}[FORM]
    spikes = [((cx - 30, cy - 18), (cx - 16, cy - 16), (cx - 14, cy - 6)), ((cx - 24, cy - 34), (cx - 14, cy - 12), (cx - 4, cy - 18)),
              ((cx - 6, cy - 40), (cx - 10, cy - 16), (cx + 6, cy - 18)), ((cx + 14, cy - 38), (cx, cy - 18), (cx + 14, cy - 14)),
              ((cx + 30, cy - 26), (cx + 8, cy - 16), (cx + 16, cy - 8)), ((cx + 32, cy - 8), (cx + 14, cy - 12), (cx + 16, cy)),
              ((cx - 12, cy - 2), (cx - 16, cy - 14), (cx - 4, cy - 14)), ((cx - 2, cy + 1), (cx - 8, cy - 14), (cx + 6, cy - 14)),
              ((cx + 11, cy), (cx + 2, cy - 14), (cx + 16, cy - 12))]
    for t, a, b in spikes:
        m = cv.mask().poly([t, a, b])
        cv.part(m, HAIR, 'hair', 'flat', normal=(-0.25, -0.6, 1))
        if tip and t[1] < cy - 10:
            base_y = (a[1] + b[1]) / 2
            for y, x in zip(*m.m.nonzero()):
                r = (y - t[1]) / max(1.0, (base_y - t[1]) * tip)   # 0 at the tip -> 1 where the flame ends
                if r < 1:
                    cv.px[y, x] = FLAME[4 - min(3, int(r * 3.2 + (cv.band[y, x] < 2)))]
    band = GOLD if FORM == 5 else SCARF
    cv.part(cv.mask().poly([(cx - 15, cy - 9), (cx + 15, cy - 9), (cx + 15, cy - 6), (cx - 15, cy - 6)]), band,
            'metal' if FORM == 5 else 'cloth', 'cyl_v', cast=False)
    # hand-pixelled features: anime eyes (mirrored), brows, nose, mouth
    iris = ['#8e2a1e', '#c4471e', '#ff9a4a'] if FORM < 5 else ['#b0401a', '#ff8a2a', '#ffe07a']
    pal = {'e': '#241016', 'W': '#fff4e8', 'w': '#ffffff', 'i': iris[0], 'I': iris[1], 'k': '#1a0a10'}

    def eye(x0, y0, flip):
        for y, r in enumerate(EYE_R):
            for x, c in enumerate(r):
                if c in pal:
                    cv.dot(x0 + (6 - x if flip else x), y0 + y, pal[c])
        cv.dot(x0 + (1 if not flip else 5), y0 + 2, '#ffffff')
    eye(cx - 11, cy + 1, True)
    eye(cx + 4, cy + 1, False)
    for x in range(-11, -3):
        cv.dot(cx + x, cy - 3 + (1 if x > -6 else 0), HAIR[1])
    for x in range(4, 12):
        cv.dot(cx + x, cy - 3 + (1 if x < 7 else 0), HAIR[1])
    cv.pixels([(cx, cy + 9), (cx + 1, cy + 10)], SKIN[1])
    cv.pixels([(cx - 2, cy + 14), (cx - 1, cy + 14), (cx, cy + 14), (cx + 1, cy + 14), (cx + 2, cy + 13)], SKIN[0])
    if FORM == 3:   # scarf knot under the chin
        cv.part(cv.mask().ellipse(cx, cy + 24, 15, 5).poly([(cx - 6, cy + 24), (cx + 5, cy + 24), (cx - 1, cy + 38)]), SCARF, 'cloth', 'cyl_v')
    cv.cleanup().outline()
    return cv.image()


# ------------------------------------------------------------------ export
def export(form):
    global FORM
    FORM = form
    fid = FORMS[form]
    out = os.path.join(ROOT, fid)
    os.makedirs(out, exist_ok=True)
    rows = [(n, fn(), fps, loop) for n, fn, fps, loop in ANIMS]
    cols = max(len(r[1]) for r in rows)
    sheet = Image.new('RGBA', (cols * FW, len(rows) * FH), (0, 0, 0, 0))
    meta = {'frame_size': [FW, FH], 'pivot': [FW // 2, GROUND], 'animations': {}}
    for ri, (name, frames, fps, loop) in enumerate(rows):
        for ci, im in enumerate(frames):
            sheet.paste(im, (ci * FW, ri * FH), im)
        meta['animations'][name] = {'row': ri, 'frames': len(frames), 'fps': fps, 'loop': loop}
    sheet.save(os.path.join(out, fid + '_sheet.png'))
    with open(os.path.join(out, fid + '_sheet.json'), 'w') as f:
        json.dump(meta, f, indent=1)
    pr = portrait()
    pr.save(os.path.join(out, fid + '_portrait.png'))
    print(fid, 'sheet', sheet.size, 'colours', colours(sheet), '| portrait colours', colours(pr))


if __name__ == '__main__':
    for f in (sys.argv[1:] or FORMS):
        export(int(f))
