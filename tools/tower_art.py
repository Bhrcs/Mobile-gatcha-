"""Evolution Tower overview art (180x320 portrait): three elemental towers on a
cliff under a dusk sky - ember (left, red stone with a flame crown), tide (centre,
blue coral-glass) and verdant (right, vine-wrapped wood). Original art, drawn
procedurally with flat colour bands so the PNG stays small.
Run: python3 tools/tower_art.py  ->  assets/environments/bg_tower.png
"""
import math
import os
import random
import numpy as np
from PIL import Image

W, H = 180, 320
BAYER = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) / 16.0
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Content'))  # game content root
YY, XX = np.mgrid[0:H, 0:W]
B = BAYER[YY % 4, XX % 4]


def hx(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64)


def C(c):
    return hx(c) if isinstance(c, str) else np.asarray(c, dtype=np.float64)


class Canvas:
    def __init__(self, seed=1):
        self.a = np.zeros((H, W, 3))
        self.rng = random.Random(seed)

    def px(self, x, y, c):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < W and 0 <= y < H:
            self.a[y, x] = C(c)

    def paint(self, m, c):
        self.a[m] = C(c)

    def tint(self, m, c, amt):
        self.a[m] = self.a[m] * (1 - amt) + C(c) * amt

    def bands(self, cols, y0, y1, soft=2):
        cs = [C(c) for c in cols]
        n = len(cs)
        idx = [min(n - 1, int((y - y0) / max(1, y1 - y0) * n)) for y in range(y0, y1)]
        for k, y in enumerate(range(y0, y1)):
            i = idx[k]
            dn = next((j - k for j in range(k, len(idx)) if idx[j] != i), 999)
            dp = next((k - j for j in range(k, -1, -1) if idx[j] != i), 999)
            for x in range(W):
                c = cs[i]
                b = BAYER[y % 4, x % 4]
                if dn <= soft and i + 1 < n and b < 0.5 * (1 - (dn - 0.5) / (soft + 0.5)):
                    c = cs[i + 1]
                elif dp <= soft and i > 0 and b < 0.5 * (1 - (dp - 0.5) / (soft + 0.5)):
                    c = cs[i - 1]
                self.a[y, x] = c

    def line(self, x0, y0, x1, y1, c, width=1):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        steep = abs(y1 - y0) > abs(x1 - x0)
        for i in range(n + 1):
            t = i / n
            for w in range(width):
                self.px(x0 + (x1 - x0) * t + (w if steep else 0), y0 + (y1 - y0) * t + (0 if steep else w), c)


def ell(cx, cy, rx, ry):
    return ((XX + 0.5 - cx) / max(rx, 0.5)) ** 2 + ((YY + 0.5 - cy) / max(ry, 0.5)) ** 2 <= 1


def poly(pts):
    m = np.zeros((H, W), dtype=bool)
    n = len(pts)
    ys = [p[1] for p in pts]
    for y in range(max(0, int(min(ys))), min(H, int(math.ceil(max(ys))) + 1)):
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


def edge(m, side):
    d = {'l': (1, 1), 'r': (-1, 1), 't': (1, 0), 'b': (-1, 0)}[side]
    return m & ~np.roll(m, d[0], axis=d[1])


def glow(cv, cx, cy, r, col, levels=((1.0, 0.14), (0.6, 0.26)), ry=None):
    ry = ry or r
    d = np.sqrt(((XX + 0.5 - cx) / r) ** 2 + ((YY + 0.5 - cy) / ry) ** 2)
    for rr, amt in levels:
        cv.tint(d < rr + (B - 0.5) * 0.12, col, amt)


def tower_body(cx, base, top, w0, w1):
    """Mask of a gently tapering tower shaft plus per-pixel horizontal position (0..1)."""
    t = np.clip((base - (YY + 0.5)) / max(1, base - top), 0, 1)
    half = w0 + (w1 - w0) * t
    m = (YY >= top) & (YY < base) & (np.abs(XX + 0.5 - cx) <= half)
    u = (XX + 0.5 - (cx - half)) / (2 * half)
    return m, u


