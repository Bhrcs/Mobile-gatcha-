"""
px6 - Phase 6 pixel renderer (see docs/art/ART-BIBLE.md).

Parts are masks (pixlib.Mask) drawn back-to-front at NATIVE resolution - nothing is
painted large and downscaled. Each part is shaded by FORM, not by its edges:
a height field (rounded / cylinder / flat) gives a normal per pixel, lit from the
upper-left-front, then quantised onto a hand-picked hue-shifted ramp.
Afterwards: cast shadows from parts in front, orphan-pixel cleanup (no single
random pixels), selective separation lines and a coloured selective outline.
"""
import numpy as np
from PIL import Image
from pixlib import Mask, hexc

LIGHT = np.array([-0.45, -0.7, 0.75])   # upper-left-front
LIGHT = LIGHT / np.linalg.norm(LIGHT)


class Ramp:
    """Dark -> light hue-shifted colours. [0] doubles as the outline colour."""

    def __init__(self, *cols):
        self.c = [hexc(c) if isinstance(c, str) else c for c in cols]

    def __getitem__(self, i):
        return self.c[max(0, min(i, len(self.c) - 1))]

    def __len__(self):
        return len(self.c)


# material -> shade thresholds (dot(normal, light) -> ramp index 1..n-1; 0 is the line colour)
MATERIALS = {
    'cloth': [0.0, 0.45, 0.82],           # broad soft bands
    'skin': [0.1, 0.5, 0.86],
    'leather': [0.05, 0.5, 0.85],
    'hair': [0.1, 0.55, 0.86],
    'metal': [0.2, 0.55, 0.8, 0.95],      # contrasty + specular band
    'flat': [-2.0],                       # single tone
}


