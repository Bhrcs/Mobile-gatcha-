"""Portrait, layered battle stages for Cinderbound (original pixel art).

Each environment is written as four RGBA layers, 200x270 px (shown at 6x):
  <name>_far.png    sky + distant silhouettes (moves least)
  <name>_mid.png    treeline / ruins at the horizon
  <name>_ground.png the walkable ground plane in perspective (units stand here)
  <name>_fore.png   foreground framing (grass, reeds, roots) - moves most
The horizon sits at y=HORIZON; the image bottom sits a little below the
battlefield edge, so the ground plane gives formations real depth.
"""
import math
import os
import random
import numpy as np
from PIL import Image

W, H = 200, 270
HORIZON = 150
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Content'))  # game content root


def hx(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64)


class Layer:
    def __init__(self, seed=1):
        self.c = np.zeros((H, W, 3))
        self.a = np.zeros((H, W))
        self.rng = random.Random(seed)

    def px(self, x, y, col, alpha=1.0):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < W and 0 <= y < H:
            self.c[y, x] = hx(col) if isinstance(col, str) else col
            self.a[y, x] = max(self.a[y, x], alpha)

    def rect(self, x0, y0, x1, y1, col):
        for y in range(int(y0), int(y1)):
            for x in range(int(x0), int(x1)):
                self.px(x, y, col)

    def gradient(self, stops, y0, y1, bands=8):
        cols = [hx(c) for c in stops]
        for y in range(y0, y1):
            t = (y - y0) / max(1, (y1 - y0 - 1))
            for x in range(W):
                tt = t * bands + BAYER[y % 4, x % 4] - 0.5
                tt = min(max(tt / bands, 0), 1)
                seg = tt * (len(cols) - 1)
                i = min(int(seg), len(cols) - 2)
                q = round((seg - i) * 3) / 3
                self.c[y, x] = cols[i] * (1 - q) + cols[i + 1] * q
                self.a[y, x] = 1.0

    def ellipse(self, cx, cy, rx, ry, col, dither=False):
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                d = ((x - cx) / max(rx, .5)) ** 2 + ((y - cy) / max(ry, .5)) ** 2
                if d <= 1:
                    if dither and d > 0.75 and (x + y) % 2:
                        continue
                    self.px(x, y, col)

    def ridge(self, base, amp, col, seed, freq=0.05, col2=None, bottom=H):
        rng = random.Random(seed)
        ph = [rng.uniform(0, 100) for _ in range(3)]
        c, c2 = hx(col), hx(col2 or col)
        for x in range(W):
            y = int(base - amp * (0.6 * math.sin(x * freq + ph[0]) + 0.3 * math.sin(x * freq * 2.7 + ph[1])
                                  + 0.1 * math.sin(x * freq * 7 + ph[2])))
            for yy in range(max(0, y), bottom):
                self.px(x, yy, c if (yy - y) > 2 or (x + yy) % 2 else c2)

    def conifer(self, x, base, h, dark, mid, light):
        d, m, l = hx(dark), hx(mid), hx(light)
        for yy in range(h):
            y = base - yy
            half = int((h - yy) * 0.33 + 1 + ((yy % 5) < 2) * 1.2)
            for xx in range(-half, half + 1):
                c = d
                if xx < -half * 0.3:
                    c = l if (yy % 5) >= 2 else m
                elif xx < half * 0.3:
                    c = m
                self.px(x + xx, y, c)
        for yy in range(3):
            self.px(x, base + yy, d * 0.7)

    def round_tree(self, x, base, h, trunk, leaves):
        tc = hx(trunk)
        for yy in range(int(h * 0.45)):
            for xx in (-1, 0, 1):
                self.px(x + xx, base - yy, tc if xx < 1 else tc * 0.7)
        cols = [hx(c) for c in leaves]
        r = h * 0.35
        for (bx, by, br) in [(0, -h * 0.6, r), (-r * 0.7, -h * 0.5, r * .75), (r * .7, -h * .5, r * .75), (0, -h * .8, r * .7)]:
            for yy in range(int(-br), int(br) + 1):
                for xx in range(int(-br), int(br) + 1):
                    if xx * xx + yy * yy <= br * br:
                        sh = (xx + yy) / (br * 2)
                        i = 0 if sh < -0.25 else (1 if sh < 0.15 else 2)
                        if abs(xx * xx + yy * yy - br * br) < br * 1.5 and (xx + yy) % 2:
                            i = 2
                        self.px(x + bx + xx, base + by + yy, cols[i])

    def pillar(self, x, base, h, w=8, stone='#8a8478', moss=True):
        s = hx(stone)
        top = base - h
        for y in range(top, base):
            for xx in range(w):
                c = s * (1.18 if xx < 2 else (0.72 if xx > w - 3 else 1.0))
                if (y - top) % 8 == 0:
                    c = s * 0.6
                self.px(x + xx, y, c)
        for xx in range(w):   # broken top
            cut = int(3 * abs(math.sin(xx * 1.7 + x)))
            for y in range(top, top + cut):
                self.a[y, int(x + xx)] = 0 if 0 <= x + xx < W else 0
        if moss:
            for xx in range(-1, w + 1):
                if (xx + x) % 3:
                    self.px(x + xx, top + int(abs(math.sin(xx + x)) * 3) + 1, '#5a8a32')
        for y in range(base - 3, base):
            for xx in range(-2, w + 2):
                self.px(x + xx, y, s * 0.85)

    def arch(self, x, base, w, h, stone='#7a746a'):
        s = hx(stone)
        th = 6
        for xx in range(w):
            for y in range(base - h, base):
                ix = (xx - w / 2) / (w / 2 - th)
                iy = (base - h * 0.4 - y) / (h * 0.6 - th)
                oy = (base - h * 0.4 - y) / (h * 0.6)
                ox = (xx - w / 2) / (w / 2)
                if ox ** 2 + max(oy, 0) ** 2 <= 1 and not (abs(ix) < 1 and ix ** 2 + max(iy, 0) ** 2 <= 1):
                    c = s * (1.12 if xx < w / 2 else 0.85)
                    if (y + (xx // 5) * 3) % 6 == 0:
                        c = s * 0.6
                    self.px(x + xx, y, c)

    def ground_plane(self, far, near, detail, seed=3, stripes=True):
        """Perspective ground: colour ramps from far to near, detail marks grow with depth."""
        rng = random.Random(seed)
        f, n = hx(far), hx(near)
        for y in range(HORIZON, H):
            t = (y - HORIZON) / (H - HORIZON)
            for x in range(W):
                base = f * (1 - t) + n * t
                if stripes:
                    band = math.sin((t ** 0.6) * 38 + x * 0.02)
                    if band > 0.75:
                        base = base * 0.92
                if BAYER[y % 4, x % 4] < 0.1 * (1 - t):
                    base = base * 1.06
                self.c[y, x] = base
                self.a[y, x] = 1.0
        dcols = [hx(c) for c in detail]
        for _ in range(900):
            y = rng.randint(HORIZON + 1, H - 1)
            t = (y - HORIZON) / (H - HORIZON)
            x = rng.randint(0, W - 1)
            ln = 1 + int(t * 3)
            col = dcols[rng.randint(0, len(dcols) - 1)]
            for k in range(ln):
                self.px(x, y - k, col * (1.0 if k else 0.85))

    def blades(self, x, base, h, col, lean=0.0):
        c = hx(col)
        for k in range(h):
            self.px(x + lean * k, base - k, c * (0.8 + 0.4 * k / max(h, 1)))
            if k < h // 3:
                self.px(x + lean * k + 1, base - k, c * 0.7)

    def image(self):
        rgb = np.clip(self.c, 0, 255).astype(np.uint8)
        a = (np.clip(self.a, 0, 1) * 255).astype(np.uint8)
        return Image.fromarray(np.dstack([rgb, a]), 'RGBA')


def sky(layer, stops, sun=None, clouds=(), cloud_col='#f4f6f8'):
    layer.gradient(stops, 0, HORIZON + 10, bands=10)
    if sun:
        layer.ellipse(sun[0], sun[1], sun[2], sun[2], sun[3])
        layer.ellipse(sun[0], sun[1], sun[2] + 3, sun[2] + 3, sun[3], dither=True)
    for (cx, cy) in clouds:
        for k in range(5):
            layer.ellipse(cx + k * 7 - 14, cy + (k % 2) * 2, 8, 4, cloud_col, dither=True)


def fore_grass(layer, cols, seed, density=1.0, reach=34):
    rng = random.Random(seed)
    for side in (0, 1):
        for _ in range(int(60 * density)):
            d = rng.random() ** 1.6
            x = int(d * reach) if side == 0 else int(W - 1 - d * reach)
            base = H - 1 - rng.randint(0, 6)
            h = rng.randint(10, 34) * (1.0 - d * 0.6)
            layer.blades(x, base, int(h), cols[rng.randint(0, len(cols) - 1)], lean=(0.35 if side == 0 else -0.35) * rng.random())
    for _ in range(int(40 * density)):   # low tufts along the bottom edge
        x = rng.randint(0, W - 1)
        layer.blades(x, H - 1, rng.randint(3, 8), cols[rng.randint(0, len(cols) - 1)], lean=rng.uniform(-0.4, 0.4))


# ---------------------------------------------------------------- environments
def forest(seed=11):
    far, mid, gr, fo = Layer(seed), Layer(seed + 1), Layer(seed + 2), Layer(seed + 3)
    sky(far, ['#5aa0d8', '#9ccce0', '#f0e2b0'], sun=(150, 40, 9, '#fff6d8'), clouds=[(40, 30), (120, 22), (175, 55)])
    far.ridge(118, 14, '#7fa0b8', seed, freq=0.06, col2='#8fb0c4')
    far.ridge(134, 10, '#5a8070', seed + 4, freq=0.09)
    for x in range(-4, W + 6, 7):
        mid.conifer(x + mid.rng.randint(-2, 2), HORIZON + 2, mid.rng.randint(18, 28), '#2c4a3a', '#3a5e44', '#4a7050')
    for x in range(-10, W + 20, 30):
        mid.round_tree(x + mid.rng.randint(-6, 6), HORIZON + 6, mid.rng.randint(34, 46), '#4a3222', ['#6aa040', '#4a7e30', '#2f5a24'])
    gr.ground_plane('#7aa84a', '#3e6228', ['#8ac050', '#5a8a36', '#4a7e30', '#9a8058'], seed)
    # worn dirt clearing where the fight happens
    for y in range(HORIZON + 18, H):
        t = (y - HORIZON) / (H - HORIZON)
        half = 40 + t * 70
        for x in range(W):
            d = abs(x - W / 2) / half
            if d < 1 and BAYER[y % 4, x % 4] < (1 - d) * 0.9:
                gr.c[y, x] = gr.c[y, x] * 0.35 + hx('#8a6e48') * 0.65
    for _ in range(50):
        x, y = gr.rng.randint(0, W - 2), gr.rng.randint(HORIZON + 20, H - 2)
        gr.px(x, y, '#6a5438')
        gr.px(x + 1, y, '#8a7458')
    fore_grass(fo, ['#5a9a3a', '#3a6a2a', '#8ac050'], seed)
    for (x, y) in [(6, 250), (192, 256), (14, 262)]:    # ferns
        for k in range(7):
            fo.blades(x + k * 2 - 6, y, 12 - abs(k - 3) * 2, '#4a8a34', lean=(k - 3) * 0.3)
    return far, mid, gr, fo


def ruins(seed=21):
    far, mid, gr, fo = Layer(seed), Layer(seed + 1), Layer(seed + 2), Layer(seed + 3)
    sky(far, ['#6a88a8', '#a8bcc8', '#d8d4c0'], clouds=[(30, 40), (100, 26), (170, 48)], cloud_col='#e4e6e8')
    far.ridge(122, 12, '#8898a8', seed, freq=0.05)
    for (x, h) in [(30, 44), (150, 56), (180, 30)]:   # distant towers
        far.rect(x, HORIZON - h, x + 8, HORIZON, '#7a8494')
        far.rect(x - 2, HORIZON - h, x + 10, HORIZON - h + 3, '#6a7484')
    for x in range(-4, W + 6, 9):
        mid.conifer(x + mid.rng.randint(-2, 2), HORIZON + 2, mid.rng.randint(12, 20), '#34503c', '#42624a', '#507456')
    mid.arch(6, HORIZON + 8, 46, 56)
    mid.pillar(70, HORIZON + 6, 44, 9)
    mid.pillar(126, HORIZON + 6, 30, 8)
    mid.arch(150, HORIZON + 8, 44, 48, stone='#6e685e')
    gr.ground_plane('#8a8676', '#4a4a3e', ['#9a968a', '#6a8a42', '#5a5a4e'], seed, stripes=False)
    # perspective flagstones
    for y in range(HORIZON + 4, H):
        t = (y - HORIZON) / (H - HORIZON)
        row_h = 3 + t * 12
        if (y - HORIZON) % max(1, int(row_h)) == 0:
            for x in range(W):
                gr.px(x, y, gr.c[y, x] * 0.6)
        for x in range(W):
            cell = int((x - W / 2) / (8 + t * 30) + 100 + ((y - HORIZON) // max(1, int(row_h))) % 2 * 0.5)
            if int((x - W / 2) / (8 + t * 30) + 100.5) != cell and (x + y) % 3 == 0:
                gr.px(x, y, gr.c[y, x] * 0.7)
    for _ in range(90):    # moss in the cracks
        x, y = gr.rng.randint(0, W - 1), gr.rng.randint(HORIZON + 6, H - 1)
        gr.px(x, y, '#6a8a42')
    fore_grass(fo, ['#6a8a42', '#4a6a32'], seed, 0.6)
    for (x, y, r) in [(8, 262, 9), (190, 258, 11), (30, 268, 6)]:   # rubble
        fo.ellipse(x, y, r, r * 0.6, '#6a645a')
        fo.ellipse(x - 2, y - 2, r * 0.6, r * 0.35, '#8a8478')
    return far, mid, gr, fo


def scorched(seed=31):
    far, mid, gr, fo = Layer(seed), Layer(seed + 1), Layer(seed + 2), Layer(seed + 3)
    sky(far, ['#2a141c', '#7a3228', '#d8783a', '#f0a858'], sun=(60, 60, 12, '#ffd08a'))
    far.ridge(124, 14, '#5a2a2a', seed, freq=0.06, col2='#6a3230')
    far.ridge(138, 9, '#3a1e1e', seed + 5, freq=0.09)
    for x in range(-3, W + 6, 10):     # burnt trunks
        h = mid.rng.randint(18, 34)
        for yy in range(h):
            mid.px(x, HORIZON + 2 - yy, '#1c1414')
            mid.px(x + 1, HORIZON + 2 - yy, '#2a1c1a')
            if yy % 6 == 3 and yy > 5:
                for k in range((h - yy) // 4 + 2):
                    mid.px(x - k, HORIZON + 2 - yy - k // 2, '#1c1414')
                    mid.px(x + 1 + k, HORIZON + 2 - yy - k // 2, '#2a1c1a')
    gr.ground_plane('#5a3a30', '#221614', ['#3a2622', '#6a3a2a', '#1c1414'], seed, stripes=False)
    for _ in range(60):    # glowing cracks
        x, y = gr.rng.randint(0, W - 8), gr.rng.randint(HORIZON + 8, H - 2)
        t = (y - HORIZON) / (H - HORIZON)
        for k in range(int(3 + t * 8)):
            gr.px(x + k, y + (k % 3 == 0), '#ff6a1e' if k % 2 else '#c8361a')
    fore_grass(fo, ['#1c1414', '#3a2420', '#6a3a2a'], seed, 0.8)
    for (x, s) in [(4, 1), (196, -1)]:    # charred branch
        for k in range(30):
            fo.px(x + s * k, 268 - k * 0.8, '#140e0e')
            fo.px(x + s * k, 267 - k * 0.8, '#2a1c1a')
    return far, mid, gr, fo


def flooded(seed=41):
    far, mid, gr, fo = Layer(seed), Layer(seed + 1), Layer(seed + 2), Layer(seed + 3)
    sky(far, ['#3e5e8a', '#88aac4', '#c8dce0'], clouds=[(40, 30), (140, 44)], cloud_col='#dfe8f0')
    far.ridge(124, 12, '#6a8098', seed, freq=0.05)
    for x in range(-4, W + 6, 8):
        mid.conifer(x + mid.rng.randint(-2, 2), HORIZON + 2, mid.rng.randint(14, 22), '#2a4048', '#34525a', '#40646a')
    mid.arch(2, HORIZON + 8, 42, 50, stone='#6a7078')
    mid.pillar(90, HORIZON + 6, 34, 8, stone='#707880')
    mid.arch(156, HORIZON + 8, 40, 44, stone='#626a72')
    # shallow water plane with reflections and wet ground islands
    gr.ground_plane('#6a90a8', '#1c3a5a', ['#8ad0e8', '#3a6a8a'], seed, stripes=False)
    for y in range(HORIZON + 2, H):
        t = (y - HORIZON) / (H - HORIZON)
        for x in range(W):
            if (x // 2 + y * 3) % int(9 + t * 10) == 0:
                gr.c[y, x] = gr.c[y, x] * 0.5 + hx('#bfeaf8') * 0.5
    for (cx, cy, rx) in [(100, 232, 70), (60, 200, 34), (150, 196, 30), (40, 256, 28)]:   # islands where units stand
        gr.ellipse(cx, cy, rx, rx * 0.28, '#3a5244')
        gr.ellipse(cx, cy - 1, rx - 3, rx * 0.24, '#4a6a50')
        for k in range(int(rx / 3)):
            gr.px(cx - rx + 4 + k * 6, cy - rx * 0.2, '#6a9a5a')
    fore_grass(fo, ['#4a7a4a', '#6a9a5a', '#2e5a3a'], seed, 0.9)   # reeds
    for x in [3, 9, 191, 196]:
        for k in range(38):
            fo.px(x, 268 - k, '#3a6a3a' if k < 30 else '#8a6a3a')
        fo.ellipse(x, 268 - 34, 1.2, 4, '#6a4a2a')
    return far, mid, gr, fo


def heart(seed=51):
    far, mid, gr, fo = Layer(seed), Layer(seed + 1), Layer(seed + 2), Layer(seed + 3)
    far.gradient(['#0c1a14', '#16301e', '#24482a', '#3a6a34'], 0, HORIZON + 10, bands=10)
    # the great tree trunk behind the arena
    for y in range(0, HORIZON + 4):
        wdt = 34 + max(0, y - 110) * 1.4
        for x in range(int(100 - wdt / 2), int(100 + wdt / 2)):
            t = (x - (100 - wdt / 2)) / wdt
            c = hx('#4a3222') * (1.25 - t * 0.6)
            if (x * 3 + y // 5) % 11 == 0:
                c = c * 0.7
            far.px(x, y, c)
    far.ellipse(100, 80, 6, 8, '#8ae05a')
    far.ellipse(100, 80, 3, 4, '#e0ffb0')
    for i in range(50):
        far.ellipse(far.rng.randint(0, W), far.rng.randint(-8, 44), far.rng.randint(10, 20), far.rng.randint(6, 10),
                    ['#1e4a22', '#2a6028', '#163a1a'][i % 3], dither=True)
    for x in range(-4, W + 6, 7):
        if abs(x - 100) > 26:
            mid.conifer(x, HORIZON + 2, mid.rng.randint(20, 34), '#0e2014', '#16301c', '#1e4024')
    for k in range(4):   # arching roots
        cx = 20 + k * 54
        for t in range(40):
            a = math.pi * t / 39
            x = cx + math.cos(a) * 18
            y = HORIZON + 6 - math.sin(a) * 16
            for d in range(3):
                mid.px(x, y + d, '#3a2818' if d else '#6a4a2a')
    gr.ground_plane('#3a5a2a', '#142410', ['#5a8a3a', '#2e4a24', '#8ae05a'], seed)
    for k in range(6):   # roots crossing the ground
        x0 = 100 + (k - 2.5) * 10
        for t in range(120):
            x = x0 + (k - 2.5) * t * 0.8
            y = HORIZON + 4 + t * 0.95 + math.sin(t * 0.15 + k) * 2
            for d in range(2 + int(t / 40)):
                gr.px(x, y + d, '#3a2818' if d else '#5a4028')
    for _ in range(40):    # glowing moss
        x, y = gr.rng.randint(0, W - 1), gr.rng.randint(HORIZON + 4, H - 1)
        gr.px(x, y, '#8ae05a')
    fore_grass(fo, ['#1e4024', '#2e6a2a', '#8ae05a'], seed, 1.0)
    for (x, y) in [(10, 255), (188, 250)]:   # glowing mushrooms
        fo.ellipse(x, y, 5, 3, '#6ae0a0')
        fo.rect(x - 1, y, x + 1, y + 8, '#c8e0c0')
    return far, mid, gr, fo


# ================================================================ World 2 + Evolution Tower
# Newer stages favour flat colour bands with short ordered-dither seams (instead of
# full-field noise) so each 4-layer set stays small on disk.
_YY, _XX = np.mgrid[0:H, 0:W]


def _c(col):
    return hx(col) if isinstance(col, str) else np.asarray(col, dtype=np.float64)


def mixc(a, b, t):
    return _c(a) * (1 - t) + _c(b) * t


def bands(layer, cols, y0, y1, soft=2, curve=1.0, x0=0, x1=W):
    """Flat horizontal colour bands; neighbouring bands meet in a short ordered-dither seam."""
    cs = [_c(c) for c in cols]
    n = len(cs)
    rows = list(range(y0, y1))
    idx = [min(n - 1, int(((y - y0) / max(1, y1 - y0)) ** curve * n)) for y in rows]
    for k, y in enumerate(rows):
        i = idx[k]
        dn = next((j - k for j in range(k, len(rows)) if idx[j] != i), 999)
        dp = next((k - j for j in range(k, -1, -1) if idx[j] != i), 999)
        for x in range(max(0, x0), min(W, x1)):
            c = cs[i]
            b = BAYER[y % 4, x % 4]
            if dn <= soft and i + 1 < n and b < 0.5 * (1 - (dn - 0.5) / (soft + 0.5)):
                c = cs[i + 1]
            elif dp <= soft and i > 0 and b < 0.5 * (1 - (dp - 0.5) / (soft + 0.5)):
                c = cs[i - 1]
            layer.c[y, x] = c
            layer.a[y, x] = 1.0


def paint(layer, m, col, alpha=1.0):
    layer.c[m] = _c(col)
    layer.a[m] = np.maximum(layer.a[m], alpha)


def tint(layer, m, col, amt):
    """Blend existing (opaque) pixels under mask m toward col."""
    m = m & (layer.a > 0)
    layer.c[m] = layer.c[m] * (1 - amt) + _c(col) * amt


def m_ellipse(cx, cy, rx, ry):
    return ((_XX + 0.5 - cx) / max(rx, 0.5)) ** 2 + ((_YY + 0.5 - cy) / max(ry, 0.5)) ** 2 <= 1.0


def m_poly(pts):
    m = np.zeros((H, W), dtype=bool)
    n = len(pts)
    ys = [p[1] for p in pts]
    for y in range(max(0, int(math.floor(min(ys)))), min(H, int(math.ceil(max(ys))) + 1)):
        yc = y + 0.5
        xs = []
        for i in range(n):
            (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % n]
            if (ya <= yc < yb) or (yb <= yc < ya):
                xs.append(xa + (yc - ya) * (xb - xa) / (yb - ya))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            a, b = max(0, int(math.ceil(xs[i] - 0.5))), min(W - 1, int(math.floor(xs[i + 1] - 0.5)))
            if b >= a:
                m[y, a:b + 1] = True
    return m


def poly(layer, pts, col, alpha=1.0):
    paint(layer, m_poly(pts), col, alpha)


def line(layer, x0, y0, x1, y1, col, width=1):
    c = _c(col)
    steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    steep = abs(y1 - y0) > abs(x1 - x0)
    for i in range(steps + 1):
        t = i / steps
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        for w in range(width):
            layer.px(x + (w if steep else 0), y + (0 if steep else w), c)


def dither_mask(m, keep=0.5, phase=0):
    """Thin a mask with the Bayer pattern (for soft glows without noise)."""
    return m & (BAYER[(_YY + phase) % 4, _XX % 4] < keep)


def rim(m, side):
    """Edge pixels of mask m facing a direction: 'l', 'r', 't' or 'b'."""
    d = {'l': (1, 1), 'r': (-1, 1), 't': (1, 0), 'b': (-1, 0)}[side]
    return m & ~np.roll(m, d[0], axis=d[1])


def splash(layer, cx, cy, size, seed, lean=1):
    """Flat-shaded spray plume thrown up by a breaking wave."""
    rng = random.Random(seed)
    outer = np.zeros((H, W), dtype=bool)
    inner = np.zeros((H, W), dtype=bool)
    for k in range(10):
        a = -math.pi / 2 + (k - 4.5) * 0.24 + lean * 0.25
        dist = size * (0.25 + 0.75 * rng.random())
        r = size * rng.uniform(0.2, 0.32) * (1.1 - dist / size * 0.4)
        bx, by = cx + math.cos(a) * dist, cy + math.sin(a) * dist * 1.15
        outer |= m_ellipse(bx, by, r, r * 0.85)
        inner |= m_ellipse(bx - r * 0.3, by - r * 0.3, r * 0.55, r * 0.5)
    paint(layer, outer, '#7ec2cc')
    paint(layer, outer & np.roll(np.roll(outer, 2, 0), 2, 1), '#b6e4ea')
    paint(layer, inner & outer, '#eefcfc')
    paint(layer, rim(outer, 't'), '#ffffff')
    for _ in range(40):
        a = -math.pi / 2 + rng.uniform(-1.3, 1.3) + lean * 0.25
        dist = size * rng.uniform(1.0, 1.6)
        layer.px(cx + math.cos(a) * dist, cy + math.sin(a) * dist * 1.1, '#eefcfc' if rng.random() < 0.7 else '#9ad6de')


def ring_glow(layer, cx, cy, r, col, ry=None, levels=((1.0, 0.16), (0.62, 0.3))):
    """Flat stepped light halo on existing pixels, with one dithered seam per step."""
    ry = ry or r
    d = np.sqrt(((_XX + 0.5 - cx) / r) ** 2 + ((_YY + 0.5 - cy) / ry) ** 2)
    for rr, amt in levels:
        edge = rr + (BAYER[_YY % 4, _XX % 4] - 0.5) * 0.12
        tint(layer, d < edge, col, amt)


SALT = ['#f6fdff', '#cdeff5', '#98d6e2', '#5eaac0', '#3c7c9a']      # glint, light, mid, shade, deep
GLOW = ['#f0ffff', '#9af4ff', '#46d0e6', '#2690bc', '#18588a']      # cave crystals
STORM = ['#f2fbff', '#bcdcf2', '#8eaedc', '#6a7cbc', '#4a4a8c']     # boss-arena crystals


def shard(layer, x, base, h, w, pal=SALT, lean=0.0):
    """Faceted crystal spike: lit left facet, mid facet, shaded right facet and a bright ridge."""
    tx, ty = x + lean * h, base - h
    if w >= 4:
        r1, r2 = x - w * 0.35, x + w * 0.3
        poly(layer, [(x - w, base), (tx, ty), (r1, base)], pal[1])
        poly(layer, [(r1, base), (tx, ty), (r2, base)], pal[2])
        poly(layer, [(r2, base), (tx, ty), (x + w, base)], pal[3])
        line(layer, r1, base - 1, tx, ty, pal[0])
        line(layer, x + w - 0.5, base - 1, tx, ty, pal[4])
    else:
        r1 = x - w * 0.1
        poly(layer, [(x - w, base), (tx, ty), (r1, base)], pal[1])
        poly(layer, [(r1, base), (tx, ty), (x + w, base)], pal[3])
        line(layer, r1, base - 1, tx, ty, pal[0])


def crystal_cluster(layer, cx, base, size, pal, seed, spread=1.0, girth=0.2, n=4):
    rng = random.Random(seed)
    spikes = [(0, 1.0, 0.0)] + [(rng.uniform(-1, 1) * spread, rng.uniform(0.45, 0.8), rng.uniform(-0.3, 0.3)) for _ in range(n)]
    spikes.sort(key=lambda s: -abs(s[0]))
    for dx, hs, lean in spikes:
        shard(layer, cx + dx * size * 0.7, base, size * hs, max(1.5, size * girth * hs), pal, lean + dx * 0.25)


def cloud(layer, cx, cy, w, h, top, under, rim, seed, flat_bottom=True):
    """Flat 3-tone pixel cloud built from overlapping ellipses."""
    rng = random.Random(seed)
    m = np.zeros((H, W), dtype=bool)
    k = max(3, int(w / 7))
    for i in range(k):
        t = i / (k - 1)
        bx = cx - w / 2 + w * t
        bh = h * (0.55 + 0.45 * math.sin(math.pi * t)) * rng.uniform(0.8, 1.1)
        m |= m_ellipse(bx, cy - bh * 0.35, bh * rng.uniform(0.9, 1.3), bh * 0.7)
    if flat_bottom:
        m &= _YY < cy + h * 0.15
    paint(layer, m, top)
    paint(layer, m & (_YY >= cy - h * 0.1), under)
    up = np.roll(m, 1, axis=0)
    paint(layer, m & ~up, rim)


def streak(layer, x, y, ln, col, under):
    line(layer, x, y, x + ln, y, col)
    line(layer, x + 3, y + 1, x + ln - 4, y + 1, under)
    line(layer, x + ln * 0.25, y - 1, x + ln * 0.6, y - 1, col)


def glints(layer, rng, n, y0, y1, cols, x0=0, x1=W, maxlen=5):
    for _ in range(n):
        y = rng.randint(y0, y1 - 1)
        t = (y - y0) / max(1, y1 - y0)
        ln = 1 + int(t * maxlen * rng.random())
        x = rng.randint(x0, x1 - 1)
        line(layer, x, y, x + ln, y, cols[rng.randint(0, len(cols) - 1)])


def ground_cells(seed, spacing=0.1, vy=60, vscale=1.6):
    """Irregular slabs in perspective: nearest-seed id per ground pixel (jittered grid in floor space)."""
    rng = random.Random(seed)
    d = np.maximum(_YY - vy, 1).astype(np.float64)
    U = (_XX + 0.5 - W / 2) / d
    V = 100.0 * vscale / d
    seeds = []
    v = 100.0 * vscale / (H - vy) - spacing
    while v < 100.0 * vscale / (HORIZON - vy) + spacing:
        umax = (W / 2) / 100.0 * v / vscale + spacing
        u = -umax + rng.uniform(0, spacing)
        while u < umax:
            seeds.append((u + rng.uniform(-0.35, 0.35) * spacing, v + rng.uniform(-0.35, 0.35) * spacing))
            u += spacing
        v += spacing
    best = np.full((H, W), 1e9)
    ids = np.zeros((H, W), dtype=np.int32)
    for i, (su, sv) in enumerate(seeds):
        dd = (U - su) ** 2 + (V - sv) ** 2
        closer = dd < best
        best[closer] = dd[closer]
        ids[closer] = i
    return ids


def cell_edges(ids):
    up = np.roll(ids, 1, axis=0)
    left = np.roll(ids, 1, axis=1)
    e = (ids != up) | (ids != left)
    e[:, 0] = False
    e[0, :] = False
    return e


def shade_cells(layer, ids, factors, seed, y0=HORIZON):
    rng = random.Random(seed)
    table = np.array([factors[rng.randrange(len(factors))] for _ in range(ids.max() + 1)])
    f = table[ids]
    rows = _YY >= y0
    layer.c[rows] = layer.c[rows] * f[rows][:, None]


def puddle(layer, cx, cy, rx, ry, rim, fill, deep, glint):
    paint(layer, m_ellipse(cx, cy + 0.5, rx + 1.5, ry + 1), rim)
    paint(layer, m_ellipse(cx, cy, rx, ry), fill)
    paint(layer, m_ellipse(cx + rx * 0.18, cy + ry * 0.2, rx * 0.62, ry * 0.55), deep)
    line(layer, cx - rx * 0.55, cy - ry * 0.45, cx - rx * 0.15, cy - ry * 0.45, glint)
    line(layer, cx + rx * 0.1, cy + ry * 0.1, cx + rx * 0.3, cy + ry * 0.1, glint)


def wet_shore(layer, y0, water, foam, wet, seed, amp=2.0):
    for x in range(W):
        wob = int(round(2 + amp * math.sin(x * 0.07 + seed) + 0.8 * math.sin(x * 0.21 + seed * 2)))
        for y in range(y0, y0 + wob):
            layer.px(x, y, water)
        layer.px(x, y0 + wob, foam)
        if (x // 3 + seed) % 4:
            layer.px(x, y0 + wob + 1, foam)
        for y in range(y0 + wob + 2, y0 + wob + 5):
            layer.px(x, y, wet)


# ---------------------------------------------------------------- Saltglass Coast
def shore(seed=61):
    far, mid, gr, fo = Layer(seed), Layer(seed + 1), Layer(seed + 2), Layer(seed + 3)
    sea_y = 120
    bands(far, ['#3796d2', '#4aa6da', '#5eb6e0', '#76c6e6', '#90d4ea', '#aee0ec', '#cceaec', '#e6f2ea'], 0, sea_y)
    for r, c in [(15, '#8ed2ec'), (11, '#cdeef6'), (7, '#fffdf0')]:
        paint(far, m_ellipse(48, 34, r, r), c)
    for (x, y, ln) in [(96, 24, 44), (126, 30, 30), (8, 62, 36), (140, 70, 52), (60, 88, 40), (168, 100, 30), (20, 104, 22)]:
        streak(far, x, y, ln, '#f4fbfb', '#c6e4ec')
    bands(far, ['#2a80a8', '#3290b2', '#3ea2bc', '#4cb2c4', '#5ec2ca'], sea_y, HORIZON + 10, soft=1)
    line(far, 0, sea_y, W - 1, sea_y, '#246e98')
    glints(far, far.rng, 60, sea_y + 2, HORIZON + 8, ['#e2f8fa', '#a8e2ea'])
    glints(far, far.rng, 30, sea_y + 1, HORIZON + 8, ['#fffdf0', '#e2f8fa'], 36, 62, 3)    # sun glitter
    haze = ['#eef9fa', '#d2ecf2', '#b6dde8', '#9ccde0', '#88bcd0']
    for (x, h, w, ln) in [(12, 16, 3, 0.1), (22, 30, 5, -0.05), (31, 12, 3, 0.2), (76, 9, 2, 0), (83, 15, 3, -0.1),
                          (146, 20, 4, 0.1), (156, 40, 6, 0.03), (167, 26, 4, -0.1), (176, 12, 3, 0), (190, 18, 3, 0.1)]:
        shard(far, x, sea_y + 1, h, w, haze, ln)
        line(far, x, sea_y + 2, x, sea_y + 2 + h // 5, '#9ad4de')
    # mid: nearer saltglass spires standing in the shallows
    for (x, h, w, ln) in [(-4, 44, 7, 0.08), (10, 66, 9, 0.02), (24, 34, 6, -0.12), (36, 16, 4, 0.2),
                          (168, 28, 5, 0.15), (182, 76, 10, -0.02), (197, 46, 7, -0.1), (156, 14, 3, -0.2)]:
        shard(mid, x, HORIZON + 6, h, w, SALT, ln)
    for (cx, rx) in [(16, 30), (184, 28)]:
        paint(mid, m_ellipse(cx, HORIZON + 1, rx, 5), '#7ab4bc')
        paint(mid, m_ellipse(cx - 3, HORIZON - 1, rx - 6, 3), '#a2d0d4')
        for k in range(0, rx * 2, 5):
            mid.px(cx - rx + k, HORIZON - 3 + (k % 3), '#f2fcfc')
    # ground: pale sun-bleached sand
    bands(gr, ['#eee4c8', '#e8dcbe', '#e2d4b2', '#dacaa6', '#d0bf9a', '#c6b28c'], HORIZON, H, soft=2, curve=0.85)
    wet_shore(gr, HORIZON, '#86ccd0', '#f4fcfa', '#cabb98', 1)
    for k in range(11):                                   # wind ripples
        t = (k + 0.6) / 11
        y0 = HORIZON + 12 + (H - HORIZON - 14) * t ** 1.5
        seg = int(16 + t * 46)
        for x in range(W):
            if (x + k * 37) % (seg + 10) < seg:
                y = y0 + (1 + t * 3) * math.sin(x * (0.07 - t * 0.03) + k * 1.3)
                yy = int(round(y))
                if HORIZON + 8 < yy < H:
                    gr.px(x, yy, gr.c[yy, x] * 0.93)
                    gr.px(x, yy - 1, np.minimum(gr.c[yy - 1, x] * 1.04, 255))
    for (cx, cy, rx, ry) in [(24, 188, 20, 5), (184, 214, 17, 5), (148, 166, 11, 3), (70, 246, 20, 6)]:
        puddle(gr, cx, cy, rx, ry, '#b6a27c', '#62c2c8', '#4aa8b8', '#eafcff')
    for (cx, cy, rx, ry) in [(96, 176, 14, 2.5), (128, 206, 20, 3.5), (58, 214, 12, 3), (160, 186, 9, 2)]:
        crust = m_ellipse(cx, cy, rx, ry) | m_ellipse(cx + rx * 0.5, cy + ry * 0.6, rx * 0.6, ry * 0.8)
        paint(gr, rim(crust, 'b') | np.roll(rim(crust, 'b'), 1, 0), '#c8b692')
        paint(gr, crust, '#f6f0e0')
        paint(gr, rim(crust, 't'), '#fffdf6')
    for (x, y, h, w, ln) in [(10, 174, 11, 3, 0.1), (60, 166, 6, 2, -0.1), (140, 160, 4, 1.5, 0), (118, 170, 5, 2, 0.1),
                             (170, 182, 13, 3, -0.08), (192, 238, 18, 4, -0.1), (6, 222, 15, 4, 0.12), (30, 194, 7, 2, 0),
                             (186, 170, 7, 2, 0.1), (88, 158, 3, 1.5, 0)]:
        poly(gr, [(x, y), (x + w + 1, y), (x + w + h * 0.7, y + h * 0.18)], '#b8a684')      # shadow
        shard(gr, x, y, h, w, SALT, ln)
    for _ in range(36):                                    # shells and pebbles
        x, y = gr.rng.randint(0, W - 2), gr.rng.randint(HORIZON + 10, H - 2)
        gr.px(x, y, '#faf4e4')
        gr.px(x + 1, y, '#b09a78')
    # fore: dune grass, bleached driftwood, crystal cluster
    shard(fo, 186, H + 2, 46, 8, SALT, -0.1)
    shard(fo, 198, H + 2, 30, 6, SALT, -0.18)
    shard(fo, 175, H + 2, 20, 5, SALT, 0.12)
    for pts in ([(-4, H), (-4, 236), (8, 234), (22, 240), (36, 252), (46, H)], [(W + 4, H), (W + 4, 244), (190, 242), (174, 252), (164, H)]):
        m = m_poly(pts)
        paint(fo, m, '#dccca6')
        paint(fo, rim(m, 't'), '#f2e8cc')
        paint(fo, m & (_YY > 258), '#cbb690')
    wood = m_poly([(-6, 250), (40, 242), (44, 247), (42, 252), (-6, 262)])
    paint(fo, wood, '#b4a488')
    paint(fo, rim(wood, 't'), '#e6dcc6')
    paint(fo, rim(wood, 'b'), '#6e604c')
    line(fo, 28, 245, 36, 232, '#b4a488', 2)
    line(fo, 36, 232, 40, 228, '#e6dcc6')
    for (x, y) in [(6, 255), (18, 252), (31, 249)]:
        fo.px(x, y, '#6e604c')
        fo.px(x + 1, y, '#8a7a62')
    fore_grass(fo, ['#c6c27a', '#a2a25e', '#e0dca2', '#7c884a'], seed, density=0.8, reach=30)
    return far, mid, gr, fo


def rib(layer, x0, base, h, bend, col, lit, width=3):
    for s in range(int(h)):
        t = s / h
        x = x0 + bend * (1 - math.cos(t * math.pi / 2)) ** 1.0
        y = base - s
        for w in range(width):
            layer.px(x + w, y, lit if w == width - 1 else col)


def wreck(seed=71):
    far, mid, gr, fo = Layer(seed), Layer(seed + 1), Layer(seed + 2), Layer(seed + 3)
    sea_y = 124
    bands(far, ['#1c1838', '#261e46', '#342652', '#482e5a', '#603660', '#7c3e64', '#9a4a66', '#ba5a66', '#d67266',
                '#ea9266'], 0, sea_y)
    for r, c in [(19, '#f2a870'), (13, '#ffcf8e'), (9, '#fff0c4')]:
        paint(far, m_ellipse(136, sea_y + 1, r, r), c)
    for (x, y, ln) in [(4, 40, 60), (110, 28, 70), (40, 70, 50), (150, 84, 46), (8, 100, 36), (80, 106, 34)]:
        line(far, x, y, x + ln, y, '#43294f')
        line(far, x - 4, y + 1, x + ln + 3, y + 1, '#43294f')
        line(far, x + 2, y + 2, x + ln - 6, y + 2, '#e0806a')
    bands(far, ['#3a2a4c', '#44304e', '#503654', '#5a3c58'], sea_y, HORIZON + 10, soft=1)
    line(far, 0, sea_y, W - 1, sea_y, '#2c2040')
    for y in range(sea_y + 1, HORIZON + 10):              # sun path on the water
        wdt = 5 + (y - sea_y) * 0.7
        for _ in range(3):
            x = int(136 + far.rng.uniform(-wdt, wdt))
            ln = far.rng.randint(1, 2 + (y - sea_y) // 8)
            if y % 2 == 0:
                line(far, x, y, x + ln, y, '#ffc07a' if far.rng.random() < 0.6 else '#e88868')
    glints(far, far.rng, 30, sea_y + 2, HORIZON + 8, ['#7a5470', '#8a5a70'])
    sil = '#2a1e3a'
    for (x, h) in [(18, 14), (56, 22), (60, 10), (170, 18), (186, 12)]:   # distant masts
        line(far, x, sea_y, x, sea_y - h, sil)
        line(far, x - 4, sea_y - h + 4, x + 4, sea_y - h + 3, sil)
    for (cx, rx, ry) in [(58, 14, 4), (178, 12, 5), (24, 8, 3)]:
        paint(far, m_ellipse(cx, sea_y, rx, ry) & (_YY <= sea_y), sil)
    # mid: skeletal hull on the left, broken stern + leaning mast on the right
    dark, body, lit, rimc = '#2a1c28', '#3a2632', '#5a3a42', '#e08a64'
    poly(mid, [(-8, HORIZON + 6), (-8, HORIZON - 8), (70, HORIZON - 3), (74, HORIZON + 6)], body)
    line(mid, -8, HORIZON - 9, 70, HORIZON - 4, rimc)
    for i in range(7):
        x0 = 2 + i * 10
        rib(mid, x0, HORIZON - 4, 50 - i * 6 - (i % 2) * 3, -10 + i * 0.8, body, rimc if i > 0 else lit)
    for i in range(3):
        poly(mid, [(2 + i * 10, HORIZON - 4), (12 + i * 10, HORIZON - 4), (12 + i * 10, HORIZON - 16 + i * 3), (2 + i * 10, HORIZON - 18 + i * 3)], dark)
        line(mid, 2 + i * 10, HORIZON - 12 + i * 3, 12 + i * 10, HORIZON - 11 + i * 3, lit)
    line(mid, 44, HORIZON - 4, 26, HORIZON - 100, body, 3)          # broken mast
    line(mid, 46, HORIZON - 4, 28, HORIZON - 100, rimc)
    line(mid, 14, HORIZON - 78, 48, HORIZON - 84, body, 2)
    poly(mid, [(22, HORIZON - 77), (44, HORIZON - 81), (40, HORIZON - 50), (30, HORIZON - 56), (24, HORIZON - 44)], '#6a4e56')
    poly(mid, [(28, HORIZON - 70), (34, HORIZON - 72), (32, HORIZON - 64)], '#1c1838')   # torn hole
    line(mid, 26, HORIZON - 98, 66, HORIZON - 4, '#1e1628')                            # rigging
    # right: stern section tilted into the sand
    poly(mid, [(142, HORIZON + 6), (150, HORIZON - 34), (174, HORIZON - 58), (206, HORIZON - 64), (206, HORIZON + 6)], body)
    poly(mid, [(150, HORIZON - 34), (174, HORIZON - 58), (206, HORIZON - 64), (206, HORIZON - 58), (176, HORIZON - 52), (153, HORIZON - 30)], lit)
    line(mid, 142, HORIZON + 6, 150, HORIZON - 34, rimc)
    line(mid, 150, HORIZON - 34, 174, HORIZON - 58, rimc)
    for k in range(6):
        yk = HORIZON - 26 + k * 6
        line(mid, 148 - k * 0.8, yk, 206, yk - 12 + k * 1.2, dark)
    for (wx, wy) in [(176, HORIZON - 44), (188, HORIZON - 47), (200, HORIZON - 50)]:   # stern windows
        mid.rect(wx, wy, wx + 5, wy + 6, '#1a1224')
        mid.rect(wx + 1, wy + 3, wx + 4, wy + 5, '#c86a4a' if wx != 188 else '#1a1224')
    line(mid, 178, HORIZON - 60, 150, HORIZON - 132, body, 3)
    line(mid, 177, HORIZON - 60, 149, HORIZON - 132, rimc)
    line(mid, 138, HORIZON - 116, 170, HORIZON - 108, body, 2)
    poly(mid, [(141, HORIZON - 114), (166, HORIZON - 108), (160, HORIZON - 84), (150, HORIZON - 92), (146, HORIZON - 80)], '#6a4e56')
    line(mid, 150, HORIZON - 130, 206, HORIZON - 70, '#1e1628')
    line(mid, 150, HORIZON - 130, 120, HORIZON + 2, '#1e1628')
    # ground: wet dusk sand with a broken deck
    bands(gr, ['#b4747a', '#98606a', '#7e5060', '#684456', '#563a4c', '#4a3244'], HORIZON, H, soft=2, curve=0.85)
    wet_shore(gr, HORIZON, '#7a5070', '#f0c0a0', '#c07c7c', 3, amp=1.5)
    for (cx, cy, rx, ry) in [(22, 176, 18, 4), (182, 190, 16, 4), (26, 238, 16, 5), (180, 250, 14, 5)]:
        puddle(gr, cx, cy, rx, ry, '#3c2a3a', '#c07470', '#d88a70', '#ffd0a0')
    vy = 60
    planks = ['#76503e', '#6a4636', '#80583f']
    gap, edge, nail = '#2c1c22', '#b07a62', '#3a2a2a'
    prng = random.Random(seed)
    ends = {i: prng.randint(172, 196) for i in range(-6, 7)}
    ends[2] = 240                                             # a missing board shows the sand
    for y in range(HORIZON, H):
        d = y - vy
        for x in range(W):
            u = (x + 0.5 - W / 2) / d
            i = int(math.floor(u / 0.075 + 0.5))
            if abs(i) > 5 or y < ends.get(i, 999) + (x % 5 == 0):
                continue
            left_u = (x - 0.5 - W / 2) / d
            if int(math.floor(left_u / 0.075 + 0.5)) != i:
                gr.px(x, y, gap)
            elif y == ends[i] or y == ends[i] + (x % 5 == 0):
                gr.px(x, y, edge)
            else:
                gr.px(x, y, planks[(i + 7) % 3] if (y + i * 7) % 43 else gap)
    for i in range(-5, 6):                                    # nails / wet highlights along boards
        for y in (206, 244):
            if y > ends[i]:
                x = W / 2 + i * 0.075 * (y - vy)
                gr.px(x - 2, y, nail)
                gr.px(x + 2, y, nail)
        yh = ends[i] + 6
        x = W / 2 + i * 0.075 * (yh - vy)
        line(gr, x - 3, yh, x + 1, yh, '#9a6a54')
    for (x, y, ln, a) in [(6, 200, 26, 0.3), (160, 206, 30, -0.25), (150, 170, 18, 0.15)]:   # loose boards
        dx, dy = math.cos(a) * ln, math.sin(a) * ln
        poly(gr, [(x, y), (x + dx, y + dy), (x + dx, y + dy + 4), (x, y + 4)], '#6a4636')
        line(gr, x, y, x + dx, y + dy, edge)
        line(gr, x, y + 4, x + dx, y + dy + 4, gap)
    for _ in range(18):
        x, y = gr.rng.randint(0, W - 3), gr.rng.randint(HORIZON + 8, H - 2)
        if gr.c[y, x][0] > 110:
            gr.px(x, y, '#3e5a44')
            gr.px(x + 1, y - 1, '#4e7050')
    # fore: mooring post with rope, net heap with floats, rope coil
    fo.rect(0, 176, 7, H, '#2c1e26')
    fo.rect(5, 176, 7, H, '#6a4038')
    fo.rect(0, 174, 8, 177, '#4a3238')
    for k in range(4):
        line(fo, 0, 198 + k * 3, 7, 195 + k * 3, '#b8986a')
    net = m_ellipse(26, H + 6, 36, 20)
    paint(fo, net, '#3a2a36')
    paint(fo, net & (((_XX + _YY) % 5 == 0) | ((_XX - _YY) % 5 == 0)), '#a88e6a')
    paint(fo, rim(net, 't'), '#c8a47a')
    for (x, y) in [(14, 258), (32, 254), (48, 264), (4, 266)]:
        paint(fo, m_ellipse(x, y, 4, 3), '#f0b870')
        paint(fo, m_ellipse(x + 1, y + 1, 3, 2), '#b87a40')
        fo.px(x - 2, y - 1, '#fff0c0')
    for r in range(12, 0, -3):
        paint(fo, m_ellipse(182, 262, r * 1.5 + 1, r * 0.55 + 1), '#4a3424')
        paint(fo, m_ellipse(182, 261.5, r * 1.5, r * 0.55), '#c8a070' if r % 2 else '#a07e52')
    paint(fo, m_ellipse(182, 262, 3, 1.2), '#2a1c22')
    line(fo, 199, 262, 204, 257, '#c8a070', 2)
    return far, mid, gr, fo


def caves(seed=81):
    far, mid, gr, fo = Layer(seed), Layer(seed + 1), Layer(seed + 2), Layer(seed + 3)
    bands(far, ['#0a0e18', '#0d1320', '#101828', '#141e30', '#182438', '#1c2a40'], 0, HORIZON + 10)
    for k in range(7):                                  # layered rock shelves with lit upper lips
        y0 = 38 + k * 16
        top = y0 + 4 * np.sin(_XX * 0.045 + k * 2.1) + 2 * np.sin(_XX * 0.13 + k)
        shelf = (_YY >= top) & (_YY < top + 7 + 3 * np.sin(_XX * 0.08 + k * 3))
        tint(far, shelf, '#2a3c56', 0.22 if k % 2 else 0.12)
        tint(far, rim(shelf, 't'), '#3e5872', 0.5)
    mouth = m_poly([(64, 150), (60, 124), (70, 100), (86, 88), (104, 86), (122, 94), (134, 112), (136, 132), (140, 150)])
    lip = mouth | np.roll(mouth, -2, axis=0) | np.roll(mouth, 2, axis=1) | np.roll(mouth, -2, axis=1)
    paint(far, lip & ~mouth, '#2e5064')
    view = Layer(seed + 9)
    bands(view, ['#2a6e88', '#3a88a0', '#58a8b8', '#86ccd0', '#b2e4e0'], 84, 132)
    bands(view, ['#1e6a86', '#28809a', '#3494aa'], 132, 152, soft=1)
    vp = ['#e8fbff', '#bce6ee', '#8ccada', '#62a4bc', '#4a84a0']
    shard(view, 112, 132, 30, 5, vp, 0.05)
    shard(view, 102, 132, 14, 3, vp, -0.1)
    glints(view, view.rng, 16, 133, 150, ['#c8f4f6', '#6ac0cc'], 64, 140, 3)
    far.c[mouth] = view.c[mouth]
    for (x, ln, w) in [(6, 34, 7), (22, 18, 4), (40, 48, 8), (58, 22, 5), (84, 14, 4), (118, 22, 5), (146, 52, 9),
                       (164, 26, 5), (180, 42, 7), (196, 22, 5), (70, 32, 5), (130, 30, 6)]:       # stalactites
        poly(far, [(x - w, 0), (x + w, 0), (x + 0.5, ln)], '#1a2436')
        poly(far, [(x + w * 0.3, 0), (x + w, 0), (x + 0.5, ln)], '#121a2a')
        line(far, x - w + 1, 0, x, ln - 1, '#30465e')
        if ln > 25:
            far.px(x, ln + 3, '#46d0e6')
    for (cx, cy, s) in [(22, 96, 9), (178, 70, 11), (168, 128, 7), (42, 134, 6)]:
        ring_glow(far, cx, cy, s * 2.6, '#2a8aa0', s * 2.1, levels=((1.0, 0.12), (0.58, 0.24)))
        crystal_cluster(far, cx, cy + s * 0.6, s * 1.5, GLOW, int(cx + cy), spread=0.8, girth=0.32, n=3)
    # mid: rock wall and stalagmites flanking the arena
    rock, rlit = '#111826', '#2e4e62'
    col_l = m_poly([(-6, HORIZON + 6), (-6, 0), (16, 0), (20, 26), (13, 64), (18, 100), (16, 124), (28, HORIZON + 6)])
    paint(mid, col_l, rock)
    paint(mid, rim(col_l, 'r'), rlit)
    tint(mid, col_l & (_XX < 6), '#000000', 0.3)
    for (x, h, w, s) in [(38, 30, 8, 1), (52, 18, 5, 1), (156, 38, 9, -1), (174, 26, 7, -1), (190, 46, 10, -1), (68, 10, 4, 1)]:
        m = m_poly([(x - w, HORIZON + 6), (x + w, HORIZON + 6), (x + s, HORIZON + 6 - h)])
        paint(mid, m, rock)
        paint(mid, rim(m, 'r' if s > 0 else 'l'), rlit)
    for (cx, s) in [(46, 7), (164, 9), (186, 6)]:
        ring_glow(mid, cx, HORIZON - 2, s * 2.6, '#2a8aa0', s * 1.8)
        crystal_cluster(mid, cx, HORIZON + 4, s * 1.7, GLOW, cx, spread=0.8, girth=0.32, n=3)
    # ground: damp slab floor with glowing pools
    bands(gr, ['#34485a', '#2e4052', '#28384a', '#223042', '#1c283a', '#172232'], HORIZON, H, soft=2, curve=0.85)
    ids = ground_cells(seed, spacing=0.13, vy=60, vscale=1.7)
    shade_cells(gr, ids, [0.9, 1.0, 1.08], seed)
    edges = cell_edges(ids) & (_YY > HORIZON)
    below = np.roll(edges, 1, axis=0) & ~edges
    tint(gr, below, '#6a8ea0', 0.35)
    paint(gr, edges, '#10161f')
    ring_glow(gr, 100, 206, 96, '#3e7e8c', 44, levels=((1.0, 0.12), (0.6, 0.22)))
    paint(gr, _YY == HORIZON, '#10161f')
    for (cx, cy, rx, ry) in [(36, 180, 16, 4), (164, 236, 22, 6), (152, 170, 10, 3), (56, 248, 14, 4)]:
        ring_glow(gr, cx, cy, rx * 1.6, '#2aa0b0', ry * 2.2, levels=((1.0, 0.2),))
        puddle(gr, cx, cy, rx, ry, '#0e1620', '#1e7c90', '#32b2c6', '#c8faff')
    for (x, y) in [(14, 206), (186, 190), (120, 164), (70, 166), (196, 246)]:
        crystal_cluster(gr, x, y, 7, GLOW, x + y, spread=0.7, girth=0.34, n=2)
    # fore: rock framing with glowing crystals
    for pts, side in [([(-4, H), (-4, 204), (8, 210), (16, 230), (30, 248), (40, 264), (44, H)], 'r'),
                      ([(W + 4, H), (W + 4, 192), (192, 198), (184, 220), (170, 244), (160, 264), (158, H)], 'l')]:
        m = m_poly(pts)
        paint(fo, m, '#0c121c')
        paint(fo, m & (_YY > 250), '#080c14')
        paint(fo, rim(m, side) | rim(m, 't'), '#2a6272')
    ring_glow(fo, 182, 240, 16, '#2a8aa0', 12)
    crystal_cluster(fo, 184, 250, 24, GLOW, 5, spread=0.8, girth=0.3, n=3)
    crystal_cluster(fo, 16, 256, 14, GLOW, 6, spread=0.8, girth=0.3, n=2)
    for pts in ([(-4, 0), (40, 0), (22, 14), (8, 44), (-4, 54)], [(W + 4, 0), (160, 0), (178, 18), (192, 50), (W + 4, 60)]):
        m = m_poly(pts)
        paint(fo, m, '#0c121c')
        paint(fo, rim(m, 'b'), '#22485a')
    return far, mid, gr, fo


def spire(seed=91):
    far, mid, gr, fo = Layer(seed), Layer(seed + 1), Layer(seed + 2), Layer(seed + 3)
    sea_y = 126
    bands(far, ['#120a22', '#1a0f30', '#24163e', '#30204c', '#3a2a5a', '#3a3a66', '#34506e', '#326a7a', '#4a8a8c'], 0, sea_y)
    for (cx, cy, w, h, s) in [(20, 22, 70, 22, 1), (100, 10, 90, 20, 2), (182, 26, 70, 24, 3), (40, 64, 50, 14, 4),
                              (170, 76, 56, 14, 5), (8, 96, 34, 10, 6), (196, 104, 30, 9, 7)]:
        cloud(far, cx, cy, w, h, '#2a1c46', '#1c1234', '#5a4a8a', seed + s)
    # lightning fork
    pts = [(176, 36), (170, 54), (178, 66), (166, 86), (172, 98), (162, 124)]
    for (a, b) in zip(pts, pts[1:]):
        line(far, a[0] + 1, a[1], b[0] + 1, b[1], '#8ad8ff')
        line(far, a[0], a[1], b[0], b[1], '#f4fcff')
    line(far, 178, 66, 190, 80, '#bfe8ff')
    line(far, 190, 80, 188, 92, '#bfe8ff')
    # the great saltglass spire
    ring_glow(far, 100, 70, 44, '#6ac8d8', 90, levels=((1.0, 0.1), (0.7, 0.18)))
    base, tip = sea_y + 4, (102, -30)
    xs = [76, 88, 97, 108, 116, 124]
    fcols = ['#e8fbff', '#b4e6f0', '#86cadc', '#5a9cbc', '#3e6a96']
    for i in range(5):
        poly(far, [(xs[i], base), tip, (xs[i + 1], base)], fcols[i])
    for (y, x0, x1) in [(96, 88, 108), (60, 94, 106), (112, 84, 114), (30, 97, 105)]:     # fracture bands
        line(far, x0, y, x1, y - 3, '#4a3a7a')
        line(far, x0, y + 1, x1, y - 2, '#d8ccff')
    line(far, 99, base - 2, 101.5, -20, '#ffffff')
    line(far, 100, base - 2, 102.5, -20, '#bff8ff')
    for y in (46, 84, 118):
        paint(far, m_poly([(100, y - 5), (104, y), (100, y + 5), (96, y)]), '#ffffff')
    for (x, h, w, ln) in [(66, 44, 7, -0.25), (136, 52, 8, 0.22), (56, 22, 4, -0.3), (146, 26, 5, 0.3), (84, 18, 4, -0.1)]:
        shard(far, x, base, h, w, STORM, ln)
    bands(far, ['#162c3c', '#1a3646', '#1e4052', '#244c5e'], sea_y, HORIZON + 10, soft=1)
    rocks = m_poly([(48, base + 6), (54, base - 2), (62, base - 6), (70, base - 3), (78, base - 9), (90, base - 4),
                    (100, base - 7), (112, base - 3), (124, base - 10), (134, base - 4), (142, base - 6), (150, base + 6)])
    paint(far, rocks, '#1c2234')
    paint(far, rim(rocks, 't'), '#46587a')
    paint(far, rocks & (_YY > base + 2), '#141a28')
    for x in range(44, 156):
        if (x * 7) % 5 < 3:
            far.px(x, base + 6 + math.sin(x * 0.7) * 1.2, '#e0f6f6')
    glints(far, far.rng, 70, sea_y + 2, HORIZON + 8, ['#d8f4f4', '#6ab4bc', '#8ad0d4'], maxlen=6)
    line(far, 0, sea_y, W - 1, sea_y, '#12202e')
    # mid: breakers exploding against rocks on both flanks
    for side in (0, 1):
        def X(x):
            return x if side == 0 else W - 1 - x

        def P(pts):
            return [(X(x), y) for x, y in pts]
        swell = m_poly(P([(-8, HORIZON + 6), (-8, 134), (20, 130), (46, 132), (70, 138), (86, HORIZON + 6)]))
        paint(mid, swell, '#1e5e6c')
        paint(mid, swell & (_YY > 142), '#23707e')
        paint(mid, rim(swell, 't'), '#e6f8f8')
        splash(mid, X(22), 116, 30, seed + side, -1 if side else 1)
        rock = m_poly(P([(-8, HORIZON + 6), (-8, 124), (6, 118), (14, 122), (24, 116), (34, 126), (42, 138), (50, HORIZON + 6)]))
        paint(mid, rock, '#1a2030')
        paint(mid, rim(rock, 't'), '#46587a')
        paint(mid, rim(rock, 'r' if side == 0 else 'l'), '#34405c')
        foam = np.zeros((H, W), dtype=bool)
        for k in range(8):
            foam |= m_ellipse(X(-4 + k * 8), HORIZON - 3 + (k % 2) * 2, 6, 3)
        paint(mid, foam & (_YY < HORIZON + 6), '#bfe8ec')
        paint(mid, rim(foam, 't') & (_YY < HORIZON + 6), '#f4fcfc')
    # ground: cracked saltglass platform
    bands(gr, ['#a4bcd2', '#90aac6', '#7e98b8', '#6e86aa', '#60769c', '#556a90'], HORIZON, H, soft=2, curve=0.85)
    ids = ground_cells(seed + 1, spacing=0.16, vy=60, vscale=1.5)
    shade_cells(gr, ids, [0.88, 0.96, 1.05, 1.12], seed)
    edges = cell_edges(ids) & (_YY > HORIZON + 2)
    below = np.roll(edges, 1, axis=0) & ~edges
    tint(gr, below, '#e6f6ff', 0.4)
    paint(gr, edges, '#2a3052')
    rng = random.Random(seed)
    glow_ids = set(rng.sample(range(int(ids.max()) + 1), int(ids.max() * 0.2)))
    lit_edges = edges & np.isin(ids, list(glow_ids)) & (BAYER[_YY % 4, _XX % 4] < 0.9)
    paint(gr, lit_edges, '#7aeeff')
    for y in range(HORIZON, HORIZON + 3):
        for x in range(W):
            gr.px(x, y, '#d6f2fa' if y == HORIZON else ('#8ab0c8' if y == HORIZON + 1 else '#3a4870'))
    ring = m_ellipse(100, 214, 74, 27) & ~m_ellipse(100, 214, 72, 25.5)
    paint(gr, ring & (BAYER[_YY % 4, _XX % 4] < 0.75), '#8af2ff')
    for k in range(12):
        a = k * math.pi / 6
        gr.px(100 + math.cos(a) * 80, 214 + math.sin(a) * 30, '#bff8ff')
    # fore: storm-lit crystal spikes
    shard(fo, 6, H + 2, 70, 11, STORM, 0.06)
    shard(fo, 22, H + 2, 36, 6, STORM, 0.24)
    shard(fo, -6, H + 2, 44, 8, STORM, 0.12)
    shard(fo, 194, H + 2, 78, 11, STORM, -0.06)
    shard(fo, 178, H + 2, 40, 7, STORM, -0.24)
    shard(fo, 206, H + 2, 50, 8, STORM, -0.1)
    for _ in range(14):
        x = fo.rng.choice([fo.rng.randint(0, 40), fo.rng.randint(160, 199)])
        fo.px(x, fo.rng.randint(150, 230), '#dff6f8')
    return far, mid, gr, fo


# ---------------------------------------------------------------- Evolution Tower halls
TOWER = {
    'ember': dict(dark='#140a0a', wall='#4a2622', wall2='#54302a', mortar='#2a1412', trim='#8a4a3a', trim_lit='#c47a52',
                  floor=('#6e4034', '#58322a'), grout='#2a1412', light='#ff9a4a', vista=['#5a1a14', '#8a2a18', '#c8481e', '#f07a2a', '#ffb050'],
                  accent='#ffb050', banner=('#8a1e1a', '#5a1210'), gem='#ffd070'),
    'tide': dict(dark='#080e1a', wall='#1e3048', wall2='#24384f', mortar='#101a2a', trim='#3e6284', trim_lit='#78b0d0',
                 floor=('#3a5a72', '#2c465c'), grout='#121c2c', light='#5ad0f0', vista=['#0a2440', '#12385a', '#1e5a80', '#3a88aa', '#7ac8d8'],
                 accent='#7ae4ff', banner=('#1a4a7a', '#10304e'), gem='#bff6ff'),
    'verdant': dict(dark='#0a120a', wall='#2a3622', wall2='#324028', mortar='#161e12', trim='#56663e', trim_lit='#96a86a',
                    floor=('#4c5c38', '#3c4a2c'), grout='#1a2212', light='#b0e070', vista=['#1e3a1a', '#2e5a24', '#4a8a34', '#86c05a', '#d4f0a0'],
                    accent='#b8f070', banner=('#2e5a26', '#1c3a18'), gem='#e0ffb0'),
}


def flame(layer, cx, base, h, w, cols=('#b8341a', '#ff7a2a', '#ffd070', '#fff4c0'), seed=0):
    rng = random.Random(seed)
    for k, (col, s) in enumerate(zip(cols, (1.0, 0.72, 0.46, 0.22))):
        hh, ww = h * s, w * s
        pts = [(cx - ww, base), (cx - ww * 0.8, base - hh * 0.4), (cx - ww * 0.3 + rng.uniform(-1, 1), base - hh * 0.75),
               (cx + rng.uniform(-1.5, 1.5), base - hh), (cx + ww * 0.35, base - hh * 0.6), (cx + ww * 0.7, base - hh * 0.8),
               (cx + ww, base - hh * 0.3), (cx + ww, base)]
        poly(layer, pts, col)


def vine(layer, x0, y0, x1, y1, amp, cols, seed, leaves=True):
    rng = random.Random(seed)
    n = int(math.hypot(x1 - x0, y1 - y0)) + 1
    for s in range(n):
        t = s / n
        x = x0 + (x1 - x0) * t + amp * math.sin(t * 9 + seed)
        y = y0 + (y1 - y0) * t
        layer.px(x, y, cols[0])
        layer.px(x + 1, y, cols[1])
        if leaves and s % 5 == 0:
            side = 1 if (s // 5) % 2 else -1
            layer.px(x + side * 2, y, cols[2])
            layer.px(x + side * 3, y - 1, cols[2])
            layer.px(x + side * 2, y - 1, cols[3])
        if leaves and s % 23 == 11 and rng.random() < 0.6:
            layer.px(x + 2, y + 1, '#f0d0e8')


def tower_hall(el, seed):
    p = TOWER[el]
    far, mid, gr, fo = Layer(seed), Layer(seed + 1), Layer(seed + 2), Layer(seed + 3)
    wall, wall2, mortar = _c(p['wall']), _c(p['wall2']), _c(p['mortar'])
    # far: brick back wall that fades into a dark vault
    for y in range(0, HORIZON + 10):
        row = y // 9
        off = (row % 2) * 9
        for x in range(W):
            if y % 9 == 0 or (x + off) % 18 == 0:
                c = mortar
            else:
                c = wall if ((row * 7 + (x + off) // 18 * 3) % 5) else wall2
                if y % 9 == 1:
                    c = c * 1.12
            far.c[y, x] = c
            far.a[y, x] = 1
    for lvl, (y1, amt) in enumerate([(26, 0.72), (48, 0.5), (72, 0.3)]):
        m = (_YY < y1 + (BAYER[_YY % 4, _XX % 4] - 0.5) * 4)
        tint(far, m, p['dark'], 0.3)
    ring_glow(far, 100, 150, 110, p['light'], 70, levels=((1.0, 0.08), (0.62, 0.14)))
    # great doorway with the element's vista
    door = m_ellipse(100, 84, 28, 34) & (_YY < 84) | m_poly([(72, 84), (128, 84), (128, 152), (72, 152)])
    frame_m = m_ellipse(100, 84, 35, 41) & (_YY < 84) | m_poly([(65, 84), (135, 84), (135, 152), (65, 152)])
    paint(far, frame_m & ~door, p['trim'])
    for k in range(9):                                        # voussoir joints
        a = math.pi * (k + 0.5) / 9
        line(far, 100 - math.cos(a) * 28, 84 - math.sin(a) * 34, 100 - math.cos(a) * 35, 84 - math.sin(a) * 41, p['mortar'])
    for y in range(92, 152, 10):
        line(far, 65, y, 71, y, p['mortar'])
        line(far, 129, y, 135, y, p['mortar'])
    line(far, 65, 84, 65, 152, p['trim_lit'])
    paint(far, m_poly([(96, 42), (104, 42), (106, 52), (94, 52)]), p['trim_lit'])
    paint(far, m_ellipse(100, 47, 2.5, 2.5), p['gem'])
    view = Layer(seed + 7)
    bands(view, p['vista'], 48, 152, soft=2)
    vr = random.Random(seed)
    if el == 'ember':
        for (x, w, h) in [(74, 12, 30), (88, 10, 18), (116, 14, 26), (126, 8, 36)]:
            poly(view, [(x - w, 152), (x - w * 0.3, 152 - h), (x + w * 0.4, 152 - h * 0.8), (x + w, 152)], '#2a0c0a')
        for x in (84, 108, 120):
            line(view, x, 60 + (x % 7), x + 1, 150, '#ffd070')
            line(view, x + 1, 60 + (x % 7), x + 2, 150, '#ff8a30')
        glints(view, vr, 20, 60, 140, ['#fff0b0', '#ffb050'], 72, 128, 1)
    elif el == 'tide':
        for x in (80, 100, 118):
            for y in range(50, 152):
                if (y // 2 + x) % 3 == 0:
                    view.px(x + (y - 50) * 0.15, y, '#5ab4d0')
        for (x, h) in [(76, 34), (84, 22), (122, 40), (114, 20)]:
            vine(view, x, 152, x + 2, 152 - h, 2, ['#0e3a4a', '#16505e', '#1e6070', '#2a7a86'], x, leaves=True)
        for _ in range(14):
            x, y = vr.randint(74, 126), vr.randint(56, 140)
            view.px(x, y, '#bff6ff')
            view.px(x + 1, y - 1, '#7ad0e8')
    else:
        for (cx, cy, r) in [(82, 70, 14), (118, 64, 16), (100, 56, 12), (78, 100, 10), (124, 96, 12)]:
            paint(view, m_ellipse(cx, cy, r, r * 0.8), '#3a7a2e')
            paint(view, m_ellipse(cx - 2, cy - 2, r * 0.7, r * 0.5), '#5aa040')
        poly(view, [(90, 152), (96, 132), (97, 84), (104, 84), (105, 132), (112, 152)], '#3a2a1a')
        line(view, 97, 104, 84, 86, '#3a2a1a', 2)
        line(view, 104, 98, 116, 80, '#3a2a1a', 2)
        line(view, 97, 90, 97, 140, '#5a4028')
        for (cx, cy, r) in [(86, 80, 11), (116, 76, 12), (100, 70, 13)]:
            paint(view, m_ellipse(cx, cy, r, r * 0.75), '#2e6a26')
            paint(view, m_ellipse(cx - 2, cy - 3, r * 0.65, r * 0.45), '#6ab048')
        for x in (86, 108, 116):
            for y in range(60, 150):
                if (y + x) % 4 == 0:
                    view.px(x + (y - 60) * 0.3, y, '#e8ffc0')
    far.c[door] = view.c[door]
    # alcoves with element relics
    for ax in (20, 150):
        alc = m_ellipse(ax + 15, 104, 15, 16) & (_YY < 104) | m_poly([(ax, 104), (ax + 30, 104), (ax + 30, 150), (ax, 150)])
        fr = m_ellipse(ax + 15, 104, 19, 20) & (_YY < 104) | m_poly([(ax - 4, 104), (ax + 34, 104), (ax + 34, 150), (ax - 4, 150)])
        paint(far, fr & ~alc, p['trim'])
        paint(far, alc, p['dark'])
        ring_glow(far, ax + 15, 118, 16, p['light'], 20, levels=((1.0, 0.18), (0.55, 0.3)))
    far.rect(0, 146, W, 150, p['trim'])
    far.rect(0, 146, W, 147, p['trim_lit'])
    # mid: pillars, arches and element features
    pil = _c(p['trim'])
    for cx in (-2, 58, 142, 202):
        x0 = cx - 8
        for y in range(0, HORIZON + 6):
            for x in range(x0, x0 + 16):
                k = x - x0
                c = pil * (1.25 if k < 3 else (0.7 if k > 12 else (0.92 if k % 4 == 3 else 1.0)))
                mid.px(x, y, c)
        mid.rect(x0 - 3, 30, x0 + 19, 38, _c(p['trim_lit']))
        mid.rect(x0 - 3, 36, x0 + 19, 38, pil * 0.7)
        mid.rect(x0 - 3, 138, x0 + 19, HORIZON + 6, pil * 0.85)
        mid.rect(x0 - 3, 138, x0 + 19, 140, _c(p['trim_lit']))
        ring_glow(mid, cx, 118, 20, p['light'], 30, levels=((1.0, 0.2),))
    for (xa, xb) in [(-2, 58), (142, 202)]:
        for k in range(60):
            t = k / 59
            x = xa + (xb - xa) * t
            y = 30 - math.sin(t * math.pi) * 22
            for d in range(5):
                mid.px(x, y - d, pil * (0.75 if d == 0 else (1.2 if d == 4 else 1.0)))
    for cx in (58, 142):                                          # banners on the inner pillars
        bx = cx - 6
        paint(mid, m_poly([(bx, 40), (bx + 12, 40), (bx + 12, 92), (bx + 6, 86), (bx, 92)]), p['banner'][0])
        paint(mid, m_poly([(bx + 9, 40), (bx + 12, 40), (bx + 12, 92), (bx + 9, 89)]), p['banner'][1])
        mid.rect(bx - 1, 39, bx + 13, 42, _c(p['accent']))
        paint(mid, m_poly([(bx + 6, 56), (bx + 10, 62), (bx + 6, 68), (bx + 2, 62)]), p['accent'])
        paint(mid, m_poly([(bx + 6, 59), (bx + 8, 62), (bx + 6, 65), (bx + 4, 62)]), p['gem'])
    if el == 'ember':
        for cx in (35, 165):
            mid.rect(cx - 1, 124, cx + 2, HORIZON + 4, '#2a1612')
            poly(mid, [(cx - 8, 118), (cx + 9, 118), (cx + 6, 125), (cx - 5, 125)], '#6a3a2a')
            line(mid, cx - 8, 118, cx + 9, 118, '#c47a52')
            mid.rect(cx - 5, HORIZON, cx + 6, HORIZON + 5, '#3a1e18')
            ring_glow(mid, cx, 104, 22, '#ff9a4a', 22, levels=((1.0, 0.18), (0.55, 0.3)))
            flame(mid, cx, 119, 22, 7, seed=cx)
    elif el == 'tide':
        for cx in (35, 165):
            mid.rect(cx - 5, 134, cx + 6, HORIZON + 5, p['trim'])
            mid.rect(cx - 6, 132, cx + 7, 135, p['trim_lit'])
            ring_glow(mid, cx, 112, 18, '#5ad0f0', 20, levels=((1.0, 0.18), (0.55, 0.3)))
            paint(mid, m_poly([(cx, 96), (cx + 7, 112), (cx, 126), (cx - 7, 112)]), '#2a9ac8')
            paint(mid, m_poly([(cx, 96), (cx, 126), (cx - 7, 112)]), '#7ae4ff')
            line(mid, cx - 3, 104, cx - 1, 100, '#f0ffff')
            for k in range(3):
                mid.px(cx - 8 + k * 8, 128 - k * 2, '#bff6ff')
    else:
        for cx in (-2, 58, 142, 202):
            vine(mid, cx - 6, 0, cx + 2, HORIZON + 4, 5, ['#1e3a18', '#2e5a24', '#5aa040', '#96d060'], cx + 3)
        for (xa, xb) in [(-2, 58), (142, 202), (58, 142)]:
            for k in range(0, 60, 6):
                t = k / 59
                x = xa + (xb - xa) * t
                ln = 10 + ((k * 7 + xa) % 17)
                vine(mid, x, 26 - math.sin(t * math.pi) * 18, x + 1, 26 - math.sin(t * math.pi) * 18 + ln, 1,
                     ['#1e3a18', '#2e5a24', '#5aa040', '#96d060'], k + xa)
        for cx in (35, 165):
            mid.rect(cx - 6, 132, cx + 7, HORIZON + 5, p['trim'])
            mid.rect(cx - 7, 130, cx + 8, 133, p['trim_lit'])
            paint(mid, m_ellipse(cx, 122, 11, 9), '#2e5a24')
            paint(mid, m_ellipse(cx - 2, 119, 7, 5), '#5aa040')
            paint(mid, m_ellipse(cx - 3, 117, 3, 2), '#96d060')
            for (fx, fy) in [(cx + 4, 116), (cx - 6, 124), (cx + 6, 126)]:
                mid.px(fx, fy, '#f0d0e8')
                mid.px(fx + 1, fy, '#d890c0')
    # ground: polished tiles in perspective, element sigil and doorway light
    vy = 70
    fa, fb, grout = _c(p['floor'][0]), _c(p['floor'][1]), _c(p['grout'])
    for y in range(HORIZON, H):
        d = y - vy
        v = 100.0 / d
        j = int(math.floor(v / 0.075))
        jn = int(math.floor(100.0 / (d + 1) / 0.075))
        for x in range(W):
            u = (x + 0.5 - W / 2) / d
            i = int(math.floor(u / 0.2 + 0.5))
            il = int(math.floor((x - 0.5 - W / 2) / d / 0.2 + 0.5))
            if il != i or jn != j:
                c = grout
            else:
                c = fa if (i + j) % 2 else fb
                if (y - vy) and int(math.floor(100.0 / (d - 1) / 0.075)) != j:
                    c = c * 1.15
            gr.c[y, x] = c
            gr.a[y, x] = 1
    ring_glow(gr, 100, 156, 44, p['light'], 40, levels=((1.0, 0.1), (0.62, 0.18), (0.32, 0.26)))
    for side in (0, 1):
        m = (_XX < 24 + (BAYER[_YY % 4, _XX % 4] - 0.5) * 6) if side == 0 else (_XX > W - 25 + (BAYER[_YY % 4, _XX % 4] - 0.5) * 6)
        tint(gr, m & (_YY >= HORIZON), p['dark'], 0.3)
    sig = mixc(p['accent'], p['floor'][0], 0.45)
    ring_o = m_ellipse(100, 212, 72, 26) & ~m_ellipse(100, 212, 70, 24.8)
    ring_i = m_ellipse(100, 212, 54, 19) & ~m_ellipse(100, 212, 52.5, 18)
    paint(gr, ring_o | ring_i, sig)
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        x, y = 100 + math.cos(a) * 62, 212 + math.sin(a) * 22.4
        paint(gr, m_poly([(x, y - 2), (x + 3, y), (x, y + 2), (x - 3, y)]), p['accent'])
    paint(gr, _YY == HORIZON, p['grout'])
    grout_m = np.all(np.abs(gr.c - grout) < 1, axis=2) & (_YY > HORIZON + 4)
    frng = random.Random(seed + 5)
    if el == 'ember':                                          # cracked tiles leaking heat
        for (x, y, ln) in [(34, 176, 10), (150, 188, 14), (70, 246, 16), (170, 238, 12), (120, 168, 8), (20, 214, 12)]:
            pts = [(x, y)]
            for k in range(3):
                pts.append((pts[-1][0] + ln / 3 + frng.uniform(-1, 1), pts[-1][1] + frng.uniform(-2, 2)))
            for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
                line(gr, xa, ya + 1, xb, yb + 1, '#2a1412')
                line(gr, xa, ya, xb, yb, '#ff8a30')
            gr.px(pts[1][0], pts[1][1], '#ffd070')
        for _ in range(40):
            gr.px(frng.randint(0, W - 1), frng.randint(HORIZON + 6, H - 1), '#3a2420')
    elif el == 'tide':                                         # caustic ripples of light
        shimmer = mixc(p['accent'], p['floor'][0], 0.5)
        for (cx, cy, rx, ry) in [(52, 186, 22, 7), (150, 176, 20, 6), (100, 250, 30, 9), (30, 238, 16, 7), (172, 234, 18, 7)]:
            t = (cy - HORIZON) / (H - HORIZON)
            for _ in range(9):
                x, y = cx + frng.uniform(-rx, rx), cy + frng.uniform(-ry, ry)
                ln = int(3 + t * 5)
                for k in range(ln):
                    gr.px(x + k, y + round(math.sin(k * 1.4) * 0.8), shimmer)
    else:                                                      # moss creeping through the grout
        patches = np.zeros((H, W), dtype=bool)
        for _ in range(26):
            x, y = frng.randint(0, W - 1), frng.randint(HORIZON + 8, H - 1)
            t = (y - HORIZON) / (H - HORIZON)
            patches |= m_ellipse(x, y, 4 + t * 8, 1.5 + t * 3)
        moss = grout_m & patches
        paint(gr, moss, '#4a7a30')
        paint(gr, np.roll(moss, -1, 0) & ~grout_m & (BAYER[_YY % 4, _XX % 4] < 0.4), '#3e6a2a')
        for (x, y) in [(30, 180), (160, 172), (18, 236), (178, 222), (64, 260), (140, 256), (110, 166)]:
            for k in range(5):
                gr.blades(x + k - 2, y, 3 + (k % 3) * 2, '#6aa84a', lean=(k - 2) * 0.3)
    # fore: framing pillars and element accents
    for (x0, lit_x) in [(-6, 9), (190, 190)]:
        fo.rect(x0, 0, x0 + 16, H, pil * 0.45)
        fo.rect(lit_x, 0, lit_x + 1, H, mixc(p['light'], p['trim'], 0.5))
        fo.rect(x0 - 2, 238, x0 + 18, H, pil * 0.55)
        fo.rect(x0 - 2, 238, x0 + 18, 240, mixc(p['light'], p['trim'], 0.4))
    if el == 'ember':
        for (x, y, w) in [(14, 256, 14), (184, 260, 12)]:
            paint(fo, m_poly([(x - w, H), (x - w + 3, y), (x + w - 2, y + 2), (x + w, H)]), '#3a1e18')
            line(fo, x - w + 4, y + 5, x + 2, y + 9, '#ff7a2a')
            line(fo, x + 2, y + 9, x + 6, y + 6, '#ffc060')
        for _ in range(16):
            x = fo.rng.choice([fo.rng.randint(12, 36), fo.rng.randint(164, 188)])
            fo.px(x, fo.rng.randint(170, 250), '#ffb050' if fo.rng.random() < 0.5 else '#ff7a2a')
    elif el == 'tide':
        tide_pal = ['#f0ffff', '#9ae8fa', '#46b8e0', '#2a78b0', '#1a4a80']
        crystal_cluster(fo, 18, H + 2, 26, tide_pal, 3)
        crystal_cluster(fo, 184, H + 2, 30, tide_pal, 4)
        for _ in range(10):
            x = fo.rng.choice([fo.rng.randint(12, 34), fo.rng.randint(166, 188)])
            y = fo.rng.randint(170, 236)
            fo.px(x, y, '#bff6ff')
            fo.px(x, y - 1, '#5ad0f0')
    else:
        vc = ['#1e3a18', '#2e5a24', '#5aa040', '#96d060']
        vine(fo, 10, 0, 12, 150, 3, vc, 1)
        vine(fo, 190, 0, 188, 130, 3, vc, 2)
        vine(fo, 16, 0, 26, 64, 2, vc, 3)
        vine(fo, 184, 0, 172, 58, 2, vc, 4)
        fore_grass(fo, ['#2e5a24', '#5aa040', '#96d060', '#1e3a18'], seed, density=0.5, reach=30)
    return far, mid, gr, fo


def tower_ember(seed=101):
    return tower_hall('ember', seed)


def tower_tide(seed=111):
    return tower_hall('tide', seed)


def tower_verdant(seed=121):
    return tower_hall('verdant', seed)


ENVIRONMENTS = {'forest': forest, 'ruins': ruins, 'scorched': scorched, 'flooded': flooded, 'heart': heart,
                'shore': shore, 'wreck': wreck, 'caves': caves, 'spire': spire,
                'tower_ember': tower_ember, 'tower_tide': tower_tide, 'tower_verdant': tower_verdant}
# stages added after World 1 are written with PNG optimisation (World 1 files stay byte-identical)
OPTIMIZED = {'shore', 'wreck', 'caves', 'spire', 'tower_ember', 'tower_tide', 'tower_verdant'}


def build_all(only=None):
    out = os.path.join(ROOT, 'assets/environments/battle')
    os.makedirs(out, exist_ok=True)
    for name, fn in ENVIRONMENTS.items():
        if only and name not in only:
            continue
        layers = fn()
        for lname, layer in zip(['far', 'mid', 'ground', 'fore'], layers):
            path = os.path.join(out, f'{name}_{lname}.png')
            if name in OPTIMIZED:
                layer.image().save(path, optimize=True)
            else:
                layer.image().save(path)
    print('battle stages generated')


if __name__ == '__main__':
    import sys
    # optional: python3 tools/battle_bg.py shore,wreck   (build only the listed stages)
    build_all(set(sys.argv[1].split(',')) if len(sys.argv) > 1 else None)
