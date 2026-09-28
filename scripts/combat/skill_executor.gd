class_name SkillExecutor
extends RefCounted
## Plays a planned action on screen: anticipation, movement, animation, hit
## timing, impact (flash, particles, numbers, hit-stop, tiered shake), sounds and
## the per-hero Burst presentation. All rules come from BattleModel; this class
## only decides WHEN each hit is applied so damage lines up with the animation.

const DASH_TIME := 0.24
const RETURN_TIME := 0.22
const PROJECTILE_TIME := 0.26
const MULTI_HIT_GAP := 0.07

## Shake tiers (pixels, seconds).
const SHAKE_TINY := [3.0, 0.08]
const SHAKE_STRONG := [8.0, 0.14]
const SHAKE_BURST := [15.0, 0.22]
const SHAKE_BOSS := [20.0, 0.3]

var battle: Node          # BattleController (owns views, effects, camera, hud)
var model: BattleModel


func _init(owner_battle: Node, battle_model: BattleModel) -> void:
	battle = owner_battle
	model = battle_model


func _wait(t: float) -> void:
	if t > 0.0:
		await battle.get_tree().create_timer(t, false).timeout


func _view(c: Combatant) -> BattleUnitView:
	return battle.views.get(c)


## Runs the whole action. Returns the finish_action() events.
func execute(plan: Dictionary) -> Array:
	var user: Combatant = plan["user"]
	var skill: Dictionary = plan["skill"]
	var uview := _view(user)
	battle.hud.add_log("%s uses %s!" % [user.display_name, skill.get("name", "?")],
			UIKit.GOLD if plan["is_burst"] else (UIKit.TEXT if user.is_player else Color("#ffb0a0")))
	if plan["is_burst"]:
		await _burst_intro(user, skill)
	elif not user.is_player and skill.get("kind", "") == "skill":
		await _enemy_special_windup(user, skill)
	match skill.get("motion", "melee"):
		"melee":
			await _melee(plan, uview, skill)
		"ranged":
			await _ranged(plan, uview, skill)
		_:
			await _self_cast(plan, uview, skill)
	var events := model.finish_action(plan)
	await _show_events(events, plan)
	if plan["is_burst"]:
		await _burst_outro(user)
	return events


# ------------------------------------------------------------------ anticipation
func _enemy_special_windup(user: Combatant, skill: Dictionary) -> void:
	var v := _view(user)
	if v == null:
		return
	var col := Database.element_color(user.element)
	v.anticipate(col.lightened(0.3), 0.35)
	battle.effects.floating_text(v.impact_point() + Vector2(0, -v.visual_height() * 0.7), String(skill.get("name", "")).to_upper(),
			col.lightened(0.5), 40)
	battle.effects.particles(user.element, v.impact_point(), 10)
	AudioManager.play_sfx("burst_ready", 0.1, -8.0)
	await _wait(0.35)


# ------------------------------------------------------------------ motions
func _melee(plan: Dictionary, uview: BattleUnitView, skill: Dictionary) -> void:
	var targets: Array = plan["targets"]
	if targets.is_empty():
		return
	var user: Combatant = plan["user"]
	var anchor: Vector2
	if targets.size() == 1:
		anchor = _view(targets[0]["unit"]).melee_anchor(user.is_player)
	else:
		var sum := Vector2.ZERO
		for t in targets:
			sum += _view(t["unit"]).home_pos
		anchor = sum / targets.size() + Vector2(260 if user.is_player else -260, 0)
	if not plan["is_burst"]:
		battle.camera.focus(anchor, 1.04, 0.25)
	uview.z_index = 12
	# anticipation: a short crouch before the lunge
	uview.anticipate(Color(1, 1, 1), 0.1)
	await _wait(0.08)
	await uview.move_to(anchor, DASH_TIME).finished
	var anim := uview.resolve_anim(skill.get("anim", "attack"))
	var total := uview.play_anim(anim)
	var elapsed := await _run_hits(plan, uview, skill, anim)
	await _wait(max(total - elapsed, 0.0) + 0.05)
	await uview.return_home(RETURN_TIME).finished
	uview.z_index = 0
	uview.play_idle()
	if not plan["is_burst"]:
		battle.camera.reset(0.25)


