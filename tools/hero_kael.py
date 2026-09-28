"""Kael Emberclaw - young fire mercenary. Original design for Cinderbound."""
import math
from pixlib import Canvas, Pal, hexc, mix
from rig import Pose, skeleton, draw_leg, draw_arm, draw_head, blade, lying, W, H, GROUND

SKIN = Pal('#eeb48a', '#ffd6b0', '#c47f5e', '#8a4a3a')
HAIR = Pal('#4a2b1e', '#704432', '#2c1912', '#1c100c')
IRON = Pal('#555b6b', '#848da0', '#373a47', '#23252f')
PAULDRON = Pal('#737c8e', '#a8b2c4', '#4d5363', '#2b2e39')
CLOTH = Pal('#b0302a', '#dd5038', '#76191f', '#4a0f15')
SCARF = Pal('#d63a2e', '#ff6b47', '#8e2026', '#5a1018')
TROUSER = Pal('#3a3141', '#524659', '#28212e', '#18131c')
BOOT = Pal('#1f1d27', '#3d3a4a', '#15131b', '#0c0b10')
BACK = Pal('#2e2a36', '#403a4a', '#221e29', '#141117')
STEEL = Pal('#8e98a8', '#c9d1dc', '#5f6776', '#3a404b')
EMBER = Pal('#ff8a2a', '#ffc15a', '#e0521c', '#a8300f')
HILT = Pal('#5a3622', '#7c5034', '#3a2216', '#22140c')
GUARD = Pal('#c49a3a', '#f0cd6a', '#8a6a24', '#4f3b12')
SPARK = [hexc('#ffd35a'), hexc('#ff8a2a'), hexc('#ffef9a')]

# ---- evolution tiers (1 = Emberclaw 3*, 2 = Blazeheart 4*, 3 = Cinderlord 5*)
TIER = 1
CAPE = Pal('#9a2a22', '#c8402e', '#6a1818', '#3a0c0c')
TRIM = GUARD
_BASE = dict(IRON=IRON, PAULDRON=PAULDRON, CLOTH=CLOTH, SCARF=SCARF, STEEL=STEEL, TROUSER=TROUSER, BOOT=BOOT)


def set_tier(t):
    """Swaps palettes/features for an evolved form. Call before drawing."""
    global TIER, IRON, PAULDRON, CLOTH, SCARF, STEEL, TROUSER, BOOT, CAPE
    TIER = t
    for k, v in _BASE.items():
        globals()[k] = v
    if t == 2:
        IRON = Pal('#474d5e', '#727c92', '#2f3340', '#1a1c24')
        PAULDRON = Pal('#b88a34', '#f0c85a', '#806020', '#44320e')
        SCARF = Pal('#ff5a2e', '#ff9a52', '#c0301e', '#6a1410')
        STEEL = Pal('#a0a8b8', '#e0e6f0', '#6c7486', '#3c424e')
        CAPE = Pal('#9a2a22', '#c8402e', '#6a1818', '#3a0c0c')
    elif t == 3:
        IRON = Pal('#2e2a34', '#4a4452', '#1e1a22', '#0e0c10')
        PAULDRON = Pal('#e0a830', '#ffe07a', '#a87418', '#583a08')
        CLOTH = Pal('#7a1a20', '#a8282a', '#501014', '#2c080a')
        SCARF = Pal('#ffb03a', '#ffe08a', '#e06a1c', '#8a3410')
        STEEL = Pal('#3a3440', '#5c5466', '#26222c', '#141216')
        TROUSER = Pal('#2a2230', '#3e3446', '#1a1520', '#0e0b12')
        BOOT = Pal('#3a2a22', '#5a4232', '#241a14', '#120c0a')
        CAPE = Pal('#5a1016', '#8a1c22', '#3a0a0e', '#1e0506')


def cape_back(cv, sh, phase):
    """Evolved Kael wears a cape; the 5* cape is long with ember-lit tatters."""
    sx, sy = sh
    wave = math.sin(phase) * 1.5
    ln = 12 if TIER == 2 else 16
    m = cv.mask().poly([(sx - 1, sy - 1), (sx + 2, sy), (sx - 3, sy + ln - 2), (sx - 7 - wave, sy + ln),
                        (sx - 9 - wave, sy + ln - 3), (sx - 4, sy + 2)])
    cv.part(m, CAPE)
    if TIER == 3:
        for k in range(3):
            cv.dot(sx - 7 - wave + k * 2, sy + ln - (k % 2), SPARK[k])


