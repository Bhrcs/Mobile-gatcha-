"""
hero_roster - the gacha heroes built with hero_gen (all original designs).

FORMS maps form_id -> Spec. Families share a choreography (hero_moves), so the
tiers of one family always have identical animation names / frame counts.
"""
from dataclasses import replace
from pixlib import Pal, hexc
from hero_gen import Spec

P = Pal

# ------------------------------------------------------------------ shared materials
SKIN_FAIR = P('#f2c3a0', '#ffe0c6', '#cc8f72', '#8a5646')
SKIN_WARM = P('#eeb48a', '#ffd6b0', '#c47f5e', '#8a4a3a')
SKIN_TAN = P('#d9a077', '#f0c29c', '#aa6f52', '#6e4332')
SKIN_DEEP = P('#a0684a', '#c08866', '#784a32', '#44281a')
SKIN_PALE = P('#f6d6c4', '#fff0e6', '#d6a896', '#8e6456')
SKIN_OLD = P('#dcaa88', '#f2c8a8', '#b07e62', '#704a38')
BARK_SKIN = P('#8a6a48', '#a88a62', '#624a32', '#34241a')

GOLD = P('#e0b040', '#fff0a0', '#a87c20', '#5c420c')
BRASS = P('#c8a040', '#f2d272', '#8c6a24', '#4c3a12')
SILVER = P('#b8c2cf', '#eef3f8', '#808b9b', '#4c5563')
WOOD = P('#7a5638', '#a27a52', '#553a24', '#2f2013')
DARKWOOD = P('#5a3a22', '#7a5434', '#3e2614', '#22140a')
LEATHER = P('#7a5234', '#9c6c46', '#553822', '#321f12')
BOOT_BROWN = P('#4a3020', '#6a4a32', '#32200f', '#1a1008')
BOOT_DARK = P('#1f1d27', '#3d3a4a', '#15131b', '#0c0b10')

EMBER_FX = [hexc('#ffd35a'), hexc('#ff8a2a'), hexc('#ffef9a')]
WATER_FX = [hexc('#9ff3ff'), hexc('#4fc9e8'), hexc('#e0ffff')]
LEAF_FX = [hexc('#7cc043'), hexc('#4f9a2c'), hexc('#a9dd62')]
PETAL_FX = [hexc('#ffc0d8'), hexc('#f08cb0'), hexc('#fff6fa')]
FROST_FX = [hexc('#e0f8ff'), hexc('#9fe0ff'), hexc('#ffffff')]
GLYPH_FX = [hexc('#6ff0ff'), hexc('#2ab8e0'), hexc('#d8ffff')]

FORMS = {}


def add(sp):
    FORMS[sp.form_id] = sp
    return sp


def evolve(sp, **kw):
    """Copy a spec for the next tier (dict/list fields are copied, then updated)."""
    new = replace(sp, **{k: v for k, v in kw.items() if k not in ('pal_add', 'weapon_add')})
    new.pal = dict(sp.pal)
    new.pal.update(kw.get('pal_add', {}))
    new.weapon = dict(sp.weapon)
    new.weapon.update(kw.get('weapon_add', {}))
    return new


# ================================================================== FIRE
# ---- Rhea: young fire-keeper with a lantern-staff (Support / buffer)
rhea = add(Spec(
    form_id='rhea_flintwhistle', name='Rhea Flintwhistle', family='rhea', tier=1, moves='lantern', build='young',
    skin=SKIN_WARM, eye=(120, 60, 24, 255),
    hair=P('#c85a24', '#ec8440', '#963e16', '#58220a'), hair_style='curly', head=['goggles'],
    tunic=P('#e0782c', '#ffa352', '#b0521c', '#6a2e10'),
    chest=P('#efe0bf', '#fff8e6', '#c6b18c', '#7a6a4e'), chest_style='vest',
    legs=P('#6a4630', '#86603f', '#4a3020', '#2a1a10'), boots=BOOT_BROWN,
    sleeve=P('#e0782c', '#ffa352', '#b0521c', '#6a2e10'), sleeve_b=P('#b0521c', '#d06a2c', '#823810', '#4a1e08'),
    skirt='tabard', skirt_pal=P('#efe0bf', '#fff8e6', '#c6b18c', '#7a6a4e'), belt=LEATHER,
    items=['satchel'],
    weapon=dict(kind='lantern', wood=WOOD, brass=BRASS, len=21, below=8, style='one',
                orb=P('#ffd35a', '#fff6c8', '#ff9a2a', '#a8500f')),
    glow_col=(255, 160, 60), fx=EMBER_FX,
    pal=dict(strap=P('#3a2418', '#553624', '#26160c', '#140a04'), brass=BRASS,
             lens=P('#ffb040', '#ffe08a', '#c87a20', '#6a3a0c'), bag=LEATHER,
             sun=P('#ffd35a', '#fff6c8', '#e0a030', '#8a5a10'), gem=P('#ff6a2a', '#ffe08a', '#c83a10'))))

