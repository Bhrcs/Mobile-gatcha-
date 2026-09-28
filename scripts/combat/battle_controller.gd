class_name BattleController
extends Node2D
## Orchestrates a battle scene: builds the arena from stage data, routes player
## input, runs the player -> enemy -> end-of-round loop, handles waves and the
## victory / defeat flow. Rules live in BattleModel, animation in SkillExecutor.

signal state_changed(state: String)
signal battle_finished(victory: bool)

enum State { INTRO, PLAYER, BUSY, ENEMY, RESULT }

# Formation slots as offsets from the battlefield's bottom edge (portrait layout).
# Five slots per side for 5-hero squads (leader in front).
const PLAYER_SLOTS := [Vector2(690, -170), Vector2(905, -300), Vector2(915, -50), Vector2(660, -420), Vector2(790, -10)]
const ENEMY_SLOTS := [Vector2(380, -140), Vector2(175, -280), Vector2(165, -30), Vector2(380, -390), Vector2(340, -10)]
const SINGLE_PLAYER_POS := Vector2(790, -90)
const SINGLE_ENEMY_POS := Vector2(290, -90)
# Minions called by a boss appear in front of it.
const SUMMON_SLOTS := [Vector2(470, -300), Vector2(480, -20)]

var battle_speed := 1.0
var _warned_charge := false

var model := BattleModel.new()
var executor: SkillExecutor
var views: Dictionary = {}          # Combatant -> BattleUnitView
var state: State = State.INTRO
var selected: Combatant
var target: Combatant
var stage_id := ""
var result_summary: Dictionary = {}

@onready var camera: BattleCamera = $Camera
@onready var background: Sprite2D = $Background
var stage_view: BattleStage
@onready var units_root: Node2D = $Units
@onready var effects: EffectsLayer = $Effects
@onready var dim: ColorRect = $Dim
@onready var hud: BattleHUD = $HUD


func _ready() -> void:
	stage_id = SceneRouter.params.get("stage_id", GameManager.current_stage_id)
	if stage_id.is_empty() or Database.get_stage(stage_id).is_empty():
		stage_id = Database.stage_order[0]
	if not GameManager.has_profile():
		# Scene launched directly from the editor: use a throwaway profile.
		if not GameManager.continue_game():
			GameManager.profile = SaveManager.default_profile()
			GameManager.profile["starter_id"] = "kael_emberclaw"
			GameManager.profile["units"] = [{"uid": "u1", "char_id": "kael_emberclaw", "level": 1, "exp": 0}]
			GameManager.profile["party"] = ["u1"]
	GameManager.current_stage_id = stage_id
	executor = SkillExecutor.new(self, model)
	var seed_value := int(SceneRouter.params.get("seed", -1))
	model.setup(stage_id, GameManager.party_units(), seed_value)
	_setup_background()
	dim.visible = false
	hud.unit_selected.connect(_on_unit_selected)
	hud.card_action.connect(func(c, a):
		if hud.auto_on:
			hud.set_auto(false, true)
		request_action(a, c))
	hud.menu_requested.connect(_on_menu)
	hud.target_requested.connect(func(c):
		if state == State.PLAYER and c.is_alive() and c != target:
			set_target(c)
			AudioManager.play_sfx("target", 0.05, -4.0)
			_coach_progress("target"))
	hud.set_party(model.players)
	hud.set_auto_available(GameManager.feature_unlocked("auto"))
	hud.set_auto(bool(GameManager.settings.get("auto_battle", false)))
	hud.auto_toggled.connect(func(on):
		GameManager.set_setting("auto_battle", on)
		hud.add_log("Auto Battle %s." % ("ON" if on else "OFF"), UIKit.SKY)
		if on:
			_auto_step())
	set_battle_speed(float(GameManager.settings.get("battle_speed", 1.0)))
	hud.speed_toggled.connect(func(v):
		set_battle_speed(v)
		GameManager.set_setting("battle_speed", v))
	_fit_background()      # party size decides where the battlefield ends
	model.enemy_defeated.connect(func(_e): _update_loot())
	_update_loot()
	for p in model.players:
		_spawn_view(p, _slot_pos(PLAYER_SLOTS, p.slot, model.players.size(), true))
	AudioManager.play_music("boss" if model.stage.get("boss", false) else "battle")
	_start_battle()


