"""
Cinderbound UI theme v2 - original pixel art.
Materials: worn iron, dark stone, ember-lit edges, carved corner ornaments,
wood plank headers, elemental crystal accents.

Everything is drawn at 1x and stored at 3x (nearest) so 9-slice borders stay
crisp at the 1080x1920 reference resolution. Icons are 16x16 at 1x with a
shared outline / light direction (top-left) and are scaled by whole numbers
in-engine.

Run: python3 tools/ui_v2.py
"""
import math
import os
import random
import numpy as np
from PIL import Image
from pixlib import Canvas, Pal, hexc

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Content'))  # game content root
UI = os.path.join(ROOT, 'assets', 'ui')
ICONS = os.path.join(ROOT, 'assets', 'icons')
S = 3


def c(h, a=255):
    h = h.lstrip('#')
    return np.array([int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a], dtype=np.int32)


def to_img(a):
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def save3(img, name, folder=UI):
    img.resize((img.width * S, img.height * S), Image.NEAREST).save(os.path.join(folder, name + '.png'))


def save1(img, name, folder=ICONS):
    img.save(os.path.join(folder, name + '.png'))


# ---------------------------------------------------------------- materials
METALS = {
    'iron':   ['#16121a', '#3a3640', '#5a5660', '#8a8690', '#c0bcc4'],
    'ember':  ['#1a0c0a', '#5a1e12', '#9a3a1a', '#e0702a', '#ffc070'],
    'steel':  ['#0c1220', '#243650', '#3e5a80', '#6e94c0', '#b8d8f0'],
    'bronze': ['#141008', '#3a2e14', '#6a5a28', '#9a8a44', '#d0c078'],
    'gold':   ['#1a1006', '#6a4410', '#a8741e', '#e0a83a', '#fff0b0'],
    'silver': ['#121418', '#4a5058', '#7a828c', '#b0b8c4', '#f0f4f8'],
    'crimson': ['#14060a', '#4a0e16', '#7a1a22', '#c0303a', '#ff8a7a'],
    'wood':   ['#140c06', '#3a2412', '#5a3a1e', '#7a5430', '#a07848'],
    'prism':  ['#100818', '#3a2a6a', '#6a4ab0', '#a07ae0', '#e8d8ff'],
}


