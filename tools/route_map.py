"""Portrait adventure map of Ashroot Wilds (256x448, shown at 4x).

The trail climbs from the forest edge (bottom) through the ruins, the wild
growth, the scorched path and the flooded ruins to the Heart (top).
Route points must match `route_pos` in data/stages/ashroot_wilds.json.
Original art, drawn procedurally.
"""
import json
import math
import os
import random
import numpy as np
from PIL import Image

W, H = 256, 448
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Content'))  # game content root


def hx(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64)


# region bands (y_top, ground colours) from top to bottom
REGIONS = [
    (0, ['#16301a', '#1e3a20', '#12261a']),      # heart - deep old forest
    (118, ['#2a4a5a', '#345868', '#22404e']),    # flooded ruins
    (168, ['#4a3226', '#5a3a2a', '#3e2a22']),    # scorched path
    (222, ['#2a5226', '#32602c', '#224620']),    # wild growth
    (278, ['#4e5a44', '#5a6650', '#44503c']),    # old ruins
    (338, ['#3e6a2e', '#4a7a36', '#36602a']),    # forest edge
]


def route_points():
    with open(os.path.join(ROOT, 'data/stages/ashroot_wilds.json')) as f:
        d = json.load(f)
    return [tuple(s['route_pos']) for s in d['stages']]