## Applies hits at the animation frames listed in the skill. Returns time spent.
func _run_hits(plan: Dictionary, uview: BattleUnitView, skill: Dictionary, anim: String) -> float:
	var hit_count: int = 0
	for t in plan["targets"]:
		hit_count = max(hit_count, t["hits"].size())
	var frames_list: Array = skill.get("hit_frames", [])
	var times: Array = []
	var last_frame := -1
	var dupes := 0
	for i in hit_count:
		var f: int = int(frames_list[i]) if i < frames_list.size() else (int(frames_list[-1]) if not frames_list.is_empty() else 2)
		dupes = dupes + 1 if f == last_frame else 0
		last_frame = f
		times.append(SpriteFactory.frame_time(uview.frames, anim, f) + dupes * MULTI_HIT_GAP)
	var elapsed := 0.0
	for i in hit_count:
		await _wait(times[i] - elapsed)
		elapsed = max(elapsed, times[i])
		for ti in plan["targets"].size():
			_hit(plan, ti, i, i == hit_count - 1)
	return elapsed


func _ranged(plan: Dictionary, uview: BattleUnitView, skill: Dictionary) -> void:
	var anim := uview.resolve_anim(skill.get("anim", "attack"))
	var total := uview.play_anim(anim)
	var release := SpriteFactory.frame_time(uview.frames, anim, int(skill.get("release_frame", 2)))
	var user: Combatant = plan["user"]
	# cast glow gathers while the staff / fins rise
	battle.effects.particles(user.element, uview.impact_point() + Vector2(-60 if user.is_player else 60, -20), 8, 360.0)
	await _wait(release)
	AudioManager.play_sfx(skill.get("sfx_cast", "water"))
	var from := uview.impact_point() + Vector2(-70 if user.is_player else 70, -10)
	var proj: String = skill.get("projectile", "")
	var last_tween: Tween = null
	for t in plan["targets"]:
		last_tween = battle.effects.projectile(proj, from, _view(t["unit"]).impact_point(), PROJECTILE_TIME, user.is_player)
	if last_tween:
		await last_tween.finished
	var hit_count: int = 0
	for t in plan["targets"]:
		hit_count = max(hit_count, t["hits"].size())
	for i in hit_count:
		for ti in plan["targets"].size():
			_hit(plan, ti, i, i == hit_count - 1)
		if i < hit_count - 1:
			# the stream keeps pouring: extra small projectiles for follow-up hits
			for t in plan["targets"]:
				battle.effects.projectile(proj, from, _view(t["unit"]).impact_point(), 0.12, user.is_player)
			await _wait(0.12)
	var spent := release + PROJECTILE_TIME + 0.12 * (hit_count - 1)
	await _wait(max(total - spent, 0.0) + 0.1)
	uview.play_idle()


