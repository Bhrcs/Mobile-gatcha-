# Cinderbound - Content Guide (v0.4.0)

Almost everything in Cinderbound is data. The game reads JSON files from `data/`
at start-up, validates the references between them and reports problems in the
log (and in `Cinderbound.exe -- --selftest`). This guide explains every file and
how to add new heroes, enemies, stages, towers, banners and missions.

> Editing data requires the project source (the `data/` folder is packed inside
> the exe). The generator `tools/make_content.py` rebuilds most Phase 4 data;
> either edit its tables and run `python3 tools/make_content.py`, or edit the JSON
> directly (then do not re-run the generator, or port your edits into it).

## File map

| File / folder | Contents |
|---|---|
| `data/characters/<form_id>.json` | one file per hero **form** |
| `data/skills/hero_skills.json` | hero normal attacks and Bursts |
| `data/skills/enemy_skills.json` | enemy attacks, specials, curses, heals |
| `data/enemies/<enemy_id>.json` | enemies, elites and bosses (stats, skills, AI) |
| `data/stages/<world>.json` | a story world and its stages |
| `data/towers/<tower>.json` | a tower and its floors |
| `data/items/items.json` | materials, wisps, sigils, misc items |
| `data/drop_tables.json` | named drop tables used by enemies |
| `data/statuses.json` | status effects (Burn, Shield, ATK Down...) |
| `data/summon.json` | summon banners, rates, duplicate conversion |
| `data/missions.json` | daily / weekly missions and the daily chest |
| `data/login_rewards.json` | the 7-day login cycle |
| `data/progression.json` | curves, energy, rank rewards, unlocks, gifts, combat knobs |
| `data/elements.json` | element chart and colours |
| `data/tutorial_hints.json` | one-time battle tips |

Art lives in `assets/` (`characters/<form_id>/`, `enemies/<id>/`,
`environments/battle/`, `icons/`, `ui/`), audio in `assets/audio/`.

## Heroes

A hero **family** (e.g. `kael`) has 1-3 **forms** (3* -> 4* -> 5*). Each form is a
file in `data/characters/`:

```json
{
  "id": "kael_blazeheart", "family": "kael", "name": "Kael Blazeheart",
  "element": "fire", "role": "Attacker", "class": "ATTACKER",
  "rarity": 4, "form_index": 1,
  "forms": ["kael_emberclaw", "kael_blazeheart", "kael_cinderlord"],
  "starter": false, "level": 1, "max_level": 25,
  "base_stats": {"hp": 1178, "atk": 227, "def": 129, "rec": 103, "spd": 105},
  "growth":     {"hp": 33,   "atk": 6,   "def": 4,   "rec": 2,   "spd": 0},
  "normal_attack": "ember_slash", "burst": "inferno_break_ii",
  "passive": {"name": "...", "description": "...",
              "effects": [{"kind": "stat_up", "stat": "atk", "value": 0.12,
                           "condition": "hp_above", "threshold": 0.7}]},
  "leader_skill": {"name": "...", "description": "...",
                   "effects": [{"stat": "atk", "value": 0.10, "element": "fire"}]},
  "evolution": {"into": "kael_cinderlord", "gold": 15000,
                "materials": {"flame_core": 8, "infernal_crystal": 3, "prism_shard": 1}},
  "sprite": {"sheet": "res://assets/characters/kael_blazeheart/kael_blazeheart_sheet.png",
             "meta": "res://assets/characters/kael_blazeheart/kael_blazeheart_sheet.json", "scale": 8},
  "portrait": "res://assets/characters/kael_blazeheart/kael_blazeheart_portrait.png",
  "lore": "...", "description": "..."
}
```

* Stats at level L = `base + growth x (L - 1)`. `max_level` should follow
  `progression.json -> max_level_by_rarity` (3*: 15, 4*: 25, 5*: 35).
* The final form has `"evolution": null`. Evolution resets to Lv.1 and keeps the
  Burst level. Materials must exist in `items.json` and should have a source
  (a stage drop, drop table, tower floor, mission or login reward) - the
  OBTAINED FROM screen lists them automatically.
* **Passive effect kinds**: `stat_up` (stat, value, optional `condition:
  hp_above` + `threshold`), `heal_received_up`, `damage_taken_down`,
  `burst_gain_up`, `regen` (% max HP per turn), `crit_up`, `guard_bonus`,
  `damage_vs_low_hp` (value, threshold), `damage_vs_debuffed`. Add
  `"scope": "allies"` to apply it to the whole squad.
* **Leader skill effects**: `{"stat": "atk|def|hp|rec", "value": 0.08,
  "element": "fire"}` (element optional = everyone) or
  `{"kind": "burst_gain_up", "value": 0.1}` (any passive kind).