COAT_RED = P('#b8402a', '#e06444', '#842a1c', '#4c1410')
add(evolve(rhea, form_id='rhea_hearthsong', name='Rhea Hearthsong', tier=2,
           sleeve=COAT_RED, sleeve_b=P('#842a1c', '#a03a26', '#5e1c12', '#340c08'),
           skirt='coat', skirt_pal=COAT_RED, trim=GOLD, cape='tail', cape_pal=COAT_RED, cape_trim=GOLD,
           pauldron=None, items=['satchel', 'gold_trim'],
           weapon_add=dict(style='two')))

SUN_WHITE = P('#f4ead2', '#fffbf0', '#d0c098', '#7c6c48')
add(evolve(rhea, form_id='rhea_sunchoir', name='Rhea Sunchoir', tier=3,
           head=['sun_circlet'], back=['sun_halo'],
           tunic=P('#e8862e', '#ffb050', '#b85e1c', '#6a3210'),
           chest=SUN_WHITE, sleeve=SUN_WHITE, sleeve_b=P('#d0c098', '#e8dcbc', '#a8986c', '#5c5034'),
           skirt='coat', skirt_pal=SUN_WHITE, trim=GOLD,
           cape='long', cape_pal=P('#d8402a', '#ff6a44', '#a02a1c', '#5a1410'), cape_trim=GOLD,
           items=['gold_trim'], aura='spark', boots=P('#8c5a24', '#b07a38', '#643e16', '#361f08'),
           weapon_add=dict(style='sun', wood=P('#e8d8b0', '#fffbe8', '#b8a47a', '#6e5e3c'))))

# ---- Voss: big bald greataxe breaker
VOSS_IRON = P('#4a4652', '#6c6676', '#322f38', '#1a181e')
SOOT = P('#6a666c', '#8a868c', '#4a464c', '#2a282c')
voss = add(Spec(
    form_id='voss_ashmantle', name='Voss Ashmantle', family='voss', tier=1, moves='greataxe', build='heavy',
    skin=SKIN_TAN, eye=(60, 30, 20, 255), hair=P('#8a3a1a', '#a84c26', '#62240c', '#361206'), hair_style='bald',
    beard='full', beard_pal=P('#b8421e', '#e0643a', '#82280e', '#4a1406'),
    tunic=P('#3a3440', '#544c5c', '#26222b', '#141117'), chest=VOSS_IRON, chest_style='breast',
    legs=P('#2e2a32', '#443e4a', '#1e1b22', '#0f0d11'), boots=BOOT_DARK,
    sleeve=SKIN_TAN, sleeve_b=P('#b8845e', '#d0a07a', '#8c5c40', '#583624'), glove=LEATHER,
    skirt='kilt', skirt_pal=P('#4a3a30', '#665044', '#32261e', '#1a130e'), belt=P('#2a2024', '#3e3036', '#1a1216', '#0c080a'),
    pauldron=VOSS_IRON, neck='mantle', neck_pal=SOOT, cape='mantle', cape_pal=SOOT,
    weapon=dict(kind='greataxe', haft=DARKWOOD, metal=P('#4e4a54', '#77717e', '#34303a', '#1c1a20'),
                edge=P('#aab0bc', '#e0e6ee', '#747a86', '#3c4048'), crack=[hexc('#ff7a24'), hexc('#ffc050')],
                up=13, down=8, size=1.25),
    glow_col=(255, 120, 40), fx=EMBER_FX,
    pal=dict(greave=VOSS_IRON)))