func _self_cast(plan: Dictionary, uview: BattleUnitView, skill: Dictionary) -> void:
	var anim := uview.resolve_anim(skill.get("anim", "burst"))
	var total := uview.play_anim(anim)
	var release := SpriteFactory.frame_time(uview.frames, anim, int(skill.get("release_frame", 4)))
	var user: Combatant = plan["user"]
	var style: String = skill.get("burst_fx", "")
	var col := Database.element_color(user.element)
	match style:
		"tide_ring":
			# water gathers around Mira before the wave breaks
			battle.effects.ring(uview.global_position, Color("#5ac8ff"), 160, release, 10, 0.4)
			battle.effects.particles("water", uview.impact_point(), 12, 360.0)
		"hearth_hymn", "bloom", "litany", "bulwark":
			battle.effects.ring(uview.global_position, col.lightened(0.3), 150, release, 10, 0.4)
			battle.effects.particles(user.element, uview.impact_point(), 12, 360.0)
	await _wait(release)
	AudioManager.play_sfx(skill.get("sfx_cast", "burst"))
	var field: String = skill.get("field_effect", "")
	# skills that hit foes (e.g. a whirlpool or a curse on every enemy) play on the targets
	var hit_units: Array = plan["targets"].map(func(t): return t["unit"])
	var field_units: Array = hit_units if not hit_units.is_empty() and skill.get("target", "") != "ally_all" \
			else model.alive(model.allies_of(user))
	for ally in field_units:
		var v := _view(ally)
		if v == null:
			continue
		if field == "roots":
			battle.effects.spawn(field, v.global_position + Vector2(-40 if user.is_player else 40, -110), user.is_player, 1.0, 5)
		elif not field.is_empty():
			battle.effects.spawn(field, v.global_position + Vector2(0, -10), false, 1.0, -1)
		match style:
			"tide_ring":
				battle.effects.ring(v.global_position, Color("#8ae0ff"), 200, 0.5, 12, 0.4)
				battle.effects.particles("heal", v.impact_point(), 14, 360.0)
			"grove_bastion":
				battle.effects.shield_dome(v.global_position, Color("#8ae05a"), v.visual_height() * 0.62, 0.7)
				battle.effects.particles("earth", v.global_position + Vector2(0, -10), 16, 70.0)
				battle.effects.ring(v.global_position, Color("#8ae05a"), 220, 0.55, 12, 0.4)
			"bulwark":
				battle.effects.shield_dome(v.global_position, Color("#8ad8ff"), v.visual_height() * 0.62, 0.7)
				battle.effects.ring(v.global_position, Color("#8ad8ff"), 220, 0.55, 12, 0.4)
			"hearth_hymn":
				battle.effects.ring(v.global_position, Color("#ffcf6a"), 210, 0.5, 12, 0.4)
				battle.effects.particles("fire", v.impact_point(), 12, 360.0)
			"bloom":
				battle.effects.spawn("petal_burst", v.impact_point(), false, 1.0, -1)
				battle.effects.particles("heal", v.impact_point(), 14, 360.0)
			"litany":
				battle.effects.ring(v.global_position, Color("#b08aff"), 200, 0.5, 12, 0.4)
	if style == "litany":
		for f in model.alive(model.foes_of(user)):
			var fv := _view(f)
			if fv:
				battle.effects.spawn("hex_cloud", fv.impact_point(), false, 1.0, -1)
	var shake := float(skill.get("shake", 0.0))
	if shake > 0.0:
		battle.camera.shake(6.0 + 10.0 * shake, 0.25)
	match style:
		"grove_bastion", "bloom":
			battle.hud.flash_screen(Color("#8ae05a"), 0.2, 0.18)
		"tide_ring", "bulwark":
			battle.hud.flash_screen(Color("#8ae0ff"), 0.2, 0.18)
		"hearth_hymn":
			battle.hud.flash_screen(Color("#ffcf6a"), 0.2, 0.18)
		"litany":
			battle.hud.flash_screen(Color("#b08aff"), 0.2, 0.18)
	# damage part (all-target casts)
	var spent := 0.0
	if not plan["targets"].is_empty():
		var hit_count: int = 0
		for t in plan["targets"]:
			hit_count = max(hit_count, t["hits"].size())
		for i in hit_count:
			for ti in plan["targets"].size():
				_hit(plan, ti, i, i == hit_count - 1)
			if i < hit_count - 1:
				await _wait(0.12)
				spent += 0.12
	await _wait(max(total - release - spent, 0.2))
	uview.play_idle()