def crest(cv, cx, cy):
    """Flame crest (5*) / gold hair clasp (4*) worn over the spiky hair."""
    if TIER == 2:
        cv.dot(cx - 3, cy - 3, TRIM.hi)
        cv.dot(cx - 4, cy - 3, TRIM.base)
    elif TIER == 3:
        m = cv.mask().poly([(cx - 2, cy - 5), (cx, cy - 10), (cx + 1, cy - 6), (cx + 3, cy - 9), (cx + 3, cy - 4)])
        cv.part(m, Pal('#ff8a2a', '#ffe08a', '#e0521c', '#8a2a0c'))
        cv.part(cv.mask().rect(cx - 3, cy - 5, cx + 3, cy - 4), PAULDRON, shade=False)


def hair(cv, cx, cy):
    # spiky swept-back hair
    m = cv.mask().ellipse(cx - 0.5, cy - 3, 4.6, 2.4)
    m.poly([(cx - 5, cy - 2), (cx - 8, cy - 4), (cx - 5, cy - 5)])      # back spike
    m.poly([(cx - 4, cy - 4), (cx - 6, cy - 7), (cx - 1, cy - 5)])      # top-back spike
    m.poly([(cx - 1, cy - 5), (cx + 1, cy - 8), (cx + 2, cy - 4)])      # top spike
    m.poly([(cx + 2, cy - 5), (cx + 5, cy - 5), (cx + 3, cy - 2)])      # fringe
    m.rect(cx - 5, cy - 2, cx - 2, cy + 2)                              # back of head
    cv.part(m, HAIR)


def scarf_tail(cv, sh, phase):
    """Scarf tail flowing behind (left)."""
    sx, sy = sh[0] - 1, sh[1] - 1
    wave = math.sin(phase) * 1.2
    m = cv.mask().poly([(sx, sy - 1), (sx - 4, sy + 1 + wave), (sx - 8, sy + 4 + wave * 1.5),
                        (sx - 7, sy + 5 + wave), (sx - 4, sy + 3), (sx, sy + 1)])
    cv.part(m, SCARF)


def draw(p):
    cv = Canvas(W, H)
    s = skeleton(p)
    if TIER >= 2:
        cape_back(cv, s['sh'], p.extra.get('scarf', 0.0))
    scarf_tail(cv, s['sh'], p.extra.get('scarf', 0.0))
    # back arm (grips nothing, balances)
    draw_arm(cv, s['b_sh'], s['b_hand'], BACK, SKIN, bend=-1)
    if TIER >= 2:   # matching pauldron on the far shoulder
        cv.part(cv.mask().ellipse(s['b_sh'][0], s['b_sh'][1], 2.2, 1.8), PAULDRON)
    draw_leg(cv, (s['hip'][0] - 1, s['hip'][1]), s['b_foot'], BACK, BOOT)
    # torso: iron breastplate over red cloth
    hx, hy = s['hip']
    sx, sy = s['sh']
    torso = cv.mask().poly([(hx - 3, hy + 1), (hx + 3, hy + 1), (sx + 4, sy + 1), (sx - 3, sy)])
    cv.part(torso, CLOTH)
    plate = cv.mask().poly([(hx - 2, hy - 2), (hx + 3, hy - 2), (sx + 4, sy + 1), (sx - 2, sy + 1)])
    cv.part(plate, IRON)
    if TIER >= 2:   # gold trim down the breastplate
        tm = cv.mask().line(sx + 1, sy + 1, hx + 1, hy - 2, 1)
        cv.part(tm, TRIM, shade=False, separate=False)
    draw_leg(cv, (hx + 1, hy), s['f_foot'], TROUSER, BOOT)
    # red tabard flaps below the plate
    tab = cv.mask().poly([(hx - 3, hy - 2), (hx + 3, hy - 2), (hx + 4, hy + 3), (hx - 4, hy + 3)])
    cv.part(tab, CLOTH)
    belt = cv.mask().rect(hx - 3, hy - 2, hx + 3, hy - 2)
    cv.part(belt, HILT, shade=False)
    # scarf wrap around the neck
    wrap = cv.mask().rect(sx - 3, sy - 1, sx + 3, sy + 1)
    cv.part(wrap, SCARF)
    draw_head(cv, s['head'], SKIN, hair, p.eyes)
    crest(cv, s['head'][0], s['head'][1])
    # pauldron on the front shoulder
    fsx, fsy = s['f_sh']
    pm = cv.mask().ellipse(fsx, fsy, 2.6, 2.2)
    cv.part(pm, PAULDRON)
    elbow = draw_arm(cv, (fsx, fsy + 1), s['f_hand'], CLOTH, SKIN, bend=1, glove=BOOT)
    if not p.extra.get('no_sword'):
        blade(cv, s['f_hand'], p.weapon, {1: 13, 2: 15, 3: 17}[TIER],
              STEEL, EMBER if not p.extra.get('glow') else Pal('#ffe27a', '#fff6c8', '#ffb040'),
              HILT, GUARD, width=3 if TIER < 3 else 4, guard_w=2 if TIER == 1 else 3)
    cv.outline()
    if TIER == 3 and not p.extra.get('glow'):
        cv.glow((255, 110, 30), alpha=55)
    if p.extra.get('glow'):
        cv.glow((255, 140, 40), alpha=120)
    for (x, y, i) in p.extra.get('sparks', []):
        cv.dot(x, y, SPARK[i % 3])
    return cv.image()


