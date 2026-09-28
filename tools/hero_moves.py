"""
hero_moves - choreography for hero_gen archetypes.

Each archetype returns the seven battle animations as lists of pose dicts
(see hero_gen.GP) plus fps and skill timing metadata. All tiers of a family
share the archetype, so frame counts / hit frames are identical across tiers.

Pose dict keys: ox oy crouch lean ff bf fh bh head_dx head_dy eyes w w2 glow fx
plus weapon/feature flags (lsw, lit, spin, draw, arrows, nock, planted, sraise,
axe_front, club_front, tome_up, open, noweapon, cape_fly, hair_fly ...).
Hands (fh/bh) are offsets from the shoulders; feet (ff/bf) are (x offset, lift).
"""
import math

D = dict
FPS = {'idle': 6, 'attack': 12, 'hit': 10, 'victory': 6, 'ko': 6, 'burst': 11, 'guard': 6}
ORDER = ['idle', 'attack', 'hit', 'victory', 'ko', 'burst', 'guard']
LOOP = {'idle': True, 'victory': True, 'guard': True}


def with_(base, **kw):
    d = dict(base)
    d.update(kw)
    return d


def std_hit(base, dw=-10):
    lean = base.get('lean', 1)
    return [with_(base, lean=lean - 3, ox=base.get('ox', 0) - 2, eyes='hurt', head_dx=-1, w=base['w'] + dw),
            with_(base, lean=lean - 2, ox=base.get('ox', 0) - 1, eyes='hurt', w=base['w'] + dw / 2),
            with_(base)]


def std_ko(kneel, down):
    return [kneel, with_(down, eyes='ko', lying=True)]


def ring(r, ry, n, ph):
    return ('ring', 'focus', 0, r, ry, n, ph)


def bring(cx, cy, r, ry, n, ph):
    return ('ring', cx, cy, r, ry, n, ph)


# ================================================================ lantern (Rhea)
def lantern():
    idle = [D(oy=b, fh=(3, 4 + b), bh=(-1, 6 + b), w=-80, lsw=sw)
            for b, sw in zip((0, 0, 1, 1), (0, 1, 0, -1))]
    base = idle[0]
    attack = [
        D(lean=0, crouch=1, fh=(0, 2), bh=(-2, 5), w=-104, lsw=-2, eyes='fierce', fx=[ring(4, 3, 3, 0.0)]),
        D(lean=-1, crouch=1, fh=(-2, 0), bh=(-3, 4), w=-122, lsw=-3, eyes='fierce', lit=True,
          fx=[ring(5, 4, 4, 1.0)]),
        D(lean=3, fh=(6, 0), bh=(-1, 5), w=-45, lsw=3, eyes='fierce', lit=True, ff=(8, 0), cape_fly=1),
        D(lean=4, fh=(7, 1), bh=(0, 5), w=-30, lsw=4, eyes='fierce', ff=(8, 0), cape_fly=1,
          fx=[('bolt', 44, 21, 'ember'), (40, 24, 0), (38, 20, 1)]),
        D(lean=2, fh=(5, 3), bh=(-1, 6), w=-55, lsw=2, ff=(7, 0)),
        D(lean=1, fh=(3, 4), bh=(-1, 6), w=-76, lsw=0),
    ]
    victory = [D(oy=u, fh=(2, -6 + u), bh=(-2, 4 + u), w=-88, lsw=sw, lit=True,
                 eyes='closed' if i in (1, 2) else 'open', fx=[ring(6, 4, 3, i * 0.9)])
               for i, (u, sw) in enumerate(zip((0, -1, -1, 0), (1, 0, -1, 0)))]
    ko = std_ko(D(lean=2, crouch=4, fh=(4, 7), bh=(0, 6), w=-12, eyes='hurt', ff=(6, 0), bf=(-6, 0), lsw=2),
                D(fh=(2, 6), bh=(-1, 6), w=-80, noweapon=True))
    burst = [
        D(fh=(3, 3), bh=(-1, 6), w=-85, eyes='closed', glow=True, lit=True),
        D(fh=(2, -2), bh=(-2, 2), w=-88, eyes='closed', glow=True, lit=True, fx=[ring(5, 3, 4, 0.0)]),
        D(oy=-1, fh=(1, -6), bh=(-3, 0), w=-90, eyes='fierce', glow=True, lit=True, fx=[ring(7, 5, 5, 0.3)]),
        D(oy=-2, fh=(1, -7), bh=(-3, -1), w=-90, eyes='fierce', glow=True, lit=True, lsw=1,
          fx=[ring(9, 6, 6, 1.1)]),
        D(oy=-2, fh=(1, -7), bh=(-3, -1), w=-90, eyes='fierce', glow=True, lit=True, lsw=-1,
          fx=[ring(11, 7, 7, 1.9)]),
        D(oy=-1, fh=(1, -7), bh=(-4, -2), w=-90, eyes='fierce', glow=True, lit=True,
          fx=[('star', 'focus', 0, 3), bring(24, 30, 17, 9, 10, 0.2)]),
        D(crouch=1, fh=(2, -3), bh=(-2, 3), w=-88, glow=True, lit=True,
          fx=[bring(24, 30, 20, 10, 10, 0.5)]),
        D(crouch=1, fh=(3, 1), bh=(-1, 5), w=-84, lit=True, fx=[(10, 38, 0), (40, 36, 1), (16, 30, 2), (35, 28, 0)]),
        D(fh=(3, 3), bh=(-1, 6), w=-80, fx=[(12, 42, 1), (38, 41, 0)]),
        D(fh=(3, 4), bh=(-1, 6), w=-80),
    ]
    guard = [D(lean=-1, crouch=2 + (i == 1), fh=(3, 2), bh=(1, 4), w=-62 + i, lsw=-1 + i, eyes='fierce',
               ff=(7, 0), bf=(-7, 0)) for i in range(3)]
    return dict(idle=idle, attack=attack, hit=std_hit(base, -12), victory=victory, ko=ko, burst=burst, guard=guard)


