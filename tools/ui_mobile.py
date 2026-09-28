"""
Mobile (portrait) UI kit for Cinderbound - all original pixel art.
Gold-rimmed panels, glossy buttons, unit cards, element orbs, nav icons,
bars and banners. Drawn at 1x then stored at 3x for crisp 9-slice scaling.
"""
import math
import numpy as np
from PIL import Image
from pixlib import Canvas, Pal, hexc

SCALE = 3


def h(c):
    c = c.lstrip('#')
    return np.array([int(c[i:i + 2], 16) for i in (0, 2, 4)] + [255], dtype=np.int32)


def img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def up(im, s=SCALE):
    return im.resize((im.width * s, im.height * s), Image.NEAREST)


GOLD = [h('#5a3a10'), h('#a8741e'), h('#e0a83a'), h('#ffe08a'), h('#fff6d0')]   # dark -> light


def gold_frame(w, hh, interior_top, interior_bottom, rim=3, gems=True, round_=True, gem_col='#d8342a'):
    """Bevelled gold border with a vertical-gradient interior."""
    a = np.zeros((hh, w, 4), dtype=np.int32)
    t, b = h(interior_top), h(interior_bottom)
    for y in range(hh):
        k = y / max(hh - 1, 1)
        row = t * (1 - k) + b * k
        a[y, :, :] = row
    for y in range(hh):
        for x in range(w):
            e = min(x, y, w - 1 - x, hh - 1 - y)
            corner = round_ and ((x < 2 or x > w - 3) and (y < 2 or y > hh - 3)) and (min(x, w - 1 - x) + min(y, hh - 1 - y) < 2)
            if corner:
                a[y, x] = 0
                continue
            if e == 0:
                a[y, x] = h('#1a1008')
            elif e < rim + 1:
                top_left = (y <= x and y < hh - 1 - x) or (x < y and x < hh - 1 - y and x < w // 2 and y < hh // 2)
                idx = e  # 1..rim
                light = (y == e) or (x == e)
                dark = (y == hh - 1 - e) or (x == w - 1 - e)
                if light and not dark:
                    a[y, x] = GOLD[4] if idx == 1 else GOLD[3]
                elif dark and not light:
                    a[y, x] = GOLD[1] if idx == 1 else GOLD[1]
                else:
                    a[y, x] = GOLD[2]
                if idx == rim:
                    a[y, x] = GOLD[0] if not light else GOLD[2]
            elif e == rim + 1:
                a[y, x] = h('#0a0610')
    if gems:
        g = h(gem_col)
        for (cx, cy) in ((2, 2), (w - 3, 2), (2, hh - 3), (w - 3, hh - 3)):
            for dx, dy in ((0, 0), (1, 0), (0, 1), (-1, 0), (0, -1)):
                x, y = cx + dx, cy + dy
                if 0 <= x < w and 0 <= y < hh:
                    a[y, x] = g if (dx, dy) != (-1, 0) and (dx, dy) != (0, -1) else h('#ffb0a0')
    return img(a)


def stone_tile(w=32, hh=32, base='#3e5674', seed=3):
    """Tileable blue slate with cracks (for large backgrounds)."""
    rng = np.random.default_rng(seed)
    b = h(base)[:3]
    a = np.zeros((hh, w, 4), dtype=np.int32)
    noise = rng.integers(-8, 9, (hh, w))
    blot = rng.integers(-10, 11, (hh // 4, w // 4))
    blot = np.kron(blot, np.ones((4, 4), dtype=np.int32))
    for y in range(hh):
        for x in range(w):
            v = b + noise[y, x] // 2 + blot[y, x]
            a[y, x, :3] = v
            a[y, x, 3] = 255
    # flagstone joints
    for y in range(hh):
        for x in range(w):
            if y % 16 == 0 or (x + (8 if (y // 16) % 2 else 0)) % 16 == 0:
                a[y, x, :3] = b - 34
            elif y % 16 == 1 or (x + (8 if (y // 16) % 2 else 0)) % 16 == 1:
                a[y, x, :3] = b + 16
    # a couple of cracks
    for (x0, y0) in ((5, 5), (21, 22)):
        x, y = x0, y0
        for i in range(7):
            if 0 <= x < w and 0 <= y < hh:
                a[y, x, :3] = b - 40
            x += rng.integers(0, 2)
            y += 1
    return img(a)


def glossy_button(w, hh, top, bottom, rim='gold', pressed=False, disabled=False):
    a = np.zeros((hh, w, 4), dtype=np.int32)
    t, bb = h(top), h(bottom)
    if disabled:
        t, bb = h('#5a5a64'), h('#34343c')
    for y in range(hh):
        k = y / (hh - 1)
        col = t * (1 - k) + bb * k
        if pressed:
            col = col * 0.8
            col[3] = 255
        a[y, :] = col
    # gloss band on the upper half
    if not disabled:
        for y in range(2, hh // 2):
            for x in range(3, w - 3):
                a[y, x, :3] = a[y, x, :3] + (40 if not pressed else 16) * (1 - (y - 2) / (hh / 2))
    rimc = [h('#fff0b0'), h('#e0a83a'), h('#8a5a18')] if rim == 'gold' else [h('#e0e8f0'), h('#8a9aac'), h('#3a4454')]
    for y in range(hh):
        for x in range(w):
            e = min(x, y, w - 1 - x, hh - 1 - y)
            cornerish = min(x, w - 1 - x) + min(y, hh - 1 - y)
            if cornerish < 2:
                a[y, x] = 0
            elif e == 0 or cornerish == 2 and e < 1:
                a[y, x] = h('#140a06')
            elif e == 1:
                a[y, x] = rimc[0] if y <= hh // 2 else rimc[2]
                if x in (1, w - 2):
                    a[y, x] = rimc[1]
    return img(a)


def orb(color):
    cv = Canvas(16, 16)
    c = hexc(color)
    light = tuple(min(255, int(v * 0.5 + 255 * 0.5)) for v in c[:3]) + (255,)
    dark = tuple(int(v * 0.5) for v in c[:3]) + (255,)
    cv.part(cv.mask().ellipse(7.5, 7.5, 6.8, 6.8), Pal(c, light, dark))
    a = np.array(cv.image())
    # gold ring + gloss
    for y in range(16):
        for x in range(16):
            d = math.hypot(x - 7.5, y - 7.5)
            if 6.8 < d <= 7.9:
                a[y, x] = (224, 168, 58, 255) if y < 8 else (138, 90, 24, 255)
    for (x, y) in ((5, 3), (6, 3), (4, 4), (5, 4), (4, 5)):
        a[y, x] = (255, 255, 255, 255)
    return Image.fromarray(a, 'RGBA')


def bar_tex(colors):
    """1x6 vertical banded gradient used as a StyleBoxTexture fill."""
    a = np.zeros((6, 4, 4), dtype=np.int32)
    for i, c in enumerate(colors):
        a[i, :] = h(c)
    return img(a)


def ribbon(w=80, hh=18):
    """Title ribbon: red cloth with gold edges and folded tails."""
    a = np.zeros((hh, w, 4), dtype=np.int32)
    for y in range(hh):
        for x in range(w):
            inset = 6
            tail = x < inset or x >= w - inset
            if tail:
                # swallow-tail ends
                xx = x if x < inset else w - 1 - x
                notch = abs(y - hh / 2) < (inset - xx) * 0.6
                if notch:
                    continue
                col = h('#7a1a18') if y % 2 else h('#6a1614')
            else:
                k = y / (hh - 1)
                col = h('#d0402e') * (1 - k) + h('#8a2018') * k
            if y in (0, hh - 1):
                col = h('#1a0806')
            elif y in (1, hh - 2) and not tail:
                col = h('#ffd870') if y == 1 else h('#a8741e')
            a[y, x] = col
            a[y, x, 3] = 255
    return img(a)


def nav_button(active=False):
    return gold_frame(32, 32, '#6a2a1c' if active else '#2e2436', '#3a1410' if active else '#16121c', rim=2, gems=False)


def icon(draw):
    cv = Canvas(16, 16)
    draw(cv)
    cv.outline()
    return cv.image()


def ic_home(cv):
    cv.part(cv.mask().poly([(1, 8), (8, 1), (15, 8)]), Pal('#c0402e', '#ff7a5a', '#7a1a14'))
    cv.part(cv.mask().rect(3, 8, 12, 14), Pal('#d8b890', '#f8e0c0', '#9a7a58'))
    cv.part(cv.mask().rect(7, 10, 9, 14), Pal('#6a4424'), flat=True)


def ic_units(cv):
    cv.part(cv.mask().ellipse(8, 8, 6, 6.5).rect(2, 8, 14, 13), Pal('#9aa4b4', '#e0e8f0', '#5a6474'))
    cv.part(cv.mask().rect(4, 8, 12, 9), Pal('#20242c'), flat=True)
    cv.part(cv.mask().poly([(8, 0), (10, 3), (6, 3)]), Pal('#d8342a', '#ff7a5a', '#8a1a14'))


def ic_quest(cv):
    cv.part(cv.mask().line(2, 14, 13, 3, 2), Pal('#c9d1dc', '#ffffff', '#8e98a8'))
    cv.part(cv.mask().line(14, 14, 3, 3, 2), Pal('#c9d1dc', '#ffffff', '#8e98a8'))
    cv.part(cv.mask().line(3, 10, 6, 13, 1).line(13, 10, 10, 13, 1), Pal('#e0a83a'), shade=False)


def ic_bag(cv):
    cv.part(cv.mask().ellipse(8, 10, 6, 5), Pal('#a8743a', '#d8a868', '#6a4420'))
    cv.part(cv.mask().rect(5, 3, 11, 6), Pal('#a8743a', '#d8a868', '#6a4420'))
    cv.part(cv.mask().rect(4, 6, 12, 6), Pal('#e0a83a'), flat=True)


def ic_summon(cv):
    cv.part(cv.mask().ellipse(8, 12, 7, 3), Pal('#7a3ab0', '#b07ae0', '#4a1a70'))
    cv.part(cv.mask().poly([(8, 1), (12, 7), (8, 12), (4, 7)]), Pal('#6ae0ff', '#e0ffff', '#2a90c0'))


def ic_shop(cv):
    cv.part(cv.mask().ellipse(8, 10, 6, 5.5), Pal('#6a8a3a', '#9ac068', '#3a5a20'))
    cv.part(cv.mask().rect(6, 2, 10, 5), Pal('#6a8a3a', '#9ac068', '#3a5a20'))
    cv.part(cv.mask().ellipse(8, 10, 2.5, 2.5), Pal('#f0c040', '#fff0a0', '#b8841c'), separate=False)


def ic_settings(cv):
    m = cv.mask().ellipse(8, 8, 6.5, 6.5)
    for k in range(8):
        a = k * math.pi / 4
        m.rect(8 + math.cos(a) * 6 - 1, 8 + math.sin(a) * 6 - 1, 8 + math.cos(a) * 6 + 1, 8 + math.sin(a) * 6 + 1)
    m.subtract(cv.mask().ellipse(8, 8, 2.5, 2.5))
    cv.part(m, Pal('#9aa4b4', '#e0e8f0', '#5a6474'))


def quest_banner(w=110, hh=40):
    """Big ornate QUEST plate: gold frame, ember-red body, flame flourishes on top."""
    base = gold_frame(w, hh, '#c8481e', '#6a1408', rim=3, gems=True, gem_col='#ffd35a')
    a = np.array(base).astype(np.int32)
    # engraved diagonal ember streaks
    for y in range(6, hh - 6):
        for x in range(6, w - 6):
            if (x + y * 2) % 11 == 0:
                a[y, x, :3] = a[y, x, :3] * 0.85
    return img(a)


def screen_frame():
    return gold_frame(24, 24, '#1a2236', '#0e1220', rim=2, gems=True)


def card_frame(selected=False, acted=False):
    top, bot = ('#3a2230', '#140a14') if not selected else ('#5a2a18', '#20100a')
    im = gold_frame(40, 24, top, bot, rim=2, gems=False)
    if acted:
        a = np.array(im).astype(np.int32)
        a[:, :, :3] = a[:, :, :3] * 0.6
        im = img(a)
    return im


def tile_frame():
    return gold_frame(24, 24, '#28324a', '#121626', rim=2, gems=False)


def slate_plate():
    """Row plate for stage lists: slate body, thin gold rim."""
    base = gold_frame(48, 16, '#46607e', '#2a3a52', rim=1, gems=False)
    return base


def build(out):
    items = {
        'm_frame': screen_frame(),
        'm_frame_red': gold_frame(24, 24, '#5a1a18', '#2a0a08', rim=2, gems=True, gem_col='#ffd35a'),
        'm_card': card_frame(),
        'm_card_sel': card_frame(True),
        'm_tile': tile_frame(),
        'm_plate': slate_plate(),
        'm_btn_blue': glossy_button(32, 14, '#3a78d8', '#153a8a'),
        'm_btn_blue_p': glossy_button(32, 14, '#3a78d8', '#153a8a', pressed=True),
        'm_btn_red': glossy_button(32, 14, '#e0502e', '#8a1a12'),
        'm_btn_red_p': glossy_button(32, 14, '#e0502e', '#8a1a12', pressed=True),
        'm_btn_gold': glossy_button(32, 14, '#f0c048', '#a0661a'),
        'm_btn_off': glossy_button(32, 14, '#000000', '#000000', disabled=True),
        'm_nav': nav_button(),
        'm_nav_on': nav_button(True),
        'm_quest': quest_banner(),
        'm_ribbon': ribbon(),
        'm_bar_bg': gold_frame(12, 6, '#0a0a10', '#1a1a24', rim=1, gems=False, round_=False),
    }
    for k, v in items.items():
        up(v).save(f'{out}/{k}.png')
    stone_tile().resize((96, 96), Image.NEAREST).save(f'{out}/m_stone.png')
    for name, cols in {'m_fill_hp': ['#c8ff9a', '#7ae05a', '#4ec03a', '#3aa02a', '#2a8020', '#1e6018'],
                       'm_fill_burst': ['#c8f8ff', '#6ae0ff', '#3ab0f0', '#2a88d8', '#1e68b8', '#164c90'],
                       'm_fill_burst_full': ['#fff8c0', '#ffe070', '#ffc040', '#f0a020', '#d07818', '#a05410'],
                       'm_fill_enemy': ['#ffb0a0', '#ff5a4a', '#e0342a', '#c02418', '#961810', '#6a0c08'],
                       'm_fill_xp': ['#e8d8ff', '#c0a8ff', '#a890f0', '#8a70d8', '#6a50b8', '#4a3490']}.items():
        bar_tex(cols).resize((12, 18), Image.NEAREST).save(f'{out}/{name}.png')
    for el, col in (('fire', '#ff5a2a'), ('water', '#2a8ae0'), ('nature', '#4ab02a')):
        up(orb(col)).save(f'{out}/../icons/orb_{el}.png')
    for name, fn in (('home', ic_home), ('units', ic_units), ('quest', ic_quest), ('bag', ic_bag),
                     ('summon', ic_summon), ('shop', ic_shop), ('settings', ic_settings)):
        up(icon(fn)).save(f'{out}/../icons/nav_{name}.png')


if __name__ == '__main__':
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    build(os.path.join(here, '..', 'assets', 'ui'))
    print('mobile ui kit generated')
