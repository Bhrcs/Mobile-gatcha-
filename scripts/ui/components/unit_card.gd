class_name UnitCard
extends Control
## Collection tile: rarity frame, portrait on element backdrop, element orb,
## short name, level, stars, PARTY/LEADER tags and a selection state.

signal tapped(uid: String)

const W := 244
const H := 330

var unit: Dictionary = {}
var selected := false
var _frame: PanelFrame


static func make(u: Dictionary) -> UnitCard:
	var c := UnitCard.new()
	c.unit = u
	c.name = "UnitTile_%s" % u.get("uid", "")
	c.custom_minimum_size = Vector2(W, H)
	return c


func _ready() -> void:
	var def := Database.get_character(unit.get("char_id", ""))
	var rarity := int(def.get("rarity", 3))
	_frame = PanelFrame.make("rarity_%d" % clampi(rarity, 3, 6), 12)
	_frame.set_anchors_preset(Control.PRESET_FULL_RECT)
	_frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_frame)
	var v := UIKit.vbox(2)
	v.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_frame.add_child(v)
	var art := UIKit.portrait_art(def, Vector2(W - 24, 208))
	v.add_child(art)
	var name_l := UIKit.label(String(def.get("name", "")).split(" ")[0], 30, UIKit.TEXT, HORIZONTAL_ALIGNMENT_CENTER, 6)
	v.add_child(name_l)
	var row := UIKit.hbox(4)
	row.alignment = BoxContainer.ALIGNMENT_CENTER
	row.add_child(UIKit.orb(def.get("element", ""), 32))
	var lvl := int(unit.get("level", 1))
	var max_l := int(def.get("max_level", 20))
	row.add_child(UIKit.label("Lv.MAX" if lvl >= max_l else "Lv.%d" % lvl, 30, UIKit.GOLD, HORIZONTAL_ALIGNMENT_LEFT, 6))
	v.add_child(row)
	var stars := UIKit.stars(rarity, 16)
	stars.position = Vector2(W - 20 - rarity * 16, 190)
	add_child(stars)
	var uid: String = unit.get("uid", "")
	if GameManager.is_in_party(uid):
		var leader := GameManager.party_uids().find(uid) == 0
		var tag := UIKit.tag("LEADER" if leader else "PARTY", Color("#b8281e") if leader else Color("#2a5a9a"))
		tag.position = Vector2(14, 14)
		add_child(tag)
		if leader:
			var em := UIKit.icon("res://assets/icons/leader.png", 32)
			em.position = Vector2(W - 48, 14)
			add_child(em)
	var flags := UIKit.hbox(2)
	flags.position = Vector2(14, 150)
	if bool(unit.get("locked", false)):
		flags.add_child(UIKit.icon("res://assets/icons/lock.png", 32))
	if bool(unit.get("favorite", false)):
		flags.add_child(UIKit.icon("res://assets/icons/fav.png", 32))
	add_child(flags)
	if bool(unit.get("new", false)):
		var nt := UIKit.tag("NEW", Color("#c8281e"))
		nt.name = "NewTag"
		nt.position = Vector2(W - 90, 50)
		add_child(nt)
	elif GameManager.feature_unlocked("evolution") and GameManager.can_evolve(uid):
		var et := UIKit.tag("EVOLVE", Color("#8a5a10"))
		et.position = Vector2(W - 130, 50)
		add_child(et)
	if rarity >= 5:
		UIKit.sparkle(self, Rect2(12, 12, W - 24, 200))
	UIKit.on_tap(self, func(): tapped.emit(uid))


func set_selected(on: bool) -> void:
	selected = on
	modulate = Color(1.15, 1.1, 0.95) if on else Color.WHITE
