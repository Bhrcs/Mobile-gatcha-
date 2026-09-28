class_name RewardItem
extends Control
## Reward slot that "physically" pops in: bronze slot, item icon, quantity.

const SIZE := 150

var icon_path := ""
var qty_text := ""
var caption := ""
var px := SIZE
var hidden_start := true      # false: visible immediately (no pop-in)


static func make(icon_p: String, qty: String, cap := "", slot_px := SIZE) -> RewardItem:
	var r := RewardItem.new()
	r.icon_path = icon_p
	r.qty_text = qty
	r.caption = cap
	r.px = slot_px
	r.custom_minimum_size = Vector2(slot_px, slot_px + (40 if not cap.is_empty() else 0))
	return r


func _ready() -> void:
	var slot := PanelFrame.make("slot", 12)
	slot.size = Vector2(px, px)
	slot.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(slot)
	var isz := UIKit.snap_icon(int(px * 0.62))
	var ic := UIKit.icon(icon_path, isz)
	ic.position = Vector2((px - isz) / 2.0, px * 0.1)
	ic.size = Vector2(isz, isz)
	add_child(ic)
	var fs := 30 if px >= 130 else 20
	var q := UIKit.label(qty_text, fs, Color.WHITE, HORIZONTAL_ALIGNMENT_RIGHT, 6)
	q.position = Vector2(0, px - fs - 14)
	q.size = Vector2(px - 10, fs + 8)
	add_child(q)
	if not caption.is_empty():
		var c := UIKit.label(caption, 20, UIKit.MUTED, HORIZONTAL_ALIGNMENT_CENTER)
		c.position = Vector2(-20, px + 2)
		c.size = Vector2(px + 40, 36)
		add_child(c)
	modulate.a = 0.0 if hidden_start else 1.0
	pivot_offset = Vector2(px / 2.0, px / 2.0)


## Pop-in after `delay` seconds, with the reward sound (quiet when `silent`).
func pop(delay: float, silent := false) -> void:
	scale = Vector2(0.3, 0.3)
	var tw := create_tween()
	tw.tween_interval(delay)
	if not silent:
		tw.tween_callback(func(): AudioManager.play_sfx("reward", 0.05, -4.0))
	tw.set_parallel(true)
	tw.tween_property(self, "modulate:a", 1.0, 0.12)
	tw.tween_property(self, "scale", Vector2(1.15, 1.15), 0.12).set_trans(Tween.TRANS_BACK)
	tw.chain().tween_property(self, "scale", Vector2.ONE, 0.08)
