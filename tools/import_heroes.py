"""
Imports the owner's 8x8 battle sheets (tools/art_src/<form_id>.png, black background, facing right) for Kael, Mira
and Thorne, and writes every hero's portrait as its first idle frame.  Run: python3 tools/import_heroes.py

Sheet rows: 0 idle/basic swing, 1 attack (projectile / shield bash), 2 skill, 3 Burst, 4 hit + stun, 5 poison/freeze,
6 KO, 7 victory. Frames are kept 1:1 (body ~128 px, drawn x2 in battle like Kael; UI uses ui_scale 0.25).
Animation frame picks keep the hit/release frames of hero_skills.json (attack 2/4 or release 2, Burst release 4/6).
"""
import json
import os
import numpy as np
from PIL import Image
from scipy import ndimage

ART = os.path.join(os.path.dirname(__file__), 'art_src')
OUT = os.path.join(os.path.dirname(__file__), '..', 'Content', 'assets', 'characters')
F = 160                                   # frame size; feet on row F - 4 (the game's anchor), body centred
ANIMS = {   # name: ([(row, col), ...], fps, loop)
    'kael': {'idle': ([(0, c) for c in (0, 1, 2, 3)], 5, True),
             'attack': ([(1, c) for c in (1, 2, 3, 4, 5, 6, 7)], 14, False),             # slashes on 2 and 4
             'hit': ([(4, c) for c in (0, 0, 3)], 10, False),
             'victory': ([(7, c) for c in (2, 3, 4, 5, 6, 7)], 6, True),
             'ko': ([(6, c) for c in range(8)], 10, False),
             'burst': ([(3, c) for c in (0, 1, 2, 3, 4, 3, 4, 5, 4, 5, 7)], 12, False),   # hits on 3/5/7/9
             'guard': ([(0, c) for c in (4, 5, 6)], 6, True)},
    'mira': {'idle': ([(0, c) for c in (0, 1, 2, 3)], 5, True),
             'attack': ([(1, c) for c in (1, 2, 3, 4, 5, 6, 7)], 12, False),            # bolt leaves on frame 2
             'hit': ([(4, c) for c in (0, 1, 2, 3)], 10, False),
             'victory': ([(7, c) for c in range(8)], 8, True),
             'ko': ([(6, c) for c in range(8)], 10, False),
             'burst': ([(3, c) for c in (0, 1, 1, 2, 2, 3, 4, 5, 6, 7)], 10, False),    # big wave on frame 6
             'guard': ([(2, c) for c in (0, 1, 2)], 6, True)},
    'thorne': {'idle': ([(0, c) for c in (0, 1, 2, 3)], 5, True),
               'attack': ([(1, c) for c in (0, 1, 2, 3, 5, 6, 7)], 12, False),         # shield 2, quake 4
               'hit': ([(4, c) for c in (0, 1, 2, 3)], 10, False),
               'victory': ([(7, c) for c in range(8)], 8, True),
               'ko': ([(6, c) for c in range(8)], 10, False),
               'burst': ([(3, c) for c in range(8)], 10, False),                       # earth spikes on 4
               'guard': ([(0, c) for c in (4, 5, 6)], 6, True)},
}


def cells(path):
    """-> 8x8 RGBA cells with the connected black background made transparent."""
    a = np.array(Image.open(path).convert('RGB'))
    n = a.shape[0] / 8
    out = []
    for r in range(8):
        row = []
        for c in range(8):
            cell = a[round(r * n):round((r + 1) * n), round(c * n):round((c + 1) * n)]
            lab, _ = ndimage.label(cell.max(-1) <= 10)
            edge = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])) - {0}
            alpha = np.where(np.isin(lab, list(edge)), 0, 255).astype(np.uint8)
            fg, _ = ndimage.label(alpha > 0)   # specks bleeding in from neighbouring cells
            sizes = np.bincount(fg.ravel())
            for k in set(np.unique(np.r_[fg[0], fg[-1], fg[:, 0], fg[:, -1]])) - {0}:
                if sizes[k] < 60:
                    alpha[fg == k] = 0
            row.append(Image.fromarray(np.dstack([cell, alpha]), 'RGBA'))
        out.append(row)
    return out


def place(cell, dx, dy):
    fr = Image.new('RGBA', (F, F), (0, 0, 0, 0))
    fr.alpha_composite(cell, (dx, dy))
    return fr


def portrait(frame):
    bb = frame.getbbox()
    c = frame.crop(bb)
    s = max(c.size) + 8
    out = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    out.alpha_composite(c, ((s - c.width) // 2, s - c.height - 2))
    return out


def import_sheet(fid, anims):
    cs = cells(os.path.join(ART, fid + '.png'))
    x0, y0, x1, y1 = cs[0][0].getbbox()            # idle frame: put its feet on F-4, centred
    dx, dy = round(F / 2 - (x0 + x1) / 2), F - 4 - y1
    sheet = Image.new('RGBA', (max(len(v[0]) for v in anims.values()) * F, len(anims) * F), (0, 0, 0, 0))
    meta = {'frame_size': [F, F], 'ui_scale': 0.25, 'source': f'tools/art_src/{fid}.png', 'animations': {}}
    for ri, (name, (frames, fps, loop)) in enumerate(anims.items()):
        for ci, (r, c) in enumerate(frames):
            sheet.alpha_composite(place(cs[r][c], dx, dy), (ci * F, ri * F))
        meta['animations'][name] = {'row': ri, 'frames': len(frames), 'fps': fps, 'loop': loop}
    d = os.path.join(OUT, fid)
    os.makedirs(d, exist_ok=True)
    sheet.save(os.path.join(d, fid + '_sheet.png'))
    with open(os.path.join(d, fid + '_sheet.json'), 'w') as f:
        json.dump(meta, f, indent=1)


def portraits():
    """Every hero's portrait = its first idle frame."""
    for fid in sorted(os.listdir(OUT)):
        meta = json.load(open(os.path.join(OUT, fid, fid + '_sheet.json')))
        fw, fh = meta['frame_size']
        row = meta['animations']['idle']['row']
        sheet = Image.open(os.path.join(OUT, fid, fid + '_sheet.png'))
        portrait(sheet.crop((0, row * fh, fw, (row + 1) * fh))).save(os.path.join(OUT, fid, fid + '_portrait.png'))


if __name__ == '__main__':
    for fam, forms in {'kael': ('emberclaw', 'blazeheart', 'cinderlord'), 'mira': ('tidesong', 'tidecaller', 'wavesage'),
                       'thorne': ('mossguard', 'oakwarden', 'ancientroot')}.items():
        for form in forms:
            import_sheet(f'{fam}_{form}', ANIMS[fam])
            print(f'{fam}_{form}')
    portraits()
