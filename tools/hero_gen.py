"""
hero_gen - parametric humanoid generator for Cinderbound's gacha heroes.

A hero *form* is described by a Spec (palettes, hair style, headgear, body
build, cape, weapon and tier features). A choreography (one per weapon
archetype, see hero_moves.py) turns a Spec into the seven battle animations.
All designs are original to Cinderbound.

Conventions shared with rig.py: 48x48 frames, heroes face RIGHT, feet rest on
row GROUND (43), light comes from the top-left.
"""
import math
from dataclasses import dataclass, field
from pixlib import Canvas, Pal, hexc, mix, lighten, darken
from rig import ik, draw_head, lying, W, H, GROUND


# ------------------------------------------------------------------ geometry
def uv(a):
    r = math.radians(a)
    return math.cos(r), math.sin(r)


def along(p, a, d):
    ux, uy = uv(a)
    return (p[0] + ux * d, p[1] + uy * d)


def side(p, a, d):
    """Offset perpendicular to direction a (positive = clockwise side)."""
    ux, uy = uv(a)
    return (p[0] - uy * d, p[1] + ux * d)


def clamp_len(p, a, want, lo=1, hi=46):
    """Longest length <= want that keeps p + dir(a)*len inside the frame."""
    ux, uy = uv(a)
    best = want
    for (u, c) in ((ux, p[0]), (uy, p[1])):
        if u > 1e-6:
            best = min(best, (hi - c) / u)
        elif u < -1e-6:
            best = min(best, (lo - c) / u)
    return max(best, 3)


def rgba(c):
    return c if len(c) == 4 else tuple(c) + (255,)


# ------------------------------------------------------------------ builds
BUILDS = {
    'young':  dict(hip_y=35, torso=7, head=5, sh_w=2, leg=5.0, leg_w=3, arm=3.9, arm_w=2, body=3, stance=0.9, boot=3),
    'light':  dict(hip_y=34, torso=8, head=5, sh_w=2, leg=5.5, leg_w=3, arm=4.2, arm_w=3, body=3, stance=1.0, boot=3),
    'lithe':  dict(hip_y=33, torso=8, head=5, sh_w=2, leg=6.0, leg_w=3, arm=4.4, arm_w=2, body=3, stance=1.1, boot=3),
    'robe':   dict(hip_y=34, torso=8, head=5, sh_w=2, leg=5.5, leg_w=3, arm=4.2, arm_w=3, body=3, stance=0.8, boot=3),
    'sturdy': dict(hip_y=34, torso=8, head=5, sh_w=3, leg=5.5, leg_w=4, arm=4.4, arm_w=3, body=4, stance=1.1, boot=4),
    'heavy':  dict(hip_y=32, torso=10, head=5, sh_w=3, leg=6.2, leg_w=4, arm=4.9, arm_w=4, body=5, stance=1.2, boot=4),
    'giant':  dict(hip_y=30, torso=11, head=3, sh_w=5, leg=7.2, leg_w=5, arm=6.4, arm_w=5, body=7, stance=1.35, boot=5,
                   head_dx=2),
}


@dataclass
class Spec:
    form_id: str
    name: str
    family: str
    tier: int
    moves: str                         # choreography archetype (hero_moves.MOVES key)
    build: str = 'light'
    skin: Pal = None
    eye: tuple = (40, 26, 30, 255)
    hair: Pal = None
    hair_style: str = 'short'
    beard: str = ''
    beard_pal: Pal = None
    head: list = field(default_factory=list)       # headgear feature names (drawn over the hair)
    tunic: Pal = None
    chest: Pal = None
    chest_style: str = ''                          # plate | vest | bib | ''
    trim: Pal = None
    legs: Pal = None
    boots: Pal = None
    sleeve: Pal = None
    sleeve_b: Pal = None
    glove: Pal = None
    skirt: str = 'tabard'                          # tabard | kilt | coat | robe | dress | loin | ''
    skirt_pal: Pal = None
    belt: Pal = None
    pauldron: Pal = None
    pauldron_b: Pal = None
    neck: str = ''                                 # scarf | mantle | collar | ''
    neck_pal: Pal = None
    cape: str = ''                                 # short | long | leaf | ribbon | wave | tail
    cape_pal: Pal = None
    cape_trim: Pal = None
    back: list = field(default_factory=list)       # back-layer features: halo, wings, quiver ...
    items: list = field(default_factory=list)      # front accessory features: satchel, plates ...
    weapon: dict = field(default_factory=dict)     # {'kind': ..., palettes + params}
    aura: str = ''                                 # spark | drop | leaf | petal | frost | glyph
    aura_glow: int = 0                             # alpha of a faint silhouette aura (0 = none)
    glow_col: tuple = (255, 160, 60)
    fx: list = field(default_factory=list)         # 3 particle colours
    pal: dict = field(default_factory=dict)        # extra named palettes for features


# ------------------------------------------------------------------ pose
class GP:
    """Generic pose. Hands are offsets from the shoulder joints (scaled by the
    build's arm length); feet are x offsets from the hip line plus a lift."""

    def __init__(self, **kw):
        self.ox = 0
        self.oy = 0
        self.crouch = 0
        self.lean = 1
        self.ff = (6, 0)
        self.bf = (-5, 0)
        self.fh = (3, 6)
        self.bh = (-1, 7)
        self.head_dx = 0
        self.head_dy = 0
        self.eyes = 'open'
        self.w = -35
        self.w2 = None
        self.glow = False
        self.fx = []
        self.t = 0
        self.anim = ''
        self.x = {}
        for k, v in kw.items():
            if hasattr(self, k):
                setattr(self, k, v)
            else:
                self.x[k] = v


def skel(spec, p):
    b = BUILDS[spec.build]
    k = b['arm'] / 4.2
    hip = (24 + p.ox, b['hip_y'] + p.oy + p.crouch)
    sh = (hip[0] + p.lean, hip[1] - b['torso'])
    head = (sh[0] + 1 + b.get('head_dx', 0) + p.head_dx, sh[1] - b['head'] + p.head_dy)
    f_sh = (sh[0] + b['sh_w'], sh[1] + 1)
    b_sh = (sh[0] - b['sh_w'], sh[1] + 1)
    f_hand = (f_sh[0] + p.fh[0] * k, f_sh[1] + p.fh[1] * k)
    if isinstance(p.bh, tuple) and len(p.bh) == 2 and isinstance(p.bh[0], str):
        # ('grip', d): back hand on the weapon shaft d px behind the front hand
        b_hand = along(f_hand, p.w, -p.bh[1])
    elif p.bh == 'nock':
        b_hand = along(f_hand, p.w, -(spec.weapon.get('bend', 2.5) + p.x.get('draw', 0)))
    else:
        b_hand = (b_sh[0] + p.bh[0] * k, b_sh[1] + p.bh[1] * k)
    st = b['stance']
    lift = min(p.oy, 0)
    f_foot = (round(24 + p.ox + p.ff[0] * st), GROUND + p.ff[1] + lift)
    b_foot = (round(24 + p.ox + p.bf[0] * st), GROUND + p.bf[1] + lift)
    return dict(hip=hip, sh=sh, head=head, f_sh=f_sh, b_sh=b_sh, f_hand=f_hand, b_hand=b_hand,
                f_foot=f_foot, b_foot=b_foot, b=b, focus=None)


# ------------------------------------------------------------------ limbs
def arm(cv, sh, hand, sleeve, skin, bend=1, l=4.2, w=3, glove=None, cuff=None):
    elbow = ik(sh, hand, l, l, bend=bend)
    m = cv.mask().line(sh[0], sh[1], elbow[0], elbow[1], w)
    m.line(elbow[0], elbow[1], hand[0], hand[1], max(w - 1, 2))
    cv.part(m, sleeve)
    if cuff is not None:
        cm = cv.mask().line(elbow[0] * 0.3 + hand[0] * 0.7, elbow[1] * 0.3 + hand[1] * 0.7,
                            elbow[0] * 0.15 + hand[0] * 0.85, elbow[1] * 0.15 + hand[1] * 0.85, max(w, 2) + 1)
        cv.part(cm, cuff)
    n = 1 if w < 4 else 2
    hm = cv.mask().rect(hand[0] - 1, hand[1] - 1, hand[0] + n - 1, hand[1] + n - 1)
    cv.part(hm, glove or skin)
    return elbow


def leg(cv, hip, foot, trouser, boot, l=5.5, w=3, boot_len=3, greave=None):
    knee = ik(hip, (foot[0], foot[1] - 1), l, l, bend=-1)
    m = cv.mask().line(hip[0], hip[1], knee[0], knee[1], w).line(knee[0], knee[1], foot[0], foot[1] - 2, w)
    cv.part(m, trouser)
    bh = 2 if w < 4 else 3
    b = cv.mask().rect(foot[0] - 1, foot[1] - bh, foot[0] + boot_len - 1, foot[1])
    b.line(knee[0] * 0.3 + foot[0] * 0.7, knee[1] * 0.3 + foot[1] * 0.7, foot[0], foot[1] - 1, w)
    cv.part(b, boot)
    if greave is not None:
        g = cv.mask().line(knee[0], knee[1], knee[0] * 0.4 + foot[0] * 0.6, knee[1] * 0.4 + foot[1] * 0.6, w)
        g.ellipse(knee[0] + 0.5, knee[1], w / 2.0, 1.3)
        cv.part(g, greave)
    return knee


# ------------------------------------------------------------------ registries
HAIR = {}        # name -> (front_fn(cv, cx, cy, spec), back_fn(cv, spec, s, p) or None)
HEADGEAR = {}    # name -> fn(cv, cx, cy, spec, layer)   layer: 'back' | 'front'
BEARDS = {}      # name -> fn(cv, cx, cy, spec)
CAPES = {}       # name -> fn(cv, spec, s, p)
BACKFX = {}      # name -> fn(cv, spec, s, p)
ITEMS = {}       # name -> fn(cv, spec, s, p, layer)  layer: 'torso' | 'belt' | 'shoulder'
WEAPONS = {}     # kind -> fn(cv, spec, s, p, layer) layer: back | back_hand | mid | pre | post


def reg(table, name):
    def deco(fn):
        table[name] = fn
        return fn
    return deco


# ------------------------------------------------------------------ hair
def _hair_front(name):
    def deco(fn):
        HAIR.setdefault(name, [None, None])[0] = fn
        return fn
    return deco


def _hair_back(name):
    def deco(fn):
        HAIR.setdefault(name, [None, None])[1] = fn
        return fn
    return deco


@_hair_front('curly')
def _(cv, cx, cy, sp):
    m = cv.mask().ellipse(cx - 0.5, cy - 2.5, 4.6, 2.6)
    for (dx, dy, r) in ((-4, -3, 1.9), (-2, -5, 1.8), (1, -5.4, 1.7), (3.5, -4, 1.5), (-5, 0, 1.8),
                        (-4, 2, 1.6), (4.6, -2.2, 1.2)):
        m.ellipse(cx + dx, cy + dy, r, r)
    m.rect(cx - 5, cy - 2, cx - 2, cy + 2)
    cv.part(m, sp.hair)
    # curl highlights
    for (dx, dy) in ((-3, -5), (0, -6), (-5, -2)):
        cv.dot(cx + dx, cy + dy, sp.hair.hi)


