# CINDERBOUND — v0.6 (C++ / Axmol)

An original 2D pixel-art, portrait, turn-based unit-collection RPG. Since v0.6 it is written in
**C++20 on [Axmol](https://axmol.dev) 2.11.5** (the maintained cocos2d-x fork); v0.1–v0.5 were Godot
prototypes. Every sprite, portrait, background, icon, UI texture, the pixel font, all sound effects and all
music were made from scratch for Cinderbound by the Python scripts in `tools/`. Nothing is taken from
Brave Frontier or any other game.

## Play it
**Windows:** download `Cinderbound_Windows.zip` from the
[`cpp-latest` pre-release](https://github.com/Bhrcs/Mobile-gatcha-/releases/tag/cpp-latest) (built by GitHub
Actions on every push), unzip, run `Cinderbound.exe`. Windows SmartScreen may warn because the exe is unsigned —
*More info → Run anyway*. The old Godot build (v0.5) is still in `releases/`.

Saves live in the Axmol writable folder (`%LOCALAPPDATA%\Cinderbound\` on Windows): `cinderbound_save.json`
(+ `.bak` backup) and `cinderbound_settings.json`. Delete them to reset.

The layout is a portrait phone screen (1080x1920 design units). On PC it opens in a tall window; taller screens
show more height, wider ones get side bars.

| Action | Touch / mouse | Keyboard |
|---|---|---|
| Attack | tap a unit card | `A` |
| Burst (gauge full) | swipe up on the card | `B` |
| Guard | swipe down on the card | `G` |
| Choose target | tap an enemy | `Tab` / `←` `→` |
| Back / close popup · confirm | header BACK | `Esc` · `Enter` |

Content: 12 heroes / 27 forms, 2 worlds × 10 stages, 3 elemental towers, summoning with Soul Shards, training,
evolution, missions, daily login, codex, auto battle and 2× speed. How to play: `docs/player/HOW-TO-PLAY.txt`.

## Build from source
Needs CMake and a C++20 compiler; Axmol is fetched separately.
```
git clone --branch v2.11.5 https://github.com/axmolengine/axmol.git axmol   # inside this repo
pwsh ./axmol/setup.ps1                     # Linux: answer "y" to install the system packages
axmol build -p win32 -t Cinderbound -O 3   # or -p linux / -p android; exe in build/bin/Cinderbound/Release
```
CI (`.github/workflows/build.yml`) does exactly this on Windows and Linux, runs the rule tests and a screenshot
probe, publishes the Windows zip and pushes logs + screenshots to the `ci-logs-windows` / `ci-logs-linux` branches.

## Project layout
```
Source/
  logic/     rules, no engine: Database, SaveManager, GameManager, Progression, SummonSystem, Battle (model + AI)
  ui/        Gui (Godot-style Control/containers/tweens/particles on Axmol), UIKit (theme + shared widgets), Sprites
  app/       AudioManager, SceneRouter (history + transitions), UIManager (toasts, tooltips, dialogs), App start-up
  screens/   one .cpp per screen + components/ (widgets shared by several screens)
  battle/    battle screen: flow, skill timing, unit views, effects, camera, HUD, results
Content/     assets/ (art, audio, font) and data/ (JSON content + manifest.json)
Tests/       engine-free rule tests: bash Tests/run_logic_tests.sh
tools/       Python generators for all art, audio, the font and data (write into Content/)
proj.*/      platform entry points (win32, linux, android)
docs/        player/ guides and changelog, dev/ plans and the C++ porting guide
```
Rules never touch nodes and visuals never decide outcomes: the same `BattleModel` powers the game and the tests.

## Adding content
Edit / regenerate JSON in `Content/data/` (generator: `tools/make_content.py`, reference:
`docs/player/CONTENT-GUIDE.md`), then run `python3 tools/make_manifest.py` so the game sees new files.
Art and audio: `python3 tools/make_assets.py`, `tools/ui_v2.py`, `tools/battle_bg.py`, `tools/route_map.py`,
`tools/make_audio.py`, `tools/make_font.py` (Pillow, numpy, fonttools, ffmpeg).

## Known limitations
* Godot shaders (hit flash, ember dissolve) are approximated with tints, additive sprites and fades; colours
  brighter than white are clamped.
* Audio has no pitch variation (Axmol AudioEngine has no pitch control).
* Android/iOS project files exist (`proj.android`) but are not built by CI yet.