MOLTEN = P('#ff7a24', '#ffd060', '#d04a10', '#7a2208')
CHAR = P('#2a2226', '#443840', '#1c161a', '#0e0a0c')
add(evolve(voss, form_id='voss_magmaborn', name='Voss Magmaborn', tier=2,
           head=['horned_helm'], chest=CHAR, tunic=P('#3a2226', '#553038', '#261418', '#12080a'),
           pauldron=CHAR, items=['molten'], neck_pal=P('#4a4046', '#665a60', '#322a2e', '#1a1416'),
           cape_pal=P('#4a4046', '#665a60', '#322a2e', '#1a1416'), aura='spark',
           skirt_pal=P('#3a2a26', '#54403a', '#261a18', '#120c0a'),
           weapon_add=dict(metal=P('#3a2a2a', '#5a4040', '#261a1a', '#120a0a'),
                           edge=MOLTEN, crack=[hexc('#ffd060'), hexc('#ff7a24'), hexc('#fff0a0')], size=1.6,
                           cracks=((-2, 3), (-4, 4), (-3, 2), (-5, 2), (-1, 4), (-6, 3), (-3, 5))),
           pal_add=dict(helm=CHAR, horn=P('#5a4a48', '#8a7470', '#3a2e2e', '#1a1414'), molten=MOLTEN, greave=CHAR)))

# ---- Seraphine: flame-pennant lancer (single ★5 form)
CRIMSON = P('#b01e32', '#e0384a', '#7a1022', '#480814')
add(Spec(
    form_id='seraphine_pyrelance', name='Seraphine Pyrelance', family='seraphine', tier=1, moves='spear',
    build='lithe', skin=SKIN_FAIR, eye=(200, 90, 30, 255),
    hair=P('#f2e2b0', '#fffbe6', '#cdb67a', '#8a7444'), hair_style='ponytail', head=['winged_circlet'],
    tunic=CRIMSON, chest=P('#c42a3c', '#ea5060', '#8a1426', '#4e0a16'), chest_style='plate', trim=GOLD,
    legs=P('#e8e0d8', '#fffaf4', '#bcb2a8', '#726860'), boots=P('#9a1a2a', '#c83044', '#6a1020', '#3a0810'),
    sleeve=CRIMSON, sleeve_b=P('#7a1022', '#9a1a2e', '#560a18', '#30060c'), glove=GOLD,
    skirt='kilt', skirt_pal=CRIMSON, belt=GOLD, pauldron=GOLD, items=['sash'],
    weapon=dict(kind='spear', shaft=P('#e8e0c8', '#fffbe8', '#b8ac90', '#6e6450'), gold=GOLD,
                head=P('#d8dce4', '#ffffff', '#9aa2b0', '#5a6070'), edge=P('#ff8a2a', '#ffe08a', '#e0521c'),
                pennant=P('#ff6a2a', '#ffc050', '#d0381c', '#7a1c0c'), fwd=13, back=9),
    aura='spark', glow_col=(255, 140, 60), fx=EMBER_FX,
    pal=dict(wing=P('#f4f4f0', '#ffffff', '#c8ccd4', '#7a808c'), gem=P('#e0304a', '#ff8a9a', '#a01a2e'),
             tie=GOLD, sash=P('#f4e6b8', '#fffbe8', '#cdb67a', '#8a7444'), greave=GOLD)))

