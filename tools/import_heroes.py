"""
Imports the owner's 8x8 battle sheets (tools/art_src/<form_id>.png, black background, facing right) for Kael, Mira
and Thorne, and writes every hero's portrait as its first idle frame.  Run: python3 tools/import_heroes.py

Every hero is normalised to the same technical spec, so the roster reads as one set:
  * same frame (F x F), same feet line (F-4, the game's anchor) and head centred on the same column;
  * same body height (head top to feet = BODY px), measured on the idle frames and rescaled;
  * same animation layout, frame counts and speeds (ANIM, taken from the same sheet cells for everyone);
  * same 1 px dark outline (the black-background removal eats the original one);
  * effects that run past a grid cell are kept (cells are cut with a margin, neighbours' pieces dropped).
Sheet rows: 0 idle/basic swing, 1 attack, 2 skill, 3 Burst, 4 hit + stun, 5 poison/freeze, 6 KO, 7 victory.
Hit timings this implies (hero_skills.json): attack hits on frames 2 and 4 (ranged: release 2), Burst 3/5/7/9
(self Bursts: release 4).
"""
import json
import os
import numpy as np
from PIL import Image
from scipy import ndimage

ART = os.path.join(os.path.dirname(__file__), 'art_src')
OUT = os.path.join(os.path.dirname(__file__), '..', 'Content', 'assets', 'characters')
F, BODY, M = 256, 124, 72          # frame size, head-to-feet height, cut margin around each source cell
OUTLINE = (26, 14, 22, 255)
ANIM = {   # name: ([(row, col), ...], fps, loop) - identical for every hero
    'idle': ([(0, c) for c in (0, 1, 2, 3)], 5, True),
    'attack': ([(1, c) for c in (1, 2, 3, 4, 5, 6, 7)], 14, False),
    'hit': ([(4, c) for c in (0, 1, 2, 3)], 10, False),
    'victory': ([(7, c) for c in range(8)], 8, True),
    'ko': ([(6, c) for c in range(8)], 10, False),
    'burst': ([(3, c) for c in (0, 1, 2, 3, 4, 3, 4, 5, 4, 5, 7)], 12, False),
    'guard': ([(0, c) for c in (4, 5, 6)], 6, True),
}
HEROES = {'kael': ('emberclaw', 'blazeheart', 'cinderlord'), 'mira': ('tidesong', 'tidecaller', 'wavesage'),
          'thorne': ('mossguard', 'oakwarden', 'ancientroot')}


def cells(path):
    """-> 8x8 RGBA crops (cell + margin M) with the black background removed and neighbours' pieces dropped."""
    a = np.array(Image.open(path).convert('RGB'))
    H, W = a.shape[:2]
    n = H / 8
    pad = np.zeros((H + 2 * M, W + 2 * M, 3), np.uint8)
    pad[M:M + H, M:M + W] = a
    out = []
    for r in range(8):
        row = []
        for c in range(8):
            y0, x0 = round(r * n), round(c * n)
            y1, x1 = round((r + 1) * n), round((c + 1) * n)
            crop = pad[y0:y1 + 2 * M, x0:x1 + 2 * M]
            lab, _ = ndimage.label(crop.max(-1) <= 10)
            edge = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])) - {0}
            fg = ~np.isin(lab, list(edge))
            parts, k = ndimage.label(fg, structure=np.ones((3, 3)))
            keep = np.zeros_like(fg)
            if k:
                cys = ndimage.mean(np.indices(fg.shape)[0], parts, range(1, k + 1))
                cxs = ndimage.mean(np.indices(fg.shape)[1], parts, range(1, k + 1))
                sizes = ndimage.sum(fg, parts, range(1, k + 1))
                for i, (cy, cx, sz) in enumerate(zip(cys, cxs, sizes), 1):
                    inside = M <= cy < M + (y1 - y0) and M <= cx < M + (x1 - x0)
                    if inside and sz >= 12:   # its own pieces (centre inside the cell), no specks
                        piece = parts == i
                        xs = np.nonzero(piece.any(0))[0]
                        # fused with a neighbour's pose: its feet stand on the ground row outside this cell -> cut that
                        # side at the cell edge (effects, even big ones, don't stand on the ground there)
                        w, gy = x1 - x0, np.nonzero(piece.any(1))[0].max()
                        ground = np.nonzero(piece[max(0, gy - 6):gy + 1].any(0))[0]
                        cov = piece.sum(0)   # cut along the emptiest column between the two poses
                        if ground.min() < M - 0.25 * w:
                            lo, hi = int(M - 0.35 * w), int(M + 0.1 * w)
                            piece[:, :lo + int(np.argmin(cov[lo:hi]))] = False
                        if ground.max() > M + 1.25 * w:
                            lo, hi = int(M + 0.9 * w), int(M + 1.35 * w)
                            piece[:, lo + int(np.argmin(cov[lo:hi])):] = False
                        keep |= piece
            row.append(Image.fromarray(np.dstack([crop, np.where(keep, 255, 0).astype(np.uint8)]), 'RGBA'))
        out.append(row)
    return out


