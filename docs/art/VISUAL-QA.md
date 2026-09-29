# Visual QA — run before every package

Tick each on the CI screenshots (`ci-logs-linux` branch, `shots/`) and at 400 % zoom on changed sheets.

- [ ] No blurred sprites (nearest filtering, whole-number scales)
- [ ] No mismatched art styles on one screen (note Phase-4 leftovers in ART-ASSET-MANIFEST.md)
- [ ] No AI-looking anatomy, changing costume/weapon between frames, or random highlights
- [ ] No broken animation frames; hit frames land on the drawn impact
- [ ] Controlled palettes (hue-shifted ramps, no RGB gradients)
- [ ] No default engine widgets (buttons, bars, scrollbars, tabs all themed)
- [ ] No stretched borders / broken 9-slice corners
- [ ] No missing icons
- [ ] No smooth placeholder gradients (except deliberate large light overlays)
- [ ] Nobody floats: feet on the ground line, shadow under every actor
- [ ] Z-order correct: back FX < actors < front FX < UI; weapons/effects not clipped by frames
- [ ] No cropped weapons or effects at texture edges
- [ ] Portraits match sprites (hair, clothes, colours)
- [ ] Backgrounds sharp, lower contrast behind the combat zone
- [ ] Readable at 720×1280, 1080×1920, 1440×2560 and a large PC window
- [ ] Battle stress: 5 heroes + 3+ enemies + statuses + numbers + Burst + boss UI still readable
- [ ] Performance: sheets/atlases, pooled effects, particle counts bounded
