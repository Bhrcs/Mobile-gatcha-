"""
Builds the second wave of enemy sprite sheets (tools/enemies2.py).
Run from the project root:

    python3 tools/make_enemies2.py                 # every species
    python3 tools/make_enemies2.py tide_slime ...  # just some
    python3 tools/make_enemies2.py --preview DIR   # also write 3x contact sheets

Writes assets/enemies/<id>/<id>_sheet.png + <id>_sheet.json (same meta format
as make_assets.write_sheet) and tools/enemy_manifest.json. Sheets are stored as
indexed PNGs (exact palette when it fits in 256 colours) to keep the download
small.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from pixlib import sheet  # noqa: E402
import enemies2  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MANIFEST = os.path.join(ROOT, 'tools', 'enemy_manifest.json')


def save_indexed(img, path):
    """Saves an RGBA image as a palette PNG (lossless when <= 256 colours)."""
    a = np.array(img.convert('RGBA'))
    a[a[:, :, 3] == 0] = 0
    h, w = a.shape[:2]
    v = np.ascontiguousarray(a).view('<u4').reshape(h, w)
    uniq, inv = np.unique(v, return_inverse=True)
    if len(uniq) <= 256:
        pal = uniq.view(np.uint8).reshape(-1, 4)
        p = Image.fromarray(inv.reshape(h, w).astype(np.uint8), 'P')
        p.putpalette(pal[:, :3].flatten().tolist())
        p.save(path, optimize=True, transparency=bytes(pal[:, 3].tolist()))
    else:
        q = Image.fromarray(a, 'RGBA').quantize(256, method=Image.Quantize.FASTOCTREE,
                                                  dither=Image.Dither.NONE)
        q.save(path, optimize=True)
    return os.path.getsize(path)


def check_frames(eid, anims, fw, fh):
    """Warns about sprites touching the frame border (clipping)."""
    issues = []
    for (name, frames, _fps, _loop) in anims:
        for i, f in enumerate(frames):
            a = np.array(f)[:, :, 3] > 0
            if a[0, :].any() or a[-1, :].any() or a[:, 0].any() or a[:, -1].any():
                issues.append(f'{name}[{i}]')
    if issues:
        print(f'  ! {eid}: touches frame edge in {", ".join(issues)}')
    return issues


def write_species(eid, anims, size):
    folder = os.path.join(ROOT, 'assets', 'enemies', eid)
    os.makedirs(folder, exist_ok=True)
    rows, meta = [], {'frame_size': [size, size], 'animations': {}}
    for i, (anim, frames, fps, loop) in enumerate(anims):
        for f in frames:
            assert f.size == (size, size), (eid, anim, f.size)
        rows.append(frames)
        meta['animations'][anim] = {'row': i, 'frames': len(frames), 'fps': fps, 'loop': loop}
    img = sheet(rows, size, size)
    nbytes = save_indexed(img, os.path.join(folder, eid + '_sheet.png'))
    with open(os.path.join(folder, eid + '_sheet.json'), 'w') as f:
        json.dump(meta, f, indent=1)
    return img, meta, nbytes


def manifest_entry(eid, meta, size):
    t = enemies2.TIMING[eid]
    anims = meta['animations']
    return {'size': size,
            'frames': {k: v['frames'] for k, v in anims.items()},
            'fps': {k: v['fps'] for k, v in anims.items()},
            'attack': t['attack'], 'special': t['special'], 'role': t['role']}


def contact(img, size, scale=3, bg=(128, 128, 128)):
    big = img.resize((img.width * scale, img.height * scale), Image.NEAREST)
    out = Image.new('RGBA', big.size, bg + (255,))
    # faint frame grid so clipping is easy to spot
    g = np.array(out)
    step = size * scale
    g[:, ::step] = (112, 112, 112, 255)
    g[::step, :] = (112, 112, 112, 255)
    out = Image.fromarray(g, 'RGBA')
    out.alpha_composite(big)
    return out


def main(argv):
    preview_dir = None
    if '--preview' in argv:
        k = argv.index('--preview')
        preview_dir = argv[k + 1]
        argv = argv[:k] + argv[k + 2:]
        os.makedirs(preview_dir, exist_ok=True)
    ids = argv or list(enemies2.ANIMS.keys())
    manifest = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            manifest = json.load(f)
    for eid in ids:
        fn, size = enemies2.ANIMS[eid]
        anims = fn()
        check_frames(eid, anims, size, size)
        img, meta, nbytes = write_species(eid, anims, size)
        manifest[eid] = manifest_entry(eid, meta, size)
        limit = 16 * 1024 if size == 48 else 32 * 1024
        flag = '' if nbytes <= limit else '  (OVER BUDGET)'
        print(f'{eid:22s} {img.width}x{img.height}  {nbytes / 1024:5.1f} KB{flag}')
        if preview_dir:
            contact(img, size).save(os.path.join(preview_dir, eid + '.png'))
    ordered = {k: manifest[k] for k in enemies2.ANIMS if k in manifest}
    with open(MANIFEST, 'w') as f:
        json.dump(ordered, f, indent=1)


if __name__ == '__main__':
    main(sys.argv[1:])
