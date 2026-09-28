extends Node
## Visual probe: builds a well-progressed profile, opens a screen and saves
## screenshots (dev tool for UI review, run windowed):
##   godot --resolution 540x960 res://tests/screen_probe.tscn -- --scene=summon --action=summon1 --shots=3 --gap=0.8
## --stage=  (battle stage id)  --progress=early|mid|late  --prefix=

var args: Dictionary = {}
var out_dir := "user://shots/"


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		var kv := a.trim_prefix("--").split("=")
		if kv.size() == 2:
			args[kv[0]] = kv[1]
	print("probe start")
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(out_dir))
	SaveManager.save_path = "user://probe_save.json"
	GameManager.new_game(args.get("starter", "kael_emberclaw"))
	var prog: String = args.get("progress", "late")
	var upto: int = {"early": 3, "mid": 9, "late": 14}[prog]
	for i in upto:
		GameManager.apply_battle_result(Database.stage_order[i], {"xp": 400, "gold": 300, "items": {}, "stars": [true, i % 2 == 0, i % 3 == 0]})
	GameManager.profile["tutorial"]["intro_seen"] = true
	GameManager.profile["login"]["last_date"] = GameManager._date_key()
	for f in ["auto", "units", "squad", "training", "tower", "evolution", "summon", "missions", "world2"]:
		GameManager.mark_feature_announced(f)
	if prog != "early":
		for cid in ["nerys_frostwake", "seraphine_pyrelance", "wren_briarshot"]:
			var uid := GameManager._add_unit(cid)
			if GameManager.party_uids().size() < 5:
				GameManager.toggle_party(uid)
		for it in ["ember_wisp", "tide_wisp", "radiant_wisp", "spark_sigil", "ember_fragment", "flame_core", "tide_fragment"]:
			GameManager.add_item(it, 4)
		GameManager.add_gems(1500)
		GameManager.profile["player"]["soul_shards"] = 45
		GameManager.track("stage_clear", 3)
	GameManager.save()
	await get_tree().create_timer(0.3).timeout
	var scene: String = args.get("scene", "home")
	var params := {}
	if args.has("stage"):
		params["stage_id"] = args["stage"]
		params["highlight"] = args["stage"]
		params["skip_hints"] = true
	if args.has("uid"):
		params["uid"] = args["uid"]
	if args.has("world"):
		params["world"] = args["world"]
	if scene == "unit_detail" or scene == "evolve":
		params["uid"] = GameManager.party_uids()[0]
		if scene == "evolve":
			GameManager.get_unit(params["uid"])["level"] = 15
	SceneRouter.go(scene, params)
	await get_tree().create_timer(1.3).timeout
	var cur = get_tree().current_scene
	match args.get("action", ""):
		"summon1":
			cur._do_summon(1)
		"summon10":
			cur._do_summon(10)
		"details":
			cur._open_details()
		"train":
			cur._open_train()
			await get_tree().create_timer(0.3).timeout
			cur._auto_select()
		"prepare":
			StageInfo.open_prepare(cur, args.get("stage", "ashroot_01"))
		"energy":
			EnergyPopup.open(cur, "ashroot_05")
		"rankup":
			RankUpOverlay.play(cur, [{"rank": 12, "energy_max_up": 1, "gems": 50}])
		"sources":
			ItemSources.open(cur, "flame_core")
		"auto":
			cur.hud.set_auto(true)
			cur._auto_step()
			cur.set_battle_speed(2.0)
		"lastwave":
			while cur.state != BattleController.State.PLAYER:
				await get_tree().create_timer(0.1).timeout
			while cur.model.has_next_wave():
				for e in cur.model.enemies:
					cur.model.apply_dot(e, 999999)
					cur.views[e].play_defeat()
				cur.state = BattleController.State.BUSY
				await cur._after_player_action()
				await get_tree().create_timer(0.2).timeout
			cur.hud.set_auto(true)
			cur._auto_step()
	if args.get("dump", "") == "badges":
		await get_tree().create_timer(0.5).timeout
		for nd in _all(get_tree().root, []):
			if nd.name == "Badge":
				print("BADGE parent=", nd.get_parent().name, " gpos=", nd.global_position, " size=", nd.size)
	var n := int(args.get("shots", "1"))
	for i in n:
		await get_tree().create_timer(float(args.get("gap", "0.8"))).timeout
		await RenderingServer.frame_post_draw
		var img := get_viewport().get_texture().get_image()
		img.save_png(ProjectSettings.globalize_path(out_dir + args.get("prefix", "probe_") + "%s_%d.png" % [scene, i]))
	GameManager.quit_game(0)


func _all(n: Node, out: Array) -> Array:
	out.append(n)
	for c in n.get_children():
		_all(c, out)
	return out
