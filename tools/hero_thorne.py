"""Thorne Mossguard - forest guardian tank. Original design for Cinderbound."""
import math
from pixlib import Canvas, Pal, hexc
from rig import Pose, skeleton, draw_leg, draw_arm, draw_head, lying, W, H, GROUND

SKIN = Pal('#d9a077', '#f0c29c', '#aa6f52', '#6e4332')
HOOD = Pal('#2f5a2c', '#467a3c', '#1f3d1e', '#122612')
LEATHER = Pal('#7a5234', '#9c6c46', '#553822', '#321f12')
BARK = Pal('#5b4330', '#7d6048', '#3e2c1f', '#241810')
MOSS = Pal('#6fa83a', '#9ccf55', '#4a7a26', '#2c4a16')
TROUSER = Pal('#4a3a2c', '#5f4c3a', '#33271d', '#1c150f')
BOOT = Pal('#3b2a1e', '#56402e', '#281c13', '#150e09')
SHIELD = Pal('#9a6a3a', '#c28a50', '#6e4a28', '#3e2914')
SHIELD_RIM = Pal('#5e4a38', '#7e6852', '#403224', '#221a12')
STONE = Pal('#8c8a82', '#b8b6ac', '#62605a', '#3a3935')
HANDLE = Pal('#6a4a2c', '#8a6640', '#4a321e', '#2a1c10')
LEAF = [hexc('#7cc043'), hexc('#4f9a2c'), hexc('#a9dd62')]

# ---- evolution tiers (1 = Mossguard 3*, 2 = Oakwarden 4*, 3 = Ancientroot 5*)
TIER = 1
ANTLER = Pal('#8a6a48', '#b08a62', '#624a32', '#34241a')
IRON = Pal('#6a6e78', '#9aa0aa', '#484c54', '#26282c')
_BASE = dict(HOOD=HOOD, LEATHER=LEATHER, BARK=BARK, SHIELD=SHIELD, SHIELD_RIM=SHIELD_RIM, STONE=STONE)


def set_tier(t):
    global TIER, HOOD, LEATHER, BARK, SHIELD, SHIELD_RIM, STONE
    TIER = t
    for k, v in _BASE.items():
        globals()[k] = v
    if t == 2:
        HOOD = Pal('#3a6e2e', '#58944a', '#264a1e', '#142a10')
        SHIELD_RIM = IRON
    elif t == 3:
        HOOD = Pal('#4a8a34', '#72b64e', '#305e22', '#183412')
        LEATHER = Pal('#5b4330', '#7d6048', '#3e2c1f', '#241810')
        BARK = Pal('#6a5238', '#8e7050', '#4a3826', '#281e14')
        SHIELD = Pal('#6a5238', '#8e7050', '#4a3826', '#281e14')
        SHIELD_RIM = Pal('#4a8a34', '#72b64e', '#305e22', '#183412')
        STONE = Pal('#9dff5a', '#e2ffb8', '#5ab030', '#2a6a14')


def antlers(cv, cx, cy):
    """Branching antlers grow from the hood as Thorne evolves."""
    if TIER < 2:
        return
    big = TIER == 3
    for side in (-1, 1):
        x0, y0 = cx - 1 + side * 2, cy - 5
        pts = [(x0, y0), (x0 + side * 2, y0 - 3), (x0 + side * 1, y0 - 6 - (2 if big else 0))]
        m = cv.mask()
        for a, b in zip(pts, pts[1:]):
            m.line(a[0], a[1], b[0], b[1], 1)
        m.line(pts[1][0], pts[1][1], pts[1][0] + side * 3, pts[1][1] - 1, 1)
        cv.part(m, ANTLER, shade=False, separate=False)
        if big:
            cv.dot(pts[2][0], pts[2][1] - 1, LEAF[0])
            cv.dot(pts[1][0] + side * 3, pts[1][1] - 2, LEAF[2])


def leaf_cape(cv, s):
    if TIER < 3:
        return
    sx, sy = s['sh']
    hx, hy = s['hip']
    m = cv.mask().poly([(sx - 2, sy - 1), (sx + 1, sy), (hx - 2, hy + 6), (hx - 9, hy + 5), (sx - 6, sy + 2)])
    cv.part(m, Pal('#3e7a2c', '#5ca040', '#2a5a1c', '#16300e'))
    for k in range(4):
        cv.dot(hx - 8 + k * 2, hy + 5 - (k % 2), LEAF[k % 3])