@_hair_front('bald')
def _(cv, cx, cy, sp):
    # scalp sheen + a fringe of hair at the back of the head
    m = cv.mask().rect(cx - 4, cy - 1, cx - 3, cy + 1)
    cv.part(m, sp.hair, shade=False)
    cv.dot(cx - 1, cy - 3, sp.skin.hi)
    cv.dot(cx, cy - 3, sp.skin.hi)


@_hair_front('ponytail')
def _(cv, cx, cy, sp):
    m = cv.mask().ellipse(cx - 0.5, cy - 2.6, 4.7, 2.5)
    m.poly([(cx + 1, cy - 5), (cx + 5, cy - 3), (cx + 4, cy), (cx + 2, cy - 2)])     # swept bangs
    m.rect(cx - 5, cy - 2, cx - 2, cy + 1)
    cv.part(m, sp.hair)


@_hair_back('ponytail')
def _(cv, sp, s, p):
    cx, cy = s['head']
    sway = math.sin(p.t * 1.3 + (0.8 if p.anim == 'attack' else 0)) * 1.2 + p.x.get('hair_fly', 0)
    base = (cx - 2, cy - 5)
    m = cv.mask().ellipse(base[0], base[1], 2.2, 1.8)                     # high tie
    pts = [(cx - 3, cy - 6), (cx - 8, cy - 5 + sway * 0.3), (cx - 11, cy - 1 + sway),
           (cx - 12, cy + 4 + sway * 1.3), (cx - 10, cy + 5 + sway), (cx - 9, cy + 1 + sway * 0.6),
           (cx - 5, cy - 2), (cx - 2, cy - 4)]
    m.poly(pts)
    cv.part(m, sp.hair)
    tie = cv.mask().rect(cx - 3, cy - 6, cx - 2, cy - 4)
    cv.part(tie, sp.pal.get('tie', sp.trim or sp.hair), shade=False)


@_hair_front('sleek')
def _(cv, cx, cy, sp):
    # short swept silver hair with a long fringe over the brow
    m = cv.mask().ellipse(cx - 0.5, cy - 2.6, 4.7, 2.6)
    m.poly([(cx - 5, cy - 3), (cx - 8, cy - 1), (cx - 5, cy + 1)])
    m.poly([(cx, cy - 5), (cx + 6, cy - 3), (cx + 4, cy - 1), (cx + 3, cy)])
    m.rect(cx - 5, cy - 2, cx - 2, cy + 2)
    cv.part(m, sp.hair)


@_hair_front('capped')
def _(cv, cx, cy, sp):
    # tufts peeking out beneath a cap
    m = cv.mask().rect(cx - 5, cy - 2, cx - 2, cy + 2)
    m.poly([(cx - 5, cy + 1), (cx - 7, cy + 3), (cx - 4, cy + 3)])
    m.poly([(cx + 2, cy - 2), (cx + 5, cy - 1), (cx + 3, cy + 1)])
    cv.part(m, sp.hair)


@_hair_front('wavy')
def _(cv, cx, cy, sp):
    m = cv.mask().ellipse(cx - 0.5, cy - 2.6, 4.8, 2.7)
    m.poly([(cx + 1, cy - 5), (cx + 5, cy - 3), (cx + 5, cy + 1), (cx + 3, cy - 1)])
    m.rect(cx - 5, cy - 3, cx - 2, cy + 3)
    cv.part(m, sp.hair)


@_hair_back('wavy')
def _(cv, sp, s, p):
    cx, cy = s['head']
    fl = math.sin(p.t * 1.1) * 0.8 + p.x.get('hair_fly', 0)
    pts = [(cx - 2, cy - 4), (cx - 6, cy - 2), (cx - 7 - fl * 0.5, cy + 3), (cx - 6 - fl, cy + 7),
           (cx - 8 - fl, cy + 10), (cx - 6 - fl, cy + 13), (cx - 3 - fl * 0.5, cy + 12),
           (cx - 2, cy + 8), (cx - 1, cy + 3)]
    m = cv.mask().poly(pts)
    cv.part(m, sp.hair)
    for k in range(3):
        cv.dot(cx - 5 - fl * 0.6 + (k % 2), cy + 3 + k * 3, sp.hair.sh)


@_hair_front('none')
def _(cv, cx, cy, sp):
    pass


@_hair_front('mossy')
def _(cv, cx, cy, sp):
    # giant-kin: mossy brow ridge + twig tufts on a bark head
    m = cv.mask().ellipse(cx - 0.8, cy - 3, 4.9, 2.1)
    for (dx, dy, r) in ((-3.5, -4.3, 1.6), (-0.5, -4.9, 1.8), (2.4, -4.2, 1.4), (-5, -1.5, 1.4)):
        m.ellipse(cx + dx, cy + dy, r, r)
    cv.part(m, sp.hair)
    for (dx, dy) in ((-3, -5), (0, -6), (3, -5), (-5, -2)):
        cv.dot(cx + dx, cy + dy, sp.hair.hi)
    # heavy bark brow
    cv.part(cv.mask().line(cx, cy - 1, cx + 4, cy - 1, 1), Pal(sp.skin.line, sp.skin.line, sp.skin.line),
            shade=False, separate=False)
    cv.dot(cx - 2, cy + 1, sp.skin.sh)
    cv.dot(cx - 1, cy + 2, sp.skin.sh)


@_hair_front('hooded')
def _(cv, cx, cy, sp):
    m = cv.mask().rect(cx - 5, cy - 1, cx - 2, cy + 3)
    cv.part(m, sp.hair)


# ------------------------------------------------------------------ headgear
@reg(HEADGEAR, 'goggles')
def _(cv, cx, cy, sp, layer):
    if layer != 'front':
        return
    band = cv.mask().line(cx - 5, cy - 2, cx + 3, cy - 3, 1)
    cv.part(band, sp.pal['strap'], shade=False, separate=False)
    lens = cv.mask().ellipse(cx + 1.5, cy - 3.6, 1.6, 1.3)
    cv.part(lens, sp.pal['brass'], separate=False)
    cv.dot(cx + 1, cy - 4, sp.pal['lens'].hi)
    cv.dot(cx + 2, cy - 4, sp.pal['lens'].base)


@reg(HEADGEAR, 'horned_helm')
def _(cv, cx, cy, sp, layer):
    if layer == 'back':
        return
    helm = cv.mask().ellipse(cx - 0.3, cy - 2.4, 4.8, 3.0)
    helm.rect(cx - 5, cy - 2, cx - 3, cy + 2)
    helm.rect(cx + 2, cy - 2, cx + 3, cy + 1)   # cheek guard
    cv.part(helm, sp.pal['helm'])
    # nose guard + glowing seam
    cv.part(cv.mask().rect(cx + 3, cy - 2, cx + 3, cy + 1), sp.pal['helm'], shade=False)
    for x in range(-3, 3):
        cv.dot(cx + x, cy - 1, sp.pal['molten'].base if x % 2 else sp.pal['molten'].hi)
    horn = sp.pal['horn']
    h1 = cv.mask().poly([(cx - 3, cy - 4), (cx - 6, cy - 7), (cx - 8, cy - 11), (cx - 5, cy - 9), (cx - 2, cy - 6)])
    h2 = cv.mask().poly([(cx + 1, cy - 5), (cx + 3, cy - 9), (cx + 6, cy - 11), (cx + 5, cy - 8), (cx + 3, cy - 4)])
    cv.part(h1, horn)
    cv.part(h2, horn)


@reg(HEADGEAR, 'winged_circlet')
def _(cv, cx, cy, sp, layer):
    if layer != 'front':
        return
    band = cv.mask().line(cx - 4, cy - 3, cx + 4, cy - 4, 1)
    cv.part(band, sp.trim, shade=False, separate=False)
    cv.dot(cx + 3, cy - 4, sp.pal['gem'].hi)
    wing = cv.mask().poly([(cx - 3, cy - 3), (cx - 6, cy - 7), (cx - 9, cy - 8), (cx - 8, cy - 6),
                           (cx - 7, cy - 4), (cx - 5, cy - 2)])
    cv.part(wing, sp.pal['wing'])
    cv.dot(cx - 7, cy - 6, sp.pal['wing'].sh)
    cv.dot(cx - 6, cy - 4, sp.pal['wing'].sh)


@reg(HEADGEAR, 'bandana')
def _(cv, cx, cy, sp, layer):
    ph = sp.pal.get('_phase', 0)
    if layer == 'back':
        return
    m = cv.mask().ellipse(cx - 0.6, cy - 2.8, 4.8, 2.6)
    m.rect(cx - 5, cy - 3, cx + 3, cy - 2)
    cv.part(m, sp.pal['bandana'])
    # knot + tails at the back
    t = cv.mask().poly([(cx - 5, cy - 3), (cx - 9, cy - 2), (cx - 10, cy), (cx - 7, cy - 1), (cx - 5, cy - 1)])
    t.poly([(cx - 5, cy - 2), (cx - 8, cy + 1), (cx - 7, cy + 2), (cx - 4, cy - 1)])
    cv.part(t, sp.pal['bandana'])
    cv.dot(cx, cy - 4, sp.pal['bandana'].hi)
    cv.dot(cx - 2, cy - 3, (240, 240, 230, 255))
    cv.dot(cx + 2, cy - 3, (240, 240, 230, 255))


@reg(HEADGEAR, 'finned_helm')
def _(cv, cx, cy, sp, layer):
    if layer == 'back':
        return
    helm = cv.mask().ellipse(cx - 0.2, cy - 1, 5.0, 4.8)
    cv.part(helm, sp.pal['helm'])
    # visor slit
    for x in range(0, 5):
        cv.dot(cx + x, cy + 1, sp.pal['helm'].line)
    cv.dot(cx + 2, cy + 1, sp.pal['visor'])
    cv.dot(cx + 3, cy + 1, sp.pal['visor'])
    fin = cv.mask().poly([(cx - 3, cy - 5), (cx - 2, cy - 9), (cx + 1, cy - 8), (cx - 8, cy - 7),
                          (cx - 10, cy - 3), (cx - 5, cy - 3)])
    cv.part(fin, sp.pal['fin'])
    for (dx, dy) in ((-4, -7), (-6, -6), (-2, -8)):
        cv.dot(cx + dx, cy + dy, sp.pal['fin'].hi)
    gill = cv.mask().poly([(cx + 1, cy + 2), (cx + 3, cy + 5), (cx - 1, cy + 4)])
    cv.part(gill, sp.pal['fin'])


@reg(HEADGEAR, 'hood_down')
def _(cv, cx, cy, sp, layer):
    if layer == 'back':
        m = cv.mask().poly([(cx - 3, cy - 3), (cx - 8, cy - 1), (cx - 11, cy + 3), (cx - 7, cy + 5),
                            (cx - 3, cy + 5)])
        cv.part(m, sp.pal['hood'])
        return
    # scarf over the mouth
    sc = cv.mask().poly([(cx - 4, cy + 2), (cx + 4, cy + 2), (cx + 5, cy + 4), (cx + 3, cy + 5), (cx - 4, cy + 5)])
    cv.part(sc, sp.pal['scarf'])


