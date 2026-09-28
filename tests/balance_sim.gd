extends Node
## Headless balance simulator (informational). Plays each starter through the
## story (World 1 + World 2) with a simple policy and a growing squad, grinding
## earlier stages / evolving when a stage is too hard, then samples the towers.
##   godot --headless res://tests/balance_sim.tscn
## Output per stage: win% at the moment it was attempted, squad levels and how many
## grinding replays were needed first (anti-softlock: grinding must always help).

const SAMPLES := 40


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	var only := ""
	var probe := ""
	var squad_arg := ""
	for a in args:
		if a.begins_with("--starter="):
			only = a.get_slice("=", 1)
		elif a.begins_with("--probe="):
			probe = a.get_slice("=", 1)
		elif a.begins_with("--squad="):
			squad_arg = a.get_slice("=", 1)
	if not probe.is_empty():
		# --probe=stage1,stage2 --squad=kael_emberclaw:10,mira_tidesong:8
		var squad: Array = []
		for part in squad_arg.split(","):
			squad.append({"uid": "u%d" % squad.size(), "char_id": part.get_slice(":", 0),
					"level": int(part.get_slice(":", 1)), "exp": 0, "burst_level": 1})
		for sid in probe.split(","):
			var rounds := 0.0
			var wins := 0
			for sd in SAMPLES:
				var r := simulate(sid, _copy(squad), sd * 7919 + 5)
				if r["win"]:
					wins += 1
					rounds += float(r.get("rounds", 0))
			print("%-16s win %3d%%  avg rounds %.1f" % [sid, wins * 100 / SAMPLES, rounds / maxf(wins, 1)])
		GameManager.quit_game(0)
		return
	for starter in Database.starter_ids():
		if only.is_empty() or only == starter:
			_run_starter(starter)
	GameManager.quit_game(0)


func _choose_target(user: Combatant, foes: Array) -> Combatant:
	var best: Combatant = null
	var best_score := -INF
	for f in foes:
		if not f.is_alive():
			continue
		var score: float = Database.element_multiplier(user.element, f.element) * 1000.0 - f.hp_ratio() * 300.0
		if f.is_boss:
			score -= 150.0      # clear adds first
		if score > best_score:
			best_score = score
			best = f
	return best


func _is_support(u: Combatant) -> bool:
	return Database.get_skill(u.burst_skill).get("target", "") == "ally_all"


func simulate(stage_id: String, units: Array, seed_value: int) -> Dictionary:
	var m := BattleModel.new()
	m.setup(stage_id, units, seed_value)
	var rounds := 0
	while true:
		var charging := false
		for e in m.alive(m.enemies):
			charging = charging or not e.charging_skill.is_empty()
		while m.players_can_act():
			var u: Combatant = m.first_ready_player()
			var lowest := 1.0
			for p in m.alive(m.players):
				lowest = minf(lowest, p.hp_ratio())
			if u.burst_ready() and (not _is_support(u) or lowest < 0.65 or charging):
				m.resolve_instant(m.plan_action(u, u.burst_skill, _choose_target(u, m.enemies), true))
			elif charging and u.hp_ratio() < 0.5:
				m.guard(u)
			else:
				m.resolve_instant(m.plan_action(u, u.normal_skill, _choose_target(u, m.enemies)))
			if m.all_enemies_dead():
				break
		if m.all_enemies_dead():
			if m.has_next_wave():
				m.advance_wave()
				continue
			return _won(m)
		for e in m.enemy_turn_order():
			if not e.is_alive():
				continue
			m.check_phase2(e)
			var act := EnemyAI.decide(e, m)
			match act["type"]:
				"charge":
					m.begin_charge(e, act["skill_id"])
				"summon":
					m.summon_minions(e)
				_:
					if act["target"] == null and Database.get_skill(act["skill_id"]).get("target", "") == "enemy_single":
						break
					m.resolve_instant(m.plan_action(e, act["skill_id"], act["target"]))
			if m.all_players_dead():
				return {"win": false, "xp": 0, "rounds": rounds}
		for ev in m.end_round():
			if ev["type"] == "hot":
				m.apply_hot(ev["unit"], ev["amount"])
			else:
				m.apply_dot(ev["unit"], ev["amount"])
		if m.all_players_dead():
			return {"win": false, "xp": 0, "rounds": rounds}
		if m.all_enemies_dead():
			if m.has_next_wave():
				m.advance_wave()
				continue
			return _won(m)
		m.start_player_phase()
		rounds += 1
		if rounds > 150:
			return {"win": false, "xp": 0, "rounds": rounds}
	return {}