# ------------------------------------------------------------------ animations
def idle():
    frames = []
    for i in range(4):
        bob = [0, 0, 1, 1][i]
        p = Pose(oy=bob, lean=2, f_foot=(30, GROUND), b_foot=(18, GROUND),
                 f_hand=(31, 33 + bob), b_hand=(21, 35 + bob), weapon=-32 - bob * 2,
                 extra={'scarf': i * math.pi / 2})
        p.crouch = 0
        frames.append(draw(p))
    return frames


def attack():
    """Ember Slash: wind-up, two strikes, recover (7 frames)."""
    seq = [
        # wind-up: sword raised behind
        dict(lean=0, crouch=1, f_hand=(27, 27), b_hand=(21, 34), weapon=-120, eyes='fierce'),
        dict(lean=-1, crouch=1, f_hand=(25, 25), b_hand=(20, 33), weapon=-150, eyes='fierce'),
        # strike 1: diagonal downward slash
        dict(lean=3, crouch=2, f_hand=(33, 34), b_hand=(20, 35), weapon=20, eyes='fierce',
             f_foot=(32, GROUND), sparks=[(40, 38, 0), (42, 35, 1), (38, 41, 2)], slash=1),
        # reverse swing up
        dict(lean=3, crouch=1, f_hand=(32, 28), b_hand=(21, 34), weapon=-70, eyes='fierce',
             f_foot=(32, GROUND)),
        # strike 2: horizontal cut
        dict(lean=4, crouch=2, f_hand=(34, 31), b_hand=(20, 34), weapon=-5, eyes='fierce',
             f_foot=(33, GROUND), sparks=[(45, 29, 1), (44, 33, 0), (46, 31, 2)], slash=2),
        dict(lean=3, crouch=1, f_hand=(33, 33), b_hand=(21, 35), weapon=10, eyes='open',
             f_foot=(32, GROUND)),
        dict(lean=2, crouch=0, f_hand=(31, 33), b_hand=(21, 35), weapon=-30, eyes='open'),
    ]
    return [draw(_mk(d, i)) for i, d in enumerate(seq)]


def _mk(d, i):
    extra = {'scarf': i * 1.1, 'sparks': d.pop('sparks', []), 'glow': d.pop('glow', False),
             'no_sword': d.pop('no_sword', False)}
    d.pop('slash', None)
    kw = dict(f_foot=(30, GROUND), b_foot=(18, GROUND))
    kw.update(d)
    return Pose(extra=extra, **kw)


def hit():
    seq = [
        dict(lean=-2, ox=-2, f_hand=(27, 35), b_hand=(18, 33), weapon=-10, eyes='hurt', head_dx=-1),
        dict(lean=-1, ox=-1, f_hand=(28, 34), b_hand=(19, 34), weapon=-20, eyes='hurt'),
        dict(lean=1, f_hand=(30, 33), b_hand=(20, 35), weapon=-30, eyes='open'),
    ]
    return [draw(_mk(d, i)) for i, d in enumerate(seq)]