# ================================================================== WATER
# ---- Corin: sailor-guard with a trident and shell buckler (Defender)
TEAL = P('#2a8a8a', '#48b4ac', '#1c6262', '#0e3434')
NAVY = P('#23305c', '#34467e', '#161f3e', '#0c1224')
SHELL_RIM = P('#d88a70', '#f4b49a', '#a8604c', '#643428')
SHELL_FACE = P('#f6dcc8', '#fff4ea', '#d8a890', '#8a5c4c')
CORAL = P('#e8705a', '#ff9c82', '#b44a3c', '#6e2a22')
corin = add(Spec(
    form_id='corin_saltmarsh', name='Corin Saltmarsh', family='corin', tier=1, moves='trident', build='sturdy',
    skin=SKIN_DEEP, eye=(30, 40, 50, 255), hair=P('#2a2220', '#3e3230', '#1a1414', '#0c0a0a'), hair_style='capped',
    beard='stubble', beard_pal=P('#2a2220', '#3e3230', '#1a1414', '#0c0a0a'), head=['bandana'],
    tunic=NAVY, chest=TEAL, chest_style='plate', legs=P('#2c3a66', '#40528a', '#1c2646', '#0e1426'),
    boots=BOOT_BROWN, sleeve=NAVY, sleeve_b=P('#161f3e', '#23305c', '#0e1428', '#060a14'), glove=LEATHER,
    skirt='tabard', skirt_pal=NAVY, belt=LEATHER, pauldron=P('#6a9aa0', '#a0ccd0', '#46707a', '#243c42'),
    weapon=dict(kind='trident', shaft=WOOD, metal=P('#8ab8c0', '#d0f0f4', '#5a8890', '#2e4a50'),
                rim=SHELL_RIM, face=SHELL_FACE, coral=CORAL, shield='shell', r=4.2, fwd=16, back=7,
                iron=P('#6a9aa0', '#a0ccd0', '#46707a', '#243c42')),
    glow_col=(90, 220, 255), fx=WATER_FX,
    pal=dict(bandana=P('#2aa6a0', '#52d0c4', '#1c7470', '#0e3e3e'))))

add(evolve(corin, form_id='corin_reefwarden', name='Corin Reefwarden', tier=2,
           chest=P('#2a9a94', '#4cc4b8', '#1c6c68', '#0e3a38'), trim=CORAL, items=['coral'],
           pauldron=CORAL,
           pal_add=dict(coral=CORAL, pauldron_trim=False, greave=P('#6a9aa0', '#a0ccd0', '#46707a', '#243c42')),
           weapon_add=dict(r=5.4, coral_trim=True, iron_rim=True, metal=P('#9ad0d4', '#e0ffff', '#62989e', '#325058'))))

HELM = P('#3a8a96', '#5cb8c2', '#26606a', '#12343a')
add(evolve(corin, form_id='corin_tidebulwark', name='Corin Tidebulwark', tier=3, build='heavy',
           head=['finned_helm'], hair_style='none', beard='',
           tunic=P('#1c2a54', '#2c3e74', '#121c3a', '#080e20'),
           chest=HELM, chest_style='breast', trim=CORAL, items=['coral'], pauldron=CORAL,
           sleeve=P('#2c3e74', '#40548e', '#1c2a54', '#0e1630'), glove=HELM,
           legs=P('#1c2a54', '#2c3e74', '#121c3a', '#080e20'), boots=HELM,
           aura='drop', aura_glow=40,
           pal_add=dict(helm=HELM, fin=P('#3ab8c8', '#8ae8f0', '#22808e', '#10444c'), visor=hexc('#9ff3ff'),
                        coral=CORAL, pauldron_trim=False, greave=HELM),
           weapon_add=dict(shield='tower', rim=P('#2a6a78', '#4a929e', '#1c4a54', '#0c262c'),
                           face=CORAL, coral=P('#ffd0c0', '#fff4ee', '#e89a88', '#8a4a3e'),
                           rune=hexc('#9ff3ff'), metal=P('#9ad0d4', '#e0ffff', '#62989e', '#325058'), fwd=17)))

