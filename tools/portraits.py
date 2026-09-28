"""64x64 pixel-art bust portraits for the three starters (original designs)."""
from pixlib import Canvas, Pal, hexc
import hero_kael as K
import hero_mira as M
import hero_thorne as T

S = 64


def face(cv, skin, cx=33, cy=31, jaw=1.0):
    m = cv.mask().ellipse(cx, cy - 1, 11, 12)
    m.poly([(cx - 10, cy + 2), (cx + 11, cy + 2), (cx + 6, cy + 12 * jaw), (cx, cy + 14 * jaw),
            (cx - 6, cy + 11 * jaw)])
    cv.part(m, skin)
    # ear on the far-left side
    cv.part(cv.mask().ellipse(cx - 11, cy + 2, 2, 3), skin)


def eyes(cv, cx, cy, iris, lash=(30, 20, 26, 255), fierce=False, soft=False):
    white = (248, 244, 238, 255)
    for (ex, w) in ((cx - 6, 3), (cx + 4, 4)):
        for x in range(w):
            for y in range(4):
                cv.dot(ex + x, cy + y, white)
        # iris
        for x in range(2):
            for y in range(3):
                cv.dot(ex + w - 2 + x, cy + 1 + y, iris)
        cv.dot(ex + w - 1, cy + 1, (255, 255, 255, 255))
        # upper lash
        for x in range(-1, w + 1):
            cv.dot(ex + x, cy - 1, lash)
        if soft:
            cv.dot(ex + w, cy, lash)
        # brow
        by = cy - 4 + (1 if fierce else 0)
        for x in range(w + 1):
            yy = by + (x * 1 // (w + 1) if fierce else 0) - (1 if (fierce and x < 1) else 0)
            cv.dot(ex - 1 + x, yy if not fierce else by + (1 if x >= w - 1 else 0), lash)


def nose_mouth(cv, skin, cx, cy, smile=False):
    cv.dot(cx + 2, cy + 7, skin.sh)
    cv.dot(cx + 2, cy + 8, skin.sh)
    cv.dot(cx + 1, cy + 9, skin.sh)
    if smile:
        for x in range(0, 3):
            cv.dot(cx + x, cy + 12, skin.line)
        cv.dot(cx - 1, cy + 11, skin.line)
        cv.dot(cx + 3, cy + 11, skin.line)
    else:
        for x in range(-1, 3):
            cv.dot(cx + x, cy + 12, skin.line)


def kael(cv=None, finish=True):
    """finish=False leaves the outline off so evolution overlays can be added first."""
    cv = cv or Canvas(S, S)
    # scarf tail behind
    cv.part(cv.mask().poly([(12, 44), (4, 50), (2, 58), (10, 56), (18, 50)]), K.SCARF)
    # shoulders: iron plate + pauldron
    cv.part(cv.mask().poly([(8, 63), (12, 50), (24, 46), (44, 46), (54, 52), (58, 63)]), K.CLOTH)
    cv.part(cv.mask().poly([(18, 63), (22, 52), (44, 52), (48, 63)]), K.IRON)
    cv.part(cv.mask().ellipse(52, 53, 9, 7), K.PAULDRON)
    cv.dot(49, 50, K.PAULDRON.hi)
    cv.dot(50, 50, K.PAULDRON.hi)
    cv.part(cv.mask().rect(29, 42, 38, 48), K.SKIN)            # neck
    face(cv, K.SKIN)
    # scarf wrap
    cv.part(cv.mask().poly([(20, 46), (26, 43), (42, 43), (48, 47), (44, 52), (22, 52)]), K.SCARF)
    # spiky dark-brown hair
    h = cv.mask().ellipse(31, 20, 13, 8)
    h.poly([(18, 22), (8, 16), (18, 14)])
    h.poly([(20, 14), (14, 4), (27, 11)])
    h.poly([(26, 11), (30, 1), (35, 11)])
    h.poly([(34, 11), (44, 4), (42, 15)])
    h.poly([(41, 15), (50, 16), (44, 24)])
    h.poly([(36, 22), (42, 26), (39, 20)])
    h.rect(19, 18, 23, 34)
    h.poly([(19, 30), (23, 30), (21, 38)])
    cv.part(h, K.HAIR)
    eyes(cv, 33, 29, (170, 70, 30, 255), fierce=True)
    nose_mouth(cv, K.SKIN, 33, 29)
    # small scar on the cheek
    cv.dot(40, 37, K.SKIN.sh)
    cv.dot(41, 36, K.SKIN.sh)
    if finish:
        cv.outline()
    return cv.image()


def mira(cv=None, finish=True):
    """finish=False leaves the outline off so evolution overlays can be added first."""
    cv = cv or Canvas(S, S)
    # long hair behind
    cv.part(cv.mask().poly([(14, 20), (46, 20), (48, 58), (40, 63), (16, 63), (12, 50)]), M.HAIR)
    cv.part(cv.mask().poly([(6, 63), (12, 50), (24, 46), (44, 46), (54, 50), (60, 63)]), M.CLOAK)
    cv.part(cv.mask().poly([(20, 63), (24, 52), (42, 52), (46, 63)]), M.SILVER)
    cv.dot(33, 57, M.CRYSTAL.base)
    cv.dot(33, 58, M.CRYSTAL.hi)
    cv.part(cv.mask().rect(29, 42, 37, 48), M.SKIN)
    face(cv, M.SKIN, jaw=0.95)
    cv.part(cv.mask().poly([(18, 46), (26, 44), (40, 44), (50, 48), (44, 52), (22, 52)]), M.CLOAK)
    # hair: centre part with side curtains
    h = cv.mask().ellipse(32, 20, 13, 9)
    h.poly([(20, 16), (18, 42), (23, 40), (25, 22)])
    h.poly([(38, 16), (46, 22), (47, 36), (43, 30), (41, 22)])
    h.poly([(26, 16), (32, 24), (36, 16)])
    cv.part(h, M.HAIR)
    # hair clip: small water crystal
    cv.part(cv.mask().poly([(43, 16), (45, 13), (47, 16), (45, 19)]), M.CRYSTAL)
    eyes(cv, 33, 29, (40, 120, 190, 255), soft=True)
    nose_mouth(cv, M.SKIN, 33, 29, smile=True)
    if finish:
        cv.outline()
    return cv.image()


def thorne(cv=None, finish=True):
    """finish=False leaves the outline off so evolution overlays can be added first."""
    cv = cv or Canvas(S, S)
    # broad shoulders in leather + bark, moss on the pauldron
    cv.part(cv.mask().poly([(2, 63), (8, 50), (22, 45), (46, 45), (58, 50), (63, 63)]), T.LEATHER)
    cv.part(cv.mask().poly([(18, 63), (22, 52), (44, 52), (48, 63)]), T.BARK)
    cv.part(cv.mask().ellipse(53, 52, 10, 7), T.BARK)
    for x in range(46, 60, 2):
        cv.dot(x, 46 + (x % 3), T.MOSS.hi)
        cv.dot(x + 1, 47 + (x % 2), T.MOSS.base)
    # hood back
    cv.part(cv.mask().ellipse(32, 26, 18, 19), T.HOOD)
    cv.part(cv.mask().rect(28, 42, 38, 48), T.SKIN)
    face(cv, T.SKIN, cy=32, jaw=1.05)
    # stubble / beard
    b = cv.mask().poly([(24, 39), (42, 39), (40, 45), (33, 47), (26, 44)])
    cv.part(b, Pal('#5a3e2a', '#6e4e36', '#3e2a1c'))
    # hood front rim shading the brow
    rim = cv.mask().poly([(15, 30), (17, 14), (30, 8), (46, 12), (50, 24), (50, 34), (44, 22), (32, 19),
                          (22, 22), (20, 36)])
    cv.part(rim, T.HOOD)
    for (x, y) in ((22, 12), (25, 10), (40, 10), (44, 13)):
        cv.dot(x, y, T.MOSS.hi)
    eyes(cv, 33, 29, (90, 150, 60, 255), fierce=True)
    cv.dot(35, 36, T.SKIN.sh)
    cv.dot(35, 37, T.SKIN.sh)
    for x in range(31, 36):
        cv.dot(x, 41, T.SKIN.line)
    if finish:
        cv.outline()
    return cv.image()


PORTRAITS = {'kael_emberclaw': kael, 'mira_tidesong': mira, 'thorne_mossguard': thorne}