* Sprite sheets: rows of frames described by the `_sheet.json` meta
  (`frame_size`, `animations: {name: {row, frames, fps, loop}}`); heroes need
  `idle, attack, hit, guard, burst, victory, ko`. The art tools are
  `tools/hero_gen.py`, `tools/make_heroes_p4.py` and `tools/portrait_gen.py`.
* To make the hero summonable add its **first form** id to a banner `pool` in
  `summon.json`. The Codex order is set in `Database.family_ids()`.

## Skills

```json
"inferno_break": {
  "name": "Inferno Break", "kind": "burst", "description": "...",
  "target": "enemy_single", "power": 2.2, "hits": 6, "motion": "melee",
  "anim": "burst", "hit_weights": [1,1,1,1.5,1.5,2], "hit_frames": [3,5,7,9,9,9],
  "burst_fx": "ember_rush", "hit_effect": "slash_ember", "impact_effect": "hit_fire",
  "sfx_hit": "sword", "shake": 1.0,
  "level_bonus": {"power": 0.12, "chance": 0.05},
  "effects": [{"type": "status", "status": "burn", "chance": 0.2, "duration": 3, "on": "target"}]
}
```

* `target`: `enemy_single`, `enemy_all`, `ally_all`, `ally_lowest`, `self`.
* `power` is the total ATK multiplier split over `hits`.
* `motion`: `melee` (dash in), `ranged` (projectile), `self` (cast in place -
  also used for all-target casts).