# ---- Nerys: agile rogue with twin ice daggers (Attacker)
ICE = P('#bff0ff', '#ffffff', '#7cc8e8', '#3a86a8')
nerys = add(Spec(
    form_id='nerys_frostwake', name='Nerys Frostwake', family='nerys', tier=1, moves='daggers', build='light',
    skin=SKIN_PALE, eye=(60, 150, 210, 255), hair=P('#a8c4dc', '#e4f2ff', '#7894b4', '#48607c'), hair_style='sleek',
    head=['hood_down'], tunic=P('#34405a', '#4a5876', '#232c40', '#121826'),
    chest=P('#4a5a74', '#66789a', '#323e52', '#1a2230'), chest_style='vest',
    legs=P('#2a3246', '#3c465e', '#1c2232', '#0e121a'), boots=P('#1e2434', '#323a50', '#141824', '#0a0c12'),
    sleeve=P('#34405a', '#4a5876', '#232c40', '#121826'), sleeve_b=P('#232c40', '#34405a', '#161c2a', '#0a0e16'),
    glove=P('#1e2434', '#323a50', '#141824', '#0a0c12'), skirt='tabard',
    skirt_pal=P('#2c4a6e', '#44688e', '#1c3250', '#0e1a2c'), belt=P('#5a4a3a', '#76624e', '#3e3226', '#201a14'),
    weapon=dict(kind='daggers', grip=P('#2a2a3a', '#40405a', '#1c1c28', '#0e0e14'), guard=SILVER, ice=ICE,
                len=6, curve=1.2),
    glow_col=(140, 220, 255), fx=FROST_FX,
    pal=dict(hood=P('#2c4a6e', '#44688e', '#1c3250', '#0e1a2c'), scarf=P('#3a6a8e', '#5a8cb0', '#284c6a', '#142a3c'),
             ice=ICE, fur=P('#e8f4fa', '#ffffff', '#b4ccdc', '#6e8aa0'))))

add(evolve(nerys, form_id='nerys_rimefang', name='Nerys Rimefang', tier=2,
           head=['hood_down', 'ice_crown'], items=['frost_mantle'], aura='frost', aura_glow=36,
           tunic=P('#2c3c5e', '#44587e', '#1c2842', '#0e1424'),
           chest=P('#8ab0cc', '#c4e0f2', '#5e84a2', '#324a60'),
           weapon_add=dict(len=9, curve=1.8, ice=P('#d8fbff', '#ffffff', '#8ad8f0', '#3a96b8'))))

# ---- Aldric: elder scholar-priest with an open tome (Support, single ★5)
ROBE = P('#1c3a6e', '#2c5696', '#12264a', '#0a1428')
add(Spec(
    form_id='aldric_deepvow', name='Aldric Deepvow', family='aldric', tier=1, moves='tome', build='robe',
    skin=SKIN_OLD, eye=(40, 90, 140, 255), hair=P('#e8ecf0', '#ffffff', '#b8c0cc', '#6e7684'), hair_style='hooded',
    beard='long', beard_pal=P('#e8ecf0', '#ffffff', '#b8c0cc', '#6e7684'), head=['cowl'],
    tunic=ROBE, chest=P('#2a8aa8', '#48b0cc', '#1c6078', '#0e3444'), chest_style='bib', trim=SILVER,
    legs=ROBE, boots=BOOT_DARK, sleeve=ROBE, sleeve_b=P('#12264a', '#1c3a6e', '#0a1830', '#060c18'),
    skirt='robe', skirt_pal=ROBE, belt=SILVER, items=['glyph_belt'],
    weapon=dict(kind='tome', cover=P('#1e6a78', '#3a92a0', '#124a54', '#08262c'),
                page=P('#f0e8d0', '#fffbf0', '#c8bc9c', '#7c7058'), ink=hexc('#2ab8e0')),
    aura='glyph', aura_glow=34, glow_col=(90, 220, 255), fx=GLYPH_FX,
    pal=dict(cowl=ROBE, gem=P('#4fe0f0', '#d0ffff', '#23a8c4'), cuff=SILVER, cuff_b=SILVER)))

