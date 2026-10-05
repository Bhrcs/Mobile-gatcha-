"""
Cinderbound hero sprites - one shared chibi rig for every hero (owner's sheets in tools/art_src/ were the baseline).
Run: python3 tools/hero_art.py   (writes Content/assets/characters/<form>/<form>_sheet.png|json + _portrait.png)

Same technical design for everyone: 64x64 native canvas drawn at x4 (256 px frames), feet on native row 62,
31 px head-to-feet, identical skeleton, poses, frame counts and timings. Heroes differ only by palette, hair,
outfit (armour / robe), what they hold (sword / staff / shield) and their element effects.
Timings (hero_skills.json): attack hits on frames 2 and 4 (staff releases on 2), Burst hits 3/5/7/9,
self-Bursts release on 4 (shield) or 6 (staff).
"""
import json
import math
import os
import numpy as np
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import ik  # noqa: E402
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(__file__), '..', 'Content', 'assets', 'characters')
L, U, K = 64, 2, 2                # layout grid (rig coordinates), detail factor, display scale
N = L * U                         # native canvas 128 px: shapes are laid out on the 64 grid, shaded/detailed at 128
CX, FEET = 30, 62                 # body centre x, feet row (layout units)
LINE = (26, 14, 22, 255)


def hx(s):
    s = s.lstrip('#')
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) + (255,)


def ramp(*c):
    return [hx(x) for x in c]   # dark, mid, light (+ optional highlight)


SKIN = ramp('#b8684a', '#f2b48a', '#ffdcb8')
EYE, WHITE = hx('#1a1020'), hx('#ffffff')

# ------------------------------------------------------------------ heads traced from the owner's sheets
# per form: (x0, top, x1, chin, face_x) in the idle cell of tools/art_src/<form>.png (import_heroes.cells)
HEAD_BOX = {'kael_emberclaw': (108, 90, 173, 148, 150), 'kael_blazeheart': (118, 93, 177, 151, 152),
            'kael_cinderlord': (118, 88, 179, 149, 152), 'mira_tidesong': (88, 105, 166, 153, 145),
            'mira_tidecaller': (91, 108, 168, 156, 148), 'mira_wavesage': (89, 104, 171, 153, 150),
            'thorne_mossguard': (106, 89, 166, 151, 148), 'thorne_oakwarden': (113, 92, 167, 151, 150),
            'thorne_ancientroot': (113, 83, 169, 149, 150)}
_heads = {}


