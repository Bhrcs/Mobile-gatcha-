# CINDERBOUND — PHASE 5 MASTER DEVELOPMENT PROMPT
## COMPLETE UI / UX IMPROVEMENT PHASE

You are continuing development of my existing game **Cinderbound**.

This is **Phase 5**.

The focus of this phase is:

**UI, UX, menus, navigation, information presentation, visual consistency, interaction feedback, responsive mobile layout, and final interface polish.**

Do NOT create a new project.

Do NOT restart the game.

Do NOT replace working gameplay systems.

Do NOT spend this phase adding large new gameplay systems.

Do NOT add dozens of characters, worlds, bosses, or features.

The gameplay foundation from previous phases already exists.

The purpose of Phase 5 is to make Cinderbound look and feel like a finished commercial pixel-art hero-collection RPG.

The visual direction may take inspiration from the readability and information density of classic hero-collection RPGs such as Brave Frontier, but:

- do not copy Brave Frontier UI assets
- do not copy exact layouts
- do not copy icons
- do not copy frames
- do not copy fonts
- do not copy artwork
- do not copy animations
- do not copy menu structure exactly

Cinderbound must maintain its own visual identity.

---

# PHASE 5 PRIMARY OBJECTIVE

Take every existing screen in Cinderbound and perform a complete UI/UX quality pass.

The player should immediately notice improvements in:

- spacing
- readability
- menu hierarchy
- character presentation
- button quality
- panel quality
- navigation
- transitions
- feedback
- icons
- resource displays
- stage presentation
- squad presentation
- inventory
- summoning
- evolution
- Tower UI
- missions
- rewards
- combat HUD
- responsiveness
- consistency

The game should no longer feel like separate prototype screens connected together.

Every interface should look like part of the same game.

---

# 1. DO NOT CHANGE CORE GAMEPLAY FIRST

Before implementing anything:

inspect the entire existing project.

Create a complete list of all current screens.

Likely screens include:

- Title
- Intro
- Home
- Quest
- World Select
- Stage Select
- Stage Details
- Squad Select
- Battle
- Battle Results
- Units
- Unit Collection
- Unit Details
- Training
- Evolution
- Squad Management
- Summoning
- Summon Results
- Inventory
- Tower
- Tower Floor Select
- Daily Missions
- Weekly Missions
- Login Rewards
- Player Profile
- Settings
- Tutorials
- Popups
- Confirmation dialogs

Identify every screen actually present.

Do not create duplicates of screens that already exist.

---

# 2. BUILD A GLOBAL UI DESIGN SYSTEM

Create a unified Cinderbound UI design system.

Do not manually style every screen separately.

Create reusable components.

The game should have a recognizable interface language.

Use a combination of:

- dark metal
- blackened iron
- worn stone
- leather
- muted wood
- ember accents
- elemental crystals
- carved fantasy framing

Avoid overly ornate borders around everything.

The game should remain readable.

---

# 3. UI COLOR STRUCTURE

Create consistent categories.

Background:

dark enough to make content readable.

Panels:

slightly lighter than background.

Primary interactive button:

clearly visible.

Secondary button:

less visual weight.

Disabled button:

visibly inactive.

Danger/destructive button:

clearly distinguished.

Confirm button:

consistent across the entire game.

Use elemental colors primarily for:

- Fire
- Water
- Nature
- future elements

Do not color random buttons based only on appearance.

Color should communicate meaning.

---

# 4. CREATE REUSABLE UI COMPONENTS

Create reusable UI scenes/components such as:

CinderButton

CinderPanel

CinderHeader

CinderPopup

CinderTab

CinderNavButton

CinderResourceDisplay

CinderUnitCard

CinderStageNode

CinderRewardCard

CinderItemCard

CinderMissionCard

CinderProgressBar

CinderTooltip

CinderConfirmationDialog

CinderNotificationDot

CinderToast

CinderCurrencyDisplay

CinderStatRow

CinderRarityFrame

CinderElementIcon

CinderStatusIcon

Do not duplicate interface logic across screens.

---

# 5. RESPONSIVE DESIGN FOUNDATION

Cinderbound should support portrait mobile first.

Use a reference design resolution such as:

720 × 1280

The Windows build should scale correctly.

Support:

- narrow portrait
- standard portrait
- tall modern phones
- Windows resized portrait
- maximized Windows window

Use anchors and containers properly.

Do not hard-code every UI position.

Avoid controls falling outside the screen.

Avoid text overlapping buttons.

Avoid stretching pixel art incorrectly.

---

# 6. MOBILE SAFE AREAS

Prepare layouts for phones with:

- camera cutouts
- rounded corners
- status bars
- gesture areas

Important buttons should not sit directly against screen edges.