def shade_body(cv, m, u, lit, base, shade, dark):
    cv.paint(m, base)
    cv.paint(m & (u < 0.24), lit)
    cv.paint(m & (u > 0.72), shade)
    cv.paint(m & (u > 0.9), dark)


def window(cv, x, y, w, h, frame, light):
    cv.paint(poly([(x - w - 1, y + h + 1), (x - w - 1, y), (x, y - w - 1), (x + w + 1, y), (x + w + 1, y + h + 1)]), frame)
    cv.paint(poly([(x - w, y + h), (x - w, y), (x, y - w), (x + w, y), (x + w, y + h)]), light)


def flame(cv, cx, base, h, w, seed):
    rng = random.Random(seed)
    for col, s in zip(('#b8341a', '#ff7a2a', '#ffd070', '#fff4c0'), (1.0, 0.74, 0.48, 0.24)):
        hh, ww = h * s, w * s
        cv.paint(poly([(cx - ww, base), (cx - ww * 0.9, base - hh * 0.45), (cx - ww * 0.35 + rng.uniform(-1, 1), base - hh * 0.8),
                       (cx + rng.uniform(-1.5, 1.5), base - hh), (cx + ww * 0.3, base - hh * 0.62), (cx + ww * 0.7, base - hh * 0.85),
                       (cx + ww, base - hh * 0.35), (cx + ww, base)]), col)


