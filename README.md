# CINDERBOUND — prototype v0.5

An original 2D pixel-art, side-view, turn-based unit RPG built in **Godot 4.3 (GDScript)**.
Every sprite, portrait, background, icon, UI texture, the pixel font, all sound effects and all
music in this project were created from scratch for Cinderbound (procedurally, by the scripts in
`tools/`). Nothing is taken from Brave Frontier or any other game.

---

## Play it

**Windows (no install, no Godot needed):** unzip `build/Cinderbound_Phase5_Windows.zip` (built locally, not committed to git) and double-click `Cinderbound.exe`
(the zip also holds `HOW-TO-PLAY.txt`, `CHANGELOG.txt` and `UI-GUIDE.md`).
It is a single self-contained file (engine + game data embedded) and can be moved anywhere.
Windows SmartScreen may warn because the exe is unsigned — choose *More info → Run anyway*.

**From source:** install [Godot 4.3 stable](https://godotengine.org/download/archive/4.3-stable/) (standard, not .NET),
open `project.godot`, press **F5**. First launch imports assets (~10 s).

Saves live in `%APPDATA%\Godot\app_userdata\Cinderbound\` (`cinderbound_save.json` + `.bak` backup, plus
`cinderbound_settings.json`). Delete them to reset.

The game uses a **portrait phone layout** (1080x1920). On PC it opens in a tall window you can resize or
maximise; the layout keeps its width and grows taller on longer phones.

### Controls (touch or mouse)
| Action | Touch / mouse | Keyboard |
|---|---|---|
| Choose target | tap an enemy | `Tab` / `←` `→` |
| Attack | **tap** a unit card | `A` |
| Burst (gauge full) | **swipe up** on the card | `B` |
| Guard | **swipe down** on the card | `G` |

Screens: title → starter select → story → Home (squad at camp, QUEST, UNITS / SQUAD / SUMMON / TOWER / ITEMS /
MISSIONS tiles with locks + notification markers; bottom nav: Home / Units / Quest / Summon / Menu) → Quest map with
world tabs → stage sheet → PREPARE → battle (AUTO, 1x/2x). Menu: Squad, Items, Missions, Codex, Towers, Profile,
Settings, title. Features unlock gradually in World 1 (see `build/package/HOW-TO-PLAY.txt`).

## Phase 5 (v0.5) — complete UI / UX pass
* Design system: text roles, spacing scale, semantic buttons, theme, tooltips, toasts, one confirmation dialog
  (`scripts/ui/ui_kit.gd`, `scripts/core/ui_manager.gd`). Rules: `build/package/UI-GUIDE.md`.
* Navigation history + transitions (`scripts/core/scene_router.gd`), bottom nav HOME / QUEST / UNITS / SUMMON / MENU,
  consistent BACK / "?" header, Esc / Enter on PC.
* New screens: Quest hub (world select), Menu, Settings (tabs), Help & Guide (element chart), Training.
* Units filter & sort (remembered), fixed card indicators, VIEW, skill fact chips, evolution WHERE TO FIND,
  summon duplicates, connected tower floors, CLAIM ALL, item detail panel, name validation.
* Battle: AUTO ON plate, boss PHASE / DANGER, stacked damage numbers, results SKIP, defeat tips.
* Tests: `tests/run_tests.sh` now includes the Phase 5 full-flow click-through (`--phase=5`).

## Phase 4 (v0.4) — collection, summoning, evolution, progression, repeatable PvE
* 12 heroes / 27 forms (4 per element, 3★–5★) with passives, leader skills, Burst levels 1–5 and evolution paths
  (`data/characters/`, art from `tools/make_heroes_p4.py`, `tools/portrait_gen.py`).
* Training with wisps + gold (preview), Evolution screen with OBTAINED FROM navigation, lock / favourite, Codex.
* Embergate summoning (`data/summon.json`, `scripts/progression/summon_system.gd`, ceremony in
  `scripts/ui/components/summon_ceremony.gd`), duplicates → Soul Shards.
* 5-hero squads, Auto battle + 2× speed, shields / poison / regen / debuffs, data-driven enemy AI
  (`scripts/combat/enemy_ai.gd`): healers, tanks, buffers, debuffers, chargers with WARNING telegraphs, elites,
  bosses with patterns, minions, HP events and phase 2.
* World 2 *Saltglass Reach* (10 stages + Saltglass Colossus), Ember / Tide / Verdant Towers (10 floors each),
  stars, possible drops, first-clear gems.
* Energy (offline regen), Rank-up rewards, daily / weekly missions + chest, 7-day login, inventory tabs, Profile.
* Save v2 with migration (`scripts/save/save_manager.gd`) — old saves keep all progress.
* Data reference: `build/package/CONTENT-GUIDE.md`. Content generator: `tools/make_content.py`.
* Tests: `tests/run_tests.sh` (2,061 rule checks, click-through flows incl. the full Phase 4 loop, balance sim).
  Visual probe for UI review: `tests/screen_probe.tscn`. Packaging: `tools/pack_zip.py` (zopfli, keeps the zip < 30 MiB).

## Phase 3 (v0.3) — graphics, combat presentation, UI/UX
* Original "worn iron and ember" UI kit (`tools/ui_v2.py`) and reusable components in `scripts/ui/components/`
  (FantasyButton, PanelFrame, ResourceBar, StatusIcon, UnitCard, EnemyPlate, StageNode, RewardItem, StatRow,
  ScreenHeader, NavBar, CurrencyDisplay, FantasyPopup, Toast, CoachMark, CutinDecor; screens extend `ScreenBase`).
* Battle HUD: enemy plates (boss frame), ember target sigil, element-framed hero cards with Burst
  EMPTY/CHARGING/READY states, gesture arrows, KO stamp, wave / ANCIENT FOE banners.
* Layered portrait battlefields with parallax + ambience (`tools/battle_bg.py`, `scripts/combat/battle_stage.gd`).
* Impact: particles, impact flash, hit-stop, tiered shake, typed damage numbers (CRITICAL / ADVANTAGE / RESIST /
  heal / burn / FINISH), per-hero Burst cut-ins and effects, boss entrance, guard / special animations.
* Portrait adventure map (`tools/route_map.py`, `route_pos` in stage data), sequenced victory screen, squad editor,
  coach-mark tutorial, ember-dissolve battle transitions, new UI sounds. Full list: `build/package/CHANGELOG.txt`.

---

## First milestone — status: ✅ complete
Launch → New Game → choose Kael / Mira / Thorne → confirm → story intro → Ashroot Wilds map →
Stage 1 → animated fight with normal attacks → Burst gauge fills → Burst with cut-in → Victory screen
(XP bar animates, LEVEL UP!, gold, items) → NEXT returns to the stage map → Stage 2 →
close the game → reopen → **Continue** → progress restored.
This exact path is automated in `tests/ui_flow.tscn` and passes for all three starters.

## What's in the prototype
* **3 starters** (Kael Emberclaw — Fire attacker, Mira Tidesong — Water healer, Thorne Mossguard — Nature tank),
  each with idle(4) / attack(6–7) / hit(2–3) / victory(4) / KO(2) / burst(10–11) animations and a 64×64 portrait.
* **3 enemy species** (Cinder Slime, Tidefin, Bramble Pup) with idle / attack / hit / death, scaled by level,
  plus the **Ancient Bramble Pup** mini-boss (larger native sprite, autumn palette, stone horns, party-wide attack).
* **Ashroot Wilds**: 10 stages with waves, tutorial hints (basic attack, targeting, elements, waves, burst,
  guard, burn, boss), five backdrops (forest, ruins, scorched, flooded, heart) and a world map.
* **Combat**: side-view turn-based; units dash in, strike on the animation frames, and return.
  Fire > Nature > Water > Fire (125% / 75%), crits (5%, 150%), ±5% variance, minimum damage,
  Burst gauge (attack +34, hit taken +6, guard +15), GUARD (−50% damage), Burn (5% max HP/turn),
  DEF Up, damage reduction, taunt, 20% HP recovery between waves.
  Presentation: hit flash, pooled damage numbers (CRIT / WEAK / RESIST), smooth-draining HP bars,
  particles, limited screen shake, attack zoom, burst dim + portrait cut-in + camera focus, battle log.
* **Progression**: XP curve to Lv 20, stat growth per unit, LEVEL UP sequence, player rank, gold,
  gold training ("LEVEL UP" button in unit details), loot (herbs + elemental shards), stage unlocks.
* **Screens**: Main menu (Continue/New Game/Settings/Exit), starter select (Select/View Skills/Back + confirm),
  intro, Home (rank, gold, party; Summon/Shop show COMING SOON), stage map, Units, Unit Details
  (Level Up / Party / Back), party editor (3 slots, built for 5), Inventory, Settings (volumes, shake, fullscreen).
* **Save system**: automatic, local JSON, atomic writes, rolling backup, field-by-field repair of missing or
  wrong data, graceful "save could not be read" message instead of a crash.

---

## Project layout
```
assets/      characters/ enemies/ environments/ ui/ effects/ icons/ audio/ fonts/ shaders/
data/        characters/*.json  enemies/*.json  skills/*.json  stages/*.json  items/  elements.json
             statuses.json  progression.json (all balance knobs)  tutorial_hints.json
scenes/      ui/ (one scene per screen)  combat/battle.tscn  characters/ enemies/ (battle unit scenes)
scripts/
  core/        game_manager (profile, rewards, settings)  audio_manager  scene_router (fades)
  data/        database (loads every JSON at startup)
  save/        save_manager (atomic save, backup, validation)
  progression/ progression (XP, stats, enemy scaling, loot)
  combat/      battle_model (rules only)  combatant  damage_calculator  enemy_ai
               skill_executor (animation timing)  battle_controller (flow)  battle_unit_view
               effects_layer (pooled FX + numbers)  battle_camera
  characters/  sprite_factory (SpriteFrames from sheets)
  ui/          ui_kit (theme + widgets)  battle_hud  party_card  battle_result  one script per screen
tests/       logic_tests, ui_flow (clicks through the real UI), balance_sim, run_tests.sh
tools/       Python generators for all art, the font and all audio (ignored by Godot)
```
Rules (`BattleModel`) never touch nodes, and visuals (`SkillExecutor`, views) never decide outcomes — the
same model powers the game, the tests and the balance simulator.

## Adding content (no combat code changes)
* **New unit**: drop `data/characters/<id>.json` (copy an existing one), reference skills in
  `data/skills/*.json`, and point `sprite.sheet` / `sprite.meta` at a sheet with rows
  `idle, attack, hit, victory, ko, burst` (see `tools/hero_*.py` for how the current ones are drawn).
* **New skill**: add an entry to `data/skills/` — `power`, `hits`, `hit_frames`, `motion` (melee/ranged/self),
  `effects` (heal / cleanse / status). New status kinds go in `data/statuses.json`.
* **New element**: add it to `data/elements.json` with `strong_against` — the chart is fully data-driven.
* **New stage/world**: add a JSON in `data/stages/` (waves reference enemy ids + levels, optional `hp_scale`).
* **Party size 5**: change `party_size` in `data/progression.json`; formations, battle cards (3 rows) and the
  squad editor already scale to 5.

## Tests
```
GODOT=/path/to/godot tests/run_tests.sh        # macOS/Linux/Git-Bash
```
On Windows without bash, run each line from `tests/run_tests.sh` with `Godot_v4.3-stable_win64_console.exe`.
Current result (v0.5): **2,074/2,074 rule checks pass; UI flows 1-5 pass; the milestone flow passes for all 3 starters; settings +
corrupted-save UI passes; the Phase 4 flow (auto battle, unlock popups, gift hero, summon ceremony + results, training,
evolution + OBTAINED FROM, tower floor, missions, login, inventory, codex, profile, World 2, squad from PREPARE,
energy popup) passes headless and with real mouse clicks**. Covered edge cases include Burst at exactly 100, Burst after loading
a save, an enemy dying mid multi-hit, a player dying during an enemy attack, rapid clicking,
save corruption (bad JSON, missing fields, wrong types) and 16:9 / 21:9 / 4:3 resolutions.
`tests/balance_sim.tscn` plays every starter through all ten stages with a simple policy (see table below).

Balance snapshot (win rate at the level you'd normally arrive with, simple AI):
Kael 100% on most stages, 71% on Threefold Trial; Mira ≥93% everywhere but slower fights;
Thorne 99–100% until the mini-boss (40% at Lv10 — train or grind a level). Tune in `data/progression.json`.

## Regenerating assets
```
python3 tools/make_assets.py   # sprites, portraits, effects, icons, UI, backgrounds (needs Pillow + numpy)
python3 tools/ui_v2.py         # v2 UI kit + 16x16 icon family
python3 tools/battle_bg.py     # layered portrait battlefields
python3 tools/route_map.py     # portrait adventure map
python3 tools/make_audio.py    # SFX (wav) + music (ogg, needs ffmpeg)
python3 tools/make_font.py     # "Cinder Pixel" font (needs fonttools)
```

## Known limitations / next steps
* One standard summon banner; no limited banners, PvP, guilds or co-op (out of scope for this phase).
* Balance: World 1 is gentle (passives + leader skills help a lot); World 2's last stages and tower floors 6–10 expect
  evolved heroes. Tune `recommended_level` / enemy levels in `tools/make_content.py`.
* Android/iOS export presets are not set up yet; the portrait touch layout is ready for them.
* Battle items (herbs) drop but are not usable yet.
* Placeholder audio is synthesized chiptune — replace by dropping files with the same names into
  `assets/audio/sfx|music`.
