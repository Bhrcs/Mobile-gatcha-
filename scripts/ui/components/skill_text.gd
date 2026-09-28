class_name SkillText
extends RefCounted
## Short, scannable skill facts built from the skill data (not hand-written):
## "1 FOE", "220% ATK", "6 HITS", "HEAL", "BURN 20%" ... shown as chips above the
## flavour description, so players can compare skills at a glance.


static func tags(sk: Dictionary) -> Array:
	var out: Array = []
	out.append({"enemy_single": "1 FOE", "enemy_all": "ALL FOES", "ally_all": "ALL ALLIES", "ally_single": "1 ALLY",
			"self": "SELF"}.get(sk.get("target", ""), String(sk.get("target", "")).to_upper()))
	var power := float(sk.get("power", 0.0))
	if power > 0.0:
		out.append("%d%% ATK" % int(round(power * 100.0)))
	if int(sk.get("hits", 0)) > 1:
		out.append("%d HITS" % int(sk["hits"]))
	for eff in sk.get("effects", []):
		match String(eff.get("type", "")):
			"heal":
				if not out.has("HEAL"):
					out.append("HEAL")
			"cleanse":
				if not out.has("CLEANSE"):
					out.append("CLEANSE")
			"shield":
				if not out.has("SHIELD"):
					out.append("SHIELD")
			"status":
				var st := Database.get_status(String(eff.get("status", "")))
				var t := String(st.get("name", eff.get("status", ""))).to_upper()
				var ch := float(eff.get("chance", 1.0))
				if ch < 1.0:
					t += " %d%%" % int(round(ch * 100.0))
				if not out.has(t):
					out.append(t)
	return out


## Chip row for a skill.
static func chips(sk: Dictionary, accent: Color = UIKit.SKY) -> HFlowContainer:
	var row := HFlowContainer.new()
	row.name = "SkillTags"
	row.add_theme_constant_override("h_separation", UIKit.SP_S)
	row.add_theme_constant_override("v_separation", UIKit.SP_S)
	row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for t in tags(sk):
		row.add_child(UIKit.tag(t, accent.darkened(0.55)))
	return row
