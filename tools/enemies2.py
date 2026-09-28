"""
enemies2 - the second wave of ORIGINAL Cinderbound enemies: twelve 48x48
species and four 64x64 bosses. Every creature faces RIGHT (towards the
heroes); the ground line sits at size-5 like the originals in enemies.py.

Each species has a pose function `<id>(**pose) -> PIL.Image` and an
`<id>_anims()` that returns [(name, frames, fps, loop), ...] in the order
idle, attack, hit, death, special (+ enrage for the world boss).

`ANIMS` maps id -> (anims_fn, frame_size) and `TIMING` holds the combat
timing data that make_enemies2.py writes into tools/enemy_manifest.json.
"""
import math
import random
import numpy as np
from PIL import Image
from pixlib import Canvas, Mask, Pal, hexc, mix, lighten, darken
from enemies import dissolve, aura, sink

INK = (18, 10, 20, 255)
WHITE = (252, 250, 240, 255)

ANIMS = {}    # id -> (anims_fn, frame_size)
TIMING = {}   # id -> {"attack": {...}, "special": {...}, "role": str}


def register(eid, size, fn, attack, special, role):
    ANIMS[eid] = (fn, size)
    TIMING[eid] = {'attack': attack, 'special': special, 'role': role}


def C(h, a=255):
    return hexc(h, a)


def A(col, a):
    return (col[0], col[1], col[2], a)


# ------------------------------------------------------------------ geometry
def bez(*P, n=20):
    """Bezier curve through control points P (any degree) sampled n+1 times."""
    pts = []
    for i in range(n + 1):
        t = i / n
        Q = list(P)
        while len(Q) > 1:
            Q = [(Q[j][0] + (Q[j + 1][0] - Q[j][0]) * t, Q[j][1] + (Q[j + 1][1] - Q[j][1]) * t)
                 for j in range(len(Q) - 1)]
        pts.append(Q[0])
    return pts


def catmull(pts, n=10):
    """Catmull-Rom spline through pts (passes through every point)."""
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in range(2)))
    out.append(pts[-1])
    return out


def tube(m, pts, r0, r1=None, step=0.5):
    """Stamps discs along a polyline; radius tapers linearly r0 -> r1."""
    r1 = r0 if r1 is None else r1
    segs = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    total = max(sum(segs), 1e-6)
    acc = 0.0
    for i, L in enumerate(segs):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        n = max(1, int(L / step))
        for k in range(n + 1):
            t = k / n
            r = r0 + (r1 - r0) * ((acc + L * t) / total)
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            if r < 0.7:
                m.set(x, y)
            else:
                m.ellipse(x, y, r, r)
        acc += L
    if len(pts) == 1:
        m.ellipse(pts[0][0], pts[0][1], r0, r0)
    return m


def rot(px, py, ox, oy, ang):
    """Rotates point (px,py) around (ox,oy) by ang radians (screen coords)."""
    c, s = math.cos(ang), math.sin(ang)
    x, y = px - ox, py - oy
    return (ox + x * c - y * s, oy + x * s + y * c)


def polar(ox, oy, ang_deg, r):
    a = math.radians(ang_deg)
    return (ox + r * math.cos(a), oy + r * math.sin(a))


# ------------------------------------------------------------------ shading
def crescent(cv, mask, col, dx, dy, only):
    """Recolours the (dx,dy)-facing inner rim of `mask` (only pixels that are
    still colour `only`, so part edges/separation lines survive). Used to give
    big shapes a second, wider shadow/light band."""
    q = mask.shifted(-dx, -dy).m
    sel = mask.m & ~q
    if only is not None:
        sel &= np.all(cv.px == np.array(only, np.uint8), axis=2)
    cv.px[sel] = col
    return cv


def vpart(cv, mask, pal, depth=2, light=1, **kw):
    """part() plus a wide lower-right shadow band and a top-left light band."""
    cv.part(mask, pal, **kw)
    if depth:
        crescent(cv, mask, pal.sh, depth, depth, pal.base)
    if light:
        crescent(cv, mask, pal.hi, -light, -light, pal.base)
    return cv


def pid(cv):
    return cv._next_id


def translucent(cv, pids, alpha, cols=None):
    """Makes the given parts see-through (call after outline())."""
    sel = np.isin(cv.owner, list(pids)) & (cv.px[:, :, 3] > 0)
    if cols is not None:
        cm = np.zeros(sel.shape, bool)
        for c in cols:
            cm |= np.all(cv.px[:, :, :3] == np.array(c[:3], np.uint8), axis=2)
        sel &= cm
    cv.px[sel, 3] = alpha
    return cv


def dots(cv, pts, col):
    for p in pts:
        cv.dot(p[0], p[1], col)


def fx_dots(img, pts, col):
    """Draws unoutlined particles onto a finished frame (only on empty pixels
    unless the tuple carries a 3rd element 'force')."""
    out = img.copy()
    px = out.load()
    w, h = out.size
    for p in pts:
        x, y = int(round(p[0])), int(round(p[1]))
        if 1 <= x < w - 1 and 1 <= y < h - 1:
            px[x, y] = col if len(col) == 4 else tuple(col) + (255,)
    return out


def over(base, top):
    out = base.copy()
    out.alpha_composite(top)
    return out


def shift(img, dx, dy):
    out = Image.new('RGBA', img.size, (0, 0, 0, 0))
    out.paste(img, (dx, dy), img)
    return out


def tint(img, col, t):
    """Blends every opaque pixel towards col (used for glowing charge frames)."""
    a = np.array(img).astype(np.float32)
    sel = a[:, :, 3] > 0
    for i in range(3):
        a[:, :, i][sel] = a[:, :, i][sel] * (1 - t) + col[i] * t
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), 'RGBA')


def charge(img, col, level):
    """Wind-up read: level 1 = soft rim, 2 = bright rim, 3 = rim + tint."""
    bright = tuple(min(255, c + 90) for c in col[:3])
    if level <= 1:
        return aura(img, col, 130)
    if level == 2:
        return aura(img, bright, 210)
    return aura(tint(img, bright, 0.22), bright, 235)


def die(frames_alive, seeds=(11, 12), tint_col=None):
    """Two last death frames: 40% then ~92% dissolved (ends near-empty)."""
    a, b = frames_alive
    return [dissolve(a, 0.4, seeds[0], tint_col), dissolve(b, 0.93, seeds[1], tint_col)]


def ring(cv_or_mask, cx, cy, rx, ry, th=1.0):
    m = cv_or_mask if isinstance(cv_or_mask, Mask) else cv_or_mask.mask()
    outer = Mask(m.w, m.h).ellipse(cx, cy, rx, ry)
    inner = Mask(m.w, m.h).ellipse(cx, cy, max(rx - th, 0.1), max(ry - th, 0.1))
    m.union(outer.subtract(inner))
    return m


def eyes_pair(cv, pts, state, col=INK, shine=None, h=2):
    """Generic 1-2px wide eyes. state: open / hurt / closed / glow."""
    for (x, y) in pts:
        if state in ('open', 'glow'):
            for k in range(h):
                cv.dot(x, y + k, col)
            if shine:
                cv.dot(x, y, shine)
        elif state == 'hurt':
            cv.dot(x - 1, y, col)
            cv.dot(x, y + 1, col)
            cv.dot(x + 1, y, col)
        else:
            cv.dot(x - 1, y + 1, col)
            cv.dot(x, y + 1, col)


# ============================================================ 1. TIDE SLIME
# Water slime: tall pear-shaped see-through body, rising bubbles, a floating
# crown of three droplets. Spits water; special = geyser from its crown.
TS_BODY = Pal('#3a9eec', '#9ce2ff', '#2872c8', '#15408a')
TS_BUB = Pal('#c4f2ff', '#ffffff', '#8cd6f2', '#4a9ad0')
TS_DROP = Pal('#63c2f2', '#c8f4ff', '#3288d0', '#173f82')
TS_EYE = C('#0c1a36')
TS_FOAM = C('#e8fbff')
TS_GLOW = (90, 200, 255)


def _droplet(m, x, y, r, tip=1.7, lean=0.0):
    m.ellipse(x, y, r, r)
    m.poly([(x - r * 0.8, y - r * 0.35), (x + lean, y - r - tip * r), (x + r * 0.8, y - r * 0.35)])
    return m


def tide_slime(sx=1.0, sy=1.0, dx=0, lean=0, eyes='open', mouth=0, bub=0,
               crown=((0, 0), (0, 0), (0, 0)), spout=0.0, spit=0):
    cv = Canvas(48, 48)
    g = 43
    cx = 23 + dx
    brx, bry = 12.5 * sx, 6.2 * sy
    hrx, hry = 8.5 * sx, 7.2 * sy
    hcx, hcy = cx + lean + 1, g - 2 * bry - hry * 0.5
    body = cv.mask().ellipse(cx, g - bry + 0.5, brx, bry).ellipse(hcx, hcy, hrx, hry)
    body.poly([(cx - brx * 0.85, g - bry), (hcx - hrx * 0.95, hcy + 1), (hcx + hrx * 0.95, hcy + 1),
               (cx + brx * 0.85, g - bry)])
    body.rect(cx - brx + 1.5, g - 1, cx + brx - 1.5, g)
    top = hcy - hry
    # geyser (behind the crown, in front of nothing)
    ytop = top
    if spout > 0:
        ytop = top + 1 - spout * (top - 6)
        col = cv.mask()
        tube(col, [(hcx, top + 3), (hcx + 0.5, (top + ytop) / 2), (hcx, ytop + 1)], 3.2, 4.2)
        col.ellipse(hcx, ytop + 1, 7.5 * min(1, spout + 0.3), 2.8)
        for k in (-4, 0, 4):
            col.poly([(hcx + k - 1.5, ytop + 1), (hcx + k * 1.3, ytop - 3 + abs(k) * 0.4), (hcx + k + 1.5, ytop + 1)])
        cv.part(col, TS_DROP)
        for y in range(int(ytop) + 2, int(top) + 2, 2):
            cv.dot(hcx - 1, y, TS_FOAM)
        dots(cv, [(hcx - 3, ytop), (hcx - 2, ytop), (hcx + 2, ytop + 1)], TS_FOAM)
    b_id = pid(cv)
    vpart(cv, body, TS_BODY, depth=2)
    # bubbles rising through the body
    for k, (bx, ph, big) in enumerate(((-6, 0, True), (3, 7, False), (-1, 12, True), (6, 3, False),
                                       (-8, 9, False))):
        yy = g - 3 - ((bub * 3 + ph) % 22)
        xx = cx + bx + lean * (g - yy) / 26.0
        r = 2 if big else 1
        ok = all(body.m[int(yy + oy), int(round(xx + ox))]
                 for ox in (-r - 1, 0, r + 1) for oy in (-r - 1, 0, r + 1)
                 if 0 <= int(yy + oy) < 48 and 0 <= int(round(xx + ox)) < 48)
        if not ok:
            continue
        if big:
            rm = ring(cv, xx, yy, 2.1, 2.1, 1.0)
            cv.part(rm, TS_BUB, separate=False, shade=False)
            cv.dot(xx - 1, yy - 1, WHITE)
        else:
            cv.dot(xx, yy, TS_BUB.base)
    # glassy shine
    dots(cv, [(hcx - hrx * 0.55, hcy - hry * 0.45), (hcx - hrx * 0.55 + 1, hcy - hry * 0.62),
              (hcx - hrx * 0.55, hcy - hry * 0.45 + 1)], WHITE)
    dots(cv, [(cx - brx * 0.7, g - bry)], TS_BUB.base)
    # face
    ey = hcy - 1
    ex = (hcx + 1, hcx + 5)
    if eyes == 'open':
        for x in ex:
            cv.part(cv.mask().rect(x, ey, x + 1, ey + 2), Pal(TS_EYE, TS_EYE, TS_EYE, TS_EYE), flat=True)
            cv.dot(x, ey, WHITE)
    else:
        eyes_pair(cv, [(x + 0.5, ey) for x in ex], eyes, TS_EYE)
    mx, my = hcx + 3, hcy + 3
    if mouth == 1:
        dots(cv, [(mx, my), (mx + 1, my)], TS_EYE)
    elif mouth == 2:
        cv.part(cv.mask().rect(mx, my, mx + 1, my + 1), Pal(TS_EYE, TS_EYE, TS_EYE, TS_EYE), flat=True)
        cv.dot(mx + 2, my, TS_EYE)
    # water glob being spat
    if spit:
        sxp, syp = mx + 3 + spit, my
        gm = cv.mask().ellipse(sxp, syp, 2.2, 2)
        gm.poly([(sxp - 1, syp - 2), (sxp - 6, syp), (sxp - 1, syp + 2)])
        cv.part(gm, TS_DROP)
    # droplet crown
    if crown is not None and spout > 0:
        # the geyser flings the crown droplets outwards
        crown = ((-4 - spout * 3, 7), (0, 30), (4 + spout * 3, 5))
    if crown is not None:
        base_y = ytop if spout > 0 else top
        for (ox, oy, r, ln), (cdx, cdy) in zip(((-5.5, -1, 1.5, -0.8), (0, -4, 2.1, 0), (5.5, -1, 1.5, 0.8)),
                                              crown):
            if cdy >= 30:
                continue
            x = hcx + ox + cdx
            y = base_y + oy + cdy
            cv.part(_droplet(cv.mask(), x, y, r, 1.6, ln), TS_DROP)
            cv.dot(x - 1, y - 1 if r > 1.8 else y, WHITE)
    cv.outline(dark=(12, 26, 60, 255))
    translucent(cv, [b_id], 218, [TS_BODY.base, TS_BODY.sh])
    return cv.image()


