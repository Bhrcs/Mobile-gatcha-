"""Original 480x270 pixel-art environments for Ashroot Wilds."""
import math
import random
import numpy as np
from PIL import Image

W, H = 480, 270
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0


def hx(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64)


class BG:
    def __init__(self, seed=1):
        self.a = np.zeros((H, W, 3), dtype=np.float64)
        self.rng = random.Random(seed)
        self.nrng = np.random.default_rng(seed)

    def gradient(self, stops, y0=0, y1=H, bands=8):
        """Dithered vertical gradient through colour stops."""
        cols = [hx(c) for c in stops]
        for y in range(y0, y1):
            t = (y - y0) / max(1, (y1 - y0 - 1))
            for x in range(W):
                tt = t * bands + BAYER[y % 4, x % 4] - 0.5
                tt = min(max(tt / bands, 0), 1)
                seg = tt * (len(cols) - 1)
                i = min(int(seg), len(cols) - 2)
                f = seg - i
                q = round(f * 3) / 3
                self.a[y, x] = cols[i] * (1 - q) + cols[i + 1] * q

    def ridge(self, base_y, amp, color, seed, freq=0.02, rough=0.5, color2=None):
        rng = random.Random(seed)
        ph = [rng.uniform(0, 100) for _ in range(4)]
        c = hx(color)
        c2 = hx(color2) if color2 else c
        tops = []
        for x in range(W):
            y = base_y - amp * (0.55 * math.sin(x * freq + ph[0]) + 0.3 * math.sin(x * freq * 2.3 + ph[1])
                                + rough * 0.2 * math.sin(x * freq * 6.1 + ph[2]))
            y = int(y)
            tops.append(y)
            for yy in range(max(0, y), H):
                self.a[yy, x] = c if (yy - y) > 3 or (x + yy) % 2 else c2
        return tops

    def rect(self, x0, y0, x1, y1, color):
        c = hx(color)
        self.a[max(0, y0):min(H, y1), max(0, x0):min(W, x1)] = c

    def px(self, x, y, color):
        if 0 <= x < W and 0 <= y < H:
            self.a[int(y), int(x)] = hx(color) if isinstance(color, str) else color

    def ellipse(self, cx, cy, rx, ry, color, dither_edge=False):
        c = hx(color)
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if d <= 1 and 0 <= x < W and 0 <= y < H:
                    if dither_edge and d > 0.8 and (x + y) % 2:
                        continue
                    self.a[y, x] = c

    def conifer(self, x, base, h, dark, mid=None, light=None):
        dark = hx(dark)
        mid = hx(mid) if mid else dark
        light = hx(light) if light else mid
        for yy in range(h):
            y = base - yy
            half = int((h - yy) * 0.33 + 1 + ((yy % 6) < 2) * 1.5)
            for xx in range(-half, half + 1):
                c = dark
                if xx < -half * 0.3:
                    c = light if (yy % 6) >= 2 else mid
                elif xx < half * 0.3:
                    c = mid
                self.px(x + xx, y, c)
        for yy in range(4):
            self.px(x, base + yy, dark * 0.7)

    def round_tree(self, x, base, h, trunk, leaves):
        tc = hx(trunk)
        for yy in range(int(h * 0.45)):
            for xx in (-1, 0, 1):
                self.px(x + xx, base - yy, tc if xx < 1 else tc * 0.7)
        cols = [hx(c) for c in leaves]
        r = h * 0.35
        blobs = [(0, -h * 0.6, r), (-r * 0.7, -h * 0.5, r * 0.75), (r * 0.7, -h * 0.5, r * 0.75),
                 (0, -h * 0.8, r * 0.7)]
        for (bx, by, br) in blobs:
            for yy in range(int(-br), int(br) + 1):
                for xx in range(int(-br), int(br) + 1):
                    if xx * xx + yy * yy <= br * br:
                        shade = (xx + yy) / (br * 2)
                        i = 0 if shade < -0.25 else (1 if shade < 0.15 else 2)
                        if abs(xx * xx + yy * yy - br * br) < br * 1.5 and (xx + yy) % 2:
                            i = 2
                        self.px(x + bx + xx, base + by + yy, cols[i])

    def ground(self, y0, top, mid, low, grass=None, seed=3):
        rng = random.Random(seed)
        self.gradient([top, mid, low], y0, H, bands=6)
        if grass:
            g = [hx(c) for c in grass]
            for x in range(W):
                for k in range(rng.randint(0, 3)):
                    self.px(x, y0 + k - 1, g[(x + k) % len(g)])
            for _ in range(160):
                x, y = rng.randint(0, W - 1), rng.randint(y0 + 4, H - 1)
                self.px(x, y, g[rng.randint(0, len(g) - 1)])
                self.px(x, y - 1, g[0])

    def pebbles(self, y0, color, n=60, seed=4):
        rng = random.Random(seed)
        c = hx(color)
        for _ in range(n):
            x, y = rng.randint(0, W - 2), rng.randint(y0, H - 2)
            self.px(x, y, c)
            self.px(x + 1, y, c * 0.8)

    def pillar(self, x, base, h, w=10, stone='#8a8478', broken=True, moss=True):
        s = hx(stone)
        top = base - h
        for y in range(top, base):
            for xx in range(w):
                c = s * (1.15 if xx < 2 else (0.75 if xx > w - 3 else 1.0))
                if (y - top) % 9 == 0:
                    c = s * 0.6
                self.px(x + xx, y, c)
        if broken:
            for xx in range(w):
                cut = int(3 * abs(math.sin(xx * 1.7 + x)))
                for y in range(top, top + cut):
                    if 0 <= x + xx < W:
                        self.a[y, x + xx] = self.sky_at(x + xx, y)
        if moss:
            for xx in range(-1, w + 1):
                if (xx + x) % 3:
                    self.px(x + xx, top + int(abs(math.sin(xx + x)) * 3) + 1, '#5a8a32')
        # base block
        for y in range(base - 4, base):
            for xx in range(-2, w + 2):
                self.px(x + xx, y, s * 0.85 if y > base - 2 else s)

    def sky_at(self, x, y):
        return self._sky[y, x] if hasattr(self, '_sky') else self.a[y, x]

    def snapshot_sky(self):
        self._sky = self.a.copy()

    def motes(self, n, colors, y0=0, y1=H, seed=7):
        rng = random.Random(seed)
        for _ in range(n):
            x, y = rng.randint(0, W - 1), rng.randint(y0, y1 - 1)
            self.px(x, y, colors[rng.randint(0, len(colors) - 1)])

    def arch(self, x, base, w, h, stone='#7a746a'):
        s = hx(stone)
        th = 8
        for xx in range(w):
            for y in range(base - h, base):
                inner_x = (xx - w / 2) / (w / 2 - th)
                inner_y = (base - h * 0.4 - y) / (h * 0.6 - th)
                outer_y = (base - h * 0.4 - y) / (h * 0.6)
                outer_x = (xx - w / 2) / (w / 2)
                inside_outer = outer_x ** 2 + max(outer_y, 0) ** 2 <= 1
                inside_inner = abs(inner_x) < 1 and (inner_x ** 2 + max(inner_y, 0) ** 2 <= 1)
                if inside_outer and not inside_inner:
                    c = s * (1.12 if xx < w / 2 else 0.85)
                    if (y + (xx // 6) * 3) % 7 == 0:
                        c = s * 0.6
                    self.px(x + xx, y, c)

    def water(self, y0, y1, deep, mid, light, seed=5):
        rng = random.Random(seed)
        self.gradient([mid, deep], y0, y1, bands=4)
        L = hx(light)
        for _ in range(int((y1 - y0) * 6)):
            x, y = rng.randint(0, W - 8), rng.randint(y0 + 1, y1 - 1)
            ln = rng.randint(3, 8)
            for k in range(ln):
                self.px(x + k, y, L if k % 3 else L * 0.85)

    def save(self, path, scale=1):
        img = Image.fromarray(np.clip(self.a, 0, 255).astype(np.uint8), 'RGB')
        if scale != 1:
            img = img.resize((W * scale, H * scale), Image.NEAREST)
        img.save(path)
        return img


# ---------------------------------------------------------------- scenes
def forest(seed=1):
    b = BG(seed)
    b.gradient(['#6fb0d8', '#a8d4e0', '#f0e0b0'], 0, 150, bands=10)
    b.snapshot_sky()
    b.ellipse(380, 40, 16, 16, '#fff6d8')
    for i, (cx, cy) in enumerate([(80, 40), (140, 30), (300, 55), (430, 25)]):
        for k in range(5):
            b.ellipse(cx + k * 9 - 18, cy + (k % 2) * 3, 10, 5, '#f4f6f8', dither_edge=True)
    b.ridge(120, 25, '#7fa0b8', seed + 1, freq=0.015, color2='#8fb0c4')
    b.ridge(140, 18, '#5a8070', seed + 2, freq=0.022)
    for x in range(-5, W + 10, 11):
        b.conifer(x + b.rng.randint(-3, 3), 160, b.rng.randint(28, 40), '#2c4a3a', '#3a5e44', '#4a7050')
    for x in range(0, W + 30, 38):
        b.round_tree(x + b.rng.randint(-8, 8), 172, b.rng.randint(40, 52), '#4a3222',
                     ['#6aa040', '#4a7e30', '#2f5a24'])
    b.ground(168, '#6a9a3a', '#5a7e32', '#46602a', grass=['#8ac050', '#6aa040', '#4a7e30'], seed=seed)
    # dirt path band where fighters stand
    for y in range(182, 214):
        for x in range(W):
            if (x + y) % 3 or y > 186:
                b.a[y, x] = b.a[y, x] * 0.35 + hx('#8a6e48') * 0.65
    b.pebbles(186, '#6a5438', 90, seed)
    return b


def ruins(seed=2):
    b = forest(seed)
    b.snapshot_sky()
    b.arch(40, 176, 70, 80)
    b.pillar(150, 176, 60, 12)
    b.pillar(330, 176, 44, 10)
    b.arch(390, 176, 60, 64, stone='#6e685e')
    b.pillar(250, 180, 18, 14, broken=False)
    for x in range(0, W, 2):
        if b.rng.random() < 0.3:
            b.px(x, 214 + b.rng.randint(0, 50), '#7a746a')
    return b


def scorched(seed=3):
    b = BG(seed)
    b.gradient(['#3a1c24', '#8a3a2a', '#e08a4a', '#f0b060'], 0, 150, bands=10)
    b.snapshot_sky()
    b.ellipse(120, 60, 22, 22, '#ffd08a')
    b.ridge(122, 22, '#5a2a2a', seed + 1, freq=0.017, color2='#6a3230')
    b.ridge(140, 16, '#3a1e1e', seed + 2, freq=0.024)
    for x in range(-5, W + 10, 14):
        # burnt conifers: dark trunks with a few charred branches
        base = 164
        h = b.rng.randint(24, 40)
        for yy in range(h):
            b.px(x, base - yy, '#1c1414')
            b.px(x + 1, base - yy, '#2a1c1a')
            if yy % 7 == 3 and yy > 6:
                ln = (h - yy) // 4 + 2
                for k in range(ln):
                    b.px(x - k, base - yy - k // 2, '#1c1414')
                    b.px(x + 1 + k, base - yy - k // 2, '#2a1c1a')
    b.ground(166, '#4a3028', '#3a2622', '#281a18', grass=['#6a3a2a', '#1c1414', '#8a4a2a'], seed=seed)
    for y in range(182, 214):
        for x in range(W):
            if (x + y) % 3 or y > 186:
                b.a[y, x] = b.a[y, x] * 0.4 + hx('#5a4036') * 0.6
    b.motes(140, ['#ffb03a', '#ff6a1e', '#fff0a0'], 0, 200, seed)
    for _ in range(50):
        x, y = b.rng.randint(0, W - 3), b.rng.randint(170, H - 2)
        b.px(x, y, '#ff6a1e')
        b.px(x + 1, y, '#c8361a')
    return b


def flooded(seed=4):
    b = BG(seed)
    b.gradient(['#4a6a9a', '#8ab0c8', '#c8dce0'], 0, 150, bands=10)
    b.snapshot_sky()
    for (cx, cy) in [(100, 30), (260, 50), (400, 35)]:
        for k in range(6):
            b.ellipse(cx + k * 10 - 25, cy + (k % 2) * 4, 12, 6, '#dfe8f0', dither_edge=True)
    b.ridge(125, 20, '#6a8098', seed + 1, freq=0.016)
    for x in range(-5, W + 10, 12):
        b.conifer(x + b.rng.randint(-3, 3), 158, b.rng.randint(24, 34), '#2a4048', '#34525a', '#40646a')
    b.ground(162, '#5a7a5a', '#4a6a50', '#3a5244', grass=['#6a9a5a', '#4a7a4a'], seed=seed)
    b.arch(20, 176, 64, 70, stone='#6a7078')
    b.pillar(120, 174, 46, 11, stone='#707880')
    b.pillar(360, 174, 56, 12, stone='#707880')
    b.arch(410, 176, 56, 60, stone='#626a72')
    # shallow flood water across the arena
    b.water(176, H, '#1c3a5a', '#3a6a8a', '#8ad0e8', seed)
    for y in range(182, 212):
        for x in range(W):
            if (x // 2 + y) % 5 == 0:
                b.a[y, x] = b.a[y, x] * 0.6 + hx('#a8e0f0') * 0.4
    return b


def heart(seed=5):
    b = BG(seed)
    b.gradient(['#12241c', '#1e3e2a', '#2e5a36', '#4a7a3a'], 0, 170, bands=10)
    b.snapshot_sky()
    # giant ancient tree trunk in the middle
    for y in range(20, 180):
        wdt = 40 + (180 - y) * 0.05 + (max(0, y - 150)) * 1.2
        for x in range(int(240 - wdt / 2), int(240 + wdt / 2)):
            t = (x - (240 - wdt / 2)) / wdt
            c = hx('#4a3222') * (1.25 - t * 0.6)
            if (x * 3 + y // 6) % 11 == 0:
                c = c * 0.7
            b.px(x, y, c)
    # canopy glow
    for i in range(80):
        cx, cy = b.rng.randint(0, W), b.rng.randint(-10, 60)
        b.ellipse(cx, cy, b.rng.randint(12, 26), b.rng.randint(8, 14),
                  ['#2a5a2a', '#3a7a34', '#1e4420'][i % 3], dither_edge=True)
    for x in range(-5, W + 10, 9):
        if abs(x - 240) > 40:
            b.conifer(x, 166, b.rng.randint(26, 44), '#0e2014', '#16301c', '#1e4024')
    # glowing heart knot
    b.ellipse(240, 110, 8, 10, '#8ae05a')
    b.ellipse(240, 110, 4, 6, '#e0ffb0')
    b.ground(166, '#3a5a2a', '#2e4a24', '#20361a', grass=['#5a8a3a', '#3a6a2a', '#8ae05a'], seed=seed)
    # roots crossing the ground
    for k in range(6):
        x0 = 240 + (k - 2.5) * 20
        for t in range(90):
            x = x0 + (k - 2.5) * t * 1.6
            y = 172 + t * 0.35 + math.sin(t * 0.2 + k) * 2
            for d in range(3):
                b.px(x, y + d, '#3a2818' if d else '#5a4028')
    b.motes(160, ['#8ae05a', '#e0ffb0', '#5ab040'], 0, 200, seed)
    return b


def title(seed=6):
    b = BG(seed)
    b.gradient(['#140c1c', '#3a1c34', '#8a3a3a', '#e0804a'], 0, 200, bands=12)
    b.snapshot_sky()
    b.motes(90, ['#fff0c0', '#c8b8e0'], 0, 90, seed)   # stars
    b.ridge(170, 30, '#2a1824', seed + 1, freq=0.012, color2='#34202c')
    b.ridge(200, 22, '#1a1018', seed + 2, freq=0.02)
    # lone cliff with a burning tree
    for x in range(290, 480):
        # rocky cliff: steep jagged face on the left, gently rising plateau to the right
        face = max(0, 345 - x) * 1.6
        top = int(152 - (x - 345) * 0.05 + face + 3 * math.sin(x * 0.7) + 2 * math.sin(x * 0.23))
        for y in range(max(top, 0), H):
            b.px(x, y, '#120a10' if (x * 3 + y) % 7 else '#1c1018')
    b.round_tree(400, 152, 70, '#120a10', ['#2a1418', '#1c0e12', '#120a10'])
    b.motes(220, ['#ffb03a', '#ff6a1e', '#fff0a0', '#e04a1e'], 40, 260, seed + 3)
    return b


def camp(seed=7):
    b = BG(seed)
    b.gradient(['#101a30', '#1e2e4a', '#3a4a64', '#5a5a6a'], 0, 170, bands=10)
    b.snapshot_sky()
    b.motes(120, ['#fff8e0', '#c8d8ff', '#8898c0'], 0, 120, seed)
    b.ellipse(90, 45, 12, 12, '#f0ecd8')
    b.ellipse(95, 42, 10, 10, '#101a30')
    b.ridge(150, 20, '#202838', seed + 1, freq=0.018)
    for x in range(-5, W + 10, 10):
        b.conifer(x + b.rng.randint(-3, 3), 168, b.rng.randint(26, 42), '#0e1620', '#141e2a', '#1a2634')
    b.ground(168, '#2a3a2a', '#223022', '#1a241a', grass=['#3a4e32', '#2a3a2a'], seed=seed)
    # tent
    for y in range(0, 44):
        half = int(y * 0.75)
        for x in range(-half, half + 1):
            c = '#8a6a4a' if x < 0 else '#6a4e36'
            if abs(x) < 3 and y > 26:
                c = '#1a1210'
            b.px(110 + x, 150 + y, c)
    # campfire glow on the ground
    for y in range(160, 230):
        for x in range(160, 320):
            d = math.hypot((x - 240) / 80, (y - 205) / 26)
            if d < 1 and (x + y) % 2 == 0:
                b.a[y, x] = b.a[y, x] * 0.6 + hx('#e08a3a') * 0.4 * (1 - d)
    for k in range(6):
        a = k / 6 * math.pi * 2
        b.ellipse(240 + math.cos(a) * 12, 208 + math.sin(a) * 4, 3, 2, '#5a5048')
    for i in range(3):
        b.ellipse(240 + (i - 1) * 3, 204 - i, 3 - i * 0.5, 6 - i, ['#e04a1e', '#ffb03a', '#fff0a0'][i])
    b.motes(40, ['#ffb03a', '#ff6a1e'], 160, 200, seed)
    return b


def world_map(seed=8):
    """Top-down stylised map of Ashroot Wilds for the stage select screen."""
    b = BG(seed)
    b.gradient(['#4a6a34', '#3e5c2e'], 0, H, bands=4)
    rng = random.Random(seed)
    # scorched region (east-south)
    for _ in range(400):
        x, y = rng.randint(260, 380), rng.randint(150, 260)
        b.ellipse(x, y, rng.randint(2, 6), rng.randint(2, 4), ['#5a3a2a', '#4a2e24', '#6a4030'][rng.randint(0, 2)])
    # ruins region (north-east)
    for _ in range(40):
        x, y = rng.randint(330, 470), rng.randint(20, 110)
        b.rect(x, y, x + rng.randint(4, 10), y + rng.randint(3, 8), ['#7a746a', '#6a645a'][rng.randint(0, 1)])
    # river from north down to the flooded ruins
    for t in range(0, 400):
        y = t * 0.7
        x = 200 + math.sin(t * 0.03) * 40 + t * 0.35
        b.ellipse(x, y, 5, 3, '#3a7ab0')
        b.ellipse(x - 1, y, 2, 2, '#6ab0d8')
    # forest canopy dots (west)
    for _ in range(700):
        x, y = rng.randint(0, 240), rng.randint(0, H)
        b.ellipse(x, y, 4, 3, ['#2e5a24', '#3a6a2a', '#24481c'][rng.randint(0, 2)])
        b.px(x - 1, y - 1, '#5a8a3a')
    # heart tree (far east)
    b.ellipse(440, 200, 26, 20, '#1e4420')
    b.ellipse(440, 200, 14, 12, '#2e6a2a')
    b.ellipse(440, 198, 5, 5, '#8ae05a')
    # vignette border
    for y in range(H):
        for x in range(W):
            e = min(x, y, W - 1 - x, H - 1 - y)
            if e < 6:
                b.a[y, x] = b.a[y, x] * (0.45 + e * 0.08)
    return b


SCENES = {'bg_forest': forest, 'bg_ruins': ruins, 'bg_scorched': scorched, 'bg_flooded': flooded,
          'bg_heart': heart, 'bg_title': title, 'bg_camp': camp, 'bg_worldmap': world_map}
