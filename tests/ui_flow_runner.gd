extends Node
## Plays through the FIRST MILESTONE using simulated mouse clicks on the real UI.
## phase 1: New Game -> starter -> Stage 1 (attacks + Burst) -> Victory -> Stage 2 -> quit
## phase 2: Continue -> verify restored progress -> Stage 2 burst after load -> quit

var args: Dictionary = {}
var shots_dir := "user://shots/"
var failures: PackedStringArray = []
var log_lines: PackedStringArray = []


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		var kv := a.trim_prefix("--").split("=")
		if kv.size() == 2:
			args[kv[0]] = kv[1]
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(shots_dir))
	SaveManager.save_path = "user://flow_test_save.json"
	await _wait(0.8)
	match args.get("phase", "1"):
		"1":
			await _phase1()
		"2":
			await _phase2()
		"4":
			await _phase4()
		_:
			await _phase3()
	for l in log_lines:
		print(l)
	if failures.is_empty():
		print("UI FLOW PHASE %s: PASS" % args.get("phase", "1"))
		GameManager.quit_game(0)
	else:
		for f in failures:
			print("FAIL: ", f)
		GameManager.quit_game(1)


# ------------------------------------------------------------------ phases
func _phase1() -> void:
	SaveManager.delete_profile()
	_check(get_tree().current_scene.name == "MainMenu", "main menu is the first scene")
	await _shot("m01_main_menu")
	await _click_text("NEW GAME")
	await _wait(0.8)
	_check(get_tree().current_scene.name == "StarterSelect", "starter select opened")
	var starter: String = args.get("starter", "kael_emberclaw")
	var def := Database.get_character(starter)
	# tap the starter card (its label shows the first name)
	await _click_node(_find_card_for(def["name"].split(" ")[0], true))
	await _wait(0.3)
	await _shot("m02_starter_select")
	await _click_text("SKILLS")
	await _wait(0.3)
	await _shot("m03_view_skills")
	await _click_text("CLOSE")
	await _click_text("SELECT")
	await _wait(0.3)
	_check(_find_label_containing("Begin your journey with %s?" % def["name"]) != null, "confirmation text shown")
	await _shot("m04_confirm")
	await _click_text("CONFIRM")
	await _wait(0.9)
	_check(get_tree().current_scene.name == "Intro", "intro/tutorial opened")
	await _shot("m05_intro")
	await _click_text("SKIP")
	await _wait(0.9)
	_check(get_tree().current_scene.name == "StageSelect", "stage select opened")
	_check(GameManager.party_units().size() == 1 and GameManager.party_units()[0]["char_id"] == starter, "starter is in the party")
	await _shot("m06_stage_select")
	await _click_node(_find_named("Node_ashroot_01"))
	await _wait(0.4)
	_check(_find_label_exact("First Steps") != null, "stage sheet shows the selected stage")
	await _shot("m06b_briefing")
	await _click_text("START")
	await _wait(0.5)
	_check(_find_named("PreparePopup") != null, "PREPARE popup opened")
	await _shot("m06c_prepare")
	var energy_before := GameManager.energy()
	await _click_text("DEPART")
	await _wait(1.6)
	_check(GameManager.energy() == energy_before - GameManager.stage_energy("ashroot_01"), "departing spent energy")
	var battle = get_tree().current_scene
	_check(battle is BattleController, "battle scene loaded")
	await _shot("m07_battle_hint")
	await _click_text("GOT IT")
	var used_burst := await _fight(battle, true)
	_check(used_burst, "used the Burst in stage 1")
	_check(battle.state == BattleController.State.RESULT, "battle reached result state")
	await _wait(3.0)
	await _shot("m09_victory")
	_check(_find_label_containing("VICTORY") != null, "victory screen shown")
	_check(GameManager.gold() > 0, "gold gained (%d)" % GameManager.gold())
	var u: Dictionary = GameManager.party_units()[0]
	_check(int(u["level"]) > 1 or int(u["exp"]) > 0, "xp gained")
	log_lines.append("after stage1: level=%d exp=%d gold=%d items=%s" % [u["level"], u["exp"], GameManager.gold(), GameManager.profile["inventory"]])
	await _click_text("CONTINUE")
	await _wait(1.0)
	_check(get_tree().current_scene.name == "StageSelect", "returned to stage menu")
	_check(GameManager.is_stage_unlocked("ashroot_02"), "stage 2 unlocked")
	await _shot("m10_stage_select_after")
	await _click_node(_find_named("Node_ashroot_02"))
	await _wait(0.3)
	await _click_text("START")
	await _wait(0.4)
	await _click_text("DEPART")
	await _wait(1.6)
	battle = get_tree().current_scene
	_check(battle is BattleController and battle.stage_id == "ashroot_02", "entered stage 2")
	await _click_text("GOT IT")
	await _wait(0.5)
	await _shot("m11_stage2")
	# "Close the game" happens here: quit without touching anything else.