def hood(cv, cx, cy):
    m = cv.mask().ellipse(cx - 0.5, cy - 1.5, 5.4, 4.6)
    m.poly([(cx - 6, cy - 1), (cx - 9, cy + 4), (cx - 4, cy + 5)])   # hood drape behind
    face = cv.mask().ellipse(cx + 1.5, cy + 1, 3.0, 3.2)
    m.subtract(face)
    cv.part(m, HOOD)


def shield(cv, hand, raise_=0, wide=False):
    hx, hy = hand
    w = (5 if not wide else 6) + (1 if TIER >= 2 else 0)
    if TIER == 3:   # tall bark tower shield with a glowing rune
        rim = cv.mask().rect(hx + 1 - w, hy - 10 - raise_, hx + 1 + w, hy + 7 - raise_)
        cv.part(rim, SHIELD_RIM)
        face = cv.mask().rect(hx + 2 - w, hy - 9 - raise_, hx + w, hy + 6 - raise_)
        cv.part(face, SHIELD, separate=False)
        for dy in (-7, -3, 1, 5):
            cv.dot(hx - 2, hy + dy - raise_, SHIELD.sh)
            cv.dot(hx + 3, hy + dy + 1 - raise_, SHIELD.sh)
        for (dx, dy) in ((1, -3), (1, -2), (0, -1), (2, -1), (1, 0), (1, 1)):
            cv.dot(hx + dx, hy + dy - raise_, STONE.base if dy != -1 else STONE.hi)
        return
    rim = cv.mask().ellipse(hx + 1, hy - 1 - raise_, w, 8 + (1 if TIER == 2 else 0))
    cv.part(rim, SHIELD_RIM)
    face = cv.mask().ellipse(hx + 1, hy - 1 - raise_, w - 1.2, 6.8)
    cv.part(face, SHIELD, separate=False)
    # wood grain + moss patch + boss
    for dy in (-5, -1, 3):
        cv.dot(hx - 1, hy + dy - raise_, SHIELD.sh)
        cv.dot(hx + 3, hy + dy + 1 - raise_, SHIELD.sh)
    cv.dot(hx + 1, hy - 1 - raise_, STONE.hi)
    cv.dot(hx + 2, hy - 1 - raise_, STONE.base)
    cv.dot(hx + 1, hy - raise_, STONE.sh)
    for (dx, dy) in ((-2, -7), (-1, -7), (-3, -6), (0, -8)):
        cv.dot(hx + dx + 1, hy + dy - raise_, MOSS.base)


def hammer(cv, hand, angle, glow=False):
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    px, py = -uy, ux
    hx, hy = hand
    x0, y0 = hx - ux * 2, hy - uy * 2
    x1, y1 = hx + ux * 10, hy + uy * 10
    cv.part(cv.mask().line(x0, y0, x1, y1, 2), HANDLE, separate=False)
    # stone head, a block perpendicular to the handle
    cx, cy = x1 + ux * 1.5, y1 + uy * 1.5
    pts = []
    for (s, t) in ((-4, -2.2), (4, -2.2), (4, 2.2), (-4, 2.2)):
        pts.append((cx + px * s + ux * t, cy + py * s + uy * t))
    cv.part(cv.mask().poly(pts), STONE if not glow else Pal('#a8e07a', '#e0ffb0', '#6fa83a'))
    return (cx, cy)