func _setup_background() -> void:
	background.visible = false
	stage_view = BattleStage.new()
	stage_view.name = "Stage"
	stage_view.z_index = -10
	add_child(stage_view)
	move_child(stage_view, 0)
	stage_view.setup(model.stage.get("background", "bg_forest"), bool(model.stage.get("boss", false)), camera)
	_fit_background()
	get_viewport().size_changed.connect(_fit_background)


## Fits the layered stage to any window shape: the ground plane always ends just
## under the unit cards, whatever the aspect ratio or party size.
func _fit_background() -> void:
	var vs := get_viewport_rect().size
	camera.base_position = vs / 2.0
	camera.position = camera.base_position
	stage_view.fit(vs, hud.field_bottom())


func _enemy_pos(e: Combatant) -> Vector2:
	if e.summoned:
		var off: Vector2 = SUMMON_SLOTS[e.summon_index % SUMMON_SLOTS.size()]
		return Vector2(off.x, hud.field_bottom() + off.y)
	var wave_size := 0
	for x in model.enemies:
		if not x.summoned:
			wave_size += 1
	return _slot_pos(ENEMY_SLOTS, e.slot, wave_size, false)


func _slot_pos(slots: Array, slot: int, count: int, is_player: bool) -> Vector2:
	var off: Vector2 = slots[slot % slots.size()]
	if count == 1:
		off = SINGLE_PLAYER_POS if is_player else SINGLE_ENEMY_POS
	return Vector2(off.x, hud.field_bottom() + off.y)


func _spawn_view(c: Combatant, pos: Vector2) -> BattleUnitView:
	var scene: PackedScene = load("res://scenes/characters/player_battle_unit.tscn") if c.is_player \
			else load("res://scenes/enemies/enemy_battle_unit.tscn")
	var v: BattleUnitView = scene.instantiate()
	units_root.add_child(v)
	# big squads / summoned minions are drawn a little smaller so the field stays readable
	var mult := 1.0
	if c.is_player and model.players.size() >= 4:
		mult = 0.86
	elif c.summoned:
		mult = 0.9
	v.setup(c, pos, mult)
	views[c] = v
	return v


# ------------------------------------------------------------------ flow
func _set_state(s: State) -> void:
	state = s
	state_changed.emit(State.keys()[s])
	_refresh_hud()


func _start_battle() -> void:
	_set_state(State.INTRO)
	await _spawn_wave_views(true)
	var hint_id: String = model.stage.get("hint", "")
	if not hint_id.is_empty() and not GameManager.hint_seen(hint_id) and not SceneRouter.params.get("skip_hints", false):
		await hud.show_hint(Database.hints.get(hint_id, {}))
		GameManager.mark_hint_seen(hint_id)
	_begin_player_phase()


func _spawn_wave_views(_first: bool) -> void:
	hud.set_header(model.stage, model.wave_index, model.wave_count(), model.round_number)
	var boss: Combatant = null
	for e in model.enemies:
		if bool(e.def.get("boss", false)):
			boss = e
	if boss == null:
		await hud.show_banner("WAVE %d/%d" % [model.wave_index + 1, model.wave_count()], Color("#fff0c0"), 0.45)
	for e in model.enemies:
		if e == boss:
			continue
		var pos := _enemy_pos(e)
		var v := _spawn_view(e, pos)
		v.position.x -= 700
		v.move_to(pos, 0.5)
	if boss:
		await _boss_intro(boss)
	else:
		await get_tree().create_timer(0.55, false).timeout
	hud.set_enemies(model.enemies)
	await _wave_hints()
	hud.add_log("Wave %d: %s" % [model.wave_index + 1, ", ".join(model.enemies.map(func(e): return "%s Lv.%d" % [e.display_name, e.level]))], UIKit.MUTED)