def tide_slime_anims():
    c0 = ((0, 0), (0, 0), (0, 0))
    idle = [tide_slime(bub=0, crown=c0),
            tide_slime(1.03, 0.97, bub=1, crown=((0, 1), (0, 0), (0, -1))),
            tide_slime(bub=2, crown=((0, 0), (0, -1), (0, 0))),
            tide_slime(0.97, 1.03, bub=3, crown=((0, -1), (0, 0), (0, 1)))]
    attack = [tide_slime(1.1, 0.88, lean=-1, eyes='closed', bub=1, crown=((0, 1), (0, 1), (0, 1))),
              tide_slime(1.18, 0.8, lean=-2, eyes='closed', mouth=1, bub=2, crown=((1, 2), (0, 2), (-1, 2))),
              tide_slime(0.9, 1.1, lean=2, mouth=2, bub=3, crown=((0, -2), (0, -2), (0, -2))),
              tide_slime(0.95, 1.05, lean=3, mouth=2, bub=4, spit=4, crown=((0, -1), (0, -1), (0, -1))),
              fx_dots(tide_slime(1.05, 0.95, lean=1, mouth=1, bub=5, crown=c0),
                      [(42, 26), (44, 24), (41, 22), (45, 28)], C('#9ff3ff')),
              tide_slime(bub=6, crown=c0)]
    hit = [tide_slime(1.14, 0.86, dx=-2, eyes='hurt', bub=1, crown=((-2, -2), (-1, -3), (1, -1))),
           tide_slime(1.05, 0.96, dx=-1, eyes='hurt', bub=2, crown=((-1, -1), (0, -1), (0, 0)))]
    death = [tide_slime(1.12, 0.9, eyes='hurt', crown=((-1, 3), (0, 3), (1, 3))),
             tide_slime(1.35, 0.62, eyes='closed', crown=None, bub=2)]
    death += die((tide_slime(1.5, 0.42, eyes='closed', crown=None, bub=4),
                  tide_slime(1.6, 0.3, eyes='closed', crown=None, bub=6)), (21, 22))
    spin = ((-1, -3), (0, -5), (1, -3))
    special = [charge(tide_slime(bub=0, crown=((0, -2), (0, -2), (0, -2))), TS_GLOW, 1),
               charge(tide_slime(1.12, 0.85, bub=1, crown=spin), TS_GLOW, 2),
               charge(tide_slime(1.22, 0.74, eyes='closed', bub=2, crown=((1, -6), (0, -7), (-1, -6))),
                      TS_GLOW, 3),
               tide_slime(0.92, 1.08, mouth=2, bub=3, spout=0.4, crown=c0),
               tide_slime(0.95, 1.05, mouth=2, bub=4, spout=0.85, crown=c0),
               fx_dots(tide_slime(0.95, 1.05, mouth=2, bub=5, spout=1.0, crown=c0),
                       [(16, 4), (31, 5), (14, 8), (33, 9), (18, 2), (29, 2)], C('#bff4ff')),
               fx_dots(tide_slime(1.0, 1.0, mouth=1, bub=6, spout=0.5, crown=c0),
                       [(15, 12), (32, 14), (13, 18), (34, 20), (19, 9), (28, 10)], C('#8fe6ff')),
               tide_slime(1.05, 0.95, bub=7, crown=c0)]
    return [('idle', idle, 6, True), ('attack', attack, 12, False), ('hit', hit, 10, False),
            ('death', death, 8, False), ('special', special, 10, False)]


register('tide_slime', 48, tide_slime_anims,
         {'motion': 'ranged', 'release_frame': 3},
         {'motion': 'ranged', 'release_frame': 4}, 'attacker')


# ============================================================ 2. MOSS SLIME
# Nature slime: low lumpy mound with moss clumps, stones stuck in its body and
# a sprout on its head. Forms a mossy fist to slam; special = spore puff.
MS_BODY = Pal('#5aa83c', '#8ad05a', '#3c7c2a', '#1c4414')
MS_MOSS = Pal('#3a7c2c', '#58983a', '#2a5e1e', '#163a10')
MS_PEB = [Pal('#8e8a7e', '#c4c0b2', '#64605a', '#302e2a'), Pal('#a88c64', '#d0b890', '#7a6246', '#3a2c1e')]
MS_STEM = Pal('#6aa83e', '#9ad464', '#467a28', '#1e3e12')
MS_LEAF = Pal('#7cc84a', '#b4ea7a', '#4e962e', '#1e4a12')
MS_BUD = Pal('#e8d060', '#fff4a8', '#b89a38', '#5a4418')
MS_BUD_GLOW = Pal('#fff09a', '#ffffff', '#ead060', '#8a7020')
MS_SPORE = Pal('#cfe07a', '#f6f9c8', '#a4b84e', '#566a20')
MS_EYE = C('#10240c')
MS_GLOW = (170, 230, 90)


def _leaf(m, bx, by, ang, ln, wd):
    tip = polar(bx, by, ang, ln)
    mid = polar(bx, by, ang, ln * 0.45)
    l = polar(mid[0], mid[1], ang - 90, wd)
    r = polar(mid[0], mid[1], ang + 90, wd)
    return m.poly([(bx, by), l, tip, r])


def _top_y(mask, x):
    col = mask.m[:, int(round(x))]
    ys = np.nonzero(col)[0]
    return ys[0] if len(ys) else None


def moss_slime(sx=1.0, sy=1.0, dx=0, lean=0.0, eyes='open', mouth=0, sway=0, bud=1, arm=None, cloud=0):
    cv = Canvas(48, 48)
    g = 43
    cx = 21 + dx

    def L(h):
        return lean * h / 18.0

    body = cv.mask()
    body.ellipse(cx, g - 6.5 * sy, 14 * sx, 6.5 * sy)
    body.ellipse(cx - 6 * sx + L(10), g - 9.5 * sy, 6.5 * sx, 5.5 * sy)
    body.ellipse(cx + 3 * sx + L(13), g - 12 * sy, 8 * sx, 7 * sy)
    body.rect(cx - 13 * sx, g - 1, cx + 13 * sx, g)
    vpart(cv, body, MS_BODY, depth=2)
    # moss clumps along the top edge make the silhouette fuzzy
    tufts = cv.mask()
    for tx, r in ((-9, 2.4), (-2.5, 2.1), (5, 2.5)):
        x = cx + tx * sx + L(12)
        ty = _top_y(body, x)
        if ty is not None:
            tufts.ellipse(x, ty + 1.2, r, r * 0.85)
    cv.part(tufts, MS_MOSS, separate=False)
    # embedded pebbles
    for i, (px_, py_, rx, ry) in enumerate(((-8, 3.5, 2.6, 2.0), (11, 4, 2.0, 1.6), (-4, 11, 2.0, 1.5))):
        x, y = cx + px_ * sx + L(py_), g - py_ * sy
        cv.part(cv.mask().ellipse(x, y, rx, ry), MS_PEB[i % 2])
    # sprout
    hx = cx + 3 * sx + L(19)
    hy = _top_y(body, hx)
    hy = (hy if hy is not None else g - 19) + 1
    stem_top = (hx + 1 + sway * 0.7, hy - 7)
    cv.part(tube(cv.mask(), bez((hx, hy), (hx - 1, hy - 4), stem_top, n=8), 0.8, 0.6), MS_STEM)
    cv.part(_leaf(cv.mask(), stem_top[0], stem_top[1] + 1, -145 + sway * 8, 6.5, 2.2), MS_LEAF)
    cv.part(_leaf(cv.mask(), stem_top[0], stem_top[1] + 1, -35 + sway * 8, 6.5, 2.2), MS_LEAF)
    if bud == 1:
        cv.part(cv.mask().ellipse(stem_top[0], stem_top[1] - 1, 1.3, 1.8), MS_BUD)
    elif bud == 2:
        cv.part(cv.mask().ellipse(stem_top[0], stem_top[1] - 1.5, 2.2, 2.6), MS_BUD_GLOW)
    elif bud == 3:
        for a in (-150, -90, -30):
            cv.part(_leaf(cv.mask(), stem_top[0], stem_top[1] - 1, a, 3.5, 1.3), MS_BUD)
    # mossy fist
    if arm is not None:
        ang, ln = arm
        sh = (cx + 10 * sx + L(9), g - 9 * sy)
        end = polar(sh[0], sh[1], ang, ln)
        am = tube(cv.mask(), [sh, end], 3.0, 2.4)
        am.ellipse(end[0], end[1], 3.4, 3.2)
        vpart(cv, am, MS_BODY, depth=1)
        cv.part(cv.mask().ellipse(end[0] + 0.5, end[1] - 1, 1.5, 1.2), MS_PEB[0])
        cv.part(cv.mask().ellipse(end[0] - 1.5, end[1] + 1.5, 1.8, 1.0), MS_MOSS, separate=False)
    # sleepy, heavy-lidded face
    ey = g - 13 * sy
    for ex in (cx + 5 * sx + L(12), cx + 9.5 * sx + L(12)):
        if eyes in ('open', 'angry'):
            cv.part(cv.mask().rect(ex, ey, ex + 1, ey + 2), Pal(MS_EYE, MS_EYE, MS_EYE, MS_EYE), flat=True)
            cv.dot(ex, ey + 1, C('#e8f8b0'))
            if eyes == 'open':
                dots(cv, [(ex - 1, ey - 1), (ex, ey - 1), (ex + 1, ey - 1), (ex + 2, ey - 1)], MS_BODY.line)
            else:
                dots(cv, [(ex - 1, ey - 2), (ex, ey - 1), (ex + 1, ey - 1), (ex + 2, ey), (ex + 1, ey)],
                     MS_BODY.line)
        else:
            eyes_pair(cv, [(ex + 0.5, ey)], eyes, MS_EYE)
    mx, my = cx + 6.5 * sx + L(8), g - 8.5 * sy
    if mouth == 1:
        dots(cv, [(mx, my), (mx + 1, my), (mx + 2, my)], MS_EYE)
    elif mouth == 2:
        cv.part(cv.mask().rect(mx, my - 1, mx + 2, my), Pal(MS_EYE, MS_EYE, MS_EYE, MS_EYE), flat=True)
    # spore cloud
    if cloud:
        cxl, cyl = stem_top[0] + 1 + cloud * 2.5, stem_top[1] - 4 - cloud * 1.5
        cm = cv.mask()
        r = 1.8 + cloud * 1.2
        for ox, oy, k in ((0, 0, 1), (-r * 0.95, r * 0.45, 0.7), (r * 1.0, r * 0.4, 0.75),
                          (-r * 0.35, -r * 0.7, 0.72), (r * 0.6, -r * 0.55, 0.66)):
            cm.ellipse(cxl + ox, cyl + oy, r * k, r * k * 0.9)
        vpart(cv, cm, MS_SPORE, depth=1, light=0)
        for ox, oy in ((-1, 0), (2, 1), (0, -2), (-3, 2)):
            if cloud >= 2 or abs(ox) < 2:
                cv.dot(cxl + ox * cloud * 0.6, cyl + oy * cloud * 0.5, MS_SPORE.line)
    cv.outline(dark=(14, 30, 10, 255))
    img = cv.image()
    return img


def _spores(img, pts):
    img = fx_dots(img, pts, MS_SPORE.base)
    return fx_dots(img, [(x + 1, y) for (x, y) in pts[::2]], MS_SPORE.hi)


def moss_slime_anims():
    idle = [moss_slime(), moss_slime(1.02, 0.97, sway=1), moss_slime(sway=0), moss_slime(0.98, 1.03, sway=-1)]
    attack = [moss_slime(1.04, 0.96, lean=-2, arm=(-80, 3), eyes='angry'),
              moss_slime(lean=-3, arm=(-65, 11), eyes='angry', sway=-1),
              moss_slime(0.97, 1.04, lean=-3, arm=(-100, 14), eyes='angry', mouth=2, sway=-2),
              moss_slime(1.03, 0.97, dx=1, lean=2, arm=(28, 10), eyes='angry', mouth=2, sway=2),
              fx_dots(moss_slime(1.08, 0.92, dx=1, lean=1, arm=(38, 9), eyes='angry', sway=1),
                      [(43, 38), (44, 35), (41, 34), (45, 40)], C('#9c9484')),
              moss_slime(arm=(-10, 3), sway=0)]
    hit = [moss_slime(1.1, 0.9, dx=-2, eyes='hurt', sway=-2), moss_slime(1.03, 0.97, dx=-1, eyes='hurt', sway=-1)]
    death = [moss_slime(1.05, 0.95, eyes='hurt', sway=-2, bud=0),
             moss_slime(1.2, 0.7, eyes='closed', sway=-3, bud=0)]
    death += die((moss_slime(1.3, 0.55, eyes='closed', sway=-3, bud=0),
                  moss_slime(1.35, 0.45, eyes='closed', sway=-3, bud=0)), (31, 32))
    special = [charge(moss_slime(bud=2), MS_GLOW, 1),
               charge(moss_slime(1.05, 1.1, bud=2, eyes='closed'), MS_GLOW, 2),
               charge(moss_slime(1.1, 1.16, bud=2, eyes='closed', sway=1), MS_GLOW, 3),
               moss_slime(1.14, 0.86, bud=3, mouth=2, cloud=1, sway=-1),
               _spores(moss_slime(1.06, 0.94, bud=3, mouth=2, cloud=2),
                       [(36, 10), (39, 13), (33, 7), (40, 8)]),
               _spores(moss_slime(bud=3, mouth=1, cloud=3, sway=1),
                       [(40, 12), (43, 9), (38, 6), (44, 15), (35, 4)]),
               _spores(moss_slime(bud=3, sway=0), [(42, 14), (44, 10), (40, 7), (45, 17), (37, 5), (43, 20)]),
               moss_slime(bud=1)]
    return [('idle', idle, 5, True), ('attack', attack, 12, False), ('hit', hit, 10, False),
            ('death', death, 8, False), ('special', special, 10, False)]


