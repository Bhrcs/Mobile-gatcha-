"""
Writes every Phase 4 hero form to assets/characters/<form_id>/:
  <form_id>_sheet.png / _sheet.json   (rows = idle attack hit victory ko burst guard)
  <form_id>_portrait.png              (64x64 bust, see portrait_gen.py)

  python3 tools/make_heroes_p4.py            # all forms
  python3 tools/make_heroes_p4.py kael_blazeheart ...

Starter evolutions reuse the bespoke starter generators (hero_kael/mira/thorne)
with set_tier(2|3); the gacha heroes come from hero_roster / hero_gen.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixlib import sheet  # noqa: E402
from make_enemies2 import save_indexed  # noqa: E402
import hero_kael  # noqa: E402
import hero_mira  # noqa: E402
import hero_thorne  # noqa: E402
import hero_roster as R  # noqa: E402
import hero_gen as G  # noqa: E402
import portrait_gen as PG  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Content'))  # game content root

STARTER_FORMS = {
    'kael_emberclaw': (hero_kael, 1), 'kael_blazeheart': (hero_kael, 2), 'kael_cinderlord': (hero_kael, 3),
    'mira_tidesong': (hero_mira, 1), 'mira_tidecaller': (hero_mira, 2), 'mira_wavesage': (hero_mira, 3),
    'thorne_mossguard': (hero_thorne, 1), 'thorne_oakwarden': (hero_thorne, 2), 'thorne_ancientroot': (hero_thorne, 3),
}


def out(*p):
    path = os.path.join(ROOT, *p)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def write_sheet(form_id, anims, fw=48, fh=48):
    rows, meta = [], {'frame_size': [fw, fh], 'animations': {}}
    for i, (anim, frames, fps, loop) in enumerate(anims):
        rows.append(frames)
        meta['animations'][anim] = {'row': i, 'frames': len(frames), 'fps': fps, 'loop': loop}
    save_indexed(sheet(rows, fw, fh), out('assets/characters', form_id, form_id + '_sheet.png'))
    with open(out('assets/characters', form_id, form_id + '_sheet.json'), 'w') as f:
        json.dump(meta, f, indent=1)
    return meta


def starter_anims(mod, tier):
    mod.set_tier(tier)
    try:
        return [(n, fn(), fps, loop) for (n, fn, fps, loop) in mod.ANIMS]
    finally:
        mod.set_tier(1)


def build(only=None):
    done = []
    for form_id, (mod, tier) in STARTER_FORMS.items():
        if only and form_id not in only:
            continue
        if False:  # starters are owner art (tools/import_kael.py, import_heroes.py);   # tier 1: make_assets.py; Kael: tools/import_kael.py
            write_sheet(form_id, starter_anims(mod, tier))
        save_indexed(PG.starter_portrait(form_id), out('assets/characters', form_id, form_id + '_portrait.png'))
        done.append(form_id)
    for form_id, sp in R.FORMS.items():
        if only and form_id not in only:
            continue
        write_sheet(form_id, G.anims(sp))
        save_indexed(PG.roster_portrait(sp), out('assets/characters', form_id, form_id + '_portrait.png'))
        done.append(form_id)
    print('hero forms written:', len(done))


if __name__ == '__main__':
    build(set(sys.argv[1:]) or None)