## Ancient foe entrance: the wave pauses, the field darkens, the boss stalks in
## as a silhouette with heavy steps, its title appears, then the light returns.
func _boss_intro(boss: Combatant) -> void:
	var pos := _enemy_pos(boss)
	AudioManager.stop_music(0.3)
	dim.visible = true
	var dtw := create_tween()
	dtw.tween_property(dim, "color:a", 0.72, 0.25)
	var v := _spawn_view(boss, pos + Vector2(-520, 0))
	v.z_index = 8
	v.set_silhouette(true)
	await get_tree().create_timer(0.25, false).timeout
	AudioManager.play_sfx("boss_sting")
	for i in 3:
		var tw := create_tween()
		tw.tween_property(v, "position", pos + Vector2(-520 + 175 * (i + 1), 0), 0.24).set_trans(Tween.TRANS_QUAD)
		await tw.finished
		camera.shake(10.0 + i * 3.0, 0.14)
		effects.particles("earth", v.global_position, 10, 80.0)
	hud.play_boss_title(boss.display_name)     # runs alongside the reveal (about 1.6 s)
	await get_tree().create_timer(0.35, false).timeout
	hud.flash_screen(Color("#c8ff9a"), 0.4, 0.2)
	var ctw := create_tween().set_parallel(true)
	ctw.tween_property(dim, "color:a", 0.0, 0.35)
	v.set_silhouette(false, 0.35)
	camera.shake(16.0, 0.3)
	await get_tree().create_timer(1.25, false).timeout
	dim.visible = false
	v.z_index = 0
	v.home_pos = pos
	AudioManager.play_music("boss")


func _begin_player_phase() -> void:
	if model.all_players_dead():
		_finish(false)
		return
	hud.set_header(model.stage, model.wave_index, model.wave_count(), model.round_number)
	for p in model.players:
		if views.has(p) and not p.guarding:
			views[p].set_guarding(false)
	selected = model.first_ready_player()
	if target == null or not target.is_alive():
		_auto_target()
	_set_state(State.PLAYER)
	_coach_check()
	_auto_step()


# ------------------------------------------------------------------ coach marks (visual tutorial)
var _coach: CoachMark
var _coach_step := ""


## Shows at most one coach mark at a time; each step is permanent once done
## (Settings > Reset Tutorial brings them back).
func _coach_check() -> void:
	if state != State.PLAYER or SceneRouter.params.get("skip_hints", false) or _coach != null or hud.auto_on:
		return
	var ready_unit: Combatant = null
	for p in model.players:
		if p.can_act() and p.burst_ready():
			ready_unit = p
	if not GameManager.coach_done("tap_attack") and selected and hud.cards.has(selected):
		_show_coach("tap_attack", hud.cards[selected], "Tap %s to attack." % selected.display_name.split(" ")[0], "tap")
	elif ready_unit and not GameManager.coach_done("burst") and hud.cards.has(ready_unit):
		_show_coach("burst", hud.cards[ready_unit], "Burst is full! Swipe up on %s." % ready_unit.display_name.split(" ")[0], "up")
	elif model.alive(model.enemies).size() > 1 and not GameManager.coach_done("target") and GameManager.coach_done("tap_attack"):
		_show_coach("target", hud.enemy_row, "Tap an enemy to choose your target.", "tap", false)


func _show_coach(step: String, ctrl: Control, text: String, gesture: String, block := true) -> void:
	_coach_step = step
	_coach = CoachMark.show_on(hud.root, ctrl, text, gesture, block)


## Completes the current coach step when the matching thing happened.
func _coach_progress(event: String) -> void:
	if _coach == null:
		return
	var done := (_coach_step == "tap_attack" and event in ["attack", "burst", "guard"]) \
			or (_coach_step == "burst" and event == "burst") \
			or (_coach_step == "target" and event in ["target", "attack", "burst", "guard"])
	if done:
		GameManager.mark_coach_done(_coach_step)
		_coach.finish()
		_coach = null
		_coach_step = ""


func _auto_target() -> void:
	var living := model.alive(model.enemies)
	set_target(living[0] if not living.is_empty() else null)


# ------------------------------------------------------------------ input API (HUD, keyboard, tests)
func set_target(e: Combatant) -> void:
	if target and views.has(target):
		views[target].set_targeted(false)
	target = e
	if target and views.has(target) and target.is_alive():
		views[target].set_targeted(true)
	hud.set_target_text(target)