# ================================================================ blossom staff (Faye)
def blossom():
    idle = [D(oy=b, fh=(3, 4 + b), bh=(-1, 6 + b), w=-82, spin=i * 0.3) for i, b in enumerate((0, 0, 1, 1))]
    base = idle[0]
    attack = [
        D(fh=(3, 1), bh=(-1, 5), w=-88, eyes='closed', spin=0.0, fx=[('petal', 36, 14), ('petal', 30, 12)]),
        D(lean=0, fh=(0, -1), bh=(-3, 3), w=-112, eyes='closed', spin=0.6,
          fx=[ring(5, 4, 4, 0.0)]),
        D(lean=2, fh=(5, 1), bh=(-1, 5), w=-50, spin=1.2, fx=[ring(4, 3, 4, 0.8)]),
        D(lean=3, fh=(7, 2), bh=(0, 5), w=-26, spin=1.8, ff=(8, 0),
          fx=[('bolt', 44, 22, 'petals'), ('petal', 39, 19)]),
        D(lean=2, fh=(5, 3), bh=(-1, 6), w=-55, spin=2.4),
        D(lean=1, fh=(3, 4), bh=(-1, 6), w=-78, spin=3.0),
    ]
    victory = [D(oy=u, fh=(2, -5 + u), bh=(-3, 1 + u), w=-90, spin=i * 0.8,
                 eyes='closed' if i in (1, 2) else 'open',
                 fx=[('petal', 16 + i * 3, 10 + (i * 5) % 7), ('petal', 34 - i * 2, 8 + i * 2)])
               for i, u in enumerate((0, -1, -1, 0))]
    ko = std_ko(D(lean=2, crouch=4, fh=(4, 7), bh=(0, 6), w=-15, eyes='hurt', ff=(6, 0), bf=(-6, 0)),
                D(fh=(2, 6), bh=(-1, 6), w=-80, noweapon=True))
    burst = [
        D(fh=(3, 3), bh=(-1, 6), w=-86, eyes='closed', glow=True),
        D(fh=(2, -2), bh=(-2, 2), w=-90, eyes='closed', glow=True, spin=0.5,
          fx=[('petal', 14, 20), ('petal', 36, 18)]),
        D(oy=-1, fh=(2, -6), bh=(-3, -1), w=-90, glow=True, spin=1.0, fx=[ring(7, 5, 5, 0.0)]),
        D(oy=-2, fh=(2, -7), bh=(-3, -2), w=-90, glow=True, spin=1.6, eyes='fierce', fx=[ring(9, 6, 6, 0.7)]),
        D(oy=-2, fh=(2, -7), bh=(-3, -2), w=-90, glow=True, spin=2.2, eyes='fierce', fx=[ring(11, 7, 7, 1.4)]),
        D(crouch=1, fh=(5, 4), bh=(-2, 3), w=-89, glow=True, spin=2.8,
          fx=[('star', 'focus', 0, 3), bring(26, 43, 14, 2, 10, 0.0)]),
        D(crouch=2, fh=(5, 5), bh=(-3, 2), w=-89, glow=True, spin=3.2,
          fx=[bring(26, 43, 19, 3, 12, 0.3), ('petal', 12, 32), ('petal', 38, 30), ('petal', 22, 24)]),
        D(crouch=1, fh=(4, 4), bh=(-2, 4), w=-86, spin=3.6,
          fx=[('petal', 10, 22), ('petal', 40, 18), ('petal', 20, 14), ('petal', 32, 10)]),
        D(fh=(3, 4), bh=(-1, 6), w=-82, fx=[('petal', 14, 10), ('petal', 36, 6)]),
        D(fh=(3, 4), bh=(-1, 6), w=-82),
    ]
    guard = [D(lean=-1, crouch=2, fh=(4, 1), bh=(2, 3), w=-70, spin=i * 0.4, eyes='fierce',
               fx=[('petal', 38, 22 + i), ('petal', 36, 32 - i)]) for i in range(3)]
    return dict(idle=idle, attack=attack, hit=std_hit(base, -10), victory=victory, ko=ko, burst=burst, guard=guard)