register('moss_slime', 48, moss_slime_anims,
         {'motion': 'melee', 'hit_frames': [3]},
         {'motion': 'ranged', 'release_frame': 4}, 'attacker')


# ============================================================ 3. GLOWCAP
# Nature healer: a little walking mushroom with a plum cap covered in glowing
# lime spots, a cream stem with a face and stubby legs. Headbutts; special =
# cap lifts, spots flare and healing spores rise.
GC_CAP = Pal('#8e3c78', '#b85e9c', '#632656', '#34102c')
GC_RIM = Pal('#6e2a5c', '#8e3c78', '#4c1a40')
GC_GILL = Pal('#c8b490', '#e0d0ae', '#a08c6a', '#5c4c34')
GC_STEM = Pal('#ece0c4', '#fffaea', '#c8b898', '#6e5e44')
GC_FOOT = Pal('#d6c49e', '#efe2c2', '#ae9a74', '#5e4e34')
GC_SPOT = [Pal('#a6e05a', '#d8ff9a', '#7cb83a', '#3c6a1a'),     # dim
           Pal('#caff6a', '#f4ffc8', '#9ee04a', '#4c8020'),     # lit
           Pal('#eeffb0', '#ffffff', '#caff6a', '#6aa030')]     # flare
GC_EYE = C('#2a1424')
GC_BLUSH = C('#e8a0a0')
GC_GLOW = (170, 255, 110)


def glowcap(dx=0, dy=0, lift=0, tilt=0, legs=(0, 0), eyes='open', mouth=0, spot=1, squash=0.0):
    cv = Canvas(48, 48)
    g = 43
    cx = 23 + dx
    sq = squash
    # stubby legs
    for (lx, up) in ((-3, legs[0]), (3, legs[1])):
        top = g - 6 + dy
        foot_y = g - 1 - up
        lm = cv.mask().rect(cx + lx - 1.5, min(top, foot_y - 2), cx + lx + 1.5, foot_y)
        lm.ellipse(cx + lx + 0.8, foot_y, 2.6, 1.4)
        cv.part(lm, GC_FOOT)
    # stem / body
    st_h = 11 * (1 - sq * 0.3)
    st_w = 5.8 * (1 + sq * 0.25)
    scy = g - 5 - st_h / 2 + dy
    stem = cv.mask().ellipse(cx, scy, st_w, st_h / 2 + 1)
    vpart(cv, stem, GC_STEM, depth=1)
    # tiny arms
    for (ax, s_) in ((-st_w - 0.5, -1), (st_w + 0.5, 1)):
        cv.part(cv.mask().ellipse(cx + ax, scy + 2, 1.4, 1.8), GC_STEM)
    # face on the stem
    ey = scy - 1.5
    if eyes in ('open', 'happy'):
        for x in (cx + 1, cx + 4):
            if eyes == 'open':
                cv.dot(x, ey, GC_EYE)
                cv.dot(x, ey + 1, GC_EYE)
            else:
                dots(cv, [(x - 1, ey + 1), (x, ey), (x + 1, ey + 1)], GC_EYE)
    else:
        eyes_pair(cv, [(cx + 1, ey), (cx + 4, ey)], eyes, GC_EYE)
    cv.dot(cx - 0.5, ey + 2.5, GC_BLUSH)
    cv.dot(cx + 5.5, ey + 2.5, GC_BLUSH)
    if mouth == 1:
        dots(cv, [(cx + 2, ey + 3), (cx + 3, ey + 3)], GC_EYE)
    elif mouth == 2:
        dots(cv, [(cx + 2, ey + 3), (cx + 3, ey + 3), (cx + 2, ey + 4), (cx + 3, ey + 4)], GC_EYE)
    # cap (rotatable dome with gills underneath)
    ccx, ccy = cx - 0.5, scy - st_h / 2 - 1.5 - lift
    rx, ry = 12.5 * (1 + sq * 0.12), 8.5 * (1 - sq * 0.15)
    a = math.radians(tilt)

    def R(p):
        return rot(p[0], p[1], ccx, ccy + 2, a)

    dome = [R((ccx + rx * math.cos(t), ccy + 1 - ry * math.sin(t)))
            for t in np.linspace(0, math.pi, 22)]
    under = [R((ccx - rx + 1, ccy + 2.5)), R((ccx, ccy + 3.5)), R((ccx + rx - 1, ccy + 2.5))]
    gm = cv.mask().poly([R((ccx - rx + 2, ccy + 1)), R((ccx - rx + 3, ccy + 3.2)), R((ccx + rx - 3, ccy + 3.2)),
                         R((ccx + rx - 2, ccy + 1))])
    cv.part(gm, GC_GILL)
    cap = cv.mask().poly(dome + [under[2], under[1], under[0]])
    vpart(cv, cap, GC_CAP, depth=2)
    rim = cv.mask().poly([R((ccx - rx, ccy + 0.5)), R((ccx - rx + 1, ccy + 2.5)), R((ccx + rx - 1, ccy + 2.5)),
                          R((ccx + rx, ccy + 0.5)), R((ccx + rx - 1, ccy + 1.5)), R((ccx - rx + 1, ccy + 1.5))])
    cv.part(rim, GC_RIM, separate=False, shade=False)
    # glowing spots
    sp = GC_SPOT[spot]
    for (ox, oy, r) in ((-6, -2, 2.0), (1, -5.5, 2.4), (6.5, -1.5, 1.8), (-1.5, 0, 1.4), (-8.5, 1.2, 1.1),
                        (4, -8, 1.2), (9.5, 0.8, 1.0)):
        p = R((ccx + ox * (1 + sq * 0.12), ccy + oy * (1 - sq * 0.15)))
        cv.part(cv.mask().ellipse(p[0], p[1], r, r * 0.85), sp, separate=False)
    cv.outline(dark=(28, 12, 26, 255))
    return cv.image()


def _heal_sparks(img, pts, big=False, cols=None):
    """Little rising '+' shaped healing spores."""
    out = img
    cols = cols or (GC_SPOT[1].base, GC_SPOT[2].base)
    for i, (x, y) in enumerate(pts):
        col = cols[i % 2]
        out = fx_dots(out, [(x, y), (x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)] if (big or i % 2 == 0)
                      else [(x, y)], col)
        out = fx_dots(out, [(x, y)], WHITE)
    return out


def _heal_ring(img, cx, cy, rx, ry, col):
    m = ring(Mask(48, 48), cx, cy, rx, ry, 1.0)
    a = np.array(img)
    sel = m.m & (a[:, :, 3] == 0)
    a[sel] = A(col, 200)
    return Image.fromarray(a, 'RGBA')


def glowcap_anims():
    idle = [glowcap(legs=(0, 0), spot=1), glowcap(dy=-1, legs=(2, 0), spot=1),
            glowcap(legs=(0, 0), spot=0), glowcap(dy=-1, legs=(0, 2), spot=0)]
    attack = [glowcap(squash=0.5, tilt=-12, eyes='closed', spot=1),
              glowcap(dy=-5, dx=1, tilt=-18, legs=(3, 3), spot=1, mouth=2),
              glowcap(dy=-3, dx=7, tilt=28, legs=(1, 3), spot=2, mouth=2),
              glowcap(dx=9, tilt=35, squash=0.4, legs=(0, 0), spot=2, eyes='closed'),
              glowcap(dx=4, tilt=5, legs=(2, 0), spot=1),
              glowcap(spot=1)]
    hit = [glowcap(dx=-2, tilt=-15, eyes='hurt', spot=0, lift=1), glowcap(dx=-1, tilt=-6, eyes='hurt', spot=0)]
    death = [glowcap(eyes='hurt', tilt=-10, squash=0.3, spot=0),
             glowcap(eyes='closed', tilt=-25, dy=2, squash=0.8, spot=0)]
    death += die((glowcap(eyes='closed', tilt=-40, dy=4, squash=1.0, spot=0),
                  glowcap(eyes='closed', tilt=-50, dy=5, squash=1.0, spot=0)), (41, 42), (120, 200, 90))
    sp = GC_SPOT[1].base
    special = [charge(glowcap(spot=2, eyes='happy'), GC_GLOW, 1),
               charge(glowcap(squash=0.5, spot=2, eyes='closed'), GC_GLOW, 2),
               _heal_sparks(charge(glowcap(dy=-2, lift=3, spot=2, eyes='happy', legs=(1, 1)), GC_GLOW, 3),
                            [(17, 18), (30, 16), (23, 14)]),
               _heal_sparks(charge(glowcap(dy=-3, lift=5, spot=2, eyes='happy', mouth=2, legs=(2, 2)), GC_GLOW, 3),
                            [(15, 12), (32, 10), (24, 7), (19, 9), (28, 13)], True),
               _heal_sparks(_heal_ring(glowcap(dy=-2, lift=4, spot=2, eyes='happy', mouth=2), 23, 30, 20, 13, sp),
                            [(14, 6), (33, 5), (24, 3), (19, 8), (29, 9)], True),
               _heal_sparks(_heal_ring(glowcap(dy=-1, lift=2, spot=2, eyes='happy'), 23, 30, 22.5, 15,
                                       GC_SPOT[2].base), [(13, 3), (34, 2), (21, 4), (27, 6)]),
               _heal_sparks(glowcap(lift=1, spot=1, eyes='happy'), [(12, 2), (35, 3), (26, 2)]),
               glowcap(spot=1)]
    return [('idle', idle, 6, True), ('attack', attack, 12, False), ('hit', hit, 10, False),
            ('death', death, 8, False), ('special', special, 10, False)]


register('glowcap', 48, glowcap_anims,
         {'motion': 'melee', 'hit_frames': [3]},
         {'motion': 'self', 'release_frame': 4}, 'healer')


# ============================================================ 4. EMBERWISP
# Fire buffer: a floating living flame with a grinning face, a curling wisp
# tail instead of legs and three embers orbiting it. Flicks fireballs;
# special = shrinks to a white-hot core, then flares up huge.
EW_HEAT = [
    (Pal('#7a3a30', '#9a5444', '#5a2620', '#2e1210'), Pal('#a4523a', '#c06a48', '#84402e'),
     Pal('#c8764a', '#e09a64', '#a85e3a')),                                           # dying
    (Pal('#e0401c', '#ff7a2e', '#a82a14', '#5a120a'), Pal('#ff9a2e', '#ffc860', '#e86a1e'),
     Pal('#ffe27a', '#fff8d0', '#ffc848')),                                           # normal
    (Pal('#ff8a2a', '#ffc050', '#e0501c', '#7a1c0a'), Pal('#ffd060', '#fff0a0', '#ffa838'),
     Pal('#fffbe8', '#ffffff', '#fff0b0')),                                           # white-hot
]
EW_EYE = C('#4a0e06')
EW_EMBER = Pal('#ffb03a', '#fff0a0', '#e0601c', '#6a1a08')
EW_GLOW = (255, 150, 40)


def _flame_mask(m, cx, cy, s, lean, ph):
    f = [math.sin(ph * 1.7 + k * 2.1) for k in range(3)]
    m.ellipse(cx, cy, 8.5 * s, 7.8 * s)
    m.poly([(cx - 8.5 * s, cy), (cx - 8 * s + lean * 0.3, cy - 5 * s),
            (cx - 6 * s + lean * 0.8 + f[0], cy - (13 + f[1]) * s),
            (cx - 2.5 * s + lean * 0.5, cy - 8.5 * s),
            (cx + 0.5 * s + lean + f[1] * 0.7, cy - (18 + f[2]) * s),
            (cx + 3.5 * s + lean * 0.5, cy - 9 * s),
            (cx + 6.5 * s + lean * 0.8 + f[2] * 0.6, cy - (13.5 + f[0]) * s),
            (cx + 8.5 * s + lean * 0.2, cy - 4 * s), (cx + 8.5 * s, cy)])
    tail = bez((cx - 0.5 * s, cy + 5 * s), (cx - 2 * s - lean * 0.2, cy + 10 * s),
               (cx - 6 * s - lean * 0.4 + f[1], cy + 10.5 * s), (cx - 4.5 * s - lean * 0.5, cy + 13 * s), n=12)
    tube(m, tail, 4.6 * s, 0.6)
    return m