@reg(HEADGEAR, 'ice_crown')
def _(cv, cx, cy, sp, layer):
    if layer != 'front':
        return
    ice = sp.pal['ice']
    m = cv.mask().line(cx - 4, cy - 3, cx + 3, cy - 4, 1)
    for (dx, h) in ((-3, 3), (-1, 5), (1, 4), (3, 2)):
        m.poly([(cx + dx - 1, cy - 3), (cx + dx, cy - 4 - h), (cx + dx + 1, cy - 3)])
    cv.part(m, ice)
    cv.dot(cx - 1, cy - 8, ice.hi)


@reg(HEADGEAR, 'cowl')
def _(cv, cx, cy, sp, layer):
    if layer == 'back':
        m = cv.mask().ellipse(cx - 1.2, cy - 1.2, 5.6, 5.4)
        m.poly([(cx - 5, cy - 2), (cx - 8, cy + 6), (cx - 2, cy + 6)])
        cv.part(m, sp.pal['cowl'])
        return
    rim = cv.mask().poly([(cx - 5, cy + 2), (cx - 5, cy - 4), (cx - 1, cy - 7), (cx + 3, cy - 6),
                          (cx + 5, cy - 4), (cx + 3, cy - 4), (cx + 1, cy - 4), (cx - 2, cy - 2), (cx - 3, cy + 3)])
    cv.part(rim, sp.pal['cowl'])
    band = cv.mask().line(cx - 1, cy - 6, cx + 4, cy - 4, 1)
    cv.part(band, sp.trim, shade=False, separate=False)
    cv.dot(cx + 1, cy - 5, sp.pal['gem'].hi)


@reg(HEADGEAR, 'feather_cap')
def _(cv, cx, cy, sp, layer):
    if layer != 'front':
        return
    cap = cv.mask().poly([(cx - 5, cy - 1), (cx - 4, cy - 5), (cx, cy - 6), (cx + 4, cy - 4), (cx + 6, cy - 2),
                          (cx + 3, cy - 2), (cx - 1, cy - 2), (cx - 8, cy - 1), (cx - 10, cy + 1)])
    cv.part(cap, sp.pal['cap'])
    band = cv.mask().line(cx - 5, cy - 2, cx + 3, cy - 2, 1)
    cv.part(band, sp.pal['cap'], shade=False)
    cv.part(cv.mask().rect(cx - 4, cy - 2, cx + 2, cy - 2), Pal(sp.pal['cap'].sh, sp.pal['cap'].sh,
                                                                sp.pal['cap'].line), shade=False, separate=False)
    f = sp.pal['feather']
    fm = cv.mask().poly([(cx - 3, cy - 4), (cx - 7, cy - 8), (cx - 11, cy - 9), (cx - 8, cy - 6), (cx - 4, cy - 3)])
    cv.part(fm, f)
    cv.dot(cx - 8, cy - 7, f.sh)


@reg(HEADGEAR, 'flower_crown')
def _(cv, cx, cy, sp, layer):
    if layer != 'front':
        return
    vine = cv.mask().line(cx - 5, cy - 2, cx + 4, cy - 4, 1)
    cv.part(vine, sp.pal['leafp'], shade=False, separate=False)
    for (dx, dy, c) in ((-4, -3, 'petal'), (-1, -4, 'petal2'), (2, -5, 'petal'), (4, -4, 'petal2')):
        pc = sp.pal[c]
        cv.dot(cx + dx, cy + dy, pc.base)
        cv.dot(cx + dx + 1, cy + dy, pc.hi)
        cv.dot(cx + dx, cy + dy - 1, pc.hi)
        cv.dot(cx + dx + 1, cy + dy - 1, sp.pal['pollen'])


@reg(HEADGEAR, 'bloom_crown')
def _(cv, cx, cy, sp, layer):
    """Tier-2 Faye: a taller crown of open blossoms."""
    if layer != 'front':
        return
    vine = cv.mask().line(cx - 5, cy - 2, cx + 4, cy - 4, 1)
    cv.part(vine, sp.pal['leafp'], shade=False, separate=False)
    for (dx, dy, c) in ((-4, -4, 'petal'), (0, -6, 'petal2'), (3, -5, 'petal')):
        pc = sp.pal[c]
        m = cv.mask().ellipse(cx + dx, cy + dy, 1.6, 1.6)
        cv.part(m, pc, separate=False)
        cv.dot(cx + dx, cy + dy, sp.pal['pollen'])
    for (dx, dy) in ((-6, -2), (5, -3)):
        cv.dot(cx + dx, cy + dy, sp.pal['leafp'].hi)


@reg(HEADGEAR, 'circlet')
def _(cv, cx, cy, sp, layer):
    if layer != 'front':
        return
    band = cv.mask().line(cx - 4, cy - 3, cx + 4, cy - 4, 1)
    cv.part(band, sp.trim, shade=False, separate=False)
    cv.dot(cx + 2, cy - 5, sp.pal['gem'].base)
    cv.dot(cx + 2, cy - 4, sp.pal['gem'].hi)


@reg(HEADGEAR, 'sun_circlet')
def _(cv, cx, cy, sp, layer):
    if layer != 'front':
        return
    band = cv.mask().line(cx - 4, cy - 3, cx + 4, cy - 4, 1)
    cv.part(band, sp.trim, shade=False, separate=False)
    for (dx, dy) in ((0, -6), (2, -6), (-2, -5), (4, -5)):
        cv.dot(cx + dx, cy + dy, sp.trim.hi)
    cv.dot(cx + 1, cy - 5, sp.pal['gem'].hi)


@reg(HEADGEAR, 'leaf_hood')
def _(cv, cx, cy, sp, layer):
    """Tier-3 Wren: a pointed hood of layered leaves (replaces the cap)."""
    L = sp.pal['cap']
    if layer == 'back':
        m = cv.mask().poly([(cx - 3, cy - 5), (cx - 9, cy - 4), (cx - 13, cy - 1), (cx - 9, cy),
                            (cx - 6, cy + 4), (cx - 3, cy + 3)])
        cv.part(m, L)
        return
    m = cv.mask().ellipse(cx - 0.8, cy - 2.5, 5.0, 3.0)
    m.poly([(cx + 1, cy - 5), (cx + 6, cy - 3), (cx + 3, cy - 1)])
    cv.part(m, L)
    for (dx, dy) in ((-3, -4), (0, -5), (-5, -2), (3, -3)):
        cv.dot(cx + dx, cy + dy, L.hi)
    cv.dot(cx - 1, cy - 3, L.sh)


# ------------------------------------------------------------------ beards
@reg(BEARDS, 'full')
def _(cv, cx, cy, sp):
    m = cv.mask().poly([(cx - 3, cy), (cx - 1, cy + 3), (cx + 3, cy + 3), (cx + 4, cy + 2),
                        (cx + 5, cy + 3), (cx + 3, cy + 7), (cx - 1, cy + 7), (cx - 3, cy + 4)])
    cv.part(m, sp.beard_pal)
    cv.dot(cx + 2, cy + 5, sp.beard_pal.hi)


@reg(BEARDS, 'stubble')
def _(cv, cx, cy, sp):
    c = mix(sp.skin.sh, sp.beard_pal.base, 0.55)
    for (dx, dy) in ((-2, 3), (0, 3), (1, 4), (3, 3), (-1, 4), (2, 4), (-3, 2)):
        cv.dot(cx + dx, cy + dy, c)


@reg(BEARDS, 'long')
def _(cv, cx, cy, sp):
    m = cv.mask().poly([(cx - 3, cy), (cx - 1, cy + 3), (cx + 3, cy + 3), (cx + 5, cy + 2),
                        (cx + 5, cy + 5), (cx + 3, cy + 10), (cx + 1, cy + 13), (cx - 1, cy + 10), (cx - 3, cy + 5)])
    cv.part(m, sp.beard_pal)
    m2 = cv.mask().poly([(cx + 2, cy + 1), (cx + 6, cy + 1), (cx + 5, cy + 2), (cx + 2, cy + 2)])
    cv.part(m2, sp.beard_pal, separate=False)     # moustache
    cv.dot(cx + 2, cy + 6, sp.beard_pal.sh)
    cv.dot(cx + 1, cy + 9, sp.beard_pal.sh)


@reg(BEARDS, 'moss')
def _(cv, cx, cy, sp):
    m = cv.mask().poly([(cx - 3, cy + 1), (cx + 1, cy + 3), (cx + 4, cy + 2), (cx + 6, cy + 4), (cx + 5, cy + 8),
                        (cx + 4, cy + 12), (cx + 2, cy + 10), (cx + 1, cy + 13), (cx - 1, cy + 10), (cx - 3, cy + 11),
                        (cx - 4, cy + 5)])
    cv.part(m, sp.beard_pal)
    for (dx, dy) in ((1, 6), (-1, 8), (3, 7), (4, 10), (0, 11)):
        cv.dot(cx + dx, cy + dy, sp.beard_pal.hi if dy % 2 else sp.beard_pal.sh)
    cv.dot(cx + 3, cy + 3, sp.skin.line)   # mouth in the moss


# ------------------------------------------------------------------ capes
def _cape_poly(s, p, length, spread, flow_amp=1.0):
    sx, sy = s['sh']
    hx, hy = s['hip']
    fl = math.sin(p.t * 1.4 + (1.0 if p.anim in ('attack', 'burst') else 0)) * flow_amp + p.x.get('cape_fly', 0)
    bottom = min(hy + length, GROUND - 1 + min(p.oy, 0) + (0 if p.oy >= 0 else 2))
    return [(sx - 2, sy - 1), (sx + 1, sy - 1), (hx - 1, bottom - 1),
            (hx - spread - fl, bottom), (hx - spread - 2 - fl, bottom - 2), (sx - 5 - fl * 0.4, sy + 3)], fl, bottom


@reg(CAPES, 'short')
def _(cv, sp, s, p):
    pts, fl, bottom = _cape_poly(s, p, 3, 5)
    cv.part(cv.mask().poly(pts), sp.cape_pal)
    if sp.cape_trim:
        cv.part(cv.mask().line(pts[3][0], pts[3][1], pts[4][0], pts[4][1], 1), sp.cape_trim, shade=False, separate=False)


@reg(CAPES, 'long')
def _(cv, sp, s, p):
    pts, fl, bottom = _cape_poly(s, p, 9, 7)
    cv.part(cv.mask().poly(pts), sp.cape_pal)
    if sp.cape_trim:
        t = cv.mask().line(pts[2][0], pts[2][1], pts[3][0], pts[3][1], 1)
        t.line(pts[3][0], pts[3][1], pts[4][0], pts[4][1], 1)
        cv.part(t, sp.cape_trim, shade=False, separate=False)


