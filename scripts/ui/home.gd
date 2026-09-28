extends ScreenBase
## Home hub: status bar (rank, energy, gems, gold), interactive camp with the
## squad around the fire (tap a hero to focus, tap again for a reaction), the big
## QUEST plate, then UNITS / SUMMON, then TOWER / MISSIONS / SQUAD, with locks
## and notification markers only where there is something to do.
## On arrival it shows, one at a time: save-update notes, the daily login reward
## and announcements for newly unlocked features.

const CAMP_MIN_H := 560
const FEATURE_INFO := {
	"auto": ["AUTO BATTLE", "res://assets/icons/auto.png", "Tap AUTO in battle and your heroes fight on their own - they Burst when it matters and Guard against charged attacks. Tap 1x/2x to speed battles up.", ""],
	"units": ["UNITS & SQUAD", "res://assets/icons/nav_units.png", "Your squad can now hold up to 5 heroes. Open UNITS to inspect heroes and SQUAD to choose who fights and who leads - the leader's Leader Skill boosts the team.", "squad"],
	"training": ["TRAINING", "res://assets/icons/radiant_wisp.png", "Feed Wisps and Gold to a hero to level them up. Wisps of the hero's own element give +50% EXP.", "units"],
	"tower": ["ELEMENTAL TOWERS", "res://assets/icons/tower.png", "Three towers - Ember, Tide and Verdant - wait to be climbed. Each floor is harder than the last and each tower is the best source of its element's evolution materials.", "tower"],
	"evolution": ["EVOLUTION", "res://assets/icons/star.png", "Heroes at max level can evolve into a stronger form with Fragments, Cores and Gold. Tap EVOLVE on a hero; WHERE TO FIND shows where materials drop.", "units"],
	"summon": ["THE EMBERGATE", "res://assets/icons/nav_summon.png", "The Embergate is open! Spend Gems to summon new heroes. Heroes you already own become Soul Shards for Burst training.", "summon"],
	"missions": ["MISSIONS", "res://assets/icons/missions.png", "Daily and weekly missions now give Gems, Gold and Wisps. Claim 4 daily missions to open the daily chest.", "missions"],
	"world2": ["SALTGLASS REACH", "res://assets/icons/world.png", "A new region beyond the Wilds: a glittering coast of salt-glass, drowned ruins and something enormous sleeping in the spire.", "world_select"],
}
## Short camp lines when a focused hero is tapped again (by element).
const LINES := {
	"fire": ["The fire's warm. Let's move!", "Point me at the next fight.", "Ready when you are."],
	"water": ["The tide is turning our way.", "Calm first, then strike.", "Ready when you are."],
	"nature": ["The forest is listening.", "Roots hold, branches strike.", "Ready when you are."],
	"light": ["Our path is bright.", "Stand behind me.", "Ready when you are."],
	"dark": ["The night hides us well.", "Quietly now.", "Ready when you are."],
}
const BG_SCALE := 5
const FIRE := Vector2(240, 205)          # campfire position in bg_camp pixels
# member feet relative to the campfire: leader in front, others around the fire
const SLOTS := [Vector2(0, 150), Vector2(-280, 60), Vector2(280, 60), Vector2(-420, 170), Vector2(420, 170)]

var camp: Control
var focus_plate: PanelFrame
var focus_uid := ""
var sprites: Dictionary = {}     # uid -> UnitSpriteDisplay


func _ready() -> void:
	if not require_profile():
		return
	var area := build_frame("bg_camp", "", "home", Callable(), 0.55)
	var col := UIKit.vbox(12)
	col.set_anchors_preset(Control.PRESET_FULL_RECT)
	area.add_child(col)
	col.add_child(_camp_view())
	col.add_child(_quest_plate())
	# feature hierarchy: QUEST (above) > UNITS / SUMMON > TOWER / MISSIONS / SQUAD
	var grid := GridContainer.new()
	grid.name = "FeatureGrid"
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", UIKit.SP_M)
	grid.add_theme_constant_override("v_separation", UIKit.SP_M)
	col.add_child(grid)
	grid.add_child(_tile("UNITS", "res://assets/icons/nav_units.png", "units", "UnitsButton", "units", GameManager.units_badge()))
	grid.add_child(_tile("SUMMON", "res://assets/icons/nav_summon.png", "summon", "SummonButton", "summon", GameManager.summon_badge()))
	var small := GridContainer.new()
	small.name = "SmallGrid"
	small.columns = 3
	small.add_theme_constant_override("h_separation", UIKit.SP_M)
	small.add_theme_constant_override("v_separation", UIKit.SP_M)
	col.add_child(small)
	small.add_child(_tile("TOWER", "res://assets/icons/nav_tower.png", "tower", "TowerButton", "tower", false, "!", 116))
	var mc := GameManager.missions_claimable()
	small.add_child(_tile("MISSIONS", "res://assets/icons/nav_missions.png", "missions", "MissionsButton", "missions",
			mc > 0 or GameManager.login_available(), str(mc) if mc > 0 else "!", 116))
	small.add_child(_tile("SQUAD", "res://assets/icons/leader.png", "squad", "SquadTile", "squad", false, "!", 116))
	AudioManager.play_music("world")
	_arrival_popups.call_deferred()