def emberwisp(dx=0, dy=0, s=1.0, lean=0.0, ph=0, orbit=0, heat=1, eyes='open', mouth=1, ball=None,
              embers=True, orbit_r=12):
    cv = Canvas(48, 48)
    cx, cy = 22 + dx, 28 + dy
    outer, mid, core = EW_HEAT[heat]
    em = []
    if embers:
        for k in range(3):
            a = math.radians(orbit + k * 120)
            em.append((cx + orbit_r * math.cos(a), cy - 3 + 3.5 * math.sin(a) - 2 * math.cos(a), math.sin(a)))
        for (x, y, z) in em:
            if z < 0:
                cv.part(cv.mask().ellipse(x, y, 1.1, 1.1), EW_EMBER)
    body = _flame_mask(cv.mask(), cx, cy, s, lean, ph)
    cv.part(body, outer)
    crescent(cv, body, outer.sh, 2, 1, outer.base)
    m2 = _flame_mask(cv.mask(), cx + 0.6, cy + 1.6 * s, s * 0.7, lean * 0.7, ph + 1)
    cv.part(m2, mid, separate=False)
    m3 = cv.mask().ellipse(cx + 1, cy + 2 * s, 4.8 * s, 4.2 * s)
    m3.poly([(cx - 2.5 * s, cy + 1 * s), (cx + 1.5 * s + lean * 0.4, cy - 7 * s), (cx + 5 * s, cy + 1 * s)])
    cv.part(m3, core, separate=False)
    # face
    ex, ey = cx + 1 * s + lean * 0.2, cy - 1
    if eyes in ('open', 'fierce'):
        for x in (ex, ex + 4):
            dots(cv, [(x, ey), (x, ey + 1), (x + 1, ey + 1), (x + 1, ey), (x, ey + 2), (x + 1, ey + 2)], EW_EYE)
            if eyes == 'fierce':
                cv.dot(x + (1 if x == ex else 0), ey - 1, EW_EYE)
            cv.dot(x + 1, ey, core.hi)
    else:
        eyes_pair(cv, [(ex + 0.5, ey), (ex + 4.5, ey)], eyes, EW_EYE)
    mx, my = ex + 1, ey + 4
    if mouth == 1:
        dots(cv, [(mx, my), (mx + 1, my + 1), (mx + 2, my + 1), (mx + 3, my)], EW_EYE)
    elif mouth == 2:
        dots(cv, [(mx, my), (mx + 1, my + 1), (mx + 2, my + 1), (mx + 3, my), (mx + 1, my), (mx + 2, my)], EW_EYE)
        dots(cv, [(mx + 1, my + 2), (mx + 2, my + 2)], EW_EYE)
    for (x, y, z) in em:
        if z >= 0:
            cv.part(cv.mask().ellipse(x, y, 1.1, 1.1), EW_EMBER)
    if ball is not None:
        bx, by, br = ball
        bm = cv.mask().ellipse(bx, by, br, br * 0.9)
        bm.poly([(bx - br * 0.2, by - br * 0.9), (bx - br * 2.6, by - br * 0.3), (bx - br * 0.6, by),
                 (bx - br * 2.2, by + br * 0.7), (bx - br * 0.2, by + br * 0.9)])
        cv.part(bm, EW_HEAT[1][0])
        cv.part(cv.mask().ellipse(bx + 0.5, by, br * 0.55, br * 0.5), EW_HEAT[2][2], separate=False)
    cv.outline(dark=(70, 14, 8, 255), tint=0.2)
    return cv.image()


def emberwisp_anims():
    idle = [emberwisp(dy=0, ph=0, orbit=0), emberwisp(dy=-1, ph=1, orbit=30),
            emberwisp(dy=-2, ph=2, orbit=60), emberwisp(dy=-1, ph=3, orbit=90)]
    attack = [emberwisp(dx=-2, lean=-3, ph=0, orbit=0, eyes='fierce'),
              emberwisp(dx=-3, lean=-4, ph=1, orbit=20, eyes='fierce', mouth=2, s=1.06, ball=(31, 27, 2.2)),
              emberwisp(dx=1, lean=4, ph=2, orbit=40, eyes='fierce', mouth=2, ball=(38, 26, 3.2)),
              emberwisp(dx=2, lean=3, ph=3, orbit=60, eyes='open', mouth=2),
              emberwisp(dx=1, lean=1, ph=4, orbit=80),
              emberwisp(ph=5, orbit=100)]
    hit = [emberwisp(dx=-3, lean=-5, ph=1, eyes='hurt', mouth=2, orbit_r=13),
           emberwisp(dx=-1, lean=-2, ph=2, eyes='hurt', orbit=15)]
    smoke = (90, 80, 80)
    death = [emberwisp(dy=1, s=0.9, lean=-2, ph=1, heat=1, eyes='hurt', mouth=2, embers=False),
             emberwisp(dy=3, s=0.75, ph=2, heat=0, eyes='closed', mouth=0, embers=False)]
    death += die((emberwisp(dy=5, s=0.6, ph=3, heat=0, eyes='closed', mouth=0, embers=False),
                  emberwisp(dy=5, s=0.55, ph=4, heat=0, eyes='closed', mouth=0, embers=False)), (51, 52), smoke)
    special = [charge(emberwisp(ph=0, orbit=0, eyes='fierce'), EW_GLOW, 1),
               charge(emberwisp(s=0.85, dy=2, ph=1, orbit=40, eyes='closed', mouth=0, orbit_r=10), EW_GLOW, 2),
               charge(emberwisp(s=0.72, dy=3, ph=2, heat=2, orbit=80, eyes='closed', mouth=0, orbit_r=8),
                      EW_GLOW, 3),
               emberwisp(s=1.3, dy=-1, ph=3, heat=2, orbit=120, eyes='fierce', mouth=2, orbit_r=16),
               fx_dots(emberwisp(s=1.25, dy=-1, ph=4, heat=2, orbit=150, eyes='fierce', mouth=2, orbit_r=17),
                       [(6, 14), (41, 12), (4, 30), (44, 34), (10, 6), (36, 4)], EW_EMBER.hi),
               fx_dots(emberwisp(s=1.2, ph=5, heat=1, orbit=180, eyes='fierce', mouth=1, orbit_r=15),
                       [(4, 10), (44, 8), (2, 28), (46, 32)], EW_EMBER.base),
               emberwisp(s=1.1, ph=6, orbit=210, orbit_r=13),
               emberwisp(ph=7, orbit=240)]
    return [('idle', idle, 7, True), ('attack', attack, 12, False), ('hit', hit, 10, False),
            ('death', death, 8, False), ('special', special, 10, False)]


register('emberwisp', 48, emberwisp_anims,
         {'motion': 'ranged', 'release_frame': 2},
         {'motion': 'self', 'release_frame': 4}, 'buffer')


# ============================================================ 5. HEXMOTH
# Nature debuffer: big dusky moth hovering sideways, feathery antennae, wings
# banded pale at the edge with staring eye-spots. Swoops to buffet; special =
# eye-spots flare, a huge downstroke releases a violet hex-powder cloud.
HM_WING = Pal('#b49aa8', '#d4c0c8', '#8a7086', '#3a2438')
HM_WING_IN = Pal('#6a4478', '#84589a', '#50325c', '#2a1432')
HM_FAR = Pal('#5a3a64', '#6e4a78', '#44284c', '#22122a')
HM_FUR = Pal('#dccab0', '#f4ead8', '#b4a084', '#5a4a38')
HM_ABD = Pal('#8a6a70', '#a88890', '#6a4e56', '#34222a')
HM_BAND = C('#4e343c')
HM_EYE_RING = [C('#2a1030'), C('#c8e05a'), C('#1a0a1a')]
HM_EYE_HEX = [C('#2a1030'), C('#ff7ae0'), C('#fff0ff')]
HM_POWDER = Pal('#c490e0', '#ecd0fa', '#9a62c0', '#4a2066')
HM_GLOW = (200, 110, 240)

FORE = [(0, -1.5), (4, -3.8), (11, -5.2), (15.5, -3.6), (17, -0.5), (15.5, 2.8), (9, 4.4), (2.5, 2.4)]
HIND = [(0, 0), (4, -2.2), (9.5, -3), (12, -0.5), (11, 3.6), (6.5, 5.6), (1.5, 3)]


def _wing_pts(shape, px, py, ang, width, k=1.0):
    d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    n = (-d[1], d[0])
    return [(px + (u * d[0] + v * width * n[0]) * k, py + (u * d[1] + v * width * n[1]) * k) for (u, v) in shape]


def _wing_at(u, v, px, py, ang, width):
    d = (math.cos(math.radians(ang)), math.sin(math.radians(ang)))
    n = (-d[1], d[0])
    return (px + u * d[0] + v * width * n[0], py + u * d[1] + v * width * n[1])


def _eye_spot(cv, c, r, width, cols):
    rs = (r, r * 0.66, r * 0.33)
    for rr, col in zip(rs, cols):
        cv.part(cv.mask().ellipse(c[0], c[1], max(rr, 0.6), max(rr * max(width, 0.5), 0.6)),
                Pal(col, col, col, col), flat=True)
    if width > 0.6:
        cv.dot(c[0] - 1 if r > 2 else c[0], c[1] - 1 if r > 2 else c[1], WHITE)


def hexmoth(dx=0, dy=0, fore=-120, hind=-155, width=1.0, eyes='open', hexed=False, legs=0, cloud=0):
    cv = Canvas(48, 48)
    W = 1.3
    bx, by = 26 + dx, 28 + dy
    pvx, pvy = bx - 1, by - 2
    # far wings (behind)
    cv.part(cv.mask().poly(_wing_pts(HIND, pvx + 3, pvy - 1, hind + 16, width * 0.8, W * 0.85)), HM_FAR)
    cv.part(cv.mask().poly(_wing_pts(FORE, pvx + 3, pvy - 1, fore + 16, width * 0.8, W * 0.9)), HM_FAR)
    # dangling legs
    for k, lx in enumerate((-2, 1, 4)):
        a = (bx + lx, by + 2)
        b = (bx + lx + 1 + legs * (k + 1) * 0.6, by + 6.5 - abs(legs) * 0.5)
        cv.part(cv.mask().line(a[0], a[1], b[0], b[1], 1), HM_ABD, shade=False)
    # abdomen (segmented, short, tapering back)
    ctrl = ((bx - 1, by + 1), (bx - 4, by + 2), (bx - 7, by + 4))
    cv.part(tube(cv.mask(), bez(*ctrl, n=10), 2.8, 1.4), HM_ABD)
    curve = bez(*ctrl, n=100)
    for t in (0.4, 0.7):
        p = curve[int(t * 100)]
        dots(cv, [(p[0], p[1] - 1), (p[0], p[1]), (p[0] + 0.5, p[1] + 1)], HM_BAND)
    # fuzzy thorax + head
    th = cv.mask().ellipse(bx + 1, by, 4.2, 3.6)
    vpart(cv, th, HM_FUR, depth=1)
    cv.part(cv.mask().ellipse(bx + 5.2, by - 0.5, 2.8, 2.6), HM_FUR)
    # feathery antennae sweeping forward
    for (ox, sp) in ((0, 0.0), (-1.5, 1.2)):
        pts = bez((bx + 5 + ox, by - 2.5), (bx + 7 + ox, by - 8 - sp), (bx + 11 + ox, by - 10 - sp), n=10)
        cv.part(tube(cv.mask(), pts, 0.5), HM_ABD, shade=False)
        for p in pts[3::2]:
            cv.dot(p[0], p[1] - 1, HM_FUR.sh)
    # near wings
    cv.part(cv.mask().poly(_wing_pts(HIND, pvx, pvy + 1, hind, width, W)), HM_WING)
    cv.part(cv.mask().poly(_wing_pts(HIND, pvx, pvy + 1, hind, width, W * 0.74)), HM_WING_IN, separate=False)
    cv.part(cv.mask().poly(_wing_pts(FORE, pvx, pvy, fore, width, W)), HM_WING)
    cv.part(cv.mask().poly(_wing_pts(FORE, pvx, pvy, fore, width, W * 0.76)), HM_WING_IN, separate=False)
    cols = HM_EYE_HEX if hexed else HM_EYE_RING
    if width >= 0.5:
        _eye_spot(cv, _wing_at(9.5 * W, 0.3 * W, pvx, pvy, fore, width), 3.9, width, cols)
        _eye_spot(cv, _wing_at(6.5 * W, 1.2 * W, pvx, pvy + 1, hind, width), 2.6, width, cols)
    for t in np.linspace(0.12, 0.5, 5):
        p = _wing_at(16 * W * t, -0.9 * W, pvx, pvy, fore, width)
        cv.dot(p[0], p[1], HM_WING_IN.sh)
    # compound eye
    ex, ey = bx + 6, by - 1
    if eyes == 'open':
        dots(cv, [(ex, ey), (ex + 1, ey), (ex, ey + 1), (ex + 1, ey + 1)], C('#1a0a1a'))
        cv.dot(ex + 1, ey, C('#9aff6a') if not hexed else C('#ff9af0'))
    else:
        eyes_pair(cv, [(ex + 0.5, ey)], eyes, C('#1a0a1a'))
    cv.outline(dark=(26, 12, 30, 255))
    img = cv.image()
    if cloud:
        img = _powder(img, bx + 7 + cloud * 1.2, by + 1 + cloud, cloud)
    return img


def _powder(img, cx, cy, n):
    """Loose, sparkly cloud of hex powder (several separate puffs)."""
    cv = Canvas(48, 48)
    r = 1.5 + n * 0.6
    for (ox, oy, k) in ((0, 0, 1.0), (-4, 3, 0.8), (3, -3, 0.75), (3, 4, 0.85), (-2, -4, 0.6), (-5, -1, 0.6))[:2 + n]:
        m = cv.mask().ellipse(cx + ox * (0.6 + n * 0.3), cy + oy * (0.6 + n * 0.25), r * k, r * k * 0.9)
        cv.part(m, HM_POWDER, separate=False)
    cv.outline(dark=(58, 22, 80, 255), tint=0.4)
    translucent(cv, range(0, 99), 190)
    out = over(img, cv.image())
    pts = [(cx + ox * (1 + n * 0.5), cy + oy * (1 + n * 0.4)) for (ox, oy) in
           ((-5, -2), (2, 4), (4, -3), (-3, 5), (5, 1), (1, -6), (-7, 3))]
    return _hex_sparkles(out, pts[:3 + n])


def _hex_sparkles(img, pts):
    img = fx_dots(img, pts, HM_POWDER.hi)
    return fx_dots(img, pts[::3], WHITE)