# ================================================================ great axe (Voss)
def greataxe():
    G = ('grip', 5)
    idle = [D(oy=b, fh=(3, 3 + b), bh=G, w=66 - b, bflip=True, ff=(6, 0), bf=(-6, 0)) for b in (0, 0, 1, 1)]
    base = idle[0]
    attack = [
        D(lean=0, crouch=1, fh=(2, 3), bh=G, w=-96, ff=(6, 0), bf=(-6, 0)),
        D(lean=-1, fh=(0, -4), bh=G, w=-140, eyes='fierce', ff=(6, 0), bf=(-6, 0)),
        D(lean=-2, oy=-1, fh=(-1, -6), bh=G, w=-172, eyes='fierce', ff=(6, 0), bf=(-6, 0), fx=[(14, 12, 0), (18, 9, 1)]),
        D(lean=4, crouch=3, fh=(6, 5), bh=G, w=42, eyes='fierce', ff=(9, 0), bf=(-6, 0), axe_front=True,
          fx=[('crack', 42, 43, 4), (44, 38, 0), (40, 37, 2), (46, 40, 1)]),
        D(lean=2, crouch=1, fh=(4, 0), bh=G, w=-72, eyes='fierce', ff=(8, 0), bf=(-6, 0)),
        D(lean=5, crouch=2, fh=(7, 2), bh=G, w=-8, eyes='fierce', ff=(9, 0), bf=(-6, 0), axe_front=True,
          fx=[('streak', 44, 22, 46, 34, 0), (43, 30, 2)]),
        D(lean=2, crouch=1, fh=(4, 4), bh=G, w=-44, ff=(7, 0), bf=(-6, 0)),
        D(lean=1, fh=(3, 4), bh=G, w=30, bflip=True, ff=(6, 0), bf=(-6, 0)),
    ]
    victory = [D(oy=u, fh=(1, -6 + u), bh=(-1, 4 + u), w=-100, eyes='closed' if i in (1, 2) else 'fierce',
                 ff=(6, 0), bf=(-6, 0), fx=[(30 + i, 6 + (i % 2), i), (36 - i, 9, i + 1)])
               for i, u in enumerate((0, -1, -1, 0))]
    ko = std_ko(D(lean=2, crouch=4, fh=(5, 7), bh=G, w=30, eyes='hurt', ff=(6, 0), bf=(-6, 0)),
                D(fh=(3, 6), bh=(-1, 6), w=-60, noweapon=True))
    burst = [
        D(crouch=2, fh=(2, 4), bh=G, w=-80, eyes='fierce', glow=True, ff=(6, 0), bf=(-6, 0)),
        D(crouch=4, lean=0, fh=(1, 2), bh=G, w=-112, eyes='fierce', glow=True, ff=(6, 0), bf=(-6, 0),
          fx=[(12, 36, 0), (36, 34, 1), (16, 28, 2), (33, 26, 0)]),
        D(oy=-6, lean=0, fh=(0, -5), bh=G, w=-150, eyes='fierce', glow=True, ff=(4, -3), bf=(-4, -1),
          fx=[(20, 44, 0), (27, 45, 1), (24, 42, 2)]),
        D(oy=-9, lean=-1, fh=(-1, -7), bh=G, w=-176, eyes='fierce', glow=True, ff=(3, -4), bf=(-4, -3),
          fx=[(10, 8, 0), (8, 14, 1)]),
        D(oy=-5, lean=4, fh=(6, 1), bh=G, w=-4, eyes='fierce', glow=True, axe_front=True, ff=(6, -2), bf=(-4, -1),
          fx=[('streak', 43, 18, 46, 32, 0)]),
        D(crouch=4, lean=5, fh=(6, 6), bh=G, w=55, eyes='fierce', glow=True, axe_front=True, ff=(9, 0), bf=(-6, 0),
          fx=[('crack', 40, 43, 7), ('star', 42, 40, 2)]),
        D(crouch=4, lean=5, fh=(6, 6), bh=G, w=57, eyes='fierce', glow=True, axe_front=True, ff=(9, 0), bf=(-6, 0),
          fx=[('crack', 40, 43, 9), ('column', 34, 30, 42), ('column', 44, 26, 42), ('column', 39, 33, 42)]),
        D(crouch=3, lean=4, fh=(6, 6), bh=G, w=57, eyes='fierce', axe_front=True, ff=(9, 0), bf=(-6, 0),
          fx=[('column', 36, 34, 42), ('column', 45, 32, 42), (30, 28, 1), (42, 24, 2)]),
        D(crouch=1, lean=2, fh=(4, 2), bh=G, w=-50, ff=(7, 0), bf=(-6, 0)),
        D(lean=1, fh=(3, 4), bh=G, w=20, bflip=True, ff=(6, 0), bf=(-6, 0)),
        D(lean=1, fh=(3, 3), bh=G, w=64, bflip=True, ff=(6, 0), bf=(-6, 0)),
    ]
    guard = [D(lean=-1, crouch=2 + (i == 1), fh=(5, 3), bh=('grip', 7), w=-93 + i, eyes='fierce', ff=(8, 0),
               bf=(-7, 0)) for i in range(3)]
    return dict(idle=idle, attack=attack, hit=std_hit(base, -8), victory=victory, ko=ko, burst=burst, guard=guard)


