"""
Original enemy designs for Cinderbound: Cinder Slime, Tidefin, Bramble Pup,
plus the Ancient Bramble Pup mini-boss variant. All face RIGHT.
"""
import math
import random
import numpy as np
from PIL import Image
from pixlib import Canvas, Pal, hexc


def dissolve(img, amount, seed=3, tint=None):
    """Removes a random fraction of pixels (death fade)."""
    a = np.array(img).copy()
    rng = random.Random(seed)
    h, w = a.shape[:2]
    for y in range(h):
        for x in range(w):
            if a[y, x, 3] and rng.random() < amount:
                a[y, x, 3] = 0
            elif a[y, x, 3] and tint is not None:
                a[y, x, :3] = (a[y, x, :3] * 0.5 + np.array(tint) * 0.5).astype(np.uint8)
    return Image.fromarray(a, 'RGBA')


def sink(img, dy):
    out = Image.new('RGBA', img.size, (0, 0, 0, 0))
    out.paste(img, (0, dy), img)
    return out


# ============================================================ CINDER SLIME
SL_BODY = Pal('#9c2324', '#d0433a', '#651419', '#3c0a10')
SL_CORE = Pal('#ff9a2e', '#ffe07a', '#e0601c')
FLAME = [hexc('#ffe27a'), hexc('#ff9a2e'), hexc('#e8481c')]


def slime(sx=1.0, sy=1.0, dx=0, eyes='open', flame=0, core_pulse=0, open_mouth=False):
    cv = Canvas(48, 48)
    rx, ry = 12.0 * sx, 9.5 * sy
    cx, cy = 24 + dx, 43 - ry
    body = cv.mask().ellipse(cx, cy, rx, ry)
    body.rect(cx - rx + 1, 42, cx + rx - 1, 43)            # flat bottom
    cv.part(body, SL_BODY)
    # glowing core with floating embers
    cv.part(cv.mask().ellipse(cx - 1, cy + 1, 3.5 + core_pulse * 0.5, 3 + core_pulse * 0.5), SL_CORE,
            separate=False)
    cv.dot(cx - 5, cy + 3, SL_CORE.base)
    cv.dot(cx + 2, cy - 3, SL_CORE.hi)
    cv.dot(cx - 3, cy - 4, SL_CORE.sh)
    # shine
    cv.dot(cx - rx * 0.55, cy - ry * 0.55, (255, 180, 160, 255))
    cv.dot(cx - rx * 0.55 + 1, cy - ry * 0.65, (255, 180, 160, 255))
    ex = cx + rx * 0.45
    ey = cy - ry * 0.2
    if eyes == 'open':
        for (x, y) in ((ex, ey), (ex, ey + 1), (ex + 3, ey), (ex + 3, ey + 1)):
            cv.dot(x, y, (18, 8, 10, 255))
    elif eyes == 'hurt':
        for (x, y) in ((ex - 1, ey), (ex, ey + 1), (ex + 1, ey), (ex + 3, ey), (ex + 4, ey + 1), (ex + 2, ey + 1)):
            cv.dot(x, y, (18, 8, 10, 255))
    else:
        for (x, y) in ((ex, ey + 1), (ex + 1, ey + 1), (ex + 3, ey + 1), (ex + 4, ey + 1)):
            cv.dot(x, y, (18, 8, 10, 255))
    if open_mouth:
        for x in range(3):
            cv.dot(ex + x + 1, ey + 3, (40, 8, 10, 255))
    cv.outline()
    if flame:
        fx, fy = cx + 1, cy - ry - 1
        shape = [(0, 0, 1), (-1, 0, 1), (1, 0, 2), (0, -1, 0), (0, -2, 1), (-1, -1, 1)]
        if flame == 2:
            shape += [(1, -2, 0), (0, -3, 1), (1, -1, 0)]
        for (x, y, c) in shape:
            cv.dot(fx + x, fy + y, FLAME[c])
    return cv.image()


def aura(img, col, strength=150):
    """Adds a 1px coloured rim around the sprite (charging / special attack glow)."""
    from PIL import Image
    a = img.copy()
    src = img.load()
    dst = a.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            if src[x, y][3] > 0:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < w and 0 <= yy < h and src[xx, yy][3] > 0:
                    dst[x, y] = (col[0], col[1], col[2], strength)
                    break
    return a