Create configurable safe-area padding.

---

# 7. GLOBAL SCREEN STRUCTURE

Create a consistent structure for major screens.

Typical structure:

TOP BAR

SCREEN CONTENT

BOTTOM NAVIGATION

The top bar should normally contain:

- back button where appropriate
- screen title
- player Rank
- Energy
- Gold
- Gems

Do not show every resource on every screen if it is irrelevant.

---

# 8. TOP RESOURCE BAR

Create a reusable resource bar.

Display resources with:

icon

value

optional +

Examples:

Energy

Gold

Gems

The resource bar should remain compact.

Do not dedicate 25% of the screen to currencies.

When resource values change:

animate the number.

Example:

2,410

→

2,760

Do not instantly snap unless loading a screen.

---

# 9. LARGE NUMBER FORMATTING

Handle large currency values.

Examples:

999

1,250

12.4K

1.3M

Use consistent formatting.

Do not display:

123456789

inside a small resource panel.

Tooltips or detail screens can display the full value.

---

# 10. BOTTOM NAVIGATION

Create a polished persistent bottom navigation.

Recommended main tabs:

HOME

QUEST

UNITS

SUMMON

MENU

If the current architecture needs another structure, adapt accordingly.

The selected tab should:

- raise slightly
- glow subtly
- show a clearer icon
- animate into selected state

Unselected tabs should remain readable.

Do not hide important navigation behind several menus.

---

# 11. NAVIGATION STATE

The game must remember where the player came from.

Example:

Units

→ Unit Detail

→ Evolution

→ Material Source

→ Tower

Press Back.

The player should not randomly return Home.

Implement sensible navigation history.

Avoid deep navigation traps.

---

# 12. BACK BUTTON CONSISTENCY

Every secondary screen should have a consistent Back button.

Same:

position

size

icon

interaction behavior

Do not use:

X

Back

arrow

Cancel

for the same function across random screens.

---

# 13. BUTTON REDESIGN

Every button must support:

normal

hover

pressed

disabled

selected

where appropriate.

Buttons should feel physical.

Use subtle:

- depression
- highlight change
- small scale movement
- sound

Do not over-animate buttons.

Button labels should use verbs when possible.

Examples:

START

TRAIN

EVOLVE

SUMMON

CLAIM

EDIT SQUAD

CONTINUE

---

# 14. TOUCH TARGETS

Ensure mobile touch targets are large enough.

Avoid tiny clickable icons.

Critical buttons should be easy to press with a thumb.

Small information icons can remain smaller but should have larger invisible touch areas.

---

# 15. TYPOGRAPHY SYSTEM

Create a consistent text hierarchy.

Suggested categories:

Display Title

Screen Title

Panel Title

Unit Name

Button Label

Body Text

Secondary Text

Metadata

Damage Number

Currency Value

Do not randomly assign sizes.

---

# 16. TEXT READABILITY

Avoid huge paragraphs in tiny boxes.

Break information into:

- icons
- short lines
- stat rows
- bullet-style entries
- tooltips

Skill descriptions should be concise.

Example:

Bad:

"Deals a large amount of fire damage to the currently selected enemy and has a chance..."

Better:

Fire DMG to one enemy.

30% chance to Burn for 2 turns.

---

# 17. TEXT AUTO-FIT

Long unit names and stage names should not overlap UI.

Implement:

- font scaling within limits
- truncation
- multi-line handling
- tooltip for full text where appropriate

Never allow text to cover icons or buttons.

---

# 18. HOME SCREEN REWORK

Make Home feel like a headquarters.

The player's active Leader should be visible.

Use:

- animated pixel-art Leader
- camp/background scene
- subtle ambient effects
- resource bar
- quick access buttons

Primary actions:

Quest

Units

Summon

Tower

Missions

Do not place all actions inside identical rectangles.

Use a clear visual hierarchy.

---

# 19. HOME LEADER INTERACTION

Allow the active Leader to react when tapped.

Examples:

idle variation

small animation

short visual reaction

Do not require voice acting.

Keep the interaction fast.

---

# 20. HOME NOTIFICATIONS

Display notification indicators only when useful.

Examples:

Mission reward available

Free summon available if implemented

Hero can Evolve

Login reward available

New unit obtained

Do not place notification dots everywhere.

---

# 21. WORLD SELECT UI

World Select should feel like an adventure.

Each World card should show:

- World name
- environment artwork
- completion %
- total stars
- boss defeated state
- locked/unlocked state

Swipe or scroll between Worlds.

Do not display Worlds as plain text buttons.

---

# 22. STAGE MAP

Improve Stage Select.

Use connected nodes.

Node types:

Normal

Elite

Boss

Cleared

Locked

Available

Each must be visually distinct.

Avoid relying only on color.