# ================================================================ spear (Seraphine)
def spear():
    G = ('grip', 7)
    idle = [D(oy=b, fh=(3, 5 + b), bh=G, w=-72 + b, pen=[0, 1, 1.5, 0.5][i]) for i, b in enumerate((0, 0, 1, 1))]
    base = idle[0]
    attack = [
        D(ox=-5, lean=0, crouch=1, fh=(1, 4), bh=G, w=-8, eyes='fierce', ff=(7, 0), bf=(-6, 0)),
        D(ox=-6, lean=-1, crouch=1, fh=(-1, 4), bh=G, w=-6, eyes='fierce', ff=(7, 0), bf=(-6, 0), pen=1.5),
        D(ox=-6, lean=4, crouch=1, fh=(7, 3), bh=G, w=-4, eyes='fierce', ff=(10, 0), bf=(-6, 0), pen=-1,
          hair_fly=1, fx=[('star', 45, 26, 1)]),
        D(ox=-6, lean=1, fh=(2, 4), bh=G, w=-12, eyes='fierce', ff=(8, 0), bf=(-6, 0)),
        D(ox=-6, lean=4, fh=(7, 1), bh=G, w=-16, eyes='fierce', ff=(10, 0), bf=(-6, 0), pen=-1, hair_fly=1,
          fx=[('star', 45, 20, 1)]),
        D(ox=-7, lean=-1, crouch=2, fh=(-1, 4), bh=G, w=-4, eyes='fierce', ff=(8, 0), bf=(-6, 0), pen=2),
        D(ox=-6, lean=5, crouch=2, fh=(8, 3), bh=G, w=0, eyes='fierce', ff=(11, 0), bf=(-7, 0), pen=-1, hair_fly=2,
          fx=[('star', 45, 29, 2), ('streak', 30, 29, 38, 29, 0)]),
        D(ox=-3, lean=2, fh=(4, 4), bh=G, w=-40, ff=(8, 0), bf=(-6, 0)),
    ]
    victory = [D(oy=u, fh=(2, -3 + u), bh=(-2, 4 + u), w=-90, pen=i * 0.7, eyes='closed' if i in (1, 2) else 'open',
                 fx=[(36 + i % 2, 5 + i, i), (30 - i, 8 + (i * 3) % 4, i + 1)])
               for i, u in enumerate((0, -1, -1, 0))]
    ko = std_ko(D(lean=2, crouch=4, fh=(4, 7), bh=G, w=-160, eyes='hurt', ff=(6, 0), bf=(-6, 0)),
                D(fh=(2, 6), bh=(-1, 6), w=-80, noweapon=True))
    T = D(glow=True, eyes='fierce', ff=(10, 0), bf=(-6, 0), bh=G, hair_fly=1)
    burst = [
        D(ox=-5, crouch=1, fh=(1, 4), bh=G, w=-8, eyes='fierce', glow=True, ff=(7, 0), bf=(-6, 0),
          fx=[(20, 20, 0), (32, 16, 1)]),
        D(ox=-6, crouch=2, lean=-1, fh=(-1, 4), bh=G, w=-6, eyes='fierce', glow=True, ff=(7, 0), bf=(-6, 0),
          fx=[(16, 18, 1), (28, 12, 2), (36, 20, 0)]),
        with_(T, ox=-6, lean=4, fh=(7, 3), w=-4, fx=[('star', 45, 26, 1)]),
        with_(T, ox=-6, lean=3, fh=(6, 0), w=-18, fx=[('star', 45, 18, 1), (40, 26, 0)]),
        with_(T, ox=-6, lean=4, fh=(7, 5), w=8, fx=[('star', 45, 31, 1), (41, 21, 0)]),
        with_(T, ox=-6, lean=3, fh=(6, 1), w=-12, fx=[('star', 45, 22, 1), (40, 30, 2)]),
        with_(T, ox=-6, lean=4, fh=(7, 3), w=-2, fx=[('star', 45, 27, 1), (42, 20, 0), (41, 33, 2)]),
        D(ox=-8, lean=-2, crouch=3, fh=(-2, 4), bh=G, w=-4, eyes='fierce', glow=True, ff=(8, 0), bf=(-6, 0), pen=2,
          fx=[ring(5, 5, 6, 0.0), (14, 30, 0), (12, 24, 1)]),
        D(ox=-5, lean=6, crouch=2, fh=(8, 3), bh=G, w=0, eyes='fierce', glow=True, ff=(12, 0), bf=(-8, 0), pen=-2,
          hair_fly=2, fx=[('streak', 16, 28, 30, 29, 0), ('streak', 18, 32, 28, 32, 1), ('star', 45, 30, 2)]),
        D(ox=-4, lean=6, crouch=2, fh=(8, 3), bh=G, w=0, eyes='fierce', glow=True, ff=(12, 0), bf=(-8, 0), pen=-2,
          hair_fly=2, fx=[('column', 44, 22, 38), ('column', 40, 26, 36), ('star', 45, 30, 3)]),
        D(ox=-2, lean=2, fh=(4, 4), bh=G, w=-40, ff=(8, 0), bf=(-6, 0)),
        D(lean=1, fh=(3, 5), bh=G, w=-70),
    ]
    guard = [D(lean=-1, crouch=2 + (i == 1), fh=(4, 3), bh=('grip', 8), w=-58 + i, eyes='fierce', ff=(8, 0),
               bf=(-7, 0), pen=i * 0.5) for i in range(3)]
    return dict(idle=idle, attack=attack, hit=std_hit(base, -8), victory=victory, ko=ko, burst=burst, guard=guard)


# ================================================================ trident + shell (Corin)
def trident():
    """Hoplite stance: shell buckler on the lead (front) arm, trident in the rear hand."""
    idle = [D(oy=b, fh=(5, 3 + b), bh=(-1, 2 + b), w=-86, ff=(6, 0), bf=(-6, 0)) for b in (0, 0, 1, 1)]
    base = idle[0]
    attack = [
        D(ox=-3, lean=0, crouch=1, fh=(4, 3), bh=(-3, 3), w=-8, eyes='fierce', ff=(6, 0), bf=(-6, 0)),
        D(ox=-4, lean=-1, crouch=1, fh=(4, 3), bh=(-5, 3), w=-6, eyes='fierce', ff=(6, 0), bf=(-6, 0)),
        D(ox=-4, lean=4, crouch=1, fh=(3, 5), bh=(9, 2), w=-5, eyes='fierce', ff=(9, 0), bf=(-6, 0),
          fx=[('star', 'focus', 0, 1), (42, 32, 2)]),
        D(ox=-3, lean=1, fh=(4, 3), bh=(1, 3), w=-40, ff=(7, 0), bf=(-6, 0)),
        D(ox=-1, lean=5, crouch=1, fh=(9, 1), bh=(-1, 3), w=-80, eyes='fierce', ff=(9, 0), bf=(-6, 0),
          fx=[(45, 23, 0), (46, 29, 1), (44, 34, 2), (46, 26, 2)]),
        D(lean=2, fh=(6, 3), bh=(0, 3), w=-84, ff=(7, 0), bf=(-6, 0)),
        D(lean=1, fh=(5, 3), bh=(-1, 2), w=-86, ff=(6, 0), bf=(-6, 0)),
    ]
    victory = [D(oy=u, fh=(5, 3 + u), bh=(1, -5 + u), w=-90, eyes='closed' if i in (1, 2) else 'open',
                 ff=(6, 0), bf=(-6, 0), fx=[ring(4, 3, 3, i * 1.1)])
               for i, u in enumerate((0, -1, -1, 0))]
    ko = std_ko(D(lean=2, crouch=4, fh=(5, 6), bh=(0, 5), w=-30, eyes='hurt', ff=(6, 0), bf=(-6, 0)),
                D(fh=(3, 6), bh=(-1, 6), w=-80, noweapon=True))
    burst = [
        D(fh=(5, 3), bh=(-1, 2), w=-86, eyes='closed', glow=True, ff=(6, 0), bf=(-6, 0)),
        D(fh=(5, 2), bh=(1, -3), w=-88, eyes='fierce', glow=True, ff=(6, 0), bf=(-6, 0), fx=[ring(4, 4, 4, 0.0)]),
        D(oy=-1, fh=(5, 1), bh=(1, -5), w=-89, eyes='fierce', glow=True, ff=(6, 0), bf=(-6, 0),
          fx=[ring(5, 5, 5, 0.6)]),
        D(crouch=2, fh=(5, 3), bh=(3, 4), w=-90, planted=True, eyes='fierce', glow=True, ff=(7, 0), bf=(-6, 0),
          fx=[('crack', 25, 43, 6), (28, 40, 0), (21, 40, 1)]),
        D(crouch=2, fh=(3, -5), bh=(3, 4), w=-90, planted=True, eyes='fierce', glow=True, ff=(7, 0),
          bf=(-6, 0), fx=[('column', 12, 30, 42), ('column', 40, 30, 42), (18, 26, 1), (36, 24, 2)]),
        D(crouch=1, fh=(3, -7), bh=(3, 4), w=-90, planted=True, eyes='fierce', glow=True, ff=(7, 0),
          bf=(-6, 0), fx=[bring(25, 30, 16, 12, 12, 0.0), ('star', 'focus', 0, 2)]),
        D(crouch=1, fh=(3, -7), bh=(3, 4), w=-90, planted=True, eyes='fierce', glow=True, ff=(7, 0),
          bf=(-6, 0), fx=[bring(25, 30, 20, 13, 14, 0.3)]),
        D(crouch=1, fh=(5, -1), bh=(3, 4), w=-90, planted=True, ff=(7, 0), bf=(-6, 0),
          fx=[(8, 34, 0), (42, 30, 1), (12, 22, 2)]),
        D(fh=(5, 2), bh=(0, 2), w=-87, ff=(6, 0), bf=(-6, 0)),
        D(fh=(5, 3), bh=(-1, 2), w=-86, ff=(6, 0), bf=(-6, 0)),
    ]
    guard = [D(lean=0, crouch=2 + (i == 1), fh=(8, 2), bh=(-1, 3), w=-94, eyes='fierce', ff=(8, 0),
               bf=(-7, 0)) for i in range(3)]
    return dict(idle=idle, attack=attack, hit=std_hit(base, -8), victory=victory, ko=ko, burst=burst, guard=guard)