def special_from(idle0, attack, col):
    """Wind-up with a glowing rim, then the attack frames still charged."""
    bright = (min(255, col[0] + 80), min(255, col[1] + 80), min(255, col[2] + 80))
    return [aura(idle0, col, 120), aura(idle0, bright, 200), aura(attack[0], bright, 220)] + \
        [aura(f, col, 170) for f in attack[1:]]


def slime_anims():
    idle = [slime(1.0, 1.0), slime(1.05, 0.93, core_pulse=1), slime(1.0, 1.0, flame=1),
            slime(0.95, 1.07, flame=2, core_pulse=1)]
    attack = [slime(1.15, 0.8, eyes='closed'), slime(1.2, 0.72, eyes='closed', core_pulse=1),
              slime(0.8, 1.2, dx=4, flame=2, open_mouth=True), slime(1.25, 0.8, dx=7, flame=2, open_mouth=True),
              slime(1.05, 0.95, dx=2)]
    hit = [slime(1.15, 0.85, dx=-2, eyes='hurt'), slime(1.05, 0.95, dx=-1, eyes='hurt')]
    base = slime(1.3, 0.65, eyes='hurt')
    death = [slime(1.2, 0.8, eyes='hurt'), base, dissolve(slime(1.5, 0.45, eyes='closed'), 0.35, 1),
             dissolve(slime(1.6, 0.35, eyes='closed'), 0.75, 2)]
    return [('idle', idle, 6, True), ('attack', attack, 12, False), ('hit', hit, 10, False),
            ('death', death, 8, False), ('special', special_from(idle[0], attack, (255, 140, 40)), 12, False)]


# ============================================================ TIDEFIN
TF_BODY = Pal('#23457a', '#3665a8', '#172d52', '#0c1730')
TF_BELLY = Pal('#8cc6e8', '#c4e8f8', '#5f9cc4', '#3b6e92')
TF_FIN = Pal('#3aa0c8', '#7ad4ee', '#23709a', '#134860')
TF_EYE = hexc('#ffd83a')


def tidefin(dx=0, dy=0, fin=0, tail=0, eyes='open', mouth=False, leg=0, belly_up=False, lean=0):
    cv = Canvas(48, 48)
    cx, cy = 24 + dx, 33 + dy
    # tail (behind, left)
    ta = math.radians(tail)
    tx0, ty0 = cx - 8, cy
    tx1, ty1 = tx0 - 7 * math.cos(ta), ty0 - 7 * math.sin(ta) + 1
    tail_m = cv.mask().line(tx0, ty0, tx1, ty1, 4).line(tx1, ty1, tx1 - 3 * math.cos(ta + 0.6),
                                                            ty1 - 3 * math.sin(ta + 0.6), 2)
    cv.part(tail_m, TF_BODY)
    # tail fin
    fx, fy = tx1 - 2 * math.cos(ta), ty1 - 2 * math.sin(ta)
    cv.part(cv.mask().poly([(fx, fy), (fx - 4, fy - 5), (fx - 2, fy), (fx - 4, fy + 4)]), TF_FIN)
    # back legs
    for (lx, ph) in ((cx - 5, leg), (cx + 4, -leg)):
        cv.part(cv.mask().line(lx, cy + 4, lx + ph, cy + 9, 3), TF_BODY.__class__('#1d3a66'))
    # dorsal fin
    cv.part(cv.mask().poly([(cx - 6, cy - 5), (cx - 3, cy - 12 - fin), (cx + 1, cy - 11 - fin),
                            (cx + 4, cy - 5)]), TF_FIN)
    # body
    cv.part(cv.mask().ellipse(cx, cy + lean * 0.3, 10, 6), TF_BODY)
    cv.part(cv.mask().ellipse(cx + 1, cy + 3, 8, 2.5), TF_BELLY, separate=False)
    # head
    hx, hy = cx + 9, cy - 2 + lean
    cv.part(cv.mask().ellipse(hx, hy, 5.5, 4.5), TF_BODY)
    cv.part(cv.mask().ellipse(hx + 1, hy + 2.5, 4, 1.5), TF_BELLY, separate=False)
    if mouth:
        for x in range(4):
            cv.dot(hx + 2 + x, hy + 2, (10, 20, 40, 255))
        cv.dot(hx + 5, hy + 3, (240, 240, 255, 255))
    # front legs
    for (lx, ph) in ((cx + 6, -leg),):
        cv.part(cv.mask().line(lx, cy + 4, lx + 1 + ph, cy + 9, 3), Pal('#2a4f88'))
    # pectoral fin (oversized)
    cv.part(cv.mask().poly([(cx + 2, cy), (cx - 5, cy + 3 - fin), (cx - 7, cy + 7 - fin), (cx + 1, cy + 4)]),
            TF_FIN)
    # big yellow eye
    ex, ey = hx + 1, hy - 2
    if eyes == 'open':
        cv.part(cv.mask().rect(ex, ey, ex + 2, ey + 1), Pal(TF_EYE, TF_EYE, TF_EYE, TF_EYE), flat=True)
        cv.dot(ex + 2, ey, (20, 14, 8, 255))
        cv.dot(ex + 2, ey + 1, (20, 14, 8, 255))
    elif eyes == 'hurt':
        for (x, y) in ((ex, ey), (ex + 1, ey + 1), (ex + 2, ey)):
            cv.dot(x, y, (20, 14, 8, 255))
    else:
        for x in range(3):
            cv.dot(ex + x, ey + 1, (20, 14, 8, 255))
    cv.outline()
    img = cv.image()
    if belly_up:
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        bb = img.getbbox()
        img = sink(img, 44 - bb[3])
    return img


