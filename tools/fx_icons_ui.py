"""Effects, icons and UI textures for Cinderbound (all original, procedurally drawn)."""
import math
import random
import numpy as np
from PIL import Image
from pixlib import Canvas, Pal, hexc, mix, darken, lighten


def img_from(arr):
    return Image.fromarray(arr.astype(np.uint8), 'RGBA')


def blank(w, h):
    return np.zeros((h, w, 4), dtype=np.uint8)


def put(a, x, y, c):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < a.shape[1] and 0 <= y < a.shape[0]:
        a[y, x] = c if len(c) == 4 else tuple(c) + (255,)


# ------------------------------------------------------------------ EFFECTS
def arc_slash(colors, frames=5, size=48, r=17, width=4, start=-70, sweep=150):
    """Crescent slash that sweeps then fades (facing right)."""
    out = []
    for f in range(frames):
        a = blank(size, size)
        prog = min(1.0, (f + 1) / (frames - 2))
        fade = max(0, f - (frames - 3))
        cx, cy = size / 2 - 6, size / 2
        end = start + sweep * prog
        s0 = max(start, end - sweep * 0.8)
        steps = 90
        for i in range(steps + 1):
            ang = math.radians(s0 + (end - s0) * i / steps)
            t = i / steps  # 0 tail -> 1 head
            wid = max(1, int(round(width * t))) - fade
            for w in range(wid):
                rr = r - w
                c = colors[min(len(colors) - 1, w)]
                put(a, cx + math.cos(ang) * rr, cy + math.sin(ang) * rr, c)
        out.append(img_from(a))
    return out