func _phase2() -> void:
	_check(get_tree().current_scene.name == "MainMenu", "main menu after reopen")
	var cont := _find_button("CONTINUE")
	_check(cont != null and not cont.disabled, "CONTINUE enabled")
	await _click_text("CONTINUE")
	await _wait(0.9)
	_check(get_tree().current_scene.name == "Home", "home opened")
	await _shot("m12_home_restored")
	var starter: String = args.get("starter", "kael_emberclaw")
	_check(GameManager.profile.get("starter_id") == starter, "starter restored")
	_check(GameManager.is_stage_cleared("ashroot_01"), "stage 1 still cleared")
	_check(GameManager.is_stage_unlocked("ashroot_02"), "stage 2 still unlocked")
	_check(GameManager.gold() > 0, "gold restored (%d)" % GameManager.gold())
	var u: Dictionary = GameManager.party_units()[0]
	log_lines.append("restored: level=%d exp=%d gold=%d" % [u["level"], u["exp"], GameManager.gold()])
	_check(int(u["level"]) >= 2, "unit level restored")
	# Screens (UNITS / SQUAD / SUMMON are still locked this early)
	var units_tile := _find_named("UnitsButton")
	_check(units_tile != null and units_tile.get_node_or_null("Badge") == null, "units tile present")
	await _click_node(units_tile)
	await _wait(0.3)
	_check(_find_label_containing("unlocks after clearing") != null, "locked units tile explains where it unlocks")
	GameManager.profile["stages"]["cleared"].append("ashroot_05")      # jump ahead: units + squad unlocked
	GameManager.save()
	SceneRouter.go("home")
	await _wait(1.2)
	var ok := _find_button("OK")
	if ok:
		await _click_node(ok)
		await _wait(0.4)
	await _click_node(_find_named("UnitsButton"))
	await _wait(0.8)
	await _shot("m13_units")
	await _click_node(_find_named("UnitTile_" + GameManager.party_uids()[0]))
	await _wait(0.8)
	_check(get_tree().current_scene.name == "UnitDetail", "unit detail opened")
	await _shot("m14_unit_detail")
	await _click_text("SQUAD")
	await _wait(0.9)
	_check(get_tree().current_scene.name == "Squad", "squad editor opened")
	await _shot("m15_party")
	await _click_node(_find_named("Slot_0"))
	await _wait(0.2)
	await _click_text("BACK")
	await _wait(0.9)
	_check(get_tree().current_scene.name == "UnitDetail", "squad BACK returns to unit detail")
	await _click_text("BACK")
	await _wait(0.9)
	await _click_text("BACK")
	await _wait(0.9)
	_check(get_tree().current_scene.name == "Home", "back to home")
	await _click_node(_find_named("ItemsButton"))
	await _wait(0.9)
	_check(get_tree().current_scene.name == "Inventory", "inventory opened")
	await _shot("m16_inventory")
	await _click_text("BACK")
	await _wait(0.9)
	var sealed := _find_named("SummonButton")
	_check(sealed != null, "summon tile shown (locked)")
	await _click_node(sealed)
	await _wait(0.3)
	_check(_find_label_containing("unlocks after clearing") != null, "locked feature explains itself")
	await _shot("m17_locked")
	await _click_node(_find_named("QuestButton"))
	await _wait(0.9)
	await _shot("m17b_quest")
	await _click_node(_find_named("Node_ashroot_02"))
	await _wait(0.3)
	await _click_text("START")
	await _wait(0.4)
	await _click_text("DEPART")
	await _wait(1.6)
	var battle = get_tree().current_scene
	_check(battle is BattleController and battle.stage_id == "ashroot_02", "stage 2 battle after load")
	var hint := _find_button("GOT IT")
	if hint:
		await _click_node(hint)
	# a bigger squad can win before any gauge fills naturally: pre-charge the leader
	battle.model.players[0].add_burst(100)
	var used := await _fight(battle, false)
	_check(used, "burst works after loading a save")
	log_lines.append("stage 2 result state=%s" % BattleController.State.keys()[battle.state])