Use:

shape

icon

border

animation

---

# 23. STAGE NODE FEEDBACK

Available node:

subtle pulse.

Cleared node:

clear completion icon.

Three-star completion:

visible stars.

Boss:

unique frame.

Locked:

darkened but readable.

Do not make locked nodes invisible.

---

# 24. STAGE DETAILS PANEL

When selecting a stage:

show a dedicated information panel.

Display:

Stage name

Energy cost

Recommended Power

Enemy elements

Wave count

Possible rewards

First-clear reward

Star objectives

START button

Do not immediately launch the stage from a single tap.

---

# 25. REWARD PREVIEW

Reward icons should be visible.

Examples:

Gold

XP

evolution material

training item

Gems

Tap/hover item:

show item name and description.

---

# 26. SQUAD SELECTION BEFORE BATTLE

Create a polished pre-battle squad screen.

Show:

5 party slots

Leader

Squad Power

Element composition

Stage enemy elements

Each party member should have:

portrait

level

rarity

element

HP if relevant

Leader marker

---

# 27. ELEMENT WARNING

If a player's squad is heavily disadvantaged:

show informational feedback.

Example:

Enemy Element:

WATER

Fire units may take increased damage.

Do not prevent the player from starting.

---

# 28. SQUAD EDITOR

Improve drag/drop or tap-to-select squad editing.

Player should easily:

add unit

remove unit

swap units

change Leader

Avoid requiring five different confirmation popups.

---

# 29. UNIT COLLECTION SCREEN

Make this screen visually dense but readable.

Use a grid.

Cards should display:

portrait

rarity

element

level

favorite

lock

new indicator

Cards should be large enough for the portrait to remain recognizable.

---

# 30. UNIT CARD STATES

Support:

Normal

Selected

New

Favorite

Locked

Can Evolve

Max Level

In Squad

Do not display all indicators in the same corner.

Reserve predictable positions.

---

# 31. UNIT FILTER PANEL

Create a clean filter/sort overlay.

Filter:

Fire

Water

Nature

Rarity

Role

Evolution available

Favorite

Sort:

Level

Rarity

HP

ATK

DEF

REC

Recently Obtained

Name

Include:

RESET FILTERS

---

# 32. UNIT DETAIL SCREEN

This is one of the most important interfaces.

Top area:

large portrait or sprite

name

element

rarity

level

XP

Middle:

HP

ATK

DEF

REC

Burst

Passive

Leader Skill

Bottom:

TRAIN

EVOLVE

SQUAD

LOCK/FAVORITE

The visual hierarchy should emphasize the hero.

---

# 33. CHARACTER ART DISPLAY

Allow players to view unit artwork clearly.

Add:

VIEW

or portrait tap behavior.

Open a clean character viewer.

Show:

pixel-art portrait

evolution state

name

element

rarity

Do not clutter this view with every stat.

---

# 34. STAT PRESENTATION

Avoid plain text like:

HP 1520

ATK 670

DEF 580

REC 330

Use organized rows.

Example:

HP     1,520

ATK      670

DEF      580

REC      330

Highlight stat increases when comparing evolution or training.

---

# 35. TRAINING SCREEN

Improve Training.

Left/top:

hero being trained.

Show:

Current Level

XP bar

Stats

Material selection below.

Selecting materials should immediately preview:

Level 23

→

Level 27

HP +142

ATK +57

Gold Cost

TRAIN button

Do not require players to guess the result.

---

# 36. TRAINING MATERIAL UI

Use clear material cards.

Display:

icon

name

element

XP amount

quantity

selected amount

Provide:

+1

+5

MAX

when appropriate.

Do not make players tap 50 times.

---

# 37. EVOLUTION SCREEN

Evolution needs stronger presentation.

Display:

CURRENT FORM

→

NEXT FORM

Use large artwork.

Show:

rarity increase

max level increase

stat increase

new passive

new Burst

visual changes

required materials

Gold cost

---

# 38. MATERIAL REQUIREMENTS

Display material requirements as:

Owned / Required

Example:

Ember Core

3 / 5

Enough:

normal appearance.

Missing:

clear warning.

Tap missing item:

WHERE TO FIND

---

# 39. EVOLUTION CONFIRMATION

Before Evolution:

show one clean confirmation screen.

Do not require multiple warnings unless a permanent resource will be consumed.

Then play a short Evolution animation.

---

# 40. EVOLUTION RESULT

After evolution:

show the new hero artwork.

Display:

EVOLUTION COMPLETE

Previous rarity

→

New rarity

New stats

Unlocked ability if applicable

Continue

Make this feel rewarding without turning it into a long cutscene.

---

# 41. SUMMON SCREEN

Summon should be one of the strongest screens visually.