# ------------------------------------------------------------------ camp
func _camp_view() -> Control:
	var frame := PanelFrame.make("panel", 10)
	frame.custom_minimum_size.y = CAMP_MIN_H
	frame.size_flags_vertical = Control.SIZE_EXPAND_FILL
	camp = Control.new()
	camp.clip_contents = true
	camp.mouse_filter = Control.MOUSE_FILTER_IGNORE
	frame.add_child(camp)
	camp.resized.connect(_layout_camp)
	var bg := TextureRect.new()
	bg.name = "CampBG"
	bg.texture = load("res://assets/environments/bg_camp.png")
	bg.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.stretch_mode = TextureRect.STRETCH_SCALE
	bg.size = bg.texture.get_size() * BG_SCALE
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	camp.add_child(bg)
	var glow := _fire_glow()
	camp.add_child(glow)
	var embers := CPUParticles2D.new()
	embers.name = "FireEmbers"
	embers.amount = 22
	embers.lifetime = 1.8
	embers.preprocess = 2.0
	embers.emission_shape = CPUParticles2D.EMISSION_SHAPE_RECTANGLE
	embers.emission_rect_extents = Vector2(20, 6)
	embers.direction = Vector2(0, -1)
	embers.spread = 20
	embers.gravity = Vector2(6, -40)
	embers.initial_velocity_min = 40
	embers.initial_velocity_max = 90
	embers.scale_amount_min = 4
	embers.scale_amount_max = 8
	var g := Gradient.new()
	g.set_color(0, Color("#fff0a0"))
	g.add_point(0.4, Color("#ff8a2a"))
	g.set_color(g.get_point_count() - 1, Color(0.8, 0.2, 0.1, 0))
	embers.color_ramp = g
	camp.add_child(embers)

	var party := GameManager.party_units()
	for i in party.size():
		var u: Dictionary = party[i]
		_add_member(u, i)
	if not party.is_empty():
		focus_uid = party[0]["uid"]

	focus_plate = PanelFrame.make("plank", 12)
	focus_plate.name = "FocusPlate"
	camp.add_child(focus_plate)
	var hint := UIKit.label("TAP YOUR HEROES", UIKit.T_SMALL, Color(1, 1, 1, 0.6), HORIZONTAL_ALIGNMENT_RIGHT, 5)
	hint.name = "CampHint"
	camp.add_child(hint)
	_refresh_focus()
	return frame


func _fire_glow() -> Control:
	var glow := TextureRect.new()
	glow.name = "FireGlow"
	var grad := Gradient.new()
	grad.set_color(0, Color(1.0, 0.6, 0.2, 0.35))
	grad.set_color(1, Color(1.0, 0.4, 0.1, 0.0))
	var gt := GradientTexture2D.new()
	gt.gradient = grad
	gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.5)
	gt.fill_to = Vector2(1.0, 0.5)
	gt.width = 64
	gt.height = 32
	glow.texture = gt
	glow.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	glow.size = Vector2(900, 360)
	glow.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var mat := CanvasItemMaterial.new()
	mat.blend_mode = CanvasItemMaterial.BLEND_MODE_ADD
	glow.material = mat
	var tw := glow.create_tween().set_loops()
	tw.tween_property(glow, "modulate:a", 0.7, 0.35).set_trans(Tween.TRANS_SINE)
	tw.tween_property(glow, "modulate:a", 1.0, 0.25).set_trans(Tween.TRANS_SINE)
	tw.tween_property(glow, "modulate:a", 0.82, 0.3).set_trans(Tween.TRANS_SINE)
	tw.tween_property(glow, "modulate:a", 1.0, 0.4).set_trans(Tween.TRANS_SINE)
	return glow