def hexmoth_anims():
    idle = [hexmoth(dy=-1, fore=-128, hind=-158, width=1.0),
            hexmoth(dy=0, fore=-146, hind=-170, width=0.8),
            hexmoth(dy=1, fore=-168, hind=172, width=0.55, legs=-1),
            hexmoth(dy=0, fore=-146, hind=-170, width=0.8)]
    attack = [hexmoth(dx=-2, dy=-1, fore=-112, hind=-145, width=1.0, eyes='open'),
              hexmoth(dx=-3, dy=-2, fore=-102, hind=-135, width=0.95, legs=1),
              hexmoth(dx=5, dy=2, fore=-165, hind=172, width=0.55, legs=2),
              fx_dots(hexmoth(dx=8, dy=3, fore=172, hind=160, width=0.6, legs=3),
                      [(44, 26), (45, 30), (43, 22)], HM_WING.hi),
              hexmoth(dx=4, dy=0, fore=-140, hind=-165, width=0.8),
              hexmoth(dy=-1, fore=-128, hind=-158, width=1.0)]
    hit = [hexmoth(dx=-3, dy=-1, fore=-108, hind=-140, width=0.7, eyes='hurt'),
           hexmoth(dx=-1, fore=-130, hind=-158, width=0.9, eyes='hurt')]
    death = [hexmoth(dy=2, fore=-105, hind=-138, width=0.6, eyes='hurt', legs=-1),
             hexmoth(dy=6, fore=-175, hind=175, width=0.5, eyes='closed', legs=-2)]
    death += die((hexmoth(dy=9, fore=175, hind=165, width=0.5, eyes='closed', legs=-2),
                  hexmoth(dy=10, fore=170, hind=160, width=0.5, eyes='closed', legs=-2)), (61, 62), (150, 110, 170))
    special = [charge(hexmoth(dy=-1, fore=-128, hind=-155, width=1.1, hexed=True), HM_GLOW, 1),
               _hex_sparkles(charge(hexmoth(dy=-1, fore=-126, hind=-155, width=1.15, hexed=True), HM_GLOW, 2),
                             [(8, 14), (14, 6), (6, 26), (20, 4), (11, 33)]),
               _hex_sparkles(charge(hexmoth(dy=-2, fore=-104, hind=-136, width=1.05, hexed=True, legs=1),
                                    HM_GLOW, 3), [(5, 10), (16, 3), (4, 22), (24, 3), (8, 30), (12, 16)]),
               hexmoth(dy=1, fore=172, hind=158, width=0.6, hexed=True, cloud=1, legs=2),
               hexmoth(dy=0, fore=-160, hind=175, width=0.6, hexed=True, cloud=2),
               hexmoth(dy=-1, fore=-140, hind=-165, width=0.85, hexed=True, cloud=3),
               _hex_sparkles(hexmoth(dy=-1, fore=-128, hind=-158, width=1.0),
                             [(40, 22), (44, 18), (43, 30), (46, 26), (39, 35), (45, 33)]),
               hexmoth(dy=0, fore=-146, hind=-170, width=0.8)]
    return [('idle', idle, 8, True), ('attack', attack, 12, False), ('hit', hit, 10, False),
            ('death', death, 8, False), ('special', special, 10, False)]


register('hexmoth', 48, hexmoth_anims,
         {'motion': 'melee', 'hit_frames': [3]},
         {'motion': 'ranged', 'release_frame': 4}, 'debuffer')


# ============================================================ 6. SCORCH BEETLE
# Fire burst attacker: squat armoured beetle, bronze-black shell with an iron
# furnace hump on its back (glowing grille + little chimney) and hooked
# mandibles. Special = long furnace charge (legs dig in) then a ramming charge.
SB_SHELL = Pal('#5e3c30', '#90604a', '#3c2420', '#1a0c0a')
SB_PRONO = Pal('#46302a', '#6a4a3e', '#2e1c18', '#140a08')
SB_IRON = Pal('#3c3c48', '#5e5e6c', '#282830', '#121218')
SB_HEAT = [Pal('#b8401a', '#e0642a', '#8a2a10', '#3a0e06'), Pal('#ff8a2a', '#ffd070', '#e0581c', '#5a1a08'),
           Pal('#ffe890', '#ffffff', '#ffc050', '#8a3a10')]
SB_BELLY = Pal('#6e2e20', '#8e422c', '#4c1c14', '#240a06')
SB_LEG = Pal('#3a2826', '#5a403a', '#241618', '#0e0808')
SB_LEG_FAR = Pal('#261a1a', '#342424', '#1a1010', '#0a0506')
SB_MAND = Pal('#6a4c44', '#9a7a6a', '#44302a', '#180e0e')
SB_EYE = [C('#ffb040'), C('#fff0a0')]
SB_GLOW = (255, 120, 30)


def scorch_beetle(dx=0, dy=0, heat=1, legs=0, jaw=0.5, head_dy=0, lean=0, squash=0.0, eyes='open', dig=0):
    cv = Canvas(48, 48)
    g = 43
    cx = 17 + dx
    sx = 1 + squash * 0.1
    sy = 1 - squash * 0.12
    shy = g - 9.5 + dy
    hp = SB_HEAT[heat]

    def leg(att, knee, foot, pal, w0=2):
        m = cv.mask().line(att[0], att[1], knee[0], knee[1], w0).line(knee[0], knee[1], foot[0], foot[1], 1)
        cv.part(m, pal)

    # far legs (splayed, darker)
    for (ax, kx, fx_, ph) in ((6, 11, 13, -legs), (0, 4, 6, legs), (-6, -9, -10, -legs)):
        leg((cx + ax + 1, shy + 2), (cx + kx + 1 + ph, shy - 0.5 - dig * 0.3), (cx + fx_ + 1 + ph * 1.3, g - 1.5),
            SB_LEG_FAR, 1)
    # rear chimney
    b0, b1 = (cx - 7, shy - 5), (cx - 9, shy - 10)
    cv.part(tube(cv.mask(), [b0, b1], 1.4), SB_IRON)
    cv.part(cv.mask().rect(b1[0] - 2, b1[1] - 1, b1[0] + 1.5, b1[1]), SB_IRON)
    cv.dot(b1[0], b1[1] - 1, hp.base)
    # belly
    cv.part(cv.mask().ellipse(cx + 1, shy + 3.8, 11 * sx, 2.4), SB_BELLY)
    # head + mandibles
    hx, hy = cx + 16 - squash, shy + 1.5 + head_dy
    for sgn in (1, -1):
        ang = -10 * sgn - jaw * 24 * sgn
        base = (hx + 2.5, hy + 0.3 * sgn)
        p1 = polar(base[0], base[1], ang, 3.8)
        tip = polar(p1[0], p1[1], ang + 50 * sgn, 2.6)
        cv.part(tube(cv.mask(), [base, p1, tip], 1.4, 0.6), SB_MAND)
    cv.part(cv.mask().ellipse(hx, hy, 3.4, 3.0), SB_PRONO)
    # pronotum with a forward horn
    px_, py_ = cx + 11 * sx, shy - 0.5 + head_dy * 0.5
    horn = bez((px_ + 1, py_ - 3), (px_ + 3.5, py_ - 7), (px_ + 7.5, py_ - 7.5), n=10)
    cv.part(tube(cv.mask(), horn, 1.8, 0.6), SB_PRONO)
    pm = cv.mask().ellipse(px_, py_, 4.8 * sx, 4.8 * sy)
    vpart(cv, pm, SB_PRONO, depth=1)
    # domed wing-cases
    sh = cv.mask().ellipse(cx - 0.5, shy, 11.5 * sx, 9 * sy)
    sh.subtract(cv.mask().rect(0, shy + 3, 47, 47))
    sh.union(cv.mask().ellipse(cx - 0.5, shy + 2.5, 11.2 * sx, 1.8))
    vpart(cv, sh, SB_SHELL, depth=2)
    for t in np.linspace(0.1, 0.9, 8):
        p = bez((cx - 9.5, shy), (cx - 9, shy - 5.5), (cx - 4, shy - 7.5), n=100)[int(t * 100)]
        cv.dot(p[0], p[1] + 1.5, SB_SHELL.hi)
    # the split between the wing-cases glows like an open furnace
    top = shy - 9 * sy
    win = cv.mask().poly([(cx - 9, top + 5), (cx - 4, top + 1), (cx + 2, top + 0.6), (cx + 7, top + 2.5),
                          (cx + 2, top + 3.2), (cx - 4, top + 3.6)])
    cv.part(win, hp, shade=False)
    for t in np.linspace(0.1, 0.9, 6):
        p = bez((cx - 8, top + 4.4), (cx - 3, top + 1.6), (cx + 6, top + 2.2), n=100)[int(t * 100)]
        cv.dot(p[0], p[1], hp.hi)
    # near legs
    for (ax, kx, fx_, ph) in ((6, 10, 13, legs), (0, 3, 5, -legs), (-6, -9, -10, legs)):
        leg((cx + ax, shy + 3), (cx + kx + ph, shy + 0.5 - dig * 0.3), (cx + fx_ + ph * 1.3 - dig * 0.3, g),
            SB_LEG)
    # eye
    ex, ey = hx + 0.5, hy - 1
    if eyes == 'open':
        cv.dot(ex, ey, SB_EYE[0])
        cv.dot(ex + 1, ey, SB_EYE[1] if heat else SB_EYE[0])
    else:
        eyes_pair(cv, [(ex + 0.5, ey)], eyes, INK)
    cv.outline(dark=(20, 10, 10, 255))
    return cv.image()


def _smoke(img, pts, ember=False):
    img = fx_dots(img, pts, C('#8a7a7a') if not ember else SB_HEAT[1].base)
    return fx_dots(img, pts[::2], C('#b0a4a0') if not ember else SB_HEAT[2].base)


def _speed_lines(img, x0, rows, ln=6):
    pts = []
    for y in rows:
        pts += [(x0 - k, y) for k in range(ln)]
    return fx_dots(img, pts, C('#ffd070'))


def scorch_beetle_anims():
    idle = [_smoke(scorch_beetle(heat=1, legs=0), [(8, 20)]),
            _smoke(scorch_beetle(heat=1, legs=1, jaw=0.4), [(7, 18), (8, 16)]),
            _smoke(scorch_beetle(heat=2, legs=0, jaw=0.5), [(6, 15), (8, 13)], True),
            scorch_beetle(heat=1, legs=-1, jaw=0.6)]
    attack = [scorch_beetle(dx=-1, head_dy=-2, jaw=1.1, lean=-1, legs=1),
              scorch_beetle(dx=2, head_dy=0, jaw=1.3, legs=2),
              fx_dots(scorch_beetle(dx=4, head_dy=1, jaw=-0.2, legs=-1),
                      [(45, 30), (45, 35), (44, 38)], C('#fff0c0')),
              scorch_beetle(dx=3, head_dy=0, jaw=0.0),
              scorch_beetle(dx=1, jaw=0.4, legs=1),
              scorch_beetle(jaw=0.5)]
    hit = [scorch_beetle(dx=-2, head_dy=-2, eyes='hurt', jaw=1.0, lean=-1),
           scorch_beetle(dx=-1, eyes='hurt', jaw=0.7)]
    death = [scorch_beetle(dy=1, eyes='hurt', heat=0, jaw=1.0, head_dy=1),
             scorch_beetle(dy=3, eyes='closed', heat=0, jaw=0.9, head_dy=3, legs=2, dig=1)]
    death += die((scorch_beetle(dy=4, eyes='closed', heat=0, jaw=0.9, head_dy=3, legs=2, dig=2),
                  scorch_beetle(dy=4, eyes='closed', heat=0, jaw=0.9, head_dy=3, legs=2, dig=2)),
                 (71, 72), (80, 60, 60))
    special = [charge(scorch_beetle(heat=2, jaw=0.6), SB_GLOW, 1),
               _smoke(charge(scorch_beetle(dx=-1, head_dy=2, heat=2, jaw=0.9, dig=1), SB_GLOW, 2),
                      [(6, 16), (7, 13), (5, 10)], True),
               _smoke(charge(scorch_beetle(dx=-1, head_dy=2, heat=2, jaw=1.0, dig=2, legs=1), SB_GLOW, 3),
                      [(5, 15), (6, 11), (4, 8), (8, 6)], True),
               _smoke(charge(scorch_beetle(dx=-2, head_dy=2, heat=2, jaw=1.1, dig=2, legs=-1), SB_GLOW, 3),
                      [(3, 14), (5, 10), (3, 6), (7, 4), (2, 18)], True),
               _speed_lines(charge(scorch_beetle(dx=2, head_dy=1, heat=2, jaw=1.2, legs=2), SB_GLOW, 2),
                            6, (24, 29, 34), 5),
               fx_dots(charge(scorch_beetle(dx=3, head_dy=0, heat=2, jaw=-0.2, squash=1.0), SB_GLOW, 1),
                       [(45, 27), (46, 32), (45, 37), (44, 23), (43, 40)], C('#fff0c0')),
               scorch_beetle(dx=2, head_dy=-1, heat=1, jaw=0.8, lean=-1),
               scorch_beetle(dx=1, heat=1, jaw=0.5, legs=1),
               scorch_beetle(heat=1, jaw=0.5)]
    return [('idle', idle, 6, True), ('attack', attack, 12, False), ('hit', hit, 10, False),
            ('death', death, 8, False), ('special', special, 11, False)]


register('scorch_beetle', 48, scorch_beetle_anims,
         {'motion': 'melee', 'hit_frames': [2]},
         {'motion': 'melee', 'hit_frames': [5]}, 'burst')