# ================================================================ twin daggers (Nerys)
def daggers():
    idle = [D(oy=b, crouch=1, lean=2, fh=(4, 4 + b), bh=(1, 5 + b), w=-40 - b * 3, w2=140, ff=(7, 0), bf=(-6, 0))
            for b in (0, 0, 1, 1)]
    base = idle[0]
    attack = [
        D(crouch=3, lean=0, fh=(1, 2), bh=(1, 3), w=-120, w2=-150, eyes='fierce', ff=(6, 0), bf=(-6, 0)),
        D(ox=2, lean=4, crouch=1, fh=(4, -2), bh=(2, 2), w=-100, w2=-160, eyes='fierce', ff=(9, 0), bf=(-4, 0),
          fx=[('streak', 8, 30, 14, 30, 0), ('streak', 9, 34, 13, 34, 1)]),
        D(ox=2, lean=4, crouch=2, fh=(7, 5), bh=(1, 4), w=40, w2=-150, eyes='fierce', ff=(9, 0), bf=(-4, 0),
          fx=[('streak', 38, 22, 44, 34, 2)]),
        D(ox=2, lean=3, crouch=1, fh=(2, 4), bh=(9, 1), w=-60, w2=0, eyes='fierce', ff=(9, 0), bf=(-4, 0),
          fx=[('streak', 34, 26, 44, 28, 0)]),
        D(ox=2, lean=4, fh=(7, -1), bh=(3, 5), w=-60, w2=120, eyes='fierce', ff=(9, 0), bf=(-4, 0),
          fx=[('streak', 42, 36, 44, 22, 1)]),
        D(ox=2, lean=5, crouch=2, fh=(8, 3), bh=(8, 4), w=-2, w2=12, eyes='fierce', ff=(10, 0), bf=(-4, 0),
          fx=[('star', 44, 30, 2), ('streak', 36, 22, 44, 36, 0)]),
        D(ox=1, lean=1, crouch=1, fh=(4, 4), bh=(1, 5), w=-30, w2=150, ff=(7, 0), bf=(-5, 0)),
        D(crouch=1, lean=2, fh=(4, 4), bh=(1, 5), w=-40, w2=140, ff=(7, 0), bf=(-6, 0)),
    ]
    victory = [D(oy=u, lean=1, fh=(2, -3 + u), bh=(-2, 5 + u), w=-80 + i * 90, w2=150,
                 eyes='closed' if i in (1, 2) else 'open', fx=[(34 + i, 8 + i, i), (38 - i, 12, i + 1)])
               for i, u in enumerate((0, -1, -1, 0))]
    ko = std_ko(D(lean=2, crouch=4, fh=(4, 7), bh=(1, 6), w=60, w2=150, eyes='hurt', ff=(6, 0), bf=(-6, 0)),
                D(fh=(2, 6), bh=(-1, 6), w=-80, noweapon=True))
    F = D(glow=True, eyes='fierce', ff=(10, 0), bf=(-4, 0), ox=2)
    burst = [
        D(crouch=3, lean=0, fh=(5, 1), bh=(5, 2), w=-50, w2=-130, eyes='fierce', glow=True, ff=(6, 0), bf=(-6, 0),
          fx=[(16, 24, 0), (32, 20, 1)]),
        D(ox=3, lean=5, crouch=1, fh=(4, -2), bh=(2, 2), w=-100, w2=-160, eyes='fierce', glow=True, ff=(10, 0),
          bf=(-3, 0), fx=[('streak', 4, 28, 14, 28, 0), ('streak', 6, 33, 14, 33, 1), ('streak', 8, 38, 13, 38, 2)]),
        with_(F, lean=4, crouch=2, fh=(7, 5), bh=(1, 4), w=40, w2=-150, fx=[('streak', 38, 22, 44, 34, 2)]),
        with_(F, lean=3, crouch=1, fh=(2, 4), bh=(9, 1), w=-60, w2=0, fx=[('streak', 34, 26, 44, 28, 0)]),
        with_(F, lean=4, fh=(7, -1), bh=(3, 5), w=-60, w2=120, fx=[('streak', 42, 36, 44, 22, 1)]),
        with_(F, lean=3, crouch=2, fh=(3, 5), bh=(9, 4), w=-50, w2=40, fx=[('streak', 36, 24, 44, 38, 2)]),
        with_(F, lean=4, crouch=1, fh=(8, 2), bh=(2, 3), w=-20, w2=-150, fx=[('streak', 34, 32, 44, 22, 0)]),
        with_(F, lean=5, crouch=2, fh=(8, 3), bh=(8, 4), w=-2, w2=12, fx=[('star', 44, 30, 2)]),
        D(ox=1, oy=-5, lean=2, fh=(2, -6), bh=(0, -5), w=-100, w2=-80, eyes='fierce', glow=True, ff=(4, -2),
          bf=(-4, -1), fx=[(30, 4, 0), (20, 6, 1)]),
        D(ox=2, lean=5, crouch=3, fh=(7, 6), bh=(6, 5), w=50, w2=70, eyes='fierce', glow=True, ff=(10, 0), bf=(-5, 0),
          fx=[('streak', 34, 18, 46, 40, 0), ('streak', 46, 18, 34, 40, 1), ('star', 40, 29, 3)]),
        D(ox=1, lean=2, crouch=2, fh=(4, 4), bh=(1, 5), w=-30, w2=150, ff=(7, 0), bf=(-5, 0),
          fx=[(40, 36, 2), (36, 40, 0)]),
        D(crouch=1, lean=2, fh=(4, 4), bh=(1, 5), w=-40, w2=140, ff=(7, 0), bf=(-6, 0)),
    ]
    guard = [D(lean=0, crouch=2 + (i == 1), fh=(5, 2), bh=(6, 3), w=-58, w2=-125, eyes='fierce', ff=(8, 0),
               bf=(-6, 0)) for i in range(3)]
    return dict(idle=idle, attack=attack, hit=std_hit(base, -20), victory=victory, ko=ko, burst=burst, guard=guard)


