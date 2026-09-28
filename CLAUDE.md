# Cinderbound — notes for Claude Code

Original 2D pixel-art, portrait-mobile, turn-based unit-collection RPG (inspired by the
*readability* of Brave Frontier, but with its own art, layouts, icons and identity — never copy
Brave Frontier assets, frames, fonts, icons or exact menu structure).
Built in **Godot 4.3 (GDScript)**, gl_compatibility renderer. All art, audio and the pixel font are
generated from scratch by the Python scripts in `tools/`.

## Current status

- Phases 1–4 are complete and shipped (last package: `Cinderbound_Phase4_Windows.zip`, v0.4.0).
- **Phase 5 = complete UI/UX improvement pass — IN PROGRESS.** Full requirements:
  `docs/PHASE5_PROMPT.md` (read it before continuing). Key constraints: do not restart or rebuild the
  project, do not replace working gameplay systems, no new worlds/elements/PvP/guilds/raids/
  equipment/banners/shops/events; implement changes directly and test every screen.

### Phase 5 — done so far (compiles: `check_scripts` = 0 failures)
- Removed unused old assets (old bg/button/panel/node art) to free package space.
- `tools/ui_p5.py`: new art — crimson (danger) button, tabs, ON/OFF switch, slider knob,
  scrollbars, tooltip plate, elite/perfect/cleared stage nodes, tower path tiles, 16×16 icons
  (back, help, info, filter, sort, plus, minus, close, pause, element_chart, new, squad, role_*).
- `tools/make_audio.py`: new sfx ui_back, ui_confirm, ui_error, coin, mission (ADPCM imports).
- `scripts/ui/ui_kit.gd`: typography roles (T_DISPLAY 120 … T_SMALL 20), spacing scale
  (SP_XS 4 … SP_XXL 32, MARGIN 16, TOUCH_MIN 88), semantic `btn(text, kind)` (primary/secondary/
  quiet/reward/danger), `format_compact()` (12.4K / 1.3M), `fit_label()` (shrink → ellipsis +
  tooltip), theme for scrollbars/slider/switches/tooltips/LineEdit/type variations, configurable
  extra safe-area margin (setting `safe_area` 0–3). Legacy `UIKit.confirm/message/toast` now delegate
  to UIManager.
- **New autoload `UIManager`** (`scripts/core/ui_manager.gd`): toasts (max 3, deduped, kinds info/
  success/error/warning/reward), `not_enough()` error text, tooltip system (hover / hold / tap, kept
  on screen), universal `confirm()` + `message()` dialogs (single instance), popup stack,
  Esc = close top popup / Back, Enter = popup default action, `show_loading()`, UI sounds, haptics.
- `FantasyPopup`: registers with UIManager, `cancel_action`, `default_action`, `tap_outside_closes`,
  fade + slight scale open (no bounce).
- New `LoadingOverlay` (only shown when a real threaded load takes > 0.15 s).
- **SceneRouter rewrite**: navigation history (`go(scene, params, nav)` with push / tab / replace /
  reset, `back()`, `remember()`, `push_entry()`, `leave_battle()`), push/back slide transitions,
  tab fades, ember dissolve for battle, threaded scene loading, `reduce_motion` setting.
- `ScreenBase`/`ScreenHeader`: consistent BACK (icon) via history, auto-fitting title, optional
  help "?" button (`opts.help`), `on_back()` used by Esc. Screens now use history Back.
- `FantasyButton`: press debounce (`press_cooldown` 0.25 s), `set_selected()`.
- `StatusBar`: compact animated counters with gain/spend flash, tooltips, `show_currency("shards")`.
- `NavBar`: order HOME / QUEST / UNITS / SUMMON / MENU, sliding gold marker, icon pop, locks.
- New components: `CinderTabs` (tab row, `Tab_<LABEL>` names, badges), `CinderSwitch` (ON/OFF with
  text), `ElementChart` (triangle + `ElementChart.popup()`).
- `SettingsPanel` rebuilt with AUDIO / GAMEPLAY / GRAPHICS / ACCOUNT categories (sliders, switches,
  speed segment, screen margins, reduce motion, vibration on mobile, tutorial reset, account info).
- Home: hierarchy QUEST > UNITS / SUMMON > TOWER / MISSIONS / SQUAD; tapping the focused hero
  makes them hop and say a short line.
- New settings keys: reduce_motion, haptics, safe_area, unit_sort, unit_sort_desc, unit_filter.