func _on_unit_selected(c: Combatant) -> void:
	if state != State.PLAYER or not c.can_act():
		return
	selected = c
	_refresh_hud()


## "attack" | "burst" | "guard" for `unit` (defaults to the next ready unit).
## Ignored while anything is animating, so rapid taps can never double-act.
func request_action(action: String, unit: Combatant = null) -> void:
	if unit != null:
		selected = unit
	if state != State.PLAYER or selected == null or not selected.can_act():
		return
	if action == "burst" and not selected.burst_ready():
		hud.add_log("%s's Burst gauge is not full yet." % selected.display_name, UIKit.MUTED)
		return
	if target == null or not target.is_alive():
		_auto_target()
	var user := selected
	_coach_progress(action)
	if _coach:          # an unrelated coach step stays up; hide it while animating
		_coach.visible = false
	_set_state(State.BUSY)
	match action:
		"attack":
			await executor.execute(model.plan_action(user, user.normal_skill, target))
		"burst":
			await executor.execute(model.plan_action(user, user.burst_skill, target, true))
		"guard":
			model.guard(user)
			hud.add_log("%s is guarding." % user.display_name, Color("#a8c4e0"))
			var gv: BattleUnitView = views[user]
			gv.play_guard()
			effects.floating_text(gv.impact_point() + Vector2(0, -80), "GUARD", Color("#a8d0ff"), 40)
			effects.shield_dome(gv.global_position, Color("#a8d0ff"), gv.visual_height() * 0.6, 0.25)
			AudioManager.play_sfx("guard")
			await get_tree().create_timer(0.4, false).timeout
	await _after_player_action()


func _after_player_action() -> void:
	if await _check_wave_end():
		return
	if model.players_can_act():
		selected = model.first_ready_player()
		_set_state(State.PLAYER)
		if _coach:
			_coach.visible = true
		_coach_check()
		_auto_step()
	else:
		await _enemy_phase()


## Returns true if the battle moved on (next wave or victory).
func _check_wave_end() -> bool:
	if not model.all_enemies_dead():
		return false
	await get_tree().create_timer(0.5, false).timeout
	if model.has_next_wave():
		for c in views.keys():
			if not c.is_player:
				views[c].queue_free()
				views.erase(c)
		target = null
		hud.set_enemies([])
		model.advance_wave()
		_show_wave_recovery()
		await _spawn_wave_views(false)
		_begin_player_phase()
	else:
		_finish(true)
	return true


func _show_wave_recovery() -> void:
	var pct := float(Database.balance("combat", "wave_recovery_percent", 0.0))
	if pct <= 0.0:
		return
	for p in model.alive(model.players):
		effects.floating_text(views[p].impact_point() + Vector2(0, -60), "RECOVER", Color("#8ae05a"), 30)
		effects.particles("heal", views[p].impact_point(), 8, 360.0)
		views[p].flash(Color("#8ae05a"), 0.3)
		pulse_card(p, Color("#8ae05a"))


func _enemy_phase() -> void:
	_set_state(State.ENEMY)
	for e in model.enemy_turn_order():
		if not e.is_alive():
			continue
		if model.all_players_dead():
			break
		await get_tree().create_timer(0.15, false).timeout
		await _check_phase2(e)
		var act := EnemyAI.decide(e, model)
		match act["type"]:
			"charge":
				await _start_charge(e, act["skill_id"])
			"summon":
				await _summon(e)
			_:
				var sk := Database.get_skill(act["skill_id"])
				if act["target"] == null and sk.get("target", "enemy_single") in ["enemy_single", "enemy_all"]:
					break
				await executor.execute(model.plan_action(e, act["skill_id"], act["target"]))
		if model.all_players_dead():
			break
		if model.all_enemies_dead():
			break
	if model.all_players_dead():
		await get_tree().create_timer(0.6, false).timeout
		_finish(false)
		return
	await _end_round()