def head_and_feet(img):
    """(head top y, feet y, head centre x): the head is the first row with a solid run >= 18 px."""
    a = np.array(img)[..., 3] > 0
    feet = np.nonzero(a.any(1))[0].max()
    for y in range(a.shape[0]):
        runs, best, cur, start = a[y], (0, 0), 0, 0
        for x, v in enumerate(runs):
            if v:
                if cur == 0:
                    start = x
                cur += 1
                if cur > best[0]:
                    best = (cur, start)
            else:
                cur = 0
        if best[0] >= 18:
            rows = a[y:y + 24]
            xs = np.nonzero(rows.any(0))[0]
            mid = best[1] + best[0] / 2
            near = xs[np.abs(xs - mid) < 26]
            return y, feet, float(near.mean())
    return 0, feet, a.shape[1] / 2


def outline(img):
    a = np.array(img)
    solid = a[..., 3] > 0
    ring = np.zeros_like(solid)
    ring[1:] |= solid[:-1]; ring[:-1] |= solid[1:]; ring[:, 1:] |= solid[:, :-1]; ring[:, :-1] |= solid[:, 1:]
    ring &= ~solid
    a[ring] = OUTLINE
    return Image.fromarray(a, 'RGBA')


def portrait(frame):
    c = frame.crop(frame.getbbox())
    s = max(c.size) + 8
    out = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    out.alpha_composite(c, ((s - c.width) // 2, s - c.height - 2))
    return out


def import_sheet(fid):
    cs = cells(os.path.join(ART, fid + '.png'))
    probes = [head_and_feet(cs[0][c]) for c in range(4)]
    h = float(np.median([f - t for t, f, _ in probes]))
    s = BODY / h                                       # same body height for every hero / form
    _, feet, hx = probes[0]
    sheet = Image.new('RGBA', (max(len(v[0]) for v in ANIM.values()) * F, len(ANIM) * F), (0, 0, 0, 0))
    meta = {'frame_size': [F, F], 'layout_size': [200, 200], 'ui_scale': 0.25, 'source': f'tools/art_src/{fid}.png', 'animations': {}}
    for ri, (name, (frames, fps, loop)) in enumerate(ANIM.items()):
        for ci, (r, c) in enumerate(frames):
            cell = cs[r][c]
            sc = cell.convert('RGBa').resize((round(cell.width * s), round(cell.height * s)), Image.LANCZOS).convert('RGBA')
            al = np.array(sc)
            al[..., 3] = np.where(al[..., 3] >= 128, 255, 0)   # crisp edges again after resampling
            sc = Image.fromarray(al, 'RGBA')
            fr = Image.new('RGBA', (F, F), (0, 0, 0, 0))
            fr.alpha_composite(sc, (round(F / 2 - hx * s), round(F - 4 - feet * s)))
            sheet.alpha_composite(outline(fr), (ci * F, ri * F))
        meta['animations'][name] = {'row': ri, 'frames': len(frames), 'fps': fps, 'loop': loop}
    d = os.path.join(OUT, fid)
    os.makedirs(d, exist_ok=True)
    sheet.save(os.path.join(d, fid + '_sheet.png'))
    with open(os.path.join(d, fid + '_sheet.json'), 'w') as f:
        json.dump(meta, f, indent=1)
    portrait(sheet.crop((0, 0, F, F))).save(os.path.join(d, fid + '_portrait.png'))
    return s


if __name__ == '__main__':
    for fam, forms in HEROES.items():
        for form in forms:
            print(f'{fam}_{form}', 'scale %.3f' % import_sheet(f'{fam}_{form}'))
