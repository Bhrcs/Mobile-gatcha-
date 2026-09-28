"""
Cinderbound UI Phase 5 additions (original pixel art, same materials and icon
rules as tools/ui_v2.py): danger button, tabs, switches, slider knob,
scrollbars, tooltip plate, stage-node variants, tower path pieces and the
utility / role icon family.

    python3 tools/ui_p5.py
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixlib import Canvas, Pal, hexc  # noqa: E402
import ui_v2 as v2  # noqa: E402

UI, ICONS = v2.UI, v2.ICONS


def icon(fn):
    cv = Canvas(16, 16)
    fn(cv)
    cv.outline()
    return cv.image()


# ---------------------------------------------------------------- icons
IRON = Pal('#9aa4b4', '#e0e8f0', '#5a6474')
GOLDP = Pal('#e0a83a', '#fff0b0', '#8a5a14')
EMBERP = Pal('#e0702a', '#ffc070', '#8a2a12')
BONE = Pal('#e8dcc0', '#fffaf0', '#a89a78')


def ic_back(cv):
    cv.part(cv.mask().poly([(1, 8), (8, 1), (8, 5), (14, 5), (14, 11), (8, 11), (8, 15)]), BONE)


def ic_help(cv):
    cv.part(cv.mask().ellipse(7.5, 7.5, 7, 7), Pal('#3e5a80', '#6e94c0', '#243650'))
    m = cv.mask().rect(5, 3, 10, 4).rect(9, 5, 10, 7).rect(7, 7, 9, 9).rect(7, 11, 8, 12)
    cv.part(m, Pal('#fff6e0'), flat=True, separate=False)


def ic_info(cv):
    cv.part(cv.mask().ellipse(7.5, 7.5, 7, 7), Pal('#6a5a28', '#9a8a44', '#3a2e14'))
    cv.part(cv.mask().rect(7, 3, 8, 4).rect(6, 6, 8, 7).rect(7, 8, 8, 11).rect(6, 12, 9, 12),
            Pal('#fff6e0'), flat=True, separate=False)


def ic_filter(cv):
    cv.part(cv.mask().poly([(1, 2), (14, 2), (9, 8), (9, 14), (6, 12), (6, 8)]), IRON)


def ic_sort(cv):
    for i, w in enumerate((12, 9, 6)):
        cv.part(cv.mask().rect(2, 2 + i * 5, 2 + w, 4 + i * 5), GOLDP)


def ic_plus(cv):
    cv.part(cv.mask().rect(6, 2, 9, 13).rect(2, 6, 13, 9), GOLDP)


def ic_minus(cv):
    cv.part(cv.mask().rect(2, 6, 13, 9), Pal('#c0303a', '#ff8a7a', '#7a1a22'))


def ic_close(cv):
    cv.part(cv.mask().line(3, 3, 12, 12, 2).line(12, 3, 3, 12, 2), BONE)


def ic_pause(cv):
    cv.part(cv.mask().rect(3, 2, 6, 13).rect(9, 2, 12, 13), BONE)


def ic_element_chart(cv):
    cv.part(cv.mask().ellipse(8, 3, 2.5, 2.5), Pal('#ff5a2a', '#ffb07a', '#8a1a0a'))
    cv.part(cv.mask().ellipse(3, 12, 2.5, 2.5), Pal('#2a8ae0', '#8ad0ff', '#12406a'))
    cv.part(cv.mask().ellipse(13, 12, 2.5, 2.5), Pal('#4ab02a', '#a8f070', '#1e5a12'))
    cv.part(cv.mask().line(8, 5, 12, 10, 1).line(11, 13, 5, 13, 1).line(3, 10, 7, 5, 1), Pal('#e8dcc0'), flat=True)


# roles ------------------------------------------------------------
def ic_role_attacker(cv):
    cv.part(cv.mask().line(3, 13, 12, 3, 2), Pal('#c9d1dc', '#ffffff', '#8e98a8'))
    cv.part(cv.mask().line(2, 10, 6, 14, 1), Pal('#9a6a2a', '#d0a060', '#5a3a14'))
    cv.part(cv.mask().rect(1, 13, 3, 15), Pal('#c0303a', '#ff8a7a', '#7a1a22'))


def ic_role_defender(cv):
    cv.part(cv.mask().poly([(2, 2), (13, 2), (13, 8), (8, 14), (7, 14), (2, 8)]), Pal('#6e94c0', '#b8d8f0', '#243650'))
    cv.part(cv.mask().rect(7, 4, 8, 11).rect(4, 6, 11, 7), Pal('#e0a83a', '#fff0b0', '#8a5a14'))


def ic_role_healer(cv):
    cv.part(cv.mask().rect(6, 2, 9, 13).rect(2, 6, 13, 9), Pal('#e8f0e0', '#ffffff', '#9aa890'))
    cv.part(cv.mask().rect(7, 3, 8, 12).rect(3, 7, 12, 8), Pal('#4ab02a', '#9ae060', '#2a6a18'), flat=True)


def ic_role_support(cv):
    cv.part(cv.mask().rect(3, 1, 4, 15), Pal('#9a6a2a', '#d0a060', '#5a3a14'))
    cv.part(cv.mask().poly([(5, 2), (14, 2), (11, 6), (14, 10), (5, 10)]), Pal('#e0a83a', '#fff0b0', '#8a5a14'))


def ic_role_breaker(cv):
    cv.part(cv.mask().line(4, 14, 9, 7, 1), Pal('#9a6a2a', '#d0a060', '#5a3a14'))
    cv.part(cv.mask().poly([(6, 3), (12, 1), (15, 7), (9, 9)]), Pal('#8a8690', '#c0bcc4', '#3a3640'))


def ic_new(cv):
    cv.part(cv.mask().poly([(8, 0), (10, 5), (15, 5), (11, 9), (13, 15), (8, 11), (3, 15), (5, 9), (1, 5), (6, 5)]),
            Pal('#ff5a4a', '#ffb0a0', '#8a1a14'))


def ic_squad(cv):
    for (x, y) in ((4, 5), (11, 5)):
        cv.part(cv.mask().ellipse(x, y, 2.5, 2.5).rect(x - 3, y + 3, x + 3, y + 8), IRON)
    cv.part(cv.mask().ellipse(7.5, 6, 3, 3).rect(4, 9, 11, 15), Pal('#e0702a', '#ffc070', '#8a2a12'))


def ic_role_list():
    return {'role_attacker': ic_role_attacker, 'role_defender': ic_role_defender, 'role_healer': ic_role_healer,
            'role_support': ic_role_support, 'role_breaker': ic_role_breaker}


# ---------------------------------------------------------------- pieces
def tab(active):
    """Tab: rounded top, open bottom edge."""
    w, h = 32, 14
    metal = v2.METALS['ember' if active else 'iron']
    m = [v2.c(x) for x in metal]
    top, bot = (v2.c('#7a2e14'), v2.c('#3a140c')) if active else (v2.c('#3a3640'), v2.c('#221e28'))
    a = np.zeros((h, w, 4), dtype=np.int32)
    for y in range(h):
        for x in range(w):
            corner = min(x, w - 1 - x) + y < 2
            if corner:
                continue
            e = min(x, y, w - 1 - x)
            if e == 0:
                col = m[0]
            elif e == 1:
                col = m[4] if y == 1 else m[2]
            else:
                k = y / (h - 1)
                col = top * (1 - k) + bot * k
                if y == 2:
                    col = col + 40
            a[y, x] = col
            a[y, x, 3] = 255
    return a


def switch(on):
    w, h = 24, 12
    a = v2.frame(w, h, 'ember' if on else 'iron', rim=1, interior='#3a140c' if on else '#141018', stone_int=False,
                 ornament=None, rivets=False)
    # knob
    kx = w - 11 if on else 2
    kcol = ['#fff0b0', '#e0a83a', '#8a5a14'] if on else ['#c0bcc4', '#8a8690', '#3a3640']
    for y in range(2, h - 2):
        for x in range(kx, kx + 9):
            e = min(x - kx, y - 2, kx + 8 - x, h - 3 - y)
            a[y, x] = v2.c(kcol[2] if e == 0 else (kcol[0] if y < 5 else kcol[1]))
            a[y, x, 3] = 255
    return a


def knob():
    w, h = 10, 16
    a = np.zeros((h, w, 4), dtype=np.int32)
    for y in range(h):
        for x in range(w):
            e = min(x, y, w - 1 - x, h - 1 - y)
            a[y, x] = v2.c('#16121a' if e == 0 else ('#fff0c0' if y < 4 else ('#e0a83a' if y < h - 4 else '#8a5a14')))
            a[y, x, 3] = 255
    for y in (6, 8, 10):
        for x in range(3, 7):
            a[y, x] = v2.c('#8a5a14')
    return a


def _box(w, h, rim, hi, fill, line=None):
    a = np.zeros((h, w, 4), dtype=np.int32)
    for y in range(h):
        for x in range(w):
            e = min(x, y, w - 1 - x, h - 1 - y)
            if e == 0:
                col = rim
            elif e == 1 and line:
                col = line
            elif e == 1 and y == 1:
                col = hi
            else:
                col = fill
            a[y, x] = v2.c(col)
            a[y, x, 3] = 255
    return a


def scroll_track():
    return _box(6, 16, '#16121a', '#241e2a', '#0e0a12')


def scroll_grab(hot=False):
    return _box(6, 16, '#16121a', '#ffc070' if hot else '#c0bcc4', '#e0702a' if hot else '#6a6670')


def tip_plate():
    return _box(16, 16, '#16121a', '#3a3640', '#0e0a12', line='#c0501a')


def node_elite():
    cv = Canvas(24, 24)
    cv.part(cv.mask().poly([(12, 1), (22, 12), (12, 23), (2, 12)]), Pal('#a8741e', '#fff0b0', '#6a4410'))
    cv.part(cv.mask().poly([(12, 5), (18, 12), (12, 19), (6, 12)]), Pal('#c0303a', '#ff8a7a', '#7a1a22'))
    cv.part(cv.mask().poly([(12, 8), (15, 12), (12, 16), (9, 12)]), Pal('#fff0c0', '#ffffff', '#ffb04a'))
    cv.outline()
    return cv.image()


def node_perfect():
    """Cleared with all three stars: gold ring + check."""
    cv = Canvas(24, 24)
    cv.part(cv.mask().ellipse(11.5, 11.5, 10.5, 10.5), Pal('#a8741e', '#fff0b0', '#6a4410'))
    cv.part(cv.mask().ellipse(11.5, 11.5, 7.5, 7.5), Pal('#4ab02a', '#b0f070', '#2a6a18'))
    cv.part(cv.mask().line(7, 12, 10, 15, 1).line(10, 15, 16, 8, 1), Pal('#ffffff'), flat=True)
    cv.outline()
    return cv.image()


def node_cleared_check():
    cv = Canvas(24, 24)
    cv.part(cv.mask().ellipse(11.5, 11.5, 10.5, 10.5), Pal('#6a5a28', '#d0c078', '#3a2e14'))
    cv.part(cv.mask().ellipse(11.5, 11.5, 7.5, 7.5), Pal('#3a8a24', '#8ad060', '#1e5212'))
    cv.part(cv.mask().line(7, 12, 10, 15, 1).line(10, 15, 16, 8, 1), Pal('#f0ffe0'), flat=True)
    cv.outline()
    return cv.image()


def tower_path(branch):
    """Vertical path segment between tower floors (tiles vertically), per branch."""
    w, h = 12, 16
    pal = {'ember': ['#16121a', '#3a3640', '#5a3a2a', '#e0702a', '#ffc070'],
           'tide': ['#0c1220', '#243650', '#2a5a80', '#6ae0ff', '#e0f8ff'],
           'verdant': ['#140c06', '#3a2412', '#4a5a28', '#8ad060', '#d8ffb0']}[branch]
    cols = [v2.c(x) for x in pal]
    a = np.zeros((h, w, 4), dtype=np.int32)
    for y in range(h):
        for x in range(2, w - 2):
            e = min(x - 2, w - 3 - x)
            a[y, x] = cols[0] if e == 0 else (cols[2] if e > 1 else cols[1])
            a[y, x, 3] = 255
    # branch motif: embers / droplets / leaves on the path centre
    for y in range(h):
        if branch == 'ember' and y % 8 in (2, 3):
            a[y, 5:7] = cols[3] if y % 8 == 2 else cols[4]
        elif branch == 'tide' and y % 8 in (1, 2, 3):
            a[y, 5 + (y % 2)] = cols[3]
        elif branch == 'verdant' and y % 8 in (4, 5):
            a[y, 4:8] = cols[3] if y % 8 == 4 else cols[2]
        if branch == 'verdant' and y % 8 == 5:
            a[y, 4] = cols[4]
    return a


def build():
    # buttons: danger (crimson) + normal/pressed
    v2.save3(v2.to_img(v2.button('#c0303a', '#5a0e16', 'crimson')), 'v2_btn_crimson')
    v2.save3(v2.to_img(v2.button('#c0303a', '#5a0e16', 'crimson', pressed=True)), 'v2_btn_crimson_p')
    v2.save3(v2.to_img(tab(False)), 'p5_tab')
    v2.save3(v2.to_img(tab(True)), 'p5_tab_on')
    v2.save3(v2.to_img(switch(False)), 'p5_switch_off')
    v2.save3(v2.to_img(switch(True)), 'p5_switch_on')
    v2.save3(v2.to_img(knob()), 'p5_knob')
    v2.save3(v2.to_img(scroll_track()), 'p5_scroll')
    v2.save3(v2.to_img(scroll_grab()), 'p5_scroll_grab')
    v2.save3(v2.to_img(scroll_grab(True)), 'p5_scroll_grab_hot')
    v2.save3(v2.to_img(tip_plate()), 'p5_tip')
    node_elite().save(os.path.join(UI, 'v2_node_elite.png'))
    node_perfect().save(os.path.join(UI, 'v2_node_perfect.png'))
    node_cleared_check().save(os.path.join(UI, 'v2_node_cleared.png'))
    for b in ('ember', 'tide', 'verdant'):
        v2.save1(v2.to_img(tower_path(b)), 'p5_path_' + b, UI)
    icons = {'back': ic_back, 'help': ic_help, 'info': ic_info, 'filter': ic_filter, 'sort': ic_sort,
             'plus': ic_plus, 'minus': ic_minus, 'close': ic_close, 'pause': ic_pause,
             'element_chart': ic_element_chart, 'new': ic_new, 'squad': ic_squad}
    icons.update(ic_role_list())
    for name, fn in icons.items():
        icon(fn).save(os.path.join(ICONS, name + '.png'))
    print('ui p5 generated: %d icons' % len(icons))


if __name__ == '__main__':
    build()