func _add_member(u: Dictionary, slot: int) -> void:
	var def := Database.get_character(u.get("char_id", ""))
	var holder := Control.new()
	holder.name = "Member_%s" % u["uid"]
	holder.set_meta("slot", slot)
	camp.add_child(holder)
	var shadow := ColorRect.new()
	shadow.color = Color(0, 0, 0, 0.35)
	shadow.size = Vector2(150, 18)
	shadow.position = Vector2(-75, -10)
	shadow.mouse_filter = Control.MOUSE_FILTER_IGNORE
	holder.add_child(shadow)
	var sp := UnitSpriteDisplay.new()
	sp.setup(def.get("sprite", {}), 8.0 if slot == 0 else 7.0, slot == 2 or slot == 4)
	sp.size = sp.custom_minimum_size
	sp.position = Vector2(-sp.size.x / 2, -sp.size.y)
	holder.add_child(sp)
	sprites[u["uid"]] = sp
	# stagger idle so they don't bob in sync
	if sp.sprite:
		sp.sprite.frame = slot % 3
	var hit := Control.new()
	hit.name = "Tap_%s" % u["uid"]
	hit.size = Vector2(sp.size.x * 0.7, sp.size.y * 0.85)
	hit.position = Vector2(-hit.size.x / 2, -hit.size.y)
	holder.add_child(hit)
	var uid: String = u["uid"]
	UIKit.on_tap(hit, func(): _on_member_tapped(uid))
	if slot == 0:
		var em := UIKit.icon("res://assets/icons/leader.png", 64)
		em.name = "LeaderEmblem"
		em.position = Vector2(-32, -sp.size.y * 0.8 - 56)
		holder.add_child(em)
		var tw := em.create_tween().set_loops()
		tw.tween_property(em, "position:y", em.position.y - 10, 0.7).set_trans(Tween.TRANS_SINE)
		tw.tween_property(em, "position:y", em.position.y, 0.7).set_trans(Tween.TRANS_SINE)


func _layout_camp() -> void:
	var w := camp.size.x
	# campfire sits in the lower third of the view; the starry sky fills the rest
	var fire_y := camp.size.y - 290.0
	var off := Vector2(w / 2.0 - FIRE.x * BG_SCALE, fire_y - FIRE.y * BG_SCALE)
	camp.get_node("CampBG").position = off
	var fire := FIRE * BG_SCALE + off
	var glow: Control = camp.get_node("FireGlow")
	glow.position = fire - glow.size / 2.0
	(camp.get_node("FireEmbers") as CPUParticles2D).position = fire + Vector2(0, -20)
	for ch in camp.get_children():
		if ch.has_meta("slot"):
			var s: Vector2 = SLOTS[int(ch.get_meta("slot")) % SLOTS.size()]
			ch.position = fire + s
	# draw back members first
	for ch in camp.get_children():
		if ch.has_meta("slot"):
			ch.z_index = int(ch.position.y / 10.0) - 60
	focus_plate.position = Vector2(12, 12)
	focus_plate.size = Vector2(w - 24, 0)
	var hint: Control = camp.get_node("CampHint")
	hint.position = Vector2(w - 420, camp.size.y - 44)
	hint.size = Vector2(400, 34)


func _on_member_tapped(uid: String) -> void:
	var sp: UnitSpriteDisplay = sprites.get(uid)
	if sp == null:
		return
	if uid == focus_uid:
		# flourish: victory pose (leader) or attack swing
		sp.play("victory" if uid == GameManager.leader_uid() else "attack")
		AudioManager.play_sfx("unit_select", 0.05)
		if not sp.sprite.animation_finished.is_connected(_idle.bind(sp)):
			sp.sprite.animation_finished.connect(_idle.bind(sp))
		var holder := sp.get_parent() as Control
		if holder.has_meta("hopping"):
			return
		holder.set_meta("hopping", true)
		var base_y := holder.position.y
		var tw := holder.create_tween()
		tw.tween_property(holder, "position:y", base_y - 24, 0.12).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		tw.tween_property(holder, "position:y", base_y, 0.14).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		tw.tween_callback(func(): holder.remove_meta("hopping"))
		var def := Database.get_character(GameManager.get_unit(uid).get("char_id", ""))
		var pool: Array = LINES.get(def.get("element", "fire"), LINES["fire"])
		_speech(holder, sp, pool[randi() % pool.size()])
	else:
		focus_uid = uid
		AudioManager.play_sfx("unit_select", 0.03, -3.0)
		_refresh_focus()