## Telegraph: the enemy glows and a WARNING band tells the player what is coming.
func _start_charge(e: Combatant, skill_id: String) -> void:
	model.begin_charge(e, skill_id)
	var v: BattleUnitView = views.get(e)
	var skill_name: String = Database.get_skill(skill_id).get("name", "a powerful attack")
	hud.add_log("%s is charging %s! Guard to halve the damage." % [e.display_name, skill_name], Color("#ffb04a"))
	if v:
		v.anticipate(Color("#ffcf4a"), 0.5)
		effects.particles(e.element, v.impact_point(), 16, 360.0)
	await hud.show_warning("WARNING", "%s is charging %s!" % [e.display_name, skill_name])
	if not _warned_charge and not GameManager.hint_seen("charge") and not SceneRouter.params.get("skip_hints", false) \
			and Database.hints.has("charge"):
		_warned_charge = true
		await hud.show_hint(Database.hints["charge"])
		GameManager.mark_hint_seen("charge")


## Boss phase 2: announcement, enrage flash and (optionally) a queued skill.
func _check_phase2(e: Combatant) -> void:
	var p2 := model.check_phase2(e)
	if p2.is_empty():
		return
	var v: BattleUnitView = views.get(e)
	AudioManager.play_sfx("boss_sting")
	if v:
		v.flash(Color("#ff5a3a"), 0.6)
		effects.ring(v.global_position, Color("#ff7a4a"), 320, 0.6, 16, 0.5)
		effects.particles(e.element, v.impact_point(), 30, 360.0)
	camera.shake(18.0, 0.4)
	hud.add_log(p2.get("announce", "%s grows furious!" % e.display_name), Color("#ff7a5a"))
	await hud.show_warning("ENRAGED", p2.get("announce", ""))


## A boss calls minions: they rise in front of it.
func _summon(boss: Combatant) -> void:
	var bv: BattleUnitView = views.get(boss)
	if bv:
		bv.anticipate(Database.element_color(boss.element).lightened(0.3), 0.4)
		bv.play_anim(bv.resolve_anim("special"))
	AudioManager.play_sfx("summon_charge", 0.05, -4.0)
	await get_tree().create_timer(0.4, false).timeout
	var spawned := model.summon_minions(boss)
	for m in spawned:
		var pos := _enemy_pos(m)
		var v := _spawn_view(m, pos)
		v.modulate.a = 0.0
		var tw := v.create_tween()
		tw.tween_property(v, "modulate:a", 1.0, 0.35)
		effects.particles(m.element, pos + Vector2(0, -40), 16, 360.0)
		effects.ring(pos, Database.element_color(m.element), 180, 0.4, 10, 0.35)
	if not spawned.is_empty():
		hud.add_log("%s calls for help! %s appears." % [boss.display_name, ", ".join(spawned.map(func(x): return x.display_name))],
				Color("#ffb0a0"))
		hud.set_enemies(model.alive(model.enemies))
		set_target(target)
	await get_tree().create_timer(0.5, false).timeout
	if bv:
		bv.play_idle()


## One-time tips for new mechanics met in a wave (healers, elites, charging...).
func _wave_hints() -> void:
	if SceneRouter.params.get("skip_hints", false):
		return
	var wanted: Array = []
	for e in model.enemies:
		if e.is_elite:
			wanted.append("elites")
	for hid in wanted:
		if Database.hints.has(hid) and not GameManager.hint_seen(hid):
			await hud.show_hint(Database.hints[hid])
			GameManager.mark_hint_seen(hid)


func _end_round() -> void:
	for ev in model.end_round():
		var unit: Combatant = ev["unit"]
		if not unit.is_alive():
			continue
		var v: BattleUnitView = views.get(unit)
		if ev["type"] == "hot":
			var healed := model.apply_hot(unit, int(ev["amount"]))
			if v and healed > 0:
				effects.particles("heal", v.impact_point(), 6, 360.0)
				effects.damage_number(v.impact_point() + Vector2(0, -60), healed, "heal", "REGEN")
				pulse_card(unit, Color("#8ae05a"))
			await get_tree().create_timer(0.12, false).timeout
			continue
		var dealt := model.apply_dot(unit, int(ev["amount"]))
		var poison: bool = ev["status"] == "poison"
		if v:
			effects.spawn("hit_nature" if poison else "hit_fire", v.impact_point(), false, 0.7)
			effects.particles("nature" if poison else "fire", v.impact_point(), 6)
			effects.damage_number(v.impact_point() + Vector2(0, -60), dealt, "dot", "POISON" if poison else "BURN")
			hud.add_log("%s suffers %d %s damage." % [unit.display_name, dealt, "poison" if poison else "burn"],
					Color("#c08aff") if poison else Color("#ffa04a"))
			if unit.is_alive():
				v.hit_react()
			else:
				v.play_defeat()
				on_unit_defeated(unit)
		await get_tree().create_timer(0.25, false).timeout
	if model.all_players_dead():
		_finish(false)
		return
	if await _check_wave_end():
		return
	model.start_player_phase()
	_begin_player_phase()


