"""
pixlib - a tiny pixel-art drawing toolkit used to author all of Cinderbound's
original sprites procedurally.

Sprites are assembled from shaded "parts" (masks) drawn back-to-front on a
small canvas. Each part receives 3-tone shading (light from the top-left) and
a dark separation line where it overlaps parts drawn earlier. A coloured
exterior outline ("selective outline") is added at the end.
"""
import math
import numpy as np
from PIL import Image


def hexc(h, a=255):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def mix(c1, c2, t):
    return tuple(int(round(c1[i] + (c2[i] - c1[i]) * t)) for i in range(3)) + (255,)


def darken(c, t):
    return mix(c, (20, 12, 28, 255), t)


def lighten(c, t):
    return mix(c, (255, 250, 235, 255), t)


class Pal:
    """3-tone palette + separation outline for one material."""

    def __init__(self, base, hi=None, sh=None, line=None):
        self.base = hexc(base) if isinstance(base, str) else base
        self.hi = (hexc(hi) if isinstance(hi, str) else hi) or lighten(self.base, 0.28)
        self.sh = (hexc(sh) if isinstance(sh, str) else sh) or darken(self.base, 0.32)
        self.line = (hexc(line) if isinstance(line, str) else line) or darken(self.base, 0.62)


class Mask:
    """Boolean mask the same size as the canvas with drawing primitives."""

    def __init__(self, w, h):
        self.w, self.h = w, h
        self.m = np.zeros((h, w), dtype=bool)

    def set(self, x, y):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.m[y, x] = True

    def rect(self, x0, y0, x1, y1):
        """Inclusive rectangle."""
        for y in range(int(y0), int(y1) + 1):
            for x in range(int(x0), int(x1) + 1):
                self.set(x, y)
        return self

    def ellipse(self, cx, cy, rx, ry):
        for y in range(int(cy - ry - 1), int(cy + ry + 2)):
            for x in range(int(cx - rx - 1), int(cx + rx + 2)):
                dx = (x - cx) / max(rx, 0.01)
                dy = (y - cy) / max(ry, 0.01)
                if dx * dx + dy * dy <= 1.0:
                    self.set(x, y)
        return self

    def poly(self, pts):
        """Scanline polygon fill (pixel centres)."""
        ys = [p[1] for p in pts]
        n = len(pts)
        for y in range(int(math.floor(min(ys))), int(math.ceil(max(ys))) + 1):
            yc = y + 0.0
            xs = []
            for i in range(n):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % n]
                if (y1 <= yc < y2) or (y2 <= yc < y1):
                    xs.append(x1 + (yc - y1) * (x2 - x1) / (y2 - y1))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                for x in range(int(math.ceil(xs[i] - 0.5)), int(math.floor(xs[i + 1] + 0.5)) + 1):
                    self.set(x, y)
        for p in pts:
            self.set(p[0], p[1])
        return self

    def line(self, x0, y0, x1, y1, width=1):
        """Thick line built from stamped discs/squares."""
        steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
        r = (width - 1) / 2.0
        for i in range(steps + 1):
            t = i / steps
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            if width <= 1:
                self.set(x, y)
            else:
                for yy in range(int(math.floor(y - r)), int(math.ceil(y + r)) + 1):
                    for xx in range(int(math.floor(x - r)), int(math.ceil(x + r)) + 1):
                        if (xx - x) ** 2 + (yy - y) ** 2 <= (r + 0.35) ** 2:
                            self.set(xx, yy)
        return self

    def union(self, other):
        self.m |= other.m
        return self

    def subtract(self, other):
        self.m &= ~other.m
        return self

    def shifted(self, dx, dy):
        out = Mask(self.w, self.h)
        out.m = np.roll(np.roll(self.m, dy, axis=0), dx, axis=1)
        if dy > 0:
            out.m[:dy, :] = False
        elif dy < 0:
            out.m[dy:, :] = False
        if dx > 0:
            out.m[:, :dx] = False
        elif dx < 0:
            out.m[:, dx:] = False
        return out


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = np.zeros((h, w, 4), dtype=np.uint8)
        self.owner = np.full((h, w), -1, dtype=np.int32)
        self._next_id = 0

    def mask(self):
        return Mask(self.w, self.h)

    def part(self, mask, pal, shade=True, separate=True, flat=False):
        """Draws a shaded part on top of whatever is already on the canvas."""
        m = mask.m
        pid = self._next_id
        self._next_id += 1
        h, w = m.shape
        ys, xs = np.nonzero(m)
        for y, x in zip(ys, xs):
            def inside(xx, yy):
                return 0 <= xx < w and 0 <= yy < h and m[yy, xx]

            def other(xx, yy):
                return 0 <= xx < w and 0 <= yy < h and (not m[yy, xx]) and self.owner[yy, xx] >= 0

            col = pal.base
            if not flat:
                if separate and any(other(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    col = pal.line
                elif shade:
                    sh = (not inside(x + 1, y)) or (not inside(x, y + 1)) or (not inside(x + 1, y + 1))
                    hi = (not inside(x - 1, y)) or (not inside(x, y - 1))
                    if sh and not hi:
                        col = pal.sh
                    elif hi and not sh:
                        col = pal.hi
                    elif hi and sh:
                        # thin feature: favour highlight on top edge, shadow on bottom
                        col = pal.hi if not inside(x, y - 1) else pal.sh
            self.px[y, x] = col
            self.owner[y, x] = pid
        return self

    def dot(self, x, y, col):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y, x] = col if len(col) == 4 else tuple(col) + (255,)
            if self.owner[y, x] < 0:
                self.owner[y, x] = 9999

    def outline(self, dark=(24, 14, 30, 255), tint=0.25):
        """Adds a 1px exterior outline tinted by the neighbouring colour."""
        a = self.px[:, :, 3] > 0
        out = self.px.copy()
        h, w = a.shape
        for y in range(h):
            for x in range(w):
                if a[y, x]:
                    continue
                neigh = []
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    xx, yy = x + dx, y + dy
                    if 0 <= xx < w and 0 <= yy < h and a[yy, xx]:
                        neigh.append(self.px[yy, xx])
                if neigh:
                    c = neigh[0]
                    out[y, x] = mix(dark, tuple(int(v) for v in c[:3]) + (255,), tint)
        self.px = out
        return self

    def glow(self, col, alpha=110, radius=1):
        """Soft single-colour aura behind existing pixels (used for bursts)."""
        a = self.px[:, :, 3] > 0
        out = self.px.copy()
        h, w = a.shape
        for y in range(h):
            for x in range(w):
                if a[y, x]:
                    continue
                near = False
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        xx, yy = x + dx, y + dy
                        if 0 <= xx < w and 0 <= yy < h and a[yy, xx]:
                            near = True
                            break
                    if near:
                        break
                if near:
                    out[y, x] = (col[0], col[1], col[2], alpha)
        self.px = out
        return self

    def image(self):
        return Image.fromarray(self.px, 'RGBA')


def flip_image(img):
    return img.transpose(Image.FLIP_LEFT_RIGHT)


def sheet(rows, frame_w, frame_h):
    """rows: list of lists of PIL images -> sprite sheet (row per animation)."""
    cols = max(len(r) for r in rows)
    out = Image.new('RGBA', (cols * frame_w, len(rows) * frame_h), (0, 0, 0, 0))
    for ri, r in enumerate(rows):
        for ci, im in enumerate(r):
            out.paste(im, (ci * frame_w, ri * frame_h), im)
    return out


def preview(img, scale=6, bg=(52, 58, 70)):
    big = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    base = Image.new('RGBA', big.size, bg + (255,))
    base.alpha_composite(big)
    return base
