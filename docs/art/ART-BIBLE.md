# Cinderbound Pixel-Art Bible (Phase 6)

Every new asset follows this page. Reference games (e.g. Brave Frontier) set the *quality bar* only —
no character, pose, frame, icon, layout, font or name is copied.

## 1. Sizes & scale
| Asset | Native canvas | In-game scale | Notes |
|---|---|---|---|
| Hero battle sprite (3★–4★) | 96×96 frame | ×4 in battle | body ≈ 68 px tall, feet on row 88, pivot `[48, 88]` in the sheet JSON |
| Hero battle sprite (5★ / large) | 128×128 frame | ×3–×4 | same pivot rule (feet row = frame − 8) |
| Enemy | 64×64 – 96×96 | ×4–×5 | |
| Boss | 128×128 – 192×192 | ×3–×4 | never a scaled-up normal enemy |
| Portrait | 96×96 bust | ×2 cards, ×4 detail | whole-number scaling only; head ≈ 40 px |
| Unit-detail art | 160×240 | ×2 | (planned, Phase N) |
| Icons | 16×16 (UI) / 24×24–32×32 (items) | whole multiples | |
| UI textures | drawn 1×, stored 3× | 9-slice | margins in texture px |

Nearest filtering everywhere; integer scales; sprites move in whole native pixels.
`UnitSpriteDisplay` converts old 48px-sheet UI scales to the sheet's frame size (rounded to whole numbers).

## 2. Proportions
**Human, lightly stylised: ~5–5.5 heads tall** (chibi was rejected — characters must read as people).
On a 96px frame (ground row 88): crown 20, chin 33, shoulders 35, elbow ≈ waist 49, hip joint 56,
wrist ≈ crotch 57, knee ≈ 71, ankle 85. Head 11×13 px (face oval, taller than wide), neck 4 px,
shoulders ≈ 14 px wide in 3/4 view, waist 10, hips 12. Limbs: thigh 16 / shin 15, upper arm 13 /
forearm 11, tapering (thigh 7→5.5, calf 5.5→4, upper arm 5→4, forearm 4.5→3.5).
Portraits: adult head-and-shoulders — oval face, nose line, jaw to a firm chin, neck into broad shoulders.
Weapons are ~1.2–1.5× realistic size (Kael's blade ≈ 30 px) but never hide the body.
Every hero must be identifiable as a **black silhouette** (see §10 test).

## 3. Light, shading, outlines
* Light: **upper-left-front** (`px6.LIGHT = (-0.45, -0.7, 0.75)`) for sprites, portraits, enemies, cards.
* Shading describes **form**, not edges: each part is a height field (dome, vertical cylinder, horizontal
  cylinder or flat plate with a normal) lit by the light, quantised onto the material's ramp.
  No pillow shading (dark rim + bright centre).
* Parts in front cast a 1–2 px shadow down-right onto parts behind.
* Separation lines only on the down/right side of a part edge, one ramp step darker — never black.
* Outer outline: darkest colour of the touching material; lit (upper/left-facing) edges use the second
  darkest (selective outline). No pure black anywhere except pupils.
* No blur, no soft anti-aliasing; orphan pixels (a pixel matching none of its 4 neighbours) are removed.

## 4. Palettes
Ramps are 4–6 colours, dark → light, **hue-shifted** (shadows cooler/redder, highlights warmer/yellower).
A hero uses ≈ 20–40 meaningful colours in total (Kael 3★: 53 across the whole sheet incl. effects).

| Element | Highlight | Mid | Shadow | Deep shadow / line |
|---|---|---|---|---|
| Fire | `#ffe070` yellow-orange | `#c43a2e` red-orange | `#5a1420` crimson | `#2a0a14` red-brown/purple |
| Water | `#bff4ff` pale cyan | `#3a8ad8` blue | `#1c3e8a` deep blue | `#16143a` blue-violet |
| Nature | `#d8f07a` yellow-green | `#4a9a3a` green | `#245a2a` forest | `#12261e` blue-green/brown |

Shared materials: skin `#4a2426 #9c5a48 #d98e6c #f2b68c #ffd9b4`, black steel
`#0e0e16 #262634 #3e3e52 #62647a #9aa0b8 #e6ecf5`, brass/gold `#2a1608 #6a3e10 #a86a1a #e0a232 #ffe07a`,
leather `#1a0f12 #3a2220 #5a3628 #7a4e36 #9a6a48`.

## 5. Materials (`px6.MATERIALS` thresholds)
metal — 4 bands + specular, sharp small highlights · cloth — 3 broad soft bands · leather — medium
highlights, warm shadows · hair — grouped locks (each lock its own shape), large highlight masses ·
skin — soft, low contrast · stone/crystal/wood — see UI section; crystal = high contrast + internal highlight.

## 6. Characters
Detail priority at battle scale: silhouette > face/head > weapon > major armour/clothing > element > accessories.
Faces: eyes 2×3 px (sprite) / 4–5×5 px (portrait) with one highlight pixel; readable expression per hero.
Hair: 4–6 large lock shapes, a few internal strands — never dozens of thin lines.
No recolours: a new hero changes proportions, hair, weapon silhouette, stance, clothing and animation.
Evolutions change equipment/silhouette/ornament in a way that tells the hero's story (★3 clean, ★4
developed, ★5 signature) — no random spikes/wings/effect soup.

