"""
Humanoid rig used to pose the three starter heroes.

All heroes are drawn facing RIGHT on a 48x48 canvas with the feet resting on
row 43. The game flips player units horizontally so they face the enemies.
"""
import math
from pixlib import Canvas, Pal, hexc

W = H = 48
GROUND = 43


def ik(p0, p1, l1, l2, bend=1):
    """Two-bone IK. Returns the joint position between p0 and p1.
    bend=+1 pushes the joint to the right-hand side of the p0->p1 vector."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    d = math.hypot(dx, dy)
    if d < 0.001:
        return (p0[0], p0[1] + l1)
    d = min(d, l1 + l2 - 0.01)
    a = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    hgt = math.sqrt(max(l1 * l1 - a * a, 0))
    ux, uy = dx / math.hypot(dx, dy), dy / math.hypot(dx, dy)
    mx, my = p0[0] + ux * a, p0[1] + uy * a
    # perpendicular (rotate u by -90 for "right" side in screen space)
    px, py = -uy * bend, ux * bend
    return (mx + px * hgt, my + py * hgt)


class Pose:
    """Pose description. Everything is relative to the default stance."""

    def __init__(self, **kw):
        self.ox = 0            # whole-body offset
        self.oy = 0
        self.crouch = 0        # hips drop by this many pixels
        self.lean = 1          # shoulder x offset from hip (forward = +)
        self.f_foot = (29, GROUND)
        self.b_foot = (19, GROUND)
        self.f_hand = None     # absolute hand positions; None = rest
        self.b_hand = None
        self.head_dx = 0
        self.head_dy = 0
        self.eyes = 'open'     # open | closed | hurt | fierce | ko
        self.weapon = -35      # weapon angle in degrees (0 = right, -90 = up)
        self.extra = {}        # character specific flags
        for k, v in kw.items():
            setattr(self, k, v)


def skeleton(p):
    hip = (24 + p.ox, 34 + p.oy + p.crouch)
    sh = (hip[0] + p.lean, hip[1] - 8)
    head = (sh[0] + 1 + p.head_dx, sh[1] - 5 + p.head_dy)
    f_sh = (sh[0] + 2, sh[1] + 1)
    b_sh = (sh[0] - 2, sh[1] + 1)
    f_hand = p.f_hand if p.f_hand else (f_sh[0] + 3, f_sh[1] + 6)
    b_hand = p.b_hand if p.b_hand else (b_sh[0] - 1, b_sh[1] + 7)
    f_foot = (p.f_foot[0] + p.ox, p.f_foot[1] + min(p.oy, 0))
    b_foot = (p.b_foot[0] + p.ox, p.b_foot[1] + min(p.oy, 0))
    return dict(hip=hip, sh=sh, head=head, f_sh=f_sh, b_sh=b_sh,
                f_hand=f_hand, b_hand=b_hand, f_foot=f_foot, b_foot=b_foot)


def draw_leg(cv, hip, foot, trouser, boot, knee_bend=1, boot_len=3):
    knee = ik(hip, (foot[0], foot[1] - 1), 5.5, 5.5, bend=-knee_bend)
    m = cv.mask().line(hip[0], hip[1], knee[0], knee[1], 3).line(knee[0], knee[1], foot[0], foot[1] - 2, 3)
    cv.part(m, trouser)
    b = cv.mask().rect(foot[0] - 1, foot[1] - 2, foot[0] + boot_len - 1, foot[1])
    b.line(knee[0] * 0.3 + foot[0] * 0.7, knee[1] * 0.3 + foot[1] * 0.7, foot[0], foot[1] - 1, 3)
    cv.part(b, boot)
    return knee


def draw_arm(cv, shoulder, hand, sleeve, skin, bend=1, width=3, glove=None):
    elbow = ik(shoulder, hand, 4.2, 4.2, bend=bend)
    m = cv.mask().line(shoulder[0], shoulder[1], elbow[0], elbow[1], width)
    m.line(elbow[0], elbow[1], hand[0], hand[1], max(width - 1, 2))
    cv.part(m, sleeve)
    hm = cv.mask().rect(hand[0] - 1, hand[1] - 1, hand[0], hand[1])
    cv.part(hm, glove or skin)
    return elbow


def draw_head(cv, c, skin, hair_fn, eyes='open', eye_col=(40, 26, 30, 255), facing=1):
    cx, cy = c
    face = cv.mask().ellipse(cx, cy, 4.2, 4.0)
    cv.part(face, skin)
    hair_fn(cv, cx, cy)
    # eye (single visible eye for a 3/4 side view)
    ex, ey = int(round(cx + 2)), int(round(cy + 1))
    if eyes == 'open' or eyes == 'fierce':
        cv.dot(ex, ey, eye_col)
        cv.dot(ex, ey - 1, eye_col)
        cv.dot(ex - 1, ey - 1, (250, 246, 240, 255))
        if eyes == 'fierce':
            cv.dot(ex - 1, ey - 2, eye_col)
            cv.dot(ex, ey - 2, eye_col)
    elif eyes == 'closed':
        cv.dot(ex, ey, eye_col)
        cv.dot(ex - 1, ey, eye_col)
    elif eyes == 'hurt':
        cv.dot(ex, ey - 1, eye_col)
        cv.dot(ex - 1, ey, eye_col)
        cv.dot(ex + 1, ey, eye_col)
    elif eyes == 'ko':
        cv.dot(ex - 1, ey - 1, eye_col)
        cv.dot(ex + 1, ey + 1, eye_col)
        cv.dot(ex + 1, ey - 1, eye_col)
        cv.dot(ex - 1, ey + 1, eye_col)
        cv.dot(ex, ey, eye_col)
    # mouth hint
    if eyes in ('fierce', 'hurt'):
        cv.dot(cx + 3, cy + 3, darken_px(skin.sh))


def darken_px(c):
    return (max(c[0] - 60, 0), max(c[1] - 60, 0), max(c[2] - 50, 0), 255)


def blade(cv, hand, angle, length, core, edge, hilt, guard, width=3, grip=2, guard_w=2):
    """Straight blade from the hand along angle (degrees)."""
    a = math.radians(angle)
    ux, uy = math.cos(a), math.sin(a)
    px, py = -uy, ux
    hx, hy = hand
    # grip behind the hand
    g = cv.mask().line(hx - ux * grip, hy - uy * grip, hx, hy, 2)
    cv.part(g, hilt)
    # guard
    gx, gy = hx + ux * 1.2, hy + uy * 1.2
    gm = cv.mask().line(gx - px * guard_w, gy - py * guard_w, gx + px * guard_w, gy + py * guard_w, 2)
    cv.part(gm, guard)
    # blade body
    bx0, by0 = hx + ux * 2, hy + uy * 2
    bx1, by1 = hx + ux * length, hy + uy * length
    bm = cv.mask().line(bx0, by0, bx1 - ux, by1 - uy, width)
    cv.part(bm, core, separate=False)
    # ember edge along the leading side + tip
    em = cv.mask().line(bx0 + px * (width / 2.0 - 0.3), by0 + py * (width / 2.0 - 0.3),
                        bx1 + px * 0.2, by1 + py * 0.2, 1)
    em.set(bx1, by1)
    cv.part(em, edge, shade=False, separate=False)
    return (bx1, by1)


def lying(img):
    """Rotates a standing frame so the hero lies on their back (head behind)."""
    from PIL import Image
    r = img.rotate(90, expand=False)
    bbox = r.getbbox()
    out = Image.new('RGBA', img.size, (0, 0, 0, 0))
    if not bbox:
        return out
    crop = r.crop(bbox)
    x = 24 - crop.width // 2
    y = 44 - crop.height
    out.paste(crop, (x, y), crop)
    return out


def kneel_shift(img, dy):
    from PIL import Image
    out = Image.new('RGBA', img.size, (0, 0, 0, 0))
    out.paste(img, (0, dy), img)
    return out