Display:

summon banner

featured artwork if relevant

Gems

single summon

multi summon

rates/details button

summon currency cost

Do not hide costs.

---

# 42. SUMMON BUTTONS

Display clear costs directly inside buttons.

Example:

SUMMON ×1

100 Gems

SUMMON ×10

1,000 Gems

Player should never need to guess what a summon costs.

---

# 43. SUMMON RESULT SCREEN

After summoning:

display hero result prominently.

Show:

NEW if new

Name

Rarity

Element

Role

For multi summon:

display results in a clean grid after reveal sequence.

Allow player to inspect each unit.

---

# 44. DUPLICATE RESULT

When duplicate appears:

clearly show conversion.

Example:

DUPLICATE

Kael Emberclaw

Converted:

20 Soul Shards

Do not silently modify currency.

---

# 45. TOWER SCREEN

Redesign Tower as a major progression screen.

Show the Tower vertically.

Three branches can use:

Ember

Tide

Verdant

Display floors as connected stages.

Show:

completed floors

current floor

locked floors

boss floor

material rewards

---

# 46. TOWER BRANCH IDENTITIES

Each Tower branch should have visual identity.

Ember:

heat

embers

dark metal

Tide:

water

blue crystal

ripples

Verdant:

roots

stone

growth

Do not simply recolor the same screen.

Reuse layout architecture, not identical artwork.

---

# 47. MISSIONS UI

Create tabs:

DAILY

WEEKLY

ACHIEVEMENTS if implemented later

Mission card shows:

objective

progress

reward

claim button

Example:

Complete 3 Stages

2 / 3

Reward:
5 Gems

---

# 48. MISSION PROGRESS BARS

Use progress bars when objectives have counts.

Do not display only:

2/20

when a progress bar would be easier to read.

Completed mission:

clearly indicate completion.

CLAIM button should stand out.

---

# 49. CLAIM ALL

If multiple completed missions exist:

add:

CLAIM ALL

Do not force players to claim 15 rewards one at a time.

---

# 50. LOGIN REWARD UI

Create a 7-day reward panel.

Show:

Day 1

Day 2

Day 3

...

Current day should be clearly highlighted.

Claimed days:

check mark.

Upcoming:

visible but inactive.

Do not use deceptive countdowns.

---

# 51. INVENTORY SCREEN

Improve Inventory into a grid/list hybrid.

Tabs:

Materials

Training

Items

Other

Each card:

icon

quantity

rarity if relevant

Tap item:

open detail panel.

---

# 52. INVENTORY ITEM DETAIL

Display:

item name

icon

description

quantity

rarity

used for

obtained from

If item is usable:

USE

If not:

do not show useless buttons.

---

# 53. BATTLE HUD SECOND PASS

Even if Phase 3 already improved battle UI, perform another pass after all Phase 4 systems exist.

Ensure battle UI supports:

5 heroes

status effects

Burst

Guard

Auto

Speed

Boss HUD

wave indicator

target selection

element feedback

damage numbers

---

# 54. PLAYER BATTLE CARDS

Each hero battle card should display:

portrait

HP

Burst

element

status effects

KO state

selection state

Avoid huge cards.

The battlefield must remain visible.

---

# 55. BATTLE CONTROL BAR

Add compact controls for:

AUTO

1× / 2×

PAUSE or MENU

Do not place these next to unit attack areas where they can be accidentally pressed.

---

# 56. AUTO STATE

When Auto is active:

AUTO ON

must be obvious.

Use a persistent state indicator.

Do not require players to guess whether Auto is running.

---

# 57. BATTLE SPEED STATE

Show:

1×

2×

Use one button that cycles states.

Avoid opening a settings menu during combat.

---

# 58. BOSS HUD

Boss UI should include:

Boss name

element

large HP bar

status icons

phase indicator if applicable

danger attack warning

Boss UI should feel different from normal enemies.

---

# 59. DANGEROUS ATTACK WARNING

When a boss prepares a major attack:

display clear warning.

Example:

CHARGING

or an original Cinderbound term.

Use:

icon

short text

animation

Do not rely on red flashing alone.

---

# 60. STATUS EFFECT TOOLTIP

On desktop:

hover status icon.

On mobile:

tap/hold.

Display:

name

effect

remaining turns

Example:

BURN

Takes Fire damage at end of turn.

2 turns remaining.

---

# 61. DAMAGE NUMBER CLEANUP

Ensure damage numbers remain readable with 5 heroes.

Avoid overlap.

Use separate visual style for:

Damage

Critical

Weakness

Resist

Healing

Shield

Damage Over Time

---

# 62. BATTLE RESULT SCREEN

Victory sequence should remain compact.

Display:

VICTORY

then:

Player XP

Hero XP