## Small speech bubble above a camp hero (one at a time, fades by itself).
func _speech(holder: Control, sp: UnitSpriteDisplay, text: String) -> void:
	var old := camp.get_node_or_null("Speech")
	if old:
		old.free()
	var b := PanelFrame.make("inset", 10)
	b.name = "Speech"
	b.mouse_filter = Control.MOUSE_FILTER_IGNORE
	b.add_child(UIKit.label(text, UIKit.T_SMALL, UIKit.TEXT, HORIZONTAL_ALIGNMENT_CENTER, 5))
	camp.add_child(b)
	b.z_index = 40
	b.size = b.get_combined_minimum_size()
	var x := clampf(holder.position.x - b.size.x / 2.0, 8.0, camp.size.x - b.size.x - 8.0)
	b.position = Vector2(x, holder.position.y - sp.size.y * 0.9 - b.size.y - 30)
	b.modulate.a = 0.0
	var tw := b.create_tween()
	tw.tween_property(b, "modulate:a", 1.0, 0.12)
	tw.tween_interval(1.6)
	tw.tween_property(b, "modulate:a", 0.0, 0.25)
	tw.tween_callback(b.queue_free)


func _idle(sp: UnitSpriteDisplay) -> void:
	if is_instance_valid(sp):
		sp.play("idle")


func _refresh_focus() -> void:
	for uid in sprites.keys():
		var sp: UnitSpriteDisplay = sprites[uid]
		sp.modulate = Color.WHITE if uid == focus_uid else Color(0.72, 0.72, 0.8)
	for ch in focus_plate.get_children():
		ch.queue_free()
	var u := GameManager.get_unit(focus_uid)
	if u.is_empty():
		focus_plate.visible = false
		return
	focus_plate.visible = true
	var def := Database.get_character(u["char_id"])
	var row := UIKit.hbox(12)
	focus_plate.add_child(row)
	row.add_child(UIKit.orb(def.get("element", ""), 64))
	var v := UIKit.vbox(0)
	v.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var nm := UIKit.label(def.get("name", ""), UIKit.T_NAME, Color("#fff0c0"), HORIZONTAL_ALIGNMENT_LEFT, 8)
	nm.name = "FocusName"
	v.add_child(nm)
	var lead := " - LEADER" if focus_uid == GameManager.leader_uid() else ""
	v.add_child(UIKit.label("Lv.%d  %s%s" % [int(u["level"]), def.get("class", ""), lead], UIKit.T_SMALL, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 5))
	row.add_child(v)
	var b := FantasyButton.make("DETAILS", "steel", Vector2(230, 96))
	b.add_theme_font_size_override("font_size", 30)
	var uid := focus_uid
	b.pressed.connect(func(): SceneRouter.go("unit_detail", {"uid": uid}))
	row.add_child(b)


# ------------------------------------------------------------------ plates
func _next_stage() -> Dictionary:
	var last := Database.stage_order[0]
	for sid in Database.stage_order:
		if GameManager.is_stage_unlocked(sid):
			last = sid
	return Database.get_stage(last)


func _quest_plate() -> Control:
	var b := FantasyButton.make("", "ember", Vector2(0, 230))
	b.name = "QuestButton"
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var v := UIKit.vbox(0)
	v.set_anchors_preset(Control.PRESET_FULL_RECT)
	v.alignment = BoxContainer.ALIGNMENT_CENTER
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	b.add_child(v)
	var h := UIKit.hbox(20)
	h.alignment = BoxContainer.ALIGNMENT_CENTER
	h.mouse_filter = Control.MOUSE_FILTER_IGNORE
	h.add_child(UIKit.icon("res://assets/icons/nav_quest.png", 112))
	var title := UIKit.label("QUEST", 120, Color("#ffe08a"), HORIZONTAL_ALIGNMENT_CENTER, 20)
	title.add_theme_color_override("font_outline_color", Color("#3a0e08"))
	h.add_child(title)
	v.add_child(h)
	var st := _next_stage()
	var cleared := GameManager.is_stage_cleared(st.get("id", ""))
	var sub := "%s  -  %s: %s" % ["Replay" if cleared else "Next", GameManager.stage_label(st.get("id", "")), st.get("name", "")]
	var sl := UIKit.label(sub, UIKit.T_BODY, Color("#fff0d0"), HORIZONTAL_ALIGNMENT_CENTER, 6)
	sl.name = "QuestNext"
	v.add_child(sl)
	var sid: String = st.get("id", "")
	b.pressed.connect(func(): SceneRouter.go("stage_select", {"highlight": sid}))
	b.add_shine()
	# ember sparks drift over the main action
	UIKit.sparkle(b, Rect2(40, 30, 960, 190), Color("#ffb04a"), 8)
	return b