## 7. Animation
| Anim | Frames | FPS | Rules |
|---|---|---|---|
| idle | 6 (4–8) | 6 | breathing, cloth/hair sway, weapon glint; feet never move; no whole-body bounce |
| attack | 7 | 14 | anticipation → action → impact → recovery; hit frames must match `hit_frames` in the skill data |
| hit | 3 | 10 | recoil back + hurt face (the game adds the white flash) |
| guard | 3 | 6 | distinct defensive stance (never idle) |
| burst | 11 | 12 | upgraded identity move; hero stays readable; element shapes (flames/ribbons/roots) not particle soup |
| ko | 2–3 | 6 | kneel → fall; no gore |
| victory | 4 | 6 | short personality moment |
Frame-to-frame: identical head/torso/limb sizes, weapon length and costume; stable pivot.
Sprite-level trails: filled crescent smears, 3 tones, only on impact frames.

## 8. Effects
5–8 colours per element effect. Fire: flames, embers, slash arcs, heat rings · Water: ribbons, droplets,
waves, bubbles · Nature: leaves, roots, stone, spores. Clean alpha (on/off), pixel sprites for particles.
Screen flash: none on normal hits, small on crits, brief on Burst. Shake: 0–1 native px normal, 2–3 heavy.

## 9. UI
Materials: dark forged metal (primary), aged stone (secondary), brass (accent), crystal (element),
dark leather/stone (backdrops). 9-slice everything; corners/edges/inner shadow/highlight line; pixel drop
shadows (1–3 px, no blur); no high-frequency texture behind small text. Rarity frames: ★3 iron/brass,
★4 + ornament, ★5 carved + crystal. Motifs (repeat, don't multiply): broken ember sigil, three-point
elemental crest, black iron framing, glowing rune channels.

## 10. Checks (every asset)
Silhouette test (all heroes as black shapes side by side) · palette controlled · no orphan pixels ·
light consistent · materials readable · weapon readable · portrait matches sprite · proportions stable
across frames · sharp at native, 2×, 3×, 4× · nothing looks like texture noise. See `VISUAL-QA.md`.

## 11. Pipeline & files
* Source = code: `tools/px6.py` (renderer) + one `tools/art_<hero>.py` per hero (design, parts, poses,
  portrait). Parts are layered back → front: back cloth, back arm, back leg, front leg, torso, head
  (back hair, face, front hair, band), scarf, front arm, armour, weapon, effects.
* Output: `Content/assets/characters/<form_id>/<form_id>_sheet.png|.json` (+ `_portrait.png`); the JSON
  holds `frame_size`, `pivot` and per-animation `row/frames/fps/loop`. One row per animation.
* Names: `<hero>_<form>_...` lower-case, no `final2` / `test` names. Git is the version history — compare
  with `git show HEAD~n:<path>` before replacing art.
* Export: RGBA PNG, no premultiplication, no compression artefacts; `python3 tools/art_kael.py`.