# ================================================================== NATURE
# ---- Wren: young archer (Attacker, ranged)
LEAFP = P('#5a9a34', '#86c850', '#3a6e22', '#1e3c12')
wren = add(Spec(
    form_id='wren_briarshot', name='Wren Briarshot', family='wren', tier=1, moves='bow', build='young',
    skin=SKIN_WARM, eye=(50, 90, 30, 255), hair=P('#8a4a24', '#ac6a3a', '#643216', '#381a0a'), hair_style='capped',
    head=['feather_cap'], tunic=P('#9a7a4c', '#bc9a64', '#725834', '#40301a'),
    chest=P('#4e7e2c', '#6ca440', '#36581c', '#1c300e'), chest_style='vest',
    legs=P('#4a4a2a', '#62623a', '#32321a', '#1a1a0c'), boots=BOOT_BROWN,
    sleeve=P('#9a7a4c', '#bc9a64', '#725834', '#40301a'), sleeve_b=P('#725834', '#8a6c44', '#523e22', '#2c2010'),
    glove=LEATHER, skirt='tabard', skirt_pal=P('#4e7e2c', '#6ca440', '#36581c', '#1c300e'), belt=LEATHER,
    cape='leaf', cape_pal=LEAFP,
    weapon=dict(kind='bow', wood=P('#8a5a30', '#b07a44', '#62401e', '#34200e'), string=P('#e8e0c8', '#fffbe8', '#b8ac90'),
                grip=LEATHER, vine=P('#5aa032', '#8ad050', '#3a7020', '#1e3c10'),
                arrow=P('#c8a878', '#e8d0a0', '#9a7c50'), arrowhead=P('#8a929e', '#d8dee8', '#5a6068'),
                len=14, bend=2.5),
    glow_col=(140, 230, 90), fx=LEAF_FX,
    pal=dict(cap=P('#4a8a2c', '#6cb040', '#305e1c', '#1a3610'), feather=P('#d8503a', '#ff8a6a', '#a8321e', '#5a180c'),
             fletch=P('#d8503a', '#ff8a6a', '#a8321e', '#5a180c'),
             arrow=P('#c8a878', '#e8d0a0', '#9a7c50'), arrowhead=P('#8a929e', '#d8dee8', '#5a6068'),
             quiver=P('#6a4428', '#8c5e38', '#4a2e18', '#28180a'))))

add(evolve(wren, form_id='wren_thornvolley', name='Wren Thornvolley', tier=2, back=['quiver'],
           chest=P('#3e6e24', '#5c9636', '#2a4c16', '#16280a'), pauldron=P('#6a4428', '#8c5e38', '#4a2e18', '#28180a'),
           cape_pal=P('#4e8e2e', '#7abc48', '#346a1e', '#1a3a0e'),
           weapon_add=dict(wood=P('#5a3422', '#7a4c32', '#3e2214', '#20100a'), len=18, bend=3.0, recurve=True,
                           thorns=True, thorn=hexc('#c8d890'), vine=P('#4a9a2c', '#7ac848', '#2e6a1a', '#18380c'))))

add(evolve(wren, form_id='wren_galeleaf', name='Wren Galeleaf', tier=3, back=['quiver'], cape='gale',
           cape_pal=P('#7ac850', '#b0ec7c', '#4e9a30', '#2a5a18'), cape_trim=P('#e8ffd0', '#ffffff', '#b8e0a0'),
           chest=P('#e0d49a', '#fff8d0', '#b0a468', '#6a6234'), pauldron=P('#7ac850', '#b0ec7c', '#4e9a30', '#2a5a18'),
           tunic=P('#3e7a2c', '#5ca040', '#2a5a1c', '#16300e'), sleeve=P('#3e7a2c', '#5ca040', '#2a5a1c', '#16300e'),
           trim=GOLD, aura='leaf', aura_glow=30,
           pal_add=dict(feather=P('#f2d060', '#fff4b0', '#c8a030', '#6e5410'), fletch=P('#f2d060', '#fff4b0', '#c8a030')),
           weapon_add=dict(wood=P('#6a4a2a', '#8a6a3e', '#4a321a', '#26180c'), len=18, bend=3.0, recurve=True,
                           thorns=True, thorn=hexc('#fff4b0'), glowing=True,
                           glow_wood=P('#c8f080', '#f8ffd8', '#8ac850', '#4a7a24'),
                           vine=P('#f2d060', '#fff4b0', '#c8a030', '#6e5410'))))