## Settings + corrupted save handling through the real menu.
func _phase3() -> void:
	SaveManager.save_path = "user://flow_test_save_p3.json"
	await _click_text("SETTINGS")
	await _wait(0.4)
	await _shot("m18_settings")
	var sliders: Array = _all_nodes(get_tree().root, []).filter(func(n): return n is HSlider)
	_check(sliders.size() == 3, "three volume sliders")
	if sliders.size() == 3:
		sliders[1].value = 0.25
		_check(is_equal_approx(float(GameManager.settings["music_volume"]), 0.25), "music volume applied")
		_check(is_equal_approx(float(SaveManager.load_settings()["music_volume"]), 0.25), "settings saved")
		sliders[1].value = 0.6
	await _click_text("CLOSE")
	# corrupt both save files, then reload the menu
	for path in [SaveManager.save_path, SaveManager.save_path + ".bak"]:
		var f := FileAccess.open(path, FileAccess.WRITE)
		f.store_string("corrupted!!")
		f.close()
	GameManager.profile = {}
	SaveManager.load_profile()
	get_tree().change_scene_to_file("res://scenes/ui/main_menu.tscn")
	await _wait(0.8)
	_check(_find_label_containing("could not be read") != null, "corruption message shown")
	var cont := _find_button("CONTINUE")
	_check(cont != null and cont.disabled, "CONTINUE disabled for corrupted save")
	await _shot("m19_corrupted")
	await _click_text("OK")
	await _click_text("NEW GAME")
	await _wait(0.8)
	_check(get_tree().current_scene.name == "StarterSelect", "new game still possible")


