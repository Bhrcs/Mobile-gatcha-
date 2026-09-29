"""
Kael - Phase 6 art for all three forms: 3* Emberclaw, 4* Blazeheart, 5* Cinderlord.
Design sheet: docs/art/characters/kael.md.  Run: python3 tools/art_kael.py [3 4 5]

Battle sprite: 192x128 frames, feet on row 120 (pivot [96, 120]), faces RIGHT (the game flips players).
Human proportions (~5.5 heads): the head is a HAND-PIXELLED stamp (3/4 view), the body is shaded
parts on a skeleton (analytic form shading from px6). Wide stance, blade held low and forward.
Portrait: a separate front-facing bust (not the battle pose), same person/colours.
Evolution = story: 3* travelling swordsman (tunic, leather harness, sash), 4* knight (breastplate,
layered pauldrons, tabard, cape, ember-edged blade), 5* Cinderlord (dark plate + gold, horned pauldron,
burning cape hem and blade, flame-lit hair).
Poses are written in "pose units" (the old 96px rig) and scaled by K / KH in skel().
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

FW, FH = 224, 128
GROUND = 120
HIP_X = 112
K, KH = 1.4, 1.6                     # pose units -> pixels (body offsets / hand offsets)
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
SASH = Ramp('#2a1608', '#7a4a14', '#b87a22', '#e0a640', '#f6d27a')
CREAM = Ramp('#3a2a22', '#8a7462', '#bca88e', '#e0d0b4', '#f6ecd8')
HORN = Ramp('#1a1216', '#3a2a2a', '#5e4640', '#86685a', '#b89480')
TROUSER = Ramp('#120c16', '#241a2a', '#3a2c40', '#524258', '#6a5a70')
EMBER = ['#ff5a1e', '#ffa02a', '#ffe070']
SMEAR = [(255, 122, 48, 255), (255, 200, 90, 255), (255, 246, 200, 255)]


def armour():
    return DARK if FORM == 5 else STEEL


# ------------------------------------------------------------------ hand-pixelled head (3/4 view, facing right)
HEAD = [   # chin point = (14, 21). Light from the upper left: lit cheek by the ear, the front plane mid-tone.
    "..........o..o.......",
    ".....o...oLooLo.o....",
    "....oLo.oLHoLHooLo...",
    "...oLHHoLHHLHHoLHo...",
    "..oLHHHLHHHHHHLHHo...",
    ".oLHHHHHHHHHHHHHHHo..",
    "oLHHhHHHHHHHHHHHHHo..",
    ".ohhh1222222222223o..",
    "ohhhh1111111111111o..",
    ".ohhhhHHoHHHoLHoHHo..",
    "ohhhhhHKHsHKHsHSHSx..",
    ".ohhhhhKKSKKSSSSSSx..",
    "..ohhxsKbbbKSSSbbSx..",
    "..ohxsKKeeeKSSSeeSSx.",
    "..ohxsKKwikKSSSikSSx.",
    "...ohxKKKKKSSSSSSSSSx",
    "...ohxKKKKSSSSSSSSsx.",
    "....oxsKKKSSSSSSSSx..",
    ".....xsKKKSSSSSmmSx..",
    "......xsKKSSSSSSSSx..",
    "........xsKSSSSSSx...",
    "..........xxsssSx....",
    "............xxxx.....",
]
CHIN = (14, 21)
EXPR = {   # replacement rows 12..14 (brows + eyes)
    'fierce': ["..ohhxsKbbKKSSSSbbx..", "..ohxsKKeeeKSSSeeSSx.", "..ohxsKKwikKSSSikSSx."],
    'closed': ["..ohhxsKbbbKSSSbbSx..", "..ohxsKKKKKKSSSSSSSx.", "..ohxsKKeeeKSSSeeSSx."],
    'hurt': ["..ohhxsKbKKKSSSSbbx..", "..ohxsKKeKKKSSSSeSSx.", "..ohxsKKKeeKSSSeSSSx."],
    'ko': ["..ohhxsKKKKKSSSSSSx..", "..ohxsKKeKeKSSSeSeSx.", "..ohxsKKKeKKSSSSeSSx."],
}


def head_img(expr):
    rows = list(HEAD)
    if expr in EXPR:
        rows[12:15] = EXPR[expr]
    band = GOLD if FORM == 5 else SCARF
    pal = {'o': HAIR[0], 'h': HAIR[1], 'H': HAIR[3], 'L': HAIR[4], '1': band[1], '2': band[2], '3': band[4],
           'x': SKIN[0], 's': SKIN[1], 'S': SKIN[2], 'K': SKIN[3], 'b': HAIR[1], 'e': hexc('#241016'),
           'w': hexc('#f4ece4'), 'i': hexc('#b0381c') if FORM < 5 else hexc('#ff8a2a'), 'k': hexc('#1a0a10'),
           'm': SKIN[1]}
    flame = {'o': FLAME[0], 'h': FLAME[1], 'H': FLAME[2], 'L': FLAME[4]}
    tips = {3: 0, 4: 3, 5: 5}[FORM]           # evolved forms: the crown locks burn
    im = Image.new('RGBA', (len(rows[0]), len(rows)), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        for x, c in enumerate(r):
            if c in pal:
                im.putpixel((x, y), flame[c] if (y < tips and c in flame) else pal[c])
    if FORM == 5:   # circlet gem
        im.putpixel((16, 7), hexc(EMBER[2]))
    return im


# ------------------------------------------------------------------ skeleton
class Pose:
    """Pose units: hands are offsets from their shoulder (x KH); feet/body offsets x K."""
    def __init__(self, **kw):
        self.ox = 0; self.oy = 0; self.crouch = 0; self.lean = 2
        self.f_foot = (58, GROUND); self.b_foot = (34, GROUND)
        self.f_hand = (8, 17); self.b_hand = (-3, 18)
        self.head_dx = 0; self.head_dy = 0
        self.eyes = 'open'; self.blade = 30; self.blade_front = True
        self.breath = 0; self.wind = 0.0; self.embers = 0
        self.smear = None; self.aura = 0; self.back_hand_on_hilt = False; self.no_blade = False
        self.__dict__.update(kw)


HIP_Y, TORSO, THIGH, SHIN, UPPER, FORE = 74, 28, 24, 23, 17, 15


def skel(p):
    hip = (HIP_X + p.ox * K, HIP_Y + (p.oy + p.crouch) * K)
    sh = (hip[0] + p.lean * K, hip[1] - TORSO + p.breath)
    chin = (sh[0] + 4 + p.head_dx * K, sh[1] - 4 + p.head_dy * K)
    fsh, bsh = (sh[0] + 5, sh[1] + 2), (sh[0] - 7, sh[1] + 2)
    fh = (fsh[0] + p.f_hand[0] * KH, fsh[1] + p.f_hand[1] * KH)
    bh = (bsh[0] + p.b_hand[0] * KH, bsh[1] + p.b_hand[1] * KH)

    def foot(f):
        return (HIP_X + (f[0] - 46 + p.ox) * K, min(GROUND, GROUND + (f[1] - GROUND + p.oy) * K))
    return dict(hip=hip, sh=sh, chin=chin, fsh=fsh, bsh=bsh, fh=fh, bh=bh, ff=foot(p.f_foot), bf=foot(p.b_foot))


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


def add(a, dx, dy):
    return (a[0] + dx, a[1] + dy)


def fold(cv, a, b, ramp, mat='cloth'):
    """A crease: a 1px darker line inside cloth/leather."""
    cv.part(cv.mask().line(a[0], a[1], b[0], b[1], 1), ramp, mat, 'flat', normal=(0.5, 0.5, 1), bias=-0.55, sep=False, cast=False)


def trim(cv, pts, ramp=None):
    cv.part(cv.mask().poly(pts), ramp or GOLD, 'metal', 'flat', normal=(-0.2, -0.4, 1), cast=False)


# ------------------------------------------------------------------ body parts
def cape(cv, s, p):
    if FORM < 4:
        return
    sx, sy = s['sh']
    w = p.wind * K
    ln = 50 if FORM == 4 else 62
    pts = [(sx - 9, sy - 1), (sx + 2, sy - 1), (sx - 4 - w * 0.4, sy + ln * 0.55), (sx - 10 - w, sy + ln),
           (sx - 18 - w * 1.4, sy + ln - 4), (sx - 26 - w * 1.8, sy + ln - 1), (sx - 24 - w * 1.4, sy + ln * 0.5)]
    cv.part(cv.mask().poly(pts), CAPE, 'cloth', 'flat', normal=(-0.1, -0.2, 1))
    for i in range(3):   # long folds
        a = (sx - 6 - i * 5, sy + 6)
        fold(cv, a, (sx - 12 - i * 5 - w * (1 + i * 0.3), sy + ln - 3 - (i % 2) * 3), CAPE)
    if FORM == 5:   # ember-lit tattered hem
        for i in range(5):
            x = sx - 10 - w * (1 + i * 0.2) - i * 4
            y = sy + ln - (i % 2) * 3
            cv.part(cv.mask().poly([(x - 3, y - 4), (x + 3, y - 4), (x, y + 4 + (i + p.embers) % 3)]), FLAME, 'flat', cast=False, sep=False)


def back_cloth(cv, s, p):
    """Scarf tail + headband tails blown back; `wind` animates them."""
    cx, cy = s['chin']
    sx, sy = s['sh']
    w = p.wind * K
    if FORM < 5:
        cv.part(cv.mask().poly([(sx - 4, sy - 3), (sx, sy + 1), (sx - 14 - w, sy + 7 + w * 0.4), (sx - 24 - w * 1.3, sy + 5 + w),
                                (sx - 17 - w, sy)]), SCARF, 'cloth', 'flat', normal=(-0.1, -0.3, 1))
        fold(cv, (sx - 6, sy), (sx - 18 - w, sy + 4 + w * 0.6), SCARF)
    hy = cy - 13
    cv.part(cv.mask().poly([(cx - 13, hy - 1), (cx - 22 - w, hy + 2 + w * 0.4), (cx - 27 - w * 1.2, hy + 6 + w * 0.3),
                            (cx - 20 - w, hy + 5), (cx - 13, hy + 2)]),
            SCARF if FORM < 5 else CAPE, 'cloth', 'flat', normal=(0, -0.2, 1), bias=-0.2)


def skirt_back(cv, s, p):
    """Back tunic panel (+ sash tails) hanging behind the legs."""
    hx, hy = s['hip']
    w = p.wind * K * 0.5
    cv.part(cv.mask().poly([(hx - 8, hy - 2), (hx + 2, hy - 2), (hx - 1, hy + 18), (hx - 10 - w, hy + 19), (hx - 12 - w, hy + 6)]),
            TUNIC, 'cloth', 'flat', normal=(-0.2, 0, 1), bias=-0.3)
    fold(cv, (hx - 5, hy + 2), (hx - 6 - w, hy + 17), TUNIC)
    if FORM == 3:   # sash tails from the knot on the back hip
        cv.part(cv.mask().poly([(hx - 8, hy - 3), (hx - 5, hy - 3), (hx - 11 - w, hy + 14), (hx - 14 - w, hy + 12)]), SASH, 'cloth', 'cyl_h')
        cv.part(cv.mask().poly([(hx - 6, hy - 3), (hx - 3, hy - 3), (hx - 6 - w, hy + 16), (hx - 9 - w, hy + 15)]), SASH, 'cloth', 'cyl_h')


def leg(cv, hip, foot, back):
    ankle = (foot[0] - 1, foot[1] - 4)
    knee = ik(hip, ankle, THIGH, SHIN, bend=-1)
    bias = -0.3 if back else 0.0
    cv.part(limb(cv, hip, knee, 10, 7.5), TROUSER, 'cloth', 'cyl_v', bias=bias)
    cv.part(limb(cv, knee, ankle, 7.5, 5.5), TROUSER, 'cloth', 'cyl_v', bias=bias)
    # tall boot + folded cuff
    top = lerp(knee, ankle, 0.22)
    boot = limb(cv, top, ankle, 8, 7)
    boot.poly([(ankle[0] - 3, ankle[1] - 2), (ankle[0] + 3, ankle[1] - 2), (foot[0] + 6, foot[1] - 3),
               (foot[0] + 7, foot[1]), (ankle[0] - 3, foot[1])])
    cv.part(boot, LEATHER, 'leather', bias=bias - 0.1)
    cv.part(limb(cv, lerp(knee, ankle, 0.14), lerp(knee, ankle, 0.3), 9, 8.5), LEATHER, 'leather', 'cyl_v', bias=bias + 0.15, cast=False)
    cv.part(cv.mask().rect(foot[0] - 4, foot[1] - 1, foot[0] + 6, foot[1]), LEATHER, 'flat', cast=False, sep=False, bias=-1)
    if FORM >= 4 or not back:   # greave / knee guard
        if FORM >= 4:
            cv.part(limb(cv, lerp(knee, ankle, 0.2), lerp(knee, ankle, 0.85), 7, 6), armour(), 'metal', 'cyl_v', cast=False, bias=bias)
        cv.part(cv.mask().ellipse(knee[0] + 1, knee[1], 4, 3.5), GOLD if FORM == 5 else armour(), 'metal', cast=False, bias=bias)
        if FORM >= 4:
            trim(cv, [add(lerp(knee, ankle, 0.85), -3.5, 0), add(lerp(knee, ankle, 0.85), 3.5, 0),
                      add(lerp(knee, ankle, 0.85), 3.5, 2), add(lerp(knee, ankle, 0.85), -3.5, 2)])
    return knee


def torso(cv, s, p, knee_f):
    (hx, hy), (sx, sy) = s['hip'], s['sh']
    body = [(sx - 10, sy), (sx + 6, sy - 1), (sx + 9, sy + 6), (sx + 8, sy + 15), (hx + 6, hy - 6), (hx + 7, hy + 1),
            (hx - 8, hy + 1), (hx - 8, hy - 8), (sx - 11, sy + 10)]
    cv.part(cv.mask().poly(body), TUNIC, 'cloth', 'cyl_v')
    mid = lerp((sx, sy), (hx, hy), 0.5)
    if FORM == 3:
        # dark leather vest, open V at the collar, + diagonal harness strap with a brass buckle
        cv.part(cv.mask().poly([(sx - 10, sy + 1), (sx - 1, sy), (hx - 1, hy - 6), (hx - 8, hy - 6), (sx - 11, sy + 10)]), LEATHER, 'leather', 'cyl_v')
        cv.part(cv.mask().poly([(sx + 4, sy), (sx + 8, sy + 5), (sx + 8, sy + 15), (hx + 6, hy - 6), (hx + 2, hy - 6), (sx + 5, sy + 10)]),
                LEATHER, 'leather', 'cyl_v')
        cv.part(limb(cv, (sx - 8, sy + 1), (hx + 5, hy - 7), 3.5, 3.5), LEATHER, 'leather', 'flat', normal=(0, -0.2, 1), bias=0.3)
        b = lerp((sx - 8, sy + 1), (hx + 5, hy - 7), 0.45)
        cv.part(cv.mask().rect(b[0] - 1.5, b[1] - 1.5, b[0] + 1.5, b[1] + 1.5), GOLD, 'metal', cast=False)
        fold(cv, (sx - 4, sy + 12), (sx - 2, sy + 20), LEATHER, 'leather')
    else:
        # forged breastplate: rounded chest plate, gold collar trim + gem, ab plates below
        plate = cv.mask().poly([(sx - 10, sy + 1), (sx + 6, sy - 1), (sx + 9, sy + 6), (sx + 8, sy + 15), (hx + 6, hy - 9),
                                (hx - 8, hy - 9), (sx - 11, sy + 10)])
        cv.part(plate, armour(), 'metal', 'round')
        trim(cv, [(sx - 7, sy), (sx + 6, sy - 1), (sx + 7, sy + 1), (sx - 6, sy + 2)])
        cv.part(cv.mask().ellipse(sx + 1, sy + 2.5, 1.6, 1.6), FLAME, 'flat', cast=False)
        for i in range(2):   # articulated ab plates
            y = hy - 9 + i * 3
            cv.part(cv.mask().poly([(hx - 8, y), (hx + 6, y), (hx + 7, y + 3), (hx - 8, y + 3)]), armour(), 'metal', 'cyl_h', bias=-0.1 * i)
        if FORM == 5:   # gold filigree + ember core
            fold(cv, (sx - 6, sy + 6), (mid[0] - 1, mid[1] + 1), GOLD, 'metal')
            fold(cv, (sx + 6, sy + 7), (mid[0] + 2, mid[1] + 1), GOLD, 'metal')
            cv.part(cv.mask().ellipse(mid[0] + 1, mid[1], 3, 3), GOLD, 'metal', cast=False)
            cv.pixels([(mid[0] + 1, mid[1]), (mid[0], mid[1]), (mid[0] + 1, mid[1] - 1)], EMBER[1 + p.embers % 2])
    # belt (+ 3*: gold sash wrap) with buckle
    cv.part(cv.mask().poly([(hx - 8, hy - 5), (hx + 7, hy - 6), (hx + 7, hy - 2), (hx - 8, hy - 1)]), SASH if FORM == 3 else LEATHER,
            'cloth' if FORM == 3 else 'leather', 'cyl_v')
    cv.part(cv.mask().poly([(hx - 8, hy - 2), (hx + 7, hy - 3), (hx + 7, hy - 1), (hx - 8, hy)]), LEATHER, 'leather', 'cyl_v')
    cv.part(cv.mask().rect(hx + 2, hy - 6, hx + 5, hy - 1), GOLD, 'metal', 'flat', normal=(-0.3, -0.4, 1))
    # front skirt panel over the front thigh (tabard on 4*+)
    k = lerp((hx, hy), knee_f, 0.75)
    panel = [(hx - 3, hy - 1), (hx + 7, hy - 2), (k[0] + 5, k[1]), (k[0] - 3, k[1] + 2)]
    cv.part(cv.mask().poly(panel), TUNIC, 'cloth', 'flat', normal=(0.1, -0.1, 1))
    fold(cv, (hx + 2, hy + 1), (k[0] + 1, k[1]), TUNIC)
    if FORM == 3:
        cv.part(cv.mask().poly([(k[0] - 3, k[1] + 2), (k[0] + 5, k[1]), (k[0] + 5, k[1] + 2), (k[0] - 3, k[1] + 4)]), CREAM, 'cloth', cast=False)
    else:   # gold border + armoured tasset
        trim(cv, [(k[0] - 3, k[1] + 1), (k[0] + 5, k[1] - 1), (k[0] + 5, k[1] + 1), (k[0] - 3, k[1] + 3)])
        cv.part(cv.mask().poly([(hx - 1, hy - 2), (hx + 9, hy - 3), (hx + 10, hy + 5), (hx + 1, hy + 6)]), armour(), 'metal', 'cyl_v', cast=False)
        trim(cv, [(hx + 1, hy + 5), (hx + 10, hy + 4), (hx + 10, hy + 6), (hx + 1, hy + 7)])


def neck(cv, s):
    (cx, cy), (sx, sy) = s['chin'], s['sh']
    cv.part(limb(cv, (cx - 4, cy - 3), (sx + 1, sy + 1), 6, 7), SKIN, 'skin', 'cyl_v', bias=-0.35)


def scarf_wrap(cv, s):
    sx, sy = s['sh']
    m = cv.mask().ellipse(sx + 1, sy - 1, 7, 3)
    if FORM < 5:
        cv.part(m, SCARF, 'cloth', 'cyl_v')
    else:   # high gorget
        cv.part(m, armour(), 'metal', 'cyl_v')
        trim(cv, [(sx - 6, sy + 1), (sx + 8, sy), (sx + 8, sy + 2), (sx - 6, sy + 3)])


def head(cv, s, p):
    cx, cy = s['chin']
    cv.stamp(head_img(p.eyes), int(round(cx)) - CHIN[0], int(round(cy)) - CHIN[1], HAIR)


def arm(cv, shoulder, hand, front, bend):
    elbow = ik(shoulder, hand, UPPER, FORE, bend=bend)
    bias = 0.0 if front else -0.35
    cv.part(limb(cv, shoulder, elbow, 7, 6), TUNIC, 'cloth', 'cyl_v', bias=bias)
    if FORM >= 4:   # rerebrace
        cv.part(limb(cv, lerp(shoulder, elbow, 0.45), elbow, 6.5, 6), armour(), 'metal', 'cyl_v', bias=bias, cast=False)
    fore = limb(cv, lerp(elbow, hand, 0.25), hand, 6, 5)
    cv.part(limb(cv, elbow, hand, 5.5, 4.5), SKIN, 'skin', 'cyl_v', bias=bias)
    cv.part(fore, LEATHER if FORM == 3 else armour(), 'leather' if FORM == 3 else 'metal', 'cyl_v', bias=bias)
    w = lerp(elbow, hand, 0.8)
    cv.part(limb(cv, lerp(elbow, hand, 0.74), w, 6.5, 6.5), GOLD if FORM >= 4 else LEATHER, 'metal' if FORM >= 4 else 'leather',
            'cyl_v', bias=bias + 0.2, cast=False)
    fist(cv, hand, front, bias)
    return elbow


def fist(cv, hand, front, bias=0.0):
    steel = front or FORM >= 4
    cv.part(cv.mask().ellipse(hand[0], hand[1], 3, 2.8), armour() if steel else SKIN, 'metal' if steel else 'skin', bias=bias, cast=False)


def pauldron(cv, sh, back=False):
    x, y = sh
    bias = -0.35 if back else 0.0
    ar = armour() if FORM >= 4 else STEEL
    cv.part(cv.mask().poly([(x - 6, y - 2), (x, y - 5), (x + 6, y - 2), (x + 6, y + 4), (x - 4, y + 5)]), ar, 'metal', bias=bias)
    trim(cv, [(x - 4, y + 3), (x + 6, y + 2), (x + 6, y + 4), (x - 4, y + 5)])
    if FORM >= 4:   # second, lower plate
        cv.part(cv.mask().poly([(x - 4, y + 5), (x + 6, y + 4), (x + 5, y + 9), (x - 3, y + 9)]), ar, 'metal', 'cyl_h', bias=bias - 0.1)
        trim(cv, [(x - 3, y + 8), (x + 5, y + 7), (x + 5, y + 9), (x - 3, y + 10)])
    if FORM == 5 and back:   # curved horn sweeping up behind the head
        cv.part(cv.mask().poly([(x - 3, y - 3), (x - 10, y - 7), (x - 18, y - 7), (x - 11, y - 2), (x + 2, y + 1)]), HORN, 'leather', cast=False)


def sword(cv, hand, ang, embers=0):
    """Hand-and-a-half blade with a fuller; grows and ignites with each form."""
    a = math.radians(ang)
    ux, uy = math.cos(a), math.sin(a)
    px, py = -uy, ux                      # +p = spine side, -p = cutting edge
    hx, hy = hand

    def at(t, o):
        return (hx + ux * t + px * o, hy + uy * t + py * o)
    L = {3: 46, 4: 52, 5: 56}[FORM]
    W = {3: 4.4, 4: 5.0, 5: 5.6}[FORM]
    if FORM == 5:   # flame tongues along the edge (behind the steel)
        for i, t in enumerate(range(10, L - 3, 8)):
            h = 7 + (i + embers) % 3 * 3
            cv.part(cv.mask().poly([at(t - 4, -W + 1), at(t + 4, -W + 1), at(t, -W - h * 0.55), at(t - 5, -W - h)]), FLAME, 'flat', cast=False, sep=False)
    cv.part(limb(cv, at(-8, 0), at(2, 0), 3.5, 3.5), LEATHER, 'leather', 'cyl_h', cast=False)
    for t in (-5, -2):   # grip wraps
        cv.part(cv.mask().line(*at(t, -1.5), *at(t + 1, 1.5), 1), LEATHER, 'leather', 'flat', bias=-0.6, cast=False, sep=False)
    cv.part(cv.mask().ellipse(*at(-9, 0), 2.2, 2.2), GOLD, 'metal', cast=False)
    g = 6 if FORM == 3 else 8
    cv.part(limb(cv, at(3, -g), at(3, g), 3.5, 3.5), GOLD, 'metal', cast=False)
    cv.part(cv.mask().ellipse(*at(3.5, 0), 1.6, 1.6), FLAME if FORM >= 4 else SCARF, 'flat', cast=False)
    blade = cv.mask().poly([at(5, -W + 0.6), at(L - 10, -W), at(L, 1.2), at(L - 5, W), at(5, W)])
    cv.part(blade, DARK if FORM == 5 else STEEL, 'metal', 'flat', normal=(-0.2, -0.5, 1), cast=False, bias=-0.45)
    cv.part(cv.mask().line(*at(7, 1), *at(L - 12, 1), 1), DARK if FORM == 5 else STEEL, 'metal', 'flat', bias=-1.0, cast=False, sep=False)
    edge = cv.mask()
    for t in range(6, L - 9):
        edge.set(*at(t, -W + 1))
    for k in range(10):
        edge.set(*at(L - 10 + k, -W + 0.8 + k * 0.5))
    if FORM == 3:
        cv.part(edge, STEEL, 'metal', 'flat', normal=(-0.6, -0.8, 0.5), sep=False, cast=False, bias=0.25)
    else:
        cv.part(edge, FLAME, 'metal', 'flat', normal=(-0.6, -0.8, 0.5), sep=False, cast=False)
    for i, t in enumerate(range(12, L - 8, 8)):   # ember cracks along the spine
        c = EMBER[(i + embers) % 3]
        for (tt, oo) in ((t, 2.2), (t, 3.2), (t + 1, 2.7), (t + 1, 3.7), (t + 2, 3.2)):
            cv.dot(*at(tt, oo), c)
    return at(L, 0)


def smear(cv, centre, r0, r1, a0, a1, thick=4):
    """Hand-shaped slash smear: a filled crescent, thickest mid-swing, 3 tones (hot edge outside)."""
    cx, cy = centre
    n = max(6, int(abs(a1 - a0) / 5))
    outer, inner = [], []
    for i in range(n + 1):
        t = i / n
        a = math.radians(a0 + (a1 - a0) * t)
        w = thick * math.sin(math.pi * t) ** 0.7 + 0.8
        outer.append((cx + math.cos(a) * r1, cy + math.sin(a) * r1))
        inner.append((cx + math.cos(a) * (r1 - w), cy + math.sin(a) * (r1 - w)))
    m = cv.mask().poly(outer + inner[::-1]).m
    for y, x in zip(*m.nonzero()):
        d = r1 - math.hypot(x - cx, y - cy)
        cv.dot(x, y, SMEAR[2] if d < 1.6 else (SMEAR[1] if d < thick * 0.55 else SMEAR[0]))


def flames(cv, base_x, base_y, n, h, phase):
    """Controlled flame tongues (Kael's aura) - shapes, not particle soup."""
    for i in range(n):
        x = base_x + (i - n / 2) * 10 + (4 if (i + phase) % 2 else 0)
        hh = h * (0.6 + 0.4 * ((i * 7 + phase * 3) % 5) / 4)
        m = cv.mask().poly([(x - 4, base_y), (x + 4, base_y), (x + 1, base_y - hh * 0.6), (x + 3, base_y - hh), (x - 3, base_y - hh * 0.5)])
        cv.part(m, FLAME, 'flat', 'round', cast=False, sep=False)


# ------------------------------------------------------------------ frame
def frame(p):
    cv = Canvas(FW, FH)
    s = skel(p)
    if p.aura:
        flames(cv, s['hip'][0], GROUND, 7, (10 + p.aura * 6 + (FORM - 3) * 3) * K, p.embers)
    cape(cv, s, p)
    back_cloth(cv, s, p)
    bh = s['bh'] if not p.back_hand_on_hilt else (s['fh'][0] - 5, s['fh'][1] + 3)
    arm(cv, s['bsh'], bh, False, bend=1)
    if FORM >= 4:
        pauldron(cv, s['bsh'], back=True)
    skirt_back(cv, s, p)
    leg(cv, s['hip'], s['bf'], True)
    knee_f = leg(cv, s['hip'], s['ff'], False)
    torso(cv, s, p, knee_f)
    neck(cv, s)
    raised = -135 < p.blade < -45 and p.blade_front   # a blade held up passes behind the head
    if (not p.blade_front or raised) and not p.no_blade:
        sword(cv, s['fh'], p.blade, p.embers)
    scarf_wrap(cv, s)
    head(cv, s, p)
    arm(cv, s['fsh'], s['fh'], True, bend=-1)
    pauldron(cv, (s['fsh'][0] + 2, s['fsh'][1] + 1))
    if p.blade_front and not p.no_blade:
        if not raised:
            sword(cv, s['fh'], p.blade, p.embers)
        fist(cv, s['fh'], True)
    if p.smear:   # (dx, dy) from the front shoulder, r0, r1, a0, a1, thick
        dx, dy, r0, r1, a0, a1, th = p.smear
        smear(cv, (s['fsh'][0] + dx * K, s['fsh'][1] + dy * K), r0 * KH, r1 * KH, a0, a1, th * K)
    cv.cleanup().outline()
    return cv.image()


# ------------------------------------------------------------------ animations (counts/hit frames match data/skills)
G = GROUND


def idle():
    out = []
    for i in range(6):
        k = math.sin(i / 6 * math.tau)
        up = 1 if k > 0.3 else 0
        out.append(frame(Pose(breath=up, wind=1.5 + k * 1.5, embers=i % 3, f_hand=(8, 17 - up * 0.6))))
    return out


LUNGE = dict(ox=10, f_foot=(62, G), b_foot=(32, G), eyes='fierce')


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
    down = frame(Pose(eyes='ko', f_hand=(6, 18), no_blade=True, wind=0)).rotate(90, expand=True)
    gs = Canvas(FW, FH)
    sword(gs, (HIP_X - 40, G - 3), -4)
    gs.cleanup().outline()
    lying = gs.image()
    bb = down.getbbox()
    if bb:
        c = down.crop(bb)
        lying.paste(c, (FW // 2 - c.width // 2, G + 1 - c.height), c)
    return [kneel, lying]


def burst():
    P = Pose
    L = dict(ox=12, f_foot=(62, G), b_foot=(32, G), eyes='fierce')
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
EYE_R = ["..eeee.", ".eWwiie", "eWWiIke", ".eWiiIe", "..eeee."]   # a human, almond eye (mirrored for the left one)


def portrait():
    cv = Canvas(96, 96)
    cx, cy = 48, 42                                  # face centre
    arm_ = armour()
    # blade resting behind the right shoulder (hilt up by the head)
    cv.part(limb(cv, (70, 30), (84, 10), 5, 5), LEATHER, 'leather', 'cyl_h', cast=False)
    cv.part(cv.mask().ellipse(86, 8, 3, 3), GOLD, 'metal')
    cv.part(limb(cv, (60, 40), (80, 30), 5, 5), GOLD, 'metal', cast=False)
    cv.part(cv.mask().poly([(66, 38), (74, 34), (20, 96), (6, 96)]), DARK if FORM == 5 else STEEL, 'metal', 'flat',
            normal=(-0.2, -0.5, 1), bias=-0.5, cast=False)
    if FORM >= 4:
        if FORM == 5:
            for i in range(5):
                y, x = 50 + i * 10, 64 - i * 9
                cv.part(cv.mask().poly([(x, y - 4), (x + 5, y), (x + 10, y - 8)]), FLAME, 'flat', cast=False, sep=False)
        cv.part(cv.mask().line(68, 38, 14, 96, 1), FLAME, 'metal', 'flat', sep=False, cast=False)
        cv.part(cv.mask().poly([(8, 96), (12, 66), (34, 58), (62, 58), (84, 66), (90, 96)]), CAPE, 'cloth', 'cyl_v')
    # shoulders / chest
    cv.part(cv.mask().poly([(8, 96), (14, 74), (34, 66), (62, 66), (82, 74), (88, 96)]), TUNIC, 'cloth', 'cyl_v')
    if FORM >= 4:
        cv.part(cv.mask().poly([(20, 96), (24, 76), (38, 70), (58, 70), (72, 76), (76, 96)]), arm_, 'metal', 'cyl_v')
        cv.part(cv.mask().poly([(34, 70), (48, 76), (62, 70), (62, 73), (48, 79), (34, 73)]), GOLD, 'metal', 'flat', cast=False)
        cv.part(cv.mask().ellipse(48, 79, 2.5, 2.5), FLAME, 'flat', cast=False)
        if FORM == 5:
            cv.part(cv.mask().ellipse(48, 90, 4, 4), GOLD, 'metal', cast=False)
            cv.part(cv.mask().ellipse(48, 90, 2.4, 2.4), FLAME, 'flat', cast=False)
    else:   # leather vest lapels over the tunic + harness strap
        cv.part(cv.mask().poly([(34, 67), (46, 76), (40, 96), (26, 96)]), LEATHER, 'leather', 'cyl_v')
        cv.part(cv.mask().poly([(62, 67), (50, 76), (56, 96), (70, 96)]), LEATHER, 'leather', 'cyl_v')
        cv.part(limb(cv, (62, 70), (30, 96), 5, 5), LEATHER, 'leather', 'flat', normal=(0, -0.2, 1), bias=0.3)
        cv.part(cv.mask().rect(44, 80, 48, 84), GOLD, 'metal', cast=False)
    # pauldrons: 3* one steel plate (right), 4*+ layered both sides
    for side in (-1, 1):
        if FORM == 3 and side < 0:
            continue
        x = cx + side * 32
        cv.part(cv.mask().ellipse(x, 72, 11, 7).poly([(x - 11, 72), (x + 11, 72), (x + 9, 80), (x - 9, 80)]), arm_, 'metal')
        cv.part(cv.mask().poly([(x - 10, 78), (x + 10, 78), (x + 9, 81), (x - 9, 81)]), GOLD, 'metal', 'flat', cast=False)
        if FORM >= 4:
            cv.part(cv.mask().poly([(x - 9, 81), (x + 9, 81), (x + 8, 88), (x - 8, 88)]), arm_, 'metal', 'cyl_h')
        if FORM == 5:
            cv.part(cv.mask().poly([(x - side * 2, 66), (x + side * 8, 54), (x + side * 13, 50), (x + side * 9, 59), (x + side * 6, 67)]),
                    HORN, 'leather', cast=False)
    # neck + scarf/gorget
    cv.part(limb(cv, (cx, cy + 12), (cx, cy + 24), 13, 14), SKIN, 'skin', 'cyl_v', bias=-0.35)
    if FORM < 5:
        cv.part(cv.mask().ellipse(cx, cy + 25, 15, 5), SCARF, 'cloth', 'cyl_v')
        fold(cv, (cx - 6, cy + 23), (cx - 2, cy + 28), SCARF)
    else:
        cv.part(cv.mask().ellipse(cx, cy + 25, 15, 5), arm_, 'metal', 'cyl_v')
    # back hair mass
    cv.part(cv.mask().ellipse(cx, cy - 7, 18, 16).poly([(cx - 18, cy - 6), (cx + 18, cy - 6), (cx + 16, cy + 8), (cx - 16, cy + 8)]),
            HAIR, 'hair')
    # face: longer oval, defined jaw and chin; ears
    face = cv.mask().ellipse(cx, cy - 2, 12.5, 13)
    face.poly([(cx - 12, cy), (cx + 12, cy), (cx + 10, cy + 9), (cx + 4, cy + 15), (cx - 4, cy + 15), (cx - 10, cy + 9)])
    cv.part(cv.mask().ellipse(cx - 13, cy + 1, 2.5, 4), SKIN, 'skin', bias=-0.2)
    cv.part(cv.mask().ellipse(cx + 13, cy + 1, 2.5, 4), SKIN, 'skin', bias=-0.2)
    cv.part(face, SKIN, 'skin')
    # hair: tousled locks + bangs; flame tips on evolved forms
    tip = {3: 0.0, 4: 0.4, 5: 0.62}[FORM]
    locks = [((cx - 22, cy - 12), (cx - 15, cy - 16), (cx - 13, cy - 4)), ((cx - 20, cy - 26), (cx - 14, cy - 12), (cx - 3, cy - 18)),
             ((cx - 6, cy - 30), (cx - 10, cy - 16), (cx + 5, cy - 18)), ((cx + 11, cy - 29), (cx, cy - 18), (cx + 13, cy - 14)),
             ((cx + 23, cy - 20), (cx + 7, cy - 16), (cx + 15, cy - 7)), ((cx + 23, cy - 4), (cx + 13, cy - 12), (cx + 14, cy + 1)),
             ((cx - 11, cy - 5), (cx - 15, cy - 15), (cx - 3, cy - 15)), ((cx - 2, cy - 3), (cx - 7, cy - 15), (cx + 5, cy - 15)),
             ((cx + 9, cy - 5), (cx + 2, cy - 15), (cx + 14, cy - 13))]
    for t, a, b in locks:
        m = cv.mask().poly([t, a, b])
        cv.part(m, HAIR, 'hair', 'flat', normal=(-0.25, -0.6, 1))
        if tip and t[1] < cy - 10:
            base_y = (a[1] + b[1]) / 2
            for y, x in zip(*m.m.nonzero()):
                r = (y - t[1]) / max(1.0, (base_y - t[1]) * tip)
                if r < 1:
                    cv.px[y, x] = FLAME[4 - min(3, int(r * 3.2 + (cv.band[y, x] < 2)))]
    band = GOLD if FORM == 5 else SCARF
    cv.part(cv.mask().poly([(cx - 14, cy - 10), (cx + 14, cy - 10), (cx + 14, cy - 7), (cx - 14, cy - 7)]), band,
            'metal' if FORM == 5 else 'cloth', 'cyl_v', cast=False)
    # hand-pixelled features: almond eyes, straight brows, nose, mouth, jaw shade
    iris = ['#8e2a1e', '#c4471e'] if FORM < 5 else ['#b0401a', '#ff8a2a']
    pal = {'e': '#241016', 'W': '#f4e8dc', 'w': '#ffffff', 'i': iris[0], 'I': iris[1], 'k': '#1a0a10'}

    def eye(x0, y0, flip):
        for y, r in enumerate(EYE_R):
            for x, c in enumerate(r):
                if c in pal:
                    cv.dot(x0 + (6 - x if flip else x), y0 + y, pal[c])
    eye(cx - 10, cy - 1, True)
    eye(cx + 3, cy - 1, False)
    for x in range(-11, -3):
        cv.dot(cx + x, cy - 4 + (1 if x > -6 else 0), HAIR[1]); cv.dot(cx + x, cy - 3 + (1 if x > -6 else 0), HAIR[1])
    for x in range(3, 11):
        cv.dot(cx + x, cy - 4 + (1 if x < 6 else 0), HAIR[1]); cv.dot(cx + x, cy - 3 + (1 if x < 6 else 0), HAIR[1])
    cv.pixels([(cx, cy + 4), (cx, cy + 5), (cx, cy + 6), (cx + 1, cy + 7), (cx - 1, cy + 8), (cx + 1, cy + 8)], SKIN[1])
    cv.pixels([(cx - 3, cy + 11), (cx - 2, cy + 11), (cx - 1, cy + 11), (cx, cy + 11), (cx + 1, cy + 11), (cx + 2, cy + 11)], SKIN[0])
    cv.pixels([(cx - 1, cy + 12), (cx, cy + 12)], SKIN[1])
    for y in range(4, 13):   # shadow side of the face
        cv.dot(cx + 11 - max(0, y - 9), cy + y, SKIN[1])
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
    meta = {'frame_size': [FW, FH], 'pivot': [HIP_X, GROUND], 'animations': {}}
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
