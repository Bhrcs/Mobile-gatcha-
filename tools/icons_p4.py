"""
icons_p4.py - Cinderbound art pack 4 (all ORIGINAL, procedurally drawn).

  * 16x16 icons (materials, training wisps, currencies, menu/nav/status icons)
    in the same family style as the existing icons: 3-tone shading lit from
    the top-left, 1px tinted dark outline, transparent background.
  * Battle effects (horizontal strips, facing right) + metadata merged into
    assets/effects/effects.json without touching existing entries.
  * "Embergate" summon gate (frame + looping vortex), the Standard Summon
    banner and the rarity reveal glows.

Run:  python3 tools/make_p4.py            (writes assets)
      python3 tools/make_p4.py --preview DIR   (also writes contact sheets)
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixlib import Canvas, Pal, hexc, mix, darken, lighten  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Content'))  # game content root
ICON_DIR = os.path.join(ROOT, 'assets', 'icons')
FX_DIR = os.path.join(ROOT, 'assets', 'effects')
UI_DIR = os.path.join(ROOT, 'assets', 'ui')

BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=float) / 16.0


def C(h, a=255):
    return hexc(h, a)


def save(img, path):
    img.save(path, optimize=True)


def to_img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def put(a, x, y, col, alpha=None):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < a.shape[1] and 0 <= y < a.shape[0]:
        c = C(col) if isinstance(col, str) else col
        if alpha is not None:
            c = tuple(c[:3]) + (alpha,)
        elif len(c) == 3:
            c = tuple(c) + (255,)
        a[y, x] = c


def blend(a, x, y, col, alpha):
    """Alpha-over a single pixel (keeps existing pixels readable)."""
    x, y = int(round(x)), int(round(y))
    if not (0 <= x < a.shape[1] and 0 <= y < a.shape[0]):
        return
    c = np.array(C(col) if isinstance(col, str) else col, dtype=float)
    dst = a[y, x].astype(float)
    sa = alpha / 255.0
    da = dst[3] / 255.0
    oa = sa + da * (1 - sa)
    if oa <= 0:
        return
    rgb = (c[:3] * sa + dst[:3] * da * (1 - sa)) / oa
    a[y, x] = list(np.clip(rgb, 0, 255).astype(np.uint8)) + [int(round(oa * 255))]


# =================================================================== ICONS
def icon(draw, post=None):
    cv = Canvas(16, 16)
    draw(cv)
    cv.outline()
    img = cv.image()
    if post:
        a = np.array(img)
        post(a)
        img = Image.fromarray(a, 'RGBA')
    return img


def twinkle(a, x, y, core='#ffffff', arm='#fff0b0', big=False):
    """4-point sparkle drawn after the outline (no outline of its own)."""
    put(a, x, y, core)
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        put(a, x + dx, y + dy, arm)
    if big:
        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            blend(a, x + dx, y + dy, arm, 150)


class El:
    def __init__(self, base, hi, sh, glow, deep):
        self.base, self.hi, self.sh, self.glow, self.deep = base, hi, sh, glow, deep

    def pal(self):
        return Pal(self.base, self.hi, self.sh)


FIRE = El('#ff6a2a', '#ffc070', '#b8301a', '#fff0b0', '#6a1410')
WATER = El('#3aa0e0', '#a8eaff', '#1f5fa8', '#e6ffff', '#143a7a')
NATURE = El('#5aa832', '#b0e070', '#2f6a1c', '#e8ffc0', '#1a4012')
INFERNAL = El('#e8401e', '#ffb04a', '#8a1812', '#fff3a8', '#4a0a0a')
ABYSS = El('#2a62d0', '#7ad0ff', '#16287a', '#e0ffff', '#0c1440')
GOLD = Pal('#e0a83a', '#fff0b0', '#a8741e')
GOLD_DARK = Pal('#a8741e', '#e0a83a', '#6a4410')
IRON = Pal('#5a5660', '#8a8690', '#3a3640')
STEEL = Pal('#c9d1dc', '#ffffff', '#8e98a8')
WOOD = Pal('#a8743a', '#d8a868', '#6a4420')
PARCH = Pal('#e8d8b0', '#fff6e0', '#b0986a')
UP_GREEN = Pal('#7ae05a', '#c0ff9a', '#3a9a2a')
DOWN_RED = Pal('#e8342a', '#ff8a6a', '#8a1a14')


# ---------------------------------------------------------------- materials
def ic_fragment(E):
    """Tier 1: a small broken crystal chip plus a loose splinter."""
    def d(cv):
        cv.part(cv.mask().poly([(2.5, 12.5), (3.5, 8), (8, 3.5), (10.5, 6), (9.5, 11), (6, 13.5)]), E.pal())
        cv.part(cv.mask().poly([(4.5, 9), (8, 5), (8, 9.5), (5.5, 12)]), Pal(E.hi, E.glow, E.base), separate=False)
        cv.part(cv.mask().poly([(12.5, 14), (13, 10.5), (14.8, 13)]), E.pal())

    def post(a):
        put(a, 7, 6, '#ffffff')

    return icon(d, post)


def ic_core(E):
    """Tier 2: glowing orb seated in a gold claw setting."""
    def d(cv):
        cv.part(cv.mask().ellipse(7.5, 6.5, 4.8, 4.8), E.pal())
        cv.part(cv.mask().ellipse(7, 6, 2.2, 2.2), Pal(E.hi, E.glow, E.hi), separate=False)
        claw = cv.mask().ellipse(7.5, 8.2, 6.2, 4.6)
        claw.subtract(cv.mask().ellipse(7.5, 6.3, 4.9, 4.9))
        keep = cv.mask().rect(0, 7, 15, 15)
        claw.m &= keep.m
        claw.rect(1, 5, 2, 8).rect(13, 5, 14, 8)       # side prongs
        cv.part(claw, GOLD)
        cv.part(cv.mask().rect(6, 12, 9, 12).rect(4, 13, 11, 14), GOLD_DARK)

    def post(a):
        put(a, 5, 4, '#ffffff')
        put(a, 6, 3, '#ffffff')
        put(a, 5, 5, E.glow)
        twinkle(a, 13, 2, '#ffffff', E.glow)

    return icon(d, post)


def ic_crystal(E, spark=True):
    """Tier 3: large faceted radiant crystal cluster."""
    def d(cv):
        side = Pal(E.sh, E.base, E.deep)
        cv.part(cv.mask().poly([(1, 10), (3, 6), (6, 8), (6, 14), (2, 14)]), side)
        cv.part(cv.mask().poly([(10, 8), (13, 5), (14.5, 9), (14, 14), (10, 14)]), side)
        cv.part(cv.mask().poly([(8, 1), (11.5, 4.5), (11.5, 11), (8, 14.5), (4.5, 11), (4.5, 4.5)]), E.pal())
        cv.part(cv.mask().poly([(8, 2), (9.5, 5), (9.5, 11), (8, 13), (7, 11), (7, 5)]),
                Pal(E.hi, E.glow, E.base), separate=False)

    def post(a):
        put(a, 8, 3, '#ffffff')
        put(a, 8, 4, E.glow)
        put(a, 3, 8, E.hi)
        put(a, 12, 7, E.hi)
        if spark:
            twinkle(a, 13, 2, '#ffffff', E.glow)
            twinkle(a, 2, 3, '#ffffff', E.glow)

    return icon(d, post)


def ic_ancient_seed():
    """Tier 3 nature: an acorn-shaped emerald seed with a gold cap and a living sprout."""
    leaf = Pal('#8ad04a', '#c8f080', '#3f7a22')

    def d(cv):
        cv.part(cv.mask().poly([(8.5, 3), (11.5, 0.5), (13, 1.5), (10.5, 3.5)]), leaf)
        cv.part(cv.mask().line(8, 4, 8.5, 2.5, 1), Pal('#4a8a2a'), shade=False)
        body = cv.mask().poly([(3.2, 6.5), (12.8, 6.5), (12.3, 10.5), (8, 14.8), (3.7, 10.5)])
        cv.part(body, Pal('#2e9a50', '#86e0a0', '#145a2e'))
        cv.part(cv.mask().poly([(6, 7.5), (10, 7.5), (8, 13)]), Pal('#5ac878', '#b8f0c8', '#2e9a50'), separate=False)
        cv.part(cv.mask().poly([(7, 8), (9, 8), (8, 11)]), Pal('#e8ffc0', '#ffffff', '#b8f0c8'), separate=False)
        cv.part(cv.mask().ellipse(8, 5.2, 5.6, 2.6), GOLD)
        for (x, y) in ((5, 5), (8, 5), (11, 5), (6, 6), (10, 6)):
            cv.dot(x, y, C('#a8741e'))

    def post(a):
        put(a, 5, 4, '#fff6c8')
        twinkle(a, 14, 9, '#ffffff', '#e8ffc0')
        twinkle(a, 1, 11, '#ffffff', '#e8ffc0')

    return icon(d, post)


def ic_prism_shard():
    """Generic high tier shard: white crystal with rainbow facets."""
    def d(cv):
        body = cv.mask().poly([(9, 1), (13, 6), (11, 14), (6, 14.5), (3, 8)])
        cv.part(body, Pal('#e8e4ff', '#ffffff', '#a8a0d8'))
        cv.part(cv.mask().poly([(4.5, 8), (8, 3), (7.5, 9), (6, 13)]), Pal('#ff8ac8'), flat=True)
        cv.part(cv.mask().poly([(8, 3), (9, 1.5), (9.5, 7), (7.5, 9)]), Pal('#ffe070'), flat=True)
        cv.part(cv.mask().poly([(9.5, 7), (12, 6), (10.5, 12)]), Pal('#6ae0ff'), flat=True)
        cv.part(cv.mask().poly([(7.5, 9), (9.5, 7), (10.5, 12), (8, 13)]), Pal('#8ae06a'), flat=True)
        cv.part(cv.mask().poly([(6, 13), (7.5, 9), (8, 13)]), Pal('#b07aff'), flat=True)

    def post(a):
        put(a, 8, 5, '#ffffff')
        put(a, 7, 6, '#ffffff')
        twinkle(a, 13, 2, '#ffffff', '#e8d8ff')
        twinkle(a, 2, 12, '#ffffff', '#ffe0f0')

    return icon(d, post)


# ---------------------------------------------------------------- wisps
def ic_wisp(E, kind, big=False):
    def d(cv):
        if big:
            cx, cy, r = 8.5, 8.5, 5.0
            tail = [(5.5, 13, 2.3), (3.5, 14, 1.4)]
        else:
            cx, cy, r = 9, 7.5, 4.2
            tail = [(6, 11.5, 2.3), (4.2, 13, 1.5), (2.8, 13.8, 0.9)]
        m = cv.mask().ellipse(cx, cy, r, r * 0.95)
        for (tx, ty, tr) in tail:
            m.ellipse(tx, ty, tr, tr)
        if kind == 'fire':
            m.poly([(cx - 3, cy - 2), (cx - 1, cy - 7), (cx + 0.5, cy - 3)])
            m.poly([(cx, cy - 3), (cx + 2.5, cy - 6.5), (cx + 3.5, cy - 1)])
        elif kind == 'water':
            m.poly([(cx - 2.5, cy - 2), (cx + 2, cy - 7), (cx + 3, cy - 1)])
        elif kind == 'radiant':
            m.poly([(cx - 2.5, cy - 3), (cx + 1, cy - 6.5), (cx + 3, cy - 2)])
        if kind == 'radiant':
            halo = cv.mask().ellipse(cx, 1.6, 3.4, 1.5)
            halo.subtract(cv.mask().ellipse(cx, 1.6, 1.6, 0.5))
            cv.part(halo, Pal('#fff4a8', '#ffffff', '#e0a830'))
        cv.part(m, E.pal())
        if kind == 'nature':
            cv.part(cv.mask().poly([(cx - 1, cy - 4), (cx - 5, cy - 7), (cx - 2, cy - 2)]),
                    Pal('#8ad04a', '#c8f080', '#3f7a22'))
            cv.part(cv.mask().poly([(cx + 1, cy - 4), (cx + 4, cy - 7.5), (cx + 2.5, cy - 2)]),
                    Pal('#8ad04a', '#c8f080', '#3f7a22'))
        cv.part(cv.mask().ellipse(cx - 0.5, cy + 0.5, r * 0.55, r * 0.5), Pal(E.hi, E.glow, E.hi), separate=False)
        ey = 8 if big else int(round(cy))
        ex = int(round(cx))
        for x in (ex - 2, ex + 1):
            cv.dot(x, ey, C('#241428'))
            cv.dot(x, ey + 1, C('#241428'))

    def post(a):
        ex = int(round(8.5 if big else 9))
        ey = 8 if big else 8
        put(a, ex - 2, ey, '#ffffff')
        put(a, ex + 1, ey, '#ffffff')
        if big:
            twinkle(a, 14, 5, '#ffffff', '#fff0a0')
            twinkle(a, 13, 13, '#ffffff', '#fff0a0')
            twinkle(a, 2, 5, '#ffffff', '#fff0a0')

    return icon(d, post)


RADIANT = El('#f8c030', '#fff4a8', '#c07a18', '#ffffff', '#6a4410')


# ---------------------------------------------------------------- misc icons
def ic_spark_sigil():
    """Burst training rune: slate diamond tablet with a glowing spark glyph."""
    def d(cv):
        cv.part(cv.mask().poly([(8, 0.5), (15, 7.5), (8, 14.5), (1, 7.5)]), Pal('#4a4658', '#7a7690', '#2a2634'))
        cv.part(cv.mask().poly([(8, 2.5), (13, 7.5), (8, 12.5), (3, 7.5)]), Pal('#2e2a3a', '#3e3a4c', '#1e1a26'))
        pts = []
        for i in range(8):
            r = 4.6 if i % 2 == 0 else 1.5
            ang = -math.pi / 2 + i * math.pi / 4
            pts.append((8 + math.cos(ang) * r, 7.5 + math.sin(ang) * r))
        cv.part(cv.mask().poly(pts), Pal('#6ae0ff', '#e0ffff', '#2a90d0'), separate=False)

    def post(a):
        put(a, 8, 7, '#ffffff')
        put(a, 8, 8, '#fff0a0')
        for (x, y) in ((8, 1), (14, 7), (8, 14), (1, 7)):
            pass
        twinkle(a, 13, 2, '#ffffff', '#fff0a0')

    return icon(d, post)


def ic_soul_shard():
    def d(cv):
        cv.part(cv.mask().poly([(12, 1), (13.5, 3), (6, 14), (3.5, 14.5), (4, 12)]), Pal('#9a5ae0', '#d8b0ff', '#5a2aa0'))
        cv.part(cv.mask().poly([(12, 2), (12.5, 3), (6, 12.5), (5, 12.5)]), Pal('#e8d0ff', '#ffffff', '#b890f0'),
                separate=False)

    def post(a):
        blend(a, 2, 10, '#c8a0ff', 200)
        blend(a, 1, 8, '#c8a0ff', 140)
        twinkle(a, 13, 8, '#ffffff', '#d8b0ff')

    return icon(d, post)


def ic_gem():
    """Premium faceted gem (brilliant cut, teal/cyan)."""
    def d(cv):
        body = cv.mask().poly([(5, 3), (10, 3), (14, 7), (7.5, 14.5), (1, 7)])
        cv.part(body, Pal('#28c8c8', '#a8fff0', '#0e7a8a'))
        # crown facets
        cv.part(cv.mask().poly([(5.5, 3.5), (9.5, 3.5), (10, 6), (5, 6)]), Pal('#8af8ec'), flat=True)
        cv.part(cv.mask().poly([(2, 7), (5, 4), (5, 6)]), Pal('#c8fff8'), flat=True)
        cv.part(cv.mask().poly([(13, 7), (10, 4), (10, 6)]), Pal('#1aa0b0'), flat=True)
        # girdle
        cv.part(cv.mask().rect(2, 7, 13, 7), Pal('#e0fffa'), flat=True)
        # pavilion facets
        cv.part(cv.mask().poly([(3, 8), (6, 8), (7.5, 13.5)]), Pal('#5ae8e0'), flat=True)
        cv.part(cv.mask().poly([(9, 8), (12, 8), (7.5, 13.5)]), Pal('#107a90'), flat=True)
        cv.part(cv.mask().poly([(6.5, 8), (8.5, 8), (7.5, 13)]), Pal('#1ab4bc'), flat=True)

    def post(a):
        put(a, 6, 4, '#ffffff')
        put(a, 7, 4, '#ffffff')
        put(a, 4, 8, '#ffffff')
        twinkle(a, 13, 2, '#ffffff', '#c8fff8')

    return icon(d, post)


def ic_energy():
    def d(cv):
        cv.part(cv.mask().poly([(10, 0.5), (3, 9), (7.5, 9), (5, 15), (13, 6), (8.5, 6), (12, 0.5)]),
                Pal('#ffb02a', '#fff4b0', '#d0501a'))
        cv.part(cv.mask().line(10.5, 1.5, 6, 8, 1), Pal('#fff4b0'), flat=True)
        cv.part(cv.mask().line(10, 7, 6.5, 12.5, 1), Pal('#fff4b0'), flat=True)

    return icon(d)


def _chest_body(cv):
    cv.part(cv.mask().rect(2, 8, 13, 14), WOOD)
    cv.part(cv.mask().rect(2, 8, 13, 8), Pal('#6a4420'), flat=True)
    cv.part(cv.mask().rect(4, 8, 4, 14).rect(11, 8, 11, 14), IRON, separate=False)


def ic_chest(open_=False):
    def d(cv):
        if not open_:
            lid = cv.mask().rect(2, 4, 13, 8)
            lid.ellipse(7.5, 4.5, 5.5, 2.5)
            cv.part(lid, WOOD)
            cv.part(cv.mask().rect(4, 2, 4, 8).rect(11, 2, 11, 8), IRON, separate=False)
            _chest_body(cv)
            cv.part(cv.mask().rect(6, 7, 9, 10), GOLD)
            cv.dot(7, 9, C('#3a2408'))
            cv.dot(8, 9, C('#3a2408'))
        else:
            cv.part(cv.mask().poly([(3, 6), (4, 1), (12, 1), (12, 6)]), Pal('#7a5028', '#a8743a', '#4a2c14'))
            cv.part(cv.mask().rect(4, 1, 4, 6).rect(11, 1, 11, 6), IRON, separate=False)
            cv.part(cv.mask().rect(2, 6, 13, 8), Pal('#3a2010'), flat=True)
            cv.part(cv.mask().ellipse(7.5, 7, 5, 2), Pal('#f8c830', '#fff6c8', '#c88a18'), separate=False)
            _chest_body(cv)
            cv.part(cv.mask().rect(6, 9, 9, 11), GOLD)

    def post(a):
        if open_:
            for (x, y) in ((6, 5), (9, 4)):
                put(a, x, y, '#fff6c8')
            twinkle(a, 7, 2, '#ffffff', '#fff0a0')
            twinkle(a, 14, 3, '#ffffff', '#fff0a0')
            twinkle(a, 1, 3, '#ffffff', '#fff0a0')

    return icon(d, post)


def ic_scroll_check():
    def d(cv):
        cv.part(cv.mask().rect(3, 2, 12, 13), PARCH)
        cv.part(cv.mask().rect(2, 1, 13, 3), Pal('#c8a878', '#f0dcb0', '#8a6a44'))
        cv.part(cv.mask().rect(2, 12, 13, 14), Pal('#c8a878', '#f0dcb0', '#8a6a44'))
        for y in (5, 7):
            for x in range(5, 11):
                cv.dot(x, y, C('#9a8460'))
        cv.part(cv.mask().line(4.5, 9, 7, 11.5, 2).line(7, 11.5, 13, 5, 2), UP_GREEN)

    return icon(d)


def ic_tower():
    """Dark crenellated tower silhouette with ember-lit windows."""
    def d(cv):
        stone = Pal('#4a4454', '#6a6478', '#2e2a36')
        cv.part(cv.mask().poly([(4, 15), (5, 5), (11, 5), (12, 15)]), stone)
        top = cv.mask().rect(3, 2, 12, 5)
        top.subtract(cv.mask().rect(5, 2, 5, 2)).subtract(cv.mask().rect(8, 2, 8, 2)).subtract(cv.mask().rect(11, 2, 11, 2))
        cv.part(top, stone)
        cv.part(cv.mask().rect(7, 7, 8, 9), Pal('#ffb04a', '#fff0a0', '#e0601c'), shade=False)
        cv.part(cv.mask().rect(7, 12, 8, 14), Pal('#1e1a24'), flat=True)
        cv.dot(6, 10, C('#2e2a36'))
        cv.dot(9, 11, C('#2e2a36'))

    return icon(d)


def ic_nav_tower():
    """Tall watch tower with a slate spire (distinct from nav_home's red-roof house)."""
    def d(cv):
        stone = Pal('#9a92a4', '#d0cad8', '#5e586a')
        cv.part(cv.mask().rect(5, 6, 10, 14), stone)
        cv.part(cv.mask().rect(4, 5, 11, 7), Pal('#7a7288', '#aaa2b8', '#4e4858'))
        cv.part(cv.mask().poly([(3.5, 5.5), (7.5, 0.5), (11.5, 5.5)]), Pal('#4a62c0', '#8aa8f0', '#26347a'))
        cv.part(cv.mask().rect(7, 8, 8, 9), Pal('#ffb04a', '#fff0a0', '#e0601c'), shade=False)
        cv.part(cv.mask().rect(7, 12, 8, 14), Pal('#5a3622'), flat=True)
        cv.dot(7, 11, C('#5a3622'))
        cv.dot(8, 11, C('#5a3622'))

    def post(a):
        put(a, 7, 1, '#ffd35a')

    return icon(d, post)


def ic_codex():
    """Closed leather tome with a gold flame crest."""
    def d(cv):
        cv.part(cv.mask().rect(11, 2, 13, 14), PARCH)
        cv.part(cv.mask().rect(2, 1, 12, 14), Pal('#8a2a2a', '#c04a3a', '#5a1a1a'))
        cv.part(cv.mask().rect(2, 1, 3, 14), Pal('#5a1a1a', '#7a2424', '#3a0e0e'), separate=False)
        crest = cv.mask().poly([(5, 4), (11, 4), (11, 8), (8, 11.5), (5, 8)])
        cv.part(crest, GOLD, separate=False)
        cv.part(cv.mask().poly([(8, 5), (9.5, 7.5), (8, 9.5), (6.5, 7.5)]), Pal('#e0342a', '#ff8a6a', '#8a1a14'),
                separate=False)
        for (x, y) in ((11, 1), (11, 14)):
            cv.dot(x, y, C('#e0a83a'))

    return icon(d)


def ic_nav_codex():
    """Open book with a crest page and ribbon."""
    def d(cv):
        cv.part(cv.mask().poly([(1, 4), (7.5, 5), (14, 4), (14, 13), (7.5, 14), (1, 13)]),
                Pal('#8a2a2a', '#c04a3a', '#5a1a1a'))
        cv.part(cv.mask().poly([(2, 3), (7, 4), (7, 12), (2, 11)]), PARCH)
        cv.part(cv.mask().poly([(8, 4), (13, 3), (13, 11), (8, 12)]), PARCH)
        for y in (6, 8, 10):
            for x in (3, 4, 5):
                cv.dot(x, y, C('#9a8460'))
        cv.part(cv.mask().poly([(9, 5), (12, 5), (12, 8), (10.5, 9.5), (9, 8)]), Pal('#d0342a', '#ff7a5a', '#7a1a14'),
                separate=False)
        cv.part(cv.mask().rect(7, 1, 8, 5), Pal('#e0a83a', '#fff0b0', '#a8741e'))

    def post(a):
        put(a, 10, 6, '#ffd35a')
        put(a, 11, 6, '#ffd35a')

    return icon(d, post)


def ic_nav_missions():
    """Clip board with a big check."""
    def d(cv):
        cv.part(cv.mask().rect(2, 2, 13, 14), WOOD)
        cv.part(cv.mask().rect(3, 3, 12, 13), PARCH)
        cv.part(cv.mask().rect(5, 1, 10, 3), Pal('#c0c8d4', '#f0f4f8', '#7a828c'))
        for y in (5, 7):
            for x in range(5, 11):
                cv.dot(x, y, C('#9a8460'))
        cv.part(cv.mask().line(4.5, 10, 6.5, 12, 2).line(6.5, 12, 12, 7, 2), UP_GREEN)

    return icon(d)


def ic_profile():
    """Neutral bust silhouette (avatar placeholder)."""
    def d(cv):
        body = cv.mask().ellipse(7.5, 15, 6.4, 5.2)
        body.m &= cv.mask().rect(0, 0, 15, 14).m
        cv.part(body, Pal('#4a6a98', '#8aaad8', '#2a4270'))
        cv.part(cv.mask().ellipse(7.5, 5.6, 3.7, 3.9), Pal('#7a9ac8', '#c0d8f0', '#4a6a98'))

    return icon(d)


def _arc_mask(cv, cx, cy, r0, r1, a0, a1):
    m = cv.mask()
    for y in range(16):
        for x in range(16):
            dx, dy = x - cx, y - cy
            r = math.hypot(dx, dy)
            if r0 <= r <= r1:
                ang = math.degrees(math.atan2(dy, dx)) % 360
                if (a0 <= ang <= a1) if a0 <= a1 else (ang >= a0 or ang <= a1):
                    m.m[y, x] = True
    return m


def ic_auto():
    """Two chasing arrows forming a loop (clockwise): heads point down on the right, up on the left."""
    def d(cv):
        pal = Pal('#48c0e8', '#c0f4ff', '#1e70b0')
        top = _arc_mask(cv, 7.5, 7.5, 4.0, 6.1, 195, 318)
        top.poly([(9.5, 5.5), (15.2, 5.5), (12.4, 9.2)])
        cv.part(top, pal)
        bot = _arc_mask(cv, 7.5, 7.5, 4.0, 6.1, 15, 138)
        bot.poly([(5.5, 9.5), (-0.2, 9.5), (2.6, 5.8)])
        cv.part(bot, pal)

    return icon(d)


def ic_speed():
    def d(cv):
        pal = Pal('#ffb03a', '#fff0a0', '#e0601c')
        cv.part(cv.mask().poly([(1, 2), (4.5, 2), (9, 7.5), (4.5, 13), (1, 13), (5.5, 7.5)]), pal)
        cv.part(cv.mask().poly([(6.5, 2), (10, 2), (14.5, 7.5), (10, 13), (6.5, 13), (11, 7.5)]), pal)

    return icon(d)


def ic_warning():
    def d(cv):
        cv.part(cv.mask().poly([(7.5, 0.5), (15, 14), (0, 14)]), Pal('#e0342a', '#ff7a5a', '#8a1a14'))
        cv.part(cv.mask().poly([(7.5, 3.5), (12.5, 12.5), (2.5, 12.5)]), Pal('#ffc83a', '#fff4b0', '#e08a1c'),
                separate=False)
        cv.part(cv.mask().rect(7, 5, 8, 9), Pal('#3a1208'), flat=True)
        cv.part(cv.mask().rect(7, 11, 8, 11), Pal('#3a1208'), flat=True)

    return icon(d)


def ic_elite():
    """Small gold crown resting on a green laurel sprig pair."""
    def d(cv):
        leaf = Pal('#5aa832', '#a8e070', '#2f6a1c')
        for side in (-1, 1):
            stem = cv.mask().line(7.5 + side * 1, 14, 7.5 + side * 5.5, 8.5, 1)
            for (t, lx, ly) in ((0.2, 2.2, 12.8), (0.5, 4.2, 11.4), (0.8, 5.8, 9.4)):
                stem.ellipse(7.5 + side * lx, ly, 1.3, 1.0)
            stem.ellipse(7.5 + side * 6.2, 7.6, 0.9, 1.4)
            cv.part(stem, leaf)
        crown = cv.mask().poly([(3.5, 9.5), (3.5, 3.5), (5.5, 5.8), (7.5, 1.8), (9.5, 5.8), (11.5, 3.5), (11.5, 9.5)])
        cv.part(crown, Pal('#f8c830', '#fff0a0', '#c88a18'))
        cv.part(cv.mask().rect(4, 8, 11, 9), Pal('#c88a18', '#f8c830', '#8a5a10'), separate=False)

    def post(a):
        put(a, 7, 6, '#e8342a')
        put(a, 8, 6, '#e8342a')
        put(a, 7, 5, '#ff9a8a')
        put(a, 5, 8, '#48c0e8')
        put(a, 10, 8, '#48c0e8')
        put(a, 7, 8, '#e8342a')

    return icon(d, post)


def ic_heart(pal, hl='#ffffff'):
    def d(cv):
        m = cv.mask().ellipse(4.8, 5.5, 3.6, 3.6).ellipse(10.2, 5.5, 3.6, 3.6)
        m.poly([(1.3, 6.5), (13.7, 6.5), (7.5, 14)])
        cv.part(m, pal)

    def post(a):
        put(a, 4, 4, hl)
        put(a, 3, 5, hl)

    return icon(d, post)


def ic_world():
    """Brass compass."""
    def d(cv):
        cv.part(cv.mask().ellipse(7.5, 7.5, 6.8, 6.8), Pal('#c8923a', '#f8d078', '#8a5a1e'))
        cv.part(cv.mask().ellipse(7.5, 7.5, 5, 5), Pal('#efe0b8', '#fff8e8', '#c0ac80'), separate=False)
        cv.part(cv.mask().poly([(7.5, 2.5), (9, 7.5), (6, 7.5)]), Pal('#e0342a', '#ff8a6a', '#8a1a14'),
                separate=False)
        cv.part(cv.mask().poly([(7.5, 12.5), (9, 7.5), (6, 7.5)]), Pal('#6a7488', '#a8b0c0', '#3a4250'),
                separate=False)
        cv.part(cv.mask().rect(0, 7, 1, 7).rect(14, 7, 15, 7), Pal('#8a5a1e'), flat=True, separate=False)

    def post(a):
        put(a, 7, 7, '#fff0b0')
        put(a, 8, 8, '#fff0b0')
        for (x, y) in ((3, 7), (12, 7), (7, 12)):
            pass

    return icon(d, post)


def ic_login():
    """Calendar page with a highlighted day."""
    def d(cv):
        cv.part(cv.mask().rect(1, 3, 14, 14), Pal('#f4ecd8', '#ffffff', '#b8a888'))
        cv.part(cv.mask().rect(1, 3, 14, 6), Pal('#d8342a', '#ff7a5a', '#8a1a14'))
        for x in (4, 11):
            cv.part(cv.mask().rect(x, 1, x, 4), Pal('#8a8690', '#c0bcc4', '#3a3640'), shade=False)
        for gy in (8, 11):
            for gx in (3, 6, 9, 12):
                if (gx, gy) == (9, 11):
                    continue
                cv.dot(gx, gy, C('#b0a488'))
                cv.dot(gx + 1, gy, C('#b0a488'))
        cv.part(cv.mask().rect(8, 10, 11, 12), Pal('#f8b030', '#fff0a0', '#c07a18'), separate=False)

    return icon(d)


def _star_pts(r_out=7.2, r_in=3.1, cx=7.5, cy=8.2):
    pts = []
    for i in range(10):
        r = r_out if i % 2 == 0 else r_in
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    return pts


def ic_star_obj(filled=True):
    def d(cv):
        if filled:
            cv.part(cv.mask().poly(_star_pts()), Pal('#f8c030', '#fff0a0', '#c07a18'))
            cv.part(cv.mask().poly(_star_pts(3.8, 1.7)), Pal('#ffe070', '#fff8d0', '#f0b030'), separate=False)
        else:
            cv.part(cv.mask().poly(_star_pts()), Pal('#5a5468', '#7a748a', '#3a3446'))
            cv.part(cv.mask().poly(_star_pts(4.6, 2.0)), Pal('#1c1822'), flat=True, separate=False)

    def post(a):
        if filled:
            put(a, 6, 5, '#ffffff')

    return icon(d, post)


# ---------------------------------------------------------------- status icons
def _mini_sword(cv):
    cv.part(cv.mask().line(3, 11, 9.5, 3, 2), STEEL)
    cv.part(cv.mask().line(1.5, 8.5, 5.5, 12.5, 1), Pal('#c49a3a', '#f0cd6a', '#8a6a24'), shade=False)
    cv.part(cv.mask().line(1.5, 13.5, 3, 12, 2), Pal('#5a3622'))


def _mini_shield(cv):
    cv.part(cv.mask().poly([(2, 2), (10, 2), (10, 7.5), (6, 12.5), (2, 7.5)]), Pal('#6a8ab0', '#a8c4e0', '#3e5a80'))
    cv.part(cv.mask().poly([(4.5, 4), (7.5, 4), (7.5, 7.5), (6, 9), (4.5, 7.5)]), Pal('#c8d4e4', '#ffffff', '#8e9cb0'),
            separate=False)


def _arrow_up(cv, pal):
    cv.part(cv.mask().poly([(12, 5), (15, 9), (13, 9), (13, 14), (11, 14), (11, 9), (9, 9)]), pal)


def _arrow_down(cv, pal):
    cv.part(cv.mask().poly([(12, 14), (15, 10), (13, 10), (13, 5), (11, 5), (11, 10), (9, 10)]), pal)


def st_atk_up(cv):
    _mini_sword(cv)
    _arrow_up(cv, UP_GREEN)


def st_atk_down(cv):
    _mini_sword(cv)
    _arrow_down(cv, DOWN_RED)


def st_def_down(cv):
    _mini_shield(cv)
    _arrow_down(cv, DOWN_RED)


def st_rec_up(cv):
    cv.part(cv.mask().rect(4, 2, 7, 12).rect(1, 5, 10, 9), Pal('#ff6a9a', '#ffc0d8', '#b02a5a'))
    _arrow_up(cv, UP_GREEN)


def st_regen():
    def d(cv):
        m = cv.mask().ellipse(4.5, 7, 3.4, 3.4).ellipse(9.5, 7, 3.4, 3.4)
        m.poly([(1.2, 8), (12.8, 8), (7, 14.5)])
        cv.part(m, Pal('#4ac05a', '#b0f090', '#1e7a34'))
        cv.part(cv.mask().rect(12, 1, 13, 6).rect(10, 3, 15, 4), Pal('#ffffff', '#ffffff', '#b0e8c0'))

    def post(a):
        put(a, 4, 5, '#e8ffe0')
        put(a, 3, 6, '#e8ffe0')

    return icon(d, post)


def st_shield():
    """Cyan hexagonal barrier."""
    def d(cv):
        hexa = [(7.5 + math.cos(math.radians(a)) * 7, 7.5 + math.sin(math.radians(a)) * 7.2) for a in range(-90, 270, 60)]
        cv.part(cv.mask().poly(hexa), Pal('#3ab0e8', '#b8f4ff', '#1a5aa8'))
        inner = [(7.5 + math.cos(math.radians(a)) * 4.2, 7.5 + math.sin(math.radians(a)) * 4.4) for a in range(-90, 270, 60)]
        cv.part(cv.mask().poly(inner), Pal('#1e78c0', '#5ac8f0', '#145090'), separate=False)
        cv.part(cv.mask().poly([(7.5 + math.cos(math.radians(a)) * 2, 7.5 + math.sin(math.radians(a)) * 2.1)
                                for a in range(-90, 270, 60)]), Pal('#b8f4ff', '#ffffff', '#6ad0f0'), separate=False)

    def post(a):
        put(a, 5, 2, '#ffffff')
        put(a, 4, 3, '#ffffff')

    return icon(d, post)


def st_poison():
    def d(cv):
        m = cv.mask().ellipse(7, 9.5, 5, 4.8)
        m.poly([(7, 1), (11.3, 8), (2.7, 8)])
        cv.part(m, Pal('#9a3ad0', '#d890ff', '#58187a'))
        cv.part(cv.mask().ellipse(12.5, 4, 1.8, 1.8), Pal('#8ae04a', '#d0ff9a', '#3a8a1e'))
        cv.part(cv.mask().ellipse(7.5, 10.5, 2.2, 2), Pal('#8ae04a', '#d0ff9a', '#3a8a1e'), separate=False)

    def post(a):
        put(a, 4, 8, '#f0d8ff')
        put(a, 4, 9, '#f0d8ff')
        put(a, 7, 10, '#e8ffd0')

    return icon(d, post)


def st_charge():
    """Boss charging: crimson spiky burst with a white-hot bolt."""
    def d(cv):
        pts = []
        for i in range(16):
            r = 7.6 if i % 2 == 0 else 4.4
            a = i * math.pi / 8 + math.pi / 16
            pts.append((7.5 + math.cos(a) * r, 7.5 + math.sin(a) * r))
        cv.part(cv.mask().poly(pts), Pal('#d02838', '#ff7a6a', '#6a0a18'))
        cv.part(cv.mask().poly([(9, 2.5), (4.5, 8.5), (7.5, 8.5), (6, 12.5), (11, 6.5), (8, 6.5), (10, 2.5)]),
                Pal('#ffe070', '#ffffff', '#f0a020'), separate=False)

    return icon(d)


ICONS = {
    # materials
    'ember_fragment': lambda: ic_fragment(FIRE),
    'flame_core': lambda: ic_core(FIRE),
    'infernal_crystal': lambda: ic_crystal(INFERNAL),
    'tide_fragment': lambda: ic_fragment(WATER),
    'current_core': lambda: ic_core(WATER),
    'abyss_crystal': lambda: ic_crystal(ABYSS),
    'sprout_fragment': lambda: ic_fragment(NATURE),
    'verdant_core': lambda: ic_core(NATURE),
    'ancient_seed': ic_ancient_seed,
    'prism_shard': ic_prism_shard,
    # training
    'ember_wisp': lambda: ic_wisp(FIRE, 'fire'),
    'tide_wisp': lambda: ic_wisp(WATER, 'water'),
    'verdant_wisp': lambda: ic_wisp(NATURE, 'nature'),
    'radiant_wisp': lambda: ic_wisp(RADIANT, 'radiant', big=True),
    # other
    'spark_sigil': ic_spark_sigil,
    'soul_shard': ic_soul_shard,
    'gem': ic_gem,
    'energy': ic_energy,
    'chest': lambda: ic_chest(False),
    'chest_open': lambda: ic_chest(True),
    'missions': ic_scroll_check,
    'tower': ic_tower,
    'codex': ic_codex,
    'profile': ic_profile,
    'auto': ic_auto,
    'speed': ic_speed,
    'warning': ic_warning,
    'elite': ic_elite,
    'fav': lambda: ic_heart(Pal('#e8385a', '#ff9ab0', '#a01838')),
    'world': ic_world,
    'login': ic_login,
    'star_obj': lambda: ic_star_obj(True),
    'star_obj_empty': lambda: ic_star_obj(False),
    # nav
    'nav_tower': ic_nav_tower,
    'nav_missions': ic_nav_missions,
    'nav_codex': ic_nav_codex,
    # status
    'status_atk_up': lambda: icon(st_atk_up),
    'status_atk_down': lambda: icon(st_atk_down),
    'status_def_down': lambda: icon(st_def_down),
    'status_rec_up': lambda: icon(st_rec_up),
    'status_regen': st_regen,
    'status_shield': st_shield,
    'status_poison': st_poison,
    'status_charge': st_charge,
}


# =================================================================== EFFECTS
def blank(w, h):
    return np.zeros((h, w, 4), dtype=np.uint8)


def quant(v, x, y, n):
    """Ordered-dither quantisation of v in [0,1] into n levels (-1 = empty)."""
    t = v * n + BAYER[y % 4, x % 4] - 0.5
    return int(math.floor(t))


def ember_bolt(frames=4, size=16):
    cols = [C('#7a1c14'), C('#c8361a'), C('#ff7a22'), C('#ffc14a'), C('#fff3a8'), C('#ffffff')]
    out = []
    for f in range(frames):
        a = blank(size, size)
        ph = f * math.pi / 2
        hx, hy = 11.0, 7.5
        for y in range(size):
            for x in range(size):
                dx, dy = x - hx, y - hy
                head = 1 - math.hypot(dx * (0.8 if dx > 0 else 1.0), dy * 1.1) / 4.2
                v = head * 1.5
                if x < hx:
                    along = (hx - x) / 11.0
                    w = 3.3 * (1 - along) ** 0.9 + 0.3
                    wave = math.sin(along * 7 + ph) * 1.3 * along
                    tail = 1 - abs(dy - wave) / w - along * 0.55
                    v = max(v, tail)
                if v <= 0:
                    continue
                k = quant(min(v, 1.0), x, y, 5)
                if k < 0:
                    continue
                a[y, x] = cols[min(k, 5)]
        rng = random.Random(f)
        for i in range(3):
            put(a, 1 + ((f * 3 + i * 5) % 6), hy + rng.choice((-3, -2, 2, 3)), cols[3 if i % 2 else 2])
        out.append(Image.fromarray(a, 'RGBA'))
    return out


def arrow_proj(frames=4):
    out = []
    for f in range(frames):
        cv = Canvas(16, 16)
        wob = (0, 1, 0, -1)[f]
        cv.part(cv.mask().line(2, 8, 11, 8, 1), Pal('#b08050', '#d8b078', '#6a4a28'))
        leaf = Pal('#6fb33a', '#a9dd62', '#3f7a22')
        cv.part(cv.mask().poly([(1, 8), (2.5, 5 + wob * 0.5), (6, 6), (4.5, 7.5)]), leaf)
        cv.part(cv.mask().poly([(1, 8), (2.5, 11 + wob * 0.5), (6, 10), (4.5, 8.5)]), leaf)
        cv.part(cv.mask().poly([(11, 6), (15, 8), (11, 10)]), STEEL)
        cv.outline()
        a = np.array(cv.image())
        for i in range(2):
            x0 = (f * 2 + i * 3) % 4
            blend(a, x0, 5 + i * 6, '#ffffff', 150)
            blend(a, x0 + 1, 5 + i * 6, '#ffffff', 90)
        out.append(Image.fromarray(a, 'RGBA'))
    return out


def tide_orb(frames=6, size=16):
    out = []
    cx, cy, R = 8.5, 7.5, 5.2
    for f in range(frames):
        a = blank(size, size)
        ph = f * 2 * math.pi / frames
        for y in range(size):
            for x in range(size):
                dx, dy = x - cx, y - cy
                r = math.hypot(dx, dy)
                if r > R:
                    continue
                th = math.atan2(dy, dx)
                swirl = math.cos(2 * th - r * 1.1 + ph)
                if r > R - 1:
                    col = '#1a5a9a'
                elif swirl > 0.55 and r > 1.2:
                    col = '#c8f6ff' if r < 3.2 else '#7ae0f0'
                elif swirl < -0.4:
                    col = '#1f78c0'
                else:
                    col = '#3aa8e0'
                put(a, x, y, col)
        put(a, cx - 2, cy - 3, '#ffffff')
        put(a, cx - 3, cy - 2, '#ffffff')
        for k in range(2):
            ang = ph / 2 + k * math.pi
            put(a, cx + math.cos(ang) * 7, cy + math.sin(ang) * 4, '#8ae8ff')
        for i in range(3):
            blend(a, cx - 6 - i * 1.5, cy + math.sin(ph + i) * 1.5, '#7ae0f0', 200 - i * 50)
        out.append(Image.fromarray(a, 'RGBA'))
    return out


def _petal(a, cx, cy, ang, length=2.6, width=1.3, cols=('#ffd8ec', '#ff9ac8', '#d04a8a'), alpha=255):
    ca, sa = math.cos(ang), math.sin(ang)
    for y in range(int(cy - 4), int(cy + 5)):
        for x in range(int(cx - 4), int(cx + 5)):
            dx, dy = x - cx, y - cy
            u = dx * ca + dy * sa
            v = -dx * sa + dy * ca
            q = (u / length) ** 2 + (v / width) ** 2
            if q <= 1:
                col = cols[0] if (u < -length * 0.2 and q < 0.5) else (cols[1] if q < 0.75 else cols[2])
                if alpha >= 255:
                    put(a, x, y, col)
                else:
                    blend(a, x, y, col, alpha)


def petal_bolt(frames=6, size=16):
    out = []
    cx, cy = 9.5, 7.5
    for f in range(frames):
        a = blank(size, size)
        rot = f * math.pi / 6
        for k in range(4):
            ang = rot + k * math.pi / 2
            _petal(a, cx + math.cos(ang) * 2.8, cy + math.sin(ang) * 2.8, ang)
        put(a, cx, cy, '#fff0a0')
        put(a, cx - 1 + 1, cy - 1 + 1, '#fff0a0')
        for i in range(3):
            x = 3 - i * 1.2 + ((f + i) % 3) * 0.6
            y = cy + math.sin(f * math.pi / 3 + i * 2.1) * 3
            blend(a, x, y, '#ff9ac8', 230 - i * 60)
        out.append(Image.fromarray(a, 'RGBA'))
    return out


def _band_color(bands, i):
    return bands[min(i, len(bands) - 1)]


def axe_cleave(frames=6, size=48):
    """Heavy vertical cleave: a thick, nearly straight crescent chopping top to bottom."""
    bands = [C('#ffffff'), C('#fff0b0'), C('#ffc14a'), C('#ff7a22'), C('#d8391a'), C('#8a1c10')]
    cx, cy, R = -22.0, 23.5, 47.0
    amax = 31.0
    heads = [-12, 14, amax, amax, amax, amax]
    widths = [4, 8, 11, 8, 4, 2]
    out = []
    rng = random.Random(4)
    shards = [(i / 14 * 2 * math.pi + rng.uniform(-0.2, 0.2), rng.uniform(4, 8), rng.randint(0, 2)) for i in range(14)]
    for f in range(frames):
        a = blank(size, size)
        head = heads[f]
        tail = -amax if f < 3 else -amax + (f - 2) * 18
        W = widths[f]
        steps = 260
        for i in range(steps + 1):
            t = i / steps
            angd = tail + (head - tail) * t
            if angd < -amax or angd > amax:
                continue
            ang = math.radians(angd)
            k = t ** 0.6 if f < 3 else 0.35 + 0.65 * math.sin(math.pi * t)
            wid = max(1, int(round(W * k)))
            for w in range(wid):
                rr = R - w
                col = _band_color(bands, int(w * len(bands) / max(W, 1)) if f < 3 else w + 2)
                x = cx + math.cos(ang) * rr
                y = cy + math.sin(ang) * rr
                if f >= 4 and (int(x) + int(y)) % 2:
                    continue
                put(a, x, y, col)
        # impact flash + flying shards
        ix, iy = cx + R - 2, cy
        if f == 2:
            for d in range(-8, 9):
                put(a, ix + d, iy, bands[0] if abs(d) < 5 else bands[2])
            for d in range(-3, 4):
                put(a, ix + d, iy - 1, bands[1])
                put(a, ix + d, iy + 1, bands[1])
        if f >= 3:
            for (ang, sp, ci) in shards:
                dist = sp * (f - 2)
                x = ix + math.cos(ang) * dist
                y = iy + math.sin(ang) * dist * 0.75
                col = [bands[1], bands[2], bands[3]][ci]
                if f == 5 and ci:
                    continue
                put(a, x, y, col)
                put(a, x - 1, y, bands[4])
        out.append(Image.fromarray(a, 'RGBA'))
    return out


def spear_thrust(frames=5, w=48, h=32):
    core, mid, edge, dark = C('#ffffff'), C('#d8ecff'), C('#8ab4e8'), C('#3a5a98')
    tips = [18, 40, 43, 43, 43]
    tails = [2, 6, 18, 28, 36]
    out = []
    cy = 16
    for f in range(frames):
        a = blank(w, h)
        tip, tail = tips[f], tails[f]
        if f <= 2:
            for x in range(tail, tip + 1):
                t = (x - tail) / max(1, tip - tail)
                half = 0 if t < 0.35 else (1 if t < 0.8 else 2)
                if x > tip - 3:
                    half = max(0, (tip - x) // 1 - 0)
                    half = min(half, 2)
                for dy in range(-half, half + 1):
                    col = core if abs(dy) == 0 else (mid if abs(dy) == 1 else edge)
                    put(a, x, cy + dy, col)
                if half >= 2:
                    put(a, x, cy - 3, dark)
                    put(a, x, cy + 3, dark)
            for (ly, x0, ln) in ((cy - 6, tail + 4, 10), (cy + 6, tail + 8, 8), (cy - 9, tail + 12, 5)):
                for x in range(x0, min(tip - 4, x0 + ln)):
                    put(a, x, ly, edge)
        else:
            for (ly, x0, ln) in ((cy, tail, 12), (cy - 3, tail + 3, 8), (cy + 3, tail - 2, 9)):
                for x in range(x0, min(w, x0 + ln)):
                    if f == 4 and x % 2:
                        continue
                    put(a, x, ly, mid if ly == cy else edge)
        # impact
        if f >= 2:
            ix = 43
            rad = [0, 0, 0, 5, 8][f]
            if f == 2:
                for d in range(1, 6):
                    for (dx, dy) in ((1, 0), (0, 1), (0, -1), (-1, 0)):
                        put(a, ix + dx * d, cy + dy * d, core if d < 3 else mid)
                for (dx, dy) in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                    for d in (1, 2, 3):
                        put(a, ix + dx * d, cy + dy * d, mid if d < 3 else edge)
            else:
                n = 28
                for i in range(n):
                    ang = i / n * 2 * math.pi
                    if f == 4 and i % 2:
                        continue
                    put(a, ix + math.cos(ang) * rad * 0.6, cy + math.sin(ang) * rad, mid if f == 3 else edge)
        out.append(Image.fromarray(a, 'RGBA'))
    return out


def dagger_flurry(frames=7, size=40):
    core, mid, edge = C('#ffffff'), C('#e0d8ff'), C('#9a8ae0')
    slashes = [(15, 13, 0), (26, 22, 1), (13, 26, 2), (27, 11, 3)]
    rng = random.Random(7)
    out = []
    for f in range(frames):
        a = blank(size, size)
        for (sx, sy, start) in slashes:
            age = f - start
            if age < 0 or age > 2:
                continue
            L = 7 if age < 2 else 5
            for diag, ok in ((1, True), (-1, age >= 1)):
                if not ok:
                    continue
                for s in range(-L, L + 1):
                    x = sx + s
                    y = sy + s * diag
                    frac = abs(s) / L
                    if age == 2 and (s % 2):
                        continue
                    col = core if frac < 0.45 and age < 2 else (mid if frac < 0.8 else edge)
                    put(a, x, y, col)
                    if age == 0 and frac < 0.6:
                        put(a, x + 1, y, mid)
            if age == 1:
                for (dx, dy) in ((0, -3), (0, 3), (-3, 0), (3, 0)):
                    put(a, sx + dx, sy + dy, core)
        if f >= 3:
            for i in range(10):
                ang = rng.uniform(0, 2 * math.pi)
                d = rng.uniform(6, 16) + (f - 3) * 1.5
                if f == 6 and i % 2:
                    continue
                put(a, 20 + math.cos(ang) * d, 19 + math.sin(ang) * d, mid if i % 3 else edge)
        out.append(Image.fromarray(a, 'RGBA'))
    return out


def petal_burst(frames=7, size=40, seed=12):
    rng = random.Random(seed)
    parts = []
    for i in range(16):
        ang = i / 16 * 2 * math.pi + rng.uniform(-0.2, 0.2)
        parts.append((ang, rng.uniform(0.55, 1.0), rng.uniform(0, math.pi), i % 3 == 0, rng.uniform(-0.6, 0.6)))
    pink = ('#ffe0f0', '#ff9ac8', '#d04a8a')
    green = ('#d8ffa8', '#8ad04a', '#3f7a22')
    out = []
    c = size / 2 - 0.5
    for f in range(frames):
        a = blank(size, size)
        if f <= 1:
            rad = 4 + f * 5
            for i in range(48):
                ang = i / 48 * 2 * math.pi
                if f == 1 and i % 2:
                    continue
                put(a, c + math.cos(ang) * rad, c + math.sin(ang) * rad * 0.9, '#e8fff0' if f == 0 else '#9af0c8')
            if f == 0:
                for d in range(-2, 3):
                    put(a, c + d, c, '#ffffff')
                    put(a, c, c + d, '#ffffff')
        for (ang, sp, spin, is_leaf, drift) in parts:
            dist = 15 * sp * (1 - math.exp(-(f + 0.6) * 0.65))
            x = c + math.cos(ang) * dist + drift * f
            y = c + math.sin(ang) * dist * 0.85 - max(0, f - 2) * 1.6
            alpha = 255 if f < frames - 2 else (210 if f == frames - 2 else 140)
            _petal(a, x, y, spin + f * 0.7, 2.2, 1.1, green if is_leaf else pink, alpha)
        if 2 <= f <= 5:
            for k in range(4):
                sx = c + math.cos(k * 1.9 + f) * (8 + k * 2)
                sy = c + math.sin(k * 1.9 + f) * (6 + k) - f * 2
                twinkle(a, sx, sy, '#ffffff', '#b0f8d8')
        out.append(Image.fromarray(a, 'RGBA'))
    return out


def _hex_norm(x, y, R):
    """Distance of (x, y) to the centre of its pointy-top hex cell (0 centre .. 1 edge)."""
    q = (math.sqrt(3) / 3 * x - y / 3) / R
    r = (2 / 3 * y) / R
    s = -q - r
    rq, rr, rs = round(q), round(r), round(s)
    dq, dr, ds = abs(rq - q), abs(rr - r), abs(rs - s)
    if dq > dr and dq > ds:
        rq = -rr - rs
    elif dr > ds:
        rr = -rq - rs
    hx = R * math.sqrt(3) * (rq + rr / 2)
    hy = R * 1.5 * rr
    dx, dy = abs(x - hx), abs(y - hy)
    ap = R * math.sqrt(3) / 2
    return max(dx, dx / 2 + dy * math.sqrt(3) / 2) / ap


def shield_flash(frames=6, w=40, h=48):
    rim_hi, rim, cell, cell_dim, fillc = C('#ffffff'), C('#b8f4ff'), C('#6ad8ff'), C('#2a88d0'), C('#8ae8ff')
    reveal = [0.35, 0.8, 1.2, 1.2, 1.2, 1.2]
    band = [None, None, -10, 8, 26, None]
    out = []
    cx, cy, rx, ry = 19.5, 23.5, 16.5, 21.5
    for f in range(frames):
        a = blank(w, h)
        for y in range(h):
            for x in range(w):
                dx, dy = (x - cx) / rx, (y - cy) / ry
                e = math.hypot(dx, dy)
                if e > 1.0:
                    continue
                if e > reveal[f]:
                    continue
                in_band = band[f] is not None and abs((x - cx) + (y - cy) * 0.6 - band[f]) < 3.5
                hn = _hex_norm(x - cx + 0.5, y - cy + 0.5, 4.6)
                if e > 0.93:
                    col = rim_hi if (in_band or f <= 2) else rim
                    if f == 5 and (x + y) % 2:
                        continue
                    put(a, x, y, col)
                elif hn > 0.87:
                    if f >= 4 and (x + y) % 2 == 0:
                        continue
                    if f == 5:
                        continue
                    col = rim_hi if in_band else (cell if e > 0.55 or f == 2 else cell_dim)
                    put(a, x, y, col, 230 if not in_band else 255)
                elif in_band:
                    put(a, x, y, fillc, 110)
                elif f == 2:
                    put(a, x, y, fillc, 45)
        if f == 0:
            for d in range(-3, 4):
                put(a, cx + d, cy, rim_hi)
                put(a, cx, cy + d, rim_hi)
        out.append(Image.fromarray(a, 'RGBA'))
    return out


def hex_cloud(frames=7, size=40, seed=21):
    rng = random.Random(seed)
    puffs = [(rng.uniform(-8, 8), rng.uniform(-5, 7), rng.uniform(3, 5), rng.uniform(1.0, 1.8)) for _ in range(7)]
    cols = [C('#3a1458'), C('#5e2690'), C('#8a4ac8'), C('#b884ec'), C('#e8c8ff')]
    nrng = np.random.default_rng(seed)
    noise = nrng.uniform(-0.25, 0.25, (size, size))
    out = []
    c = size / 2 - 0.5
    for f in range(frames):
        a = blank(size, size)
        fade = max(0, f - 3) * 0.2
        for y in range(size):
            for x in range(size):
                v = 0
                for (ox, oy, r0, g) in puffs:
                    r = r0 + g * f
                    d = math.hypot(x - (c + ox * (1 + f * 0.12)), y - (c + oy - f * 0.9))
                    v = max(v, 1 - d / r)
                if v <= 0:
                    continue
                v = v + noise[y, x] - fade
                if v <= 0.05:
                    continue
                k = quant(min(1.0, v * 1.3), x, y, 5)
                if k < 0:
                    continue
                col = cols[min(4, k)]
                put(a, x, y, col, 235 if k >= 1 else 170)
        for i in range(6):
            ang = i * 1.05 + f * 0.5
            d = 6 + (i * 3 + f * 2) % 11
            sx, sy = c + math.cos(ang) * d, c + math.sin(ang) * d * 0.8 - f
            if (i + f) % 3 == 0 or f == 0:
                continue
            twinkle(a, sx, sy, '#ffffff' if i % 2 else '#d8ff9a', '#e0b0ff' if i % 2 else '#8ae04a')
        out.append(Image.fromarray(a, 'RGBA'))
    return out


def _up_arrow(a, cx, top, fade=0):
    """Chunky golden up-arrow. fade 0 = solid+outline, 1 = no outline + light dither, 2 = sparse."""
    fill_c, hi, sh, line = '#ffd35a', '#fff6c8', '#e08a1c', '#8a4a10'
    shape = ["....#....", "...###...", "..#####..", ".#######.", "#########", "...###...", "...###...",
             "...###..."]
    Wd = len(shape[0])

    def inside(px_, py_):
        return 0 <= py_ < len(shape) and 0 <= px_ < Wd and shape[py_][px_] == '#'

    for py, row in enumerate(shape):
        for pxx, ch in enumerate(row):
            if ch != '#':
                continue
            x, y = cx - Wd // 2 + pxx, top + py
            if fade == 1 and (x + y) % 4 == 0:
                continue
            if fade == 2 and (x + y) % 2:
                continue
            col = hi if (not inside(pxx - 1, py) or not inside(pxx, py - 1)) else (
                sh if not inside(pxx + 1, py) or not inside(pxx, py + 1) else fill_c)
            if fade:
                col = hi if fade == 2 else col
            put(a, x, y, col)
    if fade == 0:
        for py in range(-1, len(shape) + 1):
            for pxx in range(-1, Wd + 1):
                if inside(pxx, py):
                    continue
                if any(inside(pxx + dx, py + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    put(a, cx - Wd // 2 + pxx, top + py, line)


def buff_rise(frames=7, w=40, h=48):
    arrows = [(11, 32, 0), (29, 36, 1), (20, 40, 2)]
    out = []
    for f in range(frames):
        a = blank(w, h)
        if f <= 2:
            rx = 10 + f * 4
            for i in range(60):
                ang = i / 60 * 2 * math.pi
                if f == 2 and i % 2:
                    continue
                put(a, 19.5 + math.cos(ang) * rx, 42 + math.sin(ang) * rx * 0.28, '#ffe070' if f < 2 else '#e0a030')
        for i in range(9):
            x = 5 + (i * 7) % 31
            y = 44 - ((f * 5 + i * 9) % 40)
            put(a, x, y, '#fff0a0' if i % 2 else '#ffc040')
            if i % 3 == 0:
                put(a, x, y + 1, '#c07a18')
        for (ax, y0, delay) in arrows:
            age = f - delay
            if age < 0:
                continue
            top = y0 - age * 6
            if top < -8:
                continue
            fade = 0 if top > 10 else (1 if top > 2 else 2)
            _up_arrow(a, ax, top, fade)
        out.append(Image.fromarray(a, 'RGBA'))
    return out


# name -> (fn, frame_w, frame_h, fps, loop)
EFFECTS = {
    'ember_bolt': (ember_bolt, 16, 16, 14, True),
    'arrow': (arrow_proj, 16, 16, 12, True),
    'tide_orb': (tide_orb, 16, 16, 12, True),
    'petal_bolt': (petal_bolt, 16, 16, 14, True),
    'axe_cleave': (axe_cleave, 48, 48, 18, False),
    'spear_thrust': (spear_thrust, 48, 32, 20, False),
    'dagger_flurry': (dagger_flurry, 40, 40, 20, False),
    'petal_burst': (petal_burst, 40, 40, 14, False),
    'shield_flash': (shield_flash, 40, 48, 14, False),
    'hex_cloud': (hex_cloud, 40, 40, 12, False),
    'buff_rise': (buff_rise, 40, 48, 14, False),
}


def strip(frames):
    w, h = frames[0].size
    out = Image.new('RGBA', (w * len(frames), h), (0, 0, 0, 0))
    for i, fr in enumerate(frames):
        out.paste(fr, (i * w, 0), fr)
    return out


# =================================================================== EMBERGATE
GATE_W, GATE_H = 96, 128
G_CX, G_CY, R_IN, R_OUT = 47.5, 56.0, 26.0, 38.0
FLOOR_Y = 93            # last row of the opening
VORTEX_POS = (16, 30)   # where the 64x64 vortex sits under the frame (1x gate coords)

STONE = ['#100c14', '#1e1a24', '#2c2634', '#3c3546', '#544b60']   # line, sh, base, hi, hi2
IRONC = ['#0e0c12', '#26222c', '#3e3a46', '#666270', '#9a96a4']
EMBER = ['#5a1e12', '#a8401a', '#ff7a2a', '#ffb04a', '#fff0b0']


def _pip(poly, X, Y):
    """Vectorised point-in-polygon (even-odd)."""
    inside = np.zeros(X.shape, dtype=bool)
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cond = ((y1 <= Y) & (Y < y2)) | ((y2 <= Y) & (Y < y1))
        with np.errstate(divide='ignore', invalid='ignore'):
            xint = x1 + (Y - y1) * (x2 - x1) / (y2 - y1 + 1e-9)
        inside ^= cond & (X < xint)
    return inside


def gate_masks(s=1.0):
    W, H = int(round(GATE_W * s)), int(round(GATE_H * s))
    yy, xx = np.mgrid[0:H, 0:W]
    X = (xx + 0.5) / s - 0.5
    Y = (yy + 0.5) / s - 0.5
    D = np.hypot(X - G_CX, Y - G_CY)
    AX = np.abs(X - G_CX)
    TH = np.degrees(np.arctan2(X - G_CX, G_CY - Y))     # 0 = straight up, -90 left, +90 right
    m = {}
    m['arch'] = (Y <= G_CY) & (D >= R_IN) & (D < R_OUT)
    m['pillar'] = (Y > G_CY) & (Y <= FLOOR_Y) & (AX >= R_IN) & (AX < R_OUT)
    m['capital'] = (Y > G_CY - 1) & (Y <= G_CY + 5) & (AX >= R_IN) & (AX < R_OUT + 2)
    m['base'] = (Y >= 86) & (Y <= FLOOR_Y) & (AX >= R_IN) & (AX < R_OUT + 3)
    m['step1'] = (Y >= 94) & (Y <= 100) & (AX <= 43)
    m['step2'] = (Y >= 101) & (Y <= 110) & (AX <= 45.5)
    m['step3'] = (Y >= 111) & (Y <= 121) & (AX <= 47)
    m['keystone'] = _pip([(39.5, 12.5), (55.5, 12.5), (52.5, 31.5), (42.5, 31.5)], X, Y)
    crest = np.zeros(X.shape, dtype=bool)
    for tri in ([(43.5, 15), (47.5, -0.5), (51.5, 15)],
                [(39.5, 15), (40.5, 2.5), (45.5, 13)], [(55.5, 15), (54.5, 2.5), (49.5, 13)],
                [(35.5, 16), (34, 7), (41, 14)], [(59.5, 16), (61, 7), (54, 14)]):
        crest |= _pip(tri, X, Y)
    m['crest'] = crest
    spikes = np.zeros(X.shape, dtype=bool)
    for k, deg in enumerate(range(-78, 79, 13)):
        if abs(deg) < 12:
            continue
        L = (13 if (k % 2 == 0) else 8) * (0.55 + 0.45 * math.cos(math.radians(deg)))
        rad = math.radians(deg)
        ux, uy = math.sin(rad), -math.cos(rad)
        px_, py_ = -uy, ux
        b = R_OUT - 2
        tip = (G_CX + ux * (R_OUT + L), G_CY + uy * (R_OUT + L))
        p1 = (G_CX + ux * b + px_ * 2.6, G_CY + uy * b + py_ * 2.6)
        p2 = (G_CX + ux * b - px_ * 2.6, G_CY + uy * b - py_ * 2.6)
        spikes |= _pip([p1, tip, p2], X, Y)
    m['spikes'] = spikes & ~m['arch']
    opening = ((Y <= G_CY) & (D < R_IN)) | ((Y > G_CY) & (Y <= FLOOR_Y) & (AX < R_IN))
    m['opening'] = opening
    solid = np.zeros(X.shape, dtype=bool)
    for k in ('arch', 'pillar', 'capital', 'base', 'step1', 'step2', 'step3', 'keystone', 'crest', 'spikes'):
        solid |= m[k]
    m['solid'] = solid & ~opening
    m['X'], m['Y'], m['D'], m['AX'], m['TH'] = X, Y, D, AX, TH
    return m


def _label_shade(labels, colfn):
    """Carved-block shading: lit top/left bevel, shadowed bottom/right, dark mortar between blocks."""
    H, W = labels.shape
    out = np.zeros((H, W, 4), dtype=np.float64)
    pad = np.pad(labels, 1, constant_values=0)
    up, dn = pad[:-2, 1:-1], pad[2:, 1:-1]
    lf, rt = pad[1:-1, :-2], pad[1:-1, 2:]
    for L in np.unique(labels):
        if L == 0:
            continue
        msk = labels == L
        line, sh, base, hi = colfn(L)
        mortar = msk & (((dn != L) & (dn != 0)) | ((rt != L) & (rt != 0)))
        lit = msk & ~mortar & ((up != L) | (lf != L))
        shade = msk & ~mortar & ~lit & ((dn != L) | (rt != L))
        rest = msk & ~mortar & ~lit & ~shade
        out[rest] = base
        out[lit] = hi
        out[shade] = sh
        out[mortar] = line
    return out


def _outline(a, skip=None, dark=(18, 10, 20)):
    alpha = a[:, :, 3] > 0
    pad = np.pad(alpha, 1)
    near = pad[:-2, 1:-1] | pad[2:, 1:-1] | pad[1:-1, :-2] | pad[1:-1, 2:]
    ring = near & ~alpha
    if skip is not None:
        ring &= ~skip
    a[ring] = list(dark) + [255]
    return a


def _small_icon_canvas(w, h, draw):
    cv = Canvas(w, h)
    draw(cv)
    cv.outline()
    return np.array(cv.image())


def _paste(dst, src, ox, oy):
    h, w = src.shape[:2]
    for y in range(h):
        for x in range(w):
            if src[y, x, 3] > 0:
                X, Y = ox + x, oy + y
                if 0 <= X < dst.shape[1] and 0 <= Y < dst.shape[0]:
                    blend(dst, X, Y, tuple(int(v) for v in src[y, x, :3]), int(src[y, x, 3]))


def _socket(E, w=13, h=15):
    def d(cv):
        cx, cy = (w - 1) / 2, (h - 1) / 2
        cv.part(cv.mask().ellipse(cx, cy, w / 2 - 1, h / 2 - 1), Pal(IRONC[2], IRONC[3], IRONC[1]))
        cv.part(cv.mask().ellipse(cx, cy, w / 2 - 2.2, h / 2 - 2.2), GOLD_DARK)
        top, bot = 2.2, h - 3.2
        cv.part(cv.mask().poly([(cx, top), (cx + w / 2 - 3.2, cy), (cx, bot), (cx - w / 2 + 3.2, cy)]), E.pal())
        cv.part(cv.mask().poly([(cx, top + 1.5), (cx + 1.2, cy), (cx, bot - 1.5), (cx - 1.2, cy)]),
                Pal(E.hi, E.glow, E.base), separate=False)

    a = _small_icon_canvas(w, h, d)
    cx = w // 2
    put(a, cx - 1, 4, '#ffffff')
    return a


GLYPHS = [
    [".#.", "###", ".#.", "#.#"],
    ["#..", "##.", "#.#", "#.."],
    ["###", "..#", ".#.", "#.."],
    [".#.", "#.#", ".#.", ".#."],
    ["#.#", "###", "..#", ".##"],
    ["##.", "#..", "###", "..#"],
]


def _rune(a, x0, y0, g):
    """Carved glowing glyph: dark cut shadow down-right, ember glow on top."""
    pat = GLYPHS[g % len(GLYPHS)]
    cells = {(pxx, py) for py, row in enumerate(pat) for pxx, ch in enumerate(row) if ch == '#'}
    for (pxx, py) in cells:
        if (pxx + 1, py + 1) not in cells:
            put(a, x0 + pxx + 1, y0 + py + 1, STONE[0])
    for (pxx, py) in cells:
        put(a, x0 + pxx, y0 + py, EMBER[3] if py < 2 else EMBER[2])


def _bayer_tile(H, W):
    return np.tile(BAYER, (H // 4 + 1, W // 4 + 1))[:H, :W]


def _warm(a, mask, w, tint='#ff7a2a', strengths=(0.0, 0.2, 0.38, 0.56)):
    """Quantised, ordered-dithered light spill (keeps the pixel-art palette tight)."""
    H, W = mask.shape
    lvl = np.clip(np.floor(w * 3 + _bayer_tile(H, W) - 0.5), 0, 3).astype(int)
    st = np.array(strengths)[lvl]
    sel = mask & (lvl > 0)
    t = np.array(C(tint), dtype=float)[:3]
    a[sel, :3] = a[sel, :3] * (1 - st[sel, None]) + t * st[sel, None]


def embergate_frame():
    m = gate_masks(1.0)
    X, Y, D, AX, TH = m['X'], m['Y'], m['D'], m['AX'], m['TH']
    H, W = X.shape
    rng = np.random.default_rng(5)
    F = lambda h: np.array(C(h), dtype=float)  # noqa: E731

    # ---------------------------------------------------------- iron behind: spikes + flame crest
    iron_lab = np.zeros((H, W), dtype=np.int32)
    iron_lab[m['spikes']] = 1
    iron_lab[m['crest']] = 2
    a = _label_shade(iron_lab, lambda L: [F(IRONC[0]), F(IRONC[1]), F(IRONC[2]), F(IRONC[3])])
    # heated spike tips / crest base
    tip = m['spikes'] & (D > R_OUT + 7)
    _warm(a, tip, np.clip((D - R_OUT - 7) / 5.0, 0, 1), '#ff6a2a', (0.0, 0.35, 0.6, 0.85))
    crest_heat = m['crest'] & (iron_lab == 2)
    _warm(a, crest_heat, np.clip((Y - 6) / 9.0, 0, 1) * 0.9, '#ff7a2a', (0.0, 0.3, 0.55, 0.8))

    # ---------------------------------------------------------- carved stone blocks
    labels = np.zeros((H, W), dtype=np.int32)
    step = 180 / 11
    vous = (np.floor((TH + 90) / step)).astype(int) + 100
    labels[m['arch']] = vous[m['arch']]
    course = np.clip(((Y - 62) // 8).astype(int), 0, 5)
    side = (X > G_CX).astype(int)
    labels[m['pillar']] = (300 + course * 2 + side)[m['pillar']]
    labels[m['capital']] = (400 + side)[m['capital']]
    labels[m['base']] = (410 + side)[m['base']]
    for i, k in enumerate(('step1', 'step2', 'step3')):
        off = (0, 7, 3)[i]
        blk = 500 + i * 50 + ((X + off + 200) // 15).astype(int)
        labels[m[k]] = blk[m[k]]
    labels[m['keystone']] = 200
    labels[m['opening']] = 0
    var = {int(L): int(rng.integers(-6, 7)) + (6 if (L >= 100 and L < 200 and L % 2) else 0)
           for L in np.unique(labels)}

    def stone_cols(L):
        if L == 200:
            return [F('#140e12'), F('#3a2c30'), F('#4e3c40'), F('#76585a')]
        v = var[int(L)]
        steps_ = 500 <= L < 700
        cols = []
        for i, hcol in enumerate(STONE[:4]):
            c = F(hcol)
            if i:
                c[:3] = np.clip(c[:3] + v + (8 if steps_ else 0), 0, 255)
            cols.append(c)
        return cols

    st = _label_shade(labels, stone_cols)
    sel = labels > 0
    a[sel] = st[sel]
    speck = (rng.random((H, W)) < 0.07) & (labels > 0) & (labels != 200)
    a[speck, :3] = a[speck, :3] * 0.8

    # ---------------------------------------------------------- iron: outer arch band, inner lip
    band = m['arch'] & (D >= R_OUT - 2.3)
    a[band] = F(IRONC[1])
    a[band & (D >= R_OUT - 1.2)] = F(IRONC[3])
    for deg in range(-84, 85, 12):
        rad = math.radians(deg)
        xi = int(round(G_CX + math.sin(rad) * (R_OUT - 1.6)))
        yi = int(round(G_CY - math.cos(rad) * (R_OUT - 1.6)))
        if abs(deg) > 10 and m['arch'][yi, xi]:
            a[yi, xi] = F(IRONC[4])
    lip = (m['arch'] & (D < R_IN + 1.7)) | (m['pillar'] & (AX < R_IN + 1.7) & ~m['capital'] & ~m['base'])
    a[lip] = F('#3a2626')
    edge = (m['arch'] & (D < R_IN + 0.85)) | (m['pillar'] & (AX < R_IN + 0.85) & ~m['capital'] & ~m['base'])
    a[edge] = F('#d0601e')

    # ---------------------------------------------------------- pillar rune channels
    for (x0, x1) in ((13, 17), (78, 82)):
        chan = m['pillar'] & (X >= x0) & (X <= x1) & (Y >= 62) & (Y <= 84) & ~m['capital']
        a[chan] = F('#18141e')
        a[chan & (X == x0)] = F('#0e0a12')
        a[chan & (Y == 62)] = F('#0e0a12')
        a[chan & (X == x1)] = F('#3c3546')
        a[chan & (Y == 84)] = F('#3c3546')
    for yb in (69, 77):
        row = m['pillar'][yb]
        a[yb, row] = F(IRONC[3])
        a[yb + 1, row] = F(IRONC[1])
        for x in (11, 20, 75, 84):
            a[yb, x] = F(IRONC[4])

    # ---------------------------------------------------------- warm light from the portal
    dist_open = np.where(Y <= G_CY, D - R_IN, AX - R_IN)
    stone = (labels > 0) & ~band
    _warm(a, stone & ~lip, np.clip(1 - (dist_open - 1.7) / 4.5, 0, 1))
    for i, k in enumerate(('step1', 'step2', 'step3')):
        mk = m[k]
        ys = np.where(mk.any(axis=1))[0]
        top = ys.min()
        tread = mk & (Y <= top + 1)
        riser = mk & (Y > top + 1)
        a[tread & (Y == top)] = F(STONE[4])
        reach = 28 - i * 4
        _warm(a, tread, np.clip(1 - AX / reach, 0, 1) * (1.0 - i * 0.2), '#ffa040', (0.0, 0.3, 0.55, 0.8))
        _warm(a, riser, np.clip(1 - AX / (15 - i * 3), 0, 1) * (0.8 - i * 0.25), '#ff7a2a', (0.0, 0.12, 0.22, 0.34))

    a = np.clip(a, 0, 255).astype(np.uint8)

    # ---------------------------------------------------------- ember details
    for i, yc in enumerate((64, 72, 80)):
        _rune(a, 14, yc - 1, i)
        _rune(a, 79, yc - 1, i + 3)
    for i, deg in enumerate((-76, -28, 28, 76)):
        rad = math.radians(deg)
        x = G_CX + math.sin(rad) * 31
        y = G_CY - math.cos(rad) * 31
        _rune(a, int(round(x - 1)), int(round(y - 2)), i + 1)
    for crack in (((40, 94), (39, 96), (40, 98), (38, 100)), ((55, 94), (56, 96), (55, 97), (57, 100), (56, 103)),
                  ((47, 101), (48, 104), (47, 106))):
        for (x0, y0), (x1, y1) in zip(crack, crack[1:]):
            n = max(abs(x1 - x0), abs(y1 - y0))
            for t in range(n + 1):
                x = int(round(x0 + (x1 - x0) * t / n))
                y = int(round(y0 + (y1 - y0) * t / n))
                put(a, x, y, EMBER[3] if t % 2 == 0 else EMBER[2])
    # element crystal sockets: fire on the keystone, water left haunch, nature right haunch
    _paste(a, _socket(FIRE, 13, 17), 41, 12)
    _paste(a, _socket(WATER, 11, 13), 18, 30)
    _paste(a, _socket(NATURE, 11, 13), 67, 30)
    for (x, y) in ((47, 4), (48, 4), (47, 5), (48, 5), (47, 6), (48, 6)):
        put(a, x, y, EMBER[3] if y < 6 else EMBER[2])
    put(a, 47, 3, EMBER[4])

    a[m['opening']] = 0
    a = _outline(a, skip=m['opening'])
    return Image.fromarray(a, 'RGBA')


VORTEX_PAL = ['#0a0612', '#180c26', '#2c1240', '#4a1a54', '#782050', '#b0303a', '#e0602a', '#ffa044',
              '#ffd88a', '#fff8e0']


def vortex_frame(f, n=6, size=64):
    a = np.zeros((size, size, 4), dtype=np.uint8)
    cols = [C(x) for x in VORTEX_PAL]
    c = (size - 1) / 2
    sc = size / 64.0
    ph = f * 2 * math.pi / n
    for y in range(size):
        for x in range(size):
            dx, dy = (x - c) / sc, (y - c) / sc
            r = math.hypot(dx, dy)
            th = math.atan2(dy, dx)
            lr = math.log(r + 2.0)
            arms = 0.5 + 0.5 * math.cos(3 * th + 4.2 * lr - ph)
            arms2 = 0.5 + 0.5 * math.cos(5 * th - 2.5 * lr + 2 * ph + 1.0)
            rn = r / 32.0
            fall = max(0.0, 1 - rn * 0.95)
            core = math.exp(-(rn / 0.2) ** 2)
            v = core * 1.05 + fall ** 1.1 * (0.78 * arms ** 2.2 + 0.28 * arms2 ** 4) + 0.08 * (1 - min(1, rn))
            v = min(v, 1.0)
            k = quant(v, x, y, len(cols) - 1) + 1
            a[y, x] = cols[max(0, min(len(cols) - 1, k))]
    # motes spiralling inward (seamless: each mote reaches the next one's start after n frames)
    t = f / n
    for arm in range(3):
        for j in range(5):
            u = j + t
            r = 30 * (0.62 ** u)
            th = arm * 2 * math.pi / 3 - ph / 3 + 1.6 * u
            mx, my = c + math.cos(th) * r * sc, c + math.sin(th) * r * sc
            col = '#fff8e0' if r < 14 else '#ffd88a'
            put(a, mx, my, col)
            if r > 12:
                blend(a, mx - math.cos(th + 1.2), my - math.sin(th + 1.2), '#ffa044', 200)
    return a


def embergate_vortex(n=6):
    frames = [Image.fromarray(vortex_frame(f, n), 'RGBA') for f in range(n)]
    return strip(frames)


def _dither_mix(base, tgt, t, x, y):
    return tgt if t > BAYER[y % 4, x % 4] else base


def _downsample_mask(mask, k=2, thr=0.5):
    H, W = mask.shape
    h, w = H // k, W // k
    cov = mask[:h * k, :w * k].reshape(h, k, w, k).mean(axis=(1, 3))
    return cov >= thr


def banner_standard():
    W, H = 180, 72
    rng = random.Random(33)
    by = _bayer_tile(H, W)
    gcx = 140
    # background: night gradient + dithered ember glow around the gate
    ramp = [C(h) for h in ('#0b0812', '#110b18', '#170d1c', '#1f101e', '#2a121e', '#36161e', '#44191c',
                           '#541e1a', '#682418', '#7e2c16')]
    a = np.zeros((H, W, 4), dtype=np.uint8)
    for y in range(H):
        for x in range(W):
            v = 1.2 + 2.2 * (y / H)                                   # night gradient
            d = math.hypot((x - gcx) / 1.3, (y - 40) * 1.05)
            v += 7.0 * max(0.0, 1 - d / 60) ** 1.6                     # ember glow behind the gate
            v -= 0.8 * max(0.0, 1 - x / 90)                            # calmer text side
            k = int(math.floor(v + by[y, x] - 0.5))
            a[y, x] = ramp[max(0, min(len(ramp) - 1, k))]
    # distant ridge
    for x in range(W):
        top = H - 9 + int(round(2.5 * math.sin(x * 0.08) + 1.5 * math.sin(x * 0.21 + 1)))
        for y in range(top, H):
            a[y, x] = C('#0c070c')
        lit = max(0.0, 1 - abs(x - gcx) / 45)
        a[top, x] = C('#7a3418') if lit > 0.45 else (C('#3a1a18') if lit > 0.1 else C('#1c1218'))
    # ring + sigils (behind the gate)
    ocx, ocy = gcx, 38
    RX, RY = 33, 29
    sig_pos = {'fire': (ocx, ocy - RY), 'water': (ocx - RX * math.cos(math.radians(30)), ocy + RY * 0.5),
               'nature': (ocx + RX * math.cos(math.radians(30)), ocy + RY * 0.5)}
    for i in range(720):
        ang = math.radians(i / 2)
        x, y = ocx + math.cos(ang) * RX, ocy + math.sin(ang) * RY
        col = '#ffb04a' if (i // 20) % 4 == 0 else '#a8482a'
        blend(a, x, y, col, 220)
    for i in range(0, 360, 10):
        ang = math.radians(i)
        blend(a, ocx + math.cos(ang) * (RX - 3), ocy + math.sin(ang) * (RY - 3), '#c0602a', 130)
    # gate: the real Embergate frame at 1/2 scale, back-lit (dark body, glowing details)
    gm = gate_masks(1.0)
    frame = np.array(embergate_frame())
    gh, gw = GATE_H // 2, GATE_W // 2
    small = np.zeros((gh, gw, 4), dtype=np.uint8)
    for y in range(gh):
        for x in range(gw):
            blk = frame[y * 2:y * 2 + 2, x * 2:x * 2 + 2].reshape(4, 4)
            op = blk[blk[:, 3] > 0]
            if len(op) < 2:
                continue
            rgb = op[:, :3].astype(float)
            lum = rgb.max(axis=1) + (rgb.max(axis=1) - rgb.min(axis=1))
            small[y, x] = op[int(np.argmax(lum))]
    body = small[:, :, 3] > 0
    rgb = small[:, :, :3].astype(float)
    bright = (rgb.max(axis=2) - rgb.min(axis=2) > 110) & (rgb.max(axis=2) > 200)
    dark = rgb * 0.42 + np.array([6, 2, 8])
    small[:, :, :3] = np.where(bright[..., None], rgb, dark).astype(np.uint8)
    opening = _downsample_mask(gm['opening'], thr=0.5) & ~body
    ox, oy = gcx - gw // 2, ocy - 31
    vs = 33
    vort = vortex_frame(1, 6, vs)
    vx, vy = ox + VORTEX_POS[0] // 2, oy + VORTEX_POS[1] // 2
    for y in range(gh):
        for x in range(gw):
            X, Y = ox + x, oy + y
            if not (0 <= X < W and 0 <= Y < H):
                continue
            if opening[y, x]:
                a[Y, X] = vort[min(vs - 1, max(0, Y - vy)), min(vs - 1, max(0, X - vx))]
            elif body[y, x]:
                a[Y, X] = small[y, x]
    # rim light on the silhouette top edges
    for y in range(gh):
        for x in range(gw):
            if not body[y, x] or bright[y, x]:
                continue
            X, Y = ox + x, oy + y
            if not (0 <= X < W and 0 <= Y < H):
                continue
            if y == 0 or not body[y - 1, x]:
                a[Y, X] = C('#6a3424') if x >= gw // 2 else C('#4a2a2e')

    # the three elemental sigils
    sig = {'fire': ('#ff6a2a', '#ffc070', '#fff0b0'), 'water': ('#3aa0e0', '#a8eaff', '#e6ffff'),
           'nature': ('#5aa832', '#b0e070', '#e8ffc0')}
    pats = {'fire': ["..#..", ".##..", ".###.", "##.##", ".###."],
            'water': ["..#..", "..#..", ".###.", "#####", ".###."],
            'nature': ["...##", "..###", ".###.", "###..", "#...."]}
    for el, (sx, sy) in sig_pos.items():
        sx, sy = int(round(sx)), int(round(sy))
        base, hi, glw = sig[el]
        for y in range(-10, 11):
            for x in range(-10, 11):
                d = math.hypot(x, y)
                X, Y = sx + x, sy + y
                if d <= 5.4:
                    put(a, X, Y, '#140a18')
                elif d <= 6.5:
                    put(a, X, Y, hi if (x + y) < 0 else base)
                elif d <= 7.4:
                    put(a, X, Y, '#07040a')
                elif d <= 9.5 and (X + Y) % 2 == 0 and d > 8.2:
                    blend(a, X, Y, base, 150)
        for py, row in enumerate(pats[el]):
            for pxx, ch in enumerate(row):
                if ch == '#':
                    put(a, sx - 2 + pxx, sy - 2 + py, glw if py < 2 else hi)
    # rising ember sparks (sparse over the text area)
    for i in range(80):
        right = rng.random() < 0.82
        x = rng.uniform(98, 177) if right else rng.uniform(4, 98)
        y = rng.uniform(4, H - 8)
        col = rng.choice(['#ffb04a', '#ff7a2a', '#fff0a0', '#e0502a'])
        blend(a, x, y, col, 255 if right else 140)
        if right and rng.random() < 0.3:
            blend(a, x, y + 1, '#a8401a', 200)
    for (x, y) in ((112, 14), (170, 16), (104, 34), (176, 40), (122, 62)):
        twinkle(a, x, y, '#ffffff', '#ffd88a')
    # frame: dark rim with a warm bronze hairline
    a[0, :] = C('#07040a')
    a[H - 1, :] = C('#07040a')
    a[:, 0] = C('#07040a')
    a[:, W - 1] = C('#07040a')
    a[1, 1:W - 1] = C('#6a4a26')
    a[H - 2, 1:W - 1] = C('#3a2414')
    a[1:H - 1, 1] = C('#4a3018')
    a[1:H - 1, W - 2] = C('#3a2414')
    return Image.fromarray(a, 'RGBA')


def rarity_glow(cols, rays, ray_len, core_r, twist=0.0, size=32):
    """Soft pixel starburst: cols = [core, bright, mid, dim] ; alpha steps baked in."""
    a = np.zeros((size, size, 4), dtype=np.uint8)
    c = (size - 1) / 2
    levels = [(C(cols[3]), 70), (C(cols[2]), 130), (C(cols[1]), 200), (C(cols[0]), 255)]
    for y in range(size):
        for x in range(size):
            dx, dy = x - c, y - c
            r = math.hypot(dx, dy)
            th = math.atan2(dy, dx)
            v = max(0.0, 1 - r / core_r) ** 1.2
            for k in range(rays):
                ang = k * 2 * math.pi / rays + twist
                L = ray_len if k % 2 == 0 else ray_len * 0.62
                da = math.atan2(math.sin(th - ang), math.cos(th - ang))
                perp = abs(math.sin(da)) * r
                if abs(da) < math.pi / 2 and r < L:
                    wv = max(0.0, 1 - perp / (1.6 * (1 - r / L) + 0.35)) * (1 - r / L) ** 0.8
                    v = max(v, wv)
            if v <= 0:
                continue
            t = v * 4 + BAYER[y % 4, x % 4] * 0.9 - 0.45
            k = int(math.floor(t))
            if k < 0:
                continue
            col, al = levels[min(3, k)]
            a[y, x] = tuple(col[:3]) + (al,)
    return Image.fromarray(a, 'RGBA')


def rarity_glows():
    return {
        'rarity_glow_3': rarity_glow(['#fff0d0', '#f0b878', '#c07a3a', '#7a4a20'], 4, 15.5, 7.5, math.pi / 4),
        'rarity_glow_4': rarity_glow(['#ffffff', '#e8f0fa', '#b0c0d8', '#6a7a98'], 8, 15.5, 8.5),
        'rarity_glow_5': rarity_glow(['#fffbe0', '#ffe070', '#f0b030', '#b07010'], 12, 15.5, 9.5, math.pi / 12),
    }


# =================================================================== BUILD
# outputs owned by other generators - never overwritten by this pack
PROTECTED_ICONS = {'leader', 'hand', 'gesture_up', 'gesture_down', 'orb_fire', 'orb_water', 'orb_nature',
                   'nav_home', 'nav_units', 'nav_quest', 'nav_bag', 'nav_summon', 'nav_shop', 'nav_settings',
                   'nav_menu'}


def _check_names():
    import fx_icons_ui as fx
    clash = (set(ICONS) & (set(fx.ICONS) | PROTECTED_ICONS)) | (set(EFFECTS) & set(fx.EFFECTS))
    if clash:
        raise RuntimeError('name clash with existing assets: %s' % sorted(clash))


def build(verbose=True):
    _check_names()
    for d in (ICON_DIR, FX_DIR, UI_DIR):
        os.makedirs(d, exist_ok=True)
    written = []
    for name, fn in ICONS.items():
        img = fn()
        assert img.size == (16, 16), name
        p = os.path.join(ICON_DIR, name + '.png')
        save(img, p)
        written.append(p)
    meta_path = os.path.join(FX_DIR, 'effects.json')
    with open(meta_path) as fh:
        meta = json.load(fh)
    for name, (fn, fw, fhh, fps, loop) in EFFECTS.items():
        frames = fn()
        assert all(fr.size == (fw, fhh) for fr in frames), name
        p = os.path.join(FX_DIR, name + '.png')
        save(strip(frames), p)
        written.append(p)
        meta[name] = {'frame_size': [fw, fhh], 'frames': len(frames), 'fps': fps, 'loop': loop}
    with open(meta_path, 'w') as fh:
        json.dump(meta, fh, indent=1)
    ui = {'embergate_frame': embergate_frame(), 'embergate_vortex': embergate_vortex(),
          'banner_standard': banner_standard()}
    ui.update(rarity_glows())
    for name, img in ui.items():
        p = os.path.join(UI_DIR, name + '.png')
        save(img, p)
        written.append(p)
    if verbose:
        print('p4 assets written: %d files' % len(written))
    return written


if __name__ == '__main__':
    build()