def burst_star(colors, frames=4, size=24, rays=8):
    out = []
    for f in range(frames):
        a = blank(size, size)
        c = size / 2
        ln = [3, 7, 9, 6][f % 4] if frames == 4 else 2 + f * 2
        for k in range(rays):
            ang = k * 2 * math.pi / rays + (0.2 if f % 2 else 0)
            L = ln if k % 2 == 0 else ln * 0.55
            for d in range(int(L)):
                col = colors[min(2, d * 3 // max(1, int(L)))]
                if f == frames - 1 and d < L * 0.5:
                    continue
                put(a, c + math.cos(ang) * d, c + math.sin(ang) * d, col)
        if f < 2:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    put(a, c + dx, c + dy, colors[0])
        out.append(img_from(a))
    return out


def orb(colors, frames=4, size=16):
    out = []
    for f in range(frames):
        cv = Canvas(size, size)
        m = cv.mask().ellipse(size / 2 + 1, size / 2, 3.5 + (f % 2) * 0.5, 3.2)
        cv.part(m, Pal(colors[1], colors[0], colors[2]))
        a = np.array(cv.image())
        # trail
        for k in range(4):
            put(a, size / 2 - 4 - k * 1.5, size / 2 + ((f + k) % 3 - 1), colors[2] if k < 2 else colors[1])
        put(a, size / 2, size / 2 - 1, (255, 255, 255, 255))
        out.append(img_from(a))
    return out


def splash(colors, frames=5, size=32, seed=1):
    rng = random.Random(seed)
    parts = [(rng.uniform(0, 2 * math.pi), rng.uniform(0.5, 1.0)) for _ in range(16)]
    out = []
    for f in range(frames):
        a = blank(size, size)
        c = size / 2
        rad = 3 + f * 3
        for (ang, sp) in parts:
            d = rad * sp
            x, y = c + math.cos(ang) * d, c + math.sin(ang) * d * 0.8
            col = colors[(f + int(sp * 3)) % len(colors)]
            put(a, x, y, col)
            if f < frames - 2:
                put(a, x + 1, y, col)
                put(a, x, y + 1, col)
        # ring
        if f < frames - 1:
            for i in range(40):
                ang = i / 40 * 2 * math.pi
                put(a, c + math.cos(ang) * rad * 0.7, c + math.sin(ang) * rad * 0.5, colors[0])
        out.append(img_from(a))
    return out


def flame_burst(frames=6, size=32, seed=2):
    rng = random.Random(seed)
    cols = [hexc('#fff3a8'), hexc('#ffc14a'), hexc('#ff7a22'), hexc('#d8391a'), hexc('#6a1c14')]
    out = []
    for f in range(frames):
        a = blank(size, size)
        c = size / 2
        R = 4 + f * 2.2
        for y in range(size):
            for x in range(size):
                dx, dy = x - c, (y - c) * 1.1
                d = math.hypot(dx, dy) + rng.uniform(-1.8, 1.8) - max(0, -dy) * 0.25
                if d < R:
                    t = d / R + f * 0.1
                    idx = min(4, int(t * 4))
                    if f >= frames - 2 and rng.random() < 0.45:
                        continue
                    a[y, x] = cols[idx]
        out.append(img_from(a))
    return out


def leaf_burst(frames=5, size=32, seed=5):
    rng = random.Random(seed)
    leaves = [(rng.uniform(0, 2 * math.pi), rng.uniform(0.4, 1.0), rng.randint(0, 2)) for _ in range(12)]
    cols = [hexc('#a9dd62'), hexc('#6fb33a'), hexc('#3f7a22')]
    out = []
    for f in range(frames):
        a = blank(size, size)
        c = size / 2
        for (ang, sp, ci) in leaves:
            d = (2 + f * 3.2) * sp
            x, y = c + math.cos(ang) * d, c + math.sin(ang) * d + f * 0.6
            put(a, x, y, cols[ci])
            put(a, x + 1, y, cols[(ci + 1) % 3])
            if f < 3:
                put(a, x, y - 1, cols[0])
        if f < 2:
            for i in range(-3, 4):
                put(a, c + i, c, hexc('#e8ffc0'))
                put(a, c, c + i, hexc('#e8ffc0'))
        out.append(img_from(a))
    return out


def heal_ring(frames=7, w=96, h=32):
    cols = [hexc('#e6ffff'), hexc('#7fe8f4'), hexc('#35b8d8'), hexc('#1c7ea8')]
    out = []
    for f in range(frames):
        a = blank(w, h)
        cx, cy = w / 2, h / 2
        for ring in range(2):
            rx = 8 + (f - ring * 2) * 6.5
            if rx <= 4:
                continue
            ry = rx * 0.3
            steps = int(rx * 6)
            for i in range(steps):
                ang = i / steps * 2 * math.pi
                col = cols[min(3, ring + f // 3)]
                if f >= frames - 2 and i % 2:
                    continue
                put(a, cx + math.cos(ang) * rx, cy + math.sin(ang) * ry, col)
                if ring == 0:
                    put(a, cx + math.cos(ang) * (rx - 1), cy + math.sin(ang) * ry, cols[min(3, ring + 1)])
        # rising sparkles
        for k in range(8):
            x = cx + math.cos(k * 1.3) * (10 + k * 4)
            y = cy - f * 2 + (k % 3)
            if 0 < f < frames - 1:
                put(a, x, y, cols[0])
        out.append(img_from(a))
    return out


def roots(frames=6, w=64, h=48, seed=9):
    rng = random.Random(seed)
    bark = Pal('#6e4a2e', '#936644', '#4c321f', '#2c1c10')
    tips = [(rng.randint(4, w - 5), rng.randint(6, 22), rng.choice([-1, 1])) for _ in range(6)]
    out = []
    for f in range(frames):
        cv = Canvas(w, h)
        grow = min(1.0, (f + 1) / 4)
        for i, (tx, ty, bend) in enumerate(tips):
            bx = tx - bend * 4
            m = cv.mask()
            steps = 10
            last = (bx, h - 1)
            for s in range(1, int(steps * grow) + 1):
                t = s / steps
                x = bx + (tx - bx) * t + math.sin(t * 3 + i) * 2 * bend
                y = (h - 1) + (ty - (h - 1)) * t
                m.line(last[0], last[1], x, y, max(1, int(4 - t * 3)))
                last = (x, y)
            cv.part(m, bark)
            if grow >= 1 and f < frames - 1:
                cv.dot(last[0], last[1] - 1, hexc('#7cc043'))
                cv.dot(last[0] + 1, last[1] - 1, hexc('#a9dd62'))
        cv.outline()
        img = cv.image()
        if f == frames - 1:
            a = np.array(img)
            a[:, :, 3] = (a[:, :, 3] * 0.5).astype(np.uint8)
            img = Image.fromarray(a, 'RGBA')
        out.append(img)
    return out


def bubble(frames=3, size=12):
    out = []
    for f in range(frames):
        a = blank(size, size)
        c = size / 2
        r = 3 + (f % 2) * 0.5
        for i in range(24):
            ang = i / 24 * 2 * math.pi
            put(a, c + math.cos(ang) * r, c + math.sin(ang) * r, hexc('#9fe8ff'))
        put(a, c - 1, c - 2, (255, 255, 255, 255))
        put(a, c - 2, c - 1, (255, 255, 255, 255))
        out.append(img_from(a))
    return out


def embers(frames=6, w=48, h=48, seed=11):
    rng = random.Random(seed)
    pts = [(rng.uniform(4, w - 4), rng.uniform(h * 0.5, h), rng.uniform(0.6, 1.4)) for _ in range(14)]
    cols = [hexc('#fff0a0'), hexc('#ffb03a'), hexc('#ff6a1e')]
    out = []
    for f in range(frames):
        a = blank(w, h)
        for i, (x, y, sp) in enumerate(pts):
            yy = y - f * 5 * sp
            if 0 <= yy < h:
                put(a, x + math.sin(f + i) * 1.5, yy, cols[(i + f) % 3])
        out.append(img_from(a))
    return out


def strip(frames):
    w, h = frames[0].size
    out = Image.new('RGBA', (w * len(frames), h), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        out.paste(f, (i * w, 0), f)
    return out


EFFECTS = {
    'slash_ember': (lambda: arc_slash([hexc('#fff6c8'), hexc('#ffc14a'), hexc('#ff7a22'), hexc('#c8361a')]), 48, 48, 22),
    'slash_steel': (lambda: arc_slash([hexc('#ffffff'), hexc('#d8e0ec'), hexc('#8e98a8')], width=3), 48, 48, 22),
    'slash_heavy': (lambda: arc_slash([hexc('#ffffff'), hexc('#ffe27a'), hexc('#ff8a2a'), hexc('#d8391a'),
                                       hexc('#8a1c10')], frames=6, r=21, width=6, start=-100, sweep=190), 48, 48, 20),
    'hit_spark': (lambda: burst_star([hexc('#ffffff'), hexc('#ffe27a'), hexc('#ff9a3a')]), 24, 24, 20),
    'hit_water': (lambda: splash([hexc('#e6ffff'), hexc('#7fe8f4'), hexc('#35b8d8')]), 32, 32, 16),
    'hit_nature': (lambda: leaf_burst(), 32, 32, 16),
    'hit_fire': (lambda: flame_burst(), 32, 32, 18),
    'water_bolt': (lambda: orb([hexc('#e6ffff'), hexc('#5ee6f0'), hexc('#1c7ea8')]), 16, 16, 12),
    'bubble': (lambda: bubble(), 12, 12, 8),
    'heal_ring': (lambda: heal_ring(), 96, 32, 12),
    'roots': (lambda: roots(), 64, 48, 10),
    'embers': (lambda: embers(), 48, 48, 12),
}


# ------------------------------------------------------------------ ICONS (16x16)
def icon_canvas():
    return Canvas(16, 16)


def icon_gold():
    cv = icon_canvas()
    cv.part(cv.mask().ellipse(8, 8, 5.5, 6), Pal('#f0c040', '#fff0a0', '#b8841c'))
    cv.part(cv.mask().ellipse(8, 8, 3, 3.5), Pal('#e0a830', '#f8d868', '#a8741a'), separate=False)
    cv.dot(8, 6, hexc('#fff6c8'))
    cv.dot(8, 7, hexc('#b8841c'))
    cv.dot(8, 9, hexc('#b8841c'))
    cv.outline()
    return cv.image()


def icon_herb():
    cv = icon_canvas()
    stem = cv.mask().line(8, 14, 8, 6, 1)
    cv.part(stem, Pal('#4a7a26'))
    for (x, y, a) in ((5, 7, 1), (11, 6, -1), (6, 11, 1), (10, 10, -1), (8, 3, 0)):
        cv.part(cv.mask().ellipse(x, y, 2.6, 1.6), Pal('#6fb33a', '#a9dd62', '#3f7a22'))
    cv.dot(8, 2, hexc('#ff8ab0'))
    cv.dot(9, 3, hexc('#ffd0e0'))
    cv.outline()
    return cv.image()


def icon_shard(pal):
    cv = icon_canvas()
    cv.part(cv.mask().poly([(8, 1), (12, 6), (10, 14), (6, 14), (4, 6)]), pal)
    cv.part(cv.mask().poly([(8, 2), (10, 6), (8, 12), (7, 6)]), Pal(pal.hi, lighten(pal.hi, 0.5), pal.base),
            separate=False)
    cv.outline()
    return cv.image()


def icon_fire():
    cv = icon_canvas()
    cv.part(cv.mask().poly([(8, 1), (12, 7), (13, 11), (10, 15), (6, 15), (3, 11), (4, 7), (6, 9)]),
            Pal('#ff6a22', '#ffb04a', '#c8361a'))
    cv.part(cv.mask().poly([(8, 7), (10, 11), (9, 14), (7, 14), (6, 11)]), Pal('#ffd35a', '#fff3a8', '#ff9a2e'),
            separate=False)
    cv.outline()
    return cv.image()


def icon_water():
    cv = icon_canvas()
    m = cv.mask().ellipse(8, 10, 4.5, 4.5)
    m.poly([(8, 1), (12, 9), (4, 9)])
    cv.part(m, Pal('#3aa0e0', '#9ee6ff', '#1f5fa8'))
    cv.dot(6, 9, hexc('#e6ffff'))
    cv.dot(6, 10, hexc('#e6ffff'))
    cv.outline()
    return cv.image()


def icon_nature():
    cv = icon_canvas()
    cv.part(cv.mask().poly([(13, 2), (14, 8), (10, 13), (4, 14), (3, 10), (6, 5)]), Pal('#5aa832', '#9cd75a', '#2f6a1c'))
    cv.part(cv.mask().line(4, 14, 11, 5, 1), Pal('#2f6a1c'), shade=False, separate=False)
    cv.outline()
    return cv.image()


def icon_star(filled=True):
    cv = icon_canvas()
    pts = []
    for i in range(10):
        r = 7 if i % 2 == 0 else 3
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((8 + math.cos(a) * r, 8.5 + math.sin(a) * r))
    cv.part(cv.mask().poly(pts), Pal('#f8c830', '#fff0a0', '#c88a18') if filled else Pal('#4a4a58', '#6a6a7a', '#34343e'))
    cv.outline()
    return cv.image()


def icon_sword():
    cv = icon_canvas()
    cv.part(cv.mask().line(4, 12, 13, 3, 2), Pal('#c9d1dc', '#ffffff', '#8e98a8'))
    cv.part(cv.mask().line(3, 9, 7, 13, 2), Pal('#c49a3a', '#f0cd6a', '#8a6a24'))
    cv.part(cv.mask().line(2, 14, 4, 12, 2), Pal('#5a3622'))
    cv.outline()
    return cv.image()


def icon_shield():
    cv = icon_canvas()
    cv.part(cv.mask().poly([(3, 2), (13, 2), (13, 8), (8, 14), (3, 8)]), Pal('#6a8ab0', '#a8c4e0', '#3e5a80'))
    cv.part(cv.mask().poly([(6, 4), (10, 4), (10, 8), (8, 10), (6, 8)]), Pal('#c8d4e4', '#ffffff', '#8e9cb0'),
            separate=False)
    cv.outline()
    return cv.image()


def icon_burst():
    cv = icon_canvas()
    pts = []
    for i in range(16):
        r = 7.5 if i % 2 == 0 else 3.5
        a = i * math.pi / 8
        pts.append((8 + math.cos(a) * r, 8 + math.sin(a) * r))
    cv.part(cv.mask().poly(pts), Pal('#ffb03a', '#fff0a0', '#e0601c'))
    cv.part(cv.mask().ellipse(8, 8, 2.5, 2.5), Pal('#ffffff', '#ffffff', '#ffe27a'), separate=False)
    cv.outline()
    return cv.image()


def icon_lock():
    cv = icon_canvas()
    m = cv.mask().rect(5, 3, 10, 8)
    m.subtract(cv.mask().rect(7, 5, 8, 8))
    cv.part(m, Pal('#9aa4b4', '#d0d8e4', '#5f6776'))
    cv.part(cv.mask().rect(3, 8, 12, 14), Pal('#c49a3a', '#f0cd6a', '#8a6a24'))
    cv.dot(7, 10, hexc('#3a2a10'))
    cv.dot(7, 11, hexc('#3a2a10'))
    cv.dot(8, 10, hexc('#3a2a10'))
    cv.dot(8, 11, hexc('#3a2a10'))
    cv.outline()
    return cv.image()


def icon_check():
    cv = icon_canvas()
    cv.part(cv.mask().line(3, 8, 6, 12, 2).line(6, 12, 13, 4, 2), Pal('#7ae05a', '#c0ff9a', '#3a9a2a'))
    cv.outline()
    return cv.image()


def icon_burn():
    return icon_fire()


def icon_def_up():
    cv = icon_canvas()
    cv.part(cv.mask().poly([(3, 3), (11, 3), (11, 8), (7, 13), (3, 8)]), Pal('#6a8ab0', '#a8c4e0', '#3e5a80'))
    cv.part(cv.mask().poly([(12, 5), (15, 9), (13, 9), (13, 14), (11, 14), (11, 9), (9, 9)]),
            Pal('#7ae05a', '#c0ff9a', '#3a9a2a'))
    cv.outline()
    return cv.image()


def icon_guard_wall():
    cv = icon_canvas()
    cv.part(cv.mask().rect(2, 4, 13, 13), Pal('#7a6a58', '#a8967e', '#4e4236'))
    for y in (7, 10):
        for x in range(2, 14):
            cv.dot(x, y, hexc('#3a3026'))
    for (x, y) in ((6, 5), (10, 8), (5, 11), (9, 12), (12, 5)):
        cv.dot(x, y, hexc('#3a3026'))
    cv.part(cv.mask().ellipse(8, 3, 4, 1.5), Pal('#6fa83a', '#9ccf55', '#4a7a26'))
    cv.outline()
    return cv.image()


def icon_taunt():
    cv = icon_canvas()
    cv.part(cv.mask().poly([(8, 1), (15, 14), (1, 14)]), Pal('#e04a3a', '#ff8a6a', '#9a2a20'))
    cv.part(cv.mask().rect(7, 5, 8, 10), Pal('#ffffff'), flat=True)
    cv.part(cv.mask().rect(7, 12, 8, 12), Pal('#ffffff'), flat=True)
    cv.outline()
    return cv.image()


def icon_cursor():
    """Downward target arrow."""
    cv = icon_canvas()
    cv.part(cv.mask().poly([(1, 2), (14, 2), (8, 13)]), Pal('#ffd35a', '#fff6c8', '#e08a1c'))
    cv.outline()
    return cv.image()


def icon_rank():
    cv = icon_canvas()
    cv.part(cv.mask().poly([(2, 3), (14, 3), (14, 10), (8, 14), (2, 10)]), Pal('#8a2a2a', '#c04a3a', '#5a1a1a'))
    cv.part(cv.mask().poly([(8, 5), (9, 8), (12, 8), (9.5, 10), (10.5, 13), (8, 11), (5.5, 13), (6.5, 10), (4, 8), (7, 8)]),
            Pal('#f8c830', '#fff0a0', '#c88a18'), separate=False)
    cv.outline()
    return cv.image()


def icon_xp():
    cv = icon_canvas()
    cv.part(cv.mask().poly([(8, 1), (15, 8), (8, 15), (1, 8)]), Pal('#8a6ae0', '#c0a8ff', '#5a3ab0'))
    cv.part(cv.mask().poly([(8, 4), (11, 8), (8, 12), (5, 8)]), Pal('#d8ccff', '#ffffff', '#a890f0'), separate=False)
    cv.outline()
    return cv.image()


ICONS = {
    'gold': icon_gold, 'herb': icon_herb,
    'shard_fire': lambda: icon_shard(Pal('#ff6a2a', '#ffc070', '#b8301a')),
    'shard_water': lambda: icon_shard(Pal('#3aa0e0', '#a8eaff', '#1f5fa8')),
    'shard_nature': lambda: icon_shard(Pal('#5aa832', '#b0e070', '#2f6a1c')),
    'element_fire': icon_fire, 'element_water': icon_water, 'element_nature': icon_nature,
    'star': icon_star, 'star_empty': lambda: icon_star(False),
    'sword': icon_sword, 'shield': icon_shield, 'burst': icon_burst, 'lock': icon_lock, 'check': icon_check,
    'status_burn': icon_burn, 'status_def_up': icon_def_up, 'status_guard_wall': icon_guard_wall,
    'status_taunt': icon_taunt, 'cursor': icon_cursor, 'rank': icon_rank, 'xp': icon_xp,
}


# ------------------------------------------------------------------ UI TEXTURES
def stone_noise(w, h, base, seed=1, var=10):
    rng = np.random.default_rng(seed)
    n = rng.integers(-var, var + 1, size=(h, w, 1))
    # coarse blotches for a stone feel
    coarse = rng.integers(-var, var + 1, size=((h + 3) // 4, (w + 3) // 4, 1))
    coarse = np.repeat(np.repeat(coarse, 4, axis=0), 4, axis=1)[:h, :w]
    arr = np.zeros((h, w, 4), dtype=np.int32)
    arr[:, :, :3] = np.array(base[:3]) + n // 2 + coarse
    arr[:, :, 3] = 255
    return np.clip(arr, 0, 255)


def panel(w=48, h=48, base=(38, 42, 52), metal=(116, 110, 100), seed=1, rivets=True, inset=False):
    a = stone_noise(w, h, base, seed)
    dark = (14, 12, 18, 255)
    m_hi = tuple(min(255, c + 60) for c in metal) + (255,)
    m_sh = tuple(max(0, c - 45) for c in metal) + (255,)
    m = tuple(metal) + (255,)
    for i in range(w):
        for j in range(h):
            edge = min(i, j, w - 1 - i, h - 1 - j)
            if edge == 0:
                a[j, i] = dark
            elif edge == 1:
                a[j, i] = m_hi if (j == 1 or i == 1) else m
            elif edge == 2:
                a[j, i] = m if not inset else m_sh
            elif edge == 3:
                a[j, i] = m_sh if not inset else dark
            elif edge == 4 and not inset:
                a[j, i] = (max(0, base[0] - 18), max(0, base[1] - 18), max(0, base[2] - 16), 255)
    if rivets:
        for (x, y) in ((6, 6), (w - 7, 6), (6, h - 7), (w - 7, h - 7)):
            a[y, x] = m_hi
            a[y, x + 1] = m
            a[y + 1, x] = m
            a[y + 1, x + 1] = m_sh
    return img_from(a)


def button(state):
    w, h = 48, 24
    if state == 'normal':
        base, metal = (58, 52, 50), (140, 120, 96)
    elif state == 'hover':
        base, metal = (78, 62, 52), (220, 160, 90)
    elif state == 'pressed':
        base, metal = (40, 34, 34), (120, 96, 72)
    else:
        base, metal = (40, 40, 44), (80, 80, 84)
    a = np.array(panel(w, h, base, metal, seed=4, rivets=False))
    if state == 'pressed':
        # inner top shadow for a pressed-in look
        for x in range(4, w - 4):
            a[4, x] = (20, 16, 18, 255)
    if state == 'hover':
        for x in range(5, w - 5):
            a[4, x] = (255, 190, 110, 255)
    return img_from(a)


def bar_frame():
    w, h = 24, 10
    a = blank(w, h)
    for i in range(w):
        for j in range(h):
            edge = min(i, j, w - 1 - i, h - 1 - j)
            if edge == 0:
                a[j, i] = (14, 12, 18, 255)
            elif edge == 1:
                a[j, i] = (120, 110, 96, 255) if j > 1 else (170, 160, 140, 255)
    return img_from(a)


def stage_node(kind):
    cv = Canvas(24, 24)
    if kind == 'locked':
        pal = Pal('#4a4a52', '#6a6a74', '#34343a')
    elif kind == 'open':
        pal = Pal('#d8762a', '#ffb05a', '#9a4a1a')
    elif kind == 'cleared':
        pal = Pal('#4a9a3a', '#8ad060', '#2a6020')
    else:  # boss
        pal = Pal('#a02a2a', '#e05a4a', '#6a1818')
    cv.part(cv.mask().ellipse(12, 12, 9, 9), Pal('#3a3430', '#5a5048', '#241e1a'))
    cv.part(cv.mask().ellipse(12, 12, 6.5, 6.5), pal)
    if kind == 'boss':
        cv.part(cv.mask().poly([(7, 9), (9, 6), (12, 9), (15, 6), (17, 9), (16, 15), (8, 15)]),
                Pal('#f8c830', '#fff0a0', '#c88a18'))
    cv.outline()
    return cv.image()


UI = {
    'panel': lambda: panel(48, 48, (34, 38, 48), (112, 104, 92), seed=1),
    'panel_dark': lambda: panel(48, 48, (22, 24, 32), (88, 82, 74), seed=2, rivets=False),
    'panel_inset': lambda: panel(24, 24, (18, 20, 26), (60, 58, 56), seed=3, rivets=False, inset=True),
    'panel_ember': lambda: panel(48, 48, (46, 30, 28), (200, 120, 60), seed=6),
    'button_normal': lambda: button('normal'),
    'button_hover': lambda: button('hover'),
    'button_pressed': lambda: button('pressed'),
    'button_disabled': lambda: button('disabled'),
    'bar_frame': bar_frame,
    'node_locked': lambda: stage_node('locked'),
    'node_open': lambda: stage_node('open'),
    'node_cleared': lambda: stage_node('cleared'),
    'node_boss': lambda: stage_node('boss'),
}