def head_img(form):
    """-> (image, face_x) : the form's own head from the owner's idle frame at half size, colours quantised."""
    if form not in _heads:
        import import_heroes as H
        cell = H.cells(os.path.join(os.path.dirname(__file__), 'art_src', form + '.png'))[0][0]
        x0, y0, x1, y1, fx = HEAD_BOX[form]
        im = cell.crop((x0, y0, x1 + 1, y1 + 1))
        im = im.convert('RGBa').resize(((x1 - x0 + 1) // 2, (y1 - y0 + 1) // 2), Image.LANCZOS).convert('RGBA')
        a = np.array(im)
        a[..., 3] = np.where(a[..., 3] >= 140, 255, 0)
        rgb = np.array(Image.fromarray(a[..., :3]).quantize(24, method=Image.Quantize.MEDIANCUT).convert('RGB'))
        alpha = a[..., 3].copy()
        cx = int((fx - x0) / 2)
        alpha[-5:, :max(0, cx - 8)] = 0          # collar / pauldron bits below the jaw belong to the old body
        alpha[-5:, cx + 8:] = 0
        _heads[form] = (Image.fromarray(np.dstack([rgb, alpha]).astype(np.uint8), 'RGBA'), (fx - x0) / 2)
    return _heads[form]


# ------------------------------------------------------------------ heroes
HEROES = {
    'kael': dict(item='sword', outfit='armour', element='fire', forms={
        'kael_emberclaw': dict(hair=ramp('#7a1010', '#d0301c', '#ff7a3a'), cloth=ramp('#5a0e12', '#a81c18', '#e04a2a'),
                               trim=ramp('#7a4a10', '#d09a28', '#ffe070'), metal=ramp('#4a5060', '#a8b0c0', '#f0f4ff'), tier=3),
        'kael_blazeheart': dict(hair=ramp('#8a1408', '#e0401a', '#ff9a40'), cloth=ramp('#6a1010', '#c42418', '#ff6a30'),
                                trim=ramp('#8a5a10', '#e0aa30', '#fff090'), metal=ramp('#a83a10', '#ff9a2a', '#ffe070'), tier=4),
        'kael_cinderlord': dict(hair=ramp('#9a1c08', '#ff5a1a', '#ffc050'), cloth=ramp('#3a0c10', '#8a1418', '#d8401c'),
                                trim=ramp('#9a6a10', '#ffc040', '#fff8b0'), metal=ramp('#c84a10', '#ffb030', '#fff4a0'), tier=5)}),
    'mira': dict(item='staff', outfit='robe', element='water', forms={
        'mira_tidesong': dict(hair=ramp('#0e1a6a', '#1a40d0', '#4a88ff'), cloth=ramp('#7a90c0', '#d8e4f8', '#ffffff'),
                              trim=ramp('#10248a', '#2a5ae0', '#6aa0ff'), metal=ramp('#1a6ad8', '#4ac8ff', '#d8f8ff'), tier=3),
        'mira_tidecaller': dict(hair=ramp('#0e1a7a', '#1a48e0', '#5a98ff'), cloth=ramp('#6a88c8', '#d0e0fa', '#ffffff'),
                                trim=ramp('#0a2a9a', '#2a68f0', '#8ac0ff'), metal=ramp('#1a7ae0', '#5ad8ff', '#e8ffff'), tier=4),
        'mira_wavesage': dict(hair=ramp('#0a1680', '#1a50f0', '#6aa8ff'), cloth=ramp('#5a7ad0', '#c8dcff', '#ffffff'),
                              trim=ramp('#a07a20', '#e8c050', '#fff4b0'), metal=ramp('#2a8af0', '#6ae8ff', '#ffffff'), tier=5)}),
    'thorne': dict(item='shield', outfit='armour', element='nature', forms={
        'thorne_mossguard': dict(hair=ramp('#0a2410', '#1a5224', '#348a3a'), cloth=ramp('#2a3a10', '#5a7a1c', '#9ab838'),
                                 trim=ramp('#3a2010', '#7a4a20', '#b07a40'), metal=ramp('#5a6070', '#c0c8d4', '#ffffff'), tier=3),
        'thorne_oakwarden': dict(hair=ramp('#0a2a12', '#1a5e28', '#3a9a40'), cloth=ramp('#24400e', '#4a8a1a', '#8acc3a'),
                                 trim=ramp('#5a4010', '#b0882a', '#f0d060'), metal=ramp('#606878', '#ccd2de', '#ffffff'), tier=4),
        'thorne_ancientroot': dict(hair=ramp('#24400e', '#4a8a1a', '#8acc3a'), cloth=ramp('#1e3a0c', '#3e7a18', '#7ac034'),
                                   trim=ramp('#7a5a10', '#d8b030', '#fff090'), metal=ramp('#7a8090', '#dde2ea', '#ffffff'), tier=5)}),
}
GEM = {'fire': ramp('#a01a0a', '#ff6a1a', '#ffe070'), 'water': ramp('#0a40a0', '#3ac0ff', '#e0ffff'),
       'nature': ramp('#0a6a2a', '#2ae05a', '#d0ffd8')}
FX = {'fire': [hx('#c42a0e'), hx('#ff8a1e'), hx('#ffe070'), hx('#fffad0')],
      'water': [hx('#1a4ad0'), hx('#3ab0ff'), hx('#a8f0ff'), hx('#ffffff')],
      'nature': [hx('#6a3a14'), hx('#a8702a'), hx('#2ae05a'), hx('#d0ffd8')]}


# ------------------------------------------------------------------ drawing
class SD:
    """ImageDraw that takes layout coordinates (x U)."""
    def __init__(self, d):
        self.d = d

    def _p(self, pts):
        return [(x * U + U / 2, y * U + U / 2) for x, y in pts]

    def polygon(self, pts, fill=255):  # noqa
        self.d.polygon(self._p(pts), fill=fill)

    def line(self, pts, fill=255, width=1):
        self.d.line(self._p(pts), fill=fill, width=int(width * U))

    def ellipse(self, box, fill=255):  # noqa
        x0, y0, x1, y1 = box
        self.d.ellipse([x0 * U + U / 2, y0 * U + U / 2, x1 * U + U / 2, y1 * U + U / 2], fill=fill)

    def rectangle(self, box, fill=255):  # noqa
        x0, y0, x1, y1 = box
        self.d.rectangle([x0 * U, y0 * U, x1 * U + U - 1, y1 * U + U - 1], fill=fill)


class Canvas:
    def __init__(self):
        self.img = np.zeros((N, N, 4), np.uint8)
        self.solid = np.zeros((N, N), bool)

    def part(self, draw_fn, rmp, shade=True):
        m = Image.new('L', (N, N), 0)
        draw_fn(SD(ImageDraw.Draw(m)))
        mask = np.array(m) > 0
        if not mask.any():
            return
        col = np.zeros((N, N, 4), np.uint8)
        col[mask] = rmp[1]
        if shade:   # form shading, light from the upper left: shadow side, mid, lit band, specular glint
            def sh(m, dx, dy, k):
                o = m.copy()
                for i in range(1, k + 1):
                    o &= np.roll(np.roll(m, i * dy, 0), i * dx, 1)
                return o
            dark = mask & ~sh(mask, -1, -1, 2)            # 2 px shadow on the bottom-right
            core = mask & ~sh(mask, -1, -1, 1)
            lite = mask & ~sh(mask, 1, 1, 3) & ~core      # 3 px lit band on the top-left
            col[lite] = rmp[2]
            col[dark & ~lite] = rmp[0]
            if len(rmp) > 3 or shade == 'metal':
                spec = lite & sh(mask, 1, 1, 1) & ~sh(mask, 1, 1, 2)
                ys, xs = np.nonzero(spec)
                if len(ys):   # one small glint near the top-left
                    k = np.argmin(ys + xs)
                    col[ys[k]:ys[k] + 2, xs[k]:xs[k] + 2] = (255, 248, 230, 255)
        self.img[mask] = col[mask]
        self.solid |= mask

    def stamp(self, rows, x0, y0, pal, u=U):
        """Character map: layout units (u=U, x0/y0 in layout units) or native pixels (u=1, x0/y0 native)."""
        bx, by = (x0 * U, y0 * U) if u == U else (x0, y0)
        for y, r in enumerate(rows):
            for x, ch in enumerate(r):
                if ch in pal:
                    Y, X = int(by + y * u), int(bx + x * u)
                    self.img[max(Y, 0):Y + u, max(X, 0):X + u] = pal[ch]
                    self.solid[max(Y, 0):Y + u, max(X, 0):X + u] = True

    def hair(self, rows, x0, y0, rmp):
        """Hair map ('#' mid, '+' light, '-' dark) at U x, then rim-shaded like a part."""
        m = np.zeros((N, N), bool)
        tone = np.zeros((N, N), np.int8)
        for y, r in enumerate(rows):
            for x, ch in enumerate(r):
                if ch in '#+-':
                    Y, X = (y0 + y) * U, (x0 + x) * U
                    m[Y:Y + U, X:X + U] = True
                    tone[Y:Y + U, X:X + U] = {'#': 1, '+': 2, '-': 0}[ch]
        dark = m & ~(np.roll(m, -1, 1) & np.roll(m, -1, 0))
        tone[dark] = 0
        lite = m & ~(np.roll(m, 1, 1) & np.roll(m, 1, 0)) & ~dark
        tone[lite & (tone == 1)] = 2
        ys, xs = np.nonzero(m)
        for y, x in zip(ys, xs):
            self.img[y, x] = rmp[tone[y, x]]
        self.solid |= m

    def px(self, x, y, c, size=U):
        x, y = int(round(x * U)), int(round(y * U))
        for dy in range(size):
            for dx in range(size):
                if 0 <= x + dx < N and 0 <= y + dy < N:
                    self.img[y + dy, x + dx] = c
                    self.solid[y + dy, x + dx] = True

    def outlined(self):
        s = self.solid
        ring = np.zeros_like(s)
        ring[1:] |= s[:-1]; ring[:-1] |= s[1:]; ring[:, 1:] |= s[:, :-1]; ring[:, :-1] |= s[:, 1:]
        ring &= ~s
        out = self.img.copy()
        out[ring] = LINE
        return Image.fromarray(out, 'RGBA')


def limb(d, a, b, w):
    d.line([a, b], fill=255, width=w)
    r = w / 2 - 0.5
    for p in (a, b):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=255)


def polar(o, deg, length):
    """deg: 0 = straight down, 90 = forward (right), 180 = up."""
    a = math.radians(deg)
    return (o[0] + math.sin(a) * length, o[1] + math.cos(a) * length)


# ------------------------------------------------------------------ one frame
DARKCLOTH = ramp('#24161e', '#3e2a36', '#5a4250')
BROWN = ramp('#3a1e10', '#6e3e1c', '#a06830')


def taper(d, a, b, w0, w1):
    """Limb segment: thick at the joint it grows from (a), thinner towards b, rounded ends."""
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    nx, ny = -math.sin(ang), math.cos(ang)
    d.polygon([(a[0] + nx * w0 / 2, a[1] + ny * w0 / 2), (b[0] + nx * w1 / 2, b[1] + ny * w1 / 2),
               (b[0] - nx * w1 / 2, b[1] - ny * w1 / 2), (a[0] - nx * w0 / 2, a[1] - ny * w0 / 2)])
    for (x, y), w in ((a, w0), (b, w1)):
        d.ellipse([x - w / 2 + 0.3, y - w / 2 + 0.3, x + w / 2 - 0.3, y + w / 2 - 0.3])


# chibi skeleton (layout units, 1 = 2 native px): big head, real torso/limbs underneath it
LEG_UP, LEG_LO, ARM_UP, ARM_LO = 5.2, 5.0, 4.0, 3.6
PELVIS_Y, TORSO = FEET - 9.6, 6.6          # hip joint height above the ground, hip -> shoulder line


def skeleton(p):
    bx, by = p.get('bx', 0), p.get('by', 0) + p.get('crouch', 0)
    lean, sp = p.get('lean', 0), p.get('spread', 0)
    pelvis = (CX + bx, PELVIS_Y + by)
    chest = (pelvis[0] + lean, pelvis[1] - TORSO)
    J = dict(pelvis=pelvis, chest=chest, neck=(chest[0] + 0.5, chest[1] - 1))
    J['fsh'], J['bsh'] = (chest[0] + 3.2, chest[1] + 0.8), (chest[0] - 3.2, chest[1] + 0.8)
    for side, foot_x in (('f', CX + bx + 3.2 + sp), ('b', CX + bx - 3.2 - sp)):
        hj = (pelvis[0] + (1.4 if side == 'f' else -1.4), pelvis[1])
        ankle = (foot_x, FEET - 1.2)
        J[side + 'hip'], J[side + 'ankle'] = hj, ankle
        J[side + 'knee'] = ik(hj, ankle, LEG_UP, LEG_LO, bend=-1)          # knees bend forward
    for side, ang in (('f', p.get('fa', 30)), ('b', p.get('ba', -20))):
        sh = J[side + 'sh']
        hand = polar(sh, ang, (ARM_UP + ARM_LO) * 0.92)
        J[side + 'hand'] = hand
        J[side + 'elbow'] = ik(sh, hand, ARM_UP, ARM_LO, bend=1 if side == 'f' else 1)   # elbows bend back/down
    return J


def draw(hero, form, p):
    H, f = HEROES[hero], HEROES[hero]['forms'][form]
    c = Canvas()
    el, tier, item = H['element'], f['tier'], H['item']
    robe = H['outfit'] == 'robe'
    sway = p.get('sway', 0)
    J = skeleton(p)
    hip, neck, chest = J['pelvis'], J['neck'], J['chest']
    fsh, bsh, fhand, bhand = J['fsh'], J['bsh'], J['fhand'], J['bhand']
    boots = BROWN if hero == 'thorne' else (f['trim'] if robe else f['cloth'])
    if p.get('aura') or tier == 5:   # 5* forms always glow a little
        aura(c, el, hip, max(p.get('aura', 0), 1 if tier == 5 else 0), p.get('t', 0))
    if hero == 'mira':   # long hair down the back, ends at the waist
        c.part(lambda d: d.polygon([(neck[0] - 1, neck[1] - 5), (neck[0] + 1, neck[1] - 2), (chest[0] - 1, hip[1] - 1),
                                    (chest[0] - 4 - sway, hip[1] + 1), (chest[0] - 7 - sway, hip[1] - 1), (neck[0] - 6, neck[1] - 1)]),
               f['hair'])
    if tier >= 4 and not robe:   # short cape behind the back
        c.part(lambda d: d.polygon([(neck[0] - 3, neck[1] + 1), (neck[0] + 1, neck[1] + 1), (hip[0] - 1 - sway, FEET - 4),
                                    (hip[0] - 7 - sway, FEET - 5)]), f['cloth'])
    # back arm (behind the body)
    sleeve = f['cloth'] if robe else f['cloth']
    c.part(lambda d: taper(d, bsh, J['belbow'], 2.8, 2.4), sleeve)
    c.part(lambda d: taper(d, J['belbow'], bhand, 2.4, 2.2), SKIN if robe else DARKCLOTH)
    c.part(lambda d: d.ellipse([bhand[0] - 1.3, bhand[1] - 1.3, bhand[0] + 1.3, bhand[1] + 1.3]), SKIN if robe else DARKCLOTH)
    # legs: thigh -> knee -> shin -> boot (back leg first)
    for side in ('b', 'f'):
        hj, kn, an = J[side + 'hip'], J[side + 'knee'], J[side + 'ankle']
        if not robe:
            c.part(lambda d, a=hj, b=kn: taper(d, a, b, 3.6, 2.8), DARKCLOTH)                    # thigh
            c.part(lambda d, a=kn, b=an: taper(d, a, b, 2.9, 2.4), f['cloth'])                   # greave
            c.part(lambda d, k=kn: d.ellipse([k[0] - 1.4, k[1] - 1.3, k[0] + 1.4, k[1] + 1.3]), f['trim'], shade='metal')
        c.part(lambda d, a=an: d.polygon([(a[0] - 1.4, a[1] - 1.6), (a[0] + 1.6, a[1] - 1.6), (a[0] + 3.4, FEET),
                                          (a[0] - 1.6, FEET)]), boots)                           # boot, toe forward
    # torso: shoulders > waist < hips, like a real ribcage + pelvis under the armour / robe
    sh_w, waist_w, hip_w = 5.0, 3.2, 3.6
    waist = (hip[0] + (chest[0] - hip[0]) * 0.35, hip[1] - TORSO * 0.35)
    if robe:
        c.part(lambda d: d.polygon([(chest[0] - sh_w + 0.6, chest[1]), (chest[0] + sh_w - 0.6, chest[1]), (waist[0] + waist_w, waist[1]),
                                    (hip[0] + 6.5, FEET - 0.5), (hip[0] - 7 - sway, FEET - 0.5), (waist[0] - waist_w, waist[1])]),
               f['cloth'])
        c.part(lambda d: d.polygon([(waist[0] - 0.6, waist[1]), (waist[0] + 1.2, waist[1]), (hip[0] + 3.5, FEET - 0.5),
                                    (hip[0] - 2.5, FEET - 0.5)]), f['trim'])                     # front panel
        c.part(lambda d: d.polygon([(hip[0] - 7 - sway, FEET - 2), (hip[0] + 6.5, FEET - 2), (hip[0] + 6.5, FEET - 0.5),
                                    (hip[0] - 7 - sway, FEET - 0.5)]), f['trim'], shade=False)    # hem
        c.part(lambda d: d.rectangle([waist[0] - waist_w, waist[1] - 0.6, waist[0] + waist_w, waist[1] + 0.4]), f['trim'], shade=False)
    else:
        c.part(lambda d: d.polygon([(chest[0] - sh_w, chest[1]), (chest[0] + sh_w, chest[1]), (waist[0] + waist_w, waist[1]),
                                    (hip[0] + hip_w, hip[1] + 0.8), (hip[0] - hip_w, hip[1] + 0.8), (waist[0] - waist_w, waist[1])]),
               f['cloth'])
        c.part(lambda d: d.polygon([(chest[0] - 2.4, chest[1] + 0.8), (chest[0] + 2.8, chest[1] + 0.8), (chest[0] + 2.2, chest[1] + 3.6),
                                    (chest[0] - 1.8, chest[1] + 3.6)]), f['cloth'], shade='metal')   # breastplate
        c.part(lambda d: d.rectangle([waist[0] - waist_w - 0.2, hip[1] - 1.6, waist[0] + waist_w + 0.4, hip[1] - 0.4]),
               BROWN if hero == 'thorne' else DARKCLOTH)                                          # belt
        c.part(lambda d: d.ellipse([hip[0] - 0.9, hip[1] - 1.9, hip[0] + 1.3, hip[1] - 0.1]), f['trim'], shade='metal')
        c.part(lambda d: d.polygon([(hip[0] - 0.6, hip[1] - 0.2), (hip[0] + 1.6, hip[1] - 0.2), (hip[0] + 1.2, hip[1] + 4.5),
                                    (hip[0] - 0.2, hip[1] + 4.5)]), f['trim'])                     # tabard
    # pauldrons (grow with each form)
    pr = 2.3 + (tier - 3) * 0.45
    pal = f['metal'] if robe else f['cloth']
    c.part(lambda d: d.ellipse([bsh[0] - pr - 0.4, bsh[1] - pr, bsh[0] + pr - 0.4, bsh[1] + pr]), pal, shade='metal')
    c.part(lambda d: d.ellipse([fsh[0] - pr, fsh[1] - pr, fsh[0] + pr, fsh[1] + pr]), pal, shade='metal')
    c.part(lambda d: d.rectangle([fsh[0] - pr, fsh[1] + pr - 0.8, fsh[0] + pr, fsh[1] + pr]), f['trim'], shade=False)
    # head
    img, fx = head_img(form)
    c.part(lambda d: taper(d, (neck[0], neck[1] + 1), (neck[0] + 0.3, neck[1] - 1.2), 2.2, 2.0), SKIN)   # neck
    hx0 = int(round((neck[0] + 0.8) * U - fx))
    hy0 = int(round((neck[1] + 0.6 + p.get('head_dy', 0)) * U - img.height))
    a = np.array(img)
    for yy in range(a.shape[0]):
        for xx in range(a.shape[1]):
            if a[yy, xx, 3] and 0 <= hy0 + yy < N and 0 <= hx0 + xx < N:
                c.img[hy0 + yy, hx0 + xx] = a[yy, xx]
                c.solid[hy0 + yy, hx0 + xx] = True
    # front arm + held item
    def front_arm():
        c.part(lambda d: taper(d, fsh, J['felbow'], 2.9, 2.5), f['cloth'])
        c.part(lambda d: taper(d, J['felbow'], fhand, 2.6, 2.3), SKIN if robe else DARKCLOTH)
        c.part(lambda d: d.ellipse([fhand[0] - 1.4, fhand[1] - 1.4, fhand[0] + 1.4, fhand[1] + 1.4]), SKIN if robe else DARKCLOTH)
    if p.get('no_item'):   # knocked out: the weapon has fallen
        front_arm()
    elif item == 'shield':
        front_arm()
        shield(c, f, el, fhand, p.get('item', 0))
    else:
        (sword if item == 'sword' else staff)(c, f, el, fhand, p.get('item', 60 if item == 'sword' else 180), tier)
        front_arm()
    if p.get('fx'):
        effect(c, el, p['fx'], fhand, p.get('t', 0))
    return c.outlined()


def sword(c, f, el, hand, ang, tier):
    tip = polar(hand, ang, 16)
    c.part(lambda d: d.polygon([polar(hand, ang + 8, 3), polar(hand, ang + 3, 14), tip, polar(hand, ang - 4, 14),
                                polar(hand, ang - 8, 3)]), f['metal'])
    c.part(lambda d: d.line([polar(hand, ang, 4), polar(hand, ang, 12)], width=0.5), [f['metal'][2]] * 3, shade=False)
    if tier >= 4:   # burning edge
        c.part(lambda d: d.line([polar(hand, ang - 5, 4), polar(hand, ang - 3, 14)], width=0.5), [FX[el][1], FX[el][2], FX[el][3]],
               shade=False)
    c.part(lambda d: limb(d, polar(hand, ang + 90, 3), polar(hand, ang - 90, 3), 2), f['trim'])
    c.part(lambda d: limb(d, hand, polar(hand, ang + 180, 3), 2), BROWN)


def staff(c, f, el, hand, ang, tier):
    top, bot = polar(hand, ang, 13), polar(hand, ang + 180, 10)
    c.part(lambda d: limb(d, bot, top, 2), BROWN)
    head = polar(hand, ang, 16)
    c.part(lambda d: d.polygon([(top[0] - 3, top[1]), (top[0] - 3, top[1] - 3), (top[0] - 1, top[1] - 1), (top[0] + 1, top[1] - 1),
                                (top[0] + 3, top[1] - 3), (top[0] + 3, top[1])]), f['trim'] if tier == 5 else ramp('#7a8090', '#d0d8e8', '#ffffff'))
    c.part(lambda d: d.polygon([(head[0], head[1] - 4), (head[0] + 2, head[1]), (head[0], head[1] + 2), (head[0] - 2, head[1])]),
           f['metal'])
    c.px(head[0] - 0.5, head[1] - 1.5, WHITE, size=1)


def shield(c, f, el, hand, tilt):
    x, y = hand[0] + 4 + tilt, hand[1] - 2
    pts = [(x, y - 9), (x + 5, y - 6), (x + 5, y + 6), (x, y + 10), (x - 4, y + 6), (x - 4, y - 6)]
    c.part(lambda d: d.polygon(pts), f['metal'])
    inner = [(x, y - 7), (x + 3, y - 5), (x + 3, y + 5), (x, y + 8), (x - 2, y + 5), (x - 2, y - 5)]
    c.part(lambda d: d.polygon(inner), ramp('#0a3a1a', '#11602a', '#1a8a3a'))
    c.part(lambda d: d.polygon([(x, y - 4), (x + 1.5, y), (x, y + 4), (x - 1.5, y)]), GEM[el], shade=False)
    c.px(x - 0.5, y - 1.5, GEM[el][2], size=1)
    for ry in (-7, 8):
        c.px(x, y + ry, f['trim'][1], size=1)


def aura(c, el, hip, k, t):
    col = FX[el]
    for i in range(8 + 4 * k):   # rising element motes
        a = i * 2.39996
        r = 8 + k * 2 + (i % 3) * 2
        x = hip[0] + math.cos(a) * r
        y = hip[1] + 6 - ((i * 5 + t * 3) % (18 + k * 4))
        c.px(x, y, col[1 + (i + t) % 3], size=2 if i % 3 else 1)


def effect(c, el, kind, hand, t):
    col = FX[el]
    x, y = hand

    def crescent(cx, cy, r, a0, a1, thick):
        m = Image.new('L', (N, N), 0)
        d = ImageDraw.Draw(m)
        steps = 24
        outer = [(cx + math.cos(math.radians(a0 + (a1 - a0) * i / steps)) * r,
                  cy + math.sin(math.radians(a0 + (a1 - a0) * i / steps)) * r) for i in range(steps + 1)]
        inner = [(cx + math.cos(math.radians(a0 + (a1 - a0) * i / steps)) * (r - thick * math.sin(math.pi * i / steps)),
                  cy + math.sin(math.radians(a0 + (a1 - a0) * i / steps)) * (r - thick * math.sin(math.pi * i / steps)))
                 for i in range(steps, -1, -1)]
        d.polygon([(px * U, py * U) for px, py in outer + inner], fill=255)
        mk = np.array(m) > 0
        yy, xx = np.nonzero(mk)
        for Y, X in zip(yy, xx):
            dist = r * U - math.hypot(X - cx * U, Y - cy * U)
            c.img[Y, X] = col[3] if dist < 2 else (col[2] if dist < thick * U * 0.45 else col[1])
            c.solid[Y, X] = True
    if kind == 'slash':   # first cut downward, second rising
        crescent(x - 2, y + 1, 14, -80, 80, 5) if t % 2 == 0 else crescent(x - 2, y - 2, 13, 100, -60, 5)
    elif kind == 'bolt':
        ox = x + 22 + (t % 2) * 4
        c.part(lambda d: d.polygon([(x + 6, y - 7), (ox, y - 9), (ox, y - 3), (x + 6, y - 5)]), [col[0], col[1], col[2]], shade=False)
        crescent(ox, y - 6, 5, 0, 360, 5)
        c.px(ox - 2, y - 8, col[3], size=2)
    elif kind == 'quake':
        for i in range(5):
            h = 5 + (i * 3 + t) % 6
            bx = x + 7 + i * 4
            c.part(lambda d, bx=bx, h=h: d.polygon([(bx - 2, FEET), (bx + 2, FEET), (bx + 0.5, FEET - h)]), BROWN)
            c.px(bx, FEET - h - 2, col[2], size=2)
    elif kind == 'nova':
        crescent(CX, FEET - 14, 17, 0, 360, 3)
        for i in range(10):
            a = i * 0.628 + t
            c.px(CX + math.cos(a) * 20, FEET - 14 + math.sin(a) * 16, col[3], size=2)
    elif kind == 'sparkle':
        for i in range(5):
            a = i * 1.25 + t
            sx, sy = x + math.cos(a) * 6, y - 5 + math.sin(a) * 6
            c.px(sx, sy, col[3], size=1); c.px(sx - 0.5, sy, col[2], size=1); c.px(sx + 0.5, sy, col[2], size=1)


# ------------------------------------------------------------------ animations (shared poses; item style per weapon)
def poses(item):
    ready = {'sword': dict(fa=40, item=60), 'staff': dict(fa=45, item=180), 'shield': dict(fa=60, item=0)}[item]
    up = {'sword': dict(fa=170, item=170), 'staff': dict(fa=150, item=180), 'shield': dict(fa=120, item=1)}[item]
    strike = {'sword': dict(fa=80, item=95), 'staff': dict(fa=95, item=160), 'shield': dict(fa=90, item=2, bx=3)}[item]
    low = {'sword': dict(fa=30, item=30), 'staff': dict(fa=70, item=150), 'shield': dict(fa=50, item=0, crouch=1)}[item]
    hit = {'sword': 'slash', 'staff': 'bolt', 'shield': 'quake'}[item]

    def P(*ds, **kw):
        o = {}
        for d in ds:
            o.update(d)
        o.update(kw)
        return o
    A = {
        'idle': [P(ready, sway=0), P(ready, sway=0, by=0), P(ready, by=1, sway=1, head_dy=0), P(ready, by=1, sway=1)],
        'attack': [P(ready), P(up, lean=-1, crouch=1), P(strike, lean=2, fx=hit, t=0), P(low, lean=2),
                   P(strike, lean=2, fx=hit, t=3), P(low, lean=1), P(ready)],
        'hit': [P(ready, bx=-3, lean=-2, face='hurt'), P(ready, bx=-2, lean=-1, face='hurt'), P(ready, bx=-1, face='hurt'), P(ready)],
        'victory': [P(up, face='closed', fx='sparkle', t=i) if i % 2 else P(up, by=1, fx='sparkle', t=i) for i in range(4)],
        'ko': [P(ready, face='hurt', crouch=2, lean=-1), P(low, face='hurt', crouch=4, lean=2), P(low, face='ko', crouch=5, lean=3),
               P(low, face='ko', crouch=6, lean=3)],
        'burst': [P(ready, aura=1, t=0), P(up, aura=2, t=1, crouch=1), P(up, aura=3, t=2, crouch=1),
                  P(strike, aura=2, fx=hit, t=3, lean=2), P(low, aura=2, fx='nova', t=4, lean=2),
                  P(strike, aura=2, fx=hit, t=5, lean=2), P(up, aura=3, fx='nova', t=6),
                  P(strike, aura=3, fx=hit, t=7, lean=2), P(up, aura=3, t=8, crouch=1),
                  P(strike, aura=3, fx='nova', t=9, lean=3), P(up, aura=1, t=10, face='closed')],
        'guard': [P(low, crouch=2, aura=1, t=0), P(low, crouch=2, aura=1, t=1, by=1), P(low, crouch=2, aura=1, t=2)],
    }
    return A


FPS = {'idle': (5, True), 'attack': (14, False), 'hit': (10, False), 'victory': (6, True), 'ko': (8, False),
       'burst': (12, False), 'guard': (6, True)}


def lying(img):
    """KO: the last kneel pose tipped onto the ground."""
    r = img.rotate(90, expand=False)
    bb = r.getbbox()
    c = r.crop(bb)
    out = Image.new('RGBA', (N, N), (0, 0, 0, 0))
    out.alpha_composite(c, (CX * U - c.width // 2 - 4 * U, FEET * U + U - c.height))
    return out


def build(hero, form):
    anims = poses(HEROES[hero]['item'])
    F = N * K
    cols = max(len(v) for v in anims.values()) + 2
    sheet = Image.new('RGBA', (cols * F, len(anims) * F), (0, 0, 0, 0))
    meta = {'frame_size': [F, F], 'layout_size': [200, 200], 'ui_scale': 0.25, 'source': 'tools/hero_art.py',
            'animations': {}}
    for ri, (name, ps) in enumerate(anims.items()):
        frames = [draw(hero, form, p) for p in ps]
        if name == 'ko':
            frames += [lying(draw(hero, form, dict(ps[0], face='ko', crouch=0, no_item=True, fa=10, ba=-10, aura=0)))] * 2
        for ci, im in enumerate(frames):
            sheet.alpha_composite(im.resize((F, F), Image.NEAREST), (ci * F, ri * F))
        fps, loop = FPS[name]
        meta['animations'][name] = {'row': ri, 'frames': len(frames), 'fps': fps, 'loop': loop}
    d = os.path.join(OUT, form)
    os.makedirs(d, exist_ok=True)
    sheet.save(os.path.join(d, form + '_sheet.png'))
    with open(os.path.join(d, form + '_sheet.json'), 'w') as fh:
        json.dump(meta, fh, indent=1)
    idle = sheet.crop((0, 0, F, F))
    c = idle.crop(idle.getbbox())
    s = max(c.size) + 16
    pr = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    pr.alpha_composite(c, ((s - c.width) // 2, s - c.height - 4))
    pr.save(os.path.join(d, form + '_portrait.png'))


if __name__ == '__main__':
    for hero, h in HEROES.items():
        for form in h['forms']:
            build(hero, form)
            print(form)