def victory():
    seq = []
    for i in range(4):
        up = [0, -1, -1, 0][i]
        seq.append(dict(lean=1, oy=up, f_hand=(29, 20 + up), b_hand=(21, 33 + up), weapon=-70,
                        eyes='closed' if i in (1, 2) else 'open',
                        sparks=[(33 + (i * 3) % 5, 6 + i, i), (37 - i, 9 + (i * 2) % 4, i + 1)]))
    return [draw(_mk(d, i)) for i, d in enumerate(seq)]


def ko():
    kneel = dict(lean=2, crouch=4, f_hand=(31, 41), b_hand=(20, 38), weapon=80, eyes='hurt',
                 f_foot=(30, GROUND), b_foot=(17, GROUND))
    down = dict(lean=0, f_hand=(29, 36), b_hand=(19, 36), weapon=70, eyes='ko', no_sword=True)
    f1 = draw(_mk(kneel, 0))
    p = _mk(down, 1)
    p.extra['no_sword'] = True
    return [f1, lying(draw(p))]


def burst():
    """Inferno Break: charge, leap, three rapid strikes, heavy downward slash (11 frames)."""
    seq = [
        dict(lean=0, crouch=2, f_hand=(28, 31), b_hand=(21, 33), weapon=-60, eyes='fierce', glow=True),
        dict(lean=-1, crouch=3, f_hand=(27, 30), b_hand=(20, 33), weapon=-80, eyes='fierce', glow=True,
             sparks=[(30, 12, 0), (22, 18, 1), (35, 16, 2)]),
        # leap
        dict(lean=2, oy=-5, f_hand=(31, 21), b_hand=(21, 27), weapon=-100, eyes='fierce', glow=True,
             f_foot=(28, GROUND - 2), b_foot=(21, GROUND - 1)),
        # rapid strike 1
        dict(lean=4, oy=-3, f_hand=(35, 30), b_hand=(21, 30), weapon=15, eyes='fierce', glow=True,
             sparks=[(43, 35, 0), (45, 32, 1)]),
        dict(lean=3, oy=-3, f_hand=(33, 25), b_hand=(21, 30), weapon=-60, eyes='fierce', glow=True),
        # rapid strike 2
        dict(lean=4, oy=-2, f_hand=(35, 29), b_hand=(21, 31), weapon=-8, eyes='fierce', glow=True,
             sparks=[(46, 28, 2), (44, 31, 0)]),
        dict(lean=3, oy=-2, f_hand=(33, 24), b_hand=(21, 31), weapon=-75, eyes='fierce', glow=True),
        # rapid strike 3
        dict(lean=4, oy=-1, f_hand=(35, 32), b_hand=(20, 32), weapon=25, eyes='fierce', glow=True,
             sparks=[(42, 39, 1), (45, 36, 2)]),
        # raise for the heavy slash
        dict(lean=0, oy=-4, f_hand=(27, 20), b_hand=(22, 23), weapon=-100, eyes='fierce', glow=True,
             sparks=[(26, 5, 0), (31, 7, 1), (23, 8, 2)]),
        # heavy downward slash
        dict(lean=5, crouch=4, f_hand=(35, 38), b_hand=(24, 37), weapon=60, eyes='fierce', glow=True,
             f_foot=(33, GROUND), sparks=[(40, 44, 0), (44, 42, 1), (37, 45, 2), (46, 45, 0)]),
        dict(lean=2, crouch=1, f_hand=(31, 34), b_hand=(21, 35), weapon=-20, eyes='open'),
    ]
    return [draw(_mk(d, i)) for i, d in enumerate(seq)]


def guard():
    """Braced stance: blade held upright across the body (loops while guarding)."""
    seq = []
    for i in range(3):
        seq.append(dict(lean=-1, crouch=2 + (i == 1), f_hand=(29, 31), b_hand=(26, 32), weapon=-95 + i * 2,
                        eyes='fierce', f_foot=(31, GROUND), b_foot=(16, GROUND)))
    return [draw(_mk(d, i)) for i, d in enumerate(seq)]

ANIMS = [('idle', idle, 6, True), ('attack', attack, 14, False), ('hit', hit, 10, False),
         ('victory', victory, 6, True), ('ko', ko, 6, False), ('burst', burst, 12, False),
         ('guard', guard, 6, True)]