## Feature tile: opens its screen, or explains where it unlocks.
func _tile(text: String, icon_path: String, scene: String, node_name: String, feature: String, badge: bool,
		badge_text := "!", height := 150) -> Control:
	var b := FantasyButton.make(text, "steel", Vector2(0, height), icon_path)
	b.name = node_name
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	b.add_theme_font_size_override("font_size", UIKit.T_NAME if height >= 140 else UIKit.T_BODY)
	b.add_theme_constant_override("icon_max_width", 72 if height >= 140 else 56)
	var locked := not feature.is_empty() and not GameManager.feature_unlocked(feature)
	if locked:
		b.modulate = Color(0.55, 0.53, 0.58)
		var lk := UIKit.icon("res://assets/icons/lock.png", 40)
		lk.position = Vector2(10, 10)
		b.add_child(lk)
		var req := GameManager.feature_unlock_label(feature)
		b.tooltip_text = "Unlocks after clearing %s" % req
		b.pressed.connect(func(): UIManager.toast("%s unlocks after clearing %s." % [text.capitalize(), req], "info"))
	else:
		b.pressed.connect(func(): SceneRouter.go(scene))
		if badge:
			UIKit.badge(b, badge_text)
	return b


# ------------------------------------------------------------------ arrival popups
func _arrival_popups() -> void:
	if not is_inside_tree():
		return
	await get_tree().create_timer(0.35).timeout
	if not GameManager.pending_migration_notes.is_empty():
		var notes: Array = GameManager.pending_migration_notes
		GameManager.pending_migration_notes = []
		var p := UIKit.message(self, "YOUR SAVE WAS UPDATED", "\n\n".join(notes) + "\n\nAll your progress was kept.")
		await p.tree_exited
	if not is_inside_tree():
		return
	if GameManager.login_available() and GameManager.profile.get("tutorial", {}).get("intro_seen", false) \
			and GameManager.stages_cleared_count() > 0:
		await _login_popup()
	if not is_inside_tree():
		return
	var fresh: Array = []
	for f in ["auto", "units", "training", "tower", "evolution", "summon", "missions", "world2"]:
		if GameManager.feature_unlocked(f) and not GameManager.feature_announced(f) and \
				not Database.progression.get("unlocks", {}).get(f, "").is_empty():
			fresh.append(f)
	if fresh.size() > 2:
		await _announce_many(fresh)
	else:
		for f in fresh:
			if not is_inside_tree():
				return
			await _announce(f)


func _login_popup() -> void:
	var cycle: Array = Database.login_rewards.get("cycle", [])
	if cycle.is_empty():
		return
	var idx := GameManager.login_day_index()
	var p := FantasyPopup.open(self, "DAILY LOGIN", 960, "boss")
	p.name = "LoginPopup"
	p.content.add_child(UIKit.label("DAY %d REWARD" % (idx + 1), UIKit.T_NAME, UIKit.GOLD, HORIZONTAL_ALIGNMENT_CENTER, 8))
	var row := UIKit.hbox(8)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	for i in cycle.size():
		var c := PanelFrame.make("slot" if i != idx else "boss", 4)
		c.custom_minimum_size = Vector2(118, 118)
		var l := UIKit.label("D%d" % (i + 1), UIKit.T_SMALL, UIKit.GOLD if i == idx else (UIKit.MUTED if i < idx else UIKit.TEXT),
				HORIZONTAL_ALIGNMENT_CENTER, 5)
		l.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		c.add_child(l)
		if i < idx:
			c.modulate = Color(0.6, 0.6, 0.65)
		row.add_child(c)
	p.content.add_child(row)
	var claim := FantasyButton.make("CLAIM", "gold", Vector2(360, 120))
	claim.name = "ClaimLoginPopup"
	claim.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	claim.add_shine()
	p.content.add_child(claim)
	p.cancel_action = func(): claim.pressed.emit()
	p.default_action = p.cancel_action
	await claim.pressed
	if not is_inside_tree():
		return
	var r := GameManager.claim_login()
	p.close()
	AudioManager.play_sfx("claim")
	var rp := RewardPopup.open(self, "LOGIN REWARD", r, "Day %d of 7 - come back tomorrow for the next reward!" % int(r.get("day", 1)))
	await rp.tree_exited
	_refresh_after_rewards()