# ------------------------------------------------------------------ hits
func _hit(plan: Dictionary, ti: int, hi: int, is_final: bool) -> void:
	var entry: Dictionary = plan["targets"][ti]
	var target: Combatant = entry["unit"]
	var result := model.apply_hit(plan, ti, hi)
	if result["skipped"]:
		return
	var skill: Dictionary = plan["skill"]
	var user: Combatant = plan["user"]
	var is_burst: bool = plan["is_burst"]
	var style: String = skill.get("burst_fx", "")
	var tv := _view(target)
	var point := tv.impact_point()
	var flip := user.is_player   # effects drawn facing right; mirror for player attacks
	var slash: String = skill.get("hit_effect", "")
	var finisher := is_final and is_burst
	if finisher and skill.has("final_effect"):
		slash = skill["final_effect"]
	battle.effects.spawn(slash, point + Vector2(randf_range(-12, 12), randf_range(-16, 16)), flip, 1.3 if finisher else 1.0)
	battle.effects.spawn(skill.get("impact_effect", "hit_spark"), point + Vector2(randf_range(-30, 30), randf_range(-30, 30)), flip,
			1.5 if finisher else 0.8)
	battle.effects.particles(user.element, point, 18 if finisher else (10 if entry["crit"] else 6))
	if is_burst:
		match style:
			"ember_rush":
				battle.effects.streaks(point, Color("#ff9a3a"), 3 if not finisher else 7)
			"frost_waltz":
				battle.effects.streaks(point, Color("#bff4ff"), 3 if not finisher else 7)
			"volley":
				battle.effects.streaks(point, Color("#aef07a"), 2 if not finisher else 5)

	# ---- number
	var kind := "player" if target.is_player else "normal"
	var icon := ""
	if entry["tag"] == "WEAK":
		kind = "advantage"
		icon = "res://assets/icons/orb_%s.png" % user.element
	elif entry["tag"] == "RESIST":
		kind = "resist"
	if entry["crit"]:
		kind = "crit"
	if finisher and plan["targets"].size() == 1:
		kind = "finisher"
	var stagger := Vector2((hi % 3 - 1) * 70, -(hi % 3) * 30)
	if int(result.get("absorbed", 0)) > 0:
		battle.effects.floating_text(point + Vector2(0, -90) + stagger, "ABSORB %d" % int(result["absorbed"]), Color("#8ad8ff"), 28)
		battle.effects.shield_dome(tv.global_position, Color("#8ad8ff"), tv.visual_height() * 0.6, 0.25)
	if int(result["dealt"]) > 0 or int(result.get("absorbed", 0)) == 0:
		battle.effects.damage_number(point + Vector2(0, -30) + stagger, int(result["dealt"]), kind,
				entry["tag"] if hi == 0 else "", icon)
	AudioManager.play_sfx(skill.get("sfx_hit", "hit"), 0.08)

	# ---- impact: flash frame, hit-stop and tiered shake
	var boss_hit := bool(user.def.get("boss", false)) or bool(target.def.get("boss", false)) and is_final
	var tier: Array = []
	if finisher:
		tier = SHAKE_BURST
		battle.hud.flash_screen(Database.element_color(user.element).lightened(0.5), 0.35, 0.14)
		battle.effects.ring(tv.global_position, Database.element_color(user.element).lightened(0.3), 260, 0.4, 12, 0.35)
		battle.hit_stop(0.1)
	elif entry["crit"]:
		tier = SHAKE_STRONG
		battle.hud.flash_screen(Color.WHITE, 0.18, 0.08)
		battle.hit_stop(0.06)
	elif float(skill.get("shake", 0.0)) > 0.0 and (is_final or not is_burst):
		tier = SHAKE_STRONG
	elif is_final and not is_burst:
		tier = SHAKE_TINY
		battle.hit_stop(0.03)
	if bool(user.def.get("boss", false)) and is_final:
		tier = SHAKE_BOSS
		battle.hit_stop(0.07)
	elif boss_hit and tier.is_empty():
		tier = SHAKE_TINY
	if not tier.is_empty():
		battle.camera.shake(float(tier[0]), float(tier[1]))

	if hi == 0 and entry["tag"] == "WEAK":
		battle.hud.add_log("  Elemental advantage!", Color("#ff9a5a"))
	elif hi == 0 and entry["tag"] == "RESIST":
		battle.hud.add_log("  The attack is resisted...", Color("#9ab4d0"))
	if result["killed"]:
		battle.hud.add_log("%s was defeated!" % target.display_name, UIKit.MUTED if not target.is_player else UIKit.DANGER)
		tv.play_defeat()
		battle.effects.particles(target.element, point, 20)
		AudioManager.play_sfx("ko" if target.is_player else "enemy_die")
		if not target.is_player:
			battle.hit_stop(0.05)
		battle.on_unit_defeated(target)
	else:
		tv.hit_react(26.0 if (finisher or entry["crit"]) else 14.0)


