"""
Builds Kael's three battle sheets from the owner-supplied art tools/art_src/kael_tiers.png
(4 evolution tiers x 8 poses, transparent PNG, facing right like every hero sheet - the game flips heroes so they
face the enemies).  Run: python3 tools/import_kael.py

Source poses per row: 0 idle, 1 idle-2, 2 wind-up, 3 slash (arc), 4 follow-through, 5 ready, 6 hurt, 7 victory.
Missing in-betweens (breathing, recoil, crouch/guard, kneel, fall, Burst glow, lunges) are derived from those poses.
Frames are scaled 2/3 (body ~128 px, drawn x2 in battle; UI views use the sheet's ui_scale). Hit frames match
hero_skills.json (attack 2/4, Burst 3/5/7/9).
"""
import json
import os
import numpy as np
from PIL import Image, ImageFilter

SRC = os.path.join(os.path.dirname(__file__), 'art_src', 'kael_tiers.png')
OUT = os.path.join(os.path.dirname(__file__), '..', 'Content', 'assets', 'characters')
FORM_ROWS = {'kael_emberclaw': 0, 'kael_blazeheart': 1, 'kael_cinderlord': 3}   # tier row used for each form
CW, CH, FEET = 360, 234, 228            # source-scale frame, feet row
S = 2 / 3                               # -> 240 x 156 frames, feet on row 152 (= frame - 4, the game's anchor)
FW, FH = round(CW * S), round(CH * S)


def runs(mask, gap):
    xs = np.nonzero(mask)[0]
    out, s, p = [], xs[0], xs[0]
    for x in xs[1:]:
        if x > p + gap:
            out.append((s, p))
            s = x
        p = x
    return out + [(s, p)]


def cut(src):
    """-> rows of 8 frames, each pose placed with the midpoint between its feet at (CW/2, FEET)."""
    a = np.array(src)[..., 3] > 40
    rows = []
    for y0, y1 in runs(a.any(1), 3):
        poses = []
        for x0, x1 in runs(a[y0:y1 + 1].any(0), 2):
            feet = runs(a[y1 - 4:y1 + 1, x0:x1 + 1].any(0), 3)
            ax = x0 + (feet[0][0] + feet[-1][1]) / 2
            fr = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
            fr.alpha_composite(src.crop((x0, y0, x1 + 1, y1 + 1)), (round(CW / 2 - (ax - x0)), FEET - (y1 - y0)))
            poses.append(fr)
        rows.append(poses)
    return rows


# ---- derived frames
def shift(fr, dx=0, dy=0):
    out = Image.new('RGBA', fr.size, (0, 0, 0, 0))
    out.alpha_composite(fr, (dx, dy))
    return out


def breathe(fr, d=2, waist=110):
    """Upper body dips d px, feet stay planted."""
    out = fr.copy()
    top = fr.crop((0, 0, CW, FEET - waist))
    out.paste((0, 0, 0, 0), (0, 0, CW, FEET - waist + d))
    out.alpha_composite(top, (0, d))
    return out


def squash(fr, k):
    """Crouch: compress vertically towards the feet."""
    h = round(CH * k)
    s = fr.resize((CW, h), Image.LANCZOS)
    out = Image.new('RGBA', fr.size, (0, 0, 0, 0))
    out.alpha_composite(s, (0, round(FEET - FEET * k)))
    return out


def glow(fr, color=(255, 138, 42), strength=0.75):
    """Burst aura: soft fire glow behind the sprite."""
    al = fr.getchannel('A').filter(ImageFilter.MaxFilter(9)).filter(ImageFilter.GaussianBlur(6))
    g = Image.new('RGBA', fr.size, color + (0,))
    g.putalpha(al.point(lambda v: int(v * strength)))
    g.alpha_composite(fr)
    return g


def down(fr):
    """Hurt pose tipped onto its back, lying on the ground line."""
    r = fr.rotate(90, expand=True)
    c = r.crop(r.getbbox())
    out = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    out.alpha_composite(c, (CW // 2 - c.width // 2 - 20, FEET - c.height))
    return out


def anims(p):
    idle0, idle1, wind, slash, follow, ready, hurt, win = p
    return [('idle', [idle0, breathe(idle0), idle1, breathe(idle1)], 5, True),
            ('attack', [ready, wind, slash, shift(slash, 6), follow, shift(follow, 4), ready], 14, False),
            ('hit', [shift(hurt, -12), shift(hurt, -6), shift(ready, -2)], 10, False),
            ('victory', [win, breathe(win), win, breathe(win)], 6, True),
            ('ko', [squash(hurt, 0.8), down(idle0)], 6, False),
            ('burst', [ready, glow(squash(ready, 0.94)), glow(wind), glow(slash), glow(follow), glow(shift(slash, 8)),
                       glow(wind), glow(shift(slash, 8)), glow(follow), glow(shift(slash, 12)), glow(win)], 12, False),
            ('guard', [squash(ready, 0.95), breathe(squash(ready, 0.95), 2), squash(ready, 0.95)], 6, True)]


def main():
    rows = cut(Image.open(SRC).convert('RGBA'))
    for fid, r in FORM_ROWS.items():
        an = anims(rows[r])
        cols = max(len(f) for _, f, _, _ in an)
        sheet = Image.new('RGBA', (cols * FW, len(an) * FH), (0, 0, 0, 0))
        meta = {'frame_size': [FW, FH], 'ui_scale': 0.25, 'source': 'tools/art_src/kael_tiers.png', 'animations': {}}
        for ri, (name, frames, fps, loop) in enumerate(an):
            for ci, fr in enumerate(frames):
                sheet.alpha_composite(fr.convert('RGBa').resize((FW, FH), Image.LANCZOS).convert('RGBA'), (ci * FW, ri * FH))
            meta['animations'][name] = {'row': ri, 'frames': len(frames), 'fps': fps, 'loop': loop}
        d = os.path.join(OUT, fid)
        os.makedirs(d, exist_ok=True)
        sheet.save(os.path.join(d, fid + '_sheet.png'))
        with open(os.path.join(d, fid + '_sheet.json'), 'w') as f:
            json.dump(meta, f, indent=1)
        print(fid, sheet.size)


if __name__ == '__main__':
    main()