DROPLET = [hexc('#9ff3ff'), hexc('#4fc9e8')]


def with_drops(img, pts):
    a = img.copy()
    for i, (x, y) in enumerate(pts):
        a.putpixel((x, y), DROPLET[i % 2])
    return a


def tidefin_anims():
    idle = [tidefin(fin=0, tail=0), tidefin(dy=-1, fin=1, tail=8), tidefin(dy=-1, fin=2, tail=14),
            tidefin(fin=1, tail=6)]
    attack = [tidefin(dx=-2, tail=-25, fin=1, eyes='closed', lean=1),
              tidefin(dx=-1, tail=-50, fin=2, lean=1),
              with_drops(tidefin(dx=4, tail=40, fin=0, mouth=True, leg=2, lean=-1), [(10, 22), (13, 18), (8, 26)]),
              with_drops(tidefin(dx=6, tail=80, fin=2, mouth=True, leg=-2), [(14, 14), (18, 12)]),
              tidefin(dx=5, tail=30, fin=1, mouth=True),
              tidefin(dx=1, tail=5, fin=0)]
    hit = [tidefin(dx=-2, eyes='hurt', fin=2, tail=-10), tidefin(dx=-1, eyes='hurt', fin=1)]
    death = [tidefin(eyes='hurt', dy=1, fin=2), tidefin(eyes='closed', dy=3, fin=0, tail=-20),
             dissolve(tidefin(eyes='closed', belly_up=True), 0.3, 4),
             dissolve(tidefin(eyes='closed', belly_up=True), 0.7, 5)]
    return [('idle', [with_drops(f, [(40, 40)]) if i == 2 else f for i, f in enumerate(idle)], 6, True),
            ('attack', attack, 12, False), ('hit', hit, 10, False), ('death', death, 8, False),
            ('special', special_from(idle[0], attack, (90, 200, 255)), 12, False)]


# ============================================================ BRAMBLE PUP
def pup_palettes(ancient=False):
    if not ancient:
        return dict(bark=Pal('#6e4a2e', '#936644', '#4c321f', '#2c1c10'),
                    bark_dark=Pal('#553822', '#6e4a2e', '#3a2616', '#20140b'),
                    leaf=Pal('#4f9a2c', '#7cc043', '#326a1c', '#1c3e0f'),
                    leaf2=Pal('#3f8a28', '#6aae3c', '#2a5e18'),
                    claw=Pal('#3e2a18', '#5a4028', '#2a1c10'),
                    eye=hexc('#9dff5a'), eye_glow=hexc('#e2ffb8'))
    return dict(bark=Pal('#4a3a36', '#6a5650', '#322624', '#1a1212'),
                bark_dark=Pal('#3a2c2a', '#4a3a36', '#261c1a', '#120c0b'),
                leaf=Pal('#c0501e', '#f08a34', '#8a3212', '#4a1a08'),
                leaf2=Pal('#9a3a1a', '#d06a2a', '#6a220e'),
                claw=Pal('#8c8a82', '#b8b6ac', '#62605a'),
                eye=hexc('#ffb02e'), eye_glow=hexc('#fff0b0'))