def draw(p):
    cv = Canvas(W, H)
    s = skeleton(p)
    hammer_front = p.extra.get('hammer_front', False)
    # back arm carries the stone hammer
    leaf_cape(cv, s)
    draw_arm(cv, s['b_sh'], s['b_hand'], LEATHER, SKIN, bend=-1, width=3, glove=BARK)
    if not hammer_front:
        hammer(cv, s['b_hand'], p.weapon, glow=p.extra.get('glow'))
    draw_leg(cv, (s['hip'][0] - 1, s['hip'][1]), s['b_foot'], TROUSER, BOOT, boot_len=4)
    hx, hy = s['hip']
    sx, sy = s['sh']
    torso = cv.mask().poly([(hx - 4, hy + 1), (hx + 4, hy + 1), (sx + 5, sy + 1), (sx - 4, sy - 1)])
    cv.part(torso, LEATHER)
    # bark plates on the chest
    plate = cv.mask().poly([(hx - 2, hy - 3), (hx + 3, hy - 3), (sx + 4, sy + 2), (sx - 1, sy + 2)])
    cv.part(plate, BARK)
    cv.dot(sx + 1, sy + 4, BARK.hi)
    cv.dot(sx + 2, sy + 5, BARK.hi)
    draw_leg(cv, (hx + 1, hy), s['f_foot'], TROUSER, BOOT, boot_len=4)
    kilt = cv.mask().poly([(hx - 4, hy - 2), (hx + 4, hy - 2), (hx + 5, hy + 3), (hx - 5, hy + 3)])
    cv.part(kilt, LEATHER)
    belt = cv.mask().rect(hx - 4, hy - 2, hx + 4, hy - 2)
    cv.part(belt, BARK, shade=False)
    draw_head(cv, (s['head'][0], s['head'][1] + 1), SKIN, hood, p.eyes, eye_col=(40, 30, 20, 255))
    antlers(cv, s['head'][0], s['head'][1] + 1)
    # mossy bark pauldron on the front shoulder
    fsx, fsy = s['f_sh']
    cv.part(cv.mask().ellipse(fsx, fsy, 3.2, 2.4), BARK)
    for dx in (-2, -1, 0, 1):
        cv.dot(fsx + dx, fsy - 2 + (1 if dx in (-2, 1) else 0), MOSS.base if dx % 2 else MOSS.hi)
    if hammer_front:
        hammer(cv, s['b_hand'], p.weapon, glow=p.extra.get('glow'))
    draw_arm(cv, (fsx, fsy + 1), s['f_hand'], LEATHER, SKIN, bend=1, width=3, glove=BARK)
    if not p.extra.get('no_shield'):
        shield(cv, s['f_hand'], raise_=p.extra.get('sraise', 0), wide=p.extra.get('wide', False))
    if TIER >= 2:   # second bark pauldron on the far shoulder
        pass
    cv.outline()
    if p.extra.get('glow'):
        cv.glow((120, 220, 80), alpha=110)
    elif TIER == 3:
        cv.glow((120, 220, 80), alpha=45)
    for i, (x, y) in enumerate(p.extra.get('leaves', [])):
        cv.dot(x, y, LEAF[i % 3])
        cv.dot(x + 1, y, LEAF[(i + 1) % 3])
    return cv.image()


def _mk(d, i):
    extra = {k: d.pop(k) for k in list(d.keys()) if k in
             ('hammer_front', 'glow', 'leaves', 'sraise', 'wide', 'no_shield')}
    kw = dict(f_foot=(30, GROUND), b_foot=(18, GROUND), lean=1)
    kw.update(d)
    return Pose(extra=extra, **kw)


def idle():
    leaf_sets = [[(14, 43), (35, 42)], [(15, 42), (36, 43)], [(13, 42), (34, 41)], [(14, 41), (36, 42)]]
    out = []
    for i in range(4):
        bob = [0, 0, 1, 1][i]
        out.append(draw(_mk(dict(oy=bob, f_hand=(32, 33 + bob), b_hand=(19, 33 + bob), weapon=-118,
                                 leaves=leaf_sets[i]), i)))
    return out


def attack():
    """Root Hammer: overhead hammer swing then a shield bash (7 frames)."""
    seq = [
        dict(lean=-1, crouch=1, f_hand=(31, 34), b_hand=(19, 22), weapon=-110),
        dict(lean=-1, crouch=1, f_hand=(30, 34), b_hand=(22, 18), weapon=-140, eyes='fierce'),
        dict(lean=3, crouch=2, f_hand=(29, 36), b_hand=(32, 30), weapon=20, eyes='fierce',
             hammer_front=True, f_foot=(32, GROUND), leaves=[(44, 41), (46, 38)]),
        dict(lean=2, crouch=1, f_hand=(30, 35), b_hand=(28, 33), weapon=38, eyes='fierce',
             hammer_front=True),
        dict(lean=4, crouch=1, f_hand=(36, 32), b_hand=(22, 32), weapon=-30, eyes='fierce',
             f_foot=(33, GROUND), wide=True, leaves=[(46, 30), (45, 34)]),
        dict(lean=3, f_hand=(34, 33), b_hand=(20, 33), weapon=-105, eyes='open', f_foot=(32, GROUND)),
        dict(lean=1, f_hand=(32, 33), b_hand=(19, 33), weapon=-118, eyes='open'),
    ]
    return [draw(_mk(d, i)) for i, d in enumerate(seq)]