### ⚠ Known work-in-progress breakage (fix first)
SceneRouter / NavBar already reference scenes that **do not exist yet**:
`world_select`, `menu`, `settings`, `help`, `train` (`scenes/ui/*.tscn` + `scripts/ui/*.gd`).
Tapping QUEST or MENU in the bottom bar fails until they are created. `tests/ui_flow_runner.gd`
still expects the old structure (MENU popup `GameMenu`, stage_select as the QUEST tab, old
settings toggles) and must be updated.

### Phase 5 — next steps (in the prompt's order)
1. Create scenes: **Menu** screen (SQUAD, ITEMS, MISSIONS, CODEX, TOWERS, PROFILE, SETTINGS,
   HELP & GUIDE, TITLE; keep node names `Menu_<X>`), **Settings** screen (uses
   `SettingsPanel.fill` + `CinderTabs`), **Help & Guide** (topics + `ElementChart`), **World Select**
   (world cards: art, completion %, stars, boss defeated, lock reason). Scene template: copy
   `scenes/ui/missions.tscn` (root Control, full rect, script). Add ElementChart access to the
   battle pause menu and the squad screen.
2. Stage map: distinct node types (normal / elite / boss / cleared / perfect / locked / available
   by shape+icon), stage detail panel with reward tooltips; pre-battle squad screen with element
   composition vs enemy elements (warning only, never blocking).
3. Units grid (fixed indicator positions, filter/sort overlay, remembered sort), Unit Detail
   hierarchy + VIEW, concise skill text, **Training** screen (+1 / +5 / MAX with live preview),
   Evolution (current → next, materials with WHERE TO FIND, one confirm, EVOLUTION COMPLETE).
4. Summon (costs in buttons, results inspection, DUPLICATE → shards), vertical Tower with branch
   identity, Missions CLAIM ALL + login check marks, Inventory grid + detail, Profile validation.
5. Battle HUD pass, results skip + multi-level XP, defeat RETRY / EDIT SQUAD / STAGE SELECT + tips.
6. Tutorial overlay, empty states, resolution/overflow/extreme-resource/100-unit/200-item tests,
   rapid-input tests, update `tests/ui_flow_runner.gd` + add a Phase 5 full-flow test.
7. Docs + package: UI-GUIDE.md, CHANGELOG v0.5.0, HOW-TO-PLAY.txt, bump version to 0.5.0
   (`project.godot`, `export_presets.cfg`), export `Cinderbound.exe`, pack
   `build/Cinderbound_Phase5_Windows.zip` (≤ 30 MiB, exe + HOW-TO-PLAY.txt + CHANGELOG.txt +
   UI-GUIDE.md only; no .bat, no cache folders).

## Architecture
- Design space 1080×1920 (canvas_items stretch, keep_width); pixel font on a 10 px grid, font sizes
  are multiples of 10; icons 16×16 scaled by whole numbers; UI art drawn at 1× and saved at 3×.
- Autoloads: Database, SaveManager, AudioManager, SceneRouter, GameManager, UIManager.
- Data-driven content in `data/` (JSON), generated by `tools/make_content.py`.
- Screens: `scripts/ui/*.gd` extend `ScreenBase` and call `build_frame(bg, title, nav_tab, on_back,
  dim, with_status, opts)`. Reusable pieces live in `scripts/ui/components/`.

## Godot gotchas learned the hard way
- Warnings are treated as errors: type Variant values explicitly (`var t: float = ...`), prefix unused
  params with `_`.
- After adding a new `class_name` script run `godot --headless --import` before compiling, or the
  class is "not found".
- `set_anchors_preset()` on a node already in the tree keeps size 0 → use
  `set_anchors_and_offsets_preset()`.
- Emitting `gui_input` doesn't call a `_gui_input` override — connect the signal instead.
- Lambdas containing `match` inside `connect()` fail to parse — move the logic into a function.
- Coroutines awaiting tweens/timers of freed nodes leak at exit; `GameManager.quit_game()` handles
  a clean shutdown.

## Testing
- Compile check: `godot --headless res://tests/check_scripts.tscn`
- Full suite (bash): `tests/run_tests.sh` — compile, logic tests (~2061 checks), self-test, UI flow
  phases 1–4, balance sim. On Windows run it from Git Bash, or run the individual commands inside.
- Screenshot probe: `godot --resolution 540x960 res://tests/screen_probe.tscn -- --scene=home --shots=1`
  (screens saved to the Godot user data folder under `shots/`).
- Tools need Python 3 with Pillow. Packing uses `tools/pack_zip.py` (zopfli optional).