def pup(s=1.0, size=48, ancient=False, dx=0, dy=0, crouch=0, legs=0, tail=0, mouth=0,
        eyes='open', head_dy=0, stretch=0, fall=False):
    P = pup_palettes(ancient)
    cv = Canvas(size, size)
    base_x = size / 2 + dx
    ground = size - 5

    def T(x, y):
        return (base_x + x * s, ground + (y + dy) * s)

    def M():
        return cv.mask()

    body_y = -9 + crouch
    # tail (leaf covered) behind
    ta = math.radians(-40 + tail)
    t0 = T(-9, body_y - 1)
    t1 = (t0[0] - 7 * s * math.cos(ta), t0[1] + 7 * s * math.sin(ta) * -1)
    cv.part(M().line(t0[0], t0[1], t1[0], t1[1], max(2, int(3 * s))), P['bark_dark'])
    cv.part(M().ellipse(t1[0] - 1 * s, t1[1] - 1 * s, 3 * s, 2.2 * s), P['leaf'])
    # far legs (darker)
    for (lx, ph) in ((-6, legs), (6, -legs)):
        a = T(lx + 1, body_y + 2)
        b = T(lx + 1 + ph + stretch * (1 if lx > 0 else -1), -1)
        cv.part(M().line(a[0], a[1], b[0], b[1], max(2, int(3 * s))), P['bark_dark'])
    # body
    bc = T(0 + stretch * 0.5, body_y)
    cv.part(M().ellipse(bc[0], bc[1], (9 + stretch) * s, 5.5 * s), P['bark'])
    # bark plates on the back
    for i, px in enumerate((-5, -1, 3)):
        c = T(px + stretch * 0.5, body_y - 4)
        cv.part(M().ellipse(c[0], c[1], 2.2 * s, 1.5 * s), P['bark_dark'])
    if ancient:
        # stone thorn ridge along the spine and glowing old runes on the flank
        for i, px in enumerate((-7, -3, 1, 5)):
            b0 = T(px + stretch * 0.5 - 1.5, body_y - 4.5)
            b1 = T(px + stretch * 0.5 + 1.5, body_y - 4.5)
            tip = T(px + stretch * 0.5 - 0.5, body_y - 9 - (i % 2) * 1.5)
            cv.part(M().poly([b0, tip, b1]), Pal('#9c9a90', '#d0cec4', '#6a6860'))
        for (rx, ry) in ((-4, -9 + 1), (-1, -9 + 2), (2, -9 + 1), (-2, -9 + 3)):
            c = T(rx + stretch * 0.5, body_y + ry - body_y - 9 + 9 + 1)
            cv.dot(c[0], c[1], hexc('#9dff5a'))
            cv.dot(c[0] + 1, c[1], hexc('#e2ffb8'))
    # near legs with root-like claws
    for (lx, ph) in ((-5, -legs), (7, legs)):
        a = T(lx, body_y + 3)
        b = T(lx + ph + stretch * (1 if lx > 0 else -1), -1)
        cv.part(M().line(a[0], a[1], b[0], b[1], max(3, int(3 * s))), P['bark'])
        for k in (-1, 0, 1):
            c0 = (b[0] + k * s, b[1])
            cv.part(M().line(c0[0], c0[1], c0[0] + (k + 1) * s, c0[1] + 1 * s, 1), P['claw'], shade=False)
    # head
    hc = T(10 + stretch, body_y - 4 + head_dy)
    cv.part(M().ellipse(hc[0], hc[1], 4.5 * s, 4 * s), P['bark'])
    # snout / jaw
    sn = T(14 + stretch, body_y - 3 + head_dy)
    cv.part(M().ellipse(sn[0], sn[1], 3 * s, 2 * s), P['bark'])
    if mouth:
        jaw = T(13 + stretch, body_y - 1 + head_dy + mouth)
        cv.part(M().ellipse(jaw[0], jaw[1], 3 * s, 1.3 * s), P['bark_dark'])
        for k in range(3):
            tp = T(12 + stretch + k * 1.5, body_y - 1.5 + head_dy)
            cv.dot(tp[0], tp[1], (236, 228, 200, 255))
    # leaf mane around the neck
    mane_pts = [(6, -8), (4, -6), (5, -3), (7, -10), (9, -9), (3, -9), (6, -1)]
    for i, (mx, my) in enumerate(mane_pts):
        c = T(mx + stretch, body_y + my + 4 + head_dy * 0.5)
        cv.part(M().ellipse(c[0], c[1], 2.2 * s, 1.6 * s), P['leaf'] if i % 2 == 0 else P['leaf2'])
    # ear leaves
    e0 = T(9 + stretch, body_y - 8 + head_dy)
    cv.part(M().poly([e0, (e0[0] - 2 * s, e0[1] - 4 * s), (e0[0] + 2 * s, e0[1] - 1 * s)]), P['leaf'])
    if ancient:
        # stone horns + moss crown
        h0 = T(11 + stretch, body_y - 8 + head_dy)
        cv.part(M().poly([h0, (h0[0] + 3 * s, h0[1] - 5 * s), (h0[0] + 2.5 * s, h0[1] + 1 * s)]),
                Pal('#9c9a90', '#d0cec4', '#6a6860'))
    # glowing eye
    ec = T(12 + stretch, body_y - 5 + head_dy)
    if eyes == 'open':
        cv.dot(ec[0], ec[1], P['eye'])
        cv.dot(ec[0] + 1, ec[1], P['eye_glow'])
        if s > 1.2:
            cv.dot(ec[0], ec[1] + 1, P['eye'])
            cv.dot(ec[0] + 1, ec[1] + 1, P['eye'])
    elif eyes == 'hurt':
        cv.dot(ec[0], ec[1] - 1, (30, 20, 10, 255))
        cv.dot(ec[0] + 1, ec[1], (30, 20, 10, 255))
        cv.dot(ec[0], ec[1] + 1, (30, 20, 10, 255))
    else:
        cv.dot(ec[0], ec[1], (30, 20, 10, 255))
        cv.dot(ec[0] + 1, ec[1], (30, 20, 10, 255))
    cv.outline()
    img = cv.image()
    if fall:
        img = img.rotate(-90 if False else 180, expand=False)
        bb = img.getbbox()
        img = sink(img, (size - 4) - bb[3])
    return img


