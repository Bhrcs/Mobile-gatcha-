# Cinderbound — UI Guide (v0.5)

The rules every Cinderbound screen follows. Brave Frontier was a reference for
*readability* only; every frame, icon, font, colour, layout and animation here is
Cinderbound's own ("worn iron and ember").

Code lives in `scripts/ui/ui_kit.gd` (tokens, theme, helpers),
`scripts/core/ui_manager.gd` (toasts, tooltips, dialogs, loading, sounds, haptics),
`scripts/core/scene_router.gd` (navigation + transitions) and
`scripts/ui/components/` (reusable widgets). Art comes from `tools/ui_v2.py` and
`tools/ui_p5.py`.

---

## 1. Design space and responsive layout

* Design space **1080 × 1920** (1.5 × the 720 × 1280 reference), `canvas_items`
  stretch, aspect `keep_width`: the width is fixed, taller phones get more height.
* Every screen is built by `ScreenBase.build_frame()` in this order:
  backdrop → scene art → dim → **status bar** → **header** → content → **bottom nav**.
* Safe areas: `UIKit.safe_top()` / `safe_bottom()` use the phone's reported safe
  area plus the player's **Screen Margins** setting (None / Small / Medium / Large =
  +0 / 30 / 60 / 90 px). Nothing interactive sits inside those margins.
* Content scrolls (`ScrollContainer`, vertical only); no screen scrolls sideways.
* Tested at 720×1280, 1080×1920, 1440×2560, a small 360×640 window and a wide
  desktop window.

## 2. Typography (pixel font "Cinder Pixel", 10 px grid)

| Role | Constant | Size | Use |
|---|---|---|---|
| Display | `T_DISPLAY` | 120 | VICTORY, DEFEAT, QUEST plate |
| Title | `T_TITLE` | 80 | World names, EVOLUTION COMPLETE |
| Screen / popup title | `T_HEAD` (`T_SCREEN`) | 50 | Header title, popup title plates |
| Name / primary button | `T_NAME` (`T_UNIT`, `T_BUTTON`) | 40 | Hero names, big values, main buttons |
| Body | `T_BODY` (`T_PANEL`, `T_CURRENCY`, `T_BUTTON_S`) | 30 | Text, currency values, small buttons |
| Meta | `T_SMALL` (`T_META`) | 20 | Captions, tags, hints |

* Sizes are always multiples of 10 (`UIKit.snap_text`) so pixels stay square.
* Long text: `UIKit.fit_label(label, width)` shrinks in 10 px steps down to 20,
  then truncates with "…" and puts the full text in a tooltip.
* Theme type variations: `DisplayLabel`, `TitleLabel`, `PanelTitle`, `UnitName`,
  `BodyLabel`, `MetaLabel`.

## 3. Spacing

`SP_XS 4 · SP_S 8 · SP_M 12 · SP_L 16 · SP_XL 24 · SP_XXL 32`.
Screen side margin `MARGIN 16`. Minimum touch target `TOUCH_MIN 88` px (≈7 mm).
Lists use `SP_M` between rows, panels pad with `SP_L`–`SP_XL`.

## 4. Buttons (`UIKit.btn(text, kind, size, icon)` → `FantasyButton`)

| Kind | Art | Use |
|---|---|---|
| `primary` / `confirm` | ember | The one main action of a screen or dialog (DEPART, TRAIN, EVOLVE, OK) |
| `secondary` | steel | Other useful actions (EDIT SQUAD, WHERE TO FIND, FILTER) |
| `quiet` | stone | Back, Cancel, Close, low-importance actions |
| `reward` | gold | Claiming things (CLAIM, CLAIM ALL), selected choices |
| `danger` | crimson | Destructive / costly-to-undo (RETREAT) — always behind a confirmation |

* States: normal, hover (brighter, PC), pressed (face drops, squash), disabled
  (grey plate, no sound), selected (`set_selected(true)`: lit face, gold text).
* Every press plays a sound; presses closer than 0.25 s are ignored
  (`press_cooldown`, 0 for +1/-1 steppers) so double taps never fire twice.
* Costs live **inside** the button (SUMMON x10 · 1000 💎). Cursor = pointing hand.
* One primary button per view. Order in dialogs: **Cancel left, Confirm right**.

## 5. Panels and frames (`PanelFrame.make(variant)`)

`panel` (standard iron frame), `inset` (recessed: rows, info boxes), `plank`
(wooden headers and bars), `boss` (crimson: boss, danger, highlighted choice),
`slot` (item slots), `card_<element>[_lit]` (hero art backgrounds),
`rarity_3…6` (hero frames). Popups use `FantasyPopup`.

## 6. Header and navigation

* **Header** (`ScreenHeader`): `[< BACK]  TITLE  [? help]`. BACK is always top-left
  and follows the navigation history; the "?" opens Help & Guide on the right topic.
* **Bottom nav** (`NavBar`): HOME · QUEST · UNITS · SUMMON · MENU. The selected tab
  is raised, gold-labelled, its icon pops and a gold marker slides over from the
  previous tab. Sub-screens light their parent tab (Unit Detail → UNITS,
  Stage map / Towers → QUEST, Items / Missions / Settings → MENU). Tapping the lit
  tab from a sub-screen returns to that tab's root.