Gold

Items

Stars

First-clear rewards

Level ups

Allow animation skipping after initial presentation.

---

# 63. XP ANIMATION

XP bars should animate.

If hero levels multiple times:

show the total increase without forcing a popup for every level.

Example:

Lv. 12

→

Lv. 15

LEVEL UP

---

# 64. REWARD CARDS

Rewards should use reusable cards.

Display:

icon

name

quantity

new indicator if relevant

rare reward effect if appropriate

---

# 65. DEFEAT SCREEN

Keep Defeat simple.

Show:

DEFEAT

Then:

RETRY

EDIT SQUAD

STAGE SELECT

If helpful:

suggest:

Level Up Units

Check Element Matchup

Do not shame the player.

---

# 66. SETTINGS UI

Organize Settings into categories.

AUDIO

GAMEPLAY

GRAPHICS

ACCOUNT

Possible controls:

Music Volume

SFX Volume

Battle Speed

Screen Shake

Damage Numbers

Battle Effects

Tutorial Reset

Use:

sliders

toggles

drop-downs where appropriate.

---

# 67. SLIDER DESIGN

Sliders need:

clear handle

current value

consistent width

Do not rely solely on mouse wheel interaction.

Mobile drag must work.

---

# 68. TOGGLE DESIGN

Use visible:

ON

OFF

or a clear switch.

Do not use tiny checkboxes for major settings.

---

# 69. CONFIRMATION DIALOGS

Create one universal confirmation-dialog system.

Use it for actions such as:

spending Gems

Evolution

leaving a battle

resetting tutorials

Do not create different confirmation designs for every system.

---

# 70. DO NOT OVERUSE CONFIRMATIONS

Do not ask:

Are you sure?

for:

opening menus

changing tabs

selecting stages

changing filters

ordinary squad edits

Only ask when an action has meaningful consequences.

---

# 71. TOOLTIP SYSTEM

Create one reusable tooltip system.

Support:

items

skills

status effects

currencies

elements

materials

stats

Tooltips should intelligently remain inside screen boundaries.

---

# 72. TOAST NOTIFICATIONS

Use small temporary notifications for simple feedback.

Examples:

Squad Saved

Mission Claimed

Not Enough Gold

Hero Favorited

Settings Saved

Do not use full-screen popups for minor information.

---

# 73. ERROR FEEDBACK

Errors should explain the actual problem.

Bad:

ERROR

Better:

Not enough Gold.

Need 1,200 Gold.

You have 840.

Where possible, give the player the next useful action.

---

# 74. LOADING SCREEN

Create a consistent loading screen.

Use:

Cinderbound logo

small animation

loading indicator

Optional rotating gameplay tips.

Do not fake loading delays.

If loading completes, continue immediately.

---

# 75. SCREEN TRANSITIONS

Standardize navigation transitions.

Recommended:

main screen:

short fade

sub-menu:

short horizontal movement

popup:

small scale/fade

Do not create extreme animations.

Target roughly:

0.15–0.30 seconds.

---

# 76. POPUP ANIMATION

Popups should:

fade in

scale slightly

Do not bounce excessively.

Closing:

fast fade.

---

# 77. MICRO-INTERACTIONS

Add small feedback where useful.

Examples:

button presses

currency increases

XP increases

unit selected

stage selected

mission completed

Burst ready

Evolution available

Do not animate every label.

---

# 78. ICON CONSISTENCY PASS

Audit every icon in the game.

Standardize:

resolution

pixel density

outline

shading

lighting direction

padding

frame

Review:

Gold

Gems

Energy

XP

Rank

elements

rarity

roles

status effects

mission icons

settings icons

navigation

inventory

Tower

Summon

---

# 79. RARITY PRESENTATION

Rarity should have a consistent style.

★3

★4

★5

Use:

stars

frame complexity

minor visual accents

Do not rely only on color.

Higher rarity cards may have slightly more ornamentation.

---

# 80. ELEMENT PRESENTATION

Current elements:

Fire

Water

Nature

Every element needs:

icon

UI accent

effect language

Do not rely on color alone.

For example:

Fire:
flame icon

Water:
drop/wave

Nature:
leaf/root

---

# 81. ROLE ICONS

Create simple role icons.

Attacker

Defender

Healer

Support

Hybrid if necessary

Keep them readable at small size.

---

# 82. EMPTY STATES

Every empty menu needs a proper state.

Examples:

No Missions Completed

No Materials

No Heroes Match This Filter

No Rewards Available

Do not leave blank panels.

---

# 83. LOADING STATES

Menus that need loading should show loading feedback.

Do not display empty content for several frames.

---

# 84. LOCKED CONTENT UI

Locked features should explain:

what they are

how they unlock

Example:

TOWER

Unlock by clearing Stage 1-7.

Do not let tapping a locked feature do nothing.

---

# 85. NEW FEATURE INTRODUCTION

When a new system unlocks:

show a small introduction.

Example:

TOWER UNLOCKED

Earn Evolution materials by clearing Tower floors.

ENTER

Keep explanations short.

---

# 86. TUTORIAL HIGHLIGHT SYSTEM

Use a reusable guided tutorial overlay.

It should:

dim unrelated interface

highlight required control

show short instruction

wait for action

Examples:

Tap QUEST.

Select Stage 1-1.

Swipe up to use Burst.

Do not use long tutorial paragraphs.

---

# 87. PLAYER PROFILE UI

Improve profile.

Display:

Player Name

Rank

Leader

Heroes Collected

World Progress

Tower Progress

Total Stars

Play Time

Keep it focused.

---

# 88. EDIT PLAYER NAME

If supported:

allow player to change displayed name.

Use one simple text dialog.

Prevent:

empty names

extremely long names

unsupported characters if necessary.

---

# 89. MENU SCREEN

Create a clean secondary Menu screen.

Possible options:

Profile

Inventory

Missions

Settings

Help

Return to Title

Do not overload the bottom navigation.

---

# 90. HELP / GAME GUIDE

Create a simple in-game help section.

Sections:

Combat

Elements

Burst

Guard

Squads

Training

Evolution

Summoning

Tower

Only explain systems that exist.

---

# 91. ELEMENT CHART UI

Create a small visual triangle:

Fire → Nature

Nature → Water

Water → Fire

Allow access from:

Help

Battle information

Squad screen

Do not force players to memorize it.

---

# 92. AUDIO FEEDBACK PASS

Assign consistent UI sounds.

Examples:

Button Press

Back

Confirm

Cancel

Currency Gain

Mission Complete

Reward Claim

Evolution

Summon

Level Up

Error

Do not use loud battle sounds for menu interaction.

---

# 93. HAPTIC PREPARATION

For future mobile versions:

prepare calls/hooks for light vibration on:

major button confirm

Burst ready

Summon reveal

Evolution complete

Do not require haptics on Windows.

Keep it optional.

---

# 94. PERFORMANCE OF UI

Menus must remain responsive.

Do not recreate every UI element every frame.

Use:

cached resources

reusable nodes

virtualized lists if necessary

efficient scrolling

Avoid loading every full-resolution portrait at startup.

---

# 95. SCROLL PERFORMANCE

Test Units and Inventory with larger datasets.

Simulate:

100 units

200 inventory entries

Menu should still scroll smoothly.

Even if current content is smaller, architecture should scale.

---

# 96. SAVE UI PREFERENCES

Remember useful UI state where appropriate.

Examples:

last selected Unit sort

battle speed

Auto preference

audio volume

screen shake

Do not remember temporary things such as open popups.

---

# 97. ACCESSIBILITY PASS

Do not communicate critical states through color alone.

Use:

icons

text

shapes

patterns

Support disabling:

screen shake

large effects

damage numbers

Ensure readable contrast.

---

# 98. PIXEL-ART QUALITY

All pixel-art UI assets must:

use clean pixel placement

avoid blurred scaling

avoid mixed resolution

avoid inconsistent outline widths

avoid smooth vector-looking assets mixed randomly with pixel assets

If vector UI is used internally for scaling, ensure it visually matches the pixel-art direction.

---

# 99. UI VISUAL HIERARCHY TEST

For every screen ask:

What should the player notice first?

What should they press next?

What information is secondary?

If everything has equal visual weight, redesign the screen.

---

# 100. CONSISTENCY AUDIT

Before completing the phase:

compare every screen.

Check:

same button style

same back button

same panel border

same resource bar

same font sizes

same icon style

same spacing system

same rarity treatment

same element treatment

same popup design

same transitions

---

# 101. SPACING SYSTEM

Create a standard spacing scale.

Example:

4 px

8 px

12 px

16 px

24 px

32 px

Use consistent spacing instead of random values like:

13 px

19 px

27 px

unless a visual asset requires it.

---

# 102. SCREEN MARGINS

Define standard safe margins.

Do not place random elements against screen edges.

Use consistent horizontal padding.

---

# 103. ALIGNMENT

Audit every screen for:

misaligned labels

uneven buttons

inconsistent icon centers

uneven margins

different panel widths

small visual jumps

These small problems make UI look unfinished.

---

# 104. NO DEAD UI

Every visible interactive element must work.

Do not create:

fake buttons

placeholder tabs

nonfunctional arrows

dead icons

If a feature is unfinished:

hide it

or clearly mark:

COMING LATER

Do not make it look active.

---

# 105. CURSOR SUPPORT

