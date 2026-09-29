"""
Regenerates every Cinderbound art asset from code.
Run from the project root:  python3 tools/make_assets.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from pixlib import sheet
import hero_kael, hero_mira, hero_thorne, enemies, portraits, fx_icons_ui as fx, backgrounds as bg

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Content'))  # game content root


def out(*p):
    path = os.path.join(ROOT, *p)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def write_sheet(folder, name, anims, fw, fh):
    rows, meta = [], {'frame_size': [fw, fh], 'animations': {}}
    for i, (anim, frames, fps, loop) in enumerate(anims):
        rows.append(frames)
        meta['animations'][anim] = {'row': i, 'frames': len(frames), 'fps': fps, 'loop': loop}
    sheet(rows, fw, fh).save(out(folder, name + '_sheet.png'))
    with open(out(folder, name + '_sheet.json'), 'w') as f:
        json.dump(meta, f, indent=1)


def main():
    heroes = {'kael_emberclaw': hero_kael, 'mira_tidesong': hero_mira, 'thorne_mossguard': hero_thorne}
    for hid, mod in heroes.items():
        anims = [(n, fn(), fps, loop) for (n, fn, fps, loop) in mod.ANIMS]
        write_sheet(f'assets/characters/{hid}', hid, anims, 48, 48)
        portraits.PORTRAITS[hid]().save(out(f'assets/characters/{hid}', hid + '_portrait.png'))
    write_sheet('assets/enemies/cinder_slime', 'cinder_slime', enemies.slime_anims(), 48, 48)
    write_sheet('assets/enemies/tidefin', 'tidefin', enemies.tidefin_anims(), 48, 48)
    write_sheet('assets/enemies/bramble_pup', 'bramble_pup', enemies.pup_anims(), 48, 48)
    write_sheet('assets/enemies/ancient_bramble_pup', 'ancient_bramble_pup', enemies.pup_anims(True), 64, 64)
    fxmeta = {}
    for name, (fn, fw, fh, fps) in fx.EFFECTS.items():
        frames = fn()
        fx.strip(frames).save(out('assets/effects', name + '.png'))
        fxmeta[name] = {'frame_size': [fw, fh], 'frames': len(frames), 'fps': fps}
    with open(out('assets/effects', 'effects.json'), 'w') as f:
        json.dump(fxmeta, f, indent=1)
    for name, fn in fx.ICONS.items():
        fn().save(out('assets/icons', name + '.png'))
    for name, fn in fx.UI.items():
        im = fn()   # UI textures are stored at 3x so 9-slice borders stay crisp at 1080p
        im.resize((im.width * 3, im.height * 3), 0).save(out('assets/ui', name + '.png'))
    for name, fn in bg.SCENES.items():
        fn().save(out('assets/environments', name + '.png'))
    print('assets generated')


if __name__ == '__main__':
    main()
