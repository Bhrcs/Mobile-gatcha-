"""
The Saltglass Colossus - World 2 boss (original design for Cinderbound).

A hunched giant of sea-worn stone and coral with a saltglass spine and a huge
crystal club for a right arm. Its chest core glows brighter as it charges.
64x64 frames, faces RIGHT (enemies stand on the left of the field).

    python3 tools/boss_w2.py        -> assets/enemies/saltglass_colossus/
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixlib import Canvas, Pal, hexc, sheet  # noqa: E402
from make_enemies2 import save_indexed  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SZ = 64
GROUND = 60

STONE = Pal('#5a6a78', '#8494a4', '#3c4a58', '#1e2630')
STONE_D = Pal('#46535f', '#5a6a78', '#2e3944', '#161d24')
GLASS = Pal('#a8ecfa', '#ffffff', '#6ac4de', '#2a7894')
GLASS_HOT = Pal('#dffcff', '#ffffff', '#9ae8f6', '#3a98b0')
CORAL = Pal('#e8705a', '#ff9c82', '#b44a3c', '#6e2a22')
KELP = Pal('#4a8a4a', '#6aae5a', '#326a32', '#1a3a1a')
CORE = [hexc('#6ff0ff'), hexc('#d8ffff'), hexc('#2ab8e0')]
EYE = hexc('#aefcff')


def polar(x, y, a, r):
    t = math.radians(a)
    return (x + math.cos(t) * r, y + math.sin(t) * r)


def colossus(dy=0, lean=0, club=(-40,), back=(110,), eyes='open', core=1, crack=0, spikes=1.0, fade=0.0, lift=0):
    cv = Canvas(SZ, SZ)
    bx = 26 + lean
    by = 38 + dy
    # back arm (stone), hanging
    sh_b = (bx - 8, by - 8)
    hb = polar(sh_b[0], sh_b[1], back[0], 12)
    cv.part(cv.mask().line(sh_b[0], sh_b[1], hb[0], hb[1], 5), STONE_D)
    cv.part(cv.mask().ellipse(hb[0], hb[1], 3.5, 3), STONE_D)
    # legs
    for (lx, ph) in ((bx - 5, 0), (bx + 7, 1)):
        top = (lx, by + 8)
        foot = (lx + (lift if ph else 0) + 1, GROUND - (lift if ph else 0))
        knee = (lx + 3, (top[1] + foot[1]) / 2)
        cv.part(cv.mask().line(top[0], top[1], knee[0], knee[1], 7).line(knee[0], knee[1], foot[0], foot[1] - 2, 6),
                STONE_D if ph == 0 else STONE)
        cv.part(cv.mask().rect(foot[0] - 4, foot[1] - 3, foot[0] + 5, foot[1]), STONE_D)
    # saltglass spine spikes (behind the body)
    for i, (sx, sa, ln) in enumerate(((bx - 12, -150, 10), (bx - 7, -125, 13), (bx - 1, -100, 12), (bx + 5, -80, 9))):
        base = (sx, by - 9 + abs(i - 1.5))
        tip = polar(base[0], base[1], sa, ln * spikes)
        l = polar(base[0], base[1], sa - 90, 2.4)
        r = polar(base[0], base[1], sa + 90, 2.4)
        cv.part(cv.mask().poly([l, tip, r]), GLASS if core < 3 else GLASS_HOT)
    # body boulder
    body = cv.mask().ellipse(bx, by - 2, 12, 13)
    body.ellipse(bx + 3, by - 13, 12, 7)          # hunched shoulders
    body.ellipse(bx - 1, by + 7, 10, 5)           # hips
    cv.part(body, STONE)
    cv.part(cv.mask().ellipse(bx - 6, by - 4, 3, 6), STONE.__class__(STONE.hi, STONE.hi, STONE.base, STONE.sh),
            shade=False, separate=False)
    # coral + barnacles
    for (x, y, r) in ((bx - 9, by + 4, 2.4), (bx - 4, by + 8, 1.8), (bx + 10, by + 6, 2.0)):
        cv.part(cv.mask().ellipse(x, y, r, r), CORAL)
    for (x, y) in ((bx - 12, by - 2), (bx + 2, by + 9), (bx - 6, by - 6)):
        cv.dot(x, y, STONE.hi)
    # kelp strands
    for (x, y) in ((bx - 13, by - 4), (bx + 1, by - 11)):
        cv.part(cv.mask().line(x, y, x - 2, y + 7, 1).line(x - 2, y + 7, x, y + 12, 1), KELP, shade=False,
                separate=False)
    # cracks glow when damaged / enraged
    if crack:
        for (x0, y0, x1, y1) in ((bx - 6, by - 4, bx - 1, by + 3), (bx - 1, by + 3, bx - 4, by + 9),
                                 (bx + 6, by - 2, bx + 10, by + 4))[:crack + 1]:
            cv.part(cv.mask().line(x0, y0, x1, y1, 1), Pal(CORE[0], CORE[1], CORE[2]), shade=False, separate=False)
    # head
    hx, hy = bx + 13, by - 17
    cv.part(cv.mask().ellipse(hx, hy, 6, 5), STONE)
    cv.part(cv.mask().poly([(hx - 3, hy + 3), (hx + 7, hy + 2), (hx + 6, hy + 6), (hx - 2, hy + 6)]), STONE_D)  # jaw
    for (dx, h) in ((-3, 6), (0, 9), (3, 6)):
        cv.part(cv.mask().poly([(hx + dx - 1, hy - 4), (hx + dx, hy - 4 - h), (hx + dx + 2, hy - 4)]), GLASS)
    if eyes in ('open', 'flare'):
        cv.dot(hx + 3, hy - 1, EYE)
        cv.dot(hx + 4, hy - 1, EYE if eyes == 'open' else CORE[1])
        if eyes == 'flare':
            cv.dot(hx + 5, hy - 2, CORE[1])
            cv.dot(hx + 3, hy - 2, CORE[0])
    elif eyes == 'hurt':
        cv.dot(hx + 3, hy - 2, (20, 30, 40, 255))
        cv.dot(hx + 4, hy - 1, (20, 30, 40, 255))
    else:
        cv.dot(hx + 3, hy - 1, (20, 30, 40, 255))
        cv.dot(hx + 4, hy - 1, (20, 30, 40, 255))
    # chest core
    cr = 2 + min(core, 3) * 0.7
    cv.part(cv.mask().ellipse(bx + 4, by - 4, cr + 1.5, cr + 1.5), STONE_D)
    cv.part(cv.mask().ellipse(bx + 4, by - 4, cr, cr), Pal(CORE[0], CORE[1], CORE[2]), separate=False)
    # front arm + saltglass club
    sh = (bx + 10, by - 12)
    a = club[0]
    elbow = polar(sh[0], sh[1], a + 70, 8)
    hand = polar(elbow[0], elbow[1], a + 20, 7)
    cv.part(cv.mask().line(sh[0], sh[1], elbow[0], elbow[1], 6).line(elbow[0], elbow[1], hand[0], hand[1], 5), STONE)
    cv.part(cv.mask().ellipse(sh[0], sh[1], 4.5, 4), STONE_D)
    tip = polar(hand[0], hand[1], a, 18)
    l = polar(hand[0], hand[1], a - 90, 3)
    r = polar(hand[0], hand[1], a + 90, 3)
    lt = polar(tip[0], tip[1], a - 90, 5)
    rt = polar(tip[0], tip[1], a + 90, 5)
    cv.part(cv.mask().poly([l, lt, polar(tip[0], tip[1], a, 3), rt, r]), GLASS if core < 3 else GLASS_HOT)
    cv.part(cv.mask().ellipse(hand[0], hand[1], 3, 3), STONE)
    cv.outline()
    if core >= 2:
        cv.glow((110, 230, 255), alpha=60 if core == 2 else 110)
    img = cv.image().copy()
    if fade > 0:
        import random
        rng = random.Random(int(fade * 100))
        px = img.load()
        for y in range(SZ):
            for x in range(SZ):
                if px[x, y][3] and rng.random() < fade:
                    px[x, y] = (0, 0, 0, 0)
    return img


def anims():
    idle = [colossus(), colossus(dy=1, core=1), colossus(dy=1, core=2, spikes=1.05), colossus(core=1)]
    attack = [colossus(club=(-70,), lean=-2, eyes='flare'), colossus(club=(-110,), lean=-3, dy=1, eyes='flare'),
              colossus(club=(10,), lean=3, eyes='flare'), colossus(club=(40,), lean=4, dy=1),
              colossus(club=(30,), lean=3), colossus(club=(-20,), lean=1)]
    hit = [colossus(lean=-3, eyes='hurt', club=(-10,)), colossus(lean=-1, eyes='hurt')]
    death = [colossus(eyes='hurt', dy=1, crack=1), colossus(eyes='closed', dy=3, crack=2, club=(60,)),
             colossus(eyes='closed', dy=5, crack=2, club=(70,), fade=0.3),
             colossus(eyes='closed', dy=6, crack=2, club=(75,), fade=0.65),
             colossus(eyes='closed', dy=7, crack=2, club=(80,), fade=0.92)]
    special = [colossus(core=2, eyes='flare'), colossus(core=3, eyes='flare', spikes=1.15, lean=-1),
               colossus(core=3, eyes='flare', spikes=1.3, club=(-100,), lean=-3, dy=1),
               colossus(core=3, eyes='flare', spikes=1.3, club=(-130,), lean=-3, dy=2),
               colossus(core=3, eyes='flare', spikes=1.2, club=(20,), lean=4, lift=2),
               colossus(core=3, eyes='flare', spikes=1.1, club=(45,), lean=5, dy=1),
               colossus(core=2, club=(35,), lean=3), colossus(core=1, club=(-20,), lean=1)]
    return [('idle', idle, 4, True), ('attack', attack, 11, False), ('hit', hit, 10, False),
            ('death', death, 8, False), ('special', special, 10, False)]


def build():
    folder = os.path.join(ROOT, 'assets', 'enemies', 'saltglass_colossus')
    os.makedirs(folder, exist_ok=True)
    rows, meta = [], {'frame_size': [SZ, SZ], 'animations': {}}
    for i, (anim, frames, fps, loop) in enumerate(anims()):
        rows.append(frames)
        meta['animations'][anim] = {'row': i, 'frames': len(frames), 'fps': fps, 'loop': loop}
    save_indexed(sheet(rows, SZ, SZ), os.path.join(folder, 'saltglass_colossus_sheet.png'))
    with open(os.path.join(folder, 'saltglass_colossus_sheet.json'), 'w') as f:
        json.dump(meta, f, indent=1)
    print('saltglass_colossus written')


if __name__ == '__main__':
    build()