* **History** (`SceneRouter`): `go()` pushes; tabs reset history to [Home]; the same
  screen with new data replaces; battles are never in the history. Example:
  Units → Detail → Evolution → Where to find → Tower → **Back** → Evolution.
  Screens call `SceneRouter.remember({...})` so Back restores tabs and popups.
* **Transitions**: push = slide in from the right (0.18 s), back = from the left,
  tab = quick fade (~0.26 s total), battle = ember dissolve. "Reduce Motion" turns
  slides into fades. Input is blocked during a transition.
* PC keys: **Esc** = close tooltip → close top popup → Back (pause menu in battle);
  **Enter** = the popup's default action / continue results.

## 7. Resource widgets (`StatusBar`)

`[RANK + EXP] [ENERGY cur/max, +1 in m:ss] [GEMS] [GOLD]`.
* Values use compact numbers (`format_compact`: 9,999 · 12.4K · 1.3M · 2.1B); the
  exact value is in the tooltip.
* Changes count up/down over 0.45 s and flash green (gained) or red (spent).
* A screen may swap the Gems chip for its own currency (`show_currency("shards")`).
* Tapping RANK opens the Profile, ENERGY explains regeneration.

## 8. Unit card rules (`UnitCard`)

Fixed positions, identical on every card:

| Where | What |
|---|---|
| top-left | squad state: LEADER (crown) or SQUAD |
| top-right | one status tag: NEW > EVOLVE > MAX |
| art bottom-left | lock, favourite |
| art bottom-right | rarity stars |
| bottom row | element symbol, role icon, level (Lv.MAX at the cap) |
| frame | rarity frame (bronze 3★, silver 4★, gold 5★) |

## 9. Rarity and element visuals (never colour alone)

* Rarity = frame metal **and** star count.
* Elements = symbol **and** name: Fire = flame, Water = drop, Nature = leaf
  (`UIKit.orb`). Advantage: Fire > Nature > Water > Fire (+25% / −25%), shown in
  `ElementChart` (Help, battle pause menu, PREPARE, squad).
* Roles have their own icons: attacker (sword), defender (shield), healer (cross),
  support (banner), breaker (hammer).
* Stage nodes differ by shape: open ring, elite diamond, boss crest, cleared ring +
  check, perfect gold ring + check, padlock when locked.

## 10. Screen layout patterns

* **Hub** (Home): scene on top, one dominant action (QUEST), then secondary tiles in
  descending size (UNITS / SUMMON, then TOWER / MISSIONS / SQUAD).
* **List + docked sheet** (stage map, towers, inventory): scroll area above, a
  fixed detail sheet with the primary action at the bottom.
* **Tabs** (`CinderTabs`): Missions, Settings, Help, Inventory. Tab buttons are named
  `Tab_<LABEL>` and can carry a badge.
* **Empty states** always say why the list is empty and how to fill it (with a button
  when there is one, e.g. CLEAR FILTERS).
* **Locked content** stays visible (dimmed + padlock) and says exactly which stage
  opens it; no dead buttons.

## 11. Popups, dialogs and feedback

* `FantasyPopup`: dim backdrop, fade + slight scale (0.94 → 1, 0.16 s, no bounce).
  Registered with UIManager; only the top popup reacts to Esc/Enter.
* `UIManager.confirm()`: the one confirmation dialog (single instance, never
  stacked). Used only for spending premium currency, evolving, retreating and
  leaving with progress at stake — not for everyday actions.
* `UIManager.toast(text, kind)`: info / success / error / warning / reward,
  max 3, duplicates merge. Errors are explicit:
  *"Not enough Gold. Need 1,200 - you have 840."* (`not_enough()`).
* Tooltips (`attach_tooltip`): hover 0.35 s on PC, press-and-hold on buttons,
  tap on icons; always clamped inside the screen margins.
* Loading cover appears only if a real load takes longer than 0.15 s.
* Reward celebration levels: toast (small) → reward popup (claims) →
  full ceremony (summons, evolution, rank up). All ceremonies can be skipped.

## 12. Icons

16 × 16 pixel icons scaled by whole numbers (32 / 48 / 64 / 96). One icon per
meaning everywhere: back, help, info, filter, sort, plus/minus, close, pause,
element chart, new, squad, lock, check, warning, gem, gold, energy, soul shard,
roles, statuses. Icons always come with a label or a tooltip.

## 13. Battle HUD

Top: stage, wave pips, loot, **1x/2x · AUTO · MENU**. Enemy plates below (boss plate
larger, with PHASE 1/2 and a marker on the HP bar; DANGER - GUARD! pulses while a
foe charges). Hero cards at the bottom. While AUTO is on, a pulsing AUTO BATTLE plate
sits above the cards (tap it to take control). Damage numbers stack instead of
overlapping; they, screen shake and effects can be turned off in Settings.

## 14. Sound and haptics

One sound per meaning (`UIManager.SOUNDS`): press, back, confirm, error, coin,
claim, mission, level up, evolve, summon, open/close, select, toggle.
Phones get short vibrations for confirms, bursts, reveals and evolutions
(Settings → Gameplay → Vibration); desktop builds never vibrate.

## 15. Saved UI preferences

Unit sort + direction + filters, default battle speed, start on AUTO, volumes,
screen shake, effects, damage numbers, reduce motion, screen margins, vibration.