## Phase 4 player flow: auto battle + 2x, unlock announcements, gift hero,
## Embergate summon (ceremony, results, NEW hero -> squad), training with wisps,
## evolution (OBTAINED FROM -> GO), towers, missions + login, inventory tabs,
## codex, profile, World 2 tab, squad editing from PREPARE and the energy popup.
func _phase4() -> void:
	SaveManager.save_path = "user://flow_test_save_p4.json"
	SaveManager.delete_profile()
	GameManager.set_setting("auto_battle", false)
	GameManager.set_setting("battle_speed", 1.0)
	await _click_text("NEW GAME")
	await _wait(0.8)
	await _click_node(_find_card_for("Mira", true))
	await _click_text("SELECT")
	await _click_text("CONFIRM")
	await _wait(0.9)
	await _click_text("SKIP")
	await _wait(1.0)
	# the battle tutorial (coach marks) is covered by phase 1
	for step in ["tap_attack", "burst", "target"]:
		GameManager.mark_coach_done(step)
	# clear 1-1 .. 1-4 quickly (battles are covered by phases 1/2)
	for i in range(1, 5):
		GameManager.apply_battle_result("ashroot_%02d" % i, {"xp": 150, "gold": 60, "items": {}, "stars": [true, true, true]})
	_check(GameManager.feature_unlocked("auto"), "auto battle unlocked after 1-4")
	_check(GameManager.energy() > 0, "energy available")
	# ---- 1-5 with AUTO + 2x through the real UI
	SceneRouter.go("stage_select", {"highlight": "ashroot_05"})
	await _wait(1.2)
	await _shot("p4_01_stage_sheet")
	_check(_find_named("StarObjectives") != null and _find_named("PossibleDrops") != null, "stage sheet shows stars + possible drops")
	await _click_text("START")
	await _wait(0.4)
	await _shot("p4_02_prepare")
	await _click_text("DEPART")
	await _wait(1.8)
	var battle = get_tree().current_scene
	_check(battle is BattleController, "1-5 battle started")
	var hint := await _wait_for_button("GOT IT", 6.0)
	if hint:
		await _click_node(hint)
		await _wait(0.4)
	await _click_node(_find_named("SpeedButton"))
	await _wait(0.2)
	_check(is_equal_approx(Engine.time_scale, 2.0) or battle.battle_speed == 2.0, "2x speed on")
	await _click_node(_find_named("AutoButton"))
	_check(battle.hud.auto_on, "auto battle on")
	await _wait(1.0)
	await _shot("p4_03_auto_battle")
	var t := 0.0
	while battle.state != BattleController.State.RESULT and t < 200.0:
		var gi := _find_button("GOT IT")
		if gi:
			await _click_node(gi)
		await _wait(0.25)
		t += 0.25
	_check(battle.state == BattleController.State.RESULT, "auto battle finished the stage")
	await _wait(2.5)
	await _shot("p4_04_victory")
	_check(GameManager.is_stage_cleared("ashroot_05"), "1-5 cleared by auto battle")
	_check(GameManager.owned_units().size() == 2, "gift hero received at 1-5")
	_check(GameManager.party_uids().size() == 2, "gift hero joined the squad")
	await _finish_result()
	await _wait(1.0)
	GameManager.set_setting("auto_battle", false)
	GameManager.set_setting("battle_speed", 1.0)
	# ---- home: feature announcements
	SceneRouter.go("home")
	await _wait(1.6)
	if _find_named("LoginPopup"):
		await _shot("p4_05a_login")
		await _click_node(_find_named("ClaimLoginPopup"))
		await _wait(0.8)
		await _click_node(_find_named("RewardOK"))
		await _wait(0.8)
	await _shot("p4_05_home_unlock")
	_check(_find_named("FeaturePopup") != null, "feature unlock announced on home")
	await _dismiss_home_popups()
	# ---- clear up to 1-9 for training / tower / evolution / summon
	for i in range(6, 10):
		GameManager.apply_battle_result("ashroot_%02d" % i, {"xp": 300, "gold": 200, "items": {}, "stars": [true, false, false]})
	GameManager.add_gems(1200)
	SceneRouter.go("home")
	await _wait(1.6)
	await _dismiss_home_popups()
	await _shot("p4_06_home")
	_check(_find_named("FeatureGrid") != null, "home feature grid")
	# ---- summon
	await _click_node(_find_named("SummonButton"))
	await _wait(1.2)
	_check(get_tree().current_scene.name == "Summon", "summon screen opened")
	await _shot("p4_07_summon")
	await _click_node(_find_named("SummonDetails"))
	await _wait(0.4)
	await _shot("p4_08_summon_details")
	_check(_find_label_containing("75%") != null and _find_label_containing("3%") != null, "rates shown in details")
	await _click_text("CLOSE")
	await _wait(0.4)
	var gems_before := GameManager.gems()
	await _click_node(_find_named("SummonOne"))
	await _wait(0.3)
	await _click_text("SUMMON")
	await _wait(0.2)
	_check(GameManager.gems() == gems_before - 100, "single summon cost 100 gems")
	_check(_find_named("SkipSummon") == null, "no SKIP on the very first summon")
	await _wait(2.2)
	await _shot("p4_09_summon_reveal")
	var tries := 0
	while _find_named("SummonResults") == null and tries < 40:
		var cer := _find_named("SummonCeremony")
		if cer:
			await _click_node(cer)
		await _wait(0.4)
		tries += 1
	_check(_find_named("SummonResults") != null, "summon results shown")
	await _shot("p4_10_summon_results")
	var add := _find_named("NewHeroAdd")
	if add:
		await _click_node(add)
		await _wait(0.3)
	await _click_node(_find_named("ResultsContinue"))
	await _wait(0.4)
	await _click_node(_find_named("SummonTen"))
	await _wait(0.3)
	await _click_text("SUMMON")
	await _wait(0.6)
	_check(_find_named("SkipSummon") != null, "SKIP offered after the first summon")
	await _click_node(_find_named("SkipSummon"))
	await _wait(0.8)
	_check(_find_named("SummonResults") != null, "10x results shown after SKIP")
	await _shot("p4_11_summon_ten")
	await _click_node(_find_named("ResultsContinue"))
	await _wait(0.3)
	_check(GameManager.profile["codex"].size() >= 3, "codex grew from summons")
	# ---- training
	var uid: String = GameManager.party_uids()[0]
	GameManager.add_item("radiant_wisp", 5)
	GameManager.add_gold(50000)
	SceneRouter.go("unit_detail", {"uid": uid})
	await _wait(1.2)
	await _shot("p4_12_unit_detail")
	await _click_node(_find_named("TrainButton"))
	await _wait(0.4)
	_check(_find_named("TrainPopup") != null, "train popup opened")
	await _click_node(_find_named("AutoSelect"))
	await _wait(0.3)
	await _shot("p4_13_train_preview")
	var lvl_before := int(GameManager.get_unit(uid)["level"])
	await _click_node(_find_named("ConfirmTrain"))
	await _wait(0.6)
	_check(int(GameManager.get_unit(uid)["level"]) > lvl_before, "training raised the level")
	await _click_text("OK")
	# ---- evolution
	var u := GameManager.get_unit(uid)
	u["level"] = int(Database.get_character(u["char_id"])["max_level"])
	var st := GameManager.evolution_status(uid)
	for m in st["materials"].keys():
		GameManager.add_item(m, int(st["materials"][m]))
	SceneRouter.go("evolve", {"uid": uid})
	await _wait(1.2)
	await _shot("p4_14_evolve")
	var first_mat: String = st["materials"].keys()[0]
	await _click_node(_find_named("Source_" + first_mat))
	await _wait(0.4)
	await _shot("p4_15_obtained_from")
	_check(_find_named("ItemSourcesPopup") != null, "OBTAINED FROM popup")
	await _click_text("GO")
	await _wait(1.2)
	var sc := get_tree().current_scene.name
	_check(sc == "StageSelect" or sc == "Tower", "GO navigated to a source (%s)" % sc)
	SceneRouter.go("evolve", {"uid": uid})
	await _wait(1.2)
	var old_form: String = GameManager.get_unit(uid)["char_id"]
	await _click_node(_find_named("ConfirmEvolve"))
	await _wait(0.3)
	await _click_text("EVOLVE")
	await _wait(2.5)
	await _shot("p4_16_evolved")
	_check(GameManager.get_unit(uid)["char_id"] == st["into"] and old_form != st["into"], "hero evolved")
	await _click_node(_find_named("EvolveContinue"))
	await _wait(1.2)
	_check(get_tree().current_scene.name == "UnitDetail", "back to the evolved hero")
	# ---- tower
	SceneRouter.go("tower")
	await _wait(1.2)
	await _shot("p4_17_tower")
	_check(get_tree().current_scene.name == "Tower", "tower opened")
	await _click_text("START")
	await _wait(0.4)
	await _click_text("DEPART")
	await _wait(1.8)
	battle = get_tree().current_scene
	_check(battle is BattleController and Database.is_tower_stage(battle.stage_id), "tower floor battle")
	GameManager.set_setting("auto_battle", true)
	battle.hud.set_auto(true, true)
	t = 0.0
	while battle.state != BattleController.State.RESULT and t < 200.0:
		var gi := _find_button("GOT IT")
		if gi:
			await _click_node(gi)
		await _wait(0.25)
		t += 0.25
	await _wait(2.5)
	_check(GameManager.tower_highest_floor("ember_tower") >= 1, "tower floor 1 cleared")
	if battle.state == BattleController.State.RESULT and GameManager.tower_highest_floor("ember_tower") >= 1:
		await _finish_result()
		await _wait(1.2)
		_check(get_tree().current_scene.name == "Tower", "tower victory returns to the tower")
	GameManager.set_setting("auto_battle", false)
	# ---- missions + login
	GameManager.apply_battle_result("ashroot_10", {"xp": 400, "gold": 300, "items": {}, "stars": [true, true, true]})
	GameManager.track("stage_clear", 5)
	SceneRouter.go("missions")
	await _wait(1.2)
	await _shot("p4_18_missions")
	var gold_before := GameManager.gold()
	var claim := _find_named("Claim_d_stages")
	await _click_node(claim)
	await _wait(0.4)
	_check(GameManager.gold() > gold_before, "mission reward claimed")
	await _click_text("OK")
	await _click_node(_find_named("Tab_LOGIN"))
	await _wait(0.4)
	await _shot("p4_19_login")
	# ---- inventory / codex / profile
	SceneRouter.go("inventory")
	await _wait(1.2)
	await _click_node(_find_named("Tab_TRAINING"))
	await _wait(0.3)
	await _shot("p4_20_inventory")
	await _click_node(_find_named("Tab_OTHER"))
	await _wait(0.3)
	_check(_find_named("Currency_SoulShards") != null, "currencies tab")
	SceneRouter.go("codex")
	await _wait(1.2)
	await _shot("p4_21_codex")
	_check(_find_label_containing("OWNED") != null, "codex count shown")
	SceneRouter.go("profile")
	await _wait(1.2)
	await _shot("p4_22_profile")
	# ---- world 2 + squad from prepare + energy popup
	SceneRouter.go("stage_select", {"world": "saltglass_reach"})
	await _wait(1.2)
	await _shot("p4_23_world2")
	_check(_find_label_containing("SALTGLASS") != null, "world 2 map")
	await _click_text("START")
	await _wait(0.4)
	await _click_node(_find_named("EditSquad"))
	await _wait(1.2)
	_check(get_tree().current_scene.name == "Squad", "edit squad from prepare")
	await _shot("p4_24_squad")
	await _click_text("BACK")
	await _wait(1.4)
	_check(_find_named("PreparePopup") != null, "back from squad reopens PREPARE")
	GameManager.profile["player"]["energy"] = 0
	GameManager.profile["player"]["energy_ts"] = int(GameManager.now())
	await _click_text("DEPART")
	await _wait(0.5)
	_check(_find_label_containing("NOT ENOUGH ENERGY") != null or _find_label_containing("need") != null, "energy popup instead of a dead end")
	await _shot("p4_25_energy")
	await _click_text("OK")