def pup_anims(ancient=False):
    s, size = (1.0, 48) if not ancient else (1.6, 64)
    k = dict(s=s, size=size, ancient=ancient)
    idle = [pup(**k), pup(tail=10, crouch=0.5, **k), pup(tail=20, head_dy=1, **k), pup(tail=8, **k)]
    attack = [pup(crouch=2, dx=-2, tail=25, eyes='open', **k),
              pup(crouch=3, dx=-3, tail=35, head_dy=1, **k),
              pup(dy=-3, dx=3, stretch=3, legs=3, mouth=1, tail=-10, **k),
              pup(dy=-1, dx=6, stretch=4, legs=-2, mouth=2, head_dy=1, **k),
              pup(dx=5, mouth=1, legs=1, **k),
              pup(dx=1, **k)]
    hit = [pup(dx=-2, eyes='hurt', head_dy=-1, crouch=1, **k), pup(dx=-1, eyes='hurt', **k)]
    death = [pup(eyes='hurt', crouch=2, **k), pup(eyes='closed', crouch=4, head_dy=3, legs=2, **k),
             dissolve(pup(eyes='closed', crouch=5, head_dy=4, legs=3, **k), 0.3, 7),
             dissolve(pup(eyes='closed', crouch=5, head_dy=4, legs=3, **k), 0.7, 8)]
    col = (255, 150, 50) if ancient else (140, 230, 90)
    anims = [('idle', idle, 5, True), ('attack', attack, 12, False), ('hit', hit, 10, False),
             ('death', death, 8, False), ('special', special_from(idle[0], attack, col), 12, False)]
    if ancient:
        # heavier boss idle: slow breathing with a pulsing rune glow
        anims[0] = ('idle', [idle[0], aura(idle[1], (140, 230, 90), 90), aura(idle[2], (180, 255, 120), 140),
                             aura(idle[3], (140, 230, 90), 90)], 4, True)
    return anims
