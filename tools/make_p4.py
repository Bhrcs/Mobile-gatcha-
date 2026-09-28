"""
Runner for art pack 4 (tools/icons_p4.py).

  python3 tools/make_p4.py                 # write icons / effects / summon-gate UI
  python3 tools/make_p4.py --preview DIR   # ...and render QA contact sheets into DIR

Only writes NEW files (see icons_p4.ICONS / EFFECTS / build()) and merges new
entries into assets/effects/effects.json without altering existing ones.
NOTE: tools/make_assets.py rewrites effects.json from fx_icons_ui only - run
this script again after it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import icons_p4 as p4  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402


def _label(d, xy, text, fill=(255, 255, 255, 255)):
    d.text(xy, text, fill=fill)


def icon_sheet(path, scale=4, bg=(118, 118, 126)):
    refs = ['orb_fire', 'gold', 'nav_home', 'status_burn', 'shard_fire', 'star', 'status_def_up', 'leader']
    names = list(p4.ICONS.keys())
    cols = 10
    cell_w, cell_h = 16 * scale + 22, 16 * scale + 16
    rows = (len(names) + cols - 1) // cols + 2
    W = cols * cell_w + 20
    H = rows * cell_h + 40 + 2 * (16 * 2 + 10)
    out = Image.new('RGBA', (W, H), bg + (255,))
    d = ImageDraw.Draw(out)

    def draw_icon(name, x, y, s=scale):
        im = Image.open(os.path.join(p4.ICON_DIR, name + '.png')).convert('RGBA')
        out.alpha_composite(im.resize((16 * s, 16 * s), Image.NEAREST), (x, y))

    _label(d, (10, 4), 'reference (existing):')
    for i, n in enumerate(refs):
        draw_icon(n, 10 + i * cell_w, 16)
        _label(d, (10 + i * cell_w, 16 + 16 * scale), n[:13], (220, 220, 220, 255))
    y0 = 16 + cell_h + 10
    _label(d, (10, y0 - 12), 'new:')
    for i, n in enumerate(names):
        x = 10 + (i % cols) * cell_w
        y = y0 + (i // cols) * cell_h
        draw_icon(n, x, y)
        _label(d, (x, y + 16 * scale), n[:13])
    # 1x and 2x strips on a dark UI panel colour (actual in-game reading size)
    yb = y0 + ((len(names) + cols - 1) // cols) * cell_h + 8
    d.rectangle([0, yb - 4, W, H], fill=(34, 30, 40, 255))
    for i, n in enumerate(refs + names):
        draw_icon(n, 10 + i * 18, yb, 1) if 10 + i * 18 + 16 < W else None
    for i, n in enumerate(names):
        x = 10 + (i % 27) * 34
        y = yb + 22 + (i // 27) * 36
        draw_icon(n, x, y, 2)
    out.save(path)


def fx_sheet(path, scale=3, bg=(52, 56, 66)):
    items = []
    for name, (fn, fw, fh, fps, loop) in p4.EFFECTS.items():
        im = Image.open(os.path.join(p4.FX_DIR, name + '.png')).convert('RGBA')
        items.append(('%s  %dx%d x%d @%dfps %s' % (name, fw, fh, im.width // fw, fps, 'loop' if loop else ''),
                      im.resize((im.width * scale, im.height * scale), Image.NEAREST), fw * scale))
    W = max(i[1].width for i in items) + 20
    H = sum(i[1].height + 16 for i in items) + 10
    out = Image.new('RGBA', (W, H), bg + (255,))
    d = ImageDraw.Draw(out)
    y = 6
    for (lab, im, fws) in items:
        _label(d, (8, y), lab)
        y += 12
        for fx_ in range(0, im.width, fws):
            d.rectangle([10 + fx_, y, 10 + fx_ + fws - 1, y + im.height - 1], outline=(70, 76, 88, 255))
        out.alpha_composite(im, (10, y))
        y += im.height + 4
    out.save(path)


def gate_sheet(path, scale=3):
    gate = Image.open(os.path.join(p4.UI_DIR, 'embergate_frame.png')).convert('RGBA')
    vort = Image.open(os.path.join(p4.UI_DIR, 'embergate_vortex.png')).convert('RGBA')
    ban = Image.open(os.path.join(p4.UI_DIR, 'banner_standard.png')).convert('RGBA')
    glows = [Image.open(os.path.join(p4.UI_DIR, 'rarity_glow_%d.png' % k)).convert('RGBA') for k in (3, 4, 5)]
    comp = Image.new('RGBA', gate.size, (30, 22, 34, 255))
    comp.alpha_composite(vort.crop((0, 0, 64, 64)), p4.VORTEX_POS)
    comp.alpha_composite(gate)
    bgc = (40, 36, 48, 255)
    G = lambda im: im.resize((im.width * scale, im.height * scale), Image.NEAREST)  # noqa: E731
    W = max(gate.width * scale * 3 + 40, ban.width * scale + 20)
    H = gate.height * scale + 20 + 64 * scale + 20 + ban.height * scale + 20 + 32 * scale * 1 + 40
    out = Image.new('RGBA', (W, H), bgc)
    d = ImageDraw.Draw(out)
    grey = Image.new('RGBA', gate.size, (120, 120, 128, 255))
    grey.alpha_composite(gate)
    out.alpha_composite(G(gate), (10, 10))
    out.alpha_composite(G(grey), (20 + gate.width * scale, 10))
    out.alpha_composite(G(comp), (30 + gate.width * scale * 2, 10))
    y = 20 + gate.height * scale
    out.alpha_composite(G(vort), (10, y))
    y += 64 * scale + 10
    out.alpha_composite(G(ban), (10, y))
    y += ban.height * scale + 10
    for i, g in enumerate(glows):
        for j, bg in enumerate(((20, 16, 26, 255), (90, 90, 98, 255))):
            tile = Image.new('RGBA', g.size, bg)
            tile.alpha_composite(g)
            out.alpha_composite(G(tile), (10 + (i * 2 + j) * (32 * scale + 8), y))
    _label(d, (12, 12), 'embergate_frame (transparent)')
    out.save(path)


def main():
    p4.build()
    if '--preview' in sys.argv:
        dst = sys.argv[sys.argv.index('--preview') + 1]
        os.makedirs(dst, exist_ok=True)
        icon_sheet(os.path.join(dst, 'p4_icons.png'))
        fx_sheet(os.path.join(dst, 'p4_fx.png'))
        gate_sheet(os.path.join(dst, 'p4_gate.png'))
        print('previews in', dst)


if __name__ == '__main__':
    main()