# ---- Faye: gentle blossom healer
PINK = P('#f08cb0', '#ffc0d8', '#c05a84', '#7a2c50')
MOSS = P('#6a9a44', '#90c060', '#4a7030', '#28401a')
faye = add(Spec(
    form_id='faye_lumenbloom', name='Faye Lumenbloom', family='faye', tier=1, moves='blossom', build='light',
    skin=SKIN_FAIR, eye=(70, 130, 60, 255), hair=P('#b0703e', '#d4955c', '#824e26', '#4a2a10'), hair_style='wavy',
    head=['flower_crown'], tunic=PINK, chest=MOSS, chest_style='bib',
    legs=P('#f0e0d4', '#fff6ee', '#c8b4a4', '#7c6a5c'), boots=P('#4a7030', '#6a9a44', '#32501e', '#1a2a0e'),
    sleeve=PINK, sleeve_b=P('#c05a84', '#e07aa2', '#8e3c60', '#521e36'),
    skirt='dress', skirt_pal=PINK, trim=MOSS, belt=MOSS,
    weapon=dict(kind='blossom', wood=P('#a88a5c', '#ccae7c', '#7c643e', '#44361e'), vine=MOSS,
                petal=P('#ffb0cc', '#fff0f6', '#e07aa2', '#8e3c60'), core=P('#ffd35a', '#fff6c8', '#e0a030'),
                len=16, r=3.0, petals=5),
    glow_col=(255, 170, 210), fx=PETAL_FX,
    pal=dict(leafp=MOSS, petal=P('#f08cb0', '#ffc0d8', '#c05a84', '#7a2c50'),
             petal2=P('#fff0f6', '#ffffff', '#e8c8d4', '#9a7a86'), pollen=hexc('#ffd35a'))))

add(evolve(faye, form_id='faye_everbloom', name='Faye Everbloom', tier=2, head=['bloom_crown'], cape='petal_wings',
           chest=P('#7aaa4c', '#a0d070', '#567c34', '#2c441a'), items=['blossoms'], aura='petal', aura_glow=30,
           weapon_add=dict(r=3.8, petals=6, glowing=True, petal=P('#ffc4da', '#ffffff', '#f08cb0', '#a04a70'))))

# ---- Gorran: bark-skinned giant-kin with a great club (Breaker, single ★5)
MOSSG = P('#5e9a36', '#88c450', '#3e6e22', '#20400f')
add(Spec(
    form_id='gorran_oakheart', name='Gorran Oakheart', family='gorran', tier=1, moves='club', build='giant',
    skin=BARK_SKIN, eye=(255, 210, 90, 255), hair=MOSSG, hair_style='mossy', beard='moss', beard_pal=MOSSG,
    tunic=BARK_SKIN, legs=BARK_SKIN, boots=P('#5a4430', '#76583e', '#3e2e20', '#221810'),
    sleeve=BARK_SKIN, sleeve_b=P('#6a5036', '#86684a', '#4a3624', '#281c12'),
    glove=P('#7a7a6a', '#a0a08c', '#58584c', '#30302a'),
    skirt='loin', skirt_pal=P('#4e8a2e', '#72b048', '#34601e', '#1a340e'),
    belt=P('#6a5a3a', '#8a7650', '#4a3e26', '#282012'), items=['bark'],
    weapon=dict(kind='club', wood=P('#6e4a2c', '#8e6640', '#4e3220', '#2a1a10'),
                band=P('#6a6a70', '#9a9aa0', '#4a4a50', '#26262a'), moss=MOSSG, knot=MOSSG, len=16,
                bloom=P('#f0a0c0', '#ffe0ec', '#c06a8e')),
    aura='leaf', aura_glow=0, glow_col=(130, 230, 90), fx=LEAF_FX,
    pal=dict(bloom=P('#f0a0c0', '#ffe0ec', '#c06a8e'))))

FAMILIES = {
    'rhea': ['rhea_flintwhistle', 'rhea_hearthsong', 'rhea_sunchoir'],
    'voss': ['voss_ashmantle', 'voss_magmaborn'],
    'seraphine': ['seraphine_pyrelance'],
    'corin': ['corin_saltmarsh', 'corin_reefwarden', 'corin_tidebulwark'],
    'nerys': ['nerys_frostwake', 'nerys_rimefang'],
    'aldric': ['aldric_deepvow'],
    'wren': ['wren_briarshot', 'wren_thornvolley', 'wren_galeleaf'],
    'faye': ['faye_lumenbloom', 'faye_everbloom'],
    'gorran': ['gorran_oakheart'],
}