def build(path):
    cv = Canvas(3)
    horizon = 232
    cv.bands(['#16122e', '#1e1840', '#2a1e50', '#3c2862', '#56306e', '#763a74', '#9a4676', '#bc5876', '#da7474',
              '#ee9678', '#f6b67e'], 0, horizon)
    rng = random.Random(7)
    for _ in range(70):                                                     # stars
        x, y = rng.randrange(W), rng.randrange(0, 120)
        cv.px(x, y, '#fff6e0' if rng.random() < 0.3 else '#b8b0e0')
    for (x, y) in [(22, 18), (150, 40), (60, 52), (120, 12)]:
        cv.px(x, y, '#ffffff')
        for d in (-1, 1):
            cv.px(x + d, y, '#9a90d0')
            cv.px(x, y + d, '#9a90d0')
    cv.paint(ell(154, 26, 9, 9) & ~ell(158, 23, 8, 8), '#fff0d0')          # crescent moon
    for (x, y, ln) in [(4, 150, 50), (110, 140, 60), (40, 176, 70), (130, 190, 46), (0, 204, 40), (84, 212, 56)]:
        cv.line(x, y, x + ln, y, '#6a3a6e')
        cv.line(x + 3, y + 1, x + ln - 3, y + 1, '#f0a07a')
    # distant sea and mountains
    for (base, amp, col, ph) in [(226, 14, '#5a3a6a', 1.0), (234, 8, '#462e5a', 2.5)]:
        for x in range(W):
            y = int(base - amp * (0.6 * math.sin(x * 0.045 + ph) + 0.4 * math.sin(x * 0.11 + ph * 2)))
            cv.a[y:horizon + 20, x] = C(col)
    cv.a[236:262] = C('#3e2e56')
    cv.a[244:262] = C('#34284c')
    cv.a[236] = C('#6a4470')
    for _ in range(46):                                                     # sunset glints on the far sea
        x, y = rng.randrange(W), rng.randrange(238, 262)
        ln = rng.randint(2, 3 + (y - 236) // 6)
        cv.line(x, y, x + ln, y, '#f0a07a' if rng.random() < 0.5 else '#9a5a7a')
    # cliff plateau
    top = 262 + 3 * np.sin(XX * 0.07) + 2 * np.sin(XX * 0.21)
    cliff = YY >= top
    cv.paint(cliff, '#2c2236')
    cv.paint(cliff & (YY > top + 14), '#241c2e')
    cv.paint(cliff & (YY > top + 34), '#1c1624')
    for k in range(4):                                                      # rock ledges
        ly = 276 + k * 11 + 3 * np.sin(XX * 0.05 + k * 1.7) + 2 * np.sin(XX * 0.17 + k)
        ledge = (YY >= ly) & (YY < ly + 5) & (np.sin(XX * 0.06 + k * 2.3) > -0.4)
        cv.tint(ledge, '#3e3050', 0.5)
        cv.paint(edge(ledge, 't'), '#54405e')
        cv.paint(edge(ledge, 'b'), '#140f1a')
    cv.paint(edge(cliff, 't') | (edge(cliff, 't') & np.roll(edge(cliff, 't'), 1, 0)), '#6a4a6a')
    cv.paint(np.roll(edge(cliff, 't'), 1, 0), '#4a3650')
    for _ in range(40):                                                     # grass tufts on the rim
        x = rng.randrange(W)
        y = int(262 + 3 * math.sin(x * 0.07) + 2 * math.sin(x * 0.21))
        for k in range(rng.randint(2, 4)):
            cv.px(x + k - 1, y - 1 - (k % 2), '#5a6a4a' if k % 2 else '#7a8a5a')

    # ---- ember tower (left)
    cx, base, tp = 34, 266, 124
    glow(cv, cx, tp - 22, 34, '#ff9a4a', ((1.0, 0.12), (0.6, 0.22)), ry=40)
    m, u = tower_body(cx, base, tp, 15, 12)
    shade_body(cv, m, u, '#b8583e', '#8a3a2e', '#6a2a24', '#4a1c18')
    brick = m & ((((YY - tp) % 7) == 0) | ((((XX + ((YY - tp) // 7) % 2 * 4) % 8) == 0) & (u > 0.05) & (u < 0.95)))
    cv.tint(brick, '#3a1410', 0.45)
    for yy in (150, 176, 202, 228):
        window(cv, cx - 1, yy, 3, 7, '#3a1410', '#ffc060')
    cv.paint(poly([(cx - 7, base), (cx - 7, base - 12), (cx, base - 19), (cx + 7, base - 12), (cx + 7, base)]), '#2a0e0c')
    cv.paint(poly([(cx - 5, base), (cx - 5, base - 11), (cx, base - 16), (cx + 5, base - 11), (cx + 5, base)]), '#ff8a30')
    cv.paint(poly([(cx - 20, base + 4), (cx - 18, base - 4), (cx + 18, base - 4), (cx + 20, base + 4)]), '#6a2a24')
    cv.paint(poly([(cx - 18, base - 4), (cx + 18, base - 4), (cx + 18, base - 2), (cx - 18, base - 2)]), '#b8583e')
    cv.paint((YY >= tp - 6) & (YY < tp + 2) & (np.abs(XX + 0.5 - cx) <= 16), '#8a3a2e')      # battlement
    for k in range(-3, 4):
        if k % 2 == 0:
            cv.paint((YY >= tp - 12) & (YY < tp - 6) & (np.abs(XX + 0.5 - (cx + k * 4.6)) <= 2.3), '#9a4432')
    cv.paint((YY == tp - 6) & (np.abs(XX + 0.5 - cx) <= 16), '#c8704a')
    cv.paint((YY >= tp) & (YY < tp + 2) & (np.abs(XX + 0.5 - cx) <= 16), '#4a1c18')
    flame(cv, cx, tp - 8, 34, 12, 1)
    flame(cv, cx - 10, tp - 9, 16, 5, 2)
    flame(cv, cx + 11, tp - 9, 18, 5, 3)
    for _ in range(18):
        cv.px(cx + rng.uniform(-16, 16), tp - 40 - rng.uniform(0, 30), '#ffc060' if rng.random() < 0.5 else '#ff7a2a')

    # ---- tide tower (centre): coral-glass spire
    cx, base, tp = 90, 264, 70
    glow(cv, cx, tp + 10, 40, '#5ad0f0', ((1.0, 0.1), (0.55, 0.2)), ry=60)
    m, u = tower_body(cx, base, tp, 17, 9)
    shade_body(cv, m, u, '#8adcf0', '#3a92c0', '#28709e', '#1a4a78')
    spiral = m & ((((XX * 2 + YY) % 22) < 2))
    cv.paint(spiral & (u < 0.5), '#c8f4ff')
    cv.paint(spiral & (u >= 0.5), '#46a8d0')
    for (yy, ww) in [(96, 3), (130, 3), (166, 4), (204, 4)]:
        window(cv, cx, yy, ww, 8, '#1a4a78', '#e0fcff')
    cv.paint(poly([(cx - 8, base), (cx - 8, base - 13), (cx, base - 21), (cx + 8, base - 13), (cx + 8, base)]), '#10304e')
    cv.paint(poly([(cx - 6, base), (cx - 6, base - 12), (cx, base - 18), (cx + 6, base - 12), (cx + 6, base)]), '#7ae4ff')
    cv.paint(poly([(cx - 22, base + 4), (cx - 20, base - 4), (cx + 20, base - 4), (cx + 22, base + 4)]), '#28709e')
    cv.paint(poly([(cx - 20, base - 4), (cx + 20, base - 4), (cx + 20, base - 2), (cx - 20, base - 2)]), '#8adcf0')
    coral = ['#f0fcff', '#9ae8fa', '#5ac4e6']
    for side in (-1, 1):                                                    # coral branches along the shaft
        for (y0, ln) in [(236, 16), (196, 14), (150, 12), (110, 10)]:
            half = 17 - (264 - y0) / (264 - 70) * 8
            x0 = cx + side * (half - 1)
            pts = [(x0, y0)]
            for s in range(3):
                pts.append((pts[-1][0] + side * ln / 3, pts[-1][1] - ln / 3 - s))
            for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
                cv.line(xa, ya, xb, yb, coral[1], 2)
                cv.line(xa, ya - 1, xb, yb - 1, coral[0])
            cv.line(pts[1][0], pts[1][1], pts[1][0] + side * 2, pts[1][1] - 6, coral[2], 2)
            cv.px(pts[-1][0], pts[-1][1] - 1, coral[0])
    for (dx, h, w) in [(0, 34, 6), (-8, 20, 4), (8, 22, 4), (-14, 10, 3), (14, 12, 3)]:   # glass crown
        x = cx + dx
        cv.paint(poly([(x - w, tp + 4), (x, tp + 4 - h), (x + w, tp + 4)]), '#7ad0e8')
        cv.paint(poly([(x - w, tp + 4), (x, tp + 4 - h), (x - w * 0.2, tp + 4)]), '#e0fcff')
        cv.paint(poly([(x + w * 0.45, tp + 4), (x, tp + 4 - h), (x + w, tp + 4)]), '#3a92c0')
    cv.paint(ell(cx, tp - 14, 4, 4), '#ffffff')
    glow(cv, cx, tp - 14, 9, '#bff8ff', ((1.0, 0.4),))
    cv.paint(ell(cx, tp - 14, 2.5, 2.5), '#ffffff')

    # ---- verdant tower (right): vine-wrapped wood
    cx, base, tp = 146, 266, 112
    m, u = tower_body(cx, base, tp, 14, 11)
    shade_body(cv, m, u, '#a8804a', '#7a5630', '#5a3c20', '#3a2614')
    cv.tint(m & ((XX % 4) == 0), '#3a2614', 0.35)
    for yy in range(tp + 14, base, 22):
        cv.paint(m & (YY >= yy) & (YY < yy + 3), '#4a3018')
        cv.paint(m & (YY == yy), '#c8a060')
    for yy in (150, 186, 222):
        cv.paint(ell(cx + 1, yy, 4, 5), '#3a2614')
        cv.paint(ell(cx + 1, yy, 3, 4), '#ffd88a')
    cv.paint(poly([(cx - 7, base), (cx - 7, base - 12), (cx, base - 18), (cx + 7, base - 12), (cx + 7, base)]), '#2a1a0e')
    cv.paint(poly([(cx - 5, base), (cx - 5, base - 11), (cx, base - 15), (cx + 5, base - 11), (cx + 5, base)]), '#ffd88a')
    for (dx, s) in [(-14, -1), (14, 1), (-6, -1), (7, 1)]:                   # root flare
        cv.paint(poly([(cx + dx - 3 * s, base - 14), (cx + dx + 2 * s, base - 14), (cx + dx + 9 * s, base + 3), (cx + dx + 2 * s, base + 3)]), '#5a3c20')
        cv.line(cx + dx - 3 * s, base - 14, cx + dx + 2 * s, base + 3, '#a8804a' if s < 0 else '#3a2614')
    for k in range(3):                                                      # spiral vines
        for s in range(150):
            y = base - 4 - s
            half = 14 - (s / 154) * 3
            ph = s * 0.09 + k * 2.1
            x = cx + math.sin(ph) * half
            if y < tp:
                break
            front = math.cos(ph) > -0.2
            cv.px(x, y, '#3a7a2a' if front else '#24481c')
            if front:
                cv.px(x + 1, y, '#5aa040')
                if s % 6 == 0:
                    cv.px(x + 2, y - 1, '#96d060')
                    cv.px(x - 1, y - 1, '#6ab048')
                if s % 29 == 7:
                    cv.px(x + 2, y + 1, '#f0d0e8')
    for (dx, dy, r) in [(0, -6, 18), (-14, 4, 12), (14, 2, 13), (-8, -18, 12), (9, -20, 12), (0, -30, 10)]:   # canopy crown
        cv.paint(ell(cx + dx + 1, tp + dy + 2, r, r * 0.8), '#1e3a18')
    for (dx, dy, r) in [(0, -6, 18), (-14, 4, 12), (14, 2, 13), (-8, -18, 12), (9, -20, 12), (0, -30, 10)]:
        cv.paint(ell(cx + dx, tp + dy, r - 1, (r - 1) * 0.78), '#2e6a26')
        cv.paint(ell(cx + dx - r * 0.25, tp + dy - r * 0.25, r * 0.55, r * 0.4), '#5aa040')
        cv.paint(ell(cx + dx - r * 0.35, tp + dy - r * 0.38, r * 0.25, r * 0.18), '#96d060')
    for (x, y) in [(cx - 6, tp - 8), (cx + 10, tp - 14), (cx - 12, tp + 2), (cx + 4, tp - 30)]:
        cv.px(x, y, '#f0d0e8')
        cv.px(x + 1, y, '#d890c0')
    for s in range(24):                                                     # hanging vines from the canopy
        for (x0, ln) in [(cx - 16, 20), (cx + 13, 26), (cx - 4, 14)]:
            if s < ln:
                cv.px(x0 + math.sin(s * 0.4) * 1.2, tp + 8 + s, '#3a7a2a')
    for _ in range(14):                                                     # fireflies
        cv.px(cx + rng.uniform(-26, 26), tp + rng.uniform(-40, 60), '#e0ffb0')

    # soft vignette on the lower cliff
    cv.tint((YY > 300) & (B < (YY - 300) / 24), '#0e0a14', 0.5)
    Image.fromarray(np.clip(cv.a, 0, 255).astype(np.uint8), 'RGB').save(path, optimize=True)


if __name__ == '__main__':
    build(os.path.join(ROOT, 'assets/environments/bg_tower.png'))
