"""Mira Tidesong - wandering water mage. Original design for Cinderbound."""
import math
from pixlib import Canvas, Pal, hexc
from rig import Pose, skeleton, draw_leg, draw_arm, draw_head, lying, W, H, GROUND

SKIN = Pal('#f2c3a0', '#ffe0c6', '#cc8f72', '#8a5646')
HAIR = Pal('#23336e', '#3b5199', '#16204a', '#0d1330')
CLOAK = Pal('#8fb8dc', '#c2def2', '#5f87b0', '#35557a')
CLOAK_IN = Pal('#4a6f99', '#6189b2', '#34527a', '#223750')
SILVER = Pal('#b8c2cf', '#eef3f8', '#808b9b', '#4c5563')
TUNIC = Pal('#2b3a68', '#40548c', '#1c2749', '#10172d')
BOOT = Pal('#2f5fa6', '#4d84cc', '#1f4078', '#12254a')
STAFF = Pal('#7a5638', '#a27a52', '#553a24', '#2f2013')
CRYSTAL = Pal('#5ee6f0', '#c8fbff', '#23a8c4', '#136478')
DROP = [hexc('#9ff3ff'), hexc('#4fc9e8'), hexc('#e0ffff')]

# ---- evolution tiers (1 = Tidesong 3*, 2 = Tidecaller 4*, 3 = Wavesage 5*)
TIER = 1
_BASE = dict(CLOAK=CLOAK, CLOAK_IN=CLOAK_IN, TUNIC=TUNIC, SILVER=SILVER, BOOT=BOOT, CRYSTAL=CRYSTAL, STAFF=STAFF)


def set_tier(t):
    global TIER, CLOAK, CLOAK_IN, TUNIC, SILVER, BOOT, CRYSTAL, STAFF
    TIER = t
    for k, v in _BASE.items():
        globals()[k] = v
    if t == 2:
        CLOAK = Pal('#3aa6b8', '#7ad6e2', '#237a8c', '#124452')
        CLOAK_IN = Pal('#1e5a78', '#2e7896', '#143e56', '#0a2232')
        CRYSTAL = Pal('#7af2ff', '#e0ffff', '#2ac0dc', '#12708a')
    elif t == 3:
        CLOAK = Pal('#e8f4fa', '#ffffff', '#b4d0e0', '#6a8ea4')
        CLOAK_IN = Pal('#2a8ab0', '#48b0d4', '#1c6284', '#0e3448')
        TUNIC = Pal('#1c4a8a', '#2e66b0', '#123262', '#0a1c3a')
        SILVER = Pal('#d8c070', '#fff0b0', '#a88c40', '#5c4a1a')
        BOOT = Pal('#e8f4fa', '#ffffff', '#b4d0e0', '#6a8ea4')
        CRYSTAL = Pal('#9ff8ff', '#ffffff', '#4fd0e8', '#1e7a94')
        STAFF = Pal('#e8e0c8', '#fffbe8', '#b8ac90', '#6e6450')


def circlet(cv, cx, cy):
    if TIER == 2:
        cv.part(cv.mask().rect(cx - 3, cy - 4, cx + 3, cy - 4), SILVER, shade=False)
        cv.dot(cx + 1, cy - 5, CRYSTAL.base)
    elif TIER == 3:   # wave-crest tiara
        cv.part(cv.mask().rect(cx - 3, cy - 4, cx + 3, cy - 4), SILVER, shade=False)
        for (dx, h) in ((-2, 2), (0, 4), (2, 3)):
            cv.part(cv.mask().poly([(cx + dx - 1, cy - 4), (cx + dx, cy - 4 - h), (cx + dx + 1, cy - 4)]), CRYSTAL)


def hair(cv, cx, cy):
    m = cv.mask().ellipse(cx - 0.5, cy - 3, 4.8, 2.6)
    m.rect(cx - 5, cy - 3, cx - 2, cy + 6)            # long hair down the back
    m.poly([(cx - 5, cy + 6), (cx - 2, cy + 6), (cx - 4, cy + 9)])
    m.poly([(cx + 1, cy - 5), (cx + 5, cy - 3), (cx + 4, cy - 1), (cx + 2, cy - 2)])  # side fringe
    cv.part(m, HAIR)