@reg(CAPES, 'wave')
def _(cv, sp, s, p):
    """Long cloak whose hem is trimmed with a scalloped wave pattern."""
    pts, fl, bottom = _cape_poly(s, p, 9, 8)
    cv.part(cv.mask().poly(pts), sp.cape_pal)
    x0, x1 = int(pts[3][0]) - 1, int(pts[2][0])
    for x in range(x0, x1 + 1):
        yy = bottom - 1 + (0 if (x + p.t) % 3 else -1)
        cv.dot(x, yy, sp.cape_trim.base)
        if (x + p.t) % 3 == 1:
            cv.dot(x, yy - 1, sp.cape_trim.hi)


@reg(CAPES, 'leaf')
def _(cv, sp, s, p):
    sx, sy = s['sh']
    hx, hy = s['hip']
    fl = math.sin(p.t * 1.5) * 1.0 + p.x.get('cape_fly', 0)
    pts = [(sx - 2, sy - 1), (sx + 1, sy - 1), (hx - 1, hy - 1), (hx - 3, hy + 1), (hx - 5 - fl, hy - 1),
           (hx - 7 - fl, hy + 1), (hx - 8 - fl, hy - 2), (sx - 6 - fl * 0.5, sy + 3)]
    cv.part(cv.mask().poly(pts), sp.cape_pal)
    for (x, y) in ((hx - 4 - fl, hy - 3), (sx - 4, sy + 3), (hx - 7 - fl, hy - 4)):
        cv.dot(x, y, sp.cape_pal.sh)


@reg(CAPES, 'gale')
def _(cv, sp, s, p):
    """Tier-3 Wren: a long wind-swept cloak of overlapping leaves."""
    sx, sy = s['sh']
    hx, hy = s['hip']
    fl = math.sin(p.t * 1.5) * 1.5 + p.x.get('cape_fly', 0)
    pts = [(sx - 2, sy - 1), (sx + 1, sy - 1), (hx - 1, hy + 2), (hx - 4 - fl, hy + 5), (hx - 6 - fl, hy + 3),
           (hx - 9 - fl, hy + 4), (hx - 10 - fl, hy + 1), (hx - 13 - fl, hy), (hx - 11 - fl, hy - 3),
           (sx - 7 - fl * 0.6, sy + 2)]
    cv.part(cv.mask().poly(pts), sp.cape_pal)
    for i, (x, y) in enumerate(((hx - 6 - fl, hy), (sx - 4, sy + 4), (hx - 10 - fl, hy - 1), (hx - 3, hy + 2))):
        cv.dot(x, y, sp.cape_pal.hi if i % 2 else sp.cape_pal.sh)
    if sp.cape_trim:
        for k in range(3):
            cv.dot(hx - 12 - fl + k * 2, hy - 2 + k, sp.cape_trim.hi)


@reg(CAPES, 'ribbon')
def _(cv, sp, s, p):
    """Tier-3 Mira-like flowing water ribbons (translucent-looking bands)."""
    sx, sy = s['sh']
    hx, hy = s['hip']
    for k, off in enumerate((0, 3)):
        ph = p.t * 1.2 + k * 1.7
        pts = []
        for i in range(9):
            t = i / 8.0
            x = sx - 2 - t * 13 - off * 0.5
            y = sy + t * (hy - sy + 6) + math.sin(ph + t * 5) * 1.6 + off
            pts.append((x, y))
        m = cv.mask()
        for i in range(8):
            m.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], 2 if i < 6 else 1)
        cv.part(m, sp.cape_pal if k == 0 else sp.cape_trim, separate=False)


@reg(CAPES, 'tail')
def _(cv, sp, s, p):
    """Coat tails flaring behind the hips."""
    hx, hy = s['hip']
    sx, sy = s['sh']
    fl = math.sin(p.t * 1.4) * 0.8 + p.x.get('cape_fly', 0)
    pts = [(sx - 3, sy + 4), (hx - 1, hy - 1), (hx, hy + 6), (hx - 4 - fl, hy + 7), (hx - 6 - fl, hy + 5),
           (hx - 4, hy)]
    cv.part(cv.mask().poly(pts), sp.cape_pal)
    if sp.cape_trim:
        t = cv.mask().line(hx, hy + 6, hx - 4 - fl, hy + 7, 1).line(hx - 4 - fl, hy + 7, hx - 6 - fl, hy + 5, 1)
        cv.part(t, sp.cape_trim, shade=False, separate=False)


@reg(CAPES, 'mantle')
def _(cv, sp, s, p):
    """Voss: heavy ragged soot mantle hanging down the back."""
    sx, sy = s['sh']
    hx, hy = s['hip']
    fl = math.sin(p.t * 1.2) * 0.7 + p.x.get('cape_fly', 0)
    bottom = hy + 5
    pts = [(sx - 3, sy - 2), (sx + 2, sy - 2), (hx - 2, hy), (hx - 3, bottom), (hx - 5 - fl, bottom - 2),
           (hx - 6 - fl, bottom + 1), (hx - 8 - fl, bottom - 2), (hx - 9 - fl, bottom), (sx - 8 - fl * 0.5, sy + 5)]
    cv.part(cv.mask().poly(pts), sp.cape_pal)
    for (x, y) in ((sx - 5, sy + 4), (hx - 6 - fl, hy + 1)):
        cv.dot(x, y, sp.cape_pal.sh)


@reg(CAPES, 'petal_wings')
def _(cv, sp, s, p):
    """Tier-2 Faye: two layered blossom wings behind the shoulders."""
    sx, sy = s['sh']
    fl = math.sin(p.t * 1.3) * 1.0 + p.x.get('cape_fly', 0)
    P1, P2 = sp.pal['petal'], sp.pal['petal2']
    up = cv.mask().poly([(sx - 1, sy + 1), (sx - 6, sy - 6 - fl), (sx - 11, sy - 8 - fl), (sx - 12, sy - 4 - fl * 0.5),
                         (sx - 9, sy), (sx - 4, sy + 3)])
    cv.part(up, P2)
    lo = cv.mask().poly([(sx - 1, sy + 3), (sx - 8, sy + 3), (sx - 12, sy + 6 + fl * 0.5), (sx - 9, sy + 9),
                         (sx - 3, sy + 7)])
    cv.part(lo, P1)
    for (x, y) in ((sx - 8, sy - 4 - fl), (sx - 7, sy + 5)):
        cv.dot(x, y, sp.pal['pollen'])


# ------------------------------------------------------------------ back-layer fx
@reg(BACKFX, 'sun_halo')
def _(cv, sp, s, p):
    cx, cy = s['head']
    cx -= 3
    cy -= 2
    S = sp.pal['sun']
    disc = cv.mask().ellipse(cx, cy, 6.2, 6.2)
    cv.part(disc, Pal(S.hi, S.hi, S.base, S.sh), separate=False)
    cv.part(cv.mask().ellipse(cx, cy, 4.6, 4.6), Pal(lighten(S.hi, 0.4), lighten(S.hi, 0.4), S.hi), shade=False,
            separate=False)
    for k in range(6):
        a = math.pi * (0.55 + k * 0.3) + (p.t % 2) * 0.12
        for d in (7.4, 8.4):
            cv.dot(cx + math.cos(a) * d, cy + math.sin(a) * d, S.base if d > 8 else S.hi)


@reg(BACKFX, 'quiver')
def _(cv, sp, s, p):
    sx, sy = s['sh']
    a = -120
    base = (sx - 2, sy + 7)
    top = along(base, a, 10)
    q = cv.mask().line(base[0], base[1], top[0], top[1], 3)
    cv.part(q, sp.pal['quiver'])
    for k, d in enumerate((-1, 0, 1)):
        f0 = along(top, a, 0.5)
        f = (f0[0] + d, f0[1] - 1 - (k % 2))
        cv.dot(f[0], f[1], sp.pal['fletch'].base if k != 1 else sp.pal['fletch'].hi)
        cv.dot(f[0], f[1] - 1, sp.pal['fletch'].hi)


@reg(BACKFX, 'glyph_ring_back')
def _(cv, sp, s, p):
    pass


# ------------------------------------------------------------------ torso & legs
def body(cv, sp, s, p):
    b = s['b']
    hx, hy = s['hip']
    sx, sy = s['sh']
    bw = b['body']
    torso = cv.mask().poly([(hx - bw, hy + 1), (hx + bw, hy + 1), (sx + bw + 1, sy + 1), (sx - bw, sy)])
    cv.part(torso, sp.tunic)
    st = sp.chest_style
    if sp.chest and st:
        if st == 'plate':
            pts = [(hx - bw + 1, hy - 2), (hx + bw, hy - 2), (sx + bw + 1, sy + 1), (sx - bw + 1, sy + 1)]
        elif st == 'vest':
            pts = [(hx - 1, hy - 2), (hx + bw, hy - 2), (sx + bw + 1, sy + 1), (sx, sy + 1)]
        elif st == 'bib':
            pts = [(hx, hy - 3), (hx + bw, hy - 3), (sx + bw + 1, sy + 2), (sx + 1, sy + 2)]
        else:  # 'breast' - broad breastplate for heavies
            pts = [(hx - bw + 1, hy - 1), (hx + bw + 1, hy - 1), (sx + bw + 2, sy + 1), (sx - bw + 1, sy)]
        cv.part(cv.mask().poly(pts), sp.chest)
        if sp.trim is not None and st in ('plate', 'breast'):
            t = cv.mask().line(pts[3][0], pts[3][1], pts[2][0], pts[2][1], 1)
            t.line(pts[2][0], pts[2][1], pts[1][0], pts[1][1], 1)
            cv.part(t, sp.trim, shade=False, separate=False)


def lower(cv, sp, s, p, front):
    """Legs (back leg when front=False). Robes hide the legs."""
    b = s['b']
    hx, hy = s['hip']
    if sp.skirt == 'robe':
        return
    greave = sp.pal.get('greave')
    if front:
        leg(cv, (hx + 1, hy), s['f_foot'], sp.legs, sp.boots, l=b['leg'], w=b['leg_w'], boot_len=b['boot'],
            greave=greave)
    else:
        leg(cv, (hx - 1, hy), s['b_foot'], sp.legs_b if hasattr(sp, 'legs_b') else sp.legs, sp.boots,
            l=b['leg'], w=b['leg_w'], boot_len=b['boot'], greave=greave)