func on_unit_defeated(c: Combatant) -> void:
	if c == target:
		_auto_target()
	if c == selected:
		selected = model.first_ready_player()
	_refresh_hud()


func _finish(victory: bool) -> void:
	if state == State.RESULT:
		return
	_set_state(State.RESULT)
	if _coach:
		_coach.finish()
		_coach = null
	set_target(null)
	set_battle_speed(1.0, false)
	var result := BattleResult.new()
	_result = result
	if victory:
		for p in model.players:
			views[p].play_victory()
		AudioManager.play_sting("victory")
		model.roll_stage_drops()
		result_summary = GameManager.apply_battle_result(stage_id, model.victory_data())
		await hud.show_banner("VICTORY", UIKit.GOLD, 0.7, "victory")
		hud.root.add_child(result)
		result.show_victory(result_summary, not GameManager.next_stage_id(stage_id).is_empty())
	else:
		AudioManager.play_sting("defeat")
		GameManager.record_defeat()
		hud.root.add_child(result)
		result.show_defeat()
	result.next_pressed.connect(func():
		var next_id := GameManager.next_stage_id(stage_id)
		SceneRouter.leave_battle(_map_scene(), {"highlight": next_id if not next_id.is_empty() else stage_id}))
	result.retry_pressed.connect(func():
		var r: Dictionary = GameManager.try_start_stage(stage_id)
		if r["ok"]:
			SceneRouter.go("battle", {"stage_id": stage_id})
		else:
			EnergyPopup.open(hud.root, stage_id))
	result.party_pressed.connect(func():
		SceneRouter.push_entry(_map_scene(), {"highlight": stage_id, "prepare": true})
		if GameManager.feature_unlocked("squad"):
			SceneRouter.go("squad", {"return_to": _map_scene(), "stage_id": stage_id}, "replace")
		else:
			SceneRouter.go("unit_detail", {"uid": GameManager.leader_uid()}, "replace"))
	result.stage_select_pressed.connect(func(): SceneRouter.leave_battle(_map_scene(), {"highlight": stage_id}))
	battle_finished.emit(victory)


func _on_menu() -> void:
	if state != State.PLAYER:
		return
	hud.show_menu(func(): SceneRouter.leave_battle(_map_scene(), {"highlight": stage_id}))


## Called before the game quits: stop auto-play so the battle settles.
func prepare_quit() -> void:
	hud.set_auto(false)
	_quitting = true


## True when no action / animation coroutine is running.
func is_idle() -> bool:
	if state == State.PLAYER:
		return not _auto_pending
	if state == State.RESULT:
		return _result == null or not is_instance_valid(_result) or _result.sequence_done
	return false


var _quitting := false
var _result: BattleResult


func _map_scene() -> String:
	return "tower" if Database.is_tower_stage(stage_id) else "stage_select"


# ------------------------------------------------------------------ helpers
func _update_loot() -> void:
	var drops := 0
	for k in model.items_earned.keys():
		drops += int(model.items_earned[k])
	hud.set_loot(model.gold_earned, drops)



## Brief global freeze on heavy impacts (skipped when Battle Effects are off).
var _stop_depth := 0


func hit_stop(duration: float) -> void:
	if duration <= 0.0 or not bool(GameManager.settings.get("battle_effects", true)):
		return
	_stop_depth += 1
	Engine.time_scale = 0.05 * battle_speed
	await get_tree().create_timer(duration / battle_speed, true, false, true).timeout
	_stop_depth -= 1
	if _stop_depth <= 0:
		_stop_depth = 0
		Engine.time_scale = battle_speed


