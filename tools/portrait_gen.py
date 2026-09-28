"""
portrait_gen - 64x64 bust portraits for every Phase 4 hero form (original art).

roster_portrait(spec)      -> generic parametric bust driven by a hero_gen Spec
starter_portrait(form_id)  -> the hand-drawn starter busts (portraits.py) with
                              evolution overlays for the 4* / 5* forms

Portraits are drawn on a transparent canvas; the game places them on an
element-lit backdrop, so they stay reusable in cards, detail and cut-ins.
"""
import math
from pixlib import Canvas, Pal, hexc, lighten, darken
import portraits as PT
import hero_kael as K
import hero_mira as M
import hero_thorne as T

S = 64
CX, CY = 33, 31          # face centre used by portraits.face()
WHITE = (252, 250, 240, 255)


def _p(sp, key, fallback):
    return sp.pal.get(key) or fallback


def _flat(c):
    return Pal(c, c, c, darken(c, 0.5) if hasattr(c, '__len__') else c)


# ------------------------------------------------------------------ body
def shoulders(cv, sp):
    heavy = sp.build in ('heavy', 'giant', 'sturdy')
    y_top = 46 if sp.build != 'giant' else 44
    spread = 4 if heavy else 0
    if sp.build == 'young':
        spread = -3
    tun = cv.mask().poly([(4 - spread, 63), (10 - spread, 50), (23, y_top), (45, y_top), (56 + spread, 50),
                          (62 + spread, 63)])
    cv.part(tun, sp.sleeve or sp.tunic)
    chest = sp.chest or sp.tunic
    style = sp.chest_style
    if style in ('plate', 'breast'):
        cv.part(cv.mask().poly([(17, 63), (21, 51), (45, 51), (49, 63)]), chest)
        cv.part(cv.mask().line(33, 52, 33, 63, 1), Pal(chest.sh, chest.sh, chest.sh), shade=False, separate=False)
    elif style == 'vest':
        cv.part(cv.mask().poly([(19, 63), (22, 51), (30, 51), (30, 63)]), chest)
        cv.part(cv.mask().poly([(36, 63), (36, 51), (44, 51), (47, 63)]), chest)
        cv.part(cv.mask().poly([(30, 63), (30, 51), (36, 51), (36, 63)]), sp.tunic)
    elif style == 'bib':
        cv.part(cv.mask().poly([(23, 63), (25, 51), (41, 51), (43, 63)]), chest)
    else:
        cv.part(cv.mask().poly([(20, 63), (23, 51), (43, 51), (46, 63)]), sp.tunic)
    if sp.trim is not None:
        t = cv.mask().line(21, 51, 45, 51, 1)
        if style in ('plate', 'breast', 'bib'):
            t.line(23, 51, 20, 63, 1).line(43, 51, 46, 63, 1)
        cv.part(t, sp.trim, shade=False, separate=False)
    if sp.pauldron is not None:
        r = 10 if heavy else 8
        cv.part(cv.mask().ellipse(53 + spread // 2, 53, r, 7), sp.pauldron)
        cv.part(cv.mask().ellipse(12 - spread // 2, 53, r - 2, 6), sp.pauldron)
        cv.dot(50, 49, sp.pauldron.hi)
        cv.dot(51, 49, sp.pauldron.hi)
        if sp.trim is not None and sp.pal.get('pauldron_trim', True) is not False:
            cv.part(cv.mask().line(46, 58, 60, 55, 1), sp.trim, shade=False, separate=False)
    # neck
    cv.part(cv.mask().rect(28, 41, 38, 48), sp.skin)


def neck_and_items(cv, sp):
    if sp.neck in ('mantle', 'collar', 'scarf'):
        pal = sp.neck_pal or sp.tunic
        cv.part(cv.mask().poly([(16, 50), (24, 44), (42, 44), (50, 50), (44, 54), (22, 54)]), pal)
    items = set(sp.items)
    if 'frost_mantle' in items:
        F = sp.pal['fur']
        cv.part(cv.mask().poly([(12, 52), (22, 44), (44, 44), (54, 52), (46, 56), (20, 56)]), F)
        for x in range(16, 52, 3):
            cv.dot(x, 55 + (x % 2), F.sh)
    if 'sash' in items:
        cv.part(cv.mask().line(24, 51, 42, 63, 3), sp.pal['sash'], separate=False)
    if 'satchel' in items:
        cv.part(cv.mask().line(22, 50, 44, 63, 2), sp.pal['strap'], shade=False, separate=False)
    if 'molten' in items:
        mol = sp.pal['molten']
        for (x0, y0, x1, y1) in ((26, 54, 29, 60), (29, 60, 27, 63), (38, 53, 40, 58), (40, 58, 43, 61)):
            cv.part(cv.mask().line(x0, y0, x1, y1, 1), mol, shade=False, separate=False)
    if 'coral' in items:
        C = sp.pal['coral']
        for (x, y) in ((50, 50), (53, 48), (55, 51), (12, 52)):
            cv.dot(x, y, C.hi)
            cv.dot(x + 1, y + 1, C.base)
    if 'gold_trim' in items and sp.trim is not None:
        cv.part(cv.mask().line(22, 50, 22, 63, 1).line(44, 50, 44, 63, 1), sp.trim, shade=False, separate=False)
    if 'bark' in items:
        for (x, y) in ((24, 56), (40, 58), (30, 60)):
            cv.dot(x, y, sp.skin.sh)
            cv.dot(x + 1, y, sp.skin.line)
    if 'blossoms' in items:
        P = sp.pal['petal']
        for (x, y) in ((24, 55), (42, 57), (50, 50)):
            cv.part(cv.mask().ellipse(x, y, 1.6, 1.6), P, separate=False)
            cv.dot(x, y, sp.pal['pollen'])
    if 'glyph_belt' in items or 'glyph' in sp.aura:
        for x in (26, 33, 40):
            cv.dot(x, 60, sp.fx[0])


def cape(cv, sp):
    if not sp.cape:
        return
    pal = sp.cape_pal or sp.tunic
    if sp.cape == 'petal_wings':
        for side in (-1, 1):
            cx = 33 + side * 22
            cv.part(cv.mask().ellipse(cx, 44, 9, 13), Pal(pal.hi, lighten(pal.hi, 0.4), pal.base, pal.sh))
        return
    if sp.cape in ('leaf', 'gale'):
        m = cv.mask().poly([(2, 63), (6, 44), (18, 40), (48, 40), (60, 44), (63, 63)])
    else:
        m = cv.mask().poly([(0, 63), (4, 46), (16, 42), (50, 42), (62, 46), (63, 63)])
    cv.part(m, pal)
    if sp.cape_trim is not None:
        cv.part(cv.mask().line(4, 46, 16, 42, 1).line(50, 42, 62, 46, 1), sp.cape_trim, shade=False, separate=False)


def back_features(cv, sp):
    if 'sun_halo' in sp.back:
        Sp = sp.pal['sun']
        cv.part(cv.mask().ellipse(33, 22, 22, 22), Pal(Sp.hi, lighten(Sp.hi, 0.3), Sp.base, Sp.sh), separate=False)
        cv.part(cv.mask().ellipse(33, 22, 18, 18), Pal(lighten(Sp.hi, 0.35), lighten(Sp.hi, 0.5), Sp.hi), shade=False,
                separate=False)
    if 'quiver' in sp.back:
        cv.part(cv.mask().line(8, 60, 16, 34, 5), sp.pal['quiver'])
        for k in range(3):
            cv.dot(14 + k * 2, 31 - k, sp.pal['fletch'].hi)
            cv.dot(14 + k * 2, 32 - k, sp.pal['fletch'].base)


# ------------------------------------------------------------------ hair
def hair_back(cv, sp):
    H = sp.hair
    st = sp.hair_style
    if st in ('wavy', 'sleek'):
        m = cv.mask().poly([(14, 20), (50, 20), (52, 52), (44, 58), (22, 58), (12, 50)])
        if st == 'wavy':
            for y in range(28, 58, 6):
                m.ellipse(14, y, 3, 3)
                m.ellipse(51, y, 3, 3)
        cv.part(m, H)
    elif st == 'ponytail':
        m = cv.mask().poly([(14, 20), (8, 30), (4, 46), (10, 50), (14, 38), (20, 26)])
        cv.part(m, H)
    elif st == 'curly':
        m = cv.mask()
        for (x, y, r) in ((18, 22, 6), (46, 22, 6), (16, 32, 5), (49, 32, 5), (20, 40, 4), (46, 40, 4)):
            m.ellipse(x, y, r, r)
        cv.part(m, H)


def hair_front(cv, sp):
    H = sp.hair
    st = sp.hair_style
    if st in ('bald', 'none', 'hooded'):
        if st == 'bald':
            cv.dot(28, 15, lighten(sp.skin.hi, 0.2))
            cv.dot(29, 14, lighten(sp.skin.hi, 0.2))
        return
    m = cv.mask()
    if st == 'capped':
        m.rect(19, 20, 23, 34).rect(43, 20, 46, 30)
    elif st == 'curly':
        for (x, y, r) in ((22, 17, 6), (30, 13, 6), (39, 13, 6), (46, 18, 5), (26, 22, 4), (41, 21, 4)):
            m.ellipse(x, y, r, r)
        m.rect(19, 18, 23, 32)
    elif st == 'ponytail':
        m.ellipse(32, 19, 13, 8).rect(19, 18, 23, 32)
        m.poly([(36, 16), (46, 20), (44, 28), (40, 22)])
    elif st == 'sleek':
        m.ellipse(32, 19, 13, 8)
        m.poly([(20, 16), (18, 40), (23, 38), (25, 22)])
        m.poly([(40, 16), (47, 22), (47, 38), (43, 32), (41, 22)])
    elif st == 'wavy':
        m.ellipse(32, 19, 13, 9)
        m.poly([(20, 16), (17, 42), (23, 40), (25, 22)])
        m.poly([(38, 16), (46, 22), (48, 38), (43, 30), (41, 22)])
    elif st == 'mossy':
        for (x, y, r) in ((22, 15, 5), (31, 11, 6), (41, 12, 5), (47, 18, 4), (18, 22, 3)):
            m.ellipse(x, y, r, r)
    else:   # short
        m.ellipse(32, 19, 13, 8).rect(19, 18, 23, 32)
        m.poly([(34, 14), (46, 18), (42, 24)])
    cv.part(m, H)
    if st == 'mossy':
        for (x, y) in ((24, 12), (36, 9), (44, 14), (20, 20)):
            cv.dot(x, y, sp.fx[0])
            cv.dot(x + 1, y, sp.fx[2])


def beard(cv, sp):
    if not sp.beard:
        return
    B = sp.beard_pal or sp.hair
    if sp.beard == 'stubble':
        for x in range(26, 41, 2):
            for y in (39, 41):
                cv.dot(x + (y % 2), y, B.base)
        return
    long_ = sp.beard in ('long', 'moss', 'full')
    top = 38 if sp.beard == 'moss' else 34
    m = cv.mask().poly([(23, top), (43, top), (42, 44 if not long_ else 50), (33, 54 if long_ else 47),
                        (24, 44 if not long_ else 50)])
    face_gap = cv.mask().ellipse(33, 38, 4, 2)
    m.subtract(face_gap)
    cv.part(m, B)
    if sp.beard == 'moss':
        for (x, y) in ((26, 46), (38, 48), (32, 51)):
            cv.dot(x, y, sp.fx[0])


# ------------------------------------------------------------------ headgear
def headgear(cv, sp):
    for h in sp.head:
        fn = HEADGEAR.get(h)
        if fn:
            fn(cv, sp)


def _goggles(cv, sp):
    cv.part(cv.mask().rect(19, 17, 47, 19), sp.pal['strap'], shade=False)
    for x in (27, 38):
        cv.part(cv.mask().ellipse(x, 17, 4, 3.5), sp.pal['brass'])
        cv.part(cv.mask().ellipse(x, 17, 2.4, 2.2), sp.pal['lens'], separate=False)


def _sun_circlet(cv, sp):
    cv.part(cv.mask().rect(20, 15, 46, 16), GOLDP, shade=False)
    Sp = sp.pal['sun']
    cv.part(cv.mask().ellipse(33, 12, 4, 4), Sp)
    for a in range(0, 360, 45):
        r = math.radians(a)
        cv.dot(33 + math.cos(r) * 6, 12 + math.sin(r) * 6, Sp.hi)


def _horned_helm(cv, sp):
    Hm = sp.pal['helm']
    cv.part(cv.mask().ellipse(33, 17, 15, 9).rect(18, 17, 48, 21), Hm)
    for side in (-1, 1):
        x0 = 33 + side * 13
        m = cv.mask().poly([(x0, 16), (x0 + side * 7, 6), (x0 + side * 9, 0), (x0 + side * 4, 12), (x0 + side, 19)])
        cv.part(m, sp.pal['horn'])
    if 'molten' in sp.pal:
        cv.part(cv.mask().rect(24, 19, 42, 20), sp.pal['molten'], shade=False)


def _winged_circlet(cv, sp):
    cv.part(cv.mask().rect(20, 15, 46, 16), GOLDP, shade=False)
    W = sp.pal['wing']
    for side in (-1, 1):
        x0 = 33 + side * 14
        m = cv.mask().poly([(x0, 15), (x0 + side * 9, 6), (x0 + side * 7, 12), (x0 + side * 10, 11),
                            (x0 + side * 6, 17)])
        cv.part(m, W)
    cv.part(cv.mask().poly([(33, 12), (35, 15), (33, 18), (31, 15)]), sp.pal['gem'])


def _bandana(cv, sp):
    B = sp.pal['bandana']
    cv.part(cv.mask().ellipse(33, 16, 14, 7).rect(19, 16, 47, 20), B)
    cv.part(cv.mask().poly([(19, 18), (10, 24), (13, 27), (20, 22)]), B)


def _finned_helm(cv, sp):
    Hm = sp.pal['helm']
    m = cv.mask().ellipse(33, 18, 16, 11).rect(17, 18, 49, 23)
    m.rect(17, 23, 22, 38).rect(44, 23, 49, 36)          # cheek guards
    cv.part(m, Hm)
    F = sp.pal['fin']
    cv.part(cv.mask().poly([(26, 8), (34, -1), (44, 4), (40, 10)]), F)
    cv.part(cv.mask().rect(22, 22, 44, 23), Pal(sp.pal['visor'], sp.pal['visor'], sp.pal['visor']), shade=False)


def _hood_down(cv, sp):
    Hd = sp.pal['hood']
    cv.part(cv.mask().poly([(12, 52), (16, 40), (24, 44), (42, 44), (50, 40), (54, 52), (44, 56), (22, 56)]), Hd)


def _ice_crown(cv, sp):
    I = sp.pal['ice']
    for (x, h) in ((22, 6), (27, 9), (33, 12), (39, 9), (44, 6)):
        cv.part(cv.mask().poly([(x - 2, 14), (x, 14 - h), (x + 2, 14)]), I)


def _cowl(cv, sp):
    C = sp.pal['cowl']
    back = cv.mask().ellipse(33, 26, 19, 20)
    cv.part(back, C)


def _cowl_front(cv, sp):
    C = sp.pal['cowl']
    rim = cv.mask().poly([(14, 34), (16, 14), (30, 7), (46, 11), (51, 24), (51, 36), (45, 22), (33, 18),
                          (22, 21), (20, 38)])
    cv.part(rim, C)
    cv.part(cv.mask().poly([(33, 10), (35, 13), (33, 16), (31, 13)]), sp.pal['gem'])


def _feather_cap(cv, sp):
    Cp = sp.pal['cap']
    cv.part(cv.mask().ellipse(33, 16, 15, 7).rect(18, 16, 48, 19), Cp)
    cv.part(cv.mask().poly([(40, 12), (56, 0), (58, 3), (44, 14)]), sp.pal['feather'])


def _flower_crown(cv, sp, big=False):
    P = sp.pal['petal']
    P2 = sp.pal['petal2']
    L = sp.pal.get('leafp', sp.fx and Pal(sp.fx[0], sp.fx[2], sp.fx[1]))
    pts = ((21, 17), (27, 13), (33, 11), (39, 13), (45, 17))
    for i, (x, y) in enumerate(pts):
        if big and i % 2 == 0:
            cv.part(cv.mask().ellipse(x - 3, y + 1, 2, 1.2), L, separate=False)
        r = 2.6 if (big and i == 2) else 2.0
        cv.part(cv.mask().ellipse(x, y, r, r), P if i % 2 == 0 else P2)
        cv.dot(x, y, sp.pal['pollen'])


HEADGEAR = {
    'goggles': _goggles, 'sun_circlet': _sun_circlet, 'horned_helm': _horned_helm,
    'winged_circlet': _winged_circlet, 'bandana': _bandana, 'finned_helm': _finned_helm,
    'hood_down': lambda cv, sp: None, 'ice_crown': _ice_crown, 'cowl': _cowl_front,
    'feather_cap': _feather_cap, 'flower_crown': _flower_crown,
    'bloom_crown': lambda cv, sp: _flower_crown(cv, sp, big=True),
}
GOLDP = Pal('#e0b040', '#fff0a0', '#a87c20', '#5c420c')


# ------------------------------------------------------------------ aura
def aura_overlay(cv, sp):
    if not sp.aura:
        return
    cols = sp.fx or [(255, 255, 255, 255)] * 3
    pts = ((6, 12), (58, 10), (4, 30), (60, 34), (10, 4), (54, 22))
    for i, (x, y) in enumerate(pts[: 4 if sp.aura_glow < 30 else 6]):
        cv.dot(x, y, cols[i % 3])
        if i % 2 == 0:
            cv.dot(x + 1, y, cols[(i + 1) % 3])


# ------------------------------------------------------------------ public
def roster_portrait(sp):
    cv = Canvas(S, S)
    back_features(cv, sp)
    cape(cv, sp)
    if 'cowl' in sp.head:
        _cowl(cv, sp)
    if 'hood_down' in sp.head:
        _hood_down(cv, sp)
    hair_back(cv, sp)
    shoulders(cv, sp)
    jaw = {'giant': 1.15, 'heavy': 1.08, 'sturdy': 1.05, 'young': 0.95}.get(sp.build, 1.0)
    PT.face(cv, sp.skin, jaw=jaw)
    neck_and_items(cv, sp)
    beard(cv, sp)
    hair_front(cv, sp)
    headgear(cv, sp)
    fierce = sp.moves in ('greataxe', 'spear', 'daggers', 'club', 'trident')
    soft = sp.moves in ('blossom', 'lantern')
    PT.eyes(cv, CX, 29, sp.eye, fierce=fierce, soft=soft)
    PT.nose_mouth(cv, sp.skin, CX, 29, smile=soft or sp.build == 'young')
    cv.outline()
    if sp.aura_glow:
        cv.glow(sp.glow_col, alpha=min(90, sp.aura_glow * 2))
    aura_overlay(cv, sp)
    return cv.image()


# ---- starters: hand-drawn busts + evolution overlays
def _kael(tier):
    K.set_tier(tier)
    try:
        cv = Canvas(S, S)
        cv.part(cv.mask().poly([(0, 63), (4, 46), (16, 42), (50, 42), (62, 46), (63, 63)]), K.CAPE)
        PT.kael(cv, finish=False)
        cv.part(cv.mask().ellipse(13, 53, 7, 6), K.PAULDRON)               # second pauldron
        cv.part(cv.mask().line(33, 53, 33, 63, 1), K.TRIM, shade=False, separate=False)
        if tier == 3:
            cv.part(cv.mask().poly([(26, 11), (30, 1), (33, 7), (37, 0), (40, 11)]),
                    Pal('#ff8a2a', '#ffe08a', '#e0521c', '#8a2a0c'))
            cv.part(cv.mask().rect(24, 10, 42, 12), K.PAULDRON, shade=False)
        cv.outline()
        if tier == 3:
            cv.glow((255, 120, 40), alpha=70)
            for (x, y, i) in ((6, 14, 0), (58, 20, 1), (8, 34, 2), (56, 6, 0)):
                cv.dot(x, y, K.SPARK[i])
        return cv.image()
    finally:
        K.set_tier(1)


def _mira(tier):
    M.set_tier(tier)
    try:
        cv = Canvas(S, S)
        if tier == 3:   # flowing mantle behind the shoulders
            cv.part(cv.mask().poly([(0, 63), (2, 44), (14, 40), (52, 40), (62, 44), (63, 63)]), M.CLOAK_IN)
        PT.mira(cv, finish=False)
        cv.part(cv.mask().rect(20, 14, 46, 15), M.SILVER, shade=False)
        cv.part(cv.mask().poly([(33, 9), (35, 13), (33, 16), (31, 13)]), M.CRYSTAL)
        if tier == 3:
            for (x, h) in ((24, 5), (29, 8), (37, 8), (42, 5)):
                cv.part(cv.mask().poly([(x - 2, 14), (x, 14 - h), (x + 2, 14)]), M.CRYSTAL)
        cv.outline()
        if tier == 3:
            cv.glow((120, 220, 255), alpha=60)
            for (x, y) in ((8, 20), (56, 16), (6, 40), (58, 38)):
                cv.dot(x, y, M.DROP[x % 3])
        return cv.image()
    finally:
        M.set_tier(1)


def _thorne(tier):
    T.set_tier(tier)
    try:
        cv = Canvas(S, S)
        big = tier == 3
        for side in (-1, 1):   # antlers behind the hood
            x0 = 33 + side * 10
            m = cv.mask().line(x0, 14, x0 + side * 7, 2, 2).line(x0 + side * 4, 7, x0 + side * 11, 4, 2)
            if big:
                m.line(x0 + side * 7, 2, x0 + side * 6, 0, 2).line(x0 + side * 9, 5, x0 + side * 13, 1, 1)
            cv.part(m, T.ANTLER)
        if big:
            cv.part(cv.mask().poly([(0, 63), (2, 46), (14, 42), (52, 42), (62, 46), (63, 63)]),
                    Pal('#3e7a2c', '#5ca040', '#2a5a1c', '#16300e'))
        PT.thorne(cv, finish=False)
        cv.part(cv.mask().ellipse(12, 52, 8, 6), T.BARK)                 # second bark pauldron
        if big:
            for side in (-1, 1):
                cv.dot(33 + side * 21, 2, T.LEAF[0])
                cv.dot(33 + side * 17, 0, T.LEAF[2])
        cv.outline()
        if big:
            cv.glow((120, 220, 80), alpha=60)
            for (x, y) in ((6, 30), (58, 26), (4, 50), (60, 46)):
                cv.dot(x, y, T.LEAF[x % 3])
        return cv.image()
    finally:
        T.set_tier(1)


STARTER_TIERS = {
    'kael_emberclaw': (_kael, 1), 'kael_blazeheart': (_kael, 2), 'kael_cinderlord': (_kael, 3),
    'mira_tidesong': (_mira, 1), 'mira_tidecaller': (_mira, 2), 'mira_wavesage': (_mira, 3),
    'thorne_mossguard': (_thorne, 1), 'thorne_oakwarden': (_thorne, 2), 'thorne_ancientroot': (_thorne, 3),
}


def starter_portrait(form_id):
    fn, tier = STARTER_TIERS[form_id]
    if tier == 1:
        return PT.PORTRAITS[form_id]()
    return fn(tier)