For Windows:

use appropriate cursor states where possible.

Buttons:

pointer/hand.

Dragging:

drag state.

Do not require this on mobile.

---

# 106. KEYBOARD / ESCAPE SUPPORT

For Windows testing:

Esc should normally:

close popup

go Back

open pause in combat

depending on context.

Enter can confirm simple dialogs when appropriate.

Do not interfere with touch controls.

---

# 107. SCREEN-SPECIFIC TESTING

Test each screen individually.

HOME:

navigation

resource updates

notifications

QUEST:

world selection

stage selection

locked states

UNITS:

sorting

filters

details

training

evolution

SUMMON:

cost

results

duplicates

TOWER:

floor unlocking

rewards

MISSIONS:

progress

claim

LOGIN:

claim

INVENTORY:

tabs

items

BATTLE:

HUD

five units

statuses

results

SETTINGS:

all controls

---

# 108. RESOLUTION TESTING

Test at multiple sizes.

Examples:

720 × 1280

1080 × 1920

1440 × 2560

smaller Windows portrait window

large desktop window

Verify:

text remains readable

icons remain sharp

panels scale correctly

bottom nav remains visible

safe areas work

---

# 109. TEXT OVERFLOW TEST

Use artificially long values.

Test:

long hero names

large Gold amount

large Gem amount

large Player Rank

long skill names

large inventory counts

long stage names

No UI element should overlap.

---

# 110. LOW RESOURCE TESTS

Test UI when player has:

0 Gold

0 Gems

0 Energy

0 materials

The game should remain usable.

Buttons requiring resources should clearly explain why they are disabled.

---

# 111. EXTREME RESOURCE TESTS

Test:

999,999 Gold

10,000 Gems

hundreds of materials

100+ heroes

Ensure UI does not break.

---

# 112. TRANSITION INTERRUPT TESTING

Rapidly press:

Back

tabs

menus

stage nodes

Do not allow duplicated screens or stuck transitions.

Disable conflicting input during short transition periods when necessary.

---

# 113. POPUP STACKING

Prevent multiple dialogs from stacking accidentally.

Example:

Confirm Evolution

should not open three times from repeated taps.

Use input locks/debounce.

---

# 114. UI MANAGER

If current architecture allows it:

create a central UI manager responsible for:

popups

toasts

transitions

tooltips

navigation state

loading overlays

confirmation dialogs

Do not put all gameplay logic inside the UI manager.

---

# 115. THEME RESOURCE

Create reusable Godot Theme resources.

Centralize:

fonts

font sizes

button styles

panel styles

colors

margins

progress bars

scrollbars

Do not manually configure every Control node.

---

# 116. REUSABLE SCREEN HEADER

Create a common header component.

Support:

Back button

Title

optional help icon

optional resource information

Different screens should not rebuild this independently.

---

# 117. REUSABLE CURRENCY WIDGET

One widget should display:

icon

number

plus button if relevant

Reuse on:

Home

Summon

Training

Evolution

Shop in future

---

# 118. PROGRESS BARS

Standardize:

Player XP

Hero XP

HP

Burst

Mission progress

Tower progress if used

Do not use the exact same bar art for everything.

Use the same structural rules but meaningful variants.

---

# 119. SCROLLBARS

Create custom scrollbars that match Cinderbound.

Keep them visible enough to communicate scroll position.

Do not use default Godot scrollbar appearance if it conflicts with the game's style.

---

# 120. MODAL BACKGROUND

When a modal opens:

dim the screen.

Do not completely hide context.

Block interaction with the underlying UI.

---

# 121. REWARD CELEBRATION LEVELS

Different rewards need different presentation intensity.

Common item:

small reveal.

Rare material:

small glow.

New hero:

larger presentation.

Evolution:

major presentation.

Do not make every Gold reward trigger a massive animation.

---

# 122. UI ANIMATION TIMING

Keep interaction fast.

General targets:

Button response:
immediate

Popup:
0.1–0.2 sec

Menu transition:
0.15–0.30 sec

Reward:
short

Do not make players wait on interface animations.

---

# 123. SKIP SUPPORT

Longer presentation sequences such as:

Summon

Evolution

Battle Results

should eventually allow skipping or speeding up after the player has seen them.

---

# 124. VISUAL EFFECT LIMITS

Menus should not be covered in constant particles.

Use ambient effects sparingly.

Good places:

Home

Summon

Evolution

Tower

Keep Units and Inventory cleaner for readability.

---

# 125. PHASE 5 DEVELOPMENT ORDER

Follow this order.

## STEP 1
Audit every existing screen.

## STEP 2
Create global Theme and spacing system.

## STEP 3
Create reusable buttons, panels and headers.

## STEP 4
Create resource bar and bottom navigation.