func _won(m: BattleModel) -> Dictionary:
	var d := m.victory_data()
	d["win"] = true
	d["xp"] = m.xp_earned + int(m.stage.get("rewards", {}).get("xp", 0))
	return d


func _win_rate(sid: String, squad: Array, salt: int) -> float:
	var wins := 0
	for s in SAMPLES:
		if simulate(sid, _copy(squad), s * 7919 + salt)["win"]:
			wins += 1
	return wins / float(SAMPLES)


func _copy(squad: Array) -> Array:
	return squad.map(func(u): return u.duplicate())


func _gain(squad: Array, xp: int) -> void:
	for u in squad:
		Progression.add_unit_xp(u, xp)


## Evolves every capped hero whose next form exists (materials assumed farmed).
func _evolve_capped(squad: Array) -> bool:
	var any := false
	for u in squad:
		var d := Database.get_character(u["char_id"])
		var evo = d.get("evolution")
		if evo is Dictionary and int(u["level"]) >= int(d["max_level"]) and int(d["rarity"]) < 5:
			u["char_id"] = evo["into"]
			u["level"] = 1
			u["exp"] = 0
			any = true
	return any


func _all_capped(squad: Array) -> bool:
	for u in squad:
		if int(u["level"]) < int(Database.get_character(u["char_id"])["max_level"]):
			return false
	return true


func _run_starter(starter: String) -> void:
	var squad: Array = [{"uid": "u1", "char_id": starter, "level": 1, "exp": 0, "burst_level": 1}]
	var gift: String = Database.progression["unlock_gifts"]["ashroot_05"]["hero_by_starter"][starter]
	var extras := ["rhea_flintwhistle", "corin_saltmarsh", "wren_briarshot", "kael_emberclaw", "mira_tidesong", "thorne_mossguard"]
	extras = extras.filter(func(c): return c != starter and c != gift)
	var cleared: Array = []
	var line := "%-17s" % starter
	var evo_unlocked := false
	for sid in Database.stage_order:
		if sid == "ashroot_06":
			squad.append({"uid": "u2", "char_id": gift, "level": 1, "exp": 0, "burst_level": 1})
			Progression.add_unit_xp(squad[1], 3000)      # gift radiant wisp + early training
		if sid == "saltglass_01":
			# a couple of standard summons / more gift heroes by World 2
			for i in 2:
				squad.append({"uid": "u%d" % (3 + i), "char_id": extras[i], "level": 1, "exp": 0, "burst_level": 1})
				Progression.add_unit_xp(squad[-1], 6000)
		if sid == "ashroot_09":
			evo_unlocked = true
		var grinds := 0
		var wr := _win_rate(sid, squad, 13)
		while wr < 0.6 and grinds < 40:
			grinds += 1
			if evo_unlocked and _all_capped(squad):
				_evolve_capped(squad)
			var farm: String = cleared[-1] if not cleared.is_empty() else sid
			var r := simulate(farm, _copy(squad), 5000 + grinds)
			if r.get("win", false):
				_gain(squad, int(r["xp"]))
			if grinds % 4 == 0:
				wr = _win_rate(sid, squad, 13 + grinds)
		var clear := {}
		for t in 20:
			clear = simulate(sid, _copy(squad), 100000 + t * 31)
			if clear.get("win", false):
				break
		if clear.get("win", false):
			_gain(squad, int(clear["xp"]))
			cleared.append(sid)
		var lv := "/".join(squad.map(func(u): return str(u["level"]) + ("*" if int(Database.get_character(u["char_id"])["rarity"]) > 3 else "")))
		line += "\n   %-13s win %3d%%  grind %2d  squad L%s  stars %s" % [sid, int(wr * 100), grinds, lv,
				"".join(clear.get("stars", [false, false, false]).map(func(b): return "*" if b else "."))]
	print(line)
	var tline := "   towers:"
	for tid in Database.tower_order:
		for fl in [1, 5, 10]:
			var fid: String = Database.towers[tid]["stages"][fl - 1]["id"]
			tline += " %s%d=%d%%" % [tid.left(4), fl, int(_win_rate(fid, squad, 77) * 100)]
	print(tline)