## Waits for the victory sequence (dismissing RANK UP) and presses CONTINUE.
func _finish_result() -> bool:
	var t := 0.0
	while t < 15.0:
		var rk := _find_named("RankUpOK")
		if rk:
			await _click_node(rk)
			await _wait(0.4)
		var c := _find_named("ContinueButton") as Button
		if c and not c.disabled and _find_named("RankUpOverlay") == null:
			await _click_node(c)
			return true
		await _wait(0.25)
		t += 0.25
	failures.append("victory CONTINUE never became available")
	return false


func _dismiss_home_popups() -> void:
	for i in 10:
		var target: Control = null
		for n in ["ClaimLoginPopup", "RewardOK", "FeatureOK"]:
			target = _find_named(n)
			if target:
				break
		if target == null:
			var ok := _find_button("OK")
			if ok == null:
				return
			target = ok
		await _click_node(target)
		await _wait(0.7)


## Fights using real button clicks. Returns true if a Burst was used.
func _fight(battle, shot_burst: bool) -> bool:
	var used_burst := false
	var t := 0.0
	var shot_taken := false
	while battle.state != BattleController.State.RESULT and t < 240.0:
		if battle.state == BattleController.State.PLAYER:
			var unit: Combatant = battle.model.first_ready_player()
			var card: PartyCard = battle.hud.cards.get(unit)
			if unit and unit.burst_ready():
				await _swipe(card, -160.0)
				used_burst = true
				if shot_burst:
					await _wait(0.7)
					await _shot("m08_burst")
			elif card:
				# rapid tapping: several taps in a row must only trigger one action
				await _click_node(card)
				await _click_node(card)
				await _click_node(card)
				if not shot_taken:
					shot_taken = true
					await _wait(0.5)
					await _shot("m07b_attack")
		await _wait(0.1)
		t += 0.1
	return used_burst