def skirt(cv, sp, s, p):
    b = s['b']
    hx, hy = s['hip']
    bw = b['body']
    k = sp.skirt
    pal = sp.skirt_pal or sp.tunic
    if k == 'tabard':
        m = cv.mask().poly([(hx - bw, hy - 2), (hx + bw, hy - 2), (hx + bw + 1, hy + 3), (hx - bw - 1, hy + 3)])
        cv.part(m, pal)
    elif k == 'kilt':
        m = cv.mask().poly([(hx - bw, hy - 2), (hx + bw, hy - 2), (hx + bw + 2, hy + 5), (hx - bw - 1, hy + 5)])
        cv.part(m, pal)
        for x in range(int(hx - bw), int(hx + bw + 2), 2):
            cv.dot(x, hy + 3, pal.sh)
    elif k == 'coat':
        m = cv.mask().poly([(hx - bw, hy - 2), (hx + bw, hy - 2), (hx + bw + 1, hy + 4), (hx + 1, hy + 5),
                            (hx - bw - 2, hy + 6)])
        cv.part(m, pal)
        if sp.trim:
            t = cv.mask().line(hx + bw + 1, hy + 4, hx + 1, hy + 5, 1).line(hx + 1, hy + 5, hx - bw - 2, hy + 6, 1)
            t.line(hx + bw, hy - 2, hx + bw + 1, hy + 4, 1)
            cv.part(t, sp.trim, shade=False, separate=False)
    elif k == 'dress':
        ff, bf = s['f_foot'], s['b_foot']
        bottom = hy + 7
        m = cv.mask().poly([(hx - bw, hy - 3), (hx + bw, hy - 3), (max(hx + bw + 3, ff[0] - 1), bottom),
                            (hx + 1, bottom + 1), (min(hx - bw - 3, bf[0] + 1), bottom)])
        cv.part(m, pal)
        for x in range(int(hx - bw - 2), int(hx + bw + 3), 2):
            cv.dot(x, bottom - 1, pal.sh)
        if sp.trim:
            t = cv.mask().line(min(hx - bw - 3, bf[0] + 1), bottom, hx + 1, bottom + 1, 1)
            t.line(hx + 1, bottom + 1, max(hx + bw + 3, ff[0] - 1), bottom, 1)
            cv.part(t, sp.trim, shade=False, separate=False)
    elif k == 'robe':
        ff, bf = s['f_foot'], s['b_foot']
        bottom = max(ff[1], bf[1])
        fx_ = max(hx + bw + 3, ff[0] + 2)
        bx_ = min(hx - bw - 3, bf[0] - 1)
        m = cv.mask().poly([(hx - bw, hy - 3), (hx + bw, hy - 3), (fx_, bottom - 1), (hx + 1, bottom),
                            (bx_, bottom - 1)])
        cv.part(m, pal)
        # folds
        cv.part(cv.mask().line(hx + 1, hy + 1, hx + 2, bottom - 2, 1), Pal(pal.sh, pal.sh, pal.line), shade=False,
                separate=False)
        if sp.trim:
            t = cv.mask().line(bx_, bottom - 1, fx_, bottom - 1, 1)
            t.line(hx + 3, hy - 2, fx_ - 1, bottom - 1, 1)
            cv.part(t, sp.trim, shade=False, separate=False)
        # boot tips peeking out
        for foot in (bf, ff):
            cv.part(cv.mask().rect(foot[0], foot[1] - 1, foot[0] + 2, foot[1]), sp.boots)
    elif k == 'loin':
        m = cv.mask().poly([(hx - bw, hy - 2), (hx + bw, hy - 2), (hx + 3, hy + 5), (hx, hy + 7), (hx - 3, hy + 4)])
        cv.part(m, pal)
        for (dx, dy) in ((0, 3), (-1, 5), (2, 1)):
            cv.dot(hx + dx, hy + dy, pal.hi)
    if sp.belt is not None and k != 'robe':
        cv.part(cv.mask().rect(hx - bw, hy - 2, hx + bw, hy - 2), sp.belt, shade=False)
    elif sp.belt is not None:
        cv.part(cv.mask().rect(hx - bw, hy - 3, hx + bw, hy - 3), sp.belt, shade=False)


def neckwear(cv, sp, s, p):
    sx, sy = s['sh']
    b = s['b']
    k = sp.neck
    if k == 'scarf':
        cv.part(cv.mask().rect(sx - 3, sy - 1, sx + 3, sy + 1), sp.neck_pal)
    elif k == 'mantle':
        bw = b['body']
        m = cv.mask().poly([(sx - bw - 1, sy - 1), (sx + bw + 1, sy - 2), (sx + bw + 3, sy + 3), (sx + 1, sy + 5),
                            (sx - bw - 2, sy + 4)])
        cv.part(m, sp.neck_pal)
        for x in range(int(sx - bw), int(sx + bw + 2), 2):
            cv.dot(x, sy + 3 + (x % 2), sp.neck_pal.sh)
    elif k == 'collar':
        cv.part(cv.mask().poly([(sx - 3, sy - 1), (sx + 3, sy - 2), (sx + 4, sy + 1), (sx - 3, sy + 1)]), sp.neck_pal)
    elif k == 'fur':
        m = cv.mask().ellipse(sx, sy, 5, 2.3)
        cv.part(m, sp.neck_pal)
        for x in range(int(sx - 4), int(sx + 5), 2):
            cv.dot(x, sy + 2, sp.neck_pal.base)
            cv.dot(x + 1, sy - 2, sp.neck_pal.hi)


def pauldrons(cv, sp, s, p, front):
    b = s['b']
    if front and sp.pauldron is not None:
        fsx, fsy = s['f_sh']
        r = 2.6 if b['arm_w'] < 4 else 3.4
        cv.part(cv.mask().ellipse(fsx, fsy, r, r * 0.85), sp.pauldron)
        if sp.trim is not None and sp.pal.get('pauldron_trim', True):
            cv.part(cv.mask().line(fsx - r + 1, fsy + r * 0.85 - 0.5, fsx + r - 1, fsy + r * 0.85 - 0.5, 1), sp.trim,
                    shade=False, separate=False)
    if not front and sp.pauldron_b is not None:
        bsx, bsy = s['b_sh']
        r = 2.4 if b['arm_w'] < 4 else 3.2
        cv.part(cv.mask().ellipse(bsx, bsy, r, r * 0.85), sp.pauldron_b)


def do_head(cv, sp, s, p):
    front, back = HAIR.get(sp.hair_style, (None, None))
    cx, cy = s['head']

    def hair_fn(cv_, x, y):
        if front:
            front(cv_, x, y, sp)
        for hg in sp.head:
            HEADGEAR[hg](cv_, x, y, sp, 'front')
        if sp.beard:
            BEARDS[sp.beard](cv_, x, y, sp)
    draw_head(cv, (cx, cy), sp.skin, hair_fn, p.eyes, eye_col=sp.eye)


# ------------------------------------------------------------------ aura
def aura(cv, sp, s, p):
    k = sp.aura
    if not k:
        return
    hx, hy = s['hip']
    t = p.t + {'idle': 0, 'attack': 3, 'hit': 7, 'victory': 11, 'ko': 5, 'burst': 13, 'guard': 17}.get(p.anim, 0)
    c = sp.fx
    if k == 'spark':
        # embers rising around the body
        for i in range(3):
            ph = (t * 3 + i * 7) % 16
            x = hx - 9 + i * 8 + ((t + i) % 3) - 1
            y = hy + 6 - ph * 1.6
            if 6 < y < 44:
                cv.dot(x, y, c[i % 3])
    elif k == 'drop':
        for i in range(3):
            a = t * 0.7 + i * 2.094
            cv.dot(hx + math.cos(a) * 11, hy - 4 + math.sin(a) * 3, c[i % 3])
    elif k == 'leaf':
        for i in range(3):
            ph = (t * 2 + i * 5) % 14
            x = hx - 10 + i * 9 + math.sin(t * 0.8 + i) * 1.5
            y = 10 + ph * 2.2
            if y < 42:
                cv.dot(x, y, c[i % 3])
                cv.dot(x + 1, y, c[(i + 1) % 3])
    elif k == 'petal':
        for i in range(4):
            ph = (t * 2 + i * 4) % 15
            x = hx - 12 + i * 7 + math.sin(t * 0.9 + i * 1.3) * 2
            y = 8 + ph * 2.1
            if y < 42:
                cv.dot(x, y, c[i % 3])
                if i % 2:
                    cv.dot(x + 1, y + 1, c[(i + 1) % 3])
    elif k == 'frost':
        for i in range(3):
            ph = (t * 2 + i * 5) % 14
            x = hx - 10 + i * 9 + ((t + i) % 2)
            y = 12 + ph * 2
            if y < 42:
                cv.dot(x, y, c[i % 3])
    elif k == 'glyph':
        for i in range(3):
            a = t * 0.6 + i * 2.094
            x, y = hx + math.cos(a) * 12, hy - 8 + math.sin(a) * 4
            cv.dot(x, y, c[0])
            cv.dot(x + 1, y, c[1])
            cv.dot(x, y - 1, c[2])


# ------------------------------------------------------------------ fx
def fx_dot(cv, x, y, col):
    if 0 <= x < W and 0 <= y < H:
        cv.dot(x, y, col)