## 1x / 2x battle speed (scales every animation, tween and timer in the battle).
func set_battle_speed(v: float, update_hud := true) -> void:
	battle_speed = 2.0 if v >= 1.5 else 1.0
	if _stop_depth <= 0:
		Engine.time_scale = battle_speed
	if update_hud:
		hud.set_speed(battle_speed)


func _exit_tree() -> void:
	Engine.time_scale = 1.0


# ------------------------------------------------------------------ auto battle
var _auto_pending := false


func _popup_open() -> bool:
	for ch in hud.root.get_children():
		if ch is FantasyPopup:
			return true
	return false


## Auto Battle: picks sensible actions for the next ready hero (Bursts when useful,
## Guards against charged attacks, element-advantage targets). Tap AUTO to stop.
func _auto_step() -> void:
	if not hud.auto_on or state != State.PLAYER or _auto_pending or _quitting:
		return
	_auto_pending = true
	await get_tree().create_timer(0.3, false).timeout
	_auto_pending = false
	if not hud.auto_on or state != State.PLAYER or _popup_open():
		if hud.auto_on and state == State.PLAYER:
			get_tree().create_timer(0.5, false).timeout.connect(_auto_step)
		return
	var u := model.first_ready_player()
	if u == null:
		return
	var charging := false
	for e in model.alive(model.enemies):
		charging = charging or not e.charging_skill.is_empty()
	var lowest := 1.0
	for p in model.alive(model.players):
		lowest = minf(lowest, p.hp_ratio())
	var support: bool = Database.get_skill(u.burst_skill).get("target", "") == "ally_all"
	var best: Combatant = null
	var best_score := -INF
	for f in model.alive(model.enemies):
		var score: float = Database.element_multiplier(u.element, f.element) * 1000.0 - f.hp_ratio() * 300.0
		if f.is_boss:
			score -= 150.0
		if score > best_score:
			best_score = score
			best = f
	if best:
		set_target(best)
	if u.burst_ready() and (not support or lowest < 0.65 or charging):
		request_action("burst", u)
	elif charging and u.hp_ratio() < 0.5:
		request_action("guard", u)
	else:
		request_action("attack", u)


## Quick colour pulse on a hero's battle card (heals, buffs, recovery).
func pulse_card(c: Combatant, color: Color) -> void:
	var card: PartyCard = hud.cards.get(c)
	if card == null:
		return
	var tw := card.create_tween()
	tw.tween_property(card.frame, "modulate", color.lightened(0.4), 0.1)
	tw.tween_property(card.frame, "modulate", Color.WHITE, 0.3)


func set_dim(on: bool) -> void:
	dim.visible = true
	var tw := create_tween()
	tw.tween_property(dim, "color:a", 0.45 if on else 0.0, 0.2)
	if not on:
		tw.tween_callback(func(): dim.visible = false)


func _refresh_hud() -> void:
	var can_input := state == State.PLAYER
	hud.refresh(can_input, selected)
	for c in views.keys():
		if c.is_player:
			views[c].set_selected(can_input and c == selected)


func _unhandled_input(event: InputEvent) -> void:
	if state != State.PLAYER:
		return
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		var world_pos := get_global_mouse_position()
		for c in views.keys():
			if not c.is_player and c.is_alive() and views[c].hit_rect().has_point(world_pos):
				set_target(c)
				AudioManager.play_sfx("target", 0.05, -4.0)
				_coach_progress("target")
				get_viewport().set_input_as_handled()
				return
	elif event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_A:
				request_action("attack")
			KEY_B:
				request_action("burst")
			KEY_G:
				request_action("guard")
			KEY_TAB, KEY_RIGHT, KEY_LEFT:
				_cycle_target(1 if event.keycode != KEY_LEFT else -1)
			KEY_1, KEY_2, KEY_3, KEY_4, KEY_5:
				var idx: int = event.keycode - KEY_1
				if idx < model.players.size():
					_on_unit_selected(model.players[idx])


func _cycle_target(dir: int) -> void:
	var living := model.alive(model.enemies)
	if living.is_empty():
		return
	var i := living.find(target)
	set_target(living[(i + dir + living.size()) % living.size()])