* **Effects** (`type`): `status` (status, value, duration, chance), `heal`
  (`percent_max_hp`, `rec_multiplier`), `shield` (`percent_caster_hp`,
  duration), `cleanse` (count), `burst` (value - fills allies' gauges).
  `on`: `target`, `allies`, `self`, `foes`, `target_ally` (with `ally_lowest`).
* **Burst levels** (`level_bonus`, per level above 1): `power`, `heal`, `shield`,
  `value` (status strength), `chance`, `burst`, `gauge` (lower Burst cost),
  `duration_at: [levels]` (+1 turn at those levels). Burst EXP thresholds are in
  `progression.json -> burst_levels`.
* `burst_fx` presets: `ember_rush`, `frost_waltz`, `volley`, `tide_ring`,
  `hearth_hymn`, `bulwark`, `grove_bastion`, `bloom`, `litany`.

## Enemies and AI

```json
{
  "id": "scorch_beetle", "name": "Scorch Beetle", "element": "fire", "role": "burst",
  "base_stats": {"hp": 260, "atk": 44, "def": 40, "spd": 50},
  "skills": {"normal": "horn_jab", "special": "scorch_charge"},
  "ai": {"profile": "charger", "skill_chance": 0.0, "targeting": "random", "charge_every": 3},
  "rewards": {"xp": 16, "gold": [8, 14]}, "drop_table": "fire_uncommon",
  "sprite": {"sheet": "...", "meta": "...", "scale": 7}
}
```

* Stats scale with level (`progression.json -> enemy_scaling`).
* **AI profiles** (`scripts/combat/enemy_ai.gd`): `attacker`, `healer`, `tank`,
  `buffer`, `debuffer`, `charger` (`charge_every`), `boss`.
* **Targeting**: `random` (Provoke-weighted), `lowest_hp`, `highest_atk`.
  A hero with Provoke always overrides smart targeting.
* **Elites**: `"elite": true`, `"tint": "#ffd060"`, `skills.extra` and
  `ai.extra_every: 3`.
* **Bosses**: `"boss": true` and an AI like
  ```json
  "ai": {"profile": "boss", "targeting": "lowest_hp",
         "pattern": ["normal", "curse", "normal", "charge"],
         "curse": "brine_curse", "heal": "tidal_glow",
         "summon": {"enemy": "tide_slime", "level_offset": -3, "every": 3, "count": 1, "max": 2},
         "hp_events": [{"below": 0.6, "skill": "bark_armor"}],
         "phase2": {"below": 0.5, "atk_up": 0.3, "pattern": ["normal", "charge"],
                    "announce": "The Colossus cracks - its core blazes!", "skill": "glass_carapace"}}
  ```
  `charge` spends a turn CHARGING (WARNING banner) and releases `skills.special`
  next turn. Minions appear in front of the boss (max 2, max 4 enemies alive) and
  drop no items.
* `drop_table` is a name from `drop_tables.json` or an inline list.

## Drop tables

```json
"fire_boss": {
  "guaranteed": [{"item": "flame_core", "chance": 1, "min": 1, "max": 1}],
  "rolls":      [{"item": "infernal_crystal", "chance": 0.15, "min": 1, "max": 1}]
}
```

## Stages (story worlds)

`data/stages/<world>.json`:

```json
{"id": "saltglass_reach", "name": "Saltglass Reach", "type": "story", "number": 2,
 "order": 2, "requires": "ashroot_10", "music": "world2",
 "route_map": "res://assets/environments/bg_routemap_w2.png",
 "stages": [ { ...stage... } ]}
```

Stage fields: `id`, `number`, `name`, `summary`, `background` (battle set:
`assets/environments/battle/<name>_{far,mid,ground,fore}.png`), `route_pos`
(map pixel), `recommended_level`, `recommended_power`, `energy`, `boss`,
`hint` (tutorial id), `music`, `waves` (list of waves; each wave is a list of
`{"enemy", "level", "hp_scale"?}` or `{"enemy_by_leader_element": {...}}`),
`rewards` (`xp`, `gold`, `first_clear_gold`), `drops` (list of
`{item, chance, min, max}` rolled once on victory), `first_clear`
(`{"gems": 5, "items": {...}}` - 5 Gems normally, 25 on bosses), `stars`
(three objectives: `{"type": "clear"}`, `{"type": "no_ko"}`,
`{"type": "turns", "max": 12}`, `{"type": "burst", "min": 2}` - each with a
`text`), `unlocks` (next stage ids).
A new world appears as a tab on the Quest map when its `requires` stage is
cleared. Add its first stage to `progression.json -> unlocks` if it should be
announced as a feature.

## Towers

`data/towers/<tower>.json`: `id`, `name`, `element`, `counter_element`,
`materials`, `music` and `stages` (floors) with the same fields as stages plus
`floor`. Floors unlock one another through `unlocks`. The first floor of every
tower is unlocked with the `tower` feature.

## Items

```json
"ember_wisp": {"name": "Ember Wisp", "icon": "res://assets/icons/ember_wisp.png",
               "category": "training", "rarity": 1, "sort": 50, "xp": 600,
               "element": "fire", "use": "...", "description": "..."}
```

Categories: `material`, `training`, `item` (inventory tabs). `xp` makes an item
a training wisp (+`training.element_bonus` for same-element heroes);
`burst_xp` makes it a Burst trainer. Stack limit: `inventory_stack_limit`.
Renamed items can be mapped for old saves in `progression.json -> legacy_items`.

## Statuses

`kind`: `dot` (`dot_percent_max_hp`), `hot` (value = % max HP), `stat_mod`
(`stat`, `sign` +1/-1), `shield` (value = HP absorbed), `damage_reduction`,
`taunt`, `charge`. `negative: true` statuses can be cleansed.

## Summon banners

```json
"standard": {"name": "Embergate - Standard", "currency": "gems",
             "single_cost": 100, "multi_cost": 1000, "multi_count": 10,
             "rates": {"3": 0.75, "4": 0.22, "5": 0.03},
             "pool": ["kael_emberclaw", "..."], "art": "res://assets/ui/banner_standard.png"}
```

Rates are normalised and shown exactly as used (DETAILS screen).
`duplicate_shards` sets the Soul Shards per rarity for heroes already owned.

## Missions and login

`missions.json`: `daily` / `weekly` lists of
`{"id", "text", "event", "target", "reward"}`. Events: `stage_clear`,
`tower_clear`, `enemy_kill`, `boss_kill`, `burst_use`, `train`, `summon`.
`daily_chest`: `{"needed": 4, "reward": {...}}`.
`login_rewards.json`: `cycle` of 7 `{day, reward}`; missed days continue the
cycle. Rewards everywhere use `{"gold", "gems", "soul_shards", "items": {id: qty}}`.

## Progression knobs (`progression.json`)

* `max_level_by_rarity`, `unit_xp_curve`, `rank_xp_curve`, `rank_max`,
  `enemy_scaling` (per-level stat / reward growth for enemies)
* `energy`: `base_max`, `per_rank`, `cap`, `regen_seconds`
* `rank_rewards`: `gems_every`, `gems`
* `training`: `gold_per_xp`, `element_bonus`
* `burst_levels`: `max`, `xp`, `per_use`, `shards_per_step`, `shard_step_xp`
* `unlocks`: feature -> stage id (`auto`, `units`, `squad`, `training`, `tower`,
  `evolution`, `summon`, `missions`, `world2`)
* `unlock_gifts`: stage id -> `{gems, items, hero_by_starter}` (given once)
* `starting_items`, `party_size`, `power` weights, `combat` and `burst` knobs

## Checking your changes

1. `godot --headless -- --selftest` (or `Cinderbound.exe -- --selftest`)
   prints `SELFTEST OK` or the broken references.
2. `tests/run_tests.sh` runs the rule tests, click-through flows and the balance
   simulation. `godot --headless res://tests/balance_sim.tscn -- --probe=stage_a,stage_b --squad=kael_emberclaw:10,mira_tidesong:8`
   estimates win rates for a stage with a given squad.