# ============================================================ 7. SHELLCRAB
# Water tank: squat crab wearing a big faceted sea-glass dome, one huge
# pale-tipped crusher claw and a tiny one. Special = hunkers under the glass
# dome, claw folded as a shield, while a shine sweeps across it (guard).
SC_GLASS = Pal('#86d6e6', '#d4f8ff', '#58aac8', '#2a6488')
SC_FACET = C('#b4eef6')
SC_FACET_D = C('#6cc0d8')
SC_BODY = Pal('#2e6a8a', '#4a92b0', '#1e4a66', '#0e2436')
SC_CLAW = Pal('#34549a', '#5a7ec8', '#243a70', '#101c3a')
SC_TIP = Pal('#d0dcee', '#f4f8ff', '#a0b0c8', '#4a5670')
SC_LEG = Pal('#3a7898', '#5a9cba', '#285a78', '#0e2436')
SC_LEG_FAR = Pal('#24506e', '#306482', '#1a3c56', '#0a1a28')
SC_GLOW = (110, 200, 255)


def _claw(cv, px, py, ang, opn, s=1.0, pal=SC_CLAW, tip=SC_TIP):
    """Crab chela in side view: swollen palm, fixed lower finger and a hinged
    upper finger (opn 0 = shut, 1 = wide open) with pale tips."""
    A_ = math.radians(ang)

    def L(u, v):
        return rot(px + u * s, py + v * s, px, py, A_)

    # fixed lower finger
    lf = [L(3.5, 1.4), L(7, 1.6), L(9.5, 0.4), L(10.5, -0.8)]
    cv.part(tube(cv.mask(), lf, 1.7 * s, 0.6), pal)
    cv.part(tube(cv.mask(), lf[2:], 0.9 * s, 0.5), tip, shade=False)
    # hinged upper finger
    hinge = L(3, -1.8)
    da = ang - 8 - opn * 42
    u1 = polar(hinge[0], hinge[1], da, 4.5 * s)
    u2 = polar(u1[0], u1[1], da + 22, 3.2 * s)
    u3 = polar(u2[0], u2[1], da + 55, 1.6 * s)
    cv.part(tube(cv.mask(), [hinge, u1, u2, u3], 1.9 * s, 0.6), pal)
    cv.part(tube(cv.mask(), [u2, u3], 0.9 * s, 0.5), tip, shade=False)
    # swollen palm
    pts = [L(5 * math.cos(t), 3.6 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, 22, endpoint=False)]
    palm = cv.mask().poly(pts)
    vpart(cv, palm, pal, depth=1)
    for (u, v) in ((-1.5, -2.2), (0.5, -2.6), (2.5, -2.2)):
        k = L(u, v)
        cv.dot(k[0], k[1], pal.hi)


def shellcrab(dx=0, dy=0, claw=(13, -1, -12, 0.3), eyes='open', stalk=1.0, legs=0, shine=None, crack=0,
              tuck=0.0):
    cv = Canvas(48, 48)
    g = 43
    cx = 17 + dx
    by = g - 9 + dy + tuck * 2.5
    LEGS = ((-8, -11, -14), (-3, -6, -9), (2, 0, -3))
    # far legs
    for k, (ax, kx, fx_) in enumerate(LEGS[:2]):
        ph = legs if k % 2 else -legs
        a = (cx + ax + 2, by + 1)
        knee = (cx + kx + 2 + ph + tuck * 2, by - 3 + tuck * 3)
        foot = (cx + fx_ + 2 + ph + tuck * 3, g - 1)
        m = cv.mask().line(a[0], a[1], knee[0], knee[1], 2).line(knee[0], knee[1], foot[0], foot[1], 2)
        cv.part(m, SC_LEG_FAR)
    # small claw (behind)
    _claw(cv, cx + 9, by + 2 - tuck, 5, 0.3, 0.5, SC_LEG, SC_TIP)
    # carapace
    body = cv.mask().ellipse(cx, by, 11, 4.5)
    vpart(cv, body, SC_BODY, depth=1)
    for x in range(int(cx - 8), int(cx + 10), 3):
        cv.dot(x, by + 2, SC_BODY.sh)
    # eyestalks
    for (ox, h) in ((6, 7), (9, 6.5)):
        h *= stalk
        b0 = (cx + ox, by - 2)
        b1 = (cx + ox + 1, by - 2 - h)
        cv.part(tube(cv.mask(), [b0, b1], 0.8), SC_BODY)
        if eyes == 'open':
            cv.part(cv.mask().ellipse(b1[0], b1[1], 1.4, 1.4), Pal(INK, INK, INK, INK), flat=True)
            cv.dot(b1[0] - 0.4, b1[1] - 0.6, WHITE)
        elif eyes == 'hurt':
            dots(cv, [(b1[0] - 1, b1[1] - 1), (b1[0], b1[1]), (b1[0] + 1, b1[1] - 1)], INK)
        else:
            dots(cv, [(b1[0] - 1, b1[1]), (b1[0], b1[1]), (b1[0] + 1, b1[1])], INK)
    # glass dome (sits on the rear of the carapace)
    top = by - 17 + tuck * 1.5
    d0 = cx - 3
    dome_pts = [(d0 - 9.5, by - 1), (d0 - 8.5, by - 10 + tuck), (d0 - 3.5, top + 1), (d0 + 2.5, top),
                (d0 + 7.5, by - 10 + tuck), (d0 + 8.5, by - 1)]
    dome = cv.mask().poly(dome_pts)
    gid = pid(cv)
    vpart(cv, dome, SC_GLASS, depth=2)
    apex = (d0 - 0.5, by - 8 + tuck * 0.5)
    for p in dome_pts[1:5]:
        for t in np.linspace(0.15, 0.85, 7):
            x, y = apex[0] + (p[0] - apex[0]) * t, apex[1] + (p[1] - apex[1]) * t
            cv.dot(x, y, SC_FACET if p[0] < apex[0] + 2 else SC_FACET_D)
    fac = cv.mask().poly([apex, dome_pts[2], dome_pts[3]])
    fac.m &= dome.m
    crescent(cv, fac, SC_FACET, 0, 1, SC_GLASS.base)
    dots(cv, [(d0 - 5, top + 5), (d0 - 4, top + 4), (d0 - 6, top + 7)], WHITE)
    if shine is not None:
        for y in range(int(top), int(by)):
            for w in range(3):
                x = int(d0 - 11 + shine * 22 + (by - y) * 0.6 + w)
                if 0 <= x < 48 and dome.m[y, x]:
                    cv.dot(x, y, WHITE if w == 1 else SC_GLASS.hi)
    if crack:
        pts = bez((d0 + 2, top + 1), (d0 - 1, top + 6), (d0 + 3, by - 7), (d0 - 2, by - 2), n=12)
        dots(cv, pts[:int(4 + crack * 8)], SC_GLASS.line)
        dots(cv, [(d0 - 4, top + 8), (d0 - 5, top + 9), (d0 - 6, top + 11)], SC_GLASS.line)
    # near legs
    for k, (ax, kx, fx_) in enumerate(LEGS):
        ph = -legs if k % 2 else legs
        a = (cx + ax, by + 2)
        knee = (cx + kx + ph + tuck * 2, by - 2 + tuck * 3)
        foot = (cx + fx_ + ph + tuck * 3, g)
        m = cv.mask().line(a[0], a[1], knee[0], knee[1], 2).line(knee[0], knee[1], foot[0], foot[1], 2)
        cv.part(m, SC_LEG)
        cv.dot(foot[0], foot[1], SC_TIP.sh)
    # big crusher claw + arm
    hxo, hyo, ang, opn = claw
    shoulder = (cx + 8, by + 1.5)
    hand = (cx + hxo, by + hyo)
    elbow = ((shoulder[0] + hand[0]) / 2 + 1.5, min(shoulder[1], hand[1]) - 1)
    cv.part(tube(cv.mask(), [shoulder, elbow, hand], 1.8, 2.2), SC_CLAW)
    _claw(cv, hand[0], hand[1], ang, opn, 1.05)
    cv.outline(dark=(10, 20, 36, 255))
    translucent(cv, [gid], 222, [SC_GLASS.base, SC_GLASS.sh])
    return cv.image()


def shellcrab_anims():
    idle = [shellcrab(claw=(13, -1, -12, 0.25)),
            shellcrab(claw=(13, -2, -16, 0.5), legs=1, stalk=0.95),
            shellcrab(claw=(13, -1, -12, 0.25), stalk=1.05),
            shellcrab(claw=(13, 0, -8, 0.05), legs=-1)]
    attack = [shellcrab(dx=-1, claw=(11, -12, -55, 0.8), legs=1),
              shellcrab(dx=-1, claw=(9, -17, -75, 1.0), legs=1, stalk=0.9),
              shellcrab(dx=1, claw=(14, 1, 18, 0.0), legs=-1),
              fx_dots(shellcrab(dx=1, dy=1, claw=(14, 1, 22, 0.0), legs=-1),
                      [(42, 42), (44, 40), (40, 41), (45, 43)], C('#9fe8ff')),
              shellcrab(dx=1, claw=(13, -2, -5, 0.3)),
              shellcrab(claw=(13, -1, -12, 0.25))]
    hit = [shellcrab(dx=-1, claw=(11, -8, -40, 0.7), eyes='hurt', stalk=0.8, crack=0.3),
           shellcrab(dx=-1, claw=(12, -4, -25, 0.5), eyes='hurt', stalk=0.9)]
    death = [shellcrab(claw=(12, 0, 10, 0.8), eyes='hurt', stalk=0.7, crack=0.6),
             shellcrab(claw=(13, 2, 25, 0.9), eyes='closed', stalk=0.4, crack=1.0, tuck=0.6)]
    death += die((shellcrab(claw=(13, 2, 30, 0.9), eyes='closed', stalk=0.3, crack=1.0, tuck=1.0),
                  shellcrab(claw=(13, 2, 30, 0.9), eyes='closed', stalk=0.3, crack=1.0, tuck=1.0)),
                 (81, 82), (160, 220, 235))
    hunker = dict(claw=(11, -4, -85, 0.0), stalk=0.25, tuck=1.0, eyes='closed')
    special = [charge(shellcrab(claw=(13, -1, -12, 0.25)), SC_GLOW, 1),
               charge(shellcrab(claw=(12, -3, -50, 0.1), stalk=0.6, tuck=0.5), SC_GLOW, 2),
               charge(shellcrab(**hunker), SC_GLOW, 3),
               aura(shellcrab(shine=0.1, **hunker), (200, 240, 255), 230),
               aura(shellcrab(shine=0.45, **hunker), (160, 220, 255), 200),
               fx_dots(aura(shellcrab(shine=0.85, **hunker), (120, 200, 255), 160),
                       [(6, 22), (26, 18), (10, 17), (30, 23)], WHITE),
               shellcrab(claw=(12, -2, -30, 0.1), stalk=0.7, tuck=0.4)]
    return [('idle', idle, 5, True), ('attack', attack, 11, False), ('hit', hit, 10, False),
            ('death', death, 8, False), ('special', special, 10, False)]


register('shellcrab', 48, shellcrab_anims,
         {'motion': 'melee', 'hit_frames': [2]},
         {'motion': 'self', 'release_frame': 3}, 'tank')


# ============================================================ 8. BRINE EEL
# Water fast attacker: a slate-teal eel rising from its own little puddle in
# an S-curve (a second coil humps out behind), coral fin frill, pale belly,
# long snapping jaws. Attack = two quick bites; special = sinks, then erupts
# into a lunging double bite.
BE_BODY = Pal('#2f6f78', '#4f9aa0', '#1e4a54', '#0c2228')
BE_BELLY = Pal('#c8d8a8', '#eef4d8', '#9ab080', '#4a5a3a')
BE_FIN = Pal('#e0784a', '#ffa872', '#b0502e', '#5a2012')
BE_PUDDLE = Pal('#2a5a8a', '#5aa0d8', '#1e4068', '#0e2440')
BE_MOUTH = C('#3a0e14')
BE_EYE = [C('#ffe04a'), C('#fffbd0')]
BE_GLOW = (80, 220, 230)