# ------------------------------------------------------------------ helpers
func _check(cond: bool, what: String) -> void:
	if cond:
		log_lines.append("ok   - " + what)
	else:
		failures.append(what)
		log_lines.append("FAIL - " + what)


func _wait(t: float) -> void:
	await get_tree().create_timer(t).timeout


func _shot(name: String) -> void:
	if DisplayServer.get_name() == "headless":
		return
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(ProjectSettings.globalize_path(shots_dir + args.get("prefix", "") + name + ".png"))


func _all_nodes(n: Node, out: Array) -> Array:
	out.append(n)
	for c in n.get_children():
		_all_nodes(c, out)
	return out


func _find_button(text: String) -> Button:
	var found: Button = null
	for n in _all_nodes(get_tree().root, []):
		if n is Button and n.text == text and n.is_visible_in_tree():
			found = n    # prefer the last (top-most, e.g. inside a modal)
	return found


func _find_label_containing(text: String) -> Control:
	for n in _all_nodes(get_tree().root, []):
		if n is Label and n.is_visible_in_tree() and n.text.contains(text):
			return n
	return null


func _find_named(node_name: String) -> Control:
	for n in _all_nodes(get_tree().root, []):
		if n is Control and n.name == node_name and n.is_visible_in_tree():
			return n
	return null


