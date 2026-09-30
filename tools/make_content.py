"""
Cinderbound content generator (Phase 4).

Writes the data-driven game content as JSON under data/ so every number lives
in one reviewable place. The JSON files are the game's source of truth at
runtime; re-run this script after editing the tables below.

    python3 tools/make_content.py

Writes: data/characters/*.json, data/skills/hero_skills.json,
        data/skills/enemy_skills.json, data/enemies/*.json, data/items/items.json,
        data/drop_tables.json, data/statuses.json, data/stages/ashroot_wilds.json,
        data/stages/saltglass_reach.json, data/towers/*.json, data/summon.json,
        data/missions.json, data/login_rewards.json, data/progression.json
"""
import copy
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Content'))  # game content root
D = os.path.join(ROOT, 'data')


def write(rel, obj):
    path = os.path.join(D, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(obj, f, indent=1)


def read(rel):
    with open(os.path.join(D, rel)) as f:
        return json.load(f)


ELEMENTS = ('fire', 'water', 'nature')
MAX_LEVEL = {3: 15, 4: 25, 5: 35}
ICON = 'res://assets/icons/%s.png'

# ====================================================================== statuses
STATUSES = {
    "burn": {"name": "Burn", "negative": True, "kind": "dot", "dot_percent_max_hp": 0.05, "icon": ICON % "status_burn",
             "color": "#ff7a2a", "desc": "Loses 5% max HP at the end of each turn."},
    "poison": {"name": "Poison", "negative": True, "kind": "dot", "dot_percent_max_hp": 0.04, "icon": ICON % "status_poison",
               "color": "#b06ae0", "desc": "Loses 4% max HP at the end of each turn."},
    "regen": {"name": "Regen", "negative": False, "kind": "hot", "icon": ICON % "status_regen", "color": "#8ae05a",
              "desc": "Recovers HP at the end of each turn."},
    "def_up": {"name": "DEF Up", "negative": False, "kind": "stat_mod", "stat": "def", "sign": 1,
               "icon": ICON % "status_def_up", "color": "#7ae05a", "desc": "DEF is raised."},
    "atk_up": {"name": "ATK Up", "negative": False, "kind": "stat_mod", "stat": "atk", "sign": 1,
               "icon": ICON % "status_atk_up", "color": "#ffb04a", "desc": "ATK is raised."},
    "rec_up": {"name": "REC Up", "negative": False, "kind": "stat_mod", "stat": "rec", "sign": 1,
               "icon": ICON % "status_rec_up", "color": "#ff8ab0", "desc": "REC (healing power) is raised."},
    "atk_down": {"name": "ATK Down", "negative": True, "kind": "stat_mod", "stat": "atk", "sign": -1,
                 "icon": ICON % "status_atk_down", "color": "#d06a6a", "desc": "ATK is lowered."},
    "def_down": {"name": "DEF Down", "negative": True, "kind": "stat_mod", "stat": "def", "sign": -1,
                 "icon": ICON % "status_def_down", "color": "#d0a06a", "desc": "DEF is lowered."},
    "shield": {"name": "Shield", "negative": False, "kind": "shield", "icon": ICON % "status_shield", "color": "#8ad8ff",
               "desc": "Absorbs damage until broken."},
    "damage_reduction": {"name": "Bastion", "negative": False, "kind": "damage_reduction",
                         "icon": ICON % "status_guard_wall", "color": "#c8a878", "desc": "Takes less damage."},
    "taunt": {"name": "Provoke", "negative": False, "kind": "taunt", "icon": ICON % "status_taunt", "color": "#ff5a4a",
              "desc": "Draws enemy attacks."},
    "charging": {"name": "Charging", "negative": False, "kind": "charge", "icon": ICON % "status_charge",
                 "color": "#ffe04a", "desc": "Gathering power for a devastating attack next turn!"},
    # ---- Phase 7: boss mechanics. "dispellable": False = Dispel cannot remove it (shown in its description).
    "flame_armor": {"name": "Flame Armor", "negative": False, "kind": "damage_reduction", "dispellable": False,
                    "removed_by_break": True, "icon": ICON % "status_guard_wall", "color": "#ff9a3a",
                    "desc": "Takes 40% less damage. Cannot be dispelled - BREAK the foe to shatter it."},
    "broken": {"name": "Broken", "negative": True, "kind": "damage_taken_up", "icon": ICON % "status_def_down",
               "color": "#ffe070", "desc": "BROKEN: loses its turn, its charged attack is cancelled and it takes "
                                            "50% more damage."},
    "ember_fervor": {"name": "Ember Fervor", "negative": False, "kind": "stat_mod", "stat": "atk", "sign": 1,
                     "dispellable": False, "icon": ICON % "status_atk_up", "color": "#ff6a2a",
                     "desc": "ATK raised by the Ember Totems. Destroy the Totems to remove it."},
}

# Phase 7 stacking rules (see docs/dev/BALANCE-GUIDE.md): the same status never stacks - the stronger value and the
# longer duration are kept. Different stat buffs add up, capped at +-status_stat_cap.

# ====================================================================== items
def item(name, icon, cat, rarity, desc, use, sort, **kw):
    d = {"name": name, "icon": ICON % icon, "category": cat, "rarity": rarity, "description": desc, "use": use,
         "sort": sort}
    d.update(kw)
    return d


ITEMS = {
    # evolution materials (tier 1 fragment, tier 2 core, tier 3 crystal) per element
    "ember_fragment": item("Ember Fragment", "ember_fragment", "material", 1,
                           "A splinter of stone that still holds fire.", "Evolves Fire heroes (3* to 4*).", 10, element="fire"),
    "flame_core": item("Flame Core", "flame_core", "material", 2, "A heart of living flame in a crystal shell.",
                       "Evolves Fire heroes.", 11, element="fire"),
    "infernal_crystal": item("Infernal Crystal", "infernal_crystal", "material", 3,
                             "Burns without fuel. Found high in the Ember Tower.", "Evolves Fire heroes (4* to 5*).", 12,
                             element="fire"),
    "tide_fragment": item("Tide Fragment", "tide_fragment", "material", 1, "Sea-glass that is always cool and damp.",
                          "Evolves Water heroes (3* to 4*).", 20, element="water"),
    "current_core": item("Current Core", "current_core", "material", 2, "A sphere with a tide trapped inside.",
                         "Evolves Water heroes.", 21, element="water"),
    "abyss_crystal": item("Abyss Crystal", "abyss_crystal", "material", 3, "Dark blue glass from the deep tower halls.",
                          "Evolves Water heroes (4* to 5*).", 22, element="water"),
    "sprout_fragment": item("Sprout Fragment", "sprout_fragment", "material", 1, "A green crystal with a seedling inside.",
                            "Evolves Nature heroes (3* to 4*).", 30, element="nature"),
    "verdant_core": item("Verdant Core", "verdant_core", "material", 2, "Warm, and it slowly grows moss.",
                         "Evolves Nature heroes.", 31, element="nature"),
    "ancient_seed": item("Ancient Seed", "ancient_seed", "material", 3, "A seed older than the Wilds themselves.",
                         "Evolves Nature heroes (4* to 5*).", 32, element="nature"),
    "prism_shard": item("Prism Shard", "prism_shard", "material", 3, "Holds every colour at once. Very rare.",
                        "Needed for every 5* evolution.", 40),
    # training
    "ember_wisp": item("Ember Wisp", "ember_wisp", "training", 1, "A playful spark of experience.",
                       "Training: 600 EXP (+50% for Fire heroes).", 50, xp=600, element="fire"),
    "tide_wisp": item("Tide Wisp", "tide_wisp", "training", 1, "A droplet of distilled experience.",
                      "Training: 600 EXP (+50% for Water heroes).", 51, xp=600, element="water"),
    "verdant_wisp": item("Verdant Wisp", "verdant_wisp", "training", 1, "A seed-light of experience.",
                         "Training: 600 EXP (+50% for Nature heroes).", 52, xp=600, element="nature"),
    "radiant_wisp": item("Radiant Wisp", "radiant_wisp", "training", 2, "A bright wisp any hero can learn from.",
                         "Training: 2,500 EXP for any hero.", 53, xp=2500),
    "spark_sigil": item("Spark Sigil", "spark_sigil", "training", 2, "A sigil that teaches a hero to channel Burst.",
                        "Burst training: +3 Burst EXP.", 54, burst_xp=3),
    # items / other
    "minor_healing_herb": item("Minor Healing Herb", "herb", "item", 1,
                               "A bitter forest herb that knits small wounds.",
                               "Kept for battle items in a future update.", 60),
}
LEGACY_ITEMS = {"fire_shard": "ember_fragment", "water_shard": "tide_fragment", "nature_shard": "sprout_fragment"}
FRAG = {"fire": "ember_fragment", "water": "tide_fragment", "nature": "sprout_fragment"}
CORE = {"fire": "flame_core", "water": "current_core", "nature": "verdant_core"}
CRYS = {"fire": "infernal_crystal", "water": "abyss_crystal", "nature": "ancient_seed"}
WISP = {"fire": "ember_wisp", "water": "tide_wisp", "nature": "verdant_wisp"}

# ====================================================================== drop tables
def drops(*entries):
    return [dict(zip(("item", "chance", "min", "max"), e)) for e in entries]


DROP_TABLES = {}
for el in ELEMENTS:
    DROP_TABLES[f"{el}_common"] = {"rolls": drops((FRAG[el], 0.22, 1, 1), ("minor_healing_herb", 0.10, 1, 1))}
    DROP_TABLES[f"{el}_uncommon"] = {"rolls": drops((FRAG[el], 0.35, 1, 2), (WISP[el], 0.10, 1, 1))}
    DROP_TABLES[f"{el}_elite"] = {"guaranteed": drops((FRAG[el], 1, 1, 2)),
                                  "rolls": drops((CORE[el], 0.25, 1, 1), (WISP[el], 0.35, 1, 1))}
    DROP_TABLES[f"{el}_boss"] = {"guaranteed": drops((CORE[el], 1, 1, 1), (WISP[el], 1, 1, 2)),
                                 "rolls": drops((CRYS[el], 0.15, 1, 1), ("radiant_wisp", 0.2, 1, 1))}

# ====================================================================== hero families
# role templates at 3* Lv1: hp atk def rec  / growth per level
ROLE_STATS = {
    "attacker": ((720, 145, 80, 70), (28, 5, 3, 2)),
    "healer": ((650, 100, 85, 150), (24, 3, 3, 5)),
    "defender": ((900, 115, 150, 75), (34, 3, 5, 2)),
    "support": ((700, 110, 95, 120), (26, 3, 3, 4)),
    "breaker": ((800, 135, 105, 70), (30, 5, 4, 2)),
}
CLASS_OF = {"attacker": "ATTACKER", "healer": "HEALER", "defender": "DEFENDER", "support": "SUPPORT",
            "breaker": "BREAKER"}


def stat_block(role, rarity, start_rarity, tweak=None):
    """Stats of a form. Evolved/high-rarity forms start near the previous form's cap."""
    (b, g) = ROLE_STATS[role]
    base = list(b)
    growth = list(g)
    if tweak:
        base = [int(x * t) for x, t in zip(base, tweak)]
    r = 3
    while r < rarity:
        cap = [base[i] + growth[i] * (MAX_LEVEL[r] - 1) for i in range(4)]
        base = [int(c * 1.06) for c in cap]
        growth = [max(1, int(round(x * 1.18))) for x in growth]
        r += 1
    keys = ("hp", "atk", "def", "rec")
    return ({k: base[i] for i, k in enumerate(keys)} | {"spd": 60 + {"attacker": 45, "healer": 30, "defender": 5,
                                                                   "support": 25, "breaker": 20}[role]},
            {k: growth[i] for i, k in enumerate(keys)} | {"spd": 0})


# owner-supplied sheets (tools/import_kael.py): ~128 px bodies drawn at x2 instead of 48 px sheets at x8
IMPORTED_SPRITES = {"kael_emberclaw": 2, "kael_blazeheart": 2, "kael_cinderlord": 2}


def sprite(form_id, scale=8):
    base = f"res://assets/characters/{form_id}/{form_id}_sheet"
    return {"sheet": base + ".png", "meta": base + ".json", "scale": IMPORTED_SPRITES.get(form_id, scale)}


# family: element, role, start rarity, forms [(form_id, name, rarity, normal, burst)], passive, leader, lore
FAMILIES = {
    "kael": dict(element="fire", role="attacker", starter=True, weapon="Sword", forms=[
        ("kael_emberclaw", "Kael Emberclaw", 3, "ember_slash", "inferno_break"),
        ("kael_blazeheart", "Kael Blazeheart", 4, "ember_slash", "inferno_break_ii"),
        ("kael_cinderlord", "Kael Cinderlord", 5, "ember_slash", "cinder_cataclysm")],
        passive=("Ember Rush", "ATK +{v}% while HP is above 70%.",
                 [{"kind": "stat_up", "stat": "atk", "value": [0.10, 0.12, 0.15], "condition": "hp_above", "threshold": 0.7}]),
        leader=("Hearthfire Vanguard", "Fire allies gain +{v}% ATK.",
                [{"stat": "atk", "value": [0.08, 0.10, 0.12], "element": "fire"}]),
        lore="Kael grew up hauling coal in the smelting camps on the edge of the Wilds. When the embers under "
             "Ashroot began to stir, he traded his shovel for a blade forged from a cooled cinder.",
        desc="A young sellsword who fights up close. Hits hard and fast."),
    "rhea": dict(element="fire", role="support", weapon="Lantern staff", forms=[
        ("rhea_flintwhistle", "Rhea Flintwhistle", 3, "lantern_spark", "hearthlight_hymn"),
        ("rhea_hearthsong", "Rhea Hearthsong", 4, "lantern_spark", "hearthlight_hymn_ii"),
        ("rhea_sunchoir", "Rhea Sunchoir", 5, "lantern_spark", "sunchoir_anthem")],
        passive=("Kindling", "Allies' Burst gauges fill {v}% faster.",
                 [{"kind": "burst_gain_up", "value": [0.10, 0.12, 0.15], "scope": "allies"}]),
        leader=("Lamplighter's Lead", "All allies gain +{v}% Burst charge.",
                [{"kind": "burst_gain_up", "value": [0.08, 0.10, 0.12]}]),
        lore="A lamp-tender's daughter who talks to the flames she carries. Her lantern has never gone out, "
             "not even in the rain.",
        desc="A cheerful fire-keeper. Her songs sharpen every blade in the squad."),
    "voss": dict(element="fire", role="breaker", weapon="Greataxe", forms=[
        ("voss_ashmantle", "Voss Ashmantle", 4, "ash_cleave", "rending_quake"),
        ("voss_magmaborn", "Voss Magmaborn", 5, "ash_cleave", "magma_sunder")],
        passive=("Crushing Weight", "Deals +{v}% damage to foes with lowered DEF or ATK.",
                 [{"kind": "damage_vs_debuffed", "value": [0.20, 0.25]}]),
        leader=("Forge Wall", "All allies gain +{v}% max HP.", [{"stat": "hp", "value": [0.06, 0.08]}]),
        lore="A smith who swore never to lift a weapon again - until the Wilds burned his forge. He quenched "
             "his greataxe in the ashes and walked out to find whoever lit the fire.",
        desc="A towering breaker. Shatters defences so others can finish the job."),
    "seraphine": dict(element="fire", role="attacker", weapon="Pennant spear", forms=[
        ("seraphine_pyrelance", "Seraphine Pyrelance", 5, "pyre_thrust", "phoenix_lance")],
        passive=("Blazing Resolve", "Critical hit chance +{v}%.", [{"kind": "crit_up", "value": [0.10]}]),
        leader=("Crimson Charge", "Fire allies gain +{v}% ATK.", [{"stat": "atk", "value": [0.12]}]),
        lore="Captain of a disbanded lancer order, she still flies its pennant from her spear. Nobody has "
             "seen her lose a duel - she simply refuses to.",
        desc="A peerless lancer. Seven-strike Burst that melts single targets."),
    "mira": dict(element="water", role="healer", starter=True, weapon="Crystal staff", forms=[
        ("mira_tidesong", "Mira Tidesong", 3, "tidal_bolt", "restoring_current"),
        ("mira_tidecaller", "Mira Tidecaller", 4, "tidal_bolt", "restoring_current_ii"),
        ("mira_wavesage", "Mira Wavesage", 5, "tidal_bolt", "wavesong_renewal")],
        passive=("Flowing Grace", "Healing received by allies +{v}%.",
                 [{"kind": "heal_received_up", "value": [0.10, 0.12, 0.15], "scope": "allies"}]),
        leader=("Tidal Blessing", "All allies gain +{v}% REC.", [{"stat": "rec", "value": [0.08, 0.10, 0.12]}]),
        lore="Mira follows the rivers from spring to sea, mending whoever she finds along the way. She says "
             "water remembers everyone it has touched.",
        desc="A wandering water mage. Keeps allies standing with tides of healing."),
    "corin": dict(element="water", role="defender", weapon="Trident & shell buckler", forms=[
        ("corin_saltmarsh", "Corin Saltmarsh", 3, "trident_jab", "tidal_bulwark"),
        ("corin_reefwarden", "Corin Reefwarden", 4, "trident_jab", "tidal_bulwark_ii"),
        ("corin_tidebulwark", "Corin Tidebulwark", 5, "trident_jab", "reef_aegis")],
        passive=("Steady Keel", "Own DEF +{v}%.", [{"kind": "stat_up", "stat": "def", "value": [0.10, 0.12, 0.15]}]),
        leader=("Harbor Line", "Water allies gain +{v}% DEF.",
                [{"stat": "def", "value": [0.08, 0.10, 0.12], "element": "water"}]),
        lore="A harbour guard from the salt-flats who has never abandoned a post. His buckler is a giant "
             "shell he pulled from a wreck with his bare hands.",
        desc="A sturdy sailor-guard. Shields the whole squad and draws the enemy's fury."),
    "nerys": dict(element="water", role="attacker", weapon="Twin ice daggers", forms=[
        ("nerys_frostwake", "Nerys Frostwake", 4, "frost_flurry", "rimefang_waltz"),
        ("nerys_rimefang", "Nerys Rimefang", 5, "frost_flurry", "glacial_requiem")],
        passive=("Cold Precision", "Deals +{v}% damage to foes below 50% HP.",
                 [{"kind": "damage_vs_low_hp", "value": [0.15, 0.20], "threshold": 0.5}]),
        leader=("Frostbite Pact", "Water allies gain +{v}% ATK.",
                [{"stat": "atk", "value": [0.08, 0.10], "element": "water"}]),
        lore="A courier who runs the frozen passes no one else will. The daggers are made from icicles that "
             "never melt; she will not say where she found them.",
        desc="A swift duelist. Many quick hits and a Burst that weakens the target."),
    "aldric": dict(element="water", role="support", weapon="Tide tome", forms=[
        ("aldric_deepvow", "Aldric Deepvow", 5, "glyph_bolt", "deepvow_litany")],
        passive=("Tidal Ward", "All allies take {v}% less damage.",
                 [{"kind": "damage_taken_down", "value": [0.06], "scope": "allies"}]),
        leader=("Keeper's Vigil", "All allies gain +{v}% max HP.", [{"stat": "hp", "value": [0.10]}]),
        lore="The last keeper of a drowned library, Aldric copied every book into his memory before the sea "
             "took the shelves. He reads the tides the way others read letters.",
        desc="An elder scholar. Weakens every foe while bolstering allies."),
    "thorne": dict(element="nature", role="defender", starter=True, weapon="Hammer & bark shield", forms=[
        ("thorne_mossguard", "Thorne Mossguard", 3, "root_hammer", "ancient_bastion"),
        ("thorne_oakwarden", "Thorne Oakwarden", 4, "root_hammer", "ancient_bastion_ii"),
        ("thorne_ancientroot", "Thorne Ancientroot", 5, "root_hammer", "worldroot_citadel")],
        passive=("Rooted Guard", "Guarding reduces damage by an extra {v}%.",
                 [{"kind": "guard_bonus", "value": [0.15, 0.20, 0.25]}]),
        leader=("Deep Roots", "Nature allies gain +{v}% DEF.",
                [{"stat": "def", "value": [0.08, 0.10, 0.12], "element": "nature"}]),
        lore="Raised by the old grove-wardens, Thorne speaks little and plants a seed wherever a fight ends. "
             "His shield is a slab of living bark that still grows.",
        desc="A forest guardian with a living-bark shield. Soaks up punishment."),
    "wren": dict(element="nature", role="attacker", weapon="Briar bow", forms=[
        ("wren_briarshot", "Wren Briarshot", 3, "briar_shot", "thorn_volley"),
        ("wren_thornvolley", "Wren Thornvolley", 4, "briar_shot", "thorn_volley_ii"),
        ("wren_galeleaf", "Wren Galeleaf", 5, "briar_shot", "galeleaf_tempest")],
        passive=("Keen Eye", "Critical hit chance +{v}%.", [{"kind": "crit_up", "value": [0.06, 0.08, 0.10]}]),
        leader=("Hunter's Mark", "Nature allies gain +{v}% ATK.",
                [{"stat": "atk", "value": [0.08, 0.10, 0.12], "element": "nature"}]),
        lore="A village scout who can split a hanging leaf at a hundred paces. Wren keeps a feather from every "
             "bird that ever led her home.",
        desc="A young archer. Rains arrows on every enemy at once."),
    "faye": dict(element="nature", role="healer", weapon="Blossom wand", forms=[
        ("faye_lumenbloom", "Faye Lumenbloom", 4, "petal_dart", "bloomsong"),
        ("faye_everbloom", "Faye Everbloom", 5, "petal_dart", "everbloom_chorus")],
        passive=("Gentle Bloom", "Allies recover {v}% max HP at the end of each turn.",
                 [{"kind": "regen", "value": [0.02, 0.03], "scope": "allies"}]),
        leader=("Garden Grace", "All allies gain +{v}% REC.", [{"stat": "rec", "value": [0.10, 0.12]}]),
        lore="Faye tends the moon-gardens at the edge of the Wilds, where flowers open only for the injured. "
             "She is gentler than anyone - until someone steps on her seedlings.",
        desc="A blossom healer. Heals over time and keeps the squad topped up."),
    "gorran": dict(element="nature", role="breaker", weapon="Great oak club", forms=[
        ("gorran_oakheart", "Gorran Oakheart", 5, "oakheart_smash", "grove_quake")],
        passive=("Bark Hide", "Takes {v}% less damage.", [{"kind": "damage_taken_down", "value": [0.10]}]),
        leader=("Oakheart Stand", "Nature allies gain +{v}% max HP.",
                [{"stat": "hp", "value": [0.10], "element": "nature"}]),
        lore="A grove-giant who slept for a century in a hollow hill. He woke up because the ground grew warm, "
             "and he does not like being woken.",
        desc="A giant of living bark. Quakes the ground and breaks every enemy's defence."),
}
STARTER_TWEAKS = {"kael": None, "mira": None, "thorne": None}
FAMILY_ORDER = ["kael", "rhea", "voss", "seraphine", "mira", "corin", "nerys", "aldric", "thorne", "wren", "faye",
                "gorran"]

# evolution costs (per step, keyed by target rarity)
EVO_COST = {4: dict(gold=2500, frag=5, core=2), 5: dict(gold=15000, core=8, crys=3, prism=1)}


def fmt(desc, effects, tier):
    v = None
    for e in effects:
        if isinstance(e.get("value"), list):
            v = e["value"][min(tier, len(e["value"]) - 1)]
            break
    return desc.replace("{v}", str(int(round(v * 100)))) if v is not None else desc


def pick(effects, tier):
    out = []
    for e in effects:
        e = dict(e)
        if isinstance(e.get("value"), list):
            e["value"] = e["value"][min(tier, len(e["value"]) - 1)]
        out.append(e)
    return out


def build_characters():
    chars = {}
    for fam_id in FAMILY_ORDER:
        f = FAMILIES[fam_id]
        forms = f["forms"]
        start_r = forms[0][2]
        for i, (fid, name, rarity, normal, burst) in enumerate(forms):
            base, growth = stat_block(f["role"], rarity, start_r)
            evo = None
            if i + 1 < len(forms):
                nxt = forms[i + 1]
                c = EVO_COST[nxt[2]]
                mats = {}
                if nxt[2] == 4:
                    mats[FRAG[f["element"]]] = c["frag"]
                    mats[CORE[f["element"]]] = c["core"]
                else:
                    mats[CORE[f["element"]]] = c["core"]
                    mats[CRYS[f["element"]]] = c["crys"]
                    mats["prism_shard"] = c["prism"]
                evo = {"into": nxt[0], "gold": c["gold"], "materials": mats}
            ptier = i if len(forms) > 1 else 0
            chars[fid] = {
                "id": fid, "family": fam_id, "name": name, "element": f["element"],
                "role": f["role"].capitalize(), "class": CLASS_OF[f["role"]], "rarity": rarity,
                "form_index": i, "forms": [x[0] for x in forms],
                "starter": bool(f.get("starter")) and i == 0, "level": 1, "max_level": MAX_LEVEL[rarity],
                "experience": 0, "base_stats": base, "growth": growth,
                "normal_attack": normal, "burst": burst,
                "passive": {"name": f["passive"][0], "description": fmt(f["passive"][1], f["passive"][2], ptier),
                            "effects": pick(f["passive"][2], ptier)},
                "leader_skill": {"name": f["leader"][0], "description": fmt(f["leader"][1], f["leader"][2], ptier),
                                 "effects": pick(f["leader"][2], ptier)},
                "evolution": evo,
                "sprite": sprite(fid), "portrait": f"res://assets/characters/{fid}/{fid}_portrait.png",
                "weapon": f["weapon"], "description": f["desc"], "lore": f["lore"],
            }
    return chars


# ====================================================================== hero skills
def phase7_skills(hs):
    """Breakers' Bursts also Dispel one buff (Phase 7)."""
    for sid in ("rending_quake", "magma_sunder", "grove_quake"):
        hs[sid].setdefault("effects", []).append({"type": "dispel", "count": 1, "on": "target"})
        hs[sid]["description"] += " Dispels 1 buff."
    return hs


def atk(name, desc, power, hits, motion, anim_frames=None, **kw):
    d = {"name": name, "kind": "normal", "description": desc, "target": "enemy_single", "power": power, "hits": hits,
         "motion": motion, "anim": "attack"}
    d.update(kw)
    return d


def burst(name, desc, target, power, hits, motion, level_bonus, **kw):
    d = {"name": name, "kind": "burst", "description": desc, "target": target, "power": power, "hits": hits,
         "motion": motion, "anim": "burst", "level_bonus": level_bonus}
    d.update(kw)
    return d


FX = dict(fire=("hit_fire", "fire"), water=("hit_water", "water_hit"), nature=("hit_nature", "nature"))

HERO_SKILLS = {
    # ------------------------------------------------ Kael (existing timings)
    "ember_slash": atk("Ember Slash", "Rushes in and cuts twice. 100% ATK over 2 hits.", 1.0, 2, "melee",
                       hit_frames=[2, 4], hit_effect="slash_ember", impact_effect="hit_spark", sfx_hit="sword"),
    "inferno_break": burst("Inferno Break", "Three rapid strikes and a heavy downward slash. 220% ATK over 6 hits, "
                           "20% chance to Burn.", "enemy_single", 2.2, 6, "melee", {"power": 0.12, "chance": 0.05},
                           hit_weights=[1, 1, 1, 1.5, 1.5, 2], hit_frames=[3, 5, 7, 9, 9, 9], burst_fx="ember_rush",
                           hit_effect="slash_ember", final_effect="slash_heavy", impact_effect="hit_fire", sfx_hit="sword",
                           shake=1.0, effects=[{"type": "status", "status": "burn", "chance": 0.2, "duration": 3,
                                                "on": "target"}]),
    "inferno_break_ii": burst("Inferno Break II", "A hotter Inferno Break. 270% ATK over 6 hits, 35% chance to Burn.",
                              "enemy_single", 2.7, 6, "melee", {"power": 0.14, "chance": 0.05},
                              hit_weights=[1, 1, 1, 1.5, 1.5, 2.2], hit_frames=[3, 5, 7, 9, 9, 9], burst_fx="ember_rush",
                              hit_effect="slash_ember", final_effect="slash_heavy", impact_effect="hit_fire",
                              sfx_hit="sword", shake=1.0,
                              effects=[{"type": "status", "status": "burn", "chance": 0.35, "duration": 3,
                                        "on": "target"}]),
    "cinder_cataclysm": burst("Cinder Cataclysm", "Kael's finishing art: 340% ATK over 6 hits, 50% Burn, and his ATK "
                              "rises 20% for 2 turns.", "enemy_single", 3.4, 6, "melee", {"power": 0.16, "value": 0.03},
                              hit_weights=[1, 1, 1, 1.5, 1.5, 2.6], hit_frames=[3, 5, 7, 9, 9, 9], burst_fx="ember_rush",
                              hit_effect="slash_ember", final_effect="slash_heavy", impact_effect="hit_fire",
                              sfx_hit="sword", shake=1.2,
                              effects=[{"type": "status", "status": "burn", "chance": 0.5, "duration": 3, "on": "target"},
                                       {"type": "status", "status": "atk_up", "value": 0.2, "duration": 2, "chance": 1.0,
                                        "on": "self"}]),
    # ------------------------------------------------ Rhea
    "lantern_spark": atk("Lantern Spark", "Flicks a spark from her lantern. 90% ATK over 2 hits.", 0.9, 2, "ranged",
                         release_frame=3, projectile="ember_bolt", impact_effect="hit_fire", sfx_cast="fire",
                         sfx_hit="fire"),
    "hearthlight_hymn": burst("Hearthlight Hymn", "All allies gain +20% ATK for 3 turns and recover 10% max HP.",
                              "ally_all", 0, 0, "self", {"value": 0.03, "heal": 0.02}, release_frame=5,
                              field_effect="buff_rise", sfx_cast="fire", burst_fx="hearth_hymn",
                              effects=[{"type": "status", "status": "atk_up", "value": 0.2, "duration": 3, "chance": 1.0,
                                        "on": "allies"},
                                       {"type": "heal", "percent_max_hp": 0.10, "rec_multiplier": 0.3, "on": "allies"}]),
    "hearthlight_hymn_ii": burst("Hearthlight Hymn II", "All allies gain +25% ATK for 3 turns, recover 12% max HP and "
                                 "gain 10 Burst.", "ally_all", 0, 0, "self", {"value": 0.03, "burst": 3},
                                 release_frame=5, field_effect="buff_rise", sfx_cast="fire", burst_fx="hearth_hymn",
                                 effects=[{"type": "status", "status": "atk_up", "value": 0.25, "duration": 3,
                                           "chance": 1.0, "on": "allies"},
                                          {"type": "heal", "percent_max_hp": 0.12, "rec_multiplier": 0.3, "on": "allies"},
                                          {"type": "burst", "value": 10, "on": "allies"}]),
    "sunchoir_anthem": burst("Sunchoir Anthem", "All allies gain +30% ATK and +20% REC for 3 turns, recover 15% max HP "
                             "and lose 1 negative status.", "ally_all", 0, 0, "self", {"value": 0.03, "duration_at": [4]},
                             release_frame=5, field_effect="buff_rise", sfx_cast="fire", burst_fx="hearth_hymn",
                             effects=[{"type": "status", "status": "atk_up", "value": 0.3, "duration": 3, "chance": 1.0,
                                       "on": "allies"},
                                      {"type": "status", "status": "rec_up", "value": 0.2, "duration": 3, "chance": 1.0,
                                       "on": "allies"},
                                      {"type": "heal", "percent_max_hp": 0.15, "rec_multiplier": 0.4, "on": "allies"},
                                      {"type": "cleanse", "count": 1, "on": "allies"}]),
    # ------------------------------------------------ Voss
    "ash_cleave": atk("Ash Cleave", "Two heavy chops. 110% ATK over 2 hits, 30% chance to lower DEF by 15%.", 1.1, 2,
                      "melee", hit_frames=[3, 5], hit_effect="axe_cleave", impact_effect="hit_fire", sfx_hit="sword",
                      shake=0.3, effects=[{"type": "status", "status": "def_down", "value": 0.15, "duration": 2,
                                           "chance": 0.3, "on": "target"}]),
    "rending_quake": burst("Rending Quake", "Shatters one foe's guard. 260% ATK over 4 hits and lowers DEF by 30% for "
                           "3 turns.", "enemy_single", 2.6, 4, "melee", {"power": 0.12, "value": 0.03},
                           hit_frames=[4, 5, 6, 6], hit_weights=[1, 1, 1.5, 2], hit_effect="axe_cleave",
                           final_effect="slash_heavy", impact_effect="hit_fire", sfx_hit="sword", shake=1.0,
                           burst_fx="ember_rush",
                           effects=[{"type": "status", "status": "def_down", "value": 0.3, "duration": 3, "chance": 1.0,
                                     "on": "target"}]),
    "magma_sunder": burst("Magma Sunder", "Splits the ground under every foe. 200% ATK to all over 4 hits and lowers "
                          "their DEF by 30% for 3 turns.", "enemy_all", 2.0, 4, "melee", {"power": 0.1, "duration_at": [5]},
                          hit_frames=[4, 5, 6, 6], hit_weights=[1, 1, 1.5, 2], hit_effect="axe_cleave",
                          final_effect="slash_heavy", impact_effect="hit_fire", sfx_hit="sword", shake=1.2,
                          burst_fx="ember_rush",
                          effects=[{"type": "status", "status": "def_down", "value": 0.3, "duration": 3, "chance": 1.0,
                                    "on": "target"}]),
    # ------------------------------------------------ Seraphine
    "pyre_thrust": atk("Pyre Thrust", "Three blinding thrusts. 110% ATK over 3 hits.", 1.1, 3, "melee",
                       hit_frames=[2, 4, 6], hit_effect="spear_thrust", impact_effect="hit_fire", sfx_hit="sword"),
    "phoenix_lance": burst("Phoenix Lance", "Seven strikes that end in a burst of flame. 380% ATK over 7 hits, 50% "
                           "chance to Burn.", "enemy_single", 3.8, 7, "melee", {"power": 0.15, "gauge": 4},
                           hit_frames=[2, 3, 4, 5, 6, 8, 9], hit_weights=[1, 1, 1, 1, 1, 1.5, 3],
                           hit_effect="spear_thrust", final_effect="slash_heavy", impact_effect="hit_fire",
                           sfx_hit="sword", shake=1.2, burst_fx="ember_rush",
                           effects=[{"type": "status", "status": "burn", "chance": 0.5, "duration": 3, "on": "target"}]),
    # ------------------------------------------------ Mira (existing timings)
    "tidal_bolt": atk("Tidal Bolt", "Launches compressed water. 90% ATK over 3 hits.", 0.9, 3, "ranged",
                      release_frame=2, projectile="water_bolt", impact_effect="hit_water", sfx_cast="water",
                      sfx_hit="water_hit"),
    "restoring_current": burst("Restoring Current", "Heals all allies for 25% max HP + REC, removes 1 negative status "
                               "and grants +15% DEF for 3 turns.", "ally_all", 0, 0, "self", {"heal": 0.03},
                               release_frame=6, field_effect="heal_ring", sfx_cast="water", burst_fx="tide_ring",
                               effects=[{"type": "heal", "percent_max_hp": 0.25, "rec_multiplier": 1.0, "on": "allies"},
                                        {"type": "cleanse", "count": 1, "on": "allies"},
                                        {"type": "status", "status": "def_up", "value": 0.15, "duration": 3,
                                         "chance": 1.0, "on": "allies"}]),
    "restoring_current_ii": burst("Restoring Current II", "Heals all allies for 30% max HP + REC, removes 2 negative "
                                  "statuses and grants +20% DEF for 3 turns.", "ally_all", 0, 0, "self",
                                  {"heal": 0.03, "gauge": 4}, release_frame=6, field_effect="heal_ring",
                                  sfx_cast="water", burst_fx="tide_ring",
                                  effects=[{"type": "heal", "percent_max_hp": 0.30, "rec_multiplier": 1.1,
                                            "on": "allies"},
                                           {"type": "cleanse", "count": 2, "on": "allies"},
                                           {"type": "status", "status": "def_up", "value": 0.2, "duration": 3,
                                            "chance": 1.0, "on": "allies"}]),
    "wavesong_renewal": burst("Wavesong Renewal", "Heals all allies for 35% max HP + REC, cleanses all negative "
                              "statuses, grants +20% DEF and Regen (5% per turn) for 3 turns.", "ally_all", 0, 0, "self",
                              {"heal": 0.03, "duration_at": [4]}, release_frame=6, field_effect="heal_ring",
                              sfx_cast="water", burst_fx="tide_ring",
                              effects=[{"type": "heal", "percent_max_hp": 0.35, "rec_multiplier": 1.2, "on": "allies"},
                                       {"type": "cleanse", "count": 9, "on": "allies"},
                                       {"type": "status", "status": "def_up", "value": 0.2, "duration": 3, "chance": 1.0,
                                        "on": "allies"},
                                       {"type": "status", "status": "regen", "value": 0.05, "duration": 3, "chance": 1.0,
                                        "on": "allies"}]),
    # ------------------------------------------------ Corin
    "trident_jab": atk("Trident Jab", "Two quick jabs. 95% ATK over 2 hits.", 0.95, 2, "melee", hit_frames=[2, 4],
                       hit_effect="spear_thrust", impact_effect="hit_water", sfx_hit="water_hit"),
    "tidal_bulwark": burst("Tidal Bulwark", "Every ally gains a Shield worth 15% of Corin's max HP for 3 turns; Corin "
                           "draws enemy attacks for 2 turns.", "ally_all", 0, 0, "self", {"shield": 0.03},
                           release_frame=5, field_effect="shield_flash", sfx_cast="guard", burst_fx="bulwark",
                           effects=[{"type": "shield", "percent_caster_hp": 0.15, "duration": 3, "on": "allies"},
                                    {"type": "status", "status": "taunt", "value": 1.0, "duration": 2, "chance": 1.0,
                                     "on": "self"}]),
    "tidal_bulwark_ii": burst("Tidal Bulwark II", "Shields worth 20% of Corin's max HP for every ally, +15% DEF for 3 "
                              "turns; Corin draws enemy attacks.", "ally_all", 0, 0, "self", {"shield": 0.03},
                              release_frame=5, field_effect="shield_flash", sfx_cast="guard", burst_fx="bulwark",
                              effects=[{"type": "shield", "percent_caster_hp": 0.20, "duration": 3, "on": "allies"},
                                       {"type": "status", "status": "def_up", "value": 0.15, "duration": 3, "chance": 1.0,
                                        "on": "allies"},
                                       {"type": "status", "status": "taunt", "value": 1.0, "duration": 2, "chance": 1.0,
                                        "on": "self"}]),
    "reef_aegis": burst("Reef Aegis", "Shields worth 25% of Corin's max HP for every ally, +25% DEF for 3 turns, "
                        "Corin takes 30% less damage and draws enemy attacks.", "ally_all", 0, 0, "self",
                        {"shield": 0.03, "gauge": 4}, release_frame=5, field_effect="shield_flash", sfx_cast="guard",
                        burst_fx="bulwark",
                        effects=[{"type": "shield", "percent_caster_hp": 0.25, "duration": 3, "on": "allies"},
                                 {"type": "status", "status": "def_up", "value": 0.25, "duration": 3, "chance": 1.0,
                                  "on": "allies"},
                                 {"type": "status", "status": "damage_reduction", "value": 0.3, "duration": 2,
                                  "chance": 1.0, "on": "self"},
                                 {"type": "status", "status": "taunt", "value": 1.0, "duration": 2, "chance": 1.0,
                                  "on": "self"}]),
    # ------------------------------------------------ Nerys
    "frost_flurry": atk("Frost Flurry", "Four quick cuts. 100% ATK over 4 hits.", 1.0, 4, "melee",
                        hit_frames=[2, 3, 4, 5], hit_effect="dagger_flurry", impact_effect="hit_water", sfx_hit="sword"),
    "rimefang_waltz": burst("Rimefang Waltz", "Seven frozen cuts. 300% ATK over 7 hits and lowers the target's ATK by "
                            "20% for 3 turns.", "enemy_single", 3.0, 7, "melee", {"power": 0.14, "value": 0.02},
                            hit_frames=[2, 3, 4, 5, 6, 7, 9], hit_weights=[1, 1, 1, 1, 1, 1, 2.5],
                            hit_effect="dagger_flurry", final_effect="slash_heavy", impact_effect="hit_water",
                            sfx_hit="sword", shake=0.8, burst_fx="frost_waltz",
                            effects=[{"type": "status", "status": "atk_down", "value": 0.2, "duration": 3, "chance": 1.0,
                                      "on": "target"}]),
    "glacial_requiem": burst("Glacial Requiem", "Seven cuts of living ice. 380% ATK over 7 hits, lowers the target's "
                             "ATK and DEF by 25% for 3 turns.", "enemy_single", 3.8, 7, "melee",
                             {"power": 0.15, "gauge": 4}, hit_frames=[2, 3, 4, 5, 6, 7, 9],
                             hit_weights=[1, 1, 1, 1, 1, 1, 3], hit_effect="dagger_flurry", final_effect="slash_heavy",
                             impact_effect="hit_water", sfx_hit="sword", shake=1.0, burst_fx="frost_waltz",
                             effects=[{"type": "status", "status": "atk_down", "value": 0.25, "duration": 3,
                                       "chance": 1.0, "on": "target"},
                                      {"type": "status", "status": "def_down", "value": 0.25, "duration": 3,
                                       "chance": 1.0, "on": "target"}]),
    # ------------------------------------------------ Aldric
    "glyph_bolt": atk("Glyph Bolt", "A spinning tide-glyph. 100% ATK over 2 hits.", 1.0, 2, "ranged",
                      release_frame=3, projectile="tide_orb", impact_effect="hit_water", sfx_cast="water",
                      sfx_hit="water_hit"),
    "deepvow_litany": burst("Deepvow Litany", "Every foe's ATK drops 25% for 3 turns; all allies gain +25% REC and "
                            "recover 15% max HP.", "enemy_all", 0.6, 1, "self", {"value": 0.03, "heal": 0.02},
                            release_frame=6, field_effect="hex_cloud", sfx_cast="water", burst_fx="litany",
                            impact_effect="hit_water", sfx_hit="water_hit",
                            effects=[{"type": "status", "status": "atk_down", "value": 0.25, "duration": 3,
                                      "chance": 1.0, "on": "foes"},
                                     {"type": "status", "status": "rec_up", "value": 0.25, "duration": 3, "chance": 1.0,
                                      "on": "allies"},
                                     {"type": "heal", "percent_max_hp": 0.15, "rec_multiplier": 0.5, "on": "allies"}]),
    # ------------------------------------------------ Thorne (existing timings)
    "root_hammer": atk("Root Hammer", "A hammer swing then a shield bash. 95% ATK over 2 hits.", 0.95, 2, "melee",
                       hit_frames=[2, 4], impact_effect="hit_nature", sfx_hit="nature", shake=0.3),
    "ancient_bastion": burst("Ancient Bastion", "Roots rise around the party: all allies gain +30% DEF for 3 turns. "
                             "Thorne takes 40% less damage for 2 turns and draws enemy attacks.", "ally_all", 0, 0,
                             "self", {"value": 0.03, "duration_at": [4]}, release_frame=4, field_effect="roots",
                             sfx_cast="nature", shake=0.6, burst_fx="grove_bastion",
                             effects=[{"type": "status", "status": "def_up", "value": 0.30, "duration": 3, "chance": 1.0,
                                       "on": "allies"},
                                      {"type": "status", "status": "damage_reduction", "value": 0.40, "duration": 2,
                                       "chance": 1.0, "on": "self"},
                                      {"type": "status", "status": "taunt", "value": 1.0, "duration": 2, "chance": 1.0,
                                       "on": "self"}]),
    "ancient_bastion_ii": burst("Ancient Bastion II", "All allies gain +35% DEF for 3 turns and a Shield worth 10% of "
                                "Thorne's max HP. Thorne takes 45% less damage and draws enemy attacks.", "ally_all",
                                0, 0, "self", {"value": 0.03, "shield": 0.02}, release_frame=4, field_effect="roots",
                                sfx_cast="nature", shake=0.6, burst_fx="grove_bastion",
                                effects=[{"type": "status", "status": "def_up", "value": 0.35, "duration": 3,
                                          "chance": 1.0, "on": "allies"},
                                         {"type": "shield", "percent_caster_hp": 0.10, "duration": 3, "on": "allies"},
                                         {"type": "status", "status": "damage_reduction", "value": 0.45, "duration": 2,
                                          "chance": 1.0, "on": "self"},
                                         {"type": "status", "status": "taunt", "value": 1.0, "duration": 2,
                                          "chance": 1.0, "on": "self"}]),
    "worldroot_citadel": burst("Worldroot Citadel", "The grove itself stands guard: +40% DEF and a Shield worth 15% of "
                               "Thorne's max HP for all allies; Regen 4% for 3 turns; Thorne draws enemy attacks and "
                               "takes 50% less damage.", "ally_all", 0, 0, "self", {"value": 0.03, "gauge": 4},
                               release_frame=4, field_effect="roots", sfx_cast="nature", shake=0.8,
                               burst_fx="grove_bastion",
                               effects=[{"type": "status", "status": "def_up", "value": 0.40, "duration": 3,
                                         "chance": 1.0, "on": "allies"},
                                        {"type": "shield", "percent_caster_hp": 0.15, "duration": 3, "on": "allies"},
                                        {"type": "status", "status": "regen", "value": 0.04, "duration": 3,
                                         "chance": 1.0, "on": "allies"},
                                        {"type": "status", "status": "damage_reduction", "value": 0.5, "duration": 2,
                                         "chance": 1.0, "on": "self"},
                                        {"type": "status", "status": "taunt", "value": 1.0, "duration": 2,
                                         "chance": 1.0, "on": "self"}]),
    # ------------------------------------------------ Wren
    "briar_shot": atk("Briar Shot", "Two quick arrows. 95% ATK over 2 hits.", 0.95, 2, "ranged", release_frame=4,
                      projectile="arrow", impact_effect="hit_nature", sfx_cast="sword", sfx_hit="nature"),
    "thorn_volley": burst("Thorn Volley", "A rain of thorned arrows. 150% ATK to all foes over 3 hits.", "enemy_all",
                          1.5, 3, "ranged", {"power": 0.1}, release_frame=7, projectile="arrow",
                          impact_effect="hit_nature", sfx_cast="nature", sfx_hit="nature", burst_fx="volley"),
    "thorn_volley_ii": burst("Thorn Volley II", "180% ATK to all foes over 3 hits; 30% chance to Poison.", "enemy_all",
                             1.8, 3, "ranged", {"power": 0.1, "chance": 0.05}, release_frame=7, projectile="arrow",
                             impact_effect="hit_nature", sfx_cast="nature", sfx_hit="nature", burst_fx="volley",
                             effects=[{"type": "status", "status": "poison", "chance": 0.3, "duration": 3,
                                       "on": "target"}]),
    "galeleaf_tempest": burst("Galeleaf Tempest", "A storm of golden arrows: 230% ATK to all foes over 3 hits; 50% "
                              "Poison; Wren's ATK +20% for 2 turns.", "enemy_all", 2.3, 3, "ranged",
                              {"power": 0.12, "gauge": 4}, release_frame=7, projectile="arrow",
                              impact_effect="hit_nature", sfx_cast="nature", sfx_hit="nature", burst_fx="volley",
                              effects=[{"type": "status", "status": "poison", "chance": 0.5, "duration": 3,
                                        "on": "target"},
                                       {"type": "status", "status": "atk_up", "value": 0.2, "duration": 2,
                                        "chance": 1.0, "on": "self"}]),
    # ------------------------------------------------ Faye
    "petal_dart": atk("Petal Dart", "A spinning petal. 85% ATK over 2 hits.", 0.85, 2, "ranged", release_frame=3,
                      projectile="petal_bolt", impact_effect="hit_nature", sfx_cast="nature", sfx_hit="nature"),
    "bloomsong": burst("Bloomsong", "Heals all allies for 22% max HP + REC and grants Regen (5% per turn) for 3 turns.",
                       "ally_all", 0, 0, "self", {"heal": 0.03, "value": 0.01}, release_frame=5,
                       field_effect="petal_burst", sfx_cast="heal", burst_fx="bloom",
                       effects=[{"type": "heal", "percent_max_hp": 0.22, "rec_multiplier": 0.9, "on": "allies"},
                                {"type": "status", "status": "regen", "value": 0.05, "duration": 3, "chance": 1.0,
                                 "on": "allies"}]),
    "everbloom_chorus": burst("Everbloom Chorus", "Heals all allies for 30% max HP + REC, Regen 7% for 3 turns and "
                              "+15% REC.", "ally_all", 0, 0, "self", {"heal": 0.03, "value": 0.01, "gauge": 4},
                              release_frame=5, field_effect="petal_burst", sfx_cast="heal", burst_fx="bloom",
                              effects=[{"type": "heal", "percent_max_hp": 0.30, "rec_multiplier": 1.1, "on": "allies"},
                                       {"type": "status", "status": "regen", "value": 0.07, "duration": 3,
                                        "chance": 1.0, "on": "allies"},
                                       {"type": "status", "status": "rec_up", "value": 0.15, "duration": 3,
                                        "chance": 1.0, "on": "allies"}]),
    # ------------------------------------------------ Gorran
    "oakheart_smash": atk("Oakheart Smash", "Two earth-shaking blows. 110% ATK over 2 hits, 35% chance to lower DEF by "
                          "15%.", 1.1, 2, "melee", hit_frames=[3, 4], impact_effect="hit_nature", sfx_hit="nature",
                          shake=0.4, effects=[{"type": "status", "status": "def_down", "value": 0.15, "duration": 2,
                                               "chance": 0.35, "on": "target"}]),
    "grove_quake": burst("Grove Quake", "The whole field heaves: 220% ATK to all foes over 4 hits and lowers their DEF "
                         "by 30% for 3 turns.", "enemy_all", 2.2, 4, "melee", {"power": 0.1, "value": 0.03},
                         hit_frames=[5, 6, 7, 7], hit_weights=[1, 1, 1.5, 2.5], impact_effect="hit_nature",
                         final_effect="slash_heavy", sfx_hit="nature", shake=1.3, burst_fx="grove_bastion",
                         effects=[{"type": "status", "status": "def_down", "value": 0.3, "duration": 3, "chance": 1.0,
                                   "on": "target"}]),
}

# ====================================================================== enemies
def enemy(eid, name, element, role, stats, normal, special, xp, gold, drop, ai, desc, size_scale=8, **kw):
    folder = kw.pop("sprite_id", eid)
    d = {"id": eid, "name": name, "element": element, "role": role, "type": kw.pop("type", role.capitalize()),
         "base_stats": dict(zip(("hp", "atk", "def", "spd"), stats)),
         "skills": {"normal": normal, "special": special}, "ai": ai,
         "rewards": {"xp": xp, "gold": gold}, "drop_table": drop,
         "sprite": {"sheet": f"res://assets/enemies/{folder}/{folder}_sheet.png",
                    "meta": f"res://assets/enemies/{folder}/{folder}_sheet.json", "scale": size_scale},
         "description": desc}
    d.update(kw)
    return d


def AI(profile, chance=0.3, targeting="random", **kw):
    d = {"profile": profile, "skill_chance": chance, "targeting": targeting}
    d.update(kw)
    return d


ENEMIES = {
    # ---- World 1 originals (stats unchanged)
    "cinder_slime": enemy("cinder_slime", "Cinder Slime", "fire", "attacker", (180, 40, 20, 35), "slime_tackle",
                          "scorch_splash", 12, [6, 12], "fire_common", AI("attacker"),
                          "A lump of smouldering goo. Its core never quite cools.", type="Slime"),
    "tidefin": enemy("tidefin", "Tidefin", "water", "attacker", (220, 35, 30, 50), "tail_swipe", "bubble_shot", 13,
                     [6, 12], "water_common", AI("attacker"), "A long-legged fish that learned to walk on the shore.",
                     type="Beast"),
    "bramble_pup": enemy("bramble_pup", "Bramble Pup", "nature", "attacker", (250, 45, 35, 45), "bramble_bite",
                         "thorn_rush", 14, [7, 13], "nature_common", AI("attacker"),
                         "A wolf pup grown from thorns and bark. It bites first and sniffs later.", type="Beast"),
    "ancient_bramble_pup": enemy("ancient_bramble_pup", "Ancient Bramble Pup", "nature", "boss", (760, 54, 42, 60),
                                 "ancient_maul", "verdant_rampage", 60, [60, 90], "nature_boss",
                                 AI("boss", 0.0, pattern=["normal", "normal", "charge"],
                                    summon={"enemy": "bramble_pup", "level_offset": -2, "every": 4, "count": 1, "max": 2},
                                    hp_events=[{"below": 0.6, "skill": "bark_armor"}]),
                                 "The oldest beast of the Wilds. Stone horns, burning eyes, and it calls its pack.",
                                 size_scale=10, boss=True, type="Ancient Beast"),
    # ---- new families
    "tide_slime": enemy("tide_slime", "Tide Slime", "water", "attacker", (190, 36, 22, 38), "droplet_spit",
                        "soaking_surge", 12, [6, 12], "water_common", AI("attacker"),
                        "A slime of brine and foam. Squishes into a puddle when threatened.", type="Slime"),
    "moss_slime": enemy("moss_slime", "Moss Slime", "nature", "attacker", (210, 38, 26, 33), "mossy_bump",
                        "spore_puff", 12, [6, 12], "nature_common", AI("attacker"),
                        "A mossy mound that grows a sprout when it is happy.", type="Slime"),
    "glowcap": enemy("glowcap", "Glowcap", "nature", "healer", (200, 30, 30, 40), "cap_bonk", "glow_mend", 15, [7, 13],
                     "nature_uncommon", AI("healer", 0.1), "A walking mushroom whose spores knit wounds shut - "
                     "for its friends.", type="Fungus"),
    "emberwisp": enemy("emberwisp", "Emberwisp", "fire", "buffer", (170, 42, 18, 70), "wisp_flick", "kindle", 15,
                       [7, 13], "fire_uncommon", AI("buffer", 0.15), "A floating flame that fans its allies into a "
                       "frenzy.", type="Spirit"),
    "hexmoth": enemy("hexmoth", "Hexmoth", "nature", "debuffer", (190, 38, 24, 65), "dust_bite", "hex_powder", 15,
                     [7, 13], "nature_uncommon", AI("debuffer", 0.3, targeting="highest_atk"),
                     "Its wing-dust saps strength from anything it settles on.", type="Insect"),
    "scorch_beetle": enemy("scorch_beetle", "Scorch Beetle", "fire", "burst", (260, 50, 45, 30), "horn_jab",
                           "scorch_charge", 17, [8, 15], "fire_uncommon", AI("charger", 0.0, charge_every=3),
                           "A beetle that stokes the furnace in its shell before a devastating charge.", type="Insect"),
    "shellcrab": enemy("shellcrab", "Shellcrab", "water", "tank", (320, 34, 60, 25), "pincer", "shell_up", 16, [8, 14],
                       "water_uncommon", AI("tank", 0.0), "It hides behind a salt crystal and pinches anyone who "
                       "reaches for its friends.", type="Crustacean"),
    "brine_eel": enemy("brine_eel", "Brine Eel", "water", "fast", (200, 46, 22, 90), "eel_snap", "riptide_coil", 16,
                       [8, 14], "water_uncommon", AI("attacker", 0.3, targeting="lowest_hp"),
                       "Strikes twice before you see it move. Always goes for the weakest.", type="Serpent"),
    "drift_jelly": enemy("drift_jelly", "Drift Jelly", "water", "healer", (210, 30, 28, 45), "jelly_sting",
                         "tidal_glow", 16, [8, 14], "water_uncommon", AI("healer", 0.1),
                         "A glowing jelly whose light soothes its school.", type="Jelly"),
    "salt_wraith": enemy("salt_wraith", "Salt Wraith", "water", "debuffer", (220, 44, 26, 60), "salt_shard",
                         "brine_curse", 18, [9, 15], "water_uncommon", AI("debuffer", 0.35, targeting="highest_atk"),
                         "Mist and salt given a hateful will. Its curse leaves armour brittle.", type="Spirit"),
    # ---- World 2 boss
    "saltglass_colossus": enemy("saltglass_colossus", "Saltglass Colossus", "water", "boss", (1400, 70, 70, 50),
                                "glass_club", "shatterstorm", 150, [150, 220], "water_boss",
                                AI("boss", 0.0, pattern=["normal", "curse", "normal", "charge"],
                                   curse="brine_curse", targeting="lowest_hp",
                                   phase2={"below": 0.5, "atk_up": 0.3, "pattern": ["normal", "charge"],
                                           "announce": "The Colossus cracks - its core blazes!",
                                           "skill": "glass_carapace"}),
                                "A giant of sea-worn stone and saltglass. When its shell breaks, its core burns.",
                                size_scale=10, boss=True, type="Colossus"),
}
# ---- elites: stronger variants with one extra ability, better rewards, gold frame + tint
ELITES = {
    "elite_bramble_pup": ("bramble_pup", "Elite Bramble Pup", "howl", "#ffd060", "nature_elite"),
    "elite_cinder_slime": ("cinder_slime", "Elite Cinder Slime", "flare_up", "#ffd060", "fire_elite"),
    "elite_tidefin": ("tidefin", "Elite Tidefin", "tidal_mend", "#ffd060", "water_elite"),
    "elite_scorch_beetle": ("scorch_beetle", "Elite Scorch Beetle", "flare_up", "#ffd060", "fire_elite"),
    "elite_shellcrab": ("shellcrab", "Elite Shellcrab", "tidal_mend", "#ffd060", "water_elite"),
    "elite_hexmoth": ("hexmoth", "Elite Hexmoth", "howl", "#ffd060", "nature_elite"),
    "elite_brine_eel": ("brine_eel", "Elite Brine Eel", "tidal_mend", "#ffd060", "water_elite"),
    "elite_emberwisp": ("emberwisp", "Elite Emberwisp", "flare_up", "#ffd060", "fire_elite"),
}
# ---- tower bosses: giant tinted variants with boss patterns
TOWER_BOSSES = {
    "scorch_matriarch": ("scorch_beetle", "Scorch Beetle Matriarch", "fire", (900, 62, 60, 40), "#ff9a6a",
                         dict(pattern=["normal", "curse", "charge"], curse="kindle",
                              summon={"enemy": "cinder_slime", "level_offset": -3, "every": 3, "count": 1, "max": 2})),
    "emberwisp_tyrant": ("emberwisp", "Emberwisp Tyrant", "fire", (1300, 80, 55, 80), "#ffe06a",
                         dict(pattern=["normal", "curse", "normal", "charge"], curse="kindle",
                              phase2={"below": 0.5, "atk_up": 0.25, "pattern": ["normal", "charge"],
                                      "announce": "The Tyrant flares white-hot!"})),
    "deepwater_matron": ("drift_jelly", "Deepwater Matron", "water", (950, 55, 55, 45), "#9ad0ff",
                         dict(pattern=["normal", "heal", "charge"], heal="tidal_glow",
                              summon={"enemy": "tide_slime", "level_offset": -3, "every": 3, "count": 1, "max": 2})),
    "brine_leviathan": ("brine_eel", "Brine Leviathan", "water", (1350, 82, 50, 90), "#6ad8ff",
                        dict(pattern=["normal", "normal", "charge"], targeting="lowest_hp",
                             phase2={"below": 0.5, "atk_up": 0.25, "pattern": ["normal", "charge"],
                                     "announce": "The Leviathan thrashes in a frenzy!"})),
    "elder_glowcap": ("glowcap", "Elder Glowcap", "nature", (950, 50, 60, 40), "#d0ff8a",
                      dict(pattern=["normal", "heal", "curse", "charge"], heal="glow_mend", curse="spore_puff",
                           summon={"enemy": "moss_slime", "level_offset": -3, "every": 3, "count": 1, "max": 2})),
    "thornback_elder": ("ancient_bramble_pup", "Thornback Elder", "nature", (1400, 84, 60, 60), "#b0ff9a",
                        dict(pattern=["normal", "normal", "charge"],
                             summon={"enemy": "bramble_pup", "level_offset": -3, "every": 4, "count": 1, "max": 2},
                             phase2={"below": 0.5, "atk_up": 0.25, "pattern": ["normal", "charge"],
                                     "announce": "The Elder's thorns lengthen!"})),
}
TOWER_BOSS_SKILLS = {"scorch_beetle": ("horn_jab", "scorch_charge"), "emberwisp": ("wisp_flick", "inferno_nova"),
                     "drift_jelly": ("jelly_sting", "maelstrom"), "brine_eel": ("eel_snap", "riptide_coil"),
                     "glowcap": ("cap_bonk", "spore_storm"), "ancient_bramble_pup": ("ancient_maul", "verdant_rampage")}


# ---- Phase 7: the Ashen Warden (first mechanical boss) and its Ember Totems
def phase7_enemy_skills():
  return {
    "warden_maul": eatk("Warden's Maul", "Two heavy blows with a burning fist.", 1.15, 2, "melee", [2, 3],
                        impact_effect="hit_fire", sfx_hit="fire", shake=0.5),
    "cinder_wave": espc("Cinder Wave", "A wave of cinders washes over the party. May Burn.", 0.7, 1, "melee", [4],
                        target="enemy_all", impact_effect="hit_fire", sfx_hit="fire",
                        effects=[{"type": "status", "status": "burn", "chance": 0.4, "duration": 2, "on": "target"}]),
    "reforge_armor": espc("Reforge Armor", "Wraps itself in Flame Armor again (40% less damage).", 0, 0, "self", 3,
                          target="self", field_effect="shield_flash", sfx_cast="guard",
                          effects=[{"type": "status", "status": "flame_armor", "value": 0.4, "duration": 99,
                                    "chance": 1.0, "on": "self"}]),
    "furnace_collapse": espc("Furnace Collapse", "After charging: the furnace in its chest bursts over the whole "
                             "party. BREAK the Warden or deal 15% of its HP while it charges to stop it.", 2.4, 3,
                             "melee", [4, 5, 5], target="enemy_all", impact_effect="hit_fire", sfx_hit="fire",
                             shake=1.3, interrupt={"break": True, "damage_percent": 0.15},
                             effects=[{"type": "status", "status": "burn", "chance": 0.6, "duration": 3,
                                       "on": "target"}]),
    "totem_hum": eatk("Totem Hum", "The totem hums with heat.", 0.5, 1, "melee", [2], impact_effect="hit_fire"),
  }
PHASE7_ENEMIES = {
    "ashen_warden": enemy("ashen_warden", "Ashen Warden", "fire", "boss", (2400, 130, 80, 55), "warden_maul",
                          "furnace_collapse", 400, [400, 520], "fire_boss",
                          AI("boss", 0.0, actions=2, pattern=["normal", "cinder_wave", "normal", "reforge_armor"],
                             phases=[{"below": 0.7, "announce": "The Warden calls up two Ember Totems! "
                                                               "They feed it ATK - destroy them.",
                                      "summon": {"enemy": "ember_totem", "count": 2, "max": 2, "level_offset": -4}},
                                     {"below": 0.4, "atk_up": 0.15, "charge": "furnace_collapse",
                                      "announce": "Its furnace roars open! BREAK it, Guard or burst it down!",
                                      "pattern": ["normal", "cinder_wave", "charge", "normal", "reforge_armor"]}]),
                          "A knight of ash who guards the first Fracture. Its Flame Armor turns blades aside "
                          "until something breaks its stance - water hits it hardest.",
                          size_scale=10, boss=True, type="Fracture Guardian", sprite_id="saltglass_colossus",
                          tint="#ff8a5a", variant_of="saltglass_colossus",
                          **{"break": {"max": 220, "weak": "water"}, "resist": {"burn": 0.8},
                             "start_statuses": [{"id": "flame_armor", "value": 0.4, "turns": 99}],
                             "mechanics": ["Flame Armor: -40% damage taken until Broken.",
                                           "Break Gauge: Water heroes and Breakers drain it fastest.",
                                           "70% HP: two Ember Totems raise its ATK until destroyed.",
                                           "40% HP: charges Furnace Collapse - Break it, deal 15% HP, or Guard."]}),
    "ember_totem": enemy("ember_totem", "Ember Totem", "fire", "totem", (380, 0, 40, 1), "totem_hum", "totem_hum",
                         0, [0, 0], "fire_common", AI("totem", 0.0),
                         "A pillar of banked coals. While it stands, the Warden burns hotter (+20% ATK each).",
                         size_scale=7, type="Totem", sprite_id="emberwisp", tint="#b0402a", variant_of="emberwisp",
                         aura={"status": "ember_fervor", "value": 0.2}),
}


def build_enemies():
    out = copy.deepcopy(ENEMIES)
    out.update(copy.deepcopy(PHASE7_ENEMIES))
    for eid, (base_id, name, extra, tint, drop) in ELITES.items():
        b = copy.deepcopy(ENEMIES[base_id])
        b.update({"id": eid, "name": name, "elite": True, "tint": tint, "drop_table": drop,
                  "variant_of": base_id,
                  "description": "An elite, battle-hardened " + b["name"].lower() + ". Stronger, and it knows one "
                                 "extra trick."})
        b["base_stats"] = {k: int(v * m) for (k, v), m in zip(b["base_stats"].items(), (1.8, 1.3, 1.3, 1.1))}
        b["skills"]["extra"] = extra
        b["ai"]["extra_every"] = 3
        b["rewards"] = {"xp": b["rewards"]["xp"] * 3, "gold": [g * 3 for g in b["rewards"]["gold"]]}
        out[eid] = b
    for eid, (base_id, name, element, stats, tint, pattern) in TOWER_BOSSES.items():
        b = copy.deepcopy(ENEMIES[base_id])
        normal, special = TOWER_BOSS_SKILLS[base_id]
        b.update({"id": eid, "name": name, "element": element, "role": "boss", "boss": True, "tint": tint,
                  "variant_of": base_id, "type": "Tower Guardian",
                  "base_stats": dict(zip(("hp", "atk", "def", "spd"), stats)),
                  "skills": {"normal": normal, "special": special},
                  "ai": AI("boss", 0.0, **pattern), "rewards": {"xp": 120, "gold": [120, 180]},
                  "drop_table": f"{element}_boss",
                  "description": "A guardian of the " + {"fire": "Ember", "water": "Tide", "nature": "Verdant"}[element]
                                 + " Tower, grown huge on the tower's power."})
        b["sprite"]["scale"] = 11 if base_id != "ancient_bramble_pup" else 10
        out[eid] = b
    return out


def eatk(name, desc, power, hits, motion, frames=None, **kw):
    d = {"name": name, "kind": "normal", "description": desc, "target": "enemy_single", "power": power, "hits": hits,
         "motion": motion, "anim": "attack"}
    if motion == "melee":
        d["hit_frames"] = frames or [3]
    else:
        d["release_frame"] = frames or 3
    d.update(kw)
    return d


def espc(name, desc, power, hits, motion, frames=None, **kw):
    d = eatk(name, desc, power, hits, motion, frames, **kw)
    d["kind"] = "skill"
    d["anim"] = "special"
    return d


def build_enemy_skills():
    s = read("skills/enemy_skills.json")
    s = {k: v for k, v in s.items() if not k.startswith("_")}
    s["verdant_rampage"]["description"] = "After charging: tears through the whole party with thorned roots."
    s["verdant_rampage"]["power"] = 1.6
    new = {
        "droplet_spit": eatk("Droplet Spit", "Spits a ball of brine.", 1.0, 1, "ranged", 3, projectile="bubble",
                             impact_effect="hit_water", sfx_cast="water", sfx_hit="water_hit"),
        "soaking_surge": espc("Soaking Surge", "A wave that lowers DEF.", 1.2, 2, "ranged", 4, projectile="water_bolt",
                              impact_effect="hit_water", sfx_cast="water", sfx_hit="water_hit",
                              effects=[{"type": "status", "status": "def_down", "value": 0.1, "duration": 2,
                                        "chance": 0.5, "on": "target"}]),
        "mossy_bump": eatk("Mossy Bump", "Bumps into a foe.", 1.0, 1, "melee", [3], impact_effect="hit_nature",
                           sfx_hit="nature"),
        "spore_puff": espc("Spore Puff", "A cloud of spores that Poisons.", 0.8, 1, "ranged", 4, projectile="petal_bolt",
                           impact_effect="hit_nature", sfx_cast="nature", sfx_hit="nature",
                           effects=[{"type": "status", "status": "poison", "chance": 0.6, "duration": 3,
                                     "on": "target"}]),
        "cap_bonk": eatk("Cap Bonk", "Headbutts with its cap.", 0.9, 1, "melee", [3], impact_effect="hit_nature",
                         sfx_hit="nature"),
        "glow_mend": espc("Glow Mend", "Heals the most injured ally for 25% max HP.", 0, 0, "self", 4,
                          target="ally_lowest", field_effect="heal_ring", sfx_cast="heal",
                          effects=[{"type": "heal", "percent_max_hp": 0.25, "on": "target_ally"}]),
        "wisp_flick": eatk("Wisp Flick", "Flicks an ember.", 1.0, 1, "ranged", 2, projectile="ember_bolt",
                           impact_effect="hit_fire", sfx_cast="fire", sfx_hit="fire"),
        "kindle": espc("Kindle", "Fans the flames: all allies gain +20% ATK for 2 turns.", 0, 0, "self", 4,
                       target="ally_all", field_effect="buff_rise", sfx_cast="fire",
                       effects=[{"type": "status", "status": "atk_up", "value": 0.2, "duration": 2, "chance": 1.0,
                                 "on": "allies"}]),
        "dust_bite": eatk("Dust Bite", "A dusty nip.", 1.0, 1, "melee", [3], impact_effect="hit_nature",
                          sfx_hit="nature"),
        "hex_powder": espc("Hex Powder", "Hexing dust: lowers ATK by 20% for 3 turns.", 0.6, 1, "ranged", 4,
                           projectile="petal_bolt", impact_effect="hit_nature", sfx_cast="nature", sfx_hit="nature",
                           effects=[{"type": "status", "status": "atk_down", "value": 0.2, "duration": 3, "chance": 1.0,
                                     "on": "target"}]),
        "horn_jab": eatk("Horn Jab", "Jabs with its horn.", 1.0, 1, "melee", [2], impact_effect="hit_fire",
                         sfx_hit="fire"),
        "scorch_charge": espc("Scorch Charge", "After charging: a blazing charge for heavy damage and Burn.", 2.4, 1,
                              "melee", [5], impact_effect="hit_fire", sfx_hit="fire", shake=0.9,
                              effects=[{"type": "status", "status": "burn", "chance": 0.5, "duration": 3,
                                        "on": "target"}]),
        "pincer": eatk("Pincer", "Snaps a claw.", 1.0, 1, "melee", [2], impact_effect="hit_water", sfx_hit="water_hit"),
        "shell_up": espc("Shell Up", "Hides behind salt: gains a Shield (25% max HP) and draws attacks.", 0, 0, "self", 3,
                         target="self", field_effect="shield_flash", sfx_cast="guard",
                         effects=[{"type": "shield", "percent_caster_hp": 0.25, "duration": 2, "on": "self"},
                                  {"type": "status", "status": "taunt", "value": 1.0, "duration": 2, "chance": 1.0,
                                   "on": "self"}]),
        "eel_snap": eatk("Eel Snap", "Two lightning-fast bites.", 1.1, 2, "melee", [2, 4], impact_effect="hit_water",
                         sfx_hit="water_hit"),
        "riptide_coil": espc("Riptide Coil", "Coils and crushes the weakest foe.", 1.7, 2, "melee", [5, 6],
                             impact_effect="hit_water", sfx_hit="water_hit", shake=0.5),
        "jelly_sting": eatk("Jelly Sting", "A stinging touch that may Poison.", 0.9, 1, "melee", [2],
                            impact_effect="hit_water", sfx_hit="water_hit",
                            effects=[{"type": "status", "status": "poison", "chance": 0.25, "duration": 2,
                                      "on": "target"}]),
        "tidal_glow": espc("Tidal Glow", "Its light heals all allies for 12% max HP.", 0, 0, "self", 4,
                           target="ally_all", field_effect="heal_ring", sfx_cast="heal",
                           effects=[{"type": "heal", "percent_max_hp": 0.12, "on": "allies"}]),
        "salt_shard": eatk("Salt Shard", "Flings a jagged shard.", 1.0, 1, "ranged", 2, projectile="water_bolt",
                           impact_effect="hit_water", sfx_cast="water", sfx_hit="water_hit"),
        "brine_curse": espc("Brine Curse", "A curse on every foe: DEF -20% for 3 turns.", 0.5, 1, "ranged", 4,
                            target="enemy_all", projectile="tide_orb", impact_effect="hit_water", sfx_cast="water",
                            sfx_hit="water_hit",
                            effects=[{"type": "status", "status": "def_down", "value": 0.2, "duration": 3,
                                      "chance": 1.0, "on": "target"}]),
        # elite extras
        "howl": espc("Howl", "A rallying howl: all allies gain +15% ATK for 2 turns.", 0, 0, "self", 3,
                     target="ally_all", field_effect="buff_rise", sfx_cast="nature",
                     effects=[{"type": "status", "status": "atk_up", "value": 0.15, "duration": 2, "chance": 1.0,
                               "on": "allies"}]),
        "flare_up": espc("Flare Up", "Bursts into flame: 140% ATK to all foes, may Burn.", 1.4, 1, "self", 3,
                         target="enemy_all", impact_effect="hit_fire", sfx_cast="fire", sfx_hit="fire",
                         effects=[{"type": "status", "status": "burn", "chance": 0.3, "duration": 2, "on": "target"}]),
        "tidal_mend": espc("Tidal Mend", "Heals itself for 20% max HP and gains +20% DEF.", 0, 0, "self", 3,
                           target="self", field_effect="heal_ring", sfx_cast="heal",
                           effects=[{"type": "heal", "percent_max_hp": 0.2, "on": "self"},
                                    {"type": "status", "status": "def_up", "value": 0.2, "duration": 2, "chance": 1.0,
                                     "on": "self"}]),
        # bosses
        "bark_armor": espc("Bark Armor", "Bark hardens over its hide: DEF +40% for 3 turns.", 0, 0, "self", 3,
                           target="self", field_effect="roots", sfx_cast="nature",
                           effects=[{"type": "status", "status": "def_up", "value": 0.4, "duration": 3, "chance": 1.0,
                                     "on": "self"}]),
        "glass_club": eatk("Glass Club", "A crushing blow with its saltglass arm.", 1.1, 2, "melee", [2, 3],
                           impact_effect="hit_water", sfx_hit="water_hit", shake=0.5),
        "shatterstorm": espc("Shatterstorm", "After charging: saltglass explodes across the whole party.", 1.9, 3,
                             "melee", [4, 5, 5], target="enemy_all", impact_effect="hit_water", sfx_hit="water_hit",
                             shake=1.0),
        "glass_carapace": espc("Glass Carapace", "Regrows its shell: Shield worth 20% max HP.", 0, 0, "self", 3,
                               target="self", field_effect="shield_flash", sfx_cast="guard",
                               effects=[{"type": "shield", "percent_caster_hp": 0.2, "duration": 3, "on": "self"}]),
        "inferno_nova": espc("Inferno Nova", "After charging: a nova of fire burns the whole party.", 1.7, 2, "self", 4,
                             target="enemy_all", impact_effect="hit_fire", sfx_cast="fire", sfx_hit="fire", shake=1.0,
                             effects=[{"type": "status", "status": "burn", "chance": 0.4, "duration": 3,
                                       "on": "target"}]),
        "maelstrom": espc("Maelstrom", "After charging: a whirlpool drags at every foe.", 1.6, 3, "self", 4,
                          target="enemy_all", impact_effect="hit_water", sfx_cast="water", sfx_hit="water_hit",
                          shake=0.9),
        "spore_storm": espc("Spore Storm", "After charging: choking spores poison the party.", 1.4, 2, "ranged", 4,
                            target="enemy_all", projectile="petal_bolt", impact_effect="hit_nature",
                            sfx_cast="nature", sfx_hit="nature",
                            effects=[{"type": "status", "status": "poison", "chance": 0.7, "duration": 3,
                                      "on": "target"}]),
    }
    s.update(new)
    s.update(phase7_enemy_skills())
    return s


# ====================================================================== stages
STAR_OBJ = {
    "clear": {"type": "clear", "text": "Clear the stage"},
    "no_ko": {"type": "no_ko", "text": "No heroes defeated"},
}


def turns_obj(n):
    return {"type": "turns", "max": n, "text": f"Clear within {n} turns"}


def burst_obj(n=1):
    return {"type": "burst", "min": n, "text": "Use Burst" if n == 1 else f"Use Burst {n} times"}


def ref_power(level, units):
    """Squad power of `units` average heroes at `level` (same formula as GameManager.unit_power)."""
    hp, atk, df, rec = 740 + 28 * (level - 1), 125 + 4 * (level - 1), 100 + 4 * (level - 1), 95 + 3 * (level - 1)
    return int(round(units * (hp * 0.1 + atk + df * 0.8 + rec * 0.5) / 10.0)) * 10


def spawn(enemy_id, level, **kw):
    d = {"enemy": enemy_id, "level": level}
    d.update(kw)
    return d


def build_world1():
    w = read("stages/ashroot_wilds.json")
    energies = [2, 2, 2, 3, 3, 3, 3, 4, 4, 5]
    units = [1, 1, 1, 1.2, 1.4, 2, 2, 2.2, 2.4, 2.6]
    stars = [
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], turns_obj(6)],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], turns_obj(6)],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], turns_obj(8)],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], burst_obj()],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], turns_obj(12)],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], turns_obj(12)],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], burst_obj()],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], turns_obj(14)],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], turns_obj(18)],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], burst_obj(2)],
    ]
    # teach new mechanics gradually (healers 1-6, buffers 1-7, debuffs 1-8, elites 1-9, boss mechanics 1-10)
    waves = {
        "ashroot_06": [[spawn("bramble_pup", 5), spawn("glowcap", 5)],
                       [spawn("bramble_pup", 6, hp_scale=1.2), spawn("moss_slime", 5)]],
        "ashroot_07": [[spawn("cinder_slime", 6), spawn("cinder_slime", 6)],
                       [spawn("cinder_slime", 7, hp_scale=1.2), spawn("emberwisp", 6)]],
        "ashroot_08": [[spawn("tidefin", 7), spawn("tide_slime", 7)],
                       [spawn("tidefin", 8, hp_scale=1.2), spawn("hexmoth", 7)]],
        "ashroot_09": [[spawn("cinder_slime", 7), spawn("tidefin", 7)],
                       [spawn("bramble_pup", 7), spawn("glowcap", 7)],
                       [spawn("cinder_slime", 8), spawn("elite_tidefin", 8), spawn("bramble_pup", 8)]],
    }
    drops_by = {1: [], 2: [], 3: [], 4: [("ember_fragment", 0.15)], 5: [("tide_fragment", 0.2)],
                6: [("sprout_fragment", 0.25), ("verdant_wisp", 0.15)], 7: [("ember_fragment", 0.3), ("ember_wisp", 0.2), ("flame_core", 0.1)],
                8: [("tide_fragment", 0.3), ("tide_wisp", 0.2), ("current_core", 0.1)],
                9: [("radiant_wisp", 0.15), ("verdant_core", 0.1)],
                10: [("verdant_core", 0.3), ("radiant_wisp", 0.3)]}
    for i, s in enumerate(w["stages"]):
        n = i + 1
        s["energy"] = energies[i]
        s["recommended_power"] = ref_power(s["recommended_level"], units[i])
        s["stars"] = stars[i]
        s["drops"] = [{"item": it, "chance": c, "min": 1, "max": 1} for (it, c) in drops_by[n]]
        s["first_clear"] = {"gems": 25 if s.get("boss") else 5}
        if s["id"] in waves:
            s["waves"] = waves[s["id"]]
        s["music"] = "boss" if s.get("boss") else "battle"
        if n == 10:
            s["first_clear"]["items"] = {"verdant_core": 1, "radiant_wisp": 1}
    w["type"] = "story"
    w["number"] = 1
    w["order"] = 1
    w["subtitle"] = "Forest, stone and old ruins scarred by fires that burn from below."
    w["hints_by_stage"] = {}
    w["hints"] = {"ashroot_06": "healers", "ashroot_07": "buffs", "ashroot_08": "debuffs", "ashroot_09": "elites"}
    for s in w["stages"]:
        if s["id"] in w["hints"] and not s.get("hint"):
            s["hint"] = w["hints"][s["id"]]
    w["stages"][9]["hint"] = "boss"
    del w["hints"]
    del w["hints_by_stage"]
    return w