def brine_eel(sway=0.0, strike=0.0, back=0.0, jaw=0.2, rise=0.0, ripple=0, eyes='open',
              droop=0.0, spray=False, glow=False):
    cv = Canvas(48, 48)
    g = 43
    cx = 18
    pp = BE_PUDDLE if not glow else Pal('#3a8ac0', '#9ae4ff', '#2a6a9a', '#123a5a')
    # coil hump behind
    hump_h = max(0.0, 6 + rise * 0.5)
    if hump_h > 1.5:
        hp = bez((cx - 13, g - 1), (cx - 12, g - hump_h - 3), (cx - 5, g - hump_h - 3), (cx - 4, g - 1), n=16)
        cv.part(tube(cv.mask(), hp, 2.2), BE_BODY)
        for p in hp[4:13:3]:
            cv.part(cv.mask().poly([(p[0] - 1.5, p[1] - 1.5), (p[0] - 1, p[1] - 4.5), (p[0] + 1.5, p[1] - 1.5)]),
                    BE_FIN)
    # serpentine spine through explicit S-curve points
    k = max(0.0, 1 - strike * 0.7 - back * 0.3)
    lift = rise
    pts = [(cx + 2, g - 2),
           (cx - 5 * k + strike * 1, g - 7 - lift * 0.25),
           (cx + 4 * k - back * 3 + strike * 5, g - 14 - lift * 0.55 + strike * 1.5),
           (cx - 1 * k - back * 7 + strike * 10 + sway * 0.6, g - 21 - lift * 0.8 + strike * 4 + droop * 6),
           (cx + 4 + sway - back * 9 + strike * 13.5, g - 26 - lift + back * 1 + strike * 7 + droop * 10)]
    spine = catmull(pts, 10)
    n = len(spine)
    head = spine[-1]
    # fin frill along the back
    fin = cv.mask()
    for i in range(6, n - 6, 3):
        p, q = spine[i], spine[i + 2]
        nx, ny = -(q[1] - p[1]), q[0] - p[0]
        L_ = math.hypot(nx, ny) or 1
        nx, ny = nx / L_, ny / L_
        if nx > 0.2 or (abs(nx) <= 0.2 and ny > 0):
            nx, ny = -nx, -ny
        h = 3.0 if (i // 3) % 2 == 0 else 2.0
        fin.poly([(p[0], p[1]), (p[0] + nx * (2.4 + h), p[1] + ny * (2.4 + h) - 1), (q[0], q[1])])
    cv.part(fin, BE_FIN)
    body = tube(cv.mask(), spine, 3.0, 2.1)
    vpart(cv, body, BE_BODY, depth=1)
    # belly stripe on the front side
    for i in range(3, n - 3):
        p, q = spine[i], spine[i + 1]
        nx, ny = -(q[1] - p[1]), q[0] - p[0]
        L_ = math.hypot(nx, ny) or 1
        nx, ny = nx / L_, ny / L_
        if nx < -0.2 or (abs(nx) <= 0.2 and ny < 0):
            nx, ny = -nx, -ny
        cv.dot(p[0] + nx * 1.7, p[1] + ny * 1.7, BE_BELLY.base)
        if i % 3 == 0:
            cv.dot(p[0] + nx * 1.2, p[1] + ny * 1.2, BE_BELLY.hi)
    for i in range(8, n - 6, 7):
        cv.dot(spine[i][0] - 1, spine[i][1], BE_BODY.sh)
    # head
    d = (head[0] - spine[-5][0], head[1] - spine[-5][1])
    ang = math.degrees(math.atan2(d[1], d[0]))
    ang = max(-60, min(50, ang)) * 0.5 + (-8 + droop * 60) * 0.5
    A_ = math.radians(ang)

    def H(u, v):
        return rot(head[0] + u, head[1] + v, head[0], head[1], A_)

    ja = math.radians(jaw * 38)

    def J(u, v):
        p = H(u, v)
        return rot(p[0], p[1], H(0, 0.5)[0], H(0, 0.5)[1], ja)

    lower = cv.mask().poly([J(-1, 0.5), J(4, 0.8), J(7.5, 1.2), J(7, 2.4), J(2, 3), J(-1.5, 2.5)])
    if jaw > 0.25:
        mouth = cv.mask().poly([H(0, 0.2), H(7.5, 0.6), J(7.5, 1.2), J(0, 1.0)])
        cv.part(mouth, Pal(BE_MOUTH, BE_MOUTH, BE_MOUTH, BE_MOUTH), flat=True)
    cv.part(lower, BE_BELLY)
    skull = cv.mask().poly([H(-3, -3.2), H(2, -3.8), H(6, -2.2), H(8.5, -0.2), H(8, 1), H(0, 1), H(-3, 1.5)])
    skull.ellipse(*H(-1, -1), 3.2, 3.0)
    vpart(cv, skull, BE_BODY, depth=1)
    if jaw > 0.25:
        for u in (2.5, 5, 7):
            p = H(u, 1.6)
            cv.dot(p[0], p[1], WHITE)
            q = J(u - 0.5, 0.2)
            cv.dot(q[0], q[1], WHITE)
    cv.part(cv.mask().poly([H(-4, -2), H(-1, -6.5), H(1.5, -3.5)]), BE_FIN)
    e = H(3, -1.6)
    if eyes == 'open':
        cv.dot(e[0], e[1], BE_EYE[0])
        cv.dot(e[0] + 1, e[1], BE_EYE[1])
        cv.dot(e[0], e[1] + 1, BE_EYE[0])
    else:
        eyes_pair(cv, [(e[0] + 0.5, e[1])], eyes, INK)
    cv.outline(dark=(8, 22, 30, 255))
    # the puddle is painted after the outline: soft, see-through water
    pud = cv.mask().ellipse(cx - 1, g - 1.5, 14 + ripple * 0.5, 2.0)
    lip = cv.mask().ellipse(cx - 1, g - 0.8, 13 + ripple * 0.5, 1.3)
    lip.subtract(cv.mask().rect(0, 0, 47, g - 2))
    a = cv.px
    empty = a[:, :, 3] == 0
    a[pud.m & empty] = A(pp.base, 215)
    a[lip.m] = A(pp.base, 235)
    rim = ring(Mask(48, 48), cx - 1, g - 1.5, 14 + ripple * 0.5, 2.0, 1.0)
    rim.subtract(Mask(48, 48).rect(0, g - 1, 47, 47))
    a[rim.m & (empty | lip.m)] = A(pp.hi, 235)
    for kx in range(3):
        x = int(cx - 9 + kx * 7 + ripple)
        if a[g - 1, x, 3] and a[g - 1, x, 3] < 255:
            a[g - 1, x] = A(pp.hi, 240)
            a[g - 1, x + 1] = A(pp.hi, 240)
    bottom = Mask(48, 48).ellipse(cx - 1, g - 1.5, 14.5 + ripple * 0.5, 2.6)
    bottom.subtract(pud)
    bottom.subtract(Mask(48, 48).rect(0, 0, 47, g - 1))
    a[bottom.m & (a[:, :, 3] == 0)] = A(pp.line, 230)
    img = cv.image()
    if spray:
        img = fx_dots(img, [(cx - 10, g - 6), (cx - 13, g - 9), (cx + 9, g - 7), (cx + 12, g - 4),
                            (cx - 6, g - 11), (cx + 6, g - 12), (cx - 15, g - 4)], C('#aef0ff'))
    return img


def brine_eel_anims():
    idle = [brine_eel(sway=0, jaw=0.15, ripple=0), brine_eel(sway=1.5, jaw=0.3, ripple=1),
            brine_eel(sway=2.5, jaw=0.15, ripple=2), brine_eel(sway=1, jaw=0.05, ripple=1)]
    attack = [brine_eel(back=0.8, jaw=0.1, rise=1, ripple=1),
              brine_eel(strike=0.9, jaw=1.0, ripple=2),
              fx_dots(brine_eel(strike=1.0, jaw=0.0, ripple=2), [(44, 18), (45, 22)], WHITE),
              brine_eel(strike=0.55, back=0.1, jaw=0.9, ripple=1),
              fx_dots(brine_eel(strike=0.95, jaw=0.0, ripple=0), [(44, 20), (45, 24)], WHITE),
              brine_eel(sway=0.5, jaw=0.2, ripple=1)]
    hit = [brine_eel(back=0.6, eyes='hurt', jaw=0.6, ripple=2, sway=-1),
           brine_eel(back=0.25, eyes='hurt', jaw=0.3, ripple=1)]
    death = [brine_eel(back=0.3, eyes='hurt', jaw=0.7, droop=0.3, ripple=1),
             brine_eel(rise=-8, eyes='closed', jaw=0.5, droop=0.6, ripple=2)]
    death += die((brine_eel(rise=-12, eyes='closed', jaw=0.4, droop=0.6, ripple=2),
                  brine_eel(rise=-12, eyes='closed', jaw=0.4, droop=0.6, ripple=3)), (91, 92), (120, 200, 220))
    special = [charge(brine_eel(rise=-4, back=0.3, jaw=0.2, ripple=1, glow=True), BE_GLOW, 1),
               charge(brine_eel(rise=-9, back=0.5, jaw=0.1, ripple=2, glow=True), BE_GLOW, 2),
               charge(brine_eel(rise=-12, back=0.7, jaw=0.0, ripple=3, glow=True, eyes='closed'), BE_GLOW, 3),
               brine_eel(rise=3, back=0.2, jaw=0.8, ripple=3, spray=True),
               brine_eel(rise=1, strike=1.0, jaw=1.0, ripple=2, spray=True),
               fx_dots(brine_eel(strike=1.05, jaw=0.0, ripple=2), [(44, 18), (45, 22), (43, 15)], WHITE),
               fx_dots(brine_eel(strike=0.9, jaw=0.0, back=0.05, ripple=1), [(44, 21), (45, 25)], WHITE),
               brine_eel(sway=0.5, jaw=0.2, ripple=1)]
    return [('idle', idle, 8, True), ('attack', attack, 14, False), ('hit', hit, 10, False),
            ('death', death, 8, False), ('special', special, 12, False)]


register('brine_eel', 48, brine_eel_anims,
         {'motion': 'melee', 'hit_frames': [2, 4]},
         {'motion': 'melee', 'hit_frames': [5, 6]}, 'attacker')


# ============================================================ 9. DRIFT JELLY
# Water healer: a floating lavender jellyfish with a see-through bell, a pink
# four-lobed heart, glowing cyan rim lights and long glowing tendrils. Lashes
# with its tendrils; special = contracts, glows, and releases a healing ring.
DJ_BELL = Pal('#d0a6ee', '#f4e2ff', '#a476cc', '#4a2a6a')
DJ_HEART = Pal('#ff9ad8', '#ffd8f0', '#e060b0', '#7a2060')
DJ_ARM = Pal('#e8a8e0', '#ffe0f8', '#c078c0', '#6a3070')
DJ_TEND = [C('#9ae8f0'), C('#c8fbff'), C('#ffffff')]
DJ_EYE = C('#2a1440')
DJ_GLOW = (120, 240, 255)


def drift_jelly(dx=0, dy=0, pulse=0.0, ph=0.0, glow=0, sweep=0.0, curl=0.0, eyes='open', droop=0.0):
    cv = Canvas(48, 48)
    cx, by = 23 + dx, 20 + dy
    rx, ry = 11.5 * (1 - 0.16 * pulse), 9.5 * (1 + 0.14 * pulse)
    rim_y = by + 1
    tcol = DJ_TEND[min(glow, 2)]
    tip = DJ_TEND[2] if glow else DJ_TEND[1]
    # tendrils (behind the bell)
    tend = []
    for i, off in enumerate((-8, -4.5, 4.5, 8, -1, 1.5)):
        x0 = cx + off * rx / 11.5
        ln = (16 + (i % 3) * 3) * (1 - curl * 0.5) * (1 - max(sweep, 0) * 0.42)
        ang = math.radians(90 - sweep * (70 + i * 4) + droop * 30)
        dirx, diry = math.cos(ang), math.sin(ang)
        pts = []
        for k in range(int(ln) + 1):
            w = math.sin(ph + k * 0.45 + i * 1.3) * (1.2 + k * 0.05) * (1 - sweep * 0.6)
            c_ = curl * k * 0.25 * (1 if off < 0 else -1)
            pts.append((x0 + dirx * k - diry * w + c_, rim_y + diry * k + dirx * w))
        tend.append(pts)
        if i < 4:
            m = cv.mask()
            for a_, b_ in zip(pts, pts[1:]):
                m.line(a_[0], a_[1], b_[0], b_[1], 1)
            cv.part(m, Pal(tcol, tcol, tcol, tcol), flat=True)
    # frilly oral arms
    for pts in tend[4:]:
        m = tube(cv.mask(), pts[:int(len(pts) * 0.75)], 1.3, 0.8)
        cv.part(m, DJ_ARM)
    # bell
    bell = cv.mask().ellipse(cx, by, rx, ry)
    bell.subtract(cv.mask().rect(0, rim_y, 47, 47))
    for k in range(-4, 5):
        bell.ellipse(cx + k * rx / 4.4, rim_y, 1.5, 1.4)
    bid = pid(cv)
    vpart(cv, bell, DJ_BELL, depth=2)
    # inner heart (four lobes)
    hc = (cx - 0.5, by - ry * 0.35)
    heart = cv.mask()
    for (ox, oy) in ((-2, 0), (2, 0), (0, -1.8), (0, 1.8)):
        heart.ellipse(hc[0] + ox, hc[1] + oy, 1.8, 1.6)
    hp = DJ_HEART if glow < 2 else Pal('#ffd0f0', '#ffffff', '#ff9ad8', '#a03a80')
    cv.part(heart, hp, separate=False)
    # rim lights
    for k in range(-3, 4):
        x = cx + k * rx / 3.6
        cv.dot(x, rim_y - 1, tcol if glow else DJ_TEND[0])
    dots(cv, [(cx - rx * 0.55, by - ry * 0.55), (cx - rx * 0.55 + 1, by - ry * 0.68),
              (cx - rx * 0.62, by - ry * 0.4)], WHITE)
    # face
    ey = by - 1
    ex = (cx + 3, cx + 7)
    if eyes == 'open':
        for x in ex:
            dots(cv, [(x, ey), (x, ey + 1)], DJ_EYE)
    else:
        eyes_pair(cv, [(x, ey) for x in ex], eyes, DJ_EYE)
    cv.outline(dark=(40, 20, 60, 255))
    translucent(cv, [bid], 205, [DJ_BELL.base, DJ_BELL.sh])
    img = cv.image()
    # glowing tendril tips on top
    pts = [t[-1] for t in tend[:4]]
    img = fx_dots(img, pts, tip)
    if glow:
        img = fx_dots(img, [t[len(t) // 2] for t in tend[:4]], DJ_TEND[2])
    return img


def _pulse_ring(img, cx, cy, r, col, alpha=210):
    m = ring(Mask(48, 48), cx, cy, r, r * 0.75, 1.0)
    a = np.array(img)
    sel = m.m & (a[:, :, 3] == 0)
    sel[0, :] = sel[-1, :] = False
    sel[:, 0] = sel[:, -1] = False
    a[sel] = A(col, alpha)
    return Image.fromarray(a, 'RGBA')


def drift_jelly_anims():
    idle = [drift_jelly(pulse=0.0, ph=0), drift_jelly(pulse=0.6, dy=-1, ph=1.2),
            drift_jelly(pulse=1.0, dy=-2, ph=2.4), drift_jelly(pulse=0.4, dy=-1, ph=3.6)]
    attack = [drift_jelly(dx=-2, pulse=1.0, ph=0.5, sweep=-0.15),
              drift_jelly(dx=2, dy=-1, pulse=-0.2, ph=1.2, sweep=-0.3),
              fx_dots(drift_jelly(dx=2, pulse=0.3, ph=2.0, sweep=0.9, glow=1),
                      [(43, 26), (45, 30), (44, 22)], DJ_TEND[2]),
              drift_jelly(dx=2, pulse=0.2, ph=2.6, sweep=0.7, glow=1),
              drift_jelly(dx=1, pulse=0.3, ph=3.2, sweep=0.2),
              drift_jelly(pulse=0.0, ph=3.8)]
    hit = [drift_jelly(dx=-3, pulse=1.0, eyes='hurt', ph=1, sweep=0.3),
           drift_jelly(dx=-1, pulse=0.5, eyes='hurt', ph=2, sweep=0.15)]
    death = [drift_jelly(dy=2, pulse=0.8, eyes='hurt', ph=1, droop=0.3),
             drift_jelly(dy=8, pulse=-0.2, eyes='closed', ph=2, curl=0.6, droop=0.5)]
    death += die((drift_jelly(dy=12, pulse=-0.3, eyes='closed', ph=3, curl=0.9),
                  drift_jelly(dy=13, pulse=-0.3, eyes='closed', ph=3.5, curl=1.0)), (101, 102), (200, 170, 230))
    rc = DJ_TEND[1]
    special = [charge(drift_jelly(ph=0, glow=1, eyes='closed'), DJ_GLOW, 1),
               charge(drift_jelly(pulse=0.9, dy=-1, ph=1, glow=1, curl=0.4, eyes='closed'), DJ_GLOW, 2),
               charge(drift_jelly(pulse=1.1, dy=-2, ph=2, glow=2, curl=0.8, eyes='closed'), DJ_GLOW, 3),
               _pulse_ring(drift_jelly(pulse=-0.3, dy=-1, ph=3, glow=2), 23, 22, 14, rc, 230),
               _pulse_ring(_pulse_ring(drift_jelly(pulse=-0.2, ph=3.6, glow=2), 23, 22, 19, rc, 220),
                           23, 22, 11, DJ_TEND[2], 200),
               _heal_sparks(_pulse_ring(drift_jelly(pulse=0.1, ph=4.2, glow=1), 23, 22, 22, DJ_TEND[0], 170),
                            [(10, 12), (36, 10), (14, 30), (34, 32), (23, 4)], cols=(DJ_TEND[0], DJ_TEND[1])),
               _heal_sparks(drift_jelly(pulse=0.3, ph=4.8, glow=1), [(8, 8), (39, 6), (12, 26), (37, 28)],
                            cols=(DJ_TEND[0], DJ_TEND[1])),
               drift_jelly(pulse=0.0, ph=5.4)]
    return [('idle', idle, 6, True), ('attack', attack, 12, False), ('hit', hit, 10, False),
            ('death', death, 8, False), ('special', special, 10, False)]


register('drift_jelly', 48, drift_jelly_anims,
         {'motion': 'melee', 'hit_frames': [2]},
         {'motion': 'self', 'release_frame': 4}, 'healer')


# ============================================================ 10. SALT WRAITH
# Water debuffer: a hooded figure of sea mist with a hollow face and two
# cyan eyes, jagged salt crystals growing from its shoulders, crystal-shard
# claws and a curling wisp tail. Flings salt shards; special = shards gather
# into a halo, then it pushes a crescent curse wave forward.
SW_MIST = Pal('#a8bccc', '#dce8f0', '#7890a4', '#34465a')
SW_MIST_FAR = Pal('#8a9eb2', '#a8bccc', '#687e94', '#2a3a4c')
SW_SALT = Pal('#eef4f8', '#ffffff', '#b4c6d4', '#56687a')
SW_HOLLOW = C('#1a2636')
SW_EYE = [C('#7ff8ff'), C('#e8ffff')]
SW_CURSE = Pal('#9a8ad8', '#d8d0ff', '#6e5eb0', '#2e2460')
SW_GLOW = (150, 140, 255)


def _shard(m, x, y, ang, ln, wd=1.6):
    tip = polar(x, y, ang, ln)
    mid = polar(x, y, ang, ln * 0.35)
    l = polar(mid[0], mid[1], ang - 90, wd)
    r = polar(mid[0], mid[1], ang + 90, wd)
    return m.poly([(x, y), l, tip, r])


def salt_wraith(dx=0, dy=0, arm=(20, 9), back_arm=(200, 6), ph=0.0, orbit=0.0, eyes='open', halo=0.0,
                wave=0.0, held=False, fade=0.0, spread=0.0):
    cv = Canvas(48, 48)
    cx = 21 + dx
    hx, hy = cx + 2, 13 + dy
    # back arm
    sh_b = (hx - 3, hy + 7)
    hb = polar(sh_b[0], sh_b[1], back_arm[0], back_arm[1])
    cv.part(tube(cv.mask(), bez(sh_b, ((sh_b[0] + hb[0]) / 2, (sh_b[1] + hb[1]) / 2 + 2), hb, n=8), 1.8, 1.1),
            SW_MIST_FAR)
    for k in (-35, 0, 35):
        cv.part(_shard(cv.mask(), hb[0], hb[1], back_arm[0] + k, 3.2, 0.9), SW_SALT)
    # floating shards behind
    orb = []
    for k in range(3):
        a = math.radians(orbit + k * 120)
        orb.append((cx + 13 * math.cos(a), hy + 12 + 4 * math.sin(a), math.sin(a), a))
    for (x, y, z, a) in orb:
        if z < 0:
            cv.part(_shard(cv.mask(), x, y + 2, -90 + math.degrees(a) * 0.2, 5, 1.3), SW_SALT)
    # body of mist with a curling tail
    body = cv.mask().ellipse(cx, hy + 10, 7.5 + spread, 8.5)
    tail = bez((cx, hy + 15), (cx - 1 + math.sin(ph) * 1.5, hy + 23), (cx - 7, hy + 26 + math.sin(ph + 1)),
               (cx - 11 + math.sin(ph + 2), hy + 22), n=16)
    tube(body, tail, 5.5, 0.8)
    body.ellipse(hx, hy, 5.5, 5.8)
    body.poly([(hx - 3.5, hy - 3), (hx - 8 + math.sin(ph) * 0.8, hy - 6.5), (hx - 1, hy - 5.2)])
    bid = pid(cv)
    vpart(cv, body, SW_MIST, depth=2)
    # drifting mist wisps on the body
    for i, (ox, oy) in enumerate(((-4, 9), (2, 14), (-2, 18))):
        x = cx + ox + math.sin(ph + i) * 1.2
        dots(cv, [(x, hy + oy), (x + 1, hy + oy), (x + 2, hy + oy + 1)], SW_MIST.hi)
    # salt crystals growing from shoulders and back
    for (ox, oy, a, ln) in ((-5, 4, -118, 8), (-1.5, 5, -96, 5.5), (-8, 7, -150, 7), (-7, 11, -175, 5)):
        cv.part(_shard(cv.mask(), hx + ox, hy + oy, a, ln, 1.8), SW_SALT)
    # hollow face
    cv.part(cv.mask().ellipse(hx + 1.8, hy + 0.8, 3.0, 3.4), Pal(SW_HOLLOW, SW_HOLLOW, SW_HOLLOW, SW_HOLLOW),
            flat=True)
    if eyes in ('open', 'flare'):
        for x in (hx + 1, hx + 3.5):
            cv.dot(x, hy, SW_EYE[0])
            cv.dot(x, hy + 1, SW_EYE[0] if eyes == 'flare' else SW_HOLLOW)
            if eyes == 'flare':
                cv.dot(x, hy - 1, SW_EYE[1])
        cv.dot(hx + 1, hy, SW_EYE[1])
    else:
        eyes_pair(cv, [(hx + 1.5, hy), (hx + 4, hy)], eyes, SW_EYE[0])
    # front arm with crystal claws
    sh_f = (hx + 2, hy + 7)
    hf = polar(sh_f[0], sh_f[1], arm[0], arm[1])
    el = ((sh_f[0] + hf[0]) / 2 - 1, (sh_f[1] + hf[1]) / 2 + 2)
    cv.part(tube(cv.mask(), bez(sh_f, el, hf, n=10), 2.0, 1.3), SW_MIST)
    for k in (-35, 0, 35):
        cv.part(_shard(cv.mask(), hf[0], hf[1], arm[0] + k, 3.8, 1.0), SW_SALT)
    if held:
        cv.part(_shard(cv.mask(), hf[0] + 1, hf[1] - 1, -60, 6, 1.6), Pal('#ffffff', '#ffffff', '#cfe8ff', '#6a8aa8'))
    # floating shards in front
    for (x, y, z, a) in orb:
        if z >= 0:
            cv.part(_shard(cv.mask(), x, y + 2, -90 + math.degrees(a) * 0.2, 5, 1.3), SW_SALT)
    # halo of gathered shards (special wind-up)
    if halo:
        for k in range(6):
            a = math.radians(k * 60 + halo * 40)
            x, y = hx - 1 + 9 * math.cos(a) * halo, hy - 5 + 3 * math.sin(a) * halo
            cv.part(_shard(cv.mask(), x, y + 2, -90, 4.5, 1.2), SW_SALT)
    # curse wave
    if wave:
        r = 6 + wave * 12
        wcx, wcy = hx + 2, hy + 12
        wm = cv.mask()
        for t in np.linspace(-55, 55, 30):
            p = polar(wcx, wcy, t, r)
            wm.ellipse(p[0], p[1], 2.2 - abs(t) / 55, 1.8 - abs(t) / 70)
        wm.subtract(cv.mask().rect(46, 0, 47, 47))
        cv.part(wm, SW_CURSE)
        for t in (-40, -10, 20, 45):
            p = polar(wcx, wcy, t, r + 1)
            cv.part(_shard(cv.mask(), p[0], p[1], t, 3, 0.9), SW_SALT)
    cv.outline(dark=(22, 30, 46, 255))
    translucent(cv, [bid], 190, [SW_MIST.base, SW_MIST.sh])
    img = cv.image()
    if fade:
        img = dissolve(img, fade, 7)
    return img


def salt_wraith_anims():
    idle = [salt_wraith(ph=0, orbit=0), salt_wraith(dy=-1, ph=1.5, orbit=30, arm=(25, 9)),
            salt_wraith(dy=-2, ph=3, orbit=60, arm=(28, 9)), salt_wraith(dy=-1, ph=4.5, orbit=90, arm=(24, 9))]
    attack = [salt_wraith(dx=-1, arm=(-80, 8), back_arm=(170, 6), ph=0.5, orbit=10, held=True),
              salt_wraith(dx=-2, arm=(-130, 8), back_arm=(150, 6), ph=1, orbit=20, held=True, eyes='flare'),
              fx_dots(salt_wraith(dx=2, arm=(5, 11), back_arm=(210, 6), ph=1.5, orbit=30, eyes='flare'),
                      [(40, 22), (42, 21), (44, 20), (41, 23)], SW_SALT.base),
              salt_wraith(dx=2, arm=(30, 10), back_arm=(215, 6), ph=2, orbit=40),
              salt_wraith(dx=1, arm=(25, 9), ph=2.5, orbit=50),
              salt_wraith(ph=3, orbit=60)]
    hit = [salt_wraith(dx=-3, arm=(80, 7), back_arm=(230, 5), ph=1, eyes='hurt', orbit=15),
           salt_wraith(dx=-1, arm=(50, 8), ph=2, eyes='hurt', orbit=25)]
    death = [salt_wraith(dy=1, arm=(95, 7), back_arm=(250, 5), eyes='hurt', ph=1),
             salt_wraith(dy=3, arm=(100, 6), back_arm=(260, 5), eyes='closed', ph=2, fade=0.15)]
    death += die((salt_wraith(dy=4, arm=(100, 6), back_arm=(260, 5), eyes='closed', ph=3),
                  salt_wraith(dy=5, arm=(100, 6), back_arm=(260, 5), eyes='closed', ph=4)), (111, 112),
                 (230, 240, 250))
    special = [charge(salt_wraith(ph=0, orbit=0, eyes='flare'), SW_GLOW, 1),
               charge(salt_wraith(dy=-1, arm=(-40, 9), back_arm=(220, 7), ph=1, orbit=40, eyes='flare',
                                  halo=0.5, spread=1), SW_GLOW, 2),
               charge(salt_wraith(dy=-2, arm=(-60, 9), back_arm=(240, 7), ph=2, orbit=80, eyes='flare',
                                  halo=1.0, spread=1.5), SW_GLOW, 3),
               charge(salt_wraith(dx=1, arm=(0, 11), back_arm=(200, 7), ph=3, orbit=120, eyes='flare', halo=0.6,
                                  wave=0.1), SW_GLOW, 2),
               salt_wraith(dx=2, arm=(5, 11), back_arm=(205, 7), ph=3.5, orbit=150, eyes='flare', wave=0.45),
               salt_wraith(dx=2, arm=(10, 10), ph=4, orbit=180, eyes='flare', wave=0.8),
               fx_dots(salt_wraith(dx=1, arm=(20, 9), ph=4.5, orbit=210),
                       [(42, 18), (44, 24), (43, 30), (45, 21), (41, 34)], SW_CURSE.hi),
               salt_wraith(ph=5, orbit=240)]
    return [('idle', idle, 6, True), ('attack', attack, 12, False), ('hit', hit, 10, False),
            ('death', death, 8, False), ('special', special, 10, False)]


register('salt_wraith', 48, salt_wraith_anims,
         {'motion': 'ranged', 'release_frame': 2},
         {'motion': 'ranged', 'release_frame': 4}, 'debuffer')