func _find_label_exact(text: String) -> Label:
	for n in _all_nodes(get_tree().root, []):
		if n is Label and n.is_visible_in_tree() and n.text == text:
			return n
	return null


## Real swipe gesture on a control (press, drag, release).
func _swipe(c: Control, dy: float) -> void:
	await get_tree().process_frame
	var local := c.size / 2.0
	var down := InputEventMouseButton.new()
	down.button_index = MOUSE_BUTTON_LEFT
	down.pressed = true
	down.position = local
	var up := down.duplicate()
	up.pressed = false
	up.position = local + Vector2(0, dy)
	if DisplayServer.get_name() == "headless":
		c.gui_input.emit(down)
		c.gui_input.emit(up)
	else:
		var xf: Transform2D = c.get_viewport().get_screen_transform() * c.get_global_transform_with_canvas()
		for ev in [down, up]:
			var e: InputEventMouseButton = ev.duplicate()
			e.position = xf * ev.position
			e.global_position = e.position
			if not e.pressed:
				var mv := InputEventMouseMotion.new()
				mv.position = e.position
				mv.global_position = e.position
				mv.button_mask = MOUSE_BUTTON_MASK_LEFT
				Input.parse_input_event(mv)
				await get_tree().process_frame
			Input.parse_input_event(e)
			await get_tree().process_frame
	await get_tree().process_frame


func _find_card_for(char_name: String, exact := false) -> Control:
	var l: Control = _find_label_exact(char_name) if exact else _find_label_containing(char_name)
	var n: Node = l
	while n and not (n is PanelContainer):
		n = n.get_parent()
	return n


func _wait_for_button(text: String, timeout: float = 5.0) -> Button:
	var t := 0.0
	while t < timeout:
		var b := _find_button(text)
		if b and not b.disabled and not SceneRouter.transitioning:
			return b
		await _wait(0.1)
		t += 0.1
	return null


func _click_text(text: String) -> void:
	var b := await _wait_for_button(text, 4.0)
	if b == null:
		failures.append("button not found: " + text)
		log_lines.append("FAIL - button not found: " + text)
		return
	await _click_node(b)


## Real mouse click at the centre of a control, through the viewport input path.
func _click_node(c: Control) -> void:
	if c == null:
		failures.append("click target missing")
		return
	await get_tree().process_frame
	if DisplayServer.get_name() == "headless":
		# no window to route mouse events through: emit the same signals a click would
		if c is BaseButton:
			if not c.disabled:
				c.pressed.emit()
		else:
			var ev := InputEventMouseButton.new()
			ev.button_index = MOUSE_BUTTON_LEFT
			ev.pressed = true
			ev.position = c.size / 2.0
			c.gui_input.emit(ev)
			var ev2: InputEventMouseButton = ev.duplicate()
			ev2.pressed = false
			c.gui_input.emit(ev2)
		await get_tree().process_frame
		return
	# scroll the control into view first, like a player would
	var sp: Node = c.get_parent()
	while sp and not (sp is ScrollContainer):
		sp = sp.get_parent()
	if sp:
		(sp as ScrollContainer).ensure_control_visible(c)
		await get_tree().process_frame
		await get_tree().process_frame
	var pos := c.get_global_rect().get_center()
	# convert canvas coordinates to viewport (window) coordinates
	var screen_pos: Vector2 = c.get_viewport().get_screen_transform() * c.get_global_transform_with_canvas() * (c.size / 2.0)
	var motion := InputEventMouseMotion.new()
	motion.position = screen_pos
	motion.global_position = screen_pos
	Input.parse_input_event(motion)
	var down := InputEventMouseButton.new()
	down.button_index = MOUSE_BUTTON_LEFT
	down.pressed = true
	down.position = screen_pos
	down.global_position = screen_pos
	Input.parse_input_event(down)
	await get_tree().process_frame
	var up := down.duplicate()
	up.pressed = false
	Input.parse_input_event(up)
	await get_tree().process_frame
	await get_tree().process_frame