def cloak_back(cv, s, flow):
    sx, sy = s['sh']
    hx, hy = s['hip']
    ext = {1: 0, 2: 2, 3: 4}[TIER]
    m = cv.mask().poly([(sx - 2, sy - 1), (sx + 1, sy - 1), (hx - 1, hy + 6 + ext // 2),
                        (hx - 6 - flow - ext, hy + 7 + ext // 2), (hx - 8 - flow - ext, hy + 5), (sx - 5 - ext // 2, sy + 3)])
    cv.part(m, CLOAK_IN)
    if TIER == 3:   # wave-edged mantle trim
        for k in range(4):
            cv.dot(hx - 6 - flow - ext + k * 2, hy + 7 + ext // 2 - (k % 2), DROP[k % 3])


def staff(cv, hand, angle, length=17, glow=False, crystal_dy=0):
    length += {1: 0, 2: 1, 3: 3}[TIER]
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    hx, hy = hand
    x0, y0 = hx - ux * 5, hy - uy * 5
    x1, y1 = hx + ux * (length - 5), hy + uy * (length - 5)
    m = cv.mask().line(x0, y0, x1, y1, 2)
    cv.part(m, STAFF, separate=False)
    # prongs holding the crystal
    px, py = -uy, ux
    pr = cv.mask().line(x1 + px * 2, y1 + py * 2, x1 + ux * 2 + px * 2, y1 + uy * 2 + py * 2, 1)
    pr.line(x1 - px * 2, y1 - py * 2, x1 + ux * 2 - px * 2, y1 + uy * 2 - py * 2, 1)
    pr.line(x1 - px * 2, y1 - py * 2, x1 + px * 2, y1 + py * 2, 1)
    cv.part(pr, SILVER, shade=False, separate=False)
    cx, cy = x1 + ux * 4.5, y1 + uy * 4.5 + crystal_dy
    cr = 3 if TIER == 1 else 4
    cm = cv.mask().poly([(cx, cy - cr), (cx + cr - 1, cy), (cx, cy + cr), (cx - cr + 1, cy)])
    cv.part(cm, CRYSTAL if not glow else Pal('#b4fbff', '#ffffff', '#5ee6f0'), separate=False)
    return (cx, cy)


def draw(p):
    cv = Canvas(W, H)
    s = skeleton(p)
    cloak_back(cv, s, p.extra.get('flow', 0))
    staff_behind = p.extra.get('staff_behind', False)
    draw_arm(cv, s['b_sh'], s['b_hand'], TUNIC, SKIN, bend=-1, width=2)
    draw_leg(cv, (s['hip'][0] - 1, s['hip'][1]), s['b_foot'], TUNIC, BOOT)
    hx, hy = s['hip']
    sx, sy = s['sh']
    torso = cv.mask().poly([(hx - 3, hy + 1), (hx + 3, hy + 1), (sx + 3, sy + 1), (sx - 3, sy)])
    cv.part(torso, TUNIC)
    chest = cv.mask().poly([(hx - 2, hy - 3), (hx + 3, hy - 3), (sx + 3, sy + 1), (sx - 2, sy + 1)])
    cv.part(chest, SILVER)
    draw_leg(cv, (hx + 1, hy), s['f_foot'], TUNIC, BOOT)
    # skirt of the tunic
    sk = cv.mask().poly([(hx - 3, hy - 2), (hx + 3, hy - 2), (hx + 5, hy + 4), (hx - 4, hy + 4)])
    cv.part(sk, TUNIC)
    belt = cv.mask().rect(hx - 3, hy - 2, hx + 3, hy - 2)
    cv.part(belt, SILVER, shade=False)
    cv.dot(hx + 1, hy - 2, CRYSTAL.base)
    # cloak over the shoulders (front drape)
    drape = cv.mask().poly([(sx - 4, sy - 1), (sx + 3, sy - 1), (sx + 1, sy + 1), (sx - 4, sy + 3)])
    cv.part(drape, CLOAK)
    draw_head(cv, s['head'], SKIN, hair, p.eyes, eye_col=(30, 40, 90, 255))
    circlet(cv, s['head'][0], s['head'][1])
    tip = None
    if staff_behind:
        tip = staff(cv, s['f_hand'], p.weapon, glow=p.extra.get('glow'), crystal_dy=p.extra.get('cdy', 0))
    draw_arm(cv, (s['f_sh'][0], s['f_sh'][1] + 1), s['f_hand'], CLOAK, SKIN, bend=1, width=2)
    if not staff_behind:
        tip = staff(cv, s['f_hand'], p.weapon, glow=p.extra.get('glow'), crystal_dy=p.extra.get('cdy', 0))
    cv.outline()
    if p.extra.get('glow'):
        cv.glow((90, 220, 255), alpha=110)
    # orbiting droplets
    for i, (x, y) in enumerate(p.extra.get('drops', [])):
        cv.dot(x, y, DROP[i % 3])
    if TIER >= 2 and tip and p.extra.get('orbit') is None:
        p.extra['orbit'] = p.extra.get('flow', 0) * 1.3   # evolved forms keep water circling the crystal
    if TIER == 3 and not p.extra.get('glow'):
        cv.glow((120, 220, 255), alpha=45)
    if tip and p.extra.get('orbit') is not None:
        ph = p.extra['orbit']
        for k in range(3):
            a = ph + k * 2 * math.pi / 3
            cv.dot(tip[0] + math.cos(a) * 4, tip[1] + math.sin(a) * 2, DROP[k])
    return cv.image()


def _mk(d, i):
    extra = {'flow': d.pop('flow', i % 2), 'glow': d.pop('glow', False), 'drops': d.pop('drops', []),
             'orbit': d.pop('orbit', None), 'staff_behind': d.pop('staff_behind', False),
             'cdy': d.pop('cdy', 0)}
    kw = dict(f_foot=(28, GROUND), b_foot=(20, GROUND), lean=1)
    kw.update(d)
    return Pose(extra=extra, **kw)


def idle():
    out = []
    for i in range(4):
        bob = [0, 0, 1, 1][i]
        out.append(draw(_mk(dict(oy=bob, f_hand=(33, 32 + bob), b_hand=(20, 35 + bob), weapon=-80,
                                 orbit=i * math.pi / 2, flow=[0, 1, 1, 0][i], cdy=[0, -1, -1, 0][i]), i)))
    return out


def attack():
    """Tidal Bolt: gather water, thrust the staff forward, release (6 frames)."""
    seq = [
        dict(f_hand=(32, 29), b_hand=(22, 31), weapon=-95, eyes='closed', orbit=0.0),
        dict(lean=0, f_hand=(27, 27), b_hand=(23, 29), weapon=-115, eyes='fierce', orbit=1.2,
             drops=[(22, 18), (26, 15), (31, 17)]),
        dict(lean=2, f_hand=(33, 30), b_hand=(22, 32), weapon=-35, eyes='fierce', glow=True,
             drops=[(42, 20), (44, 23)]),
        dict(lean=3, f_hand=(35, 30), b_hand=(21, 33), weapon=-20, eyes='fierce', glow=True,
             drops=[(45, 24), (46, 21), (43, 26)]),
        dict(lean=2, f_hand=(33, 31), b_hand=(21, 34), weapon=-40, eyes='open'),
        dict(lean=1, f_hand=(33, 32), b_hand=(20, 35), weapon=-80, eyes='open', orbit=2.0),
    ]
    return [draw(_mk(d, i)) for i, d in enumerate(seq)]


def hit():
    seq = [
        dict(lean=-2, ox=-2, f_hand=(27, 33), b_hand=(18, 32), weapon=-70, eyes='hurt'),
        dict(lean=-1, ox=-1, f_hand=(28, 32), b_hand=(19, 34), weapon=-78, eyes='hurt'),
        dict(lean=1, f_hand=(33, 32), b_hand=(20, 35), weapon=-80, eyes='open'),
    ]
    return [draw(_mk(d, i)) for i, d in enumerate(seq)]


def victory():
    seq = []
    for i in range(4):
        up = [0, -1, -1, 0][i]
        seq.append(dict(oy=up, f_hand=(32, 22 + up), b_hand=(19, 29 + up), weapon=-90,
                        eyes='closed' if i in (1, 2) else 'open', glow=i in (1, 2), orbit=i * 1.5))
    return [draw(_mk(d, i)) for i, d in enumerate(seq)]


def ko():
    f1 = draw(_mk(dict(lean=2, crouch=4, f_hand=(32, 38), b_hand=(21, 38), weapon=-10, eyes='hurt',
                       f_foot=(29, GROUND), b_foot=(18, GROUND)), 0))
    f2 = lying(draw(_mk(dict(f_hand=(29, 35), b_hand=(20, 35), weapon=-60, eyes='ko'), 1)))
    return [f1, f2]


def burst():
    """Restoring Current: raise the staff, gather a tide, plant it to release a healing wave (10 frames)."""
    seq = [
        dict(f_hand=(32, 30), b_hand=(22, 31), weapon=-88, eyes='closed', orbit=0.0),
        dict(f_hand=(31, 24), b_hand=(23, 26), weapon=-90, eyes='closed', glow=True, orbit=1.0),
        dict(oy=-1, f_hand=(31, 20), b_hand=(23, 22), weapon=-90, eyes='closed', glow=True, orbit=2.0,
             drops=[(18, 14), (38, 14), (16, 22), (40, 22)]),
        dict(oy=-2, f_hand=(31, 19), b_hand=(23, 21), weapon=-90, eyes='fierce', glow=True, orbit=3.0,
             drops=[(20, 11), (36, 11), (15, 18), (41, 18), (28, 6)]),
        dict(oy=-2, f_hand=(31, 19), b_hand=(23, 21), weapon=-90, eyes='fierce', glow=True, orbit=4.0,
             drops=[(22, 9), (34, 9), (17, 15), (39, 15), (28, 4)]),
        dict(oy=-1, f_hand=(31, 24), b_hand=(23, 26), weapon=-90, eyes='fierce', glow=True, orbit=5.0),
        dict(crouch=2, f_hand=(31, 32), b_hand=(23, 32), weapon=-88, eyes='fierce', glow=True,
             drops=[(14, 42), (40, 42), (10, 41), (44, 41)]),
        dict(crouch=3, f_hand=(31, 33), b_hand=(23, 33), weapon=-88, eyes='closed', glow=True,
             drops=[(8, 40), (46, 40), (4, 42), (43, 43)]),
        dict(crouch=1, f_hand=(30, 32), b_hand=(21, 34), weapon=-86, eyes='open', orbit=6.0),
        dict(f_hand=(33, 32), b_hand=(20, 35), weapon=-80, eyes='open', orbit=7.0),
    ]
    return [draw(_mk(d, i)) for i, d in enumerate(seq)]


def guard():
    """Staff held level before her, a thin ring of water drops circling it."""
    seq = []
    for i in range(3):
        seq.append(dict(lean=-1, crouch=2, f_hand=(31, 31), b_hand=(24, 32), weapon=-10, eyes='fierce',
                        drops=[(36 + i, 24 - i), (27 - i, 27 + i), (34, 38 - i)]))
    return [draw(_mk(d, i)) for i, d in enumerate(seq)]

ANIMS = [('idle', idle, 6, True), ('attack', attack, 12, False), ('hit', hit, 10, False),
         ('victory', victory, 6, True), ('ko', ko, 6, False), ('burst', burst, 10, False),
         ('guard', guard, 6, True)]