def _depth(m, cap):
    """Chebyshev distance to the outside, capped (small erosion loop, numpy only)."""
    d = np.zeros(m.shape, dtype=np.float32)
    cur = m.copy()
    for i in range(1, cap + 1):
        d[cur] = i
        n = cur.copy()
        n[1:, :] &= cur[:-1, :]
        n[:-1, :] &= cur[1:, :]
        n[:, 1:] &= cur[:, :-1]
        n[:, :-1] &= cur[:, 1:]
        n[0, :] = n[-1, :] = False
        n[:, 0] = n[:, -1] = False
        if not n.any():
            break
        cur = n
    return d


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = np.zeros((h, w, 4), dtype=np.uint8)
        self.pid = np.full((h, w), -1, dtype=np.int32)
        self.band = np.zeros((h, w), dtype=np.int32)
        self.ramps = []
        self.locked = np.zeros((h, w), dtype=bool)   # hand-placed pixels: never repainted or cleaned

    def mask(self):
        return Mask(self.w, self.h)

    def part(self, mask, ramp, material='cloth', form='round', normal=None, cap=None, cast=True, sep=True, bias=0.0):
        """form: round (dome), cyl_v / cyl_h (cylinder across x / y), flat (use `normal`)."""
        m = mask.m if isinstance(mask, Mask) else mask
        if not m.any():
            return self
        pid = len(self.ramps)
        self.ramps.append(ramp)
        if form == 'flat':
            n = np.array(normal if normal is not None else (0, 0, 1), dtype=np.float32)
            dot = np.full(m.shape, float(np.dot(n / np.linalg.norm(n), LIGHT)), np.float32)
            # a gentle edge falloff keeps flat plates from looking pasted-on
            d = _depth(m, 2)
            dot -= (d == 1) * 0.12
        else:
            cap = cap or max(2, int(_depth(m, 40).max()))   # whole part rounds, not just its rim
            d = _depth(m, cap) / cap
            hgt = np.sqrt(np.clip(1 - (1 - d) ** 2, 0, 1)) * cap
            gy, gx = np.gradient(hgt)
            if form == 'cyl_v':
                gy = gy * 0.15
            elif form == 'cyl_h':
                gx = gx * 0.15
            nx, ny, nz = -gx, -gy, np.ones_like(gx) * 0.9
            ln = np.sqrt(nx * nx + ny * ny + nz * nz)
            dot = (nx * LIGHT[0] + ny * LIGHT[1] + nz * LIGHT[2]) / ln
        dot = dot + bias
        th = MATERIALS[material]
        band = np.ones(m.shape, dtype=np.int32)
        for t in th:
            band += (dot > t)
        band = np.minimum(band, len(ramp) - 1)
        ys, xs = np.nonzero(m)
        # cast shadow: what this part covers casts one band darker just below-right of it
        if cast:
            below = np.zeros_like(m)
            below[2:, 1:] |= m[:-2, :-1]
            below[1:, 1:] |= m[:-1, :-1]
            hit = below & ~m & (self.pid >= 0)
            self.band[hit] = np.maximum(1, self.band[hit] - 1)
            self._repaint(hit)
        self.locked[m] = False   # a part drawn over a stamp replaces it
        self.pid[m] = pid
        self.band[m] = band[m]
        # separation: our boundary against parts behind -> one band darker (never the outline colour)
        if sep:
            edge = np.zeros_like(m)
            for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                sh = np.zeros_like(m)
                sy0, sy1 = max(dy, 0), self.h + min(dy, 0)
                sx0, sx1 = max(dx, 0), self.w + min(dx, 0)
                other = (self.pid >= 0) & (self.pid != pid)
                sh[sy0 - dy:sy1 - dy, sx0 - dx:sx1 - dx] = other[sy0:sy1, sx0:sx1]
                edge |= sh
            edge &= m
            # only below / right edges get a line (light from upper-left keeps the lit side open)
            lit = np.zeros_like(m)
            lit[1:, :] |= ~m[:-1, :]
            lit[:, 1:] |= ~m[:, :-1]
            e2 = edge & ~(lit & (band >= 2))
            self.band[e2] = np.maximum(1, self.band[e2] - 1)
        self._repaint(m)
        return self

    def stamp(self, img, x0, y0, ramp):
        """Pastes a hand-pixelled RGBA image (e.g. a face) as-is; `ramp` colours its outline."""
        pid = len(self.ramps)
        self.ramps.append(ramp)
        a = np.array(img.convert('RGBA'))
        for y in range(a.shape[0]):
            for x in range(a.shape[1]):
                X, Y = x0 + x, y0 + y
                if a[y, x, 3] and 0 <= X < self.w and 0 <= Y < self.h:
                    self.px[Y, X] = a[y, x]
                    self.pid[Y, X] = pid
                    self.locked[Y, X] = True
        return self

    def _repaint(self, sel):
        sel = sel & ~self.locked
        ys, xs = np.nonzero(sel)
        for y, x in zip(ys, xs):
            self.px[y, x] = self.ramps[self.pid[y, x]][self.band[y, x]]

    def dot(self, x, y, col):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y, x] = hexc(col) if isinstance(col, str) else col

    def pixels(self, pts, col):
        for x, y in pts:
            self.dot(x, y, col)
        return self

    def cleanup(self):
        """Removes orphan pixels: a pixel whose colour matches none of its 4 neighbours
        (inside the same part) takes the most common neighbouring colour."""
        px = self.px.copy()
        for y in range(1, self.h - 1):
            for x in range(1, self.w - 1):
                p = self.pid[y, x]
                if p < 0 or self.locked[y, x]:
                    continue
                c = tuple(px[y, x])
                ns = [tuple(px[y + dy, x + dx]) for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0))
                      if self.pid[y + dy, x + dx] == p]
                if len(ns) >= 3 and c not in ns:
                    best = max(set(ns), key=ns.count)
                    self.px[y, x] = best
        return self

    def outline(self):
        """Selective outline: ramp[0] of the touching part; lit (upper-left) edges use ramp[1]."""
        a = self.px[:, :, 3] > 0
        out = self.px.copy()
        for y in range(self.h):
            for x in range(self.w):
                if a[y, x]:
                    continue
                best = None
                for dx, dy, lit in ((1, 0, True), (0, 1, True), (-1, 0, False), (0, -1, False)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < self.w and 0 <= yy < self.h and a[yy, xx]:
                        p = self.pid[yy, xx]
                        ramp = self.ramps[p] if p >= 0 else None
                        col = (ramp[1] if lit else ramp[0]) if ramp else (30, 16, 24, 255)
                        if best is None or not lit:
                            best = col
                if best is not None:
                    out[y, x] = best
        self.px = out
        return self

    def image(self):
        return Image.fromarray(self.px, 'RGBA')


def colours(img):
    return len({p for p in img.getdata() if p[3] > 0})