def hit():
    seq = [
        dict(lean=-2, ox=-1, f_hand=(30, 32), b_hand=(18, 33), weapon=-125, eyes='hurt', sraise=1),
        dict(lean=0, f_hand=(31, 33), b_hand=(19, 33), weapon=-120, eyes='hurt'),
    ]
    return [draw(_mk(d, i)) for i, d in enumerate(seq)]


def victory():
    seq = []
    for i in range(4):
        up = [0, -1, -1, 0][i]
        seq.append(dict(oy=up, f_hand=(31, 33 + up), b_hand=(22, 18 + up), weapon=-95,
                        eyes='closed' if i in (1, 2) else 'open',
                        leaves=[(20 + i * 3, 8 + (i % 2) * 2), (30 - i * 2, 6 + i)]))
    return [draw(_mk(d, i)) for i, d in enumerate(seq)]


def ko():
    f1 = draw(_mk(dict(lean=2, crouch=4, f_hand=(33, 39), b_hand=(18, 38), weapon=10, eyes='hurt',
                       f_foot=(30, GROUND), b_foot=(17, GROUND)), 0))
    f2 = lying(draw(_mk(dict(f_hand=(30, 34), b_hand=(19, 35), weapon=80, eyes='ko', no_shield=True), 1)))
    return [f1, f2]


def burst():
    """Ancient Bastion: raise shield, slam the hammer into the earth, roots erupt (10 frames)."""
    seq = [
        dict(f_hand=(32, 32), b_hand=(19, 30), weapon=-100, eyes='closed', glow=True),
        dict(crouch=1, f_hand=(32, 30), b_hand=(21, 19), weapon=-120, eyes='fierce', glow=True, sraise=2,
             leaves=[(12, 30), (38, 26)]),
        dict(oy=-2, f_hand=(32, 28), b_hand=(24, 16), weapon=-150, eyes='fierce', glow=True, sraise=3,
             leaves=[(10, 24), (40, 20), (26, 4)]),
        dict(oy=-3, f_hand=(32, 27), b_hand=(25, 15), weapon=-165, eyes='fierce', glow=True, sraise=3,
             leaves=[(12, 18), (42, 16), (28, 2)]),
        dict(lean=3, crouch=4, f_hand=(31, 35), b_hand=(33, 34), weapon=40, eyes='fierce', glow=True,
             hammer_front=True, leaves=[(38, 44), (44, 43), (10, 44)]),
        dict(lean=3, crouch=4, f_hand=(31, 35), b_hand=(33, 34), weapon=42, eyes='fierce', glow=True,
             hammer_front=True, leaves=[(6, 42), (46, 41), (20, 44), (40, 40)]),
        dict(lean=2, crouch=2, f_hand=(33, 31), b_hand=(29, 32), weapon=35, eyes='fierce', glow=True,
             hammer_front=True, wide=True, sraise=1),
        dict(lean=1, crouch=1, f_hand=(33, 31), b_hand=(21, 31), weapon=-100, eyes='fierce', wide=True,
             sraise=1, leaves=[(18, 12), (32, 10)]),
        dict(lean=1, f_hand=(32, 33), b_hand=(19, 33), weapon=-118, eyes='open'),
        dict(lean=1, f_hand=(32, 33), b_hand=(19, 33), weapon=-118, eyes='open', leaves=[(14, 43), (35, 42)]),
    ]
    return [draw(_mk(d, i)) for i, d in enumerate(seq)]


def guard():
    """Wide shield planted forward, hammer tucked behind (the tank's wall)."""
    seq = []
    for i in range(3):
        seq.append(dict(lean=0, crouch=2 + (i == 1), f_hand=(33, 32), b_hand=(18, 34), weapon=-135, eyes='fierce',
                        sraise=1, wide=True, f_foot=(32, GROUND), b_foot=(16, GROUND)))
    return [draw(_mk(d, i)) for i, d in enumerate(seq)]

ANIMS = [('idle', idle, 5, True), ('attack', attack, 12, False), ('hit', hit, 9, False),
         ('victory', victory, 6, True), ('ko', ko, 6, False), ('burst', burst, 10, False),
         ('guard', guard, 6, True)]
