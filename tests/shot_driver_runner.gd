extends Node
## Plays a stage automatically and saves screenshots at key moments.
## args: --starter= --stage= --level= --prefix= --hints=0|1 --lose=0|1

var out_dir := "user://shots/"
var args: Dictionary = {}


func _ready() -> void:
	for a in OS.get_cmdline_user_args():
		var kv := a.trim_prefix("--").split("=")
		if kv.size() == 2:
			args[kv[0]] = kv[1]
	DirAccess.make_dir_recursive_absolute(ProjectSettings.globalize_path(out_dir))
	SaveManager.save_path = "user://shot_save.json"
	GameManager.new_game(args.get("starter", "kael_emberclaw"))
	GameManager.profile["units"][0]["level"] = int(args.get("level", "1"))
	for sid in Database.stage_order:
		GameManager.profile["stages"]["unlocked"].append(sid)
	await get_tree().create_timer(0.3).timeout
	SceneRouter.go("battle", {"stage_id": args.get("stage", "ashroot_01"), "skip_hints": args.get("hints", "0") == "0"})
	await get_tree().create_timer(1.0).timeout
	var battle = get_tree().current_scene
	if args.get("lose", "0") == "1":
		battle.model.players[0].hp = 1
	if args.get("skip_to_last_wave", "0") == "1":
		while battle.state != BattleController.State.PLAYER:
			await _wait(0.1)
		while battle.model.has_next_wave():
			if args.get("timeline", "0") == "1":
				_timeline("10_intro", 8, 0.35)
			for e in battle.model.enemies:
				battle.model.apply_dot(e, 999999)
				battle.views[e].play_defeat()
			battle.state = BattleController.State.BUSY
			await battle._after_player_action()
			await _wait(0.2)
	var shots := 0
	var enemy_shot := false
	var burst_shot := false
	var t := 0.0
	while battle.state != BattleController.State.RESULT and t < 400.0:
		if battle.state == BattleController.State.PLAYER:
			if shots == 0:
				await _wait(0.4)
				await _shot("01_start")
				shots += 1
			if battle.selected and battle.selected.burst_ready() and (not burst_shot or args.get("burst_always", "1") == "1"):
				battle.request_action("burst")
				if not burst_shot:
					burst_shot = true
					await _wait(0.6)
					await _shot("03_burst_cutin")
					for i in 3:
						await _wait(0.55)
						await _shot("04_burst_%d" % i)
			else:
				battle.request_action("attack")
				if shots == 1:
					await _wait(0.55)
					await _shot("02_attack")
					shots += 1
		elif battle.state == BattleController.State.ENEMY and not enemy_shot:
			enemy_shot = true
			await _wait(0.45)
			await _shot("05_enemy_turn")
		await _wait(0.05)
		t += 0.05
	await _wait(1.2)
	await _shot("06_result_a")
	await _wait(2.0)
	await _shot("06_result")
	print("RESULT victory=%s level=%d gold=%d" % [str(GameManager.is_stage_cleared(args.get("stage", "ashroot_01"))),
			GameManager.party_units()[0]["level"], GameManager.gold()])
	GameManager.quit_game(0)


## Captures `count` shots every `step` seconds without blocking the caller.
func _timeline(prefix: String, count: int, step: float) -> void:
	for i in count:
		await _wait(step)
		await _shot("%s_%d" % [prefix, i])


func _wait(t: float) -> void:
	await get_tree().create_timer(t).timeout


func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := get_viewport().get_texture().get_image()
	img.save_png(ProjectSettings.globalize_path(out_dir + args.get("prefix", "") + name + ".png"))