func _show_events(events: Array, plan: Dictionary) -> void:
	var healed := false
	for e in events:
		var v := _view(e["unit"])
		if v == null:
			continue
		match e["type"]:
			"heal":
				battle.effects.damage_number(v.impact_point() + Vector2(0, -40), int(e["amount"]), "heal")
				battle.hud.add_log("  %s recovers %d HP." % [e["unit"].display_name, int(e["amount"])], UIKit.GOOD)
				v.flash(Color("#8ae05a"), 0.3)
				battle.pulse_card(e["unit"], Color("#8ae05a"))
				if not healed:
					AudioManager.play_sfx("heal")
					healed = true
			"status":
				var sdef := Database.get_status(e["status"])
				battle.effects.floating_text(v.impact_point() + Vector2(0, -120), String(sdef.get("name", "")).to_upper(),
						Color(sdef.get("color", "#ffffff")), 30)
				battle.hud.add_log("  %s: %s" % [e["unit"].display_name, sdef.get("name", "")], Color(sdef.get("color", "#ffffff")))
				if not sdef.get("negative", false):
					battle.pulse_card(e["unit"], Color(sdef.get("color", "#ffffff")))
			"cleanse":
				battle.effects.floating_text(v.impact_point() + Vector2(0, -160), "CLEANSED", Color("#bff4ff"), 30)
			"shield":
				battle.effects.shield_dome(v.global_position, Color("#8ad8ff"), v.visual_height() * 0.62, 0.6)
				battle.effects.floating_text(v.impact_point() + Vector2(0, -120), "SHIELD %d" % int(e["amount"]), Color("#8ad8ff"), 30)
				battle.hud.add_log("  %s gains a %d-point Shield." % [e["unit"].display_name, int(e["amount"])], Color("#8ad8ff"))
				battle.pulse_card(e["unit"], Color("#8ad8ff"))
			"burst":
				battle.effects.floating_text(v.impact_point() + Vector2(0, -150), "BURST +%d" % int(e["amount"]), UIKit.GOLD, 28)
				battle.pulse_card(e["unit"], UIKit.GOLD)
		await _wait(0.06)


# ------------------------------------------------------------------ burst presentation
## darken -> cut-in (hero + burst name) -> charge-up effect -> restore light.
func _burst_intro(user: Combatant, skill: Dictionary) -> void:
	AudioManager.play_sfx("burst")
	var uview := _view(user)
	uview.z_index = 12
	battle.set_dim(true)
	battle.camera.focus(uview.global_position, 1.07, 0.3)
	await battle.hud.play_burst_cutin(user, skill)
	# charge: element aura gathers on the hero
	var col := Database.element_color(user.element)
	uview.flash(col.lightened(0.4), 0.3)
	battle.effects.ring(uview.global_position, col.lightened(0.3), 170, 0.3, 10, 0.4)
	battle.effects.particles(user.element, uview.impact_point(), 20, 360.0)
	match skill.get("burst_fx", ""):
		"ember_rush":
			battle.effects.streaks(uview.impact_point(), Color("#ffb03a"), 4)
		"frost_waltz":
			battle.effects.streaks(uview.impact_point(), Color("#bff4ff"), 4)
	await _wait(0.18)
	battle.set_dim(false)


func _burst_outro(user: Combatant) -> void:
	var uview := _view(user)
	if uview:
		uview.z_index = 0
	await battle.camera.reset(0.3).finished