# ================================================================ tome (Aldric)
def tome():
    idle = [D(oy=b, fh=(4, 3 + b), bh=(-1, 6 + b), w=0) for b in (0, 0, 1, 1)]
    base = idle[0]
    attack = [
        D(fh=(4, 2), bh=(-1, 6), w=0, eyes='closed', fx=[('glyph', 36, 18)]),
        D(lean=0, fh=(4, 1), bh=(1, -2), w=0, eyes='fierce', fx=[('glyph', 34, 16), ring(3, 2, 4, 0.0)]),
        D(lean=2, fh=(4, 2), bh=(6, 0), w=0, eyes='fierce', glow=True, fx=[ring(3, 3, 5, 0.9)]),
        D(lean=3, fh=(4, 2), bh=(9, 1), w=0, eyes='fierce', fx=[('bolt', 44, 24, 'orb'), (39, 21, 1)]),
        D(lean=2, fh=(4, 2), bh=(6, 3), w=0),
        D(lean=1, fh=(4, 3), bh=(1, 5), w=0),
        D(fh=(4, 3), bh=(-1, 6), w=0),
    ]
    victory = [D(oy=u, fh=(4, 1 + u), bh=(0, -4 + u), w=0, eyes='closed' if i in (1, 2) else 'open',
                 fx=[('glyph', 18 + i * 2, 8 + i), ('glyph', 34 - i, 6 + (i % 2) * 2)])
               for i, u in enumerate((0, -1, -1, 0))]
    ko = std_ko(D(lean=2, crouch=4, fh=(4, 6), bh=(1, 6), w=0, open=0.0, eyes='hurt', ff=(6, 0), bf=(-6, 0)),
                D(fh=(2, 6), bh=(-1, 6), w=0, noweapon=True))
    burst = [
        D(fh=(4, 2), bh=(-1, 6), w=0, eyes='closed', glow=True),
        D(fh=(3, -2), tome_up=1, bh=(-3, 1), w=0, eyes='closed', glow=True, fx=[('glyph', 20, 14), ('glyph', 38, 12)]),
        D(oy=-1, fh=(3, -4), tome_up=2, bh=(-4, -1), w=0, eyes='fierce', glow=True,
          fx=[bring(24, 42, 12, 2, 6, 0.0)]),
        D(oy=-2, fh=(3, -5), tome_up=2, bh=(-4, -2), w=0, eyes='fierce', glow=True,
          fx=[bring(24, 42, 15, 3, 8, 0.4), ('glyph', 12, 34), ('glyph', 36, 32)]),
        D(oy=-2, fh=(3, -5), tome_up=2, bh=(-4, -2), w=0, eyes='fierce', glow=True,
          fx=[bring(24, 42, 18, 3, 10, 0.8), ('glyph', 10, 26), ('glyph', 38, 24), ('glyph', 24, 6)]),
        D(oy=-2, fh=(3, -5), tome_up=3, bh=(-5, -3), w=0, eyes='fierce', glow=True,
          fx=[bring(24, 42, 20, 3, 12, 1.2), ring(5, 4, 6, 0.0)]),
        D(oy=-2, fh=(3, -5), tome_up=3, bh=(-5, -3), w=0, eyes='fierce', glow=True,
          fx=[('star', 'focus', 0, 3), bring(24, 30, 19, 12, 12, 0.3)]),
        D(oy=-1, fh=(3, -3), tome_up=1, bh=(-3, 0), w=0, glow=True,
          fx=[('glyph', 8, 20), ('glyph', 40, 18), ('glyph', 16, 10), ('glyph', 32, 8)]),
        D(fh=(4, 1), bh=(-2, 4), w=0, fx=[('glyph', 12, 8), ('glyph', 36, 5)]),
        D(fh=(4, 2), bh=(-1, 6), w=0),
        D(fh=(4, 3), bh=(-1, 6), w=0),
    ]
    guard = [D(lean=-1, crouch=1 + (i == 1), fh=(5, 1), bh=(4, 2), w=0, eyes='fierce',
               fx=[('glyph', 39, 16 + i * 2), ('glyph', 40, 26 - i), ('glyph', 38, 34 + i)]) for i in range(3)]
    return dict(idle=idle, attack=attack, hit=std_hit(base, 0), victory=victory, ko=ko, burst=burst, guard=guard)