## STEP 5
Rebuild Home UI.

## STEP 6
Rebuild Quest / World / Stage UI.

## STEP 7
Rebuild Squad selection and editor.

## STEP 8
Rebuild Units grid.

## STEP 9
Rebuild Unit Detail.

## STEP 10
Rebuild Training.

## STEP 11
Rebuild Evolution.

## STEP 12
Rebuild Summon UI.

## STEP 13
Rebuild Tower UI.

## STEP 14
Rebuild Missions / Login Rewards.

## STEP 15
Rebuild Inventory.

## STEP 16
Battle HUD second pass.

## STEP 17
Battle Results / Defeat.

## STEP 18
Settings / Profile / Menu.

## STEP 19
Tutorial overlay system.

## STEP 20
Tooltips / Toasts / Dialogs.

## STEP 21
Transitions.

## STEP 22
Audio feedback.

## STEP 23
Responsive mobile pass.

## STEP 24
Performance pass.

## STEP 25
Full UI consistency audit.

## STEP 26
Regression test every gameplay system.

Do not jump randomly between screens.

---

# 126. IMPORTANT LIMIT FOR PHASE 5

Do NOT spend this phase primarily implementing:

new Worlds

new elements

PvP

guilds

raids

equipment systems

new summoning banners

large character batches

events

shops

battle passes

social systems

The purpose of this phase is to make the CURRENT game feel complete.

---

# 127. REQUIRED FINAL PLAYER FLOW

The following must feel consistent:

Launch game

→ Title

→ Home

→ Quest

→ World Select

→ Stage

→ Squad

→ Battle

→ Victory

→ Rewards

→ Home

→ Units

→ Unit Detail

→ Training

→ Evolution

→ Tower

→ obtain material

→ return to Evolution

→ evolve hero

→ Summon

→ obtain hero

→ edit Squad

→ Missions

→ claim reward

→ Settings

→ Home

At no point should the interface suddenly look like a different game.

---

# 128. PHASE 5 QUALITY TARGET

After Phase 5 the game should feel:

organized

responsive

readable

consistent

fast to navigate

designed for touch

usable on PC

visually recognizable as Cinderbound

The UI should support future content without requiring another complete redesign.

---

# 129. FINAL TEST CHECKLIST

Before completion:

Launch from clean install.

Test new save.

Test existing save.

Resize window repeatedly.

Test all tabs.

Test Back navigation.

Test every popup.

Test every scroll area.

Test every button.

Test every disabled state.

Test every tooltip.

Test low resources.

Test high resources.

Test long text.

Test 5-unit squad.

Test battle HUD.

Test Summon.

Test Evolution.

Test Tower.

Test Missions.

Test Inventory.

Test Settings.

Test Login reward.

Check for:

missing textures

default Godot controls

overlapping text

blurred art

dead buttons

wrong navigation

inconsistent panels

incorrect touch areas

runtime errors

warnings caused by broken UI scripts

Fix issues before packaging.

---

# 130. PACKAGE PHASE 5 BUILD

When testing is complete:

create:

Cinderbound_Phase5_Windows.zip

Include:

Cinderbound.exe

required data/assets

HOW-TO-PLAY.txt

CHANGELOG.txt

UI-GUIDE.md

No batch launcher.

No unnecessary cache folders.

---

# 131. UI-GUIDE.MD

Document the final UI system.

Include:

font hierarchy

spacing rules

button styles

panel styles

resource widgets

unit card rules

rarity visuals

element visuals

screen layout rules

navigation rules

popup rules

icon rules

responsive design rules

This becomes the UI standard for future development.

---

# 132. CHANGELOG

Document exactly what changed.

Examples:

- Redesigned Home screen
- Added persistent navigation
- Standardized resource displays
- Rebuilt Unit Collection layout
- Added unit filtering
- Redesigned Evolution screen
- Redesigned Tower navigation
- Updated Battle HUD for five-unit squads
- Added reusable tooltip system
- Added reusable confirmation dialogs
- Added responsive portrait layouts
- Added mobile safe-area support
- Added menu transitions
- Added UI sound feedback
- Fixed text overflow
- Fixed navigation bugs

Do not write vague notes.

---

# 133. FINAL DEVELOPMENT INSTRUCTION

Do not stop at screenshots, suggestions, or mockups.

Inspect the existing Cinderbound project.

Implement the interface changes directly into the current project.

Preserve the gameplay systems from previous phases.

Run the game after major changes.

Test every screen.

Fix layout bugs.

Fix navigation bugs.

Fix broken references.

Fix runtime errors.

Retest the packaged executable.

The purpose of Phase 5 is not to add more systems.

The purpose of Phase 5 is to make everything already built look and behave like one finished game.