class Map:
    def __init__(self, seed=11):
        self.a = np.zeros((H, W, 3))
        self.rng = random.Random(seed)

    def px(self, x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < W and 0 <= y < H:
            self.a[y, x] = hx(c) if isinstance(c, str) else c

    def disc(self, cx, cy, r, c, ry=None):
        ry = ry or r
        col = hx(c) if isinstance(c, str) else c
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - r) - 1, int(cx + r) + 2):
                if ((x - cx) / max(r, 0.5)) ** 2 + ((y - cy) / max(ry, 0.5)) ** 2 <= 1.0:
                    self.px(x, y, col)

    def ground(self):
        rng = self.rng
        for y in range(H):
            # pick region with dithered blend at the borders
            for x in range(W):
                idx = 0
                for i, (top, _) in enumerate(REGIONS):
                    if y >= top + 7 * math.sin(x * 0.045 + i * 1.7) + 3 * math.sin(x * 0.13 + i):
                        idx = i
                j = idx
                nxt = REGIONS[idx + 1][0] if idx + 1 < len(REGIONS) else 10 ** 6
                nxt += 7 * math.sin(x * 0.045 + (idx + 1) * 1.7) + 3 * math.sin(x * 0.13 + idx + 1)
                if nxt - y < 10 and BAYER[y % 4, x % 4] > (nxt - y) / 10.0:
                    j = idx + 1
                cols = REGIONS[j][1]
                n = (math.sin(x * 0.21 + y * 0.13) + math.sin(x * 0.07 - y * 0.19)) * 0.5
                k = 0 if n > 0.35 else (2 if n < -0.35 else 1)
                if k == 1 and BAYER[y % 4, x % 4] < 0.2:
                    k = 0
                self.a[y, x] = hx(cols[k])
        for _ in range(900):   # grass / dirt specks
            x, y = rng.randrange(W), rng.randrange(H)
            self.a[y, x] = self.a[y, x] * 1.25

    def river(self):
        # a stream that falls from the heart, pools in the flooded ruins, then runs off east
        pts = [(210, 0), (196, 40), (178, 90), (150, 128), (120, 150), (170, 160), (230, 175), (256, 190)]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            steps = int(math.hypot(x1 - x0, y1 - y0))
            for s in range(steps):
                t = s / steps
                x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
                self.disc(x, y, 5, '#2a5a8a')
                self.disc(x, y, 3, '#3a7ab0')
                if s % 5 == 0:
                    self.px(x - 1, y, '#8ad0f0')
        for (cx, cy, r) in [(80, 140, 16), (40, 128, 10), (130, 140, 12)]:
            self.disc(cx, cy, r + 2, '#22486a', ry=(r + 2) * 0.6)
            self.disc(cx, cy, r, '#3a7ab0', ry=r * 0.6)
            for k in range(4):
                self.px(cx - r // 2 + k * 3, cy - 1, '#9ae0ff')

    def ruins(self):
        rng = self.rng
        for _ in range(26):
            x, y = rng.randrange(8, W - 8), rng.randrange(282, 334)
            w, h = rng.randrange(4, 10), rng.randrange(3, 7)
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    self.px(xx, yy, '#8a8478' if yy == y else '#6a645a')
            self.px(x, y + h, '#2a2620')
        for x, y in [(30, 300), (226, 318), (200, 290)]:   # broken pillars
            for yy in range(y - 14, y):
                self.px(x, yy, '#9a9488')
                self.px(x + 1, yy, '#7a746a')
                self.px(x + 2, yy, '#5a544a')
            self.px(x + 1, y - 15, '#6a9a4a')
        # flooded ruins stones sticking out of the water
        for x, y in [(70, 132), (92, 146), (136, 136), (36, 124)]:
            self.disc(x, y, 3, '#8a8478', ry=2)
            self.px(x - 1, y - 1, '#b0aa9e')

    def scorched(self):
        rng = self.rng
        for _ in range(140):
            x, y = rng.randrange(W), rng.randrange(172, 220)
            c = ['#2a1a16', '#6a2a1a', '#3a221a'][rng.randrange(3)]
            self.disc(x, y, rng.randrange(1, 3), c, ry=1)
        for _ in range(40):   # ember cracks
            x, y = rng.randrange(W), rng.randrange(176, 218)
            for k in range(rng.randrange(3, 7)):
                self.px(x + k, y + (k % 2), '#ff7a2a' if k % 2 else '#c0401a')
        for x in [20, 60, 236, 180]:   # burnt stumps
            y = rng.randrange(180, 214)
            for yy in range(y - 8, y):
                self.px(x, yy, '#1a1210')
                self.px(x + 1, yy, '#2a1a14')
            self.px(x - 2, y - 6, '#1a1210')
            self.px(x + 3, y - 4, '#1a1210')

    def tree(self, x, y, r, dark, mid, light):
        self.disc(x + 1, y + 2, r, np.array([12, 18, 10]) * 1.0)   # shadow
        self.disc(x, y, r, dark)
        self.disc(x - 1, y - 1, r - 1, mid)
        self.disc(x - r * 0.35, y - r * 0.4, max(1, r * 0.4), light)

    def forests(self, route):
        rng = self.rng
        palettes = {
            'heart': ('#0e2410', '#1a3a1c', '#2e5a2a'),
            'wild': ('#1a3e18', '#2a5a22', '#4a8a34'),
            'edge': ('#24481c', '#3a6a2a', '#6aa04a'),
        }
        def near_path(x, y):
            for (x0, y0), (x1, y1) in zip(route, route[1:]):
                dx, dy = x1 - x0, y1 - y0
                t = max(0, min(1, ((x - x0) * dx + (y - y0) * dy) / max(1, dx * dx + dy * dy)))
                if math.hypot(x - (x0 + dx * t), y - (y0 + dy * t)) < 14:
                    return True
            return any(math.hypot(x - px, y - py) < 16 for px, py in route)
        for band, (y0, y1), n in [('heart', (6, 112), 110), ('wild', (224, 276), 80), ('edge', (340, 444), 90)]:
            for _ in range(n):
                x, y = rng.randrange(0, W), rng.randrange(y0, y1)
                if near_path(x, y):
                    continue
                self.tree(x, y, rng.randrange(4, 8), *palettes[band])

    def heart_tree(self, x, y):
        # the great glowing tree at the top of the route
        for r, c in [(30, '#0a1c0c'), (26, '#143218'), (20, '#1e4a20'), (12, '#2e6a2a')]:
            self.disc(x, y - 6, r, c, ry=r * 0.8)
        for yy in range(y - 4, y + 16):
            for xx in range(x - 3, x + 4):
                self.px(xx, yy, '#3a2616' if xx < x + 2 else '#2a1a10')
        self.disc(x, y - 8, 5, '#6ae05a')
        self.disc(x, y - 8, 3, '#c8ff9a')
        for k in range(18):   # glow motes
            a = k * 0.35
            self.px(x + math.cos(a) * (18 + k % 5), y - 8 + math.sin(a) * 12, '#8ae05a')

    def trail(self, route):
        for (x0, y0), (x1, y1) in zip(route, route[1:]):
            steps = int(math.hypot(x1 - x0, y1 - y0) * 2)
            for s in range(steps + 1):
                t = s / steps
                wob = math.sin(t * math.pi * 2) * 2
                nx, ny = -(y1 - y0), (x1 - x0)
                ln = max(1, math.hypot(nx, ny))
                x = x0 + (x1 - x0) * t + nx / ln * wob
                y = y0 + (y1 - y0) * t + ny / ln * wob
                self.disc(x, y, 4, '#2a2016')
            for s in range(steps + 1):
                t = s / steps
                wob = math.sin(t * math.pi * 2) * 2
                nx, ny = -(y1 - y0), (x1 - x0)
                ln = max(1, math.hypot(nx, ny))
                x = x0 + (x1 - x0) * t + nx / ln * wob
                y = y0 + (y1 - y0) * t + ny / ln * wob
                self.disc(x, y, 3, '#8a6a44')
                if s % 3 == 0:
                    self.px(x, y - 1, '#a8885a')
        for (x, y) in route:   # clearings under nodes
            self.disc(x, y + 2, 10, '#2a2016', ry=6)
            self.disc(x, y + 1, 9, '#7a5e3c', ry=5)

    def fog(self):
        # soft top fog and vignette
        for y in range(H):
            for x in range(W):
                e = min(x, y, W - 1 - x, H - 1 - y)
                if e < 8:
                    self.a[y, x] *= 0.5 + e * 0.06
                if y < 24 and BAYER[y % 4, x % 4] > y / 24.0:
                    self.a[y, x] = self.a[y, x] * 0.6 + hx('#3a3a4a') * 0.4

    def save(self, path, scale=1):
        img = Image.fromarray(np.clip(self.a, 0, 255).astype(np.uint8), 'RGB')
        if scale != 1:
            img = img.resize((W * scale, H * scale), Image.NEAREST)
        img.save(path)


def build(path):
    route = route_points()
    m = Map()
    m.ground()
    m.river()
    m.ruins()
    m.scorched()
    m.forests(route)
    m.heart_tree(route[-1][0], route[-1][1] - 18)
    m.trail(route)
    m.fog()
    m.save(path)


# ================================================================ World 2: Saltglass Coast
# Trail climbs from the bleached shore (bottom) through the wreck cove and the
# crystal sea caves to the saltglass spire on its storm-wrapped island (top).
# Route points live in tools/route_w2.json (copy them into the World 2 stage data).
_YY, _XX = np.mgrid[0:H, 0:W]
REGIONS_W2 = [
    (0, ['#343a52', '#3e4660', '#2c3246']),      # spire isle - storm-dark rock
    (104, ['#3c4a5e', '#48586e', '#323e50']),    # sea caves - blue-grey highland rock
    (222, ['#8a6a6a', '#987672', '#7c5e62']),    # wreck cove - dusky wet sand
    (332, ['#e0d2ae', '#eae0c2', '#d4c49e']),    # saltglass shore - bleached sand
]
SALT_W2 = ['#f6fdff', '#cdeff5', '#98d6e2', '#5eaac0', '#3c7c9a']
GLOW_W2 = ['#f0ffff', '#9af4ff', '#46d0e6', '#2690bc', '#18588a']


def route_points_w2():
    with open(os.path.join(os.path.dirname(__file__), 'route_w2.json')) as f:
        return [tuple(p) for p in json.load(f)['route_pos']]


def _border(i, x):
    return REGIONS_W2[i][0] + 6 * math.sin(x * 0.05 + i * 1.9) + 3 * math.sin(x * 0.15 + i)


class CoastMap(Map):
    def ground_w2(self):
        for y in range(H):
            for x in range(W):
                idx = 0
                for i in range(len(REGIONS_W2)):
                    if y >= _border(i, x):
                        idx = i
                j = idx
                if idx + 1 < len(REGIONS_W2):
                    gap = _border(idx + 1, x) - y
                    if gap < 6 and BAYER[y % 4, x % 4] > gap / 6.0:
                        j = idx + 1
                cols = REGIONS_W2[j][1]
                n = math.sin(x * 0.11 + y * 0.07) + math.sin(x * 0.05 - y * 0.13) + 0.5 * math.sin(x * 0.23 + y * 0.19)
                n += (BAYER[y % 4, x % 4] - 0.5) * 0.25
                k = 1 if n > 0.9 else (2 if n < -0.9 else 0)
                self.a[y, x] = hx(cols[k])

    def water_mask(self):
        m = np.zeros((H, W), dtype=bool)
        isle = ((_XX - 128) / 58.0) ** 2 + ((_YY - 46) / 40.0) ** 2 < 1 + 0.12 * np.sin(_XX * 0.3) + 0.1 * np.sin(_YY * 0.4)
        top = _YY < REGIONS_W2[1][0] + 6 * np.sin(_XX * 0.05 + 1.9) + 3 * np.sin(_XX * 0.15 + 1) - 4
        m |= top & ~isle
        shore = _XX > 226 + 8 * np.sin(_YY * 0.045) + 4 * np.sin(_YY * 0.15 + 1) + np.maximum(0, 350 - _YY) * 1.4
        taper = np.maximum(0, 236 - _YY) * 1.1 + np.maximum(0, _YY - 318) * 1.1
        cove = (_XX < 18 + 8 * np.sin(_YY * 0.07) + 3 * np.sin(_YY * 0.2) - taper) \
            | (((_XX - 22) / 36.0) ** 2 + ((_YY - 246) / 17.0) ** 2 < 1)
        bay = _XX > 238 + 6 * np.sin(_YY * 0.1) + ((_YY - 158) / 34.0) ** 2 * 22
        return m | shore | cove | bay

    def paint_water(self, m):
        deep = np.zeros((H, W, 3))
        storm = _YY < 110
        cove = (_YY >= 200) & (_YY < 340)
        deep[:] = hx('#2e8cb0')
        deep[cove] = hx('#3a5a80')
        deep[storm] = hx('#1e3c54')
        shallow = np.zeros((H, W, 3))
        shallow[:] = hx('#5ec0ca')
        shallow[cove] = hx('#6a7a9a')
        shallow[storm] = hx('#2e5a6e')
        # distance from the coast by repeated erosion
        dist = np.zeros((H, W), dtype=np.int32)
        cur = m.copy()
        for k in range(1, 9):
            er = cur & np.roll(cur, 1, 0) & np.roll(cur, -1, 0) & np.roll(cur, 1, 1) & np.roll(cur, -1, 1)
            dist[cur & ~er] = k
            cur = er
        dist[cur] = 9
        b = BAYER[_YY % 4, _XX % 4]
        is_shallow = m & (dist + b * 2 < 6)
        self.a[m] = deep[m]
        self.a[is_shallow] = shallow[is_shallow]
        foam = m & (dist == 1) & (((_XX // 2 + _YY) % 5) != 0)
        self.a[foam] = hx('#eaf8f8')
        rng = random.Random(5)
        for _ in range(170):   # wave glints / whitecaps
            x, y = rng.randrange(W), rng.randrange(H)
            if m[y, x] and dist[y, x] > 3:
                c = '#dff4f6' if y < 110 else ('#9ab0d0' if 200 <= y < 340 else '#a8e6ee')
                for k in range(rng.randint(2, 4)):
                    self.px(x + k, y, c)

    def shard(self, x, base, h, w, pal=SALT_W2, shadow=True):
        if shadow:
            for k in range(int(h * 0.5)):
                self.px(x + 1 + k, base + k * 0.25, self.a[min(H - 1, int(base + k * 0.25)), min(W - 1, x + 1 + k)] * 0.72)
        for yy in range(int(h)):
            half = w * (1 - yy / h)
            for xx in range(-int(half + 0.5), int(half + 0.5) + 1):
                c = pal[1] if xx < 0 else (pal[2] if xx == 0 else pal[3])
                if xx == -int(half + 0.5) or (xx == 0 and yy % 3 == 0):
                    c = pal[0] if xx == 0 else pal[1]
                self.px(x + xx, base - yy, c)
        self.px(x, base - h, pal[0])

    def glow(self, cx, cy, r, col, amt=0.28):
        m = ((_XX - cx) / r) ** 2 + ((_YY - cy) / (r * 0.7)) ** 2 < 1 + (BAYER[_YY % 4, _XX % 4] - 0.5) * 0.3
        self.a[m] = self.a[m] * (1 - amt) + hx(col) * amt

    def shore_decor(self, route, water):
        rng = random.Random(21)
        for (x, y, h) in [(236, 344, 14), (244, 362, 9), (232, 396, 18), (246, 420, 11), (238, 438, 7), (250, 380, 6),
                          (12, 226, 8), (6, 262, 10)]:
            self.shard(x, y, h, max(2, h // 4))
        for (cx, cy, r) in [(30, 384, 9), (112, 432, 7), (186, 434, 10), (100, 356, 6), (172, 364, 5)]:   # tide pools
            self.disc(cx, cy + 1, r + 1.5, '#b6a27c', ry=(r + 1.5) * 0.55)
            self.disc(cx, cy, r, '#62c2c8', ry=r * 0.5)
            self.disc(cx + 1, cy + 1, r * 0.55, '#4aa8b8', ry=r * 0.28)
            self.px(cx - r * 0.4, cy - 1, '#eafcff')
        for (cx, cy, r) in [(150, 440, 12), (40, 346, 8), (206, 412, 7)]:                                  # salt crust
            self.disc(cx, cy + 1, r, '#c8b692', ry=r * 0.4)
            self.disc(cx, cy, r, '#f6f0e0', ry=r * 0.4)
        for (x, y, h) in [(22, 406, 7), (98, 398, 5), (184, 378, 6), (136, 364, 4), (212, 386, 5), (20, 440, 6), (160, 424, 4)]:
            self.shard(x, y, h, 2)
        for _ in range(60):                                                                               # dune grass
            x, y = rng.randrange(0, 220), rng.randrange(338, 446)
            if water[y, x] or self._near(route, x, y, 13):
                continue
            for k in range(3):
                self.px(x + k - 1, y - (k % 2), '#9aa05a' if k != 1 else '#c6c27a')
                self.px(x + k - 1, y - 1 - (k == 1), '#7c884a')
        for k in range(9):                                                                                # wind ripples
            y0 = 344 + k * 11
            for x in range(4, 222):
                if (x + k * 31) % 46 < 26:
                    y = y0 + 2 * math.sin(x * 0.09 + k)
                    if not water[int(y), x] and not self._near(route, x, y, 10):
                        self.px(x, y, self.a[int(y), x] * 0.94)
        for (x, y) in [(40, 366), (180, 440)]:                                                            # driftwood
            for k in range(12):
                self.px(x + k, y + k * 0.3, '#d4c8b0')
                self.px(x + k, y + 1 + k * 0.3, '#8a7a62')

    def _near(self, route, x, y, d):
        for (x0, y0), (x1, y1) in zip(route, route[1:]):
            dx, dy = x1 - x0, y1 - y0
            t = max(0, min(1, ((x - x0) * dx + (y - y0) * dy) / max(1, dx * dx + dy * dy)))
            if math.hypot(x - (x0 + dx * t), y - (y0 + dy * t)) < d:
                return True
        return any(math.hypot(x - px, y - py) < d + 4 for px, py in route)

    def hull(self, cx, cy, ln, ang, submerged=False):
        ca, sa = math.cos(ang), math.sin(ang)
        for s in range(-ln, ln + 1):
            t = s / ln
            half = 5 * math.sqrt(max(0, 1 - t * t)) + (1.5 if t < 0 else 0)
            for q in range(-int(half), int(half) + 1):
                x, y = cx + ca * s - sa * q, cy + sa * s + ca * q * 0.6
                edge = abs(q) >= int(half) - 0.5
                c = '#3a2418' if edge else ('#6a4430' if q < 0 else '#4a3022')
                if not edge and s % 4 == 0:
                    c = '#8a6040'
                if submerged and s > ln * 0.3:
                    continue
                self.px(x, y, c)
        mx, my = cx - ca * ln * 0.1, cy - sa * ln * 0.1
        for k in range(14):                                      # broken mast + its shadow
            self.px(mx + k * 0.45 + 3, my + k * 0.2 + 2, self.a[int(min(H - 1, my + k * 0.2 + 2)), int(min(W - 1, mx + k * 0.45 + 3))] * 0.7)
            self.px(mx - k * 0.2, my - k, '#2a1c16')
            self.px(mx - k * 0.2 + 1, my - k, '#7a5638')
        self.px(mx - 4, my - 10, '#2a1c16')
        self.px(mx + 3, my - 10, '#2a1c16')
        for k in range(-4, 5):
            self.px(mx - 2.2 + k, my - 10, '#5a3a28')

    def wreck_decor(self, route, water):
        self.hull(28, 246, 14, 0.35, submerged=True)
        for k in range(20):
            a = k * 0.33
            self.px(34 + math.cos(a) * 16, 250 + math.sin(a) * 6, '#9ab0d0')
        self.hull(210, 268, 16, -0.4)
        self.hull(84, 330, 12, 0.15)
        self.hull(196, 314, 10, 2.8)
        rng = random.Random(33)
        for (cx, cy, r) in [(170, 246, 7), (60, 236, 5), (226, 300, 6), (94, 280, 5)]:                  # dusk puddles
            self.disc(cx, cy, r + 1, '#5a4050', ry=(r + 1) * 0.5)
            self.disc(cx, cy, r, '#c07c74', ry=r * 0.5)
            self.px(cx - 2, cy - 1, '#ffd0a0')
        for _ in range(26):                                                                              # planks
            x, y = rng.randrange(10, 246), rng.randrange(226, 334)
            if water[y, x] or self._near(route, x, y, 12):
                continue
            ln = rng.randint(4, 8)
            dx = rng.choice([1, -1]) * rng.uniform(0.3, 1)
            for k in range(ln):
                self.px(x + k, y + k * dx * 0.4, '#7a5642')
                self.px(x + k, y + 1 + k * dx * 0.4, '#3a2622')
        for _ in range(18):                                                                              # tide-line streaks
            x0, y0 = rng.randrange(0, W - 30), rng.randrange(228, 330)
            ln = rng.randint(14, 30)
            for k in range(ln):
                x, y = x0 + k, y0 + 1.5 * math.sin(k * 0.3 + x0)
                if not water[int(y), min(W - 1, x)] and not self._near(route, x, y, 11):
                    self.px(x, y, self.a[int(y), min(W - 1, x)] * 0.86)
                    self.px(x, y - 1, np.minimum(self.a[int(y) - 1, min(W - 1, x)] * 1.08, 255))
        for _ in range(16):                                                                              # kelp
            x, y = rng.randrange(8, W - 8), rng.randrange(228, 332)
            if water[y, x] or self._near(route, x, y, 12):
                continue
            for k in range(4):
                self.px(x + k - 1, y - (k % 2), '#3e5a44')
            self.px(x, y - 2, '#5a7a50')
        for (x, y) in [(150, 236), (236, 250), (40, 312)]:                                              # barrels
            self.disc(x, y, 3, '#5a3a28')
            self.disc(x, y - 1, 2, '#8a6040')
            self.px(x - 1, y - 2, '#c8a070')

    def cave_decor(self, route):
        rng = random.Random(44)
        for _ in range(42):                                                                              # rock ridges
            x, y = rng.randrange(0, W), rng.randrange(110, 222)
            if self._near(route, x, y, 16):
                continue
            r = rng.randrange(4, 9)
            self.disc(x + 1, y + 2, r, '#222a38', ry=r * 0.7)
            self.disc(x, y, r, '#2c3648', ry=r * 0.7)
            self.disc(x - 1, y - 1, r * 0.6, '#5a6a82', ry=r * 0.35)
        for (cx, cy) in [(34, 170), (168, 142), (222, 196), (96, 118), (82, 212)]:                      # cave mouths
            self.disc(cx + 1, cy + 1, 12, '#222a38', ry=8)
            self.disc(cx, cy, 11, '#48586e', ry=7.5)
            self.disc(cx - 2, cy - 3, 7, '#6a7a92', ry=3)
            for yy in range(int(cy - 1), int(cy + 7)):
                for xx in range(int(cx - 7), int(cx + 8)):
                    if ((xx - cx) / 6.5) ** 2 + ((yy - cy - 5) / 6.0) ** 2 <= 1 and yy < cy + 6:
                        self.px(xx, yy, '#1e7c90' if yy == int(cy + 5) else '#06080e')
            self.px(cx - 6, cy + 6, '#2a3444')
        for (cx, cy) in [(18, 136), (148, 204), (236, 148), (184, 118), (58, 196), (104, 150), (214, 176)]:  # crystals
            self.glow(cx, cy - 3, 11, '#46d0e6', 0.3)
            for (dx, h) in [(-3, 5), (0, 9), (3, 6)]:
                self.shard(cx + dx, cy, h, 2, GLOW_W2, shadow=False)
        for (cx, cy, r) in [(142, 132, 7), (40, 150, 6), (176, 184, 8)]:                                 # glowing pools
            self.glow(cx, cy, r * 2, '#2aa0b0', 0.25)
            self.disc(cx, cy, r + 1, '#10161f', ry=(r + 1) * 0.5)
            self.disc(cx, cy, r, '#1e7c90', ry=r * 0.5)
            self.disc(cx + 1, cy, r * 0.5, '#32b2c6', ry=r * 0.25)
            self.px(cx - r * 0.4, cy - 1, '#c8faff')

    def isle_decor(self, route):
        rng = random.Random(55)
        for (cx, cy, h) in [(86, 50, 12), (170, 44, 14), (96, 72, 8), (160, 70, 9), (74, 34, 7), (182, 64, 7)]:
            self.shard(cx, cy, h, max(2, h // 4), ['#f2fbff', '#bcdcf2', '#8eaedc', '#6a7cbc', '#4a4a8c'])
        for (x, y) in [(20, 40), (230, 30), (40, 80), (220, 88), (8, 70), (246, 60)]:                    # sea stacks
            self.disc(x, y, 5, '#1a2030', ry=3.5)
            self.disc(x - 1, y - 1, 3, '#46587a', ry=1.8)
            for k in range(6):
                self.px(x - 6 + k * 2, y + 4, '#eaf8f8')

    def causeway(self, a, b):
        (x0, y0), (x1, y1) = a, b
        n = int(math.hypot(x1 - x0, y1 - y0))
        for s in range(n + 1):
            t = s / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            self.disc(x, y + 1, 8, '#3c7c9a')
        for s in range(n + 1):
            t = s / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            self.disc(x, y, 7, '#98d6e2')
            if s % 6 == 0:
                self.px(x - 5, y - 2, '#f6fdff')
                self.px(x + 4, y + 1, '#5eaac0')

    def great_spire(self, x, base):
        self.glow(x, base - 22, 30, '#6ac8d8', 0.22)
        self.glow(x, base - 18, 18, '#9ae8f0', 0.2)
        h, w = 44, 9
        facets = ['#e8fbff', '#b4e6f0', '#86cadc', '#5a9cbc', '#3e6a96']
        for yy in range(h):
            half = w * (1 - yy / h) + 0.5
            for xx in range(-int(half), int(half) + 1):
                f = int((xx + half) / (2 * half + 1) * 5)
                self.px(x + xx, base - yy, facets[min(4, f)])
        for yy in range(2, h - 4):
            self.px(x, base - yy, '#ffffff' if yy % 5 else '#bff8ff')
        for yy in (12, 26):
            for xx in range(-3, 4):
                self.px(x + xx, base - yy + (xx > 0), '#4a3a7a')
        for (dx, hh) in [(-12, 16), (12, 20), (-18, 9), (19, 10)]:
            self.shard(x + dx, base + 2, hh, 3, ['#f2fbff', '#bcdcf2', '#8eaedc', '#6a7cbc', '#4a4a8c'])

    def storm(self):
        for y in range(H):
            for x in range(W):
                e = min(x, y, W - 1 - x, H - 1 - y)
                if e < 8:
                    self.a[y, x] *= 0.5 + e * 0.06
                if y < 28 and BAYER[y % 4, x % 4] > y / 28.0:
                    self.a[y, x] = self.a[y, x] * 0.55 + hx('#2a1e44') * 0.45
        for (a, b) in [((34, 2), (30, 10)), ((30, 10), (36, 16)), ((36, 16), (32, 26))]:
            steps = 12
            for s in range(steps + 1):
                t = s / steps
                self.px(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, '#e8f8ff')

    def save_opt(self, path):
        Image.fromarray(np.clip(self.a, 0, 255).astype(np.uint8), 'RGB').save(path, optimize=True)


def build_w2(path):
    route = route_points_w2()
    m = CoastMap(seed=12)
    m.ground_w2()
    water = m.water_mask()
    m.paint_water(water)
    m.shore_decor(route, water)
    m.wreck_decor(route, water)
    m.cave_decor(route)
    m.isle_decor(route)
    m.causeway(route[-2], route[-1])
    m.great_spire(route[-1][0], route[-1][1] - 20)
    m.trail(route)
    m.storm()
    m.save_opt(path)


if __name__ == '__main__':
    import sys
    if 'w2' not in sys.argv:
        build(os.path.join(ROOT, 'assets/environments/bg_routemap.png'))
    build_w2(os.path.join(ROOT, 'assets/environments/bg_routemap_w2.png'))