# ================================================================ bow (Wren)
def bow():
    idle = [D(oy=b, fh=(4, 5 + b), bh=(-1, 6 + b), w=-12 + b, nock=False) for b in (0, 0, 1, 1)]
    base = idle[0]
    attack = [
        D(fh=(6, 1), bh=(3, 2), w=-4, draw=0, eyes='open', ff=(7, 0), bf=(-6, 0)),
        D(lean=0, fh=(7, 0), bh='nock', w=-3, draw=3, eyes='fierce', ff=(7, 0), bf=(-6, 0)),
        D(lean=-1, fh=(7, 0), bh='nock', w=-3, draw=6, eyes='fierce', ff=(7, 0), bf=(-6, 0)),
        D(lean=-1, fh=(7, 0), bh='nock', w=-3, draw=7, eyes='fierce', ff=(7, 0), bf=(-6, 0),
          fx=[('star', 'focus_tip', 0, 1)]),
        D(lean=0, fh=(7, 0), bh=(-3, -2), w=-3, draw=0, nock=False, eyes='fierce', ff=(7, 0), bf=(-6, 0),
          fx=[('arrow', 47, 24, -3, 6), ('streak', 36, 25, 40, 25, 0)]),
        D(lean=1, fh=(6, 2), bh=(-2, 3), w=-6, nock=False, ff=(7, 0), bf=(-6, 0)),
        D(fh=(4, 5), bh=(-1, 6), w=-12, nock=False),
    ]
    victory = [D(oy=u, fh=(3, -6 + u), bh=(-1, 5 + u), w=-80, nock=False, eyes='closed' if i in (1, 2) else 'open',
                 fx=[(30 + i, 6 + i % 2, i), (36 - i, 10, i + 1)])
               for i, u in enumerate((0, -1, -1, 0))]
    ko = std_ko(D(lean=2, crouch=4, fh=(4, 7), bh=(0, 6), w=40, nock=False, eyes='hurt', ff=(6, 0), bf=(-6, 0)),
                D(fh=(2, 6), bh=(-1, 6), w=-12, nock=False, noweapon=True))
    V = D(glow=True, eyes='fierce', arrows=3, ff=(7, 0), bf=(-7, 0), bh='nock')
    burst = [
        D(crouch=1, fh=(4, 4), bh=(-1, 6), w=-12, nock=False, eyes='closed', glow=True,
          fx=[bring(24, 30, 12, 8, 5, 0.0)]),
        D(fh=(6, -1), bh=(3, 1), w=-30, arrows=3, draw=0, eyes='fierce', glow=True, ff=(7, 0), bf=(-7, 0),
          fx=[bring(24, 30, 14, 9, 6, 0.6)]),
        with_(V, lean=-1, fh=(6, -2), w=-32, draw=4, fx=[bring(24, 30, 15, 10, 7, 1.2)]),
        with_(V, lean=-2, fh=(6, -3), w=-35, draw=7, fx=[bring(24, 30, 16, 10, 8, 1.8)]),
        with_(V, lean=-2, fh=(6, -3), w=-36, draw=7, fx=[bring(24, 30, 17, 11, 8, 2.4), ('star', 'focus_tip', 0, 1)]),
        with_(V, lean=-2, fh=(6, -3), w=-38, draw=8, fx=[bring(24, 30, 18, 11, 9, 3.0), ('star', 'focus_tip', 0, 2)]),
        with_(V, lean=-2, crouch=1, fh=(6, -3), w=-38, draw=8, fx=[('star', 'focus_tip', 0, 3)]),
        D(lean=0, crouch=1, fh=(6, -3), bh=(-3, -3), w=-38, draw=0, nock=False, eyes='fierce', glow=True, ff=(7, 0),
          bf=(-7, 0), fx=[('arrow', 44, 6, -38, 5), ('arrow', 46, 12, -32, 5), ('arrow', 40, 4, -44, 5),
                          ('streak', 34, 20, 38, 16, 0)]),
        D(lean=1, fh=(5, 0), bh=(-2, 1), w=-30, nock=False, eyes='fierce', ff=(7, 0), bf=(-7, 0),
          fx=[(44, 4, 0), (46, 8, 1), (41, 3, 2)]),
        D(fh=(5, 3), bh=(-1, 4), w=-15, nock=False),
        D(fh=(4, 5), bh=(-1, 6), w=-12, nock=False),
    ]
    guard = [D(lean=-1, crouch=2 + (i == 1), fh=(5, 1), bh=(2, 3), w=-50 + i, nock=False, eyes='fierce', ff=(7, 0),
               bf=(-7, 0)) for i in range(3)]
    return dict(idle=idle, attack=attack, hit=std_hit(base, -6), victory=victory, ko=ko, burst=burst, guard=guard)