func _refresh_after_rewards() -> void:
	# currencies are live in the status bar; badges refresh on the next visit
	pass


func _announce(f: String) -> void:
	var info: Array = FEATURE_INFO.get(f, [f.to_upper(), "res://assets/icons/star.png", "", ""])
	GameManager.mark_feature_announced(f)
	var p := FantasyPopup.open(self, "NEW: " + info[0], 940, "boss")
	p.name = "FeaturePopup"
	var ic := UIKit.icon(info[1], 128)
	ic.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	p.content.add_child(ic)
	var w := UIKit.wrap_label(info[2], UIKit.T_BODY)
	w.custom_minimum_size.x = 860
	w.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	p.content.add_child(w)
	if f == "units":
		var gift := _gift_unit()
		if not gift.is_empty():
			var d := Database.get_character(gift["char_id"])
			var g := UIKit.hbox(14)
			g.alignment = BoxContainer.ALIGNMENT_CENTER
			var fr := PanelFrame.make("rarity_%d" % int(d.get("rarity", 3)), 6)
			fr.add_child(UIKit.portrait_art(d, Vector2(180, 180)))
			g.add_child(fr)
			var gw := UIKit.wrap_label("%s has joined you and is already in your squad!" % d.get("name", ""), UIKit.T_BODY, UIKit.GOLD)
			gw.custom_minimum_size.x = 560
			g.add_child(gw)
			p.content.add_child(g)
			if not GameManager.is_in_party(gift["uid"]) and GameManager.party_uids().size() < GameManager.max_party_size():
				GameManager.toggle_party(gift["uid"])
			if not GameManager.is_in_party(gift["uid"]):
				gw.text = "%s has joined you! Add them to your squad from SQUAD." % d.get("name", "")
	var row := UIKit.hbox(14)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	if not String(info[3]).is_empty():
		var go := FantasyButton.make("TAKE ME THERE", "ember", Vector2(420, 116))
		go.name = "FeatureGo"
		var scene: String = info[3]
		go.pressed.connect(func():
			p.close()
			SceneRouter.go(scene))
		row.add_child(go)
	var later := FantasyButton.make("OK", "stone", Vector2(260, 116))
	later.name = "FeatureOK"
	later.pressed.connect(p.close)
	row.add_child(later)
	p.content.add_child(row)
	AudioManager.play_sfx("level_up", 0.0, -4.0)
	await p.tree_exited


func _announce_many(features: Array) -> void:
	var p := FantasyPopup.open(self, "NEW FEATURES", 940, "boss")
	p.name = "FeaturePopup"
	for f in features:
		GameManager.mark_feature_announced(f)
		var info: Array = FEATURE_INFO.get(f, [f.to_upper(), "res://assets/icons/star.png", "", ""])
		var h := UIKit.hbox(12)
		h.add_child(UIKit.icon(info[1], 56))
		h.add_child(UIKit.label(info[0], UIKit.T_BODY, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 6))
		p.content.add_child(h)
	var w := UIKit.wrap_label("Explore them from the Home screen and the MENU.", UIKit.T_SMALL, UIKit.MUTED)
	w.custom_minimum_size.x = 860
	p.content.add_child(w)
	var ok := FantasyButton.make("OK", "ember", Vector2(300, 116))
	ok.name = "FeatureOK"
	ok.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	ok.pressed.connect(p.close)
	p.content.add_child(ok)
	await p.tree_exited


func _gift_unit() -> Dictionary:
	var gifts: Dictionary = Database.progression.get("unlock_gifts", {}).get(Database.progression.get("unlocks", {}).get("units", ""), {})
	var hero: String = gifts.get("hero_by_starter", {}).get(GameManager.profile.get("starter_id", ""), "")
	if hero.is_empty():
		return {}
	return GameManager.unit_of_family(Database.get_character(hero).get("family", ""))