def stone(w, h, base='#24202a', var=10, seed=1):
    rng = np.random.default_rng(seed)
    b = c(base)
    a = np.zeros((h, w, 4), dtype=np.int32)
    n = rng.integers(-var, var + 1, (h, w))
    blot = rng.integers(-var, var + 1, ((h + 3) // 4, (w + 3) // 4))
    blot = np.kron(blot, np.ones((4, 4), dtype=np.int32))[:h, :w]
    for ch in range(3):
        a[:, :, ch] = b[ch] + n // 2 + blot
    a[:, :, 3] = 255
    return a


def frame(w, h, metal='iron', rim=3, interior='#24202a', stone_int=True, ember_line=None,
          ornament='scroll', rivets=True, seed=1, inset=False, alpha_interior=255, bevel=True):
    """Generic metal frame. ornament: None | 'scroll' | 'flame' | 'wave' | 'leaf' | 'horn' | 'gem'"""
    m = [c(x) for x in METALS[metal]]
    a = stone(w, h, interior, seed=seed) if stone_int else np.tile(c(interior), (h, w, 1))
    a[:, :, 3] = alpha_interior
    rng = random.Random(seed)
    for y in range(h):
        for x in range(w):
            e = min(x, y, w - 1 - x, h - 1 - y)
            if e == 0:
                a[y, x] = m[0]
            elif e <= rim:
                top_left = (y == e and x >= e and x <= w - 1 - e) or (x == e and y >= e and y <= h - 1 - e)
                bottom_right = (y == h - 1 - e) or (x == w - 1 - e)
                if inset:
                    top_left, bottom_right = bottom_right, top_left
                if e == 1:
                    col = m[4] if top_left and not bottom_right else (m[1] if bottom_right else m[3])
                elif e == rim:
                    col = m[1] if top_left else m[2]
                else:
                    col = m[3] if top_left and not bottom_right else m[2]
                if not bevel:
                    col = m[2] if e < rim else m[1]
                # worn scratches
                if rng.random() < 0.06:
                    col = m[1]
                a[y, x] = col
            elif e == rim + 1:
                a[y, x] = m[0]
                if ember_line is not None and not inset:
                    a[y, x] = c(ember_line) if (y == h - 2 - rim or x == w - 2 - rim) else m[0]
            elif e == rim + 2 and inset:
                a[y, x, :3] = a[y, x, :3] // 2
    # rivets
    if rivets and w >= 16 and h >= 16:
        for (x, y) in ((rim // 2 + 1, rim // 2 + 1), (w - 2 - rim // 2, rim // 2 + 1),
                       (rim // 2 + 1, h - 2 - rim // 2), (w - 2 - rim // 2, h - 2 - rim // 2)):
            a[y, x] = m[4]
            if x + 1 < w:
                a[y, x + 1] = m[2]
            if y + 1 < h:
                a[y + 1, x] = m[1]
    if ornament:
        _ornament(a, w, h, rim, m, ornament)
    return a


def _ornament(a, w, h, rim, m, kind):
    """Carved corner motif, mirrored into all four corners."""
    pat = {
        'scroll': ["##...", "#.#..", "..##.", "...#.", "....."],
        'flame':  ["..#..", ".##..", "##.#.", "#..#.", "....."],
        'wave':   [".##..", "#..#.", "...#.", "..#..", "....."],
        'leaf':   ["..##.", ".###.", "###..", "#....", "....."],
        'horn':   ["#....", "##...", ".##..", "..###", "....#"],
        'gem':    [".#...", "###..", ".#...", ".....", "....."],
    }[kind]
    accent = {'flame': c('#ffb04a'), 'wave': c('#8ad8ff'), 'leaf': c('#9ae060'),
              'horn': c('#ff8a7a'), 'gem': c('#ff5a5a'), 'scroll': m[4]}[kind]
    off = rim + 2
    for py, row in enumerate(pat):
        for px, ch in enumerate(row):
            if ch != '#':
                continue
            for (x, y) in ((off + px, off + py), (w - 1 - off - px, off + py),
                           (off + px, h - 1 - off - py), (w - 1 - off - px, h - 1 - off - py)):
                if 0 <= x < w and 0 <= y < h:
                    a[y, x] = accent


def button(face_top, face_bot, metal='iron', pressed=False, disabled=False, w=40, h=18):
    """Raised button: metal rim, bevelled face with shine, 2px drop shadow (none when pressed)."""
    m = [c(x) for x in METALS[metal]]
    a = np.zeros((h, w, 4), dtype=np.int32)
    shadow = 0 if pressed else 2
    fh = h - 2
    top = 2 if pressed else 0
    t, b = c(face_top), c(face_bot)
    if disabled:
        t, b = c('#4a4650'), c('#2e2a34')
        m = [c(x) for x in METALS['iron']]
    for y in range(fh):
        yy = y + top
        k = y / (fh - 1)
        for x in range(w):
            e = min(x, y, w - 1 - x, fh - 1 - y)
            corner = min(x, w - 1 - x) + min(y, fh - 1 - y) < 2
            if corner:
                continue
            if e == 0:
                col = m[0]
            elif e == 1:
                col = m[4] if (y == 1 and not pressed) else (m[3] if y < fh / 2 else m[1])
            else:
                col = t * (1 - k) + b * k
                if y == 2 and not disabled:
                    col = col + 50
                elif y < fh * 0.45 and not disabled and not pressed:
                    col = col + 18
            a[yy, x] = col
            a[yy, x, 3] = 255
    if shadow:
        for x in range(2, w - 2):
            for s in range(shadow):
                if a[fh + s, x, 3] == 0:
                    a[fh + s, x] = c('#000000', 150 - s * 50)
    return a


def bar_frame(w=20, h=8, metal='iron'):
    return frame(w, h, metal, rim=1, interior='#0a080c', stone_int=False, ornament=None, rivets=False)


def fill(colors, h=6):
    a = np.zeros((h, 4, 4), dtype=np.int32)
    for i in range(h):
        a[i, :] = c(colors[min(i, len(colors) - 1)])
    return a


# ---------------------------------------------------------------- special pieces
def target_sigil(frame_i, n=8):
    """Original Cinderbound target mark: rotating ember rune ring with four notches."""
    size = 32
    a = np.zeros((size, size, 4), dtype=np.int32)
    cx = cy = (size - 1) / 2
    rot = frame_i / n * (math.pi / 2)
    for y in range(size):
        for x in range(size):
            dx, dy = x - cx, (y - cy) * 1.0
            r = math.hypot(dx, dy)
            ang = math.atan2(dy, dx) - rot
            if 12.5 <= r <= 14.5:
                seg = (ang % (math.pi / 2)) / (math.pi / 2)
                if 0.12 < seg < 0.88:
                    a[y, x] = c('#ffb04a') if r < 13.6 else c('#a8401a')
            elif 9.5 <= r <= 10.4:
                seg = ((ang + math.pi / 4) % (math.pi / 4)) / (math.pi / 4)
                if seg < 0.5:
                    a[y, x] = c('#ffe08a')
    for k in range(4):
        ang = rot + k * math.pi / 2 + math.pi / 4
        for t in range(4):
            x = int(round(cx + math.cos(ang) * (15 - t)))
            y = int(round(cy + math.sin(ang) * (15 - t)))
            for d in range(-(3 - t) // 2, (3 - t) // 2 + 1):
                xx = int(round(x - math.sin(ang) * d))
                yy = int(round(y + math.cos(ang) * d))
                if 0 <= xx < size and 0 <= yy < size:
                    a[yy, xx] = c('#fff0c0')
    return a


def chevron():
    cv = Canvas(16, 12)
    cv.part(cv.mask().poly([(1, 1), (14, 1), (7.5, 10)]), Pal('#ffb04a', '#fff0c0', '#c0501a'))
    cv.outline()
    return np.array(cv.image()).astype(np.int32)


def leader_emblem():
    """Flame crown badge (original)."""
    cv = Canvas(16, 16)
    cv.part(cv.mask().poly([(1, 13), (1, 6), (4, 9), (8, 2), (12, 9), (15, 6), (15, 13)]),
            Pal('#f0b030', '#fff0a0', '#a06a10'))
    cv.part(cv.mask().rect(2, 12, 14, 14), Pal('#c0501a', '#ff9a4a', '#7a2a10'))
    cv.dot(8, 6, hexc('#ff5a3a'))
    cv.dot(8, 7, hexc('#ffb04a'))
    cv.outline()
    return cv.image()


def ko_stamp():
    cv = Canvas(24, 14)
    cv.part(cv.mask().rect(1, 1, 22, 12), Pal('#8a1a1a', '#c04040', '#5a0e0e'))
    img = np.array(cv.image())
    return img


def hand_pointer():
    """Pointing hand (index finger up) for tutorial coach marks."""
    cv = Canvas(16, 16)
    m = cv.mask().rect(6, 1, 8, 8).rect(5, 7, 12, 13).rect(3, 9, 5, 11)
    cv.part(m, Pal('#f4d0b0', '#fff0e0', '#c09070'))
    for x in (9, 11):
        cv.dot(x, 8, hexc('#c09070'))
    cv.part(cv.mask().rect(5, 13, 12, 14), Pal('#3a78d8', '#8ab8ff', '#1a3a8a'))
    cv.outline()
    return cv.image()


def node(kind):
    size = 32 if kind == 'boss' else 24
    cv = Canvas(size, size)
    ccx = ccy = size / 2 - 0.5
    if kind == 'boss':
        cv.part(cv.mask().ellipse(ccx, ccy + 1, 13, 12), Pal('#4a0e16', '#7a1a22', '#2a060a'))
        cv.part(cv.mask().ellipse(ccx, ccy + 1, 10, 9), Pal('#c0303a', '#ff6a5a', '#7a1a22'))
        # horned skull-mask
        cv.part(cv.mask().poly([(6, 6), (2, 1), (10, 7)]), Pal('#e0d8c0', '#ffffff', '#9a9280'))
        cv.part(cv.mask().poly([(25, 6), (29, 1), (21, 7)]), Pal('#e0d8c0', '#ffffff', '#9a9280'))
        cv.part(cv.mask().ellipse(ccx, ccy + 1, 6, 5.5).rect(12, 17, 19, 21), Pal('#f0e8d0', '#ffffff', '#b0a890'))
        for (x, y) in ((13, 15), (18, 15)):
            cv.dot(x, y, hexc('#1a0a0a'))
            cv.dot(x + 1, y, hexc('#1a0a0a'))
            cv.dot(x, y - 1, hexc('#ff3a2a'))
    else:
        ring = {'locked': Pal('#3a3640', '#5a5660', '#24202a'), 'open': Pal('#6a4410', '#e0a83a', '#3a2408'),
                'cleared': Pal('#6a5a28', '#d0c078', '#3a2e14')}[kind]
        core = {'locked': Pal('#4a4650', '#6a6670', '#2e2a34'), 'open': Pal('#ff7a2a', '#ffe08a', '#c0401a'),
                'cleared': Pal('#4ab02a', '#b0f070', '#2a6a18')}[kind]
        cv.part(cv.mask().ellipse(ccx, ccy, 10.5, 10.5), ring)
        cv.part(cv.mask().ellipse(ccx, ccy, 7.5, 7.5), core)
        if kind == 'open':
            cv.part(cv.mask().poly([(12, 5), (16, 11), (12, 18), (8, 11)]), Pal('#fff0c0', '#ffffff', '#ffb04a'))
        elif kind == 'cleared':
            cv.part(cv.mask().rect(10, 5, 11, 17), Pal('#5a3a1e'), flat=True)
            cv.part(cv.mask().poly([(11, 5), (17, 7), (11, 10)]), Pal('#e0342a', '#ff8a6a', '#8a1a14'))
        else:
            m = cv.mask().rect(9, 10, 14, 15)
            cv.part(m, Pal('#9aa4b4', '#d0d8e4', '#5f6776'))
            cv.part(cv.mask().rect(10, 6, 13, 9).subtract(cv.mask().rect(11, 7, 12, 9)), Pal('#9aa4b4', '#d0d8e4', '#5f6776'))
    cv.outline()
    return cv.image()


def separator(w=48):
    a = np.zeros((5, w, 4), dtype=np.int32)
    for x in range(w):
        a[2, x] = c('#5a5660')
        a[1, x] = c('#16121a')
        a[3, x] = c('#16121a')
    mid = w // 2
    for (dx, dy) in ((0, 0), (-1, 1), (1, 1), (0, 2), (-2, 2), (2, 2), (-1, 3), (1, 3), (0, 4)):
        a[dy, mid + dx] = c('#ffb04a') if dy in (1, 2, 3) and abs(dx) < 2 else c('#a8401a')
    return a


def gesture_arrow(up=True):
    cv = Canvas(16, 16)
    pts = [(8, 1), (14, 8), (10, 8), (10, 14), (6, 14), (6, 8), (2, 8)]
    if not up:
        pts = [(x, 15 - y) for (x, y) in pts]
    cv.part(cv.mask().poly(pts), Pal('#ffd35a', '#fff6c8', '#e08a1c') if up else Pal('#8ab8ff', '#e0f0ff', '#3a6ad0'))
    cv.outline()
    return cv.image()


def reward_slot():
    return frame(24, 24, 'bronze', rim=2, interior='#1a1418', stone_int=True, ornament=None, rivets=False, inset=True)


# ---------------------------------------------------------------- icons (16x16, shared style)
def icon(draw):
    cv = Canvas(16, 16)
    draw(cv)
    cv.outline()
    return cv.image()


def orb(color):
    cv = Canvas(16, 16)
    base = hexc(color)
    hi = tuple(min(255, int(v * 0.45 + 255 * 0.55)) for v in base[:3]) + (255,)
    lo = tuple(int(v * 0.45) for v in base[:3]) + (255,)
    cv.part(cv.mask().ellipse(7.5, 7.5, 6.6, 6.6), Pal(base, hi, lo))
    a = np.array(cv.image())
    for (x, y) in ((5, 3), (6, 3), (4, 4), (5, 4), (4, 5)):
        a[y, x] = (255, 255, 255, 255)
    img = Image.fromarray(a, 'RGBA')
    cv2 = Canvas(16, 16)
    cv2.px = np.array(img)
    cv2.outline()
    return cv2.image()


def element_glyph(kind):
    """Orb with a tiny element glyph so the element is readable without colour."""
    col = {'fire': '#ff5a2a', 'water': '#2a8ae0', 'nature': '#4ab02a'}[kind]
    img = np.array(orb(col))
    pats = {'fire': ["..#..", ".##..", ".###.", "##.##", ".###."],
            'water': ["..#..", "..#..", ".###.", "#####", ".###."],
            'nature': ["...##", "..###", ".###.", "###..", "#...."]}
    for py, row in enumerate(pats[kind]):
        for px, ch in enumerate(row):
            if ch == '#':
                img[5 + py, 5 + px] = (255, 255, 255, 255)
    return Image.fromarray(img, 'RGBA')


def build():
    os.makedirs(UI, exist_ok=True)
    os.makedirs(ICONS, exist_ok=True)
    # panels ------------------------------------------------------
    save3(to_img(frame(32, 32, 'iron', rim=3, interior='#221e28', ember_line='#c0501a', ornament='scroll', seed=1)), 'v2_panel')
    save3(to_img(frame(24, 24, 'iron', rim=2, interior='#141018', ornament=None, rivets=False, inset=True, seed=2)), 'v2_inset')
    save3(to_img(frame(32, 16, 'wood', rim=2, interior='#5a3a1e', stone_int=False, ornament=None, seed=3)), 'v2_plank')
    save3(to_img(frame(32, 32, 'crimson', rim=3, interior='#1e0c10', ember_line='#ff6a3a', ornament='horn', seed=4)), 'v2_boss')
    save3(to_img(frame(32, 20, 'iron', rim=2, interior='#1c1418', ember_line='#c0303a', ornament='gem', seed=5)), 'v2_enemy')
    for el, metal, orn, line in (('fire', 'ember', 'flame', '#ffb04a'), ('water', 'steel', 'wave', '#8ad8ff'),
                                 ('nature', 'bronze', 'leaf', '#9ae060'), ('neutral', 'iron', 'scroll', None)):
        save3(to_img(frame(32, 24, metal, rim=2, interior='#1a161e', ember_line=line, ornament=orn, seed=6)), 'v2_card_' + el)
        save3(to_img(frame(32, 24, metal, rim=2, interior='#2a2432', ember_line='#fff0b0', ornament=orn, seed=6)), 'v2_card_%s_lit' % el)
    # rarity frames (unit tiles)
    save3(to_img(frame(32, 32, 'bronze', rim=2, interior='#1a161e', ornament=None, rivets=False, seed=7)), 'v2_rarity_3')
    save3(to_img(frame(32, 32, 'silver', rim=3, interior='#1a161e', ornament='scroll', rivets=True, seed=7)), 'v2_rarity_4')
    save3(to_img(frame(32, 32, 'gold', rim=3, interior='#1a161e', ember_line='#fff0b0', ornament='gem', rivets=True, seed=7)), 'v2_rarity_5')
    save3(to_img(frame(32, 32, 'prism', rim=3, interior='#1a161e', ember_line='#e8d8ff', ornament='gem', rivets=True, seed=7)), 'v2_rarity_6')
    # buttons -----------------------------------------------------
    for name, (t, b, metal) in {'ember': ('#e0602a', '#8a2412', 'iron'), 'steel': ('#4a6a98', '#1e3050', 'iron'),
                                'gold': ('#f0c048', '#9a661a', 'gold'), 'stone': ('#5a5462', '#322e38', 'iron')}.items():
        save3(to_img(button(t, b, metal)), 'v2_btn_%s' % name)
        save3(to_img(button(t, b, metal, pressed=True)), 'v2_btn_%s_p' % name)
    save3(to_img(button('#000000', '#000000', disabled=True)), 'v2_btn_off')
    # nav ---------------------------------------------------------
    save3(to_img(frame(24, 24, 'iron', rim=2, interior='#141018', ornament=None, rivets=False, inset=True, seed=8)), 'v2_nav')
    save3(to_img(frame(24, 24, 'ember', rim=2, interior='#3a1a14', ember_line='#ffc070', ornament=None, rivets=False, seed=8)), 'v2_nav_on')
    # chips (filters)
    save3(to_img(button('#3a3640', '#221e28', 'iron', w=24, h=12)), 'v2_chip')
    save3(to_img(button('#c0501a', '#6a1e0e', 'gold', w=24, h=12)), 'v2_chip_on')
    # bars --------------------------------------------------------
    save3(to_img(bar_frame()), 'v2_bar')
    save3(to_img(bar_frame(metal='crimson')), 'v2_bar_boss')
    fills = {
        'hp_high': ['#d8ffb0', '#8ae05a', '#5ac83a', '#3aa02a', '#2a8020', '#1e6018'],
        'hp_mid': ['#fff0a0', '#f0d040', '#e0b020', '#c09018', '#a07010', '#7a5008'],
        'hp_low': ['#ffc0b0', '#ff6a4a', '#e03a2a', '#c02418', '#961810', '#6a0c08'],
        'lag': ['#ffffff', '#fff0e0', '#ffe0c8', '#f0c8b0', '#e0b098', '#c09080'],
        'burst': ['#c8f8ff', '#6ae0ff', '#3ab0f0', '#2a88d8', '#1e68b8', '#164c90'],
        'burst_ready': ['#fffcd8', '#ffe070', '#ffc040', '#f0a020', '#d07818', '#a05410'],
        'enemy': ['#ffb0a0', '#ff5a4a', '#e0342a', '#c02418', '#961810', '#6a0c08'],
        'boss': ['#ffb0c0', '#ff4a6a', '#d0243a', '#a01830', '#700e22', '#4a0816'],
        'xp': ['#e8d8ff', '#c0a8ff', '#a890f0', '#8a70d8', '#6a50b8', '#4a3490'],
        'stat': ['#fff0c0', '#ffc86a', '#f0a040', '#d07828', '#a0561a', '#703a10'],
        'break': ['#fffce0', '#fff0a0', '#e8d060', '#c8a838', '#9a7c24', '#6a5418'],
    }
    for k, v in fills.items():
        save3(to_img(fill(v)), 'v2_fill_' + k)
    # misc --------------------------------------------------------
    for i in range(8):
        save1(to_img(target_sigil(i)), 'v2_target_%d' % i, UI)
    save1(to_img(chevron()), 'v2_chevron', UI)
    save3(to_img(separator()), 'v2_separator')
    save3(to_img(reward_slot()), 'v2_slot')
    for k in ('locked', 'open', 'cleared', 'boss'):
        save1(node(k), 'v2_node_' + k, UI)
    save1(leader_emblem(), 'leader', ICONS)
    save1(hand_pointer(), 'hand', ICONS)
    save1(gesture_arrow(True), 'gesture_up', ICONS)
    save1(gesture_arrow(False), 'gesture_down', ICONS)
    # standardised nav icons (16x16 at 1x, same outline/light as every other icon)
    import ui_mobile as um

    def ic_menu(cv):
        cv.part(cv.mask().rect(3, 2, 12, 13), Pal('#e8d8b0', '#fff6e0', '#b0986a'))
        cv.part(cv.mask().rect(2, 1, 13, 2).rect(2, 13, 13, 14), Pal('#8a5a2a', '#b07a40', '#5a3a1a'))
        for y in (5, 7, 9, 11):
            for x in range(5, 11):
                cv.dot(x, y, hexc('#7a6a50'))
    for name, fn in (('home', um.ic_home), ('units', um.ic_units), ('quest', um.ic_quest), ('bag', um.ic_bag),
                     ('summon', um.ic_summon), ('shop', um.ic_shop), ('settings', um.ic_settings), ('menu', ic_menu)):
        save1(um.icon(fn), 'nav_' + name)
    # standardised element orbs (16x16, with glyph)
    for el in ('fire', 'water', 'nature'):
        save1(element_glyph(el), 'orb_' + el)
    print('ui v2 generated')


if __name__ == '__main__':
    build()