def build_world2():
    with open(os.path.join(os.path.dirname(__file__), "route_w2.json")) as f:
        route = json.load(f)["route_pos"]
    stages = []
    names = ["Saltglass Shore", "Tidepool Trail", "Crab Crossing", "Glimmer Grotto", "Echoing Caves", "Drowned Shrine",
             "Wreck of the Halcyon", "Broken Keel", "Stormdeck", "The Saltglass Spire"]
    summaries = [
        "The beach glitters with shards of salt-glass. Something scuttles.",
        "Tidepools full of slimes, and a jelly that heals them.",
        "Shellcrabs hold the ford behind their crystal shells. Break through.",
        "Glowing caves where curses hang in the air.",
        "The echoes carry a charging beetle's rumble.",
        "An old shrine half under the tide. Guarded by elites.",
        "A great ship run aground. Its crew is long gone - but not its passengers.",
        "Eels coil in the broken hull. They go for the weakest first.",
        "Lightning over the wreck. Every enemy here fights together.",
        "The spire of saltglass, and the Colossus that grew from it.",
    ]
    bgs = ["bg_shore"] * 3 + ["bg_caves"] * 3 + ["bg_wreck"] * 3 + ["bg_spire"]
    levels = [12, 13, 14, 15, 16, 17, 18, 20, 22, 24]
    energy = [5, 5, 5, 6, 6, 6, 7, 7, 8, 8]
    W = [
        [[spawn("tide_slime", 11), spawn("tide_slime", 11), spawn("tidefin", 12)],
         [spawn("shellcrab", 12), spawn("tidefin", 12)]],
        [[spawn("tide_slime", 12), spawn("drift_jelly", 12), spawn("tide_slime", 12)],
         [spawn("brine_eel", 13), spawn("drift_jelly", 12)]],
        [[spawn("shellcrab", 13), spawn("tidefin", 13), spawn("brine_eel", 13)],
         [spawn("shellcrab", 14), spawn("shellcrab", 13), spawn("tide_slime", 13)]],
        [[spawn("salt_wraith", 14), spawn("moss_slime", 14), spawn("hexmoth", 14)],
         [spawn("salt_wraith", 15), spawn("glowcap", 14), spawn("bramble_pup", 15)]],
        [[spawn("scorch_beetle", 15), spawn("emberwisp", 15)],
         [spawn("scorch_beetle", 16), spawn("salt_wraith", 15), spawn("cinder_slime", 16)]],
        [[spawn("drift_jelly", 16), spawn("brine_eel", 16), spawn("tidefin", 16)],
         [spawn("elite_shellcrab", 17), spawn("salt_wraith", 16), spawn("drift_jelly", 16)]],
        [[spawn("brine_eel", 17), spawn("hexmoth", 17), spawn("emberwisp", 17)],
         [spawn("elite_brine_eel", 18), spawn("glowcap", 17), spawn("shellcrab", 18)]],
        [[spawn("brine_eel", 19), spawn("brine_eel", 19), spawn("drift_jelly", 19)],
         [spawn("elite_scorch_beetle", 20), spawn("salt_wraith", 19), spawn("tide_slime", 19)],
         [spawn("elite_brine_eel", 20), spawn("shellcrab", 20), spawn("emberwisp", 19)]],
        [[spawn("salt_wraith", 21), spawn("elite_hexmoth", 21), spawn("scorch_beetle", 21)],
         [spawn("elite_shellcrab", 22), spawn("drift_jelly", 21), spawn("brine_eel", 21), spawn("emberwisp", 21)],
         [spawn("elite_emberwisp", 22), spawn("elite_brine_eel", 22), spawn("glowcap", 22)]],
        [[spawn("shellcrab", 23), spawn("salt_wraith", 23), spawn("drift_jelly", 23)],
         [spawn("saltglass_colossus", 24)]],
    ]
    stars = [
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], turns_obj(12)],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], turns_obj(12)],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], burst_obj()],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], turns_obj(14)],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], burst_obj(2)],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], turns_obj(14)],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], turns_obj(16)],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], turns_obj(20)],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], burst_obj(3)],
        [STAR_OBJ["clear"], STAR_OBJ["no_ko"], burst_obj(2)],
    ]
    drops_by = [
        [("tide_fragment", 0.4), ("tide_wisp", 0.2)],
        [("tide_fragment", 0.4), ("current_core", 0.1)],
        [("current_core", 0.2), ("radiant_wisp", 0.15)],
        [("sprout_fragment", 0.4), ("verdant_core", 0.15)],
        [("ember_fragment", 0.4), ("flame_core", 0.15)],
        [("current_core", 0.25), ("abyss_crystal", 0.05)],
        [("flame_core", 0.2), ("verdant_core", 0.2), ("radiant_wisp", 0.2)],
        [("current_core", 0.3), ("abyss_crystal", 0.08)],
        [("radiant_wisp", 0.3), ("spark_sigil", 0.1)],
        [("abyss_crystal", 0.3), ("prism_shard", 0.1)],
    ]
    hints = {0: "shields", 3: "debuffs", 4: "charge", 9: "boss2"}
    for i in range(10):
        st = {"id": "saltglass_%02d" % (i + 1), "number": i + 1, "name": names[i], "background": bgs[i],
              "route_pos": route[i], "recommended_level": levels[i], "summary": summaries[i],
              "waves": W[i], "energy": energy[i], "recommended_power": ref_power(levels[i], 3 + (i // 4) * 0.5),
              "rewards": {"xp": 1200 + i * 250, "gold": 300 + i * 60, "first_clear_gold": 400 + i * 50},
              "first_clear": {"gems": 25 if i == 9 else 5}, "stars": stars[i],
              "drops": [{"item": it, "chance": c, "min": 1, "max": 1} for (it, c) in drops_by[i]],
              "music": "boss" if i == 9 else "battle2",
              "unlocks": ["saltglass_%02d" % (i + 2)] if i < 9 else []}
        if i in hints:
            st["hint"] = hints[i]
        if i == 9:
            st["boss"] = True
            st["first_clear"]["items"] = {"prism_shard": 1, "abyss_crystal": 1}
        stages.append(st)
    return {"id": "saltglass_reach", "name": "Saltglass Reach", "type": "story", "number": 2, "order": 2,
            "subtitle": "A coast of glittering salt-glass, drowned ruins and a stranded warship.",
            "description": "The tides beyond the Wilds glitter with salt-glass. Something enormous sleeps in the spire.",
            "route_map": "res://assets/environments/bg_routemap_w2.png", "music": "world2",
            "requires": "ashroot_10", "stages": stages}


TOWERS = {
    "ember_tower": dict(name="Ember Tower", element="fire", counter="water", bg="bg_tower_ember",
                        mats=("ember_fragment", "flame_core", "infernal_crystal"),
                        pools=[["cinder_slime", "emberwisp"], ["cinder_slime", "scorch_beetle", "emberwisp"],
                               ["elite_cinder_slime", "scorch_beetle", "emberwisp", "tide_slime"]],
                        bosses=("scorch_matriarch", "emberwisp_tyrant"),
                        elites=("elite_cinder_slime", "elite_emberwisp", "elite_scorch_beetle")),
    "tide_tower": dict(name="Tide Tower", element="water", counter="nature", bg="bg_tower_tide",
                       mats=("tide_fragment", "current_core", "abyss_crystal"),
                       pools=[["tide_slime", "tidefin"], ["tidefin", "drift_jelly", "shellcrab"],
                              ["brine_eel", "salt_wraith", "drift_jelly", "shellcrab"]],
                       bosses=("deepwater_matron", "brine_leviathan"),
                       elites=("elite_tidefin", "elite_shellcrab", "elite_brine_eel")),
    "verdant_tower": dict(name="Verdant Tower", element="nature", counter="fire", bg="bg_tower_verdant",
                          mats=("sprout_fragment", "verdant_core", "ancient_seed"),
                          pools=[["moss_slime", "bramble_pup"], ["bramble_pup", "glowcap", "hexmoth"],
                                 ["hexmoth", "glowcap", "bramble_pup", "moss_slime"]],
                          bosses=("elder_glowcap", "thornback_elder"),
                          elites=("elite_bramble_pup", "elite_hexmoth", "elite_bramble_pup")),
}


def build_towers():
    out = {}
    for tid, t in TOWERS.items():
        frag, core, crys = t["mats"]
        wisp = WISP[t["element"]]
        floors = []
        for f in range(1, 11):
            lvl = 4 + f * 2 if f <= 5 else 6 + f * 2
            tier = 0 if f <= 3 else (1 if f <= 6 else 2)
            pool = t["pools"][tier]
            boss = f in (5, 10)
            waves = []
            nwaves = 2 if f < 4 else 3
            for wv in range(nwaves):
                count = 2 + (1 if f >= 3 else 0) + (1 if f >= 8 and wv > 0 else 0)
                wave = []
                for k in range(count):
                    eid = pool[(wv + k + f) % len(pool)]
                    wave.append(spawn(eid, lvl - (1 if k else 0)))
                if f in (4, 7, 9) and wv == nwaves - 1:
                    wave[0] = spawn(t["elites"][min(tier, 2)], lvl + 1)
                waves.append(wave)
            if boss:
                waves = waves[:2] + [[spawn(t["bosses"][0 if f == 5 else 1], lvl + 2)]]
            drop_list = []
            if f <= 4:
                drop_list += [(frag, 0.6, 1, 2), (wisp, 0.35, 1, 1)]
            if f <= 7:
                drop_list += [(core, 0.12 + 0.05 * (f - 1), 1, 1)]
            if f >= 6:
                drop_list += [(crys, 0.12 + 0.04 * (f - 6), 1, 1), (wisp, 0.5, 1, 2), ("radiant_wisp", 0.2, 1, 1)]
            first = {"items": {frag: 3, wisp: 2}} if f < 5 else {"items": {core: 1, wisp: 2}}
            if f == 5:
                first = {"gems": 50, "items": {core: 2, wisp: 3, "spark_sigil": 1}}
            elif f == 10:
                first = {"gems": 100, "items": {crys: 2, "prism_shard": 1, "radiant_wisp": 2}}
            elif f >= 6:
                first = {"items": {crys: 1, "radiant_wisp": 1}}
            floors.append({
                "id": f"{tid}_{f:02d}", "number": f, "floor": f,
                "name": ("Guardian's Hall" if boss else f"Floor {f}"),
                "background": t["bg"], "recommended_level": lvl, "energy": 5 + (f - 1) // 2,
                "recommended_power": ref_power(lvl, {1: 2, 2: 2, 3: 2.2, 4: 2.5, 5: 2.8}.get(f, 3.5 if f < 10 else 4)),
                "summary": ("The tower's guardian waits here." if boss else
                            f"Floor {f} of the {t['name']}. Bring {t['counter'].capitalize()} heroes."),
                "waves": waves, "boss": boss, "music": "boss" if boss else "tower",
                "rewards": {"xp": 300 + f * 180, "gold": 150 + f * 50, "first_clear_gold": 200 + f * 60},
                "drops": [dict(zip(("item", "chance", "min", "max"), d)) for d in drop_list],
                "first_clear": first,
                "stars": [STAR_OBJ["clear"], STAR_OBJ["no_ko"], turns_obj(10 + nwaves * 2)],
                "unlocks": [f"{tid}_{f + 1:02d}"] if f < 10 else [],
                "tier": 1 if f <= 5 else 2,
            })
        out[tid] = {"id": tid, "name": t["name"], "type": "tower", "element": t["element"],
                    "counter_element": t["counter"],
                    "description": f"Climb for {ITEMS[frag]['name']}s, {ITEMS[core]['name']}s and "
                                   f"{ITEMS[crys]['name']}s.",
                    "materials": list(t["mats"]), "music": "tower", "stages": floors}
    return out


# Phase 7 endgame: The Fracture (rotating hard bosses). Fracture I = Ashen Warden, Normal / Hard / Expert.
def build_fracture():
    tiers = [("Normal", 26, [], {"gems": 100, "items": {"flame_core": 2, "radiant_wisp": 2}}),
             ("Hard", 30, [spawn("elite_emberwisp", 29)], {"gems": 150, "items": {"infernal_crystal": 2}}),
             ("Expert", 34, [spawn("elite_emberwisp", 33), spawn("elite_scorch_beetle", 33)],
              {"gems": 200, "items": {"infernal_crystal": 3, "prism_shard": 1}})]
    floors = []
    for i, (name, lvl, adds, first) in enumerate(tiers, 1):
        floors.append({
            "id": f"fracture_01_{name.lower()}", "number": i, "floor": i, "name": f"Ashen Warden - {name}",
            "difficulty": name.upper(), "background": "bg_tower_ember", "recommended_level": lvl, "energy": 10 + i * 2,
            "recommended_power": ref_power(lvl, 4 + i), "boss": True, "music": "boss",
            "summary": "The Ashen Warden guards the first Fracture. Break its armour; Water hits hardest.",
            "waves": [adds + [spawn("ashen_warden", lvl)]] if adds else [[spawn("ashen_warden", lvl)]],
            "rewards": {"xp": 2000 + i * 800, "gold": 800 + i * 300, "first_clear_gold": 1500 * i},
            "drops": [{"item": "flame_core", "chance": 0.5, "min": 1, "max": 2},
                      {"item": "infernal_crystal", "chance": 0.15 * i, "min": 1, "max": 1}],
            "first_clear": first,
            "stars": [STAR_OBJ["clear"], STAR_OBJ["no_ko"], turns_obj(12)],
            "unlocks": [f"fracture_01_{tiers[i][0].lower()}"] if i < len(tiers) else [],
            "tier": i,
            "recommended_roles": ["Breaker", "Defender", "Healer"],
        })
    return {"id": "the_fracture", "name": "Fracture I", "type": "fracture", "element": "fire", "counter_element": "water",
            "requires": "saltglass_10",
            "description": "Endgame boss encounters for developed squads. Fracture I: the Ashen Warden.",
            "materials": ["flame_core", "infernal_crystal", "prism_shard"], "music": "boss", "stages": floors}


# ====================================================================== economy tables
SUMMON = {
    "banners": {
        "standard": {
            "id": "standard", "name": "Embergate - Standard", "currency": "gems", "single_cost": 100,
            "multi_cost": 1000, "multi_count": 10, "art": "res://assets/ui/banner_standard.png",
            "description": "Every hero in the realm can answer the Embergate's call.",
            "rates": {"3": 0.75, "4": 0.22, "5": 0.03},
            "pool": ["kael_emberclaw", "mira_tidesong", "thorne_mossguard", "rhea_flintwhistle", "corin_saltmarsh",
                     "wren_briarshot", "voss_ashmantle", "nerys_frostwake", "faye_lumenbloom",
                     "seraphine_pyrelance", "aldric_deepvow", "gorran_oakheart"],
        }
    },
    "duplicate_shards": {"3": 10, "4": 30, "5": 100},
}

MISSIONS = {
    "daily": [
        {"id": "d_stages", "text": "Clear 3 stages", "event": "stage_clear", "target": 3, "reward": {"gold": 1500}},
        {"id": "d_burst", "text": "Use Burst 3 times", "event": "burst_use", "target": 3,
         "reward": {"items": {"radiant_wisp": 1}}},
        {"id": "d_enemies", "text": "Defeat 20 enemies", "event": "enemy_kill", "target": 20, "reward": {"gold": 1000}},
        {"id": "d_train", "text": "Train a hero", "event": "train", "target": 1,
         "reward": {"items": {"ember_wisp": 1, "tide_wisp": 1, "verdant_wisp": 1}}},
        {"id": "d_tower", "text": "Clear a Tower floor", "event": "tower_clear", "target": 1, "reward": {"gems": 10}},
    ],
    "daily_chest": {"needed": 4, "reward": {"gems": 30, "gold": 2000, "items": {"radiant_wisp": 1}}},
    "weekly": [
        {"id": "w_stages", "text": "Clear 25 stages", "event": "stage_clear", "target": 25, "reward": {"gems": 100}},
        {"id": "w_bosses", "text": "Defeat 5 bosses", "event": "boss_kill", "target": 5,
         "reward": {"gems": 50, "items": {"prism_shard": 1}}},
        {"id": "w_tower", "text": "Clear 10 Tower floors", "event": "tower_clear", "target": 10,
         "reward": {"items": {"flame_core": 1, "current_core": 1, "verdant_core": 1}}},
        {"id": "w_summon", "text": "Summon 5 times", "event": "summon", "target": 5,
         "reward": {"gold": 5000, "items": {"spark_sigil": 1}}},
    ],
}

LOGIN = {"cycle": [
    {"day": 1, "reward": {"gold": 3000}},
    {"day": 2, "reward": {"items": {"radiant_wisp": 2}}},
    {"day": 3, "reward": {"gems": 50}},
    {"day": 4, "reward": {"items": {"ember_fragment": 2, "tide_fragment": 2, "sprout_fragment": 2}}},
    {"day": 5, "reward": {"gems": 50}},
    {"day": 6, "reward": {"items": {"prism_shard": 1}}},
    {"day": 7, "reward": {"gems": 150}},
]}


def build_progression():
    p = read("progression.json")
    p["_comment"] = "Balance knobs. Tweak these instead of editing scripts."
    p["party_size"] = 5
    p["party_size_max_future"] = 5
    p["max_level_by_rarity"] = {str(k): v for k, v in MAX_LEVEL.items()}
    p["energy"] = {"base_max": 20, "per_rank": 0.5, "cap": 60, "regen_seconds": 180}
    p["rank_rewards"] = {"gems_every": 5, "gems": 50}
    p["training"] = {"gold_per_xp": 0.5, "element_bonus": 0.5}
    p["burst_levels"] = {"max": 5, "xp": [0, 4, 10, 18, 30], "per_use": 1, "shards_per_step": 20,
                         "shard_step_xp": 3}
    p["power"] = {"hp": 0.1, "atk": 1.0, "def": 0.8, "rec": 0.5, "burst_level": 0.03}
    p["unlocks"] = {"auto": "ashroot_04", "units": "ashroot_05", "squad": "ashroot_05", "training": "ashroot_06",
                    "tower": "ashroot_07", "evolution": "ashroot_08", "summon": "ashroot_09",
                    "missions": "ashroot_10", "world2": "ashroot_10"}
    p["unlock_gifts"] = {"ashroot_05": {"hero_by_starter": {"kael_emberclaw": "corin_saltmarsh",
                                                            "mira_tidesong": "wren_briarshot",
                                                            "thorne_mossguard": "rhea_flintwhistle"},
                                        "items": {"radiant_wisp": 1}},
                         "ashroot_06": {"items": {"ember_wisp": 2, "tide_wisp": 2, "verdant_wisp": 2}},
                         "ashroot_08": {"items": {"ember_fragment": 2, "tide_fragment": 2, "sprout_fragment": 2}},
                         "ashroot_09": {"gems": 150}}
    p["legacy_items"] = LEGACY_ITEMS
    p["inventory_stack_limit"] = 9999
    p["starting_items"] = {"ember_wisp": 1, "tide_wisp": 1, "verdant_wisp": 1}
    # Phase 7 combat rules (docs/dev/BALANCE-GUIDE.md)
    p["combat"].update({"max_mitigation": 0.75, "status_stat_cap": 0.6, "boss_status_resist": 0.3,
                        "boss_status_dr_step": 0.15})
    p["break"] = {"base": 12, "breaker_mult": 2.0, "weak_mult": 1.5, "turns": 2, "damage_taken_up": 0.5}
    return p


# ====================================================================== main
def main():
    write("statuses.json", STATUSES)
    write("items/items.json", ITEMS)
    write("drop_tables.json", DROP_TABLES)
    chars = build_characters()
    # remove stale character files, then write every form
    cdir = os.path.join(D, "characters")
    for f in os.listdir(cdir):
        if f.endswith(".json"):
            os.remove(os.path.join(cdir, f))
    for cid, c in chars.items():
        write(f"characters/{cid}.json", c)
    hs = {"_comment": "power = total ATK multiplier split across hits. level_bonus = per Burst level above 1."}
    hs.update(phase7_skills(copy.deepcopy(HERO_SKILLS)))
    write("skills/hero_skills.json", hs)
    es = {"_comment": "Enemy skills. kind 'skill' = special; charged skills are telegraphed by the AI."}
    es.update(build_enemy_skills())
    write("skills/enemy_skills.json", es)
    edir = os.path.join(D, "enemies")
    for f in os.listdir(edir):
        if f.endswith(".json"):
            os.remove(os.path.join(edir, f))
    for eid, e in build_enemies().items():
        write(f"enemies/{eid}.json", e)
    write("stages/ashroot_wilds.json", build_world1())
    write("stages/saltglass_reach.json", build_world2())
    for tid, t in build_towers().items():
        write(f"towers/{tid}.json", t)
    write("towers/the_fracture.json", build_fracture())
    write("summon.json", SUMMON)
    write("missions.json", MISSIONS)
    write("login_rewards.json", LOGIN)
    write("progression.json", build_progression())
    print("content: %d hero forms, %d enemies, %d hero skills" % (len(chars), len(build_enemies()), len(HERO_SKILLS)))


if __name__ == "__main__":
    main()