# ================================================================ great club (Gorran)
def club():
    idle = [D(oy=b, fh=(3, 4 + b), bh=(-1, 5 + b), w=72 - b * 2, ff=(5, 0), bf=(-5, 0)) for b in (0, 0, 1, 1)]
    base = idle[0]
    attack = [
        D(lean=0, crouch=1, fh=(2, 2), bh=(0, 3), w=20, eyes='fierce', ff=(5, 0), bf=(-5, 0)),
        D(lean=-2, fh=(-1, -4), bh=(0, -3), w=-118, eyes='fierce', club_front=False, ff=(5, 0), bf=(-5, 0)),
        D(lean=-2, oy=-1, fh=(-1, -5), bh=(0, -4), w=-150, eyes='fierce', club_front=False, ff=(5, 0), bf=(-5, 0),
          fx=[(10, 10, 0), (14, 6, 1)]),
        D(lean=4, crouch=3, fh=(4, 4), bh=(3, 3), w=62, eyes='fierce', ff=(7, 0), bf=(-5, 0),
          fx=[('crack', 40, 43, 5), ('star', 42, 40, 2), (46, 38, 0), (36, 39, 1)]),
        D(lean=4, crouch=3, fh=(4, 4), bh=(3, 3), w=64, eyes='fierce', ff=(7, 0), bf=(-5, 0),
          fx=[('crack', 40, 43, 8), ('column', 33, 37, 42), ('column', 46, 35, 42), (30, 34, 0), (44, 30, 2)]),
        D(lean=2, crouch=1, fh=(3, 3), bh=(0, 4), w=40, ff=(6, 0), bf=(-5, 0)),
        D(lean=1, fh=(3, 4), bh=(-1, 5), w=70, ff=(5, 0), bf=(-5, 0)),
    ]
    victory = [D(oy=u, fh=(1, -6 + u), bh=(-1, -5 + u), w=-95, club_front=False,
                 eyes='closed' if i in (1, 2) else 'fierce', ff=(5, 0), bf=(-5, 0),
                 fx=[(14 + i * 2, 8 + i, i), (36 - i, 10, i + 1)])
               for i, u in enumerate((0, -1, -1, 0))]
    ko = std_ko(D(lean=2, crouch=4, fh=(4, 6), bh=(0, 5), w=80, eyes='hurt', ff=(5, 0), bf=(-5, 0)),
                D(fh=(2, 6), bh=(-1, 6), w=70, noweapon=True))
    burst = [
        D(fh=(3, 4), bh=(-1, 3), w=72, eyes='fierce', glow=True, head_dy=-1, ff=(5, 0), bf=(-5, 0),
          fx=[(12, 12, 0), (36, 10, 1), (24, 4, 2)]),
        D(crouch=4, lean=0, fh=(2, 2), bh=(0, 3), w=30, eyes='fierce', glow=True, ff=(5, 0), bf=(-5, 0)),
        D(oy=-5, lean=-1, fh=(0, -4), bh=(1, -4), w=-100, eyes='fierce', glow=True, club_front=False, ff=(4, -2),
          bf=(-4, -1), fx=[(18, 44, 0), (30, 44, 1)]),
        D(oy=-7, lean=-2, fh=(-1, -5), bh=(0, -5), w=-140, eyes='fierce', glow=True, club_front=False, ff=(3, -3),
          bf=(-4, -2)),
        D(oy=-3, lean=3, fh=(4, -1), bh=(3, 0), w=-30, eyes='fierce', glow=True, ff=(5, -1), bf=(-4, -1),
          fx=[('streak', 38, 8, 44, 16, 0)]),
        D(crouch=4, lean=4, fh=(4, 4), bh=(3, 3), w=62, eyes='fierce', glow=True, ff=(7, 0), bf=(-5, 0),
          fx=[('crack', 38, 43, 8), ('star', 42, 40, 3)]),
        D(crouch=4, lean=4, fh=(4, 4), bh=(3, 3), w=63, eyes='fierce', glow=True, ff=(7, 0), bf=(-5, 0),
          fx=[('crack', 36, 43, 11), ('column', 10, 34, 42), ('column', 46, 32, 42), ('column', 30, 36, 42)]),
        D(crouch=3, lean=4, fh=(4, 4), bh=(3, 3), w=63, eyes='fierce', glow=True, ff=(7, 0), bf=(-5, 0),
          fx=[('column', 6, 28, 42), ('column', 44, 26, 42), ('column', 18, 32, 42), (26, 22, 0), (40, 20, 2)]),
        D(crouch=2, lean=3, fh=(4, 4), bh=(2, 4), w=60, ff=(7, 0), bf=(-5, 0), fx=[(8, 38, 1), (46, 36, 0)]),
        D(crouch=1, lean=2, fh=(3, 3), bh=(0, 4), w=45, ff=(6, 0), bf=(-5, 0)),
        D(lean=1, fh=(3, 4), bh=(-1, 5), w=70, ff=(5, 0), bf=(-5, 0)),
    ]
    guard = [D(lean=0, crouch=2 + (i == 1), fh=(4, 3), bh=(4, 1), w=-96 + i, eyes='fierce', ff=(6, 0), bf=(-6, 0))
             for i in range(3)]
    return dict(idle=idle, attack=attack, hit=std_hit(base, -6), victory=victory, ko=ko, burst=burst, guard=guard)


# ================================================================ registry
MOVES = {
    'lantern': dict(fn=lantern, fps=dict(FPS, attack=12, burst=11),
                    attack=dict(motion='ranged', release_frame=3), burst=dict(motion='self', release_frame=5)),
    'blossom': dict(fn=blossom, fps=dict(FPS, attack=12, burst=10),
                    attack=dict(motion='ranged', release_frame=3), burst=dict(motion='self', release_frame=5)),
    'greataxe': dict(fn=greataxe, fps=dict(FPS, attack=12, burst=11),
                     attack=dict(motion='melee', hit_frames=[3, 5]), burst=dict(motion='melee', hit_frames=[4, 5, 6, 6])),
    'spear': dict(fn=spear, fps=dict(FPS, attack=14, burst=13),
                  attack=dict(motion='melee', hit_frames=[2, 4, 6]),
                  burst=dict(motion='melee', hit_frames=[2, 3, 4, 5, 6, 8, 9])),
    'trident': dict(fn=trident, fps=dict(FPS, attack=12, burst=10),
                    attack=dict(motion='melee', hit_frames=[2, 4]), burst=dict(motion='self', release_frame=5)),
    'daggers': dict(fn=daggers, fps=dict(FPS, attack=15, burst=14),
                    attack=dict(motion='melee', hit_frames=[2, 3, 4, 5]),
                    burst=dict(motion='melee', hit_frames=[2, 3, 4, 5, 6, 7, 9])),
    'tome': dict(fn=tome, fps=dict(FPS, attack=11, burst=10),
                 attack=dict(motion='ranged', release_frame=3), burst=dict(motion='self', release_frame=6)),
    'bow': dict(fn=bow, fps=dict(FPS, attack=12, burst=11),
                attack=dict(motion='ranged', release_frame=4), burst=dict(motion='ranged', release_frame=7)),
    'club': dict(fn=club, fps=dict(FPS, attack=11, burst=11),
                 attack=dict(motion='melee', hit_frames=[3, 4]), burst=dict(motion='melee', hit_frames=[5, 6, 7, 7])),
}
