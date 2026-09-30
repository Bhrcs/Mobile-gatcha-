"""
Builds Kael's three battle sheets from the owner-supplied art tools/art_src/kael_tiers.png
(4 evolution tiers x 8 poses, transparent PNG, facing right).  Run: python3 tools/import_kael.py

Poses per row: 0 idle, 1 idle-breath, 2 wind-up, 3 slash (with arc), 4 follow-through, 5 ready, 6 hurt, 7 victory.
Frames are re-assembled into the game's animation rows (hit frames match hero_skills.json) and scaled 2/3 so the
body is ~128 px (drawn at x2 in battle; UI views use the sheet's ui_scale).
"""
import json
import os
from PIL import Image

SRC = os.path.join(os.path.dirname(__file__), 'art_src', 'kael_tiers.png')
OUT = os.path.join(os.path.dirname(__file__), '..', 'Content', 'assets', 'characters')
FORM_ROWS = {'kael_emberclaw': 0, 'kael_blazeheart': 1, 'kael_cinderlord': 3}   # tier row used for each form
BANDS = [(1, 226), (230, 445), (448, 667), (670, 884)]                        # y range of each tier in the source
# x crop of each pose and the x between its feet (the anchor); pose 3/4 share a strip, split at x=916
POSES = [(30, 220, 95.5), (256, 446, 322.5), (460, 630, 551), (660, 916, 740.5), (916, 1146, 983.5),
         (1170, 1368, 1237.5), (1410, 1600, 1487), (1604, 1742, 1673)]
CW, CH, FEET = 360, 234, 228            # source-scale frame, feet row
S = 2 / 3                               # -> 240 x 156 frames, feet on row 152 (= frame - 4, the game's anchor)
FW, FH = round(CW * S), round(CH * S)
ANIMS = [('idle', [0, 0, 1, 1], 4, True),
         ('attack', [5, 2, 3, 3, 4, 4, 5], 14, False),              # hits on frames 2 and 4
         ('hit', [6, 6, 5], 10, False),
         ('victory', [7, 7, 7, 7], 6, True),
         ('ko', [6, 'down'], 6, False),
         ('burst', [5, 2, 2, 3, 4, 3, 2, 3, 4, 3, 7], 12, False),   # hits on 3, 5, 7, 9
         ('guard', [5, 5, 5], 6, True)]


def pose(src, row, i):
    y0, y1 = BANDS[row]
    x0, x1, ax = POSES[i]
    part = src.crop((x0, y0, x1, y1 + 1))
    if i == 4:   # the previous pose's slash arc spills into this strip: clear it above the legs
        part.paste((0, 0, 0, 0), (0, 0, 940 - x0, (y1 - y0) - 60))
    if i == 3:   # ...and the next pose's back foot pokes into this one
        part.paste((0, 0, 0, 0), (906 - x0, (y1 - y0) - 30, x1 - x0, y1 - y0 + 1))
    fr = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    fr.alpha_composite(part, (round(CW / 2 - (ax - x0)), FEET - (y1 - y0)))
    return fr


def down(fr):
    """Hurt pose tipped over onto its back, lying on the ground line."""
    r = fr.rotate(90, expand=True)
    bb = r.getbbox()
    c = r.crop(bb)
    out = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    out.alpha_composite(c, (CW // 2 - c.width // 2, FEET - c.height))
    return out


def main():
    src = Image.open(SRC).convert('RGBA')
    for fid, row in FORM_ROWS.items():
        poses = [pose(src, row, i) for i in range(len(POSES))]
        poses_by = {i: p for i, p in enumerate(poses)}
        poses_by['down'] = down(poses[6])
        cols = max(len(f) for _, f, _, _ in ANIMS)
        sheet = Image.new('RGBA', (cols * FW, len(ANIMS) * FH), (0, 0, 0, 0))
        meta = {'frame_size': [FW, FH], 'ui_scale': 0.25, 'source': 'tools/art_src/kael_tiers.png', 'animations': {}}
        for r, (name, frames, fps, loop) in enumerate(ANIMS):
            for c, k in enumerate(frames):
                sheet.alpha_composite(poses_by[k].convert('RGBa').resize((FW, FH), Image.LANCZOS).convert('RGBA'), (c * FW, r * FH))
            meta['animations'][name] = {'row': r, 'frames': len(frames), 'fps': fps, 'loop': loop}
        d = os.path.join(OUT, fid)
        os.makedirs(d, exist_ok=True)
        sheet.save(os.path.join(d, fid + '_sheet.png'))
        with open(os.path.join(d, fid + '_sheet.json'), 'w') as f:
            json.dump(meta, f, indent=1)
        print(fid, sheet.size)


if __name__ == '__main__':
    main()