def draw_fx(cv, sp, s, p):
    cols = sp.fx
    for f in p.fx:
        if isinstance(f[0], str):
            kind = f[0]
            if kind == 'ring':             # ('ring', cx, cy, rx, ry, n, phase)
                _, cx, cy, rx, ry, n, ph = f
                if cx == 'focus':
                    cx, cy = s['focus'] or s['f_hand']
                for i in range(n):
                    a = ph + i * 2 * math.pi / n
                    fx_dot(cv, cx + math.cos(a) * rx, cy + math.sin(a) * ry, cols[i % 3])
            elif kind == 'streak':         # ('streak', x0, y0, x1, y1, ci)
                _, x0, y0, x1, y1, ci = f
                n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
                for i in range(n):
                    t = i / max(n - 1, 1)
                    fx_dot(cv, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, cols[(ci + (i * 3) // n) % 3])
            elif kind == 'star':           # ('star', x, y, r)
                _, x, y, r = f
                if x == 'focus':
                    x, y = s['focus'] or s['f_hand']
                elif x == 'focus_tip':
                    x, y = s.get('arrow_tip') or s['focus'] or s['f_hand']
                fx_dot(cv, x, y, cols[2])
                for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    for k in range(1, r + 1):
                        fx_dot(cv, x + dx * k, y + dy * k, cols[0] if k == 1 else cols[1])
            elif kind == 'bolt':           # ('bolt', x, y, style)
                BOLTS[f[3]](cv, sp, f[1], f[2])
            elif kind == 'crack':          # ('crack', x, y, len)
                _, x, y, n = f
                for i in range(n):
                    fx_dot(cv, x + i, y + (1 if i % 3 == 1 else 0), cols[i % 2])
                    fx_dot(cv, x - i, y + (1 if i % 3 == 2 else 0), cols[(i + 1) % 2])
            elif kind == 'column':         # ('column', x, y_top, y_bot)
                _, x, y0, y1 = f
                for y in range(int(y0), int(y1) + 1):
                    fx_dot(cv, x, y, cols[(y // 2) % 3])
                    if y > y0 + 2 and y % 2 == 0:
                        fx_dot(cv, x + 1, y, cols[0])
            elif kind == 'glyph':          # ('glyph', x, y)
                _, x, y = f
                for (dx, dy) in ((0, 0), (1, 0), (0, 1), (-1, 1), (1, 2), (0, 2)):
                    fx_dot(cv, x + dx, y + dy, cols[(dx + dy) % 3])
            elif kind == 'arrow':          # ('arrow', x, y, angle, len)
                _, x, y, a, n = f
                ux, uy = uv(a)
                for i in range(n):
                    fx_dot(cv, x - ux * i, y - uy * i, sp.pal['arrow'].base if i > 1 else sp.pal['arrowhead'].hi)
                fx_dot(cv, x - ux * n, y - uy * n - 1, sp.pal['fletch'].base)
                fx_dot(cv, x - ux * n, y - uy * n + 1, sp.pal['fletch'].base)
            elif kind == 'petal':          # ('petal', x, y)
                _, x, y = f
                fx_dot(cv, x, y, sp.pal['petal'].base)
                fx_dot(cv, x + 1, y, sp.pal['petal'].hi)
        else:
            x, y, ci = f
            fx_dot(cv, x, y, cols[ci % 3])


BOLTS = {}


@reg(BOLTS, 'ember')
def _(cv, sp, x, y):
    for i, c in enumerate(('#a8300f', '#e0521c', '#ff8a2a')):
        fx_dot(cv, x - 6 + i * 2, y + (i % 2), hexc(c))
    m = [(0, 0), (1, 0), (0, -1), (0, 1), (-1, 0), (1, 1), (1, -1)]
    for (dx, dy) in m:
        fx_dot(cv, x + dx, y + dy, hexc('#ff8a2a'))
    fx_dot(cv, x, y, hexc('#fff3b0'))
    fx_dot(cv, x + 1, y, hexc('#ffd35a'))


@reg(BOLTS, 'orb')
def _(cv, sp, x, y):
    for i in range(3):
        fx_dot(cv, x - 5 + i * 2, y, hexc(('#23a8c4', '#4fc9e8', '#9ff3ff')[i]))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if abs(dx) + abs(dy) < 2:
                fx_dot(cv, x + dx, y + dy, hexc('#4fc9e8'))
    fx_dot(cv, x, y - 1, hexc('#e0ffff'))
    fx_dot(cv, x, y, hexc('#9ff3ff'))


@reg(BOLTS, 'petals')
def _(cv, sp, x, y):
    P = sp.pal['petal']
    for (dx, dy, c) in ((0, 0, P.hi), (1, 0, P.base), (-2, 1, P.base), (-1, -1, P.hi), (-4, 0, P.sh), (-3, 2, P.base)):
        fx_dot(cv, x + dx, y + dy, c)
    fx_dot(cv, x - 5, y - 1, sp.pal['leafp'].hi)


# ------------------------------------------------------------------ main draw
def draw(sp, p):
    cv = Canvas(W, H)
    s = skel(sp, p)
    b = s['b']
    wk0 = WEAPONS[sp.weapon['kind']]
    wk = (lambda *a: None) if p.x.get('noweapon') else wk0
    for f in sp.back:
        BACKFX[f](cv, sp, s, p)
    for hg in sp.head:
        HEADGEAR[hg](cv, s['head'][0], s['head'][1], sp, 'back')
    if sp.cape:
        CAPES[sp.cape](cv, sp, s, p)
    hb = HAIR.get(sp.hair_style, (None, None))[1]
    if hb:
        hb(cv, sp, s, p)
    wk(cv, sp, s, p, 'back')
    arm(cv, s['b_sh'], s['b_hand'], sp.sleeve_b or sp.sleeve, sp.skin, bend=-1, l=b['arm'], w=b['arm_w'],
        glove=sp.glove, cuff=sp.pal.get('cuff_b'))
    wk(cv, sp, s, p, 'back_hand')
    pauldrons(cv, sp, s, p, False)
    lower(cv, sp, s, p, False)
    body(cv, sp, s, p)
    lower(cv, sp, s, p, True)
    skirt(cv, sp, s, p)
    for it in sp.items:
        ITEMS[it](cv, sp, s, p, 'torso')
    wk(cv, sp, s, p, 'mid')
    neckwear(cv, sp, s, p)
    do_head(cv, sp, s, p)
    pauldrons(cv, sp, s, p, True)
    for it in sp.items:
        ITEMS[it](cv, sp, s, p, 'shoulder')
    wk(cv, sp, s, p, 'pre')
    fsx, fsy = s['f_sh']
    arm(cv, (fsx, fsy + 1), s['f_hand'], sp.sleeve, sp.skin, bend=1, l=b['arm'], w=b['arm_w'], glove=sp.glove,
        cuff=sp.pal.get('cuff'))
    wk(cv, sp, s, p, 'post')
    cv.outline()
    if p.glow:
        cv.glow(sp.glow_col, alpha=110 if p.glow is True else p.glow)
    elif sp.aura_glow:
        cv.glow(sp.glow_col, alpha=sp.aura_glow)
    wk(cv, sp, s, p, 'fx')
    aura(cv, sp, s, p)
    draw_fx(cv, sp, s, p)
    return cv.image()


# ================================================================== weapons
def _stick(cv, a0, a1, pal, w=2, separate=False):
    cv.part(cv.mask().line(a0[0], a0[1], a1[0], a1[1], w), pal, separate=separate)


# ---- lantern staff (Rhea)
@reg(WEAPONS, 'lantern')
def _(cv, sp, s, p, layer):
    wp = sp.weapon
    if layer != 'pre' and layer != 'fx':
        return
    hand = s['f_hand']
    a = p.w
    L = wp.get('len', 16)
    if layer == 'fx':
        return
    below = wp.get('below', 5)
    bot = along(hand, a, -below)
    top = along(hand, a, clamp_len(hand, a, L - below, lo=4))
    _stick(cv, bot, top, wp['wood'])
    sw = p.x.get('lsw', 0)
    style = wp.get('style', 'one')
    glow = p.glow or p.x.get('lit', False)
    if style == 'sun':
        # radiant sun orb cradled in a brass crescent
        c = along(top, a, 3)
        cr = cv.mask().ellipse(c[0], c[1], 3.4, 3.4).subtract(cv.mask().ellipse(c[0] + 0.6, c[1] - 0.6, 2.6, 2.6))
        cv.part(cr, wp['brass'], separate=False)
        orb = cv.mask().ellipse(c[0] + 0.3, c[1] - 0.3, 2.4, 2.4)
        cv.part(orb, wp['orb'] if not glow else Pal('#fff6c8', '#ffffff', '#ffd35a'), separate=False)
        s['focus'] = c
        s['rays'] = c
        return
    hooks = [top] if style == 'one' else [side(top, a, -3.2), side(top, a, 3.2)]
    if style == 'two':
        _stick(cv, hooks[0], hooks[1], wp['brass'], w=1)
    else:
        hk = (top[0] + 2, top[1])
        _stick(cv, top, hk, wp['brass'], w=1)
        hooks = [hk]
    foc = []
    for i, hk in enumerate(hooks):
        swi = sw * (1 if i == 0 else 0.8)
        cx, cy = hk[0] + swi * 0.7, hk[1] + 4
        cv.part(cv.mask().line(hk[0], hk[1], cx, cy - 2, 1), wp['brass'], shade=False, separate=False)
        body_ = cv.mask().rect(cx - 1, cy - 1, cx + 1, cy + 2)
        cv.part(body_, wp['brass'])
        cv.part(cv.mask().rect(cx - 2, cy - 2, cx + 2, cy - 2), wp['brass'], shade=False)   # cap
        cv.dot(cx, cy + 3, wp['brass'].sh)
        fl = hexc('#fff3b0') if glow else hexc('#ffd35a')
        cv.dot(cx, cy, fl)
        cv.dot(cx, cy + 1, hexc('#ff8a2a'))
        foc.append((cx, cy))
    s['focus'] = foc[0] if len(foc) == 1 else ((foc[0][0] + foc[1][0]) / 2, foc[0][1])


# ---- blossom staff (Faye)
@reg(WEAPONS, 'blossom')
def _(cv, sp, s, p, layer):
    if layer != 'pre':
        return
    wp = sp.weapon
    hand = s['f_hand']
    a = p.w
    L = wp.get('len', 16)
    bot = along(hand, a, -5)
    top = along(hand, a, clamp_len(hand, a, L - 5, lo=5))
    _stick(cv, bot, top, wp['wood'])
    # curling vine along the shaft
    for k in range(3):
        q = along(hand, a, 2 + k * 3)
        q = side(q, a, 1 if k % 2 else -1)
        cv.dot(q[0], q[1], wp['vine'].base)
    c = along(top, a, 3)
    glow = p.glow or wp.get('glowing')
    P1 = wp['petal'] if not glow else Pal(lighten(wp['petal'].base, 0.25), (255, 250, 250, 255), wp['petal'].base)
    r = wp.get('r', 3.0)
    n = wp.get('petals', 5)
    rot = p.x.get('spin', 0)
    for i in range(n):
        ang = rot + i * 2 * math.pi / n - math.pi / 2
        pc = (c[0] + math.cos(ang) * r * 0.75, c[1] + math.sin(ang) * r * 0.75)
        cv.part(cv.mask().ellipse(pc[0], pc[1], r * 0.62, r * 0.62), P1, separate=True)
    cv.part(cv.mask().ellipse(c[0], c[1], 1.0, 1.0), wp['core'], separate=False)
    s['focus'] = c


# ---- great axe (Voss)
@reg(WEAPONS, 'greataxe')
def _(cv, sp, s, p, layer):
    wp = sp.weapon
    if layer not in ('pre', 'post'):
        return
    over = p.x.get('axe_front', False)
    if (layer == 'pre') == over:
        # 'pre' draws behind the front arm (default); 'post' when axe must be in front
        return
    hand = s['f_hand']
    a = p.w
    up = clamp_len(hand, a, wp.get('up', 11), lo=1, hi=46)
    butt = along(hand, a, -wp.get('down', 7))
    top = along(hand, a, up)
    _stick(cv, butt, top, wp['haft'], w=2, separate=True)
    cv.part(cv.mask().rect(butt[0] - 1, butt[1] - 1, butt[0], butt[1]), wp['metal'])
    # blade: crescent on the leading (clockwise) side of the haft near the top
    hs = wp.get('size', 1.0)
    fs = -1 if p.x.get('bflip') else 1

    def sd(q, d):
        return side(q, a, d * fs)
    h0 = along(top, a, 0.5)
    h1 = along(top, a, -5.5 * hs)
    pts = [h0, sd(along(top, a, 0.8 * hs), 2.4 * hs), sd(along(top, a, 2.6 * hs), 5.8 * hs),
           sd(along(top, a, -2.4 * hs), 7.0 * hs), sd(along(top, a, -8.0 * hs), 5.6 * hs),
           sd(along(top, a, -6.2 * hs), 2.4 * hs), h1]
    cv.part(cv.mask().poly(pts), wp['metal'])
    edge = cv.mask().line(*pts[2], *pts[3], 1).line(*pts[3], *pts[4], 1)
    cv.part(edge, wp['edge'], shade=False, separate=False)
    # back spike
    cv.part(cv.mask().poly([along(top, a, -1.5), sd(along(top, a, -2.5), -3.2 * hs), along(top, a, -4)]), wp['metal'])
    # ember cracks
    for k, (u, v) in enumerate(wp.get('cracks', ((-2, 3), (-4, 4), (-3, 2), (-5, 2)))):
        q = sd(along(top, a, u * hs), v * hs)
        cv.dot(q[0], q[1], wp['crack'][k % len(wp['crack'])])
    s['focus'] = sd(along(top, a, -2.5 * hs), 5 * hs)


# ---- flame-pennant spear (Seraphine)
@reg(WEAPONS, 'spear')
def _(cv, sp, s, p, layer):
    wp = sp.weapon
    if layer != 'post':
        return
    hand = s['f_hand']
    a = p.w
    fwd = clamp_len(hand, a, wp.get('fwd', 13), lo=1, hi=46)
    back = wp.get('back', 9)
    tip = along(hand, a, fwd)
    butt = along(hand, a, -back)
    _stick(cv, butt, along(tip, a, -3), wp['shaft'], w=2, separate=False)
    cv.part(cv.mask().rect(butt[0] - 1, butt[1] - 1, butt[0], butt[1]), wp['gold'])
    # pennant just below the spearhead, trailing behind (gravity + wind)
    pb = along(tip, a, -4)
    fly = p.x.get('pen', math.sin(p.t * 1.6) * 1.0)
    ux, uy = uv(a)
    tail_dir = (-ux * 0.8, max(0.4, 0.6 - uy * 0.3))
    q0 = pb
    q1 = along(pb, a, -3)
    q2 = (pb[0] + tail_dir[0] * 7 - 1, pb[1] + tail_dir[1] * 5 + 2 + fly)
    pen = cv.mask().poly([q0, q1, q2])
    cv.part(pen, wp['pennant'])
    cv.dot(q2[0], q2[1], wp['pennant'].hi)
    # spearhead: leaf blade
    guard = along(tip, a, -3)
    cv.part(cv.mask().line(side(guard, a, -1.6)[0], side(guard, a, -1.6)[1],
                           side(guard, a, 1.6)[0], side(guard, a, 1.6)[1], 1), wp['gold'], separate=False)
    head = cv.mask().poly([side(along(tip, a, -2.5), a, -1.4), tip, side(along(tip, a, -2.5), a, 1.4),
                           along(tip, a, -3.5)])
    head.line(guard[0], guard[1], tip[0], tip[1], 1)
    cv.part(head, wp['head'], separate=False)
    cv.dot(tip[0], tip[1], wp['edge'].hi)
    s['focus'] = tip


# ---- trident + shell buckler (Corin)
@reg(WEAPONS, 'trident')
def _(cv, sp, s, p, layer):
    wp = sp.weapon
    if layer == 'post':
        _shield(cv, sp, s, p)
        return
    if layer != 'back_hand':
        return
    hand = s['b_hand']
    a = p.w
    fwd = clamp_len(hand, a, wp.get('fwd', 12), lo=1, hi=46)
    back = wp.get('back', 7)
    if p.x.get('planted'):
        back = max(2, min(back, GROUND - hand[1] - 0.5))
    tip = along(hand, a, fwd)
    butt = along(hand, a, -back)
    _stick(cv, butt, along(tip, a, -3), wp['shaft'], w=2, separate=False)
    # three prongs
    base = along(tip, a, -3)
    cross = cv.mask().line(*side(base, a, -2.2), *side(base, a, 2.2), 1)
    for d in (-2.2, 0, 2.2):
        q0 = side(base, a, d)
        q1 = side(tip, a, d * 0.9) if d else along(tip, a, 1)
        cross.line(q0[0], q0[1], q1[0], q1[1], 1)
    cv.part(cross, wp['metal'], shade=False, separate=False)
    for d in (-2.2, 0, 2.2):
        q1 = side(tip, a, d * 0.9) if d else along(tip, a, 1)
        cv.dot(q1[0], q1[1], wp['metal'].hi)
    s['focus'] = tip


def _shield(cv, sp, s, p):
    wp = sp.weapon
    hx, hy = s['f_hand']
    style = wp.get('shield', 'shell')
    rs = p.x.get('sraise', 0)
    cx, cy = hx + 1, hy - 1 - rs
    if style == 'tower':
        pts = [(cx - 3, cy - 8), (cx + 3, cy - 9), (cx + 4, cy + 5), (cx, cy + 8), (cx - 4, cy + 5)]
        cv.part(cv.mask().poly(pts), wp['rim'])
        inner = [(cx - 2, cy - 6), (cx + 2, cy - 7), (cx + 3, cy + 4), (cx, cy + 6), (cx - 3, cy + 4)]
        cv.part(cv.mask().poly(inner), wp['face'], separate=False)
        # coral branches
        for (x0, y0, x1, y1) in ((0, 5, 0, -4), (0, 0, 2, -3), (0, 2, -2, -1), (0, -2, -1, -5)):
            cv.part(cv.mask().line(cx + x0, cy + y0, cx + x1, cy + y1, 1), wp['coral'], shade=False, separate=False)
        cv.dot(cx + 2, cy - 3, wp['coral'].hi)
        cv.dot(cx - 1, cy - 5, wp['coral'].hi)
        if wp.get('rune'):
            cv.dot(cx + 1, cy + 3, wp['rune'])
            cv.dot(cx - 1, cy + 3, wp['rune'])
        return
    r = wp.get('r', 4.0)
    # scallop shell: rounded fan that narrows to a hinge at the bottom
    fan = cv.mask().ellipse(cx, cy - 0.6, r, r * 0.9)
    fan.poly([(cx - r * 0.8, cy), (cx + r * 0.8, cy), (cx + 1, cy + r + 0.6), (cx - 1, cy + r + 0.6)])
    cv.part(fan, wp['rim'])
    inner = cv.mask().ellipse(cx, cy - 0.9, r - 1.1, r * 0.9 - 1.1)
    cv.part(inner, wp['face'], separate=False)
    hx0, hy0 = cx, cy + r - 0.5
    for k in (-2, -1, 0, 1, 2):
        ang = -math.pi / 2 + k * 0.5
        for d in range(2, int(r * 1.7)):
            x, y = hx0 + math.cos(ang) * d * 0.62 * (r / 4.0), hy0 + math.sin(ang) * d * 0.62 * (r / 4.0)
            if inner.m[int(round(y)) % H, int(round(x)) % W]:
                cv.dot(x, y, wp['face'].sh)
    ears = cv.mask().rect(cx - 2, cy + r - 1, cx + 2, cy + r)
    cv.part(ears, wp['rim'])
    if wp.get('coral_trim'):
        for k in range(-3, 4):
            x = cx + k * (r / 3.2)
            y = cy - 0.6 - math.sqrt(max(r * r * 0.81 - (x - cx) ** 2 * 0.81, 0)) + 0.4
            cv.dot(x, y, wp['coral'].hi if k % 2 else wp['coral'].base)
    if wp.get('iron_rim'):
        for k in range(-4, 5):
            ang = -math.pi / 2 + k * 0.36
            cv.dot(cx + math.cos(ang) * r * 0.98, cy - 0.6 + math.sin(ang) * r * 0.9, wp['iron'].hi if k % 2 else wp['iron'].base)


# ---- twin ice daggers (Nerys)
def _dagger(cv, sp, hand, a, L):
    wp = sp.weapon
    L = min(L, clamp_len(hand, a, L + 1) - 1)
    cv.part(cv.mask().line(*along(hand, a, -1.5), *hand, 2), wp['grip'], separate=False)
    g0, g1 = side(along(hand, a, 1), a, -1.5), side(along(hand, a, 1), a, 1.5)
    cv.part(cv.mask().line(g0[0], g0[1], g1[0], g1[1], 1), wp['guard'], shade=False, separate=False)
    curve = wp.get('curve', 1.2)
    pts_a, pts_b = [], []
    n = 6
    for i in range(n + 1):
        t = i / n
        c = side(along(hand, a, 1.5 + t * (L - 1.5)), a, -curve * t * t)
        wdt = 1.3 * (1 - t) + 0.2
        pts_a.append(side(c, a, -wdt))
        pts_b.append(side(c, a, wdt * 0.6))
    m = cv.mask().poly(pts_a + pts_b[::-1])
    cv.part(m, wp['ice'], separate=False)
    tip = pts_a[-1]
    cv.dot(tip[0], tip[1], wp['ice'].hi)
    return tip


@reg(WEAPONS, 'daggers')
def _(cv, sp, s, p, layer):
    wp = sp.weapon
    if layer == 'back_hand':
        a2 = p.w2 if p.w2 is not None else p.w + 20
        _dagger(cv, sp, s['b_hand'], a2, wp.get('len', 6))
    elif layer == 'post':
        s['focus'] = _dagger(cv, sp, s['f_hand'], p.w, wp.get('len', 6))


# ---- tome (Aldric)
@reg(WEAPONS, 'tome')
def _(cv, sp, s, p, layer):
    wp = sp.weapon
    if layer != 'post':
        return
    hx, hy = s['f_hand']
    lift = p.x.get('tome_up', 0)
    cx, cy = hx + 2, hy - 1 - lift
    op = p.x.get('open', 1.0)
    if op < 0.5:
        # closed tome
        cv.part(cv.mask().rect(cx - 3, cy - 3, cx + 3, cy + 1), wp['cover'])
        cv.part(cv.mask().rect(cx - 2, cy - 2, cx + 2, cy - 2), wp['page'], shade=False, separate=False)
        s['focus'] = (cx, cy - 5)
        return
    cov = cv.mask().poly([(cx - 5, cy - 3), (cx, cy - 1), (cx + 5, cy - 3), (cx + 5, cy + 1), (cx, cy + 2),
                          (cx - 5, cy + 1)])
    cv.part(cov, wp['cover'])
    bright = p.glow or p.x.get('lit')
    pg = cv.mask().poly([(cx - 4, cy - 4), (cx, cy - 2), (cx + 4, cy - 4), (cx + 4, cy), (cx, cy + 1), (cx - 4, cy)])
    cv.part(pg, wp['page'] if not bright else Pal('#f4ffff', '#ffffff', '#b8f0ff', '#6ab0c8'), separate=False)
    cv.part(cv.mask().line(cx, cy - 2, cx, cy + 1, 1), Pal(wp['page'].sh, wp['page'].sh, wp['page'].line),
            shade=False, separate=False)
    for (dx, dy) in ((-3, -2), (-2, -1), (2, -1), (3, -2), (-3, 0), (2, 1)):
        if cy + dy < cy + 1:
            cv.dot(cx + dx, cy + dy, wp['ink'])
    s['focus'] = (cx, cy - 6)


# ---- vine bow (Wren)
@reg(WEAPONS, 'bow')
def _(cv, sp, s, p, layer):
    wp = sp.weapon
    if layer not in ('pre', 'post'):
        return
    hand = s['f_hand']
    a = p.w
    L = wp.get('len', 14) / 2.0
    bend = wp.get('bend', 2.5)
    drawn = p.x.get('draw', 0.0)
    ux, uy = uv(a)
    if layer == 'pre':
        # string + nocked arrow go behind the bow hand
        tipu = side(along(hand, a, -bend), a, -L)
        tipd = side(along(hand, a, -bend), a, L)
        nock = along(hand, a, -bend - drawn)
        if drawn > 0.5:
            sm = cv.mask().line(tipu[0], tipu[1], nock[0], nock[1], 1).line(nock[0], nock[1], tipd[0], tipd[1], 1)
        else:
            sm = cv.mask().line(tipu[0], tipu[1], tipd[0], tipd[1], 1)
        cv.part(sm, wp['string'], shade=False, separate=False)
        n_arrows = p.x.get('arrows', 1 if p.x.get('nock', True) else 0)
        for k in range(n_arrows):
            spread = (k - (n_arrows - 1) / 2.0) * 6
            aa = a + spread
            head = along(nock, aa, bend + drawn + 3)
            cv.part(cv.mask().line(nock[0], nock[1], head[0], head[1], 1), wp['arrow'], shade=False, separate=False)
            cv.dot(head[0], head[1], wp['arrowhead'].hi)
            cv.dot(*along(head, aa, -1), wp['arrowhead'].base)
            f = along(nock, aa, 1)
            cv.dot(f[0], f[1], sp.pal['fletch'].base)
            if k == n_arrows // 2:
                s['arrow_tip'] = head
        if drawn > 0.5 or p.bh == 'nock':
            # fingers pulling the string
            cv.part(cv.mask().rect(nock[0] - 1, nock[1] - 1, nock[0], nock[1]), sp.glove or sp.skin)
        return
    # the bow limbs (post: in front of the hand)
    pts = []
    for i in range(11):
        t = -1 + i / 5.0
        q = side(along(hand, a, -bend * t * t * (1 + 0.15 * drawn)), a, t * L)
        if wp.get('recurve') and abs(t) > 0.8:
            q = along(q, a, (abs(t) - 0.8) * 8)
        pts.append(q)
    m = cv.mask()
    for i in range(10):
        m.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], 2 if 2 <= i <= 7 else 1)
    glow = p.glow or wp.get('glowing')
    cv.part(m, wp['wood'] if not glow else wp.get('glow_wood', wp['wood']), separate=False)
    # grip wrap + vine leaves
    cv.part(cv.mask().rect(hand[0] - 1, hand[1] - 1, hand[0], hand[1]), wp['grip'])
    for i in (2, 7) if not wp.get('thorns') else (1, 3, 6, 8):
        q = pts[i]
        c = wp['vine']
        cv.dot(*side(q, a, 0), c.hi)
        o = along(q, a, -1)
        cv.dot(o[0], o[1], c.base)
    if wp.get('thorns'):
        for i in (2, 4, 6, 8):
            o = along(pts[i], a, 1.2)
            cv.dot(o[0], o[1], wp['thorn'])
    s['focus'] = hand


# ---- great club (Gorran)
@reg(WEAPONS, 'club')
def _(cv, sp, s, p, layer):
    wp = sp.weapon
    over = p.x.get('club_front', True)
    if layer not in ('pre', 'post') or (layer == 'post') != over:
        return
    hand = s['f_hand']
    a = p.w
    L = clamp_len(hand, a, wp.get('len', 15), lo=1, hi=46)
    top = along(hand, a, L)
    butt = along(hand, a, -2.5)
    # log that swells toward the head
    pts = [side(butt, a, -1.4), side(along(hand, a, L * 0.4), a, -2.2), side(along(top, a, -2), a, -3.6),
           along(top, a, 0.8), side(along(top, a, -2), a, 3.6), side(along(hand, a, L * 0.4), a, 2.2),
           side(butt, a, 1.4)]
    cv.part(cv.mask().poly(pts), wp['wood'])
    # knots, iron band, moss
    band = along(hand, a, L * 0.55)
    cv.part(cv.mask().line(*side(band, a, -2.6), *side(band, a, 2.6), 1), wp['band'], shade=False, separate=False)
    for (u, v, c) in ((L - 3, -2, 'moss'), (L - 2, -1, 'moss'), (L - 5, 1.5, 'knot'), (L * 0.3, 0.5, 'knot')):
        q = side(along(hand, a, u), a, v)
        cv.dot(q[0], q[1], wp[c].hi if c == 'moss' else wp['wood'].line)
    if wp.get('bloom'):
        q = side(along(top, a, -2), a, -2)
        cv.dot(q[0], q[1], wp['bloom'].hi)
        cv.dot(q[0] + 1, q[1], wp['bloom'].base)
    s['focus'] = top


# ================================================================== items
@reg(ITEMS, 'satchel')
def _(cv, sp, s, p, layer):
    if layer != 'torso':
        return
    hx, hy = s['hip']
    sx, sy = s['sh']
    strap = cv.mask().line(sx + 2, sy, hx - 2, hy - 1, 1)
    cv.part(strap, sp.pal['strap'], shade=False, separate=False)
    bag = cv.mask().rect(hx - 5, hy - 2, hx - 2, hy + 1)
    cv.part(bag, sp.pal['bag'])
    cv.dot(hx - 3, hy - 1, sp.pal['brass'].hi)


@reg(ITEMS, 'molten')
def _(cv, sp, s, p, layer):
    """Glowing cracks across dark armour plates."""
    hx, hy = s['hip']
    sx, sy = s['sh']
    M = sp.pal['molten']
    if layer == 'torso':
        for (x0, y0, x1, y1) in ((sx - 1, sy + 2, sx + 2, sy + 5), (sx + 2, sy + 5, sx + 1, sy + 7),
                                 (sx + 3, sy + 2, sx + 5, sy + 4), (hx - 2, hy - 1, hx + 1, hy + 1)):
            cv.part(cv.mask().line(x0, y0, x1, y1, 1), M, shade=False, separate=False)
        cv.dot(sx + 2, sy + 5, M.hi)
    elif layer == 'shoulder':
        fsx, fsy = s['f_sh']
        cv.dot(fsx - 1, fsy - 1, M.hi)
        cv.dot(fsx, fsy, M.base)
        cv.dot(fsx + 1, fsy + 1, M.base)
        # spiked pauldron ridge
        cv.part(cv.mask().poly([(fsx - 2, fsy - 2), (fsx - 1, fsy - 5), (fsx + 1, fsy - 2)]), sp.pal['horn'])


@reg(ITEMS, 'coral')
def _(cv, sp, s, p, layer):
    C = sp.pal['coral']
    if layer == 'torso':
        sx, sy = s['sh']
        for (dx, dy) in ((1, 2), (3, 3), (2, 5), (4, 6)):
            cv.dot(sx + dx, sy + dy, C.base if dy % 2 else C.hi)
    elif layer == 'shoulder':
        fsx, fsy = s['f_sh']
        m = cv.mask().poly([(fsx - 3, fsy), (fsx - 2, fsy - 4), (fsx - 1, fsy - 1), (fsx, fsy - 5), (fsx + 1, fsy - 1),
                            (fsx + 3, fsy - 3), (fsx + 3, fsy + 1)])
        cv.part(m, C)


@reg(ITEMS, 'runes')
def _(cv, sp, s, p, layer):
    if layer != 'torso':
        return
    sx, sy = s['sh']
    R = sp.pal['rune']
    for (dx, dy) in ((1, 3), (2, 4), (1, 5), (3, 5)):
        cv.dot(sx + dx, sy + dy, R)


@reg(ITEMS, 'sash')
def _(cv, sp, s, p, layer):
    if layer != 'torso':
        return
    hx, hy = s['hip']
    fl = math.sin(p.t * 1.5) * 0.8
    m = cv.mask().poly([(hx - 3, hy - 2), (hx - 6 - fl, hy + 4), (hx - 4 - fl, hy + 5), (hx - 2, hy - 1)])
    cv.part(m, sp.pal['sash'])


@reg(ITEMS, 'bark')
def _(cv, sp, s, p, layer):
    """Gorran: bark ridges and moss on the torso."""
    sx, sy = s['sh']
    hx, hy = s['hip']
    if layer == 'torso':
        for (x0, y0, x1, y1) in ((sx - 2, sy + 2, sx - 1, sy + 7), (sx + 2, sy + 1, sx + 3, sy + 6),
                                 (sx + 5, sy + 3, sx + 5, sy + 7)):
            cv.part(cv.mask().line(x0, y0, x1, y1, 1), Pal(sp.skin.sh, sp.skin.sh, sp.skin.line), shade=False,
                    separate=False)
        for (dx, dy) in ((-4, 0), (-3, -1), (-2, 0), (4, 0), (5, 1)):
            cv.dot(sx + dx, sy + dy, sp.hair.hi if dx % 2 else sp.hair.base)
    elif layer == 'shoulder':
        fsx, fsy = s['f_sh']
        m = cv.mask().ellipse(fsx, fsy - 1, 3.4, 2.0)
        cv.part(m, sp.hair)
        for dx in (-2, 0, 2):
            cv.dot(fsx + dx, fsy - 2, sp.hair.hi)
        if sp.pal.get('bloom'):
            cv.dot(fsx + 1, fsy - 2, sp.pal['bloom'].hi)
            cv.dot(fsx + 2, fsy - 2, sp.pal['bloom'].base)


@reg(ITEMS, 'gold_trim')
def _(cv, sp, s, p, layer):
    if layer != 'torso':
        return
    sx, sy = s['sh']
    hx, hy = s['hip']
    t = cv.mask().line(sx + 2, sy + 1, hx + 2, hy - 2, 1)
    cv.part(t, sp.trim, shade=False, separate=False)


@reg(ITEMS, 'frost_mantle')
def _(cv, sp, s, p, layer):
    if layer != 'shoulder':
        return
    sx, sy = s['sh']
    F = sp.pal['fur']
    m = cv.mask().ellipse(sx, sy, 5.2, 2.4)
    m.poly([(sx - 5, sy), (sx - 7, sy + 5), (sx - 3, sy + 3)])
    cv.part(m, F)
    for x in range(int(sx - 4), int(sx + 5), 2):
        cv.dot(x, sy + 2, F.sh)
    cv.dot(sx + 3, sy - 1, sp.pal['ice'].hi)


@reg(ITEMS, 'glyph_belt')
def _(cv, sp, s, p, layer):
    if layer != 'torso':
        return
    hx, hy = s['hip']
    for dx in (-2, 0, 2):
        cv.dot(hx + dx, hy - 3, sp.fx[0])


@reg(ITEMS, 'blossoms')
def _(cv, sp, s, p, layer):
    if layer != 'torso':
        return
    hx, hy = s['hip']
    sx, sy = s['sh']
    for (x, y) in ((hx + 3, hy + 3), (hx - 3, hy + 5), (sx + 3, sy + 2)):
        cv.dot(x, y, sp.pal['petal'].hi)
        cv.dot(x + 1, y, sp.pal['petal'].base)


# ================================================================== builder
def frames_for(sp, anim, seq):
    from rig import lying as _lying
    out = []
    for i, d in enumerate(seq):
        d = dict(d)
        is_lying = d.pop('lying', False)
        p = GP(t=i, anim=anim, **d)
        im = draw(sp, p)
        out.append(_lying(im) if is_lying else im)
    return out


def anims(sp):
    """[(name, frames, fps, loop)] in the canonical row order."""
    import hero_moves as HM
    mv = HM.MOVES[sp.moves]
    seqs = mv['fn']()
    return [(n, frames_for(sp, n, seqs[n]), mv['fps'][n], HM.LOOP.get(n, False)) for n in HM.ORDER]
